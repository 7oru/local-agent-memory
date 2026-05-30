from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import (
    ACTIVE_RETRIEVAL_STATUSES,
    Memory,
    MemoryEvent,
    dumps_json,
    utc_now,
)


class StorageError(RuntimeError):
    pass


class MemoryNotFoundError(StorageError):
    pass


class InvalidTransitionError(StorageError):
    pass


SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  kind TEXT NOT NULL,
  scope TEXT NOT NULL,
  status TEXT NOT NULL,
  confidence REAL NOT NULL,
  source_kind TEXT NOT NULL,
  source_ref TEXT,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  supersedes_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '[]',
  metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS memory_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  memory_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor TEXT NOT NULL DEFAULT 'system',
  data TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  FOREIGN KEY(memory_id) REFERENCES memories(id)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_scope_status_updated
ON memories(scope, status, updated_at);

CREATE INDEX IF NOT EXISTS idx_memories_status_updated
ON memories(status, updated_at);

CREATE INDEX IF NOT EXISTS idx_memory_events_memory_id
ON memory_events(memory_id, id);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
USING fts5(id UNINDEXED, content, kind, scope, tags);
"""


def default_db_path() -> Path:
    return Path.home() / ".local-agent-memory" / "memory.db"


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path).expanduser()
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _new_memory_id() -> str:
    return f"mem_{uuid4().hex[:16]}"


def _fts_query(query: str) -> str:
    tokens = [token.strip().replace('"', '""') for token in query.split() if token.strip()]
    if not tokens:
        return '""'
    return " ".join(f'"{token}"' for token in tokens)


class MemoryRepository:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path).expanduser() if db_path is not None else default_db_path()

    def initialize(self) -> None:
        with closing(connect(self.db_path)) as connection:
            connection.executescript(SCHEMA)
            connection.executescript(FTS_SCHEMA)

    def create_memory(
        self,
        content: str,
        scope: str,
        *,
        kind: str = "note",
        status: str = "active",
        confidence: float = 1.0,
        source_kind: str = "manual",
        source_ref: str | None = None,
        valid_from: str | None = None,
        valid_to: str | None = None,
        supersedes_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        actor: str = "system",
    ) -> Memory:
        self.initialize()
        now = utc_now()
        memory_id = _new_memory_id()
        row = {
            "id": memory_id,
            "content": content,
            "kind": kind,
            "scope": scope,
            "status": status,
            "confidence": confidence,
            "source_kind": source_kind,
            "source_ref": source_ref,
            "valid_from": valid_from or now,
            "valid_to": valid_to,
            "supersedes_id": supersedes_id,
            "created_at": now,
            "updated_at": now,
            "tags": dumps_json(tags or []),
            "metadata": dumps_json(metadata or {}),
        }
        with closing(connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT INTO memories (
                  id, content, kind, scope, status, confidence, source_kind, source_ref,
                  valid_from, valid_to, supersedes_id, created_at, updated_at, tags, metadata
                )
                VALUES (
                  :id, :content, :kind, :scope, :status, :confidence, :source_kind, :source_ref,
                  :valid_from, :valid_to, :supersedes_id, :created_at, :updated_at, :tags, :metadata
                )
                """,
                row,
            )
            self._replace_fts(connection, row)
            self._add_event(connection, memory_id, "created", actor, {"status": status})
            connection.commit()
        return self.get_memory(memory_id)

    def get_memory(self, memory_id: str) -> Memory:
        self.initialize()
        with closing(connect(self.db_path)) as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            raise MemoryNotFoundError(f"memory not found: {memory_id}")
        return Memory.from_row(row)

    def list_memories(
        self,
        *,
        scope: str | None = None,
        status: str | None = None,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> list[Memory]:
        self.initialize()
        where, params = self._filters(scope=scope, status=status, include_inactive=include_inactive)
        with closing(connect(self.db_path)) as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM memories
                {where}
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
        return [Memory.from_row(row) for row in rows]

    def update_memory(
        self,
        memory_id: str,
        patch: dict[str, Any],
        *,
        event_type: str = "updated",
        actor: str = "system",
    ) -> Memory:
        self.initialize()
        if not patch:
            return self.get_memory(memory_id)
        allowed_fields = {
            "content",
            "kind",
            "scope",
            "status",
            "confidence",
            "source_kind",
            "source_ref",
            "valid_from",
            "valid_to",
            "supersedes_id",
            "tags",
            "metadata",
        }
        unknown_fields = sorted(set(patch) - allowed_fields)
        if unknown_fields:
            raise StorageError(f"unknown memory fields: {', '.join(unknown_fields)}")

        stored_patch = dict(patch)
        if "tags" in stored_patch:
            stored_patch["tags"] = dumps_json(stored_patch["tags"] or [])
        if "metadata" in stored_patch:
            stored_patch["metadata"] = dumps_json(stored_patch["metadata"] or {})
        stored_patch["updated_at"] = utc_now()

        assignments = ", ".join(f"{field} = :{field}" for field in stored_patch)
        params = {"id": memory_id, **stored_patch}
        with closing(connect(self.db_path)) as connection:
            before = connection.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            if before is None:
                raise MemoryNotFoundError(f"memory not found: {memory_id}")
            connection.execute(f"UPDATE memories SET {assignments} WHERE id = :id", params)
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            self._replace_fts(connection, dict(row))
            self._add_event(
                connection,
                memory_id,
                event_type,
                actor,
                {"patch": patch, "previous_status": before["status"], "status": row["status"]},
            )
            connection.commit()
        return self.get_memory(memory_id)

    def pin_memory(self, memory_id: str, *, actor: str = "system") -> Memory:
        memory = self.get_memory(memory_id)
        if memory.status == "pinned":
            return memory
        if memory.status != "active":
            raise InvalidTransitionError(f"cannot pin memory with status {memory.status}")
        return self.update_memory(memory_id, {"status": "pinned"}, event_type="pinned", actor=actor)

    def unpin_memory(self, memory_id: str, *, actor: str = "system") -> Memory:
        memory = self.get_memory(memory_id)
        if memory.status == "active":
            return memory
        if memory.status != "pinned":
            raise InvalidTransitionError(f"cannot unpin memory with status {memory.status}")
        return self.update_memory(
            memory_id, {"status": "active"}, event_type="unpinned", actor=actor
        )

    def soft_delete(self, memory_id: str, *, actor: str = "system") -> Memory:
        memory = self.get_memory(memory_id)
        if memory.status == "deleted":
            return memory
        with closing(connect(self.db_path)) as connection:
            connection.execute(
                "UPDATE memories SET status = ?, updated_at = ? WHERE id = ?",
                ("deleted", utc_now(), memory_id),
            )
            connection.execute("DELETE FROM memory_fts WHERE id = ?", (memory_id,))
            self._add_event(
                connection, memory_id, "deleted", actor, {"previous_status": memory.status}
            )
            connection.commit()
        return self.get_memory(memory_id)

    def get_pinned(self, *, scope: str | None = None, limit: int = 100) -> list[Memory]:
        self.initialize()
        params: list[Any] = []
        if scope and scope != "global":
            scope_filter = "AND scope IN (?, 'global')"
            params.append(scope)
            order_scope = scope
        elif scope == "global":
            scope_filter = "AND scope = 'global'"
            order_scope = "global"
        else:
            scope_filter = ""
            order_scope = ""

        with closing(connect(self.db_path)) as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM memories
                WHERE status = 'pinned'
                {scope_filter}
                ORDER BY
                  CASE WHEN scope = ? THEN 0 WHEN scope = 'global' THEN 1 ELSE 2 END,
                  kind ASC,
                  updated_at DESC
                LIMIT ?
                """,
                [*params, order_scope, limit],
            ).fetchall()
        return [Memory.from_row(row) for row in rows]

    def search(
        self,
        query: str,
        *,
        scope: str | None = None,
        status: str | None = None,
        include_inactive: bool = False,
        limit: int = 10,
    ) -> list[Memory]:
        self.initialize()
        seen: set[str] = set()
        results: list[Memory] = []
        if query.strip():
            results.extend(
                self._search_fts(
                    query,
                    scope=scope,
                    status=status,
                    include_inactive=include_inactive,
                    limit=limit,
                )
            )
            seen.update(memory.id for memory in results)

        if len(results) < limit:
            for memory in self._search_like(
                query,
                scope=scope,
                status=status,
                include_inactive=include_inactive,
                limit=limit,
            ):
                if memory.id not in seen:
                    results.append(memory)
                    seen.add(memory.id)
                if len(results) >= limit:
                    break
        return results[:limit]

    def list_events(self, memory_id: str | None = None) -> list[MemoryEvent]:
        self.initialize()
        params: list[Any] = []
        where = ""
        if memory_id:
            where = "WHERE memory_id = ?"
            params.append(memory_id)
        with closing(connect(self.db_path)) as connection:
            rows = connection.execute(
                f"SELECT * FROM memory_events {where} ORDER BY id ASC", params
            ).fetchall()
        return [MemoryEvent.from_row(row) for row in rows]

    def export_json(self) -> dict[str, Any]:
        return {
            "memories": [memory.to_dict() for memory in self.list_memories(include_inactive=True)],
            "events": [event.to_dict() for event in self.list_events()],
        }

    def _filters(
        self,
        *,
        scope: str | None,
        status: str | None,
        include_inactive: bool,
        table_alias: str | None = None,
    ) -> tuple[str, list[Any]]:
        prefix = f"{table_alias}." if table_alias else ""
        clauses: list[str] = []
        params: list[Any] = []
        if scope:
            if scope == "global":
                clauses.append(f"{prefix}scope = ?")
                params.append(scope)
            else:
                clauses.append(f"{prefix}scope IN (?, 'global')")
                params.append(scope)
        if status:
            clauses.append(f"{prefix}status = ?")
            params.append(status)
        elif not include_inactive:
            placeholders = ", ".join("?" for _ in ACTIVE_RETRIEVAL_STATUSES)
            clauses.append(f"{prefix}status IN ({placeholders})")
            params.extend(ACTIVE_RETRIEVAL_STATUSES)
        if not clauses:
            return "", []
        return "WHERE " + " AND ".join(clauses), params

    def _search_fts(
        self,
        query: str,
        *,
        scope: str | None,
        status: str | None,
        include_inactive: bool,
        limit: int,
    ) -> list[Memory]:
        where, params = self._filters(
            scope=scope, status=status, include_inactive=include_inactive, table_alias="m"
        )
        fts_filter = "memory_fts MATCH ?"
        if where:
            where = where.replace("WHERE ", f"WHERE {fts_filter} AND ", 1)
        else:
            where = f"WHERE {fts_filter}"
        try:
            with closing(connect(self.db_path)) as connection:
                rows = connection.execute(
                    f"""
                    SELECT m.*, bm25(memory_fts) * -1 AS score
                    FROM memory_fts
                    JOIN memories m ON m.id = memory_fts.id
                    {where}
                    ORDER BY score DESC, m.updated_at DESC
                    LIMIT ?
                    """,
                    [_fts_query(query), *params, limit],
                ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [Memory.from_row(row) for row in rows]

    def _search_like(
        self,
        query: str,
        *,
        scope: str | None,
        status: str | None,
        include_inactive: bool,
        limit: int,
    ) -> list[Memory]:
        terms = [term for term in [query.strip(), *query.split()] if term]
        if not terms:
            return self.list_memories(
                scope=scope, status=status, include_inactive=include_inactive, limit=limit
            )
        where, params = self._filters(
            scope=scope, status=status, include_inactive=include_inactive, table_alias="m"
        )
        like_clauses = []
        like_params: list[str] = []
        for term in terms:
            like_clauses.append("(m.content LIKE ? OR m.kind LIKE ? OR m.scope LIKE ?)")
            value = f"%{term}%"
            like_params.extend([value, value, value])
        like_filter = "(" + " OR ".join(like_clauses) + ")"
        if where:
            where = where.replace("WHERE ", f"WHERE {like_filter} AND ", 1)
        else:
            where = f"WHERE {like_filter}"
        with closing(connect(self.db_path)) as connection:
            rows = connection.execute(
                f"""
                SELECT m.*, 0.0 AS score
                FROM memories m
                {where}
                ORDER BY m.updated_at DESC
                LIMIT ?
                """,
                [*like_params, *params, limit],
            ).fetchall()
        return [Memory.from_row(row) for row in rows]

    def _replace_fts(self, connection: sqlite3.Connection, row: dict[str, Any]) -> None:
        connection.execute("DELETE FROM memory_fts WHERE id = ?", (row["id"],))
        if row["status"] in ACTIVE_RETRIEVAL_STATUSES:
            connection.execute(
                "INSERT INTO memory_fts (id, content, kind, scope, tags) VALUES (?, ?, ?, ?, ?)",
                (row["id"], row["content"], row["kind"], row["scope"], row["tags"]),
            )

    def _add_event(
        self,
        connection: sqlite3.Connection,
        memory_id: str,
        event_type: str,
        actor: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO memory_events (memory_id, event_type, actor, data, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (memory_id, event_type, actor, dumps_json(data or {}), utc_now()),
        )
