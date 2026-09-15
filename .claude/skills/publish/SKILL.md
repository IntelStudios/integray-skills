---
name: publish
description: >-
  Deploy projects/<name>/working/ Config Transfer JSON via Remote API:
  Upload, Process onlyTest, then Process publish. Use when the user asks
  to upload, deploy, process, or publish a transfer, or invokes /publish.
disable-model-invocation: true
---

# Publish Config Transfer (Upload + Process)

Send **`working/`** to the company: Upload (pre-check) → Process `onlyTest` → Process `publish` per conventions. Read [AGENT.md](../../../AGENT.md). Protocol: [docs/transfer/remote-api.md](../../../docs/transfer/remote-api.md).

Do **not** run this after download or after generating JSON unless the user asked to deploy, picked a run option, or conventions say **Publish after dry-run:** `auto` *after a successful onlyTest*.

`snapshots/` is immutable. Upload `working/`, never a snapshot. Process the `transferId` from **Upload**, never from `/backup`.

## Prerequisites

- `projects/<name>/` exists (clone or `/new-project`).
- `projects/<name>/.integray-connection.json` is filled (`baseUrl`, `companySlug`, Remote control `token`).
- `permission` — **`read-write`** or **`full`** to start this skill. Missing/empty = `read-only` → **stop**. Tell the user to set `permission` if they want to deploy. Do not change the field unless they ask.
  - `read-write`: Upload + Process `--only-test`. Skip `--publish` and announce that it needs `full`.
  - `full`: also Process `--publish` per conventions.
- `working/` has the complete Config Transfer JSON (copy of the newest snapshot, then edited). One `*.json`, or the user named the file.
- Full Sync: the file must contain everything the company should keep.

## Inputs

Determine from the user message or ask once:

- **`<name>`** — folder under `projects/`. Default to `project:` in `internal/work-mode.md`, then the folder named in chat. This is not the Integray `companySlug`.
- **`--file`** — only if `working/` has more than one JSON.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If dependencies are missing (`httpx`):

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Step 0 — Backup (conventions)

**Backup before process** in `projects/<name>/conventions.md` (`ask` | `auto`; missing = `ask`).

- `auto` — run `/backup` (the backup skill). Keep `transferId`. Do **not** Process it.
- `ask` — offer three options; do not backup unless they pick a run option.

## Step 1 — Upload

```bash
$PYTHON scripts/upload-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

Optional: `--file projects/<name>/working/<file>.json`, `--timeout 300`.

Note `transferId=` and `succeeded=` from stdout.

**Stop** if exit code ≠ 0 or `succeeded=false` (missing connectors). Report `hasUnresolvedReferences` / `hasSensitiveVariables`. Do not Process.

## Step 2 — onlyTest (always, do not ask)

```bash
$PYTHON scripts/process-config-transfer.py \
  --connection projects/<name>/.integray-connection.json \
  --transfer-id <upload-transferId> \
  --only-test
```

If this fails, report the error. Do **not** offer `--publish`.

## Step 3 — Publish (conventions)

**Stop** `--publish` unless connection `permission` is **`full`**. At `read-write`, announce that `onlyTest` ran and Process `--publish` needs `"permission": "full"`. Do not treat **Publish after dry-run: auto** as an override.

**Publish after dry-run** (`ask` | `auto`; missing = `ask`) applies only at **`full`**.

- `auto` — Process `--publish`. Announce that conventions say so.
- `ask` — **Publish now** / **Publish now and remember for this company** / **Don't publish**. Remember → set the key to `auto` in `conventions.md`.

```bash
$PYTHON scripts/process-config-transfer.py \
  --connection projects/<name>/.integray-connection.json \
  --transfer-id <same-upload-transferId> \
  --publish
```

Inspect stdout `publishResult.*`. Exit 2 / HTTP 422 = import already applied, cache rebuild failed — read messages, fix `working/`, Upload again (new id), onlyTest, then `--publish`.

`--apply` (publish false) only if the user explicitly wants apply without cache rebuild.

## Step 4 — Download (conventions)

After a **successful** `--publish` only. **Download after publish** (`ask` | `auto`).

- Run `/download-config`, then copy the new snapshot into `working/` (overwrite).

Failed publish: do not download.

## Errors

- **401** — Remote control token. Not a login JWT.
- **Permission** — script exits if Upload/`onlyTest` needs `read-write` or `--publish` needs `full`. Do not retry until the user sets `permission`.
- **404** — `baseUrl` / `companySlug`, or company missing from runtime cache — publish in DX.
- **400** — often empty body; `onlyTest` + `publish` together is invalid (the script forbids it).
- **422** — import applied, publish failed.

Remote API **401/403/404/400** often have an **empty body**. Use the status code.
