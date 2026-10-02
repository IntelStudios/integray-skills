# Scripts

From repo root (`.venv/bin/python` when `.venv/` exists):

```bash
python scripts/get-instance-version.py \
  --connection projects/<name>/.integray-connection.json

python scripts/download-config-transfer.py \
  --connection projects/<name>/.integray-connection.json

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

python scripts/check-transfer-schemas.py \
  projects/<name>/working/<file>.json

python scripts/config-statement.py \
  --file projects/<name>/working/<file>.json list

python scripts/config-statement.py \
  --file projects/<name>/working/<file>.json \
  get --copy-id <Configuration CopyID> --out /tmp/statement.txt

python scripts/config-statement.py \
  --file projects/<name>/working/<file>.json \
  put --copy-id <Configuration CopyID> --input /tmp/statement.txt

python scripts/deploy-config-transfer.py \
  --connection projects/<name>/.integray-connection.json

python scripts/project-git.py projects/<name> status
```

Download writes JSON under `snapshots/` (do not edit). Copy into `working/` to edit. Upload sends `working/` (or `--file`) and prints `transferId`. Process that id (`--only-test`, then `--publish`). Do not Process a Backup id. `--apply` is Process with `publish: false` (rare).

`deploy-config-transfer.py` is schema check + Upload + onlyTest + `--publish` when conventions say auto and `permission` is `full`. It does **not** download into `working/`. `--stamp-copy-id` is optional (`generated YYYY-MM-DD HH:MM:SS` in that Statement). `--backup` when conventions Backup is `ask`.

`config-statement.py` gets/puts `Configuration.Statement` so the agent does not open the whole transfer. `put --stamp` refreshes `generated YYYY-MM-DD HH:MM:SS` when that marker is already in the Statement.

`project-git.py` runs git in `projects/<name>/` after unsetting `GIT_DIR` (the KB repo otherwise shadows the company git).

`check-transfer-schemas.py` is local. **Stdout** empty + exit 0 = pass (DataSchemas[] membership, `*CopyID` refs, Configuration JSON required fields, connector action/restrictions when the catalog has that version). **Stderr** `catalog may be stale` does not fail the gate — tell the user. Run after every edit of `working/*.json` before declaring the transfer done. Deploy already runs it.

Connection `permission`: download and backup at every level; Upload and `--only-test` need `read-write` or `full`; `--publish` / `--apply` need `full`. Missing `permission` defaults to `read-only`.
