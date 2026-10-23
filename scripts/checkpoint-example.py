#!/usr/bin/env python3
"""Print the checkpoint JSON a connector stores between runs.

Looks up data/connector-checkpoints.json by connector guid (case-insensitive).
Prints the shape, any note, and the example object. Exit 2 when the guid is
not in that file. An empty stored checkpoint is {} or "".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "connector-checkpoints.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guid", help="Connector guid")
    args = parser.parse_args()
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    want = args.guid.strip().lower()
    row = next(
        (item for item in data["connectors"] if str(item.get("guid", "")).lower() == want),
        None,
    )
    if row is None:
        print(f"checkpoint: guid not in {CATALOG.name}", file=sys.stderr)
        return 2
    shape_name = row["shape"]
    shape = data["shapes"][shape_name]
    print(f"name: {row.get('name')}")
    print(f"guid: {row.get('guid')}")
    print(f"shape: {shape_name}")
    if row.get("note"):
        print(f"note: {row['note']}")
    print(f"summary: {shape.get('summary')}")
    print("empty: {} or \"\"")
    if "examples" in shape:
        print("examples:")
        print(json.dumps(shape["examples"], indent=2, ensure_ascii=False))
    else:
        print("example:")
        print(json.dumps(shape.get("example"), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
