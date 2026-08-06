#!/usr/bin/env python3
"""Fixtures for cw_agent_runner.py (agent-led orchestrator).

The lead agent is simulated by a background thread that edits work-order.json
(and appends an agent_decision event) shortly after a wake — the --dry-run
wake path prints the decision and the runner waits for the edit. Uses real
tiny shell commands in a temp dir — no network, no codex.

Covers the spec §5 fixtures: success flow, failure->repair flow (dry-run),
guardrail gate, max-loops — plus fatal / needs_human / wait-timeout / invalid.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from cw_agent_events import (
    agent_work_dir,
    append_event,
    read_events,
    read_ledger,
)
from cw_agent_executor import work_order_path
from cw_agent_runner import (
    EXIT_FATAL,
    EXIT_GUARD_GATE,
    EXIT_GUARD_STOP,
    EXIT_INVALID,
    EXIT_MAX_LOOPS,
    EXIT_NEEDS_HUMAN,
    EXIT_OK,
    EXIT_WAIT_TIMEOUT,
    run_loop,
)


def write_wo(root: Path, stages: list[dict], goal: str = "test goal") -> Path:
    d = agent_work_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    p = work_order_path(root)
    p.write_text(json.dumps({"schema_version": "1", "goal": goal, "stages": stages},
                            ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def rewrite_stage(root: Path, stage_id: str, command: str) -> None:
    """Simulate the lead agent editing work-order.json, then appending a decision.

    Atomic write (tmp + os.replace) so the executor never reads a half-written
    work-order (verify-env race seen 2026-08-07); silently returns once the
    temp dir is cleaned (late timer threads).
    """
    p = work_order_path(root)
    try:
        wo = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return  # temp dir already cleaned or concurrent write; skip
    for s in wo["stages"]:
        if s["id"] == stage_id:
            s["command"] = command
    tmp = p.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(wo, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        return  # dir gone; nothing to do
    append_event(root, "agent_decision", stage_id, {"action": "edited_work_order"})


def later(delay: float, fn) -> threading.Timer:
    t = threading.Timer(delay, fn)
    t.daemon = True
    t.start()
    return t


def event_types(root: Path) -> list[str]:
    return [e["type"] for e in read_events(root)]


def run(root: Path, **kw) -> int:
    """Default loop params; tests override what they need."""
    params = dict(dry_run=True, max_loops=10, wait_timeout=5.0,
                  max_attempts=3, max_repairs=3, no_change_limit=3, model=None)
    params.update(kw)
    return run_loop(root, **params)


class BaseCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class SuccessFlowTest(BaseCase):
    def test_all_success_emits_final_wake(self):
        write_wo(self.root, [
            {"id": "a", "command": "true"},
            {"id": "b", "command": "true"},
        ])
        rc = run(self.root)
        self.assertEqual(rc, EXIT_OK)
        types = event_types(self.root)
        self.assertEqual(types[-1], "agent_wake")
        self.assertIn("all_stages_completed", types)
        self.assertEqual(read_events(self.root)[-1]["payload"]["reason"], "all_stages_completed")
        # no wake before the final one
        self.assertEqual(sum(1 for t in types if t == "agent_wake"), 1)


class FailureRepairFlowTest(BaseCase):
    """doc/21 §3 scenario automated: TLS EOF -> wake -> repair -> all completed."""

    def test_repair_flow(self):
        write_wo(self.root, [
            {"id": "download",
             "command": "echo 'TLS EOF' >&2; exit 1",
             "expected_artifacts": ["downloads/manifest.json"]},
            {"id": "verify",
             "command": "mkdir -p verification && echo ok > verification/report.txt",
             "expected_artifacts": ["verification/report.txt"]},
            {"id": "extract",
             "command": "mkdir -p extracted && echo ok > extracted/env.txt",
             "expected_artifacts": ["extracted/env.txt"]},
            {"id": "smoke",
             "command": "mkdir -p smoke && echo ok > smoke/output.txt",
             "expected_artifacts": ["smoke/output.txt"]},
        ], goal="env assembly")
        later(0.4, lambda: rewrite_stage(
            self.root, "download",
            "mkdir -p downloads && echo fixed > downloads/manifest.json"))
        rc = run(self.root)
        self.assertEqual(rc, EXIT_OK)
        # two wakes: failure -> repair, then all_stages_completed -> final verify
        wakes = [e for e in read_events(self.root) if e["type"] == "agent_wake"]
        self.assertEqual(len(wakes), 2)
        self.assertEqual(wakes[0]["payload"]["reason"], "stage_failed:repairable")
        self.assertEqual(wakes[0]["stage_id"], "download")
        self.assertEqual(wakes[1]["payload"]["reason"], "all_stages_completed")
        ledger = read_ledger(self.root)["stages"]
        self.assertEqual(ledger["download"]["attempts"], 2)
        self.assertEqual(ledger["download"]["status"], "completed")
        for sid in ("verify", "extract", "smoke"):
            self.assertEqual(ledger[sid]["attempts"], 1, sid)
            self.assertEqual(ledger[sid]["status"], "completed", sid)
        self.assertTrue((self.root / "downloads" / "manifest.json").exists())


class GuardGateTest(BaseCase):
    def test_attempt_limit_gates_without_waking(self):
        write_wo(self.root, [
            {"id": "download",
             "command": "echo 'connection reset' >&2; exit 1",
             "expected_artifacts": ["downloads/manifest.json"]},
        ])
        # agent edits but never fixes: second round still fails -> attempt limit
        later(0.4, lambda: rewrite_stage(
            self.root, "download",
            "echo 'connection reset again' >&2; exit 1"))
        rc = run(self.root, max_attempts=2)
        self.assertEqual(rc, EXIT_GUARD_GATE)
        types = event_types(self.root)
        self.assertEqual(types.count("stage_failed"), 2)
        # no third wake: gate fired before spending another wake
        self.assertEqual(types.count("agent_wake"), 1)

    def test_no_progress_stops(self):
        write_wo(self.root, [
            {"id": "make",
             "command": "echo 'dependency missing' >&2; mkdir -p out && echo x > out/x.txt; exit 1",
             "expected_artifacts": ["out/x.txt"]},
        ])
        # agent keeps editing, artifact signature unchanged -> no_progress
        later(0.4, lambda: rewrite_stage(
            self.root, "make",
            "echo 'dependency missing 2' >&2; mkdir -p out && echo x > out/x.txt; exit 1"))
        rc = run(self.root, no_change_limit=2)
        self.assertEqual(rc, EXIT_GUARD_STOP)
        types = event_types(self.root)
        self.assertEqual(types.count("stage_failed"), 2)
        self.assertEqual(types.count("agent_wake"), 1)


class MaxLoopsTest(BaseCase):
    def test_max_loops_exceeded(self):
        write_wo(self.root, [
            {"id": "download",
             "command": "echo 'timeout' >&2; exit 1",
             "expected_artifacts": ["downloads/manifest.json"]},
        ])
        # every loop the agent edits but keeps failing
        def keep_editing():
            for i in range(5):
                later(0.3 * i, lambda i=i: rewrite_stage(
                    self.root, "download",
                    f"echo 'timeout attempt {i}' >&2; exit 1"))
        keep_editing()
        rc = run(self.root, max_loops=2, max_attempts=99, max_repairs=99, wait_timeout=5)
        self.assertEqual(rc, EXIT_MAX_LOOPS)
        self.assertEqual(event_types(self.root).count("stage_failed"), 2)


class StopPathsTest(BaseCase):
    def test_fatal_stops_without_wake(self):
        write_wo(self.root, [{"id": "auth", "command": "echo 'unauthorized' >&2; exit 1"}])
        rc = run(self.root)
        self.assertEqual(rc, EXIT_FATAL)
        self.assertNotIn("agent_wake", event_types(self.root))

    def test_needs_human_gates_without_wake(self):
        write_wo(self.root, [{"id": "perm", "command": "echo 'permission denied' >&2; exit 1"}])
        rc = run(self.root)
        self.assertEqual(rc, EXIT_NEEDS_HUMAN)
        self.assertNotIn("agent_wake", event_types(self.root))

    def test_wait_timeout_when_agent_never_edits(self):
        write_wo(self.root, [{"id": "dl", "command": "echo 'tls eof' >&2; exit 1"}])
        rc = run(self.root, wait_timeout=0.5)
        self.assertEqual(rc, EXIT_WAIT_TIMEOUT)
        self.assertEqual(event_types(self.root).count("agent_wake"), 1)


class BackendSelectionTest(BaseCase):
    """Explicit backend selection (owner decision 2026-08-06: no auto-detect)."""

    def test_real_mode_requires_backend(self):
        write_wo(self.root, [{"id": "a", "command": "true"}])
        rc = run(self.root, dry_run=False)
        self.assertEqual(rc, EXIT_INVALID)

    def test_work_order_backend_field_parsed_in_dry_run(self):
        write_wo(self.root, [{"id": "a", "command": "true"}])
        p = work_order_path(self.root)
        wo = json.loads(p.read_text(encoding="utf-8"))
        wo["backend"] = "codex"
        p.write_text(json.dumps(wo), encoding="utf-8")
        # dry-run: backend is parsed (no codex launched); success flow still works
        rc = run(self.root, dry_run=True)
        self.assertEqual(rc, EXIT_OK)


class InvalidInputTest(BaseCase):
    def test_missing_work_order(self):
        rc = run(self.root)
        self.assertEqual(rc, EXIT_INVALID)


if __name__ == "__main__":
    unittest.main()
