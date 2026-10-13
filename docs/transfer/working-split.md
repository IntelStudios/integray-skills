# Split working copy (entity files)

On-disk format for `projects/<name>/working/` after `/download-config`. The Remote API still speaks **one** Config Transfer JSON (Full Sync). Split is how the agent edits without loading that file into chat.

Canonical loop: [AGENT.md](../../AGENT.md). Download skill: [`.agents/skills/download-config/SKILL.md`](../../.agents/skills/download-config/SKILL.md). Assemble skill: [`.agents/skills/assemble/SKILL.md`](../../.agents/skills/assemble/SKILL.md).

## Download order (do not invert)

1. Write the immutable snapshot under `snapshots/<stamp>/`.
2. **Clear** `working/` (keep `.gitkeep`) and **immediately** split that snapshot into it. Do not ask. Nothing from the previous split stays.
3. **Then** print statistics from the script stdout. Do not open the snapshot JSON in chat to count entities.

Do not copy the snapshot as a single `working/*.json`. Do not skip split. Do not edit `snapshots/`.

## Statistics to report

From script stdout (same facts as a Download that already ran):

- Snapshot path and byte size (`Wrote …`)
- Split destination and file count (`Split …`)
- Transfer `Name=`
- Collection counts: `tasks`, `endpoints`, `dataSchemas`, `configurations`, plus the other lines the script prints
- `sensitiveVariables=` — **names** of `IsSensitive: true` variables (export `Value` is empty). Not a secret dump.
- `connector-outdated:` / `connector-mixed:` — company Step versions vs newest in
  `data/connectors.json`. If that Version is not on the **instance**, the user updates
  connectors in Integray first. Only then offer to bump `working/`.
  `python scripts/check-connector-versions.py projects/<name>/working` (empty stdout = ok).

## Layout

```text
working/
  _transfer.json          # envelope (Name, TransferType, Created, …) — no collection arrays
  _meta.json              # collection key order + filenames
  tasks/<copyId>.json     # whole Task including Steps
  endpoints/<copyId>.json
  data-schemas/{guid}_{version}.json   # system (Guid+Version present)
  data-schemas/<copyId>.json           # custom
  configurations/<copyId>.json
  connectors/{guid}_{version}.json
  agents/ task-groups/ endpoint-groups/ variables/
  variable-groups/ entity-comments/ templates/ …
```

- **Task + Steps** = one file. Do not split Steps out.
- **DataSchemas[]** = one file per row. Nested / table schemas are other rows in that array; the parent keeps a `ComplexType` (or table) pointer, it does not inline the nested columns.
- Filename: `Guid`+`Version` when both are set (`{guid}_{version}.json`); otherwise `CopyID.json`. `EntityComments` use `EntityCopyID.json`.
- **`connectors/` is not the platform catalog.** `data/connectors.json` (and the other `data/*.json` dumps) is ICR. `working/connectors/` lists only Guid+Version a **Step actually uses**. Do not copy unused catalog rows into the split. Checker flags unused connectors, unused Configurations, and unused Task/Endpoint groups on stdout.
- New entity: add a file in the right folder. `python scripts/next-transfer-id.py projects/<name>/working --copy-id` prints a numeric `ID` then a new `CopyID` (UUIDv4). Do not rewrite IDs on existing files. Assemble picks up files not listed in `_meta.json` (appended). Deleting a file drops that entity from the assembled transfer (Full Sync — that is a delete on the company).

## Assemble (upload)

`scripts/assemble-config-transfer.py --dir projects/<name>/working --out <path>` writes **one** complete transfer JSON and **leaves it**. Skill `/assemble`.

`/publish` and `deploy-config-transfer.py` assemble to a **temp file**, Upload that, then **delete** the temp. Do not leave an assembled JSON in `working/` (the glob would collide with the split tree). Never Upload a snapshot. Never Upload a partial tree.

## Schema check

```bash
python scripts/check-transfer-schemas.py projects/<name>/working
```

Empty **stdout**, exit 0. Same rules as a single file ([config-transfer-format.md](config-transfer-format.md) §7 / §11).

## Statement-only

```bash
python scripts/config-statement.py --file projects/<name>/working list
```

`--file` is the split directory, not a giant JSON.
