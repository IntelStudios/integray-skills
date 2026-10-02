# Company conventions

Read this file before creating or editing a Config Transfer for this company.

## Connection

- Instance `baseUrl` and `companySlug` are independent — do not derive one from the other.
- Token stays in `.integray-connection.json` (gitignored).

## Full Sync

- Every uploaded transfer must include **all** entities this company should keep.
- Do not upload a file that only contains new tasks unless this company is explicitly greenfield (`greenfield: false` below).

**greenfield:** false

## Agent loop

Values: `ask` (default) or `auto`. Missing key = `ask`. Backup before Process is **always** (KB); not listed here.

- **Publish after dry-run:** ask
- **Download after publish:** ask

## Other

- Edit the split tree `working/` (`_transfer.json`, `_meta.json`, entity JSON). Do not keep a second assembled `working/*.json` next to the split. `/publish` assembles to a temp file.
- Do **not** edit `snapshots/`.
