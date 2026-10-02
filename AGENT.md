# Integray Agent Playbook

**Start here** when asked to create or modify Integray configuration, or to develop a connector.

## What is the KB

**KB** = this repository **except** `projects/` and `internal/`.

| Path | Role |
|------|------|
| `docs/`, `recipes/`, `data/`, `AGENT.md`, skills, … | Knowledge base. When the user asks what the KB contains or what it says, answer **only** from here. |
| `projects/` | Gitignored directory (**not** a git). Each `projects/<name>/` is **its own** private git. You may **draw from** them when implementing. They are **not** KB content. |
| `internal/` | Optional local playbook (gitignored). Product-source index for this machine. **Not** KB. If it exists, read it when the KB is incomplete. Write extracted facts into the public KB **only when `kb: read-write`** — do not copy source paths into `docs/` or `recipes/`. |

Do not present `projects/` or `internal/` as “what’s in the KB”. Mention a project path only if the user asks for a sample or a specific company.

**Check `projects/<name>/` first** before downloading a transfer or otherwise using that company. `projects/` may be empty — create it as a directory; do **not** `git init` there. If `projects/<name>/` is missing, **offer** clone (if they gave a URL) or `/new-project` — do not silently scaffold. Canonical text: [docs/projects.md](docs/projects.md).

## Work mode

Source of truth: `internal/work-mode.md` (gitignored; this machine only). Read it before project work. Template: [`templates/internal/work-mode.md`](templates/internal/work-mode.md). Do not rewrite it unless the user asks to switch.

```text
kb: read
project: self-test
publish: always
```

| Key | Values | Default |
|-----|--------|---------|
| **`kb`** | `read` \| `read-write` | Missing file, missing key, empty, or any other value → **`read`**. Legacy `write` → **`read-write`**. There is no write-only mode. |
| **`project`** | Folder name under `projects/` | Empty or missing → no project |
| **`publish`** | `never` \| `ask` \| `always` | Missing, empty, or invalid → **ask the user once** (explain the three), write the choice, then continue. After finishing `working/` edits: **never** = do not `/publish` and do not ask; **ask** = ask; **always** = `/publish` immediately (checker already green). Explicit `/publish` from the user always runs. Not the same as company **Publish after dry-run**. |

`project` is the **directory** `projects/<name>/`, not the Integray `companySlug` in `.integray-connection.json`. Two folders can wrap the same slug on different instances. If `project:` is set, that folder must already exist (clone or `/new-project`).

| `kb` | Project work | Public KB |
|------|----------------|-----------|
| **`read`** (default) | Edit `projects/<name>/` when `project:` is set | **Read** only as a side effect. If you hit a KB gap, one sentence at the end — do not fix it. |
| **`read-write`** | Same | Same as `read`, plus write repeatable platform facts into `docs/` / `recipes/` / `data/`. Not company-specific data, not `internal/` paths, not a chat dump. |

Direct KB requests (“fix this recipe”, “what does the KB say”) are **not** gated.

If the user names a different `projects/` folder than `project:`, use that folder for the request. Do not change the stored value unless they ask to switch.

Announce once at the start of project work (`KB: read` or `KB: read-write`, plus `projekt: <name>` or `bez projektu`, plus `publish: never|ask|always`, plus `Oprávnění: read-only` / `read-write` / `full` from that project’s `.integray-connection.json` when the file exists). If `projects/<name>/conventions.md` exists, **read it** before editing transfers.

Compatibility: if the file still has only `mode: project` / `mode: project-kb` and no `kb:` key, treat `project-kb` as `kb: read-write` and `project` as `kb: read`. Legacy `kb: write` → `kb: read-write`.

## Two tracks

### A — Company Config Transfer

When the user asks to create, edit, upload, or deploy Integray tasks / endpoints / transfers:

1. Read this playbook. Open [docs/transfer/config-transfer-format.md](docs/transfer/config-transfer-format.md) **only the section you need** (table at the top of that file). Do not load the whole file for a small edit.
2. Read [docs/best-practices.md](docs/best-practices.md) (CopyIDs) and [docs/entities/variables.md](docs/entities/variables.md) if secrets or `${#Code}` are involved
3. Look up connectors in [data/connectors.json](data/connectors.json) → configuration in [data/configuration-schemas.json](data/configuration-schemas.json) → columns in [data/data-schemas.json](data/data-schemas.json). Hidden fields: [docs/entities/configuration-overrides.md](docs/entities/configuration-overrides.md)
4. Multi-step / branched tasks: [docs/entities/data-addressing.md](docs/entities/data-addressing.md). Filters: [docs/entities/input-data-filter.md](docs/entities/input-data-filter.md). Local vars: [docs/entities/local-variables.md](docs/entities/local-variables.md). Checkpoint: [docs/entities/data-checkpoint.md](docs/entities/data-checkpoint.md). Step agent vs connector: [docs/entities/connector-restrictions.md](docs/entities/connector-restrictions.md)
5. Shape: [examples/generic_worked_example.json](examples/generic_worked_example.json). Live company files under `projects/<name>/working/` if present (split entity JSON — [working-split.md](docs/transfer/working-split.md))
6. **Full Sync:** the file you upload must contain everything the company should keep. Do not emit “only the new tasks” unless `conventions.md` says `greenfield: true`
7. **CopyID:** editing a transfer that was already imported → keep existing CopyIDs ([recipes/edit-existing-transfer.md](recipes/edit-existing-transfer.md))
8. **Sibling `Name`s:** Endpoint and Step names need not be globally unique — they must not collide as **siblings** in the data tree Process will assemble (Columns are given; system Columns cannot be renamed). Nested same `Name` is fine. Exception: the collision is the test. If Process merge fails, check this first ([config-transfer-format.md](docs/transfer/config-transfer-format.md) §2)
9. Deploy only when the user asks — [docs/transfer/remote-api.md](docs/transfer/remote-api.md)

There is **no** YAML spec. On disk, `working/` is **split** entity JSON. Upload is still one complete Config Transfer JSON (assembled).

Instance product line / git branch: [docs/instance-version.md](docs/instance-version.md). Fetch with `python scripts/get-instance-version.py --connection projects/<name>/.integray-connection.json` (or `--base-url`). Some features exist only from a given `productLine`.

### B — Connector development

Read [docs/connector-dev/rules.md](docs/connector-dev/rules.md). Validate metadata against [data/connector-dev.schema.json](data/connector-dev.schema.json). README template: [docs/connector-dev/readme-template.md](docs/connector-dev/readme-template.md). Work in the connector’s own repo, not in this KB’s `docs/`.

## Development loop (company config)

`snapshots/` is **immutable**. Edit only `working/`. History is git (no Xeelo-style `changes/` loops).

```text
baseUrl + companySlug + token + permission
  → /download-config → if working/ already split: ask, then --replace-working
                   → snapshots/<stamp>/     (do not edit)
                   → split into working/      (immediately, same command)
                   → print statistics         (Name, counts, sensitive names)
  → edit working/ entity files (complete transfer when assembled, preserve CopyIDs)
  → deploy working/ when the user asks (needs read-write, then full for --publish):
       /backup  (always; do not ask; do not Process this id)
       assemble working/ → temp JSON → Upload → delete temp
       Process onlyTest=true
       Process publish=true  (ask / auto; **full** only)
  → /download-config again (snapshot + split + statistics)
```

Download, backup, upload, and process have Python scripts. **Deploy:** `python scripts/deploy-config-transfer.py --connection projects/<name>/.integray-connection.json` (schema check, Upload, onlyTest, `--publish` per conventions). `/publish` is that loop; prefer the one script. Details: [remote-api.md](docs/transfer/remote-api.md).

**Statement-only** (one `Configuration.Statement`): `python scripts/config-statement.py --file projects/<name>/working list|get|put`. Do not load the transfer JSON into context. Skill: [edit-statement](.agents/skills/edit-statement/SKILL.md).

**What those scripts do not do.** Process still takes minutes on the instance. They do not replace AGENT.md for new tasks. `deploy-config-transfer.py` will not `/download-config` into `working/` (that would overwrite the edit). Company git is nested under a gitignored `projects/`; if `git status` in `projects/<name>/` shows the KB remote, use `python scripts/project-git.py projects/<name> …` (`GIT_DIR` from the parent repo).

Download: `python scripts/download-config-transfer.py --connection projects/<name>/.integray-connection.json` (snapshot **then** split **then** stats). Split only: `python scripts/split-config-transfer.py --file snapshots/…json --out projects/<name>/working`. Assemble to a kept file: `python scripts/assemble-config-transfer.py --dir projects/<name>/working --out /tmp/transfer.json` (`/assemble`). Backup: `python scripts/backup-config-transfer.py --connection projects/<name>/.integray-connection.json`. Upload/Process: prefer `deploy-config-transfer.py` (assembles split `working/` to a temp file). Layout: [docs/transfer/working-split.md](docs/transfer/working-split.md).

**Download ≠ Backup.** `/download-config` writes JSON locally. `/backup` stores a record on the instance and returns `transferId` only. Process the id from **Upload**, not from Backup. **Always** Backup before Process (`/publish` / `deploy-config-transfer.py`). Do not ask. Do not skip.

`onlyTest` and `publish` **cannot** be combined (HTTP 400).

### Agent loop in conventions

Keys in `projects/<name>/conventions.md` (`ask` | `auto`; missing = `ask`):

- **Publish after dry-run**
- **Download after publish**

These apply **inside** `/publish` (after `onlyTest`, after a successful Process). Whether the agent **starts** `/publish` after finishing `working/` edits is work-mode **`publish:`** (`never` | `ask` | `always`) in `internal/work-mode.md`, not this file.

**Backup before process** is not a convention. It always runs. Do not ask.

| Value | Behaviour |
|-------|-----------|
| **`auto`** | Do it. Announce that this company’s conventions say so. |
| **`ask`** | Offer three options (do it / do it and remember / skip). Do not run unless they pick a run option. |

**Remember** → set that key to `auto` in this company’s `conventions.md`. Failed `onlyTest` or missing connection: do not offer publish. **Download after publish** runs `/download-config` (snapshot, immediate split, then statistics).

### Project permission

`permission` in `projects/<name>/.integray-connection.json` is an **agent + script gate** (not the Remote control token, not work-mode `kb` / `project`). Missing or empty → **`read-only`**. Invalid value → stop (allowed: `read-only` | `read-write` | `full`). Do not rewrite existing connection files to add the key. Do not change `permission` unless the user asks.

Higher level = everything from the previous plus the extra column.

| Level | May | Extra vs previous |
|-------|-----|-------------------|
| **`read-only`** | `/download-config`; `/backup`; read `snapshots/` / `working/` | (base — do not Upload or Process) |
| **`read-write`** | everything from `read-only` | edit `working/`; Upload; Process `--only-test` |
| **`full`** | everything from `read-write` | Process `--publish` (and `--apply`) |

`/backup` does not apply the transfer; it only stores a server-side undo record. It is allowed at every level. Do not Process a Backup `transferId`.

`permission` beats **Publish after dry-run: auto** for **`read-only`** (do not upload) and for **`read-write`** (Upload + `onlyTest` yes; skip `--publish` and announce that it needs `full`). At `full`, conventions `ask` / `auto` work as before.

Local file edits in `projects/<name>/` are not this gate — `kb: read` still allows them. This key is about the **live company** via Remote API.

## Creating a new project

When the user asks for a **new empty company** (`projects/<name>/`):

0. **`projects/`** — [docs/projects.md](docs/projects.md). Create `projects/` as a directory if needed. Do **not** `git init` in `projects/`. If `projects/<name>/` already exists, stop.
1. Create `snapshots/` and `working/` (`.gitkeep` if needed). Copy [`templates/projects-repo/.gitignore`](templates/projects-repo/.gitignore) and `README.md` into `projects/<name>/`.
2. Copy [`templates/project/conventions.md`](templates/project/conventions.md) to `projects/<name>/conventions.md`.
3. Write **only** `projects/<name>/.integray-connection.json` — empty placeholders and `"permission": "read-only"`. **Never** copy `token` from other companies. **Do not** infer `companySlug` from `baseUrl`. Ask once whether to set `permission` to `read-write` or `full`.
4. `git init` **inside** `projects/<name>/`. The user hosts a private remote (you do not create it). After creation, tell the user what to fill in.

```json
{
  "baseUrl": "https://<instance>.integray.app",
  "companySlug": "",
  "token": "",
  "permission": "read-only"
}
```

| Field | Where to get it |
|-------|-----------------|
| `baseUrl` | Integray instance URL (not implied by slug) |
| `companySlug` | Company slug in DX / `${#SYSTEM_CompanySlug}` |
| `token` | **Remote control token** — Company Detail → **Remote control** → **Allow control** / **Token**. Not a login JWT. See [remote-api.md](docs/transfer/remote-api.md). |
| `permission` | `read-only` (default) / `read-write` (edit + Upload + `onlyTest`) / `full` (also Process `--publish`). Missing = `read-only`. Ask once whether to set `read-write` or `full`. Do not change it later unless the user asks. |

File is gitignored in the **company** git (template ignore). Commit in `projects/<name>/`, not in integray-skills. Download requires **Allow sharing remote config transfer** on the company. Do not download until connection fields are filled. Next: `/download-config`.

## Skills

Canonical location: [`.agents/skills/`](.agents/skills/). Claude CLI: [CLAUDE.md](CLAUDE.md) points at the same files (copied under `.claude/skills/`).

| Skill | When | File |
|-------|------|------|
| `/new-project` | New empty company under `projects/<name>/` | [`.agents/skills/new-project/SKILL.md`](.agents/skills/new-project/SKILL.md) |
| `/download-config` | Download snapshot, **split immediately**, print statistics | [`.agents/skills/download-config/SKILL.md`](.agents/skills/download-config/SKILL.md) |
| `/assemble` | Assemble split `working/` to a JSON file and leave it | [`.agents/skills/assemble/SKILL.md`](.agents/skills/assemble/SKILL.md) |
| `/backup` | Store a transfer record on the instance (`transferId` only) | [`.agents/skills/backup/SKILL.md`](.agents/skills/backup/SKILL.md) |
| `/publish` | Deploy `working/` (prefer `scripts/deploy-config-transfer.py`) | [`.agents/skills/publish/SKILL.md`](.agents/skills/publish/SKILL.md) |
| Statement HTML | One Configuration.Statement without opening the transfer | [`.agents/skills/edit-statement/SKILL.md`](.agents/skills/edit-statement/SKILL.md) |
| `/sync-main` | Hourly check/pull of **integray-skills `main`** | [`.agents/skills/sync-main/SKILL.md`](.agents/skills/sync-main/SKILL.md) |

## Project layout

`projects/<name>/` = one Integray company.

```text
projects/<name>/
  conventions.md
  .integray-connection.json     # gitignored
  secrets.json                  # gitignored
  snapshots/<stamp>/*.json      # download only — do not edit
  working/                      # split entity JSON; edit here; /publish assembles
```

## Short rules (Config Transfer)

- Ask for the transfer `Name` before generating.
- `Task.Type`: `0` Scheduled (Quartz 7-field cron), `1` OnDemand (default), `2` Endpoint. `Cron` is `null` unless `Type: 0`.
- `ID`: do not change existing entities. New entity: `python scripts/next-transfer-id.py projects/<name>/working --copy-id` (numeric ID unique across the transfer, then a new CopyID). Checker requires uniqueness only within each kind. `TaskGroups`/`EndpointGroups` need a real non-zero `ID`.
- Exactly one `PrevStepCopyID: null` per task.
- `SelectedActionCode` must exist in `data/connectors.json`.
- No `.` in any entity `Name`. Respect varchar length limits in config-transfer-format §2.1.
- System schemas: reference `{"Guid","Version"}` **and** list that schema once in this transfer’s `DataSchemas[]`. Custom: `{"CopyID"}`. Connector `Guid`+`Version` looks up the instance catalog; schema Guid does not — ICR / `data/data-schemas.json` is not a substitute.
- After every create/edit of `projects/<name>/working/`, run `python scripts/check-transfer-schemas.py projects/<name>/working`. Empty **stdout** and exit 0 required; do not deliver until stdout is clean. Stderr catalog lines: mention to the user, do not block ([config-transfer-format.md](docs/transfer/config-transfer-format.md) §7 / §11).
- `InputSchemaMapping` must cover every `AllowNull: false` column; mapped columns must share `Type`. Nested same Name stays on the primary path ([data-addressing.md](docs/entities/data-addressing.md)). After an `InputSchema` CopyID swap, remap chips or change a path. After an Endpoint/Step `Name` change, rewrite mapping path values too ([config-transfer-format.md](docs/transfer/config-transfer-format.md) §7).
- After Process with `publish: true`, inspect `publishResult.messages[]`.
- Never store the Remote control token in transfer JSON or commit it.
- Connection `permission` (`read-only` / `read-write` / `full`) gates Remote API writes. Missing = `read-only`.

## Checklist before delivery

- [ ] `working/` was **split** from the latest `snapshots/<stamp>/` by `/download-config` (do not edit snapshots; do not copy the snapshot as one JSON)
- [ ] Output transfer is **complete** (Full Sync) unless greenfield
- [ ] Existing CopyIDs preserved
- [ ] Connector Guid+Version from `data/connectors.json` (flag if catalog may be stale)
- [ ] Ran `python scripts/check-transfer-schemas.py projects/<name>/working` — empty **stdout**, exit 0 (DataSchemas[], all `*CopyID` refs, Configuration JSON; [config-transfer-format.md](docs/transfer/config-transfer-format.md) §7 / §11). Stderr catalog lines mentioned to the user.
- [ ] `onlyTest` succeeded before offering publish
- [ ] Connection `permission` is `full` before Process `--publish`
- [ ] Sensitive variables empty in portable JSON; user sets values via Variable API after import
