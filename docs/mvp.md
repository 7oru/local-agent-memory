# MVP Spec

## Positioning

`local-agent-memory` is a local-first memory manager for AI agents. It gives agents a durable memory API while keeping the user in control of what is remembered, corrected, expired, and deleted.

The product thesis:

> RAG retrieves knowledge. Agent memory manages long-lived, user-governed context.

The MVP should be useful for a single developer running Codex, OpenClaw, Claude Desktop, or custom agents on one machine.

## Primary User Stories

1. As a user, I can add a memory manually and search it later.
2. As a user, I can pin important preferences so agents always receive them.
3. As a user, I can inspect where a memory came from before trusting it.
4. As a user, I can edit, delete, expire, or supersede wrong memories.
5. As an agent, I can retrieve relevant memories through MCP without knowing the database schema.
6. As a developer, I can start the system locally with one command and reset/export it easily.

## MVP Demo Flow

```bash
./scripts/dev-up.sh
lam init
lam add "用户偏好：个人 wiki 笔记默认写中文" --scope global --kind preference --pin
lam add "OpenClaw 默认模型是 minimax/MiniMax-M2.5" --scope project:openclaw --kind fact
lam search "OpenClaw 默认模型"
lam serve
lam mcp
```

Expected result:

- CLI search returns ranked memories with id, content, scope, source, confidence, and status.
- HTTP API is available at `http://127.0.0.1:18790`.
- Web UI shows pinned memories, searchable memories, and deleted/expired status.
- MCP tools can be configured in an agent client and used during a task.

## Core Concepts

### Memory Types

- `preference`: user preference or working style
- `fact`: factual project/user/environment information
- `decision`: an explicit decision and its rationale
- `procedure`: repeated workflow or operating rule
- `task_state`: durable task/project progress
- `note`: general long-term context

### Memory Scopes

- `global`: applies across all agents/projects
- `project:<name>`: applies to a project or repository
- `agent:<name>`: applies to a specific agent/runtime
- `session:<id>`: retained session context, usually not pinned

### Memory Status

- `active`: usable by retrieval
- `pinned`: always returned for matching scope
- `archived`: preserved but not normally retrieved
- `expired`: old information, hidden by default
- `superseded`: replaced by a newer memory
- `deleted`: soft-deleted for audit/export until vacuumed

## Data Model

Minimum fields for `memories`:

| Field | Purpose |
| --- | --- |
| `id` | stable memory id |
| `content` | user-facing memory text |
| `kind` | preference, fact, decision, procedure, task_state, note |
| `scope` | global, project, agent, session |
| `status` | active, pinned, archived, expired, superseded, deleted |
| `confidence` | 0.0 to 1.0 |
| `source_kind` | manual, cli, api, mcp, session, import |
| `source_ref` | session id, file path, URL, or command |
| `valid_from` | when this memory becomes valid |
| `valid_to` | optional expiration time |
| `supersedes_id` | old memory this replaces |
| `created_at` | creation timestamp |
| `updated_at` | last update timestamp |
| `tags` | JSON array |
| `metadata` | JSON object |

## CLI Surface

Required:

```bash
lam init
lam serve
lam mcp
lam add "..." --scope global --kind preference --pin
lam search "..." --scope project:foo
lam list --scope global --status active
lam list --scope global --status pinned
lam pin <id>
lam unpin <id>
lam update <id> --content "..."
lam delete <id>
lam export --format json
```

Nice-to-have:

```bash
lam import session.jsonl
lam expire <id>
lam supersede <old-id> "new memory text"
lam vacuum
```

## HTTP API

Required:

```text
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

## MCP Tools

Required:

```text
memory_get_pinned(scope?: string)
memory_search(query: string, scope?: string, limit?: number)
memory_add(content: string, scope: string, kind?: string, source_ref?: string)
memory_update(id: string, patch: object)
memory_delete(id: string)
```

`memory_update` must validate lifecycle status changes, including `active` to `pinned` and `pinned` to `active`, so MCP clients can unpin without a separate pin tool.

Tool responses must include:

- `id`
- `content`
- `kind`
- `scope`
- `status`
- `confidence`
- `source_kind`
- `source_ref`
- `created_at`
- `updated_at`

## Web UI

MVP pages:

- `Pinned`: hot memory that is always injected
- `Search`: searchable memory with filters
- `Inbox`: candidate memories awaiting user approval, optional in v1
- `Conflicts`: superseded/contradictory memories, optional in v1
- `Settings`: database path, export, reset, MCP config snippet

The UI should prioritize dense, inspectable data over a marketing-style landing page.

## Acceptance Criteria

The MVP is complete when:

- a fresh clone can start locally with one documented command
- memories persist in SQLite across restarts
- keyword search works with scope and status filters
- pinned memory can be added with `--pin`, listed with status filters, unpinned with `lam unpin` or `memory_update`, and returned through MCP
- every retrieved memory shows source and timestamp
- delete and export both work
- tests cover storage, search, CLI, and MCP tool behavior
- README includes a copy-paste MCP config example

## Differentiation

Compared with a basic session-RAG store, this MVP adds:

- explicit memory lifecycle
- hot/cold memory separation
- user-visible provenance
- scope-aware retrieval
- local-first data ownership
- MCP-native agent integration
