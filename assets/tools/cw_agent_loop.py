#!/usr/bin/env python3
"""Bounded, foreground Codex repair loop for continuous-work v3."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from cw_supervisor import (
    ContractError,
    append_event,
    cancel_run,
    now_utc,
    parse_contract,
    process_identity,
    process_identity_matches,
    read_json,
    relative_to_root,
    run_contract,
    sha256_file,
    write_json,
)


LOOP_SCHEMA = "cw-agent-loop/v1"
CASE_SCHEMA = "cw-repair-case/v1"
DECISION_SCHEMA = "cw-repair-decision/v1"


def require_id(value: str, label: str) -> str:
    if not value or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-" for char in value):
        raise ContractError(f"{label} must contain only letters, numbers, dot, underscore, or hyphen")
    return value


def loop_path(root: Path, loop_id: str) -> Path:
    return root.resolve() / ".codex" / "agent-loops" / require_id(loop_id, "loop_id")


def run_git(root: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(root), *args], check=False, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise ContractError(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result


def ensure_clean_git(root: Path) -> None:
    if run_git(root, ["rev-parse", "--is-inside-work-tree"], check=False).stdout.strip() != "true":
        raise ContractError("agent_loop requires a Git worktree")
    if run_git(root, ["status", "--porcelain"]).stdout.strip():
        raise ContractError("agent_loop.require_clean_git requires a clean worktree before loop start")


def write_loop(loop_dir: Path, loop: dict[str, Any]) -> None:
    write_json(loop_dir / "loop.json", loop)


def event(loop_dir: Path, name: str, details: dict[str, Any] | None = None) -> None:
    append_event(loop_dir / "events.jsonl", name, details=details)


def terminal(loop_dir: Path, loop: dict[str, Any], status: str, reason: str) -> int:
    loop["status"] = status
    loop["finished_at"] = now_utc()
    loop["terminal_reason"] = reason
    event(loop_dir, "loop_terminal", {"status": status, "reason": reason})
    write_loop(loop_dir, loop)
    print(json.dumps({"loop_id": loop["id"], "status": status, "reason": reason}, ensure_ascii=False))
    return 0 if status == "completed" else 1


def copied_path(root: Path, worktree: Path, relative_path: str) -> None:
    source = root / relative_path
    target = worktree / relative_path
    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def create_worktree(root: Path, loop_dir: Path, loop: dict[str, Any], policy: dict[str, Any], case_id: str, contract_path: Path) -> Path:
    worktree = root.parent / ".cw-agent-worktrees" / root.name / loop["id"] / case_id
    run_git(root, ["worktree", "add", "--detach", str(worktree), "HEAD"])
    for relative_path in policy["allowed_files"]:
        copied_path(root, worktree, relative_path)
    copied_path(root, worktree, relative_to_root(root, contract_path))
    return worktree


def path_under(relative_path: str, roots: list[str]) -> bool:
    return any(relative_path == root or relative_path.startswith(root.rstrip("/") + "/") for root in roots)


def command_signature(root: Path, command: dict[str, Any]) -> dict[str, Any]:
    return {"argv": command["argv"], "cwd": relative_to_root(root, command["cwd"]), "env": command["env"]}


def same_execution_surface(root: Path, original: dict[str, Any], candidate_root: Path, candidate: dict[str, Any]) -> bool:
    before_permissions = original["permissions"]
    after_permissions = candidate["permissions"]
    if before_permissions["network"] != after_permissions["network"] or before_permissions["credentials"] != after_permissions["credentials"]:
        return False
    if not set(after_permissions["path_roots"]).issubset(before_permissions["path_roots"]):
        return False
    before_limits = original["limits"]
    after_limits = candidate["limits"]
    for key in ("max_run_seconds", "max_stage_attempts", "max_handoffs"):
        before_value = before_limits[key]
        after_value = after_limits[key]
        if before_value is not None and (after_value is None or after_value > before_value):
            return False
    if before_limits["health_interval_seconds"] != after_limits["health_interval_seconds"]:
        return False
    if after_limits["terminate_grace_seconds"] > before_limits["terminate_grace_seconds"]:
        return False
    before_policy = original.get("agent_loop") or {}
    after_policy = candidate.get("agent_loop") or {}
    if before_policy.get("mode") == "assisted" and after_policy.get("mode") == "unattended":
        return False
    if not set(after_policy.get("repair_on", [])).issubset(before_policy.get("repair_on", [])):
        return False
    if after_policy.get("max_repair_turns", 0) > before_policy.get("max_repair_turns", 0):
        return False
    if after_policy.get("max_total_agent_seconds", 0) > before_policy.get("max_total_agent_seconds", 0):
        return False
    if not set(after_policy.get("allowed_files", [])).issubset(before_policy.get("allowed_files", [])):
        return False
    if not set(after_policy.get("allowed_contract_roots", [])).issubset(before_policy.get("allowed_contract_roots", [])):
        return False
    if after_policy.get("repair_execution_policy") != before_policy.get("repair_execution_policy"):
        return False
    if before_policy.get("require_clean_git") and not after_policy.get("require_clean_git"):
        return False
    if len(original["stages"]) != len(candidate["stages"]):
        return False
    for before, after in zip(original["stages"], candidate["stages"]):
        if before["id"] != after["id"]:
            return False
        before_stage = command_signature(root, before)
        after_stage = command_signature(candidate_root, after)
        before_verifier = command_signature(root, before["verifier"])
        after_verifier = command_signature(candidate_root, after["verifier"])
        before_deadline = before["deadline_seconds"]
        after_deadline = after["deadline_seconds"]
        if before_stage != after_stage or before_verifier != after_verifier or (before_deadline is not None and (after_deadline is None or after_deadline > before_deadline)):
            return False
    return True


def worker_prompt(case_relative: str, decision_relative: str) -> str:
    return (
        f"Read the bounded repair case at {case_relative}. Verify its evidence before acting. "
        "Work only on the listed allowlisted files. Do not change stage/verifier argv, permissions, deadlines, budgets, credentials, or network policy. "
        "This is a linked Git worktree: use sandboxed shell commands from the working directory for allowed writes, not the Codex patch tool, which can reject linked-worktree paths. "
        f"Write exactly one JSON decision conforming to decision_requirements at {decision_relative}. "
        "Choose propose_repair only when a new contract and deterministic checks can prove a bounded retry is appropriate; otherwise choose escalate."
    )


def materialize_worker_case(root: Path, worktree: Path, case: dict[str, Any], case_relative: str, decision_relative: str, staged_contract_relative: str) -> dict[str, Any]:
    evidence_dir = f".codex/agent-loop-evidence/{case['id']}"
    source_evidence = case["evidence"]
    targets = {
        "run_snapshot": f"{evidence_dir}/run.json",
        "stdout": f"{evidence_dir}/stage.stdout.log",
        "stderr": f"{evidence_dir}/stage.stderr.log",
    }
    source_paths = {
        "run_snapshot": source_evidence["run_snapshot"],
        "stdout": source_evidence["logs"]["stdout"],
        "stderr": source_evidence["logs"]["stderr"],
    }
    for key, source_relative in source_paths.items():
        source = root / source_relative
        if not source.is_file():
            raise ContractError(f"repair evidence is missing: {source_relative}")
        target = worktree / targets[key]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    worker_case = json.loads(json.dumps(case))
    worker_case["evidence"] = {
        "run_snapshot": targets["run_snapshot"],
        "logs": {"stdout": targets["stdout"], "stderr": targets["stderr"]},
    }
    worker_case["decision_requirements"] = {
        "schema_version": DECISION_SCHEMA,
        "case_id": case["id"],
        "failure_fingerprint": case["failure_fingerprint"],
        "write_path": decision_relative,
        "staged_replacement_contract_path": staged_contract_relative,
        "valid_decisions": ["propose_repair", "escalate"],
        "propose_repair_required_fields": ["replacement_contract", "changed_files", "candidate_check_ids"],
        "escalate_required_fields": ["reason"],
        "candidate_check_ids": [check["id"] for check in case["authority"]["candidate_checks"]],
    }
    return worker_case


def wait_worker(process: subprocess.Popen[bytes], loop_dir: Path, loop: dict[str, Any], timeout_seconds: float) -> tuple[int, str | None]:
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None:
        control = loop_dir / "control.json"
        if control.exists() and read_json(control).get("action") == "cancel":
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return process.wait(timeout=5), "cancel_requested"
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return process.wait(), "cancel_requested"
        if time.monotonic() >= deadline:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return process.wait(timeout=5), "worker_deadline_exceeded"
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return process.wait(), "worker_deadline_exceeded"
        time.sleep(0.1)
    return process.returncode, None


def start_worker(root: Path, loop_dir: Path, loop: dict[str, Any], policy: dict[str, Any], case: dict[str, Any], worktree: Path, codex_bin: str) -> tuple[dict[str, Any], Path]:
    case_relative = f".codex/agent-loop-cases/{case['id']}.json"
    worker_output_dir = f"cw-agent-output/{case['id']}"
    decision_relative = f"{worker_output_dir}/decision.json"
    staged_contract_relative = f"{worker_output_dir}/replacement-contract.json"
    case_path = worktree / case_relative
    decision_path = worktree / decision_relative
    write_json(case_path, materialize_worker_case(root, worktree, case, case_relative, decision_relative, staged_contract_relative))
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path = loop_dir / "logs" / f"{case['id']}.stdout.log"
    stderr_path = loop_dir / "logs" / f"{case['id']}.stderr.log"
    stdout_handle = stdout_path.open("ab")
    stderr_handle = stderr_path.open("ab")
    # The worker writes only to this detached candidate worktree; it must not inherit a global read-only default.
    argv = [codex_bin, "exec", "--sandbox", "workspace-write", "--add-dir", str(worktree), "-C", str(worktree), worker_prompt(case_relative, decision_relative)]
    env = os.environ.copy()
    env.update({"CW_AGENT_LOOP_CASE": str(case_path), "CW_AGENT_LOOP_DECISION": str(decision_path), "CW_AGENT_LOOP_STAGED_CONTRACT": str(worktree / staged_contract_relative)})
    try:
        process = subprocess.Popen(argv, cwd=worktree, env=env, stdout=stdout_handle, stderr=stderr_handle, start_new_session=True)
    except OSError as exc:
        stdout_handle.close()
        stderr_handle.close()
        worker = {
            "schema_version": "cw-agent-worker/v1",
            "case_id": case["id"],
            "status": "failed",
            "argv": argv,
            "process": None,
            "logs": {"stdout": relative_to_root(root, stdout_path), "stderr": relative_to_root(root, stderr_path)},
            "failure_reason": f"worker_launch_error:{exc.__class__.__name__}",
        }
        write_json(loop_dir / "workers" / f"{case['id']}.json", worker)
        event(loop_dir, "repair_worker_failed", {"case_id": case["id"], "reason": worker["failure_reason"]})
        return worker, decision_path
    try:
        worker = {
            "schema_version": "cw-agent-worker/v1",
            "case_id": case["id"],
            "status": "running",
            "argv": argv,
            "process": {"pid": process.pid, "identity": process_identity(process.pid), "started_at": now_utc(), "exit_code": None, "ended_at": None},
            "logs": {"stdout": relative_to_root(root, stdout_path), "stderr": relative_to_root(root, stderr_path)},
            "worktree": str(worktree),
        }
        write_json(loop_dir / "workers" / f"{case['id']}.json", worker)
        event(loop_dir, "repair_worker_started", {"case_id": case["id"], "pid": process.pid})
        timeout = max(1.0, policy["max_total_agent_seconds"] - loop["agent_seconds"])
        started = time.monotonic()
        exit_code, stopped_reason = wait_worker(process, loop_dir, loop, timeout)
        loop["agent_seconds"] += round(time.monotonic() - started, 3)
    finally:
        stdout_handle.close()
        stderr_handle.close()
    worker["status"] = "completed" if exit_code == 0 and stopped_reason is None else "failed"
    worker["process"]["exit_code"] = exit_code
    worker["process"]["ended_at"] = now_utc()
    if stopped_reason:
        worker["failure_reason"] = stopped_reason
    write_json(loop_dir / "workers" / f"{case['id']}.json", worker)
    event(loop_dir, "repair_worker_exited", {"case_id": case["id"], "status": worker["status"], "exit_code": exit_code, "reason": stopped_reason})
    return worker, decision_path


def changed_paths(worktree: Path) -> list[str]:
    result = run_git(worktree, ["status", "--porcelain"])
    paths = []
    for line in result.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        if path.startswith(".codex/agent-loop-cases/") or path.startswith(".codex/agent-loop-evidence/") or path.startswith("cw-agent-output/"):
            continue
        paths.append(path)
    return sorted(set(paths))


def run_checks(worktree: Path, policy: dict[str, Any], requested: list[str]) -> None:
    known = {check["id"]: check for check in policy["candidate_checks"]}
    if sorted(set(requested)) != sorted(requested) or any(item not in known for item in requested):
        raise ContractError("repair decision names unknown or duplicate candidate check ids")
    for check_id in requested:
        check = known[check_id]
        cwd = worktree / check["cwd"]
        result = subprocess.run(check["argv"], cwd=cwd, env={**os.environ, **check["env"]}, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise ContractError(f"candidate check failed: {check_id}")


def validate_candidate(root: Path, loop_dir: Path, policy: dict[str, Any], original: dict[str, Any], case: dict[str, Any], worktree: Path, decision_path: Path) -> Path:
    if not decision_path.is_file():
        raise ContractError("repair worker did not write a decision")
    decision = read_json(decision_path)
    if decision.get("schema_version") != DECISION_SCHEMA or decision.get("case_id") != case["id"]:
        raise ContractError("repair decision schema or case id is invalid")
    if decision.get("failure_fingerprint") != case["failure_fingerprint"]:
        raise ContractError("repair decision does not match the failed evidence")
    if decision.get("decision") == "escalate":
        raise ContractError(f"worker escalated: {decision.get('reason', 'no reason supplied')}")
    if decision.get("decision") != "propose_repair":
        raise ContractError("repair decision must be propose_repair or escalate")
    replacement = decision.get("replacement_contract")
    if not isinstance(replacement, str) or not path_under(replacement, policy["allowed_contract_roots"]):
        raise ContractError("replacement contract is outside allowed contract roots")
    expected_staged_contract = f"cw-agent-output/{case['id']}/replacement-contract.json"
    if decision.get("staged_replacement_contract_path") != expected_staged_contract:
        raise ContractError("repair decision does not identify the required staged replacement contract")
    staged_contract = worktree / expected_staged_contract
    if not staged_contract.is_file():
        raise ContractError("repair worker did not write the staged replacement contract")
    candidate_contract = (worktree / replacement).resolve()
    try:
        candidate_contract.relative_to(worktree)
    except ValueError as exc:
        raise ContractError("replacement contract escapes repair worktree") from exc
    candidate_contract.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staged_contract, candidate_contract)
    run_git(worktree, ["add", "-N", replacement])
    paths = changed_paths(worktree)
    declared = decision.get("changed_files")
    if not isinstance(declared, list) or sorted(set(declared)) != paths:
        raise ContractError("repair decision changed_files does not match candidate diff")
    if not paths or any(path not in policy["allowed_files"] and path != replacement for path in paths):
        raise ContractError("candidate diff touches files outside agent_loop.allowed_files")
    candidate = parse_contract(worktree, candidate_contract)
    if not same_execution_surface(root, original, worktree, candidate):
        raise ContractError("candidate changes the protected execution surface")
    requested_checks = decision.get("candidate_check_ids", [])
    if not isinstance(requested_checks, list) or not all(isinstance(item, str) for item in requested_checks):
        raise ContractError("repair decision candidate_check_ids must be a string array")
    run_checks(worktree, policy, requested_checks)
    patch = run_git(worktree, ["diff", "--binary"]).stdout
    if not patch.strip():
        raise ContractError("candidate has no applicable patch")
    patch_path = loop_dir / "patches" / f"{case['id']}.patch"
    patch_path.write_text(patch, encoding="utf-8")
    write_json(loop_dir / "decisions" / f"{case['id']}.json", {"decision": decision, "validated_at": now_utc(), "changed_files": paths, "patch": relative_to_root(root, patch_path)})
    return root / replacement


def create_case(root: Path, loop_dir: Path, loop: dict[str, Any], runtime: dict[str, Any], contract_path: Path, attempt: int) -> dict[str, Any]:
    failed = next((stage for stage in runtime["stages"] if stage.get("status") == "failed"), None)
    if failed is None or not failed.get("failure_fingerprint"):
        raise ContractError("failed run has no repairable stage fingerprint")
    case_id = f"repair-{attempt:03d}"
    case = {
        "schema_version": CASE_SCHEMA,
        "id": case_id,
        "created_at": now_utc(),
        "loop_id": loop["id"],
        "run_id": runtime["run_id"],
        "contract_path": relative_to_root(root, contract_path),
        "contract_sha256": sha256_file(contract_path),
        "stage_id": failed["id"],
        "failure_reason": failed["failure_reason"],
        "failure_fingerprint": failed["failure_fingerprint"],
        "evidence": {"run_snapshot": relative_to_root(root, root / ".codex" / "runs" / runtime["run_id"] / "run.json"), "logs": failed["logs"]},
        "authority": loop["policy"],
    }
    write_json(loop_dir / "cases" / f"{case_id}.json", case)
    event(loop_dir, "repair_case_created", {"case_id": case_id, "run_id": runtime["run_id"], "failure_fingerprint": failed["failure_fingerprint"]})
    return case


def run_loop(root: Path, contract_value: str, requested_loop_id: str | None, codex_bin: str) -> int:
    root = root.resolve()
    contract_path = (root / contract_value).resolve() if not Path(contract_value).is_absolute() else Path(contract_value).resolve()
    try:
        contract_path.relative_to(root)
    except ValueError as exc:
        raise ContractError("contract path must remain inside repo root") from exc
    original = parse_contract(root, contract_path)
    policy = original.get("agent_loop")
    if policy is None:
        raise ContractError("cw loop requires an opt-in cw-run-contract/v2 agent_loop policy")
    if policy["require_clean_git"]:
        ensure_clean_git(root)
    loop_id = requested_loop_id or f"{original['id']}-loop-{uuid.uuid4().hex[:8]}"
    require_id(loop_id, "loop_id")
    loop_dir = loop_path(root, loop_id)
    if loop_dir.exists():
        raise ContractError("loop directory already exists")
    for name in ("cases", "workers", "decisions", "patches", "logs", "worktrees"):
        (loop_dir / name).mkdir(parents=True, exist_ok=True)
    loop = {
        "schema_version": LOOP_SCHEMA,
        "id": loop_id,
        "status": "running",
        "started_at": now_utc(),
        "finished_at": None,
        "terminal_reason": None,
        "process": {"pid": os.getpid(), "identity": process_identity(os.getpid())},
        "contract_path": relative_to_root(root, contract_path),
        "contract_sha256": sha256_file(contract_path),
        "policy": policy,
        "run_ids": [],
        "repair_fingerprints": [],
        "repair_turns": 0,
        "agent_seconds": 0.0,
        "current_run_id": None,
        "current_case_id": None,
    }
    write_loop(loop_dir, loop)
    event(loop_dir, "loop_started", {"contract": loop["contract_path"]})
    current_contract = contract_path
    current_parsed = original
    run_index = 1
    while True:
        run_id = f"{loop_id}-run-{run_index}"
        loop["current_run_id"] = run_id
        loop["current_case_id"] = None
        loop["run_ids"].append(run_id)
        write_loop(loop_dir, loop)
        event(loop_dir, "replacement_run_started" if run_index > 1 else "run_started", {"run_id": run_id})
        run_contract(root, current_contract, run_id)
        runtime = read_json(root / ".codex" / "runs" / run_id / "run.json")
        if runtime["status"] == "completed":
            return terminal(loop_dir, loop, "waiting_human_final_review" if policy["require_final_review"] else "completed", "all_stages_verified")
        if runtime["status"] == "cancelled":
            return terminal(loop_dir, loop, "cancelled", "cancel_requested")
        if runtime["status"] != "failed":
            return terminal(loop_dir, loop, "unknown_recovery_needed", f"run_terminal_{runtime['status']}")
        failed = next(stage for stage in runtime["stages"] if stage.get("status") == "failed")
        reason = failed.get("failure_reason")
        fingerprint = failed.get("failure_fingerprint")
        if reason not in policy["repair_on"]:
            return terminal(loop_dir, loop, "waiting_human", f"failure_not_repairable:{reason}")
        if fingerprint in loop["repair_fingerprints"]:
            return terminal(loop_dir, loop, "waiting_human", "repeated_failure_fingerprint")
        if loop["repair_turns"] >= policy["max_repair_turns"] or loop["agent_seconds"] >= policy["max_total_agent_seconds"]:
            return terminal(loop_dir, loop, "waiting_human", "repair_budget_exhausted")
        case = create_case(root, loop_dir, loop, runtime, current_contract, loop["repair_turns"] + 1)
        loop["current_case_id"] = case["id"]
        write_loop(loop_dir, loop)
        worktree = create_worktree(root, loop_dir, loop, policy, case["id"], current_contract)
        worker, decision_path = start_worker(root, loop_dir, loop, policy, case, worktree, codex_bin)
        loop["repair_turns"] += 1
        loop["repair_fingerprints"].append(fingerprint)
        write_loop(loop_dir, loop)
        if worker["status"] != "completed":
            return terminal(loop_dir, loop, "cancelled" if worker.get("failure_reason") == "cancel_requested" else "waiting_human", worker.get("failure_reason", "worker_failed"))
        try:
            replacement = validate_candidate(root, loop_dir, policy, current_parsed, case, worktree, decision_path)
            patch_path = loop_dir / "patches" / f"{case['id']}.patch"
            applied = subprocess.run(["git", "-C", str(root), "apply", "--whitespace=nowarn", str(patch_path)], check=False, capture_output=True, text=True)
            if applied.returncode != 0:
                raise ContractError(f"candidate patch did not apply: {applied.stderr.strip()}")
            current_contract = replacement
            current_parsed = parse_contract(root, current_contract)
            event(loop_dir, "repair_accepted", {"case_id": case["id"], "replacement_contract": relative_to_root(root, replacement)})
        except ContractError as exc:
            event(loop_dir, "repair_rejected", {"case_id": case["id"], "reason": str(exc)})
            return terminal(loop_dir, loop, "waiting_human", f"repair_rejected:{exc}")
        run_index += 1


def show_loop(root: Path, loop_id: str) -> int:
    print(json.dumps(read_json(loop_path(root, loop_id) / "loop.json"), ensure_ascii=False, indent=2))
    return 0


def recover_loop(root: Path, loop_id: str) -> int:
    path = loop_path(root, loop_id)
    loop = read_json(path / "loop.json")
    if loop.get("status") != "running":
        print(json.dumps({"loop_id": loop_id, "status": loop.get("status"), "action": "none"}, ensure_ascii=False))
        return 0
    observed = process_identity_matches(loop.get("process", {}).get("pid"), loop.get("process", {}).get("identity", {}))
    if observed is True:
        print(json.dumps({"loop_id": loop_id, "status": "running_observed", "action": "controller_must_continue"}, ensure_ascii=False))
        return 0
    loop["status"] = "unknown_recovery_needed"
    loop["finished_at"] = now_utc()
    loop["terminal_reason"] = "controller_identity_unverifiable" if observed is None else "controller_missing_or_mismatched"
    event(path, "loop_recovery_unknown", {"reason": loop["terminal_reason"]})
    write_loop(path, loop)
    print(json.dumps({"loop_id": loop_id, "status": loop["status"], "action": "human_recovery_required"}, ensure_ascii=False))
    return 1


def cancel_loop(root: Path, loop_id: str) -> int:
    path = loop_path(root, loop_id)
    loop = read_json(path / "loop.json")
    if loop.get("status") != "running":
        raise ContractError("loop is not running")
    write_json(path / "control.json", {"schema_version": "cw-agent-loop-control/v1", "action": "cancel", "requested_at": now_utc()})
    run_id = loop.get("current_run_id")
    if isinstance(run_id, str):
        run_path = root.resolve() / ".codex" / "runs" / run_id / "run.json"
        if run_path.exists() and read_json(run_path).get("status") == "running":
            cancel_run(root, run_id)
    event(path, "loop_cancel_requested")
    print(json.dumps({"loop_id": loop_id, "status": "cancel_requested"}, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="continuous-work v3 bounded agent loop")
    sub = parser.add_subparsers(dest="command", required=True)
    loop = sub.add_parser("loop", help="run an opt-in contract with bounded repair workers")
    loop.add_argument("--root", default=".")
    loop.add_argument("--loop-id")
    loop.add_argument("--codex-bin", default="codex")
    loop.add_argument("contract")
    for name in ("loop-status", "loop-recover", "loop-cancel"):
        item = sub.add_parser(name)
        item.add_argument("--root", default=".")
        item.add_argument("loop_id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "loop":
            return run_loop(Path(args.root), args.contract, args.loop_id, args.codex_bin)
        if args.command == "loop-status":
            return show_loop(Path(args.root), args.loop_id)
        if args.command == "loop-recover":
            return recover_loop(Path(args.root), args.loop_id)
        return cancel_loop(Path(args.root), args.loop_id)
    except ContractError as exc:
        print(f"cw agent loop: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
