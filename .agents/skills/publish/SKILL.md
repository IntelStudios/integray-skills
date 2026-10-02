---
name: publish
description: >-
  Deploy projects/<name>/working/ (split entity tree) via Remote API:
  assemble to a temp file, Upload, Process onlyTest, then Process publish. Use when the user asks
  to upload, deploy, process, or publish a transfer, or invokes /publish.
disable-model-invocation: true
---

# Publish Config Transfer (Upload + Process)

Run **one** script (schema check, Backup, Upload, onlyTest, `--publish` when conventions say auto and `permission` is `full`):

```bash
$PYTHON scripts/deploy-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

Optional `--file`, `--stamp-copy-id <Configuration CopyID>`. Backup always runs (do not ask). The script does **not** download into `working/`. Statement-only HTML: [edit-statement](../edit-statement/SKILL.md).

Do **not** run this after download unless the user asked to deploy (`/publish`), work-mode **`publish: always`** after finishing `working/` edits, or they picked a run option. Company **Publish after dry-run: auto** applies only *after a successful onlyTest* inside an already-started deploy.

`snapshots/` is immutable. Deploy **assembles** split `working/` to a temp file, Uploads that, then deletes the temp. Never Upload a snapshot. Never leave an assembled JSON in `working/`. Process the `transferId` from **Upload**, never from `/backup`. Layout: [working-split.md](../../../docs/transfer/working-split.md). Commands: [scripts/README.md](../../../scripts/README.md). Protocol: [remote-api.md](../../../docs/transfer/remote-api.md).

## Prerequisites

- `projects/<name>/` exists (clone or `/new-project`).
- `projects/<name>/.integray-connection.json` is filled (`baseUrl`, `companySlug`, Remote control `token`).
- `permission` — **`read-write`** or **`full`** to start. Missing/empty = `read-only` → **stop**. Do not change the field unless they ask.
  - `read-write`: Upload + Process `--only-test`. Skip `--publish` and announce that it needs `full`.
  - `full`: also Process `--publish` per conventions.
- `working/` is the split tree from `/download-config` (then edited). Full Sync: assemble must contain everything the company should keep.
- Schema check already passed: `$PYTHON scripts/check-transfer-schemas.py projects/<name>/working` (empty **stdout**, exit 0). If stdout prints anything, **stop**. Stderr catalog lines: tell the user, do not block.

## Inputs

- **`<name>`** — folder under `projects/`. Default to `project:` in `internal/work-mode.md`, then the folder named in chat. Not the Integray `companySlug`.
- **`--file`** — only if uploading an already-assembled JSON. Default is assemble `working/`.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If `httpx` is missing: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.

## After deploy

If conventions **Publish after dry-run** is `ask` (`permission` `full`), the script prints `publish=skipped` with the Upload `transferId`. Then **Publish now** / **Publish now and remember for this company** / **Don't publish**. Remember → set the key to `auto` in `conventions.md`. Process `--publish`:

```bash
$PYTHON scripts/process-config-transfer.py \
  --connection projects/<name>/.integray-connection.json \
  --transfer-id <upload-transferId> \
  --publish
```

After a **successful** `--publish` only: **Download after publish** (`ask` | `auto`). `auto` or they confirm → `/download-config`. Failed publish: do not download.

Split Upload / onlyTest / Process (when the combined script cannot run): [scripts/README.md](../../../scripts/README.md). Do not re-implement that path here.

## Errors

- **401** — Remote control token. Not a login JWT.
- **Permission** — script exits if Upload/`onlyTest` needs `read-write` or `--publish` needs `full`.
- **404** — `baseUrl` / `companySlug`, or company missing from runtime cache — publish in DX.
- **400** — often empty body; `onlyTest` + `publish` together is invalid.
- **422** — import applied, publish failed.
- **`succeeded=false`** — missing connectors; do not Process.
- **`hasUnresolvedReferences=true` with `succeeded=true`** — do not treat as a failed Upload. Mention it. Same-company roundtrip of a complete export is a known false positive (pre-check looks at numeric `CompanyID`/`EndpointID`/`TaskID`, not `SameCompany`+CopyID).

Remote API **401/403/404/400** often have an **empty body**. Use the status code.
