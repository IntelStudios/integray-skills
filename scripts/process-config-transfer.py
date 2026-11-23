#!/usr/bin/env python3
"""Process an uploaded Integray Config Transfer (Remote API)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from integray_remote import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    FORCE_PUBLISH_PRODUCT_LINE,
    ConnectionConfig,
    RemoteError,
    process_config_transfer,
    publish_company_cache,
    require_product_line,
)


def _force_publish(config: ConnectionConfig, transfer_id: int, timeout: float) -> None:
    """Apply the upload, then POST Publish?force=true. Exits the process."""
    try:
        have = require_product_line(
            config.base_url, FORCE_PUBLISH_PRODUCT_LINE, timeout_seconds=timeout
        )
    except RemoteError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"productLine={have}")
    print(
        f"Processing transferId={transfer_id} (apply) at "
        f"{config.config_transfer_url(str(transfer_id) + '/Process')}"
    )
    try:
        applied = process_config_transfer(
            config,
            transfer_id,
            only_test=False,
            publish=False,
            timeout_seconds=timeout,
        )
    except RemoteError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"http={applied.http_status}")
    print("publish=false")
    if applied.http_status != 200:
        print("apply failed; not force-publishing", file=sys.stderr)
        raise SystemExit(1)

    print(f"POST {config.remote_url('Publish')}?force=true")
    try:
        pub = publish_company_cache(config, force=True, timeout_seconds=timeout)
    except RemoteError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"http={pub.http_status}")
    print("force=true")
    body = pub.raw or {}
    is_success = body.get("isSuccess", body.get("IsSuccess"))
    status = body.get("status", body.get("Status"))
    print(f"publishResult.isSuccess={str(bool(is_success)).lower()}")
    if status is not None:
        print(f"publishResult.status={status}")
    messages = body.get("messages", body.get("Messages")) or []
    if isinstance(messages, list):
        for msg in messages:
            if not isinstance(msg, dict):
                print(f"publishResult.message={msg}")
                continue
            code = msg.get("code", msg.get("Code", ""))
            text = msg.get("message", msg.get("Message", msg))
            print(f"publishResult.message={code} {text}".rstrip())
    if pub.http_status == 422 or is_success is False:
        print("publish failed", file=sys.stderr)
        raise SystemExit(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "POST Config Transfer Process for a transferId from Upload. "
            "Exactly one of --only-test, --publish, --apply, or --force."
        )
    )
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="Path to .integray-connection.json (baseUrl, companySlug, token)",
    )
    parser.add_argument(
        "--transfer-id",
        type=int,
        required=True,
        help="transferId from Upload (not from Backup)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--only-test",
        action="store_true",
        help="Dry-run: validate import, roll back (no apply, no publish)",
    )
    mode.add_argument(
        "--publish",
        action="store_true",
        help="Apply and rebuild the configuration cache",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply without rebuilding the cache (publish=false). Rare; prefer --publish.",
    )
    mode.add_argument(
        "--force",
        action="store_true",
        help=(
            "Apply this transfer (publish=false), then POST Publish?force=true. "
            "Does not wait for running task runs. Needs rel-2025-03.018."
        ),
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

    if args.force:
        _force_publish(config, args.transfer_id, args.timeout)
        return

    only_test = bool(args.only_test)
    publish = bool(args.publish)
    label = "onlyTest" if only_test else ("publish" if publish else "apply")
    print(
        f"Processing transferId={args.transfer_id} ({label}) at "
        f"{config.config_transfer_url(str(args.transfer_id) + '/Process')}"
    )
    try:
        result = process_config_transfer(
            config,
            args.transfer_id,
            only_test=only_test,
            publish=publish,
            timeout_seconds=args.timeout,
        )
    except RemoteError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"http={result.http_status}")
    print(f"onlyTest={str(result.only_test).lower()}")
    print(f"publish={str(result.publish).lower()}")
    pr = result.publish_result
    if pr:
        is_success = pr.get("isSuccess", pr.get("IsSuccess"))
        status = pr.get("status", pr.get("Status"))
        print(f"publishResult.isSuccess={str(bool(is_success)).lower()}")
        if status is not None:
            print(f"publishResult.status={status}")
        messages = pr.get("messages", pr.get("Messages")) or []
        if isinstance(messages, list):
            for msg in messages:
                if not isinstance(msg, dict):
                    print(f"publishResult.message={msg}")
                    continue
                code = msg.get("code", msg.get("Code", ""))
                text = msg.get("message", msg.get("Message", msg))
                print(f"publishResult.message={code} {text}".rstrip())

    if result.http_status == 422:
        print(
            "Import applied but publish failed (HTTP 422). "
            "Fix publishResult.messages and Process again with --publish.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if publish and pr is not None:
        is_success = pr.get("isSuccess", pr.get("IsSuccess"))
        if is_success is False:
            print("publishResult.isSuccess=false", file=sys.stderr)
            raise SystemExit(2)


if __name__ == "__main__":
    main()
