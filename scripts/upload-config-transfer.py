#!/usr/bin/env python3
"""Upload Integray Config Transfer JSON via Remote API (pre-check only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from integray_remote import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    ConnectionConfig,
    RemoteError,
    project_from_connection,
    upload_config_transfer,
)
from transfer_split import WorkingBundle  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "POST Config Transfer Upload. Stores the file on the server and prints "
            "pre-check + transferId. Does not apply the transfer."
        )
    )
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .integray-connection.json (baseUrl, companySlug, token)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="assembled JSON (default: assemble split working/, else the single *.json)",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help="Project directory (default: parent of connection file)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout seconds (default {int(DEFAULT_TIMEOUT_SECONDS)})",
    )
    args = parser.parse_args()

    try:
        config = ConnectionConfig.load(args.connection)
        project = project_from_connection(args.connection, args.project)
        bundle = WorkingBundle(project, args.file)
    except (OSError, ValueError, json.JSONDecodeError, RemoteError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    path = bundle.path
    print(f"Uploading {path} to {config.config_transfer_url('Upload')}")
    try:
        result = upload_config_transfer(
            config, path, timeout_seconds=args.timeout
        )
    except RemoteError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        bundle.close()

    print(f"transferId={result.transfer_id}")
    print(f"succeeded={str(result.succeeded).lower()}")
    print(f"hasUnresolvedReferences={str(result.has_unresolved_references).lower()}")
    print(f"hasSensitiveVariables={str(result.has_sensitive_variables).lower()}")
    missing = [
        c
        for c in result.connectors
        if isinstance(c, dict)
        and str(c.get("status", c.get("Status", ""))).lower() == "missing"
    ]
    if missing:
        print(f"missingConnectors={len(missing)}")
        for item in missing:
            name = item.get("name", item.get("Name", "?"))
            guid = item.get("guid", item.get("Guid", ""))
            version = item.get("version", item.get("Version", ""))
            print(f"  missing {name} {guid} {version}")
    if result.has_sensitive_variables:
        names = ", ".join(str(n) for n in result.sensitive_variables) or "(names not listed)"
        print(f"sensitiveVariables={names}")
    print(
        "Pre-check only. Process this transferId (--only-test then --publish). "
        "Do not Process a Backup id.",
        file=sys.stderr,
    )
    if not result.succeeded:
        print("Upload pre-check failed (succeeded=false). Do not Process.", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
