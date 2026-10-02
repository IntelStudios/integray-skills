# Editing an existing Config Transfer — preserve CopyIDs

Use this recipe whenever the user wants to **change** tasks, steps, endpoints, or schemas that already exist in a transfer that has been (or will be) imported into a live company.

Full notes: [docs/best-practices.md](../docs/best-practices.md). Identifiers: [docs/transfer/config-transfer-format.md](../docs/transfer/config-transfer-format.md) §2.

## Rule

`CopyID` is the import matching key (update vs insert). Replacing it with a fresh UUID turns a clean update into delete+insert on the next Full Sync, even when the entity did not conceptually change.

1. `/download-config` writes an immutable snapshot and **immediately splits** it into `projects/<name>/working/`. Edit **`working/`** only — never the snapshot. Layout: [docs/transfer/working-split.md](../docs/transfer/working-split.md).
2. Keep every existing entity’s `CopyID` **and `ID`** unchanged unless the user explicitly wants a **new** entity.
3. New entities only: `python scripts/next-transfer-id.py projects/<name>/working --copy-id` (`--count N` if you add several) — numeric `ID` then a new UUIDv4 `CopyID`. Use `uuid5` instead of that CopyID only if the same generator will run more than once. Add a new file in the matching `working/` folder.
4. If preserving CopyIDs is impractical and a full regeneration looks easier, **ask first** — do not silently reassign IDs.
5. Do not invent a YAML spec. Edit the entity JSON files (one Task including its Steps; one `DataSchemas[]` row per file). `/publish` assembles the whole tree.

## Also

- Unique, meaningful `Name` on every named entity; no `.` in names.
- `VariablesDefaults` compact JSON (no spaces) so DX “Changes” does not false-diff — see best-practices.
- After changing a Step `InputSchema` CopyID, remap chips on the instance (or change a
  mapping path). Same display strings do not rewrite `{dsc:}` keys
  ([config-transfer-format.md](../docs/transfer/config-transfer-format.md) §7).
