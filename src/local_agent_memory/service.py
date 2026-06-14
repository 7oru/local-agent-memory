from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import (
    MEMORY_KINDS,
    MEMORY_PRIVACY_LEVELS,
    MEMORY_RETENTION_POLICIES,
    MEMORY_STATUSES,
    SOURCE_KINDS,
    Memory,
)
from .storage import InvalidTransitionError, MemoryNotFoundError, MemoryRepository


class ServiceError(ValueError):
    pass


class ValidationError(ServiceError):
    pass


class SecretLikeContentError(ValidationError):
    pass


class LifecycleError(ServiceError):
    pass


class NotFoundError(ServiceError):
    pass


SCOPE_RE = re.compile(r"^(global|(?:project|agent|session):[A-Za-z0-9][A-Za-z0-9._/-]*)$")
SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./=+-]{16,}"
    ),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b[A-Za-z0-9_=-]{24,}\.[A-Za-z0-9_=-]{6,}\.[A-Za-z0-9_=-]{20,}\b"),
)
BLOCKED_PIN_STATUSES = {"deleted", "expired", "archived", "superseded"}


class MemoryService:
    def __init__(
        self, db_path: str | Path | None = None, repo: MemoryRepository | None = None
    ) -> None:
        self.repo = repo or MemoryRepository(db_path)

    def initialize(self) -> None:
        self.repo.initialize()

    def add_memory(
        self,
        content: str,
        *,
        scope: str,
        title: str | None = None,
        summary: str | None = None,
        kind: str = "note",
        pin: bool = False,
        status: str | None = None,
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
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        supersedes_id: str | None = None,
        actor: str = "service",
    ) -> Memory:
        normalized_status = status or ("pinned" if pin else "active")
        if pin and normalized_status != "pinned":
            raise ValidationError("--pin requires status pinned")
        validated = self._validate_memory_fields(
            {
                "content": content,
                "title": title,
                "summary": summary,
                "scope": scope,
                "kind": kind,
                "status": normalized_status,
                "confidence": confidence,
                "salience": salience,
                "privacy": privacy,
                "retention": retention,
                "subject": subject,
                "entities": entities or [],
                "relations": relations or [],
                "source_kind": source_kind,
                "user_id": user_id,
                "agent_id": agent_id,
                "app_id": app_id,
                "run_id": run_id,
                "tags": tags or [],
                "metadata": metadata or {},
            },
            partial=False,
        )
        return self.repo.create_memory(
            validated["content"],
            validated["scope"],
            title=validated["title"],
            summary=validated["summary"],
            kind=validated["kind"],
            status=validated["status"],
            confidence=validated["confidence"],
            salience=validated["salience"],
            privacy=validated["privacy"],
            retention=validated["retention"],
            subject=validated["subject"],
            entities=validated["entities"],
            relations=validated["relations"],
            source_kind=validated["source_kind"],
            source_ref=source_ref,
            user_id=validated["user_id"],
            agent_id=validated["agent_id"],
            app_id=validated["app_id"],
            run_id=validated["run_id"],
            tags=validated["tags"],
            metadata=validated["metadata"],
            supersedes_id=supersedes_id,
            actor=actor,
        )

    def get_memory(self, memory_id: str) -> Memory:
        try:
            return self.repo.get_memory(memory_id)
        except MemoryNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

    def list_memories(
        self,
        *,
        scope: str | None = None,
        status: str | None = None,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> list[Memory]:
        if scope is not None:
            self._validate_scope(scope)
        if status is not None:
            self._validate_status(status)
        return self.repo.list_memories(
            scope=scope,
            status=status,
            include_inactive=include_inactive,
            limit=self._limit(limit, 500),
        )

    def search(
        self,
        query: str,
        *,
        scope: str | None = None,
        status: str | None = None,
        include_inactive: bool = False,
        limit: int = 10,
    ) -> list[Memory]:
        if not query.strip():
            raise ValidationError("query is required")
        if scope is not None:
            self._validate_scope(scope)
        if status is not None:
            self._validate_status(status)
        return self.repo.search(
            query,
            scope=scope,
            status=status,
            include_inactive=include_inactive,
            limit=self._limit(limit, 100),
        )

    def get_pinned(self, *, scope: str | None = None, limit: int = 100) -> list[Memory]:
        if scope is not None:
            self._validate_scope(scope)
        return self.repo.get_pinned(scope=scope, limit=self._limit(limit, 500))

    def update_memory(
        self, memory_id: str, patch: dict[str, Any], *, actor: str = "service"
    ) -> Memory:
        if not patch:
            return self.get_memory(memory_id)
        current = self.get_memory(memory_id)
        validated = self._validate_memory_fields(patch, partial=True)

        desired_status = validated.pop("status", None)
        if desired_status == "pinned":
            if validated:
                current = self.repo.update_memory(memory_id, validated, actor=actor)
            return self.pin_memory(current.id, actor=actor)
        if desired_status == "active":
            if validated:
                current = self.repo.update_memory(memory_id, validated, actor=actor)
            return self.unpin_memory(current.id, actor=actor)
        if desired_status == "deleted":
            if validated:
                self.repo.update_memory(memory_id, validated, actor=actor)
            return self.delete_memory(memory_id, actor=actor)
        if desired_status is not None:
            validated["status"] = desired_status

        if current.status == "deleted":
            raise LifecycleError("deleted memories cannot be updated")
        try:
            return self.repo.update_memory(memory_id, validated, actor=actor)
        except MemoryNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

    def pin_memory(self, memory_id: str, *, actor: str = "service") -> Memory:
        current = self.get_memory(memory_id)
        if current.status in BLOCKED_PIN_STATUSES:
            raise LifecycleError(f"cannot pin memory with status {current.status}")
        try:
            return self.repo.pin_memory(memory_id, actor=actor)
        except InvalidTransitionError as exc:
            raise LifecycleError(str(exc)) from exc

    def unpin_memory(self, memory_id: str, *, actor: str = "service") -> Memory:
        current = self.get_memory(memory_id)
        if current.status in BLOCKED_PIN_STATUSES:
            raise LifecycleError(f"cannot unpin memory with status {current.status}")
        try:
            return self.repo.unpin_memory(memory_id, actor=actor)
        except InvalidTransitionError as exc:
            raise LifecycleError(str(exc)) from exc

    def delete_memory(self, memory_id: str, *, actor: str = "service") -> Memory:
        try:
            return self.repo.soft_delete(memory_id, actor=actor)
        except MemoryNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

    def supersede_memory(
        self,
        old_id: str,
        new_content: str,
        *,
        actor: str = "service",
        source_ref: str | None = None,
    ) -> Memory:
        old = self.get_memory(old_id)
        if old.status == "deleted":
            raise LifecycleError("deleted memories cannot be superseded")
        new_memory = self.add_memory(
            new_content,
            scope=old.scope,
            title=old.title,
            summary=old.summary,
            kind=old.kind,
            confidence=old.confidence,
            salience=old.salience,
            privacy=old.privacy,
            retention=old.retention,
            subject=old.subject,
            entities=old.entities,
            relations=old.relations,
            source_kind=old.source_kind,
            source_ref=source_ref or old.source_ref,
            user_id=old.user_id,
            agent_id=old.agent_id,
            app_id=old.app_id,
            run_id=old.run_id,
            tags=old.tags,
            metadata={**old.metadata, "supersedes_id": old.id},
            actor=actor,
        )
        self.repo.update_memory(
            old.id,
            {"status": "superseded", "supersedes_id": new_memory.id},
            event_type="superseded",
            actor=actor,
        )
        return new_memory

    def export_json(self) -> dict[str, Any]:
        return self.repo.export_json()

    def _validate_memory_fields(self, fields: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        validated = dict(fields)
        required = ("content", "scope", "kind", "status", "confidence", "source_kind")
        if not partial:
            missing = [field for field in required if field not in validated]
            if missing:
                raise ValidationError(f"missing fields: {', '.join(missing)}")
        if "content" in validated:
            validated["content"] = self._validate_content(validated["content"])
        for field in ("title", "summary", "subject", "user_id", "agent_id", "app_id", "run_id"):
            if field in validated:
                validated[field] = self._validate_optional_text(
                    validated[field],
                    field=field,
                    max_length=2_000 if field in {"summary"} else 256,
                )
        if "scope" in validated:
            validated["scope"] = self._validate_scope(validated["scope"])
        if "kind" in validated:
            validated["kind"] = self._validate_kind(validated["kind"])
        if "status" in validated:
            validated["status"] = self._validate_status(validated["status"])
        if "confidence" in validated:
            validated["confidence"] = self._validate_confidence(validated["confidence"])
        if "salience" in validated:
            validated["salience"] = self._validate_salience(validated["salience"])
        if "privacy" in validated:
            validated["privacy"] = self._validate_privacy(validated["privacy"])
        if "retention" in validated:
            validated["retention"] = self._validate_retention(validated["retention"])
        if "source_kind" in validated:
            validated["source_kind"] = self._validate_source_kind(validated["source_kind"])
        if "entities" in validated:
            validated["entities"] = self._validate_entities(validated["entities"])
        if "relations" in validated:
            validated["relations"] = self._validate_relations(validated["relations"])
        if "tags" in validated:
            validated["tags"] = self._validate_tags(validated["tags"])
        if "metadata" in validated:
            validated["metadata"] = self._validate_metadata(validated["metadata"])
        return validated

    def _validate_content(self, content: Any) -> str:
        if not isinstance(content, str) or not content.strip():
            raise ValidationError("content is required")
        normalized = content.strip()
        if len(normalized) > 20_000:
            raise ValidationError("content is too long")
        if any(pattern.search(normalized) for pattern in SECRET_PATTERNS):
            raise SecretLikeContentError("content looks like a secret or credential")
        return normalized

    def _validate_optional_text(self, value: Any, *, field: str, max_length: int) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValidationError(f"{field} must be a string")
        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) > max_length:
            raise ValidationError(f"{field} is too long")
        return normalized

    def _validate_scope(self, scope: Any) -> str:
        if not isinstance(scope, str) or not SCOPE_RE.match(scope):
            raise ValidationError(
                "scope must be global, project:<name>, agent:<name>, or session:<id>"
            )
        return scope

    def _validate_kind(self, kind: Any) -> str:
        if kind not in MEMORY_KINDS:
            raise ValidationError(f"kind must be one of: {', '.join(MEMORY_KINDS)}")
        return kind

    def _validate_status(self, status: Any) -> str:
        if status not in MEMORY_STATUSES:
            raise ValidationError(f"status must be one of: {', '.join(MEMORY_STATUSES)}")
        return status

    def _validate_confidence(self, confidence: Any) -> float:
        try:
            value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise ValidationError("confidence must be a number from 0.0 to 1.0") from exc
        if value < 0.0 or value > 1.0:
            raise ValidationError("confidence must be from 0.0 to 1.0")
        return value

    def _validate_salience(self, salience: Any) -> float:
        try:
            value = float(salience)
        except (TypeError, ValueError) as exc:
            raise ValidationError("salience must be a number from 0.0 to 1.0") from exc
        if value < 0.0 or value > 1.0:
            raise ValidationError("salience must be from 0.0 to 1.0")
        return value

    def _validate_privacy(self, privacy: Any) -> str:
        if privacy not in MEMORY_PRIVACY_LEVELS:
            raise ValidationError(f"privacy must be one of: {', '.join(MEMORY_PRIVACY_LEVELS)}")
        return privacy

    def _validate_retention(self, retention: Any) -> str:
        if retention not in MEMORY_RETENTION_POLICIES:
            raise ValidationError(
                f"retention must be one of: {', '.join(MEMORY_RETENTION_POLICIES)}"
            )
        return retention

    def _validate_source_kind(self, source_kind: Any) -> str:
        if source_kind not in SOURCE_KINDS:
            raise ValidationError(f"source_kind must be one of: {', '.join(SOURCE_KINDS)}")
        return source_kind

    def _validate_entities(self, entities: Any) -> list[str]:
        if not isinstance(entities, list) or any(
            not isinstance(entity, str) for entity in entities
        ):
            raise ValidationError("entities must be a list of strings")
        seen: set[str] = set()
        normalized: list[str] = []
        for entity in entities:
            value = entity.strip()
            if value and value not in seen:
                normalized.append(value)
                seen.add(value)
        return normalized

    def _validate_relations(self, relations: Any) -> list[dict[str, Any]]:
        if not isinstance(relations, list) or any(
            not isinstance(relation, dict) for relation in relations
        ):
            raise ValidationError("relations must be a list of objects")
        return relations

    def _validate_tags(self, tags: Any) -> list[str]:
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise ValidationError("tags must be a list of strings")
        return [tag.strip() for tag in tags if tag.strip()]

    def _validate_metadata(self, metadata: Any) -> dict[str, Any]:
        if not isinstance(metadata, dict):
            raise ValidationError("metadata must be an object")
        return metadata

    def _limit(self, limit: int, maximum: int) -> int:
        try:
            value = int(limit)
        except (TypeError, ValueError) as exc:
            raise ValidationError("limit must be an integer") from exc
        if value < 1:
            raise ValidationError("limit must be at least 1")
        return min(value, maximum)
