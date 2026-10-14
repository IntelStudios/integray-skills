# Variables — Reference for Config Transfer JSON Generation

> Companion to `docs/transfer/config-transfer-format.md` §3 (top-level `Variables[]`). Company-wide
> constants, set once via DX administration by a human — distinct from
> `docs/entities/local-variables.md`'s Local Variables, which are Task-scoped and reset per Task
> Run.

---

## Structure

**Company-wide, not task-scoped — never changes during a Task Run.** Closer to a
company-wide constant/secret store than a variable in the programming sense; only a
human editing it via DX administration changes the value.

```json
{
  "Code": "SensitiveVariable",
  "Description": "Sensitive variable description",
  "Value": "",
  "IsSensitive": true,
  "VariableGroupCopyID": null,
  "TemplateCopyID": null,
  "ID": 35,
  "Name": "Sensitive variable",
  "CopyID": "58f4a008-2aaf-4753-b946-6704a250a5bf"
}
```

- **`Code`** is what you reference in templating (see below) — not `Name` (a separate
  human-readable label) and not `CopyID`.
- **`IsSensitive: true`** for passwords, connection strings, API keys, tokens, logins —
  anything secret. Don't hardcode secret values inline in a `Configurations[].Configuration`
  string (or anywhere else in the transfer) — put them here instead.
- **Export / `/download-config` always blanks those values.** The platform writes
  `Value: ""` whenever `IsSensitive` is `true`. The variable stays in `Variables[]`
  (`Code`, `CopyID`, `IsSensitive: true`); only the secret is omitted. A snapshot is not a
  password dump. After import onto a **new** company, set values via the Variable API or DX
  (see below). Re-import onto a company that already has values: Process default
  `overrideVariables: false` leaves the live secrets in place — do not set
  `overrideVariables: true` unless the user wants the (empty) transfer values to win.
- **`VariableGroupCopyID`** — optional grouping (`VariableGroups[]`), not required.
- **Why `Variables[]` over hardcoding:** a Config Transfer JSON is meant to be portable
  and often gets exported, committed, or shared. A hardcoded secret gets baked into every
  copy of that JSON and leaks on every re-export. It also can't be swapped per
  environment (dev/staging/prod) without editing every `Configuration` that embeds it —
  `Variables[]` centralizes the value to one place, editable by an admin without
  touching the transfer at all.

---

## Referencing a Variable — `${#<Code>}`

**Confirmed against a real worked example:** `Code: "SensitiveVariable"` →
`${#SensitiveVariable}`. **The leading `#` is required for every templated variable, not
optional** — this was previously undocumented/wrong in this KB (an earlier version said
`${VAR_NAME}`, no `#`).

**Confirmed live usage — a live company transfer declares two
`IsSensitive:true` Variables (`ConnectionString`, `RemoteApiToken`) and references both:**
`${#ConnectionString}` inside a **Postgre SQL Database connector's** own `Configuration`
(its `ConnectionString` field — a completely different connector family from the two below),
and `${#RemoteApiToken}` inside a Node.js processor's `Statement`, alongside
`${#SYSTEM_BaseURL}`/`${#SYSTEM_CompanySlug}` used the same way to build a polling URL.
This confirms substitution isn't JS-Mapper-`Statement`-specific — it applies to
`Configuration` string content generally, across connector families. **Still not
confirmed** whether it also applies to `InputSchemaMapping`/`InputDataFilter` (neither is
a `Configuration` field).

**The runtime substitutes the raw value as-is; it does not add surrounding
quotes.** If the substituted text is going into a script as a string literal (e.g. a JS
Mapper/Node.js `Statement`), **you must supply the quotes yourself around the
placeholder** — `` `const token = "${#RemoteApiToken}";` `` — not
`` `const token = ${#RemoteApiToken};` ``, which would splice the raw value in as bare
(likely invalid) JS. Same as `${LocalVariable.X}`
(`docs/entities/local-variables.md`: quote it yourself) — confirmed here from how
a live company transfer actually uses it: every `${#...}`/
`${#SYSTEM_...}` reference inside a script is manually wrapped in `\"..\"` by the
transfer's own author, never embedded bare. The Postgre SQL Database connector's
`ConnectionString` field works without extra quotes only because the *whole field value*
is the substituted text (no surrounding script syntax to break).

**`${#<Code>}` is statically validated against `Variables[]` at *publish* time,
scanning literally any occurrence of the pattern anywhere in a `Configuration`'s string
content — including inside a comment or a human-readable label that was never meant as a
real substitution site.** Confirmed: a self-test `TestName` string containing
the literal documentation text `${#Code}` (meant as generic placeholder notation, not a
real reference) made publish emit `CACHE_FILLING_STEP_CONFIGURATION_APPLY_VARIABLE_FAILED`
(`"configurations for step ... uses invalid variable Code"`) and skip that Task —
see [publish-codes.md](../transfer/publish-codes.md). Import does not validate this.
If the skipped Task was the only bind for an Endpoint, that method is not in the cache
and its URL 404s. **Never
write the literal text `${#anything}` inside a `Configuration` string unless `anything`
is a real `Variables[]` `Code` (or a real `SYSTEM_...` name)** — including in comments,
log messages, or descriptive strings that merely *talk about* the templating syntax.

---

## `${#SYSTEM_...}` — same `#` templating, for predefined platform values

Same mechanism as above (leading `#`, substituted before a script/Configuration runs),
just for values the platform provides automatically — **no `Variables[]` entry needed
for these**:

| Variable | Meaning | Example value |
|---|---|---|
| `${#SYSTEM_CompanyID}` | ID of the current company | `1` |
| `${#SYSTEM_CompanyName}` | Name of the current company | `Self Test` |
| `${#SYSTEM_CompanySlug}` | Slug of the current company | `self-test` |
| `${#SYSTEM_BaseURL}` | Integray server address | `https://self-test.integray.app` |

Use these instead of a literal company slug/host whenever a Step or Configuration needs
to build a URL back into the platform's own API (e.g. an Endpoint URL, or a script
polling `TaskRun` status via `/api/Remote/...`). A hardcoded value imports and runs fine
on the *same* instance it was written against, then silently breaks — no import-time
error — the moment the transfer is imported into a different instance/company, since it
keeps pointing at the original one.

See `docs/transfer/config-transfer-format.md` §8.3 for the specific case this addresses (Endpoint URLs
called from a script) — the same principle applies to any other script or Configuration
that constructs a URL back into Integray's own API, not just that one case.

---

## Setting values after Remote API import

After importing a transfer via the Remote API (`docs/transfer/remote-api.md`), sensitive
variable values declared in `Variables[]` must still be set on the target company before
affected Steps can run.

| Call | What you get |
|------|----------------|
| Download / Backup JSON | `IsSensitive: true` → `Value` is **empty string**. Not a secret dump. |
| `GET …/Variable/{id}` or `GET …/Variable/Code/{code}` | Same secret is **masked with asterisks**. Inactive variables are omitted. **Company-level only** — template and system variables are not on this API. |
| `PUT` the same paths | Body is `{"value": "<complete new value>"}` only. Code, name, description stay unchanged. Partial updates are not supported. Response masks sensitive values again. |

Needs connection `permission` `read-write` or `full`. There is no skill — curl is in
`docs/transfer/remote-api.md`. Values can also be set in DX administration.

---

## Not to be confused with — three distinct placeholder families

| Placeholder | Scope | Source |
|---|---|---|
| `${#<Code>}` | Company-wide, admin-only | Top-level `Variables[]` (this file) |
| `${#SYSTEM_...}` | Platform-predefined | Not declared anywhere, always available |
| `${LocalVariable.ColumnName}` / `localVariable.ColumnName` | Task-scoped, reset per run | `docs/entities/local-variables.md` — **no `#` prefix**, different (dot) addressing entirely |

Don't mix the syntax up between these — a `#` on a Local Variable reference or a missing
`#` on a top-level `Variables[]`/`SYSTEM` reference will not substitute.
