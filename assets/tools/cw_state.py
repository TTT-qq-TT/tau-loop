#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1"
ENTITY_DIRS = {
    "project": None,
    "spec": "specs",
    "agent": "agents",
    "session": "sessions",
    "worktree": "worktrees",
    "gate": "gates",
}
BASE_FIELDS = {"schema_version", "id", "created_at", "updated_at"}
SPEC_STATUS = {"todo", "ready", "running", "blocked", "waiting_human", "review", "done", "cancelled"}
SPEC_MODE = {"serial", "parallel", "subagent"}
CHECKPOINT_STATUS = {"missing", "stale", "fresh"}
REVIEW_STATUS = {"none", "pending", "accepted", "rejected", "deferred", "needs_followup"}
REVIEW_DECISIONS = {"accepted", "rejected", "deferred", "needs_followup"}
AGENT_ROLE = {"main", "child", "reviewer", "aggregator"}
AGENT_STATUS = {"idle", "assigned", "running", "paused", "waiting_human", "completed", "failed"}
EXECUTION_KIND = {"interactive", "exec", "subagent"}
SESSION_STATUS = {"starting", "running", "checkpointed", "waiting_human", "interrupted", "completed", "failed", "abandoned"}
SESSION_LAUNCHER = {"interactive", "exec", "exec_resume"}
SESSION_RESUME_MODE = {"exec_resume", "new_session_from_checkpoint", "manual_only"}
LAUNCH_STATUS = {"none", "prepared", "launched", "resume_prepared", "resumed", "failed"}
WORKTREE_STATUS = {"planned", "ready", "active", "review_dirty", "merged", "abandoned"}
GATE_STATUS = {"open", "resolved", "cancelled"}
GATE_KIND = {"direction_change", "scope_change", "cost_increase", "subjective_choice", "deliverable_review"}
ISO_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_STALE_MINUTES = 30
SESSION_ACTIVE_BINDING_STATUS = {"starting", "running", "waiting_human"}
SESSION_TERMINAL_STATUS = {"checkpointed", "interrupted", "completed", "failed", "abandoned"}
SPEC_TERMINAL_STATUS = {"done", "cancelled"}
UNSET = object()


class ValidationError(Exception):
    pass


@dataclass
class Paths:
    root: Path
    state_dir: Path
    spec_dir: Path
    agent_dir: Path
    session_dir: Path
    worktree_dir: Path
    gate_dir: Path


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime(ISO_UTC_FORMAT)


def parse_iso_utc(value: str) -> datetime:
    return datetime.strptime(value, ISO_UTC_FORMAT).replace(tzinfo=timezone.utc)


def parse_json(text: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValidationError("entity payload must be a JSON object")
    return value


def path_for_entity(paths: Paths, entity_type: str, entity_id: str) -> Path:
    if entity_type not in ENTITY_DIRS:
        raise ValidationError(f"unsupported entity type: {entity_type}")
    subdir = ENTITY_DIRS[entity_type]
    if subdir is None:
        if entity_id != "project":
            raise ValidationError("project entity id must be 'project'")
        return paths.state_dir / "project.json"
    return getattr(paths, f"{entity_type}_dir") / f"{entity_id}.json"


def ensure_dirs(paths: Paths) -> None:
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    for name in ("spec_dir", "agent_dir", "session_dir", "worktree_dir", "gate_dir"):
        getattr(paths, name).mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return parse_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing entity file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path}: {exc}") from exc


def apply_compat_defaults(entity_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if entity_type == "spec":
        review_status = "pending" if payload.get("status") == "review" else "none"
        payload.setdefault("review_status", review_status)
        payload.setdefault("review_owner_spec_id", payload.get("parent_spec_id"))
        payload.setdefault("review_requested_at", payload.get("updated_at") if payload.get("status") == "review" else None)
        payload.setdefault("review_completed_at", None)
        payload.setdefault("convergence_summary", "")
        payload.setdefault("convergence_records", [])
    if entity_type == "agent":
        payload.setdefault("execution_session_origin", "")
    if entity_type == "session":
        payload.setdefault("launch_status", "none")
        payload.setdefault("launch_command", "")
        payload.setdefault("launch_prompt_ref", None)
        payload.setdefault("launch_args", [])
        payload.setdefault("execution_kind", "interactive" if payload.get("launcher") == "interactive" else "exec")
        payload.setdefault("subagent_evidence", [])
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_output(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None
    return result.stdout.strip() or None


def read_plan_value(plan_text: str, name: str) -> str:
    needle = f"- {name}:"
    for line in plan_text.splitlines():
        if line.startswith(needle):
            return line.split(":", 1)[1].strip().strip("`")
    return ""


def active_spec_path_from_plan(root: Path) -> Path | None:
    plan_path = root / ".codex" / "plan.md"
    if not plan_path.exists():
        raise ValidationError("missing .codex/plan.md")
    plan_text = plan_path.read_text(encoding="utf-8")
    spec_rel = read_plan_value(plan_text, "Spec")
    if not spec_rel:
        return None
    spec_path = root / spec_rel
    if not spec_path.exists():
        raise ValidationError(f"active spec does not exist: {spec_rel}")
    return spec_path


def collect_expected_outputs(spec_text: str) -> list[str]:
    outputs: list[str] = []
    capture = False
    for raw_line in spec_text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            capture = False
        if line == "## 1. Goal":
            pass
        if line.startswith("## 6. Verification"):
            break
        if line.strip() == "## 5. Implementation Checklist":
            capture = False
        if line.strip() == "## 4. Allowed Files":
            capture = False
        if line.strip() == "## 3. References Or Prior Art":
            capture = False
        if line.strip() == "## 2. Non-Goals":
            capture = False
        if line.strip() == "## 8. Notes And Decisions":
            capture = False
        if line.strip() == "## 7. Risks And Regression Points":
            capture = False
        if line.strip() == "## 9. Verification Notes":
            capture = False
        if line.strip() == "## 5. Expected Outputs":
            capture = True
            continue
        if capture and line.strip().startswith("- "):
            outputs.append(line.strip()[2:].strip().strip("`"))
    return outputs


def spec_title(spec_text: str, spec_id: str) -> str:
    for line in spec_text.splitlines():
        if line.startswith("# Task Spec:"):
            return line.split(":", 1)[1].strip()
    return spec_id.replace("-", " ")


def parse_spec_status(spec_text: str) -> str:
    for line in spec_text.splitlines():
        if line.startswith("- Status:"):
            return line.split(":", 1)[1].strip()
    raise ValidationError("spec markdown missing '- Status:' header")


def map_spec_markdown_status(markdown_status: str) -> str:
    mapping = {
        "draft": "todo",
        "ready": "ready",
        "in_progress": "running",
        "blocked": "blocked",
        "done": "done",
    }
    try:
        return mapping[markdown_status]
    except KeyError as exc:
        raise ValidationError(f"unsupported markdown spec status: {markdown_status}") from exc


def build_paths(root: Path) -> Paths:
    state_dir = root / ".codex" / "state"
    return Paths(
        root=root,
        state_dir=state_dir,
        spec_dir=state_dir / "specs",
        agent_dir=state_dir / "agents",
        session_dir=state_dir / "sessions",
        worktree_dir=state_dir / "worktrees",
        gate_dir=state_dir / "gates",
    )


def dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def next_dated_id(existing_ids: list[str], prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    head = f"{prefix}-{stamp}-"
    max_value = 0
    for entity_id in existing_ids:
        if not entity_id.startswith(head):
            continue
        tail = entity_id[len(head):]
        if tail.isdigit():
            max_value = max(max_value, int(tail))
    return f"{prefix}-{stamp}-{max_value + 1:03d}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "item"


def unique_slug_id(existing_ids: list[str], prefix: str, raw_value: str) -> str:
    base = f"{prefix}-{slugify(raw_value)}"
    if base not in existing_ids:
        return base
    suffix = 2
    while f"{base}-{suffix}" in existing_ids:
        suffix += 1
    return f"{base}-{suffix}"


def default_checkpoint_refs(spec: dict[str, Any]) -> list[str]:
    refs = [".codex/memory.md", ".codex/plan.md"]
    spec_path = spec.get("spec_path")
    if isinstance(spec_path, str) and spec_path:
        refs.append(spec_path)
    return dedupe_strings(refs)


def bootstrap_project_payload(root: Path) -> dict[str, Any]:
    timestamp = now_utc()
    active_spec_path = active_spec_path_from_plan(root)
    active_spec_id = active_spec_path.stem if active_spec_path is not None else ""
    return {
        "schema_version": SCHEMA_VERSION,
        "id": "project",
        "created_at": timestamp,
        "updated_at": timestamp,
        "repo_root": str(root.resolve()),
        "default_branch": current_branch_name(root),
        "active_spec_id": active_spec_id,
        "active_session_id": None,
        "open_gate_ids": [],
        "running_spec_ids": [],
        "blocked_spec_ids": [],
        "review_spec_ids": [],
        "done_spec_ids": [],
        "next_candidate_spec_ids": [active_spec_id] if active_spec_id else [],
        "notes": "Initialized by cw init.",
    }


def current_branch_name(root: Path) -> str:
    return git_output(root, "branch", "--show-current") or "main"


def unmet_dependency_ids(spec: dict[str, Any], specs: dict[str, dict[str, Any]]) -> list[str]:
    return sorted([dep for dep in spec.get("dependency_spec_ids", []) if specs.get(dep, {}).get("status") != "done"])


def is_active_binding_session(session: dict[str, Any] | None) -> bool:
    return bool(session) and session.get("status") in SESSION_ACTIVE_BINDING_STATUS


def default_resume_mode(spec: dict[str, Any]) -> str:
    value = spec.get("resume_strategy")
    if isinstance(value, str) and value in SESSION_RESUME_MODE:
        return value
    return "new_session_from_checkpoint"


def ensure_session(paths: Paths, entities: dict[str, Any], session_id: str) -> dict[str, Any]:
    session = entities["sessions"].get(session_id)
    if session is None:
        raise ValidationError(f"unknown session: {session_id}")
    spec = entities["specs"].get(session["spec_id"])
    agent = entities["agents"].get(session["agent_id"])
    worktree = entities["worktrees"].get(session["worktree_id"])
    if spec is None or agent is None or worktree is None:
        raise ValidationError(f"session {session_id} has missing spec/agent/worktree linkage")
    return session


def gate_resolution_to_status(resolution: str) -> tuple[str, str]:
    mapping = {
        "return_ready": ("ready", "checkpointed"),
        "continue_running": ("running", "running"),
        "cancel_spec": ("cancelled", "abandoned"),
    }
    try:
        return mapping[resolution]
    except KeyError as exc:
        raise ValidationError(f"unsupported gate resolution: {resolution}") from exc


def ensure_base_fields(entity_type: str, payload: dict[str, Any]) -> None:
    missing = sorted(BASE_FIELDS - payload.keys())
    if missing:
        raise ValidationError(f"{entity_type} missing required fields: {', '.join(missing)}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValidationError(f"{entity_type} schema_version must be {SCHEMA_VERSION}")
    for field in ("id", "created_at", "updated_at"):
        if not isinstance(payload[field], str) or not payload[field]:
            raise ValidationError(f"{entity_type}.{field} must be a non-empty string")
    for field in ("created_at", "updated_at"):
        try:
            parse_iso_utc(payload[field])
        except ValueError as exc:
            raise ValidationError(f"{entity_type}.{field} must use ISO 8601 UTC format") from exc


def expect_string(payload: dict[str, Any], field: str, *, allow_empty: bool = False, allow_null: bool = False) -> None:
    value = payload.get(field)
    if value is None:
        if allow_null:
            return
        raise ValidationError(f"{field} is required")
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    if not allow_empty and not value:
        raise ValidationError(f"{field} must be non-empty")


def expect_bool(payload: dict[str, Any], field: str) -> None:
    if not isinstance(payload.get(field), bool):
        raise ValidationError(f"{field} must be a boolean")


def expect_list_of_strings(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list")
    if not all(isinstance(item, str) and item for item in value):
        raise ValidationError(f"{field} must contain only non-empty strings")


def expect_enum(payload: dict[str, Any], field: str, allowed: set[str], *, allow_null: bool = False) -> None:
    value = payload.get(field)
    if value is None:
        if allow_null:
            return
        raise ValidationError(f"{field} is required")
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    if value not in allowed:
        raise ValidationError(f"{field} must be one of: {', '.join(sorted(allowed))}")


def expect_list_of_objects(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list")
    if not all(isinstance(item, dict) for item in value):
        raise ValidationError(f"{field} must contain only objects")


def validate_project(root: Path, payload: dict[str, Any]) -> None:
    ensure_base_fields("project", payload)
    expect_string(payload, "repo_root")
    expect_string(payload, "default_branch")
    if Path(payload["repo_root"]).expanduser().resolve() != root.resolve():
        raise ValidationError("project.repo_root must match the repo root")
    for field in (
        "active_spec_id",
        "active_session_id",
        "notes",
    ):
        allow_null = field == "active_session_id"
        allow_empty = field in {"active_spec_id", "notes"}
        expect_string(payload, field, allow_empty=allow_empty, allow_null=allow_null)
    for field in (
        "open_gate_ids",
        "running_spec_ids",
        "blocked_spec_ids",
        "review_spec_ids",
        "done_spec_ids",
        "next_candidate_spec_ids",
    ):
        expect_list_of_strings(payload, field)


def validate_spec(payload: dict[str, Any]) -> None:
    ensure_base_fields("spec", payload)
    for field in ("title", "spec_path", "priority", "summary"):
        expect_string(payload, field, allow_empty=(field == "summary"))
    expect_enum(payload, "status", SPEC_STATUS)
    expect_enum(payload, "mode", SPEC_MODE)
    for field in ("parent_spec_id", "assigned_agent_id", "active_session_id", "active_worktree_id", "open_gate_id", "review_owner_spec_id"):
        expect_string(payload, field, allow_null=True)
    for field in ("dependency_spec_ids", "blocked_by_spec_ids", "expected_outputs"):
        expect_list_of_strings(payload, field)
    expect_string(payload, "verification_profile")
    expect_enum(payload, "checkpoint_status", CHECKPOINT_STATUS)
    expect_enum(payload, "review_status", REVIEW_STATUS)
    for field in ("review_requested_at", "review_completed_at"):
        expect_string(payload, field, allow_null=True)
        if payload[field] is not None:
            try:
                parse_iso_utc(payload[field])
            except ValueError as exc:
                raise ValidationError(f"spec.{field} must use ISO 8601 UTC format") from exc
    expect_string(payload, "convergence_summary", allow_empty=True)
    expect_list_of_objects(payload, "convergence_records")
    expect_string(payload, "last_checkpoint_at", allow_null=True)
    if payload["last_checkpoint_at"] is not None:
        try:
            parse_iso_utc(payload["last_checkpoint_at"])
        except ValueError as exc:
            raise ValidationError("spec.last_checkpoint_at must use ISO 8601 UTC format") from exc
    expect_string(payload, "resume_strategy")
    if payload["status"] == "waiting_human" and not payload["open_gate_id"]:
        raise ValidationError("spec waiting_human requires open_gate_id")
    if payload["status"] == "review" and payload["review_status"] != "pending":
        raise ValidationError("spec review status requires review_status=pending")
    if payload["status"] != "review" and payload["review_status"] == "pending":
        raise ValidationError("review_status=pending requires spec.status=review")
    if payload["review_status"] in REVIEW_DECISIONS and payload["status"] == "review":
        raise ValidationError("resolved review_status cannot coexist with spec.status=review")
    if payload["review_status"] != "none" and payload["review_requested_at"] is None:
        raise ValidationError("review_status other than none requires review_requested_at")
    if payload["review_status"] in REVIEW_DECISIONS and payload["review_completed_at"] is None:
        raise ValidationError("resolved review_status requires review_completed_at")
    if payload["review_status"] in {"none", "pending"} and payload["review_completed_at"] is not None:
        raise ValidationError("review_completed_at requires a resolved review_status")
    for item in payload["convergence_records"]:
        for field in ("child_spec_id", "decision", "summary", "decided_at", "decided_by"):
            value = item.get(field)
            if not isinstance(value, str) or (field != "summary" and not value):
                raise ValidationError(f"convergence_records entries require {field}")
        if item["decision"] not in REVIEW_DECISIONS:
            raise ValidationError("convergence_records.decision must be a supported review decision")
        followup_spec_id = item.get("followup_spec_id")
        if followup_spec_id is not None and not isinstance(followup_spec_id, str):
            raise ValidationError("convergence_records.followup_spec_id must be a string or null")
        try:
            parse_iso_utc(item["decided_at"])
        except ValueError as exc:
            raise ValidationError("convergence_records.decided_at must use ISO 8601 UTC format") from exc


def validate_agent(payload: dict[str, Any]) -> None:
    ensure_base_fields("agent", payload)
    expect_enum(payload, "role", AGENT_ROLE)
    expect_enum(payload, "status", AGENT_STATUS)
    expect_string(payload, "owner_spec_id")
    expect_string(payload, "current_session_id", allow_null=True)
    expect_string(payload, "current_worktree_id", allow_null=True)
    expect_string(payload, "parent_agent_id", allow_null=True)
    expect_enum(payload, "execution_kind", EXECUTION_KIND)
    expect_string(payload, "execution_session_origin", allow_empty=True)
    expect_string(payload, "notes", allow_empty=True)


def validate_session(payload: dict[str, Any]) -> None:
    ensure_base_fields("session", payload)
    expect_enum(payload, "status", SESSION_STATUS)
    expect_string(payload, "spec_id")
    expect_string(payload, "agent_id")
    expect_string(payload, "worktree_id")
    expect_enum(payload, "launcher", SESSION_LAUNCHER)
    expect_enum(payload, "resume_mode", SESSION_RESUME_MODE)
    expect_string(payload, "resume_handle", allow_null=True)
    expect_string(payload, "started_from_session_id", allow_null=True)
    expect_string(payload, "last_heartbeat_at")
    try:
        parse_iso_utc(payload["last_heartbeat_at"])
    except ValueError as exc:
        raise ValidationError("session.last_heartbeat_at must use ISO 8601 UTC format") from exc
    expect_bool(payload, "checkpoint_written")
    expect_list_of_strings(payload, "checkpoint_refs")
    expect_enum(payload, "launch_status", LAUNCH_STATUS)
    expect_string(payload, "launch_command", allow_empty=True)
    expect_string(payload, "launch_prompt_ref", allow_null=True)
    if payload["launch_prompt_ref"] is not None and not isinstance(payload["launch_prompt_ref"], str):
        raise ValidationError("launch_prompt_ref must be a string or null")
    expect_list_of_strings(payload, "launch_args")
    expect_string(payload, "execution_kind")
    if payload["execution_kind"] not in EXECUTION_KIND:
        raise ValidationError(f"execution_kind must be one of: {', '.join(sorted(EXECUTION_KIND))}")
    expect_string(payload, "result_summary", allow_empty=True)
    expect_string(payload, "stop_reason", allow_null=True)
    expect_list_of_objects(payload, "subagent_evidence")
    if payload["launcher"] == "exec_resume" and not payload["resume_handle"]:
        raise ValidationError("session resume_handle is required for exec_resume launcher")
    if payload["status"] == "running":
        for field in ("spec_id", "agent_id", "worktree_id"):
            if not payload.get(field):
                raise ValidationError(f"session running requires {field}")
    if payload["launch_prompt_ref"] is not None and not payload["launch_prompt_ref"]:
        raise ValidationError("launch_prompt_ref must be non-empty when provided")
    for item in payload["subagent_evidence"]:
        for field in ("id", "summary", "recorded_at"):
            value = item.get(field)
            if not isinstance(value, str) or not value:
                raise ValidationError(f"subagent_evidence entries require non-empty {field}")
        refs = item.get("checkpoint_refs", [])
        if not isinstance(refs, list) or not all(isinstance(ref, str) and ref for ref in refs):
            raise ValidationError("subagent_evidence.checkpoint_refs must contain only non-empty strings")
        try:
            parse_iso_utc(item["recorded_at"])
        except ValueError as exc:
            raise ValidationError("subagent_evidence.recorded_at must use ISO 8601 UTC format") from exc


def validate_worktree(payload: dict[str, Any]) -> None:
    ensure_base_fields("worktree", payload)
    expect_enum(payload, "status", WORKTREE_STATUS)
    expect_string(payload, "path")
    expect_string(payload, "branch")
    expect_string(payload, "base_ref")
    expect_string(payload, "owner_spec_id")
    expect_string(payload, "current_session_id", allow_null=True)
    expect_bool(payload, "parallel_safe")
    expect_string(payload, "last_verified_clean_at", allow_null=True)
    if payload["last_verified_clean_at"] is not None:
        try:
            parse_iso_utc(payload["last_verified_clean_at"])
        except ValueError as exc:
            raise ValidationError("worktree.last_verified_clean_at must use ISO 8601 UTC format") from exc
    expect_string(payload, "notes", allow_empty=True)


def validate_gate(payload: dict[str, Any]) -> None:
    ensure_base_fields("gate", payload)
    expect_enum(payload, "status", GATE_STATUS)
    expect_enum(payload, "kind", GATE_KIND)
    expect_string(payload, "spec_id")
    expect_string(payload, "session_id")
    expect_string(payload, "question")
    expect_string(payload, "context_summary", allow_empty=True)
    expect_list_of_strings(payload, "options")
    expect_string(payload, "resolution", allow_null=True)
    expect_string(payload, "resolved_by", allow_null=True)
    expect_string(payload, "resolved_at", allow_null=True)
    if payload["resolved_at"] is not None:
        try:
            parse_iso_utc(payload["resolved_at"])
        except ValueError as exc:
            raise ValidationError("gate.resolved_at must use ISO 8601 UTC format") from exc
    if payload["status"] == "resolved" and not payload["resolution"]:
        raise ValidationError("resolved gate requires resolution")


def validate_entity_shape(entity_type: str, payload: dict[str, Any]) -> None:
    if entity_type == "project":
        raise ValidationError("project validation requires repo-aware context")
    validators = {
        "spec": validate_spec,
        "agent": validate_agent,
        "session": validate_session,
        "worktree": validate_worktree,
        "gate": validate_gate,
    }
    validators[entity_type](payload)


def read_entity(paths: Paths, entity_type: str, entity_id: str) -> dict[str, Any]:
    return load_json(path_for_entity(paths, entity_type, entity_id))


def entity_exists(paths: Paths, entity_type: str, entity_id: str) -> bool:
    try:
        return path_for_entity(paths, entity_type, entity_id).exists()
    except ValidationError:
        return False


def snapshot_entity_exists(paths: Paths, entities: dict[str, Any] | None, entity_type: str, entity_id: str) -> bool:
    if entities is not None:
        if entity_type == "project":
            return entities.get("project") is not None and entity_id == "project"
        return entity_id in entities.get(f"{entity_type}s", {})
    return entity_exists(paths, entity_type, entity_id)


def validate_cross_refs(paths: Paths, entity_type: str, payload: dict[str, Any], entities: dict[str, Any] | None = None) -> None:
    def require_entity(ref_type: str, ref_id: str | None, field: str) -> None:
        if ref_id is None:
            return
        if isinstance(ref_id, str) and not ref_id:
            return
        if not snapshot_entity_exists(paths, entities, ref_type, ref_id):
            raise ValidationError(f"{entity_type}.{field} points to missing {ref_type}: {ref_id}")

    if entity_type == "project":
        require_entity("spec", payload["active_spec_id"], "active_spec_id")
        require_entity("session", payload["active_session_id"], "active_session_id")
        for field in ("open_gate_ids",):
            for ref in payload[field]:
                require_entity("gate", ref, field)
        for field in ("running_spec_ids", "blocked_spec_ids", "review_spec_ids", "done_spec_ids", "next_candidate_spec_ids"):
            for ref in payload[field]:
                require_entity("spec", ref, field)
        return

    if entity_type == "spec":
        spec_path = paths.root / payload["spec_path"]
        if not spec_path.exists():
            raise ValidationError(f"spec.spec_path does not exist: {payload['spec_path']}")
        profile_path = paths.root / payload["verification_profile"]
        if not profile_path.exists():
            raise ValidationError(f"spec.verification_profile does not exist: {payload['verification_profile']}")
        require_entity("spec", payload["parent_spec_id"], "parent_spec_id")
        require_entity("spec", payload["review_owner_spec_id"], "review_owner_spec_id")
        for field in ("dependency_spec_ids", "blocked_by_spec_ids"):
            for ref in payload[field]:
                require_entity("spec", ref, field)
        for item in payload.get("convergence_records", []):
            require_entity("spec", item.get("child_spec_id"), "convergence_records.child_spec_id")
            require_entity("spec", item.get("followup_spec_id"), "convergence_records.followup_spec_id")
        require_entity("agent", payload["assigned_agent_id"], "assigned_agent_id")
        require_entity("session", payload["active_session_id"], "active_session_id")
        require_entity("worktree", payload["active_worktree_id"], "active_worktree_id")
        require_entity("gate", payload["open_gate_id"], "open_gate_id")
        return

    if entity_type == "agent":
        require_entity("spec", payload["owner_spec_id"], "owner_spec_id")
        require_entity("session", payload["current_session_id"], "current_session_id")
        require_entity("worktree", payload["current_worktree_id"], "current_worktree_id")
        require_entity("agent", payload["parent_agent_id"], "parent_agent_id")
        return

    if entity_type == "session":
        require_entity("spec", payload["spec_id"], "spec_id")
        require_entity("agent", payload["agent_id"], "agent_id")
        require_entity("worktree", payload["worktree_id"], "worktree_id")
        require_entity("session", payload["started_from_session_id"], "started_from_session_id")
        launch_prompt_ref = payload.get("launch_prompt_ref")
        if launch_prompt_ref is not None and not (paths.root / launch_prompt_ref).exists():
            raise ValidationError(f"session.launch_prompt_ref points to missing path: {launch_prompt_ref}")
        for ref in payload["checkpoint_refs"]:
            if not (paths.root / ref).exists():
                raise ValidationError(f"session.checkpoint_refs points to missing path: {ref}")
        for item in payload.get("subagent_evidence", []):
            for ref in item.get("checkpoint_refs", []):
                if not (paths.root / ref).exists():
                    raise ValidationError(f"session.subagent_evidence checkpoint ref points to missing path: {ref}")
        return

    if entity_type == "worktree":
        require_entity("spec", payload["owner_spec_id"], "owner_spec_id")
        require_entity("session", payload["current_session_id"], "current_session_id")
        return

    if entity_type == "gate":
        require_entity("spec", payload["spec_id"], "spec_id")
        require_entity("session", payload["session_id"], "session_id")


def validate_record(
    paths: Paths,
    entity_type: str,
    payload: dict[str, Any],
    *,
    expected_id: str | None = None,
    entities: dict[str, Any] | None = None,
) -> None:
    if entity_type == "project":
        validate_project(paths.root, payload)
    else:
        validate_entity_shape(entity_type, payload)
    if expected_id and payload["id"] != expected_id:
        raise ValidationError(f"{entity_type} id mismatch: expected {expected_id}, got {payload['id']}")
    validate_cross_refs(paths, entity_type, payload, entities)


def validate_entity_file(paths: Paths, path: Path, entity_type: str) -> None:
    payload = apply_compat_defaults(entity_type, load_json(path))
    expected_id = "project" if entity_type == "project" else path.stem
    validate_record(paths, entity_type, payload, expected_id=expected_id)


def iter_entity_files(paths: Paths) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    project_path = paths.state_dir / "project.json"
    if project_path.exists():
        files.append(("project", project_path))
    for entity_type, attr in (("spec", "spec_dir"), ("agent", "agent_dir"), ("session", "session_dir"), ("worktree", "worktree_dir"), ("gate", "gate_dir")):
        directory = getattr(paths, attr)
        if directory.exists():
            for path in sorted(directory.glob("*.json")):
                files.append((entity_type, path))
    return files


def load_entities(paths: Paths) -> dict[str, Any]:
    entities: dict[str, Any] = {
        "project": None,
        "specs": {},
        "agents": {},
        "sessions": {},
        "worktrees": {},
        "gates": {},
    }
    for entity_type, path in iter_entity_files(paths):
        payload = apply_compat_defaults(entity_type, load_json(path))
        if entity_type == "project":
            entities["project"] = payload
        else:
            entities[f"{entity_type}s"][payload["id"]] = payload
    return entities


def collect_validation_errors(paths: Paths, entities: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        validate_runtime_invariants(paths, entities)
    except ValidationError as exc:
        errors.append(f".codex/state runtime invariants: {exc}")
    for entity_type, path in iter_entity_files(paths):
        try:
            validate_entity_file(paths, path, entity_type)
        except ValidationError as exc:
            errors.append(f"{path.relative_to(paths.root)}: {exc}")
    return errors


def record_status_counts(records: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for payload in records.values():
        status = payload.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def child_spec_ids(spec_id: str, specs: dict[str, dict[str, Any]]) -> list[str]:
    return sorted([candidate_id for candidate_id, candidate in specs.items() if candidate.get("parent_spec_id") == spec_id])


def pending_review_child_spec_ids(owner_spec_id: str, specs: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(
        [
            candidate_id
            for candidate_id, candidate in specs.items()
            if candidate.get("status") == "review"
            and candidate.get("review_status") == "pending"
            and (candidate.get("review_owner_spec_id") or candidate.get("parent_spec_id")) == owner_spec_id
        ]
    )


def review_blocker_ids(spec_id: str, specs: dict[str, dict[str, Any]]) -> list[str]:
    return pending_review_child_spec_ids(spec_id, specs)


def dependency_blocker_ids(spec: dict[str, Any], specs: dict[str, dict[str, Any]]) -> list[str]:
    blockers = list(unmet_dependency_ids(spec, specs))
    blockers.extend(spec.get("blocked_by_spec_ids", []))
    blockers.extend(review_blocker_ids(spec["id"], specs))
    return dedupe_strings(sorted([item for item in blockers if item]))


def lane_records(specs: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    lanes: dict[str, list[str]] = {lane: [] for lane in ("todo", "ready", "running", "blocked", "waiting_human", "review", "done", "cancelled")}
    for spec_id, spec in sorted(specs.items()):
        lanes.setdefault(spec.get("status", "todo"), []).append(spec_id)
    return lanes


def summarize_spec(spec: dict[str, Any], specs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "spec_id": spec["id"],
        "title": spec.get("title"),
        "status": spec.get("status"),
        "mode": spec.get("mode"),
        "parent_spec_id": spec.get("parent_spec_id"),
        "child_spec_ids": child_spec_ids(spec["id"], specs),
        "pending_review_child_spec_ids": pending_review_child_spec_ids(spec["id"], specs),
        "dependency_spec_ids": spec.get("dependency_spec_ids", []),
        "dependency_blocker_ids": dependency_blocker_ids(spec, specs),
        "assigned_agent_id": spec.get("assigned_agent_id"),
        "active_session_id": spec.get("active_session_id"),
        "active_worktree_id": spec.get("active_worktree_id"),
        "open_gate_id": spec.get("open_gate_id"),
        "review_status": spec.get("review_status"),
        "review_owner_spec_id": spec.get("review_owner_spec_id"),
        "review_requested_at": spec.get("review_requested_at"),
        "review_completed_at": spec.get("review_completed_at"),
        "convergence_record_count": len(spec.get("convergence_records", [])),
        "expected_outputs": spec.get("expected_outputs", []),
    }


def project_lane_summary(specs: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    lanes = lane_records(specs)
    return {lane: lanes.get(lane, []) for lane in ("todo", "ready", "running", "blocked", "waiting_human", "review", "done", "cancelled")}


def shared_live_worktree_conflicts(specs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    refs: dict[str, list[str]] = {}
    conflicts: list[dict[str, Any]] = []
    for spec_id, spec in sorted(specs.items()):
        worktree_id = spec.get("active_worktree_id")
        if not worktree_id or spec.get("status") in SPEC_TERMINAL_STATUS:
            continue
        refs.setdefault(worktree_id, []).append(spec_id)
    for worktree_id, spec_ids in sorted(refs.items()):
        if len(spec_ids) <= 1:
            continue
        if any(specs[spec_id].get("mode") == "parallel" for spec_id in spec_ids):
            conflicts.append(
                {
                    "worktree_id": worktree_id,
                    "spec_ids": sorted(spec_ids),
                    "kind": "shared_live_worktree",
                }
            )
    return conflicts


def blocker_deadlock_cycles(specs: dict[str, dict[str, Any]]) -> list[list[str]]:
    graph: dict[str, list[str]] = {}
    for spec_id, spec in sorted(specs.items()):
        if spec.get("status") in SPEC_TERMINAL_STATUS:
            continue
        graph[spec_id] = [
            blocker_id
            for blocker_id in spec.get("blocked_by_spec_ids", [])
            if blocker_id in specs and specs[blocker_id].get("status") not in SPEC_TERMINAL_STATUS
        ]

    cycles: set[tuple[str, ...]] = set()
    stack: list[str] = []
    index_map: dict[str, int] = {}
    visited: set[str] = set()

    def normalize_cycle(cycle: list[str]) -> tuple[str, ...]:
        rotations = [tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle))]
        return min(rotations)

    def walk(spec_id: str) -> None:
        visited.add(spec_id)
        index_map[spec_id] = len(stack)
        stack.append(spec_id)
        for blocker_id in graph.get(spec_id, []):
            if blocker_id not in visited:
                walk(blocker_id)
                continue
            if blocker_id in index_map:
                cycle = stack[index_map[blocker_id]:]
                if len(cycle) > 1:
                    cycles.add(normalize_cycle(cycle))
        stack.pop()
        index_map.pop(spec_id, None)

    for spec_id in sorted(graph):
        if spec_id not in visited:
            walk(spec_id)
    return [list(cycle) for cycle in sorted(cycles)]


def collect_orphan_bindings(entities: dict[str, Any]) -> list[dict[str, Any]]:
    specs = entities["specs"]
    agents = entities["agents"]
    sessions = entities["sessions"]
    worktrees = entities["worktrees"]
    findings: list[dict[str, Any]] = []

    for session_id, session in sorted(sessions.items()):
        if not is_active_binding_session(session):
            continue
        spec = specs.get(session.get("spec_id"))
        agent = agents.get(session.get("agent_id"))
        worktree = worktrees.get(session.get("worktree_id"))
        if spec is not None and spec.get("active_session_id") != session_id:
            findings.append(
                {
                    "code": "orphan_session_binding",
                    "entity_type": "session",
                    "entity_id": session_id,
                    "summary": f"Active session {session_id} is not the active_session_id on spec {spec['id']}.",
                    "recommended_action": f"Repair spec {spec['id']} or clear stale session {session_id} bindings.",
                }
            )
        if agent is not None and agent.get("current_session_id") != session_id:
            findings.append(
                {
                    "code": "orphan_agent_binding",
                    "entity_type": "agent",
                    "entity_id": agent["id"],
                    "summary": f"Agent {agent['id']} is bound to active session {session_id} inconsistently.",
                    "recommended_action": f"Repair agent {agent['id']} current_session_id or stop session {session_id}.",
                }
            )
        if worktree is not None and worktree.get("current_session_id") != session_id:
            findings.append(
                {
                    "code": "orphan_worktree_binding",
                    "entity_type": "worktree",
                    "entity_id": worktree["id"],
                    "summary": f"Worktree {worktree['id']} is bound to active session {session_id} inconsistently.",
                    "recommended_action": f"Repair worktree {worktree['id']} current_session_id or stop session {session_id}.",
                }
            )

    for agent_id, agent in sorted(agents.items()):
        session_id = agent.get("current_session_id")
        if not session_id:
            continue
        session = sessions.get(session_id)
        if session is not None and not is_active_binding_session(session):
            findings.append(
                {
                    "code": "agent_points_to_inactive_session",
                    "entity_type": "agent",
                    "entity_id": agent_id,
                    "summary": f"Agent {agent_id} still points to non-active session {session_id}.",
                    "recommended_action": f"Clear agent {agent_id} current_session_id or revive session {session_id} via recovery.",
                }
            )

    for worktree_id, worktree in sorted(worktrees.items()):
        session_id = worktree.get("current_session_id")
        if not session_id:
            continue
        session = sessions.get(session_id)
        if session is not None and not is_active_binding_session(session):
            findings.append(
                {
                    "code": "worktree_points_to_inactive_session",
                    "entity_type": "worktree",
                    "entity_id": worktree_id,
                    "summary": f"Worktree {worktree_id} still points to non-active session {session_id}.",
                    "recommended_action": f"Clear worktree {worktree_id} current_session_id or repair session {session_id}.",
                }
            )
    return findings


def collect_checkpoint_findings(
    specs: dict[str, dict[str, Any]],
    sessions: dict[str, dict[str, Any]],
    *,
    stale_minutes: int,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)

    for spec_id, spec in sorted(specs.items()):
        if spec.get("status") not in {"running", "waiting_human"}:
            continue
        session_id = spec.get("active_session_id")
        session = sessions.get(session_id) if session_id else None
        last_checkpoint_at = spec.get("last_checkpoint_at")
        if not last_checkpoint_at and session is not None and not session.get("checkpoint_written"):
            findings.append(
                {
                    "code": "missing_checkpoint_evidence",
                    "entity_type": "spec",
                    "entity_id": spec_id,
                    "summary": f"Live spec {spec_id} has no checkpoint evidence recorded yet.",
                    "recommended_action": f"Write a checkpoint for spec {spec_id} before more loop state accumulates.",
                }
            )
            continue
        if last_checkpoint_at is None:
            continue
        checkpoint_at = parse_iso_utc(last_checkpoint_at)
        if checkpoint_at <= stale_cutoff:
            findings.append(
                {
                    "code": "stale_checkpoint_evidence",
                    "entity_type": "spec",
                    "entity_id": spec_id,
                    "summary": f"Spec {spec_id} has stale checkpoint evidence older than {stale_minutes} minutes.",
                    "recommended_action": f"Refresh checkpoint evidence for spec {spec_id} or close the live session cleanly.",
                }
            )
    return findings


def build_loop_metrics(paths: Paths, entities: dict[str, Any], *, stale_minutes: int, recovery: dict[str, Any] | None = None) -> dict[str, Any]:
    specs = entities["specs"]
    sessions = entities["sessions"]
    recovery = recovery or analyze_recovery(paths, entities, stale_minutes=stale_minutes)
    resume_count_by_spec: dict[str, int] = {}
    subagent_evidence_count_by_spec: dict[str, int] = {}
    checkpoint_status_counts = {status: 0 for status in sorted(CHECKPOINT_STATUS)}
    stale_checkpoint_spec_ids: list[str] = []
    missing_checkpoint_live_spec_ids: list[str] = []
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)

    for session in sessions.values():
        spec_id = session.get("spec_id")
        if session.get("started_from_session_id"):
            resume_count_by_spec[spec_id] = resume_count_by_spec.get(spec_id, 0) + 1
        evidence_count = len(session.get("subagent_evidence", []))
        if evidence_count:
            subagent_evidence_count_by_spec[spec_id] = subagent_evidence_count_by_spec.get(spec_id, 0) + evidence_count

    for spec_id, spec in sorted(specs.items()):
        checkpoint_status = spec.get("checkpoint_status", "missing")
        if checkpoint_status not in checkpoint_status_counts:
            checkpoint_status_counts[checkpoint_status] = 0
        checkpoint_status_counts[checkpoint_status] += 1
        last_checkpoint_at = spec.get("last_checkpoint_at")
        if last_checkpoint_at:
            checkpoint_at = parse_iso_utc(last_checkpoint_at)
            if checkpoint_at <= stale_cutoff and spec.get("status") not in SPEC_TERMINAL_STATUS:
                stale_checkpoint_spec_ids.append(spec_id)
        if spec.get("status") in {"running", "waiting_human"} and not last_checkpoint_at:
            missing_checkpoint_live_spec_ids.append(spec_id)

    return {
        "resume_count": sum(resume_count_by_spec.values()),
        "resume_count_by_spec": {key: value for key, value in sorted(resume_count_by_spec.items()) if value},
        "checkpoint_status_counts": checkpoint_status_counts,
        "stale_checkpoint_spec_ids": stale_checkpoint_spec_ids,
        "missing_checkpoint_live_spec_ids": missing_checkpoint_live_spec_ids,
        "open_gate_count": len(recovery["open_gates"]),
        "review_backlog_count": len(recovery["review_specs"]),
        "blocked_spec_count": len([spec_id for spec_id, spec in specs.items() if spec.get("status") == "blocked"]),
        "waiting_human_count": len([spec_id for spec_id, spec in specs.items() if spec.get("status") == "waiting_human"]),
        "subagent_evidence_count": sum(subagent_evidence_count_by_spec.values()),
        "subagent_evidence_count_by_spec": {key: value for key, value in sorted(subagent_evidence_count_by_spec.items()) if value},
        "parallel_conflict_count": len(recovery["parallel_worktree_conflicts"]) + len(shared_live_worktree_conflicts(specs)),
    }


def build_doctor_report(paths: Paths, entities: dict[str, Any], *, stale_minutes: int) -> dict[str, Any]:
    specs = entities["specs"]
    sessions = entities["sessions"]
    recovery = analyze_recovery(paths, entities, stale_minutes=stale_minutes)
    metrics = build_loop_metrics(paths, entities, stale_minutes=stale_minutes, recovery=recovery)
    findings: list[dict[str, Any]] = []

    for error in collect_validation_errors(paths, entities):
        findings.append(
            {
                "severity": "error",
                "code": "validation_error",
                "entity_type": "state",
                "entity_id": "project",
                "summary": error,
                "recommended_action": "Run `python3 .codex/tools/cw_state.py validate --root .` and repair the referenced state record.",
            }
        )

    for session in recovery["interrupted_sessions"]:
        findings.append(
            {
                "severity": "error",
                "code": "stale_running_session",
                "entity_type": "session",
                "entity_id": session["session_id"],
                "summary": f"Session {session['session_id']} is stale while still marked running.",
                "recommended_action": f"Recover session {session['session_id']} via {session['recommended_recovery']}.",
            }
        )

    for gate in recovery["open_gates"]:
        findings.append(
            {
                "severity": "warn",
                "code": "unresolved_gate",
                "entity_type": "gate",
                "entity_id": gate["gate_id"],
                "summary": f"Gate {gate['gate_id']} is still open for spec {gate['spec_id']}.",
                "recommended_action": f"Resolve gate {gate['gate_id']} before advancing more work.",
            }
        )

    for backlog in recovery["review_backlog_by_owner"]:
        if not backlog["pending_child_spec_ids"]:
            continue
        findings.append(
            {
                "severity": "warn",
                "code": "review_backlog",
                "entity_type": "spec",
                "entity_id": backlog["owner_spec_id"],
                "summary": (
                    f"Owner spec {backlog['owner_spec_id']} has pending child review backlog: "
                    + ", ".join(backlog["pending_child_spec_ids"])
                ),
                "recommended_action": f"Resolve child reviews for owner spec {backlog['owner_spec_id']} before starting unrelated work.",
            }
        )

    for cycle in blocker_deadlock_cycles(specs):
        findings.append(
            {
                "severity": "error",
                "code": "blocker_deadlock",
                "entity_type": "spec",
                "entity_id": cycle[0],
                "summary": f"Blocked-by deadlock detected across specs: {', '.join(cycle)}.",
                "recommended_action": "Break the blocked_by chain so at least one spec can make forward progress.",
            }
        )

    for conflict in parallel_worktree_conflicts(entities):
        findings.append(
            {
                "severity": "error",
                "code": "parallel_worktree_conflict",
                "entity_type": "worktree",
                "entity_id": conflict["worktree_id"],
                "summary": (
                    f"Parallel worktree conflict {conflict['kind']} on {conflict['worktree_id']} "
                    f"for spec {conflict['spec_id']}."
                ),
                "recommended_action": f"Provision or repair a dedicated parallel-safe worktree for {conflict['spec_id']}.",
            }
        )

    for conflict in shared_live_worktree_conflicts(specs):
        findings.append(
            {
                "severity": "error",
                "code": "shared_live_worktree",
                "entity_type": "worktree",
                "entity_id": conflict["worktree_id"],
                "summary": (
                    f"Live specs share worktree {conflict['worktree_id']}: "
                    + ", ".join(conflict["spec_ids"])
                ),
                "recommended_action": "Reassign one of the live specs onto its own worktree before continuing.",
            }
        )

    for finding in collect_orphan_bindings(entities):
        finding["severity"] = "error"
        findings.append(finding)

    for finding in collect_checkpoint_findings(specs, sessions, stale_minutes=stale_minutes):
        finding["severity"] = "warn"
        findings.append(finding)

    for spec_id, spec in sorted(specs.items()):
        if spec.get("status") != "blocked":
            continue
        if spec.get("open_gate_id"):
            continue
        blockers = dependency_blocker_ids(spec, specs)
        if blockers:
            continue
        findings.append(
            {
                "severity": "warn",
                "code": "blocked_without_visible_cause",
                "entity_type": "spec",
                "entity_id": spec_id,
                "summary": f"Spec {spec_id} is blocked but has no visible gate, dependency blocker, or review backlog.",
                "recommended_action": f"Either unblock spec {spec_id} or record the missing blocker in durable state.",
            }
        )

    severity_order = {"error": 0, "warn": 1, "info": 2}
    findings = sorted(findings, key=lambda item: (severity_order.get(item["severity"], 9), item["code"], item["entity_id"]))

    severity_counts = {"error": 0, "warn": 0, "info": 0}
    for finding in findings:
        severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1

    recommended_actions = dedupe_strings(
        [item["summary"] for item in recovery["recommended_actions"]]
        + [finding["recommended_action"] for finding in findings]
    )

    return {
        "ok": not findings,
        "stale_threshold_minutes": stale_minutes,
        "severity_counts": severity_counts,
        "metrics": metrics,
        "findings": findings,
        "recommended_actions": recommended_actions,
    }


def derive_spec_candidates(specs: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    blocked_by_gate: list[str] = []
    recoverable: list[str] = []
    ready: list[str] = []
    review: list[str] = []
    for spec_id, spec in sorted(specs.items()):
        if spec.get("open_gate_id") or spec.get("status") == "waiting_human":
            blocked_by_gate.append(spec_id)
            continue
        unmet = [dep for dep in spec.get("dependency_spec_ids", []) if specs.get(dep, {}).get("status") != "done"]
        if unmet:
            continue
        status = spec.get("status")
        if status in {"todo", "ready"}:
            ready.append(spec_id)
        elif status == "running" and spec.get("checkpoint_status") == "fresh":
            recoverable.append(spec_id)
        elif status == "review" and spec.get("review_status") == "pending":
            review.append(spec_id)
    return {
        "blocked_by_gate": blocked_by_gate,
        "recoverable": recoverable,
        "ready": ready,
        "review": review,
    }


def parallel_worktree_conflicts(entities: dict[str, Any]) -> list[dict[str, Any]]:
    specs = entities["specs"]
    worktrees = entities["worktrees"]
    sessions = entities["sessions"]
    conflicts: list[dict[str, Any]] = []
    for worktree_id, worktree in sorted(worktrees.items()):
        owner_spec_id = worktree.get("owner_spec_id")
        if not owner_spec_id:
            continue
        owner_spec = specs.get(owner_spec_id)
        current_session = sessions.get(worktree.get("current_session_id")) if worktree.get("current_session_id") else None
        active = is_active_binding_session(current_session)
        if owner_spec and owner_spec.get("mode") == "parallel" and not worktree.get("parallel_safe", False):
            conflicts.append(
                {
                    "worktree_id": worktree_id,
                    "spec_id": owner_spec_id,
                    "kind": "parallel_spec_on_non_parallel_safe_worktree",
                    "active_session_id": worktree.get("current_session_id"),
                    "active": active,
                }
            )
        if active and owner_spec and owner_spec.get("mode") == "parallel":
            for spec_id, spec in sorted(specs.items()):
                if spec_id == owner_spec_id:
                    continue
                if spec.get("active_worktree_id") != worktree_id:
                    continue
                if spec.get("mode") != "parallel":
                    continue
                conflicts.append(
                    {
                        "worktree_id": worktree_id,
                        "spec_id": spec_id,
                        "kind": "parallel_worktree_reuse_conflict",
                        "owner_spec_id": owner_spec_id,
                        "active_session_id": worktree.get("current_session_id"),
                    }
                )
    return conflicts


def validate_runtime_invariants(paths: Paths, entities: dict[str, Any]) -> None:
    specs = entities["specs"]
    worktrees = entities["worktrees"]
    sessions = entities["sessions"]

    for spec_id, spec in specs.items():
        if spec.get("parent_spec_id") == spec_id:
            raise ValidationError(f"spec {spec_id} cannot parent itself")
        deps = spec.get("dependency_spec_ids", [])
        if len(deps) != len(set(deps)):
            raise ValidationError(f"spec {spec_id} has duplicate dependency_spec_ids")
        if spec_id in deps:
            raise ValidationError(f"spec {spec_id} cannot depend on itself")
        blocked = spec.get("blocked_by_spec_ids", [])
        if len(blocked) != len(set(blocked)):
            raise ValidationError(f"spec {spec_id} has duplicate blocked_by_spec_ids")
        if spec_id in blocked:
            raise ValidationError(f"spec {spec_id} cannot block itself")
        if spec.get("review_owner_spec_id") == spec_id:
            raise ValidationError(f"spec {spec_id} cannot own its own review lane")
        if spec.get("mode") == "parallel" and spec.get("active_worktree_id"):
            worktree = worktrees.get(spec["active_worktree_id"])
            if worktree is None:
                raise ValidationError(f"spec {spec_id} points to missing active worktree {spec['active_worktree_id']}")
            if not worktree.get("parallel_safe", False):
                raise ValidationError(f"parallel spec {spec_id} requires parallel_safe worktree {worktree['id']}")
            if worktree.get("owner_spec_id") != spec_id:
                raise ValidationError(f"parallel spec {spec_id} must own worktree {worktree['id']}")
        if spec.get("status") == "review":
            if spec.get("active_session_id") is not None:
                raise ValidationError(f"review spec {spec_id} must not keep an active_session_id")
            if spec.get("open_gate_id") is not None:
                raise ValidationError(f"review spec {spec_id} must not hold open_gate_id")
        if spec.get("status") in SPEC_TERMINAL_STATUS and pending_review_child_spec_ids(spec_id, specs):
            raise ValidationError(f"spec {spec_id} is terminal while child reviews remain pending")
        if spec.get("review_status") in REVIEW_DECISIONS:
            seen_children: set[str] = set()
            for item in spec.get("convergence_records", []):
                child_id = item["child_spec_id"]
                if child_id in seen_children:
                    raise ValidationError(f"spec {spec_id} has duplicate convergence record for child {child_id}")
                seen_children.add(child_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def walk_dependencies(spec_id: str) -> None:
        if spec_id in visited:
            return
        if spec_id in visiting:
            raise ValidationError(f"dependency cycle detected at spec {spec_id}")
        visiting.add(spec_id)
        spec = specs[spec_id]
        for dep_id in spec.get("dependency_spec_ids", []):
            if dep_id not in specs:
                raise ValidationError(f"spec {spec_id} depends on missing spec {dep_id}")
            walk_dependencies(dep_id)
        visiting.remove(spec_id)
        visited.add(spec_id)

    for spec_id in sorted(specs):
        walk_dependencies(spec_id)

    for spec_id in sorted(specs):
        seen: set[str] = set()
        cursor = spec_id
        while True:
            parent_id = specs[cursor].get("parent_spec_id")
            if not parent_id:
                break
            if parent_id not in specs:
                raise ValidationError(f"spec {cursor} points to missing parent spec {parent_id}")
            if parent_id in seen or parent_id == spec_id:
                raise ValidationError(f"parent cycle detected at spec {spec_id}")
            seen.add(parent_id)
            cursor = parent_id

    active_worktree_refs: dict[str, list[str]] = {}
    for spec_id, spec in specs.items():
        worktree_id = spec.get("active_worktree_id")
        if not worktree_id or spec.get("status") in SPEC_TERMINAL_STATUS:
            continue
        active_worktree_refs.setdefault(worktree_id, []).append(spec_id)
    for worktree_id, ref_spec_ids in sorted(active_worktree_refs.items()):
        if len(ref_spec_ids) <= 1:
            continue
        if any(specs[spec_id].get("mode") == "parallel" for spec_id in ref_spec_ids):
            raise ValidationError(
                f"worktree {worktree_id} is shared by multiple live specs: {', '.join(sorted(ref_spec_ids))}"
            )

    for worktree_id, worktree in worktrees.items():
        session_id = worktree.get("current_session_id")
        if not session_id:
            continue
        session = sessions.get(session_id)
        if session is None:
            raise ValidationError(f"worktree {worktree_id} points to missing current session {session_id}")
        if session.get("worktree_id") != worktree_id:
            raise ValidationError(f"worktree {worktree_id} current_session_id {session_id} points back to {session.get('worktree_id')}")

    conflicts = parallel_worktree_conflicts(entities)
    if conflicts:
        first = conflicts[0]
        raise ValidationError(
            f"parallel worktree conflict: {first['kind']} on {first['worktree_id']} for spec {first['spec_id']}"
        )


def recompute_project_indexes(project: dict[str, Any], entities: dict[str, Any]) -> None:
    specs = entities["specs"]
    gates = entities["gates"]
    candidates = derive_spec_candidates(specs)

    project["open_gate_ids"] = sorted([gate_id for gate_id, gate in gates.items() if gate.get("status") == "open"])
    project["running_spec_ids"] = sorted([spec_id for spec_id, spec in specs.items() if spec.get("status") == "running"])
    project["blocked_spec_ids"] = sorted(
        [
            spec_id
            for spec_id, spec in specs.items()
            if spec.get("status") in {"blocked", "waiting_human"}
        ]
    )
    project["review_spec_ids"] = sorted([spec_id for spec_id, spec in specs.items() if spec.get("status") == "review"])
    project["done_spec_ids"] = sorted([spec_id for spec_id, spec in specs.items() if spec.get("status") == "done"])
    project["next_candidate_spec_ids"] = dedupe_strings(candidates["review"] + candidates["ready"])


def persist_entities(
    paths: Paths,
    entities: dict[str, Any],
    *,
    project_active_spec_id: str | object = UNSET,
    project_active_session_id: str | None | object = UNSET,
) -> None:
    project = entities["project"]
    if project is None:
        raise ValidationError("missing project state")
    if project_active_spec_id is not UNSET:
        project["active_spec_id"] = project_active_spec_id
    if project_active_session_id is not UNSET:
        project["active_session_id"] = project_active_session_id
    project["updated_at"] = now_utc()
    recompute_project_indexes(project, entities)

    validate_runtime_invariants(paths, entities)
    validate_record(paths, "project", project, expected_id="project", entities=entities)
    for entity_type in ("spec", "agent", "session", "worktree", "gate"):
        for entity_id, payload in entities[f"{entity_type}s"].items():
            validate_record(paths, entity_type, payload, expected_id=entity_id, entities=entities)

    write_json(path_for_entity(paths, "project", "project"), project)
    for entity_type in ("spec", "agent", "session", "worktree", "gate"):
        for entity_id, payload in sorted(entities[f"{entity_type}s"].items()):
            write_json(path_for_entity(paths, entity_type, entity_id), payload)


def analyze_recovery(paths: Paths, entities: dict[str, Any], *, stale_minutes: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(minutes=stale_minutes)
    sessions = entities["sessions"]
    specs = entities["specs"]
    worktrees = entities["worktrees"]
    gates = entities["gates"]
    project = entities["project"] or {}

    open_gates: list[dict[str, Any]] = []
    for gate_id, gate in sorted(gates.items()):
        if gate.get("status") == "open":
            open_gates.append(
                {
                    "gate_id": gate_id,
                    "spec_id": gate.get("spec_id"),
                    "session_id": gate.get("session_id"),
                    "kind": gate.get("kind"),
                    "question": gate.get("question"),
                }
            )

    missing_worktrees: list[dict[str, Any]] = []
    for worktree_id, worktree in sorted(worktrees.items()):
        if worktree.get("status") == "abandoned":
            continue
        if not Path(worktree["path"]).exists():
            missing_worktrees.append(
                {
                    "worktree_id": worktree_id,
                    "spec_id": worktree.get("owner_spec_id"),
                    "session_id": worktree.get("current_session_id"),
                    "path": worktree["path"],
                    "status": worktree.get("status"),
                }
            )

    interrupted_sessions: list[dict[str, Any]] = []
    for session_id, session in sorted(sessions.items()):
        if session.get("status") != "running":
            continue
        heartbeat = parse_iso_utc(session["last_heartbeat_at"])
        if heartbeat > stale_cutoff:
            continue
        recommended_recovery = "manual_only"
        if session.get("resume_mode") == "exec_resume" and session.get("resume_handle"):
            recommended_recovery = "exec_resume"
        elif session.get("checkpoint_written"):
            recommended_recovery = "new_session_from_checkpoint"
        interrupted_sessions.append(
            {
                "session_id": session_id,
                "spec_id": session.get("spec_id"),
                "agent_id": session.get("agent_id"),
                "worktree_id": session.get("worktree_id"),
                "resume_mode": session.get("resume_mode"),
                "resume_handle": session.get("resume_handle"),
                "launch_status": session.get("launch_status"),
                "last_heartbeat_at": session.get("last_heartbeat_at"),
                "checkpoint_written": session.get("checkpoint_written"),
                "recommended_recovery": recommended_recovery,
            }
        )

    candidates = derive_spec_candidates(specs)
    recoverable_specs = [
        {
            "spec_id": spec_id,
            "status": specs[spec_id]["status"],
            "checkpoint_status": specs[spec_id].get("checkpoint_status"),
            "resume_strategy": specs[spec_id].get("resume_strategy"),
            "active_session_id": specs[spec_id].get("active_session_id"),
            "active_worktree_id": specs[spec_id].get("active_worktree_id"),
        }
        for spec_id in candidates["recoverable"]
    ]
    ready_specs = [
        {
            "spec_id": spec_id,
            "status": specs[spec_id]["status"],
            "dependency_spec_ids": specs[spec_id].get("dependency_spec_ids", []),
            "mode": specs[spec_id].get("mode"),
            "active_worktree_id": specs[spec_id].get("active_worktree_id"),
        }
        for spec_id in candidates["ready"]
    ]
    review_specs = [
        {
            "spec_id": spec_id,
            "status": specs[spec_id]["status"],
            "review_owner_spec_id": specs[spec_id].get("review_owner_spec_id"),
            "parent_spec_id": specs[spec_id].get("parent_spec_id"),
            "review_requested_at": specs[spec_id].get("review_requested_at"),
        }
        for spec_id in candidates["review"]
    ]
    review_backlog_by_owner: list[dict[str, Any]] = []
    owners = sorted(
        {
            specs[spec_id].get("review_owner_spec_id") or specs[spec_id].get("parent_spec_id")
            for spec_id in candidates["review"]
            if specs[spec_id].get("review_owner_spec_id") or specs[spec_id].get("parent_spec_id")
        }
    )
    for owner_spec_id in owners:
        review_backlog_by_owner.append(
            {
                "owner_spec_id": owner_spec_id,
                "pending_child_spec_ids": pending_review_child_spec_ids(owner_spec_id, specs),
                "owner_status": specs.get(owner_spec_id, {}).get("status"),
            }
        )
    blocked_specs = [
        {
            "spec_id": spec_id,
            "status": specs[spec_id]["status"],
            "open_gate_id": specs[spec_id].get("open_gate_id"),
            "dependency_blocker_ids": dependency_blocker_ids(specs[spec_id], specs),
        }
        for spec_id in candidates["blocked_by_gate"]
    ]
    dependency_blocked_specs = [
        {
            "spec_id": spec_id,
            "status": spec.get("status"),
            "dependency_blocker_ids": dependency_blocker_ids(spec, specs),
            "parent_spec_id": spec.get("parent_spec_id"),
        }
        for spec_id, spec in sorted(specs.items())
        if dependency_blocker_ids(spec, specs) and spec.get("status") not in SPEC_TERMINAL_STATUS
    ]
    worktree_conflicts = parallel_worktree_conflicts(entities)

    actions: list[dict[str, Any]] = []
    for gate in open_gates:
        actions.append(
            {
                "priority": 1,
                "kind": "resolve_open_gate",
                "target_id": gate["gate_id"],
                "summary": f"Resolve open gate {gate['gate_id']} for spec {gate['spec_id']}",
            }
        )
    for session in interrupted_sessions:
        actions.append(
            {
                "priority": 2,
                "kind": "recover_session",
                "target_id": session["session_id"],
                "summary": (
                    f"Recover interrupted session {session['session_id']} via exec resume"
                    if session["recommended_recovery"] == "exec_resume"
                    else f"Recover interrupted session {session['session_id']} via {session['recommended_recovery']}"
                ),
            }
        )
    for item in missing_worktrees:
        actions.append(
            {
                "priority": 3,
                "kind": "repair_worktree",
                "target_id": item["worktree_id"],
                "summary": f"Repair or recreate missing worktree {item['worktree_id']}",
            }
        )
    for item in worktree_conflicts:
        actions.append(
            {
                "priority": 3,
                "kind": "resolve_worktree_conflict",
                "target_id": item["worktree_id"],
                "summary": f"Resolve parallel worktree conflict on {item['worktree_id']} for spec {item['spec_id']}",
            }
        )
    for spec in dependency_blocked_specs:
        actions.append(
            {
                "priority": 4,
                "kind": "clear_dependency_blockers",
                "target_id": spec["spec_id"],
                "summary": f"Spec {spec['spec_id']} is blocked by dependencies: {', '.join(spec['dependency_blocker_ids'])}",
            }
        )
    for backlog in review_backlog_by_owner:
        if not backlog["pending_child_spec_ids"]:
            continue
        actions.append(
            {
                "priority": 5,
                "kind": "converge_review_backlog",
                "target_id": backlog["owner_spec_id"],
                "summary": (
                    f"Owner spec {backlog['owner_spec_id']} must converge child reviews: "
                    + ", ".join(backlog["pending_child_spec_ids"])
                ),
            }
        )
    for spec in ready_specs:
        actions.append(
            {
                "priority": 6,
                "kind": "prepare_exec_spec" if specs[spec["spec_id"]].get("mode") == "serial" else "prepare_parallel_spec",
                "target_id": spec["spec_id"],
                "summary": (
                    f"Spec {spec['spec_id']} is ready for exec preparation"
                    if specs[spec["spec_id"]].get("mode") == "serial"
                    else f"Spec {spec['spec_id']} is ready for parallel provisioning/execution"
                ),
            }
        )
    for spec in review_specs:
        actions.append(
            {
                "priority": 5,
                "kind": "review_spec",
                "target_id": spec["spec_id"],
                "summary": (
                    f"Spec {spec['spec_id']} is waiting in review state for "
                    f"{spec.get('review_owner_spec_id') or spec.get('parent_spec_id') or 'manual'} convergence"
                ),
            }
        )
    actions.sort(key=lambda item: (item["priority"], item["target_id"]))

    return {
        "stale_threshold_minutes": stale_minutes,
        "project_active_spec_id": project.get("active_spec_id"),
        "open_gates": open_gates,
        "missing_worktrees": missing_worktrees,
        "interrupted_sessions": interrupted_sessions,
        "recoverable_specs": recoverable_specs,
        "ready_specs": ready_specs,
        "review_specs": review_specs,
        "review_backlog_by_owner": review_backlog_by_owner,
        "blocked_specs": blocked_specs,
        "dependency_blocked_specs": dependency_blocked_specs,
        "parallel_worktree_conflicts": worktree_conflicts,
        "recommended_actions": actions,
    }


def build_status_summary(paths: Paths, entities: dict[str, Any], *, stale_minutes: int) -> dict[str, Any]:
    project = entities["project"] or {}
    recovery = analyze_recovery(paths, entities, stale_minutes=stale_minutes)
    return {
        "project": {
            "active_spec_id": project.get("active_spec_id"),
            "active_session_id": project.get("active_session_id"),
            "default_branch": project.get("default_branch"),
            "open_gate_ids": project.get("open_gate_ids", []),
            "running_spec_ids": project.get("running_spec_ids", []),
            "blocked_spec_ids": project.get("blocked_spec_ids", []),
            "review_spec_ids": project.get("review_spec_ids", []),
            "done_spec_ids": project.get("done_spec_ids", []),
            "next_candidate_spec_ids": project.get("next_candidate_spec_ids", []),
        },
        "lanes": project_lane_summary(entities["specs"]),
        "spec_topology": [summarize_spec(spec, entities["specs"]) for _, spec in sorted(entities["specs"].items())],
        "counts": {
            "specs": record_status_counts(entities["specs"]),
            "agents": record_status_counts(entities["agents"]),
            "sessions": record_status_counts(entities["sessions"]),
            "worktrees": record_status_counts(entities["worktrees"]),
            "gates": record_status_counts(entities["gates"]),
        },
        "recovery": {
            "open_gate_count": len(recovery["open_gates"]),
            "missing_worktree_count": len(recovery["missing_worktrees"]),
            "interrupted_session_count": len(recovery["interrupted_sessions"]),
            "recoverable_spec_count": len(recovery["recoverable_specs"]),
            "ready_spec_count": len(recovery["ready_specs"]),
            "review_backlog_count": len(recovery["review_specs"]),
            "dependency_blocked_spec_count": len(recovery["dependency_blocked_specs"]),
            "parallel_worktree_conflict_count": len(recovery["parallel_worktree_conflicts"]),
        },
        "loop_metrics": build_loop_metrics(paths, entities, stale_minutes=stale_minutes, recovery=recovery),
    }


def load_active_spec(root: Path) -> tuple[str, Path, str]:
    plan_path = root / ".codex" / "plan.md"
    if not plan_path.exists():
        raise ValidationError("missing .codex/plan.md")
    plan_text = plan_path.read_text(encoding="utf-8")
    spec_rel = read_plan_value(plan_text, "Spec")
    if not spec_rel:
        raise ValidationError("plan does not define an active spec")
    spec_path = root / spec_rel
    if not spec_path.exists():
        raise ValidationError(f"active spec does not exist: {spec_rel}")
    return spec_path.stem, spec_path, plan_text


def sync_project_to_active_spec(paths: Paths, active_spec_id: str) -> None:
    project_path = path_for_entity(paths, "project", "project")
    if not project_path.exists():
        return
    entities = load_entities(paths)
    project = entities["project"]
    if project is None:
        raise ValidationError("missing project state")
    project["active_spec_id"] = active_spec_id
    project["updated_at"] = now_utc()
    recompute_project_indexes(project, entities)
    validate_runtime_invariants(paths, entities)
    validate_record(paths, "project", project, expected_id="project", entities=entities)
    write_json(project_path, project)


def build_project_record(paths: Paths, active_spec_id: str, default_branch: str | None) -> dict[str, Any]:
    timestamp = now_utc()
    branch = default_branch or "main"
    return {
        "schema_version": SCHEMA_VERSION,
        "id": "project",
        "created_at": timestamp,
        "updated_at": timestamp,
        "repo_root": str(paths.root),
        "default_branch": branch,
        "active_spec_id": active_spec_id,
        "active_session_id": None,
        "open_gate_ids": [],
        "running_spec_ids": [active_spec_id] if active_spec_id else [],
        "blocked_spec_ids": [],
        "review_spec_ids": [],
        "done_spec_ids": [],
        "next_candidate_spec_ids": [active_spec_id] if active_spec_id else [],
        "notes": "",
    }


def build_spec_record(paths: Paths, spec_id: str, spec_path: Path, plan_text: str) -> dict[str, Any]:
    timestamp = now_utc()
    spec_text = spec_path.read_text(encoding="utf-8")
    verification_profile = read_plan_value(plan_text, "Verification profile") or ".codex/verification-profiles/code-change.md"
    return {
        "schema_version": SCHEMA_VERSION,
        "id": spec_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "title": spec_title(spec_text, spec_id),
        "spec_path": str(spec_path.relative_to(paths.root)),
        "status": map_spec_markdown_status(parse_spec_status(spec_text)),
        "priority": "normal",
        "mode": "serial",
        "parent_spec_id": None,
        "dependency_spec_ids": [],
        "blocked_by_spec_ids": [],
        "expected_outputs": collect_expected_outputs(spec_text),
        "verification_profile": verification_profile,
        "assigned_agent_id": None,
        "active_session_id": None,
        "active_worktree_id": None,
        "open_gate_id": None,
        "checkpoint_status": "missing",
        "last_checkpoint_at": None,
        "review_status": "none",
        "review_owner_spec_id": None,
        "review_requested_at": None,
        "review_completed_at": None,
        "convergence_summary": "",
        "convergence_records": [],
        "resume_strategy": "new_session_from_checkpoint",
        "summary": "",
    }


def ensure_spec_state(paths: Paths, entities: dict[str, Any], spec_id: str) -> dict[str, Any]:
    spec = entities["specs"].get(spec_id)
    if spec is not None:
        return spec

    spec_path = paths.root / ".codex" / "specs" / f"{spec_id}.md"
    if not spec_path.exists():
        raise ValidationError(f"spec markdown does not exist: {spec_path.relative_to(paths.root)}")
    plan_path = paths.root / ".codex" / "plan.md"
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    spec = build_spec_record(paths, spec_id, spec_path, plan_text)
    entities["specs"][spec_id] = spec
    return spec


def parallel_worktree_path(root: Path, worktree_id: str) -> Path:
    return serial_worktree_path(root, worktree_id)


def ensure_parallel_spec_prereqs(spec: dict[str, Any]) -> None:
    if spec.get("mode") != "parallel":
        raise ValidationError(f"spec {spec['id']} is not a parallel spec")
    if spec.get("status") not in {"todo", "ready", "blocked"}:
        raise ValidationError(f"parallel spec {spec['id']} is not provisionable from status {spec.get('status')}")


def create_child_spec_record(
    paths: Paths,
    entities: dict[str, Any],
    *,
    spec_id: str,
    title: str,
    spec_path: str,
    verification_profile: str,
    parent_spec_id: str,
    dependency_spec_ids: list[str],
    mode: str,
    expected_outputs: list[str],
    summary: str,
) -> dict[str, Any]:
    timestamp = now_utc()
    spec_record = {
        "schema_version": SCHEMA_VERSION,
        "id": spec_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "title": title,
        "spec_path": spec_path,
        "status": "ready",
        "priority": "normal",
        "mode": mode,
        "parent_spec_id": parent_spec_id,
        "dependency_spec_ids": dedupe_strings(dependency_spec_ids),
        "blocked_by_spec_ids": [],
        "expected_outputs": dedupe_strings(expected_outputs),
        "verification_profile": verification_profile,
        "assigned_agent_id": None,
        "active_session_id": None,
        "active_worktree_id": None,
        "open_gate_id": None,
        "checkpoint_status": "missing",
        "last_checkpoint_at": None,
        "review_status": "none",
        "review_owner_spec_id": parent_spec_id,
        "review_requested_at": None,
        "review_completed_at": None,
        "convergence_summary": "",
        "convergence_records": [],
        "resume_strategy": "new_session_from_checkpoint",
        "summary": summary,
    }
    entities["specs"][spec_id] = spec_record
    return spec_record


def request_spec_review(
    entities: dict[str, Any],
    spec: dict[str, Any],
    *,
    timestamp: str,
    owner_spec_id: str | None,
    summary: str,
) -> None:
    spec["status"] = "review"
    spec["active_session_id"] = None
    spec["open_gate_id"] = None
    spec["review_status"] = "pending"
    spec["review_owner_spec_id"] = owner_spec_id or spec.get("parent_spec_id")
    spec["review_requested_at"] = timestamp
    spec["review_completed_at"] = None
    spec["convergence_summary"] = summary
    spec["updated_at"] = timestamp


def complete_spec_review(
    entities: dict[str, Any],
    *,
    child_spec: dict[str, Any],
    owner_spec: dict[str, Any] | None,
    decision: str,
    decided_by: str,
    summary: str,
    timestamp: str,
    followup_spec_id: str | None,
) -> dict[str, Any]:
    child_spec["review_status"] = decision
    child_spec["review_completed_at"] = timestamp
    child_spec["convergence_summary"] = summary
    child_spec["status"] = "done" if decision == "accepted" else ("blocked" if decision == "needs_followup" else "ready" if decision == "deferred" else "cancelled")
    child_spec["updated_at"] = timestamp
    if decision in {"deferred", "rejected"}:
        child_spec["active_worktree_id"] = child_spec.get("active_worktree_id")
    if decision in {"rejected", "cancelled"}:
        child_spec["assigned_agent_id"] = child_spec.get("assigned_agent_id")

    record = {
        "child_spec_id": child_spec["id"],
        "decision": decision,
        "summary": summary,
        "decided_at": timestamp,
        "decided_by": decided_by,
        "followup_spec_id": followup_spec_id,
    }
    if owner_spec is not None:
        records = [item for item in owner_spec.get("convergence_records", []) if item.get("child_spec_id") != child_spec["id"]]
        records.append(record)
        owner_spec["convergence_records"] = sorted(records, key=lambda item: item["child_spec_id"])
        owner_spec["convergence_summary"] = summary if summary else owner_spec.get("convergence_summary", "")
        if decision == "accepted":
            blocked_by = [item for item in owner_spec.get("blocked_by_spec_ids", []) if item != child_spec["id"]]
            dependencies = [item for item in owner_spec.get("dependency_spec_ids", []) if item != child_spec["id"]]
            owner_spec["blocked_by_spec_ids"] = blocked_by
            owner_spec["dependency_spec_ids"] = dependencies
            if not pending_review_child_spec_ids(owner_spec["id"], entities["specs"]) and owner_spec.get("status") == "blocked":
                owner_spec["status"] = "ready"
        elif decision in {"needs_followup", "deferred"}:
            blockers = dedupe_strings(owner_spec.get("blocked_by_spec_ids", []) + [child_spec["id"]])
            owner_spec["blocked_by_spec_ids"] = blockers
            if owner_spec.get("status") not in {"running", "waiting_human"}:
                owner_spec["status"] = "blocked"
        owner_spec["updated_at"] = timestamp
    return record


def ensure_parallel_worktree(
    paths: Paths,
    entities: dict[str, Any],
    *,
    spec_id: str,
    worktree_id: str | None,
    branch: str | None,
    base_ref: str | None,
    notes: str,
) -> dict[str, Any]:
    spec = entities["specs"].get(spec_id)
    if spec is None:
        raise ValidationError(f"unknown spec: {spec_id}")
    ensure_parallel_spec_prereqs(spec)

    timestamp = now_utc()
    resolved_worktree_id = worktree_id or unique_slug_id(list(entities["worktrees"].keys()), "wt", spec_id)
    existing = entities["worktrees"].get(resolved_worktree_id)
    if existing is not None:
        current_session_id = existing.get("current_session_id")
        if current_session_id:
            current_session = entities["sessions"].get(current_session_id)
            if is_active_binding_session(current_session):
                raise ValidationError(f"worktree {resolved_worktree_id} is already bound to active session {current_session_id}")
        if existing.get("owner_spec_id") not in {None, spec_id}:
            raise ValidationError(f"worktree {resolved_worktree_id} is already owned by spec {existing['owner_spec_id']}")
        if existing.get("status") in {"merged", "abandoned"}:
            raise ValidationError(f"worktree {resolved_worktree_id} is not reusable in status {existing.get('status')}")
        existing["status"] = "ready"
        existing["owner_spec_id"] = spec_id
        existing["parallel_safe"] = True
        existing["branch"] = branch or existing.get("branch") or f"cw/{spec_id}"
        existing["base_ref"] = base_ref or existing.get("base_ref") or current_branch_name(paths.root)
        existing["notes"] = notes or existing.get("notes", "")
        existing["updated_at"] = timestamp
        spec["active_worktree_id"] = resolved_worktree_id
        spec["updated_at"] = timestamp
        return existing

    resolved_branch = branch or f"cw/{spec_id}"
    resolved_base_ref = base_ref or current_branch_name(paths.root)
    worktree_path = parallel_worktree_path(paths.root, resolved_worktree_id)
    worktree_path.mkdir(parents=True, exist_ok=True)
    worktree = {
        "schema_version": SCHEMA_VERSION,
        "id": resolved_worktree_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "status": "ready",
        "path": str(worktree_path),
        "branch": resolved_branch,
        "base_ref": resolved_base_ref,
        "owner_spec_id": spec_id,
        "current_session_id": None,
        "parallel_safe": True,
        "last_verified_clean_at": None,
        "notes": notes,
    }
    entities["worktrees"][resolved_worktree_id] = worktree
    spec["active_worktree_id"] = resolved_worktree_id
    spec["updated_at"] = timestamp
    return worktree


def session_resume_prompt_refs(session: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    refs = list(session.get("checkpoint_refs") or [])
    prompt_ref = session.get("launch_prompt_ref")
    if isinstance(prompt_ref, str) and prompt_ref:
        refs.append(prompt_ref)
    refs.extend(default_checkpoint_refs(spec))
    return dedupe_strings(refs)


def render_exec_command(
    *,
    root: Path,
    mode: str,
    prompt_ref: str | None,
    session: dict[str, Any] | None = None,
    extra_args: list[str] | None = None,
) -> list[str]:
    command = ["codex", "exec"]
    if mode == "resume":
        command.extend(["resume", session["resume_handle"]])
    command.extend(["--cd", str(root)])
    command.extend(extra_args or [])
    if prompt_ref:
        command.append("-")
    return command


def activate_session_binding(
    *,
    entities: dict[str, Any],
    spec: dict[str, Any],
    agent: dict[str, Any],
    worktree: dict[str, Any],
    session: dict[str, Any],
    timestamp: str,
) -> None:
    spec["status"] = "running"
    spec["assigned_agent_id"] = agent["id"]
    spec["active_session_id"] = session["id"]
    spec["active_worktree_id"] = worktree["id"]
    spec["updated_at"] = timestamp

    agent["status"] = "running"
    agent["current_session_id"] = session["id"]
    agent["current_worktree_id"] = worktree["id"]
    agent["execution_kind"] = session["execution_kind"]
    agent["execution_session_origin"] = session.get("resume_handle") or session["id"]
    agent["updated_at"] = timestamp

    worktree["status"] = "active"
    worktree["owner_spec_id"] = spec["id"]
    worktree["current_session_id"] = session["id"]
    worktree["updated_at"] = timestamp


def prepare_exec_session(
    paths: Paths,
    entities: dict[str, Any],
    *,
    spec_id: str,
    prompt_ref: str | None,
    extra_args: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    spec = ensure_spec_state(paths, entities, spec_id)
    if spec.get("status") not in {"todo", "ready", "blocked"}:
        raise ValidationError(f"spec {spec_id} is not exec-preparable from status {spec.get('status')}")
    if spec.get("open_gate_id"):
        raise ValidationError(f"spec {spec_id} is blocked by open gate {spec['open_gate_id']}")
    unmet = unmet_dependency_ids(spec, entities["specs"])
    if unmet:
        raise ValidationError(f"spec {spec_id} has unmet dependencies: {', '.join(unmet)}")
    if prompt_ref is not None and not (paths.root / prompt_ref).exists():
        raise ValidationError(f"prompt ref does not exist: {prompt_ref}")

    if spec.get("mode") == "serial":
        worktree = ensure_serial_worktree(paths, entities, spec_id)
        agent = ensure_main_agent(entities, spec_id, worktree["id"])
    elif spec.get("mode") == "parallel":
        active_worktree_id = spec.get("active_worktree_id")
        if not active_worktree_id:
            raise ValidationError(f"parallel spec {spec_id} requires provisioned worktree before exec prepare")
        worktree = entities["worktrees"].get(active_worktree_id)
        if worktree is None:
            raise ValidationError(f"parallel spec {spec_id} points to missing worktree {active_worktree_id}")
        agent = ensure_exec_agent(entities, spec_id, worktree["id"])
    else:
        raise ValidationError(f"exec prepare only supports serial or parallel specs: {spec_id}")

    current_session_id = spec.get("active_session_id")
    if current_session_id:
        current_session = entities["sessions"].get(current_session_id)
        if is_active_binding_session(current_session):
            raise ValidationError(f"spec {spec_id} already has active session {current_session_id}")

    command = render_exec_command(root=paths.root, mode="launch", prompt_ref=prompt_ref, extra_args=extra_args)
    session = create_session_record(
        entities,
        spec,
        agent_id=agent["id"],
        worktree_id=worktree["id"],
        launcher="exec",
        resume_mode=default_resume_mode(spec),
        started_from_session_id=None,
        execution_kind="exec",
        launch_status="prepared",
        launch_command=" ".join(command),
        launch_prompt_ref=prompt_ref,
        launch_args=extra_args,
    )
    session["status"] = "starting"
    session["checkpoint_written"] = False
    return spec, agent, worktree, session


def resume_exec_session(
    paths: Paths,
    entities: dict[str, Any],
    *,
    session_id: str,
    prompt_ref: str | None,
    extra_args: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_session = ensure_session(paths, entities, session_id)
    if source_session.get("resume_mode") != "exec_resume":
        raise ValidationError(f"session {session_id} is not eligible for exec_resume")
    if not source_session.get("resume_handle"):
        raise ValidationError(f"session {session_id} is missing resume_handle")
    if source_session.get("status") not in {"interrupted", "checkpointed", "waiting_human"}:
        raise ValidationError(f"session {session_id} is not resumable from status {source_session.get('status')}")
    if prompt_ref is not None and not (paths.root / prompt_ref).exists():
        raise ValidationError(f"prompt ref does not exist: {prompt_ref}")

    spec = entities["specs"].get(source_session["spec_id"])
    agent = entities["agents"].get(source_session["agent_id"])
    worktree = entities["worktrees"].get(source_session["worktree_id"])
    if spec is None or agent is None or worktree is None:
        raise ValidationError(f"session {session_id} has missing spec/agent/worktree linkage")
    if spec.get("open_gate_id"):
        raise ValidationError(f"spec {spec['id']} is blocked by open gate {spec['open_gate_id']}")
    unmet = unmet_dependency_ids(spec, entities["specs"])
    if unmet:
        raise ValidationError(f"spec {spec['id']} has unmet dependencies: {', '.join(unmet)}")

    command = render_exec_command(root=paths.root, mode="resume", prompt_ref=prompt_ref, session=source_session, extra_args=extra_args)

    # If a checkpoint rotated the spec to a successor session, resuming from the source
    # session should retire that successor binding before activating the resumed session.
    successor_session = next(
        (
            candidate
            for candidate in entities["sessions"].values()
            if candidate.get("started_from_session_id") == session_id
            and candidate.get("spec_id") == spec["id"]
            and candidate.get("agent_id") == agent["id"]
            and candidate.get("worktree_id") == worktree["id"]
            and candidate.get("status") in SESSION_ACTIVE_BINDING_STATUS
        ),
        None,
    )
    if successor_session is not None:
        successor_session["status"] = "abandoned"
        successor_session["stop_reason"] = "superseded_by_exec_resume"
        successor_session["updated_at"] = now_utc()

    successor = create_session_record(
        entities,
        spec,
        agent_id=agent["id"],
        worktree_id=worktree["id"],
        launcher="exec_resume",
        resume_mode="exec_resume",
        started_from_session_id=session_id,
        resume_handle=source_session["resume_handle"],
        execution_kind="exec",
        launch_status="resume_prepared",
        launch_command=" ".join(command),
        launch_prompt_ref=prompt_ref,
        launch_args=extra_args,
    )
    successor["status"] = "starting"
    successor["checkpoint_refs"] = session_resume_prompt_refs(source_session, spec)
    source_session["status"] = "checkpointed" if source_session.get("checkpoint_written") else "interrupted"
    source_session["updated_at"] = now_utc()
    return spec, agent, worktree, successor


def serial_worktree_path(root: Path, worktree_id: str) -> Path:
    return root.parent / ".worktrees" / root.name / worktree_id


def ensure_serial_worktree(paths: Paths, entities: dict[str, Any], spec_id: str) -> dict[str, Any]:
    worktree_id = "wt-main"
    worktree = entities["worktrees"].get(worktree_id)
    timestamp = now_utc()
    if worktree is None:
        worktree_path = serial_worktree_path(paths.root, worktree_id)
        worktree_path.mkdir(parents=True, exist_ok=True)
        branch = current_branch_name(paths.root)
        worktree = {
            "schema_version": SCHEMA_VERSION,
            "id": worktree_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "status": "active",
            "path": str(worktree_path),
            "branch": branch,
            "base_ref": branch,
            "owner_spec_id": spec_id,
            "current_session_id": None,
            "parallel_safe": False,
            "last_verified_clean_at": None,
            "notes": "",
        }
        entities["worktrees"][worktree_id] = worktree
        return worktree

    current_session_id = worktree.get("current_session_id")
    if current_session_id:
        current_session = entities["sessions"].get(current_session_id)
        if is_active_binding_session(current_session):
            raise ValidationError(f"worktree {worktree_id} is already bound to active session {current_session_id}")
    if worktree.get("status") in {"merged", "abandoned"}:
        raise ValidationError(f"worktree {worktree_id} is not reusable in status {worktree.get('status')}")
    worktree["status"] = "active"
    worktree["owner_spec_id"] = spec_id
    worktree["updated_at"] = timestamp
    return worktree


def ensure_main_agent(entities: dict[str, Any], spec_id: str, worktree_id: str) -> dict[str, Any]:
    agent_id = "agent-main"
    agent = entities["agents"].get(agent_id)
    timestamp = now_utc()
    if agent is None:
        agent = {
            "schema_version": SCHEMA_VERSION,
            "id": agent_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "role": "main",
            "status": "assigned",
            "owner_spec_id": spec_id,
            "current_session_id": None,
            "current_worktree_id": worktree_id,
            "parent_agent_id": None,
            "execution_kind": "interactive",
            "execution_session_origin": "",
            "notes": "",
        }
        entities["agents"][agent_id] = agent
        return agent

    current_session_id = agent.get("current_session_id")
    if current_session_id:
        current_session = entities["sessions"].get(current_session_id)
        if is_active_binding_session(current_session):
            raise ValidationError(f"agent {agent_id} is already bound to active session {current_session_id}")
    agent["status"] = "assigned"
    agent["owner_spec_id"] = spec_id
    agent["current_worktree_id"] = worktree_id
    agent["execution_session_origin"] = ""
    agent["updated_at"] = timestamp
    return agent


def ensure_exec_agent(entities: dict[str, Any], spec_id: str, worktree_id: str) -> dict[str, Any]:
    agent_id = unique_slug_id(list(entities["agents"].keys()), "agent", spec_id)
    timestamp = now_utc()
    agent = entities["agents"].get(agent_id)
    if agent is None:
        agent = {
            "schema_version": SCHEMA_VERSION,
            "id": agent_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "role": "child",
            "status": "assigned",
            "owner_spec_id": spec_id,
            "current_session_id": None,
            "current_worktree_id": worktree_id,
            "parent_agent_id": None,
            "execution_kind": "exec",
            "execution_session_origin": "",
            "notes": "",
        }
        entities["agents"][agent_id] = agent
        return agent
    current_session_id = agent.get("current_session_id")
    if current_session_id:
        current_session = entities["sessions"].get(current_session_id)
        if is_active_binding_session(current_session):
            raise ValidationError(f"agent {agent_id} is already bound to active session {current_session_id}")
    agent["status"] = "assigned"
    agent["owner_spec_id"] = spec_id
    agent["current_worktree_id"] = worktree_id
    agent["execution_kind"] = "exec"
    agent["execution_session_origin"] = ""
    agent["updated_at"] = timestamp
    return agent


def create_session_record(
    entities: dict[str, Any],
    spec: dict[str, Any],
    *,
    agent_id: str,
    worktree_id: str,
    launcher: str,
    resume_mode: str,
    started_from_session_id: str | None,
    resume_handle: str | None = None,
    execution_kind: str | None = None,
    launch_status: str = "none",
    launch_command: str = "",
    launch_prompt_ref: str | None = None,
    launch_args: list[str] | None = None,
    result_summary: str = "",
) -> dict[str, Any]:
    session_id = next_dated_id(list(entities["sessions"].keys()), "session")
    timestamp = now_utc()
    session = {
        "schema_version": SCHEMA_VERSION,
        "id": session_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "status": "running",
        "spec_id": spec["id"],
        "agent_id": agent_id,
        "worktree_id": worktree_id,
        "launcher": launcher,
        "resume_mode": resume_mode,
        "resume_handle": resume_handle,
        "started_from_session_id": started_from_session_id,
        "last_heartbeat_at": timestamp,
        "checkpoint_written": bool(started_from_session_id),
        "checkpoint_refs": default_checkpoint_refs(spec),
        "launch_status": launch_status,
        "launch_command": launch_command,
        "launch_prompt_ref": launch_prompt_ref,
        "launch_args": launch_args or [],
        "execution_kind": execution_kind or ("interactive" if launcher == "interactive" else "exec"),
        "result_summary": result_summary,
        "stop_reason": None,
        "subagent_evidence": [],
    }
    entities["sessions"][session_id] = session
    return session


def create_gate_record(
    entities: dict[str, Any],
    *,
    spec_id: str,
    session_id: str,
    kind: str,
    question: str,
    context_summary: str,
    options: list[str],
) -> dict[str, Any]:
    gate_id = next_dated_id(list(entities["gates"].keys()), "gate")
    timestamp = now_utc()
    gate = {
        "schema_version": SCHEMA_VERSION,
        "id": gate_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "status": "open",
        "kind": kind,
        "spec_id": spec_id,
        "session_id": session_id,
        "question": question,
        "context_summary": context_summary,
        "options": options,
        "resolution": None,
        "resolved_by": None,
        "resolved_at": None,
    }
    entities["gates"][gate_id] = gate
    return gate


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    ensure_dirs(paths)
    spec_path = active_spec_path_from_plan(root)
    spec_id = spec_path.stem if spec_path is not None else ""
    plan_path = root / ".codex" / "plan.md"
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""

    if spec_path is not None:
        spec_state_path = path_for_entity(paths, "spec", spec_id)
        if not spec_state_path.exists():
            spec_record = build_spec_record(paths, spec_id, spec_path, plan_text)
            validate_record(paths, "spec", spec_record, expected_id=spec_id)
            write_json(spec_state_path, spec_record)

    project_path = paths.state_dir / "project.json"
    if not project_path.exists():
        default_branch = git_output(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        if default_branch and default_branch.startswith("origin/"):
            default_branch = default_branch.split("/", 1)[1]
        if default_branch is None:
            default_branch = git_output(root, "branch", "--show-current") or "main"
        project = build_project_record(paths, spec_id, default_branch)
        validate_record(paths, "project", project, expected_id="project")
        write_json(project_path, project)
    elif spec_id:
        sync_project_to_active_spec(paths, spec_id)

    errors: list[str] = []
    for entity_type, path in iter_entity_files(paths):
        try:
            validate_entity_file(paths, path, entity_type)
        except ValidationError as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")

    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1

    print(f"Initialized state foundation at {paths.state_dir}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    if args.entity_type == "project" and args.entity_id == "summary":
        entities = load_entities(paths)
        payload = build_status_summary(paths, entities, stale_minutes=args.stale_minutes)
    else:
        payload = read_entity(paths, args.entity_type, args.entity_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_spec_create_child(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    ensure_dirs(paths)
    entities = load_entities(paths)

    parent_spec = ensure_spec_state(paths, entities, args.parent_spec_id)
    spec_path = root / args.spec_path
    if not spec_path.exists():
        raise ValidationError(f"child spec markdown does not exist: {args.spec_path}")
    if not str(spec_path.relative_to(root)).startswith(".codex/specs/"):
        raise ValidationError("child spec markdown must live under .codex/specs/")

    spec_id = args.spec_id or spec_path.stem
    if spec_id in entities["specs"]:
        raise ValidationError(f"spec {spec_id} already exists")

    dependency_spec_ids = dedupe_strings(args.dependency or [])
    for dep_id in dependency_spec_ids:
        ensure_spec_state(paths, entities, dep_id)

    verification_profile = args.verification_profile or parent_spec.get("verification_profile") or ".codex/verification-profiles/code-change.md"
    profile_path = root / verification_profile
    if not profile_path.exists():
        raise ValidationError(f"verification profile does not exist: {verification_profile}")

    spec_text = spec_path.read_text(encoding="utf-8")
    expected_outputs = dedupe_strings(args.expected_output or collect_expected_outputs(spec_text))
    if not expected_outputs:
        raise ValidationError("child spec requires at least one expected output")

    child_spec = create_child_spec_record(
        paths,
        entities,
        spec_id=spec_id,
        title=args.title or spec_title(spec_text, spec_id),
        spec_path=str(spec_path.relative_to(root)),
        verification_profile=verification_profile,
        parent_spec_id=args.parent_spec_id,
        dependency_spec_ids=dependency_spec_ids,
        mode=args.mode,
        expected_outputs=expected_outputs,
        summary=args.summary or "",
    )

    if args.mode == "parallel" and args.provision_worktree:
        ensure_parallel_worktree(
            paths,
            entities,
            spec_id=spec_id,
            worktree_id=args.worktree_id,
            branch=args.branch,
            base_ref=args.base_ref,
            notes=args.worktree_notes or "",
        )

    persist_entities(paths, entities, project_active_spec_id=args.parent_spec_id)
    print(json.dumps({"created_child_spec": summarize_spec(child_spec, entities["specs"])}, ensure_ascii=False, indent=2))
    return 0


def cmd_spec_update(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    spec = ensure_spec_state(paths, entities, args.spec_id)
    timestamp = now_utc()

    if args.status is not None:
        spec["status"] = args.status
    if args.summary is not None:
        spec["summary"] = args.summary
    if args.expected_output:
        spec["expected_outputs"] = dedupe_strings(args.expected_output)
    if args.dependency is not None:
        for dep_id in args.dependency:
            ensure_spec_state(paths, entities, dep_id)
        spec["dependency_spec_ids"] = dedupe_strings(args.dependency)
    if args.blocked_by is not None:
        for blocker_id in args.blocked_by:
            ensure_spec_state(paths, entities, blocker_id)
        spec["blocked_by_spec_ids"] = dedupe_strings(args.blocked_by)
    if spec.get("status") != "review" and spec.get("review_status") == "pending":
        spec["review_status"] = "none"
        spec["review_requested_at"] = None
    if args.status == "review":
        spec["review_status"] = "pending"
        spec["review_requested_at"] = timestamp
        spec["review_owner_spec_id"] = spec.get("review_owner_spec_id") or spec.get("parent_spec_id")
    spec["updated_at"] = timestamp

    persist_entities(paths, entities, project_active_spec_id=args.spec_id)
    print(json.dumps({"updated_spec": summarize_spec(spec, entities["specs"])}, ensure_ascii=False, indent=2))
    return 0


def cmd_review_request(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    spec = ensure_spec_state(paths, entities, args.spec_id)
    owner_spec = ensure_spec_state(paths, entities, args.owner_spec_id) if args.owner_spec_id else None
    if spec.get("status") not in {"ready", "blocked", "done"}:
        raise ValidationError(f"spec {args.spec_id} is not review-requestable from status {spec.get('status')}")
    timestamp = now_utc()
    request_spec_review(
        entities,
        spec,
        timestamp=timestamp,
        owner_spec_id=owner_spec["id"] if owner_spec else spec.get("parent_spec_id"),
        summary=args.summary or spec.get("summary", ""),
    )
    persist_entities(paths, entities, project_active_spec_id=(owner_spec or spec)["id"], project_active_session_id=None)
    print(
        json.dumps(
            {
                "requested_review": {
                    "spec_id": spec["id"],
                    "review_owner_spec_id": spec.get("review_owner_spec_id"),
                    "review_requested_at": spec.get("review_requested_at"),
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_review_resolve(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    child_spec = ensure_spec_state(paths, entities, args.spec_id)
    if child_spec.get("status") != "review" or child_spec.get("review_status") != "pending":
        raise ValidationError(f"spec {args.spec_id} is not pending review")
    owner_spec_id = args.owner_spec_id or child_spec.get("review_owner_spec_id") or child_spec.get("parent_spec_id")
    owner_spec = ensure_spec_state(paths, entities, owner_spec_id) if owner_spec_id else None
    followup_spec_id = args.followup_spec_id
    if followup_spec_id:
        ensure_spec_state(paths, entities, followup_spec_id)
    timestamp = now_utc()
    record = complete_spec_review(
        entities,
        child_spec=child_spec,
        owner_spec=owner_spec,
        decision=args.decision,
        decided_by=args.decided_by,
        summary=args.summary or "",
        timestamp=timestamp,
        followup_spec_id=followup_spec_id,
    )
    persist_entities(paths, entities, project_active_spec_id=(owner_spec or child_spec)["id"], project_active_session_id=None)
    print(
        json.dumps(
            {
                "resolved_review": {
                    "spec_id": child_spec["id"],
                    "owner_spec_id": owner_spec["id"] if owner_spec else None,
                    "decision": args.decision,
                    "record": record,
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_worktree_provision(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    ensure_dirs(paths)
    entities = load_entities(paths)

    worktree = ensure_parallel_worktree(
        paths,
        entities,
        spec_id=args.spec_id,
        worktree_id=args.worktree_id,
        branch=args.branch,
        base_ref=args.base_ref,
        notes=args.notes or "",
    )
    persist_entities(paths, entities, project_active_spec_id=args.spec_id)
    print(
        json.dumps(
            {
                "provisioned_worktree": {
                    "worktree_id": worktree["id"],
                    "spec_id": args.spec_id,
                    "path": worktree["path"],
                    "branch": worktree["branch"],
                    "base_ref": worktree["base_ref"],
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_exec_prepare(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    ensure_dirs(paths)
    entities = load_entities(paths)

    spec, agent, worktree, session = prepare_exec_session(
        paths,
        entities,
        spec_id=args.spec_id,
        prompt_ref=args.prompt_ref,
        extra_args=args.arg or [],
    )
    timestamp = now_utc()
    spec["assigned_agent_id"] = agent["id"]
    spec["active_session_id"] = session["id"]
    spec["active_worktree_id"] = worktree["id"]
    spec["updated_at"] = timestamp
    agent["status"] = "assigned"
    agent["current_session_id"] = session["id"]
    agent["current_worktree_id"] = worktree["id"]
    agent["execution_kind"] = "exec"
    agent["updated_at"] = timestamp
    worktree["owner_spec_id"] = spec["id"]
    worktree["updated_at"] = timestamp

    persist_entities(paths, entities, project_active_spec_id=args.spec_id, project_active_session_id=None)
    print(
        json.dumps(
            {
                "prepared_exec": {
                    "spec_id": spec["id"],
                    "session_id": session["id"],
                    "agent_id": agent["id"],
                    "worktree_id": worktree["id"],
                    "launch_command": session["launch_command"],
                    "launch_prompt_ref": session["launch_prompt_ref"],
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_exec_launch(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    session = entities["sessions"].get(args.session_id)
    if session is None:
        raise ValidationError(f"unknown session: {args.session_id}")
    if session.get("launcher") != "exec":
        raise ValidationError(f"session {args.session_id} was not prepared for exec launch")
    if session.get("launch_status") not in {"prepared", "failed"}:
        raise ValidationError(f"session {args.session_id} is not launchable from state {session.get('launch_status')}")

    spec = entities["specs"].get(session["spec_id"])
    agent = entities["agents"].get(session["agent_id"])
    worktree = entities["worktrees"].get(session["worktree_id"])
    if spec is None or agent is None or worktree is None:
        raise ValidationError(f"session {args.session_id} has missing spec/agent/worktree linkage")

    timestamp = now_utc()
    session["status"] = "running"
    session["launch_status"] = "launched"
    session["updated_at"] = timestamp
    session["last_heartbeat_at"] = timestamp
    if args.resume_handle:
        session["resume_handle"] = args.resume_handle
        session["resume_mode"] = "exec_resume"

    activate_session_binding(entities=entities, spec=spec, agent=agent, worktree=worktree, session=session, timestamp=timestamp)
    persist_entities(paths, entities, project_active_spec_id=spec["id"], project_active_session_id=session["id"])
    print(
        json.dumps(
            {
                "launched_exec": {
                    "spec_id": spec["id"],
                    "session_id": session["id"],
                    "resume_handle": session.get("resume_handle"),
                    "launch_command": session["launch_command"],
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_exec_resume(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)

    spec, agent, worktree, session = resume_exec_session(
        paths,
        entities,
        session_id=args.session_id,
        prompt_ref=args.prompt_ref,
        extra_args=args.arg or [],
    )
    timestamp = now_utc()
    session["status"] = "running"
    session["launch_status"] = "resumed"
    session["updated_at"] = timestamp
    session["last_heartbeat_at"] = timestamp
    activate_session_binding(entities=entities, spec=spec, agent=agent, worktree=worktree, session=session, timestamp=timestamp)
    persist_entities(paths, entities, project_active_spec_id=spec["id"], project_active_session_id=session["id"])
    print(
        json.dumps(
            {
                "resumed_exec": {
                    "spec_id": spec["id"],
                    "session_id": session["id"],
                    "resume_handle": session["resume_handle"],
                    "launch_command": session["launch_command"],
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_subagent_record(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    session = ensure_session(paths, entities, args.session_id)
    spec = entities["specs"][session["spec_id"]]
    timestamp = now_utc()
    checkpoint_refs = dedupe_strings(args.ref or session.get("checkpoint_refs") or default_checkpoint_refs(spec))
    for ref in checkpoint_refs:
        if not (paths.root / ref).exists():
            raise ValidationError(f"subagent evidence ref does not exist: {ref}")

    evidence = {
        "id": unique_slug_id([item["id"] for item in session.get("subagent_evidence", [])], "subagent", args.summary),
        "summary": args.summary,
        "recorded_at": timestamp,
        "checkpoint_refs": checkpoint_refs,
    }
    session.setdefault("subagent_evidence", []).append(evidence)
    session["updated_at"] = timestamp
    session["last_heartbeat_at"] = timestamp
    if args.append_summary:
        existing = session.get("result_summary", "")
        session["result_summary"] = (existing + "\n" if existing else "") + f"[subagent] {args.summary}"
    if args.spec_summary:
        current = spec.get("summary", "")
        spec["summary"] = (current + "\n" if current else "") + f"[subagent] {args.spec_summary}"
    spec["updated_at"] = timestamp

    persist_entities(paths, entities, project_active_spec_id=spec["id"], project_active_session_id=(entities["project"] or {}).get("active_session_id"))
    print(json.dumps({"recorded_subagent": evidence, "session_id": session["id"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_upsert(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    ensure_dirs(paths)
    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    payload = parse_json(raw)
    if payload.get("id") != args.entity_id:
        raise ValidationError(f"payload id must match entity id {args.entity_id}")
    target = path_for_entity(paths, args.entity_type, args.entity_id)
    validate_record(paths, args.entity_type, payload, expected_id=args.entity_id)
    write_json(target, payload)
    print(f"Upserted {args.entity_type}:{args.entity_id}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    errors = collect_validation_errors(paths, entities)
    if errors:
        print("State validation failed:")
        for item in errors:
            print(f"- {item}")
        return 1
    print(f"State validation passed for {paths.state_dir}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    payload = build_doctor_report(paths, entities, stale_minutes=args.stale_minutes)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    payload = build_status_summary(paths, entities, stale_minutes=args.stale_minutes)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_recover(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    payload = analyze_recovery(paths, entities, stale_minutes=args.stale_minutes)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    ensure_dirs(paths)
    entities = load_entities(paths)
    spec = ensure_spec_state(paths, entities, args.spec_id)

    if spec.get("mode") != "serial":
        raise ValidationError(f"start only supports serial specs in Phase 3: {args.spec_id}")
    if spec.get("status") not in {"todo", "ready", "running"}:
        raise ValidationError(f"spec {args.spec_id} is not startable from status {spec.get('status')}")
    if spec.get("open_gate_id"):
        raise ValidationError(f"spec {args.spec_id} is blocked by open gate {spec['open_gate_id']}")
    unmet = unmet_dependency_ids(spec, entities["specs"])
    if unmet:
        raise ValidationError(f"spec {args.spec_id} has unmet dependencies: {', '.join(unmet)}")
    if spec.get("active_session_id"):
        existing = entities["sessions"].get(spec["active_session_id"])
        if is_active_binding_session(existing):
            raise ValidationError(f"spec {args.spec_id} already has active session {spec['active_session_id']}")

    worktree = ensure_serial_worktree(paths, entities, args.spec_id)
    agent = ensure_main_agent(entities, args.spec_id, worktree["id"])
    session = create_session_record(
        entities,
        spec,
        agent_id=agent["id"],
        worktree_id=worktree["id"],
        launcher=args.launcher,
        resume_mode=default_resume_mode(spec),
        started_from_session_id=None,
    )

    timestamp = now_utc()
    spec["status"] = "running"
    spec["assigned_agent_id"] = agent["id"]
    spec["active_session_id"] = session["id"]
    spec["active_worktree_id"] = worktree["id"]
    spec["checkpoint_status"] = "missing"
    spec["last_checkpoint_at"] = None
    spec["updated_at"] = timestamp

    agent["status"] = "running"
    agent["current_session_id"] = session["id"]
    agent["current_worktree_id"] = worktree["id"]
    agent["updated_at"] = timestamp

    worktree["status"] = "active"
    worktree["owner_spec_id"] = args.spec_id
    worktree["current_session_id"] = session["id"]
    worktree["updated_at"] = timestamp

    persist_entities(
        paths,
        entities,
        project_active_spec_id=args.spec_id,
        project_active_session_id=session["id"],
    )
    print(
        json.dumps(
            {
                "started": {
                    "spec_id": args.spec_id,
                    "agent_id": agent["id"],
                    "worktree_id": worktree["id"],
                    "session_id": session["id"],
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    session = entities["sessions"].get(args.session_id)
    if session is None:
        raise ValidationError(f"unknown session: {args.session_id}")
    if session.get("status") != "running":
        raise ValidationError(f"session {args.session_id} is not running")

    spec_id = session["spec_id"]
    spec = entities["specs"].get(spec_id)
    if spec is None:
        raise ValidationError(f"session {args.session_id} points to missing spec {spec_id}")
    if spec.get("active_session_id") != args.session_id:
        raise ValidationError(f"session {args.session_id} is not the active session for spec {spec_id}")
    if spec.get("mode") != "serial":
        raise ValidationError(f"checkpoint only supports serial specs in Phase 3: {spec_id}")

    agent = entities["agents"].get(session["agent_id"])
    worktree = entities["worktrees"].get(session["worktree_id"])
    if agent is None or worktree is None:
        raise ValidationError(f"session {args.session_id} has missing agent or worktree linkage")

    heartbeat = now_utc()
    checkpoint_refs = dedupe_strings(args.ref or default_checkpoint_refs(spec))
    for ref in checkpoint_refs:
        if not (paths.root / ref).exists():
            raise ValidationError(f"checkpoint ref does not exist: {ref}")

    session["status"] = "checkpointed"
    session["updated_at"] = heartbeat
    session["last_heartbeat_at"] = heartbeat
    session["checkpoint_written"] = True
    session["checkpoint_refs"] = checkpoint_refs
    session["result_summary"] = args.summary or session.get("result_summary", "")
    session["stop_reason"] = "checkpoint"

    spec["checkpoint_status"] = "fresh"
    spec["last_checkpoint_at"] = heartbeat
    spec["updated_at"] = heartbeat

    successor = create_session_record(
        entities,
        spec,
        agent_id=agent["id"],
        worktree_id=worktree["id"],
        launcher=args.successor_launcher,
        resume_mode=default_resume_mode(spec),
        started_from_session_id=args.session_id,
        result_summary="",
    )
    successor["checkpoint_written"] = True
    successor["checkpoint_refs"] = checkpoint_refs

    spec["status"] = "running"
    spec["active_session_id"] = successor["id"]

    agent["status"] = "running"
    agent["current_session_id"] = successor["id"]
    agent["updated_at"] = heartbeat

    worktree["status"] = "active"
    worktree["current_session_id"] = successor["id"]
    worktree["updated_at"] = heartbeat

    persist_entities(
        paths,
        entities,
        project_active_spec_id=spec_id,
        project_active_session_id=successor["id"],
    )
    print(
        json.dumps(
            {
                "checkpointed": {
                    "previous_session_id": args.session_id,
                    "successor_session_id": successor["id"],
                    "spec_id": spec_id,
                    "checkpoint_refs": checkpoint_refs,
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    recovery = analyze_recovery(paths, entities, stale_minutes=args.stale_minutes)

    choice: dict[str, Any] | None = None
    if recovery["open_gates"]:
        gate = recovery["open_gates"][0]
        choice = {
            "kind": "resolve_open_gate",
            "target_id": gate["gate_id"],
            "spec_id": gate["spec_id"],
            "reason": "open gate blocks automatic progression",
        }
    elif recovery["interrupted_sessions"]:
        session = recovery["interrupted_sessions"][0]
        choice = {
            "kind": "recover_session",
            "target_id": session["session_id"],
            "spec_id": session["spec_id"],
            "reason": f"interrupted session requires {session['recommended_recovery']}",
        }
    elif recovery["review_backlog_by_owner"]:
        backlog = next((item for item in recovery["review_backlog_by_owner"] if item["pending_child_spec_ids"]), None)
        if backlog:
            choice = {
                "kind": "converge_review_backlog",
                "target_id": backlog["owner_spec_id"],
                "spec_id": backlog["owner_spec_id"],
                "reason": f"child reviews are pending: {', '.join(backlog['pending_child_spec_ids'])}",
            }
    else:
        ready_specs = [item for item in recovery["ready_specs"] if entities["specs"][item["spec_id"]].get("mode") == "serial"]
        parallel_ready_specs = [item for item in recovery["ready_specs"] if entities["specs"][item["spec_id"]].get("mode") == "parallel"]
        if recovery["review_specs"]:
            spec = recovery["review_specs"][0]
            choice = {
                "kind": "review_spec",
                "target_id": spec["spec_id"],
                "spec_id": spec["spec_id"],
                "reason": "review item is the next convergence obligation",
            }
        elif ready_specs:
            spec = ready_specs[0]
            launch_kind = "prepare_exec_spec" if spec.get("mode") == "serial" else "prepare_parallel_spec"
            choice = {
                "kind": launch_kind,
                "target_id": spec["spec_id"],
                "spec_id": spec["spec_id"],
                "reason": "serial spec is ready and dependencies are satisfied",
            }
        elif parallel_ready_specs:
            spec = parallel_ready_specs[0]
            worktree_id = entities["specs"][spec["spec_id"]].get("active_worktree_id")
            choice = {
                "kind": "prepare_parallel_spec",
                "target_id": spec["spec_id"],
                "spec_id": spec["spec_id"],
                "reason": "parallel spec is ready; provision worktree and execution lane before launch",
                "active_worktree_id": worktree_id,
            }
    payload = {
        "project_active_spec_id": (entities["project"] or {}).get("active_spec_id"),
        "recommended_action": choice,
        "recovery_summary": {
            "open_gate_count": len(recovery["open_gates"]),
            "interrupted_session_count": len(recovery["interrupted_sessions"]),
            "review_backlog_count": len(recovery["review_specs"]),
            "ready_spec_count": len(recovery["ready_specs"]),
            "dependency_blocked_spec_count": len(recovery["dependency_blocked_specs"]),
            "parallel_worktree_conflict_count": len(recovery["parallel_worktree_conflicts"]),
            "review_spec_count": len(recovery["review_specs"]),
        },
        "recommended_actions": recovery["recommended_actions"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_gate_open(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    spec = ensure_spec_state(paths, entities, args.spec_id)

    if spec.get("mode") != "serial":
        raise ValidationError(f"gate open only supports serial specs in Phase 4: {args.spec_id}")
    if spec.get("open_gate_id"):
        raise ValidationError(f"spec {args.spec_id} already has open gate {spec['open_gate_id']}")
    if spec.get("status") != "running":
        raise ValidationError(f"spec {args.spec_id} must be running before opening a gate")
    session_id = spec.get("active_session_id")
    if not session_id:
        raise ValidationError(f"spec {args.spec_id} has no active session")
    session = ensure_session(paths, entities, session_id)
    if session.get("status") != "running":
        raise ValidationError(f"active session {session_id} is not running")

    options = dedupe_strings(args.option or [])
    if not options:
        raise ValidationError("gate open requires at least one --option")

    gate = create_gate_record(
        entities,
        spec_id=args.spec_id,
        session_id=session_id,
        kind=args.kind,
        question=args.question,
        context_summary=args.context_summary or "",
        options=options,
    )

    timestamp = gate["created_at"]
    spec["status"] = "waiting_human"
    spec["open_gate_id"] = gate["id"]
    spec["updated_at"] = timestamp

    session["status"] = "waiting_human"
    session["stop_reason"] = f"gate:{gate['id']}"
    session["updated_at"] = timestamp
    session["last_heartbeat_at"] = timestamp

    agent = entities["agents"][session["agent_id"]]
    agent["status"] = "waiting_human"
    agent["updated_at"] = timestamp

    persist_entities(
        paths,
        entities,
        project_active_spec_id=args.spec_id,
        project_active_session_id=session_id,
    )
    print(
        json.dumps(
            {
                "opened_gate": {
                    "gate_id": gate["id"],
                    "spec_id": args.spec_id,
                    "session_id": session_id,
                    "kind": gate["kind"],
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_gate_resolve(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    gate = entities["gates"].get(args.gate_id)
    if gate is None:
        raise ValidationError(f"unknown gate: {args.gate_id}")
    if gate.get("status") != "open":
        raise ValidationError(f"gate {args.gate_id} is not open")

    spec_id = gate["spec_id"]
    session_id = gate["session_id"]
    spec = entities["specs"].get(spec_id)
    session = ensure_session(paths, entities, session_id)
    if spec is None:
        raise ValidationError(f"gate {args.gate_id} points to missing spec {spec_id}")
    if spec.get("open_gate_id") != args.gate_id:
        raise ValidationError(f"spec {spec_id} is not bound to open gate {args.gate_id}")

    spec_status, session_status = gate_resolution_to_status(args.resolution)
    timestamp = now_utc()

    gate["status"] = "resolved"
    gate["resolution"] = args.resolution
    gate["resolved_by"] = args.resolved_by
    gate["resolved_at"] = timestamp
    gate["updated_at"] = timestamp

    spec["status"] = spec_status
    spec["open_gate_id"] = None
    spec["updated_at"] = timestamp

    session["status"] = session_status
    session["updated_at"] = timestamp
    session["last_heartbeat_at"] = timestamp
    session["stop_reason"] = None if session_status == "running" else f"gate_resolved:{args.resolution}"

    agent = entities["agents"][session["agent_id"]]
    if session_status == "running":
        agent["status"] = "running"
        agent["current_session_id"] = session_id
    else:
        agent["status"] = "paused" if spec_status == "ready" else "completed"
    agent["updated_at"] = timestamp

    worktree = entities["worktrees"][session["worktree_id"]]
    if spec_status == "cancelled":
        worktree["status"] = "abandoned"
        worktree["current_session_id"] = None
    else:
        worktree["status"] = "active"
        worktree["current_session_id"] = session_id
    worktree["updated_at"] = timestamp

    project_active_session_id = session_id if spec_status == "running" else None
    persist_entities(
        paths,
        entities,
        project_active_spec_id=spec_id,
        project_active_session_id=project_active_session_id,
    )
    print(
        json.dumps(
            {
                "resolved_gate": {
                    "gate_id": args.gate_id,
                    "resolution": args.resolution,
                    "spec_status": spec_status,
                    "session_status": session_status,
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_hook_heartbeat(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    session = ensure_session(paths, entities, args.session_id)
    if session.get("status") not in {"running", "waiting_human"}:
        raise ValidationError(f"heartbeat only supports running or waiting_human sessions: {args.session_id}")

    timestamp = now_utc()
    session["last_heartbeat_at"] = timestamp
    session["updated_at"] = timestamp
    if args.summary:
        session["result_summary"] = args.summary

    spec = entities["specs"][session["spec_id"]]
    spec["updated_at"] = timestamp

    persist_entities(
        paths,
        entities,
        project_active_spec_id=spec["id"],
        project_active_session_id=session["id"] if session.get("status") == "running" else (entities["project"] or {}).get("active_session_id"),
    )
    print(json.dumps({"hook": "heartbeat", "session_id": args.session_id, "updated_at": timestamp}, ensure_ascii=False, indent=2))
    return 0


def cmd_hook_checkpoint(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    session = ensure_session(paths, entities, args.session_id)
    if session.get("status") not in {"running", "waiting_human"}:
        raise ValidationError(f"hook checkpoint only supports running or waiting_human sessions: {args.session_id}")

    timestamp = now_utc()
    spec = entities["specs"][session["spec_id"]]
    checkpoint_refs = dedupe_strings(args.ref or session.get("checkpoint_refs") or default_checkpoint_refs(spec))
    for ref in checkpoint_refs:
        if not (paths.root / ref).exists():
            raise ValidationError(f"checkpoint ref does not exist: {ref}")

    session["checkpoint_written"] = True
    session["checkpoint_refs"] = checkpoint_refs
    session["last_heartbeat_at"] = timestamp
    session["updated_at"] = timestamp
    if args.summary:
        session["result_summary"] = args.summary

    spec["checkpoint_status"] = "fresh"
    spec["last_checkpoint_at"] = timestamp
    spec["updated_at"] = timestamp

    persist_entities(
        paths,
        entities,
        project_active_spec_id=spec["id"],
        project_active_session_id=(entities["project"] or {}).get("active_session_id"),
    )
    print(
        json.dumps(
            {"hook": "checkpoint", "session_id": args.session_id, "checkpoint_refs": checkpoint_refs, "updated_at": timestamp},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_hook_stop(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = build_paths(root)
    entities = load_entities(paths)
    session = ensure_session(paths, entities, args.session_id)
    if session.get("status") in SESSION_TERMINAL_STATUS and session.get("status") != "checkpointed":
        raise ValidationError(f"session {args.session_id} is already terminal in status {session['status']}")
    if args.status not in {"completed", "failed", "abandoned"}:
        raise ValidationError(f"unsupported stop status: {args.status}")

    timestamp = now_utc()
    spec = entities["specs"][session["spec_id"]]
    agent = entities["agents"][session["agent_id"]]
    worktree = entities["worktrees"][session["worktree_id"]]

    session["status"] = args.status
    session["stop_reason"] = args.reason
    session["updated_at"] = timestamp
    session["last_heartbeat_at"] = timestamp
    if args.summary:
        session["result_summary"] = args.summary

    if spec.get("active_session_id") == args.session_id:
        spec["active_session_id"] = None
        if args.status == "completed":
            if spec.get("parent_spec_id") or args.review_owner_spec_id:
                request_spec_review(
                    entities,
                    spec,
                    timestamp=timestamp,
                    owner_spec_id=args.review_owner_spec_id or spec.get("parent_spec_id"),
                    summary=args.summary or session.get("result_summary", ""),
                )
            else:
                spec["status"] = "done"
                spec["review_status"] = "none"
        elif args.status == "failed":
            spec["status"] = "blocked"
            spec["review_status"] = "none"
        else:
            spec["status"] = "cancelled"
            spec["review_status"] = "none"
        spec["updated_at"] = timestamp

    if agent.get("current_session_id") == args.session_id:
        agent["current_session_id"] = None
    agent["status"] = "completed" if args.status == "completed" else "failed"
    agent["updated_at"] = timestamp

    if worktree.get("current_session_id") == args.session_id:
        worktree["current_session_id"] = None
    if args.status == "abandoned":
        worktree["status"] = "abandoned"
    elif spec.get("status") == "review":
        worktree["status"] = "review_dirty"
    worktree["updated_at"] = timestamp

    persist_entities(
        paths,
        entities,
        project_active_spec_id=spec["id"],
        project_active_session_id=None,
    )
    print(
        json.dumps(
            {"hook": "stop", "session_id": args.session_id, "status": args.status, "updated_at": timestamp},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="continuous-work state foundation tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize the state directory")
    init_parser.add_argument("--root", default=".", help="repo root")
    init_parser.set_defaults(func=cmd_init)

    show_parser = subparsers.add_parser("show", help="show an entity record")
    show_parser.add_argument("--root", default=".", help="repo root")
    show_parser.add_argument("--stale-minutes", type=int, default=DEFAULT_STALE_MINUTES, help="stale-session threshold in minutes")
    show_parser.add_argument("entity_type", choices=sorted(ENTITY_DIRS))
    show_parser.add_argument("entity_id")
    show_parser.set_defaults(func=cmd_show)

    spec_parser = subparsers.add_parser("spec", help="manage durable spec orchestration state")
    spec_subparsers = spec_parser.add_subparsers(dest="spec_command", required=True)

    spec_create_child_parser = spec_subparsers.add_parser("create-child", help="register a child spec and optional parallel worktree binding")
    spec_create_child_parser.add_argument("--root", default=".", help="repo root")
    spec_create_child_parser.add_argument("--spec-id", help="override spec id; defaults to markdown filename stem")
    spec_create_child_parser.add_argument("--title", help="override spec title")
    spec_create_child_parser.add_argument("--verification-profile", help="verification profile path relative to repo root")
    spec_create_child_parser.add_argument("--dependency", action="append", help="dependency spec id; repeatable")
    spec_create_child_parser.add_argument("--expected-output", action="append", help="expected output; repeatable")
    spec_create_child_parser.add_argument("--summary", default="", help="initial spec summary")
    spec_create_child_parser.add_argument("--mode", choices=sorted(SPEC_MODE), required=True, help="execution mode for the child spec")
    spec_create_child_parser.add_argument("--provision-worktree", action="store_true", help="create a parallel-safe worktree immediately")
    spec_create_child_parser.add_argument("--worktree-id", help="explicit worktree id")
    spec_create_child_parser.add_argument("--branch", help="worktree branch name")
    spec_create_child_parser.add_argument("--base-ref", help="worktree base ref")
    spec_create_child_parser.add_argument("--worktree-notes", default="", help="optional worktree notes")
    spec_create_child_parser.add_argument("parent_spec_id")
    spec_create_child_parser.add_argument("spec_path")
    spec_create_child_parser.set_defaults(func=cmd_spec_create_child)

    spec_update_parser = spec_subparsers.add_parser("update", help="update durable spec state fields relevant to orchestration")
    spec_update_parser.add_argument("--root", default=".", help="repo root")
    spec_update_parser.add_argument("--status", choices=sorted(SPEC_STATUS), help="new spec status")
    spec_update_parser.add_argument("--summary", help="replace spec summary")
    spec_update_parser.add_argument("--expected-output", action="append", help="replace expected outputs; repeatable")
    spec_update_parser.add_argument("--dependency", action="append", help="replace dependency spec ids; repeatable")
    spec_update_parser.add_argument("--blocked-by", action="append", help="replace blocker spec ids; repeatable")
    spec_update_parser.add_argument("spec_id")
    spec_update_parser.set_defaults(func=cmd_spec_update)

    review_parser = subparsers.add_parser("review", help="manage review and convergence state")
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)

    review_request_parser = review_subparsers.add_parser("request", help="move a finished or paused spec into durable review state")
    review_request_parser.add_argument("--root", default=".", help="repo root")
    review_request_parser.add_argument("--owner-spec-id", help="spec that should consume this review item")
    review_request_parser.add_argument("--summary", default="", help="initial convergence summary")
    review_request_parser.add_argument("spec_id")
    review_request_parser.set_defaults(func=cmd_review_request)

    review_resolve_parser = review_subparsers.add_parser("resolve", help="record an explicit convergence decision for a review item")
    review_resolve_parser.add_argument("--root", default=".", help="repo root")
    review_resolve_parser.add_argument("--owner-spec-id", help="spec consuming the review item; defaults to recorded owner")
    review_resolve_parser.add_argument("--decision", choices=sorted(REVIEW_DECISIONS), required=True, help="convergence decision")
    review_resolve_parser.add_argument("--decided-by", required=True, help="reviewer or owner identity")
    review_resolve_parser.add_argument("--summary", default="", help="convergence summary")
    review_resolve_parser.add_argument("--followup-spec-id", help="optional follow-up spec linked to this decision")
    review_resolve_parser.add_argument("spec_id")
    review_resolve_parser.set_defaults(func=cmd_review_resolve)

    upsert_parser = subparsers.add_parser("upsert", help="validate and write an entity record")
    upsert_parser.add_argument("--root", default=".", help="repo root")
    upsert_parser.add_argument("entity_type", choices=sorted(ENTITY_DIRS))
    upsert_parser.add_argument("entity_id")
    upsert_parser.add_argument("--file", help="JSON payload file; defaults to stdin")
    upsert_parser.set_defaults(func=cmd_upsert)

    validate_parser = subparsers.add_parser("validate", help="validate all state records")
    validate_parser.add_argument("--root", default=".", help="repo root")
    validate_parser.set_defaults(func=cmd_validate)

    doctor_parser = subparsers.add_parser("doctor", help="audit loop health and actionable reliability findings")
    doctor_parser.add_argument("--root", default=".", help="repo root")
    doctor_parser.add_argument("--stale-minutes", type=int, default=DEFAULT_STALE_MINUTES, help="stale-session threshold in minutes")
    doctor_parser.set_defaults(func=cmd_doctor)

    status_parser = subparsers.add_parser("status", help="summarize project state")
    status_parser.add_argument("--root", default=".", help="repo root")
    status_parser.add_argument("--stale-minutes", type=int, default=DEFAULT_STALE_MINUTES, help="stale-session threshold in minutes")
    status_parser.set_defaults(func=cmd_status)

    recover_parser = subparsers.add_parser("recover", help="inspect recoverability and anomalies")
    recover_parser.add_argument("--root", default=".", help="repo root")
    recover_parser.add_argument("--stale-minutes", type=int, default=DEFAULT_STALE_MINUTES, help="stale-session threshold in minutes")
    recover_parser.set_defaults(func=cmd_recover)

    start_parser = subparsers.add_parser("start", help="start a ready serial spec")
    start_parser.add_argument("--root", default=".", help="repo root")
    start_parser.add_argument("--launcher", choices=sorted(SESSION_LAUNCHER), default="interactive", help="session launcher kind")
    start_parser.add_argument("spec_id")
    start_parser.set_defaults(func=cmd_start)

    checkpoint_parser = subparsers.add_parser("checkpoint", help="checkpoint a running serial session and rotate to a successor session")
    checkpoint_parser.add_argument("--root", default=".", help="repo root")
    checkpoint_parser.add_argument("--ref", action="append", help="checkpoint ref path relative to repo root; repeatable")
    checkpoint_parser.add_argument("--summary", default="", help="result summary for the completed session")
    checkpoint_parser.add_argument(
        "--successor-launcher",
        choices=sorted(SESSION_LAUNCHER),
        default="interactive",
        help="launcher kind for the successor session",
    )
    checkpoint_parser.add_argument("session_id")
    checkpoint_parser.set_defaults(func=cmd_checkpoint)

    exec_parser = subparsers.add_parser("exec", help="manage execution-plane launch and resume state")
    exec_subparsers = exec_parser.add_subparsers(dest="exec_command", required=True)

    exec_prepare_parser = exec_subparsers.add_parser("prepare", help="prepare an exec-backed session from durable spec state")
    exec_prepare_parser.add_argument("--root", default=".", help="repo root")
    exec_prepare_parser.add_argument("--prompt-ref", help="path to launch prompt relative to repo root")
    exec_prepare_parser.add_argument("--arg", action="append", help="extra arg to append to codex exec command; repeatable")
    exec_prepare_parser.add_argument("spec_id")
    exec_prepare_parser.set_defaults(func=cmd_exec_prepare)

    exec_launch_parser = exec_subparsers.add_parser("launch", help="mark a prepared exec session as launched")
    exec_launch_parser.add_argument("--root", default=".", help="repo root")
    exec_launch_parser.add_argument("--resume-handle", help="durable resume handle returned by external execution")
    exec_launch_parser.add_argument("session_id")
    exec_launch_parser.set_defaults(func=cmd_exec_launch)

    exec_resume_parser = exec_subparsers.add_parser("resume", help="create and activate a successor session via exec resume")
    exec_resume_parser.add_argument("--root", default=".", help="repo root")
    exec_resume_parser.add_argument("--prompt-ref", help="path to resume prompt relative to repo root")
    exec_resume_parser.add_argument("--arg", action="append", help="extra arg to append to codex exec resume command; repeatable")
    exec_resume_parser.add_argument("session_id")
    exec_resume_parser.set_defaults(func=cmd_exec_resume)

    subagent_parser = subparsers.add_parser("subagent", help="record bounded subagent evidence")
    subagent_subparsers = subagent_parser.add_subparsers(dest="subagent_command", required=True)

    subagent_record_parser = subagent_subparsers.add_parser("record", help="record bounded subagent evidence on an owning session")
    subagent_record_parser.add_argument("--root", default=".", help="repo root")
    subagent_record_parser.add_argument("--ref", action="append", help="checkpoint ref relative to repo root; repeatable")
    subagent_record_parser.add_argument("--append-summary", action="store_true", help="append evidence to session result_summary")
    subagent_record_parser.add_argument("--spec-summary", default="", help="optional spec summary note to append")
    subagent_record_parser.add_argument("session_id")
    subagent_record_parser.add_argument("summary")
    subagent_record_parser.set_defaults(func=cmd_subagent_record)

    worktree_parser = subparsers.add_parser("worktree", help="manage durable worktree state")
    worktree_subparsers = worktree_parser.add_subparsers(dest="worktree_command", required=True)

    worktree_provision_parser = worktree_subparsers.add_parser("provision", help="provision a parallel-safe worktree for a child spec")
    worktree_provision_parser.add_argument("--root", default=".", help="repo root")
    worktree_provision_parser.add_argument("--worktree-id", help="explicit worktree id")
    worktree_provision_parser.add_argument("--branch", help="worktree branch name")
    worktree_provision_parser.add_argument("--base-ref", help="worktree base ref")
    worktree_provision_parser.add_argument("--notes", default="", help="optional worktree notes")
    worktree_provision_parser.add_argument("spec_id")
    worktree_provision_parser.set_defaults(func=cmd_worktree_provision)

    next_parser = subparsers.add_parser("next", help="choose the next recommended serial control action")
    next_parser.add_argument("--root", default=".", help="repo root")
    next_parser.add_argument("--stale-minutes", type=int, default=DEFAULT_STALE_MINUTES, help="stale-session threshold in minutes")
    next_parser.set_defaults(func=cmd_next)

    gate_parser = subparsers.add_parser("gate", help="manage human gates")
    gate_subparsers = gate_parser.add_subparsers(dest="gate_command", required=True)

    gate_open_parser = gate_subparsers.add_parser("open", help="open a gate for a running serial spec")
    gate_open_parser.add_argument("--root", default=".", help="repo root")
    gate_open_parser.add_argument("--kind", choices=sorted(GATE_KIND), required=True, help="gate kind")
    gate_open_parser.add_argument("--question", required=True, help="human review question")
    gate_open_parser.add_argument("--context-summary", default="", help="optional gate context summary")
    gate_open_parser.add_argument("--option", action="append", help="resolution option; repeatable", required=True)
    gate_open_parser.add_argument("spec_id")
    gate_open_parser.set_defaults(func=cmd_gate_open)

    gate_resolve_parser = gate_subparsers.add_parser("resolve", help="resolve an open gate")
    gate_resolve_parser.add_argument("--root", default=".", help="repo root")
    gate_resolve_parser.add_argument("--resolution", choices=["return_ready", "continue_running", "cancel_spec"], required=True)
    gate_resolve_parser.add_argument("--resolved-by", required=True, help="resolver identity")
    gate_resolve_parser.add_argument("gate_id")
    gate_resolve_parser.set_defaults(func=cmd_gate_resolve)

    hook_parser = subparsers.add_parser("hook", help="write lifecycle state from repo-local hooks")
    hook_subparsers = hook_parser.add_subparsers(dest="hook_command", required=True)

    hook_heartbeat_parser = hook_subparsers.add_parser("heartbeat", help="refresh session heartbeat")
    hook_heartbeat_parser.add_argument("--root", default=".", help="repo root")
    hook_heartbeat_parser.add_argument("--summary", default="", help="optional session summary update")
    hook_heartbeat_parser.add_argument("session_id")
    hook_heartbeat_parser.set_defaults(func=cmd_hook_heartbeat)

    hook_checkpoint_parser = hook_subparsers.add_parser("checkpoint", help="refresh checkpoint metadata without session rotation")
    hook_checkpoint_parser.add_argument("--root", default=".", help="repo root")
    hook_checkpoint_parser.add_argument("--ref", action="append", help="checkpoint ref path relative to repo root; repeatable")
    hook_checkpoint_parser.add_argument("--summary", default="", help="optional session summary update")
    hook_checkpoint_parser.add_argument("session_id")
    hook_checkpoint_parser.set_defaults(func=cmd_hook_checkpoint)

    hook_stop_parser = hook_subparsers.add_parser("stop", help="record a terminal stop state for a session")
    hook_stop_parser.add_argument("--root", default=".", help="repo root")
    hook_stop_parser.add_argument("--status", choices=["completed", "failed", "abandoned"], required=True)
    hook_stop_parser.add_argument("--reason", required=True, help="stop reason")
    hook_stop_parser.add_argument("--summary", default="", help="optional terminal summary")
    hook_stop_parser.add_argument("--review-owner-spec-id", help="override convergence owner when completed work should enter review")
    hook_stop_parser.add_argument("session_id")
    hook_stop_parser.set_defaults(func=cmd_hook_stop)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
