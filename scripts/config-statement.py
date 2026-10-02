#!/usr/bin/env python3
"""Get/put a Configuration.Statement without loading the whole transfer into chat."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from transfer_split import (  # noqa: E402
    find_configuration_path,
    is_split_dir,
    iter_collection_files,
)
from transfer_util import (  # noqa: E402
    find_configuration,
    load_transfer,
    save_transfer,
    set_statement,
    stamp_generated,
    statement_of,
    step_labels_by_configuration,
)


def _load_for_list(path: Path) -> dict:
    if is_split_dir(path):
        configs = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in iter_collection_files(path, "Configurations")
        ]
        tasks = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in iter_collection_files(path, "Tasks")
        ]
        return {"Configurations": configs, "Tasks": tasks}
    return load_transfer(path)


def _cfg(args: argparse.Namespace) -> tuple[Path, dict | None, dict]:
    path = args.file
    if is_split_dir(path):
        cfg_path = find_configuration_path(
            path, copy_id=args.copy_id, name=args.name
        )
        cfg = load_transfer(cfg_path)
        return cfg_path, None, cfg
    data = load_transfer(path)
    cfg = find_configuration(data, copy_id=args.copy_id, name=args.name)
    return path, data, cfg


def cmd_list(args: argparse.Namespace) -> int:
    data = _load_for_list(args.file)
    labels = step_labels_by_configuration(data)
    rows = []
    for cfg in data.get("Configurations") or []:
        if not isinstance(cfg, dict):
            continue
        stmt = statement_of(cfg)
        if stmt is None:
            continue
        cid = cfg.get("CopyID") or ""
        cname = cfg.get("Name") or ""
        where = "; ".join(labels.get(str(cid), [])[:3])
        rows.append((len(stmt), str(cid), cname, where))
    rows.sort(key=lambda r: (-r[0], r[2] or r[3]))
    for n, cid, cname, where in rows:
        extra = cname or where or ""
        loc = where if cname else ""
        bits = [cid, f"{n} chars"]
        if extra:
            bits.append(extra)
        if loc and cname:
            bits.append(loc)
        print("\t".join(bits))
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    _, _, cfg = _cfg(args)
    stmt = statement_of(cfg)
    if stmt is None:
        print("Configuration has no Statement", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(stmt, encoding="utf-8")
        print(f"wrote {args.out} ({len(stmt)} chars)", file=sys.stderr)
    else:
        sys.stdout.write(stmt)
        if stmt and not stmt.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def cmd_put(args: argparse.Namespace) -> int:
    path, data, cfg = _cfg(args)
    text = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
    if args.stamp:
        try:
            text, stamp = stamp_generated(text)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(stamp)
    set_statement(cfg, text)
    if data is None:
        save_transfer(path, cfg)
    else:
        save_transfer(path, data)
    print(f"updated {cfg.get('CopyID')} in {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Use this instead of opening the whole transfer. "
            "--file is a split working/ directory or one Config Transfer JSON."
        )
    )
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="split working/ directory or Config Transfer JSON",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="CopyIDs that have a Statement (size, step name)")
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="Print Statement to stdout or --out")
    p_get.add_argument("--copy-id", help="Configurations[].CopyID")
    p_get.add_argument("--name", help="Configuration.Name or Step.Name")
    p_get.add_argument("--out", type=Path, help="Write to this file instead of stdout")
    p_get.set_defaults(func=cmd_get)

    p_put = sub.add_parser("put", help="Replace Statement from --input or stdin")
    p_put.add_argument("--copy-id", help="Configurations[].CopyID")
    p_put.add_argument("--name", help="Configuration.Name or Step.Name")
    p_put.add_argument(
        "--input",
        type=Path,
        help="File with new Statement (default: stdin)",
    )
    p_put.add_argument(
        "--stamp",
        action="store_true",
        help=(
            "If Statement contains `generated YYYY-MM-DD HH:MM:SS`, replace it "
            "(Europe/Prague). Off by default."
        ),
    )
    p_put.set_defaults(func=cmd_put)

    args = parser.parse_args()
    if args.cmd in ("get", "put") and not args.copy_id and not args.name:
        print("get/put require --copy-id or --name", file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
