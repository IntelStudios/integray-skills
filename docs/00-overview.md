# Integray KB — overview

Integray is an integration platform: **tasks** made of **steps**, each step using a **connector** action. Configuration moves between companies as a **Config Transfer** JSON file.

This repository is the **generic** knowledge base. It must stay usable without knowing any one company. Live company transfers, credentials, and conventions live under `projects/<name>/` — each company is its own git; `projects/` is not a repo (see [projects.md](projects.md)).

## Read order (agent)

1. [AGENT.md](../AGENT.md) — playbook: work mode, `permission`, skills, Full Sync loop
2. This file — map of docs and catalogs
3. The entity/transfer file for the thing you are changing
4. That project’s `conventions.md` before editing `working/`

Work mode (`internal/work-mode.md`, gitignored): `kb: read|read-write` (no write-only), `project:` = folder under `projects/` (not Integray `companySlug`), `publish: never|ask|always` (after `working/` edits; missing = ask the user and write the choice; explicit `/publish` always runs). Connection `permission` (`read-only` | `read-write` | `full`) gates live Remote API writes — [AGENT.md § Project permission](../AGENT.md#project-permission).

## Two work tracks

| Track | Start here |
|-------|------------|
| Generate or edit a Config Transfer, deploy via Remote API | [AGENT.md](../AGENT.md), the matching **section** of [config-transfer-format.md](transfer/config-transfer-format.md) (not the whole file), [remote-api.md](transfer/remote-api.md) |
| Develop a .NET connector | [connector-dev/rules.md](connector-dev/rules.md) |

## Config Transfer in one paragraph

Import is **Full Sync**: match by `CopyID` (update vs insert); anything on the target company that is **absent** from the file is proposed for deletion. System connectors are referenced by `Guid`+`Version` (`data/connectors.json`) against the instance catalog. System DataSchemas use the same `Guid`+`Version` **reference form**, but must also appear in this file’s `DataSchemas[]` (`data/data-schemas.json` is the catalog, not the queue). Custom schemas and all company entities use `CopyID`. Remote API: `{baseUrl}/api/Remote/{companySlug}/ConfigTransfer/…` with the company's Remote control token (`Authorization: Bearer …`).

## Skills (company config)

`/new-project` → `/download-config` (snapshot, **immediate split**, statistics) → edit `working/` → `/backup` → `/publish` (assemble, Upload, `onlyTest`, `--publish` at `full`). After every edit of `working/`, run `python scripts/check-transfer-schemas.py projects/<name>/working` (empty **stdout**, exit 0) before treating the transfer as done. `/sync-main` is git on this KB, not a company deploy. Split layout: [working-split.md](transfer/working-split.md).

## Catalogs

| File | Content |
|------|---------|
| [data/connectors.json](../data/connectors.json) | Production connectors — Guid, Version, actions |
| [data/configuration-schemas.json](../data/configuration-schemas.json) | NGX Configuration schemas |
| [data/data-schemas.json](../data/data-schemas.json) | System DataSchemas and nested table refs |
| [data/connector-restrictions.json](../data/connector-restrictions.json) | Which agent kinds a connector Guid may run on |

These files are a snapshot of the **platform catalog** (ICR). Company `working/` is not a copy of them — only entities that company uses. If a transfer uses a connector version not in the dump, say so (stderr `catalog may be stale`) and verify against the target instance. Dump freshness is separate from the split.

## Entity docs

| Topic | File |
|-------|------|
| Transfer JSON, IDs, tasks, endpoints, publish errors | [transfer/config-transfer-format.md](transfer/config-transfer-format.md) (one section, not the whole file) |
| Split `working/` (download → decompose → stats) | [transfer/working-split.md](transfer/working-split.md) |
| Remote API (Config Transfer + Variable + other live endpoints) | [transfer/remote-api.md](transfer/remote-api.md) |
| Instance version (`GET /api/Integray`, unauthenticated) | [instance-version.md](instance-version.md) |
| CopyIDs on edit, unique names, `VariablesDefaults` | [best-practices.md](best-practices.md) |
| Step-to-step addressing | [entities/data-addressing.md](entities/data-addressing.md) |
| `InputDataFilter` | [entities/input-data-filter.md](entities/input-data-filter.md) |
| Company variables `${#Code}` | [entities/variables.md](entities/variables.md) |
| Task local variables | [entities/local-variables.md](entities/local-variables.md) |
| Data checkpoint | [entities/data-checkpoint.md](entities/data-checkpoint.md) |
| Hidden configuration fields | [entities/configuration-overrides.md](entities/configuration-overrides.md) |
| Which agent a connector may run on | [entities/connector-restrictions.md](entities/connector-restrictions.md) |
