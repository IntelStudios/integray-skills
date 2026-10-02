# Scripts

From repo root (`.venv/bin/python` when `.venv/` exists):

```bash
python scripts/get-instance-version.py \
  --connection projects/<name>/.integray-connection.json

python scripts/download-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
# if working/ already has a split, ask first, then add --replace-working

python scripts/split-config-transfer.py \
  --file projects/<name>/snapshots/<stamp>/<file>.json \
  --out projects/<name>/working
# same: --replace-working after the user confirms

python scripts/assemble-config-transfer.py \
  --dir projects/<name>/working \
  --out /tmp/transfer.json

python scripts/backup-config-transfer.py \
  --connection projects/<name>/.integray-connection.json

python scripts/upload-config-transfer.py \
  --connection projects/<name>/.integray-connection.json

python scripts/process-config-transfer.py \
  --connection projects/<name>/.integray-connection.json \
  --transfer-id <upload-id> \
  --only-test

python scripts/process-config-transfer.py \
  --connection projects/<name>/.integray-connection.json \
  --transfer-id <upload-id> \
  --publish

python scripts/next-transfer-id.py \
  projects/<name>/working

python scripts/next-transfer-id.py \
  projects/<name>/working --count 3 --copy-id

python scripts/check-transfer-schemas.py \
  projects/<name>/working

python scripts/config-statement.py \
  --file projects/<name>/working list

python scripts/config-statement.py \
  --file projects/<name>/working \
  get --copy-id <Configuration CopyID> --out /tmp/statement.txt

python scripts/config-statement.py \
  --file projects/<name>/working \
  put --copy-id <Configuration CopyID> --input /tmp/statement.txt

python scripts/deploy-config-transfer.py \
  --connection projects/<name>/.integray-connection.json

python scripts/project-git.py projects/<name> status

python scripts/sync-claude-skills.py
python scripts/sync-claude-skills.py --check
```

Download writes JSON under `snapshots/` (do not edit), **immediately splits** into `working/` entity files, then prints `Name`, collection counts, and sensitive variable names. If `working/` already has a split, the script exits 2 until `--replace-working` (agent asks first). Do not copy the snapshot as a single `working/*.json`. `/publish` assembles `working/` to a temp file, Uploads, deletes the temp. `/assemble` writes a JSON and leaves it. Process the Upload `transferId` (`--only-test`, then `--publish`). Do not Process a Backup id. `--apply` is Process with `publish: false` (rare). Layout: [docs/transfer/working-split.md](../docs/transfer/working-split.md).

`deploy-config-transfer.py` is schema check + Backup + Upload + onlyTest + `--publish` when conventions say auto and `permission` is `full`. It does **not** download into `working/`. `--stamp-copy-id` is optional (`generated YYYY-MM-DD HH:MM:SS` in that Statement). Backup always runs (returns an int `backupTransferId`; do not Process it). Standalone `upload-config-transfer.py` is pre-check only — it does not Backup.

`config-statement.py` gets/puts `Configuration.Statement` so the agent does not open the whole transfer. `put --stamp` refreshes `generated YYYY-MM-DD HH:MM:SS` when that marker is already in the Statement.

`project-git.py` runs git in `projects/<name>/` after unsetting `GIT_DIR` (the KB repo otherwise shadows the company git).

`sync-claude-skills.py` copies `.agents/skills/` → `.claude/skills/` (Claude Code does not scan `.agents`). Edit only `.agents/skills/`. `--check` exits 1 if the copy is stale.

`next-transfer-id.py` prints unused numeric `ID`s (max existing + 1, unique across the transfer). `--copy-id` prints a new UUIDv4 after each ID. Use only for **new** entities; never rewrite IDs on a downloaded export.

`check-transfer-schemas.py` is local. Pass the split `working/` directory or an assembled JSON. **Stdout** empty + exit 0 = pass (DataSchemas[] membership, `*CopyID` refs, Configuration JSON required fields, connector action/restrictions when the catalog has that version, unused Connectors/Configurations/TaskGroups/EndpointGroups). **Stderr** `catalog may be stale` does not fail the gate — tell the user. Run after every edit of `working/` before declaring the transfer done. Deploy already runs it.

Connection `permission`: download and backup at every level; Upload and `--only-test` need `read-write` or `full`; `--publish` / `--apply` need `full`. Missing `permission` defaults to `read-only`.
