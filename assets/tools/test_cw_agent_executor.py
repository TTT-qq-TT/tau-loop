#!/usr/bin/env python3
"""Fixtures for cw_agent_executor.py (S3 executor).

Uses real tiny shell commands in a temp dir (touch/mkdir/false) — no network.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cw_agent_executor import (
    read_work_order,
    run_command,
    check_artifacts,
    run_stage,
    run_all,
    work_order_path,
)
from cw_agent_events import read_events, read_ledger, agent_work_dir


def write_wo(root: Path, stages: list[dict], goal: str = "test") -> Path:
    d = agent_work_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    p = work_order_path(root)
    p.write_text(json.dumps({"schema_version": "1", "goal": goal, "stages": stages}, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


class WorkOrderReadTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            read_work_order(self.root)

    def test_invalid_schema(self):
        write_wo(self.root, [{"id": "s", "command": "true"}])
        p = work_order_path(self.root)
        p.write_text('{"schema_version": "999", "stages": []}', encoding="utf-8")
        with self.assertRaises(ValueError):
            read_work_order(self.root)

    def test_empty_stages(self):
        p = work_order_path(self.root)
        agent_work_dir(self.root).mkdir(parents=True, exist_ok=True)
        p.write_text('{"schema_version": "1", "stages": []}', encoding="utf-8")
        with self.assertRaises(ValueError):
            read_work_order(self.root)

    def test_stage_requires_id_and_command(self):
        write_wo(self.root, [{"command": "true"}])
        with self.assertRaises(ValueError):
            read_work_order(self.root)


class RunCommandTest(unittest.TestCase):
    def test_exit_code_and_output(self):
        rc, out, err = run_command("echo hi", Path("/tmp"))
        self.assertEqual(rc, 0)
        self.assertIn("hi", out)

    def test_failure_exit_code(self):
        rc, out, err = run_command("exit 3", Path("/tmp"))
        self.assertEqual(rc, 3)


class CheckArtifactsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_all_present(self):
        (self.root / "a.txt").write_text("x")
        ok, missing = check_artifacts(self.root, {"expected_artifacts": ["a.txt"]})
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_missing(self):
        ok, missing = check_artifacts(self.root, {"expected_artifacts": ["nope.txt"]})
        self.assertFalse(ok)
        self.assertEqual(missing, ["nope.txt"])


class RunStageTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_success_flow(self):
        stage = {"id": "make", "command": f"mkdir -p {self.root}/out && touch {self.root}/out/x.txt", "expected_artifacts": ["out/x.txt"]}
        rc = run_stage(self.root, stage)
        self.assertEqual(rc, 0)
        events = read_events(self.root)
        self.assertEqual(events[-1]["type"], "stage_completed")
        ledger = read_ledger(self.root)["stages"]["make"]
        self.assertEqual(ledger["status"], "completed")
        self.assertTrue((agent_work_dir(self.root) / "artifacts" / "make" / "receipt.json").exists())

    def test_command_failure(self):
        stage = {"id": "bad", "command": "exit 7"}
        rc = run_stage(self.root, stage)
        self.assertEqual(rc, 1)
        events = read_events(self.root)
        self.assertEqual(events[-1]["type"], "stage_failed")
        self.assertEqual(events[-1]["payload"]["reason"], "exit:7")
        ledger = read_ledger(self.root)["stages"]["bad"]
        self.assertEqual(ledger["status"], "failed")

    def test_artifacts_missing_failure(self):
        stage = {"id": "missing", "command": "true", "expected_artifacts": ["ghost.txt"]}
        rc = run_stage(self.root, stage)
        self.assertEqual(rc, 1)
        events = read_events(self.root)
        self.assertEqual(events[-1]["type"], "stage_failed")
        self.assertIn("artifacts_missing", events[-1]["payload"]["reason"])


class RunAllTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_all_success_emits_all_completed(self):
        write_wo(self.root, [
            {"id": "a", "command": "true"},
            {"id": "b", "command": "true"},
        ])
        rc = run_all(self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(read_events(self.root)[-1]["type"], "all_stages_completed")

    def test_stops_on_failure(self):
        write_wo(self.root, [
            {"id": "a", "command": "exit 1"},
            {"id": "b", "command": "true"},
        ])
        rc = run_all(self.root)
        self.assertEqual(rc, 1)
        types = [e["type"] for e in read_events(self.root)]
        self.assertNotIn("stage_completed", types)  # b never ran
        self.assertNotIn("all_stages_completed", types)


if __name__ == "__main__":
    unittest.main()
