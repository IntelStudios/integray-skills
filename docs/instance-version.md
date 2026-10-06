# Instance version

Every Integray instance exposes an **unauthenticated** GET:

```
{baseUrl}/api/Integray
```

No Remote control token. No `{CompanySlug}`. This is **not** Remote API (`/api/Remote/...`).

Example: `https://test-prod.integray.app/api/Integray`

## Response

```json
{
  "IssuedTo": null,
  "Expiration": null,
  "Version": "rel-2025-03.017 2026-09-24 11:20:33\n",
  "RenewalNotSuccessfull": false,
  "LicenseIsNotValid": false
}
```

The field that matters for development is **`Version`**. Split it on the first space:

| Part | Example | Meaning |
|------|---------|---------|
| **First token** | `rel-2025-03.017` | Product line / git branch (`rel-YYYY-MM.patch`) |
| **Remainder** | `2026-09-24 11:20:33` | Build stamp (trailing newline is normal) |

License fields (`IssuedTo`, `Expiration`, `RenewalNotSuccessfull`, `LicenseIsNotValid`) are not used for versioning.

Read it with:

```bash
python scripts/get-instance-version.py \
  --connection projects/<name>/.integray-connection.json
```

or `--base-url {baseUrl}`. Stdout:

```
productLine=rel-2025-03.017
buildStamp=2026-09-24 11:20:33
```

`productLine` is the first token of `Version`. Do not curl `/api/Integray` by hand when this script is available. Token is not sent.

Compare two `rel-YYYY-MM.patch` tokens as **(year, month, patch)**. A later **build stamp** is not a new product line. Unparseable `productLine` (not `rel-YYYY-MM.patch`) → treat as “unknown”, do not assume a gated feature exists.

---

## Feature availability

**This table is the catalog.** When a platform behaviour exists only from a given
`productLine`, add a row here. Do not leave the floor only in a skill or a chat.
Protocol details stay in the linked doc; the floor lives in this table.

`From` = first `productLine` that has the feature (that token **and later**). Empty
`From` = no known floor; still confirm with `get-instance-version.py` before assuming
a brand-new path.

| Feature | From `productLine` | Use | Older instance |
|---------|--------------------|-----|----------------|
| Config Transfer Download / Backup / Upload / Process | — | `/download-config`, `/backup`, `/publish` | — |
| `POST Task/{id}/Start`, `GET TaskRun/{id}` | — (present on `rel-2025-03.017`) | `/debug-task-run` `start` / `status` | — |
| Step data snapshot `GET TaskRun/{taskRunId}/Step/{stepId}/Snapshot` | **`rel-2025-03.018`** | `/debug-task-run` `snapshot`; `scripts/task-run.py snapshot`. Protocol: [remote-api.md](transfer/remote-api.md) (Task run snapshot). `$dataRef` expanded in JSON; 204 if nothing stored. | Script **refuses**. Path is absent (typically HTTP 404). |

`scripts/task-run.py snapshot` enforces the snapshot row itself (`SNAPSHOT_PRODUCT_LINE` in
`scripts/integray_remote.py` must match **From** in this table).
