# Integray Agent Playbook

**Start here** when asked to create or modify Integray configuration, or to develop a connector.

## What is the KB

**KB** = this repository **except** `projects/` and `internal/`.

| Path | Role |
|------|------|
| `docs/`, `recipes/`, `data/`, `AGENT.md`, skills, … | Knowledge base. When the user asks what the KB contains or what it says, answer **only** from here. |
| `projects/` | Company working copies. Gitignored; one **private** git repo = the whole directory. You may **draw from** them when implementing. They are **not** KB content. |
| `internal/` | Optional local playbook (gitignored). Product-source index for this machine. **Not** KB. If it exists, read it when the KB is incomplete. Write extracted facts into the public KB **only in `project-kb` work mode** — do not copy source paths into `docs/` or `recipes/`. |

Do not present `projects/` or `internal/` as “what’s in the KB”. Mention a project path only if the user asks for a sample or a specific company.

**Check `projects/` first** before creating a company folder, downloading a transfer, or otherwise using that tree. If it has no company folder and no nested `projects/.git`, explain the nested-repo intent and **offer** to initialize it — do not silently scaffold `projects/<name>/`. Canonical text: [docs/projects.md](docs/projects.md).

Milestone and leftover work: [STATUS.md](STATUS.md).

## Work mode

Source of truth: `internal/work-mode.md` (gitignored; this machine only). Read it before company work. Missing `internal/`, missing file, or any other value → **`project`**. Template: [`templates/internal/work-mode.md`](templates/internal/work-mode.md). Do not rewrite it unless the user asks to switch.

Allowed: `project` | `project-kb`.

| Mode | Company work | KB |
|------|----------------|-----|
| **`project`** (default) | Edit `projects/<name>/` | **Read** only. If you hit a KB gap, one sentence at the end — do not fix it. |
| **`project-kb`** | Same | Also **harvest**: write repeatable platform facts into `docs/` / `recipes/` / `data/`. Not company-specific data, not `internal/` paths, not a chat dump. |

Direct KB requests (“fix this recipe”, “what does the KB say”) are **not** gated.

Announce once at the start of company work (`Režim: project` or `Režim: project-kb`). If `projects/<name>/conventions.md` exists, **read it** before editing transfers.

## Two tracks

### A — Company Config Transfer

When the user asks to create, edit, upload, or deploy Integray tasks / endpoints / transfers:

1. Read this playbook and [docs/transfer/config-transfer-format.md](docs/transfer/config-transfer-format.md)
2. Read [docs/best-practices.md](docs/best-practices.md) (CopyIDs) and [docs/entities/variables.md](docs/entities/variables.md) if secrets or `${#Code}` are involved
3. Look up connectors in [data/connectors.json](data/connectors.json) → configuration in [data/configuration-schemas.json](data/configuration-schemas.json) → columns in [data/data-schemas.json](data/data-schemas.json). Hidden fields: [docs/entities/configuration-overrides.md](docs/entities/configuration-overrides.md)
4. Multi-step / branched tasks: [docs/entities/data-addressing.md](docs/entities/data-addressing.md). Filters: [docs/entities/input-data-filter.md](docs/entities/input-data-filter.md). Local vars: [docs/entities/local-variables.md](docs/entities/local-variables.md). Checkpoint: [docs/entities/data-checkpoint.md](docs/entities/data-checkpoint.md)
5. Shape: [examples/generic_worked_example.json](examples/generic_worked_example.json). Live company file under `projects/<name>/` if present
6. **Full Sync:** the file you upload must contain everything the company should keep. Do not emit “only the new tasks” unless `conventions.md` says `greenfield: true`
7. **CopyID:** editing a transfer that was already imported → keep existing CopyIDs ([recipes/edit-existing-transfer.md](recipes/edit-existing-transfer.md))
8. Deploy only when the user asks — [docs/transfer/remote-api.md](docs/transfer/remote-api.md)

There is **no** YAML spec. Output is Config Transfer JSON.

### B — Connector development

Read [docs/connector-dev/rules.md](docs/connector-dev/rules.md). Validate metadata against [data/connector-dev.schema.json](data/connector-dev.schema.json). README template: [docs/connector-dev/readme-template.md](docs/connector-dev/readme-template.md). Work in the connector’s own repo, not in this KB’s `docs/`.

## Development loop (company config)

Scripts for download / validate / process are **not in this repo yet** ([STATUS.md](STATUS.md)). Use curl as in [remote-api.md](docs/transfer/remote-api.md).

```text
baseUrl + companySlug + token
  → GET Download → snapshots/
  → edit complete transfer (preserve CopyIDs)
  → POST Upload → pre-check
  → POST Process onlyTest=true
  → POST Process publish=true   (ask / auto from conventions)
  → GET Download again
```

Prefer **Backup** before a real Process when conventions say so (default: ask).

`onlyTest` and `publish` **cannot** be combined (HTTP 400).

### Agent loop in conventions

Keys in `projects/<name>/conventions.md` (`ask` | `auto`; missing = `ask`):

- **Backup before process**
- **Publish after dry-run**
- **Download after publish**

| Value | Behaviour |
|-------|-----------|
| **`auto`** | Do it. Announce that this company’s conventions say so. |
| **`ask`** | Offer three options (do it / do it and remember / skip). Do not run unless they pick a run option. |

**Remember** → set that key to `auto` in this company’s `conventions.md`. Failed `onlyTest` or missing connection: do not offer publish.

## Creating a new project

When the user asks for a **new empty company** (`projects/<name>/`):

0. **Check `projects/`** — [docs/projects.md](docs/projects.md). If there is no company and no nested git, explain the split, **offer** nested-repo init, and stop until `projects/` is ready.
1. Create `snapshots/`, `changes/` (`.gitkeep` if needed).
2. Copy [`templates/project/conventions.md`](templates/project/conventions.md) to `projects/<name>/conventions.md`.
3. Write **only** `projects/<name>/.integray-connection.json` — empty placeholders. **Never** copy `token` from other companies. **Do not** infer `companySlug` from `baseUrl`.
4. After creation, tell the user what to fill in.

```json
{
  "baseUrl": "https://<instance>.integray.app",
  "companySlug": "",
  "token": ""
}
```

| Field | Where to get it |
|-------|-----------------|
| `baseUrl` | Integray instance URL (not implied by slug) |
| `companySlug` | Company slug in DX / `${#SYSTEM_CompanySlug}` |
| `token` | Remote API Bearer JWT |

File is gitignored. Commit the new folder in `projects/` (private repo), not in integray-skills. Download requires **Allow sharing remote config transfer** on the company. Do not download until connection fields are filled.

## Skills

Canonical location: [`.agents/skills/`](.agents/skills/). Claude CLI: [CLAUDE.md](CLAUDE.md) points at the same files (copied under `.claude/skills/`).

| Skill | When | File |
|-------|------|------|
| `/new-project` | New empty company under `projects/<name>/` | [`.agents/skills/new-project/SKILL.md`](.agents/skills/new-project/SKILL.md) |
| `/sync-main` | Hourly check/pull of **integray-skills `main`** | [`.agents/skills/sync-main/SKILL.md`](.agents/skills/sync-main/SKILL.md) |

Download / publish / backup skills land with Fáze 1 scripts. Until then follow [remote-api.md](docs/transfer/remote-api.md) and this playbook.

### Change loop `notes.md`

When working under `projects/<name>/changes/<slug>/`:

- `tasks.md` = checklist
- `notes.md` = **Requested** vs **Done** for the next human/agent. Append on later rounds; do not silently rewrite history.

## Project layout

`projects/<name>/` = one Integray company.

```text
projects/<name>/
  conventions.md
  .integray-connection.json     # gitignored
  secrets.json                  # gitignored
  snapshots/<stamp>/*.json
  changes/<loop-slug>/
    tasks.md
    notes.md
    output/Transfer_*.json      # complete Config Transfer
```

## Short rules (Config Transfer)

- Ask for the transfer `Name` before generating.
- `Task.Type`: `0` Scheduled (Quartz 7-field cron), `1` OnDemand (default), `2` Endpoint. `Cron` is `null` unless `Type: 0`.
- `ID` unique sequential across the whole file. `TaskGroups`/`EndpointGroups` need a real non-zero `ID`.
- Exactly one `PrevStepCopyID: null` per task.
- `SelectedActionCode` must exist in `data/connectors.json`.
- No `.` in any entity `Name`. Respect varchar length limits in config-transfer-format §2.1.
- System schemas: reference `{"Guid","Version"}`. Custom: `{"CopyID"}`.
- `InputSchemaMapping` must cover every `AllowNull: false` column; mapped columns must share `Type`.
- After Process with `publish: true`, inspect `publishResult.messages[]`.
- Never store the Bearer token in transfer JSON or commit it.

## Checklist before delivery

- [ ] Env/snapshot is the latest download when editing an existing company
- [ ] Output transfer is **complete** (Full Sync) unless greenfield
- [ ] Existing CopyIDs preserved
- [ ] Connector Guid+Version from `data/connectors.json` (flag if catalog may be stale)
- [ ] Mapping coverage and type match ([config-transfer-format.md](docs/transfer/config-transfer-format.md) §7)
- [ ] `onlyTest` succeeded before offering publish
- [ ] Sensitive variables empty in portable JSON; user sets values via Variable API after import
