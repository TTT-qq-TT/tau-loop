#!/usr/bin/env python3
"""Fixtures for cw_agent_events.py (S2 event layer).

Pure-logic tests: event append/read, ledger updates, failure classification,
and wake decisions. No external calls.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cw_agent_events import (
    FAIL_FATAL,
    FAIL_REPAIRABLE,
    FAIL_NEEDS_HUMAN,
    append_event,
    read_events,
    read_ledger,
    update_stage_ledger,
    classify_failure,
    wake_decision,
    EVENT_TYPES,
)


class EventsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_and_read(self):
        append_event(self.root, "stage_started", "download")
        append_event(self.root, "stage_completed", "download", {"evidence": "receipt.json"})
        events = read_events(self.root)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["type"], "stage_started")
        self.assertEqual(events[1]["payload"]["evidence"], "receipt.json")

    def test_read_empty(self):
        self.assertEqual(read_events(self.root), [])

    def test_append_rejects_unknown_type(self):
        with self.assertRaises(ValueError):
            append_event(self.root, "not_an_event")

    def test_limit(self):
        for i in range(10):
            append_event(self.root, "agent_wake")
        events = read_events(self.root, limit=3)
        self.assertEqual(len(events), 3)

    def test_append_only_no_rewrite(self):
        append_event(self.root, "stage_started", "s1")
        first = read_events(self.root)
        append_event(self.root, "stage_started", "s2")
        second = read_events(self.root)
        self.assertEqual(first[0], second[0])  # history untouched
        self.assertEqual(len(second), 2)


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_ledger_defaults(self):
        ledger = read_ledger(self.root)
        self.assertEqual(ledger["stages"], {})

    def test_update_stage_increments_attempts(self):
        update_stage_ledger(self.root, "download", status="failed", failure="tls eof")
        update_stage_ledger(self.root, "download", status="failed", failure="tls eof")
        entry = read_ledger(self.root)["stages"]["download"]
        self.assertEqual(entry["attempts"], 2)
        self.assertEqual(entry["status"], "failed")
        self.assertEqual(len(entry["failures"]), 2)

    def test_update_stage_success(self):
        update_stage_ledger(self.root, "verify", status="completed", evidence="receipt.json")
        entry = read_ledger(self.root)["stages"]["verify"]
        self.assertEqual(entry["attempts"], 1)
        self.assertEqual(entry["evidence"], "receipt.json")


class ClassificationTest(unittest.TestCase):
    def test_fatal_auth(self):
        self.assertEqual(classify_failure("s1", stderr="401 Unauthorized"), FAIL_FATAL)

    def test_fatal_missing_command(self):
        self.assertEqual(classify_failure("s1", stderr="command not found: aria2"), FAIL_FATAL)

    def test_repairable_network(self):
        self.assertEqual(classify_failure("s1", stderr="Connection refused"), FAIL_REPAIRABLE)

    def test_repairable_tls(self):
        self.assertEqual(classify_failure("s1", stderr="TLS EOF"), FAIL_REPAIRABLE)

    def test_repairable_checksum(self):
        self.assertEqual(classify_failure("s1", stderr="checksum mismatch"), FAIL_REPAIRABLE)

    def test_needs_human_permission(self):
        self.assertEqual(classify_failure("s1", stderr="permission denied"), FAIL_NEEDS_HUMAN)

    def test_default_repairable(self):
        self.assertEqual(classify_failure("s1", stderr="weird mystery error"), FAIL_REPAIRABLE)

    def test_exit_zero_no_output_needs_human(self):
        self.assertEqual(classify_failure("s1", stdout="ok", exit_code=0), FAIL_NEEDS_HUMAN)


class WakeDecisionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_events(self):
        wake, reason = wake_decision(self.root)
        self.assertFalse(wake)

    def test_wake_on_repairable_failure(self):
        append_event(self.root, "stage_failed", "download", {"classification": FAIL_REPAIRABLE})
        wake, reason = wake_decision(self.root)
        self.assertTrue(wake)
        self.assertIn(FAIL_REPAIRABLE, reason)

    def test_no_wake_on_fatal_failure(self):
        append_event(self.root, "stage_failed", "download", {"classification": FAIL_FATAL})
        wake, reason = wake_decision(self.root)
        self.assertFalse(wake)

    def test_wake_on_all_completed(self):
        append_event(self.root, "all_stages_completed")
        wake, reason = wake_decision(self.root)
        self.assertTrue(wake)

    def test_no_wake_on_stage_started(self):
        append_event(self.root, "stage_started", "download")
        wake, _ = wake_decision(self.root)
        self.assertFalse(wake)


if __name__ == "__main__":
    unittest.main()
