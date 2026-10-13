---
name: download-config
description: >-
  Download the latest Integray Config Transfer JSON via Remote API into
  projects/<name>/snapshots/, split it into working/ immediately, then report
  statistics. Use when the user asks to download, refresh, or pull a config
  transfer or snapshot, sync from the company, or invokes /download-config.
disable-model-invocation: true
---

# Download Config Transfer

Download the full company Config Transfer (`GET /api/Remote/{CompanySlug}/ConfigTransfer/Download`) into `projects/<name>/snapshots/<stamp>/`, **then split it into `working/` immediately**, then report statistics. Read [AGENT.md](../../../AGENT.md) for the development loop. On-disk layout: [docs/transfer/working-split.md](../../../docs/transfer/working-split.md). Protocol: [docs/transfer/remote-api.md](../../../docs/transfer/remote-api.md).

This skill does **not** extract `env/` and does **not** publish. There is no `/download-db` — Integray has no Xeelo DB transfer. This is **not** `/backup` (that stores a transfer record on the server, no JSON file).

## Prerequisites

- `projects/<name>/` exists (clone or `/new-project`). `projects/` is a directory, not a git. If the company folder is missing, follow [docs/projects.md](../../../docs/projects.md) — do not silently scaffold, do not download into a missing tree.
- `projects/<name>/.integray-connection.json` exists and is filled in:
  - `baseUrl` — Integray instance URL (not implied by slug)
  - `companySlug` — company in that instance
  - `token` — company **Remote control token** (Company Detail → Remote control → Allow control / Token). Not a login JWT. See [remote-api.md](../../../docs/transfer/remote-api.md).
  - `permission` — missing/empty = `read-only`. Download is allowed at every level.
- If the connection file is missing or any field is empty, stop and tell the user to complete it first (see `/new-project` checklist).
- The company must have **Allow sharing remote config transfer** enabled (otherwise HTTP 403).

## Instance vs company

| Term | Meaning | Where |
|------|---------|--------|
| **instance** | Integray host | `baseUrl` |
| **company** | Tenant inside that instance | `companySlug`; URL `/api/Remote/{CompanySlug}/` |

## Inputs

Determine from the user message or ask once:

- **`<name>`** — folder under `projects/`. Default to `project:` in `internal/work-mode.md`, then the folder named in chat, then the one whose connection file is open. This is not the Integray `companySlug`.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If dependencies are missing (`httpx`), create the venv and install:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `PYTHON=python` only when system Python already has requirements installed.

## Download (split is part of this command)

```bash
$PYTHON scripts/download-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

Optional flags:

- `--project projects/<name>` — override project directory (default: parent of connection file)
- `--timeout 300` — HTTP timeout seconds (default 300)

Do **not** pass `--no-split`. `--replace-working` is ignored (always replace).

Download **clears** `projects/<name>/working/` (everything except `.gitkeep`) and writes a fresh split of the live export. Do **not** ask. Unpublished edits in `working/` are lost (`snapshots/` stay).

**Download after publish:** `auto` — they already opted in; run this command after a successful `--publish`. `ask` — still ask whether to download, not whether to replace `working/`.

The script writes `snapshots/<stamp>/`, **immediately** splits into `working/`, then prints statistics.

Keep the snapshot; do not delete it and **do not edit it**. Do not copy the snapshot JSON into `working/` as a single file. Import is Full Sync — do not generate a partial transfer from this download. Do not open the snapshot JSON in chat.

## Output (report stdout, in this order)

The script already printed these. Repeat them to the user. Do not re-read the snapshot to compute them.

- **Snapshot JSON** — `Wrote` path and byte size
- **Split** — `working/` path and file count
- **Transfer `Name`**
- **Counts** — `tasks`, `endpoints`, `dataSchemas`, `configurations`, and the other `key=n` lines
- **Sensitive variables** — `sensitiveVariables=` names (`IsSensitive: true`; `Value` empty on export). Do not treat the file as a secret dump.
- **Connector versions** — lines `connector-outdated:` / `connector-mixed:` vs
  `data/connectors.json` newest. Repeat them. **Offer** an update to the catalog
  newest, and unification when one Guid has several Versions. Do **not** bump
  Versions until they confirm. Same check anytime:
  `python scripts/check-connector-versions.py projects/<name>/working`
  (empty stdout = nothing to offer; not a delivery gate).

Remove `snapshots/.gitkeep` if real content was written.

## On success — suggest next step

Editing is the split tree in `working/` (preserve CopyIDs). `/publish` assembles to a temp file, Uploads, deletes the temp. `/assemble` writes a JSON and leaves it. Do not offer `/publish` from download alone. If connector version lines printed, ask whether to update / unify.

## Errors

- **401** — missing or wrong Remote control token. Ask the user to paste the current token from Company Detail → Remote control into `.integray-connection.json`. Do not use a DX login JWT.
- **403** — enable **Allow sharing remote config transfer** on the company, or the token cannot download.
- **404** — wrong `baseUrl` or `companySlug` (do not guess slug from hostname). If both are correct, the company may be missing from the runtime configuration cache — publish it in DX and retry.
- **Timeout** — large companies can be slow; retry with higher `--timeout`.

Remote API errors **401/403/404/400** often have an **empty body**. Use the status code; do not treat a missing JSON error as a client bug.
