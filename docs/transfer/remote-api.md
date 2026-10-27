# Remote API

> Companion to `docs/transfer/config-transfer-format.md`. Config Transfer deploy is the
> main loop (`/publish`). The same Remote control token also covers variables, task runs,
> agents, and orchestrator. Live OpenAPI: `{baseUrl}/apidocs/remote-api`.

All paths are `{baseUrl}/api/Remote/{CompanySlug}/…`. Auth: `Authorization: Bearer {token}`
(Remote control token, not a login JWT). Instance hostname and company slug are independent.

Instance **product line** (git branch) is not this API. Unauthenticated `GET {baseUrl}/api/Integray`
returns `Version`; the first token is `rel-YYYY-MM.patch` — [instance-version.md](../instance-version.md).
Remote API itself is from **`rel-2025-03.017`**. Older lines had none. Snapshot GET
and `POST Debugger/Run` are **`rel-2025-03.018`**
([remote-debugger.md](remote-debugger.md)).

## Remote API map

Skills wrap **Config Transfer** plus **Task Run snapshot** (`/debug-task-run`). Other rows
are live company operations — use them when the user asks (set a secret). Do not invent
extra paths.

| Area | Paths (relative) | Skill | `permission` |
|------|------------------|-------|----------------|
| Config Transfer | `GET ConfigTransfer/Download`; `POST ConfigTransfer/Backup`; `POST ConfigTransfer/Upload`; `POST ConfigTransfer/{id}/Process`; `GET ConfigTransfer/List`; `DELETE ConfigTransfer/{id}` | `/download-config`, `/backup`, `/publish` | download + backup: every level; Upload + `--only-test`: `read-write` or `full`; `--publish` / `--apply`: `full`. List/Delete: treat like backup (`read-only` OK — they do not apply config) |
| Variable | `GET Variable/{id}`; `GET Variable/Code/{code}`; `PUT` same | none (curl in this file) | GET: `read-only`; PUT: `read-write` or `full` |
| Cache publish | `POST Publish` | none — prefer Process `--publish` | `full` |
| Task | `GET Task`; `POST Task/{id}/Start`; `/Kill`; `/Clean`; `/Runnable` | `/debug-task-run` (`Start`) | GET: `read-only`; Start/Kill/Clean/Runnable: `read-write` or `full` |
| Task run | `GET TaskRun/…`; logs; restart | `/debug-task-run` (`status`) | GET: `read-only`; restart: `read-write` or `full` |
| Task run snapshot | `GET TaskRun/{taskRunId}/Step/{stepId}/Snapshot` | `/debug-task-run` | `read-only`. Floor: [instance-version.md](../instance-version.md) Feature availability |
| Run debugger | `POST Debugger/Run` | none. Protocol: [remote-debugger.md](remote-debugger.md) | `full` only. Runs one installed connector. Floor: [instance-version.md](../instance-version.md) Feature availability |
| Agent | `GET Agent/List` | none | `read-only` |
| Orchestrator | `GET Orchestrator`; `POST Orchestrator/Runnable` | none | GET: `read-only`; set runnable: `read-write` or `full` |

Scripts enforce the Config Transfer rows and the Task Run snapshot path
(`scripts/task-run.py`). For the rest, the agent must still honour `permission`
(do not PUT a variable or start a task in `read-only`; call `Debugger/Run` only when `permission` is `full`).

---

## Prerequisites

A single Integray **instance** hosts many **companies**. The instance hostname and the
company slug are independent — do not derive one from the other.

| Item | Description |
|---|---|
| **Integray instance** | Host of the Integray server (the site), e.g. `https://lzoubek.integray.app`. Ask the user explicitly. |
| **Company slug** | Target company within that instance, used in the URL path (e.g. `companyA`). Same concept as `${#SYSTEM_CompanySlug}` — see `docs/entities/variables.md`. Ask the user explicitly. |
| **Remote control token** | Company secret for Remote API auth. Send as `Authorization: Bearer {token}`. This is **not** a user login JWT and **not** an Endpoint token. **Never** hardcode in a transfer JSON, commit to the repo, or store in the KB. |
| **`permission`** | Agent + script gate in `.integray-connection.json` (`read-only` \| `read-write` \| `full`; missing = `read-only`). Not the Remote control token. See [AGENT.md § Project permission](../../AGENT.md#project-permission). |

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
   company slug (and vice versa). Check connection `permission` (`read-only` |
   `read-write` | `full`; missing = `read-only`). `read-only` may `/backup` but must not
   Upload or Process. `read-write` may Upload and Process `--only-test`. Process
   `--publish` / `--apply` needs **`full`**. Do not change `permission` unless the user asks.
3. **Always** run **`/backup`** first (do not ask). Keep that
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
| `hasUnresolvedReferences` | `true` when the pre-check thinks the transfer references entities missing on the target. Same-company roundtrip of a complete export can still be `true` — see below. |
| `hasSensitiveVariables` | `true` when the transfer contains sensitive variables. |
| `sensitiveVariables[]` | Names of sensitive variables detected (may be empty). |

**Do not call Process** when `succeeded === false`. A lone
`hasUnresolvedReferences=true` on a complete same-company roundtrip does **not** block
Process — tell the user, then continue if `succeeded` is true.

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

Agent path: **`/publish`** (Upload is the first step) → `scripts/upload-config-transfer.py`.

```bash
python scripts/upload-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

Default: assemble the split tree in `working/` to a temp file. Override with `--file` (already-assembled JSON).

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

When `onlyTest` is true (or `publish` is false), a successful Process returns **HTTP 200** with
an **empty** `RemoteTransferProcessResult` (no `publishResult`). That is normal — the Runtime
does not attach a body unless publish ran.

When `publish: true`, the response includes `publishResult`:

| Field | Meaning |
|---|---|
| `publishResult.isSuccess` | `true` exactly when `status` is `Published` (warnings **and** some Errors that only skipped one entity). Not a “no messages” flag. |
| `publishResult.status` | `Published`, `Failed`, or transitional states (see OpenAPI). |
| `publishResult.publishedAt` | Timestamp when publish succeeded; otherwise `null`. |
| `publishResult.messages[]` | Warnings and errors (`type`, `code`, `message`). |

**HTTP 422** on Process means the import **succeeded** but publish **failed** — the
configuration was already applied; inspect `publishResult.messages`. See the publish
catalog in [`publish-codes.md`](publish-codes.md) (short list in
`docs/transfer/config-transfer-format.md` §8.6).

### Process / publish troubleshooting

| Symptom | Meaning | What to do |
|---|---|---|
| HTTP 422 + `publishResult.isSuccess: false` | Import applied, cache rebuild failed | Read `publishResult.messages[]`; fix transfer; Process again with `publish: true` |
| `CACHE_BINDING_{VERB}_*` in messages | Endpoint method not bound into the cache. Can accompany `Published` + later HTTP 404 | [publish-codes.md](publish-codes.md) |
| `CACHE_FILLING_STEP_CONFIGURATION_APPLY_VARIABLE_FAILED` | `${#Code}` without `Variables[]` | `docs/entities/variables.md` |
| Process OK, endpoint returns wrong/error | Config live but mapping/schema wrong | Verify with GET below |
| Company orchestrator off after publish or after you switch it on | Runtime DB size monitor, not Remote API | See [Company orchestrator vs DB size](#company-orchestrator-vs-db-size) |

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

Agent path: **`/publish`** → `scripts/process-config-transfer.py` (`--only-test`, then `--publish`). Use the `transferId` from Upload.

```bash
python scripts/process-config-transfer.py \
  --connection projects/<name>/.integray-connection.json \
  --transfer-id <upload-id> \
  --only-test

python scripts/process-config-transfer.py \
  --connection projects/<name>/.integray-connection.json \
  --transfer-id <upload-id> \
  --publish
```

`--apply` is Process with `publish: false` (no cache rebuild). Rare; prefer `--publish`.

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

The call is **synchronous**: it waits for running task runs to finish, then rebuilds the
cache. On a busy or large company this can take several minutes. HTTP 200 may still include
warnings in `messages`; HTTP 422 means publish failed.

Response: `RemotePublishResult` (same shape as `publishResult` on Process). HTTP 422 when
publish fails.

---

## Pre-check interpretation

### Missing connectors (`succeeded === false`)

The transfer references connectors not installed (or wrong version) on the target company.
Cross-check `connectors[].guid` and `connectors[].version` against `data/connectors.json`.
The user must install the missing connectors in Integray before Process can succeed.
Download does not call Upload, so it cannot see `Installed` / `Missing`. After
`/download-config`, if KB-newest is not on the instance, tell the user to update
connectors in Integray first; do not bump `working/` until then.

### Unresolved references (`hasUnresolvedReferences === true`)

The transfer references entities (by CopyID or other identifiers) that do not exist in the
target company. Review which entities are referenced and whether the transfer is intended
for this company. Some references may resolve after a prior partial import; others indicate
a wrong target or an incomplete transfer.

**Same-company roundtrip:** Upload of a complete export of *this* company can still return
`hasUnresolvedReferences=true` while `succeeded=true` and Process/`onlyTest` succeed. The
pre-check treats missing numeric `CompanyID` / `EndpointID` / `TaskID` as unresolved and
does not accept portable `SameCompany` + `EndpointCopyID` / `TaskCopyID` (see
[configuration-overrides.md](../entities/configuration-overrides.md)). Do not treat that
flag alone as a failed Upload.

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
| Pre-check / apply | No | Same connector pre-check as Upload; does not apply |
| Use | Local snapshot to edit | Undo point **on the instance** before Process |

Process the `transferId` from **Upload** of the edited file. Processing the Backup id reapplies the live company as it was at backup time — it is not a deploy of your JSON.

Backup always runs (`/backup`), then Upload, then Process the **Upload** id. **Download after publish** means `/download-config` again.

If **Download** and **Backup** both HTTP **500** with an empty body while `List` /
Upload / Process still work, the published cache may have mapping paths whose first
segment is a stale Endpoint/Step `Name` ([config-transfer-format.md](config-transfer-format.md) §7).
Process can have published that state. Fix the path strings and `--publish` again;
do not treat Backup 500 as a dead token.

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

Stores the current company configuration as a transfer record named
`ApplicationBackup_{yyyyMMdd_HHmmss}.json`. Runs the same connector pre-check as Upload
(so the warning triangle in Config transfer is cleared when connectors are installed).
Does not return the JSON and does not apply anything.

Optional JSON body:

```json
{ "deleteOlderThan": 1 }
```

| `deleteOlderThan` | Effect |
|---|---|
| omitted body, omitted property, `null`, or `0` | no cleanup |
| integer `N` > 0 | hard-delete `ApplicationBackup_*` records for **this company** whose `CreatedDate` is more than **N calendar days** old (`current_date - CreatedDate::date > N`). Time of day is ignored. Other file names (uploads) are not deleted. |

```
POST /api/Remote/{CompanySlug}/ConfigTransfer/Backup
Authorization: Bearer {token}
Content-Type: application/json   (only when sending a body)
```

Response: `{ "transferId": <long> }`.

Agent path: **`/backup`** → `scripts/backup-config-transfer.py`.

```bash
python scripts/backup-config-transfer.py \
  --connection projects/<name>/.integray-connection.json
```

Optional cleanup of older automatic backups:

```bash
python scripts/backup-config-transfer.py \
  --connection projects/<name>/.integray-connection.json \
  --delete-older-than 1
```

```bash
curl -sS -X POST \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/Backup" \
  -H "Authorization: Bearer ${TOKEN}"
```

```bash
curl -sS -X POST \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/Backup" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"deleteOlderThan":1}'
```

---

## List and Delete (transfer records on the instance)

These operate on **stored records** in DX (from Backup or Upload), not on `snapshots/` files.

### List

```
GET /api/Remote/{CompanySlug}/ConfigTransfer/List
Authorization: Bearer {token}
```

Returns metadata of **active** records. The transfer JSON is **not** in the response. Inactive (deleted) records are omitted.

Typical fields (camelCase): `id`, `fileName`, `requirementsChecked`, `processedBy`, `processedDate`, `createdByProduct`, `createdByVersion`, `created`, `transferVersion`, `createdByUser`, `createdByUrl`.

`id` is the same number as `transferId` from Backup/Upload — use it with Process or Delete.

```bash
curl -sS \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/List" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Delete

Soft-deletes an active record. Does not change the live company configuration.

```
DELETE /api/Remote/{CompanySlug}/ConfigTransfer/{transferId}
Authorization: Bearer {token}
```

**404** when the record does not exist, belongs to another company, or is already inactive.

```bash
curl -sS -X DELETE \
  "${BASE_URL}/api/Remote/${COMPANY_SLUG}/ConfigTransfer/${TRANSFER_ID}" \
  -H "Authorization: Bearer ${TOKEN}"
```

No agent skill. Use when the user asks to list or remove server-side transfer records (e.g. after `/backup`). Do not Process a Backup `id` as the deploy — Process the id from Upload.

---

## Company orchestrator vs DB size

If the company orchestrator (`DXCompany.IsRunnable`) turns itself off after you switch it
on in DX, after Process `--publish`, or after `POST Orchestrator/Runnable`, it may be the
runtime **DB size monitor**, not a Remote API bug. The job compares Postgres size to
`DB_SIZE_LIMIT_MB` (env / user secrets / provisioning; unit MB). Over the error threshold
it sets `IsRunnable=false` and turns it off again on the next tick if someone switches it
on. System log key `HealthCheck=DBSize`. Orchestrator switch always logs reason
`RemoteRequest`, including publish, so the log looks like Remote API. Check
`IsRunnable` / `IsRunnablePrev`. If the limit is not configured, the job does not stop
orchestrators.

---

## Task run snapshot

**Not** Config Transfer Download (`snapshots/` on disk). This is the **data snapshot of
one Step in one Task Run**, for debugging a live process.

**Version floor:** [instance-version.md](../instance-version.md) **Feature availability**
(row “Step data snapshot”). Check `productLine` before calling; the CLI refuses an older
line. Protocol below is the contract **when the instance has that row**.
Skill: [`.agents/skills/debug-task-run/SKILL.md`](../../.agents/skills/debug-task-run/SKILL.md).
CLI: `python scripts/task-run.py --connection … snapshot --task-run-id … --step-id …`.
With `projects/<name>/working/` beside the connection file, stdout is an identity map
(`{ts:}` / `{dsc:}` / `{e:}` → `Name`) plus a compact tree; `--out` keeps the raw JSON.

```
GET /api/Remote/{CompanySlug}/TaskRun/{taskRunId}/Step/{stepId}/Snapshot
Authorization: Bearer {token}
```

- `{taskRunId}` — numeric task run id (`taskRunID` from `POST Task/{id}/Start`, or from
  `GET TaskRun/{id}`).
- `{stepId}` — numeric **`Step.ID`** on the Task definition (`taskStepID` in the log).
  **Not** Step `CopyID`, **not** a task-step-run id. The caller must already know it
  (from `working/tasks/*.json` or the log).
- Permission: GET → `read-only` is enough. Starting the task first needs `read-write`
  or `full`.

Response is one JSON object (`application/json`): the **data-structure tree** of that
Task Run as it looked after the named Step (same tree mappings walk —
[data-addressing.md](../entities/data-addressing.md)). Shape:

| Field | Meaning |
|-------|---------|
| `Schema` | Type tree. Root `Name` is `""`. Each column has `Name`, `AllowNull`, `DataType`, and when `DataType` is **7** (Table) a nested `Schema`. |
| `Rows` | Array of row objects. Keys match `Schema.Columns[].Name`. A Table cell is an **array** of nested row objects (or `null`). |
| `HasDefinedRows` | The table carries a row collection (`true` on a normal 200 with data). |

**Identity keys**, not DX display names (working JSON uses names; the runtime tree uses
these):

| Token | Guid is | Resolve in `working/` |
|-------|---------|------------------------|
| `{ts:<guid>}` | Step `CopyID` | `tasks/*.json` → `Steps[].CopyID` → `Name` |
| `{dsc:<guid>}` | DataSchema **column** `CopyID` | `data-schemas/*.json` → `Columns[].CopyID` → `Name` |
| `{e:<guid>}` | Endpoint `CopyID` | `endpoints/*.json` |

A nested schema with **`Guid` + `Version`** is a catalog / system DataSchema (e.g. Text
`b76c3662-4903-4512-97a9-72f32eaecd01` / `1.0.0`); its columns often appear as **display
names** (`Text`). A nested schema with only `Name` (e.g. `"User"`) is an inline table
shape; its columns stay `{dsc:…}`. `DataType` is the same enum as elsewhere: `1` Int,
`2` String, `3` Bool, `4` Base64, `5` DateTime, `6` Double, **`7` Table**, `8` JSON,
`9` Decimal.

A `{ts:…}` column at **root** is a Step stored at root (Bulk / no `InputSchema`). A
`{ts:…}` column **inside** another `{ts:…}` / `{e:…}` row is a RowByRow Step nested
under that parent. Do not treat `{ts:…}` as “this GET’s Step only” — the snapshot is the
**whole assembled tree**, with every Step/Endpoint node that existed when it was stored.

A cell stored as `{"$dataRef":"<guid>"}` is replaced with the file contents as a
**string**. There is no separate multipart part. When `$dataRefSource` is set (endpoint
data), the file is taken from there. If the file is missing on disk, that cell is `null`.

Example (200) — two root Steps; the second has a nested RowByRow Step. The long `Text`
cell is already expanded from `$dataRef`:

```http
GET /api/Remote/acme/TaskRun/1520/Step/88/Snapshot
Authorization: Bearer {token}

HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
```

```json
{
  "Schema": {
    "Name": "",
    "Columns": [
      {
        "Name": "{ts:6ce65480-6e47-43bd-a788-aaf6e0bc5e53}",
        "AllowNull": true,
        "DataType": 7,
        "Schema": {
          "Name": "Text",
          "Guid": "b76c3662-4903-4512-97a9-72f32eaecd01",
          "Version": "1.0.0",
          "Columns": [
            { "Name": "Text", "AllowNull": false, "DataType": 2 }
          ]
        }
      },
      {
        "Name": "{ts:5214ad46-bc75-4369-aa30-c4731e561851}",
        "AllowNull": true,
        "DataType": 7,
        "Schema": {
          "Name": "User",
          "Columns": [
            { "Name": "{dsc:fc302299-f3fc-41c1-aaa5-b583cf99dd55}", "AllowNull": true, "DataType": 1 },
            { "Name": "{dsc:58af2346-c9da-4044-b4ca-033de61cd1dc}", "AllowNull": true, "DataType": 2 },
            {
              "Name": "{ts:7bb2ea54-be03-47f5-a563-3cf63205b43f}",
              "AllowNull": true,
              "DataType": 7,
              "Schema": {
                "Name": "User",
                "Columns": [
                  { "Name": "{dsc:fc302299-f3fc-41c1-aaa5-b583cf99dd55}", "AllowNull": true, "DataType": 1 },
                  { "Name": "{dsc:58af2346-c9da-4044-b4ca-033de61cd1dc}", "AllowNull": true, "DataType": 2 }
                ]
              }
            }
          ]
        }
      }
    ]
  },
  "Rows": [
    {
      "{ts:6ce65480-6e47-43bd-a788-aaf6e0bc5e53}": [
        { "Text": "Text 1" },
        { "Text": "Text 2 - this text should be a data ref in stored in a shared location" }
      ],
      "{ts:5214ad46-bc75-4369-aa30-c4731e561851}": [
        {
          "{dsc:fc302299-f3fc-41c1-aaa5-b583cf99dd55}": 1,
          "{dsc:58af2346-c9da-4044-b4ca-033de61cd1dc}": "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, to",
          "{ts:7bb2ea54-be03-47f5-a563-3cf63205b43f}": [
            {
              "{dsc:fc302299-f3fc-41c1-aaa5-b583cf99dd55}": 1,
              "{dsc:58af2346-c9da-4044-b4ca-033de61cd1dc}": "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, to"
            }
          ]
        }
      ]
    }
  ],
  "HasDefinedRows": true
}
```

| HTTP | When |
|------|------|
| **200** | The step ran or is running in that task run, **and** a snapshot is stored. |
| **204** | The step ran or is running (`InProgress` 100, success 200–203, failure 300–307) but **no** snapshot was stored. Empty body. Often `DataSnapshotCondition: 0` (Never), or `1` (On error) on a successful step. |
| **404** | Task run missing, wrong company, or the step **did not run** in that run (`Unknown` 0, `Scheduled` 1, `WaitingForAgent` 101, `NotRun` 401, `Parked` 999). |
| **401** | Token missing, wrong, or company has no Remote control token. |

`DataSnapshotCondition` on the Step (`0` Never, `1` On error, `2` Everytime) is in
[config-transfer-format.md](config-transfer-format.md) §6. 204 is a valid debug result,
not a failed Start.

To **create** a run: `POST /api/Remote/{CompanySlug}/Task/{id}/Start` → `{ "taskRunID": … }`
(`scripts/task-run.py start --task-id`). Poll `GET …/TaskRun/{taskRunId}` (`status`) until
the family is no longer waiting/running, then `snapshot`.

---

## Cross-links

| Topic | File |
|---|---|
| Transfer JSON structure, Full Sync, publish failures | `docs/transfer/config-transfer-format.md` (§8.4, §8.6), [publish-codes.md](publish-codes.md) |
| Instance `productLine` and gated features | `docs/instance-version.md` (Feature availability) |
| Run one installed connector without a saved task | [remote-debugger.md](remote-debugger.md) |
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
