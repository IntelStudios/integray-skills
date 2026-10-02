---
name: edit-statement
description: >-
  Edit a JS Mapper or Node.js Configuration.Statement without opening the full
  Config Transfer JSON. Use when changing one Statement body (HTML page, mapper
  script) or when the user says extract / put Statement.
---

# Edit Configuration.Statement

Do **not** read [AGENT.md](../../../AGENT.md). Do **not** load `projects/<name>/working/*.json` into context.

From repo root (`.venv/bin/python` when `.venv/` exists):

```bash
$PYTHON scripts/config-statement.py --file projects/<name>/working/<file>.json list
$PYTHON scripts/config-statement.py --file … get --copy-id <CopyID> --out /tmp/statement.txt
# edit /tmp/statement.txt
$PYTHON scripts/config-statement.py --file … put --copy-id <CopyID> --input /tmp/statement.txt
```

`--name` on get/put is Configuration.Name or Step.Name when unique. `--stamp` only if that Statement already contains `generated YYYY-MM-DD HH:MM:SS`.

If the user asked to publish:

```bash
$PYTHON scripts/deploy-config-transfer.py \
  --connection projects/<name>/.integray-connection.json \
  --file projects/<name>/working/<file>.json
```

Do not also run Upload/Process separately. Do not `/download-config` after (would overwrite `working/`). Company git: `scripts/project-git.py projects/<name> status`.

What this does **not** do: Process still waits minutes on the instance. New tasks/endpoints still need AGENT.md and the full transfer.
