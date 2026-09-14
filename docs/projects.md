# Local projects (nested git)

**KB** = this repository except `projects/`. **One private git repo = the whole `projects/` directory.** Each Integray **company** is `projects/<name>/` (not its own git repo, not a branch of integray-skills).

Company working copies (snapshots, transfers, Remote API connection, secrets) must not appear in the public integray-skills repository. The public clone gitignores `/projects/` entirely — there is no `projects/README.md` in the KB, so `git clone <private> projects` can use an empty path.

Do **not** use git submodules. Do **not** `git add -f projects/` in integray-skills. Forks of the KB stay empty of companies.

Copy [templates/projects-repo/](../templates/projects-repo/) into the private repo root (`.gitignore` + `README.md`). The parent integray-skills `.gitignore` does **not** apply inside `projects/.git` — without that nested ignore, `.integray-connection.json` and snapshots would be committed.

Version `changes/` and convention files. Snapshot JSON may be gitignored in the nested repo; refresh with `/download-config`. Never commit `token` or `secrets.json`.

## Instance vs company

| Term | Meaning | Where |
|------|---------|--------|
| **instance** | Integray host (`baseUrl`) | `.integray-connection.json` |
| **company** | Tenant inside that instance (`companySlug`) | same file; URL path `/api/Remote/{CompanySlug}/` |

One folder = one company. Two companies on the same instance = two folders (do not copy `token` between them).

## Setup A — empty `projects/` (fresh KB clone)

`projects/` is missing or empty. Either clone an existing private companies repo, or initialize one:

```bash
git clone <private-url> projects
```

If the private repo has no template files yet:

```bash
cp templates/projects-repo/.gitignore templates/projects-repo/README.md projects/
```

## Setup B — `projects/` already has companies

This machine already has `company-a/`, `company-b/`, … under `projects/` with no nested git:

```bash
cd projects
cp ../templates/projects-repo/.gitignore ../templates/projects-repo/README.md .
git init
git add .
git commit -m "Initial projects repo"
```

Then host a **private** remote and:

```bash
cd projects
git remote add origin git@<host>:<org>/<integray-projects>.git
git push -u origin main
```

## Agent check

Before creating a company folder, downloading a transfer, or otherwise using `projects/`:

1. Look at `projects/`. It is ready if it contains at least one company folder (`projects/<name>/`) **or** a nested `projects/.git`.
2. **If ready** — continue. A new company belongs in the same private repo.
3. **If not** (`projects/` missing, empty, or neither git nor a company):
   - Explain the intent (public KB, one private git for all companies, nested `.gitignore` for connection files and secrets).
   - **Offer** to initialize the nested repo. Do not run it until the user says yes. Do not silently create only `projects/<name>/`.
   - After init, tell the user to host a **private** remote themselves (the agent does not create the remote) and connect it.

## Initialize a nested repo

After the user agrees:

```bash
mkdir -p projects
cp templates/projects-repo/.gitignore templates/projects-repo/README.md projects/
cd projects
git init
```

Then the user hosts an empty **private** repository and:

```bash
cd projects
git remote add origin git@<host>:<org>/<integray-projects>.git
git add .
git commit -m "Initial projects repo"
git push -u origin main
```

`/new-project` adds `projects/<name>/` into this same private repo (including `conventions.md` from [`templates/project/conventions.md`](../templates/project/conventions.md)). Commit there, not in integray-skills.

## Company conventions

`projects/<name>/conventions.md` holds **company-specific** rules. The agent reads it at the start of company work. Template defaults: **Agent loop** `ask` for publish after dry-run, download after publish, and backup before process. Edit per company; do not put these rules into the public KB.

**Agent loop** keys (`ask` | `auto`; missing = `ask`): **Backup before process**, **Publish after dry-run**, **Download after publish**. After a successful `onlyTest` the agent offers Process with `publish: true` including “remember for this company”. Remember writes `auto` into that file. See [AGENT.md](../AGENT.md).

## Self-test

The Integray self-test company is a normal project folder (`projects/self-test/`), not a branch of this KB. Until that private repo exists, the live overlay is still `SmarterMDM-IntegrayTest` branch `self-test` (`specific/`). Do not merge that overlay into integray-skills.
