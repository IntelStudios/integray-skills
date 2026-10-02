#!/usr/bin/env python3
"""Assemble a split working/ tree into one Config Transfer JSON. Leaves --out on disk."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from transfer_split import assemble_to  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        required=True,
        help="Split working directory (projects/<name>/working)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Assembled Config Transfer JSON path (left on disk)",
    )
    args = parser.parse_args()
    try:
        assemble_to(args.dir, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Wrote {args.out} ({args.out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
