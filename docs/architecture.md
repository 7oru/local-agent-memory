# Architecture

## Shape

```text
                CLI
                 |
Web UI ---- HTTP API ---- Core Memory Service ---- SQLite
                 |                 |
             MCP Server       Search Adapters
                                   |
                         FTS5 / sqlite-vec
```

The system should keep one core implementation for memory operations. CLI, HTTP, UI, and MCP are adapters around the same service layer.

## Recommended Stack

MVP default:

- Python 3.11+
- FastAPI for HTTP API
- Typer for CLI
- SQLite for storage
- SQLite FTS5 for keyword search
- optional `sqlite-vec` adapter for vector search
- MCP Python SDK or a thin stdio MCP server wrapper
- small frontend served by the API or built as static assets

Rationale:

- Python keeps local scripting, CLI, API, and agent integration simple.
- SQLite gives the best local one-command story.
- FTS5 is enough for the first useful search loop.
- Vector search can be optional so the MVP does not fail when native extensions are unavailable.

## Storage Layout

Suggested tables:

```text
memories
memory_events
memory_fts
memory_embeddings
settings
```

`memories` stores the canonical record.

`memory_events` stores audit history:

```text
created
updated
pinned
unpinned
expired
superseded
deleted
imported
```

`memory_fts` mirrors searchable text through FTS5.

`memory_embeddings` is optional. The system should still work without it.

## Write Flow

Manual memory creation:

```text
CLI/API/MCP request
  -> validate content and scope
  -> reject likely secrets
  -> insert memory
  -> insert audit event
  -> update FTS index
  -> create embedding if vector adapter is enabled
```

Session ingestion should not be automatic in v1. If added, it should create candidate memories for review:

```text
session transcript
  -> extract candidates
  -> policy filter
  -> inbox
  -> user approval
  -> durable memory
```

## Retrieval Flow

Pinned context:

```text
scope
  -> active pinned memories for exact scope
  -> active pinned global memories
  -> sort by kind and updated_at
```

Search:

```text
query + scope + filters
  -> FTS5 keyword candidates
  -> optional vector candidates
  -> merge scores
  -> filter inactive statuses by default
  -> return entries with provenance
```

Default retrieval should exclude:

- `deleted`
- `expired`
- `archived`
- `superseded`

unless the caller explicitly asks for those statuses.

## Conflict Handling

The MVP does not need full automatic contradiction detection. It does need the data path for replacement:

```text
lam supersede <old-id> "new memory"
```

This should:

- create the new memory
- set old memory status to `superseded`
- point old memory to the replacement id
- write audit events for both records

Future versions can add LLM-based conflict suggestions.

## Local Deployment

Target commands:

```bash
./scripts/dev-up.sh
lam serve
lam mcp
```

Default paths:

```text
~/.local-agent-memory/memory.db
~/.local-agent-memory/config.toml
```

Default ports:

```text
HTTP API: 127.0.0.1:18790
```

The service should bind to loopback by default.

## Postgres / pgvector Future

SQLite should be the default backend. Postgres + pgvector can come later behind the same repository interface:

```text
MemoryRepository
SearchIndex
EmbeddingIndex
AuditLog
```

Do not put SQLite-specific logic in CLI, MCP, or UI handlers. Keep it inside storage/search adapters.

## Security Rules

The MVP should avoid becoming a secret sink.

Minimum rules:

- warn or reject likely API keys and tokens
- never print full secret-like values in logs
- bind local server to `127.0.0.1` by default
- expose export and delete paths
- keep source and timestamp visible on every retrieval result
