#!/usr/bin/env python3
"""Portable foreground supervisor for continuous-work v2 Phases A and B."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


CONTRACT_SCHEMAS = {"cw-run-contract/v1", "cw-run-contract/v2"}
RUNTIME_SCHEMA = "cw-run-runtime/v1"
ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class ContractError(ValueError):
    pass


class ManagedStop(RuntimeError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"contract does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON in contract {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("contract must be a JSON object")
    return value


def require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ContractError(f"{label} must match {ID_PATTERN.pattern}")
    return value


def require_argv(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ContractError(f"{label} must be a non-empty array of non-empty strings")
    return value


def path_inside_root(root: Path, value: Any, label: str) -> Path:
    if value is None:
        return root
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a non-empty string when supplied")
    resolved = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ContractError(f"{label} must remain inside repo root: {value}") from exc
    if not resolved.is_dir():
        raise ContractError(f"{label} is not a directory: {value}")
    return resolved


def repo_path(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a non-empty string")
    resolved = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ContractError(f"{label} must remain inside repo root: {value}") from exc
    return resolved


def require_env(value: Any, label: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or not all(isinstance(key, str) and key and isinstance(item, str) for key, item in value.items()):
        raise ContractError(f"{label} must be an object with non-empty string keys and string values")
    return dict(value)


def require_positive_number(value: Any, label: str, *, default: float | None = None) -> float | None:
    if value is None:
        return default
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ContractError(f"{label} must be a positive number")
    return float(value)


def require_nonnegative_int(value: Any, label: str, *, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ContractError(f"{label} must be a non-negative integer")
    return value


def require_positive_int(value: Any, label: str, *, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ContractError(f"{label} must be a positive integer")
    return value


def parse_limits(value: Any) -> dict[str, Any]:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ContractError("limits must be an object")
    return {
        "max_run_seconds": require_positive_number(value.get("max_run_seconds"), "limits.max_run_seconds"),
        "health_interval_seconds": require_positive_number(value.get("health_interval_seconds"), "limits.health_interval_seconds", default=300.0),
        "terminate_grace_seconds": require_positive_number(value.get("terminate_grace_seconds"), "limits.terminate_grace_seconds", default=15.0),
        "max_stage_attempts": require_positive_int(value.get("max_stage_attempts"), "limits.max_stage_attempts", default=1),
        "max_handoffs": require_nonnegative_int(value.get("max_handoffs"), "limits.max_handoffs", default=0),
    }


def parse_permissions(root: Path, value: Any) -> dict[str, Any]:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ContractError("permissions must be an object")
    network = value.get("network", "unspecified")
    credentials = value.get("credentials", "none")
    paths = value.get("path_roots", ["."])
    if network not in {"unspecified", "none", "required"}:
        raise ContractError("permissions.network must be unspecified, none, or required")
    if credentials not in {"none", "inherited_env"}:
        raise ContractError("permissions.credentials must be none or inherited_env")
    if not isinstance(paths, list) or not paths:
        raise ContractError("permissions.path_roots must be a non-empty array")
    resolved_paths = [relative_to_root(root, path_inside_root(root, item, "permissions.path_roots")) for item in paths]
    return {
        "network": network,
        "credentials": credentials,
        "path_roots": sorted(set(resolved_paths)),
        "enforcement": "declarative_only",
    }


def parse_command(root: Path, value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return {
        "argv": require_argv(value.get("argv"), f"{label}.argv"),
        "cwd": path_inside_root(root, value.get("cwd"), f"{label}.cwd"),
        "env": require_env(value.get("env"), f"{label}.env"),
    }


def parse_agent_loop(root: Path, value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ContractError("agent_loop must be an object")
    mode = value.get("mode", "assisted")
    if mode not in {"assisted", "unattended"}:
        raise ContractError("agent_loop.mode must be assisted or unattended")
    repair_on = value.get("repair_on", ["command_failed", "verifier_failed"])
    if not isinstance(repair_on, list) or not repair_on or not all(item in {"command_failed", "verifier_failed"} for item in repair_on):
        raise ContractError("agent_loop.repair_on must list command_failed and/or verifier_failed")
    allowed_files = value.get("allowed_files")
    if not isinstance(allowed_files, list) or not allowed_files:
        raise ContractError("agent_loop.allowed_files must be a non-empty array")
    normalized_files = [relative_to_root(root, repo_path(root, item, "agent_loop.allowed_files")) for item in allowed_files]
    contract_roots = value.get("allowed_contract_roots", [".codex/contracts"])
    if not isinstance(contract_roots, list) or not contract_roots:
        raise ContractError("agent_loop.allowed_contract_roots must be a non-empty array")
    normalized_roots = [relative_to_root(root, path_inside_root(root, item, "agent_loop.allowed_contract_roots")) for item in contract_roots]
    checks = value.get("candidate_checks", [])
    if not isinstance(checks, list):
        raise ContractError("agent_loop.candidate_checks must be an array")
    parsed_checks = []
    check_ids: set[str] = set()
    for index, raw_check in enumerate(checks):
        if not isinstance(raw_check, dict):
            raise ContractError(f"agent_loop.candidate_checks[{index}] must be an object")
        check_id = require_id(raw_check.get("id"), f"agent_loop.candidate_checks[{index}].id")
        if check_id in check_ids:
            raise ContractError(f"duplicate agent_loop candidate check id: {check_id}")
        check_ids.add(check_id)
        parsed_check = parse_command(root, raw_check, f"agent_loop.candidate_checks[{index}]")
        parsed_checks.append(
            {
                "id": check_id,
                "argv": parsed_check["argv"],
                "cwd": relative_to_root(root, parsed_check["cwd"]),
                "env": parsed_check["env"],
            }
        )
    policy = value.get("repair_execution_policy", "same_argv_only")
    if policy != "same_argv_only":
        raise ContractError("agent_loop.repair_execution_policy must be same_argv_only")
    for label in ("require_clean_git", "require_final_review"):
        if label in value and not isinstance(value[label], bool):
            raise ContractError(f"agent_loop.{label} must be boolean")
    return {
        "mode": mode,
        "repair_on": sorted(set(repair_on)),
        "max_repair_turns": require_positive_int(value.get("max_repair_turns"), "agent_loop.max_repair_turns", default=1),
        "max_total_agent_seconds": require_positive_number(value.get("max_total_agent_seconds"), "agent_loop.max_total_agent_seconds", default=900.0),
        "allowed_files": sorted(set(normalized_files)),
        "allowed_contract_roots": sorted(set(normalized_roots)),
        "candidate_checks": parsed_checks,
        "repair_execution_policy": policy,
        "require_clean_git": value.get("require_clean_git", True),
        "require_final_review": value.get("require_final_review", True),
    }


def parse_contract(root: Path, contract_path: Path) -> dict[str, Any]:
    contract = read_json(contract_path)
    schema_version = contract.get("schema_version")
    if schema_version not in CONTRACT_SCHEMAS:
        raise ContractError("schema_version must be cw-run-contract/v1 or cw-run-contract/v2")
    contract_id = require_id(contract.get("id"), "id")
    limits = parse_limits(contract.get("limits"))
    permissions = parse_permissions(root, contract.get("permissions"))
    stages_value = contract.get("stages")
    if not isinstance(stages_value, list) or not stages_value:
        raise ContractError("stages must be a non-empty array")
    stages: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_stage in enumerate(stages_value):
        if not isinstance(raw_stage, dict):
            raise ContractError(f"stages[{index}] must be an object")
        stage_id = require_id(raw_stage.get("id"), f"stages[{index}].id")
        if stage_id in seen_ids:
            raise ContractError(f"duplicate stage id: {stage_id}")
        seen_ids.add(stage_id)
        stage_command = parse_command(root, raw_stage, f"stages[{index}]")
        verifier = parse_command(root, raw_stage.get("verifier"), f"stages[{index}].verifier")
        stages.append(
            {
                "id": stage_id,
                **stage_command,
                "verifier": verifier,
                "deadline_seconds": require_positive_number(raw_stage.get("deadline_seconds"), f"stages[{index}].deadline_seconds"),
            }
        )
    agent_loop = parse_agent_loop(root, contract.get("agent_loop"))
    if agent_loop is not None and schema_version != "cw-run-contract/v2":
        raise ContractError("agent_loop requires schema_version cw-run-contract/v2")
    return {"id": contract_id, "schema_version": schema_version, "limits": limits, "permissions": permissions, "stages": stages, "agent_loop": agent_loop}


def relative_to_root(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def process_identity(pid: int) -> dict[str, Any]:
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.exists():
        try:
            fields = proc_stat.read_text(encoding="utf-8").rsplit(") ", 1)[1].split()
            return {"kind": "linux_proc_start_ticks", "value": fields[19]}
        except (IndexError, OSError):
            pass
    try:
        result = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            check=False,
            capture_output=True,
            text=True,
        )
        value = result.stdout.strip()
        if result.returncode == 0 and value:
            return {"kind": "ps_lstart", "value": value}
    except OSError:
        pass
    return {"kind": "recorded_start_time", "value": now_utc()}


def process_identity_matches(pid: int, expected: dict[str, Any]) -> bool | None:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    if expected.get("kind") not in {"linux_proc_start_ticks", "ps_lstart"}:
        return None
    current = process_identity(pid)
    return current == expected


def log_evidence(path: Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - 4096))
            tail = handle.read()
    except OSError:
        return {"available": False}
    return {"available": True, "bytes": size, "tail_sha256": hashlib.sha256(tail).hexdigest()}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_event(path: Path, event: str, *, stage_id: str | None = None, details: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"at": now_utc(), "event": event}
    if stage_id is not None:
        payload["stage_id"] = stage_id
    if details:
        payload["details"] = details
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def snapshot_stage(root: Path, stage: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    stdout_log = run_dir / "logs" / f"{stage['id']}.stdout.log"
    stderr_log = run_dir / "logs" / f"{stage['id']}.stderr.log"
    return {
        "id": stage["id"],
        "status": "planned",
        "argv": stage["argv"],
        "cwd": relative_to_root(root, stage["cwd"]),
        "env_keys": sorted(stage["env"]),
        "verifier": {
            "argv": stage["verifier"]["argv"],
            "cwd": relative_to_root(root, stage["verifier"]["cwd"]),
            "env_keys": sorted(stage["verifier"]["env"]),
            "exit_code": None,
        },
        "process": None,
        "attempts_started": 0,
        "deadline_seconds": stage["deadline_seconds"],
        "health": None,
        "logs": {"stdout": relative_to_root(root, stdout_log), "stderr": relative_to_root(root, stderr_log)},
        "failure_reason": None,
        "failure_fingerprint": None,
    }


def build_runtime(root: Path, contract_path: Path, parsed: dict[str, Any], run_id: str, run_dir: Path) -> dict[str, Any]:
    return {
        "schema_version": RUNTIME_SCHEMA,
        "run_id": run_id,
        "contract_id": parsed["id"],
        "contract_path": relative_to_root(root, contract_path),
        "status": "running",
        "started_at": now_utc(),
        "finished_at": None,
        "host": {"platform": platform.system(), "python": platform.python_version()},
        "event_log": relative_to_root(root, run_dir / "events.jsonl"),
        "control_path": relative_to_root(root, run_dir / "control.json"),
        "limits": parsed["limits"],
        "permissions": parsed["permissions"],
        "health": {"mode": "supervisor_process_evidence", "last_at": None},
        "notification": None,
        "handoffs_started": 0,
        "stages": [snapshot_stage(root, stage, run_dir) for stage in parsed["stages"]],
    }


def write_runtime(run_dir: Path, runtime: dict[str, Any]) -> None:
    write_json(run_dir / "run.json", runtime)


def launch_command(command: dict[str, Any], stdout_log: Path, stderr_log: Path) -> tuple[subprocess.Popen[bytes], Any, Any]:
    env = os.environ.copy()
    env.update(command["env"])
    stdout_handle = stdout_log.open("ab")
    stderr_handle = stderr_log.open("ab")
    try:
        process = subprocess.Popen(
            command["argv"], cwd=command["cwd"], env=env, stdout=stdout_handle, stderr=stderr_handle, start_new_session=True
        )
    except Exception:
        stdout_handle.close()
        stderr_handle.close()
        raise
    return process, stdout_handle, stderr_handle


def cancel_requested(run_dir: Path) -> bool:
    control_path = run_dir / "control.json"
    if not control_path.exists():
        return False
    try:
        control = read_json(control_path)
    except ContractError:
        return False
    return control.get("action") == "cancel"


def terminate_process(process: subprocess.Popen[bytes], grace_seconds: float) -> int:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            process.terminate()
        try:
            return process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                process.kill()
    return process.wait()


def failure_fingerprint(root: Path, stage_runtime: dict[str, Any], reason: str) -> str:
    stderr_log = root / stage_runtime["logs"]["stderr"]
    evidence = log_evidence(stderr_log)
    material = json.dumps({"reason": reason, "exit_code": (stage_runtime.get("process") or {}).get("exit_code"), "stderr": evidence.get("tail_sha256")}, sort_keys=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def record_terminal(runtime: dict[str, Any], run_dir: Path, status: str, *, stage_id: str, reason: str) -> None:
    runtime["status"] = status
    runtime["finished_at"] = now_utc()
    runtime["notification"] = {"kind": "terminal", "status": status, "reason": reason, "at": runtime["finished_at"]}
    append_event(run_dir / "events.jsonl", "run_terminal", stage_id=stage_id, details={"status": status, "reason": reason})
    append_event(run_dir / "events.jsonl", "notification_required", stage_id=stage_id, details=runtime["notification"])
    write_runtime(run_dir, runtime)


def run_command(
    root: Path,
    run_dir: Path,
    runtime: dict[str, Any],
    stage: dict[str, Any],
    stage_runtime: dict[str, Any],
    command: dict[str, Any],
    event_prefix: str,
    limits: dict[str, Any],
    run_started_monotonic: float,
) -> int:
    stdout_log = root / stage_runtime["logs"]["stdout"]
    stderr_log = root / stage_runtime["logs"]["stderr"]
    append_event(run_dir / "events.jsonl", f"{event_prefix}_started", stage_id=stage["id"], details={"argv": command["argv"]})
    process, stdout_handle, stderr_handle = launch_command(command, stdout_log, stderr_log)
    started_at = now_utc()
    identity = process_identity(process.pid)
    if event_prefix == "stage":
        stage_runtime["status"] = "running"
        stage_runtime["attempts_started"] += 1
        stage_runtime["process"] = {"pid": process.pid, "started_at": started_at, "identity": identity, "exit_code": None, "ended_at": None}
    write_runtime(run_dir, runtime)
    try:
        if event_prefix != "stage":
            exit_code = process.wait()
        else:
            stage_started_monotonic = time.monotonic()
            stage_deadline = stage.get("deadline_seconds")
            while True:
                try:
                    exit_code = process.wait(timeout=limits["health_interval_seconds"])
                    break
                except subprocess.TimeoutExpired:
                    elapsed = time.monotonic() - stage_started_monotonic
                    run_elapsed = time.monotonic() - run_started_monotonic
                    stop_reason = None
                    if cancel_requested(run_dir):
                        stop_reason = "cancel_requested"
                    elif stage_deadline is not None and elapsed >= stage_deadline:
                        stop_reason = "stage_deadline_exceeded"
                    elif limits["max_run_seconds"] is not None and run_elapsed >= limits["max_run_seconds"]:
                        stop_reason = "run_deadline_exceeded"
                    if stop_reason:
                        exit_code = terminate_process(process, limits["terminate_grace_seconds"])
                        stage_runtime["process"]["exit_code"] = exit_code
                        stage_runtime["process"]["ended_at"] = now_utc()
                        append_event(run_dir / "events.jsonl", "stage_stopped", stage_id=stage["id"], details={"reason": stop_reason, "exit_code": exit_code})
                        write_runtime(run_dir, runtime)
                        raise ManagedStop(stop_reason)
                    health = {
                        "at": now_utc(),
                        "pid": process.pid,
                        "identity": process_identity(process.pid),
                        "stdout": log_evidence(stdout_log),
                        "stderr": log_evidence(stderr_log),
                        "stage_elapsed_seconds": round(elapsed, 3),
                        "run_elapsed_seconds": round(run_elapsed, 3),
                    }
                    stage_runtime["health"] = health
                    runtime["health"]["last_at"] = health["at"]
                    append_event(run_dir / "events.jsonl", "stage_health_observed", stage_id=stage["id"], details=health)
                    write_runtime(run_dir, runtime)
    finally:
        stdout_handle.close()
        stderr_handle.close()
    ended_at = now_utc()
    append_event(run_dir / "events.jsonl", f"{event_prefix}_exited", stage_id=stage["id"], details={"exit_code": exit_code})
    if event_prefix == "stage":
        stage_runtime["status"] = "exited"
        stage_runtime["process"]["exit_code"] = exit_code
        stage_runtime["process"]["ended_at"] = ended_at
    else:
        stage_runtime["verifier"]["exit_code"] = exit_code
    write_runtime(run_dir, runtime)
    return exit_code


def run_contract(root: Path, contract_path: Path, requested_run_id: str | None) -> int:
    root = root.resolve()
    contract_path = contract_path.resolve() if contract_path.is_absolute() else (root / contract_path).resolve()
    try:
        contract_path.relative_to(root)
    except ValueError as exc:
        raise ContractError("contract path must remain inside repo root") from exc
    parsed = parse_contract(root, contract_path)
    run_id = requested_run_id or f"{parsed['id']}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    require_id(run_id, "run_id")
    run_dir = root / ".codex" / "runs" / run_id
    if run_dir.exists():
        raise ContractError(f"run directory already exists: {relative_to_root(root, run_dir)}")
    (run_dir / "logs").mkdir(parents=True)
    runtime = build_runtime(root, contract_path, parsed, run_id, run_dir)
    write_runtime(run_dir, runtime)
    append_event(run_dir / "events.jsonl", "run_started", details={"contract_id": parsed["id"]})
    run_started_monotonic = time.monotonic()

    if len(parsed["stages"]) != len(runtime["stages"]):
        raise RuntimeError("runtime stage count does not match the run contract")
    for stage, stage_runtime in zip(parsed["stages"], runtime["stages"]):
        try:
            stage_exit = run_command(root, run_dir, runtime, stage, stage_runtime, stage, "stage", parsed["limits"], run_started_monotonic)
        except ManagedStop as exc:
            stage_runtime["status"] = "cancelled" if exc.reason == "cancel_requested" else "unknown_recovery_needed"
            stage_runtime["failure_reason"] = exc.reason
            stage_runtime["failure_fingerprint"] = failure_fingerprint(root, stage_runtime, exc.reason)
            record_terminal(runtime, run_dir, "cancelled" if exc.reason == "cancel_requested" else "unknown_recovery_needed", stage_id=stage["id"], reason=exc.reason)
            return 1
        except OSError as exc:
            stage_runtime["status"] = "failed"
            stage_runtime["failure_reason"] = f"launch_error:{exc.__class__.__name__}"
            append_event(run_dir / "events.jsonl", "stage_failed", stage_id=stage["id"], details={"reason": stage_runtime["failure_reason"]})
            stage_runtime["failure_fingerprint"] = failure_fingerprint(root, stage_runtime, stage_runtime["failure_reason"])
            record_terminal(runtime, run_dir, "failed", stage_id=stage["id"], reason=stage_runtime["failure_reason"])
            return 1
        if stage_exit != 0:
            stage_runtime["status"] = "failed"
            stage_runtime["failure_reason"] = "command_failed"
            append_event(run_dir / "events.jsonl", "stage_failed", stage_id=stage["id"], details={"reason": "command_failed"})
            stage_runtime["failure_fingerprint"] = failure_fingerprint(root, stage_runtime, "command_failed")
            record_terminal(runtime, run_dir, "failed", stage_id=stage["id"], reason="command_failed")
            return 1

        stage_runtime["status"] = "verifying"
        write_runtime(run_dir, runtime)
        try:
            verifier_exit = run_command(root, run_dir, runtime, stage, stage_runtime, stage["verifier"], "verifier", parsed["limits"], run_started_monotonic)
        except OSError as exc:
            stage_runtime["status"] = "failed"
            stage_runtime["failure_reason"] = f"verifier_launch_error:{exc.__class__.__name__}"
            append_event(run_dir / "events.jsonl", "stage_failed", stage_id=stage["id"], details={"reason": stage_runtime["failure_reason"]})
            stage_runtime["failure_fingerprint"] = failure_fingerprint(root, stage_runtime, stage_runtime["failure_reason"])
            record_terminal(runtime, run_dir, "failed", stage_id=stage["id"], reason=stage_runtime["failure_reason"])
            return 1
        if verifier_exit != 0:
            stage_runtime["status"] = "failed"
            stage_runtime["failure_reason"] = "verifier_failed"
            append_event(run_dir / "events.jsonl", "stage_failed", stage_id=stage["id"], details={"reason": "verifier_failed"})
            stage_runtime["failure_fingerprint"] = failure_fingerprint(root, stage_runtime, "verifier_failed")
            record_terminal(runtime, run_dir, "failed", stage_id=stage["id"], reason="verifier_failed")
            return 1

        stage_runtime["status"] = "completed"
        append_event(run_dir / "events.jsonl", "stage_completed", stage_id=stage["id"])
        write_runtime(run_dir, runtime)

    record_terminal(runtime, run_dir, "completed", stage_id=runtime["stages"][-1]["id"], reason="all_stages_verified")
    print(json.dumps({"run_id": run_id, "status": runtime["status"], "run_path": relative_to_root(root, run_dir)}, ensure_ascii=False))
    return 0


def run_directory(root: Path, run_id: str) -> Path:
    require_id(run_id, "run_id")
    return root.resolve() / ".codex" / "runs" / run_id


def show_run(root: Path, run_id: str) -> int:
    runtime = read_json(run_directory(root, run_id) / "run.json")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0


def cancel_run(root: Path, run_id: str) -> int:
    run_dir = run_directory(root, run_id)
    runtime = read_json(run_dir / "run.json")
    if runtime.get("status") != "running":
        raise ContractError(f"run {run_id} is not running")
    write_json(run_dir / "control.json", {"schema_version": "cw-run-control/v1", "action": "cancel", "requested_at": now_utc()})
    append_event(run_dir / "events.jsonl", "cancel_requested")
    print(json.dumps({"run_id": run_id, "status": "cancel_requested"}, ensure_ascii=False))
    return 0


def recover_run(root: Path, run_id: str) -> int:
    run_dir = run_directory(root, run_id)
    runtime = read_json(run_dir / "run.json")
    if runtime.get("status") != "running":
        print(json.dumps({"run_id": run_id, "status": runtime.get("status"), "action": "none"}, ensure_ascii=False))
        return 0
    running = next((stage for stage in runtime.get("stages", []) if stage.get("status") == "running"), None)
    if running is None or not isinstance(running.get("process"), dict):
        raise ContractError(f"running run {run_id} has no managed stage process")
    process = running["process"]
    observed = process_identity_matches(process.get("pid"), process.get("identity", {})) if isinstance(process.get("pid"), int) else False
    if observed is True:
        print(json.dumps({"run_id": run_id, "status": "running_observed", "action": "supervisor_must_continue"}, ensure_ascii=False))
        return 0
    reason = "process_identity_unverifiable" if observed is None else "managed_process_missing_or_mismatched"
    running["status"] = "unknown_recovery_needed"
    running["failure_reason"] = reason
    running["failure_fingerprint"] = failure_fingerprint(root.resolve(), running, reason)
    record_terminal(runtime, run_dir, "unknown_recovery_needed", stage_id=running["id"], reason=reason)
    print(json.dumps({"run_id": run_id, "status": "unknown_recovery_needed", "action": "human_or_fresh_agent_recovery_required"}, ensure_ascii=False))
    return 1


def handoff_path(root: Path, handoff_id: str) -> Path:
    require_id(handoff_id, "handoff_id")
    return root.resolve() / ".codex" / "handoffs" / f"{handoff_id}.json"


def create_handoff(
    root: Path,
    run_id: str,
    spec_path_value: str,
    next_action: str,
    allowed_files: list[str],
    checkpoint_refs: list[str],
    requested_handoff_id: str | None,
    final_review_required: bool,
) -> tuple[Path, dict[str, Any]]:
    root = root.resolve()
    run_dir = run_directory(root, run_id)
    runtime = read_json(run_dir / "run.json")
    if runtime.get("status") != "completed":
        raise ContractError(f"handoff requires a completed run, got {runtime.get('status')}")
    limit = runtime.get("limits", {}).get("max_handoffs", 0)
    if not isinstance(limit, int) or runtime.get("handoffs_started", 0) >= limit:
        raise ContractError("handoff limit reached; increase limits.max_handoffs in a new run contract")
    if not isinstance(next_action, str) or not next_action.strip():
        raise ContractError("next_action must be non-empty")
    if not allowed_files or not checkpoint_refs:
        raise ContractError("handoff requires at least one allowed file and checkpoint reference")
    spec_path = repo_path(root, spec_path_value, "spec_path")
    if not spec_path.is_file():
        raise ContractError(f"spec_path is not a file: {spec_path_value}")
    ref_records = []
    for ref in checkpoint_refs:
        path = repo_path(root, ref, "checkpoint_ref")
        if not path.is_file():
            raise ContractError(f"checkpoint_ref is not a file: {ref}")
        ref_records.append({"path": relative_to_root(root, path), "sha256": sha256_file(path)})
    allowed_records = [relative_to_root(root, repo_path(root, item, "allowed_file")) for item in allowed_files]
    handoff_id = requested_handoff_id or f"{run_id}-handoff-{uuid.uuid4().hex[:8]}"
    require_id(handoff_id, "handoff_id")
    target = handoff_path(root, handoff_id)
    if target.exists():
        raise ContractError(f"handoff already exists: {relative_to_root(root, target)}")
    completed_stages = [stage["id"] for stage in runtime.get("stages", []) if stage.get("status") == "completed"]
    package = {
        "schema_version": "cw-handoff/v1",
        "id": handoff_id,
        "created_at": now_utc(),
        "status": "ready",
        "run_id": run_id,
        "spec_path": relative_to_root(root, spec_path),
        "verified_stage_ids": completed_stages,
        "checkpoint_refs": ref_records,
        "allowed_files": sorted(set(allowed_records)),
        "next_action": next_action.strip(),
        "evidence": {
            "run_snapshot": relative_to_root(root, run_dir / "run.json"),
            "event_log": runtime.get("event_log"),
            "stage_logs": [stage.get("logs") for stage in runtime.get("stages", []) if stage.get("status") == "completed"],
        },
        "final_review_required": final_review_required,
        "bridge": None,
        "review": None,
    }
    write_json(target, package)
    runtime["handoffs_started"] = runtime.get("handoffs_started", 0) + 1
    runtime.setdefault("handoff_ids", []).append(handoff_id)
    append_event(run_dir / "events.jsonl", "handoff_created", details={"handoff_id": handoff_id, "final_review_required": final_review_required})
    write_runtime(run_dir, runtime)
    return target, package


def bridge_prompt(root: Path, package_path: Path) -> str:
    return (
        "Take over the continuous-work task from the durable handoff at "
        f"{relative_to_root(root, package_path)}. Verify its listed evidence before acting. "
        "Do not assume or request prior chat context. Follow only the package's next_action, "
        "allowed_files, and final-review requirement."
    )


def launch_handoff(root: Path, handoff_id: str, codex_bin: str) -> int:
    root = root.resolve()
    package_path = handoff_path(root, handoff_id)
    package = read_json(package_path)
    if package.get("schema_version") != "cw-handoff/v1" or package.get("status") != "ready":
        raise ContractError(f"handoff {handoff_id} is not ready")
    if not isinstance(codex_bin, str) or not codex_bin:
        raise ContractError("codex_bin must be non-empty")
    bridge_path = package_path.with_suffix(".bridge.json")
    if bridge_path.exists():
        raise ContractError(f"handoff bridge already exists: {relative_to_root(root, bridge_path)}")
    stdout_path = package_path.with_suffix(".bridge.stdout.log")
    stderr_path = package_path.with_suffix(".bridge.stderr.log")
    argv = [codex_bin, "exec", "-C", str(root), bridge_prompt(root, package_path)]
    stdout_handle = stdout_path.open("ab")
    stderr_handle = stderr_path.open("ab")
    try:
        process = subprocess.Popen(argv, cwd=root, stdout=stdout_handle, stderr=stderr_handle, start_new_session=True)
    except OSError:
        stdout_handle.close()
        stderr_handle.close()
        raise
    bridge = {
        "schema_version": "cw-bridge-run/v1",
        "handoff_id": handoff_id,
        "status": "running",
        "argv": argv,
        "process": {"pid": process.pid, "started_at": now_utc(), "identity": process_identity(process.pid), "exit_code": None, "ended_at": None},
        "logs": {"stdout": relative_to_root(root, stdout_path), "stderr": relative_to_root(root, stderr_path)},
    }
    write_json(bridge_path, bridge)
    try:
        exit_code = process.wait()
    finally:
        stdout_handle.close()
        stderr_handle.close()
    bridge["status"] = "completed" if exit_code == 0 else "failed"
    bridge["process"]["exit_code"] = exit_code
    bridge["process"]["ended_at"] = now_utc()
    write_json(bridge_path, bridge)
    package["bridge"] = {"path": relative_to_root(root, bridge_path), "status": bridge["status"], "completed_at": bridge["process"]["ended_at"]}
    package["status"] = "bridge_completed" if exit_code == 0 else "bridge_failed"
    write_json(package_path, package)
    print(json.dumps({"handoff_id": handoff_id, "status": package["status"], "bridge_path": relative_to_root(root, bridge_path)}, ensure_ascii=False))
    return 0 if exit_code == 0 else 1


def request_handoff_review(root: Path, handoff_id: str, summary: str) -> int:
    root = root.resolve()
    package_path = handoff_path(root, handoff_id)
    package = read_json(package_path)
    if not package.get("final_review_required"):
        raise ContractError(f"handoff {handoff_id} does not require final review")
    if package.get("status") not in {"ready", "bridge_completed"}:
        raise ContractError(f"handoff {handoff_id} cannot enter review from {package.get('status')}")
    if not isinstance(summary, str) or not summary.strip():
        raise ContractError("review summary must be non-empty")
    package["status"] = "waiting_human_final_review"
    package["review"] = {"requested_at": now_utc(), "summary": summary.strip()}
    write_json(package_path, package)
    print(json.dumps({"handoff_id": handoff_id, "status": package["status"]}, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="continuous-work v2 Phase B portable supervisor")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="run a serial contract in the foreground")
    run_parser.add_argument("--root", default=".", help="repo root")
    run_parser.add_argument("--run-id", help="optional deterministic run id")
    run_parser.add_argument("contract", help="repo-relative path to a cw-run-contract/v1 JSON file")
    for command, help_text in [("run-status", "show a run snapshot"), ("run-cancel", "request cooperative cancellation"), ("run-recover", "diagnose a stopped supervisor/run")]:
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("--root", default=".", help="repo root")
        command_parser.add_argument("run_id", help="run id")
    handoff_create_parser = subparsers.add_parser("handoff-create", help="create a durable handoff from a completed run")
    handoff_create_parser.add_argument("--root", default=".", help="repo root")
    handoff_create_parser.add_argument("--run-id", required=True)
    handoff_create_parser.add_argument("--spec-path", required=True)
    handoff_create_parser.add_argument("--next-action", required=True)
    handoff_create_parser.add_argument("--allowed-file", action="append", required=True)
    handoff_create_parser.add_argument("--checkpoint-ref", action="append", required=True)
    handoff_create_parser.add_argument("--handoff-id")
    handoff_create_parser.add_argument("--final-review", action="store_true")
    handoff_launch_parser = subparsers.add_parser("handoff-launch", help="launch a fresh Codex CLI invocation from a handoff")
    handoff_launch_parser.add_argument("--root", default=".", help="repo root")
    handoff_launch_parser.add_argument("--codex-bin", default="codex")
    handoff_launch_parser.add_argument("handoff_id")
    handoff_review_parser = subparsers.add_parser("handoff-review", help="request the final human review for a handoff")
    handoff_review_parser.add_argument("--root", default=".", help="repo root")
    handoff_review_parser.add_argument("--summary", required=True)
    handoff_review_parser.add_argument("handoff_id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "run":
            return run_contract(Path(args.root), Path(args.contract), args.run_id)
        if args.command == "run-status":
            return show_run(Path(args.root), args.run_id)
        if args.command == "run-cancel":
            return cancel_run(Path(args.root), args.run_id)
        if args.command == "run-recover":
            return recover_run(Path(args.root), args.run_id)
        if args.command == "handoff-create":
            package_path, package = create_handoff(
                Path(args.root), args.run_id, args.spec_path, args.next_action, args.allowed_file, args.checkpoint_ref, args.handoff_id, args.final_review
            )
            print(json.dumps({"handoff_id": package["id"], "status": package["status"], "handoff_path": relative_to_root(Path(args.root).resolve(), package_path)}, ensure_ascii=False))
            return 0
        if args.command == "handoff-launch":
            return launch_handoff(Path(args.root), args.handoff_id, args.codex_bin)
        return request_handoff_review(Path(args.root), args.handoff_id, args.summary)
    except ContractError as exc:
        print(f"cw supervisor: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
