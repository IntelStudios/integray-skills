# Integray KB — overview

Integray is an integration platform: **tasks** made of **steps**, each step using a **connector** action. Configuration moves between companies as a **Config Transfer** JSON file.

This repository is the **generic** knowledge base. It must stay usable without knowing any one company. Live company transfers, credentials, and conventions live under `projects/<name>/` — each company is its own git; `projects/` is not a repo (see [projects.md](projects.md)).

## Two work tracks

| Track | Start here |
|-------|------------|
| Generate or edit a Config Transfer, deploy via Remote API | [AGENT.md](../AGENT.md), [config-transfer-format.md](transfer/config-transfer-format.md), [remote-api.md](transfer/remote-api.md) |
| Develop a .NET connector | [connector-dev/rules.md](connector-dev/rules.md) |

## Config Transfer in one paragraph

Import is **Full Sync**: match by `CopyID` (update vs insert); anything on the target company that is **absent** from the file is proposed for deletion. System connectors and system DataSchemas are referenced by `Guid`+`Version` (`data/connectors.json`, `data/data-schemas.json`). Custom schemas and all company entities use `CopyID`. Remote API: `{baseUrl}/api/Remote/{companySlug}/ConfigTransfer/…` with the company's Remote control token (`Authorization: Bearer …`).

## Catalogs

| File | Content |
|------|---------|
| [data/connectors.json](../data/connectors.json) | Production connectors — Guid, Version, actions |
| [data/configuration-schemas.json](../data/configuration-schemas.json) | NGX Configuration schemas |
| [data/data-schemas.json](../data/data-schemas.json) | System DataSchemas and nested table refs |

These files are a snapshot. If a transfer uses a connector version not in the catalog, say so and verify against the target instance.

## Entity docs

| Topic | File |
|-------|------|
| Transfer JSON, IDs, tasks, endpoints, publish errors | [transfer/config-transfer-format.md](transfer/config-transfer-format.md) |
| Remote API Download / Backup / Upload / Process | [transfer/remote-api.md](transfer/remote-api.md) |
| CopyIDs on edit, unique names, `VariablesDefaults` | [best-practices.md](best-practices.md) |
| Step-to-step addressing | [entities/data-addressing.md](entities/data-addressing.md) |
| `InputDataFilter` | [entities/input-data-filter.md](entities/input-data-filter.md) |
| Company variables `${#Code}` | [entities/variables.md](entities/variables.md) |
| Task local variables | [entities/local-variables.md](entities/local-variables.md) |
| Data checkpoint | [entities/data-checkpoint.md](entities/data-checkpoint.md) |
| Hidden configuration fields | [entities/configuration-overrides.md](entities/configuration-overrides.md) |
