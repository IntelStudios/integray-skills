# Data addressing

Companion to [config-transfer-format.md](../transfer/config-transfer-format.md) §6. Read this
whenever a Task has more than one Step, a branch, or a task-bound Endpoint.

Step output is **not** a flat bag of columns. It is a **tree**. An `InputSchemaMapping`
value is a path in that tree (`StepOrEndpoint.Column`, maybe deeper). Segments are
**entity names** (Endpoint, Step, Column) — never connector type, action code, or
keywords. A Step named `Row by row` is just a name.

Write and read are separate:

| | Decides |
|---|---|
| Where this Step **stores** its output | `InputProcessType` + whether it has `InputSchema` + (if nesting) the primary mapping |
| What this Step **reads** | Each mapping’s path, turned into a **query tree** |

---

## 1. Where a Step stores its output

The Step becomes a table column named after itself. The only question is **under which
node** that column is added.

### Rule 1 — nest (RowByRow)

`InputProcessType: 2` (`RowByRowSequentially`) **or** `4` (`RowByRowInParallel`), and the
Step has an `InputSchema` and a primary `InputSchemaMapping`.

Take the **longest** primary-mapping path(s). Drop the last segment (the column). What
remains is the parent node. The Step attaches there under its own `Name`.

- One path `STEP1.Col` → parent `STEP1` → later reads are `STEP1.ThisStep.Col`.
- Several paths → they must share a prefix (same branch). The parent is that common
  prefix. If they diverge at the first segment, the parent is **root**.
- No mapping / empty mapping → root (same as Rule 2).

Connector type does not matter. Only `InputProcessType` and the presence of
`InputSchema` / mapping do.

### Rule 2 — attach at root (Bulk, or no input schema)

If **either** is true, the mapping is ignored for storage and the Step is added on the
**root** under its own `Name`:

- `InputProcessType: 1` (`Bulk`)
- `InputSchema` is `null`

Reason: folding 1:N / N:1 back onto the old path would be a cartesian product.

**`AdditionalInputs` ⇒ Bulk.** A Step with more than one input cannot be RowByRow.
Designer and backend both require `InputProcessType: 1` when `AdditionalInputs` is
non-empty. Do not emit `InputProcessType: 2` or `4` together with `AdditionalInputs`.
Every input (primary and each AdditionalInputs entry) is the **entire** collection in
one call. Storage is this rule: the Step attaches at **root**.

### Rule 3 — how a later Step reads this one’s output

```
(parent from Rule 1 or 2) . (this Step’s Name) . (column)
```

Root attachment → two segments (`Echo.Out`). Nested under an Endpoint named `Name` →
three (`Name.Echo.Out`). A nested Step may reuse the Endpoint’s `Name`; the path
repeats that segment (`<Endpoint>.<Prep>.<Endpoint>.Col`). Still one tree.

### Rule 5 — task-bound Endpoint is step zero

A POST/PATCH/PUT Endpoint with `*InputTaskCopyID` / `*InputSchema` / `*InputMapping`
drops the request at **root** under the Endpoint’s own `Name`. Full mechanism:
[config-transfer-format.md](../transfer/config-transfer-format.md) §8.5.

The bound Task’s first Step must map `{"Col": "<Endpoint>.Col"}`. Endpoint
`*InputMapping` does not replace that. The path uses the Endpoint’s **current**
`Name`. Renaming the Endpoint does not rewrite these strings
([config-transfer-format.md](../transfer/config-transfer-format.md) §7).

- First Step is RowByRow with that mapping → it **nests under the Endpoint** (Rule 1).
  Its output is `<Endpoint>.<Step>.<Col>`.
- First Step is Bulk (or has no `InputSchema`) → it does **not** nest. Endpoint stays
  one root node; the Step is a **second** root node. Mapping `{"Col": "<Endpoint>.Col"}`
  only says what the Step **reads**, not where it **stores**.

---

## 2. How a Step reads (query tree)

Runtime does not walk an arbitrary graph. `InputSchemaMapping` is compiled into a query
tree that has **one** `Next` child per node — a chain, not a fork.

Each mapping path is laid onto that chain in dictionary order. If the root already has
`Next = Name`, a second path starting with `Echo` is **not** added as a sibling. The
walker stays on `Name` and looks up the second path’s **last** segment on that wrong
node.

Consequence: primary mapping

```json
{ "FromEndpoint": "Name.Name", "FromStep": "Echo.Out" }
```

is accepted by the designer (two roots) and by import (both paths exist on the **schema**
tree). At run time `FromEndpoint` binds and `FromStep` is `null` (column `Out` is not on
the `Name` row). The Step is `Finished Success`. Swap the two keys and the other side
goes `null`.

### Rule 4 — second tree = `AdditionalInputs`

Trees created by Rule 2 (and the Endpoint node) do not mix in one primary mapping. A
Step that needs two of them uses `AdditionalInputs` and is therefore **Bulk** (Rule 2):
each entry has its **own** query tree, arrives as the full collection (`inputData2`,
`inputData3`, … in JS Mapper / Node.js), and the Step’s output sits at root.

```json
"AdditionalInputs": [
  {
    "StepCopyID": "<source Step CopyID>",
    "InputDataFilter": null,
    "InputSchema": { "CopyID": "..." },
    "InputSchemaMapping": { "<InputSchema column>": "<path>" }
  }
]
```

Designer showing two mapping roots is two trees, not a join. Put one tree on primary
input, the other on `AdditionalInputs`. Repeated `Name` on **one** branch is not two
trees — keep it on the primary path.

---

## 3. Mapping JSON

**Keys** are the consuming `InputSchema` column names, exact match. They are not aliases.
Inventing `StartTaskRunID` when the schema column is `TaskRunID` → `"Incorrect Mapping"`
/ `"Incorrect Additional Input Mapping"` even if the path is right.

**Values** are source paths (Rule 3 / Rule 5). Source column **names** may differ. Confirmed
in DX: `InputSchema` `{C1, C2}` mapped as `{"C1": "<step>.ColumnA", "C2": "<step>.ColumnB"}`
publishes; the keys had to be `C1`/`C2`, the sources had to be String like the targets.

**Types must match** (`docs/transfer/config-transfer-format.md` §7: Integer `1`, String
`2`, …). Same name is not a type match. Import / `onlyTest` check that the path exists
and that `AllowNull: false` keys are present — **not** `Type` (or `ComplexType` /
`tableRef` for tables). A schema-version bump that changes a column from int to string
publishes green. At run the consuming Step never enters the connector:
`Starting step on shared agent failed` / `Unable to cast object of type 'System.Int32'
to type 'System.String'`, then `FailedAgent` (305). Empty producer output can hide it
(`StopIfEmptyOutput` → `FinishedNoData`). After a same-Guid schema bump, align consumer
`{Guid,Version}` with the producer, or convert explicitly.

Two `AdditionalInputs` entries that both expose `TaskRunID`: keep the key `TaskRunID` on
both; disambiguate in the script (`inputData2[0].TaskRunID` vs `inputData3[0].TaskRunID`).

`AdditionalInputs[]` and the Step `Statement` are independent. Adding an entry creates
`inputDataN`; it does not merge that data into the output. A `return [...inputData2,
...inputData3]` merge that omits the new `inputDataN` drops the branch silently.

---

## 4. When the Step is allowed to start

Two questions: **when** it may start, and **what** it sees. This section is only “when”.

A Step starts when:

1. its `PrevStepCopyID` predecessor has finished (success or failure, if the Task
   continues);
2. every `AdditionalInputs` source Step has finished (computed from those mappings at
   build time).

Primary mapping is **not** in that wait list. Once the Step runs, primary input is a
binary “did every referenced Step succeed?”. Failed or not-run → empty table (0 rows),
never partial rows. Primary sources are expected to be ancestors, so this is not
race-safety; it catches failed / deactivated producers.

`AdditionalInputs` **are** scheduling gates (sibling branches). Track each entry
separately. Collapsing them to one flag lets one entry’s wait leak onto another.

**`PrevStepCopyID` is time. `AdditionalInputs` is data.** A Step can run after A and
read B and C. Chaining after `FailStepAndContinue` or `FailTaskAndContinue` does not
empty the next Step unless that Step **reads** the failed one. Confirmed: Delay failed
with `FailStepAndContinue` ([config-transfer-format.md](../transfer/config-transfer-format.md)
§6.1), next Step mapped at an earlier healthy Step — full correct output, not empty.

Exactly **one** Step per Task may have `PrevStepCopyID: null` (the `FirstStep`). A second
root throws `"Task cannot contain more than one first step"`. Parallel work: one dummy
root (JS Mapper `return []`, `OutputSchema` system Text `Guid`
`b76c3662-4903-4512-97a9-72f32eaecd01` Version `1.0.0`) and branch everyone off it.

### Empty primary input

RowByRow with a defined input that is empty → the Step is skipped (`nothing to process`).
**Bulk still runs** on `[]`. That is why empty-origin Bulk tests must actually execute.

### `AdditionalInputs` that did not run

A not-run source yields an **empty table `[]`** (schema present), never `null`.
learn.integray.app’s Multi Input Step table (null if disabled/failed/not-run, `[]` only
if executed empty) is wrong. Confirmed JS Mapper 3.5.6, rel-2025-03.017, all `[]`:

1. Consumer `StopIfEmptyOutput: true` chained after Delay (Delay output is always empty).
2. Upstream `FailedConnector`.
3. Source `IsTempDeactivated: true`.
4. RowByRow source that wrote some rows and then threw — partial output is discarded.
   Same all-or-nothing as primary input.

If the AdditionalInputs entry has no schema, the slot can be `null` instead of an empty
table.

### Delay

Connector `a1865bf9-504c-43c7-89d5-b9a940432d44`, Version `3.0.3`. Config is seconds only.
`InputSchema` / `OutputSchema` are null — no data, only a `PrevStepCopyID` slot. The next
Step must map at a real producer, not at Delay.

The connector’s own validation text lists `-1` as “infinite timeout” (with `0` and any
positive integer). That text is wrong in practice: `Delay: -1` fails the Step immediately
(`FailedConnector`), same as an invalid value such as `-5`. Do not build a test that
waits forever and then times out. Use `-1` only to force an immediate failure.

### Publish bug (active)

Mapping paths exist internally in two forms: identity keys (`{e:}` / `{ts:}` / `{dsc:}`)
for the runtime tree, and display names for humans. The Task-run snapshot JSON
([remote-api.md](../transfer/remote-api.md) Task run snapshot) is the **identity-key**
tree. If **scheduling / dependency computation** runs against the **name** form, it
silently finds zero dependencies — no error.

- **Primary input:** the “producer failed midway → empty table” protection never arms.
- **`AdditionalInputs`:** the Step becomes eligible as soon as its temporal predecessor
  finishes; it does not wait on the sibling branches it actually reads. Silent data loss.

Do not “fix” that in a transfer.

---

## 5. Examples

| | Step | Process | Mapping | Stores at | Read as |
|---|---|---|---|---|---|
| A | `STEP1` | any | none | root | `STEP1.Col` |
| B | `STEP2` | RowByRow | `STEP1.Col` | under `STEP1` | `STEP1.STEP2.Col` |
| C | `STEP3` | RowByRow | `STEP1.STEP2.Col` | under `STEP1.STEP2` | `STEP1.STEP2.STEP3.Col` |
| D | `STEP4` | Bulk | same as C | **root** | `STEP4.Col` |
| E | POST Endpoint `Name`, then Bulk `Echo` mapping `Name.Name` | — | two root nodes `Name` and `Echo` | `Echo.Out` is **not** `Name.Echo.Out` |

Chain (Start Task → Bulk Get status → RowByRow Parse → Bulk Evaluate with AdditionalInputs):

```
Start Task              no InputSchema → root          Start Task.TaskRunID
Get task run status     Bulk → root                    Get task run status.StatusCode
Parse status            RowByRow under Get …           Get task run status.Parse status.TaskRunStatus
Evaluate result         Bulk + AdditionalInputs → root Evaluate result.TestName
```

Two inputs on a merge Step — one nested RowByRow tree, one Bulk tree at root:

```json
"AdditionalInputs": [
  {
    "StepCopyID": "<Row by row>",
    "InputSchema": { "CopyID": "<schema>" },
    "InputSchemaMapping": {
      "TestName": "Generate Data.Row by row.TestName",
      "Success": "Generate Data.Row by row.Success",
      "ErrorMessage": "Generate Data.Row by row.ErrorMessage"
    }
  },
  {
    "StepCopyID": "<Bulk>",
    "InputSchema": { "CopyID": "<schema>" },
    "InputSchemaMapping": {
      "TestName": "Bulk.TestName",
      "Success": "Bulk.Success",
      "ErrorMessage": "Bulk.ErrorMessage"
    }
  }
]
```

---

## 6. Checklist

1. For each Step: `InputProcessType` (`1` Bulk, `2` sequential RowByRow, `4` parallel
   RowByRow) and whether `InputSchema` is set → Rule 2 vs Rule 1.
2. Walk `PrevStepCopyID` / `AdditionalInputs` order. Record each Step’s storage path
   (parent + own name).
3. Every mapping **value** must be a path that already exists on that map. Wrong path →
   `"Incorrect Mapping"` / `"Incorrect Additional Input Mapping"` on import. Existing
   sibling-root paths can still be a **runtime** `null` if they share one primary mapping
   (§2). After a rename, the first segment must still be a live Step or bound Endpoint
   `Name` — Process does not rewrite it.
4. Map every `AllowNull: false` column of the target schema
   ([config-transfer-format.md](../transfer/config-transfer-format.md) §7).
5. Every mapped pair: same `Type` (and `ComplexType` for tables). Import will not save
   you.
6. Two root nodes needed on one Step → primary + `AdditionalInputs` (Bulk, root), never
   two forks in one mapping and never RowByRow on that Step. Nested same Name stays
   primary.
7. One `PrevStepCopyID: null` per Task.
