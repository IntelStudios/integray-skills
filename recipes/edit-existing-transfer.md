# Editing an existing Config Transfer — preserve CopyIDs

Use this recipe whenever the user wants to **change** tasks, steps, endpoints, or schemas that already exist in a transfer that has been (or will be) imported into a live company.

Full notes: [docs/best-practices.md](../docs/best-practices.md). Identifiers: [docs/transfer/config-transfer-format.md](../docs/transfer/config-transfer-format.md) §2.

## Rule

`CopyID` is the import matching key (update vs insert). Replacing it with a fresh UUID turns a clean update into delete+insert on the next Full Sync, even when the entity did not conceptually change.

1. Copy the latest downloaded snapshot from `projects/<name>/snapshots/<stamp>/` into `projects/<name>/working/`. Edit **`working/`** only — never the snapshot.
2. Keep every existing entity’s `CopyID` unchanged unless the user explicitly wants a **new** entity.
3. New entities only: generate a new UUIDv4 (or a deterministic `uuid5` from a stable key if the same generator will run more than once).
4. If preserving CopyIDs is impractical and a full regeneration looks easier, **ask first** — do not silently reassign IDs.
5. Do not invent a YAML spec or explode the file into per-entity YAML. Edit the JSON in `working/`.

## Also

- Unique, meaningful `Name` on every named entity; no `.` in names.
- `VariablesDefaults` compact JSON (no spaces) so DX “Changes” does not false-diff — see best-practices.
- After changing a Step `InputSchema` CopyID, remap chips on the instance (or change a
  mapping path). Same display strings do not rewrite `{dsc:}` keys
  ([config-transfer-format.md](../docs/transfer/config-transfer-format.md) §7).
