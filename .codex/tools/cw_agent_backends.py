#!/usr/bin/env python3
"""cw agent-backends: session-layer backend adapters (agent-led).

Abstracts 'which agent CLI drives the lead session' behind a small
interface: probe / start_cmd / resume_cmd / extract_session_id / run.
Backends: codex (fully wired), claude / codewhale (skeletons; real
verification is a follow-up spec — spec agent-session-backend-adapters §8.5).

Selection is EXPLICIT (owner decision 2026-08-06): no auto-detection — the
lead agent picks the backend before cw starts (work-order `backend` field or
`--backend`); probe() only validates availability of the chosen backend.

run() applies the probe-report recommendations uniformly:
- hard timeout (default 300s) — a timeout is a data point, not a hang
- early-fail: no first output within early_fail seconds (default 30s) is a
  connection failure (repairable), terminated early
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MODEL = "gpt-5.6-sol"  # fallback when config cannot be read
DEFAULT_TIMEOUT = 300.0
DEFAULT_EARLY_FAIL = 30.0

BACKENDS = ("codex", "claude", "codewhale")

# run outcomes (probe report §6: timeout/connection-failure != fatal)
OUTCOME_OK = "ok"
OUTCOME_TIMEOUT = "timeout"
OUTCOME_EARLY_FAIL = "connection_failed"
OUTCOME_ERROR = "error"

MAX_CAPTURE = 200_000  # keep only the last N chars of each stream


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_codex_model(config_path: str | None = None) -> str:
    """Default codex model from config.toml (tomllib; py3.8 line-match fallback)."""
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    path = Path(config_path) if config_path else home / "config.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return DEFAULT_MODEL
    try:
        import tomllib  # py3.11+
        data = tomllib.loads(text)
        m = data.get("model")
        if isinstance(m, str):
            return m
    except Exception:
        pass
    m = re.search(r'^\s*model\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else DEFAULT_MODEL


class RunResult:
    """Structured outcome of one backend invocation."""

    def __init__(self, exit_code: int | None, stdout: str, stderr: str,
                 outcome: str, elapsed_s: float, time_to_first_output_s: float | None,
                 cmd: list[str] | None = None):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.outcome = outcome
        self.elapsed_s = round(elapsed_s, 2)
        self.time_to_first_output_s = round(time_to_first_output_s, 2) if time_to_first_output_s is not None else None
        self.cmd = cmd

    def as_dict(self) -> dict:
        return {
            "ts": now_iso(),
            "cmd": " ".join(self.cmd or []),
            "exit_code": self.exit_code,
            "outcome": self.outcome,
            "elapsed_s": self.elapsed_s,
            "time_to_first_output_s": self.time_to_first_output_s,
            "stdout_tail": self.stdout[-2000:],
            "stderr_tail": self.stderr[-2000:],
        }


class BaseBackend(ABC):
    name: str = "base"
    # codex-family CLIs read the prompt from stdin; others (codewhale) take
    # it as a trailing positional argument.
    PROMPT_VIA_STDIN: bool = True

    def probe(self) -> bool:
        return shutil.which(self.name) is not None

    @abstractmethod
    def start_cmd(self, model: str, working_dir: Path) -> list[str]:
        """Command that starts a fresh lead session (prompt via stdin)."""

    @abstractmethod
    def resume_cmd(self, session_id: str | None, model: str, working_dir: Path,
                   use_last: bool = False) -> list[str]:
        """Command that resumes a lead session (prompt via stdin)."""

    @abstractmethod
    def extract_session_id(self, stdout: str) -> str | None:
        """Best-effort session/thread handle from `--json`-style output."""

    def run(self, cmd: list[str], prompt: str, *,
            timeout: float = DEFAULT_TIMEOUT,
            early_fail: float = DEFAULT_EARLY_FAIL) -> RunResult:
        """Run cmd with prompt (stdin or trailing arg per PROMPT_VIA_STDIN).

        Hard timeout + early-fail guard. RunResult.cmd records the original
        cmd (without the injected prompt) so prompts never leak into logs.
        """
        t0 = time.monotonic()
        t_first: float | None = None
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        run_cmd = list(cmd)
        if not self.PROMPT_VIA_STDIN:
            run_cmd.append(prompt)

        proc = subprocess.Popen(
            run_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )

        def read_stream(stream, chunks: list[str]) -> None:
            nonlocal t_first
            for line in iter(stream.readline, ""):
                if t_first is None:
                    t_first = time.monotonic()
                chunks.append(line)
                if sum(len(c) for c in chunks) > MAX_CAPTURE * 2:
                    chunks.pop(0)
            stream.close()

        t_out = threading.Thread(target=read_stream, args=(proc.stdout, stdout_chunks), daemon=True)
        t_err = threading.Thread(target=read_stream, args=(proc.stderr, stderr_chunks), daemon=True)
        t_out.start()
        t_err.start()

        try:
            if self.PROMPT_VIA_STDIN:
                proc.stdin.write(prompt + "\n")
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

        outcome = OUTCOME_OK
        try:
            # Phase 1: wait for first output, bounded by min(early_fail, timeout).
            # The hard timeout must never be exceeded by the early-fail poll.
            first_phase = min(early_fail, timeout)
            deadline_first = t0 + first_phase
            while time.monotonic() < deadline_first:
                if t_first is not None:
                    break
                if proc.poll() is not None:
                    break
                time.sleep(0.2)

            if t_first is not None or proc.poll() is not None:
                # got output (or exited): wait out the remaining budget
                proc.wait(timeout=max(0.0, timeout - (time.monotonic() - t0)))
            elif early_fail < timeout:
                # still silent after early_fail -> connection failure, not a hang
                proc.kill()
                proc.wait()
                outcome = OUTCOME_EARLY_FAIL
            else:
                # early_fail >= timeout and nothing ever came -> timeout
                proc.kill()
                proc.wait()
                outcome = OUTCOME_TIMEOUT
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            outcome = OUTCOME_TIMEOUT

        exit_code = proc.returncode
        t_out.join(timeout=2)
        t_err.join(timeout=2)
        elapsed = time.monotonic() - t0
        if outcome == OUTCOME_OK and exit_code != 0:
            outcome = OUTCOME_ERROR
        return RunResult(
            exit_code=exit_code,
            stdout="".join(stdout_chunks),
            stderr="".join(stderr_chunks),
            outcome=outcome,
            elapsed_s=elapsed,
            time_to_first_output_s=(t_first - t0) if t_first is not None else None,
            cmd=cmd,
        )


# ---- codex -----------------------------------------------------------------


class CodexBackend(BaseBackend):
    """codex-cli: `codex exec` (start) / `codex exec resume` (resume)."""

    name = "codex"

    def __init__(self, model: str | None = None, config_path: str | None = None,
                 bypass: bool = True):
        self._model = model or read_codex_model(config_path)
        self._bypass = bypass

    @property
    def default_model(self) -> str:
        return self._model

    def start_cmd(self, model: str, working_dir: Path) -> list[str]:
        return ["codex", "exec", "-s", "workspace-write", "-m", model, "--json"]

    def resume_cmd(self, session_id: str | None, model: str, working_dir: Path,
                   use_last: bool = False) -> list[str]:
        # `codex exec resume` has NO -s; PROMPT must be '-' (stdin);
        # bypass approvals/sandbox by default (owner decision 2026-08-06;
        # tt-workflow constraints are the guard), --strict disables it.
        cmd = ["codex", "exec", "resume"]
        if use_last:
            cmd.append("--last")
        elif session_id:
            cmd.append(session_id)
        cmd.append("-")
        cmd += ["-m", model, "--json"]
        if self._bypass:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        return cmd

    _THREAD_ID_RE = re.compile(r'"thread_id"\s*:\s*"([0-9a-fA-F-]{20,})"')
    _SESSION_ID_RE = re.compile(r'"session_id"\s*:\s*"([0-9a-fA-F-]{20,})"')

    def extract_session_id(self, stdout: str) -> str | None:
        # codex exec --json emits thread_id (verified 2026-08-06); keep
        # session_id as a compat fallback.
        for pattern in (self._THREAD_ID_RE, self._SESSION_ID_RE):
            m = pattern.search(stdout)
            if m:
                return m.group(1)
        return None


# ---- claude (skeleton) -----------------------------------------------------


class ClaudeBackend(BaseBackend):
    """Claude Code headless: `claude -p` (+ `--resume <id>` / `--continue`).

    Skeleton: command construction + probe. Real handle extraction and
    end-to-end verification are the follow-up spec (§8.5).
    """

    name = "claude"

    def start_cmd(self, model: str, working_dir: Path) -> list[str]:
        cmd = ["claude", "-p"]
        if model and model != DEFAULT_MODEL:
            cmd += ["--model", model]
        return cmd

    def resume_cmd(self, session_id: str | None, model: str, working_dir: Path,
                   use_last: bool = False) -> list[str]:
        cmd = ["claude", "-p"]
        if use_last:
            cmd.append("--continue")
        elif session_id:
            cmd += ["--resume", session_id]
        return cmd

    def extract_session_id(self, stdout: str) -> str | None:
        # TODO(next spec): real `claude -p` session handle format not yet measured.
        return None


# ---- codewhale (skeleton) --------------------------------------------------


class CodewhaleBackend(BaseBackend):
    """Codewhale TUI runtime: `codewhale exec` (+ `--resume` / `--continue`).

    Real behavior verified 2026-08-07:
    - prompt is a TRAILING POSITIONAL ARGUMENT (not stdin) -> PROMPT_VIA_STDIN=False
    - `--auto` enables tool-backed agent mode (needed to edit work-order)
    - `--output-format stream-json` emits content events; its session_id is
      REDACTED (`<redacted:...>`), so the real handle comes from
      `codewhale sessions` short-prefix IDs (latest_session_id()).
    - `--resume <id|prefix>` / `--continue` restore conversation context
      (verified: secret 4242 recalled across sessions).
    """

    name = "codewhale"
    PROMPT_VIA_STDIN = False

    def start_cmd(self, model: str, working_dir: Path) -> list[str]:
        return ["codewhale", "exec", "--auto", "--output-format", "stream-json"]

    def resume_cmd(self, session_id: str | None, model: str, working_dir: Path,
                   use_last: bool = False) -> list[str]:
        cmd = ["codewhale", "exec"]
        if use_last:
            cmd.append("--continue")
        elif session_id:
            cmd += ["--resume", session_id]
        cmd += ["--auto", "--output-format", "stream-json"]
        return cmd

    def extract_session_id(self, stdout: str) -> str | None:
        # codewhale redacts session_id to `<redacted:...>` in stream-json, so
        # nothing usable can be parsed from stdout; use latest_session_id().
        return None

    def latest_session_id(self) -> str | None:
        """Most recent session short-prefix ID from `codewhale sessions`."""
        try:
            r = subprocess.run(["codewhale", "sessions"],
                               capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return self._latest_session_id_from_output(r.stdout)

    @staticmethod
    def _latest_session_id_from_output(output: str) -> str | None:
        m = re.search(r"^\s*\*\s+([0-9a-fA-F]{6,})\s*\|", output, re.MULTILINE)
        return m.group(1) if m else None


# ---- selection (explicit; owner decision 2026-08-06) -----------------------


def backend_for(name: str, *, model: str | None = None, config_path: str | None = None,
                bypass: bool = True, strict: bool = False) -> BaseBackend:
    if name not in BACKENDS:
        raise ValueError(f"unknown backend: {name!r} (choose from {', '.join(BACKENDS)})")
    if name == "codex":
        return CodexBackend(model=model, config_path=config_path, bypass=not strict)
    if name == "claude":
        return ClaudeBackend()
    return CodewhaleBackend()


def pick_backend(explicit: str | None, work_order_backend: str | None,
                 session_backend: str | None) -> str:
    """Explicit --backend > work-order.backend > session.backend. Never auto-detect."""
    for candidate in (explicit, work_order_backend, session_backend):
        if candidate:
            if candidate not in BACKENDS:
                raise ValueError(f"unknown backend: {candidate!r} (choose from {', '.join(BACKENDS)})")
            return candidate
    raise ValueError("no backend specified: pass --backend or set the work-order `backend` field")


def validate_backend(name: str) -> bool:
    """Probe availability of a chosen backend (validation only, not selection)."""
    if name not in BACKENDS:
        raise ValueError(f"unknown backend: {name!r}")
    return shutil.which(name) is not None


if __name__ == "__main__":
    # tiny CLI for manual checks: cw agent-backends <name> [--model M]
    argv = sys.argv[1:]
    name = argv[0] if argv else "codex"
    try:
        backend = backend_for(name)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({
        "backend": name,
        "probe": backend.probe(),
        "available": shutil.which(name),
        "default_model": getattr(backend, "default_model", None),
        "start_cmd": backend.start_cmd(getattr(backend, "default_model", DEFAULT_MODEL), Path(".")),
        "resume_cmd": backend.resume_cmd("abc-123", getattr(backend, "default_model", DEFAULT_MODEL), Path(".")),
    }, ensure_ascii=False, indent=2))
