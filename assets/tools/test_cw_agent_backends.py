#!/usr/bin/env python3
"""Fixtures for cw_agent_backends.py (session-layer backend adapters).

Covers: command construction (codex full / claude+codewhale skeletons),
thread/session id extraction (codex thread_id fix), explicit backend
selection (no auto-detect, owner decision), config-following model read,
and run() timeout / early-fail behavior (real tiny subprocesses).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from cw_agent_backends import (
    DEFAULT_MODEL,
    ClaudeBackend,
    CodexBackend,
    CodewhaleBackend,
    OUTCOME_EARLY_FAIL,
    OUTCOME_ERROR,
    OUTCOME_OK,
    OUTCOME_TIMEOUT,
    backend_for,
    pick_backend,
    read_codex_model,
    validate_backend,
)


class ReadCodexModelTest(unittest.TestCase):
    def test_reads_model_from_toml(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "config.toml"
            p.write_text('model = "gpt-9.9-x"\nbase_url = "https://x"\n', encoding="utf-8")
            self.assertEqual(read_codex_model(str(p)), "gpt-9.9-x")

    def test_missing_file_falls_back(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(read_codex_model(str(Path(td) / "nope.toml")), DEFAULT_MODEL)

    def test_invalid_toml_line_match_fallback(self):
        # tomllib rejects the malformed table; the py3.8 line-match fallback
        # must still pick up `model = "..."`.
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "config.toml"
            p.write_text('model = "gpt-9.9-y"\n[broken\n', encoding="utf-8")
            self.assertEqual(read_codex_model(str(p)), "gpt-9.9-y")


class BackendCmdTest(unittest.TestCase):
    def test_codex_start(self):
        cmd = CodexBackend().start_cmd("m1", Path("/tmp"))
        self.assertEqual(cmd[:4], ["codex", "exec", "-s", "workspace-write"])
        self.assertIn("-m", cmd)
        self.assertIn("--json", cmd)

    def test_codex_resume_default_bypass(self):
        cmd = CodexBackend().resume_cmd("abc-123", "m1", Path("/tmp"))
        self.assertNotIn("-s", cmd)
        self.assertIn("-", cmd)  # stdin prompt marker
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", cmd)

    def test_codex_resume_strict_no_bypass(self):
        cmd = CodexBackend(bypass=False).resume_cmd("abc-123", "m1", Path("/tmp"))
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", cmd)

    def test_codex_resume_last(self):
        cmd = CodexBackend().resume_cmd(None, "m1", Path("/tmp"), use_last=True)
        self.assertIn("--last", cmd)
        self.assertNotIn("abc-123", cmd)

    def test_claude_cmds(self):
        b = ClaudeBackend()
        self.assertEqual(b.start_cmd("m", Path("/tmp"))[:2], ["claude", "-p"])
        r = b.resume_cmd("s1", "m", Path("/tmp"))
        self.assertIn("--resume", r)
        self.assertIn("s1", r)
        rl = b.resume_cmd(None, "m", Path("/tmp"), use_last=True)
        self.assertIn("--continue", rl)

    def test_codewhale_cmds(self):
        b = CodewhaleBackend()
        self.assertFalse(b.PROMPT_VIA_STDIN)
        start = b.start_cmd("m", Path("/tmp"))
        self.assertEqual(start[:3], ["codewhale", "exec", "--auto"])
        self.assertIn("--output-format", start)
        self.assertIn("stream-json", start)
        r = b.resume_cmd("s1", "m", Path("/tmp"))
        self.assertIn("--resume", r)
        self.assertIn("s1", r)
        self.assertIn("--auto", r)
        rl = b.resume_cmd(None, "m", Path("/tmp"), use_last=True)
        self.assertIn("--continue", rl)

    def test_codewhale_extract_returns_none(self):
        # stream-json session_id is redacted by codewhale; handle comes from
        # latest_session_id() instead.
        self.assertIsNone(CodewhaleBackend().extract_session_id('"session_id":"<redacted:abc123def4567890>"'))

    def test_codewhale_latest_session_id_parse(self):
        b = CodewhaleBackend()
        fake = (
            "Saved Sessions\n"
            "==============\n"
            "\n"
            "  * 8c40d59d | New Session | 670 msgs | 2026-08-06 16:07 UTC\n"
            "    e9783c97 | other | 118 msgs | 2026-08-06 15:37 UTC\n"
        )
        self.assertEqual(b._latest_session_id_from_output(fake), "8c40d59d")

    def test_codewhale_latest_session_id_empty(self):
        b = CodewhaleBackend()
        self.assertIsNone(b._latest_session_id_from_output("no sessions here"))


class ExtractSessionIdTest(unittest.TestCase):
    def test_codex_thread_id(self):
        out = '{"type":"thread.started","thread_id":"019fd7a8-b60f-7613-9257-c1ebeb9f94de"}\n'
        self.assertEqual(CodexBackend().extract_session_id(out), "019fd7a8-b60f-7613-9257-c1ebeb9f94de")

    def test_codex_session_id_fallback(self):
        out = '{"type":"session_started","session_id":"11111111-2222-3333-4444-555555555555"}\n'
        self.assertEqual(CodexBackend().extract_session_id(out), "11111111-2222-3333-4444-555555555555")

    def test_codex_none_when_absent(self):
        self.assertIsNone(CodexBackend().extract_session_id('{"type":"heartbeat"}'))

    def test_claude_codewhale_todo(self):
        # skeletons: real handle format not yet measured (follow-up spec)
        self.assertIsNone(ClaudeBackend().extract_session_id("anything"))
        self.assertIsNone(CodewhaleBackend().extract_session_id("anything"))


class SelectionTest(unittest.TestCase):
    def test_backend_for(self):
        self.assertIsInstance(backend_for("codex"), CodexBackend)
        self.assertIsInstance(backend_for("claude"), ClaudeBackend)
        self.assertIsInstance(backend_for("codewhale"), CodewhaleBackend)

    def test_backend_for_unknown(self):
        with self.assertRaises(ValueError):
            backend_for("nope")

    def test_pick_backend_priority(self):
        self.assertEqual(pick_backend("codex", "claude", "codewhale"), "codex")
        self.assertEqual(pick_backend(None, "claude", "codewhale"), "claude")
        self.assertEqual(pick_backend(None, None, "codewhale"), "codewhale")

    def test_pick_backend_none_raises(self):
        with self.assertRaises(ValueError):
            pick_backend(None, None, None)

    def test_pick_backend_unknown(self):
        with self.assertRaises(ValueError):
            pick_backend("nope", None, None)

    def test_validate_backend(self):
        self.assertIsInstance(validate_backend("codex"), bool)
        with self.assertRaises(ValueError):
            validate_backend("nope")


class RunBehaviorTest(unittest.TestCase):
    def test_ok(self):
        result = CodexBackend().run(["echo", "hello"], "x", timeout=10, early_fail=5)
        self.assertEqual(result.outcome, OUTCOME_OK)
        self.assertIn("hello", result.stdout)

    def test_error_exit(self):
        result = CodexBackend().run(
            [sys.executable, "-c", "import sys; sys.exit(3)"], "x", timeout=10, early_fail=5)
        self.assertEqual(result.outcome, OUTCOME_ERROR)
        self.assertEqual(result.exit_code, 3)

    def test_timeout(self):
        result = CodexBackend().run(
            [sys.executable, "-c", "import time; time.sleep(30)"], "x", timeout=1, early_fail=30)
        self.assertEqual(result.outcome, OUTCOME_TIMEOUT)

    def test_early_fail_connection(self):
        # no output within early_fail seconds -> connection failure, killed early
        result = CodexBackend().run(
            [sys.executable, "-c", "import time; time.sleep(30)"], "x", timeout=30, early_fail=1)
        self.assertEqual(result.outcome, OUTCOME_EARLY_FAIL)
        self.assertLess(result.elapsed_s, 10)  # terminated well before timeout

    def test_prompt_as_trailing_arg(self):
        # codewhale-style backend: PROMPT_VIA_STDIN=False -> prompt appended
        b = CodewhaleBackend()
        result = b.run(
            [sys.executable, "-c", "import sys; print('ARG=' + sys.argv[1])"],
            "hello-arg", timeout=10, early_fail=5)
        self.assertEqual(result.outcome, OUTCOME_OK)
        self.assertIn("ARG=hello-arg", result.stdout)

    def test_run_result_cmd_excludes_prompt(self):
        # the injected prompt must never leak into RunResult.cmd
        b = CodewhaleBackend()
        result = b.run(
            [sys.executable, "-c", "import sys; print(sys.argv[1])"],
            "secret-prompt-xyz", timeout=10, early_fail=5)
        self.assertNotIn("secret-prompt-xyz", " ".join(result.cmd or []))


if __name__ == "__main__":
    unittest.main()
