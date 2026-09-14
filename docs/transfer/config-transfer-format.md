# Integray Config Transfer — Core Rules

> Machine-usable source of truth for generating Integray Config Transfer JSON files.
> Companion files: `data/connectors.json`/`data/configuration-schemas.json`/
> `data/data-schemas.json` (connector/configuration/data-schema data, cross-referenced by
> `guid`+`version` — see §4), `docs/entities/input-data-filter.md`
> (`InputDataFilter` reference), `docs/entities/data-addressing.md` (`InputSchemaMapping` tree
> logic — read it whenever a task has more than one branch or more than one connector
> in a row), `docs/entities/local-variables.md` (Task-scoped `VariablesSchema`/`VariablesDefaults`/
> `VariablesSchemaMapping`), `docs/entities/data-checkpoint.md` (Step-scoped `DataCheckpointColumn`/
> `DataStorageColumn`, persists across separate Task Runs), `docs/entities/variables.md`
> (top-level `Variables[]` and `${#SYSTEM_...}` — company-wide constants/secrets,
> `${#Code}` templating), `docs/entities/configuration-overrides.md` (hidden Configuration fields
> not in `data/configuration-schemas.json` — connector-specific overrides),
> `docs/transfer/remote-api.md` (upload and process a transfer via the Integray Remote API),
> `examples/generic_worked_example.json`
> (generic worked example, §10). Company working copies live under `projects/<name>/`
> (not KB). Read that project's `conventions.md` and live transfer when implementing
> for a specific company — they may extend or override generic rules.

---

## 1. What a Config Transfer is

A JSON file used to sync configuration (Tasks, Endpoints, DataSchemas, Configurations,
Variables, Agents, Tags, ...) between Integray instances. Import is a **Full Sync**:
entities matched by identifier are updated, unmatched ones are inserted, and anything
present in the target instance but absent from the transfer is proposed for deletion.

Full Sync is about which entities exist. It does not by itself overwrite variable
values, endpoint tokens, task triggers, runnable settings, or retention on entities
that already exist. Those stay unless Process is called with the matching
`override*` field set to `true` (defaults are `false`) — see
`docs/transfer/remote-api.md` (Process filter).

Import can be performed via the DX UI or programmatically through the Integray Remote API
(Upload → Process) — see `docs/transfer/remote-api.md`.

---

## 2. Identifiers — `ID` vs `CopyID` vs `Guid`

The single most important concept in this format.

| Identifier | Scope | Use |
|---|---|---|
| **`ID`** | Local DB auto-increment, per-instance. **Not portable.** | Placeholder value when generating from scratch (e.g. `0`) — import remaps it. Array order never matters. |
| **`CopyID`** (UUID) | Stable, globally unique, cross-instance. | **Import matching key** (insert vs. update). New entity → generate a fresh UUIDv4. Cross-references inside the transfer go through `*CopyID` fields (`TaskGroupCopyID`, `AgentCopyID`, `PrevStepCopyID`, `TaskCopyID`, ...) or a nested `{"CopyID": "..."}` object (custom `InputSchema`/`OutputSchema`). |
| **`Guid` + `Version`** | Platform-global (not per-company) — connectors and **system** DataSchemas. | `Steps[].Connector` is always `{"Guid": ..., "Version": "X.Y.Z"}`. System DataSchemas carry `Guid`+`Version` *in addition to* `CopyID` — reference them via `{"Guid":...,"Version":...}`, **not** `CopyID` (CopyID there is a DB-export artifact, not the real key). Custom DataSchemas have no `Guid`/`Version` at all — reference via `{"CopyID":...}`. |

**Disambiguation rule:** if a schema/entity has `Guid`+`Version` populated in `DataSchemas[]`, reference it that way; otherwise use `CopyID`.

**Shared Agent constant** — `AgentCopyID` for the built-in Shared agent is always
`11111111-1111-1111-1111-111111111111`, identical across all instances. Do not declare
it in `Agents[]`.

**Exception:** `TaskGroups[]` and `EndpointGroups[]` need a real, unique, non-zero `ID` —
unlike every other entity, `ID: 0`/missing `ID` here means the group is silently never
created (falls back to the platform's Default group on import, no error shown).

**The platform's built-in Default group — confirmed live:** `CopyID: null`, `Slug:
"default-group"`. Relevant when addressing an Endpoint that ended up ungrouped (the
fallback above) — its URL is `/api/endpoint/<company-slug>/default-group/<endpoint-slug>`.

---

### 2.1 `Name`/`Slug` — length limits and a forbidden character

Confirmed against the platform's own DB column definitions:

| Entity | Column | Limit |
|---|---|---|
| Task (`DXTask`) | `Name` | `varchar(60)` |
| Task Step (`DXTaskStep`) | `Name` | `varchar(60)` |
| Endpoint (`DXEndpoint`) | `Name` | `varchar(255)` |
| Endpoint (`DXEndpoint`) | `Slug` | `varchar(60)` |

**No literal `.` in any entity's `Name` (Task, Step, Endpoint, TaskGroup, EndpointGroup) —
confirmed root cause of a real "cannot be published" failure.** A Step named `Relay 10 MB
through Node.js` (three of them, one per size in a new "Big data on disk" test group)
silently broke publish for their whole Endpoints — no schema/reference error anywhere,
JSON fully valid, every `*CopyID` resolved — the UI's own "Select connector" step-name
field flagged it with a red warning the whole time, which is what actually surfaced this
(not inferrable from the transfer JSON alone). Rename the step (e.g. `Node.js` → `Node
JS`) and it publishes fine. Root cause is presumably the platform's own `StepName.Column`
dot-addressing convention (`docs/entities/data-addressing.md`, `*OutputMapping` strings) choking on a
literal `.` inside the name segment itself — treat `.` as forbidden in every entity `Name`
until proven otherwise, not just Step.

---

## 3. Top-level structure

```json
{
  "TransferType": "ConfigTransfer",
  "ID": 1,
  "Name": "<ask the user for a meaningful name>",
  "CreatedByProduct": "Integray",
  "CreatedByVersion": "<known KB/Integray version, else neutral>",
  "CreatedBy": "Integray",
  "CreatedByUrl": "integray.com",
  "TransferVersion": 6,
  "Created": "<current ISO 8601 timestamp>",
  "Tasks": [], "Connectors": [], "DataSchemas": [], "Agents": [],
  "TaskGroups": [], "EndpointGroups": [], "Endpoints": [], "SecondaryTokens": [],
  "Configurations": [], "Variables": [], "EntityComments": [], "VariableGroups": [],
  "Templates": [], "Tags": [], "TagMappings": [], "AuthConnections": []
}
```

- `TransferType` — always exactly `"ConfigTransfer"`.
- `Name` — **always ask the user.**
- `CreatedByProduct`/`CreatedBy` — `"Integray"`. `CreatedByUrl` — `"integray.com"`. `TransferVersion` — `6`, unless the user specifies otherwise.
- `Created` — current ISO 8601 timestamp.
- Every collection may legally be `[]` — none is required to be non-empty.

---

## 4. Connectors

```json
{ "Name": "JS Mapper", "Guid": "1bea42f2-ca51-4ca7-9585-f10323a1d804", "Version": "3.5.6" }
```

- `Guid` is the global connector-type identifier, stable across instances; `Version` is `"Major.Minor.Patch"`.
- List each connector **once** in `Connectors[]` even if used by many Steps.
- Use the **newest known version** unless the user requests otherwise.
- `Steps[].Connector` references the same way: `{"Guid": "...", "Version": "..."}`.

### Looking up connector/configuration/schema data — three cross-referenced files

**`data/connectors.json`** (257 connectors), **`data/configuration-schemas.json`** (181
Configuration schemas), **`data/data-schemas.json`** (642 system DataSchemas) — a raw,
authoritative platform export, each a flat list of entities (`{$schema, kind, guid,
version, name, metadata, ...}`, the type-specific fields — `actions`/`schema`/`columns`
— alongside). Entities cross-reference the *other* two files by `{guid, version}`, never
inlined:

```
Connector action → configurationRefs[].{guid,version} → data/configuration-schemas.json entry
Connector action → inputSchema/outputSchema.schemaRef.{guid,version} → data/data-schemas.json entry
DataSchema column (type "table") → tableRef.{guid,version} → data/data-schemas.json entry (nested sub-schema)
```

Example — `Integray Start Task Connector`'s `defaultAction`:
```json
{
  "inputSchema": { "mode": "none" },
  "outputSchema": { "mode": "required", "schemaRef": { "guid": "f7cb5a42-...", "version": "1.0.1" } },
  "configurationRefs": [ { "guid": "239b10a7-...", "version": "1.0.2" } ]
}
```
— its Configuration fields live in the `data/configuration-schemas.json` entry for
`239b10a7-.../1.0.2`; its output columns live in the `data/data-schemas.json` entry for
`f7cb5a42-.../1.0.1`.

**`schemaRef` present vs. absent is the tell for system vs. custom schema on that
action.** Present (like above) → the action always produces/consumes that *exact* system
schema, `Guid`+`Version`+columns fixed — reproduce it exactly (§7). Absent, with `mode`
still `"required"`/`"optional"`/`"mandatory"` (an action needs *some* schema, just not a
fixed one — e.g. JS Mapper's `outputSchema: {"mode": "mandatory"}`, no `schemaRef`) →
free choice, design a custom `DataSchema` for it (§7). `mode: "none"` → the action has no
input/no output at all (e.g. `Delay`) — `InputSchema`/`OutputSchema` on the Step stay
`null`.

**Field names in these three files are a raw platform export (lowercase `camelCase`:
`guid`, `columns`, `allowNull`, `tableRef`, `schemaRef`, `configurationRefs`...) — not
the Config Transfer JSON's own field names (`PascalCase`: `Guid`, `Columns`, `AllowNull`,
`ComplexType`, `InputSchema`/`OutputSchema`, `Configurations`...).** Translate, don't
copy verbatim — e.g. a DataSchema column's `tableRef` here becomes a Step/DataSchema
column's `ComplexType` in the actual transfer (§7); a connector's `configurationRefs[]`
entry becomes a Step's `Configurations[].ConfigurationSchema`.

Column `type` values here are lowercase strings (`string`, `int`, `bool`, `base64`,
`datetime`, `double`, `table`, `json`, presumably `decimal`) — map to the numeric `Type`
codes used in actual transfers, see the table in §7.

Connectors with no configuration on an action (pure converters/readers) legitimately have
`configurationRefs: []`.

**Gotcha — `Node.js processor` (`Guid: 5a70dfd2-9803-4bcf-b090-652b156f7236`) has its
*own* `Timeout` inside its Configuration, separate from the Step's platform `Timeout`.**
Any step whose `Statement` calls `fetch(...)` is bound by both: the Step's own `Timeout`
field governs the whole step, but the connector's internal HTTP client has a **second,
independent timeout that silently defaults to 100 seconds** if the Configuration JSON
omits a `"Timeout"` key (see this connector's schema in `data/configuration-schemas.json`).
Bumping only the Step's `Timeout` does nothing for outbound `fetch()` calls — confirmed
directly: a step's `Timeout` was raised 300s→600s to fix a timeout, and it kept failing
at ~100s anyway because the connector's own internal default was the actual bottleneck
the whole time, invisible from the Step `Timeout` field in the UI. **Always set an
explicit `"Timeout"` (seconds) in the Configuration JSON, at least matching the Step's
own `Timeout`, on every `Node.js processor` step that calls `fetch()`.**

---

## 5. Configurations

A concrete settings instance for a connector on a given Step (or shared across Steps if `IsShared: true`).

```json
{
  "Configuration": "<JSON string — shape defined by the connector's ConfigurationSchema>",
  "IsShared": false,
  "ConfigurationSchema": { "Guid": "ab00eb5f-e86e-4107-b8cd-b151a204c4c6", "Version": "1.0.5" },
  "TaskCopyID": "<only if IsShared:false and bound to one task>",
  "TemplateCopyID": null,
  "ID": 0, "Name": "<human-readable name>", "CopyID": "<new UUID>"
}
```

- **`Name` must be a real, non-null string** — unlike the Step-level `Configurations[].Name` wrapper field (which is fine as `null`), the actual top-level `Configurations[]` entity's own `Name` is rejected by the DX UI (`"Invalid value of Name = null."`) the moment someone tries to save/edit it, even though import itself doesn't catch it. Give every Configuration a real descriptive name, never `null`.
- `Configuration` is a **JSON string nested inside JSON** — must satisfy the connector's `ConfigurationSchema` (look up the action's `configurationRefs[]` in `data/connectors.json`, then that `{guid,version}`'s own `schema` field in `data/configuration-schemas.json`) including all `required` fields. Import doesn't validate this at load time — a missing required field surfaces later in the UI or at task run.
- `IsShared: true` → reusable across Steps/Tasks, no `TaskCopyID`. `IsShared: false` → typically scoped via `TaskCopyID`, referenced by the Step's `Configurations[].ConfigurationCopyID`.

**Required top-level `Configurations[]` fields** — every entry must include all of:

| Field | Notes |
|---|---|
| `Configuration` | JSON string (not an object) |
| `ConfigurationSchema` | `{Guid, Version}` from the action's `configurationRefs[]` |
| `IsShared` | `false` for task-scoped configs |
| `TaskCopyID` | Required when `IsShared: false` — CopyID of the owning Task |
| `TemplateCopyID` | `null` unless bound to a template |
| `Name` | Non-null descriptive string |
| `ID`, `CopyID` | Unique identifiers (§2) |

**Symptom → fix (Process/import — configurations):**

| Symptom | Typical cause | Fix |
|---|---|---|
| `Inserting configuration … failed` (empty name in log) | `ConfigurationData` instead of `Configuration` | Rename to `Configuration` |
| Same, or config not linked to task | Missing `IsShared` / `TaskCopyID` | Set `IsShared: false` + `TaskCopyID` to owning Task's CopyID |
| Config visible but broken in UI on save | `Name: null` | Set a real `Name` string |

**`$ref: "DX://..."` fields (e.g. `Integray Endpoint Connector`'s `EndpointID`, `Integray Start Task Connector`'s `TaskID`) are UI-only dropdown mechanisms.** The stored value is a raw instance-specific number (e.g. `{"CompanyID": 1, "EndpointID": 12}`). Unlike CopyID references, **these numbers are not remapped by the transfer mechanism** — after import into a different instance they still point at source-instance entities and must be fixed manually. Not an issue when exporting/reimporting into the *same* instance (e.g. self-test scenarios). For the **Integray Endpoint Connector** specifically, do not use `CompanyID`/`EndpointID` — see `docs/entities/configuration-overrides.md`.

**Correction to `data/configuration-schemas.json`'s own "Postgre Statement" description:** it says input data is available from a temp table called `#InputData`, same wording as the Microsoft SQL Database connector (where `#` is correct T-SQL). For **Postgre SQL Database specifically**, that `#` causes a real Postgres syntax error — the actual table name is just `InputData`, no `#`. Confirmed by hand-testing. The Postgre connector's own description text looks copy-pasted from MS SQL and was never adjusted — don't assume other connector descriptions are accurate either without checking.

**Note on `description` fields across these three files: only readable at the
Configuration-property level, not above it.** `data/configuration-schemas.json`'s
`schema.properties.<Field>.description` is real inline HTML/text (as quoted above) —
trustworthy to read, verify against, and correct. But `metadata.description` on a
connector or on an individual action (both in `data/connectors.json`) is an opaque
localization-string GUID, not text — there's no lookup table for it here, so don't try to
read or quote it as documentation.

**Postgre SQL Database: `InputData` column names must be double-quoted.** The input schema's column names (e.g. `CopyID`) carry their original casing, but unquoted Postgres identifiers get folded to lowercase — `i.CopyID` silently resolves to `i.copyid`, which won't exist and errors. Always quote: `SELECT i."CopyID" FROM InputData i`.

---

## 6. Tasks → Steps

```json
{
  "Description": null, "Type": 1, "Cron": null, "Priority": 99,
  "DisposeData": false, "IsRunnable": true, "MaxInstances": 1,
  "TaskRunSuccessDays": null, "TaskRunFailedDays": null, "TimeSchedule": null,
  "VariablesDefaults": null, "VariablesSchema": null,
  "TaskGroupCopyID": "<group CopyID, or omit if ungrouped>",
  "TemplateCopyID": null, "Steps": [ /* see below */ ],
  "ID": 0, "Name": "<task name>", "CopyID": "<new UUID>"
}
```

### `Task.Type` (enum `DXTaskType`)

| Value | Meaning |
|---|---|
| `0` `Scheduled` | Runs on the `Cron` schedule. |
| `1` `OnDemand` | Manual trigger only ("Run Now"). **Safe default** unless the task is explicitly bound to an Endpoint or needs a schedule. |
| `2` `Endpoint` | Triggered by an Endpoint (`*InputTaskCopyID` in some Endpoint points at this Task's `CopyID` — §8). |

`Type: 2` is only valid if such an Endpoint actually exists in the transfer — otherwise the task has no trigger and won't run from the UI. `Type: 0` only makes sense if `Cron` reflects an actually-intended schedule. **Default to `Type: 1` when unsure** and ask the user to confirm a schedule/endpoint trigger.

**Gotcha:** `Cron` is only meaningful for `Type: 0`. For `Type: 1`/`2` it **must be `null`** — a populated value there is a copy-paste leftover that misleads the UI into showing a schedule that doesn't exist. Never copy `Cron` from an existing task without checking its `Type` first.

### `Cron` — Quartz.NET syntax, not Unix cron

- **7 fields**, not 5: `seconds minutes hours day-of-month month day-of-week [year]`.
- **Seconds first**, not last/omitted.
- Day-of-month and day-of-week cannot both be `*` — one of them must be `?`.
- Year is an optional 7th field.
- Example: `"0 0 * ? * * *"` = fires every hour on the hour.
- If unsure of the exact intended schedule, ask the user rather than guessing.

### Step structure

```json
{
  "Timeout": 60, "InputProcessType": 1, "InputProcessThreads": null,
  "StopIfEmptyOutput": true, "ConnectorStorageSize": 10, "DataSnapshotCondition": 1,
  "InputSchemaMapping": { "<ColumnName>": "<path — see docs/entities/data-addressing.md>" },
  "VariablesSchemaMapping": null, "ErrorBehavior": 1, "InputDataFilter": null,
  "IsTempDeactivated": false, "Attempts": 1, "AttemptsDelay": 5,
  "Connector": { "Guid": "...", "Version": "..." },
  "AgentCopyID": "11111111-1111-1111-1111-111111111111",
  "PrevStepCopyID": "<CopyID of the temporal predecessor, or null for the first step>",
  "InputSchema": { "CopyID": "..." } | { "Guid": "...", "Version": "..." } | null,
  "OutputSchema": { "CopyID": "..." } | { "Guid": "...", "Version": "..." } | null,
  "Configurations": [
    { "ConfigurationCopyID": "<config CopyID>", "ConfigurationSchema": { "Guid": "...", "Version": "..." },
      "ID": 0, "Name": null, "CopyID": "<new UUID — independent of ConfigurationCopyID>" }
  ],
  "AdditionalInputs": null,
  "SelectedActionCode": "defaultAction", "ID": 0, "Name": "<step name>", "CopyID": "<new UUID>"
}
```

- **`InputProcessType`: `1` = `Bulk`, `2` = `RowByRowSequentially`** (confirmed from source enum) — e.g. a step named `"Bulk"` processing all rows in one call has `InputProcessType: 1`; a step named `"Row by row"` invoking the connector once per row has `InputProcessType: 2`.
- **`DataSnapshotCondition`**: `0` Never, `1` On error, `2` Everytime.
- **`StopIfEmptyOutput: true`** halts the task (status `FinishedNoData`) whenever a step produces zero output rows — including steps that *by design* never return rows, e.g. a plain SQL `DELETE`/`UPDATE` with no `RETURNING`. Set `false` on any step whose empty output is normal, not an error condition, or downstream steps silently never run.
- **`ErrorBehavior`** — see §6.1.
- **`PrevStepCopyID`/`AdditionalInputs`/`InputSchemaMapping`** — see `docs/entities/data-addressing.md`.

### 6.1 `ErrorBehavior`

```csharp
FailStep = 0, FailTask = 1, FailStepAndContinue = 2, FailTaskAndContinue = 3
```

Encodes two independent axes:

1. **Continue vs. stop** (second word) — `FailStep`/`FailTask` halt *that branch* at
   the failing step (downstream steps in it don't run). `...AndContinue` variants let
   the branch continue. This is always scoped to the failing branch — other parallel
   branches in the same task run are unaffected either way.
2. **Step vs. Task propagation** (first word) — `FailStep`/`FailStepAndContinue` keep
   the failure local to the step; overall Task Run status stays in the success family
   (`FinishedWithErrors`=202 instead of `FinishedSuccess`=200). `FailTask`/
   `FailTaskAndContinue` propagate the worst step status up to the Task Run, landing it
   in the Failed (3XX) family.

Regardless of `ErrorBehavior`, the individual **Task Step Run** always gets a specific
failed status reflecting the cause (`FailedConnector`, `FailedTimeout`, `FailedRuntime`,
`FailedInput`, `FailedOutput`, `FailedAgent`, `FailedAgentKilled`,
`FailedCancelledByUser`). `ErrorBehavior` only affects propagation/continuation, not
whether the step itself "looks" failed.

**Terminology:** `Task`/`Step` = definitions (what's in this JSON). `Task Run`/`Task Step Run` = runtime instances — only these carry a `DXTaskRunStatus`.

```csharp
public enum DXTaskRunStatus {
    Unknown = 0,
    Scheduled = 1,                                              // 0XX waiting
    InProgress = 100, WaitingForAgent = 101,                    // 1XX running
    FinishedSuccess = 200, FinishedNoData = 201,                // 2XX success
    FinishedWithErrors = 202, NothingToProcess = 203,
    FailedConnector = 300, FailedAgentKilled = 301,             // 3XX failed
    FailedTimeout = 302, FailedCancelledByUser = 303,
    FailedRuntime = 304, FailedAgent = 305,
    FailedOutput = 306, FailedInput = 307,
    NotRun = 401,                                               // 4XX other
    Parked = 999                                                // special
}
```

`NotRun` (401) is a **generic "step never ran" status**, not tied to one cause — it
fires whenever a branch stops before execution reaches the step, whether due to
`StopIfEmptyOutput` or `ErrorBehavior` without `...AndContinue`.

#### The two axes per value (no derived property names — just the 4 enum values)

| `ErrorBehavior` | Stops or continues past the failure | Task Run status family |
|---|---|---|
| `FailStep` (0) | stops (rest of that branch: `NotRun`) | stays success family (`FinishedWithErrors`) |
| `FailTask` (1) | stops (rest of that branch: `NotRun`) | propagates to Failed (3XX) |
| `FailStepAndContinue` (2) | continues | stays success family (`FinishedWithErrors`) |
| `FailTaskAndContinue` (3) | continues | propagates to Failed (3XX) |

#### How `TaskRunStatus` is derived from Task Step Run statuses

Not just the last step's status — computed by walking the step tree from `FirstStep`,
each visited step contributing (or not) to a `propagationStatuses` set:

| Step run state | Contributes | Recursion |
|---|---|---|
| No run record / `Scheduled` | `InProgress` | stops |
| `NotRun` | nothing | stops |
| `InProgress`/`WaitingForAgent` | itself | stops |
| Failure (300–307) and `ErrorBehavior` is `FailTask`/`FailTaskAndContinue` | the failure status | continues |
| Failure and `ErrorBehavior` is `FailStep`/`FailStepAndContinue` | `FinishedWithErrors` (202) | continues |
| Other (success) | itself | continues |

When recursion continues (`ErrorBehavior` is `FailStepAndContinue`/`FailTaskAndContinue`),
the next step actually runs — not over "empty data" as a rule, over whatever its **own**
`InputSchemaMapping`/`AdditionalInputs` actually resolve to, same as any other step
(`docs/entities/data-addressing.md` §1.1). It has no special awareness that its temporal predecessor
failed; if that predecessor isn't also what it reads its *data* from, it runs completely
normally on real data (confirmed: a `Delay` step deliberately failed with
`FailStepAndContinue`, immediately followed by a step whose `InputSchemaMapping` points
at an earlier, unaffected step — that following step produced its full, correct output,
not a degraded/empty result).

**Resolving multiple statuses into one final `TaskRunStatus`:** confirmed — when the set
mixes a failure status with a success-family status (e.g. `{300, 201}` under
`FailTaskAndContinue`), **the failure status wins**. Still open: the exact rule when the
set has two *different* failure codes, or two different success codes with no failure —
"worst wins" there is an unconfirmed hypothesis.

Verified end-to-end on isolated self-test branches (`Trigger failure` → `After failure`, no other branches in the task):

| `ErrorBehavior` | `Trigger failure` | `After failure` | `propagationStatuses` | Final `TaskRunStatus` |
|---|---|---|---|---|
| `FailStep` (0) | 300 | `NotRun` (401) | `{202}` | 202 (certain — singleton set) |
| `FailTask` (1) | 300 | `NotRun` (401) | `{300}` | 300 (certain — singleton set) |
| `FailStepAndContinue` (2) | 300 | runs (≈`FinishedNoData`=201) | `{202, 201}` | success family (exact value unconfirmed, both candidates < 300) |
| `FailTaskAndContinue` (3) | 300 | runs (≈`FinishedNoData`=201) | `{300, 201}` | **300 — confirmed** (failure beats success) |

#### Deliberately triggering a failure (e.g. to test `ErrorBehavior` propagation)

A JS Mapper step (`Guid: 1bea42f2-ca51-4ca7-9585-f10323a1d804`, `Version: 3.5.6`) with a
`Statement` of `throw "Expected error!"; return [];` reports Step status
**`FailedConnector` (300)** — a JS `throw` is surfaced as a connector failure, not
`FailedRuntime`. Useful when a transfer needs to deliberately exercise the
`ErrorBehavior`/`TaskRunStatus` propagation rules above. Pair it with a trivial
passthrough step (`Statement: return inputData;`) downstream to verify what, if
anything, continues past the failure.

#### `Integray Start Task Connector` (`Guid: ffbc588e-e25f-4d14-ab88-93c421b8e9bc`), `Execution: "sync"` — when the calling Step itself fails

The connector has no `Timeout` field of its own (unlike the Endpoint connector) — in
`Execution: "sync"` mode it blocks until the target task's run finishes. **Confirmed:
that wait is bounded by the calling Step's own platform `Timeout`, not unlimited.**
Tested with a `Start` step (`Timeout: 10`) targeting a task that just runs `Delay: 30`:
the `Start` step itself fails after 10s with **`FailedTimeout` (302)** — but **the target
task is completely unaffected by the caller giving up**: it keeps running independently
and finishes normally on its own schedule (confirmed `FinishedNoData`/201 at ~31s,
checked directly in the target Task Run's own history). So a sync-mode timeout is purely
"the caller stopped waiting," never a cancellation of the run it was waiting on — don't
assume a timed-out `Start` step means the target task didn't happen; check the target's
own run history, not just the caller's step status.

**Confirmed second case with the same shape — a target ending in the Failed family
(`TaskRunStatus` ≥ 300) also makes the calling `Start` step itself fail, as
`FailedConnector`, instead of returning that status as normal `TaskRunID`/`TaskRunStatus`
output.** Checked directly in the DX UI's own execution log for the `Start` step
(`"Executed task failed with status FailedConnector."` / `"Step failed -
FailedConnector."`) — not inferable from the JSON or the connector's schema. A target
ending in the *success* family (200/201/202, including `FinishedWithErrors`) behaves
normally: `Start` succeeds as a step and returns the resolved `TaskRunID`/`TaskRunStatus`
as data. So the general rule: **sync `Start` only returns data normally when the target's
outcome is in the success family; anything else (target `TaskRunStatus` ≥ 300, or the
Step's own `Timeout` expiring first) makes `Start` itself report as a failed step
(`FailedConnector`/`FailedTimeout` respectively), with no output** — plan
`InputSchemaMapping`/`ErrorBehavior` around a `Start` step accordingly: don't assume its
own success/failure as a step tracks 1:1 with whether it returned "good" data, and don't
rely on reading its primary output when testing a scenario where it's expected to fail —
read it via `AdditionalInputs` instead (confirmed to safely yield `[]`, never throw or
block the reading step, per `docs/entities/data-addressing.md` §1), since it's unconfirmed whether a
`Bulk`-processing step downstream even invokes its own connector at all against a
genuinely empty *primary* input.

---

## 7. DataSchemas

**Two fundamentally different kinds — know which one you're writing before you write it.**

- **Custom schema** — yours to design. Free choice of `Name`, column `Name`s, `Type`s,
  `AllowNull`, however many columns you want. Generate a fresh `CopyID` for the schema and
  for every column. Nothing to look up, nothing to get wrong except your own intent.
- **System schema** — the platform's, not yours. A fixed contract with a real `Guid`+
  `Version` identity that already exists on every instance, columns and all. You don't
  design it, you *reproduce* it — the exact `Name`, exact column `Name`s (and ideally
  `Type`/`AllowNull` too), copied from a confirmed source (the table below, or an actual
  live-imported transfer), never invented-but-plausible. Editing a system schema's
  `Columns` to "fix" a merge error is never the right move — if it doesn't match, your
  copy of it is wrong, not the platform's. A wrong/invented column name still produces
  perfectly valid, well-formed JSON — it fails only at merge time, on the target
  instance, with **"Cannot find column `<X>` in schema `<Name>` (ID = ...)"** (confirmed:
  `examples/generic_worked_example.json` itself had this bug — the `Text` system
  schema's real column is `Text`, not the `Content` it wrongly used, presumably confused
  with `Rest API Output`'s real `Content` column — undetected until a live import
  actually failed on it).

```json
{
  "TemplateCopyID": null,
  "Columns": [ { "Order": 0, "Type": 2, "AllowNull": true, "ID": 0, "Name": "ColumnName", "CopyID": "<new UUID per column>" } ],
  "IsHidden": false, "ID": 0, "Name": "<schema name>", "CopyID": "<new UUID>"
}
```

System schema adds `Guid`+`Version`:
```json
{ "ID": 413, "Guid": "653ab571-701c-4b67-9721-4558ea5d627e", "Version": "1.0.0",
  "Name": "Rest API Header", "CopyID": "141c1394-54b4-4255-bff9-30781d14c4ff", "Columns": [...] }
```

**Referencing a schema anywhere else — Step `InputSchema`/`OutputSchema`,
`AdditionalInputs[].InputSchema`, Endpoint `*InputSchema`/`*OutputSchema`,
`ComplexType` — always follows the same form: system schema → `{"Guid":...,
"Version":...}`; custom schema → `{"CopyID":...}`.** This applies at every reference
site, not just one of them — using `CopyID` for a system schema (or vice versa) breaks
the merge on import.

**`InputSchemaMapping` (primary and every entry in `AdditionalInputs`) must cover every
column of the declared `InputSchema` with `AllowNull: false`.** Nullable columns can be
omitted — the engine fills them as null/missing. A missing *required* column produces
**"Incorrect Mapping"** (primary) or **"Incorrect Additional Input Mapping"**
(`AdditionalInputs`) on open/import. Always check `AllowNull` before generating a mapping.

**On a GET-bound task, a missing required-column mapping can surface only at publish
time, as `CACHE_BINDING_GET_TASK_NOT_EXECUTABLE`, instead of "Incorrect Mapping" at
import.** Import can succeed with no mapping error even though a required column is
missing several steps upstream of the endpoint's `GetOutputStepCopyID` — the generic
`"task <Name> bound to the GET method is not executable"` message gives no hint the cause
is a mapping gap. This error code does not always mean the §8.4 special-schema mismatch
(its only other documented cause) — check every step's mapping coverage first, ideally
with the script below.

Before deploying any transfer with `InputSchema`/`AdditionalInputs` on custom or system
schemas, a quick script check catches missing-required-column mappings for the whole file
at once (handles both system schemas, keyed by `Guid`+`Version`, and custom ones, keyed by
`CopyID`):
```python
import json
d = json.load(open("<transfer>.json"))
by_guid = {(s["Guid"], s["Version"]): s for s in d["DataSchemas"] if "Guid" in s}
by_copyid = {s["CopyID"]: s for s in d["DataSchemas"]}

def required_cols(schema_ref):
    if not schema_ref:
        return None
    s = by_guid.get((schema_ref.get("Guid"), schema_ref.get("Version"))) if "Guid" in schema_ref else by_copyid.get(schema_ref.get("CopyID"))
    if not s:
        return None
    return {c["Name"] for c in s["Columns"] if not c.get("AllowNull", True)}

def check(label, schema_ref, mapping):
    req = required_cols(schema_ref)
    if req is None:
        return
    missing = req - set((mapping or {}).keys())
    if missing:
        print("missing required mapping:", label, "->", missing)

for t in d["Tasks"]:
    for s in t["Steps"]:
        check(f"{t['Name']} / {s['Name']} (primary)", s.get("InputSchema"), s.get("InputSchemaMapping"))
        for i, ai in enumerate(s.get("AdditionalInputs") or []):
            check(f"{t['Name']} / {s['Name']} (AdditionalInputs[{i}])", ai.get("InputSchema"), ai.get("InputSchemaMapping"))
```

**Each mapped pair must also have the same `Type`** (codes below; for `Type: 7` the
nested `ComplexType` / `tableRef` too). The source-side column in the mapping path may
have a different *name* than the target key — the platform allows that — but it may not
have a different type (`docs/entities/data-addressing.md`). Matching names is not a type match:
the same column name on two versions of one system schema can be Integer in one and
String in the next. Import / `onlyTest` do not reject that; the Task Run fails later
(`FailedAgent` + `InvalidCastException`, often `Int32` → `String`) when the consuming
step starts. After a schema version bump, align consumer `InputSchema` `{Guid,Version}`
with producer `OutputSchema`, or convert explicitly — do not copy mappings by name alone.

**A `Type: 2` (String) column whose value looks like a date/time can be silently
reformatted in transit between Steps.** When a producing Step's `String` column holds an
ISO 8601-shaped value (e.g. `2026-08-24T15:22:06Z`) and a downstream Step reads it as its
**primary** input via `InputSchema`+`InputSchemaMapping`, the value can arrive reformatted
— `T` replaced with a space, no `Z`, fractional seconds dropped, and the date portion
reordered (e.g. `24.08.2026 15:22:06`) — independent of which connector reads it.
`AdditionalInputs` does not exhibit this. Known platform bug, not yet fixed. Workaround:
wrap the value in a non-date-shaped string on the producing side (e.g. prefix with a
letter) and strip the wrapper on the consuming side, before it crosses that boundary.

### Column `Type` codes

| Code | Type |
|---|---|
| 1 | Integer |
| 2 | String |
| 3 | Bool |
| 4 | Base64 |
| 5 | DateTime |
| 6 | Double |
| 7 | Table (nested DataSchema) |
| 8 | JSON |
| 9 | Decimal |

**`Type: 7` (Table) must have `ComplexType`** referencing the sub-schema describing the
nested rows (form per the rule above) — omitting it throws `NullReferenceException` on
merge. The sub-schema itself must also be present in `DataSchemas[]`, not just
referenced.

```json
{ "Order": 1, "Type": 7, "AllowNull": true, "ID": 0, "Name": "Headers", "CopyID": "...",
  "ComplexType": { "Guid": "3db38ca0-04ea-4dc1-9300-8963615c4457", "Version": "1.0.0" } }
```

- New custom schema → generate a `CopyID`, no `Guid`/`Version`.
- **`ID` must be unique across every entity in the whole transfer** (DataSchemas, their
  Columns, top-level Configurations, Tasks, Steps, Step-level Configuration entries,
  Variables — one shared sequence). Collisions throw `"An item with the same key has
  already been added"`. Order of assignment doesn't matter, only uniqueness. `ID: 0` as a
  placeholder on individual DataSchema Columns (import remaps it) is the one long-standing
  exception seen in practice — don't extend that same leniency to Steps/Configurations/
  Tasks/Variables, keep those genuinely unique.
  - **Gotcha:** a Step's own `Configurations[]` entry (the join/reference object, its own
    `ID`+`CopyID`) is a *different* entity from the top-level `Configuration` it points at
    via `ConfigurationCopyID` (a *different* `ID`+`CopyID`) — don't reuse the target
    Configuration's `ID` for the step-level entry when adding a step later (e.g. patching
    in a middle step after the fact). Before generating a transfer, a quick script check
    across the whole file catches this class of bug cheaply:
    ```python
    import json
    d = json.load(open("<transfer>.json"))
    topcfg = {c["CopyID"]: c for c in d["Configurations"]}
    for t in d["Tasks"]:
        for s in t["Steps"]:
            for cfg in s["Configurations"]:
                tgt = topcfg.get(cfg["ConfigurationCopyID"])
                if tgt and tgt["ID"] == cfg["ID"]:
                    print("collision:", s["Name"], cfg["ID"])
    ```
- Reuse the same system schema **once** in `DataSchemas[]` even if used by many Steps/Tasks.

### Common system schemas

**Column names below are confirmed live** (imported and used successfully on a real
instance — cross-checked against a live company transfer). Guid+Version alone isn't enough to generate a working
`InputSchemaMapping`/`GetOutputMapping` — the column *name* is a separate fact you can
still get wrong even with the right Guid, and doing so fails import with **"Cannot find
column `<X>` in schema `<Name>` (ID = ...)"**, not a vague error.

| Name | Guid | Version | Columns (confirmed) |
|---|---|---|---|
| Rest API Header | 653ab571-701c-4b67-9721-4558ea5d627e | 1.0.0 | `Key`, `Value` |
| Rest API Output | 751c0d01-da24-4cde-8155-3f2b8ef9a95a | 2.1.0 | `StatusCode`, `Headers`, `Content`, `ContentText`, `ContentJSON` |
| Advanced Rest API Header | 3db38ca0-04ea-4dc1-9300-8963615c4457 | 1.0.0 | `Key`, `Value` |
| Advanced Rest API JSON Output | c216ea83-3ba3-4979-9ac9-95e108247726 | 1.2.0 | `StatusCode`, `Headers`, `Content` |
| HTML | cc494d6c-6a55-48dc-b6bc-f8f65afca13e | 1.0.0 | `HTML` |
| Text | b76c3662-4903-4512-97a9-72f32eaecd01 | 1.0.0 | `Text` |
| JSON | 5bdd29fb-b543-4d0a-acf6-c249ffe40e62 | 1.0.0 | `JSON` |
| Endpoint HTML Output | 50619995-8af1-4692-a2ec-789bc44f7e17 | 1.0.0 | `HTML` |
| Integray Task Run Status | f7cb5a42-c936-42d3-bd9e-6065a71cd5b5 | 1.0.1 | `TaskRunID`, `TaskRunStatus` |

**Gotcha — `examples/generic_worked_example.json` had the `Text` schema's column wrong
(`Content` instead of the real `Text`) until this was caught by a live import failure.**
That file is explicitly *not* validated against a live instance (see the file table at
the top of this KB) — it's illustrative, and a column name is exactly the kind of detail
that's easy to invent plausibly-but-wrongly (`Rest API Output`, a *different* schema,
genuinely does have a `Content` column, which is presumably where the confusion came
from) without ever noticing, since the JSON stays perfectly well-formed either way. Trust
the table above (or a real imported transfer) over that example file for column names.

**Gotcha — reading `Rest API Output`'s `ContentJSON` column through `AdditionalInputs`
into a JS Mapper crashes the consuming step, even with a trivial `return [];` body.**
Mapping `ContentJSON` (the `json`-typed column) via `AdditionalInputs[].InputSchemaMapping`
into a JS Mapper's `inputDataN` fails with `FailedConnector` / Jint `SyntaxError:
Unexpected token '-' in JSON at position N` — thrown during the platform's own input
marshaling, before the script body even runs (not a bug in the consuming script).
Workaround: set the producing step's `OutputFormat: 2` (Text) instead of `3` (JSON), map
`ContentText` (a plain string column, unaffected) through `AdditionalInputs` instead, and
call `JSON.parse()` on it yourself inside the script.

This table only covers schemas seen in the worked example / this KB's own self-test
project — for anything else, **check `data/data-schemas.json` first** (642 entries, each
`{guid, version, name, columns[], ...}`) before asking the user or guessing. **Match on
`{guid, version}`
together, not `guid` alone** — the same `guid` can have multiple version entries in that
file (e.g. `Rest API Output` has both `2.0.0`, 4 columns, and `2.1.0`, 5 columns incl.
`ContentJSON` — picking the wrong one silently gets you a plausible-looking but wrong
column list).

**`data/data-schemas.json` is large but confirmed *not* exhaustive** — the six special
"Endpoint ... Output" schemas below (§8.4) are absent from it entirely (all six checked,
zero found), most likely because they're synthetic/virtual (hardcoded into the raw
response-shaping mechanism, not real registered DataSchema entities), not an omission to
read anything into. If a schema isn't in that file either, fall back to what's already
confirmed live in this KB, ask the user for the exact `Guid`+`Version`+columns, or look
them up in the target instance directly. **Never invent a system schema's column
name** — a plausible-but-wrong one fails import with the "Cannot find column" error above
instead of the more familiar "Incorrect Mapping" (which is what a wrong *path*, not a
wrong *column name*, produces — see `docs/entities/data-addressing.md` §2 for that distinction).

---

## 8. Endpoints

```json
{
  "Slug": "endpoint-slug", "AuthenticationType": 0, "IsDelete": true,
  "AllowedFrom": null, "MaxMessageSize": null, "EndpointGroupCopyID": "<group CopyID>",
  "EndpointDataDays": 0, "WaitTime": 60, "ExtendedInfo": null, "TemplateCopyID": null,
  "GetToken": null, "GetInputTaskCopyID": "<Task CopyID bound to GET>",
  "GetInputMapping": null, "GetInputSchema": null, "GetOutputSchema": null,
  "GetOutputMapping": null, "GetOutputStepCopyID": "<Step CopyID GET reads output from>",
  "GetIsSystemResponse": true, "GetIsSaveOutput": false, "GetFailMessage": null,
  "GetSaveInputDataCondition": 1, "GetOutputType": 1, "GetSecondaryTokens": [],
  "PostToken": null, "PostInputTaskCopyID": "<same pattern for POST>",
  "PostOutputStepCopyID": "<same pattern for POST>",
  "...": "the same field family repeats for Patch* and Put*"
}
```

- `*InputTaskCopyID` binds that HTTP method to a **Task** by `CopyID`. **A Task may be
  bound to exactly one (Endpoint, HTTP method) pair** — never shared across two
  different Endpoints, and never shared across two different methods of the *same*
  Endpoint (e.g. `GetInputTaskCopyID` and `PostInputTaskCopyID` can't point at the same
  Task). Each task-bound method needs its own dedicated Task, no exceptions.
- `*OutputStepCopyID` binds to a **Step** inside that task — the source of the response.
- `EndpointGroupCopyID` groups endpoints (like `TaskGroupCopyID` groups tasks).
- New endpoint → generate `CopyID`, any `ID`.

**Gotcha — cloning an endpoint from a template.** Rewriting `*InputTaskCopyID`,
`*OutputStepCopyID`, `ID`, `Name`, `CopyID` is not enough. **`*OutputMapping` (e.g.
`GetOutputMapping`) is a JSON string with hard-coded `"StepName.Column"` addresses** —
if the output/merge step's name differs between the template task and the new one (e.g.
template has `"Evaluate test results"`, new task has `"Merge test results"`), the
mapping keeps pointing at a step that doesn't exist in the new task. Import succeeds
silently, but the endpoint then returns an empty `[]` even though the step really
returns data. After cloning an endpoint, always verify `*OutputMapping` points at a step
that actually exists, by name, in the target task.

### 8.1 No-task ("raw storage") endpoints

An Endpoint with every `*InputTaskCopyID` `null` and `GetIsSystemResponse: true` has no
Task behind it at all — the platform itself stores whatever is POSTed and returns it on
GET, keyed by a generated GUID. Confirmed by hand-testing against a real instance:

- `POST`/successful `PATCH` → `{"ID": "<guid>"}`.
- `GET` (collection) → array of stored records; `GET /{id}` → one record; unknown/missing
  id → `404`. The collection GET accepts two query parameters: `since` (`Created >=
  since`, inclusive) and `limit` (caps the returned count; `limit=0` returns `[]`, no
  error). Sorting is by `Created` only, with no secondary tie-breaker — records with an
  identical `Created` (or duplicate `Created` values across paginated calls) have no
  guaranteed relative order.
- No built-in way to clear a no-task endpoint's accumulated data in bulk — `DELETE` only
  targets one `/{id}` at a time, and the Integray Endpoint Connector can't issue `DELETE`
  at all (`RequestType` only supports `get`/`post`/`getnewdata`). To reset between test
  runs, delete directly via a `Postgre SQL Database` Step: `DELETE FROM dxendpointdata
  WHERE endpointid IN (SELECT id FROM dxendpoint WHERE copyid IN (...))`.
- `PUT /{id}` = **full replacement** of the record. `PATCH /{id}` = **partial merge** —
  only the properties actually present in the PATCH body change; every other property on
  the stored record is left exactly as it was. Don't assume PATCH behaves like PUT with a
  smaller body — a platform that (incorrectly) treats them the same would show up as the
  omitted properties going missing/null after a PATCH.
- `PUT /{id}` and `PATCH /{id}` both → `404` for a missing or unknown id.
- `DELETE /{id}` → success status for a known id, `404` for a missing/unknown id — but
  only when the Endpoint's `IsDelete` ("Allow Deleting") is `true`. When `IsDelete:
  false`, `DELETE` on *any* id → `405 Method Not Allowed` instead — the toggle actually
  blocks the verb, it doesn't just hide it in some UI. POST/GET/PATCH/PUT on the same
  endpoint are unaffected by `IsDelete`.
- Response shape is `GetOutputType` (`0`=Output, `1`=Input, `2`=Input & Output) ×
  `GetIsSystemResponse` (bool) — 6 combinations:

  | OutputType | SystemResponse | Shape |
  |---|---|---|
  | Output | true | `{ID, Created, Data: null}` — no Task means no Output, ever |
  | Output | false | bare `null` |
  | Input | true | `{ID, Created, Data: <posted>}` |
  | Input | false | bare `<posted>`, no wrapper |
  | Input & Output | true | `{ID, Created, Input: <posted>, Output: null}` |
  | Input & Output | false | `{Input: <posted>, Output: null}` — `ID`/`Created` gone, `Input`/`Output` kept |

**A no-task Endpoint can still have `PostInputSchema`/`PostInputMapping` populated, and
when it does, the platform *validates* the POST body against that schema before
storing** — confirmed live. This is a real, separate combination from the pure
"store-whatever-was-posted" behavior above (which only applies when `PostInputSchema` is
also left `null`): a value that fails to convert to its column's type, or a `null`/missing
value on an `AllowNull:false` column, gets rejected with a normal `400` even though
`*InputTaskCopyID` stays `null` and there's no Task involved at all. Don't assume a
no-task endpoint is automatically schema-less — check whether `PostInputSchema` is set.

**But validated raw storage still doesn't *reshape* the record to the schema's full
column set** — confirmed live: a nullable column simply omitted from the POST body stays
genuinely absent (`undefined`, not present as a key) in the stored/returned record, it is
**not** normalized to an explicit `null` the way a task-bound Endpoint's Step output is
(§8.5 — a Step's `OutputSchema` always yields every declared column, `null` for the ones
it didn't map). Same input, different result shape depending on which path it went
through — don't write a client/verification script that assumes a no-task record always
has every schema column present as a key.

### 8.2 Endpoint authentication — `AuthenticationType`

`DXEndpointAuthenticationType`:

| Value | Meaning |
|---|---|
| `0` `None` | Unsecured — every Endpoint in the worked example uses this. |
| `1` `Token` | Secured by a primary token and/or secondary endpoint tokens (below). |
| `2` `TokenInternal` | Secured by token, but the token isn't shown to the user in the UI. Not yet explored in this KB. |

At `AuthenticationType: 1`, **each HTTP verb gates independently** on two token kinds:

- **Primary token** — the verb's own `XxxToken` field (`GetToken`/`PostToken`/
  `PatchToken`/`PutToken`/`DeleteToken`), a plain string stored directly on the Endpoint.
- **Secondary tokens** — `XxxSecondaryTokens`, an array of **`CopyID` strings** (not
  wrapper objects) referencing entries in the top-level `SecondaryTokens[]` collection:
  `{"Description": "...", "Token": "...", "IsEnabled": true, "ID": 0, "Name": "...", "CopyID": "..."}`.
  Multiple Endpoints/verbs can reference the same `SecondaryTokens[]` entry.

Confirmed by hand-testing:

- Client sends the token as `Authorization: Bearer <token>`.
- **Alternative: the token can also be passed as `?access_token=<token>` on the query
  string** — works for both primary and secondary tokens, same as the header. **Not the
  preferred way to send it** (query strings end up in server access logs, browser
  history, proxies, etc.) — use the `Authorization` header unless there's a specific
  reason (e.g. a client that can't set custom headers) to fall back to this.
- Missing or wrong token → `403` (after a deliberate server-side delay, ~5s). If a test
  script fires several checks against a Token-secured endpoint, run them concurrently
  (`Promise.all`, not sequential `await`) — the delay is per-request, so awaiting one at a
  time multiplies it across every check.
- Correct token — **primary or a matching secondary, either one independently** — →
  `200`/`201`. A verb's primary and secondary token are two independent ways in, not a
  combined check.
- **Real Endpoints always have every verb's primary token field populated**, even on one
  whose intended access path is secondary-token auth — don't leave primary token fields
  `null` just because a test/Endpoint is "meant" to use secondary tokens.
- **`PostToken`/`SecondaryTokens[].Token` store the encrypted/at-rest value — NOT what the
  client sends.** The `Authorization` header needs the *decrypted/plaintext* counterpart
  instead; putting the same (encrypted) string in both places means every request gets
  `403`, including ones with the "right" token. There's no way to derive the plaintext
  from the encrypted value from within a transfer — get both from whoever generates the
  token (e.g. a paired `Label  base64Value` list where the label text turns out to be the
  plaintext), never assume one field's value doubles as both. A company under
  `projects/<name>/` may keep confirmed pairs in a gitignored secrets file — check there
  before asking the user to generate new ones. Do not commit token pools into this KB.

  **⚠️ `examples/generic_worked_example.json`'s Endpoint "03 Token-secured storage" uses
  one real pair from that self-test pool** (`rnE9TBvaDso=` encrypted / `Token 1`
  plaintext) instead of an inert placeholder, specifically to illustrate this gotcha
  end-to-end — flagged with an explicit `dxendpoint` `EntityComment` and in the
  `SecondaryTokens[]` entry's own `Description`. It is **not a safe secret** — it's
  publicly known the moment this file is read. Never reuse it (or copy this pattern with
  a *different* real credential) in a transfer meant for anything beyond illustration.

### 8.3 Endpoint URLs called from a script must not hardcode the company slug

`/api/endpoint/<company-slug>/<group-slug>/<endpoint-slug>` — the company slug is
**instance-specific**, not a fixed word. Use `${#SYSTEM_CompanySlug}` (paired with
`${#SYSTEM_BaseURL}` for the host), never a literal company name — a hardcoded slug
breaks the moment the transfer is imported into a different company/instance. Both are
system-provided template variables, substituted before the script runs; no `Variables[]`
entry needed.

### 8.4 Special "Endpoint ... Output" system schemas — raw response shaping

Assigning one of these six system schemas to an Endpoint's `GetOutputSchema`/`*OutputSchema`
replaces the normal wrapper with a raw, type-specific response. In the **default** case
the Step uses the **same** schema (see below); in rare exceptions (§8.4 exception) the Step
uses connector native output and `GetOutputMapping` bridges the gap. All
`Version: "1.0.0"`. Declare in `DataSchemas[]` via `{"Guid":...,"Version":...}` (§7).

**Default (most cases):** give the Step the **same** `OutputSchema` as the Endpoint's
`GetOutputSchema`/`*OutputSchema` — a special „Endpoint … Output“ schema — for a trivial
1:1 `GetOutputMapping`, e.g. `{"HTML": "MyStep.HTML"}`.

| Layer | Field | Schema |
|---|---|---|
| Step | `Steps[].OutputSchema` | Same as Endpoint — special „Endpoint … Output“ |
| Endpoint (GET) | `GetOutputSchema` | Special „Endpoint … Output“ for raw response |
| Mapping | `GetOutputMapping` | Trivial 1:1, e.g. `{"HTML": "MyStep.HTML"}` |

**Worked example (default wiring):** `examples/generic_worked_example.json` (§10) — Task
`03 Endpoint-triggered status`, Step `Return status`, Endpoint slug `status`: Step and
Endpoint share the same `OutputSchema` (**Text** `b76c3662…/1.0.0`) with `GetOutputMapping`
`{"Text": "Return status.Text"}`. Same-schema + mapping shape as the default above; for raw
response shaping with one of the six §8.4 special schemas, use that schema on **both** Step
and Endpoint instead of **Text**.

**Exception — connector native schema ≠ Endpoint special schema (rare).** Some connectors
produce a **different** output schema than the Endpoint special schema. The live-confirmed
case is **HTML Creator → Endpoint HTML Output**:

| Layer | Schema | Guid |
|---|---|---|
| Step | Connector native output (**HTML**, not Endpoint HTML Output) | `cc494d6c-6a55-48dc-b6bc-f8f65afca13e` / `1.0.0` |
| Endpoint (GET) | **Endpoint HTML Output** | `50619995-8af1-4692-a2ec-789bc44f7e17` / `1.0.0` |
| Bridge | `GetOutputMapping` | `{"HTML": "RenderPage.HTML"}` — column names match, Step referenced by name |

Minimal pattern (Step + Endpoint fragments):

```json
{
  "Steps": [{
    "Name": "RenderPage",
    "OutputSchema": { "Guid": "cc494d6c-6a55-48dc-b6bc-f8f65afca13e", "Version": "1.0.0" }
  }],
  "Endpoints": [{
    "GetOutputSchema": { "Guid": "50619995-8af1-4692-a2ec-789bc44f7e17", "Version": "1.0.0" },
    "GetOutputMapping": "{\"HTML\": \"RenderPage.HTML\"}",
    "GetOutputStepCopyID": "<RenderPage Step CopyID>"
  }]
}
```

Both schemas must appear in `DataSchemas[]` via `{"Guid":...,"Version":...}` (§7).

| Schema | Guid | Column(s) | Raw behavior |
|---|---|---|---|
| Endpoint HTML Output | `50619995-8af1-4692-a2ec-789bc44f7e17` | `HTML` (String) | `Content-Type: text/html`, body = string as-is. `*IsSystemResponse` ignored — always raw. |
| Endpoint XML Output | `5715560f-8fa5-4c4b-a3fd-edd3086fb767` | `XML` (String) | `Content-Type: application/xml`. Each row's `XML` wrapped in `<xml>`, concatenated, whole thing wrapped in `<root>`, `<?xml version="1.0" encoding="utf-8"?>` prepended. 2 rows `<item>1</item>`/`<item>2</item>` → `<root><xml><item>1</item></xml><xml><item>2</item></xml></root>`. No parsing/validation of the `XML` content itself. |
| Endpoint XML (single) Output | `f8c963d4-4d56-4f88-8014-6f89f5228bc4` | `XML` (String) | 1 row → unwrapped passthrough, no `<root>`, no declaration. >1 row → only first used (server-side warning, not visible to caller). |
| Endpoint JSON Output | `2251633e-1656-4fc7-8296-3cea0fd49f2a` | `JSON` (JSON) | >1 row → bare JSON array, not wrapped. |
| Endpoint JSON (single) Output | `35272974-b751-44bd-b11f-871b245d2536` | `JSON` (JSON) | 1 row → value returned directly. >1 row → only first used. |
| Endpoint File Output | `b70a4ab3-a58f-4249-b752-44852c115a29` | `Name` (String), `Data` (Base64) | Real file download: `Content-Disposition: attachment; filename=<Name>`, `Content-Type` from extension, body = decoded `Data`. >1 row → only first used. **GET-only** — status `200`, toggle ignored. DELETE/POST/PUT/PATCH: falls back to ordinary schema behavior — raw array of `{Name,Data}` with `Data` still base64-encoded (not decoded) / wrapped `{ID,Status,...}`, no special rendering. |

**Wrapper-replacement scope: GET-only, no-task endpoints (§8.1) only** — that flavor has
no POST/PATCH/PUT equivalent of the `{ID, Created, Data:...}` wrapper. Task-bound
POST/PUT/PATCH (§8.5) are affected too, separately, below.

**Task-bound POST/PUT/PATCH (§8.5):** `Content-Type` and wrapper body follow the schema
on every response (Sync+On/Async+On included), e.g.
`<response><id>..</id>...<result>...</result></response>` instead of a JSON object.

**Confirmed bug — `Async+Off` ≠ §8.5 table**, when `*OutputSchema` is populated on the
async endpoint (against §8.5's own advice to leave it `null`). Confirmed on
POST/PUT/PATCH, v16, `self-test.integray.app`, identically across verbs:

| Schema | `Async+Off` body |
|---|---|
| Endpoint XML (single) Output | completely empty — 0 bytes, not even an XML declaration |
| Endpoint XML Output | `<?xml version="1.0" encoding="utf-8"?><root />` — declaration still present |
| Endpoint JSON Output | bare `null` — **not** `[]`, despite the schema's normal shape being a bare array |
| Endpoint JSON (single) Output | bare `null`, same as Endpoint JSON Output |
| Endpoint HTML Output | `500` on both `Async+On` and `Async+Off` — see bug note below |
| Endpoint File Output | no anomaly — special renderer never engages outside GET |

`Async+On` still returns the documented wrapper; `Result` is the schema's own empty
form (`<result/>` / `null`).

**Root cause:** anomaly occurs only when `*OutputSchema` is populated on an async
endpoint. `*OutputSchema: null` (§8.5's recommendation) → `Async+Off` matches the table
exactly, normal `application/json` wrapper. Ordinary custom/JSON output schemas are
unaffected.

**GET/DELETE `*IsSystemResponse` toggle** (no async dimension — `GetIsAsync`/
`DeleteIsAsync` don't exist). Confirmed on XML (single), XML, JSON, JSON (single):

| `*IsSystemResponse` | Shape |
|---|---|
| `false` | raw passthrough (table above) |
| `true` | `<response><id>..</id><status>FinishedSuccess</status><link>..</link><messages/><result>...</result></response>` — schema-rendered `{ID,Status,Link,Message,Result}`, `result` = the schema's normal output as-is (e.g. for Endpoint XML Output, the full `<root>...</root>` nested inside `<result>`), `status` always `FinishedSuccess` |

No anomaly (no async branch). File Output excluded: GET = file-download (toggle
ignored), DELETE = ordinary-schema fallback (toggle works normally). **Not
special-schema-specific** — ordinary/custom output schemas have this same GET/DELETE
`false`=raw/`true`=wrapped toggle too (previously undocumented anywhere in this KB set
beyond a bare test count in a company's own notes).

**Confirmed bug — Endpoint HTML Output + Async → `500`.** Task-bound async
POST/PUT/PATCH: `500 Internal Server Error`, empty body, on both `Async+On` and
`Async+Off`. Sync (on/off, both raw) works fine. Expected: fall back to an ordinary
schema's async response (bare `{ID,...}` or `Status:"Scheduled"` envelope) — getting
`500` instead confirms a platform bug, not a doc gap. Untested: whether
`*OutputSchema: null` on async avoids the crash.

### 8.5 Task-bound POST/PATCH/PUT — request input mapping, response output mapping

Unlike the no-task endpoints (§8.1), a `*InputTaskCopyID`-bound Endpoint turns the
request itself into the Task's effective input, via two Endpoint-level fields per verb
(`PostInputSchema`/`PostInputMapping`, and analogously for `Patch`/`Put`):

- `*InputSchema` — the schema shape the mapped request data will have (system, custom,
  flat, or complex — any `DataSchemas[]` entry works, same as anywhere else).
- `*InputMapping` — a JSON string `{"ColumnName": "<placeholder>"}`. Placeholders:

  | Placeholder | Resolves to |
  |---|---|
  | `${body}` | entire parsed JSON request body |
  | `${headers}` | all request headers, serialized into one JSON object |
  | `${bodyBase64}` | entire parsed JSON body, Base64-encoded |
  | `${fixed:<value>}` | a predefined constant |
  | `<token_name>` | a top-level request-body property, by name |
  | `<token_name>.<nested_token_name>` | a nested request-body property, dotted path |
  | `$.<JSONPath_expression>` | a JSONPath expression into the request body |

**Gotcha — the bound Task's first Step still needs its own
`InputSchemaMapping`, and it must address the Endpoint by name.** Treat the Endpoint as
an implicit **"step zero"** in the `docs/entities/data-addressing.md` addressing tree: it deposits
its `*InputMapping`-populated data at the tree root under **its own `Name`**, exactly
like any Step would under its own name. The bound Step must therefore set
`InputSchemaMapping: {"ColumnName": "<Endpoint Name>.ColumnName"}` — leaving
`InputSchemaMapping: null` doesn't magically inherit the Endpoint-level mapping; it just
leaves every `AllowNull:false` column unmapped, producing the ordinary **"Incorrect
Mapping"** error from §7. (The Endpoint's own `*InputMapping` and the Step's
`InputSchemaMapping` are two separate, both-required layers — easy to assume the first
makes the second redundant, per this exact mistake.)

**Knock-on consequence for that Step's own output address.** Once the Step has a real
`InputSchema` + `InputSchemaMapping` (and isn't Bulk / doesn't have `AdditionalInputs`),
`docs/entities/data-addressing.md` Rule 2's reset-to-root no longer applies to it — Rule 1 does, so
the Step nests **under the Endpoint's node**: its own output is addressed as
`<Endpoint Name>.<Step Name>.<Column>` (3 segments), not just `<Step Name>.<Column>` (2
segments) like a Bulk/no-mapping root step would be. Any later reference to this Step's
output — including this same Endpoint's own `*OutputMapping`, if it reads from this
Step — must use the full 3-segment path.

**Response shaping (output side):** `*OutputSchema`/`*OutputMapping`/`*OutputStepCopyID`
work the same way as `GetOutputSchema`/`GetOutputMapping`/`GetOutputStepCopyID` (§8) — map
the bound Step's real output columns into the declared response schema.
`*IsAsync`/`*IsSystemResponse` control whether the caller waits and whether the response
is wrapped, confirmed against a real instance:

| Sync/Async | System data | Shape |
|---|---|---|
| Sync | On | `{ID, Status:"FinishedSuccess", Link, Message, Result:[...]}` |
| Sync | Off | bare array/value — no wrapper at all |
| Async | On | `{ID, Status:"Scheduled", Link, Message:null, Result:null}`, returned immediately, no waiting |
| Async | Off | **same wrapped shape as Async+On**, NOT bare † |

The system-data toggle only strips the wrapper on the **sync** path — async has no real
result yet at response time, so there's nothing to unwrap; it always returns the metadata
wrapper regardless of the toggle.

† **Exception (§8.4):** when `*OutputSchema` is one of §8.4's six special schemas and is
(against the advice just below) still populated on the async endpoint, this row doesn't
hold — response is the schema's own empty rendering instead (varies per schema, see
§8.4) or `500` for HTML Output. Not known to affect ordinary custom/JSON output schemas.

**When `*IsAsync: true`, leave `*OutputSchema`/`*OutputMapping`/`*OutputStepCopyID` all
`null`.** The immediate async response is always the fixed `Status:"Scheduled"` shape
above — `Result` is always `null` regardless of what the output mapping says, since the
task hasn't finished yet. Defining them anyway does nothing useful and produces an
import-time warning: `"Output from POST endpoint <Name> is defined, but no data will be
returned; processing is set to asynchronous."` (confirmed against a real
instance) — and, if the schema is one of §8.4's six special schemas, also the empty-body
anomaly above (†). Only set `*OutputSchema`/`*OutputMapping`/`*OutputStepCopyID` when
`*IsAsync: false`.

### 8.6 Publish-time errors — cheat-sheet

Central reference for errors that surface during **Process with `publish: true`** (or
standalone `POST .../Publish`). Import may succeed while publish fails — see
`docs/transfer/remote-api.md` (HTTP 422). After a failed publish the configuration is
**already applied** on the instance; fix the transfer and run Process/Publish again.

| Code / symptom | Typical cause | Where to look |
|---|---|---|
| `CACHE_BINDING_GET_TASK_NOT_EXECUTABLE` | Step has an Endpoint special schema instead of connector native output (typical: HTML Creator + Endpoint HTML Output); **or** a required column is missing from a step's `InputSchemaMapping`/`AdditionalInputs` mapping somewhere upstream of `GetOutputStepCopyID` | §8.4 exception, `data/connectors.json`; §7 mapping-coverage script |
| `configurations … invalid variable Code` | `${#Code}` in a Configuration without a matching `Variables[]` entry | `docs/entities/variables.md` |
| Step `Name` contains `.` | Publish fails for the whole Endpoint | §2.1 |
| HTTP 422 + `publishResult.messages[]` | Import OK, publish failed — inspect messages | `docs/transfer/remote-api.md` |

---

## 9. `EntityComments` — commenting on entities

Only **5 entity types** support comments, matched by their DB table name (not the JSON
collection name):

| Entity | `EntityName` value |
|---|---|
| Task | `dxtask` |
| Step (TaskStep) | `dxtaskstep` |
| Configuration | `dxconfiguration` |
| Endpoint | `dxendpoint` |
| DataSchema | `dxschema` |

```json
{
  "EntityName": "dxtask",
  "EntityCopyID": "<CopyID of the commented entity, must exist in this transfer>",
  "CommentData": "<p>Rich text HTML - <strong>bold</strong>, <u>underline</u>, etc.</p>",
  "CreatedByName": "Integray",
  "ModifiedByName": "Integray"
}
```

- No own `ID`/`CopyID` on the comment itself — matched purely by the
  `(EntityName, EntityCopyID)` pair on import. Only one comment observed per entity in
  practice; behavior with more than one entry for the same pair is unconfirmed.
- `EntityCopyID` must reference an entity actually present in the same transfer (same
  rule as every other `*CopyID` cross-reference in this format).
- `CommentData` is raw HTML from a WYSIWYG editor, not plain text — `<p>`, `<strong>`,
  `<u>`, `&nbsp;` confirmed working; treat it as free-form rich text, not markdown.
- `CreatedByName`/`ModifiedByName` are plain display-name strings (not validated or
  remapped like a `*CopyID` reference) — safe to set to `"Integray"` or ask the user.
- This is otherwise undocumented — every other example transfer in this KB carries
  `"EntityComments": []`. Confirmed structure comes from a real exported transfer, not
  from an official schema.

---

## 10. Worked example

`examples/generic_worked_example.json` is a complete, generic Config Transfer covering
the main constructs: one Task per `Type` (Scheduled/OnDemand/Endpoint), a multi-branch
fan-in merge (root `Split` → parallel branches → `Merge results`, demonstrating
`docs/entities/data-addressing.md` Rules 1/2/3/4), `InputDataFilter`, a `Type:7`/`ComplexType`
column, a system schema reference, `EntityComments`, and Endpoints covering
`AuthenticationType` 0 and 1 (task-bound, no-task/raw-storage, and token-secured — token
values are placeholders, not real credentials). **Not validated against a live
Integray instance** (unlike a company's live transfer under `projects/<name>/`, if present) —
built from patterns already confirmed elsewhere in this KB, but treat it as illustrative
of shape/syntax, not as proof the exact combination works end-to-end.

If `projects/<name>/` has a live-validated Config Transfer, check that too when unsure
about a company-specific detail. That tree is not KB content.

---

## 11. Pre-generation checklist

1. **Ask the user** which Tasks/Steps/Endpoints should exist, and the transfer `Name`.
2. **Per connector:** look up `Guid`+`Version` in `data/connectors.json` (newest version unless the user specifies otherwise).
3. **Per Configuration:** follow the action's `configurationRefs[]` from `data/connectors.json` into `data/configuration-schemas.json`, generate a `Configuration` JSON string satisfying every `required` field unless `docs/entities/configuration-overrides.md` documents a known override for that schema.
4. **Per DataSchema:** decide system (Guid+Version, look up in the worked example) vs. custom (new CopyID).
5. **Build Steps:** `PrevStepCopyID` for temporal order, `AdditionalInputs` for cross-branch data deps, `InputSchemaMapping` per `docs/entities/data-addressing.md`.
6. **Endpoints:** set `*InputTaskCopyID`/`*OutputStepCopyID` where relevant.
7. **Fill top-level metadata** per §3.
8. **Validate:**
   - Every `*CopyID` reference resolves to an entity actually present in the transfer.
   - No system schema referenced via CopyID instead of Guid+Version (or vice versa).
   - `Configuration` JSON strings contain every `required` field (unless `docs/entities/configuration-overrides.md` documents a known override for that schema).
   - Top-level `Configurations[]`: field is **`Configuration`**, not `ConfigurationData` (§5).
   - Each Configuration has `IsShared` + `TaskCopyID`/`TemplateCopyID` per §5.
   - Endpoint GET with raw HTML: generally Step and Endpoint share the same special schema (§8.4 default).
   - HTML Creator exception: Step `OutputSchema` = connector native HTML (`cc494d6c…`); Endpoint `GetOutputSchema` = Endpoint HTML Output (`50619995…`); mapping `{"HTML": "StepName.HTML"}` (§8.4).
   - `AgentCopyID` on Steps is either the Shared-agent constant or a real `Agents[]` entry.
   - `ErrorBehavior` matches intent (§6.1) — for parallel branches that feed a merge (typical self-test pattern), consider `FailStepAndContinue`/`FailTaskAndContinue` so one branch's failure doesn't strand the merge.
   - `Task.Type`: `2` only with a real bound Endpoint; `0` only for a genuinely intended schedule; otherwise `1`.
   - `Cron`: `null` unless `Type: 0` — never copy it from another task without checking `Type` first.
   - Exactly one `PrevStepCopyID: null` per task (see `docs/entities/data-addressing.md`) — multi-branch tasks need one shared root step, not one `null` per branch.
   - `InputSchemaMapping`/`AdditionalInputs` cover every `AllowNull: false` column of the target `InputSchema` (§7 — run the mapping-coverage script there, don't just eyeball it), and every mapped pair has the same `Type` (and `ComplexType` for tables) as the source column (`docs/entities/data-addressing.md`) — name match is not enough. On a GET-bound task, a missed required column can surface only at publish time as `CACHE_BINDING_GET_TASK_NOT_EXECUTABLE`, not as "Incorrect Mapping" at import (§7).
   - Cloned Endpoints: `*OutputMapping` points at a step that exists, by name, in the new task (§8).
   - Endpoints with `AuthenticationType:1`: every primary `XxxToken` field populated (§8.2), and every `XxxSecondaryTokens` CopyID resolves to an entry actually present in `SecondaryTokens[]`.
   - No `.` in any Task/Step/Endpoint/TaskGroup/EndpointGroup `Name`, and `Name`/`Slug` lengths respect §2.1's `varchar` limits.
   - `ID` genuinely unique across DataSchemas/Configurations/Tasks/Steps/Step-level Configuration entries/Variables (§2) — in particular, no Step-level Configuration entry sharing its `ID` with the top-level Configuration it points at.
9. **Flag to the user** if the transfer uses a connector whose latest version isn't confidently covered by `data/connectors.json` — recommend verifying against the target instance.
