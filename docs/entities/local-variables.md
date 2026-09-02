# Local Variables — Reference for Config Transfer JSON Generation

> Companion to `docs/transfer/config-transfer-format.md` §6 (Tasks → Steps). Task-scoped variables, reset
> per Task Run — distinct from top-level `Variables[]` (`docs/entities/variables.md`), which
> are company-wide constants, unchanged during a Task Run.

---

## Structure

Two `Task`-level fields (skeleton in `docs/transfer/config-transfer-format.md` §6):

- **`VariablesSchema`** — reference to a `DataSchemas[]` entry that defines the Local
  Variables' names/types, same reference-form rule as any other schema (§7 of
  `docs/transfer/config-transfer-format.md`): custom schema → `{"CopyID": "..."}`, **system schema →
  `{"Guid": "...", "Version": "..."}` — confirmed working identically to a custom
  schema.** Only primitive column types are confirmed working —
  String/Integer/Bool/Base64/DateTime/Double/JSON/Decimal, i.e. everything except `Type:7`
  (Table) — Table support is unconfirmed, not just untested-and-assumed-unsupported.
- **`VariablesDefaults`** — a JSON-string-encoded object (like `InputDataFilter`,
  double-encoded) of initial values keyed by column name, e.g.:

  ```json
  "VariablesDefaults": "{\"StringValue\":\"foo\",\"IntegerValue\":5,\"JsonValue\":\"{\\\"marker\\\":\\\"bar\\\"}\"}"
  ```

**JSON-typed column's default needs a THIRD layer of encoding.** Every other column
type's default is a plain JSON value inside `VariablesDefaults`. A `JSON`-typed (`Type:8`)
column's default must instead be an **escaped JSON string**, not a nested object —
confirmed by hand: giving it as a nested object made the DX "JSON content" default-value
editor render the literal text `[object Object]` instead of valid JSON. This is specific
to `VariablesDefaults` — a JSON-typed column written later via a Step's own output
(`VariablesSchemaMapping`, below) uses a plain JS object, same as any other JSON column
(`docs/entities/input-data-filter.md`/self-test convention: never a bare JSON string scalar there).
That inner escaped string needs the same compact, no-space serialization as the outer
`VariablesDefaults` object itself — see `docs/best-practices.md`'s `VariablesDefaults`
section for why (DX diffs it as a raw string) and how it was actually confirmed (pulling
the real merge-diff response, not just eyeballing the DX UI's truncated preview).

**`VariablesDefaults: null` (bare, literal JSON `null`) is not a state the DX UI can ever
produce, and doesn't behave like "no defaults" — don't build a transfer this way.** The DX
UI **auto-generates** a `VariablesDefaults` object the moment a `VariablesSchema` is
picked, with every column present and set to `null` (e.g.
`{"OrderID":null,"CustomField1":null,...}`) — there is no UI path that leaves
`VariablesDefaults` itself as bare `null`. Setting it to bare `null` directly in a
hand-authored transfer JSON (bypassing that auto-generation) left `localVariable` `null`
for the *entire* Task Run, even after a Step wrote to the Local Variables via its own
`VariablesSchemaMapping` — but this is a UI-unreachable edge case, not a legitimate "no
defaults" scenario, and shouldn't be read as "`VariablesSchema` alone doesn't activate
Local Variables." **The realistic "no meaningful defaults" state is the all-`null`-per-column
object above** — confirmed with that shape, Local Variables work completely normally:
writes via `VariablesSchemaMapping` and both read methods below all behave identically to
a task with real default values.

**Open question:** what `localVariable.X`/`${LocalVariable.X}` actually return, per type,
for a column whose `VariablesDefaults` value is `null` and that hasn't been written yet —
not yet pinned down.

---

## Writing to a Local Variable — `VariablesSchemaMapping` (Step-level)

```json
{
  "VariablesSchemaMapping": { "<LV column name>": "<this step's own output column name>" }
}
```

A dict on the Step itself: after the step runs, each named Local Variable is overwritten
with the value from the **same step's own output** row. Confirmed mutable across a Task
Run — a later Step can write again with a different `VariablesSchemaMapping`, and a
subsequent read sees the new value, not the first one.

---

## Reading a Local Variable

Two independent mechanisms, confirmed both to reflect the current (possibly overwritten)
value:

1. **`localVariable.ColumnName`** — a predefined object available inside Script
   connectors (JS Mapper, Python, Node.js).
2. **`${LocalVariable.ColumnName}`** — a text placeholder, substituted into **any**
   Configuration field before it's used — same substitution family/timing as
   `${#<Code>}`/`${#SYSTEM_...}` (`docs/entities/variables.md`), not a JS-runtime feature.
   Note the syntax difference: top-level `Variables[]`/`SYSTEM` placeholders take a
   leading `#`, this one doesn't — three distinct placeholder families, don't mix them up.

### Gotchas (all confirmed against a live instance)

- **Always treat the placeholder's substituted text as an opaque string — quote it,
  never embed it bare/unquoted, regardless of the column's type.** Bare embedding
  (assuming it substitutes as a native JS literal) breaks in more than one way:
  - `Bool` substitutes as .NET's capitalized `True`/`False`, not JS's lowercase
    `true`/`false` — bare `${LocalVariable.BoolFlag}` becomes the JS identifier `True`,
    throwing `ReferenceError: True is not defined`.
  - A `JSON`-typed value's substituted text is real JSON (containing literal `"`
    characters, and — see the next bullet — sometimes real newlines) — embedding it
    inside a JS **double**-quoted string breaks that string on its own embedded quotes.
- **A `JSON`-typed value's placeholder text can span multiple real (not escaped) lines —
  capture it with a backtick template literal, not single or double quotes.** A value
  written via a Step's own output (`VariablesSchemaMapping`, not `VariablesDefaults`)
  substitutes as a 2-space-indented, pretty-printed multi-line string, same shape as the
  `localVariable.X` case below. Single quotes dodge the internal `"` problem but not this
  one — an embedded literal newline inside a single/double-quoted JS string is a
  `SyntaxError`, which fails the **whole** script (`FailedConnector`), not just that one
  field, since it's a parse-time error, not a runtime one — every other field in the same
  script silently reads back as missing/`undefined` too, which can look like an unrelated
  bug in whatever field happens to sit next to it in the source until you trace it back.
  Backticks tolerate both the internal `"` and the embedded newline.
- **`localVariable.X` on a `JSON`-typed column always returns a string, never a parsed
  object** — even though the value may have been written as a genuine object via a Step's
  `VariablesSchemaMapping` output. Always `JSON.parse()` before using/comparing it.
  Formatting of that string is not stable: it can be an exact pass-through of whatever
  string you supplied in `VariablesDefaults`, or the same freshly re-serialized, indented
  multi-line string mentioned above if the value arrived via a Step's own JS object output
  — **never compare the raw text directly, always parse-then-compare.**
- `DateTime` values substitute with full .NET tick precision (7 fractional digits, e.g.
  `2026-08-03T00:00:00.0000000`) — safe inside quotes, and JS's `Date` constructor parses
  it fine, but don't expect it to match your original input string byte-for-byte.

---

## Minimal example

```json
{
  "VariablesSchema": { "CopyID": "<CopyID of a DataSchema with e.g. a String column 'Note'>" },
  "VariablesDefaults": "{\"Note\":\"nothing yet\"}",
  "Steps": [
    {
      "Name": "Write note",
      "VariablesSchemaMapping": { "Note": "Message" },
      "OutputSchema": { "CopyID": "<schema with a 'Message' String column>" },
      "...": "connector returns [{ Message: \"hello\" }]"
    },
    {
      "Name": "Read note",
      "PrevStepCopyID": "<Write note's CopyID>",
      "...": "JS Mapper Statement can now read localVariable.Note === \"hello\""
    }
  ]
}
```
