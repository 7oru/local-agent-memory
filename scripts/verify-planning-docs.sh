#!/usr/bin/env bash
set -euo pipefail

require_text() {
  local file="$1"
  local text="$2"
  local label="$3"

  if ! rg -q --fixed-strings -- "$text" "$file"; then
    printf 'missing planning-doc requirement: %s\n' "$label" >&2
    printf 'expected to find in %s: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

require_text README.md 'CLI for init, serve, add, search, pin, unpin, update, delete, export' 'README pin/unpin CLI scope'
require_text docs/mvp.md 'lam pin <id>' 'MVP CLI pin command'
require_text docs/mvp.md 'lam unpin <id>' 'MVP CLI unpin command'
require_text docs/mvp.md 'memory_update` must validate lifecycle status changes' 'MVP MCP unpin path'
require_text docs/tasks.md 'Implement repository `pin_memory(id)` and `unpin_memory(id)`' 'storage pin/unpin task'
require_text docs/tasks.md 'Add pin/unpin service methods' 'service pin/unpin task'
require_text docs/tasks.md '`lam pin <id>`' 'CLI pin task'
require_text docs/tasks.md '`lam unpin <id>`' 'CLI unpin task'
require_text docs/tasks.md 'Ensure `PATCH /memories/{id}` supports validated `status: pinned|active`' 'HTTP pin/unpin path'
require_text docs/tasks.md 'Verify `memory_update` can change `status` between `active` and `pinned`' 'MCP pin/unpin path'
require_text docs/tasks.md '## Pin/Unpin Lifecycle Acceptance Path' 'pin/unpin acceptance path'

printf 'planning docs include concrete pin/unpin implementation and verification coverage\n'
