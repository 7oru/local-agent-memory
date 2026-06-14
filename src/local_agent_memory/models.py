from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from sqlite3 import Row
from typing import Any

ACTIVE_RETRIEVAL_STATUSES = ("active", "pinned")
INACTIVE_STATUSES = ("archived", "expired", "superseded", "deleted")
MEMORY_KINDS = ("preference", "fact", "decision", "procedure", "task_state", "note")
MEMORY_STATUSES = ACTIVE_RETRIEVAL_STATUSES + INACTIVE_STATUSES
MEMORY_SCHEMA_VERSION = "lam.memory.v1"
MEMORY_PRIVACY_LEVELS = ("public", "personal", "sensitive")
MEMORY_RETENTION_POLICIES = ("ephemeral", "default", "long_term", "permanent")
SOURCE_KINDS = ("manual", "cli", "api", "mcp", "session", "import")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def loads_json(value: str | None, default: Any) -> Any:
    if value in (None, ""):
        return default
    return json.loads(value)


@dataclass(frozen=True)
class Memory:
    id: str
    schema_version: str
    content: str
    title: str | None
    summary: str | None
    kind: str
    scope: str
    status: str
    confidence: float
    salience: float
    privacy: str
    retention: str
    subject: str | None
    entities: list[str]
    relations: list[dict[str, Any]]
    source_kind: str
    source_ref: str | None
    user_id: str | None
    agent_id: str | None
    app_id: str | None
    run_id: str | None
    valid_from: str
    valid_to: str | None
    supersedes_id: str | None
    created_at: str
    updated_at: str
    tags: list[str]
    metadata: dict[str, Any]
    score: float | None = None

    @classmethod
    def from_row(cls, row: Row) -> Memory:
        keys = set(row.keys())
        return cls(
            id=row["id"],
            schema_version=_row_value(row, keys, "schema_version", MEMORY_SCHEMA_VERSION),
            content=row["content"],
            title=_row_value(row, keys, "title"),
            summary=_row_value(row, keys, "summary"),
            kind=row["kind"],
            scope=row["scope"],
            status=row["status"],
            confidence=float(row["confidence"]),
            salience=float(_row_value(row, keys, "salience", 0.5)),
            privacy=_row_value(row, keys, "privacy", "personal"),
            retention=_row_value(row, keys, "retention", "default"),
            subject=_row_value(row, keys, "subject"),
            entities=list(loads_json(_row_value(row, keys, "entities"), [])),
            relations=list(loads_json(_row_value(row, keys, "relations"), [])),
            source_kind=row["source_kind"],
            source_ref=row["source_ref"],
            user_id=_row_value(row, keys, "user_id"),
            agent_id=_row_value(row, keys, "agent_id"),
            app_id=_row_value(row, keys, "app_id"),
            run_id=_row_value(row, keys, "run_id"),
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
            supersedes_id=row["supersedes_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            tags=list(loads_json(row["tags"], [])),
            metadata=dict(loads_json(row["metadata"], {})),
            score=float(row["score"]) if "score" in keys and row["score"] is not None else None,
        )

    def to_dict(self, *, content_limit: int | None = None) -> dict[str, Any]:
        content = self.content
        content_truncated = False
        if content_limit is not None and len(content) > content_limit:
            content = content[: max(content_limit - 1, 0)] + "…"
            content_truncated = True
        data = {
            "id": self.id,
            "schema_version": self.schema_version,
            "content": content,
            "title": self.title,
            "summary": self.summary,
            "kind": self.kind,
            "scope": self.scope,
            "status": self.status,
            "confidence": self.confidence,
            "salience": self.salience,
            "privacy": self.privacy,
            "retention": self.retention,
            "subject": self.subject,
            "entities": self.entities,
            "relations": self.relations,
            "source_kind": self.source_kind,
            "source_ref": self.source_ref,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "app_id": self.app_id,
            "run_id": self.run_id,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "supersedes_id": self.supersedes_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "metadata": self.metadata,
        }
        if content_limit is not None:
            data["content_length"] = len(self.content)
            data["content_truncated"] = content_truncated
        if self.score is not None:
            data["score"] = self.score
        return data


@dataclass(frozen=True)
class MemoryEvent:
    id: int
    memory_id: str
    event_type: str
    actor: str
    data: dict[str, Any]
    created_at: str

    @classmethod
    def from_row(cls, row: Row) -> MemoryEvent:
        return cls(
            id=int(row["id"]),
            memory_id=row["memory_id"],
            event_type=row["event_type"],
            actor=row["actor"],
            data=dict(loads_json(row["data"], {})),
            created_at=row["created_at"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "data": self.data,
            "created_at": self.created_at,
        }


def _row_value(row: Row, keys: set[str], key: str, default: Any = None) -> Any:
    if key not in keys:
        return default
    value = row[key]
    return default if value is None else value
