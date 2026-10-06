# integray-skills

Agent-oriented knowledge base for Integray: **Config Transfer JSON** and **.NET connector development**.

## Quick start

1. Read **[AGENT.md](AGENT.md)** — playbook
2. Each company is `projects/<name>/` as **its own git** (`projects/` is not a repo) — **[docs/projects.md](docs/projects.md)**
3. Per company (`projects/<name>/` = one Integray company on one instance):
   - Write `projects/<name>/.integray-connection.json` with `baseUrl`, `companySlug`, the company's **Remote control token**, and `permission` (`read-only` | `read-write` | `full`; missing = `read-only`)
   - **`/download-config`** — JSON into `snapshots/<stamp>/`, **split into `working/` immediately**, then statistics (do not edit snapshots)
   - Edit the split entity files in `working/` (Full Sync when assembled)
   - **`/publish`** when asked — backup per conventions, assemble `working/`, Upload, Process `onlyTest`, then `publish`

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
| [docs/transfer/remote-api.md](docs/transfer/remote-api.md) | Download / Upload / Process / Backup |
| [docs/instance-version.md](docs/instance-version.md) | Unauthenticated `GET /api/Integray` — product line and build stamp |
| [docs/entities/](docs/entities/) | Tasks, mapping, variables, endpoints, … |
| [docs/connector-dev/](docs/connector-dev/) | Connector project rules |
| [docs/best-practices.md](docs/best-practices.md) | CopyIDs, names, `VariablesDefaults` |
| [data/](data/) | Connector, configuration, and data-schema catalogs |
| [scripts/get-instance-version.py](scripts/get-instance-version.py) | Unauthenticated `GET /api/Integray` (`productLine`, `buildStamp`) |
| [scripts/task-run.py](scripts/task-run.py) | Start task / task-run status / step snapshot (version-gated — [instance-version.md](docs/instance-version.md)) |
| [scripts/download-config-transfer.py](scripts/download-config-transfer.py) | Remote API Config Transfer download |
| [scripts/backup-config-transfer.py](scripts/backup-config-transfer.py) | Remote API Config Transfer backup (`transferId`) |
| [scripts/upload-config-transfer.py](scripts/upload-config-transfer.py) | Remote API Config Transfer upload (pre-check + `transferId`) |
| [scripts/process-config-transfer.py](scripts/process-config-transfer.py) | Remote API Process (`--only-test` / `--publish`) |
| `projects/` | One folder per Integray company, each its own git (not KB; gitignored) |

## Two tracks

- **Company config** — generate or edit Config Transfer JSON, deploy via Remote API
- **Connector development** — .NET connector projects; see [docs/connector-dev/rules.md](docs/connector-dev/rules.md)

There is **no** YAML spec language in this version. Working copy is Config Transfer JSON (full file). Do not split entities into YAML.
