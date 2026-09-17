# Status — company loop + permission (2026-09-15)

Public Integray KB in the xeelo-skills layout. **Fáze 0 is done.** `/download-config`, `/backup`, and `/publish` (Upload + Process) are in. Self-test lives at `projects/self-test/`.

## Decisions (do not reopen without a reason)

- **Public KB** = this repo except `projects/` and `internal/`.
- **Companies:** `projects/` is **not** a git. Each `projects/<name>/` **is** its own private git (clone or `git init` + user-hosted remote). Not a branch of `integray-skills`. No git submodules. Public integray-skills still gitignores `/projects/`.
- **Self-test** is `projects/self-test/` (`https://github.com/IntelStudios/integray-self-test.git`). Do not copy overlay token pools into git. Do not merge company files into this public repo.
- **Config Transfer is Full Sync.** Never generate a partial transfer that would delete existing company entities. Xeelo-style delta Object Transfer does **not** apply.
- **No YAML entity spec** for now. JSON (full snapshot ± overlay later) is the working format. A higher-level DSL is a later decision, not Fáze 1.
- **Snapshots** are immutable. Copy into `working/` and edit there. Do not use Xeelo-style `changes/<slug>/` loops; git is the history. Deploy is Remote API Upload + Process of `working/` ([docs/transfer/remote-api.md](docs/transfer/remote-api.md)).
- **No** `platform-gotchas.md`. Repeatable platform facts go into the matching `docs/entities/` or `docs/transfer/` file. Project bugs stay with the company (`PLATFORM_BUGS.md` u self-testu) until filed.
- **Work mode** (`internal/work-mode.md`): `kb: read` \| `read-write` (default `read`; there is no write-only mode) and `project:` = folder under `projects/` (not Integray `companySlug`). `kb: read-write` may record repeatable platform facts into the public KB. `kb: read` only edits `projects/<name>/` as a side effect.
- **Connection** is `baseUrl` + `companySlug` + **Remote control token** (not a login JWT). Optional `permission` (`read-only` \| `read-write` \| `full`; missing = `read-only`). Do not infer slug from hostname.
- **CopyID** is the import matching key. On edit, keep existing CopyIDs. See [docs/best-practices.md](docs/best-practices.md) and [recipes/edit-existing-transfer.md](recipes/edit-existing-transfer.md).

## What this version contains

- Ported generic KB from `SmarterMDM-IntegrayTest` `master` (docs, catalogs, generic example).
- `AGENT.md`, `CLAUDE.md`, `.cursor/rules/`, skills `/new-project`, `/download-config`, `/backup`, `/publish`, `/sync-main`.
- `scripts/download-config-transfer.py`, `scripts/backup-config-transfer.py`, `scripts/upload-config-transfer.py`, `scripts/process-config-transfer.py`, `scripts/check-transfer-schemas.py`.
- Templates for each company git (`templates/projects-repo/`) and per-company `conventions.md`.
- Catalogs in `data/` (`connectors.json`, `configuration-schemas.json`, `data-schemas.json`).
- Connection `permission` (`read-only` / `read-write` / `full`) on `.integray-connection.json` and in the Remote API scripts.

## What is not done (next after vacation)

1. **Fáze 1 remainder** — broader `validate-transfer` (overlay merge, etc.). Schema membership + required mappings: `scripts/check-transfer-schemas.py`. Extract snapshot → `env/` later.
2. **Overlay merge** — edit named entities, merge onto downloaded snapshot, emit a **complete** transfer. Still JSON, not YAML.
3. **Connector track skill** `/new-connector` — later.
4. **`make extract`** for catalogs from ICR / a live instance — catalogs are a static snapshot for now.

## Old repo

`SmarterMDM-IntegrayTest` was the old generic KB + overlay. Generic files there are superseded by this repo. Self-test company files live in `projects/self-test/`.

## Product source

`/Users/tomas/Sources/Intelstudios/SmarterMDM-Integray` — use via `internal/` when the KB is incomplete. Do not copy source paths into `docs/`. Connector catalogs do **not** come from that repo (ICR / live instance).
