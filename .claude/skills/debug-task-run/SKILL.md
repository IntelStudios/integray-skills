---
name: debug-task-run
description: >-
  Start an Integray Task via Remote API and fetch a step data snapshot for
  debugging. Use when the user asks to run a task, inspect step output, download
  a TaskRun snapshot, or debug a live process. Snapshot GET is version-gated
  (docs/instance-version.md Feature availability, from rel-2025-03.018).
disable-model-invocation: true
---

# Debug a live Task Run (step snapshot)

The Remote API can return the stored data snapshot of one step in one task run.
Use it when debugging a process: start the task, wait until the step has run, then
read the JSON.

**Floor:** [docs/instance-version.md](../../../docs/instance-version.md) **Feature
availability**. Remote API (`start` / `status`) from **`rel-2025-03.017`**. Snapshot GET
from **`rel-2025-03.018`**. Protocol: [docs/transfer/remote-api.md](../../../docs/transfer/remote-api.md)
(Task run snapshot). Do **not** invent the snapshot path on `017`.

## Version gate (mandatory)

```bash
$PYTHON scripts/get-instance-version.py \
  --connection projects/<name>/.integray-connection.json
```

Stdout `productLine=` must satisfy the **Feature availability** row for this snapshot
([docs/instance-version.md](../../../docs/instance-version.md)). Today that row is
**`rel-2025-03.018` or later**. Older (`rel-2025-03.017`, …) → **stop**. Do not curl
`/api/Integray` by hand. The snapshot subcommand also refuses older lines.

## Prerequisites

- `projects/<name>/` with `.integray-connection.json` (`baseUrl`, `companySlug`, Remote
  control `token`, `permission`).
- **`permission`:** `status` and `snapshot` are GET → any level including `read-only`.
  **`start`** needs **`read-write` or `full`**. Do not change `permission` unless the
  user asks.
- Numeric **`Task.ID`** and **`Step.ID`** from `projects/<name>/working/tasks/*.json`
  (`Steps[].ID`). That Step `ID` is `taskStepID` in the log. **Not** CopyID, **not**
  a task-step-run id.

A snapshot is stored only when the Step’s `DataSnapshotCondition` wrote one
(`2` Everytime, or `1` On error when the step failed). `0` Never → HTTP **204** even
if the step ran.

## Commands

From repo root (`.venv/bin/python` when `.venv/` exists):

```bash
# 1. Start (on-demand). Prints taskRunID=
$PYTHON scripts/task-run.py \
  --connection projects/<name>/.integray-connection.json \
  start --task-id <Task.ID>

# 2. Poll until status is not 1 / 100 / 101 (or until the step you care about has run)
$PYTHON scripts/task-run.py \
  --connection projects/<name>/.integray-connection.json \
  status --task-run-id <taskRunID>

# 3. Snapshot (018+). Write to a file; do not paste a large JSON into chat.
$PYTHON scripts/task-run.py \
  --connection projects/<name>/.integray-connection.json \
  snapshot --task-run-id <taskRunID> --step-id <Step.ID> \
  --out /tmp/step-snapshot.json
```

Existing run: skip `start`, use the `taskRunID` the user gave (or `status` on a known id).

`start` / `status` exist without that snapshot floor (see the same table). Only **`snapshot`** is gated.

## Snapshot HTTP

| Status | Meaning |
|--------|---------|
| **200** | Step in that run ran or is running, and a snapshot is stored. JSON `Schema` / `Rows` / `HasDefinedRows`. Cells stored as `{"$dataRef":"<guid>"}` are replaced with file contents (string). Missing file → `null`. `$dataRefSource` (endpoint data) is used when present. |
| **204** | Step ran or is running (`InProgress` 100, success 200–203, failure 300–307) but nothing was stored. Empty body. Script prints `snapshot=none`. |
| **404** | Task run missing / wrong company, or the step did **not** run in that run (`Unknown` 0, `Scheduled` 1, `WaitingForAgent` 101, `NotRun` 401, `Parked` 999). |
| **401** | Remote control token missing or wrong. |

Do not treat 204 as a failed start. Check `DataSnapshotCondition` on the Step.

## How to read a 200 body

Contract and example: [docs/transfer/remote-api.md](../../../docs/transfer/remote-api.md)
(Task run snapshot). Same tree as [docs/entities/data-addressing.md](../../../docs/entities/data-addressing.md).

- `Schema` / `Rows` / `HasDefinedRows`. Root schema `Name` is `""`.
- `{ts:<guid>}` = Step `CopyID`, `{dsc:<guid>}` = column `CopyID`, `{e:<guid>}` =
  Endpoint `CopyID`. `task-run.py snapshot` prints the map from `working/` automatically.
- `DataType` **7** = table (nested `Schema`, cell is an array of rows).
- Catalog schema (`Guid`+`Version`, e.g. system Text) uses display column names (`Text`).
  Inline schema (`Name` only) keeps `{dsc:…}`.
- The GET is the **whole assembled tree** at snapshot time, not only that Step’s output.
- `$dataRef` cells are already expanded to strings (missing file → `null`).

When reporting to the user, use the stdout tree (resolved names), not the raw keys.

## Workflow

1. Confirm company folder (`project:` or the folder in chat).
2. Run `get-instance-version.py`. If Feature availability says this instance is too old, **stop**.
3. Resolve Task/Step numeric IDs from `working/` (or from the user). Do not open a whole
   assembled transfer JSON.
4. If the user wants a **new** run and `permission` allows writes: `start`, then poll
   `status` (sleep between polls; do not busy-loop). Endpoint-triggered tasks may already
   have a `taskRunID` from the HTTP call — do not Start those unless asked.
5. `snapshot` with `--out`. Stdout is the **identity map + tree** (CopyIDs resolved
   from `projects/<name>/working/` beside the connection). Use that summary. Raw JSON
   stays in `--out` — do not paste it into chat. Keys in the file are `{ts:}`, `{dsc:}`,
   `{e:}` — not Step `Name`. Nested `{ts:}` inside a row is RowByRow under that parent.
   `--no-working` if you must skip the map. Do not dump megabytes of `$dataRef` payloads.
6. 404 on a still-running run: wait and retry, or the step is `NotRun` (branch skipped).

## Errors

- **`productLine=… does not include this API`** — instance is older than the Feature availability row.
- **401** — Remote control token. Not a login JWT.
- **404** on `start` / `status` — wrong `baseUrl` / `companySlug`, or unknown id.
- **Permission** — `start` in `read-only` exits; ask the user to set `read-write` or `full`.

Remote API **401/403/404/400** often have an **empty body**. Use the status code.
