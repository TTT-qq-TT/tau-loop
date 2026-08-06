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
python3 "$ROOT/.codex/tools/test_cw_agent_session.py"
python3 "$ROOT/.codex/tools/test_cw_agent_events.py"
python3 "$ROOT/.codex/tools/test_cw_agent_executor.py"
python3 "$ROOT/.codex/tools/test_cw_agent_guardrails.py"
python3 "$ROOT/.codex/tools/test_cw_agent_backends.py"
python3 "$ROOT/.codex/tools/test_cw_agent_runner.py"
python3 "$ROOT/.codex/tools/test_cw_app_server_spike.py"

# The source repository additionally proves that installed assets cannot drift.
if [[ -f "$ROOT/assets/tools/cw_supervisor.py" ]]; then
  python3 "$ROOT/assets/tools/test_cw_supervisor.py"
  python3 "$ROOT/assets/tools/test_cw_agent_session.py"
  python3 "$ROOT/assets/tools/test_cw_agent_events.py"
  python3 "$ROOT/assets/tools/test_cw_agent_executor.py"
  python3 "$ROOT/assets/tools/test_cw_agent_guardrails.py"
  python3 "$ROOT/assets/tools/test_cw_agent_backends.py"
  python3 "$ROOT/assets/tools/test_cw_agent_runner.py"
  python3 "$ROOT/assets/tools/test_cw_app_server_spike.py"
  cmp -s "$ROOT/.codex/tools/cw_supervisor.py" "$ROOT/assets/tools/cw_supervisor.py"
  cmp -s "$ROOT/.codex/tools/test_cw_supervisor.py" "$ROOT/assets/tools/test_cw_supervisor.py"
  cmp -s "$ROOT/.codex/tools/cw_agent_session.py" "$ROOT/assets/tools/cw_agent_session.py"
  cmp -s "$ROOT/.codex/tools/test_cw_agent_session.py" "$ROOT/assets/tools/test_cw_agent_session.py"
  cmp -s "$ROOT/.codex/tools/cw_agent_events.py" "$ROOT/assets/tools/cw_agent_events.py"
  cmp -s "$ROOT/.codex/tools/test_cw_agent_events.py" "$ROOT/assets/tools/test_cw_agent_events.py"
  cmp -s "$ROOT/.codex/tools/cw_agent_executor.py" "$ROOT/assets/tools/cw_agent_executor.py"
  cmp -s "$ROOT/.codex/tools/test_cw_agent_executor.py" "$ROOT/assets/tools/test_cw_agent_executor.py"
  cmp -s "$ROOT/.codex/tools/cw_agent_guardrails.py" "$ROOT/assets/tools/cw_agent_guardrails.py"
  cmp -s "$ROOT/.codex/tools/test_cw_agent_guardrails.py" "$ROOT/assets/tools/test_cw_agent_guardrails.py"
  cmp -s "$ROOT/.codex/tools/cw_agent_backends.py" "$ROOT/assets/tools/cw_agent_backends.py"
  cmp -s "$ROOT/.codex/tools/test_cw_agent_backends.py" "$ROOT/assets/tools/test_cw_agent_backends.py"
  cmp -s "$ROOT/.codex/tools/cw_agent_runner.py" "$ROOT/assets/tools/cw_agent_runner.py"
  cmp -s "$ROOT/.codex/tools/test_cw_agent_runner.py" "$ROOT/assets/tools/test_cw_agent_runner.py"
  cmp -s "$ROOT/.codex/tools/cw_app_server_spike.py" "$ROOT/assets/tools/cw_app_server_spike.py"
  cmp -s "$ROOT/.codex/tools/test_cw_app_server_spike.py" "$ROOT/assets/tools/test_cw_app_server_spike.py"
  help_dir="$(mktemp -d)"
  (
    cd "$help_dir"
    "$ROOT/assets/bin/cw" agent-run --help >/dev/null
  )
  rmdir "$help_dir"
fi

printf 'continuous-work v2 verification passed: %s\n' "$ROOT"
