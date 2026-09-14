#!/usr/bin/env python3
"""Download Integray Config Transfer JSON via Remote API."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from integray_remote import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    ConnectionConfig,
    DownloadError,
    download_config_transfer,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Config Transfer JSON from Integray Remote API"
    )
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .integray-connection.json (baseUrl, companySlug, token)",
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
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    project = args.project or args.connection.parent
    if project.name.startswith("."):
        project = project.parent

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = project / "snapshots" / stamp
    print(f"Downloading Config Transfer from {config.download_url}")
    try:
        out_path = download_config_transfer(
            config, dest_dir=out_dir, timeout_seconds=args.timeout
        )
    except DownloadError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
