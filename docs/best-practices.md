# Best Practices — Config Transfer generation

Short, cross-cutting rules that apply across many transfers, not tied to one section of
`docs/transfer/config-transfer-format.md`.

---

## Secrets and instance-specific values — use `Variables[]`, not hardcoding

Full reference (structure, `${#<Code>}` templating, `IsSensitive`, predefined
`${#SYSTEM_...}` values, how this differs from Task-scoped Local Variables) now lives in
**`docs/entities/variables.md`** — read it whenever a transfer needs a secret (password, connection
string, API key, token) or an instance-specific value (company slug, base URL) that
shouldn't be hardcoded.

---

## Editing an existing transfer — preserve CopyIDs, don't regenerate from scratch

When modifying entities that already exist in a transfer that's been imported before,
keep their original `CopyID`s. If preserving them isn't practical and a full
regeneration is the only realistic option, ask first whether the goal is brand-new
tasks/steps/schemas/configurations or an edit of the existing ones — don't silently
reassign new IDs to make the generation easier.

**Why:** `CopyID` is the import matching key (§2 in `docs/transfer/config-transfer-format.md`) — insert vs.
update. Reassigning a fresh UUID to an entity that didn't conceptually change turns a
clean update into a delete+insert on the next import, even though nothing about it
actually changed. Any generator script meant to be run more than once against the same
import target should derive `CopyID`s deterministically (e.g. `uuid5` from a stable key
per entity) instead of `uuid4()` on every run.

---

## Give every named entity a unique, meaningful `Name`

Configuration, DataSchema, Endpoint, Task, TaskGroup, EndpointGroup, Step - whatever
carries a `Name` field - give it something distinct and descriptive. Not a placeholder,
not the same generic label copy-pasted across many entities, and never `null`
(`docs/transfer/config-transfer-format.md` §5 - a `null` Configuration `Name` imports fine but the DX UI
rejects it the moment anyone tries to save/edit it).

**Why:** these names are how entities show up in DX UI lists and search - a page of
identically-named or blank entries is unusable when someone (you, in three months, or a
teammate) needs to find or troubleshoot a specific one.

---

## `Task.VariablesDefaults` — serialize compactly, no spaces

`VariablesDefaults` specifically (see `docs/entities/local-variables.md`) should be serialized
**compactly** - no space after `:` or `,` - matching the format DX itself produces
(`{"ID":null,"Name":null,...}`), not a pretty-printer's default spacing
(`{"ID": null, "Name": null, ...}`).

**Why:** DX's "Changes" diff dialog compares this field as a raw string, not
semantically-parsed JSON. A value that's semantically identical to what's already on the
instance but serialized with different whitespace still shows up as changed on every
re-import - a noisy false-diff. **Confirmed specific to `VariablesDefaults`** - other
double-encoded JSON string fields (`InputDataFilter`, `*OutputMapping`, a
`Configuration`'s own JSON content, ...) haven't shown this problem; don't generalize the
compact-serialization habit to those without a similar confirmed diff issue. Preserve key
order too where it's known (e.g. matching the schema's own column order) - order
differences show up in the diff the same way.

**Applies one layer deeper too — a `JSON`-typed column's own value inside
`VariablesDefaults` is itself an escaped JSON string (`docs/entities/local-variables.md`'s "third
layer of encoding"); that inner string needs the same compact, no-space serialization.**
Confirmed by pulling the actual `POST /api/admin/Transfer/{id}/MergeResult` diff response
directly (not just the DX UI's truncated preview) — the *only* remaining byte-level
difference on an otherwise-clean `VariablesDefaults` diff was one space inside that inner
string (`"marker": "..."` vs `"marker":"..."`).

---

## Configuration arrays

Every array property in a Configuration JSON string is present and is a JSON array. An empty list is `[]`. Omitting the property or sending JSON `null` is wrong.

That omission deserializes to a null list. A connector that walks the list then fails the step before the request is sent: `ArgumentNullException`, message `Value cannot be null.`, `ParamName: source`.

`connector-info.py` writes `[]` for every array property in the configuration skeleton. A configuration string that still lacks one of those properties is not ready to upload.

## HTTP calls — Advanced Rest API Connector

An HTTP call uses **Advanced Rest API Connector** (`fa4f643f-d1bf-48a3-92ed-fda1a682aa6d`). It is the evolution of Rest API Connector (`9ef583db-7342-4013-82c7-aeec32fdedc6`). Take the version from `data/connectors.json`: the newest one that this instance has installed. The action follows the response body: `json`, `text`, or `base64`.
