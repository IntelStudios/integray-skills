#!/usr/bin/env python3
"""Advise on company connector versions vs the KB catalog (not a delivery gate).

Stdout: mixed Guid versions and versions older than data/connectors.json newest.
Lines tell the user to update connectors in Integray first if that Version is
not on the instance. Empty stdout = nothing to offer. Exit 0 unless the
transfer cannot be loaded.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
DATA = ROOT / "data"

from connector_versions import advise, newest_in_catalog  # noqa: E402
from transfer_split import load_transfer_document  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file",
        type=Path,
        help="split working/ directory or one Config Transfer JSON",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA,
        help="KB catalog directory (default: data/)",
    )
    args = parser.parse_args()
    if not args.file.exists():
        print(f"file not found: {args.file}", file=sys.stderr)
        return 2
    try:
        data = load_transfer_document(args.file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 2
    for line in advise(data, newest_in_catalog(args.data_dir)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
