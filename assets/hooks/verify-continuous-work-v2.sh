#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-}"
if [[ -z "$ROOT" ]]; then
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
ROOT="$(cd "$ROOT" && pwd)"

python3 "$ROOT/.codex/tools/check_doc_freshness.py" "$ROOT"
python3 "$ROOT/.codex/tools/check_task_state.py" "$ROOT" --mode preflight

if [[ -f "$ROOT/.codex/state/project.json" ]]; then
  python3 "$ROOT/.codex/tools/cw_state.py" validate --root "$ROOT"
fi

python3 "$ROOT/.codex/tools/test_cw_supervisor.py"
python3 "$ROOT/.codex/tools/test_cw_app_server_spike.py"

printf 'continuous-work v2 verification passed: %s\n' "$ROOT"
