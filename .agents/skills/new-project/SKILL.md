---
name: new-project
description: >-
  Scaffold a new empty Integray company project under projects/<name>/ with
  snapshots, changes folders and .integray-connection.json template.
  Use when the user asks to create a new Integray project, company, or workspace
  folder, or invokes /new-project.
disable-model-invocation: true
---

# New Integray company

Scaffold `projects/<name>/` for one Integray company. Read [AGENT.md](../../../AGENT.md) for the full playbook. Nested git: [docs/projects.md](../../../docs/projects.md).

## Inputs

Determine from the user message or ask once:

- **`<name>`** — project slug under `projects/`. Must be a valid directory name.
- **`baseUrl`** — optional Integray instance URL. Do **not** infer `companySlug` from it.

## Steps

0. **Check `projects/`** (required). Ready = at least one company folder (`projects/<other>/`) **or** nested `projects/.git`. If missing, empty, or neither git nor a company:
   - Explain: public integray-skills has no companies; one **private** git repo = the whole `projects/` directory; connection files and secrets stay out of that git via [templates/projects-repo/.gitignore](../../../templates/projects-repo/.gitignore).
   - **Offer** to initialize the nested repo. Do **not** run it until the user says yes. Do **not** scaffold `projects/<name>/` first.
   - If they agree: `mkdir -p projects`, copy `templates/projects-repo/.gitignore` and `README.md` into `projects/`, `git init` inside `projects/`. Then tell them to host a **private** remote (you do not create the remote) and:

     ```bash
     cd projects
     git remote add origin git@<host>:<org>/<integray-projects>.git
     git add .
     git commit -m "Initial projects repo"
     git push -u origin main
     ```

   Canonical copy: [docs/projects.md](../../../docs/projects.md).

1. **Verify** `projects/<name>/` does not already exist. If it does, stop and ask whether to extend the existing project instead.

2. **Create layout:**

   ```text
   projects/<name>/
     conventions.md
     snapshots/.gitkeep
     changes/.gitkeep
     .integray-connection.json
   ```

   Copy [`templates/project/conventions.md`](../../../templates/project/conventions.md) to `projects/<name>/conventions.md`.

3. **Write** `.integray-connection.json` with **empty placeholder values**. Never copy `token` from other companies.

   ```json
   {
     "baseUrl": "https://<instance>.integray.app",
     "companySlug": "",
     "token": ""
   }
   ```

   Fill `baseUrl` only when the user gave it. Leave `companySlug` empty unless they stated it.

4. **Do not** create `.integray-connection.example.json`.

5. **Do not** download a Config Transfer until the user has filled connection details. Download also requires **Allow sharing remote config transfer** on the company.

## After creation — report this checklist

| Field | Where to get it |
|-------|-----------------|
| `baseUrl` | Integray instance URL (User / DX). Independent of company slug. |
| `companySlug` | Company slug in DX; same as `${#SYSTEM_CompanySlug}` |
| `token` | Remote API Bearer JWT |

Remind the user that `.integray-connection.json` is gitignored, and that the new folder should be committed in the nested `projects/` repo (not integray-skills). Next step after filling connection: Download (`GET {baseUrl}/api/Remote/{companySlug}/ConfigTransfer/Download`) — see [docs/transfer/remote-api.md](../../../docs/transfer/remote-api.md).
