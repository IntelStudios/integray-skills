# Integray connector project – AI rules

## Purpose of this file

This file gives high‑level instructions for AI assistants (and humans) working inside this connector project. It explains what Integray is, what an Integray connector looks like, which files are important here, and how to safely modify them.

- Use this document together with `data/connector-dev.schema.json`.
- Prefer being precise and conservative rather than guessing.
- When something is unclear, propose options and ask the user which one they want.

---

## What is Integray?

Integray is an integration platform that connects systems and applications and moves data between them. Users model **tasks** that consist of **steps**, and each step uses a **connector** and one of its **actions** to call an external system, transform data, or perform some logic.

- **Main website**: [https://integray.com](https://integray.com)
- **Learn portal**: [https://learn.integray.app](https://learn.integray.app)
- **Connector documentation**: [https://learn.integray.app/connectoracademy/](https://learn.integray.app/connectoracademy/)
- **Example library**: [https://learn.integray.app/examplelibrary/](https://learn.integray.app/examplelibrary/)

Important ideas:
- Integray works with **data collections** (tables) flowing through steps.
- Connectors describe **what** can be done (actions, inputs, outputs, configuration).
- Configuration and data schemas describe **how** data and settings look.

You are usually helping someone who is **developing or maintaining a connector** for this platform.

### ICR Developer (web UI)

Integray provides a dedicated web application called **ICR Developer** at **https://icr.integray.app**.  
This is the primary UI for connector developers and publisher companies.  
Through this application you can:

- View and manage your **channels**  
- Upload and update **connectors**, **configuration schemas**, and **data schemas**  
- View all your entities in the **My Entities** panel  
- Inspect and copy exact JSON definitions of schemas stored in the repository  
- Upload icons and documentation for channels  
- Promote PRIVATE channels to PUBLIC channels  
- Manage access tokens for **restricted** channels  
- Access automatically generated **OpenAPI docs** for the repository (DEV or PROD)

### Integray Connector CLI

In addition to the web UI, Integray provides a command-line tool called **Integray Connector CLI** (`Integray.Connector.CLI`).  
The CLI can be used for:

- Creating new connector projects from templates (`integray connector new`)
- Building and packaging connectors (`integray connector pack`)
- Publishing connectors to channels (`integray connector publish`)
- Managing channels (create, list, delete, promote, set active channel)
- Managing entities (list, add configuration schemas and data schemas)
- Managing authentication tokens

The CLI is particularly useful for automated workflows, CI/CD pipelines, and developers who prefer command-line tools.  
Both the web UI (ICR Developer) and the CLI provide access to the same Integray Repository functionality.

For detailed CLI usage, see the [CLI usage](#cli-usage--how-to-talk-about-integray-commands) section below.

---

## What is an Integray connector?

An Integray connector is a .NET plugin – specifically a class (or set of classes) that implements the `IConnector` interface from the `Integray.Plugin` NuGet package and knows how to talk to one specific external system (API, database, file storage, …). It is delivered as a **ZIP package** produced by the `integray connector pack` command.

Each connector package contains at least:
- `connector.json` – main metadata file describing the connector and its **actions**.

It may also contain:
- Zero, one or multiple **configuration schemas** (kind `Integray/ConfigurationSchema/1.0`).
- Zero, one or multiple **data schemas** (kind `Integray/DataSchema/1.0`).
- Optional documentation and icons in the `metadata/` folder.

A connector can work without configuration schemas and/or data schemas if it does not need them. They are only required when the connector or its actions actually use those schemas.

A connector can have multiple **actions**. Each action:
- Has a human‑readable name and a code.
- Has configuration references (which configuration schemas it needs).
- Has input / output schema references (which data schemas it uses).
- Can support different processing modes (bulk / row‑by‑row).

---

## Key files in this project

This project is a single Integray connector created from the SDK template. Typical important files:

- **`connector.json`**  
  Main metadata file for the connector. Describes actions, input/output schemas, configuration references and file references. Must validate against:
  - `https://icr.integray.app/schemas/connector.json`

- **`configuration.json`** (optional)  
  Optional configuration schema for connector‑level settings. The connector can work without it, or it can use multiple configuration schemas if needed. Any configuration schema must validate against:
  - `https://icr.integray.app/schemas/configuration.json`

  In every configuration schema, the property `"schema"` contains an NGX Schema Form definition.  
  This NGX Schema Form object describes the structure of the configuration UI in Integray:  
  form fields, validation rules, conditional visibility, layout, and allowed value structures.  
  The AI must not modify `"schema"` arbitrarily — only when the user explicitly asks —  
  and must keep it a valid NGX Schema Form document.

- **Additional configuration schemas** (optional)  
  Zero, one or many additional JSON files whose `$schema` points to `https://icr.integray.app/schemas/configuration.json`. These are used when actions need their own configuration schemas.

- **Data schemas**  
  Zero, one or many JSON files whose `$schema` points to `https://icr.integray.app/schemas/data-schema.json`. A connector does not have to define any data schemas if its actions do not require them.

- **`metadata/` folder**  
  Contains icons and markdown documentation files referenced from `connector.json` and its actions (for example `metadata/icon.svg`, `metadata/connector.md`, `metadata/action-description.md`).

Do **not** change `$schema` URLs unless the user explicitly asks for it.

## Channels in Integray (concept overview)

A connector package is always published **into a channel**.  
Channels define visibility, access level, and lifecycle of entities (connectors, configuration schemas, data schemas).

- **PUBLIC channels**  
  - Visible to all users  
  - Cannot be deleted  
  - Used for stable, production‑ready content  
  - A PRIVATE channel can be *promoted* into a PUBLIC one  

- **PRIVATE channels**  
  - Default type when creating a channel  
  - Editable, deletable, ideal for development and testing  
  - Entities can be moved to a PUBLIC channel during promotion  

- **Restricted channels**  
  - Require **access tokens** to read or modify entities  
  - Tokens can be created, listed, deleted and given expiration dates  
  - Used for sensitive or private content

- **Non‑restricted channels**  
  - Do not require tokens  
  - Suitable for public or low‑sensitivity data  

Channels also support:  
- Uploading icons and markdown descriptions  
- Managing entity overrides  
- Viewing connectors, configuration schemas and data schemas assigned to the channel  

## Connector Lifecycle in Integray

The full lifecycle of an Integray connector works as follows:

1. **Developer installs the Integray CLI** and generates a connector project from the template.
2. **Developer implements and tests** the connector.
3. **Developer packages the connector** using `integray connector pack`.
4. **Developer requests a developer account** at support@integray.app to gain access to the Integray Repository (ICR).
5. **Developer creates a channel** either:
   - In the ICR Developer UI at https://icr.integray.app/, or
   - Using the CLI: `integray channel new <CHANNEL_NAME>`
6. **Developer publishes the connector package** into the channel using `integray connector publish`.
7. **Integray platform users subscribe to the channel** inside the Integray administration UI.
8. **Users install the connector**—either manually or through an automated background installation job.
9. **Users add steps in tasks** and select this connector and its actions to use it in real integrations.

---

## How references work

When editing metadata, always keep references consistent:

### File references in `connector.json`

These fields are **paths to files** inside the package (not literal text):

- `metadata.icon` → file in `metadata/` (for example `metadata/icon.svg`).
- `metadata.description` → file in `metadata/` (for example `metadata/connector.md`).
- `actions[].metadata.icon` → file in `metadata/` (for example `metadata/action-icon.svg`).
- `actions[].metadata.description` → file in `metadata/` (for example `metadata/action-description.md`).

If you create or rename a file reference, also make sure the file actually exists or clearly tell the user they need to create it.

### Configuration schema references

- `actions[].configurationRefs[]` contain `guid` + `version`.  
- These must match **configuration schema** files in the package with `kind = "Integray/ConfigurationSchema/1.0"`.

Do **not** invent random GUIDs for existing schemas. If the user is creating a **new** schema, you may generate a new GUID on request and keep it stable across all references.

### Data schema references

- `actions[].inputSchema.schemaRef` and `actions[].outputSchema.schemaRef` contain `guid` + `version`.  
- These must match **data schema** files in the package with `kind = "Integray/DataSchema/1.0"`.

### Nested data schemas

In data schema files:

- Columns with `type = "table"` must have `tableRef.guid` + `tableRef.version`.  
- These must reference another data schema file (`kind = "Integray/DataSchema/1.0"`) included in the package.


Configuration schemas (`Integray/ConfigurationSchema/1.0`) **do not** reference other entities.

---

## How actions use data schemas

In `connector.json`, each action can declare how it uses **input** and **output** data schemas via the `inputSchema` and `outputSchema` objects. Both have the same structure:

- `mode`: controls whether a schema is used and how strictly it is enforced.
- `schemaRef`: (optional) reference to a concrete data schema (by `guid` + `version`).

### Modes for `inputSchema.mode` and `outputSchema.mode`

These modes come directly from the official connector JSON Schema (`https://icr.integray.app/schemas/connector.json`):

- `none`  
  - The action does **not** work with input / does **not** produce output.  
  - Users cannot assign a data schema when configuring the step in Integray.

- `required`  
  - The action works with data whose structure is **fixed** and cannot be changed in Integray.  
  - `schemaRef` **must** be provided and must reference a specific data schema (`kind = "Integray/DataSchema/1.0"`).  
  - Users cannot choose a different schema when configuring the step.

- `optional`  
  - The action can work **with or without** a data schema.  
  - Users may select a data schema in Integray, but they are not forced to.  
  - If a schema is selected, it is referenced via `schemaRef.guid` + `schemaRef.version`.

- `mandatory`  
  - Users **must** select a data schema when defining the step, but the connector does not enforce any specific one.  
  - Any compatible data schema can be chosen; the connector should be written to handle different shapes.  
  - Integray enforces that some schema is selected, but not which one.

### Relationship between actions and data schemas

- `inputSchema` describes the structure of the **input collection** delivered to the action.  
- `outputSchema` describes the structure of the **output collection** produced by the action.  
- Both always describe **collections of records**, not single objects.
- When `mode` is `required`, there must be a matching data schema file (with the correct `guid` + `version`) in the package.
- When `mode` is `optional` or `mandatory`, Integray lets the user pick a data schema whose metadata must be present in the package.

If you propose changes to these modes or to `schemaRef` values, clearly explain the impact on how the action will be configured and used in existing tasks.

---

## Working with GUIDs and versions

- `guid` is a **stable identity** of a connector, configuration schema or data schema. It is reused for all versions of the same entity.
- `version` uses semantic versioning (`x.y.z`) and **must change** when the entity changes.

-When editing files:
- The GUID must be globally unique across all publisher companies, channels and all metadata entities in Integray.

- Do **not** change existing GUIDs unless the user says they are creating a **new** entity.
- If you change the structure of an entity (for example, data schema columns), suggest bumping the version.
- If unsure, ask the user whether they are updating an existing entity or creating a new one.

---

## Source generators – how configuration and data schemas produce .NET classes

The Integray Connector SDK contains **source generators** that automatically create strongly typed C# classes based on the connector's configuration schemas and data schemas. These generators run at compile time and let developers work with normal C# objects instead of raw dictionaries.

### Example: configuration schema → generated class

Given a configuration schema like this:

```json
{
  "$schema": "https://icr.integray.app/schemas/configuration.json",
  "kind": "Integray/ConfigurationSchema/1.0",
  "guid": "c07186b4-365a-4182-a339-f7a73ea95750",
  "version": "1.0.0",
  "name": "Calculator Settings",
  "metadata": {
    "defaultSaveType": "public"
  },
  "schema": {
    "properties": {
      "Operation": {
        "type": "string",
        "title": "Operation",
        "widget": "select",
        "oneOf": [
          { "enum": ["addition"], "description": "Add numbers" },
          { "enum": ["subtraction"], "description": "Subtract numbers" },
          { "enum": ["multiplication"], "description": "Multiply numbers" },
          { "enum": ["division"], "description": "Divide numbers" }
        ],
        "default": "addition"
      },
      "Round": {
        "type": "boolean",
        "title": "Round results",
        "default": false
      },
      "Precision": {
        "type": "integer",
        "title": "Decimal places",
        "default": 2,
        "visibleIf": { "Round": [true] }
      }
    }
  }
}
```

the generator produces a strongly typed C# configuration model similar to this:

```csharp
// <auto-generated/>
#nullable enable
using System;
using System.Text.Json.Serialization;
using Integray.Connector.v2.Models;

namespace Integray.Connector.Generated.Configurations;

[IntegrayEntity("c07186b4-365a-4182-a339-f7a73ea95750", 1, 0, 0)]
public class CalculatorSettingsConfiguration
{
    public string? Operation { get; set; }
    public bool? Round { get; set; }
    public int? Precision { get; set; }
}
```

### Example: data schema → generated classes

Given a data schema like this:

```json
{
  "$schema": "https://icr.integray.app/schemas/data-schema.json",
  "kind": "Integray/DataSchema/1.0",
  "guid": "d92fa9b4-f75d-447e-8825-8a1bdda4a274",
  "version": "1.0.0",
  "name": "Calculator Input",
  "metadata": {},
  "columns": [
    { "name": "A", "type": "decimal", "constraints": { "allowNull": false } },
    { "name": "B", "type": "decimal", "constraints": { "allowNull": false } }
  ]
}
```

the generator produces a row model and helper extensions similar to this:

```csharp
// <auto-generated/>
#nullable enable
using System;
using System.Collections.Generic;

namespace Integray.Connector.Generated.DataModels;

public class CalculatorInputRowModel
{
    public decimal A { get; set; }
    public decimal B { get; set; }

    public static CalculatorInputRowModel FromDictionary(IDictionary<string, object?> dictionary)
    {
        var model = new CalculatorInputRowModel();

        if (dictionary.TryGetValue("A", out var aValue))
        {
            model.A = Convert.ToDecimal(aValue ?? 0.0m);
        }

        if (dictionary.TryGetValue("B", out var bValue))
        {
            model.B = Convert.ToDecimal(bValue ?? 0.0m);
        }

        return model;
    }
}

public static class CalculatorInputRowModelExtensions
{
    public static Dictionary<string, object?> ToDictionary(this CalculatorInputRowModel model)
    {
        return new Dictionary<string, object?>
        {
            { "A", model.A },
            { "B", model.B }
        };
    }
}
```

### Configuration schema generator

For every configuration schema whose `$schema` is:

- `https://icr.integray.app/schemas/configuration.json`

the SDK generates a C# class named:

- `<SchemaName>Configuration` (for example `CalculatorSettingsConfiguration`).

Key points:

- Each property from the NGX Schema Form `schema.properties` section becomes a C# property (for example `Operation`, `Round`, `Precision`).
- Basic JSON types are mapped to C# types (`string`, `bool`, `int`, `decimal`, etc.).
- Generated configuration classes are placed in the `Integray.Connector.Generated.Configurations` namespace.
- Generated classes are annotated with the `IntegrayEntity` attribute, which defines:
  - A stable **GUID** identifying the configuration schema
  - A **semantic version** (major, minor, patch)
- The `IntegrayEntity` attribute is the single source of truth for configuration identity and is used internally by the SDK, runtime, and test infrastructure to reliably associate configuration instances with their corresponding schema definitions.
- UI‑only features such as `visibleIf` influence how the form behaves in Integray, but do **not** change the generated C# members.

When you modify a configuration schema:

- Renaming or removing a property changes the generated C# model and can break existing code.
- Adding new properties is generally safe, but the connector code may need to be updated to use them.
- If you make structural changes, consider bumping the schema `version`.

### Data schema generator

For every data schema whose `$schema` is:

- `https://icr.integray.app/schemas/data-schema.json`

the SDK generates:

- `<DataSchemaName>RowModel`
- `<DataSchemaName>RowModelExtensions`

For example, a "Calculator Input" schema with decimal columns `A` and `B` will produce:

- `CalculatorInputRowModel` with `decimal A` and `decimal B` properties.
- Extension methods for converting between `CalculatorInputRowModel` and `Dictionary<string, object?>` so it can be easily plugged into the Integray data interfaces.

Key points:

- Each column in `columns` becomes a C# property; the type is derived from the column `type` (for example `int`, `string`, `bool`, `decimal`).
- The generator creates helper methods (such as `FromDictionary` and `ToDictionary`) to map between raw Integray row data and the strongly typed model.
- For nested tables (`type = "table"`), additional row models may be generated to represent child collections.

When you modify a data schema:

- Changing column names or types changes the generated C# model and can be a breaking change for existing connector code.
- Adding new columns is usually backward compatible, but the connector might need to be updated to use them.
- Removing or renaming columns should be done carefully and ideally accompanied by a version bump.

### Why this matters for AI helpers

Whenever you help the user modify configuration or data schemas:

- Keep in mind that these changes affect **generated C# code** as well as Integray metadata.
- Be explicit when a change will require connector code updates (for example, a renamed column or configuration property).
- Prefer incremental changes and clearly describe the impact on both the Integray UI and the generated .NET types.

---

## Implementing a connector in C# code

When helping users implement connector logic, guide them through the following patterns and practices.

### Basic connector structure

Every connector must inherit from `IntegrayConnector` and implement the `ProcessInternalAsync` method:

```csharp
using Integray.Connector.SDK;
using Integray.Connector.v2.Interfaces;

public class MyConnector : IntegrayConnector
{
    protected override async Task<IProcessResult> ProcessInternalAsync(IConnectorContext context)
    {
        // Implement connector logic here
        return GetEmptyResult();
    }
}
```

### Accessing input data

The connector receives input data as tables. Use extension methods to access them:

- **Primary input** – the first input table:
  ```csharp
  var input = context.GetPrimaryInput();
  // or use the property:
  var input = PrimaryInput;
  ```

- **Additional inputs** – other input tables (if any):
  ```csharp
  var additionalInputs = context.GetAdditionalInputs();
  ```

- **Check if input is empty**:
  ```csharp
  if (input == null || input.IsEmpty)
  {
      return GetEmptyResult();
  }
  ```

### Working with strongly-typed input rows

For each data schema, the SDK generates extension methods that convert input tables to strongly-typed row models:

```csharp
using Integray.Connector.Generated.DataSchemas;

// Convert input table to strongly-typed row models
foreach (var row in input.ToCalculatorInputRowModels())
{
    // Access properties directly
    decimal valueA = row.A;
    decimal valueB = row.B;
    // Process the row...
}
```

The extension method name follows the pattern: `To<DataSchemaName>RowModels()`.

### Accessing configurations

For each configuration schema, the SDK generates extension methods on the `Configurations` dictionary:

```csharp
using Integray.Connector.Generated.Configurations;

// Get configuration (extension method on Configurations dictionary)
var config = Configurations.GetCalculatorSettings();
// or via context:
var config = context.Configurations.GetCalculatorSettings();

// Access configuration properties
string operation = config.Operation ?? "addition";
bool shouldRound = config.Round ?? false;
int? precision = config.Precision;
```

The extension method name follows the pattern: `Get<SchemaName>()`.

### Creating output data

Create a result object and add rows to the output table:

```csharp
// Create result with output table
var result = ResultFactory.Create();

// Create output row model
var outputRow = new CalculatorOutputRowModel 
{ 
    Result = calculatedValue 
};

// Add row to output (extension method generated for each output schema)
result.Output!.AddRow(outputRow);

// Or add multiple rows at once
result.Output!.AddRows(outputRows);
```

The `AddRow` and `AddRows` extension methods are generated for each data schema and accept the strongly-typed row model.

### Logging

Use the `Log` property (available after `ProcessInternalAsync` is called) with appropriate log levels:

```csharp
// Check if log level has listeners before expensive operations
if (Log.HasDebugListener())
{
    Log.Debug($"Processing {input.Rows!.Count} rows");
}

Log.Trace("Detailed execution step");
Log.Debug("Technical details");
Log.Info("High-level information for users");
Log.Warn("Non-fatal issue occurred");
Log.Error("Error occurred");
Log.Critical("Severe failure");
```

Always check for listeners before constructing expensive log messages (string concatenation, serialization, etc.).

### Returning results

- **Empty result** (no output data):
  ```csharp
  return GetEmptyResult();
  ```

- **Result with output data**:
  ```csharp
  var result = ResultFactory.Create();
  // Add rows to result.Output!
  return result;
  ```

- **Result with checkpoint** (for incremental processing):
  ```csharp
  var result = ResultFactory.Create();
  result.CheckPoint = "last-processed-id";
  return result;
  ```

### Working with checkpoints

Checkpoints allow connectors to resume processing from where they left off, enabling incremental data processing.

To enable checkpoints, declare the `"checkpoint"` feature in `connector.json`:

```json
{
  "actions": [
    {
      "code": "syncData",
      "features": ["checkpoint"],
      ...
    }
  ]
}
```

Without this feature declaration, `CheckpointManager` is always empty regardless of previous runs.

#### Using CheckpointManager

`CheckpointManager` is available directly as a property on `IntegrayConnector` — no manual instantiation is needed. It is automatically initialized from the previous run's checkpoint data.

- **Read a value that is guaranteed to exist** (throws `KeyNotFoundException` if missing):
  ```csharp
  DateTime lastSync = CheckpointManager.GetValue<DateTime>("lastSync");
  ```

- **Read a value with a fallback** (safe for first run or missing keys):
  ```csharp
  DateTime lastSync = CheckpointManager.GetValueOrDefault("lastSync", DateTime.MinValue);
  ```

- **Check existence before reading**:
  ```csharp
  if (CheckpointManager.ContainsKey("lastProcessedId"))
  {
      string lastId = CheckpointManager.GetValue<string>("lastProcessedId");
  }
  ```

- **Write values**:
  ```csharp
  CheckpointManager.SetValue("lastSync", DateTime.UtcNow);
  CheckpointManager.SetValue("lastProcessedId", currentId);
  ```

- **Save checkpoint in result**:
  ```csharp
  var result = ResultFactory.Create();
  result.CheckPoint = CheckpointManager.ToString();
  return result;
  ```

- **Simple string checkpoint** (for simple cases where structured data is not needed):
  ```csharp
  var result = ResultFactory.Create();
  result.CheckPoint = lastProcessedId;
  return result;
  ```

If the checkpoint data from the previous run is corrupted or cannot be parsed, a warning is logged automatically and `CheckpointManager` behaves as if no checkpoint exists (`IsEmpty = true`).

Checkpoints are useful for:
- Incremental data synchronization
- Resuming after failures
- Processing large datasets in batches
- Tracking pagination state

### Handling multiple actions

If your connector supports multiple actions, check the `Action` property:

```csharp
protected override async Task<IProcessResult> ProcessInternalAsync(IConnectorContext context)
{
    return context.Action switch
    {
        "action1" => await ProcessAction1(),
        "action2" => await ProcessAction2(),
        _ => throw new ArgumentException($"Unknown action: {context.Action}")
    };
}
```

### Accessing context metadata

The context provides metadata about the execution environment:

```csharp
// Check if running in a task (not standalone)
if (context.HasTaskRunId())
{
    long taskRunId = context.GetTaskRunId()!.Value;
}

// Access endpoint token information (if available)
long? tokenId = context.GetEndpointTokenId();
string? tokenName = context.GetEndpointTokenName();

// Access endpoint data ID (if the step was triggered by endpoint data)
Guid? endpointDataId = context.GetEndpointDataId();

// Access timeout and cancellation token
TimeSpan timeout = Timeout;
CancellationToken cancellationToken = CancellationToken;
```

### Best practices

1. **Always check for empty input** before processing
2. **Use strongly-typed models** generated from schemas instead of raw dictionaries
3. **Check log listeners** before expensive logging operations
4. **Handle nulls** – configuration and data schema properties are nullable
5. **Use async/await** properly for I/O operations
6. **Respect cancellation tokens** for long-running operations
7. **Throw meaningful exceptions** with clear error messages
8. **Return empty results** when there's nothing to process

---

## Testing connectors

Integray connectors can be tested without running the full Integray runtime.  
For this purpose, the **Integray Connector Test SDK** provides a special execution context and fluent builder APIs.

The Integray Connector Test SDK is designed to mirror the runtime execution model as closely as possible, while still giving the test full control over inputs, configurations, outputs and logging behavior.

Tests are expected to construct the execution context explicitly and decide which diagnostic features (such as log capture or log forwarding) should be enabled.

### TestConnectorContext

During tests, connectors are executed using `TestConnectorContext` instead of the runtime context.  
This context is fully controlled by the test and allows:

- Supplying inputs and outputs
- Providing generated configuration objects
- Capturing logs produced during execution
- Forwarding logs to the test framework output
- Controlling how logs are handled (captured in memory, forwarded to test output, or both)
- Accessing structured log records after execution for assertions

Logging behavior is fully opt-in and configured via `TestConnectorContextBuilder`. By default, logs are neither captured nor written to any output.

### Creating a test context

A test execution context is created using the `TestConnectorContextBuilder`.  
Logging behavior is opt-in and can be configured depending on what the test needs to observe.

#### Capture logs and write them to test output
```csharp
var context = TestConnectorContextBuilder
    .Create()
    .CaptureLogs()
    .WithLogOutput(testOutput)
    .Build();
```

This setup enables:
- **In-memory log capture** – logs can be asserted after execution
- **Live log output** – logs are written to the test framework output (for example xUnit)

#### Write logs to test output only
```csharp
var context = TestConnectorContextBuilder
    .Create()
    .WithLogOutput(testOutput)
    .Build();
```

This setup forwards logs directly to the test framework output, but **does not store them in memory**.  
It is useful when you only want real-time visibility during test execution and do not need to inspect logs programmatically.

#### Capture logs only
```csharp
var context = TestConnectorContextBuilder
    .Create()
    .CaptureLogs()
    .Build();
```

This setup captures logs in memory without writing them to the test output.  
It is useful for tests that **assert on log content** but want to keep the test output clean.

### Logging in tests

Logging plays a key role when developing and debugging connectors.  
The Integray Connector Test SDK provides two complementary logging mechanisms.

The logging system intentionally separates **log generation**, **log capture**, and **log output**.  
This separation allows tests to choose between silent execution, assertion-based inspection, human-readable diagnostics, or any combination of these approaches.

#### Capturing logs

Calling `CaptureLogs()` enables in-memory collection of log records.

Captured logs are accessible after execution via:

```csharp
context.Logs
```

This collection is read-only and contains structured `TestLogRecord` entries, suitable for assertions in tests.

#### Writing logs to test output

Calling `WithLogOutput(...)` forwards all log messages to the test framework output (for example xUnit's `ITestOutputHelper`).

This is especially useful when:
- Investigating failing tests
- Understanding execution flow
- Debugging complex connector logic

#### Combining both

Both mechanisms can be enabled at the same time:

```csharp
TestConnectorContextBuilder
    .Create()
    .CaptureLogs()
    .WithLogOutput(testOutput)
    .Build();
```

### Log levels and their intended usage

Connectors should use log levels consistently to communicate intent and severity.  
Each log level represents not only the seriousness of an event, but also its intended audience.

Proper use of log levels improves test diagnostics, production observability, and overall connector maintainability.

| Log level     | Description |
|---------------|-------------|
| **Trace (0)** | In-depth execution details such as internal decisions, branches, loops, retries, and detailed flow control. Intended primarily for developers during deep debugging. Usually too verbose for normal runs. |
| **Debug (1)** | Technical details and logical steps (for example parsing input, mapping fields, preparing requests). Useful for developers and administrators when troubleshooting. Less verbose than Trace. |
| **Information (2)** | High-level, user-friendly information about what the connector is doing (for example action start/end, summaries). Intended to be understandable and useful for end users. |
| **Warning (3)** | Non-fatal and recoverable issues (fallback logic used, optional data missing, partial success). Execution continues, but attention may be required. |
| **Error (4)** | Major unrecoverable errors that cause the current action or task to fail. Execution cannot continue normally. |
| **Critical (5)** | Severe failures such as initialization errors or corrupted runtime state. Execution cannot proceed. Should be used sparingly. |

The **Critical** log level should be reserved for exceptional cases such as startup failures or corrupted runtime state.  
Overuse of this level reduces its diagnostic value.

---

## IDE and editor setup

When you suggest how the user should work with this connector project in an editor, keep in mind which IDE they might be using and how Integray SDK source generators behave.

### Recommended IDE extensions

- **Visual Studio Code**
  - Recommend installing the official C# Dev Kit extension from Microsoft.
  - Extension: `ms-dotnettools.csdevkit`
  - Marketplace: https://marketplace.visualstudio.com/items?itemName=ms-dotnettools.csdevkit

- **Cursor**
  - Recommend installing the C# extension tuned for .NET development in Cursor.
  - Extension ID: `dotnetdev-kr-custom.csharp`
  - Mention that this improves IntelliSense, navigation and basic refactorings for C#/.NET projects.

### Source generators and generated namespaces (important)

This project uses **Integray SDK source generators** which generate C# types at build time under namespaces such as:

- `Integray.Connector.Generated.Configurations`
- `Integray.Connector.Generated.DataModels`
- and other `Integray.Connector.Generated.*` namespaces

**Do not remove or "optimize away" `using` directives that reference `Integray.Connector.Generated.*`.**

Some IDEs and AI-assisted editors (including Cursor) may incorrectly mark these `using` directives as unused or unresolved, because generated code may not be visible until build time. Removing them can break compilation even if the IDE reports them as unused.

If a `using` directive references `Integray.Connector.Generated.*`, assume it is required unless the generated code has been intentionally removed and the project no longer relies on Integray SDK source generators.

### .NET 10 SDK version requirement

When working with Integray connector projects that use SDK source generators, ensure that a **sufficiently recent .NET 10 SDK** is installed.

Observed behavior:
- Older .NET 10 SDK patch versions may fail to resolve generated types during build
- Always prefer the latest available .NET 10 SDK patch version

If build errors report missing namespaces or types under `Integray.Connector.Generated.*`, **first verify the installed SDK version** using:

```bash
dotnet --info
```

---

## CLI usage – how to talk about `integray` commands

This project uses the **Integray Connector CLI** (`Integray.Connector.CLI` dotnet tool).

The CLI is organized into domains, each responsible for a specific area of functionality:

- **Connector commands** – work with local connector projects
- **Channel commands** – manage repository channels (requires authentication)
- **Entity commands** – browse and add entities (configurations and data schemas) from repository channels
- **Token commands** – manage authentication token on the local machine

### General guidance

- Prefer commands with an explicit path to the `.csproj` file, for example:
  - `integray connector pack ./MyConnector/MyConnector.csproj`
- Folder‑only form is supported but can be ambiguous if multiple projects exist. Only use it if the user clearly wants that.
- For detailed help on a specific domain, run: `integray <domain>`

### Authentication and token handling

Most commands that interact with the Integray repository require an authentication token.  
A valid Integray API token can be provided in one of the following ways (listed by priority):

1. **Command-line option** – pass the token explicitly using `--token` (or `-t`):
   ```bash
   integray connector publish ./MyConnector.zip --channel <CHANNEL_ID> --token <TOKEN>
   ```

2. **Environment variable** – set the `INTEGRAY_TOKEN` environment variable:
   ```bash
   export INTEGRAY_TOKEN=<TOKEN>
   ```

3. **Local token storage (recommended)** – store the token locally:
   ```bash
   integray token set <TOKEN>
   ```
   Once stored, the token is used automatically for all commands that require authentication.

### Active channel configuration

The CLI can remember an active channel for the current solution by storing it in a local `.integray` configuration file:

- Set the active channel: `integray channel set <CHANNEL_GUID>`
- Show the current channel: `integray channel current`
- Clear the active channel: `integray channel clear`

When both a token and an active channel are configured, you can use simplified commands without passing `--token` or `--channel` parameters.

### Connector commands

#### Create a new connector project
```bash
integray connector new --template Calculator --name MyCalculator ./MyCalculator
```

Available templates:
- `Calculator` – demonstrates input/output data, configurations and logging
- `Empty` – minimal connector template without any data or configurations
- `GitHub` – demonstrates how to call a public REST API, retrieve and parse output data

#### Package a connector

**Full form:**
```bash
integray connector pack ./MyConnector/MyConnector.csproj
integray connector pack ./MyConnector/MyConnector.csproj -o ./dist/MyConnector.zip
```

**Short form (when in project directory):**
```bash
integray connector pack
```

The CLI remembers the last successfully built package and reuses it by default when no package path is provided.

#### Publish a connector

**Full form (with explicit parameters):**
```bash
integray connector publish ./MyConnector.zip --channel <CHANNEL_ID> --token <TOKEN>
```

**Short form (with stored token and active channel):**
```bash
integray connector publish
```

When using the short form, the CLI will:
- Use the last produced package from `integray connector pack`
- Use the active channel stored in `.integray`
- Use the stored token (or environment variable)

### Channel commands

All channel commands require authentication.

- `integray channel new <NAME>` – create a new private channel
- `integray channel list` – list channels accessible with the current token
- `integray channel delete <CHANNEL_GUID>` – delete a private channel
- `integray channel promote <CHANNEL_GUID>` – promote content from a private channel to a public channel
- `integray channel set <CHANNEL_GUID>` – set the active channel for the current solution (stored in `.integray`)
- `integray channel current` – show the currently active channel for the current solution
- `integray channel clear` – clear the active channel for the current solution

### Entity commands

- `integray entity list` – list available entities (configurations and data schemas), with filtering options
- `integray entity add <ENTITY_GUID>` – download an entity and add it to the connector project metadata

### Token commands

- `integray token set <TOKEN>` – store an Integray API token locally for automatic use
- `integray token delete` – remove the stored Integray API token

### CLI version hygiene

When the user hits unexpected behavior with the CLI:
- Suggest checking the installed version with:
  - `integray --version`
- If the tool seems outdated, recommend updating via:
  - `dotnet tool update -g Integray.Connector.CLI`

You do **not** need to check the version on every single command, but it is good to remind the user occasionally when troubleshooting.

---

## Behaviour guidelines for AI in this project

When helping with this project:

1. **Validate against schemas mentally**  
   - Follow the structure from the official schemas at:
     - `https://icr.integray.app/schemas/connector.json`
     - `https://icr.integray.app/schemas/configuration.json`
     - `https://icr.integray.app/schemas/data-schema.json`
   - Do not introduce properties that are not defined there.

2. **Be conservative with breaking changes**  
   - If a change could break existing tasks (for example, renaming a column or changing a data type), clearly warn the user.

3. **Keep file paths and references in sync**  
   - When touching `metadata/` references, make sure file paths and file names match.
   - When touching GUID + version references, make sure there is a matching metadata file.

4. **Ask instead of guessing**  
   - When multiple designs are possible (for example, several ways to model a schema), describe the options and ask which one fits the user's intentions.

5. **Respect user ownership**  
   - Do not silently rewrite large parts of `connector.json`, configuration or data schemas.  
   - Make focused, well‑explained edits.

---

## Quick summary for future you

- Integray is an integration platform; this project is a single connector for it.
- `connector.json`, configuration schemas and data schemas must match official JSON Schemas hosted under `https://icr.integray.app/schemas/`.
- File paths in metadata point to files in the `metadata/` folder, not inline text.
- Configuration and data schemas are referenced by `guid` + `version`; keep those stable and consistent.
- Source generators create strongly-typed C# classes from JSON metadata; generated configuration classes use the `IntegrayEntity` attribute for identity.
- Connectors can be tested using the Test SDK with `TestConnectorContextBuilder`; logging behavior is opt-in.
- Prefer explicit `.csproj` paths in `integray connector pack` commands and help the user keep their CLI tool up to date.
