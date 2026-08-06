#!/usr/bin/env python3
"""Fixtures for cw_agent_guardrails.py (S4 guard rails). Pure logic, no IO beyond temp files."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cw_agent_events import read_ledger, write_ledger
from cw_agent_guardrails import (
    ACTION_CONTINUE,
    ACTION_STOP,
    ACTION_GATE,
    decide,
    check_evidence,
    record_progress,
)


def _ledger_with(root: Path, stage_id: str, **fields) -> dict:
    ledger = read_ledger(root)
    entry = ledger["stages"].setdefault(
        stage_id,
        {"attempts": 0, "status": "pending", "artifact_hashes": {}, "evidence": None, "failures": []},
    )
    entry.update(fields)
    write_ledger(root, ledger)
    return ledger


class DecideTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_entry_continues(self):
        action, reason = decide(self.root, "s1")
        self.assertEqual(action, ACTION_CONTINUE)

    def test_attempt_limit_gates(self):
        _ledger_with(self.root, "s1", attempts=3, status="failed")
        action, reason = decide(self.root, "s1")
        self.assertEqual(action, ACTION_GATE)
        self.assertIn("attempt_limit", reason)

    def test_repair_budget_gates(self):
        _ledger_with(self.root, "s1", attempts=2, failures=["a", "b", "c"], status="failed")
        action, reason = decide(self.root, "s1")
        self.assertEqual(action, ACTION_GATE)
        self.assertIn("repair_budget", reason)

    def test_no_progress_stops(self):
        _ledger_with(self.root, "s1", attempts=2, failures=["a", "b"], status="failed")
        (self.root / "a.txt").write_text("same")
        record_progress(self.root, "s1", ["a.txt"])
        record_progress(self.root, "s1", ["a.txt"])
        record_progress(self.root, "s1", ["a.txt"])
        action, reason = decide(self.root, "s1", no_change_limit=3)
        self.assertEqual(action, ACTION_STOP)
        self.assertIn("no_progress", reason)

    def test_progress_with_changed_signature_continues(self):
        _ledger_with(self.root, "s1", attempts=2, failures=["a", "b"], status="failed")
        (self.root / "a.txt").write_text("v1")
        record_progress(self.root, "s1", ["a.txt"])
        record_progress(self.root, "s1", ["a.txt"])
        (self.root / "a.txt").write_text("v2")  # progress: artifact changed
        record_progress(self.root, "s1", ["a.txt"])
        action, _ = decide(self.root, "s1", no_change_limit=3)
        self.assertEqual(action, ACTION_CONTINUE)

    def test_fake_completion_stops(self):
        _ledger_with(self.root, "s1", status="completed", evidence=None)
        action, reason = decide(self.root, "s1")
        self.assertEqual(action, ACTION_STOP)
        self.assertIn("fake_completion", reason)

    def test_ok_continues(self):
        _ledger_with(self.root, "s1", attempts=1, status="failed")
        action, reason = decide(self.root, "s1")
        self.assertEqual(action, ACTION_CONTINUE)


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_evidence(self):
        _ledger_with(self.root, "s1", status="completed", evidence=None)
        self.assertFalse(check_evidence(self.root, "s1"))

    def test_with_evidence(self):
        _ledger_with(self.root, "s1", status="completed", evidence="receipt.json")
        self.assertTrue(check_evidence(self.root, "s1"))

    def test_failed_with_evidence_is_not_done(self):
        _ledger_with(self.root, "s1", status="failed", evidence="receipt.json")
        self.assertFalse(check_evidence(self.root, "s1"))


class ProgressTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_streak_increments_on_same_signature(self):
        (self.root / "a.txt").write_text("x")
        record_progress(self.root, "s1", ["a.txt"])
        record_progress(self.root, "s1", ["a.txt"])
        prog = read_ledger(self.root)["stages"]["s1"]["progress"]
        self.assertEqual(prog["streak"], 2)

    def test_streak_resets_on_change(self):
        (self.root / "a.txt").write_text("x")
        record_progress(self.root, "s1", ["a.txt"])
        record_progress(self.root, "s1", ["a.txt"])
        (self.root / "a.txt").write_text("y")
        record_progress(self.root, "s1", ["a.txt"])
        prog = read_ledger(self.root)["stages"]["s1"]["progress"]
        self.assertEqual(prog["streak"], 1)

    def test_missing_files_do_not_advance_streak(self):
        record_progress(self.root, "s1", ["nope.txt"])
        prog = read_ledger(self.root)["stages"]["s1"]["progress"]
        self.assertEqual(prog["streak"], 0)


if __name__ == "__main__":
    unittest.main()
