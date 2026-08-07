#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys


REQUIRED_SPEC_SECTIONS = [
    "## 1. Goal",
    "## 2. Non-Goals",
    "## 3. References Or Prior Art",
    "## 4. Allowed Files",
    "## 5. Implementation Checklist",
    "## 6. Verification",
    "## 7. Risks And Regression Points",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def get_field(text: str, name: str) -> str:
    match = re.search(rf"^- {re.escape(name)}:[ \t]*([^\n]*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def normalize_path(value: str) -> str:
    return value.strip().strip("`")


def section_body(text: str, heading: str) -> str:
    pattern = rf"^{re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Check active task state for a repo harness.")
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--mode", choices=["preflight", "closeout"], default="preflight")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    plan_path = repo / ".harness/plan.md"
    if not plan_path.exists():
        print("Missing .harness/plan.md")
        return 1

    plan_text = read_text(plan_path)
    complexity = get_field(plan_text, "Complexity")
    spec_rel = normalize_path(get_field(plan_text, "Spec"))
    profile_rel = normalize_path(get_field(plan_text, "Verification profile"))

    if not spec_rel:
        if complexity == "quick":
            print("Quick task without spec: allowed")
            return 0
        print("Non-quick task is missing an active spec in .harness/plan.md")
        return 1

    spec_path = repo / spec_rel
    if not spec_path.exists():
        print(f"Active spec is missing: {spec_rel}")
        return 1

    spec_text = read_text(spec_path)
    errors: list[str] = []
    warnings: list[str] = []

    for marker in REQUIRED_SPEC_SECTIONS:
        if marker not in spec_text:
            errors.append(f"spec missing section: {marker}")

    allowed = section_body(spec_text, "## 4. Allowed Files")
    if not allowed or "List the files" in allowed:
        errors.append("allowed files section is still empty or placeholder text")

    spec_profile = normalize_path(get_field(spec_text, "Verification profile"))
    selected_profile = spec_profile or profile_rel
    if selected_profile:
        profile_path = repo / selected_profile
        if not profile_path.exists():
            errors.append(f"verification profile does not exist: {selected_profile}")
    else:
        warnings.append("no verification profile selected; using task-local verification only")

    if args.mode == "closeout":
        unfinished = re.findall(r"^(?:- )?\[ \].*$", spec_text, re.MULTILINE)
        blocked = re.findall(r"^(?:- )?\[-\].*$", spec_text, re.MULTILINE)
        if unfinished:
            errors.append(f"spec still has unfinished checklist items: {len(unfinished)}")
        if blocked:
            errors.append(f"spec still has blocked checklist items: {len(blocked)}")

        verification = section_body(spec_text, "## 6. Verification")
        stripped = [line.strip() for line in verification.splitlines() if line.strip()]
        useful = [line for line in stripped if line not in {"- Commands:", "- Manual checks:", "- Residual risks:"}]
        if not useful:
            errors.append("verification section does not contain any recorded commands, checks, or risks")

    if warnings:
        print("Task state warnings:")
        for item in warnings:
            print(f"- {item}")

    if errors:
        print(f"Task state check failed ({args.mode}):")
        for item in errors:
            print(f"- {item}")
        return 1

    print(f"Task state looks valid for {args.mode}: {spec_rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
