#!/usr/bin/env python3
"""Bootstrap the TauLoop skeleton in a project (the single `tau init` command)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Dict, Iterable, Tuple


MANIFEST_RELATIVE = Path(".harness/.tau-loop-managed.json")
MARKER_RELATIVE = Path(".harness-workflow")
SCHEMA_VERSION = 1

USER_FILES = (
    "AGENTS.md",
    "brief.md",
    "failure-log.md",
    "memory.md",
    "plan.md",
    "report.md",
    "verification.md",
    "specs/README.md",
    "specs/TEMPLATE.md",
    "verification-profiles/README.md",
    "verification-profiles/code-change.md",
    "verification-profiles/docs-workflow.md",
    "verification-profiles/refactor.md",
    "verification-profiles/reliability.md",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def source_path(assets: Path, relative: str) -> Path:
    if relative == "AGENTS.md":
        return assets / relative
    return assets / relative


def target_path(root: Path, relative: str) -> Path:
    if relative == "AGENTS.md":
        return root / relative
    return root / ".harness" / relative


def tool_files(assets: Path) -> Iterable[Tuple[str, Path]]:
    for directory in ("hooks", "tools"):
        base = assets / directory
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                if path.name in {"check_markdown_links.py", "project_lifecycle.py"}:
                    continue
                yield f".harness/{path.relative_to(assets)}", path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the TauLoop skeleton in a project.")
    parser.add_argument("command", choices=("init",))
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="show planned actions without writing")
    parser.add_argument("--no-brief", action="store_true", help="do not create .harness/brief.md on init")
    return parser.parse_args()


def load_manifest(root: Path) -> Dict[str, object]:
    path = root / MANIFEST_RELATIVE
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "tools": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid managed-file manifest: {path}: {exc}")
    if value.get("schema_version") != SCHEMA_VERSION or not isinstance(value.get("tools"), dict):
        raise SystemExit(f"Unsupported managed-file manifest: {path}")
    return value


def write_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if os.access(source, os.X_OK):
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def print_action(action: str, path: Path, detail: str = "") -> None:
    suffix = f" ({detail})" if detail else ""
    print(f"{action:<7} {path}{suffix}")


def create_marker(root: Path, dry_run: bool) -> None:
    marker = root / MARKER_RELATIVE
    text = "managed_by=tau-loop\nstate_dir=.harness\n"
    if marker.exists():
        print_action("keep", marker)
        return
    print_action("create", marker)
    if not dry_run:
        marker.write_text(text, encoding="utf-8")


def seed_memory(path: Path, project_name: str) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("<repo-name>", project_name), encoding="utf-8")


def init(root: Path, assets: Path, dry_run: bool, no_brief: bool) -> int:
    root.mkdir(parents=True, exist_ok=True)

    # User-owned records: create missing only, never overwrite.
    for relative in USER_FILES:
        if no_brief and relative == "brief.md":
            continue
        source = source_path(assets, relative)
        target = target_path(root, relative)
        if target.exists():
            print_action("keep", target, "user-owned")
            continue
        print_action("create", target)
        if not dry_run:
            write_file(source, target)
            if relative == "memory.md":
                seed_memory(target, root.name)

    # Tool-managed files: create missing; refresh unmodified; keep modified.
    manifest = load_manifest(root)
    tools = manifest["tools"]
    for relative, source in tool_files(assets):
        target = root / relative
        prior = tools.get(relative)
        if not target.exists():
            print_action("create", target)
            if not dry_run:
                write_file(source, target)
                tools[relative] = {"sha256": digest(target)}
            continue
        current = digest(target)
        prior_digest = prior.get("sha256") if isinstance(prior, dict) else None
        if prior_digest and current == prior_digest:
            if current == digest(source):
                print_action("keep", target, "current")
                continue
            print_action("update", target, "managed")
            if not dry_run:
                write_file(source, target)
                tools[relative] = {"sha256": digest(target)}
            continue
        print_action("keep", target, "modified or unmanaged")

    create_marker(root, dry_run)
    manifest_path = root / MANIFEST_RELATIVE
    if not dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"done  init completed for {root}")
    return 0


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    assets = source_root()
    if not (assets / "tools" / "check_task_state.py").is_file():
        raise SystemExit(f"Invalid tau-loop asset root: {assets}")
    return init(root, assets, args.dry_run, args.no_brief)


if __name__ == "__main__":
    sys.exit(main())
