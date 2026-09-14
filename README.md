# integray-skills

Agent-oriented knowledge base for Integray: **Config Transfer JSON** and **.NET connector development**.

## Quick start

1. Read **[AGENT.md](AGENT.md)** — playbook
2. Each company is `projects/<name>/` as **its own git** (`projects/` is not a repo) — **[docs/projects.md](docs/projects.md)**
3. Per company (`projects/<name>/` = one Integray company on one instance):
   - Write `projects/<name>/.integray-connection.json` with `baseUrl`, `companySlug`, and the company's **Remote control token**
   - **`/download-config`** — JSON into `snapshots/<stamp>/` (do not edit)
   - Copy the newest snapshot into `working/` and edit that **complete** transfer (Full Sync)
   - **`/publish`** when asked — backup per conventions, Upload `working/`, Process `onlyTest`, then `publish`

## Read vs generate

| | Config Transfer |
|---|---|
| **integray-skills reads** | Download via Remote API → `projects/<name>/snapshots/` |
| **integray-skills generates** | Full Config Transfer JSON in `working/` (not a delta) |
| **Deploy** | Upload `working/` → Process (`onlyTest` then `publish`) — [remote-api.md](docs/transfer/remote-api.md) |

## Structure

**KB** is everything in this repo **except** `projects/` and `internal/`. Company folders under `projects/` are working copies (gitignored; one private git **per company**). They are not KB content. See [docs/projects.md](docs/projects.md).

| Path | Purpose |
|------|---------|
| [AGENT.md](AGENT.md) | Agent playbook |
| [STATUS.md](STATUS.md) | Current milestone and what is not done yet |
| [docs/projects.md](docs/projects.md) | One private git per `projects/<name>/` |
| [docs/transfer/config-transfer-format.md](docs/transfer/config-transfer-format.md) | Transfer JSON rules (IDs, Full Sync, checklist) |
| [docs/transfer/remote-api.md](docs/transfer/remote-api.md) | Download / Upload / Process / Backup |
| [docs/entities/](docs/entities/) | Tasks, mapping, variables, endpoints, … |
| [docs/connector-dev/](docs/connector-dev/) | Connector project rules |
| [docs/best-practices.md](docs/best-practices.md) | CopyIDs, names, `VariablesDefaults` |
| [data/](data/) | Connector, configuration, and data-schema catalogs |
| [scripts/download-config-transfer.py](scripts/download-config-transfer.py) | Remote API Config Transfer download |
| [scripts/backup-config-transfer.py](scripts/backup-config-transfer.py) | Remote API Config Transfer backup (`transferId`) |
| [scripts/upload-config-transfer.py](scripts/upload-config-transfer.py) | Remote API Config Transfer upload (pre-check + `transferId`) |
| [scripts/process-config-transfer.py](scripts/process-config-transfer.py) | Remote API Process (`--only-test` / `--publish`) |
| `projects/` | One folder per Integray company, each its own git (not KB; gitignored) |

## Two tracks

- **Company config** — generate or edit Config Transfer JSON, deploy via Remote API
- **Connector development** — .NET connector projects; see [docs/connector-dev/rules.md](docs/connector-dev/rules.md)

There is **no** YAML spec language in this version. Working copy is Config Transfer JSON (full file). Do not split entities into YAML.
