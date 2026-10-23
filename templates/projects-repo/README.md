# Integray company working copy

This repository is **one** Integray company. It belongs at:

```text
<integray-skills>/projects/<name>/
```

Each company under `projects/` is its **own** git. `projects/` itself is not a repo. Not a branch of the public KB.

Full workflow lives in the parent integray-skills clone: `docs/projects.md`. Typical tree:

```text
conventions.md              # company rules; agent reads before transfer work
.integray-connection.json   # gitignored — baseUrl + companySlug + token + permission
secrets.json                # gitignored
snapshots/<stamp>/*.json    # /download-config — do not edit
working/                    # split entity JSON; edit here; /publish assembles
```

Do not add this tree to the public integray-skills repository. Pull KB updates in the integray-skills root; pull this company here.

## Debugger

Which connectors may run via `POST Debugger/Run` is **this company's** list in [`conventions.md`](conventions.md) (`## Debugger`, lines `debugger-connector: <guid> always|never`). Test and production each have their own file. No line for a guid means the agent asks once and writes the answer here. It is not a machine-wide switch. Agent rules: `docs/transfer/remote-debugger.md` in the integray-skills repo.
