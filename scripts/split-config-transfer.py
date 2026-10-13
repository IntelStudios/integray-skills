#!/usr/bin/env python3
"""Split a Config Transfer JSON into per-entity files under working/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from transfer_split import split_transfer  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Config Transfer JSON (usually a snapshots/<stamp>/*.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Destination directory (usually projects/<name>/working)",
    )
    args = parser.parse_args()
    if not args.file.is_file():
        print(f"{args.file}: file not found", file=sys.stderr)
        return 1
    try:
        stats = split_transfer(args.file, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 1
    for line in stats.format_lines(args.file):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
