#!/usr/bin/env python3
"""TauLoop pre-task check (Windows / any-platform entry).

Equivalent to pre-task.sh but shell-agnostic: invoke the same check tools
through sys.executable so no python3/python/py command-name dependency exists.
"""

from __future__ import annotations

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


def main() -> int:
    root = resolve_root(sys.argv[1] if len(sys.argv) > 1 else None)
    python = sys.executable
    checks = (
        [python, str(root / ".harness" / "tools" / "check_doc_freshness.py"), str(root)],
        [python, str(root / ".harness" / "tools" / "check_task_state.py"), str(root), "--mode", "preflight"],
    )
    for check in checks:
        result = subprocess.run(check)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
