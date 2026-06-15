from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import (
    ACTIVE_RETRIEVAL_STATUSES,
    MEMORY_SCHEMA_VERSION,
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
  schema_version TEXT NOT NULL DEFAULT 'lam.memory.v1',
  content TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  kind TEXT NOT NULL,
  scope TEXT NOT NULL,
  status TEXT NOT NULL,
  confidence REAL NOT NULL,
  salience REAL NOT NULL DEFAULT 0.5,
  privacy TEXT NOT NULL DEFAULT 'personal',
  retention TEXT NOT NULL DEFAULT 'default',
  subject TEXT,
  entities TEXT NOT NULL DEFAULT '[]',
  relations TEXT NOT NULL DEFAULT '[]',
  source_kind TEXT NOT NULL,
  source_ref TEXT,
  user_id TEXT,
  agent_id TEXT,
  app_id TEXT,
  run_id TEXT,
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
USING fts5(id UNINDEXED, content, kind, scope, tags, title, summary, subject, entities);
"""

MEMORY_COLUMN_MIGRATIONS = {
    "schema_version": (
        "ALTER TABLE memories ADD COLUMN schema_version TEXT NOT NULL DEFAULT 'lam.memory.v1'"
    ),
    "title": "ALTER TABLE memories ADD COLUMN title TEXT",
    "summary": "ALTER TABLE memories ADD COLUMN summary TEXT",
    "salience": "ALTER TABLE memories ADD COLUMN salience REAL NOT NULL DEFAULT 0.5",
    "privacy": "ALTER TABLE memories ADD COLUMN privacy TEXT NOT NULL DEFAULT 'personal'",
    "retention": "ALTER TABLE memories ADD COLUMN retention TEXT NOT NULL DEFAULT 'default'",
    "subject": "ALTER TABLE memories ADD COLUMN subject TEXT",
    "entities": "ALTER TABLE memories ADD COLUMN entities TEXT NOT NULL DEFAULT '[]'",
    "relations": "ALTER TABLE memories ADD COLUMN relations TEXT NOT NULL DEFAULT '[]'",
    "user_id": "ALTER TABLE memories ADD COLUMN user_id TEXT",
    "agent_id": "ALTER TABLE memories ADD COLUMN agent_id TEXT",
    "app_id": "ALTER TABLE memories ADD COLUMN app_id TEXT",
    "run_id": "ALTER TABLE memories ADD COLUMN run_id TEXT",
}

FTS_COLUMNS = ("id", "content", "kind", "scope", "tags", "title", "summary", "subject", "entities")


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
            self._migrate_memories(connection)
            self._ensure_fts(connection)
            connection.commit()

    def create_memory(
        self,
        content: str,
        scope: str,
        *,
        title: str | None = None,
        summary: str | None = None,
        kind: str = "note",
        status: str = "active",
        confidence: float = 1.0,
        salience: float = 0.5,
        privacy: str = "personal",
        retention: str = "default",
        subject: str | None = None,
        entities: list[str] | None = None,
        relations: list[dict[str, Any]] | None = None,
        source_kind: str = "manual",
        source_ref: str | None = None,
        user_id: str | None = None,
        agent_id: str | None = None,
        app_id: str | None = None,
        run_id: str | None = None,
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
            "schema_version": MEMORY_SCHEMA_VERSION,
            "content": content,
            "title": title,
            "summary": summary,
            "kind": kind,
            "scope": scope,
            "status": status,
            "confidence": confidence,
            "salience": salience,
            "privacy": privacy,
            "retention": retention,
            "subject": subject,
            "entities": dumps_json(entities or []),
            "relations": dumps_json(relations or []),
            "source_kind": source_kind,
            "source_ref": source_ref,
            "user_id": user_id,
            "agent_id": agent_id,
            "app_id": app_id,
            "run_id": run_id,
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
                  id, schema_version, content, title, summary, kind, scope, status, confidence,
                  salience, privacy, retention, subject, entities, relations, source_kind,
                  source_ref, user_id, agent_id, app_id, run_id, valid_from, valid_to,
                  supersedes_id, created_at, updated_at, tags, metadata
                )
                VALUES (
                  :id, :schema_version, :content, :title, :summary, :kind, :scope, :status,
                  :confidence, :salience, :privacy, :retention, :subject, :entities, :relations,
                  :source_kind, :source_ref, :user_id, :agent_id, :app_id, :run_id, :valid_from,
                  :valid_to, :supersedes_id, :created_at, :updated_at, :tags, :metadata
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
        limit: int | None = 100,
    ) -> list[Memory]:
        self.initialize()
        where, params = self._filters(scope=scope, status=status, include_inactive=include_inactive)
        limit_clause = "" if limit is None else "LIMIT ?"
        query_params = params if limit is None else [*params, limit]
        with closing(connect(self.db_path)) as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM memories
                {where}
                ORDER BY updated_at DESC, created_at DESC
                {limit_clause}
                """,
                query_params,
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
            "title",
            "summary",
            "kind",
            "scope",
            "status",
            "confidence",
            "salience",
            "privacy",
            "retention",
            "subject",
            "entities",
            "relations",
            "source_kind",
            "source_ref",
            "user_id",
            "agent_id",
            "app_id",
            "run_id",
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
        if "entities" in stored_patch:
            stored_patch["entities"] = dumps_json(stored_patch["entities"] or [])
        if "relations" in stored_patch:
            stored_patch["relations"] = dumps_json(stored_patch["relations"] or [])
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
            "schema_version": MEMORY_SCHEMA_VERSION,
            "memories": [
                memory.to_dict()
                for memory in self.list_memories(include_inactive=True, limit=None)
            ],
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
            like_clauses.append(
                "("
                "m.content LIKE ? OR m.kind LIKE ? OR m.scope LIKE ? OR "
                "m.title LIKE ? OR m.summary LIKE ? OR m.subject LIKE ? OR m.entities LIKE ?"
                ")"
            )
            value = f"%{term}%"
            like_params.extend([value, value, value, value, value, value, value])
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
                """
                INSERT INTO memory_fts (
                  id, content, kind, scope, tags, title, summary, subject, entities
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["content"],
                    row["kind"],
                    row["scope"],
                    row["tags"],
                    row.get("title"),
                    row.get("summary"),
                    row.get("subject"),
                    row.get("entities", "[]"),
                ),
            )

    def _migrate_memories(self, connection: sqlite3.Connection) -> None:
        existing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(memories)").fetchall()
        }
        for column, statement in MEMORY_COLUMN_MIGRATIONS.items():
            if column not in existing_columns:
                connection.execute(statement)

    def _ensure_fts(self, connection: sqlite3.Connection) -> None:
        existing_columns = [
            row["name"] for row in connection.execute("PRAGMA table_info(memory_fts)").fetchall()
        ]
        rebuild = False
        if existing_columns and tuple(existing_columns) != FTS_COLUMNS:
            connection.execute("DROP TABLE memory_fts")
            rebuild = True
        elif not existing_columns:
            count = connection.execute("SELECT COUNT(*) AS count FROM memories").fetchone()["count"]
            rebuild = count > 0

        connection.executescript(FTS_SCHEMA)
        if rebuild:
            rows = connection.execute("SELECT * FROM memories").fetchall()
            for row in rows:
                self._replace_fts(connection, dict(row))

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
