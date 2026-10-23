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

## Debugger

`POST Debugger/Run` for **this company**. A test company and a production company do not share this list. One line per connector guid (not version). The grant is any agent.

No line for that guid → ask once whether this connector may run in the debugger here. Name any write outside the company. Yes appends `always`. No appends `never`. `always` calls later runs and says which agent this run uses. `never` does not call that connector. An explicit request runs once and does not change the line. Product line `rel-2025-03.018`, `permission` `read-only`, and the connector restriction still apply. Details: `docs/transfer/remote-debugger.md` in the KB.

No connectors are granted yet. A grant is a line in this section:

```text
debugger-connector: <guid> always
debugger-connector: <guid> never
```

## Other

- Edit the split tree `working/` (`_transfer.json`, `_meta.json`, entity JSON). Do not keep a second assembled `working/*.json` next to the split. `/publish` assembles to a temp file.
- Do **not** edit `snapshots/`.
