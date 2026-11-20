# Parent task run of an endpoint call

A task-bound endpoint stores a parent on the task run it starts when the request carries this header:

```http
int-parent-taskrun-id: 41983
```

The value is the task run id of the step that is calling. The new run's `ParentID` becomes that number. The HTTP response stays the endpoint-data guid.

The instance stores the header from **`rel-2025-03.018`** ([instance-version.md](../instance-version.md)). An older product line ignores it and leaves `ParentID` null.

A missing header, `0`, a negative number, or text leaves `ParentID` null. Any other positive integer is stored. The endpoint does not check that the run exists. A caller may set an id on purpose.

Sync and async read the same header. An endpoint with no bound task does not start a task run, so the header has nothing to attach to.

`ParentID` is also the restart link. This call counts as one restart level.

The URL is `/api/endpoint/<company-slug>/<group-slug>/<endpoint-slug>`. `<group-slug>` is the endpoint group's `Slug`, or `default-group` when the endpoint sits in the Default group ([config-transfer-format.md](../transfer/config-transfer-format.md) §2 and §8.3). A token-secured endpoint also needs `Authorization: Bearer <plaintext token>` (§8.2). Integray Endpoint Connector applies that token itself.

## Who can read the current task run id

| Caller | Current task run id |
|---|---|
| Integray Endpoint Connector `4.6.4` (`d25ba8f6-94b4-4d0f-8fb0-cfce5937808c`) | Already on the request. This version sends the header and builds the URL. Do not add either in the Configuration. An older version of the same connector does not send the header. |
| Node.js processor statement | Global `TaskRunID`. The Node.js service copies the connector context onto the statement, so the name is bare. It is not a `${#…}` placeholder. |
| Python processor statement | Not available. The connector sends `TaskRunID` to the Python service, and the service uses it only for DataRef files. The statement namespace does not contain it. |
| Advanced Rest API Connector | Not available. Header values accept `${input.<Column>}` from the current input row, and the Configuration string accepts `${#SYSTEM_…}`. Neither is the current task run id. |
| A .NET connector | `context.GetTaskRunId()` when `context.HasTaskRunId()` is true. |

## Node.js

Quote `${#SYSTEM_…}` yourself. The platform pastes the raw text into the statement and does not add quotes ([variables.md](variables.md)).

```javascript
const BASE_URL = "${#SYSTEM_BaseURL}";
const COMPANY_SLUG = "${#SYSTEM_CompanySlug}";
const url = `${BASE_URL}/api/endpoint/${COMPANY_SLUG}/<group-slug>/<endpoint-slug>`;

await fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "int-parent-taskrun-id": String(TaskRunID),
  },
  body: JSON.stringify(payload),
});
```

Set the connector's own `Timeout` as well as the Step `Timeout`. A `fetch()` with only the Step timeout still stops at the connector default of 100 seconds ([config-transfer-format.md](../transfer/config-transfer-format.md) §4).

## Python

A Python statement cannot read the current task run id, so it cannot fill `int-parent-taskrun-id` for this run. Call the endpoint from a Node.js statement, or from Integray Endpoint Connector `4.6.4`.

## Advanced Rest API

The Endpoint field is the whole URL. `${#SYSTEM_BaseURL}` and `${#SYSTEM_CompanySlug}` are substituted in the Configuration string, so they need no extra quotes:

```json
{
  "Endpoint": "${#SYSTEM_BaseURL}/api/endpoint/${#SYSTEM_CompanySlug}/<group-slug>/<endpoint-slug>",
  "RequestType": "post",
  "Headers": [
    { "key": "int-parent-taskrun-id", "value": "${input.ParentTaskRunID}" }
  ]
}
```

`${input.ParentTaskRunID}` is replaced only when that column is already on the input row. This connector never puts the current task run id on the row. A fixed number in `value` is sent on every run. To attach this run, use the Node.js statement or Integray Endpoint Connector `4.6.4`.

## Connector

```csharp
if (context.HasTaskRunId())
{
    request.Headers.TryAddWithoutValidation(
        "int-parent-taskrun-id",
        context.GetTaskRunId()!.Value.ToString());
}
```

Build the same `/api/endpoint/<company-slug>/<group-slug>/<endpoint-slug>` path. `context.GetTaskRunId()` is the value for the header.
