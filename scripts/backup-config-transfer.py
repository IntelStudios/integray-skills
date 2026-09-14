#!/usr/bin/env python3
"""Store a Config Transfer backup record on the Integray instance (Remote API)."""

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
    backup_config_transfer,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "POST Config Transfer Backup. Stores a record on the server and prints "
            "transferId. Does not write a JSON file and does not apply the transfer."
        )
    )
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .integray-connection.json (baseUrl, companySlug, token)",
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
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Creating Config Transfer backup at {config.backup_url}")
    try:
        transfer_id = backup_config_transfer(config, timeout_seconds=args.timeout)
    except RemoteError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"transferId={transfer_id}")
    print(
        "Server-side undo point only. Process the transferId from Upload of the "
        "edited file, not this id.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
