#!/usr/bin/env python3
"""Print a connector card from the KB catalogs and a Debugger/Run skeleton.

Does not call the API. Newest catalog version unless --version is set.
Debugger grant is read from the company conventions (work-mode project, or
--project). Exit 2 when the guid, version, or action is not in the catalog.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from connector_versions import parse_version

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GUID_LINE = re.compile(
    r"^\s*debugger-connector:\s*([0-9a-fA-F-]{36})\s+(always|never)\s*$",
    re.IGNORECASE,
)
PROJECT_LINE = re.compile(r"^project:\s*(\S+)\s*$", re.MULTILINE)
TYPE_CODES = {
    "int": 1,
    "string": 2,
    "bool": 3,
    "base64": 4,
    "datetime": 5,
    "double": 6,
    "table": 7,
    "json": 8,
    "decimal": 9,
    "text": 10,
}


def load(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def index_guid_version(items: list[dict]) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for item in items:
        guid = str(item.get("guid") or "").lower()
        ver = str(item.get("version") or "")
        if guid and ver:
            out[(guid, ver)] = item
    return out


def newest(rows: list[dict]) -> dict:
    return max(rows, key=lambda item: parse_version(str(item.get("version") or "")))


def work_mode_project() -> str:
    path = ROOT / "internal" / "work-mode.md"
    if not path.is_file():
        return ""
    match = PROJECT_LINE.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def project_dir(name: str) -> Path | None:
    if not name:
        return None
    path = Path(name)
    if path.is_dir():
        return path
    candidate = ROOT / "projects" / name
    return candidate if candidate.is_dir() else None


def debugger_grant(guid: str, folder: Path | None) -> str:
    if folder is None:
        return "no project (pass --project, or set project: in work-mode)"
    conventions = folder / "conventions.md"
    if not conventions.is_file():
        return "conventions.md missing"
    hits: list[str] = []
    for line in conventions.read_text(encoding="utf-8").splitlines():
        match = GUID_LINE.match(line)
        if match and match.group(1).lower() == guid:
            hits.append(match.group(2).lower())
    if not hits:
        return "no line (ask once)"
    if len(set(hits)) > 1:
        return "conflict (" + ", ".join(hits) + ")"
    return hits[-1]


def schema_side(spec: dict | None, schemas: dict[tuple[str, str], dict]) -> tuple[str, dict | None]:
    if not isinstance(spec, dict):
        return "missing", None
    mode = str(spec.get("mode") or "missing")
    ref = spec.get("schemaRef") if isinstance(spec.get("schemaRef"), dict) else None
    if not ref:
        return mode, None
    key = (str(ref.get("guid") or "").lower(), str(ref.get("version") or ""))
    found = schemas.get(key)
    return mode, found


def column_node(column: dict, schemas: dict[tuple[str, str], dict], seen: set[tuple[str, str]]) -> dict:
    type_name = str(column.get("type") or "").lower()
    constraints = column.get("constraints") if isinstance(column.get("constraints"), dict) else {}
    node: dict[str, Any] = {
        "Name": column.get("name"),
        "AllowNull": bool(constraints.get("allowNull", True)),
        "DataType": TYPE_CODES.get(type_name),
    }
    if type_name == "table" and isinstance(column.get("tableRef"), dict):
        ref = column["tableRef"]
        key = (str(ref.get("guid") or "").lower(), str(ref.get("version") or ""))
        nested = schemas.get(key)
        if nested and key not in seen:
            node["Schema"] = schema_object(nested, schemas, seen | {key})
    return node


def schema_object(item: dict, schemas: dict[tuple[str, str], dict], seen: set[tuple[str, str]]) -> dict:
    columns = item.get("columns") if isinstance(item.get("columns"), list) else []
    return {
        "Name": item.get("name") or "",
        "Guid": item.get("guid"),
        "Version": item.get("version"),
        "Columns": [column_node(col, schemas, seen) for col in columns if isinstance(col, dict)],
    }


def prop_type(prop: dict) -> str:
    raw = prop.get("type")
    if isinstance(raw, list):
        return "|".join(str(part) for part in raw)
    if isinstance(raw, str) and raw:
        return raw
    return "value"


def empty_value(type_name: str) -> Any:
    base = type_name.split("|", 1)[0]
    return {
        "string": "",
        "number": 0,
        "integer": 0,
        "boolean": False,
        "array": [],
        "object": {},
    }.get(base, "")


def config_card(ref: dict, configs: dict[tuple[str, str], dict]) -> tuple[str, dict]:
    guid = str(ref.get("guid") or "").lower()
    ver = str(ref.get("version") or "")
    item = configs.get((guid, ver))
    if item is None:
        line = f"  {guid} {ver} (not in configuration-schemas.json)"
        body = {"guid": guid, "version": ver, "configuration": "{}"}
        return line, body
    schema = item.get("schema") if isinstance(item.get("schema"), dict) else {}
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = [name for name in (schema.get("required") or []) if isinstance(name, str)]
    fields = []
    payload: dict[str, Any] = {}
    for name, prop in props.items():
        if not isinstance(prop, dict):
            continue
        kind = prop_type(prop)
        mark = "required" if name in required else "optional"
        fields.append(f"{name} ({kind}, {mark})")
        if name in required:
            payload[name] = empty_value(kind)
    field_text = ", ".join(fields) if fields else "(no properties)"
    line = f"  {item.get('name')} {guid} {ver}\n    {field_text}"
    body = {
        "guid": guid,
        "version": ver,
        "configuration": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    }
    return line, body


def checkpoint_card(guid: str, catalog: dict) -> list[str]:
    row = next(
        (item for item in catalog.get("connectors") or [] if str(item.get("guid") or "").lower() == guid),
        None,
    )
    if row is None:
        return ["checkpoint: guid not in connector-checkpoints.json"]
    shape_name = str(row.get("shape") or "")
    shape = (catalog.get("shapes") or {}).get(shape_name) or {}
    lines = [f"checkpoint: {shape_name}"]
    if row.get("note"):
        lines.append(f"checkpointNote: {row['note']}")
    if shape.get("summary"):
        lines.append(f"checkpointSummary: {shape['summary']}")
    return lines


def choose_action(actions: list[dict], code: str | None) -> dict | None:
    if not actions:
        return None
    if code:
        for action in actions:
            if str(action.get("code") or "") == code:
                return action
        return None
    for action in actions:
        if str(action.get("code") or "") == "defaultAction":
            return action
    return actions[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guid", help="Connector guid")
    parser.add_argument("--version", help="Catalog version. Default: newest")
    parser.add_argument("--action", help="Action code. Default: defaultAction, else the first action")
    parser.add_argument("--project", help="Company folder under projects/, or a path. Default: work-mode project")
    args = parser.parse_args()
    want = args.guid.strip().lower()

    connectors = [item for item in load("connectors.json") if str(item.get("guid") or "").lower() == want]
    if not connectors:
        print(f"connector: guid not in connectors.json", file=sys.stderr)
        return 2
    versions = sorted({str(item.get("version") or "") for item in connectors}, key=parse_version)
    if args.version:
        chosen = next((item for item in connectors if str(item.get("version") or "") == args.version), None)
        if chosen is None:
            print(f"connector: version {args.version} not in catalog ({', '.join(versions)})", file=sys.stderr)
            return 2
    else:
        chosen = newest(connectors)

    actions = [item for item in (chosen.get("actions") or []) if isinstance(item, dict)]
    action = choose_action(actions, args.action)
    if args.action and action is None:
        codes = ", ".join(str(item.get("code") or "") for item in actions) or "(none)"
        print(f"connector: action {args.action} not on this version ({codes})", file=sys.stderr)
        return 2

    data_schemas = index_guid_version(load("data-schemas.json"))
    config_schemas = index_guid_version(load("configuration-schemas.json"))
    restrictions = load("connector-restrictions.json")
    by_guid = restrictions.get("byGuid") if isinstance(restrictions.get("byGuid"), dict) else {}
    if want in by_guid:
        agents = ", ".join(by_guid[want])
    else:
        default = restrictions.get("defaultIfAbsent") or ["remote"]
        agents = ", ".join(default) + " (defaultIfAbsent)"

    source = action if action is not None else chosen
    input_mode, input_schema = schema_side(source.get("inputSchema"), data_schemas)
    output_mode, output_schema = schema_side(source.get("outputSchema"), data_schemas)
    refs = source.get("configurationRefs") if isinstance(source.get("configurationRefs"), list) else []
    features = source.get("features") if isinstance(source.get("features"), list) else []
    processing = source.get("inputProcessing") if isinstance(source.get("inputProcessing"), list) else []
    meta = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}

    print(f"name: {chosen.get('name')}")
    print(f"guid: {chosen.get('guid')}")
    print(f"version: {chosen.get('version')}")
    print(f"catalogVersions: {', '.join(versions)}")
    print(f"agents: {agents}")
    if action is None:
        print("action: (none)")
    else:
        codes = ", ".join(str(item.get("code") or "") for item in actions)
        print(f"action: {action.get('code')} ({action.get('name')})")
        if len(actions) > 1:
            print(f"actions: {codes}")
    print(f"features: {', '.join(str(item) for item in features) or '(none)'}")
    print(f"inputProcessing: {', '.join(str(item) for item in processing) or '(none)'}")
    if meta.get("defaultProcessType"):
        print(f"defaultProcessType: {meta.get('defaultProcessType')}")

    def print_schema(label: str, mode: str, item: dict | None) -> None:
        if item is None:
            print(f"{label}: {mode}")
            return
        print(f"{label}: {mode} {item.get('name')} {item.get('guid')} {item.get('version')}")

    print_schema("input", input_mode, input_schema)
    print_schema("output", output_mode, output_schema)
    if input_mode == "required" and input_schema is None:
        print("inputNote: required schema is not in data-schemas.json")
    if output_mode == "required" and output_schema is None:
        print("outputNote: required schema is not in data-schemas.json")
    if input_mode == "mandatory":
        print("inputNote: caller supplies the schema")
    if output_mode == "mandatory":
        print("outputNote: caller supplies the schema")

    print("configurations:")
    bodies: list[dict] = []
    if not refs:
        print("  (none)")
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        line, body = config_card(ref, config_schemas)
        print(line)
        bodies.append(body)

    for line in checkpoint_card(want, load("connector-checkpoints.json")):
        print(line)

    folder_name = args.project or work_mode_project()
    folder = project_dir(folder_name) if folder_name else None
    if folder_name and folder is None:
        grant = f"project folder not found ({folder_name})"
    else:
        grant = debugger_grant(want, folder)
    print(f"debugger: {grant}")

    skeleton: dict[str, Any] = {
        "connectorGuid": chosen.get("guid"),
        "connectorVersion": chosen.get("version"),
    }
    if action is not None:
        skeleton["actionCode"] = action.get("code")
    if input_mode == "mandatory":
        skeleton["input"] = {
            "Schema": {"Name": "<caller schema>", "Columns": []},
            "Rows": [],
            "HasDefinedRows": True,
        }
    elif input_mode == "required" and input_schema is not None:
        skeleton["input"] = {
            "Schema": schema_object(input_schema, data_schemas, set()),
            "Rows": [],
            "HasDefinedRows": True,
        }
    if output_mode == "mandatory":
        skeleton["outputSchema"] = {"Name": "<caller schema>", "Columns": []}
    elif output_mode == "required" and output_schema is not None:
        skeleton["outputSchema"] = schema_object(output_schema, data_schemas, set())
    if bodies:
        skeleton["configurations"] = bodies
    print("skeleton:")
    print(json.dumps(skeleton, indent=2, ensure_ascii=False))
    notes = ["does not call Debugger/Run"]
    if input_mode == "mandatory" or output_mode == "mandatory":
        notes.append("replace <caller schema> before sending")
    if input_mode == "required" or output_mode == "required":
        notes.append("Required schemas below are the catalog schemas; input.Rows is empty")
    print("skeletonNote: " + ". ".join(notes) + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
