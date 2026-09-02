# Integray company working copies

This repository is the **private** git root for all Integray companies used with an integray-skills clone. It belongs at:

```text
<integray-skills>/projects/
```

Each company is a folder: `self-test/`, `site-a/`, … — not a separate git repo, not a branch of the public KB.

Full workflow lives in the parent integray-skills clone: `docs/projects.md`. Typical tree per company:

```text
<name>/
  conventions.md              # company rules; agent reads before transfer work
  .integray-connection.json   # gitignored — baseUrl + companySlug + token
  secrets.json                # gitignored
  snapshots/                  # downloaded Config Transfer JSON
  changes/<loop-slug>/        # change loops + output transfer
```

Do not add this tree to the public integray-skills repository. Pull KB updates in the integray-skills root; pull company updates here.
