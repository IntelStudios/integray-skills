# Scripts

From repo root (`.venv/bin/python` when `.venv/` exists):

```bash
python scripts/download-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

Still planned: `upload-config-transfer.py`, `process-config-transfer.py` (`--only-test` / `--publish`), `backup-config-transfer.py`, `validate-transfer.py`.
