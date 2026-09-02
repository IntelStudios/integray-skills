# `InputSchemaMapping` — data addressing between Steps

> Companion to `docs/transfer/config-transfer-format.md` §6. Read this whenever a task has more than one
> branch, or more than one connector chained in a row — this is the single most
> error-prone part of building `Steps[]`.

---

## 1. `PrevStepCopyID` vs `AdditionalInputs`

- **`PrevStepCopyID`** = **temporal** dependency. Execution order — "this step runs after that one."
- **`AdditionalInputs`** = **data** dependency. The step waits on data from *other
  branches* and consumes them as extra inputs (`inputData2`, `inputData3`, ...).
  Typical for multi-input steps (e.g. a JS Mapper merging several sources).
- These are independent and can diverge: a step can be temporally chained after step A
  (`PrevStepCopyID`) while pulling data from steps B and C (`AdditionalInputs`).

**`Delay` connector** (`Guid: a1865bf9-504c-43c7-89d5-b9a940432d44`, `Version: 3.0.3`) —
a dedicated pure-timing step: one config field, `Delay` (number, seconds). Both
`InputSchema` and `OutputSchema` are `none`/`null` — it carries **no data at all**, it
just occupies a `PrevStepCopyID` slot for N seconds before letting execution continue.
Concrete illustration of the split above: a step chained after a Delay step still has to
point its `InputSchemaMapping` at whichever real data-producing step came before the
Delay — the Delay step itself has nothing to address.

**`Delay: -1` is the simplest way to deliberately fail a step, not an "infinite wait."**
The connector's own config-validation error text describes `-1` as a legitimate value
"signifying an infinite timeout" (alongside `0` and any positive integer) — but in
practice it makes the step fail immediately (`FailedConnector`), the same as an outright
invalid value (e.g. `-5`). Don't read the error text literally and design a test around
"wait forever, then eventually time out" — if the goal is just to force an immediate step
failure (e.g. to test `ErrorBehavior` propagation to a downstream step), `Delay: -1` is
the shortest path there.

**Confirmed: a not-run `AdditionalInputs` source always yields `[]`, never `null`** —
contradicts learn.integray.app's own Multi Input Step documentation, which claims a
disabled/failed/not-run source step gives `null` (only an executed-but-empty-result
source gives `[]`). Confirmed on JS Mapper 3.5.6 (ruling out the null→`[]` normalization
bug the docs describe as fixed in 3.3.0+) across four independent mechanisms on
rel-2025-03.017, all giving `[]`:
1. `StopIfEmptyOutput:true` on the consuming step, chained after a `Delay` step (whose
   output is always empty by definition).
2. An explicit upstream connector failure (`FailedConnector`).
3. `IsTempDeactivated:true` on the source step.
4. **A `RowByRowSequentially` source that succeeds on some rows and throws on a later
   one** — even though it wrote real output for the rows that succeeded before the
   failure, the downstream `AdditionalInputs` reference still sees a clean `[]`, not the
   partial rows. Same all-or-nothing behavior confirmed for a primary input's reference
   (`TASK_SCHEDULING_AND_MULTI_INPUT_RULES.md` §3) — the platform discards partial
   writes on failure for `AdditionalInputs` too, not just primary.

**Gotcha:** exactly **one** step per task may have `PrevStepCopyID: null` — the task
graph has a single root (`FirstStep`). More than one `null` first-step throws **"Task
cannot contain more than one first step"** on open. For tasks with several parallel
branches (e.g. a self-test task starting N independent actions), create one trivial root
step (`PrevStepCopyID: null`, a JS Mapper returning an empty array — reuse the shared
`Generate empty data` config, `ConfigurationCopyID: b91fdaa8-2409-4895-abbd-969e8ad54200`,
`OutputSchema` via the system `Text` schema `Guid: b76c3662-4903-4512-97a9-72f32eaecd01`,
`Version: 1.0.0`) and branch every parallel step off it via `PrevStepCopyID`. This is
exactly what the `Split` step does in `Stop On Empty Output`.

```json
"AdditionalInputs": [
  { "StepCopyID": "<CopyID of the source step>", "InputDataFilter": null,
    "InputSchema": { "CopyID": "..." },
    "InputSchemaMapping": { "<Field>": "<path — see §2>" } }
]
```
`AdditionalInputs[0]` → `inputData2` in the JS Mapper/Node.js script, `[1]` → `inputData3`, etc. Each entry has its own independent `InputSchema`/`InputSchemaMapping`.

**`InputSchemaMapping` keys (primary *and* every `AdditionalInputs[]` entry) are not
aliases you get to choose — each key must be the *exact* column name of that mapping's
own declared `InputSchema`.** The value (the path/source side, per §2's Rule 1-5) is the
only part that's free to reference a differently-named column elsewhere — the platform
only checks that its *type* matches the target column, never its name (`docs/transfer/config-transfer-format.md`
§7 codes — Integer `1`, String `2`, …). Confirmed against the platform's own UI: a step
declaring `InputSchema` `{C1: String, C2: String}` mapped from a source step whose own
columns were named `ColumnA`/`ColumnB` published fine as `{"C1": "<source step>.ColumnA",
"C2": "<source step>.ColumnB"}` — names differ freely on the source side, but the keys
`C1`/`C2` had to match the declared schema exactly, **and** `ColumnA`/`ColumnB` had to
be String, not Integer. **Same column name is not a substitute for a type match.** A
producer column and a consumer column that share a name (or that you mapped across two
versions of the same system schema by name) can still differ in `Type` — e.g. `int` in
one version, `string` in the next. Import / `"Incorrect Mapping"` / `onlyTest` do **not**
catch that: they validate that the path exists and that `AllowNull: false` keys are
present, not that the two sides' `Type` (or, for `Type: 7`, `ComplexType`/`tableRef`)
agree. Confirmed live: a same-guid DataSchema bump on a producer `OutputSchema`, with
the next Step's `InputSchemaMapping` copied by column name (and that Step's `InputSchema`
left on the old version because the names still lined up), left one column Integer on
one side and String on the other. Process stayed green. At run time the consuming step
never entered the connector — `Starting step on shared agent failed` with `Unable to
cast object of type 'System.Int32' to type 'System.String'`, then `FailedAgent` (305).
Empty producer output hid it (`StopIfEmptyOutput` → `FinishedNoData`). When generating
or rewriting a mapping, every pair must match on **`Type`** (and nested table schema
for `Type: 7`), not name alone. After a same-guid schema bump, align the consumer
`InputSchema` `{Guid,Version}` with the producer `OutputSchema`, or insert an explicit
conversion — do not assume same-named columns kept their type.

Using a key that isn't a real column of that `InputSchema` (e.g. inventing `StartTaskRunID` as a
key when the declared schema's actual column is `TaskRunID`) fails import with
`"Incorrect Mapping"` (primary) / `"Incorrect Additional Input Mapping"` (`AdditionalInputs`)
— **even when the path/value half is completely correct** per §2, since the checklist in
§3 validates the path *against* the key, and an invented key never matches any node in
that computed tree to begin with. **If two `AdditionalInputs` entries need to expose two
same-named source columns (e.g. two different steps that each have their own `TaskRunID`)
without clashing in the script, do not try to rename via the mapping key** — the key stays
the schema's real column name in both entries; disambiguate in the script itself via the
`inputDataN` array index (`inputData2[0].TaskRunID` vs. `inputData3[0].TaskRunID` are
already distinct, no renaming needed).

**Gotcha — the `AdditionalInputs` array and the script's `Statement` text are two
independent things that must be kept in sync by hand.** Adding an entry to
`AdditionalInputs` only makes `inputDataN` *exist* as a variable for the script — it does
**not** automatically pull that data into the step's output. If the `Statement` builds its
result by explicitly naming each `inputDataN` (e.g. a hardcoded
`return [...inputData2, ...inputData3, ..., ...inputDataN];` — a common fan-in pattern for
a merge step collecting several parallel branches) and isn't updated to also include the
new `inputDataN`, the new branch's data is silently dropped: no error on import, no error
at runtime, just missing from the output. Whenever you add an `AdditionalInputs` entry to
an *existing* step, always check whether that step's own `Statement` also needs a
matching edit — the two are never inferred from each other.

---

## 1.1 Scheduling — when a step is actually allowed to start

Two independent questions per step: **when** may it start, and **what data** does it see
once it does (addressing, §2 below). Only the first is covered here.

A step starts once both hold:
- its own temporal predecessor (`PrevStepCopyID`) has finished (success or failure, if
  the task continues past failures);
- every `AdditionalInputs[]` source step it reads from has also finished — this list is
  computed once at build time from the additional-input mappings and ticked off as each
  source step completes.

**The step's own primary-input dependency never feeds into this list.** Primary input is
checked separately, only once the step is already running and pulling its actual data: a
binary "did the referenced step's overall run succeed?" check, not a completeness check
— a predecessor that throws partway through still counts as failed even though it may
have already written partial data, and the reading step gets an empty table (0 rows),
never the partial rows or an undefined value. This check is all-or-nothing across every
step a primary input's mapping references. It's not a race-safety mechanism either —
convention guarantees a primary input's source is always in the step's own ancestor
chain, which temporal order already finished by the time this step is eligible to run;
it exists purely to catch "ran but failed" or "never ran because its branch is
deactivated."

`AdditionalInputs[]` entries, by contrast, are real scheduling gates precisely because
they read from **sibling** branches with no such temporal guarantee — each entry's
deactivated-branch check and its scheduling dependency must both stay tracked **per
entry**, never collapsed to one flag for the whole step, or one entry's dependency can
leak onto an unrelated sibling entry on the same step.

**Confirmed: a step chained after a `FailStepAndContinue`/`FailTaskAndContinue` failure
runs completely normally, on real data, if it doesn't itself read from the failed step.**
A step has no special awareness that its temporal predecessor (`PrevStepCopyID`) failed —
"the branch continues" does not mean the next step runs "over empty data" as a rule; it
runs over whatever its own `InputSchemaMapping`/`AdditionalInputs` actually resolve to,
exactly like any other step. Concretely: a `Delay` step deliberately failed
(`docs/transfer/config-transfer-format.md` §6.1) with `FailStepAndContinue`, immediately followed
(`PrevStepCopyID`) by a step whose `InputSchemaMapping` points at an *earlier*,
unaffected step — not at the failed `Delay` — still produces its full, correct output.
Only a step that actually *reads its data* from the failed step (via primary input or
`AdditionalInputs`) sees the all-or-nothing empty-table effect described above; a step
merely chained *after* it in time is unaffected if its real data source lies elsewhere.

**Confirmed production regression trap:** a step's mapping paths exist internally in two
forms — one identifying the concrete referenced step (for dependency computation), one
by human-readable name (for actually navigating the result tree). If dependency
computation runs against the mapping *after* it's already been rewritten to the by-name
form, it silently finds zero dependencies — no error, just 0 results. For a primary
input, that permanently (and silently) disables the "predecessor failed midway"
protection. For `AdditionalInputs`, it removes scheduling's only real data source — every
step with an additional input becomes eligible to run as soon as its temporal
predecessor finishes, with no wait on the sibling branches it actually reads from. This
is an active, silent data-loss bug, not just a missing safeguard — confirmed in
production.

---

## 2. Tree logic of `InputSchemaMapping` addresses

Step results aren't stored flat — they go into a **tree**. `"StepName.ColumnName..."` is
a path in that tree. Segments are always entity names (Step, Column, Endpoint) — never
action/connector-type names or keywords. A path segment like `"Row by row"` is just a
step someone named that.

### Rule 1 — where a step attaches itself (its "storage location")

Take the **longest path** among the step's own `InputSchemaMapping` values and **drop
its last segment** (the column name). What's left is the tree node — the storage
location — under which the step attaches itself, as a new node **named after itself**.

- Several input paths at once (must be the same branch, not diverging) → use the **deepest** one.
- No path at all → storage location = root (see Rule 2).

### Rule 2 — exception: always lands at root, regardless of its own mapping

- `InputProcessType: 1` (`Bulk`),
- the step has `AdditionalInputs` (multi-input),
- the step has no `InputSchema`, or no `InputSchemaMapping` (`null`).

Any **one** of these is enough — whatever the step's own mapping would otherwise imply
(even a deep path) is ignored, and the step attaches directly at root under its own
name. Reason for Bulk/multi-input: aggregating 1:N/N:1 while keeping the old path would
imply a nonsensical cartesian product.

Conversely, `InputProcessType: 2` (`RowByRowSequentially`) with both `InputSchema` and
`InputSchemaMapping` set and no `AdditionalInputs` → **normal case**, storage location
computed per Rule 1 (nesting) — regardless of connector type (HTTP/Endpoint connectors
included; only `InputProcessType` + presence of mapping/AdditionalInputs matter).

> `InputProcessType`: `1` = `Bulk`, `2` = `RowByRowSequentially` — confirmed from source.

### Rule 3 — how a later step reads step X's output

```
(storage location of X) . (X's own name) . (column name)
```

### Rule 4 — `AdditionalInputs`

Data across different "trees" (created by a Rule 2 reset) doesn't mix. A step needing
data from several trees at once uses `AdditionalInputs` — each entry has its own
independent path (read per Rule 3, based on where its source step actually lives).

### Rule 5 — a task-bound POST/PATCH/PUT Endpoint is an implicit "step zero"

See `docs/transfer/config-transfer-format.md` §8.5 for the full mechanism. In short: an Endpoint with
`*InputTaskCopyID`/`*InputSchema`/`*InputMapping` set deposits its mapped request data at
the tree root under **its own `Name`**, exactly like a Step would under its own name —
so the bound Task's first Step needs `InputSchemaMapping: {"Column": "<Endpoint
Name>.Column"}`, same as Rule 1/3 for any other step, just with an Endpoint's name
instead of a Step's. Once that first Step has this mapping (and isn't Bulk / has no
`AdditionalInputs`), it stops resetting to root (Rule 2 no longer applies to it) and
nests under the Endpoint per Rule 1 — its own output address becomes `<Endpoint
Name>.<Step Name>.<Column>`, not just `<Step Name>.<Column>`.

### Examples (generic names)

- A) `STEP1` with no `InputSchemaMapping` → storage location = root → read as `STEP1.Column` (2 segments)
- B) `STEP2` with mapping `{"X": "STEP1.Column"}`, `InputProcessType: 2`, no AdditionalInputs → storage location = `STEP1` → read as `STEP1.STEP2.Column` (3 segments)
- C) `STEP3` with mapping `{"X": "STEP1.STEP2.Column"}`, `InputProcessType: 2` → storage location = `STEP1.STEP2` → read as `STEP1.STEP2.STEP3.Column` (4 segments)
- D) `STEP4` with the same mapping as C but `InputProcessType: 1` (Bulk) → Rule 2 applies, mapping ignored → storage location = root → read as `STEP4.Column` (2 segments)

### Worked example — a longer chain

```
Start Task           (InputSchema: null → root)
  read as: "Start Task.TaskRunID"

Get task run status  (InputProcessType: 1 = Bulk → Rule 2 → root,
                       even though its mapping reads "Start Task.TaskRunID")
  read as: "Get task run status.StatusCode"

Parse status         (InputProcessType: 2, mapping "Get task run status.StatusCode"
                       → storage location = "Get task run status")
  read as: "Get task run status.Parse status.TaskRunStatus"

Evaluate result      (InputProcessType: 1 = Bulk, also has AdditionalInputs
                       → Rule 2 → root, even though its primary mapping reads deep)
  read as: "Evaluate result.TestName"
```

### Worked example — multi-input step, two inputs

```json
"AdditionalInputs": [
  { "StepCopyID": "<CopyID of 'Row by row'>", "InputSchema": { "CopyID": "<schema CopyID>" },
    "InputSchemaMapping": {
      "TestName": "Generate Data.Row by row.TestName",
      "Success": "Generate Data.Row by row.Success",
      "ErrorMessage": "Generate Data.Row by row.ErrorMessage"
    } },
  { "StepCopyID": "<CopyID of 'Bulk'>", "InputSchema": { "CopyID": "<schema CopyID>" },
    "InputSchemaMapping": {
      "TestName": "Bulk.TestName", "Success": "Bulk.Success", "ErrorMessage": "Bulk.ErrorMessage"
    } }
]
```
`Generate Data` produced the data; the step named `Row by row` nested under it
(Row-by-row processing → 3-segment path). The step named `Bulk` reset the tree (Bulk
processing), so its path starts directly from its own name.

---

## 3. Checklist for multi-branch/multi-connector `Steps[]`

1. For every step, determine `InputProcessType` (`1`=Bulk, `2`=RowByRowSequentially), `InputSchema`, `AdditionalInputs` — this triple decides reset (Rule 2) vs. nest (Rule 1).
2. Walk Steps in dependency order (`PrevStepCopyID`/`AdditionalInputs`) and record where each one attached (storage location + own name = full path to its output columns).
3. Verify every value in `InputSchemaMapping`/`AdditionalInputs[].InputSchemaMapping` of the next step against that growing map — it must exactly match an already-computed path to an existing column. A wrong/nonexistent path = `"Incorrect Mapping"` / `"Incorrect Additional Input Mapping"` on import/open.
4. Don't forget `AllowNull: false` columns of the target schema (`docs/transfer/config-transfer-format.md` §7) — all of them must be mapped; nullable ones can be skipped.
5. For every mapped pair, the source column's `Type` must equal the target column's `Type` (`docs/transfer/config-transfer-format.md` §7). Name match is not enough — same-named columns can change type across schema versions, and import will not flag it. For `Type: 7` (Table), `ComplexType` / `tableRef` must match too.
