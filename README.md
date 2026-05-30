# local-agent-memory

Local-first Agent Memory Manager.

`local-agent-memory` is a local, auditable memory layer for AI agents. It is meant to run on a developer's machine with one command, expose memory through CLI / HTTP / MCP, and let the user inspect, correct, pin, expire, delete, and export what agents remember.

The project is intentionally not "just another RAG store". The MVP treats memory as governed agent state:

- every memory has scope, source, confidence, status, and timestamps
- pinned memories are injected every time; searchable memories are retrieved on demand
- outdated or contradicted memories can be superseded instead of silently competing
- users can view, edit, delete, and export local memory data

## MVP Target

The first MVP should make this demo possible:

```bash
./scripts/dev-up.sh
lam add "用户偏好：个人 wiki 笔记默认写中文" --scope global --pin
lam search "wiki 笔记"
lam mcp
```

Then an MCP-capable agent can call:

```text
memory_get_pinned
memory_search
memory_add
memory_update
memory_delete
```

and receive memory entries with provenance instead of anonymous context snippets.

## First Version Scope

- SQLite local database under `~/.local-agent-memory/memory.db`
- SQLite FTS5 keyword search
- optional vector search adapter, starting with `sqlite-vec` when available
- CLI for init, serve, add, search, pin, unpin, update, delete, export
- HTTP API for UI and external integrations
- MCP server for agents
- minimal web UI for memory review and deletion
- local one-command startup for development and self-hosted use

Out of scope for the first MVP:

- multi-user SaaS
- cloud sync
- Postgres as the default backend
- full knowledge graph database
- automatic memory extraction from every transcript without review
- storing secrets, API keys, credentials, or highly sensitive personal data

## Design Notes

The MVP borrows three ideas from popular memory projects:

- Mem0: expose memory as a small universal API, not as a hidden framework detail
- Graphiti: preserve temporal state and conflict/supersession metadata
- Letta: separate hot/pinned memory from cold/searchable memory

See [docs/mvp.md](docs/mvp.md), [docs/architecture.md](docs/architecture.md), and [docs/tasks.md](docs/tasks.md) for the build plan.
