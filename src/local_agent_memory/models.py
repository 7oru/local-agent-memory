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
    content: str
    kind: str
    scope: str
    status: str
    confidence: float
    source_kind: str
    source_ref: str | None
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
            content=row["content"],
            kind=row["kind"],
            scope=row["scope"],
            status=row["status"],
            confidence=float(row["confidence"]),
            source_kind=row["source_kind"],
            source_ref=row["source_ref"],
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
            supersedes_id=row["supersedes_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            tags=list(loads_json(row["tags"], [])),
            metadata=dict(loads_json(row["metadata"], {})),
            score=float(row["score"]) if "score" in keys and row["score"] is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "content": self.content,
            "kind": self.kind,
            "scope": self.scope,
            "status": self.status,
            "confidence": self.confidence,
            "source_kind": self.source_kind,
            "source_ref": self.source_ref,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "supersedes_id": self.supersedes_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "metadata": self.metadata,
        }
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
