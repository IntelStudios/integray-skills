#!/usr/bin/env python3
"""Start a task, read a task run, or download a step data snapshot (Remote API)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from integray_remote import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    SNAPSHOT_PRODUCT_LINE,
    ConnectionConfig,
    RemoteError,
    get_task_run,
    get_task_step_snapshot,
    start_task,
)
from snapshot_tree import (  # noqa: E402
    load_identity_names,
    summarize_snapshot,
    working_beside_connection,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--connection",
        type=Path,
        required=True,
        help="projects/<name>/.integray-connection.json",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout seconds (default {int(DEFAULT_TIMEOUT_SECONDS)})",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    start = sub.add_parser("start", help="POST Task/{id}/Start (needs read-write or full)")
    start.add_argument("--task-id", type=int, required=True, help="numeric Task.ID")

    status = sub.add_parser("status", help="GET TaskRun/{taskRunId}")
    status.add_argument("--task-run-id", type=int, required=True)

    snap = sub.add_parser(
        "snapshot",
        help=(
            f"GET TaskRun/{{id}}/Step/{{stepId}}/Snapshot "
            f"(from {SNAPSHOT_PRODUCT_LINE})"
        ),
    )
    snap.add_argument("--task-run-id", type=int, required=True)
    snap.add_argument(
        "--step-id",
        type=int,
        required=True,
        help="numeric Step.ID (taskStepID in the log), not CopyID",
    )
    snap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write 200 JSON here instead of stdout",
    )
    snap.add_argument(
        "--working",
        type=Path,
        default=None,
        help="split working/ for {ts:}/{dsc:}/{e:} → Name (default: beside --connection)",
    )
    snap.add_argument(
        "--no-working",
        action="store_true",
        help="do not resolve identity keys (raw JSON only)",
    )

    args = parser.parse_args()
    try:
        config = ConnectionConfig.load(args.connection)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    try:
        if args.cmd == "start":
            run_id = start_task(
                config, args.task_id, timeout_seconds=args.timeout
            )
            print(f"taskRunID={run_id}")
            return 0
        if args.cmd == "status":
            payload = get_task_run(
                config, args.task_run_id, timeout_seconds=args.timeout
            )
            status_val = payload.get("status", payload.get("Status"))
            print(f"id={payload.get('id', payload.get('Id', args.task_run_id))}")
            print(f"taskID={payload.get('taskID', payload.get('TaskID'))}")
            print(f"status={status_val}")
            return 0
        http_status, body = get_task_step_snapshot(
            config,
            args.task_run_id,
            args.step_id,
            timeout_seconds=args.timeout,
        )
        print(f"http={http_status}")
        if http_status == 204:
            print("snapshot=none (step ran; DataSnapshotCondition stored nothing)")
            return 0
        text = json.dumps(body, ensure_ascii=False, indent=2)
        if args.out:
            args.out.write_text(text + "\n", encoding="utf-8")
            print(f"wrote={args.out}")
        working = None if args.no_working else args.working
        if working is None and not args.no_working:
            working = working_beside_connection(args.connection)
        if working is not None:
            names = load_identity_names(working)
            print(summarize_snapshot(body, names), end="")
        elif not args.out:
            print(text)
        return 0
    except RemoteError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
