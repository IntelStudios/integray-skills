# InputDataFilter — Reference for Config Transfer JSON Generation

## Overview

`InputDataFilter` is a `string?` field on a step — its value is a **JSON object serialized as a string** (double-encoded) inside the transfer JSON.

If no filter is needed: `"InputDataFilter": null`

---

## Format in Config Transfer JSON

```json
{
  "Steps": [
    {
      "ID": 1,
      "InputSchemaMapping": { "Amount": "Fetch Transactions.Amount" },
      "InputDataFilter": "{\"Fetch Transactions.StatusCode\":[{\"Type\":\"StringEq\",\"Value\":\"200\"}]}",
      ...
    }
  ]
}
```

---

## Filter JSON Structure (before double-encoding)

```json
{
  "<path>": [
    { "Type": "<DXConditionType>", "Value": "<value>" }
  ]
}
```

- **Key** = column path in `"StepName.ColumnName"` format — same format as values in `InputSchemaMapping`
- **Value** = **array** of conditions — multiple conditions on one column are combined with **AND**
- Multiple keys = also **AND**

Fields per condition:
- `Type` — required, enum name as string (see below)
- `Value` — required for most types (see exceptions)
- `Value2` — required for `Between` / `NotBetween` types (upper bound)

---

## Filters by Data Type

### String (DataType = 2)

| Type | Description | Value |
|------|-------------|-------|
| `StringEq` | Equals (case-insensitive) | `"text"` |
| `StringNotEq` | Not equals | `"text"` |
| `StringContains` | Contains | `"text"` |
| `StringNotContains` | Does not contain | `"text"` |
| `StringIn` | Is in list (comma-separated) | `"a,b,c"` |
| `StringNotIn` | Is not in list | `"a,b,c"` |
| `StringEmpty` | Is null or empty | *(no Value field)* |
| `StringNotEmpty` | Is not null or empty | *(no Value field)* |

### Int (DataType = 1)

| Type | Description | Value / Value2 |
|------|-------------|----------------|
| `IntEq` / `IntNotEq` | Equals / not equals | `Value: 42` |
| `IntGt` / `IntLt` | Greater / less than | `Value: 42` |
| `IntGeq` / `IntLeq` | ≥ / ≤ | `Value: 42` |
| `IntIn` / `IntNotIn` | In list / not in list | `Value: "1,2,3"` |
| `IntBetween` / `IntNotBetween` | Between (inclusive) | `Value: 10, Value2: 99` |
| `IntEmpty` / `IntNotEmpty` | Is null / is not null | *(no Value field)* |

### Double (DataType = 6)

Same set as Int, prefix `Double`:
`DoubleEq`, `DoubleNotEq`, `DoubleGt`, `DoubleLt`, `DoubleGeq`, `DoubleLeq`, `DoubleIn`, `DoubleNotIn`, `DoubleBetween`, `DoubleNotBetween`, `DoubleEmpty`, `DoubleNotEmpty`

### Decimal (DataType = 9)

Same set as Int, prefix `Decimal`:
`DecimalEq`, `DecimalNotEq`, `DecimalGt`, `DecimalLt`, `DecimalGeq`, `DecimalLeq`, `DecimalIn`, `DecimalNotIn`, `DecimalBetween`, `DecimalNotBetween`, `DecimalEmpty`, `DecimalNotEmpty`

### Bool (DataType = 3)

| Type | Description |
|------|-------------|
| `BoolTrue` | Is true |
| `BoolFalse` | Is false |
| `BoolEmpty` / `BoolNotEmpty` | Is null / is not null |

*(no Value field for any Bool condition)*

### DateTime (DataType = 5)

| Type | Description | Value / Value2 |
|------|-------------|----------------|
| `DateTimeEq` / `DateTimeNotEq` | Equals / not equals | ISO datetime string |
| `DateTimeGt` / `DateTimeLt` | Greater / less than | ISO datetime string |
| `DateTimeGeq` / `DateTimeLeq` | ≥ / ≤ | ISO datetime string |
| `DateTimeBetween` / `DateTimeNotBetween` | Between (inclusive) | `Value` + `Value2` as ISO datetime |
| `DateTimeEmpty` / `DateTimeNotEmpty` | Is null / is not null | *(no Value field)* |

DateTime value format: `"2024-01-15T00:00:00"`

### Base64 (DataType = 4)

Only `Base64Empty` and `Base64NotEmpty` — *(no Value field)*

### JSON (DataType = 8)

Only `JsonEmpty` and `JsonNotEmpty` — *(no Value field)*

### Table (DataType = 7)

**Filters are not supported on Table columns.**

---

## Examples

### Single condition

Filter JSON (readable):
```json
{
  "Fetch FIO Transactions.StatusCode": [
    { "Type": "StringEq", "Value": "200" }
  ]
}
```

In transfer JSON (double-encoded):
```json
"InputDataFilter": "{\"Fetch FIO Transactions.StatusCode\":[{\"Type\":\"StringEq\",\"Value\":\"200\"}]}"
```

### Multiple conditions and columns (AND)

Filter JSON (readable):
```json
{
  "Fetch FIO Transactions.StatusCode": [
    { "Type": "StringEq", "Value": "200" }
  ],
  "Fetch FIO Transactions.Amount": [
    { "Type": "DecimalGt", "Value": 0 },
    { "Type": "DecimalLeq", "Value": 1000000 }
  ]
}
```

In transfer JSON (double-encoded):
```json
"InputDataFilter": "{\"Fetch FIO Transactions.StatusCode\":[{\"Type\":\"StringEq\",\"Value\":\"200\"}],\"Fetch FIO Transactions.Amount\":[{\"Type\":\"DecimalGt\",\"Value\":0},{\"Type\":\"DecimalLeq\",\"Value\":1000000}]}"
```

### Between (date range)

Filter JSON (readable):
```json
{
  "Fetch FIO Transactions.Date": [
    { "Type": "DateTimeBetween", "Value": "2024-01-01T00:00:00", "Value2": "2024-12-31T23:59:59" }
  ]
}
```

### No filter

```json
"InputDataFilter": null
```
