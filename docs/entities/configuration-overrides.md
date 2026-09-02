# Configuration overrides for specific connectors — hidden fields not in `data/configuration-schemas.json`

> Companion to `data/configuration-schemas.json`. That file is the authoritative schema
> source for a Configuration's UI fields (`properties`/`required`), but some connectors
> have **hidden fields that aren't listed there at all** and must be used *instead of*
> what the schema's own `properties`/`required` would otherwise imply. This file
> documents those known overrides, one connector/schema at a time, as they're discovered.
> Always check here **before** trusting `data/configuration-schemas.json`'s `required` list
> literally for a connector that has an entry below.

---

## `Integray Endpoint Connector` — `EndpointID`/`CompanyID` override

**Configuration schema:** `1e97198c-085d-492a-a049-6f8f56467df0` v`3.4.0` ("Integray Endpoint").

`data/configuration-schemas.json`'s `required` array for this schema lists `CompanyID`,
`EndpointID`, `RequestType`, `ThrowErrorOnNonSuccessResponse` — and per the schema's
`properties`, both come from a `$ref: "DX://Company_Endpoint"` UI dropdown selector.
`docs/transfer/config-transfer-format.md` §2 warns (correctly, as a *general* rule about `$ref: "DX://..."`
fields) that such a raw number pair is not remapped by the transfer mechanism and must be
fixed by hand after import into a different instance.

**That general warning does not apply to this connector — do not fill `CompanyID`/
`EndpointID` at all.** Use two hidden fields instead, neither of which appears anywhere in
`data/configuration-schemas.json`'s `properties`/`required` for this schema:

| Field | Type | Value |
|---|---|---|
| `SameCompany` | boolean | `true` |
| `EndpointCopyID` | string (UUID) | the target Endpoint's own `CopyID`, exactly as declared in this same transfer's top-level `Endpoints[]` |

```json
{
  "SameCompany": true,
  "EndpointCopyID": "<CopyID of the target Endpoint in Endpoints[]>",
  "RequestType": "post",
  "ThrowErrorOnNonSuccessResponse": true,
  "Data": "${input}"
}
```

- **`EndpointCopyID` is a normal `CopyID` cross-reference** (`docs/transfer/config-transfer-format.md` §1) —
  the transfer mechanism resolves/binds it to the actual imported Endpoint on import, the
  same as any other `*CopyID` field (`PrevStepCopyID`, `TaskCopyID`, ...). No manual
  "re-open the config and re-pick the Endpoint from the dropdown" step is needed after
  import, unlike what the general `$ref: "DX://..."` warning in §2 would otherwise imply.
- **`SameCompany: true`** — set this for the normal case, where the target Endpoint lives
  in the same company as this Configuration/Task (e.g. it's declared in the same
  transfer's `Endpoints[]`, imported into the same company). Behavior/shape when `false`
  (a cross-company reference) is not yet explored in this KB — ask the user or flag it if
  that scenario comes up.
- `RequestType`/`ThrowErrorOnNonSuccessResponse`/`Data`/etc. are otherwise exactly as
  documented in `data/configuration-schemas.json` for this schema — only the
  `$ref: "DX://Company_Endpoint"` portion (`CompanyID`+`EndpointID`) is replaced by
  `SameCompany`+`EndpointCopyID`.
- Auth against an `AuthenticationType:1` target is resolved entirely internally via
  `SameCompany`+`EndpointCopyID`. No token/header/query-param needs to be supplied
  anywhere in the calling Configuration; the connector looks up and applies the target
  Endpoint's own auth itself. This only covers `SameCompany: true` — cross-company
  behavior is still unexplored.
- `Data` placeholder substitution auto-quotes a string value; don't add your own quotes
  around it. `"Data": "{\"Value\": \"${input.Value}\"}"` (manual quotes around the
  placeholder, as you'd write for a plain string) produces a **doubled-quoted** value in the
  request body — `{"Value": ""actual-value""}` — because the platform's own substitution
  already wraps a string column's value in quotes. Correct form omits the manual quotes:
  `"Data": "{\"Value\": ${input.Value}}"`. (`"Data": "${input}"` in the example above is
  unaffected — that placeholder resolves to the whole input object, not a quoted string.)
- `RequestType` only supports `get`, `post`, and `getnewdata` — no `put`/`patch`/`delete`.
  Use a Node.js processor Step with `fetch()` for those verbs against a same-company
  Endpoint instead (build the URL from `${#SYSTEM_BaseURL}`+`${#SYSTEM_CompanySlug}`,
  `docs/transfer/config-transfer-format.md` §8.3).

### Not yet confirmed — other `$ref: "DX://..."` connectors

**A full scan of `data/configuration-schemas.json` (2026-08-07) found exactly one other
`$ref: "DX://..."` occurrence in the entire KB** — no third case exists as of that scan:

- **`Integray Task Execution`** config, `guid: 239b10a7-ed53-4768-bb1a-a33bea808e1a`,
  `version: 1.0.2` (used by the `Integray Start Task Connector`) — `$ref:
  "DX://Company_Task"`, `required: ["CompanyID", "TaskID"]`. Structurally identical
  pattern to the Endpoint Connector case above (`$ref: "DX://Company_Endpoint"` →
  `CompanyID`+`EndpointID`).

**Whether this one has an analogous hidden override (e.g. a `TaskCopyID`-style field) is
explicitly unconfirmed — asked the user directly (2026-08-07), answer was "don't know".**
Don't assume it does just because the Endpoint Connector turned out to, and don't assume
it doesn't either. If a transfer needs to call this connector: ask the user again (they
may have found out by then) or fill `CompanyID`/`TaskID` per the schema at face value and
explicitly flag to the user that this is unconfirmed and may need a manual fix after
import into a different instance (per the general `$ref: "DX://..."` warning in
`docs/transfer/config-transfer-format.md` §2) — don't silently invent a `SameCompany`/`TaskCopyID` pair by
analogy without confirming it first.

**If any future KB update, hand-test, or user-reported fact resolves this — update this
entry (don't just add a new one) and remove the "unconfirmed" framing.** Same instruction
applies if a third `$ref: "DX://..."` connector is ever added to
`data/configuration-schemas.json` — re-scan and add it here before assuming it behaves like
either case above.

---

## See also

- `docs/transfer/config-transfer-format.md` §2 — the general `$ref: "DX://..."` warning this file overrides
  for the Integray Endpoint Connector specifically.
- `data/connectors.json` / `data/configuration-schemas.json` — the general, structured schema
  files this file overrides for the specific cases listed above.
