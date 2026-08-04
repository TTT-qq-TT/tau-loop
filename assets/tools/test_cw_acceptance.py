#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


ISO_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime(ISO_UTC_FORMAT)


def stale_utc(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime(ISO_UTC_FORMAT)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_cw(script_path: Path, root: Path, *args: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    nested_commands = {"spec", "review", "worktree", "exec", "subagent", "gate", "hook"}
    if not args:
        raise AssertionError("missing cw command args")
    if args[0] in nested_commands:
        if len(args) < 2:
            raise AssertionError(f"nested command requires subcommand: {args}")
        cmd_args = [args[0], args[1], "--root", str(root), *args[2:]]
    else:
        cmd_args = [args[0], "--root", str(root), *args[1:]]
    cmd = ["python3", str(script_path), *cmd_args]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if expect_ok and result.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(cmd)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


def run_cw_json(script_path: Path, root: Path, *args: str, expect_ok: bool = True) -> dict:
    result = run_cw(script_path, root, *args, expect_ok=expect_ok)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"command did not return JSON: {' '.join(args)}\nstdout:\n{result.stdout}") from exc


def create_fixture_repo(base_dir: Path, name: str, *, active_spec_id: str = "root-spec") -> Path:
    root = base_dir / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    write_text(
        root / ".codex" / "memory.md",
        "# Memory\n\n## Current State\n\n- Fixture memory.\n",
    )
    write_text(
        root / ".codex" / "plan.md",
        "\n".join(
            [
                "# Plan",
                "",
                "## Active Task",
                "",
                "- Task: fixture acceptance",
                f"- Spec: `.codex/specs/{active_spec_id}.md`",
                "- Verification profile: `.codex/verification-profiles/code-change.md`",
                "- Phase: fixture",
                "- Owner: Codex",
                "- Status: ready",
                "- Complexity: standard",
                "",
            ]
        )
        + "\n",
    )
    write_text(
        root / ".codex" / "verification-profiles" / "code-change.md",
        "# Verification Profile: code-change\n\n- fixture profile\n",
    )
    write_text(
        root / ".codex" / "specs" / f"{active_spec_id}.md",
        "\n".join(
            [
                f"# Task Spec: {active_spec_id}",
                "",
                "- Status: ready",
                "- Owner: Codex",
                f"- Updated: {datetime.now(timezone.utc).date().isoformat()}",
                "- Related plan: `.codex/plan.md`",
                "- Verification profile: `.codex/verification-profiles/code-change.md`",
                "",
                "## 1. Goal",
                "",
                "- Fixture root spec.",
                "",
                "## 2. Non-Goals",
                "",
                "- None.",
                "",
                "## 3. References Or Prior Art",
                "",
                "- None.",
                "",
                "## 4. Allowed Files",
                "",
                "- `.codex/**`",
                "",
                "## 5. Implementation Checklist",
                "",
                "- [ ] Fixture placeholder",
                "",
                "## 6. Verification",
                "",
                "- Commands:",
                "- Manual checks:",
                "- Residual risks:",
                "",
                "## 7. Risks And Regression Points",
                "",
                "- Risk:",
                "  Why it matters:",
                "  Mitigation:",
                "",
            ]
        )
        + "\n",
    )
    return root


def create_child_spec(root: Path, spec_id: str, *, title: str | None = None) -> Path:
    path = root / ".codex" / "specs" / f"{spec_id}.md"
    write_text(
        path,
        "\n".join(
            [
                f"# Task Spec: {title or spec_id}",
                "",
                "- Status: ready",
                "- Owner: Codex",
                f"- Updated: {datetime.now(timezone.utc).date().isoformat()}",
                "- Related plan: `.codex/plan.md`",
                "- Verification profile: `.codex/verification-profiles/code-change.md`",
                "",
                "## 1. Goal",
                "",
                "- Child fixture spec.",
                "",
                "## 2. Non-Goals",
                "",
                "- None.",
                "",
                "## 3. References Or Prior Art",
                "",
                "- None.",
                "",
                "## 4. Allowed Files",
                "",
                "- `.codex/**`",
                "",
                "## 5. Implementation Checklist",
                "",
                "- [ ] Fixture placeholder",
                "",
                "## 6. Verification",
                "",
                "- Commands:",
                "- Manual checks:",
                "- Residual risks:",
                "",
                "## 7. Risks And Regression Points",
                "",
                "- Risk:",
                "  Why it matters:",
                "  Mitigation:",
                "",
            ]
        )
        + "\n",
    )
    return path


def scenario_interrupted_exec_recovery(script_path: Path, temp_root: Path) -> None:
    root = create_fixture_repo(temp_root, "interrupted-exec")
    run_cw(script_path, root, "init")
    payload = run_cw_json(script_path, root, "exec", "prepare", "root-spec")
    session_id = payload["prepared_exec"]["session_id"]
    run_cw(script_path, root, "exec", "launch", "--resume-handle", "resume-fixture-001", session_id)

    session_path = root / ".codex" / "state" / "sessions" / f"{session_id}.json"
    session = read_json(session_path)
    session["last_heartbeat_at"] = stale_utc(90)
    session["updated_at"] = now_utc()
    write_json(session_path, session)

    recover = run_cw_json(script_path, root, "recover", "--stale-minutes", "30")
    interrupted = recover["interrupted_sessions"]
    if len(interrupted) != 1:
        raise AssertionError(f"expected one interrupted session, got {interrupted}")
    if interrupted[0]["recommended_recovery"] != "exec_resume":
        raise AssertionError(f"expected exec_resume recovery, got {interrupted[0]}")

    doctor = run_cw_json(script_path, root, "doctor", "--stale-minutes", "30", expect_ok=False)
    codes = {item["code"] for item in doctor["findings"]}
    if "stale_running_session" not in codes:
        raise AssertionError(f"doctor did not flag stale_running_session: {doctor}")


def scenario_review_convergence_completion(script_path: Path, temp_root: Path) -> None:
    root = create_fixture_repo(temp_root, "review-convergence")
    create_child_spec(root, "child-spec")
    run_cw(script_path, root, "init")
    run_cw(
        script_path,
        root,
        "spec",
        "create-child",
        "--mode",
        "serial",
        "--expected-output",
        "child artifact",
        "root-spec",
        ".codex/specs/child-spec.md",
    )
    run_cw(script_path, root, "spec", "update", "--status", "blocked", "--blocked-by", "child-spec", "root-spec")
    run_cw(script_path, root, "review", "request", "--owner-spec-id", "root-spec", "--summary", "child complete", "child-spec")

    next_payload = run_cw_json(script_path, root, "next")
    if next_payload["recommended_action"]["kind"] != "converge_review_backlog":
        raise AssertionError(f"expected review backlog recommendation, got {next_payload}")

    run_cw(
        script_path,
        root,
        "review",
        "resolve",
        "--decision",
        "accepted",
        "--decided-by",
        "fixture",
        "--summary",
        "accepted child result",
        "child-spec",
    )

    parent = read_json(root / ".codex" / "state" / "specs" / "root-spec.json")
    child = read_json(root / ".codex" / "state" / "specs" / "child-spec.json")
    if parent["status"] != "ready":
        raise AssertionError(f"parent did not unblock to ready: {parent}")
    if len(parent["convergence_records"]) != 1:
        raise AssertionError(f"expected one convergence record: {parent}")
    if child["review_status"] != "accepted" or child["status"] != "done":
        raise AssertionError(f"child did not converge to done/accepted: {child}")


def scenario_checkpoint_then_exec_resume_clears_superseded_binding(script_path: Path, temp_root: Path) -> None:
    root = create_fixture_repo(temp_root, "checkpoint-resume-cleanup")
    run_cw(script_path, root, "init")

    prepared = run_cw_json(script_path, root, "exec", "prepare", "root-spec")
    source_session_id = prepared["prepared_exec"]["session_id"]
    run_cw(script_path, root, "exec", "launch", "--resume-handle", "resume-fixture-002", source_session_id)

    checkpointed = run_cw_json(
        script_path,
        root,
        "checkpoint",
        source_session_id,
        "--summary",
        "pause for resume",
        "--successor-launcher",
        "exec",
    )
    checkpoint_successor_id = checkpointed["checkpointed"]["successor_session_id"]

    resumed = run_cw_json(script_path, root, "exec", "resume", source_session_id)
    resumed_session_id = resumed["resumed_exec"]["session_id"]

    sessions_dir = root / ".codex" / "state" / "sessions"
    checkpoint_successor = read_json(sessions_dir / f"{checkpoint_successor_id}.json")
    resumed_session = read_json(sessions_dir / f"{resumed_session_id}.json")
    agent = read_json(root / ".codex" / "state" / "agents" / "agent-main.json")
    worktree = read_json(root / ".codex" / "state" / "worktrees" / "wt-main.json")

    if checkpoint_successor["status"] != "abandoned":
        raise AssertionError(f"checkpoint successor should be abandoned after exec resume: {checkpoint_successor}")
    if checkpoint_successor["stop_reason"] != "superseded_by_exec_resume":
        raise AssertionError(f"checkpoint successor should record superseded stop_reason: {checkpoint_successor}")
    if resumed_session["status"] != "running":
        raise AssertionError(f"resumed session should be running: {resumed_session}")
    if agent["current_session_id"] != resumed_session_id:
        raise AssertionError(f"agent binding should move to resumed session: {agent}")
    if worktree["current_session_id"] != resumed_session_id:
        raise AssertionError(f"worktree binding should move to resumed session: {worktree}")

    doctor = run_cw_json(script_path, root, "doctor")
    orphan_codes = {item["code"] for item in doctor["findings"]}
    if {"orphan_agent_binding", "orphan_session_binding", "orphan_worktree_binding"} & orphan_codes:
        raise AssertionError(f"doctor still reported orphan bindings after exec resume cleanup: {doctor}")


def scenario_gate_backlog_detection(script_path: Path, temp_root: Path) -> None:
    root = create_fixture_repo(temp_root, "gate-backlog")
    run_cw(script_path, root, "init")
    started = run_cw_json(script_path, root, "start", "root-spec")
    session_id = started["started"]["session_id"]
    run_cw(
        script_path,
        root,
        "gate",
        "open",
        "--kind",
        "direction_change",
        "--question",
        "Choose direction",
        "--option",
        "A",
        "--option",
        "B",
        "root-spec",
    )

    doctor = run_cw_json(script_path, root, "doctor", expect_ok=False)
    codes = {item["code"] for item in doctor["findings"]}
    if "unresolved_gate" not in codes:
        raise AssertionError(f"doctor did not flag unresolved gate: {doctor}")
    if doctor["metrics"]["open_gate_count"] != 1:
        raise AssertionError(f"expected open gate metric to be 1: {doctor}")

    recover = run_cw_json(script_path, root, "recover")
    if recover["recommended_actions"][0]["kind"] != "resolve_open_gate":
        raise AssertionError(f"recover did not prioritize gate resolution: {recover}")

    session = read_json(root / ".codex" / "state" / "sessions" / f"{session_id}.json")
    if session["status"] != "waiting_human":
        raise AssertionError(f"session should be waiting_human after gate open: {session}")


def scenario_parallel_conflict_detection(script_path: Path, temp_root: Path) -> None:
    root = create_fixture_repo(temp_root, "parallel-conflict")
    create_child_spec(root, "parallel-a")
    create_child_spec(root, "parallel-b")
    run_cw(script_path, root, "init")
    run_cw(
        script_path,
        root,
        "spec",
        "create-child",
        "--mode",
        "parallel",
        "--provision-worktree",
        "--expected-output",
        "idea A",
        "--worktree-id",
        "wt-shared",
        "root-spec",
        ".codex/specs/parallel-a.md",
    )
    run_cw(
        script_path,
        root,
        "spec",
        "create-child",
        "--mode",
        "parallel",
        "--expected-output",
        "idea B",
        "root-spec",
        ".codex/specs/parallel-b.md",
    )

    spec_b_path = root / ".codex" / "state" / "specs" / "parallel-b.json"
    spec_b = read_json(spec_b_path)
    spec_b["active_worktree_id"] = "wt-shared"
    spec_b["updated_at"] = now_utc()
    write_json(spec_b_path, spec_b)

    doctor = run_cw_json(script_path, root, "doctor", expect_ok=False)
    codes = {item["code"] for item in doctor["findings"]}
    if "validation_error" not in codes or "shared_live_worktree" not in codes:
        raise AssertionError(f"doctor did not surface shared worktree conflict: {doctor}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run continuous-work v1 acceptance fixtures.")
    parser.add_argument("--root", default=".", help="repo root")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    script_path = repo_root / ".codex" / "tools" / "cw_state.py"
    if not script_path.exists():
        raise SystemExit(f"missing cw_state.py at {script_path}")

    with tempfile.TemporaryDirectory(prefix="cw-acceptance-") as temp_dir:
        temp_root = Path(temp_dir)
        scenario_interrupted_exec_recovery(script_path, temp_root)
        scenario_review_convergence_completion(script_path, temp_root)
        scenario_checkpoint_then_exec_resume_clears_superseded_binding(script_path, temp_root)
        scenario_gate_backlog_detection(script_path, temp_root)
        scenario_parallel_conflict_detection(script_path, temp_root)

    print("continuous-work v1 acceptance fixtures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
