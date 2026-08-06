#!/usr/bin/env python3
"""Fail when a reader-facing Markdown document links to a missing local file."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple
from urllib.parse import unquote, urlparse


READER_DOCUMENTS = (
    "README.md",
    "README.en.md",
    "SKILL.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "assets/docs/first-use.md",
    "assets/docs/first-use.en.md",
    "assets/docs/user-manual.md",
    "assets/docs/user-manual.en.md",
)
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def markdown_destinations(document: Path) -> Iterable[Tuple[int, str]]:
    in_fence = False
    for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in LINK_PATTERN.finditer(line):
            destination = match.group(1).strip()
            if destination.startswith("<") and destination.endswith(">"):
                destination = destination[1:-1]
            yield line_number, destination.split(maxsplit=1)[0]


def is_local_file_link(destination: str) -> bool:
    parsed = urlparse(destination)
    return bool(destination) and not destination.startswith("#") and not parsed.scheme and not parsed.netloc


def check_links(root: Path) -> List[str]:
    errors: List[str] = []
    for relative_document in READER_DOCUMENTS:
        document = root / relative_document
        if not document.is_file():
            errors.append(f"missing reader document: {relative_document}")
            continue
        for line_number, destination in markdown_destinations(document):
            if not is_local_file_link(destination):
                continue
            relative_target = unquote(destination.split("#", maxsplit=1)[0])
            target = (document.parent / relative_target).resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{relative_document}:{line_number}: link escapes repository: {destination}")
                continue
            if not target.exists():
                errors.append(f"{relative_document}:{line_number}: missing local link target: {destination}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    errors = check_links(root)
    if errors:
        print("Markdown link check failed:", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Checked repository-local Markdown links in {len(READER_DOCUMENTS)} reader documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
