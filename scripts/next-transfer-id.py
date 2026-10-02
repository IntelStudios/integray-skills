#!/usr/bin/env python3
"""Print unused numeric IDs for new Config Transfer entities.

Does not rewrite existing IDs. Allocates max(existing)+1 … unique across the
whole transfer (nicer than per-kind). Use only when creating a new entity.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from transfer_ids import next_transfer_ids_from_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        help="split working/ directory or one Config Transfer JSON",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="how many new IDs to print (default 1)",
    )
    parser.add_argument(
        "--copy-id",
        action="store_true",
        help="also print a new CopyID (UUIDv4) after each numeric ID",
    )
    args = parser.parse_args()
    if not args.path.exists():
        print(f"{args.path}: not found", file=sys.stderr)
        return 2
    try:
        ids = next_transfer_ids_from_path(args.path, args.count)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 1
    for eid in ids:
        print(eid)
        if args.copy_id:
            print(uuid.uuid4())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
