#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [[ "${1:-}" == "--root" ]]; then
  ROOT="${2:?missing root path}"
  shift 2
fi

EVENT="${1:?missing hook event}"
shift

case "$EVENT" in
  session_heartbeat)
    EVENT="heartbeat"
    ;;
  session_checkpoint)
    EVENT="checkpoint"
    ;;
  session_stop)
    EVENT="stop"
    ;;
esac

python3 "$ROOT/.codex/tools/cw_state.py" hook "$EVENT" --root "$ROOT" "$@"
