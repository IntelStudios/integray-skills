# Remote debugger

Run one connector that is already installed on this runtime. The caller sends the
action, tables, schemas, and configurations in one request and gets the output,
logs, and checkpoint in the same response.

The company configuration is left unchanged: no task, step, task run, schema,
variable, connector storage, or publish. A saved task is still
`POST /api/Remote/{companySlug}/Task/{id}/Start`
([remote-api.md](remote-api.md)). The administration UI debugger loads a saved
step; this call does not.

**Version floor:** [instance-version.md](../instance-version.md) Feature availability
(`rel-2025-03.018`). On an older line the path is absent (HTTP 404, empty body).
Other Remote API paths on `017` still work.

Check `productLine` before calling. Call it only when `permission` is `full`.
`read-only` and `read-write` must not call it. It runs the connector, which can
call systems outside the company.

## When to call

Call `Debugger/Run` when the question is what one installed action returns for a
given input table and configuration: a statement, a configuration field, a
checkpoint, or a `${#Code}` substitution.

Whether that call happens is a **`debugger-connector:`** line in this company's
`projects/<name>/conventions.md` (`## Debugger`). One line per connector guid,
not per version. A test company and a production company keep separate lists.
There is no machine-wide switch. The company repo root `README.md` points at
that section.

| Line for this guid | What to do |
| --- | --- |
| `always` | Call on any agent. Say the connector, which agent this run uses, and any write outside the company (mail, ERP, data box, HTTP with a side effect) in the same turn, then call. |
| `never` | Do not call this connector. |
| no line | Stop and ask once: may the agent run this connector in the debugger **in this company**, on any agent? Name any outside write. Do not ask per agent. Yes appends `debugger-connector: <guid> always` under `## Debugger` in this company's `conventions.md`. No appends `never`. |

An explicit request runs this once and does not add or change a line. The line does not override
the version floor, a `permission` other than `full`, or the connector restriction (a Shared-only
connector still cannot run on a remote agent).

A task, an endpoint, mapping between steps, publish, and Full Sync stay on the
transfer. This call does not show them. A successful run is not saved in the
company.

Before building the body, print the catalog card. It does not call this API:

```bash
python scripts/connector-info.py <connector-guid>
```

Live spec: `{baseUrl}/api-docs/remote/swagger.json` (tag Debugger, summary
`Run debugger`). UI: `{baseUrl}/apidocs/remote-api`.

## Endpoint

```http
POST /api/Remote/{companySlug}/Debugger/Run
Authorization: Bearer {remoteControlToken}
Content-Type: application/json
```

`{companySlug}` is the company slug. `{remoteControlToken}` is that company's
remote control token.

Envelope properties are camelCase (`connectorGuid`, `output`, `logs`). Inside a
data table and a schema, names stay PascalCase (`Schema`, `Rows`, `HasDefinedRows`,
`Name`, `Columns`). Enum values are integers.

The connector, action schemas, and configuration schemas in the body must be the
ones installed on that runtime. Guids in the examples below are illustrations.

## Request

| Property | Required | Meaning |
| --- | --- | --- |
| `connectorGuid` | yes | Guid of a connector installed on this runtime. |
| `connectorVersion` | yes | Its version, `major.minor.patch` (for example `1.2.3`). |
| `actionCode` | when the connector has more than one action | Action to run. One stored action, including a synthetic `defaultAction`, is used when the code is omitted. No stored actions: omit the code; schema and configuration rules then come from the connector. |
| `agentId` | no | Omit or `-1` for the Shared agent. A positive id is a connected remote agent of this company. |
| `timeout` | no | Seconds the connector may run. Omit or JSON null for 60. `0` and negative values are rejected. There is no upper bound. The HTTP call can return a few seconds after the connector is cancelled; allow about 10 seconds beyond `timeout` on the client. |
| `logFilter` | no | Which log lines come back. Omit for connector lines at Info, Warning, and Error. |
| `input` | depends on the action | Input data table. |
| `additionalInputs` | no | Further input tables. A non-empty list is allowed only when the action has multiple inputs. |
| `outputSchema` | depends on the action | Output schema only. No rows. |
| `localVariables` | no | Step local variables, as a data table. The connector can read them. They are not company variables and they are not returned. |
| `companyVariablesOverride` | no | Map of a company variable code to a value. Where configuration JSON contains `${#Code}`, this value is used. A code that is not listed is still read from the company. |
| `checkpoint` | no | Checkpoint string. Allowed only when the action has a checkpoint. |
| `configurations` | yes | One configuration for every configuration schema of the action. `[]`, or omitting the property, when that set is empty. |

### Agent

| `agentId` | Where it runs |
| --- | --- |
| omitted or `-1` | Shared agent. It is not looked up in the company. |
| a positive id | That remote agent. It must belong to this company and be connected now. |
| `0` or any other non-positive id | Rejected. |

An agent of another company gets the same message as an unknown id. The response
does not say that the agent exists.

The connector restriction is checked for the agent that will run, before schema
and configuration checks:

- Shared is allowed only when the restriction allows the Shared agent.
- A remote agent is allowed only when the restriction allows remote agents.
- If the restriction cannot be loaded, only a remote agent is allowed.

### Input process type

The request does not choose bulk, row by row, or parallel. The action does.

- Exactly one allowed type: that type is used.
- More than one: the action's `DefaultProcessType` is used, when it is one of the allowed types.
- Otherwise the call is rejected and the connector does not run.

| Stored value | What the connector receives |
| --- | --- |
| `Bulk` | The whole input table at once. |
| `RowByRowSequentially` | One row at a time, in order. |
| `RowByRowInParallel` | One row at a time. This call uses one thread. |

A connector with no actions stores the same names in `InputProcessTypeList`.
On a saved task step these are the same three process types
([data-addressing.md](../entities/data-addressing.md)).

### Schema rules

`None`, `Optional`, `Mandatory`, and `Required` apply to the primary `input` and
to `outputSchema` only. When the connector has no actions, the same rules come
from the connector.

| Schema type | What to send |
| --- | --- |
| None | Do not send it. For input, omit `input`. For output, omit `outputSchema`. |
| Optional | May be omitted. A sent table must parse. It is not compared with a predefined schema. |
| Mandatory | Must be sent and must parse. It is not compared with a predefined schema. |
| Required | Fixed by the action. Omit it and the runtime uses the predefined schema: an input table with that schema and no rows, or the output schema alone. A sent schema must match the predefined one (name, guid, version, and columns). |

An omitted Required input is a table with `HasDefinedRows` true and `Rows` empty.
That is different from `HasDefinedRows` false, which means the caller sent a table
with no defined rows. Rows sent on a matching Required schema are kept. Omitting
`outputSchema` on a Required output stores the schema only. The request has no
output rows.

`Guid` and `Version` on a schema may be omitted when the schema has no identity.
A Required schema must include them.

### Additional inputs

`additionalInputs` is not a second copy of `input`.

| What was sent | Result |
| --- | --- |
| property omitted, JSON null, or `[]` | No additional inputs. Allowed even when the action has only one input. |
| one or more items, and the action does not have multiple inputs | Rejected. The connector does not run. |
| a JSON `null` item | An empty slot at that index. That slot needs no schema. |
| an object | A data table. `Schema` is required. `Rows` must parse. The schema is not compared with a predefined schema. |

Order is kept. The first item is the connector's first additional input, not the
primary input. The list is not returned.

### Configurations

`configurations` is exactly the set linked to the selected action (or to the
connector, when it has no actions). Each entry:

| Property | Meaning |
| --- | --- |
| `guid` | Configuration schema guid. |
| `version` | That schema's version. It must match the installed schema exactly. |
| `configuration` | A JSON string. Objects, arrays, and other JSON values are accepted. |

Every linked schema appears once. An extra configuration, or the same guid and
version twice, is rejected.

`${#Code}` inside `configuration` is replaced before the connector runs. A code
listed in `companyVariablesOverride` uses the request value. Otherwise the code
is an active company variable with no template, or a system variable
(`SYSTEM_CompanyID`, `SYSTEM_BaseURL`, `SYSTEM_CompanySlug`, `SYSTEM_CompanyName`).
A template-scoped variable is not used. A code that matches none of these is
rejected and the connector does not run. Several missing codes are listed in one
message.

When the schema has an OAuth select, put the auth connection id in the property
the widget uses. The runtime writes that connection's `TokenResponse` into the
configuration. The connection must be an active auth connection of this company
with no template. If the id is missing or is not one of those connections, the
JSON is left as sent and the call is not rejected for that reason.

The response does not include the configuration after substitution, OAuth, or
`ServiceUrl` were applied. The connector receives that filled string.

Two configuration schemas get `ServiceUrl` when the JSON is an object and
`ServiceUrl` is missing or blank:

| Configuration schema | Filled from the runtime |
| --- | --- |
| Node.js Statement `b0b15d2d-cc48-4dcf-9714-0e11eb98b3e5` | Node.js service address |
| Python Statement `49e63f7b-4d8d-4891-9a0e-e2f9305bff30` | Python service address |

A `ServiceUrl` the caller already set is kept. If the runtime has no address,
the JSON is unchanged and the connector fails during the run.

Node.js processor (`5a70dfd2-9803-4bcf-b090-652b156f7236`) uses the Node.js
Statement schema. Its input is optional and its output is mandatory, so
`outputSchema` must be sent. The statement returns an array. A system log line
`Error occurred while initializing v2 plugin wrapper` means the plugin did not
load; it appears in `logs` only when `includeSystem` is true.

### Checkpoint

Send `checkpoint` only when the action has a checkpoint. The string is that
connector's stored JSON. Look it up before sending one:

```bash
python scripts/checkpoint-example.py <connector-guid>
```

Missing, null, or `""` means there is no previous checkpoint. A non-empty
checkpoint on an action that has none is rejected.

The response `checkpoint` is the value after the run, and only when the connector
changed it. Unchanged is null, not a copy of the string that was sent. `""` in
the response means the connector cleared it.

### Log filter

The connector still logs. `logFilter` only chooses which lines are copied into
`logs`.

| Property | Meaning |
| --- | --- |
| `includeSystem` | `false` (default): lines the connector wrote. `true`: also agent and runtime lines, still limited to `levels`. |
| `levels` | 0 Trace, 1 Debug, 2 Info, 3 Warning, 4 Error, 5 Fatal. Omit the list for Info, Warning, and Error (`2`, `3`, `4`). An empty list returns `logs: []`. |

A connector line is any line that carries `ConnectorID`, including script
`log.info` and base-class traces such as `Initializing connector` and
`JS statement successfully executed`. Those stay on the default levels when they
are Info or above. A connector that logs only at Trace or Debug (Delay writes
`Waiting N second(s).` at Debug) returns an empty `logs` array unless those
levels are requested. A connector failure explained only at Debug, or only on a
system line, is also missing from `logs` until that level is listed and, for a
system line, `includeSystem` is true.

A level outside 0–5 is rejected and the connector does not run.

Each returned line has `elapsed` (milliseconds from the start of this run),
`level`, `message`, and `keys`. `keys` is `{}` when the connector attached
nothing. Run context (agent, company, connector, task, step) is removed.
`Exception` stays.

### Data table and schema

`input`, each additional input, `localVariables`, and `output` are data tables.
`outputSchema` is the schema object only.

```json
{
  "Schema": {
    "Name": "CustomerQuery",
    "Columns": [
      { "Name": "City", "AllowNull": true, "DataType": 2 }
    ]
  },
  "Rows": [
    { "City": "Prague" }
  ],
  "HasDefinedRows": true
}
```

`Rows` may be omitted when the table has no rows. A column with `AllowNull`
false must be present on the row. `AllowNull` true may be JSON null. A table
object that was sent must include `Schema`. A table without `Schema` fails model
validation before these rules, so the body is not `Input schema is required.`

`DataType`: 1 Int, 2 String, 3 Bool, 4 Base64, 5 DateTime, 6 Double, 7 Table,
8 Json, 9 Decimal, 10 Text. A Table column has a nested `Schema`. Cells are JSON
numbers, strings, booleans, nulls, objects, or arrays as that type requires.
Base64 is the base64 text. DateTime is the string the Integray table reader
accepts. `DisplayName`, `DataSource`, and `IsStepOutput` are accepted and
ignored. Any other unknown schema property rejects the request.

```json
{
  "connectorGuid": "f7cb5a42-c936-42d3-bd9e-6065a71cd5b5",
  "connectorVersion": "1.2.3",
  "actionCode": "ListCustomers",
  "timeout": 30,
  "input": {
    "Schema": {
      "Name": "CustomerQuery",
      "Guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "Version": "1.0.0",
      "Columns": [
        { "Name": "City", "AllowNull": true, "DataType": 2 }
      ]
    },
    "Rows": [ { "City": "Prague" } ],
    "HasDefinedRows": true
  },
  "outputSchema": {
    "Name": "Customer",
    "Guid": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "Version": "1.0.0",
    "Columns": [
      { "Name": "Name", "AllowNull": false, "DataType": 2 }
    ]
  },
  "configurations": [
    {
      "guid": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "version": "1.0.0",
      "configuration": "{\"Url\":\"https://api.example\",\"ApiKey\":\"${#ApiKey}\"}"
    }
  ],
  "companyVariablesOverride": { "ApiKey": "secret-for-this-call" }
}
```

## Response

HTTP 200 and a rejected payload (HTTP 400) use the same object. A body that is
not JSON is HTTP 400 with the framework error, not this object.

| Property | Meaning |
| --- | --- |
| `output` | Connector output as a data table, or null when there is no output table or the request was rejected. Null can still be a success (`taskRunStatus` 201 or 203). |
| `status` | `0` Success or `1` Error. This call does not return Warning (`2`) or Unknown (`3`). |
| `errorMessage` | Why the payload was rejected or why the run failed. Null on success. |
| `taskRunStatus` | Status from the connector. Null when the connector did not run. |
| `logs` | Lines the filter kept. Empty when the request was rejected, when nothing matched, or when `levels` is empty. |
| `checkpoint` | New checkpoint when the connector changed it. Otherwise null. `""` means the connector cleared it. |

`status` is Success only when `taskRunStatus` is one of these and nothing else
failed (output could not be serialized, or a data reference could not be read):

| `taskRunStatus` | Name |
| --- | --- |
| 200 | FinishedSuccess |
| 201 | FinishedNoData |
| 202 | FinishedWithErrors |
| 203 | NothingToProcess |

`FinishedWithErrors` (202) keeps `status` 0. Row-level problems are in `logs`.

Any other connector status is `status` 1. `errorMessage` is
`Connector finished with status {Name}.` The name is the enum name
(`FailedConnector`), not the number. A serialization or data-reference failure
replaces that sentence and forces `status` 1 even when `taskRunStatus` is
200–203.

| `taskRunStatus` | Name |
| --- | --- |
| 300 | FailedConnector |
| 301 | FailedAgentKilled |
| 302 | FailedTimeout |
| 303 | FailedCancelledByUser |
| 304 | FailedRuntime |
| 305 | FailedAgent |
| 306 | FailedOutput |
| 307 | FailedInput |
| 401 | NotRun |

`100` InProgress is not a success. The run is given that status before the agent
is called. The response keeps it only when the agent returns it.

## HTTP status

| HTTP | When | Body |
| --- | --- | --- |
| 200 | The connector was started, including a connector failure. | The result object. `taskRunStatus` is null when the agent failed before a status existed (`Execution on agent failed.`). |
| 400 | The payload was rejected. The connector did not run. | The result object. `status` 1, `taskRunStatus` null, `output` null, `logs` empty. |
| 400 | The body is not JSON. | Framework error, not the result object. |
| 401 | The Bearer token is missing, is not this company's remote control token, or the company has no remote control token. | Empty. |
| 404 | The company slug is not an active company, or this runtime has no `Debugger/Run` route. | Empty. The token is not checked when the slug is unknown. |
| 500 | Unexpected failure while loading the connector or talking to the database. | Empty. |

## Validation order

The connector does not run until every check below passes. The first failure is
the only `errorMessage`.

1. Body is present.
2. `timeout` is omitted or greater than zero.
3. Every `logFilter.levels` value is 0 through 5.
4. `connectorGuid` and `connectorVersion` are present, and the version is `major.minor.patch`.
5. That connector version is installed, and its plugin is installed.
6. `actionCode`, as in the request table.
7. `agentId`. A positive id must belong to this company and be connected now.
8. Connector restriction for that agent.
9. One input process type can be chosen.
10. A non-empty `checkpoint` is allowed only when the action has a checkpoint.
11. `input`, `outputSchema`, `additionalInputs`, and `localVariables` match the schema rules.
12. `configurations` is exactly the linked set. OAuth `TokenResponse` and an empty `ServiceUrl` are filled here.
13. `${#Code}` resolves from `companyVariablesOverride`, then from an active company variable with no template, then from a system variable.

An agent that disconnects after step 7 is still HTTP 400. That message has no
agent name: `Remote agent (ID: {id}) is not active.` The check in step 7 names
the agent: `Remote agent {name} (ID: {id}) is not active.`

## Messages

HTTP 400, connector did not run:

| Situation | `errorMessage` |
| --- | --- |
| No body | `Request body is required.` |
| `timeout` is 0 or negative | `Timeout must be greater than zero.` |
| Log level not 0–5 | `Log level {number} is not valid. Use 0 Trace, 1 Debug, 2 Info, 3 Warning, 4 Error, or 5 Fatal.` |
| Guid or version missing | `Connector guid and version are required.` |
| Version is not `major.minor.patch` | `Connector version is not valid.` |
| Connector is not installed | `Connector '{guid}' version '{version}' is not installed.` |
| Plugin is missing | `Plugin of connector '{name}' is not installed.` |
| Several actions and no `actionCode` | `Connector '{name}' has more than one action. Action code is required.` |
| Unknown action | `Action '{code}' was not found on connector '{name}'.` |
| Bad `agentId` | `Agent id must be omitted for the Shared agent, or be the id of a remote agent.` |
| Unknown agent, or another company's agent | `Remote agent (ID: {id}) was not found.` |
| Remote agent is not connected | `Remote agent {name} (ID: {id}) is not active.` |
| Restriction forbids this agent | `Connector '{name}' v{version} is not allowed to run on {Shared\|Remote} agent. Allowed agents: {list}.` |
| Several process types and no single default | `Connector '{name}' allows more than one input process type and has no single default.` |
| No input process type | `Connector does not define an input process type.` |
| Process-type list cannot be read | `Connector input process type could not be read.` |
| Checkpoint on an action that has none | `Checkpoint must not be sent for this connector.` |
| Additional inputs on a single-input action | `Additional inputs must not be sent for this connector.` |
| Input sent when the type is None | `Input must not be sent.` |
| Input omitted when the type is Mandatory | `Input schema is required.` |
| Output sent when the type is None | `Output schema must not be sent.` |
| Output omitted when the type is Mandatory | `Output schema is required.` |
| Schema JSON cannot be parsed | `{slot} schema could not be read. {details}` |
| Required type, but no predefined schema | `{slot} schema is required, but the connector does not define one.` |
| Predefined schema cannot be loaded | `Required {slot} schema is not available.` |
| Required schema does not match | `{Input\|Output} schema does not match the required schema '{name}' ({guid} {version}). Send that schema, or omit {input\|outputSchema}.` |
| Data table cannot be parsed | `{slot} could not be read. {details}` |
| Configuration without guid or version | `Each configuration needs a guid and a version.` |
| Configuration version is invalid | `Configuration '{guid}' has an invalid version.` |
| Configuration is not JSON | `Configuration '{guid}' {version} is not valid JSON.` |
| OAuth configuration is not a JSON object | `Configuration '{guid}' {version} has an OAuth connection but is not a JSON object.` |
| Same configuration twice | `Configuration '{guid}' {version} was sent more than once.` |
| Linked configuration schema cannot be loaded | `Configuration schema {id} of connector '{name}' is not available.` |
| Required configuration missing | `Configuration '{guid}' {version} is required and was not sent.` |
| Extra configuration | `Configuration '{guid}' {version} is not used by this connector.` |
| Company id missing inside the action | `Company was not resolved.` A missing slug is HTTP 404, not this message. |
| `${#Code}` matches nothing | `Variable name {code} was not found.` Several codes: `Variable names {codes} was not found.` |

`{slot}` is `Input`, `Output`, `localVariables`, or `Additional input N`
(1-based). `localVariables` is always optional. There is no
`localVariables must not be sent.`

HTTP 200, the run was attempted:

| Situation | `errorMessage` | `taskRunStatus` |
| --- | --- | --- |
| The agent threw, timed out, or returned no result | `Execution on agent failed.` | null |
| The output could not be turned into JSON | `Converting the debug output to JSON failed.` | the connector status, when one was returned |
| A data reference could not be read | `Data reference '{guid}' could not be read. {details}` | the connector status, when one was returned |
| The connector finished with a status that is not a success | `Connector finished with status {Name}.` | that status |

## Data references

A large output cell may appear inside the connector as
`{ "$dataRef": "{guid}" }`. Before the HTTP body is sent, each placeholder in
`output` is replaced with the stored value. JSON text is inserted as JSON.
Other text is inserted as a string.

If a placeholder cannot be read, it stays in `output`, `status` becomes 1, and
`errorMessage` names that guid. `taskRunStatus` stays the connector status.
Placeholders inside `checkpoint` or `configuration` are not expanded.
