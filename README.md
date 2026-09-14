# integray-skills

Agent-oriented knowledge base for Integray: **Config Transfer JSON** and **.NET connector development**.

## Quick start

1. Read **[AGENT.md](AGENT.md)** — playbook
2. If `projects/` is empty or missing, set up the nested private repo — **[docs/projects.md](docs/projects.md)**
3. Per company (`projects/<name>/` = one Integray company on one instance):
   - Write `projects/<name>/.integray-connection.json` with `baseUrl`, `companySlug`, and the company's **Remote control token**
   - **`/download-config`** — `GET {baseUrl}/api/Remote/{companySlug}/ConfigTransfer/Download` into `snapshots/`
   - Edit a **complete** transfer (Full Sync — missing entities are proposed for deletion)
   - Dry-run Process with `onlyTest: true`, then Process with `publish: true`

## Read vs generate

| | Config Transfer |
|---|---|
| **integray-skills reads** | Download via Remote API → snapshot under `projects/<name>/snapshots/` |
| **integray-skills generates** | Full Config Transfer JSON (not a delta) |
| **Deploy** | Remote API Upload → Process (`onlyTest` then `publish`) |

## Structure

**KB** is everything in this repo **except** `projects/` and `internal/`. Company folders under `projects/` are working copies (gitignored; one private git repo). They are not KB content. See [docs/projects.md](docs/projects.md).

| Path | Purpose |
|------|---------|
| [AGENT.md](AGENT.md) | Agent playbook |
| [STATUS.md](STATUS.md) | Current milestone and what is not done yet |
| [docs/projects.md](docs/projects.md) | Nested private git for `projects/` |
| [docs/transfer/config-transfer-format.md](docs/transfer/config-transfer-format.md) | Transfer JSON rules (IDs, Full Sync, checklist) |
| [docs/transfer/remote-api.md](docs/transfer/remote-api.md) | Download / Upload / Process / Backup |
| [docs/entities/](docs/entities/) | Tasks, mapping, variables, endpoints, … |
| [docs/connector-dev/](docs/connector-dev/) | Connector project rules |
| [docs/best-practices.md](docs/best-practices.md) | CopyIDs, names, `VariablesDefaults` |
| [data/](data/) | Connector, configuration, and data-schema catalogs |
| [scripts/download-config-transfer.py](scripts/download-config-transfer.py) | Remote API Config Transfer download |
| `projects/` | One folder per Integray company (not KB; gitignored) |

## Two tracks

- **Company config** — generate or edit Config Transfer JSON, deploy via Remote API
- **Connector development** — .NET connector projects; see [docs/connector-dev/rules.md](docs/connector-dev/rules.md)

There is **no** YAML spec language in this version. Working copy is Config Transfer JSON (full file). Do not split entities into YAML.
