#!/usr/bin/env python3
"""Run git inside projects/<name>/ without inheriting the KB repo GIT_DIR."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "usage: python scripts/project-git.py projects/<name> <git args...>",
            file=sys.stderr,
        )
        return 2
    project = Path(sys.argv[1])
    if not (project / ".git").exists():
        print(f"{project}: no .git (company repo lives in projects/<name>/)", file=sys.stderr)
        return 2
    env = os.environ.copy()
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return subprocess.call(["git", "-C", str(project), *sys.argv[2:]], env=env)


if __name__ == "__main__":
    raise SystemExit(main())
