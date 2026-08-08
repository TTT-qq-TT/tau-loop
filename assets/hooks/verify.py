#!/usr/bin/env python3
"""TauLoop verify (Windows / any-platform entry).

Equivalent to verify.sh but shell-agnostic: run the same harness checks through
sys.executable and prove the installed assets cannot drift (shutil.cmp instead
of cmp -s). Mirrors verify.sh's checks exactly, including both .sh and .py
hook entrypoints.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def resolve_root(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=False, capture_output=True, text=True,
        )
        if top.returncode == 0:
            return Path(top.stdout.strip())
    except OSError:
        pass
    return Path.cwd()


def run_check(command: list[str]) -> int:
    result = subprocess.run(command)
    return result.returncode


def mirror_pairs(root: Path) -> list[tuple[Path, Path]]:
    pairs = [
        (root / ".harness" / "tools" / "check_doc_freshness.py", root / "assets" / "tools" / "check_doc_freshness.py"),
        (root / ".harness" / "tools" / "check_task_state.py", root / "assets" / "tools" / "check_task_state.py"),
        (root / ".harness" / "hooks" / "pre-task.sh", root / "assets" / "hooks" / "pre-task.sh"),
        (root / ".harness" / "hooks" / "pre-task.py", root / "assets" / "hooks" / "pre-task.py"),
        (root / ".harness" / "hooks" / "pre-closeout.sh", root / "assets" / "hooks" / "pre-closeout.sh"),
        (root / ".harness" / "hooks" / "pre-closeout.py", root / "assets" / "hooks" / "pre-closeout.py"),
        (root / ".harness" / "hooks" / "verify.sh", root / "assets" / "hooks" / "verify.sh"),
        (root / ".harness" / "hooks" / "verify.py", root / "assets" / "hooks" / "verify.py"),
        (root / "AGENTS.md", root / "assets" / "AGENTS.md"),
    ]
    return pairs


def main() -> int:
    root = resolve_root(sys.argv[1] if len(sys.argv) > 1 else None).resolve()
    python = sys.executable

    # harness checks: doc freshness + task state (preflight + closeout)
    for command in (
        [python, str(root / ".harness" / "tools" / "check_doc_freshness.py"), str(root)],
        [python, str(root / ".harness" / "tools" / "check_task_state.py"), str(root), "--mode", "preflight"],
        [python, str(root / ".harness" / "tools" / "check_task_state.py"), str(root), "--mode", "closeout"],
    ):
        code = run_check(command)
        if code != 0:
            return code

    # The source repository additionally proves that installed assets cannot drift.
    if (root / "assets").is_dir():
        for harness_path, asset_path in mirror_pairs(root):
            if not harness_path.is_file() or not asset_path.is_file() or not shutil.cmp(harness_path, asset_path):
                print(f"mirror drift: {harness_path} <-> {asset_path}", file=sys.stderr)
                return 1

    print(f"tau-loop verification passed: {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
