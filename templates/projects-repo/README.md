# Integray company working copy

This repository is **one** Integray company. It belongs at:

```text
<integray-skills>/projects/<name>/
```

Each company under `projects/` is its **own** git. `projects/` itself is not a repo. Not a branch of the public KB.

Full workflow lives in the parent integray-skills clone: `docs/projects.md`. Typical tree:

```text
conventions.md              # company rules; agent reads before transfer work
.integray-connection.json   # gitignored — baseUrl + companySlug + token
secrets.json                # gitignored
snapshots/                  # downloaded Config Transfer JSON
changes/<loop-slug>/        # change loops + output transfer
```

Do not add this tree to the public integray-skills repository. Pull KB updates in the integray-skills root; pull this company here.
