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

- [ ] Create SQLite connection/config module
- [ ] Add migrations for `memories`, `memory_events`, `memory_fts`, `settings`
- [ ] Implement memory repository
- [ ] Implement repository `pin_memory(id)` and `unpin_memory(id)` transitions between `active` and `pinned`
- [ ] Write `pinned` and `unpinned` audit events from repository pin/unpin operations
- [ ] Implement FTS5 indexing
- [ ] Add soft delete
- [ ] Add export to JSON
- [ ] Add tests for create, update, delete, list, export
- [ ] Add tests for pin/unpin persistence, idempotency, audit events, and exclusion of deleted/expired/superseded memories from pinned retrieval

## M2: Memory Service

- [ ] Define memory schema/types
- [ ] Add validation for scope, kind, status, confidence
- [ ] Add secret-like content detection
- [ ] Add pin/unpin service methods that validate lifecycle transitions and reject deleted, expired, archived, or superseded records
- [ ] Add scoped pinned memory retrieval for exact scope plus `global`, excluding inactive statuses by default
- [ ] Add scope-aware search
- [ ] Add supersede flow
- [ ] Add audit events for all writes

## M3: CLI

- [ ] `lam init`
- [ ] `lam add`
- [ ] `lam search`
- [ ] `lam list`
- [ ] `lam pin <id>`
- [ ] `lam unpin <id>`
- [ ] `lam update`
- [ ] `lam delete`
- [ ] `lam export`
- [ ] `lam serve`
- [ ] `lam mcp`
- [ ] Add CLI lifecycle test: `lam add --pin`, `lam list --status pinned`, `lam unpin <id>`, `lam list --status pinned`, `lam pin <id>`

## M4: HTTP API

- [ ] `GET /health`
- [ ] `GET /memories`
- [ ] `POST /memories`
- [ ] `GET /memories/{id}`
- [ ] `PATCH /memories/{id}`
- [ ] `DELETE /memories/{id}`
- [ ] `POST /search`
- [ ] `GET /pinned`
- [ ] `GET /export`
- [ ] Ensure `PATCH /memories/{id}` supports validated `status: pinned|active` pin/unpin transitions through the core service
- [ ] Add HTTP lifecycle test that pins, reads `GET /pinned`, unpins, and confirms the memory is no longer pinned
- [ ] API tests

## M5: MCP Server

- [ ] Implement `memory_get_pinned`
- [ ] Implement `memory_search`
- [ ] Implement `memory_add`
- [ ] Implement `memory_update`
- [ ] Implement `memory_delete`
- [ ] Verify `memory_update` can change `status` between `active` and `pinned` and `memory_get_pinned` reflects the change
- [ ] Add MCP lifecycle test for add pinned memory, get pinned memory, unpin through update, and confirm pinned retrieval excludes it
- [ ] Add MCP config examples for Codex, Claude Desktop, and OpenClaw where applicable
- [ ] Add integration tests with representative tool calls

## M6: Minimal Web UI

- [ ] Pinned memory list
- [ ] Search with filters
- [ ] Memory detail/edit panel
- [ ] Delete/expire/supersede actions
- [ ] Export button
- [ ] MCP config snippet view

## M7: One-Command Local Run

- [ ] Add `scripts/dev-up.sh`
- [ ] Add Docker Compose only if it simplifies the local path
- [ ] Confirm fresh clone startup path
- [ ] Document default database path
- [ ] Document reset and export flow

## Definition of Done

- [ ] Fresh clone can run the MVP locally
- [ ] Data survives restart
- [ ] CLI, HTTP, and MCP all use the same core service
- [ ] Search returns source and timestamp
- [ ] Pinned memory can be added, listed, unpinned, and returned through CLI, HTTP, and MCP
- [ ] Delete and export are tested
- [ ] README has copy-paste setup instructions

## Pin/Unpin Lifecycle Acceptance Path

- [ ] `lam add "用户偏好：个人 wiki 笔记默认写中文" --scope global --kind preference --pin` creates a `pinned` memory with source and timestamps
- [ ] `lam list --scope global --status pinned` lists the new memory
- [ ] `memory_get_pinned(scope: "global")` returns the same memory with provenance fields
- [ ] `lam unpin <id>` changes the memory back to `active` and writes an `unpinned` audit event
- [ ] `memory_get_pinned(scope: "global")` no longer returns the unpinned memory
- [ ] `lam pin <id>` changes the memory back to `pinned` and writes a `pinned` audit event
- [ ] `PATCH /memories/{id}` and `memory_update(id, { "status": "active" })` use the same core service path as `lam unpin`
