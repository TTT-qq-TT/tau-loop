#!/usr/bin/env python3
"""cw agent-session: managed session lifecycle for the agent-led lead agent.

The lead agent is a memory-bearing session driven by a backend adapter
(cw_agent_backends: codex full, claude/codewhale skeletons). This module
manages its lifecycle on disk (`.cw-agent/session.json`) and delegates the
actual `start`/`resume` invocation to the selected backend, which applies
hard timeout + early-fail detection uniformly.

Backend selection is EXPLICIT (owner decision 2026-08-06): `--backend` or the
value already recorded in session.json; never auto-detected.

Naming boundary (blueprint §3.1): everything lives under `.cw-agent/`, isolated
from the harness `.codex/` tree. session.json records the resume handle,
NOT the cw_state session entities.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from cw_agent_backends import (
    DEFAULT_MODEL as BACKEND_DEFAULT_MODEL,
    DEFAULT_TIMEOUT,
    DEFAULT_EARLY_FAIL,
    CodexBackend,
    backend_for,
)

SCHEMA_VERSION = "1"
SESSION_JSON = "session.json"
DEFAULT_MODEL = BACKEND_DEFAULT_MODEL

BASE_SESSION = {
    "schema_version": SCHEMA_VERSION,
    "id": None,
    "thread": None,
    "model": DEFAULT_MODEL,
    "backend": None,  # "codex" | "claude" | "codewhale" (explicitly chosen)
    "working_dir": None,
    "last_event_at": None,
    "resume_hint": None,  # "id" | "last" | None
    "status": "idle",  # idle | active | stopped
    "notes": "",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def agent_work_dir(root: Path) -> Path:
    return root / ".cw-agent"


def session_path(root: Path) -> Path:
    return agent_work_dir(root) / SESSION_JSON


def ensure_agent_dir(root: Path) -> Path:
    d = agent_work_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    gitignore = d / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("session.json\nartifacts/\nledger.json\nevents.jsonl\n", encoding="utf-8")
    return d


def read_session(root: Path) -> dict:
    p = session_path(root)
    if not p.exists():
        return dict(BASE_SESSION)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(BASE_SESSION)
    merged = dict(BASE_SESSION)
    merged.update(d)
    return merged


def write_session(root: Path, data: dict) -> Path:
    agent_work_dir(root).mkdir(parents=True, exist_ok=True)
    p = session_path(root)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def build_start_cmd(model: str, working_dir: Path) -> list[str]:
    # Delegate to the codex backend (single source of truth).
    return CodexBackend().start_cmd(model, working_dir)


def build_resume_cmd(session_id: str | None, model: str, working_dir: Path, use_last: bool = False) -> list[str]:
    # Delegate to the codex backend (single source of truth). Note: `codex
    # exec resume` has NO `-s`; PROMPT must be '-' (stdin); approvals/sandbox
    # are bypassed by default (owner decision 2026-08-06).
    return CodexBackend().resume_cmd(session_id, model, working_dir, use_last=use_last)


_SESSION_ID_RE = re.compile(r'"session_id"\s*:\s*"([0-9a-fA-F-]{20,})"')


def extract_session_id_from_jsonl(output: str) -> str | None:
    """Best-effort extraction of a codex session/thread id from `--json` events."""
    # codex exec --json emits thread_id (verified 2026-08-06); the backend
    # keeps session_id as a compat fallback.
    return CodexBackend().extract_session_id(output)


def run_codex(cmd: list[str], prompt: str) -> tuple[int, str, str]:
    """Run codex with the prompt on stdin. Returns (exit_code, stdout, stderr)."""
    proc = subprocess.run(
        cmd,
        input=prompt + "\n",
        text=True,
        capture_output=True,
        timeout=None,
    )
    return proc.returncode, proc.stdout, proc.stderr


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ensure_agent_dir(root)
    s = read_session(root)
    s["working_dir"] = str(root)
    s["updated_at"] = now_utc()
    write_session(root, s)
    print(json.dumps({"initialized": str(agent_work_dir(root)), "session": s}, ensure_ascii=False, indent=2))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ensure_agent_dir(root)
    s = read_session(root)
    backend_name = args.backend or s.get("backend")
    if not backend_name:
        print("error: --backend required for start (codex|claude|codewhale); "
              "the lead agent picks it before cw starts", file=sys.stderr)
        return 1
    backend = backend_for(backend_name, model=args.model, bypass=not args.strict)
    s["status"] = "active"
    # model priority: --model > backend default (config-following) > recorded > fallback
    s["model"] = args.model or getattr(backend, "default_model", None) or s.get("model") or DEFAULT_MODEL
    s["backend"] = backend_name
    s["working_dir"] = str(root)
    s["last_event_at"] = now_utc()
    write_session(root, s)
    cmd = backend.start_cmd(s["model"], root)
    result = backend.run(cmd, args.prompt, timeout=args.timeout, early_fail=args.early_fail)
    session_id = backend.extract_session_id(result.stdout)
    if not session_id and hasattr(backend, "latest_session_id"):
        # codewhale redacts session_id in stream-json; fall back to the
        # short-prefix ID from `codewhale sessions`.
        session_id = backend.latest_session_id()
    s["id"] = session_id or s.get("id")
    s["resume_hint"] = "id" if session_id else "last"
    s["last_event_at"] = now_utc()
    write_session(root, s)
    print(json.dumps(
        {"exit_code": result.exit_code, "outcome": result.outcome,
         "session_id": session_id, "resume_hint": s["resume_hint"]},
        ensure_ascii=False, indent=2))
    if result.stdout.strip():
        print(f"agent output tail:\n{result.stdout[-2000:]}", file=sys.stderr)
    if result.exit_code != 0:
        print(f"stderr: {result.stderr[-2000:]}", file=sys.stderr)
    return 0 if result.exit_code == 0 else 1


def cmd_resume(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    ensure_agent_dir(root)
    s = read_session(root)
    backend_name = args.backend or s.get("backend")
    if not backend_name:
        print("error: no backend recorded for this session; pass --backend", file=sys.stderr)
        return 1
    backend = backend_for(backend_name, model=args.model, bypass=not args.strict)
    use_last = args.last or (args.last is False and not s.get("id"))
    cmd = backend.resume_cmd(s.get("id"), args.model or s.get("model") or DEFAULT_MODEL, root, use_last=use_last)
    s["status"] = "active"
    s["last_event_at"] = now_utc()
    write_session(root, s)
    result = backend.run(cmd, args.prompt, timeout=args.timeout, early_fail=args.early_fail)
    if not use_last:
        session_id = backend.extract_session_id(result.stdout)
        if session_id:
            s["id"] = session_id
            s["resume_hint"] = "id"
    s["last_event_at"] = now_utc()
    write_session(root, s)
    print(json.dumps({"exit_code": result.exit_code, "outcome": result.outcome,
                      "resumed": use_last and "last" or s.get("id")}, ensure_ascii=False, indent=2))
    if result.stdout.strip():
        print(f"agent output tail:\n{result.stdout[-2000:]}", file=sys.stderr)
    if result.exit_code != 0:
        print(f"stderr: {result.stderr[-2000:]}", file=sys.stderr)
    return 0 if result.exit_code == 0 else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    s = read_session(root)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    s = read_session(root)
    s["status"] = "stopped"
    s["last_event_at"] = now_utc()
    write_session(root, s)
    print(json.dumps({"status": "stopped", "session": s.get("id")}, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cw agent-session", description="agent-led lead-agent session lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="initialize .cw-agent/ and session.json")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("start", help="start a new lead-agent session via the chosen backend")
    p.add_argument("prompt")
    p.add_argument("--model", default=None)
    p.add_argument("--backend", default=None, help="codex|claude|codewhale (required unless recorded)")
    p.add_argument("--strict", action="store_true", help="disable approval/sandbox bypass for codex resume")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--early-fail", type=float, default=DEFAULT_EARLY_FAIL)
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("resume", help="resume the lead-agent session via the chosen backend")
    p.add_argument("prompt")
    p.add_argument("--model", default=None)
    p.add_argument("--backend", default=None, help="codex|claude|codewhale (default: recorded backend)")
    p.add_argument("--strict", action="store_true", help="disable approval/sandbox bypass for codex resume")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    p.add_argument("--early-fail", type=float, default=DEFAULT_EARLY_FAIL)
    p.add_argument("--last", action="store_true", help="resume most recent session instead of stored id")
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("status", help="show session.json")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("stop", help="mark session stopped")
    p.set_defaults(func=cmd_stop)

    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
