from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from . import __version__
from .service import LifecycleError, MemoryService, NotFoundError, ServiceError, ValidationError
from .storage import default_db_path
from .web import index_html


class MemoryCreate(BaseModel):
    content: str
    scope: str
    kind: str = "note"
    pin: bool = False
    status: str | None = None
    confidence: float = 1.0
    source_ref: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryPatch(BaseModel):
    content: str | None = None
    scope: str | None = None
    kind: str | None = None
    status: str | None = None
    confidence: float | None = None
    source_ref: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def patch_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class SearchRequest(BaseModel):
    query: str
    scope: str | None = None
    status: str | None = None
    include_inactive: bool = False
    limit: int = 10
    content_limit: int | None = Field(default=None, ge=1, le=20_000)


class SupersedeRequest(BaseModel):
    content: str
    source_ref: str | None = None


def create_app(db_path: str | Path | None = None) -> FastAPI:
    service = MemoryService(_resolve_db_path(db_path))
    service.initialize()
    app = FastAPI(title="local-agent-memory", version=__version__)
    app.state.memory_service = service

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse("/app/pinned", status_code=307)

    @app.get("/app/{view}", response_class=HTMLResponse)
    def ui_view(view: str) -> str:
        if view not in {"pinned", "search", "settings"}:
            raise HTTPException(status_code=404, detail="unknown UI view")
        return index_html()

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "version": __version__, "db_path": str(service.repo.db_path)}

    @app.get("/memories")
    def list_memories(
        scope: str | None = None,
        status: str | None = None,
        include_inactive: bool = False,
        limit: int = Query(100, ge=1, le=500),
        content_limit: int | None = Query(None, ge=1, le=20_000),
    ) -> list[dict[str, Any]]:
        return _handle(
            lambda: [
                memory.to_dict(content_limit=content_limit)
                for memory in service.list_memories(
                    scope=scope,
                    status=status,
                    include_inactive=include_inactive,
                    limit=limit,
                )
            ]
        )

    @app.post("/memories", status_code=201)
    def create_memory(payload: MemoryCreate) -> dict[str, Any]:
        return _handle(
            lambda: service.add_memory(
                payload.content,
                scope=payload.scope,
                kind=payload.kind,
                pin=payload.pin,
                status=payload.status,
                confidence=payload.confidence,
                source_kind="api",
                source_ref=payload.source_ref,
                tags=payload.tags,
                metadata=payload.metadata,
                actor="api",
            ).to_dict()
        )

    @app.get("/memories/{memory_id}")
    def get_memory(memory_id: str) -> dict[str, Any]:
        return _handle(lambda: service.get_memory(memory_id).to_dict())

    @app.patch("/memories/{memory_id}")
    def update_memory(memory_id: str, payload: MemoryPatch) -> dict[str, Any]:
        return _handle(
            lambda: service.update_memory(memory_id, payload.patch_dict(), actor="api").to_dict()
        )

    @app.delete("/memories/{memory_id}")
    def delete_memory(memory_id: str) -> dict[str, Any]:
        return _handle(lambda: service.delete_memory(memory_id, actor="api").to_dict())

    @app.post("/memories/{memory_id}/supersede", status_code=201)
    def supersede_memory(memory_id: str, payload: SupersedeRequest) -> dict[str, Any]:
        return _handle(
            lambda: service.supersede_memory(
                memory_id,
                payload.content,
                actor="api",
                source_ref=payload.source_ref,
            ).to_dict()
        )

    @app.post("/search")
    def search(payload: SearchRequest) -> list[dict[str, Any]]:
        return _handle(
            lambda: [
                memory.to_dict(content_limit=payload.content_limit)
                for memory in service.search(
                    payload.query,
                    scope=payload.scope,
                    status=payload.status,
                    include_inactive=payload.include_inactive,
                    limit=payload.limit,
                )
            ]
        )

    @app.get("/pinned")
    def get_pinned(
        scope: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        content_limit: int | None = Query(None, ge=1, le=20_000),
    ) -> list[dict[str, Any]]:
        return _handle(
            lambda: [
                memory.to_dict(content_limit=content_limit)
                for memory in service.get_pinned(scope=scope, limit=limit)
            ]
        )

    @app.get("/export")
    def export() -> dict[str, Any]:
        return service.export_json()

    return app


def run_server(
    db_path: str | Path | None = None, *, host: str = "127.0.0.1", port: int = 18790
) -> None:
    import uvicorn

    app = create_app(db_path)
    uvicorn.run(app, host=host, port=port)


def _resolve_db_path(db_path: str | Path | None = None) -> Path:
    return Path(db_path or os.environ.get("LAM_DB_PATH") or default_db_path()).expanduser()


def _handle(callable_: Any) -> Any:
    try:
        return callable_()
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
