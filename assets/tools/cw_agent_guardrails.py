#!/usr/bin/env python3
"""cw agent-guardrails: agent-led guard rails (blueprint §4.5).

Pure decision module over `.cw-agent/ledger.json` + events. Even without a
token budget, these stop conditions must exist (Ralph-family lesson):

- attempt limit:      per-stage attempt cap (default 3) -> stop/gate
- no-progress detect: artifact hash unchanged across consecutive failures
                      -> stuck -> stop
- fake-completion:    a stage is done only with a receipt; skipping requires
                      explicit authorization
- repair budget:      per-stage failure/repair cap -> human gate

Output: (action, reason) where action in {continue, stop, gate}.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cw_agent_events import read_ledger, agent_work_dir, file_sha256

ACTION_CONTINUE = "continue"
ACTION_STOP = "stop"
ACTION_GATE = "gate"

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MAX_REPAIRS = 3
DEFAULT_NO_CHANGE_LIMIT = 3


def decide(
    root: Path,
    stage_id: str,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    max_repairs: int = DEFAULT_MAX_REPAIRS,
    no_change_limit: int = DEFAULT_NO_CHANGE_LIMIT,
) -> tuple[str, str]:
    """Return (action, reason) for the given stage based on ledger state.

    Check order: attempt limit -> no-progress streak -> repair budget ->
    fake-completion. No-progress is checked before repair budget because a
    stuck stage cannot be fixed by more repair turns.
    """
    ledger = read_ledger(root)
    entry = ledger["stages"].get(stage_id)
    if entry is None:
        return ACTION_CONTINUE, "no_ledger_entry"

    # 1) attempt limit
    attempts = entry.get("attempts", 0)
    if attempts >= max_attempts:
        return ACTION_GATE, f"attempt_limit:{attempts}>={max_attempts}"

    # 2) no-progress detection: artifact signature unchanged for N consecutive
    #    failures -> stuck, stop (further repair is pointless)
    streak = entry.get("progress", {}).get("streak", 0)
    if streak >= no_change_limit:
        return ACTION_STOP, f"no_progress:streak={streak}"

    # 3) repair budget (failures count as repair turns)
    failures = entry.get("failures", [])
    if len(failures) >= max_repairs:
        return ACTION_GATE, f"repair_budget:{len(failures)}>={max_repairs}"

    # 4) fake-completion guard: status completed without evidence
    if entry.get("status") == "completed" and not entry.get("evidence"):
        return ACTION_STOP, "fake_completion:completed_without_evidence"

    return ACTION_CONTINUE, "ok"


def check_evidence(root: Path, stage_id: str) -> bool:
    """A stage counts as done only with an evidence pointer in the ledger."""
    entry = read_ledger(root)["stages"].get(stage_id)
    return bool(entry and entry.get("status") == "completed" and entry.get("evidence"))


def record_progress(root: Path, stage_id: str, artifact_paths: list[str]) -> dict:
    """Record current artifact signature and no-change streak for a stage.

    Call once per failed attempt. Streak increments when the signature is
    unchanged; resets when it changes. Returns the progress dict.
    """
    from cw_agent_events import read_ledger, write_ledger

    ledger = read_ledger(root)
    entry = ledger["stages"].setdefault(stage_id, {"attempts": 0, "status": "pending", "artifact_hashes": {}, "evidence": None, "failures": []})
    parts = []
    for rel in artifact_paths:
        p = Path(rel)
        if not p.is_absolute():
            p = root / rel
        if p.exists():
            parts.append(f"{rel}={file_sha256(p)[:16]}")
    signature = ",".join(sorted(parts))
    prog = entry.setdefault("progress", {"last_signature": None, "streak": 0})
    if signature and signature == prog.get("last_signature"):
        prog["streak"] += 1
    else:
        prog["last_signature"] = signature
        prog["streak"] = 1 if signature else 0
    entry["progress"] = prog
    write_ledger(root, ledger)
    return prog


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    action, reason = decide(root, args.stage_id, max_attempts=args.max_attempts, max_repairs=args.max_repairs, no_change_limit=args.no_change_limit)
    print(json.dumps({"action": action, "reason": reason}, ensure_ascii=False, indent=2))
    return 0 if action == ACTION_CONTINUE else 1


def cmd_evidence(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ok = check_evidence(root, args.stage_id)
    print(json.dumps({"has_evidence": ok}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cw agent-guard", description="agent-led guard rails (attempt/no-progress/fake-completion/repair)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="decide action for a stage")
    p.add_argument("stage_id")
    p.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    p.add_argument("--max-repairs", type=int, default=DEFAULT_MAX_REPAIRS)
    p.add_argument("--no-change-limit", type=int, default=DEFAULT_NO_CHANGE_LIMIT)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("evidence", help="check a stage has completion evidence")
    p.add_argument("stage_id")
    p.set_defaults(func=cmd_evidence)

    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
