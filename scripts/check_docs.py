#!/usr/bin/env python3
"""Validate relative Markdown links without external dependencies."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^]]*]\(([^)]+)\)")
errors: list[str] = []

for document in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
    for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
        for destination in LINK.findall(line):
            if destination.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = (document.parent / destination.split("#", 1)[0]).resolve()
            if not path.exists():
                errors.append(f"{document.relative_to(ROOT)}:{line_number}: missing {destination}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
print("Documentation links valid")
