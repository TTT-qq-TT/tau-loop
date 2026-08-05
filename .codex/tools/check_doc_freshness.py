#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys


CORE_FILES = [
    "AGENTS.md",
    ".codex/memory.md",
    ".codex/plan.md",
    ".codex/verification.md",
    ".codex/failure-log.md",
]

LEGACY_PATHS = [
    "docs/memory.md",
    "docs/plan.md",
    "docs/report.md",
    "docs/brief.md",
    "docs/verification.md",
    "docs/failure-log.md",
    "docs/specs/",
]

PATH_RE = re.compile(r"`((?:AGENTS\.md|\.codex/)[^`]+)`")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_path(value: str) -> str:
    return value.strip().strip("`")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check workflow doc freshness for a repo.")
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for rel in CORE_FILES:
        path = repo / rel
        if not path.exists():
            errors.append(f"missing required workflow file: {rel}")

    agents = repo / "AGENTS.md"
    if agents.exists():
        agents_text = read_text(agents)
        for legacy in LEGACY_PATHS:
            if legacy in agents_text:
                errors.append(f"AGENTS.md still references legacy path: {legacy}")

    plan_path = repo / ".codex/plan.md"
    if plan_path.exists():
        plan_text = read_text(plan_path)
        spec_match = re.search(r"^- Spec:[ \t]*([^\n]*)$", plan_text, re.MULTILINE)
        if spec_match:
            spec_value = normalize_path(spec_match.group(1))
            if spec_value and "Use a path like" not in spec_value:
                spec_path = repo / spec_value
                if not spec_path.exists():
                    errors.append(f"plan points to missing spec: {spec_value}")

    search_paths = [agents]
    codex_dir = repo / ".codex"
    if codex_dir.exists():
        search_paths.extend(sorted(codex_dir.rglob("*.md")))

    for path in search_paths:
        if not path.exists():
            continue
        text = read_text(path)
        for match in PATH_RE.finditer(text):
            rel = match.group(1)
            if "*" in rel:
                continue
            candidate = repo / rel
            if not candidate.exists():
                warnings.append(f"{path.relative_to(repo)} references missing path: {rel}")

    memory_path = repo / ".codex/memory.md"
    if memory_path.exists() and plan_path.exists():
        memory_text = read_text(memory_path)
        plan_text = read_text(plan_path)
        plan_spec = re.search(r"^- Spec:[ \t]*([^\n]*)$", plan_text, re.MULTILINE)
        memory_spec = re.search(r"^- Active spec:[ \t]*([^\n]*)$", memory_text, re.MULTILINE)
        if plan_spec and memory_spec:
            left = normalize_path(plan_spec.group(1))
            right = normalize_path(memory_spec.group(1))
            if left and right and left != right and "暂未创建" not in right:
                warnings.append(f"memory active spec does not match plan spec: {right} != {left}")

    if warnings:
        print("Freshness warnings:")
        for item in warnings:
            print(f"- {item}")

    if errors:
        print("Freshness check failed:")
        for item in errors:
            print(f"- {item}")
        return 1

    print(f"Workflow docs look fresh enough: {repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
