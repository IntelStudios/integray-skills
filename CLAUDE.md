# Integray Knowledge Base

**KB** = this repository **except** `projects/` and `internal/`. When the user asks what the KB contains or what it says, answer only from `docs/`, `recipes/`, `data/`, `AGENT.md`, skills — not from `projects/` or `internal/`. You may draw from `projects/` when implementing; they are company working copies, not KB.

**Check `projects/<name>/` first** before downloading a transfer. `projects/` is a directory, not a git — each company folder is its own git. If `projects/<name>/` is missing, **offer** clone or `/new-project` — do not silently scaffold. See [docs/projects.md](docs/projects.md).

When the user asks to create or modify Integray transfers, tasks, endpoints, or connectors:

1. Read [AGENT.md](AGENT.md) first
2. Config Transfer is **Full Sync** — do not generate a partial file that would delete company entities
3. Preserve **CopyID**s when editing a transfer that was already imported
4. Connection: `projects/<name>/.integray-connection.json` (`baseUrl`, `companySlug`, Remote control `token`, `permission` `read-only` | `read-write` | `full`; missing = `read-only`) — never copy tokens between companies; never infer slug from hostname; do not change `permission` unless the user asks
5. There is no YAML spec. Working format is Config Transfer JSON
6. After creating or editing `projects/<name>/working/*.json`, run `python scripts/check-transfer-schemas.py <that-file>` before declaring the transfer done. Empty **stdout** and exit 0 required; if stdout prints anything, fix and re-run. Stderr catalog lines: tell the user, do not block. Do not skip a stdout finding because the Guid exists in ICR, `data/data-schemas.json`, or another company ([config-transfer-format.md](docs/transfer/config-transfer-format.md) §7 / §11).
7. Connector work: [docs/connector-dev/rules.md](docs/connector-dev/rules.md)
8. Instance product line: `python scripts/get-instance-version.py --connection projects/<name>/.integray-connection.json` (or `--base-url`). See [docs/instance-version.md](docs/instance-version.md)

**Skills** live in [`.agents/skills/`](.agents/skills/). When the user invokes `/new-project`, `/download-config`, `/backup`, `/publish`, or `/sync-main`, **read** the matching `SKILL.md` first:

- [`.agents/skills/new-project/SKILL.md`](.agents/skills/new-project/SKILL.md)
- [`.agents/skills/download-config/SKILL.md`](.agents/skills/download-config/SKILL.md)
- [`.agents/skills/backup/SKILL.md`](.agents/skills/backup/SKILL.md)
- [`.agents/skills/publish/SKILL.md`](.agents/skills/publish/SKILL.md)
- [`.agents/skills/sync-main/SKILL.md`](.agents/skills/sync-main/SKILL.md)

Claude Code CLI does not scan `.agents/skills/`; this file points it at those paths. Copies also exist under `.claude/skills/`.
