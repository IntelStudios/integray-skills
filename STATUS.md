# Status — Fáze 0 + `/download-config` (2026-09-14)

Public Integray KB in the xeelo-skills layout. **Fáze 0 is done.** `/download-config` is in (snapshot JSON only, no `env/` extract). Nested `projects/` git and self-test migration are **not** done.

## Decisions (do not reopen without a reason)

- **Public KB** = this repo except `projects/` and `internal/`.
- **Companies** live in a **nested private git** at `projects/` (one repo for all companies). Each company is `projects/<name>/` on that repo’s `main` — **not** a branch of `integray-skills`.
- **Self-test** belongs at `projects/self-test/` in that private git. It is **still** in `/Users/tomas/Sources/Intelstudios/SmarterMDM-IntegrayTest` on branch `self-test` until someone clones/moves it. Do not copy `specific/` into this public repo. Do not put token pools in git.
- **Config Transfer is Full Sync.** Never generate a partial transfer that would delete existing company entities. Xeelo-style delta Object Transfer does **not** apply.
- **No YAML entity spec** for now. JSON (full snapshot ± overlay later) is the working format. A higher-level DSL is a later decision, not Fáze 1.
- **No** `platform-gotchas.md`. Repeatable platform facts go into the matching `docs/entities/` or `docs/transfer/` file. Project bugs stay with the company (`PLATFORM_BUGS.md` u self-testu) until filed.
- **Harvest** = in work mode `project-kb` only: write a repeatable platform fact into the public KB. Default mode `project` only edits `projects/<name>/`.
- **Connection** is `baseUrl` + `companySlug` + **Remote control token** (not a login JWT). Do not infer slug from hostname.
- **CopyID** is the import matching key. On edit, keep existing CopyIDs. See [docs/best-practices.md](docs/best-practices.md) and [recipes/edit-existing-transfer.md](recipes/edit-existing-transfer.md).

## What this version contains

- Ported generic KB from `SmarterMDM-IntegrayTest` `master` (docs, catalogs, generic example).
- `AGENT.md`, `CLAUDE.md`, `.cursor/rules/`, skills `/new-project`, `/download-config`, `/sync-main`.
- `scripts/download-config-transfer.py` (`/download-config`).
- Templates for the nested `projects/` git and per-company `conventions.md`.
- Catalogs in `data/` (`connectors.json`, `configuration-schemas.json`, `data-schemas.json`).

## What is not done (next after vacation)

1. **Private `projects/` repo** — user hosts a private remote; agent may `git init` only if asked. Then move self-test from `SmarterMDM-IntegrayTest` / `specific/` into `projects/self-test/`.
2. **Fáze 1 remainder** — `upload` / `process` (`onlyTest` / `publish`) / `backup` / `validate-transfer`. Skills `/publish`, `/backup`, `/remote-api`. Extract snapshot → `env/` later.
3. **Overlay merge** — edit named entities, merge onto downloaded snapshot, emit a **complete** transfer. Still JSON, not YAML.
4. **Connector track skill** `/new-connector` — later.
5. **`make extract`** for catalogs from ICR / a live instance — catalogs are a static snapshot for now.
6. **`internal/`** on this machine — optional `work-mode.md` + pointer at `/Users/tomas/Sources/Intelstudios/SmarterMDM-Integray`. Template: `templates/internal/work-mode.md`.

## Old repo

`/Users/tomas/Sources/Intelstudios/SmarterMDM-IntegrayTest` remains the live self-test overlay until migrated. Generic files there are superseded by this repo; do not keep editing both as source of truth.

## Product source

`/Users/tomas/Sources/Intelstudios/SmarterMDM-Integray` — use via `internal/` when the KB is incomplete. Do not copy source paths into `docs/`. Connector catalogs do **not** come from that repo (ICR / live instance).
