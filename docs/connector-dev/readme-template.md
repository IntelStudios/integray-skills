## Integray Connector Project

This repository is a starter project for building an **Integray connector** in **.NET 10**.  
A connector is a .NET plugin that lets Integray communicate with an external system such as an API, database, file storage, or SaaS service.

The project was generated using **[Integray.Connector.CLI](https://www.nuget.org/packages/Integray.Connector.CLI)** and already includes everything you need to implement, test, package, and publish your connector using the Integray Connector SDK.

---

## Quick start: what to do now

If you have just created this project using the Integray CLI, a typical workflow is:

Before you start, make sure you have:

- **.NET 10 SDK** installed (`dotnet --info` should show a .NET 10 SDK).
- **Integray Connector CLI** available on your machine (you already used it to generate this project).

Then follow these steps:

1. **Explore the project structure** – see [Project Structure](#project-structure) to understand where the connector code and metadata live.
2. **Adjust connector metadata and schemas** – edit the JSON files under `Metadata/`:
   - `connector.json` for actions and schema references.
   - `configuration.json` for connector configuration UI (you can preview it via the config-schema sandbox).
   - `input-schema.json` / `output-schema.json` for input/output data shapes.
3. **Implement or update connector logic** – modify `Connector.cs` using the patterns in:
   - [Implementing the Connector](#implementing-the-connector)
   - [Working With Input Data](#working-with-input-data)
   - [Working With Configurations](#working-with-configurations)
   - [Creating Output Data](#creating-output-data)
4. **Run and extend tests** – open the `Integray.Connector.<connector_name>.Tests` project and add tests using the Integray Connector Test SDK (see [Testing the Connector](#testing-the-connector)).
5. **Build and package the connector** – run `dotnet build` and then `integray connector pack` to produce a ZIP package.
6. **Prepare a channel and token** – in Integray Repository (ICR) create or select a channel, obtain an API token, and configure them locally (see [Publishing the Connector](#publishing-the-connector)).
7. **Publish your connector** – use `integray connector publish` to upload the package to the chosen channel so it can be installed and used in Integray tasks.

## Project Structure

This template creates a small solution with **two C# projects**:

- **Connector project** – `Integray.Connector.<connector_name>/Integray.Connector.<connector_name>.csproj`
  - Contains the connector implementation and all connector metadata.
  - Connector metadata lives in the `Metadata/` folder:
    - `Metadata/connector.json` – main connector metadata and action definitions; describes actions, their configuration references, input/output schema usage and file references (icons, documentation).
    - `Metadata/configuration.json` – connector configuration metadata (`kind = "Integray/ConfigurationSchema/1.0"`); contains an NGX Schema Form under `"schema"` that defines the configuration UI and drives the generated strongly-typed configuration class. You can preview how this form is rendered in any Integray environment by opening `https://<site_name>.integray.app/sandbox/config-schema` and pasting the configuration JSON there.
    - `Metadata/input-schema.json` – data schema (`kind = "Integray/DataSchema/1.0"`) for the primary action input; defines columns and types of input rows and is referenced from `connector.json` as the input schema.
    - `Metadata/output-schema.json` – data schema (`kind = "Integray/DataSchema/1.0"`) for the action output; defines the shape of produced rows and is referenced from `connector.json` as the output schema.
    - `Metadata/icon.svg` – connector icon shown in the Integray UI
    - `Metadata/documentation.md` – markdown documentation shown to Integray users
  - Connector source code is in the project root of the connector project, for example:
    - `Connector.cs` – main connector class inheriting from `IntegrayConnector`

- **Test project** – `Integray.Connector.<connector_name>.Tests/Integray.Connector.<connector_name>.Tests.csproj`
  - Contains unit/integration tests for the connector.
  - References the `Integray.Connector.<connector_name>` project.
  - Uses the Integray Connector Test SDK, for example:
    - `ConnectorTests.cs` – sample connector tests
    - `Usings.cs` – shared `using` directives for tests

Additionally, in the repository root:

- `Integray.Connector.<connector_name>.slnx` – solution file for IDEs
- `global.json` – pinned .NET SDK version for this project

---

## Implementing the Connector

Connectors inherit from `IntegrayConnector` and implement the processing logic.

Example:

```csharp
using Integray.Connector.SDK;
using Integray.Connector.v2.Interfaces;

public class MyConnector : IntegrayConnector
{
    protected override async Task<IProcessResult> ProcessInternalAsync(IConnectorContext context)
    {
        return GetEmptyResult();
    }
}
```

Inside this method you typically:

1. Read configuration
2. Read input data
3. Call an external API or service
4. Produce output data
5. Return the result

---

## Working With Input Data

During execution the connector receives input as one or more **tables** of rows.  
Most actions work with a single **primary input table**, which you can access from the execution context:

```csharp
var input = context.GetPrimaryInput();
```

You should always check if input is empty:

```csharp
if (input == null || input.IsEmpty)
    return GetEmptyResult();
```

### Strongly-typed models from data schemas

When you define data schemas in `Metadata/input-schema.json` and `Metadata/output-schema.json`, the Integray Connector SDK uses **source generators** to create strongly‑typed C# models and helper extensions.  
Instead of working with raw dictionaries, you can iterate over input rows as normal C# objects, which makes the code safer and easier to maintain.

Example:

```csharp
foreach (var row in input.ToMySchemaRowModels())
{
    var value = row.MyColumn;
}
```

The exact generated type and extension method name depend on the data schema name (for example `CalculatorInputRowModel`, `ToCalculatorInputRowModels()`).

### How input shape depends on schemas

The structure of the input table is determined by:

- The **input data schema** referenced from `connector.json` (for example via `inputSchema.schemaRef`), and  
- The **mode** of the input schema (`none`, `required`, `optional`, `mandatory`).

Typical patterns:

- If `inputSchema.mode` is `required`, the action always expects input rows that follow the specific data schema referenced in `connector.json`. Your connector code can rely on the generated row model.
- If `inputSchema.mode` is `optional` or `mandatory`, the actual schema is chosen by the Integray user when configuring the step. Your connector should be written to handle different shapes, typically by using either generated models for known schemas or more dynamic handling.
- If `inputSchema.mode` is `none`, the action does not receive input data (for example, a pure “data producer” action).

In all cases, input arrives as tables, but when data schemas are present and referenced, you get the benefit of generated models and extension methods that match the configured schema.

---

## Working With Configurations

Connector configuration is described using one or more **Integray configuration schemas** (`kind = "Integray/ConfigurationSchema/1.0"`) stored under `Metadata/`.  
The main file is usually `Metadata/configuration.json`, and you can add additional configuration schemas if specific actions need their own settings.  
Inside each configuration file, the `"schema"` property contains an NGX Schema Form definition that controls how the configuration UI looks and behaves in Integray.

From each configuration schema the Integray Connector SDK generates:

- A strongly‑typed C# configuration class (for example `<SchemaName>Configuration`), and
- Extension methods on the `Configurations` dictionary (for example `Configurations.Get<SchemaName>()`).

The connector metadata in `Metadata/connector.json` then **references** these configuration schemas (for example in `actions[].configurationRefs[]`), so that Integray knows which configuration form(s) to show for each action and which generated configuration objects will be available at runtime.

At runtime, the values come from the configuration filled in by the Integray user in the UI.

Example:

```csharp
var config = context.Configurations.GetMyConnectorConfiguration();

// Now you can use strongly-typed properties:
var operation = config.Operation;
var shouldRound = config.Round ?? false;
var precision = config.Precision;
```

You can preview and iterate on the configuration UI by pasting the JSON from `Metadata/configuration.json` into the config-schema sandbox:

- `https://<site_name>.integray.app/sandbox/config-schema`

---

## Creating Output Data

Output data works similarly to input data and is also based on data schemas.  
The `Metadata/output-schema.json` file defines an **Integray data schema** (`kind = "Integray/DataSchema/1.0"`) that describes the structure of rows your action produces, and this schema is referenced from `connector.json` (for example via `outputSchema.schemaRef` and `outputSchema.mode`).

The Integray Connector SDK generates a strongly‑typed row model (for example `MyOutputRowModel`) and helper methods such as:

- `result.Output!.AddRow(MyOutputRowModel row)`
- `result.Output!.AddRows(IEnumerable<MyOutputRowModel> rows)`

Example:

```csharp
var result = ResultFactory.Create();

result.Output!.AddRow(new MyOutputRowModel
{
    Value = 123
});

return result;
```

The exact behavior again depends on `outputSchema.mode`:

- `none` – the action does not produce an output table.
- `required` – the action always produces rows matching the referenced data schema.
- `optional` / `mandatory` – the concrete output schema is chosen (or required) in the Integray UI when configuring the step.

---

## Logging

Connectors should use the built‑in logging system available via the `Log` property on `IntegrayConnector`.  
All log entries are attached to the current **task run** and are visible in the **Task Run log** inside Integray, which makes them the primary way to understand what happened during execution.

Basic usage:

```csharp
Log.Info("Connector started");
```

Before doing expensive work for debug-level diagnostics, check whether there is a listener:

```csharp
if (Log.HasDebugListener())
{
    Log.Debug($"Processing {input.Rows?.Count ?? 0} rows");
}
```

Recommended log levels:

- **Trace** – very detailed, low-level information (branches, loops, retries); mainly for deep debugging.
- **Debug** – technical details about processing steps (parsing input, mapping fields, calling external services).
- **Info** – high-level, user-friendly messages about what the connector is doing (start/end of action, summary).
- **Warning** – recoverable issues and partial problems (fallbacks, missing optional data).
- **Error** – serious errors that cause the current action to fail.
- **Critical** – exceptional failures that prevent the connector from running at all (for example initialization problems).

Use `Info`, `Warn`, and `Error` for messages that should help users and operators understand what happened in a task run.  
Reserve `Trace` and `Debug` for developer-focused diagnostics, guarded by listener checks to avoid unnecessary overhead.

---

## Building and Packaging the Connector

Build the solution using the .NET SDK:

```bash
dotnet build
```

Then create a connector package using the Integray CLI.

- From **anywhere** (explicit project path):

  ```bash
  integray connector pack ./Integray.Connector.<connector_name>/Integray.Connector.<connector_name>.csproj
  ```

- From **inside the connector project folder**:

  ```bash
  integray connector pack
  ```

Both variants produce a ZIP package containing the connector assembly and all required metadata.

---

## Publishing the Connector

To make the connector available in Integray, you need to publish the ZIP package into a **channel** in the Integray Repository (ICR).

### What is a channel?

A channel is a container in ICR that holds connectors and schemas:

- **Private channels** – ideal for development and testing; you can freely update and delete content.
- **Public channels** – stable, production-ready content; visible to all Integray customers.
- Channels can also be **restricted** (require an access token) or **non-restricted**.

You can manage channels in the ICR Developer UI (`https://icr.integray.app`) or via the CLI.

### Prerequisites

1. **Developer access and API token** – request a developer account for the Integray Repository (ICR) via `support@integray.com`, then sign in to `https://icr.integray.app` and create or copy an API token from the Tokens section.
2. **Store the token locally** so the CLI can use it:

   ```bash
   integray token set <TOKEN>
   ```

3. **Create or select a channel**:
   - In the UI at `https://icr.integray.app`, or
   - From CLI:

   ```bash
   integray channel new <NAME>
   ```

4. **Set the active channel** for this solution:

   ```bash
   integray channel set <CHANNEL_GUID>
   ```

### Publish the package

From the connector directory (after `integray connector pack`), you can publish using the short form:

```bash
integray connector publish
```

This uses:

- The last package produced by `integray connector pack`
- The active channel from `.integray`
- The stored token from `integray token set`

You can also specify everything explicitly, without relying on stored token or active channel:

```bash
integray connector publish ./Connector.zip -c <CHANNEL_ID> -t <TOKEN>
```

---

## Testing the Connector

Connectors can be tested without the full Integray runtime using the **Integray Connector Test SDK**.

Tests create a simulated execution environment (`TestConnectorContext`) where you control inputs, configurations and logging behavior.

Example:

```csharp
var context = TestConnectorContextBuilder
    .Create()
    .CaptureLogs()
    .Build();
```

---

## Recommended Development Tools

| IDE / Editor        | How to use it with this project                                                                                  |
|---------------------|-------------------------------------------------------------------------------------------------------------------|
| Cursor              | Open the repository folder directly in Cursor. Use its AI assistance together with this README and `.ai-rules`. |
| Visual Studio Code  | Install the **C# Dev Kit** extension and open the folder as a workspace. Builds and tests run via `dotnet` CLI.  |
| JetBrains Rider     | Open the solution file `Integray.Connector.<connector_name>.slnx` and work with the usual .NET tooling.          |




## Support

For developer access or support:

support@integray.com