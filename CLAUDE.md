# Integray Knowledge Base

**KB** = this repository **except** `projects/` and `internal/`. When the user asks what the KB contains or what it says, answer only from `docs/`, `recipes/`, `data/`, `AGENT.md`, skills — not from `projects/` or `internal/`. You may draw from `projects/` when implementing; they are company working copies, not KB.

**Check `projects/` first** before creating a company folder or downloading a transfer. If it has no company folder and no nested `projects/.git`, explain the nested-repo intent and **offer** to initialize it — do not silently scaffold `projects/<name>/`. See [docs/projects.md](docs/projects.md).

When the user asks to create or modify Integray transfers, tasks, endpoints, or connectors:

1. Read [AGENT.md](AGENT.md) first
2. Config Transfer is **Full Sync** — do not generate a partial file that would delete company entities
3. Preserve **CopyID**s when editing a transfer that was already imported
4. Connection: `projects/<name>/.integray-connection.json` (`baseUrl`, `companySlug`, Bearer `token`) — never copy tokens between companies; never infer slug from hostname
5. There is no YAML spec. Working format is Config Transfer JSON
6. Connector work: [docs/connector-dev/rules.md](docs/connector-dev/rules.md)

**Skills** live in [`.agents/skills/`](.agents/skills/). When the user invokes `/new-project` or `/sync-main`, **read** the matching `SKILL.md` first:

- [`.agents/skills/new-project/SKILL.md`](.agents/skills/new-project/SKILL.md)
- [`.agents/skills/sync-main/SKILL.md`](.agents/skills/sync-main/SKILL.md)

Claude Code CLI does not scan `.agents/skills/`; this file points it at those paths. Copies also exist under `.claude/skills/`.
