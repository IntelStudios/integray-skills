#!/usr/bin/env python3
"""Copy .agents/skills/ → .claude/skills/.

Claude Code CLI does not scan .agents/skills/. Edit only the .agents tree, then run
this script. --check exits 1 when the copy is stale (use in tests).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".agents" / "skills"
DST = ROOT / ".claude" / "skills"


def _files(root: Path) -> dict[str, Path]:
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}


def diff_skills(src: Path = SRC, dst: Path = DST) -> list[str]:
    if not src.is_dir():
        return [f"missing source: {src}"]
    if not dst.is_dir():
        return [f"missing dest: {dst}"]
    left = _files(src)
    right = _files(dst)
    issues: list[str] = []
    for rel in sorted(set(left) | set(right)):
        a = left.get(rel)
        b = right.get(rel)
        if a is None:
            issues.append(f"extra in .claude/skills/: {rel}")
        elif b is None:
            issues.append(f"missing from .claude/skills/: {rel}")
        elif a.read_bytes() != b.read_bytes():
            issues.append(f"differs: {rel}")
    return issues


def sync_skills(src: Path = SRC, dst: Path = DST) -> None:
    if not src.is_dir():
        raise FileNotFoundError(f"missing source: {src}")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if .claude/skills/ does not match .agents/skills/",
    )
    args = parser.parse_args()
    if args.check:
        issues = diff_skills()
        for line in issues:
            print(line)
        return 1 if issues else 0
    try:
        sync_skills()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(f"copied {SRC.relative_to(ROOT)} -> {DST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
