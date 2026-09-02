# Data Checkpoint — Reference for Config Transfer JSON Generation

> Companion to `docs/transfer/config-transfer-format.md` §5 (Configurations). A per-Step mechanism for a
> stateless connector to remember a small piece of data between separate Task Runs —
> e.g. the last processed record ID, the last read file/message. Distinct from
> `docs/entities/local-variables.md`'s Local Variables (Task-scoped, reset per Task Run) — Data
> Checkpoint is scoped to a single Step and explicitly persists *across* runs.

---

## How it works

A Step's Configuration gets one extra field alongside its normal ones (e.g. `Statement`
for a script connector): the column whose value should be remembered. After the Step
runs, the platform takes that column's value from the **last output row** and stores it
as the checkpoint for that Step's *next* Task Run. The stored value is then exposed back
to the Step on its next run via a predefined variable/placeholder — syntax differs by
connector family, see below.

```json
{ "Statement": "...", "DataStorageColumn": "ID" }
```

**The Configuration JSON key is not always `DataCheckpointColumn`, despite the UI title
always being "Data checkpoint column"** — confirmed from `data/configuration-schemas.json`:

| Connector family | JSON key | Read syntax in the script/statement |
|---|---|---|
| JS Mapper, Node.js processor, Python processor | `DataStorageColumn` | `DataCheckpoint` (predefined constant) |
| MS SQL, MySQL, Postgre SQL, ODBC, IBM Db2 | `DataCheckpointColumn` | `@DataCheckpoint` (SQL bind variable) |
| Oracle Database | `DataCheckpointColumn` | `:DataCheckpoint` (Oracle bind syntax) |
| SQLite Mapper | `DataCheckpointColumn` | `variables.ColumnName` (different prefix entirely) |

Look up the exact key/syntax for a specific connector's Configuration in
`data/configuration-schemas.json` (follow the connector action's `configurationRefs[]` in
`data/connectors.json` to find the right entry) before assuming either name/syntax — don't
copy the JS Mapper form for a SQL connector.

**No known way to reset/clear a stored checkpoint from a script or the transfer JSON.**
The DX UI has a "Data Checkpoint Overview" (task-level menu action) where an admin can
view and manually delete a stored checkpoint by hand, but there's no confirmed
scripting-accessible reset. A test or process that needs a clean starting point has to
either treat the *current* checkpoint value as an unknown baseline and assert relative
progress from there (see the self-test example below), or rely on a human clearing it via
that UI first.

---

## Confirmed behavior

- **Persists correctly across separate Task Runs**, not just conceptually — confirmed by
  actually triggering two independent Task Runs of the same Step in sequence and checking
  the second one continued from the first (confirmed on a live company that ran two
  sequential Task Runs of the same Step).
- **Value comes from the *last* output row specifically**, not the first or some
  aggregate — confirmed indirectly: a first-row implementation would produce overlapping
  results between consecutive runs instead of a clean continuation.
- **`DataCheckpoint` starts falsy (`undefined`/`null`-ish) on a Step's very first ever
  run** — the idiomatic JS Mapper/Node.js guard is `if (!DataCheckpoint) { DataCheckpoint
  = 0; }` before using it in arithmetic.
- **JS Mapper's `Statement` does not support `async function` / top-level `await`** —
  confirmed: using either throws `SyntaxError: Unexpected identifier`. If a Step needs to
  make its own HTTP call (e.g. to orchestrate/verify something), use the **Node.js
  processor** connector instead (`Guid: 5a70dfd2-9803-4bcf-b090-652b156f7236`) — it shares
  the same `Statement`/`DataStorageColumn`/`log` Configuration shape as JS Mapper but
  supports real `async`/`await`/`fetch()`. Don't assume every script connector has the
  same JS feature set just because the Configuration schema looks identical.

---

## Minimal example (JS Mapper)

```js
if (!DataCheckpoint) {
  DataCheckpoint = 0;
}

var start = DataCheckpoint + 1;
var end = start + 2; // 3 rows this run
var rows = [];
for (var i = start; i <= end; i++) {
  rows.push({ ID: i });
}

return rows;
```
Configuration: `{ "Statement": "...", "DataStorageColumn": "ID" }`. First run (nothing
stored yet) → IDs `1,2,3`, stores `3`. Next run → IDs `4,5,6`, stores `6`. And so on.
