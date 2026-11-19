# Sensitive column

A DataSchema column may carry `Sensitive`. It is a boolean beside `AllowNull`.
`IsSensitive` stays the company Variable flag ([variables.md](variables.md)).
`Sensitive` is not a column `Type`.

```json
{ "Order": 0, "Type": 2, "AllowNull": true, "Sensitive": true,
  "ID": 0, "Name": "Password", "CopyID": "<new UUID per column>" }
```

- Missing `Sensitive`, or `false`, stores the column as not sensitive. A transfer
  from before version 7 has no property; import reads that as false.
- A `Type: 7` column (nested table) is stored as not sensitive. A column inside
  that nested schema keeps its own flag.
- The flag stays on the column that holds the value. `InputSchemaMapping` does
  not copy it. A sensitive source mapped into a plain column stays visible
  there. A plain source mapped into a sensitive column is masked there.
- The only mask text is `********`. A sensitive scalar becomes that text. Null
  stays null. A `$dataRef` in a masked write becomes the same text and that
  write does not extract the file.

## Where the mask is written

- The task-run data snapshot and the local-variables snapshot. A
  `/debug-task-run` snapshot therefore shows `********` in that cell and does
  not expand `$dataRef` there.
- The endpoint's stored input and the stored output copy. On an endpoint bound
  to a task, the HTTP response returned to the caller keeps the original value.
  The run receives the parsed table with the original values.

The live row inside a running task, the payload sent to an agent, a debugger
run, and checkpoint storage keep the original value. A log line is free text,
so it stays as written. A large value already written to disk from the original
table stays until maintenance deletes the file.

## Endpoint with no bound task

The method's input schema decides. Properties match column names. There is no
input mapping.

- POST stores the masked body. The response to the caller is the new row id.
  The body is not returned.
- PUT and PATCH without an id return 404 and store nothing.
- PUT with an id replaces the row with the masked document.
- PATCH with an id masks the incoming JSON, then merges it.
- No schema, or a schema with no sensitive column, stores the original text.
- JSON that does not parse is stored unchanged.
- A sensitive column inside a nested table is masked in that nested object.
  Null stays null.

## Restart

A task run whose endpoint input schema contains a sensitive column cannot be
restarted by reading the stored body again. The message is: `Task run cannot
be restarted because its endpoint input contains sensitive values.`

## Transfer version

`TransferVersion` **7** is the file that can carry `Sensitive`. A download from
`rel-2025-03.018` or later is already version 7, and every column has the
property (`false` when the column is not sensitive, including every `Type: 7`
column). Keep both.

Set `Sensitive: true` only together with `TransferVersion` 7. An instance older
than `rel-2025-03.018` rejects version 7 (`Only transfer version 6 is
supported.`). A version 6 file has no such property, so the same column would
be stored as not sensitive.

A file with every column not sensitive may stay version 6. Version 6 still
imports on `rel-2025-03.018`. Leave `Sensitive` on a system schema column as it
was on the instance you copied the schema from.
