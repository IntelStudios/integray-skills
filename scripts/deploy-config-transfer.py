#!/usr/bin/env python3
"""Schema-check, Upload, onlyTest, then publish a working/ Config Transfer.

Does not re-download into working/ (that would overwrite local edits).
Always POSTs Backup before Upload (do not Process that id).
Process still takes minutes on the instance — this only removes extra agent steps.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from integray_remote import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    ConnectionConfig,
    ConnectionPermissionError,
    RemoteError,
    backup_config_transfer,
    process_config_transfer,
    project_from_connection,
    upload_config_transfer,
)
from transfer_split import WorkingBundle, find_configuration_path  # noqa: E402
from transfer_util import (  # noqa: E402
    find_configuration,
    load_transfer,
    parse_conventions,
    save_transfer,
    set_statement,
    stamp_generated,
    statement_of,
)

PROCESS_TIMEOUT_SECONDS = 600.0


def _run_checker(script: str, path: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), str(path)],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _stamp_statements(bundle: WorkingBundle, copy_ids: list[str]) -> None:
    if bundle.split_dir is not None:
        for cid in copy_ids:
            cfg_path = find_configuration_path(bundle.split_dir, copy_id=cid)
            cfg = load_transfer(cfg_path)
            stmt = statement_of(cfg)
            if stmt is None:
                print(f"stamp skipped {cid}: no Statement", file=sys.stderr)
                continue
            new_stmt, stamp = stamp_generated(stmt)
            set_statement(cfg, new_stmt)
            save_transfer(cfg_path, cfg)
            print(f"stamp={cid} {stamp}")
        bundle.refresh()
        return
    data = load_transfer(bundle.path)
    for cid in copy_ids:
        cfg = find_configuration(data, copy_id=cid)
        stmt = statement_of(cfg)
        if stmt is None:
            print(f"stamp skipped {cid}: no Statement", file=sys.stderr)
            continue
        new_stmt, stamp = stamp_generated(stmt)
        set_statement(cfg, new_stmt)
        print(f"stamp={cid} {stamp}")
    save_transfer(bundle.path, data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="projects/<name>/.integray-connection.json",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="assembled JSON (default: assemble split working/, else the single *.json)",
    )
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument(
        "--timeout",
        type=float,
        default=PROCESS_TIMEOUT_SECONDS,
        help=f"HTTP timeout seconds for Upload/Process (default {int(PROCESS_TIMEOUT_SECONDS)})",
    )
    parser.add_argument(
        "--stamp-copy-id",
        action="append",
        default=[],
        help="Configuration CopyID whose Statement generated stamp to refresh. Repeatable.",
    )
    args = parser.parse_args()

    try:
        config = ConnectionConfig.load(args.connection)
        project = project_from_connection(args.connection, args.project)
        bundle = WorkingBundle(project, args.file)
    except (OSError, ValueError, json.JSONDecodeError, RemoteError) as exc:
        print(exc, file=sys.stderr)
        return 1

    path = bundle.path
    conventions = parse_conventions(project / "conventions.md")
    print(f"file={path}")
    if bundle.split_dir is not None:
        print(f"assembledFrom={bundle.split_dir}")
    print(f"permission={config.permission}")
    print(
        "conventions="
        f"publish:{conventions['publish']} "
        f"download:{conventions['download']}"
    )

    try:
        if args.stamp_copy_id:
            try:
                _stamp_statements(bundle, args.stamp_copy_id)
            except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
                print(exc, file=sys.stderr)
                return 1

        code, out, err = _run_checker("check-transfer-schemas.py", path)
        if err.strip():
            for line in err.strip().splitlines():
                print(line, file=sys.stderr)
        if out.strip() or code != 0:
            sys.stdout.write(out)
            print("schema check failed; not uploading", file=sys.stderr)
            return 1
        print("schema=ok")

        try:
            backup_id = backup_config_transfer(config, timeout_seconds=args.timeout)
        except (RemoteError, ConnectionPermissionError) as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"backupTransferId={backup_id} (do not Process this id)")

        print(f"Uploading {path} to {config.config_transfer_url('Upload')}")
        try:
            uploaded = upload_config_transfer(
                config, path, timeout_seconds=args.timeout
            )
        except (RemoteError, ConnectionPermissionError) as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"transferId={uploaded.transfer_id}")
        print(f"succeeded={str(uploaded.succeeded).lower()}")
        print(
            f"hasUnresolvedReferences={str(uploaded.has_unresolved_references).lower()}"
        )
        print(
            f"hasSensitiveVariables={str(uploaded.has_sensitive_variables).lower()}"
        )
        if not uploaded.succeeded:
            print("Upload pre-check failed. Do not Process.", file=sys.stderr)
            return 2
    finally:
        bundle.close()

    print(
        f"Processing transferId={uploaded.transfer_id} (onlyTest) at "
        f"{config.config_transfer_url(str(uploaded.transfer_id) + '/Process')}"
    )
    try:
        only = process_config_transfer(
            config,
            uploaded.transfer_id,
            only_test=True,
            publish=False,
            timeout_seconds=args.timeout,
        )
    except (RemoteError, ConnectionPermissionError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"http={only.http_status}")
    print("onlyTest=true")
    if only.http_status != 200:
        print("onlyTest failed; not publishing", file=sys.stderr)
        return 1

    if not config.can_publish:
        print(
            "publish=skipped (permission is not full; set permission to full)",
            file=sys.stderr,
        )
        return 0
    if conventions["publish"] != "auto":
        print(
            "publish=skipped (conventions Publish after dry-run: ask). "
            f"Process --transfer-id {uploaded.transfer_id} --publish when ready."
        )
        return 0

    print(
        f"Processing transferId={uploaded.transfer_id} (publish) at "
        f"{config.config_transfer_url(str(uploaded.transfer_id) + '/Process')}"
    )
    try:
        pub = process_config_transfer(
            config,
            uploaded.transfer_id,
            only_test=False,
            publish=True,
            timeout_seconds=args.timeout,
        )
    except (RemoteError, ConnectionPermissionError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"http={pub.http_status}")
    print("publish=true")
    pr = pub.publish_result or {}
    is_success = pr.get("isSuccess", pr.get("IsSuccess"))
    print(f"publishResult.isSuccess={str(bool(is_success)).lower()}")
    status = pr.get("status", pr.get("Status"))
    if status is not None:
        print(f"publishResult.status={status}")
    if pub.http_status == 422 or is_success is False:
        print("publish failed", file=sys.stderr)
        return 2

    print(
        "download=skipped (script will not overwrite working/; "
        "run download-config-transfer.py if you want a new snapshot)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
