#!/usr/bin/env python3
"""Print Integray instance product line and build stamp from GET /api/Integray."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from integray_remote import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    RemoteError,
    fetch_instance_version,
    instance_info_url,
    read_connection_base_url,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "GET {baseUrl}/api/Integray (no token). Prints productLine "
            "(git branch / from-this-version token) and buildStamp."
        )
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--connection",
        type=Path,
        help="Path to .integray-connection.json (uses baseUrl only; no token sent)",
    )
    src.add_argument(
        "--base-url",
        help="Integray instance URL, e.g. https://test-prod.integray.app",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout seconds (default {int(DEFAULT_TIMEOUT_SECONDS)})",
    )
    args = parser.parse_args()

    try:
        if args.connection:
            base_url = read_connection_base_url(args.connection)
        else:
            base_url = str(args.base_url).strip().rstrip("/")
            if not base_url:
                raise ValueError("--base-url is empty")
        url = instance_info_url(base_url)
        print(f"GET {url}", file=sys.stderr)
        info = fetch_instance_version(base_url, timeout_seconds=args.timeout)
    except (OSError, ValueError, json.JSONDecodeError, RemoteError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"productLine={info['productLine']}")
    print(f"buildStamp={info['buildStamp']}")


if __name__ == "__main__":
    main()
