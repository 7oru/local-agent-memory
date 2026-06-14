from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .models import MEMORY_PRIVACY_LEVELS, MEMORY_RETENTION_POLICIES, SOURCE_KINDS
from .service import MemoryService, ServiceError
from .storage import default_db_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1

    db_path = Path(args.db or os.environ.get("LAM_DB_PATH") or default_db_path()).expanduser()
    service = MemoryService(db_path)

    try:
        return args.handler(args, service)
    except ServiceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lam", description="Local-first memory manager")
    parser.add_argument(
        "--db",
        help="SQLite database path. Defaults to LAM_DB_PATH or ~/.local-agent-memory/memory.db",
    )
    subparsers = parser.add_subparsers(dest="command")

    init = subparsers.add_parser("init", help="Initialize the local memory database")
    init.set_defaults(handler=_cmd_init)

    add = subparsers.add_parser("add", help="Add a memory")
    add.add_argument("content")
    add.add_argument("--scope", required=True)
    add.add_argument("--title")
    add.add_argument("--summary")
    add.add_argument("--subject")
    add.add_argument("--kind", default="note")
    add.add_argument("--confidence", type=float, default=1.0)
    add.add_argument("--salience", type=float, default=0.5)
    add.add_argument("--privacy", choices=MEMORY_PRIVACY_LEVELS, default="personal")
    add.add_argument("--retention", choices=MEMORY_RETENTION_POLICIES, default="default")
    add.add_argument("--source-kind", choices=SOURCE_KINDS, default="cli")
    add.add_argument("--source-ref")
    add.add_argument("--user-id")
    add.add_argument("--agent-id")
    add.add_argument("--app-id")
    add.add_argument("--run-id")
    add.add_argument("--entity", action="append", default=[])
    add.add_argument("--relation-json", action="append", default=[], metavar="JSON_OBJECT")
    add.add_argument("--metadata", action="append", default=[], metavar="KEY=VALUE")
    add.add_argument("--tag", action="append", default=[])
    add.add_argument("--pin", action="store_true")
    add.add_argument("--json", action="store_true")
    add.set_defaults(handler=_cmd_add)

    search = subparsers.add_parser("search", help="Search memories")
    search.add_argument("query")
    search.add_argument("--scope")
    search.add_argument("--status")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--include-inactive", action="store_true")
    search.add_argument("--json", action="store_true")
    search.set_defaults(handler=_cmd_search)

    list_cmd = subparsers.add_parser("list", help="List memories")
    list_cmd.add_argument("--scope")
    list_cmd.add_argument("--status")
    list_cmd.add_argument("--limit", type=int, default=100)
    list_cmd.add_argument("--include-inactive", action="store_true")
    list_cmd.add_argument("--json", action="store_true")
    list_cmd.set_defaults(handler=_cmd_list)

    pin = subparsers.add_parser("pin", help="Pin an active memory")
    pin.add_argument("id")
    pin.add_argument("--json", action="store_true")
    pin.set_defaults(handler=_cmd_pin)

    unpin = subparsers.add_parser("unpin", help="Unpin a pinned memory")
    unpin.add_argument("id")
    unpin.add_argument("--json", action="store_true")
    unpin.set_defaults(handler=_cmd_unpin)

    update = subparsers.add_parser("update", help="Update a memory")
    update.add_argument("id")
    update.add_argument("--content")
    update.add_argument("--title")
    update.add_argument("--summary")
    update.add_argument("--subject")
    update.add_argument("--scope")
    update.add_argument("--kind")
    update.add_argument("--status")
    update.add_argument("--confidence", type=float)
    update.add_argument("--salience", type=float)
    update.add_argument("--privacy", choices=MEMORY_PRIVACY_LEVELS)
    update.add_argument("--retention", choices=MEMORY_RETENTION_POLICIES)
    update.add_argument("--source-kind", choices=SOURCE_KINDS)
    update.add_argument("--source-ref")
    update.add_argument("--user-id")
    update.add_argument("--agent-id")
    update.add_argument("--app-id")
    update.add_argument("--run-id")
    update.add_argument("--entity", action="append")
    update.add_argument("--relation-json", action="append", metavar="JSON_OBJECT")
    update.add_argument("--metadata", action="append", metavar="KEY=VALUE")
    update.add_argument("--tag", action="append")
    update.add_argument("--json", action="store_true")
    update.set_defaults(handler=_cmd_update)

    delete = subparsers.add_parser("delete", help="Soft-delete a memory")
    delete.add_argument("id")
    delete.add_argument("--json", action="store_true")
    delete.set_defaults(handler=_cmd_delete)

    export = subparsers.add_parser("export", help="Export memories and audit events")
    export.add_argument("--format", choices=["json"], default="json")
    export.set_defaults(handler=_cmd_export)

    serve = subparsers.add_parser("serve", help="Run the HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=18790)
    serve.set_defaults(handler=_cmd_serve)

    mcp = subparsers.add_parser("mcp", help="Run the stdio MCP server")
    mcp.set_defaults(handler=_cmd_mcp)

    return parser


def _cmd_init(args: argparse.Namespace, service: MemoryService) -> int:
    service.initialize()
    db_path = Path(args.db or os.environ.get("LAM_DB_PATH") or default_db_path()).expanduser()
    print(f"initialized {db_path}")
    return 0


def _cmd_add(args: argparse.Namespace, service: MemoryService) -> int:
    memory = service.add_memory(
        args.content,
        scope=args.scope,
        title=args.title,
        summary=args.summary,
        subject=args.subject,
        kind=args.kind,
        confidence=args.confidence,
        salience=args.salience,
        privacy=args.privacy,
        retention=args.retention,
        source_kind=args.source_kind,
        source_ref=args.source_ref,
        user_id=args.user_id,
        agent_id=args.agent_id,
        app_id=args.app_id,
        run_id=args.run_id,
        entities=args.entity,
        relations=_parse_json_objects(args.relation_json, "--relation-json"),
        tags=args.tag,
        metadata=_parse_metadata(args.metadata),
        pin=args.pin,
        actor="cli",
    )
    _print_memory_or_json(memory.to_dict(), as_json=args.json)
    return 0


def _cmd_search(args: argparse.Namespace, service: MemoryService) -> int:
    memories = service.search(
        args.query,
        scope=args.scope,
        status=args.status,
        include_inactive=args.include_inactive,
        limit=args.limit,
    )
    _print_many([memory.to_dict() for memory in memories], as_json=args.json)
    return 0


def _cmd_list(args: argparse.Namespace, service: MemoryService) -> int:
    memories = service.list_memories(
        scope=args.scope,
        status=args.status,
        include_inactive=args.include_inactive,
        limit=args.limit,
    )
    _print_many([memory.to_dict() for memory in memories], as_json=args.json)
    return 0


def _cmd_pin(args: argparse.Namespace, service: MemoryService) -> int:
    memory = service.pin_memory(args.id, actor="cli")
    _print_memory_or_json(memory.to_dict(), as_json=args.json)
    return 0


def _cmd_unpin(args: argparse.Namespace, service: MemoryService) -> int:
    memory = service.unpin_memory(args.id, actor="cli")
    _print_memory_or_json(memory.to_dict(), as_json=args.json)
    return 0


def _cmd_update(args: argparse.Namespace, service: MemoryService) -> int:
    patch: dict[str, Any] = {}
    for field in (
        "content",
        "title",
        "summary",
        "subject",
        "scope",
        "kind",
        "status",
        "confidence",
        "salience",
        "privacy",
        "retention",
    ):
        value = getattr(args, field)
        if value is not None:
            patch[field] = value
    for field in ("source_kind", "source_ref", "user_id", "agent_id", "app_id", "run_id"):
        value = getattr(args, field)
        if value is not None:
            patch[field] = value
    if args.entity is not None:
        patch["entities"] = args.entity
    if args.relation_json is not None:
        patch["relations"] = _parse_json_objects(args.relation_json, "--relation-json")
    if args.metadata is not None:
        metadata = dict(service.get_memory(args.id).metadata)
        metadata.update(_parse_metadata(args.metadata))
        patch["metadata"] = metadata
    if args.tag is not None:
        patch["tags"] = args.tag
    memory = service.update_memory(args.id, patch, actor="cli")
    _print_memory_or_json(memory.to_dict(), as_json=args.json)
    return 0


def _cmd_delete(args: argparse.Namespace, service: MemoryService) -> int:
    memory = service.delete_memory(args.id, actor="cli")
    _print_memory_or_json(memory.to_dict(), as_json=args.json)
    return 0


def _cmd_export(args: argparse.Namespace, service: MemoryService) -> int:
    _ = args
    print(json.dumps(service.export_json(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_serve(args: argparse.Namespace, service: MemoryService) -> int:
    from .api import run_server

    run_server(db_path=service.repo.db_path, host=args.host, port=args.port)
    return 0


def _cmd_mcp(args: argparse.Namespace, service: MemoryService) -> int:
    _ = args
    from .mcp_server import run_stdio_server

    run_stdio_server(service)
    return 0


def _print_many(items: list[dict[str, Any]], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(items, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if not items:
        print("no memories")
        return
    _print_table(items)


def _print_memory_or_json(item: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True))
        return
    _print_table([item])


def _print_table(items: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "status",
        "kind",
        "scope",
        "title",
        "subject",
        "salience",
        "confidence",
        "source_kind",
        "source_ref",
        "created_at",
        "updated_at",
        "content",
    ]
    print("\t".join(fields))
    for item in items:
        print("\t".join(_cell(item.get(field)) for field in fields))


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", " ")


def _parse_metadata(items: list[str] | None) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for item in items or []:
        if "=" not in item:
            raise ServiceError("metadata must use KEY=VALUE")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ServiceError("metadata key is required")
        metadata[key] = _parse_metadata_value(raw_value)
    return metadata


def _parse_metadata_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _parse_json_objects(items: list[str] | None, option: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for item in items or []:
        try:
            parsed = json.loads(item)
        except json.JSONDecodeError as exc:
            raise ServiceError(f"{option} must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ServiceError(f"{option} must be a JSON object")
        objects.append(parsed)
    return objects
