---
name: download-config
description: >-
  Download the latest Integray Config Transfer JSON via Remote API into
  projects/<name>/snapshots/. Use when the user asks to download, refresh, or
  pull a config transfer or snapshot, sync from the company, or invokes
  /download-config.
disable-model-invocation: true
---

# Download Config Transfer

Download the full company Config Transfer (`GET /api/Remote/{CompanySlug}/ConfigTransfer/Download`) into `projects/<name>/snapshots/<stamp>/`. Read [AGENT.md](../../../AGENT.md) for the development loop. Protocol: [docs/transfer/remote-api.md](../../../docs/transfer/remote-api.md).

This skill does **not** extract `env/` and does **not** publish. There is no `/download-db` — Integray has no Xeelo DB transfer. This is **not** `/backup` (that stores a transfer record on the server, no JSON file).

## Prerequisites

- `projects/` is ready: a company folder **or** nested `projects/.git`. If not, follow [docs/projects.md](../../../docs/projects.md) — do not download into a missing tree.
- `projects/<name>/.integray-connection.json` exists and is filled in:
  - `baseUrl` — Integray instance URL (not implied by slug)
  - `companySlug` — company in that instance
  - `token` — company **Remote control token** (Company Detail → Remote control → Allow control / Token). Not a login JWT. See [remote-api.md](../../../docs/transfer/remote-api.md).
- If the connection file is missing or any field is empty, stop and tell the user to complete it first (see `/new-project` checklist).
- The company must have **Allow sharing remote config transfer** enabled (otherwise HTTP 403).

## Instance vs company

| Term | Meaning | Where |
|------|---------|--------|
| **instance** | Integray host | `baseUrl` |
| **company** | Tenant inside that instance | `companySlug`; URL `/api/Remote/{CompanySlug}/` |

## Inputs

Determine from the user message or ask once:

- **`<name>`** — project slug under `projects/`. Default to the company mentioned in chat or the one whose connection file is open.

## Python environment

From repo root, use `.venv/bin/python` when `.venv/` exists. If dependencies are missing (`httpx`), create the venv and install:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `PYTHON=python` only when system Python already has requirements installed.

## Download

```bash
$PYTHON scripts/download-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

Optional flags:

- `--project projects/<name>` — override project directory (default: parent of connection file)
- `--timeout 300` — HTTP timeout seconds (default 300)

Note the JSON path from stdout (`Wrote projects/<name>/snapshots/<stamp>/<file>.json`).

Keep the snapshot; do not delete it. Do not generate a partial transfer from this download — import is Full Sync.

## Output

Report:

- **Snapshot JSON** — path and byte size
- **Transfer `Name`** (and task/endpoint counts if cheap to read from the file)

Remove `snapshots/.gitkeep` if real content was written.

## On success — suggest next step

Editing starts from this snapshot (preserve CopyIDs). Do not offer `/publish` from download alone.

## Errors

- **401** — missing or wrong Remote control token. Ask the user to paste the current token from Company Detail → Remote control into `.integray-connection.json`. Do not use a DX login JWT.
- **403** — enable **Allow sharing remote config transfer** on the company, or the token cannot download.
- **404** — wrong `baseUrl` or `companySlug` (do not guess slug from hostname).
- **Timeout** — large companies can be slow; retry with higher `--timeout`.
