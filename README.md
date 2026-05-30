# local-agent-memory

[中文](README.zh-CN.md) | English

Local-first Agent Memory Manager for personal agents.

`local-agent-memory` is a small, auditable memory layer for AI agents that runs on
your own machine. It exposes the same local memory store through CLI, HTTP, MCP,
and a minimal web UI, so you can add, inspect, pin, correct, delete, and export
what agents remember.

This repository is intentionally a personal experimental MVP. It is designed for
single-user local development, lightweight self-hosting, and agent integration
experiments. It is not a multi-user SaaS, a cloud sync service, or a secret store.

## What It Does

- Stores memories in a local SQLite database.
- Supports scoped memories such as `global`, `project:<name>`, `agent:<name>`,
  and `session:<id>`.
- Separates pinned memory from searchable memory.
- Preserves provenance fields such as source, confidence, status, and timestamps.
- Provides CLI for init, serve, add, search, pin, unpin, update, delete, export,
  and MCP.
- Serves a local HTTP API and minimal review UI.
- Exposes MCP tools for compatible agents.

## MVP Status

The current MVP is meant to prove a tight local loop:

```bash
./scripts/dev-up.sh
uv run lam add "User preference: write personal wiki notes in Chinese" --scope global --kind preference --pin
uv run lam search "wiki notes"
uv run lam serve
uv run lam mcp
```

See [docs/mvp.md](docs/mvp.md), [docs/architecture.md](docs/architecture.md), and
[docs/tasks.md](docs/tasks.md) for the scope, architecture, and completed task list.

## Requirements

- macOS, Linux, or another environment with Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) available on `PATH`
- SQLite with FTS5 support, which is included in the standard Python SQLite build
  on most developer machines

Install `uv` if needed:

```bash
python3 -m pip install uv
```

## Local Development

From a fresh clone:

```bash
git clone <repo-url>
cd local-agent-memory
./scripts/dev-up.sh
```

The setup command installs dependencies, creates the virtual environment through
`uv`, and initializes the SQLite database.

Useful development commands:

```bash
./scripts/dev-up.sh            # install dependencies and initialize the database
./scripts/dev-up.sh serve      # start the HTTP API and web UI
./scripts/dev-up.sh test       # initialize and run tests
./scripts/test.sh              # run the unittest suite
./scripts/format.sh            # run formatting/lint helpers
```

Direct CLI usage:

```bash
uv run lam init
uv run lam add "Project decision: keep SQLite as the default backend" --scope project:local-agent-memory --kind decision
uv run lam add "User preference: show concise summaries first" --scope global --kind preference --pin
uv run lam list --scope global --status pinned
uv run lam search "SQLite backend" --scope project:local-agent-memory
uv run lam export --format json > local-agent-memory-export.json
```

External review imports can preserve their real provenance instead of looking
like ordinary CLI-authored notes:

```bash
uv run lam add "Kimi reviewer verdict: practical MVP ready" \
  --scope project:local-agent-memory \
  --kind task_state \
  --source-kind import \
  --source-ref "kimi-api:moonshot-v1-128k" \
  --metadata model=moonshot-v1-128k \
  --metadata rounds=5
```

## Lightweight Local Deployment

The default deployment target is a single-user service bound to loopback.

```bash
LAM_HOST=127.0.0.1 \
LAM_PORT=18790 \
LAM_DB_PATH="$HOME/.local-agent-memory/memory.db" \
./scripts/dev-up.sh serve
```

Then open:

- Web UI: `http://127.0.0.1:18790/`
- Health check: `http://127.0.0.1:18790/health`
- Export endpoint: `http://127.0.0.1:18790/export`

The service initializes the database automatically when the API starts. Keep it
bound to `127.0.0.1` unless you have added your own network boundary, authentication,
and backup plan.

### Deployment Guidelines

- Keep the default loopback host for personal use: `LAM_HOST=127.0.0.1`.
- Choose a stable database path with `LAM_DB_PATH`; the default is
  `~/.local-agent-memory/memory.db`.
- Back up the SQLite file or periodically export JSON before experiments:
  `uv run lam export --format json > backup.json`.
- Do not store API keys, passwords, tokens, recovery phrases, or other secrets as
  memories.
- Use pinned memories only for small, durable preferences or operating rules that
  should always be injected.
- Prefer scoped memories for project facts: `project:<repo-or-system-name>`.
- Run the service under a simple process supervisor only after the foreground
  command works reliably on your machine.
- Check `/health` after startup and after changing environment variables.
- Reset a test database by deleting the SQLite file and running `uv run lam init`.

Example reset:

```bash
rm -f ~/.local-agent-memory/memory.db
uv run lam init
```

## HTTP API

Start the API:

```bash
./scripts/dev-up.sh serve
```

Key endpoints:

```text
GET    /
GET    /health
GET    /memories
POST   /memories
GET    /memories/{id}
PATCH  /memories/{id}
DELETE /memories/{id}
POST   /search
GET    /pinned
GET    /export
```

Example search request:

```bash
curl -s http://127.0.0.1:18790/search \
  -H 'content-type: application/json' \
  -d '{"query":"SQLite backend","scope":"project:local-agent-memory","limit":5}'
```

## MCP Integration

For MCP clients that support stdio servers, point them at the local CLI command.

```json
{
  "mcpServers": {
    "local-agent-memory": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/local-agent-memory",
        "run",
        "lam",
        "mcp"
      ],
      "env": {
        "LAM_DB_PATH": "~/.local-agent-memory/memory.db"
      }
    }
  }
}
```

Available MCP tools:

```text
memory_get_pinned
memory_search
memory_add
memory_update
memory_delete
```

For command-based OpenClaw MCP entries, use the same command, args, and environment:

```json
{
  "name": "local-agent-memory",
  "transport": "stdio",
  "command": "uv",
  "args": ["--directory", "/path/to/local-agent-memory", "run", "lam", "mcp"],
  "env": {
    "LAM_DB_PATH": "~/.local-agent-memory/memory.db"
  }
}
```

## Data Ownership

By default, data lives in:

```text
~/.local-agent-memory/memory.db
```

Use `LAM_DB_PATH` or the CLI-level `--db` option to point at another SQLite file:

```bash
LAM_DB_PATH=/tmp/lam-demo.db uv run lam add "Temporary test memory" --scope global
uv run lam --db /tmp/lam-demo.db list
```

Export is JSON and includes memory records plus audit events:

```bash
uv run lam export --format json > local-agent-memory-export.json
```

## Development Notes

This MVP borrows three product ideas:

- Mem0: expose memory as a small universal API, not as a hidden framework detail.
- Graphiti: preserve temporal state and conflict/supersession metadata.
- Letta: separate hot/pinned memory from cold/searchable memory.

The current implementation keeps SQLite-specific logic inside storage/service
layers so CLI, HTTP, UI, and MCP use the same core behavior.
