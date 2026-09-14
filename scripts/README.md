# Scripts

From repo root (`.venv/bin/python` when `.venv/` exists):

```bash
python scripts/download-config-transfer.py \
  --connection projects/<name>/.integray-connection.json

python scripts/backup-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

Download writes JSON under `snapshots/`. Backup stores a record on the instance and prints `transferId`. Process the id from Upload, not from Backup.

Still planned: `upload-config-transfer.py`, `process-config-transfer.py` (`--only-test` / `--publish`), `validate-transfer.py`.
