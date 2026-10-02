# Local projects (one git per company)

**KB** = this repository except `projects/`. `projects/` is a directory on disk, **not** a git repository. Each Integray **company** is `projects/<name>/` and **that folder is its own private git**. Not a branch of integray-skills. Not one git for all companies. Do **not** use git submodules. Do **not** `git add -f projects/` in integray-skills.

```text
integray-skills/          ← public KB
  projects/               ← gitignored; not a repo
    self-test/            ← git clone …/integray-self-test.git
    company-a/            ← its own git
```

Company working copies (snapshots, transfers, Remote API connection, secrets) must not appear in the public integray-skills repository.

Copy [templates/projects-repo/](../templates/projects-repo/) (`.gitignore` + `README.md`) into **each** `projects/<name>/`. The parent integray-skills `.gitignore` does **not** apply inside `projects/<name>/.git` — without that ignore, `.integray-connection.json` would be committed.

Version `working/`, convention files, and snapshot stamps you want to keep. **Do not edit** files under `snapshots/` — `/download-config` splits the newest stamp into `working/` immediately. Never commit `token` or `secrets.json`.

## Instance vs company

| Term | Meaning | Where |
|------|---------|--------|
| **instance** | Integray host (`baseUrl`) | `.integray-connection.json` |
| **company** | Tenant inside that instance (`companySlug`) | same file; URL path `/api/Remote/{CompanySlug}/` |
| **permission** | Agent + script gate (`read-only` / `read-write` / `full`) | same file; missing = `read-only`. Not the Integray slug. See [AGENT.md](../AGENT.md#project-permission). |

One folder = one company = one git. Two companies on the same instance = two folders and two remotes (do not copy `token` between them).

## Clone an existing company

```bash
git clone <private-url> projects/<name>
```

Example — self-test:

```bash
git clone https://github.com/IntelStudios/integray-self-test.git projects/self-test
```

If the clone has no template ignore yet:

```bash
cp templates/projects-repo/.gitignore templates/projects-repo/README.md projects/<name>/
```

## New empty company

`/new-project` (or the same steps by hand):

```bash
mkdir -p projects/<name>
cp templates/projects-repo/.gitignore templates/projects-repo/README.md projects/<name>/
cp templates/project/conventions.md projects/<name>/conventions.md
# write empty .integray-connection.json (see AGENT.md)
mkdir -p projects/<name>/snapshots projects/<name>/working
cd projects/<name>
git init
```

Then the user hosts a **private** remote (the agent does not create the GitHub/Azure repo) and:

```bash
cd projects/<name>
git remote add origin git@<host>:<org>/<company-repo>.git
git add .
git commit -m "Initial company repo"
git push -u origin main
```

## Agent check

Before creating a company folder, downloading a transfer, or otherwise using `projects/<name>/`:

1. `projects/` may be missing or empty — that is fine. Create `projects/` as a normal directory if needed. Do **not** `git init` in `projects/`.
2. For work on a named company, `projects/<name>/` must exist (clone or `/new-project`).
3. Do **not** silently scaffold `projects/<name>/`. If the folder is missing, **offer** clone (if they gave a URL) or `/new-project`.
4. Commit company files in `projects/<name>/`, never in integray-skills.

## Snapshots vs working

| Path | Role |
|------|------|
| `snapshots/<stamp>/*.json` | Output of `/download-config`. Immutable. New download = new stamp. |
| `working/` | Split entity JSON from that snapshot. Edit here. `/publish` assembles, Uploads, deletes the temp file. |

Start work: `/download-config`. If `working/` already has a split, the agent **asks** before replacing it. Two parallel edits = a git branch, not a second working folder. There is no `changes/<slug>/` loop.

After a successful Process with `publish: true`, `/download-config` again (split + statistics). Deploy is `/publish` (assemble `working/` → Upload → Process `--only-test` → `--publish` per conventions). See [working-split.md](transfer/working-split.md).

## Company conventions

`projects/<name>/conventions.md` holds **company-specific** rules. The agent reads it at the start of company work. Template defaults: **Agent loop** `ask` for publish after dry-run and download after publish. Edit per company; do not put these rules into the public KB.

Whether the agent **starts** `/publish` after finishing `working/` edits is **`publish:`** in `internal/work-mode.md` (`never` | `ask` | `always`; missing = ask the user and write the choice). That is this machine, not the company repo.

**Agent loop** keys (`ask` | `auto`; missing = `ask`): **Publish after dry-run**, **Download after publish**. Backup before Process is always (not a convention). After a successful `onlyTest` the agent offers Process with `publish: true` including “remember for this company”. Remember writes `auto` into that file. See [AGENT.md](../AGENT.md).

## Self-test

The Integray self-test company is `projects/self-test/` — its own git, remote `https://github.com/IntelStudios/integray-self-test.git`. Do not merge company files into integray-skills. Do not commit token pools.
