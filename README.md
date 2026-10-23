# integray-skills

Agent-oriented knowledge base for Integray: **Config Transfer JSON** and **.NET connector development**.

## Quick start

1. Read **[AGENT.md](AGENT.md)** — playbook
2. Each company is `projects/<name>/` as **its own git** (`projects/` is not a repo) — **[docs/projects.md](docs/projects.md)**
3. Per company (`projects/<name>/` = one Integray company on one instance):
   - Write `projects/<name>/.integray-connection.json` with `baseUrl`, `companySlug`, the company's **Remote control token**, and `permission` (`read-only` | `read-write` | `full`; missing = `read-only`)
   - **`/download-config`** — JSON into `snapshots/<stamp>/`, **clear `working/`**, split immediately, then statistics (do not edit snapshots; do not ask before replace)
   - Edit the split entity files in `working/` (Full Sync when assembled)
   - **`/publish`** when asked — backup always, assemble `working/`, Upload, Process `onlyTest`, then `publish`
   - **`/debug-task-run`** — start a live Task / step snapshot when `productLine` allows it ([instance-version.md](docs/instance-version.md) Feature availability)

## Skills

Canonical files: [`.agents/skills/`](.agents/skills/). Claude CLI copies them to `.claude/skills/` (`python scripts/sync-claude-skills.py`). Same table: [AGENT.md](AGENT.md) § Skills.

| Skill | When | File |
|-------|------|------|
| `/new-project` | New empty company under `projects/<name>/` | [new-project](.agents/skills/new-project/SKILL.md) |
| `/download-config` | Download snapshot, clear `working/`, split immediately, print statistics | [download-config](.agents/skills/download-config/SKILL.md) |
| `/assemble` | Assemble split `working/` to a JSON file and leave it | [assemble](.agents/skills/assemble/SKILL.md) |
| `/backup` | Store a transfer record on the instance (`transferId` only) | [backup](.agents/skills/backup/SKILL.md) |
| `/publish` | Deploy `working/` (backup, assemble, Upload, Process) | [publish](.agents/skills/publish/SKILL.md) |
| `/debug-task-run` | Start a Task, poll the run, fetch a step snapshot (Remote API from `017`, snapshot from `018`) | [debug-task-run](.agents/skills/debug-task-run/SKILL.md) |
| `/edit-statement` | One JS Mapper / Node.js `Configuration.Statement` without opening the transfer | [edit-statement](.agents/skills/edit-statement/SKILL.md) |
| `/sync-main` | Hourly check/pull of **integray-skills `main`** | [sync-main](.agents/skills/sync-main/SKILL.md) |

## Read vs generate

| | Config Transfer |
|---|---|
| **integray-skills reads** | Download via Remote API → `projects/<name>/snapshots/` |
| **integray-skills generates** | Split entity JSON in `working/` (assembled to a complete transfer on Upload, not a delta) |
| **Deploy** | Assemble `working/` → Upload → Process (`onlyTest` then `publish`) — [remote-api.md](docs/transfer/remote-api.md) |

## Structure

**KB** is everything in this repo **except** `projects/` and `internal/`. Company folders under `projects/` are working copies (gitignored; one private git **per company**). They are not KB content. See [docs/projects.md](docs/projects.md).

| Path | Purpose |
|------|---------|
| [AGENT.md](AGENT.md) | Agent playbook |
| [docs/projects.md](docs/projects.md) | One private git per `projects/<name>/` |
| [docs/transfer/config-transfer-format.md](docs/transfer/config-transfer-format.md) | Transfer JSON rules (IDs, Full Sync, checklist) |
| [docs/transfer/remote-api.md](docs/transfer/remote-api.md) | Download / Upload / Process / Backup / Task-run snapshot |
| [docs/transfer/remote-debugger.md](docs/transfer/remote-debugger.md) | `POST Debugger/Run` — one installed connector, no saved task (`rel-2025-03.018`) |
| [docs/instance-version.md](docs/instance-version.md) | `GET /api/Integray` and **Feature availability** by `productLine` |
| [docs/entities/](docs/entities/) | Tasks, mapping, variables, endpoints, … |
| [docs/connector-dev/](docs/connector-dev/) | Connector project rules |
| [docs/best-practices.md](docs/best-practices.md) | CopyIDs, names, `VariablesDefaults` |
| [data/](data/) | ICR catalogs (connectors, configuration schemas, data schemas, agent restrictions) |
| [scripts/get-instance-version.py](scripts/get-instance-version.py) | Unauthenticated `GET /api/Integray` (`productLine`, `buildStamp`) |
| [scripts/task-run.py](scripts/task-run.py) | Start task / task-run status / step snapshot (version-gated — [instance-version.md](docs/instance-version.md)) |
| [scripts/download-config-transfer.py](scripts/download-config-transfer.py) | Remote API Config Transfer download (always replaces `working/`) |
| [scripts/check-connector-versions.py](scripts/check-connector-versions.py) | Advisory: outdated / mixed connector versions vs catalog (instance first) |
| [scripts/backup-config-transfer.py](scripts/backup-config-transfer.py) | Remote API Config Transfer backup (`transferId`) |
| [scripts/upload-config-transfer.py](scripts/upload-config-transfer.py) | Remote API Config Transfer upload (pre-check + `transferId`) |
| [scripts/process-config-transfer.py](scripts/process-config-transfer.py) | Remote API Process (`--only-test` / `--publish`) |
| `projects/` | One folder per Integray company, each its own git (not KB; gitignored) |

## Two tracks

- **Company config** — generate or edit Config Transfer JSON, deploy via Remote API
- **Connector development** — .NET connector projects; see [docs/connector-dev/rules.md](docs/connector-dev/rules.md)

There is **no** YAML spec. `working/` is **split entity JSON**; Upload is one assembled Config Transfer JSON. Layout: [working-split.md](docs/transfer/working-split.md).
