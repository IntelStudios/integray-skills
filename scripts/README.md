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
```

Download writes JSON under `snapshots/` (do not edit). Copy into `working/` to edit. Upload sends `working/` (or `--file`) and prints `transferId`. Process that id (`--only-test`, then `--publish`). Do not Process a Backup id. `--apply` is Process with `publish: false` (rare).

`check-transfer-schemas.py` is local. **Stdout** empty + exit 0 = pass (DataSchemas[] membership, `*CopyID` refs, Configuration JSON required fields, connector action/restrictions when the catalog has that version). **Stderr** `catalog may be stale` does not fail the gate — tell the user. Run after every edit of `working/*.json` before declaring the transfer done.

Connection `permission`: download and backup at every level; Upload and `--only-test` need `read-write` or `full`; `--publish` / `--apply` need `full`. Missing `permission` defaults to `read-only`.
