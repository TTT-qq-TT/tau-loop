#!/usr/bin/env python3
"""cw agent-events: event log + ledger + failure taxonomy for agent-led.

Everything lives under `.cw-agent/`:
- events.jsonl : append-only event log (cw writes, lead agent reads)
- ledger.json  : per-stage attempt count / status / artifact hashes / evidence
                 pointers (cw writes; agents MUST NOT modify)

Naming boundary (blueprint §3.1): isolated from the harness `.codex/` tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1"
EVENTS_FILE = "events.jsonl"
LEDGER_FILE = "ledger.json"

# Event types (blueprint §4.2)
EVENT_TYPES = {
    "stage_started",
    "stage_completed",
    "stage_failed",
    "all_stages_completed",
    "agent_wake",
    "agent_decision",
}

# Failure classes (blueprint §4.4)
FAIL_FATAL = "fatal"
FAIL_REPAIRABLE = "repairable"
FAIL_NEEDS_HUMAN = "needs_human"

# Default classification rules: regex patterns on (stderr + stdout) lowercase.
# Order matters: first match wins. Rules are mergeable via CLASSIFICATION_RULES.
CLASSIFICATION_RULES: list[tuple[str, str]] = [
    # fatal: authentication / configuration / environment breaks
    ("fatal", r"unauthorized|authentication failed|invalid api key|401|403"),
    ("fatal", r"config(uration)? (not found|missing|invalid)|no such (file|directory)|not found: .*config"),
    ("fatal", r"no space left on device|disk full"),
    ("fatal", r"command not found|no such command"),
    # repairable: network / checksum / dependency / argument issues
    ("repairable", r"connection (refused|reset|closed)|tls|ssl|timeout|timed out|eof|broken pipe|network"),
    ("repairable", r"checksum|hash mismatch|integrity"),
    ("repairable", r"dependency|requirement.*not satisfied|module.*not found|import error"),
    ("repairable", r"unexpected argument|invalid argument|usage:|exit code"),
    ("repairable", r"retry|interrupted|partial (download|write)|resume"),
    # needs_human: permission / resource / anything ambiguous
    ("needs_human", r"permission denied|access denied|not authorized"),
    ("needs_human", r"quota|rate limit|insufficient|resource"),
]

BASE_LEDGER = {
    "schema_version": SCHEMA_VERSION,
    "stages": {},  # stage_id -> {attempts, status, artifact_hash, evidence, failures[]}
    "updated_at": None,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def agent_work_dir(root: Path) -> Path:
    return root / ".cw-agent"


def events_path(root: Path) -> Path:
    return agent_work_dir(root) / EVENTS_FILE


def ledger_path(root: Path) -> Path:
    return agent_work_dir(root) / LEDGER_FILE


def append_event(root: Path, event_type: str, stage_id: str | None = None, payload: dict | None = None) -> dict:
    """Append one event to events.jsonl. Returns the written event dict."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown event type: {event_type}")
    d = agent_work_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": now_utc(),
        "type": event_type,
        "stage_id": stage_id,
        "payload": payload or {},
    }
    with open(events_path(root), "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_events(root: Path, limit: int | None = None) -> list[dict]:
    p = events_path(root)
    if not p.exists():
        return []
    events = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if limit is not None:
        return events[-limit:]
    return events


def read_ledger(root: Path) -> dict:
    p = ledger_path(root)
    if not p.exists():
        return _base_ledger_copy()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _base_ledger_copy()
    merged = _base_ledger_copy()
    merged.update(d)
    return merged


def _base_ledger_copy() -> dict:
    # deep copy: BASE_LEDGER["stages"] is nested and must not be shared
    return {k: (dict(v) if isinstance(v, dict) else v) for k, v in BASE_LEDGER.items()}


def write_ledger(root: Path, ledger: dict) -> Path:
    d = agent_work_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = now_utc()
    p = ledger_path(root)
    p.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def update_stage_ledger(
    root: Path,
    stage_id: str,
    *,
    status: str,
    artifact_hashes: dict[str, str] | None = None,
    evidence: str | None = None,
    failure: str | None = None,
) -> dict:
    """Update ledger for one stage; increments attempts on every call."""
    ledger = read_ledger(root)
    entry = ledger["stages"].setdefault(
        stage_id,
        {"attempts": 0, "status": "pending", "artifact_hashes": {}, "evidence": None, "failures": []},
    )
    entry["attempts"] += 1
    entry["status"] = status
    if artifact_hashes:
        entry["artifact_hashes"] = artifact_hashes
    if evidence:
        entry["evidence"] = evidence
    if failure:
        entry["failures"].append(failure)
    write_ledger(root, ledger)
    return entry


def classify_failure(stage_id: str, stdout: str = "", stderr: str = "", exit_code: int | None = None) -> str:
    """Classify a stage failure. Returns one of FAIL_FATAL / FAIL_REPAIRABLE / FAIL_NEEDS_HUMAN."""
    text = (f"{stdout}\n{stderr}").lower()
    for cls, pattern in CLASSIFICATION_RULES:
        if re.search(pattern, text):
            return cls
    if exit_code is not None and exit_code == 0:
        return FAIL_NEEDS_HUMAN  # no error output but failed verifier -> needs judgment
    return FAIL_REPAIRABLE  # default: wake the lead agent


def wake_decision(root: Path) -> tuple[bool, str]:
    """Decide whether the lead agent should be woken, based on the last event."""
    events = read_events(root, limit=5)
    if not events:
        return False, "no_events"
    last = events[-1]
    etype = last["type"]
    if etype == "all_stages_completed":
        return True, "all_stages_completed"
    if etype == "stage_failed":
        cls = last.get("payload", {}).get("classification", FAIL_NEEDS_HUMAN)
        if cls == FAIL_REPAIRABLE:
            return True, f"stage_failed:{cls}"
        return False, f"stage_failed:{cls}"
    return False, f"event:{etype}"


# ---- CLI ------------------------------------------------------------------


def cmd_log(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    append_event(root, args.type, args.stage_id)
    print(json.dumps({"logged": args.type, "stage_id": args.stage_id}, ensure_ascii=False, indent=2))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    events = read_events(root, limit=args.limit)
    print(json.dumps(events, ensure_ascii=False, indent=2))
    return 0


def cmd_wake(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    wake, reason = wake_decision(root)
    print(json.dumps({"wake": wake, "reason": reason}, ensure_ascii=False, indent=2))
    return 0


def cmd_ledger(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    print(json.dumps(read_ledger(root), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cw agent-events", description="agent-led event log / ledger / failure taxonomy")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("log", help="append an event (stage_started|stage_completed|stage_failed|all_stages_completed|agent_wake|agent_decision)")
    p.add_argument("type", choices=sorted(EVENT_TYPES))
    p.add_argument("--stage-id")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("show", help="read recent events")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("wake", help="decide whether the lead agent should wake")
    p.set_defaults(func=cmd_wake)

    p = sub.add_parser("ledger", help="show stage ledger")
    p.set_defaults(func=cmd_ledger)

    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
