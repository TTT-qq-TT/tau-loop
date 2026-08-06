#!/usr/bin/env python3
"""cw agent-run: agent-led orchestrator (runner) — blueprint §4.2–4.5.

Wires S1–S4 into the automatic closed loop:

    executor (S3) -> stage failed -> classify (S2) -> wake decision (S2)
    -> guardrails (S4) -> resume lead agent (S1) -> agent edits work-order
    -> re-run executor -> ... until all_stages_completed -> final wake.

The runner itself contains no LLM: it is the loop driver only. The lead
agent is woken via `codex exec resume` (real mode; deferred to M4 on real
machines) or simulated by printing the decision and waiting for a work-order
edit (--dry-run; the stable path on this machine — S1 notes).

State stays under `.cw-agent/` (blueprint §3.1). The runner never touches
ledger.json; the only event it appends is `agent_wake`, which records the
wake decision (the ledger and stage events stay cw-executor-exclusive).

Wait semantics (spec §7 mitigation): after a wake the runner waits until
work-order.json mtime changes OR an `agent_decision` event is appended; a
more elaborate handshake is deferred to the real-machine milestone.

Exit codes:
  0 success (all_stages_completed)
  1 invalid environment (missing/invalid work-order)
  2 stopped: fatal failure (not wakeable)
  3 gate: needs_human classification
  4 stopped: S4 guardrail stop (no-progress / fake completion)
  5 gate: S4 guardrail gate (attempt limit / repair budget)
  6 stopped: agent did not edit work-order within --wait-timeout
  7 stopped: --max-loops exceeded
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from cw_agent_events import (
    FAIL_FATAL,
    FAIL_NEEDS_HUMAN,
    append_event,
    agent_work_dir,
    read_events,
    wake_decision,
)
from cw_agent_backends import DEFAULT_TIMEOUT, DEFAULT_EARLY_FAIL
from cw_agent_executor import read_work_order, run_all, work_order_path
from cw_agent_guardrails import (
    ACTION_GATE,
    ACTION_STOP,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_MAX_REPAIRS,
    DEFAULT_NO_CHANGE_LIMIT,
    decide,
    record_progress,
)

DEFAULT_MAX_LOOPS = 10
DEFAULT_WAIT_TIMEOUT = 300.0
DEFAULT_WAIT_POLL = 1.0

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_FATAL = 2
EXIT_NEEDS_HUMAN = 3
EXIT_GUARD_STOP = 4
EXIT_GUARD_GATE = 5
EXIT_WAIT_TIMEOUT = 6
EXIT_MAX_LOOPS = 7


def last_failed_stage(root: Path) -> tuple[str | None, str | None]:
    """Return (stage_id, classification) of the most recent stage_failed event."""
    for ev in reversed(read_events(root)):
        if ev.get("type") == "stage_failed":
            return ev.get("stage_id"), ev.get("payload", {}).get("classification")
    return None, None


def stage_artifacts(root: Path, stage_id: str) -> list[str]:
    """expected_artifacts of a stage from the current work-order ([] if unknown)."""
    try:
        wo = read_work_order(root)
    except (FileNotFoundError, ValueError):
        return []
    for s in wo.get("stages", []):
        if s.get("id") == stage_id:
            return list(s.get("expected_artifacts", []))
    return []


def decision_event_count(root: Path) -> int:
    return sum(1 for e in read_events(root) if e.get("type") == "agent_decision")


def build_wake_prompt(root: Path, stage_id: str | None, classification: str | None) -> str:
    """Best-effort prompt for the lead agent: goal + failure evidence tail."""
    if not stage_id:
        return (
            "All work-order stages completed. Read events.jsonl and the receipts, "
            "run the final verification, then report the result."
        )
    lines = [
        "A stage failed in the ongoing work order. You are the lead agent.",
        f"stage: {stage_id}",
        f"classification: {classification}",
    ]
    try:
        wo = read_work_order(root)
        lines.append(f"goal: {wo.get('goal', '')}")
    except (FileNotFoundError, ValueError):
        pass
    receipt = agent_work_dir(root) / "artifacts" / stage_id / "receipt.json"
    if receipt.exists():
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
            tail = (data.get("stderr_tail") or "").rstrip()[-1500:]
            if tail:
                lines.append("stderr tail:")
                lines.append(tail)
        except json.JSONDecodeError:
            pass
    lines.append(
        "Read events.jsonl and the receipts, decide (repair / skip / ask human), "
        "edit work-order.json, then append an agent_decision event to events.jsonl "
        "and stop. The runner re-runs the executor when it detects your edit."
    )
    return "\n".join(lines)


def resume_agent(root: Path, *, dry_run: bool, reason: str, stage_id: str | None,
                 classification: str | None, model: str | None,
                 backend_name: str | None = None, timeout: float = DEFAULT_TIMEOUT,
                 early_fail: float = DEFAULT_EARLY_FAIL, strict: bool = False) -> int:
    """Wake the lead agent via the selected backend (S1). dry_run prints only."""
    append_event(root, "agent_wake", stage_id,
                 {"reason": reason, "classification": classification, "dry_run": dry_run})
    prompt = build_wake_prompt(root, stage_id, classification)
    if dry_run:
        target = stage_id or "final-verify"
        print(f"[dry-run] would resume lead agent (reason={reason}, stage={target})")
        return 0
    # Real resume: delegate to the backend adapter (hard timeout + early-fail
    # apply uniformly; approvals/sandbox bypass per owner decision unless --strict).
    from cw_agent_session import read_session, write_session
    from cw_agent_backends import OUTCOME_OK, backend_for
    s = read_session(root)
    name = backend_name or s.get("backend")
    if not name:
        print("error: no backend recorded for this session; pass --backend", file=sys.stderr)
        return 1
    backend = backend_for(name, model=model, bypass=not strict)
    use_last = not s.get("id")
    cmd = backend.resume_cmd(
        s.get("id"),
        model or s.get("model") or getattr(backend, "default_model", None) or "gpt-5.6-sol",
        root, use_last=use_last)
    print(f"resuming lead agent (backend={name}, session={s.get('id') or 'last'})...")
    result = backend.run(cmd, prompt, timeout=timeout, early_fail=early_fail)
    if result.outcome != OUTCOME_OK:
        print(f"resume {result.outcome}: exit={result.exit_code}, "
              f"stderr={result.stderr[-1000:]!r}", file=sys.stderr)
        return 1
    # capture the precise thread/session id so later resumes no longer rely on --last
    if not use_last:
        sid = backend.extract_session_id(result.stdout)
        if sid:
            s["id"] = sid
            s["resume_hint"] = "id"
            write_session(root, s)
    return 0


def wait_for_agent_edit(root: Path, wo: Path, baseline_mtime: int,
                        baseline_decisions: int, timeout: float, poll: float) -> bool:
    """Poll until work-order mtime changes or an agent_decision event arrives."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            mtime = wo.stat().st_mtime_ns
        except OSError:
            mtime = -1
        if mtime != baseline_mtime or decision_event_count(root) != baseline_decisions:
            return True
        time.sleep(poll)
    return False


def run_loop(root: Path, *, dry_run: bool, max_loops: int, wait_timeout: float,
             max_attempts: int, max_repairs: int, no_change_limit: int,
             model: str | None, backend_name: str | None = None,
             timeout: float = DEFAULT_TIMEOUT, early_fail: float = DEFAULT_EARLY_FAIL,
             strict: bool = False) -> int:
    try:
        wo = read_work_order(root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"invalid work order: {exc}", file=sys.stderr)
        return EXIT_INVALID
    # Backend is chosen explicitly by the lead agent (owner decision): the
    # work-order `backend` field is written during planning; --backend overrides.
    wo_backend = wo.get("backend")
    effective_backend = backend_name or wo_backend
    if not dry_run and not effective_backend:
        print("error: no backend chosen; set the work-order `backend` field "
              "(codex|claude|codewhale) or pass --backend", file=sys.stderr)
        return EXIT_INVALID
    print(json.dumps({
        "goal": wo.get("goal", ""),
        "stages": [s["id"] for s in wo["stages"]],
        "dry_run": dry_run,
        "backend": effective_backend,
    }, ensure_ascii=False))

    loops = 0
    while loops < max_loops:
        loops += 1
        print(f"--- loop {loops}/{max_loops} ---")
        rc = run_all(root)
        if rc == 0:
            wake, reason = wake_decision(root)
            resume_agent(root, dry_run=dry_run, reason=reason, stage_id=None,
                         classification=None, model=model, backend_name=effective_backend,
                         timeout=timeout, early_fail=early_fail, strict=strict)
            print(f"SUCCESS: all stages completed after {loops} loop(s)")
            return EXIT_OK

        stage_id, cls = last_failed_stage(root)
        if cls == FAIL_FATAL:
            print(f"STOP: fatal failure at stage '{stage_id}' (not wakeable)")
            return EXIT_FATAL
        if cls == FAIL_NEEDS_HUMAN:
            print(f"GATE: stage '{stage_id}' needs human judgment")
            return EXIT_NEEDS_HUMAN

        # repairable: enforce S4 guardrails before spending a wake
        record_progress(root, stage_id, stage_artifacts(root, stage_id))
        action, reason = decide(root, stage_id, max_attempts=max_attempts,
                                max_repairs=max_repairs, no_change_limit=no_change_limit)
        if action == ACTION_STOP:
            print(f"STOP: guardrail stop at stage '{stage_id}': {reason}")
            return EXIT_GUARD_STOP
        if action == ACTION_GATE:
            print(f"GATE: guardrail gate at stage '{stage_id}': {reason}")
            return EXIT_GUARD_GATE

        wake, wake_reason = wake_decision(root)

        # Record the wait baseline BEFORE waking: a real lead agent edits
        # work-order.json during the resume call, so a baseline taken after
        # resume would already contain the edit and the wait would never fire
        # (real-machine closed-loop discovery, 2026-08-06).
        wo_path = work_order_path(root)
        try:
            baseline_mtime = wo_path.stat().st_mtime_ns
        except OSError:
            baseline_mtime = -1
        baseline_decisions = decision_event_count(root)

        resume_agent(root, dry_run=dry_run, reason=wake_reason, stage_id=stage_id,
                     classification=cls, model=model, backend_name=effective_backend,
                     timeout=timeout, early_fail=early_fail, strict=strict)

        print(f"waiting for lead agent to edit work-order (timeout {wait_timeout:g}s)...")
        if not wait_for_agent_edit(root, wo_path, baseline_mtime, baseline_decisions,
                                   wait_timeout, DEFAULT_WAIT_POLL):
            print(f"STOP: no work-order edit within {wait_timeout:g}s")
            return EXIT_WAIT_TIMEOUT
        print("work-order changed; re-running executor")

    print(f"STOP: max_loops ({max_loops}) exceeded")
    return EXIT_MAX_LOOPS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cw agent-run",
                                     description="agent-led orchestrator: executor -> wake -> repair -> re-run loop")
    parser.add_argument("--root", default=".")
    parser.add_argument("--dry-run", action="store_true",
                        help="simulate agent wake: print the decision, never call codex")
    parser.add_argument("--max-loops", type=int, default=DEFAULT_MAX_LOOPS,
                        help="hard loop cap (default %(default)s)")
    parser.add_argument("--wait-timeout", type=float, default=DEFAULT_WAIT_TIMEOUT,
                        help="seconds to wait for a work-order edit after a wake (default %(default)g)")
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--max-repairs", type=int, default=DEFAULT_MAX_REPAIRS)
    parser.add_argument("--no-change-limit", type=int, default=DEFAULT_NO_CHANGE_LIMIT)
    parser.add_argument("--model", default=None, help="model for real resume (ignored in --dry-run)")
    parser.add_argument("--backend", default=None, help="codex|claude|codewhale (default: work-order `backend` field)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="per-resume hard timeout seconds (default %(default)g)")
    parser.add_argument("--early-fail", type=float, default=DEFAULT_EARLY_FAIL,
                        help="terminate resume if no first output within N seconds (default %(default)g)")
    parser.add_argument("--strict", action="store_true",
                        help="disable approval/sandbox bypass for codex resume")
    args = parser.parse_args(argv)
    if args.max_loops < 1:
        print("--max-loops must be >= 1", file=sys.stderr)
        return EXIT_INVALID
    root = Path(args.root).resolve()
    return run_loop(
        root,
        dry_run=args.dry_run,
        max_loops=args.max_loops,
        wait_timeout=args.wait_timeout,
        max_attempts=args.max_attempts,
        max_repairs=args.max_repairs,
        no_change_limit=args.no_change_limit,
        model=args.model,
        backend_name=args.backend,
        timeout=args.timeout,
        early_fail=args.early_fail,
        strict=args.strict,
    )


if __name__ == "__main__":
    sys.exit(main())
