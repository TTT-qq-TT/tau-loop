#!/usr/bin/env python3
"""Install or remove the tau-loop Codex skill for one user."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import sys
from pathlib import Path


PACKAGE_NAME = "tau-loop"
COMMAND_NAME = "tau"
INSTALL_RECORD = ".tau-loop-install.json"


def package_root() -> Path:
    return Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the tau-loop Codex skill.")
    parser.add_argument(
        "--codex-home",
        default=str(Path.home() / ".codex"),
        help="Codex home directory (default: ~/.codex)",
    )
    parser.add_argument("--uninstall", action="store_true", help="remove files installed by this package")
    parser.add_argument("--quiet", action="store_true", help="suppress normal output")
    return parser.parse_args()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_tree(source: Path, target: Path) -> None:
    for item in sorted(source.rglob("*")):
        if not item.is_file() or "__pycache__" in item.parts:
            continue
        destination = target / item.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)


def log(enabled: bool, message: str) -> None:
    if enabled:
        print(message)


def validate_source(root: Path) -> None:
    required = [
        root / "SKILL.md",
        root / "assets" / "tools" / "cw_supervisor.py",
        root / "assets" / "tools" / "cw_state.py",
        root / "assets" / "tools" / "project_lifecycle.py",
        root / "assets" / "bin" / "cw",
        root / "bin" / COMMAND_NAME,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Invalid tau-loop package; missing:\n- " + "\n- ".join(missing))


def install(root: Path, codex_home: Path, verbose: bool) -> int:
    validate_source(root)
    skill_root = codex_home / "skills" / PACKAGE_NAME
    asset_root = skill_root / "assets"
    bin_root = codex_home / "bin"
    skill_root.mkdir(parents=True, exist_ok=True)
    bin_root.mkdir(parents=True, exist_ok=True)

    shutil.copy2(root / "SKILL.md", skill_root / "SKILL.md")
    copy_tree(root / "assets", asset_root)
    command = bin_root / COMMAND_NAME
    shutil.copy2(root / "bin" / COMMAND_NAME, command)
    command.chmod(command.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    record = {
        "schema_version": 1,
        "package": PACKAGE_NAME,
        "source": str(root),
        "command_sha256": digest(root / "bin" / COMMAND_NAME),
    }
    (skill_root / INSTALL_RECORD).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    log(verbose, f"Installed skill: {skill_root}")
    log(verbose, f"Installed command: {command}")
    log(verbose, "Ensure ~/.codex/bin is on PATH, then run: tau --help")
    return 0


def uninstall(codex_home: Path, verbose: bool) -> int:
    skill_root = codex_home / "skills" / PACKAGE_NAME
    record_path = skill_root / INSTALL_RECORD
    if not record_path.is_file():
        raise SystemExit(f"Refusing to remove unrecognized skill directory: {skill_root}")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    command = codex_home / "bin" / COMMAND_NAME
    expected = record.get("command_sha256")
    if command.is_file() and expected == digest(command):
        command.unlink()
        log(verbose, f"Removed command: {command}")
    elif command.exists():
        log(verbose, f"Kept modified command: {command}")

    shutil.rmtree(skill_root)
    log(verbose, f"Removed skill: {skill_root}")
    return 0


def main() -> int:
    args = parse_args()
    codex_home = Path(args.codex_home).expanduser().resolve()
    if args.uninstall:
        return uninstall(codex_home, not args.quiet)
    return install(package_root(), codex_home, not args.quiet)


if __name__ == "__main__":
    sys.exit(main())
