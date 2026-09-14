---
name: new-project
description: >-
  Scaffold a new empty Integray company project under projects/<name>/ with
  snapshots, working folders and .integray-connection.json template.
  Use when the user asks to create a new Integray project, company, or workspace
  folder, or invokes /new-project.
disable-model-invocation: true
---

# New Integray company

Scaffold `projects/<name>/` for one Integray company. That folder is **its own git**. `projects/` is a directory, not a repo. Read [AGENT.md](../../../AGENT.md). Canonical: [docs/projects.md](../../../docs/projects.md).

## Inputs

Determine from the user message or ask once:

- **`<name>`** — project slug under `projects/`. Must be a valid directory name.
- **`baseUrl`** — optional Integray instance URL. Do **not** infer `companySlug` from it.

## Steps

0. **`projects/`** may be missing — create it as a normal directory (`mkdir -p projects`). Do **not** `git init` in `projects/`. Do **not** treat `projects/.git` as the company repo.

1. **Verify** `projects/<name>/` does not already exist. If it does, stop and ask whether to extend the existing project instead. Never silently scaffold over a clone.

2. **Create layout:**

   ```text
   projects/<name>/
     conventions.md
     snapshots/.gitkeep
     working/.gitkeep
     .integray-connection.json
   ```

   Copy [`templates/project/conventions.md`](../../../templates/project/conventions.md) to `projects/<name>/conventions.md`.
   Copy [`templates/projects-repo/.gitignore`](../../../templates/projects-repo/.gitignore) and [`templates/projects-repo/README.md`](../../../templates/projects-repo/README.md) into `projects/<name>/` (the parent integray-skills ignore does **not** apply inside this git).

3. **Write** `.integray-connection.json` with **empty placeholder values**. Never copy `token` from other companies.

   ```json
   {
     "baseUrl": "https://<instance>.integray.app",
     "companySlug": "",
     "token": ""
   }
   ```

   Fill `baseUrl` only when the user gave it. Leave `companySlug` empty unless they stated it.

4. **`git init` inside `projects/<name>/`** (not in `projects/`). Then tell the user to host a **private** remote (you do not create the GitHub/Azure repo) and:

   ```bash
   cd projects/<name>
   git remote add origin git@<host>:<org>/<company-repo>.git
   git add .
   git commit -m "Initial company repo"
   git push -u origin main
   ```

5. **Do not** create `.integray-connection.example.json`.

6. **Do not** download a Config Transfer until the user has filled connection details. Download also requires **Allow sharing remote config transfer** on the company.

## After creation — report this checklist

| Field | Where to get it |
|-------|-----------------|
| `baseUrl` | Integray instance URL (User / DX). Independent of company slug. |
| `companySlug` | Company slug in DX; same as `${#SYSTEM_CompanySlug}` |
| `token` | **Remote control token** — Company Detail → **Remote control** → **Allow control** / **Token**. Not a login JWT. See [remote-api.md](../../../docs/transfer/remote-api.md). |

Remind the user that `.integray-connection.json` is gitignored **in this company git** (via the copied template ignore). Commit in `projects/<name>/`, never in integray-skills. Next step after filling connection: `/download-config`.
