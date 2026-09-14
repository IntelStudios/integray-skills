# Remote API — Upload and Process Config Transfer

> Companion to `docs/transfer/config-transfer-format.md` (transfer JSON generation and Full Sync import
> behaviour). Use this file when the user explicitly asks to **upload**, **deploy**, or
> **import** a generated Config Transfer into an Integray company via the Remote API.

---

## Prerequisites

A single Integray **instance** hosts many **companies**. The instance hostname and the
company slug are independent — do not derive one from the other.

| Item | Description |
|---|---|
| **Integray instance** | Host of the Integray server (the site), e.g. `https://lzoubek.integray.app`. Ask the user explicitly. |
| **Company slug** | Target company within that instance, used in the URL path (e.g. `companyA`). Same concept as `${#SYSTEM_CompanySlug}` — see `docs/entities/variables.md`. Ask the user explicitly. |
| **Remote control token** | Company secret for Remote API auth. Send as `Authorization: Bearer {token}`. This is **not** a user login JWT and **not** an Endpoint token. **Never** hardcode in a transfer JSON, commit to the repo, or store in the KB. |

### Where to get the token

Product UI ([Remote API help](https://learn.integray.app/knowledgebase/productivity/remoteapi/)):

1. On the Integray **Home** page, click the pencil next to the company name → **Company Detail**.
2. In the **Remote control** section, enable **Allow control** and choose **Token** — Integray generates a **Remote control token**.
3. Put that value in `projects/<name>/.integray-connection.json` as `token`. Send it as `Authorization: Bearer {token}`.

Same **Company Detail → Remote control** panel has **Open Remote API documentation** (live OpenAPI for that instance).

HTTP 401 means the header is missing or the string does not match this company's token (rotated, empty, or copied from another company). The token does not expire on its own — regenerate it in Company Detail if needed. Never copy `token` between companies.

HTTP **404** means `{CompanySlug}` was not found in the **runtime configuration cache** (the published company), not merely “this slug exists in Company Detail”. Typical causes: typo in `companySlug` / `baseUrl` (do not guess the slug from the hostname), or the company has never been published / the last publish failed. If the slug is correct, publish the company in DX and retry.

**Empty error bodies.** For **401**, **403**, **404**, and many **400**s the Runtime sets the status and writes **no JSON** (no ProblemDetails, no `message`). An empty curl body is normal — interpret the status using this file, not the payload. **422** on Process is the exception: it includes `publishResult`. **500** is also often body-less.

Full URL pattern:

```
{baseUrl}/api/Remote/{CompanySlug}/...
```

Example: `https://lzoubek.integray.app/api/Remote/companyA/ConfigTransfer/Upload`

OpenAPI spec (instance-specific):

- UI: `{baseUrl}/apidocs/remote-api`
- Spec: `{baseUrl}/api-docs/remote/swagger.json`

All Remote API paths below are relative to `{baseUrl}`.

### JSON field names

Two different JSON documents:

| Document | Where | Field names | Examples |
|---|---|---|---|
| **Remote API** request/response | Upload/Process/Backup HTTP JSON | camelCase | `transferId`, `onlyTest`, `publish`, `overrideVariables`, `publishResult` |
| **Config Transfer file** | The `.json` you download, edit, and upload as `file` | PascalCase | `TransferType`, `Tasks`, `CopyID`, `IsSensitive`, `Value` |

Do not put `onlyTest` / `transferId` into the transfer file, and do not send `TransferType` / `Tasks` as the Process body. ASP.NET model binding on Remote API is case-insensitive, but generate camelCase for API JSON and PascalCase for the transfer file.

`.integray-connection.json` is also camelCase (`baseUrl`, `companySlug`, `token`) — that file is ours, not either of the above.

---

## When to use

- **Only on explicit user request** — e.g. "upload this transfer", "deploy to company X",
  "import the transfer via Remote API".
- Do **not** call the Remote API automatically after generating a transfer file.
- The transfer file must already exist (`Transfer_<Name>_YYYY_MM_DD_HH_MM_SS.json` per
  `docs/transfer/config-transfer-format.md`).

---

## Agent workflow

1. Confirm the user wants to upload/deploy (not just generate the JSON).
2. Collect **Integray instance** (base URL), **company slug**, and **Remote control token**. Ask
   for all three when not already provided — the instance hostname does not imply the
   company slug (and vice versa).
3. If conventions say **Backup before process**, run **`/backup`** first. Keep that
   `transferId`; do **not** Process it as the deploy.
4. **Upload** the transfer file → review the pre-transfer check response. Process uses
   **this** `transferId`.
5. If pre-check passes, **ask the user** whether to run Process with **`publish: true`**
   (apply + rebuild cache) or **`publish: false`** (apply only). Do not assume — confirm
   unless the user already stated a preference. For a full deploy, suggest `publish: true`
   as the default when asking.
6. **Process** with the chosen `publish` value.
7. Report the outcome. When `publish: true`, inspect `publishResult` in the response.
8. If the transfer declares sensitive variables (`hasSensitiveVariables`), remind the user
   to set values via the Variable API or DX administration — see below.

**Do not** call the standalone `POST .../Publish` endpoint unless the user explicitly
asks for a separate publish step (e.g. a prior Process ran with `publish: false` and they
now want to rebuild the cache). Prefer asking up front and setting `publish` on Process.

---

## Step 1 — Upload (pre-transfer check)

```
POST /api/Remote/{CompanySlug}/ConfigTransfer/Upload?fileName={originalFileName}
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: <binary JSON>
```

- **`fileName`** — query parameter; use the transfer file's original name, e.g.
  `Transfer_MyTask_2026_08_10_12_00_00.json`.
- **`file`** — multipart form field containing the JSON file bytes.

### Response — `RemotePreTransferCheckResult`

| Field | Meaning |
|---|---|
| `transferId` | Required for Process. Use the id from **this Upload**, not from `/backup`. |
| `succeeded` | `true` when every required connector is installed (`Status` ≠ `Missing`). |
| `connectors[]` | Per-connector check: `guid`, `version`, `name`, `status` (`Installed` / `Missing`). |
| `hasUnresolvedReferences` | `true` when the transfer references entities missing in the target company. |
| `hasSensitiveVariables` | `true` when the transfer contains sensitive variables. |
| `sensitiveVariables[]` | Names of sensitive variables detected (may be empty). |

**Do not call Process** when `succeeded === false` or unresolved references block a safe
import — report findings to the user first.

### Upload troubleshooting

| HTTP / symptom | Typical cause | What to do |
|---|---|---|
| `401 Unauthorized` | Missing or wrong Remote control token | Verify `Authorization: Bearer {token}` against this company's Company Detail → Remote control. Not a login JWT. |
| `404 Not Found` | Slug not in the runtime configuration cache | Check `baseUrl` and `companySlug`. If both are correct, publish the company in DX and retry. |
| `400` + ProblemDetails `fileName required` | Missing query param `fileName` | Add `?fileName=Transfer_Name.json` to the URL |
| `400` + empty response body | Server rejected the transfer content (not necessarily a curl mistake) | Validate JSON structure per `docs/transfer/config-transfer-format.md`; try DX UI import to compare |
| `200` + `succeeded: false` | Missing connectors on target company | Install connectors listed in `connectors[]` before Process |

The curl example below is the correct multipart format: `?fileName=...` query param +
`-F "file=@...;type=application/json"`.

### curl example

```bash
BASE_URL="https://lzoubek.integray.app"
COMPANY_SLUG="companyA"
TOKEN="your-remote-control-token"
TRANSFER_FILE="Transfer_MyTask_2026_08_10_12_00_00.json"

curl -sS -X POST \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/Upload?fileName=${TRANSFER_FILE}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@${TRANSFER_FILE};type=application/json"
```

---

## Step 2 — Process (apply the transfer)

```
POST /api/Remote/{CompanySlug}/ConfigTransfer/{transferId}/Process
Authorization: Bearer {token}
Content-Type: application/json
```

Request body — `RemoteTransferProcessFilter`:

```json
{
  "overrideTokens": false,
  "overrideVariables": false,
  "overrideRetentionSettings": false,
  "overrideTriggers": false,
  "overrideRunnableSettings": false,
  "importEntityComments": true,
  "importEntityTags": false,
  "onlyTest": false,
  "publish": false
}
```

All fields are optional; values above match API defaults except `publish`, which the
agent sets based on user choice.

### Key fields

| Field | Default | Notes |
|---|---|---|
| `onlyTest` | `false` | Dry-run — validates without applying changes. **Cannot** combine with `publish: true` (HTTP 400). |
| `publish` | `false` | When `true`, synchronously rebuilds the configuration cache after a successful apply. Response includes `publishResult`. **Ask the user** before setting. |
| `overrideVariables` | `false` | When `true`, overwrites existing variable values with values from the transfer. Safer to leave `false` in production unless the user confirms. |
| `overrideTokens` | `false` | Overwrite endpoint tokens from the transfer file. |
| `overrideRetentionSettings` | `false` | Overwrite retention settings from the transfer file. |
| `overrideTriggers` | `false` | Overwrite task triggers from the transfer file. |
| `overrideRunnableSettings` | `false` | Overwrite task runnable settings from the transfer file. |
| `importEntityComments` | `true` | Import `EntityComments[]` from the transfer. |
| `importEntityTags` | `false` | Import entity tags from the transfer. |
| `dataSnapshotCondition` | omitted | `0` = Never, `1` = OnError, `2` = EveryTime, `null` = keep current per step. |

Missing entities are still proposed for deletion (Full Sync,
`docs/transfer/config-transfer-format.md` §1). The `override*` flags above only
control whether those fields on existing entities are replaced from the file.

### Response — `RemoteTransferProcessResult`

When `publish: true`, the response includes `publishResult`:

| Field | Meaning |
|---|---|
| `publishResult.isSuccess` | `true` when status is `Published`, even if warnings exist. |
| `publishResult.status` | `Published`, `Failed`, or transitional states (see OpenAPI). |
| `publishResult.publishedAt` | Timestamp when publish succeeded; otherwise `null`. |
| `publishResult.messages[]` | Warnings and errors (`type`, `code`, `message`). |

**HTTP 422** on Process means the import **succeeded** but publish **failed** — the
configuration was already applied; inspect `publishResult.messages`. See the publish
cheat-sheet in `docs/transfer/config-transfer-format.md` §8.6 (`CACHE_BINDING_GET_TASK_NOT_EXECUTABLE`,
invalid `${#Code}` references, step naming, etc.).

### Process / publish troubleshooting

| Symptom | Meaning | What to do |
|---|---|---|
| HTTP 422 + `publishResult.isSuccess: false` | Import applied, cache rebuild failed | Read `publishResult.messages[]`; fix transfer; Process again with `publish: true` |
| `CACHE_BINDING_GET_TASK_NOT_EXECUTABLE` in messages | Step `OutputSchema` mismatch (typical: HTML Creator) | §8.4 exception in `docs/transfer/config-transfer-format.md` |
| `configurations … invalid variable Code` | `${#Code}` without `Variables[]` | `docs/entities/variables.md` |
| Process OK, endpoint returns wrong/error | Config live but mapping/schema wrong | Verify with GET below |

**Debug workflow:** run Process with `publish: false` to validate import only → fix
transfer JSON → Process with `publish: true` (or standalone `POST .../Publish` if the
user explicitly requests a separate publish step).

**Verify endpoint after successful publish** (when the transfer includes one):

```
GET {BaseURL}/api/endpoint/{CompanySlug}/{endpointGroupSlug}/{endpointSlug}
```

Task-bound GET endpoints may return **201** with `Content-Type: text/html` (or another
raw type per §8.4) instead of the usual JSON wrapper.

### curl examples

**Dry-run (no changes applied):**

```bash
curl -sS -X POST \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/${TRANSFER_ID}/Process" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"onlyTest": true}'
```

**Apply only (`publish: false`):**

```bash
curl -sS -X POST \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/${TRANSFER_ID}/Process" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"publish": false}'
```

**Apply and publish (`publish: true`):**

```bash
curl -sS -X POST \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/${TRANSFER_ID}/Process" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"publish": true}'
```

---

## Standalone Publish (fallback only)

Use only when the user explicitly requests a cache rebuild **after** a prior Process with
`publish: false`:

```
POST /api/Remote/{CompanySlug}/Publish
Authorization: Bearer {token}
```

```bash
curl -sS -X POST \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/Publish" \
  -H "Authorization: Bearer ${TOKEN}"
```

Response: `RemotePublishResult` (same shape as `publishResult` on Process). HTTP 422 when
publish fails.

---

## Pre-check interpretation

### Missing connectors (`succeeded === false`)

The transfer references connectors not installed (or wrong version) on the target company.
Cross-check `connectors[].guid` and `connectors[].version` against `data/connectors.json`.
The user must install the missing connectors in Integray before Process can succeed.

### Unresolved references (`hasUnresolvedReferences === true`)

The transfer references entities (by CopyID or other identifiers) that do not exist in the
target company. Review which entities are referenced and whether the transfer is intended
for this company. Some references may resolve after a prior partial import; others indicate
a wrong target or an incomplete transfer.

### Sensitive variables (`hasSensitiveVariables === true`)

The transfer declares `IsSensitive: true` variables (see `docs/entities/variables.md`). Download
and Backup already store those with empty `Value`. Import does not require values in the JSON,
but the user must set them on a new company before affected Steps can run.

Set values after import via the Variable API:

```
PUT /api/Remote/{CompanySlug}/Variable/Code/{code}
Authorization: Bearer {token}
Content-Type: application/json

{"value": "the-full-new-value"}
```

```bash
curl -sS -X PUT \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/Variable/Code/RemoteApiToken" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"value": "secret-token-value"}'
```

Partial updates are not supported — always send the complete new value. GET responses mask
sensitive values with asterisks.

Alternatively, the user can set values manually in DX administration.

---

## Download vs Backup

| | **Download** | **Backup** |
|---|---|---|
| Endpoint | `GET …/ConfigTransfer/Download` | `POST …/ConfigTransfer/Backup` |
| Skill | `/download-config` | `/backup` |
| Result | JSON file under `projects/<name>/snapshots/` | `{ transferId }` on the Integray server |
| Pre-check / apply | No | No |
| Use | Local snapshot to edit | Undo point **on the instance** before Process |

Process the `transferId` from **Upload** of the edited file. Processing the Backup id reapplies the live company as it was at backup time — it is not a deploy of your JSON.

Conventions **Backup before process** means `/backup`, then Upload, then Process the **Upload** id. **Download after publish** means `/download-config` again.

---

## Download (export)

Export the full company configuration as a transfer file:

```
GET /api/Remote/{CompanySlug}/ConfigTransfer/Download
Authorization: Bearer {token}
```

Requires **Allow sharing remote config transfer** to be enabled on the company. Returns
`application/octet-stream` with a filename like `Transfer_{CompanyName}_{timestamp}.json`.

Sensitive company variables (`IsSensitive: true`) are exported with an **empty** `Value`.
The snapshot is not a secret dump — see `docs/entities/variables.md`. Backup uses the same
export, so the on-instance record is stripped the same way.

Agent path: **`/download-config`** → `scripts/download-config-transfer.py`.

```bash
python scripts/download-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

```bash
curl -sS -o exported_transfer.json \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/Download" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## Backup (on-instance record)

Stores the current company configuration as a transfer record. Does not return the JSON
and does not apply anything.

```
POST /api/Remote/{CompanySlug}/ConfigTransfer/Backup
Authorization: Bearer {token}
```

Response: `{ "transferId": <long> }`.

Agent path: **`/backup`** → `scripts/backup-config-transfer.py`.

```bash
python scripts/backup-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

```bash
curl -sS -X POST \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/Backup" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## Cross-links

| Topic | File |
|---|---|
| Transfer JSON structure, Full Sync, publish gotchas | `docs/transfer/config-transfer-format.md` (§8.4, §8.6) |
| Top-level `Variables[]`, `${#Code}`, `${#SYSTEM_...}` | `docs/entities/variables.md` |
| Connector GUIDs and versions | `data/connectors.json` |
| In-platform scripts building Remote API URLs | Use `${#SYSTEM_BaseURL}` (instance) and `${#SYSTEM_CompanySlug}` (company within that instance) separately — `docs/entities/variables.md` |

---

## OpenAPI reference

The authoritative API definition lives on each Integray instance:

- **UI docs:** `{baseUrl}/apidocs/remote-api`
- **OpenAPI spec:** `{baseUrl}/api-docs/remote/swagger.json`

Do not vendor the full swagger into this KB — it is instance-specific and covers all
Remote API endpoints (agents, task runs, variables, etc.), not just Config Transfer.
Refer to the live spec for request/response schemas beyond the Config Transfer flow
documented here.
