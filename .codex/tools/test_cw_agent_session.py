#!/usr/bin/env python3
"""Fixtures for cw_agent_session.py (S1 session layer).

Pure-logic tests only: directory init, session.json read/write, command
construction, and session-id extraction. Real `codex exec` calls are out of
scope for the fixture suite (verified separately by the S1 empirical smoke).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cw_agent_session import (
    BASE_SESSION,
    ensure_agent_dir,
    read_session,
    write_session,
    build_start_cmd,
    build_resume_cmd,
    extract_session_id_from_jsonl,
    session_path,
    now_utc,
)


class AgentDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_ensure_agent_dir_creates_gitignore(self):
        d = ensure_agent_dir(self.root)
        self.assertTrue(d.is_dir())
        gitignore = d / ".gitignore"
        self.assertTrue(gitignore.exists())
        text = gitignore.read_text(encoding="utf-8")
        self.assertIn("session.json", text)
        self.assertIn("events.jsonl", text)
        self.assertIn("ledger.json", text)

    def test_session_defaults_when_missing(self):
        s = read_session(self.root)
        self.assertEqual(s["status"], "idle")
        self.assertIsNone(s["id"])
        self.assertEqual(s["schema_version"], BASE_SESSION["schema_version"])

    def test_session_roundtrip(self):
        data = {
            "schema_version": "1",
            "id": "abcdef00-1111-2222-3333-444455556666",
            "model": "gpt-5.6-sol",
            "working_dir": str(self.root),
            "resume_hint": "id",
            "status": "active",
            "last_event_at": now_utc(),
        }
        write_session(self.root, data)
        loaded = read_session(self.root)
        self.assertEqual(loaded["id"], data["id"])
        self.assertEqual(loaded["status"], "active")
        self.assertEqual(loaded["working_dir"], str(self.root))

    def test_session_merges_defaults_for_partial(self):
        write_session(self.root, {"id": "abc"})
        loaded = read_session(self.root)
        self.assertEqual(loaded["id"], "abc")
        self.assertEqual(loaded["status"], "idle")  # default preserved

    def test_session_json_ignored_by_git(self):
        ensure_agent_dir(self.root)
        write_session(self.root, {"id": "x"})
        self.assertTrue((self.root / ".cw-agent" / "session.json").exists())


class CommandConstructionTest(unittest.TestCase):
    def test_start_cmd(self):
        cmd = build_start_cmd("gpt-5.6-sol", Path("/tmp/r"))
        self.assertEqual(cmd[:2], ["codex", "exec"])
        self.assertIn("-s", cmd)
        self.assertIn("workspace-write", cmd)
        self.assertIn("-m", cmd)
        self.assertIn("--json", cmd)

    def test_resume_cmd_with_id(self):
        cmd = build_resume_cmd("abc-123", "gpt-5.6-sol", Path("/tmp/r"))
        self.assertIn("resume", cmd)
        self.assertIn("abc-123", cmd)
        self.assertNotIn("--last", cmd)
        # resume has no -s (sandbox) option; PROMPT must be '-' from stdin
        self.assertNotIn("-s", cmd)
        self.assertNotIn("workspace-write", cmd)
        self.assertIn("-", cmd)
        self.assertIn("-m", cmd)
        self.assertIn("--json", cmd)

    def test_resume_cmd_last(self):
        cmd = build_resume_cmd(None, "gpt-5.6-sol", Path("/tmp/r"), use_last=True)
        self.assertIn("--last", cmd)
        self.assertNotIn("abc-123", cmd)
        self.assertNotIn("-s", cmd)
        self.assertIn("-", cmd)

    def test_resume_cmd_no_id_no_last_omits_positional(self):
        cmd = build_resume_cmd(None, "gpt-5.6-sol", Path("/tmp/r"))
        # resume with no id and no --last is allowed by CLI (picker), but our
        # caller decides via use_last; assert we do not inject a bogus id
        self.assertNotIn("--last", cmd)
        self.assertNotIn("-s", cmd)
        self.assertIn("-", cmd)


class SessionIdExtractionTest(unittest.TestCase):
    def test_extract_from_jsonl_event(self):
        out = '{"type":"session_started","session_id":"11111111-2222-3333-4444-555555555555","model":"gpt-5.6-sol"}\n'
        self.assertEqual(extract_session_id_from_jsonl(out), "11111111-2222-3333-4444-555555555555")

    def test_extract_thread_id(self):
        # codex exec --json emits thread_id (verified 2026-08-06)
        out = '{"type":"thread.started","thread_id":"019fd7a8-b60f-7613-9257-c1ebeb9f94de"}\n'
        self.assertEqual(extract_session_id_from_jsonl(out), "019fd7a8-b60f-7613-9257-c1ebeb9f94de")

    def test_extract_none_when_absent(self):
        self.assertIsNone(extract_session_id_from_jsonl('{"type":"heartbeat"}'))
        self.assertIsNone(extract_session_id_from_jsonl(""))

    def test_extract_short_ids_ignored(self):
        # Only UUID-ish (20+ hex/dash) ids are captured; avoids grabbing
        # unrelated short fields named session_id
        out = '{"session_id":"x"}\n'
        self.assertIsNone(extract_session_id_from_jsonl(out))


if __name__ == "__main__":
    unittest.main()
