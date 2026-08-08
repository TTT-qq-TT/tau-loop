#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-}"
if [[ -z "$ROOT" ]]; then
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
ROOT="$(cd "$ROOT" && pwd)"

# harness checks: doc freshness + task state (preflight + closeout)
python3 "$ROOT/.harness/tools/check_doc_freshness.py" "$ROOT"
python3 "$ROOT/.harness/tools/check_task_state.py" "$ROOT" --mode preflight
python3 "$ROOT/.harness/tools/check_task_state.py" "$ROOT" --mode closeout

# The source repository additionally proves that installed assets cannot drift.
if [[ -d "$ROOT/assets" ]]; then
  cmp -s "$ROOT/.harness/tools/check_doc_freshness.py" "$ROOT/assets/tools/check_doc_freshness.py"
  cmp -s "$ROOT/.harness/tools/check_task_state.py" "$ROOT/assets/tools/check_task_state.py"
  cmp -s "$ROOT/.harness/hooks/pre-task.sh" "$ROOT/assets/hooks/pre-task.sh"
  cmp -s "$ROOT/.harness/hooks/pre-task.py" "$ROOT/assets/hooks/pre-task.py"
  cmp -s "$ROOT/.harness/hooks/pre-closeout.sh" "$ROOT/assets/hooks/pre-closeout.sh"
  cmp -s "$ROOT/.harness/hooks/pre-closeout.py" "$ROOT/assets/hooks/pre-closeout.py"
  cmp -s "$ROOT/.harness/hooks/verify.sh" "$ROOT/assets/hooks/verify.sh"
  cmp -s "$ROOT/.harness/hooks/verify.py" "$ROOT/assets/hooks/verify.py"
  cmp -s "$ROOT/AGENTS.md" "$ROOT/assets/AGENTS.md"
fi

printf "tau-loop verification passed: %s\n" "$ROOT"
