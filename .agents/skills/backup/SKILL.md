---
name: backup
description: >-
  Store a Config Transfer backup record on the Integray company via Remote API
  (POST ConfigTransfer/Backup). Use when conventions say Backup before process,
  the user asks to backup live config on the instance, or invokes /backup.
  Not a local snapshot — that is /download-config.
disable-model-invocation: true
---

# Backup Config Transfer (on-instance)

`POST /api/Remote/{CompanySlug}/ConfigTransfer/Backup` stores the current company configuration as a **transfer record on the Integray server** and returns `transferId` only. No JSON file. Runs the same connector pre-check as Upload. Nothing is applied. Optional body `deleteOlderThan` (calendar days) hard-deletes older `ApplicationBackup_*` records for that company; omit it unless the user asked to prune.

This is **not** `/download-config`. Download writes JSON under `projects/<name>/snapshots/`. Backup is the undo point on the instance (conventions **Backup before process**).

Read [AGENT.md](../../../AGENT.md). Protocol: [docs/transfer/remote-api.md](../../../docs/transfer/remote-api.md).

## Prerequisites

- `projects/<name>/` exists (clone or `/new-project`). `projects/` is a directory, not a git. If the company folder is missing, follow [docs/projects.md](../../../docs/projects.md).
- `projects/<name>/.integray-connection.json` exists and is filled in:
  - `baseUrl` — Integray instance URL (not implied by slug)
  - `companySlug` — company in that instance
  - `token` — company **Remote control token** (Company Detail → Remote control → Allow control / Token). Not a login JWT. See [remote-api.md](../../../docs/transfer/remote-api.md).
  - `permission` — missing/empty = `read-only`. Backup is allowed at every level (it does not apply the transfer).
- If the connection file is missing or any field is empty, stop and tell the user to complete it first (see `/new-project` checklist).

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

## Backup

```bash
$PYTHON scripts/backup-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

Optional: `--timeout 300` (default 300). `--delete-older-than N` only when the user asked to prune older `ApplicationBackup_*` records (calendar days, exclusive). Do not pass it for a normal **Backup before process**.

Note `transferId=` from stdout. Keep it (e.g. in the change `notes.md`). **Do not** Process this id as the deploy.

## Output

Report:

- **`transferId`** — server record of the live company at this moment
- Remind: deploy uses the `transferId` from **Upload** of the edited file

## On success — next step

When the user wants to deploy `working/`, follow `/publish` (Upload this file, Process that Upload id). Do not offer `/publish` from backup alone.

## Errors

- **401** — missing or wrong Remote control token. Ask the user to paste the current token from Company Detail → Remote control into `.integray-connection.json`. Do not use a DX login JWT.
- **404** — wrong `baseUrl` or `companySlug` (do not guess slug from hostname). If both are correct, the company may be missing from the runtime configuration cache — publish it in DX and retry.
- **Timeout** — large companies can be slow; retry with higher `--timeout`.

Remote API errors **401/403/404/400** often have an **empty body**. Use the status code; do not treat a missing JSON error as a client bug.
