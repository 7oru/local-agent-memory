# Implementation Tasks

## M0: Repo Foundation

- [x] Write MVP spec
- [x] Write architecture notes
- [x] Write implementation task list
- [x] Choose package name and CLI binary name
- [x] Add project scaffold
- [x] Add formatting and test commands
- [x] Add planning doc consistency check for pin/unpin MVP coverage

## M1: Core Storage

- [x] Create SQLite connection/config module
- [x] Add migrations for `memories`, `memory_events`, `memory_fts`, `settings`
- [x] Add normalized memory envelope fields and legacy SQLite migration path
- [x] Implement memory repository
- [x] Implement repository `pin_memory(id)` and `unpin_memory(id)` transitions between `active` and `pinned`
- [x] Write `pinned` and `unpinned` audit events from repository pin/unpin operations
- [x] Implement FTS5 indexing
- [x] Add soft delete
- [x] Add export to JSON
- [x] Add tests for create, update, delete, list, export
- [x] Add tests for pin/unpin persistence, idempotency, audit events, and exclusion of deleted/expired/superseded memories from pinned retrieval

## M2: Memory Service

- [x] Define memory schema/types
- [x] Add validation for scope, kind, status, confidence
- [x] Add secret-like content detection
- [x] Add pin/unpin service methods that validate lifecycle transitions and reject deleted, expired, archived, or superseded records
- [x] Add scoped pinned memory retrieval for exact scope plus `global`, excluding inactive statuses by default
- [x] Add scope-aware search
- [x] Add supersede flow
- [x] Add audit events for all writes

## M3: CLI

- [x] `lam init`
- [x] `lam add`
- [x] `lam search`
- [x] `lam list`
- [x] `lam pin <id>`
- [x] `lam unpin <id>`
- [x] `lam update`
- [x] `lam delete`
- [x] `lam export`
- [x] `lam serve`
- [x] `lam mcp`
- [x] Add CLI lifecycle test: `lam add --pin`, `lam list --status pinned`, `lam unpin <id>`, `lam list --status pinned`, `lam pin <id>`

## M4: HTTP API

- [x] `GET /health`
- [x] `GET /memories`
- [x] `POST /memories`
- [x] `GET /memories/{id}`
- [x] `PATCH /memories/{id}`
- [x] `DELETE /memories/{id}`
- [x] `POST /search`
- [x] `GET /pinned`
- [x] `GET /export`
- [x] Ensure `PATCH /memories/{id}` supports validated `status: pinned|active` pin/unpin transitions through the core service
- [x] Add HTTP lifecycle test that pins, reads `GET /pinned`, unpins, and confirms the memory is no longer pinned
- [x] API tests

## M5: MCP Server

- [x] Implement `memory_get_pinned`
- [x] Implement `memory_search`
- [x] Implement `memory_add`
- [x] Implement `memory_update`
- [x] Implement `memory_delete`
- [x] Verify `memory_update` can change `status` between `active` and `pinned` and `memory_get_pinned` reflects the change
- [x] Add MCP lifecycle test for add pinned memory, get pinned memory, unpin through update, and confirm pinned retrieval excludes it
- [x] Add MCP config examples for Codex, Claude Desktop, and OpenClaw where applicable
- [x] Add integration tests with representative tool calls

## M6: Minimal Web UI

- [x] Pinned memory list
- [x] Search with filters
- [x] Memory detail/edit panel
- [x] Delete/expire/supersede actions
- [x] Export button
- [x] MCP config snippet view

## M7: One-Command Local Run

- [x] Add `scripts/dev-up.sh`
- [x] Add Docker Compose only if it simplifies the local path
- [x] Confirm fresh clone startup path
- [x] Document default database path
- [x] Document reset and export flow

## Definition of Done

- [x] Fresh clone can run the MVP locally
- [x] Data survives restart
- [x] CLI, HTTP, and MCP all use the same core service
- [x] Search returns source and timestamp
- [x] Pinned memory can be added, listed, unpinned, and returned through CLI, HTTP, and MCP
- [x] Delete and export are tested
- [x] README has copy-paste setup instructions

## Pin/Unpin Lifecycle Acceptance Path

- [x] `lam add "用户偏好：个人 wiki 笔记默认写中文" --scope global --kind preference --pin` creates a `pinned` memory with source and timestamps
- [x] `lam list --scope global --status pinned` lists the new memory
- [x] `memory_get_pinned(scope: "global")` returns the same memory with provenance fields
- [x] `lam unpin <id>` changes the memory back to `active` and writes an `unpinned` audit event
- [x] `memory_get_pinned(scope: "global")` no longer returns the unpinned memory
- [x] `lam pin <id>` changes the memory back to `pinned` and writes a `pinned` audit event
- [x] `PATCH /memories/{id}` and `memory_update(id, { "status": "active" })` use the same core service path as `lam unpin`

## Session Review Improvements

- [x] Improve Web UI smoothness for long review transcripts with table snippets, quick add, Enter search, and busy state
- [x] Improve memory accuracy for imported/external-review provenance
- [x] Improve search/list performance for large memory content
