"""Read a Task-run snapshot JSON (identity-key tree) against split working/."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Runtime keys in Schema.Columns[].Name and Rows objects.
# {ts:<Step CopyID>} {dsc:<column CopyID>} {e:<Endpoint CopyID>}
IDENTITY_RE = re.compile(
    r"^\{(ts|dsc|e):"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\}$"
)

_KIND_LABEL = {"ts": "Step", "dsc": "column", "e": "Endpoint"}
_MAX_STR = 100
_MAX_ROWS = 5
TABLE_TYPE = 7


def canon_identity(kind: str, guid: str) -> str:
    return "{" + kind + ":" + guid.lower() + "}"


def parse_identity(key: str) -> tuple[str, str] | None:
    match = IDENTITY_RE.match(key)
    if match is None:
        return None
    return match.group(1), match.group(2).lower()


def collect_identity_keys(obj: Any) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(key: str) -> None:
        parsed = parse_identity(key)
        if parsed is None:
            return
        token = canon_identity(*parsed)
        if token not in seen:
            seen.add(token)
            found.append(token)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                add(key)
                if key == "Name" and isinstance(value, str):
                    add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(obj)
    return found


def load_identity_names(working: Path) -> dict[str, str]:
    """Map `{ts|dsc|e:<copyId>}` → display Name from a split working/ tree."""
    working = Path(working)
    names: dict[str, str] = {}
    tasks = working / "tasks"
    if tasks.is_dir():
        for path in sorted(tasks.glob("*.json")):
            task = json.loads(path.read_text(encoding="utf-8"))
            for step in task.get("Steps") or []:
                copy_id = step.get("CopyID")
                name = step.get("Name")
                if copy_id and name:
                    names[canon_identity("ts", str(copy_id))] = str(name)
    endpoints = working / "endpoints"
    if endpoints.is_dir():
        for path in sorted(endpoints.glob("*.json")):
            endpoint = json.loads(path.read_text(encoding="utf-8"))
            copy_id = endpoint.get("CopyID")
            name = endpoint.get("Name")
            if copy_id and name:
                names[canon_identity("e", str(copy_id))] = str(name)
    schemas = working / "data-schemas"
    if schemas.is_dir():
        for path in sorted(schemas.glob("*.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            for column in schema.get("Columns") or []:
                copy_id = column.get("CopyID")
                name = column.get("Name")
                if copy_id and name:
                    names[canon_identity("dsc", str(copy_id))] = str(name)
    return names


def working_beside_connection(connection: Path) -> Path | None:
    candidate = Path(connection).expanduser().resolve().parent / "working"
    if (candidate / "tasks").is_dir() or (candidate / "_transfer.json").is_file():
        return candidate
    return None


def display_key(key: str, names: dict[str, str]) -> str:
    parsed = parse_identity(key)
    if parsed is None:
        return key
    token = canon_identity(*parsed)
    name = names.get(token)
    return name if name else token


def format_legend(keys: list[str], names: dict[str, str]) -> list[str]:
    lines = ["# identity map (working/ CopyID → Name)"]
    unresolved: list[str] = []
    for token in keys:
        parsed = parse_identity(token)
        if parsed is None:
            continue
        kind, _guid = parsed
        label = _KIND_LABEL.get(kind, kind)
        name = names.get(token)
        if name:
            lines.append(f"{token}  {label}  {name}")
        else:
            unresolved.append(f"{token}  {label}")
    if unresolved:
        lines.append("# unresolved")
        lines.extend(unresolved)
    return lines


def _fmt_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        text = value.replace("\n", "\\n")
        if len(text) > _MAX_STR:
            text = text[: _MAX_STR] + "…"
        return json.dumps(text, ensure_ascii=False)
    if isinstance(value, (int, float, bool)):
        return json.dumps(value)
    return json.dumps(value, ensure_ascii=False)[:_MAX_STR]


def _is_table_cell(column: dict[str, Any], value: Any) -> bool:
    if column.get("DataType") == TABLE_TYPE:
        return True
    return isinstance(value, list) and bool(value) and isinstance(value[0], dict)


def summarize_table(
    schema: dict[str, Any] | None,
    rows: list[Any] | None,
    names: dict[str, str],
    *,
    indent: int = 0,
    title: str | None = None,
    has_defined_rows: Any = None,
) -> list[str]:
    schema = schema or {}
    rows = rows or []
    pad = "  " * indent
    bits: list[str] = []
    if title:
        bits.append(title)
    bits.append(f"rows={len(rows)}")
    schema_name = schema.get("Name") or ""
    if schema_name:
        bits.append(f"schema={schema_name!r}")
    if has_defined_rows is not None:
        bits.append(f"HasDefinedRows={has_defined_rows}")
    lines = [pad + " ".join(bits)]
    columns = schema.get("Columns") or []
    shown = rows[:_MAX_ROWS]
    for index, row in enumerate(shown):
        lines.extend(_summarize_row(row, columns, names, indent + 1, index))
    extra = len(rows) - len(shown)
    if extra > 0:
        lines.append(pad + f"  … {extra} more rows")
    return lines


def _summarize_row(
    row: Any,
    columns: list[dict[str, Any]],
    names: dict[str, str],
    indent: int,
    index: int,
) -> list[str]:
    pad = "  " * indent
    if not isinstance(row, dict):
        return [pad + f"[{index}] {_fmt_scalar(row)}"]
    scalars: list[str] = []
    nested: list[tuple[str, dict[str, Any], list[Any]]] = []
    for column in columns:
        key = column.get("Name")
        if not isinstance(key, str):
            continue
        value = row.get(key)
        label = display_key(key, names)
        if _is_table_cell(column, value):
            nested.append((label, column.get("Schema") or {}, value or []))
        else:
            scalars.append(f"{label}={_fmt_scalar(value)}")
    extra_keys = [k for k in row if k not in {c.get("Name") for c in columns}]
    for key in extra_keys:
        value = row[key]
        label = display_key(key, names) if isinstance(key, str) else str(key)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            nested.append((label, {}, value))
        else:
            scalars.append(f"{label}={_fmt_scalar(value)}")
    line = pad + f"[{index}]"
    if scalars:
        line += " " + " ".join(scalars)
    lines = [line]
    for label, nested_schema, nested_rows in nested:
        lines.extend(
            summarize_table(
                nested_schema,
                nested_rows,
                names,
                indent=indent + 1,
                title=label,
            )
        )
    return lines


def summarize_snapshot(body: dict[str, Any], names: dict[str, str] | None = None) -> str:
    names = names or {}
    keys = collect_identity_keys(body)
    lines = format_legend(keys, names)
    lines.append("")
    lines.extend(
        summarize_table(
            body.get("Schema") or {},
            body.get("Rows") or [],
            names,
            title="root",
            has_defined_rows=body.get("HasDefinedRows"),
        )
    )
    return "\n".join(lines) + "\n"
