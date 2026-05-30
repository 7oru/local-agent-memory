from __future__ import annotations

import json
import sys
from typing import Any

from . import __version__
from .service import MemoryService, ServiceError

PROTOCOL_VERSION = "2024-11-05"


def run_stdio_server(service: MemoryService) -> None:
    service.initialize()
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle_request(service, json.loads(line))
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


def handle_request(service: MemoryService, request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    try:
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "local-agent-memory", "version": __version__},
            }
            return _result(request_id, result)
        if method == "ping":
            return _result(request_id, {})
        if method == "tools/list":
            return _result(request_id, {"tools": tool_definitions()})
        if method == "tools/call":
            params = request.get("params") or {}
            return _result(
                request_id, _call_tool(service, params.get("name"), params.get("arguments") or {})
            )
        return _error(request_id, -32601, f"unknown method: {method}")
    except json.JSONDecodeError as exc:
        return _error(request_id, -32700, str(exc))
    except ServiceError as exc:
        return _error(request_id, -32000, str(exc))
    except Exception as exc:  # pragma: no cover - defensive JSON-RPC boundary
        return _error(request_id, -32603, str(exc))


def tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "memory_get_pinned",
            "description": (
                "Return pinned memories for an optional scope, including global pinned memories."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                },
            },
        },
        {
            "name": "memory_search",
            "description": "Search memories by keyword with optional scope and limit filters.",
            "inputSchema": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "scope": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                },
            },
        },
        {
            "name": "memory_add",
            "description": (
                "Add a memory. Optional status/pin can create pinned memory through the service."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["content", "scope"],
                "properties": {
                    "content": {"type": "string"},
                    "scope": {"type": "string"},
                    "kind": {"type": "string"},
                    "source_ref": {"type": "string"},
                    "status": {"type": "string"},
                    "pin": {"type": "boolean"},
                },
            },
        },
        {
            "name": "memory_update",
            "description": (
                "Update a memory. status active/pinned uses the validated pin/unpin path."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["id", "patch"],
                "properties": {
                    "id": {"type": "string"},
                    "patch": {"type": "object"},
                },
            },
        },
        {
            "name": "memory_delete",
            "description": "Soft-delete a memory.",
            "inputSchema": {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}},
            },
        },
    ]


def _call_tool(
    service: MemoryService, name: str | None, arguments: dict[str, Any]
) -> dict[str, Any]:
    if name == "memory_get_pinned":
        data: Any = [
            memory.to_dict()
            for memory in service.get_pinned(
                scope=arguments.get("scope"),
                limit=arguments.get("limit", 100),
            )
        ]
    elif name == "memory_search":
        data = [
            memory.to_dict()
            for memory in service.search(
                arguments["query"],
                scope=arguments.get("scope"),
                limit=arguments.get("limit", 10),
            )
        ]
    elif name == "memory_add":
        data = service.add_memory(
            arguments["content"],
            scope=arguments["scope"],
            kind=arguments.get("kind", "note"),
            status=arguments.get("status"),
            pin=bool(arguments.get("pin", False)),
            source_kind="mcp",
            source_ref=arguments.get("source_ref"),
            actor="mcp",
        ).to_dict()
    elif name == "memory_update":
        data = service.update_memory(arguments["id"], arguments["patch"], actor="mcp").to_dict()
    elif name == "memory_delete":
        data = service.delete_memory(arguments["id"], actor="mcp").to_dict()
    else:
        raise ServiceError(f"unknown tool: {name}")

    return {
        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, sort_keys=True)}],
        "structuredContent": data,
        "isError": False,
    }


def _result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
