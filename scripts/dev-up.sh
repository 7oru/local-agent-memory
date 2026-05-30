#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${LAM_PORT:-18790}"
HOST="${LAM_HOST:-127.0.0.1}"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/dev-up.sh          Install dependencies and initialize the database
  ./scripts/dev-up.sh serve    Install, initialize, and start the HTTP API
  ./scripts/dev-up.sh test     Install, initialize, and run tests
USAGE
}

ensure_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    printf 'uv is required. Install uv or run: python3 -m pip install uv\n' >&2
    exit 1
  fi
}

setup() {
  ensure_uv
  uv sync --extra dev
  uv run lam init
}

case "${1:-setup}" in
  setup)
    setup
    printf 'ready: uv run lam serve --host %s --port %s\n' "$HOST" "$PORT"
    ;;
  serve)
    setup
    exec uv run lam serve --host "$HOST" --port "$PORT"
    ;;
  test)
    setup
    ./scripts/test.sh
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

