#!/usr/bin/env python3
"""cw agent-executor: agent-led stage executor (blueprint §4.3).

Reads `.cw-agent/work-order.json` (agent-generated work order: stages with
command / self_check / expected_artifacts / checksum), runs each stage, writes
receipts and events. No LLM involvement; pure execution + verification.

Executes in stage order; stops on first failure (classified via the S2
taxonomy). Receipts live in `.cw-agent/artifacts/<stage>/receipt.json`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from cw_agent_events import (
    append_event,
    classify_failure,
    update_stage_ledger,
    agent_work_dir,
)

SCHEMA_VERSION = "1"
WORK_ORDER_FILE = "work-order.json"
ARTIFACTS_DIR = "artifacts"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def work_order_path(root: Path) -> Path:
    return agent_work_dir(root) / WORK_ORDER_FILE


def artifacts_dir(root: Path, stage_id: str) -> Path:
    return agent_work_dir(root) / ARTIFACTS_DIR / stage_id


def read_work_order(root: Path) -> dict:
    p = work_order_path(root)
    if not p.exists():
        raise FileNotFoundError(f"work order not found: {p}")
    wo = json.loads(p.read_text(encoding="utf-8"))
    if wo.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported work-order schema: {wo.get('schema_version')}")
    stages = wo.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("work-order stages must be a non-empty array")
    for i, s in enumerate(stages):
        if not s.get("id") or not s.get("command"):
            raise ValueError(f"stages[{i}] requires id and command")
    return wo


def run_command(command: str, cwd: Path) -> tuple[int, str, str]:
    """Run a shell command, capture stdout/stderr."""
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def check_artifacts(root: Path, stage: dict) -> tuple[bool, list[str]]:
    """Verify expected_artifacts exist. Returns (ok, missing_list)."""
    missing = []
    for rel in stage.get("expected_artifacts", []):
        p = Path(rel)
        if not p.is_absolute():
            p = root / rel
        if not p.exists():
            missing.append(rel)
    return not missing, missing


def write_receipt(root: Path, stage: dict, *, status: str, stdout: str, stderr: str, artifacts_ok: bool, classification: str | None = None) -> Path:
    d = artifacts_dir(root, stage["id"])
    d.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "stage_id": stage["id"],
        "ts": now_utc(),
        "status": status,
        "command": stage.get("command"),
        "artifacts_ok": artifacts_ok,
        "classification": classification,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
    }
    p = d / "receipt.json"
    p.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def run_stage(root: Path, stage: dict) -> int:
    """Run one stage. Returns 0 on success, non-zero on failure."""
    sid = stage["id"]
    append_event(root, "stage_started", sid)
    exit_code, stdout, stderr = run_command(stage["command"], root)
    if exit_code == 0:
        artifacts_ok, missing = check_artifacts(root, stage)
        if artifacts_ok:
            receipt = write_receipt(root, stage, status="completed", stdout=stdout, stderr=stderr, artifacts_ok=True)
            append_event(root, "stage_completed", sid, {"evidence": str(receipt)})
            update_stage_ledger(root, sid, status="completed", evidence=str(receipt))
            return 0
        # command ok but artifacts missing -> failure needing judgment
        cls = classify_failure(sid, stdout=stdout, stderr=f"expected artifacts missing: {missing}", exit_code=0)
        receipt = write_receipt(root, stage, status="failed", stdout=stdout, stderr=str(missing), artifacts_ok=False, classification=cls)
        append_event(root, "stage_failed", sid, {"classification": cls, "evidence": str(receipt), "reason": f"artifacts_missing:{missing}"})
        update_stage_ledger(root, sid, status="failed", evidence=str(receipt), failure=f"artifacts_missing:{missing}")
        return 1
    # command failed
    cls = classify_failure(sid, stdout=stdout, stderr=stderr, exit_code=exit_code)
    receipt = write_receipt(root, stage, status="failed", stdout=stdout, stderr=stderr, artifacts_ok=False, classification=cls)
    append_event(root, "stage_failed", sid, {"classification": cls, "evidence": str(receipt), "reason": f"exit:{exit_code}"})
    update_stage_ledger(root, sid, status="failed", evidence=str(receipt), failure=f"exit:{exit_code}")
    return 1


def run_all(root: Path) -> int:
    wo = read_work_order(root)
    print(json.dumps({"work_order": wo.get("goal", ""), "stages": len(wo["stages"])}, ensure_ascii=False))
    for stage in wo["stages"]:
        print(f"stage {stage['id']}: running...")
        rc = run_stage(root, stage)
        if rc != 0:
            print(f"stage {stage['id']}: FAILED")
            return 1
        print(f"stage {stage['id']}: OK")
    append_event(root, "all_stages_completed")
    print("all stages completed")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    return run_all(root)


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    try:
        wo = read_work_order(root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"valid": True, "stages": [s["id"] for s in wo["stages"]]}, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cw agent-exec", description="agent-led stage executor (no LLM)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="run all stages from .cw-agent/work-order.json")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("validate", help="validate work-order.json")
    p.set_defaults(func=cmd_validate)

    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
