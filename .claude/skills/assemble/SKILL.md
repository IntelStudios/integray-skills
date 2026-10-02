---
name: assemble
description: >-
  Assemble projects/<name>/working/ split entity JSON into one Config Transfer
  file and leave it on disk. Use when the user invokes /assemble or asks to
  build/compose the transfer JSON without uploading.
disable-model-invocation: true
---

# Assemble Config Transfer JSON

Rebuild **one** complete Config Transfer JSON from the split tree in `projects/<name>/working/`. Layout: [docs/transfer/working-split.md](../../../docs/transfer/working-split.md).

This skill **leaves `--out` on disk**. It does **not** Upload or Process. For deploy, use `/publish` (that assembles to a temp file and deletes it).

## Prerequisites

- `projects/<name>/working/` is a split tree (`_transfer.json` + `_meta.json`). If the folder is still a single JSON, tell the user to run `/download-config` (or `split-config-transfer.py`) first.

## Run

```bash
$PYTHON scripts/assemble-config-transfer.py \
  --dir projects/<name>/working \
  --out <path>.json
```

Pick `--out` **outside** `working/` (temp or another folder). Do not write `working/*.json` next to the split tree.

Report `Wrote` path and byte size from stdout.

Full Sync: the assembled file must contain everything the company should keep. Do not assemble a subset of folders by hand.
