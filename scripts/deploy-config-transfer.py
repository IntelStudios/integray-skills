#!/usr/bin/env python3
"""Schema-check, Upload, onlyTest, then publish a working/ Config Transfer.

Does not re-download into working/ (that would overwrite local edits).
Does not invent a backup when conventions say ask.
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
    resolve_working_file,
    upload_config_transfer,
)
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


def _project_from_connection(connection: Path, project: Path | None) -> Path:
    if project is not None:
        return project
    parent = connection.parent
    if parent.name.startswith("."):
        return parent.parent
    return parent


def _run_checker(script: str, path: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), str(path)],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


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
        help="working JSON (default: the single *.json in working/)",
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
    parser.add_argument(
        "--backup",
        action="store_true",
        help="POST Backup first (also runs when conventions Backup is auto)",
    )
    args = parser.parse_args()

    try:
        config = ConnectionConfig.load(args.connection)
        project = _project_from_connection(args.connection, args.project)
        path = resolve_working_file(project, args.file)
    except (OSError, ValueError, json.JSONDecodeError, RemoteError) as exc:
        print(exc, file=sys.stderr)
        return 1

    conventions = parse_conventions(project / "conventions.md")
    print(f"file={path}")
    print(f"permission={config.permission}")
    print(
        "conventions="
        f"backup:{conventions['backup']} "
        f"publish:{conventions['publish']} "
        f"download:{conventions['download']}"
    )

    if args.stamp_copy_id:
        try:
            data = load_transfer(path)
            for cid in args.stamp_copy_id:
                cfg = find_configuration(data, copy_id=cid)
                stmt = statement_of(cfg)
                if stmt is None:
                    print(f"stamp skipped {cid}: no Statement", file=sys.stderr)
                    continue
                new_stmt, stamp = stamp_generated(stmt)
                set_statement(cfg, new_stmt)
                print(f"stamp={cid} {stamp}")
            save_transfer(path, data)
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

    do_backup = args.backup or conventions["backup"] == "auto"
    if do_backup:
        try:
            backup = backup_config_transfer(config, timeout_seconds=args.timeout)
        except (RemoteError, ConnectionPermissionError) as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"backupTransferId={backup.transfer_id} (do not Process this id)")
    else:
        print("backup=skipped (conventions ask; pass --backup to take one)")

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
