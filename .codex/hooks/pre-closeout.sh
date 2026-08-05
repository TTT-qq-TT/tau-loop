#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-}"
if [[ -z "$ROOT" ]]; then
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

python3 "$ROOT/.codex/tools/check_doc_freshness.py" "$ROOT"
python3 "$ROOT/.codex/tools/check_task_state.py" "$ROOT" --mode closeout
