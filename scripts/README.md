# Scripts

From repo root (`.venv/bin/python` when `.venv/` exists):

```bash
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
```

Download writes JSON under `snapshots/` (do not edit). Copy into `working/` to edit. Upload sends `working/` (or `--file`) and prints `transferId`. Process that id (`--only-test`, then `--publish`). Do not Process a Backup id. `--apply` is Process with `publish: false` (rare).

Connection `permission`: download and backup at every level; Upload and `--only-test` need `read-write` or `full`; `--publish` / `--apply` need `full`. Missing `permission` defaults to `read-only`.

Still planned: `validate-transfer.py`.
