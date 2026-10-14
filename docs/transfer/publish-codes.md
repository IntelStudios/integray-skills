# Publish result codes

Companion to [config-transfer-format.md](config-transfer-format.md) §8.6 and
[remote-api.md](remote-api.md). Codes in `publishResult.messages[].code` after Process
with `publish: true`.

`isSuccess` is `true` exactly when `status` is `Published` (HTTP **200**). Otherwise
HTTP **422** and `Failed`. An Error in `messages` does **not** by itself flip
`isSuccess`. The run goes `Failed` only when a code below says so, or when every Task
and Endpoint was skipped and nothing remains to publish.

`CACHE_PUBLISH_SUCCESS*` / `CACHE_PUBLISH_FAILED_*` go to `description`, not `messages`.

| Outcome | HTTP | `isSuccess` | `status` |
|---|---|---|---|
| A code marks the rebuild `Failed` | 422 | false | Failed |
| Error skipped a Task or Endpoint, at least one remains | 200 | true | Published |
| After skips, zero Tasks and zero Endpoints | 422 | false | Failed |
| Warning only | 200 | true | Published |

Skipped Endpoint: that method is **not in the cache** → caller **404**. Live-confirmed
on `CACHE_BINDING_POST_TASK_NOT_EXECUTABLE`. Binding is not attempted when the method’s
`TaskID` is null (no code). On bind Error the Endpoint is dropped; only Tasks linked via
`PostInputTaskID` / `GetInputTaskID` are removed with it.

---

## `CACHE_BINDING_{VERB}_*`

Same suffix, same meaning. `{VERB}` is the Endpoint method.

| Suffix | Type | When |
|---|---|---|
| `TASK_NOT_FOUND` | Error | Bound Task is not in the set being built (`GetTaskAsync` → null) |
| `TASK_DEACTIVATED` | Error | Bound Task `IsActive == false` (skipped when loading a snapshot; Process reads the DB, so this applies) |
| `INCORRECT_INPUT_MAPPING` | Error | Task `Executability == IncorrectEndpointInputMapping` |
| `INCORRECT_OUTPUT_MAPPING` | Error | Task `Executability == IncorrectEndpointOutputMapping` |
| `TASK_NOT_EXECUTABLE` | Error | `Executability` is not `Executable` and not the two mapping states. Bucket for step mapping / missing steps, schemas, configuration — or §8.4 special-schema mismatch (typical HTML Creator + Endpoint HTML Output). Message does not name the Step. Check coverage ([config-transfer-format.md](config-transfer-format.md) §7) |
| `TASK_NOT_RUNNABLE` | Warning | Task is executable and `IsRunnable == false`. Bind **continues**, Endpoint stays. No warning when loading a snapshot |
| `INPUT_SCHEMA_NOT_FOUND` | Error | Method `InputSchemaID` set; load throws or returns null |
| `OUTPUT_SCHEMA_NOT_FOUND` | Error | Method `OutputSchemaID` set; load throws or returns null |
| `PARSING_INPUT_MAPPING_FAILED` | Error | Placeholder substitution in `*InputMapping` throws. Inner reason: unconfirmed |

Also per verb (not `CACHE_BINDING_*`):

| Code | Type | When |
|---|---|---|
| `CACHE_SETTING_{VERB}_TASK_DETAILS_FAILED` | Error | `SetEndpointDetailsAsync` throws. Inner reason: unconfirmed |
| `CACHE_PARSING_{VERB}_FAIL_MESSAGE_FAILED` | Error | Custom fail-message parse throws |
| `CACHE_PARSING_{VERB}_SEARCH_STRINGS_FAILED` | Error | Search-string path build throws |

POST + `PostIsAsync: true` only — Warning, Endpoint stays:

| Code | When |
|---|---|
| `CACHE_POST_ASYNC_OUTPUT_DEFINED` | Both `PostOutputSchemaID` and `PostOutputStepID` set |
| `CACHE_POST_ASYNC_OUTPUT_SCHEMA_DEFINED` | Only `PostOutputSchemaID` |
| `CACHE_POST_ASYNC_OUTPUT_STEP_DEFINED` | Only `PostOutputStepID` |

Leave those three null on async POST ([config-transfer-format.md](config-transfer-format.md) §8.5).

---

## Bind / Task without a verb

| Code | Type | When | Rebuild |
|---|---|---|---|
| `CACHE_BINDING_TASK_FAILED` | Error | Uncaught exception while binding one Endpoint | Skip Endpoint |
| `CACHE_BINDING_TASKS_TO_ENDPOINTS_FAILED` | Error | Exception escapes the whole bind (not one Endpoint) | 422 Failed |
| `CACHE_TASK_NOT_EXECUTABLE` | Error | Active Task is not `Executable` and is **not** bound via `PostInputTaskID` / `GetInputTaskID`. A Task bound **only** via PUT, PATCH, or DELETE gets this too. GET/POST-bound Tasks get `CACHE_BINDING_{VERB}_*` instead | Skip Task |
| `CACHE_TASK_NOT_RUNNABLE` | Warning | Executable, `IsRunnable == false`, not GET/POST-bound. Task is still built | 200 unless something else fails |

---

## Fix the transfer

These skip the Task (Published if anything else remains):

| Code | When |
|---|---|
| `CACHE_FORBIDDEN_CONNETOR_USAGE` | Connector not allowed on the chosen agent (`AllowedSharedAgent` / `AllowedRemoteAgent`). Spelling `CONNETOR` is the real code |
| `CACHE_PLUGIN_BINARIES_DOWNLOAD_FAILED` | Connector/plugin/binary missing or download failed. Skipped when rebuilding from a snapshot |
| `C_LOADING_CACHE_MODELS_FAILED` | Loading step configurations for the Task threw |
| `CACHE_FILLING_STEP_CONFIGURATIONS_FAILED` | Step configuration JSON / placeholders threw (other than invalid variable) |
| `CACHE_FILLING_STEP_CONFIGURATION_APPLY_VARIABLE_FAILED` | `${#Code}` with no matching `Variables[]` `Code` ([variables.md](../entities/variables.md)) |
| `CACHE_INVALID_COMPANY_REFERENCE` | Integray Endpoint / Start Task: company in configuration is null, or target company inactive (DB publish) |
| `CACHE_INVALID_TASK_REFERENCE` | Start Task: target Task null or inactive (inactive not checked from a snapshot) |
| `CACHE_INVALID_ENDPOINT_REFERENCE` | Endpoint null or inactive. Cross-company: if the target snapshot has the Endpoint, this is not raised |
| `CACHE_INVALID_AUTH_CONNECTION_REFERENCE` | OAuth connection selected and null/inactive. Empty selection is skipped |
| `T_ADDITIONAL_INPUTS_CIRCULAR_DEPENDENCY` | Step graph (AdditionalInputs + previous Step) does not visit every Step |
| `CACHE_CREATING_MODEL_FAILED` | Task cache model threw something other than the rows above |
| `CACHE_CREATING_ENDPOINT_FAILED` | Endpoint cache model threw (group, company, extended info, token decrypt) |

Cross-company Warning (step still publishes from the live DB):
`CACHE_ENDPOINT_NOT_IN_PUBLISHED_CACHE`.

---

## Rebuild stops (`Failed` / 422)

| Code | When |
|---|---|
| `O_SWITCH_OFF_FAILED` | Orchestrator off before publish returned failure |
| `CACHE_REBUILD_CANCELED_TASKS_NOT_FINISHED` | Running Tasks did not finish in 30 s |
| `CACHE_REBUILDING_FAILED_SWITCHING_ORCHESTRATORS_FAILED` | Any exception from the rebuild body (including agent-status check). Often paired with `CACHE_CHECKING_AGENT_STATUSES_FAILED` |
| `CACHE_LOADING_ENDPOINTS_FAILED` / `CACHE_LOADING_TASKS_FAILED` / `CACHE_LOADING_SCHEMAS_FAILED` | Load of that collection threw |
| `CACHE_GETTING_SPECIAL_SCHEMAS_FAILED` | Load of Endpoint special output schemas (§8.4) threw |
| `CACHE_NOTHING_TO_PUBLISH` | Zero Tasks and Endpoints after build, and `messages` was still empty. If messages already exist, this code is omitted; status is still Failed |

`O_SWITCH_ON_FAILED` — orchestrator on after rebuild threw. Does **not** flip status;
if the rebuild itself succeeded, stays **200 Published**.

`CACHE_FILL_VARIABLE_SCHEMAS_FAILED` / `CACHE_CHECKING_OUTPUT_REQUIRED_FAILED` —
Error, Task **stays**, rebuild does not fail by itself.

---

## Warnings (entity stays)

| Code | When |
|---|---|
| `CACHE_REMOTE_AGENT_OFFLINE` | Step `AgentID > 0` and agent offline. Skipped when loading a snapshot |
| `CACHE_COMPUTING_TIMEOUT_FAILED` | Task timeout computation threw |
| `CACHE_COMPUTING_SNAPSHOT_TRIM_SCHEMA_FAILED` | Nested Step with snapshot ≠ Never; trim schema threw |
| `CACHE_BUILDING_SNAPSHOT_COLUMN_METADATA_FAILED` | Snapshot column metadata threw |

---

## After a successful rebuild

Cache add/clear/reschedule threw, or `TryAdd*` / `TryRemove*` returned false. Status
stays Published if the rebuild itself passed: `CACHE_GETTING_TASKS_TO_CLEAR_FAILED`,
`CACHE_CLEARING_TASK_FAILED`, `CACHE_GETTING_ENDPOINT_TO_CLEAR_BY_ID_FAILED`,
`CACHE_CLEARING_ENDPOINT_BY_ID_FAILED`, `CACHE_GETTING_ENDPOINT_TO_CLEAR_BY_SLUG_FAILED`,
`CACHE_CLEARING_ENDPOINT_BY_SLUG_FAILED`, `CACHE_ADDING_TASK_FAILED`,
`CACHE_ADDING_ENDPOINT_BY_ID_FAILED`, `CACHE_ADDING_ENDPOINT_BY_SLUG_FAILED`,
`CACHE_REBUILDING_SECONDARY_TOKENS_FAILED`, `CACHE_RESCHEDULING_TASKS_FAILED`.

---

## Not in `messages`

Constants exist in the product catalog but the publish path does not emit them:
`CACHE_BINDING_{VERB}_TASK_FAILED`, `CACHE_BINDING_{VERB}_UNKNOWN_TASK_FAILED`,
`CACHE_FILLING_POST_ENDPOINT_DETAILS_FAILED`, `CACHE_PUBLISH_CHANNEL_UNAVAILABLE`,
`CACHE_REFRESHING_LICENSE_FAILED`, `CACHE_SETTING_LAST_REFRESH_FAILED`,
`CACHE_REBUILDING`, `CACHE_REBUILDING_FAILED`, `CACHE_LOADING_FROM_DB_FAILED`,
`CACHE_ADDITIONAL_INPUT_SCHEMA_NOT_DEFINED`, `CACHE_ADDITIONAL_INPUT_SCHEMA_NOT_FOUND`.
