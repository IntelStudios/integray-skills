#!/usr/bin/env python3
"""Local Config Transfer reference checks (docs/transfer/config-transfer-format.md §7 / §11).

Stdout (exit 1 if any line): in-file refs — DataSchemas[], *CopyID, ConfigurationCopyID,
Configuration JSON required fields (when the schema is in data/configuration-schemas.json),
SelectedActionCode / configurationRefs / agent restrictions (when the connector version
is in data/connectors.json), unused Connectors[] / Configurations[] / TaskGroups[] /
EndpointGroups[], mapping path first segment not a Step or bound Endpoint Name.

Stderr (does not fail): Guid+Version missing from the KB catalogs (catalog may be stale).
Empty stdout and exit 0 = the transfer may be delivered; mention stderr catalog lines
to the user.

Exit 2 = file not found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
DATA = ROOT / "data"

from transfer_split import load_transfer_document  # noqa: E402

SHARED_AGENT = "11111111-1111-1111-1111-111111111111"
HTTP_METHODS = ("Get", "Post", "Put", "Patch", "Delete")
ENDPOINT_SCHEMA_KEYS = tuple(
    f"{m}{side}" for m in HTTP_METHODS for side in ("InputSchema", "OutputSchema")
)
# Integray Endpoint Connector — SameCompany+EndpointCopyID
ENDPOINT_CONFIG_SCHEMA = ("1e97198c-085d-492a-a049-6f8f56467df0", "3.4.0")
# Integray Start Task Connector — SameCompany+TaskCopyID (configuration-overrides.md)
START_TASK_CONFIG_SCHEMA = ("239b10a7-ed53-4768-bb1a-a33bea808e1a", "1.0.2")
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

COPYID_COLLECTION = {
    "TaskCopyID": "Tasks",
    "TaskGroupCopyID": "TaskGroups",
    "EndpointGroupCopyID": "EndpointGroups",
    "ConfigurationCopyID": "Configurations",
    "TemplateCopyID": "Templates",
    "VariableGroupCopyID": "VariableGroups",
    "AgentCopyID": "Agents",
    "PrevStepCopyID": "Steps",
    "StepCopyID": "Steps",
    "EndpointCopyID": "Endpoints",
    "EntityCopyID": None,
    **{f"{m}InputTaskCopyID": "Tasks" for m in HTTP_METHODS},
    **{f"{m}OutputStepCopyID": "Steps" for m in HTTP_METHODS},
}


def _norm(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value).lower()


def _is_uuid(value: Any) -> bool:
    return isinstance(value, str) and bool(UUID_RE.match(value))


def _gv(obj: dict[str, Any] | None) -> tuple[str, str] | None:
    if not obj or not obj.get("Guid"):
        return None
    return (str(obj["Guid"]).lower(), str(obj.get("Version") or ""))


def required_cols(schema: dict[str, Any]) -> set[str]:
    return {c["Name"] for c in schema.get("Columns") or [] if not c.get("AllowNull", True)}


def mapping_items(mapping: Any) -> list[tuple[str, str]]:
    """Yield (key, path) from a mapping object or JSON string. Skip non-string paths."""
    if isinstance(mapping, str) and mapping.strip():
        try:
            mapping = json.loads(mapping)
        except json.JSONDecodeError:
            return []
    if not isinstance(mapping, dict):
        return []
    out: list[tuple[str, str]] = []
    for key, path in mapping.items():
        if isinstance(path, str) and path:
            out.append((str(key), path))
    return out


def column_types(schema: dict[str, Any] | None) -> dict[str, Any]:
    if not schema:
        return {}
    return {c["Name"]: c.get("Type") for c in schema.get("Columns") or [] if c.get("Name")}


def load_catalogs(data_dir: Path) -> dict[str, Any]:
    connectors = json.loads((data_dir / "connectors.json").read_text())
    config_schemas = json.loads((data_dir / "configuration-schemas.json").read_text())
    restrictions = json.loads((data_dir / "connector-restrictions.json").read_text())
    by_conn = {}
    versions: dict[str, set[str]] = {}
    for item in connectors:
        guid = str(item.get("guid") or "").lower()
        ver = str(item.get("version") or "")
        by_conn[(guid, ver)] = item
        versions.setdefault(guid, set()).add(ver)
    by_cfg = {}
    cfg_versions: dict[str, set[str]] = {}
    for item in config_schemas:
        guid = str(item.get("guid") or "").lower()
        ver = str(item.get("version") or "")
        by_cfg[(guid, ver)] = item
        cfg_versions.setdefault(guid, set()).add(ver)
    return {
        "connectors": by_conn,
        "connector_versions": versions,
        "config_schemas": by_cfg,
        "config_schema_versions": cfg_versions,
        "restrictions": restrictions,
    }


def index_copyids(data: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]], dict[str, str]]:
    collections: dict[str, dict[str, Any]] = {}
    defined: dict[str, list[str]] = {}
    step_to_task: dict[str, str] = {}

    def add(collection: str, entity: dict[str, Any], label: str) -> None:
        cid = _norm(entity.get("CopyID"))
        if not cid:
            return
        collections.setdefault(collection, {})[cid] = entity
        defined.setdefault(cid, []).append(label)

    for name, key in (
        ("Tasks", "Tasks"),
        ("TaskGroups", "TaskGroups"),
        ("EndpointGroups", "EndpointGroups"),
        ("Endpoints", "Endpoints"),
        ("Configurations", "Configurations"),
        ("Agents", "Agents"),
        ("Variables", "Variables"),
        ("VariableGroups", "VariableGroups"),
        ("Templates", "Templates"),
        ("Tags", "Tags"),
        ("SecondaryTokens", "SecondaryTokens"),
        ("AuthConnections", "AuthConnections"),
        ("Connectors", "Connectors"),
    ):
        for entity in data.get(key) or []:
            add(name, entity, f"{name} {entity.get('Name') or entity.get('Slug') or entity.get('CopyID')}")

    for schema in data.get("DataSchemas") or []:
        add("DataSchemas", schema, f"DataSchema {schema.get('Name') or schema.get('CopyID')}")
        for col in schema.get("Columns") or []:
            add("Columns", col, f"Column {schema.get('Name')}.{col.get('Name')}")

    for task in data.get("Tasks") or []:
        tname = task.get("Name") or task.get("CopyID")
        tid = _norm(task.get("CopyID"))
        for step in task.get("Steps") or []:
            add("Steps", step, f"Step {tname} / {step.get('Name') or step.get('CopyID')}")
            sid = _norm(step.get("CopyID"))
            if sid and tid:
                step_to_task[sid] = tid
            for wrap in step.get("Configurations") or []:
                add(
                    "StepConfigurations",
                    wrap,
                    f"StepConfiguration {tname} / {step.get('Name')} / {wrap.get('CopyID')}",
                )

    return collections, defined, step_to_task


def config_required_fields(guid: str, version: str, parsed: dict[str, Any], catalog_schema: dict[str, Any]) -> list[str]:
    schema = catalog_schema.get("schema") or {}
    props = schema.get("properties") or {}
    required: list[str] = []
    for name in schema.get("required") or []:
        prop = props.get(name) or {}
        if "default" in prop:
            continue
        required.append(name)
    if (guid, version) == ENDPOINT_CONFIG_SCHEMA and (
        "EndpointCopyID" in parsed or parsed.get("SameCompany") is True
    ):
        required = [name for name in required if name not in ("CompanyID", "EndpointID")]
        for extra in ("SameCompany", "EndpointCopyID"):
            if extra not in required:
                required.append(extra)
    elif (guid, version) == START_TASK_CONFIG_SCHEMA and (
        "TaskCopyID" in parsed or parsed.get("SameCompany") is True
    ):
        required = [name for name in required if name not in ("CompanyID", "TaskID")]
        for extra in ("SameCompany", "TaskCopyID"):
            if extra not in required:
                required.append(extra)
    elif parsed.get("SameCompany") is True and (parsed.get("EndpointCopyID") or parsed.get("TaskCopyID")):
        required = [name for name in required if name not in ("CompanyID", "EndpointID", "TaskID")]
    return required


def check_transfer(data: dict[str, Any], catalogs: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    catalog_notes: list[str] = []
    used_configurations: set[str] = set()
    used_task_groups: set[str] = set()
    used_endpoint_groups: set[str] = set()
    collections, defined, step_to_task = index_copyids(data)

    for cid, labels in sorted(defined.items()):
        if len(labels) > 1:
            issues.append(f"duplicate CopyID: {cid} -> {labels}")

    schemas = data.get("DataSchemas") or []
    by_guid = {(_norm(s.get("Guid")), str(s.get("Version") or "")): s for s in schemas if s.get("Guid")}
    by_schema_copyid = {_norm(s["CopyID"]): s for s in schemas if s.get("CopyID")}

    def resolve_schema(schema_ref: dict[str, Any] | None) -> dict[str, Any] | None:
        if not schema_ref:
            return None
        if schema_ref.get("Guid"):
            return by_guid.get((_norm(schema_ref.get("Guid")), str(schema_ref.get("Version") or "")))
        return by_schema_copyid.get(_norm(schema_ref.get("CopyID")))

    def check_schema(label: str, schema_ref: Any, mapping: dict | None = None, *, mapping_required: bool = True) -> None:
        if not schema_ref:
            return
        if not isinstance(schema_ref, dict):
            issues.append(f"schema ref not an object: {label} -> {schema_ref!r}")
            return
        found = resolve_schema(schema_ref)
        if not found:
            issues.append(f"schema not in DataSchemas[]: {label} -> {schema_ref}")
            return
        if not schema_ref.get("Guid") and schema_ref.get("CopyID") and found.get("Guid"):
            issues.append(
                f"system schema referenced by CopyID (use Guid+Version): {label} -> {schema_ref.get('CopyID')}"
            )
        if not mapping_required:
            return
        missing = required_cols(found) - set((mapping or {}).keys())
        if missing:
            issues.append(f"missing required mapping: {label} -> {sorted(missing)}")

    def check_mapping_types(label: str, target_schema: dict[str, Any] | None, mapping: dict | None, source_schemas: list) -> None:
        if not target_schema or not mapping:
            return
        target_types = column_types(target_schema)
        source_types: dict[str, set] = {}
        for schema in source_schemas:
            for name, typ in column_types(schema).items():
                source_types.setdefault(name, set()).add(typ)
        for key, path in mapping.items():
            if key not in target_types or not isinstance(path, str) or not path:
                continue
            col = path.rsplit(".", 1)[-1]
            have = source_types.get(col)
            if not have:
                continue
            want = target_types[key]
            if want not in have:
                issues.append(
                    f"type mismatch: {label} {key} Type {want} <- {col} Type {sorted(have)}"
                )

    def check_mapping_roots(label: str, mapping: Any, roots: set[str]) -> None:
        for key, path in mapping_items(mapping):
            if "." not in path:
                continue
            first = path.split(".", 1)[0]
            if first not in roots:
                issues.append(f"mapping path root unknown: {label} {key} <- {path!r}")

    def resolve_copyid(field: str, value: Any, label: str) -> None:
        if not _is_uuid(value):
            return
        cid = _norm(value)
        if field == "ConfigurationCopyID" and cid:
            used_configurations.add(cid)
        elif field == "TaskGroupCopyID" and cid:
            used_task_groups.add(cid)
        elif field == "EndpointGroupCopyID" and cid:
            used_endpoint_groups.add(cid)
        if field == "AgentCopyID" and cid == SHARED_AGENT:
            return
        collection = COPYID_COLLECTION.get(field, None)
        if field not in COPYID_COLLECTION and field.endswith("CopyID") and field != "CopyID":
            if cid not in defined:
                issues.append(f"CopyID not in transfer: {label} {field} -> {value}")
            return
        if collection is None:
            if cid not in defined:
                issues.append(f"CopyID not in transfer: {label} {field} -> {value}")
            return
        pool = collections.get(collection) or {}
        if cid not in pool:
            issues.append(f"{field} not in {collection}[]: {label} -> {value}")

    def _path_segment(obj: Any, key: str) -> str:
        if isinstance(obj, dict):
            name = obj.get("Name") or obj.get("Slug")
            if name:
                return f"{key}[{name}]"
        return key

    def walk_copyids(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, val in obj.items():
                child = f"{path}.{_path_segment(val, key)}" if isinstance(val, dict) else f"{path}.{key}"
                if key == "Configuration" and isinstance(val, str):
                    continue
                if key.endswith("SecondaryTokens") and key != "SecondaryTokens" and isinstance(val, list):
                    for token in val:
                        if _is_uuid(token) and _norm(token) not in (collections.get("SecondaryTokens") or {}):
                            issues.append(f"secondary token CopyID not in SecondaryTokens[]: {path}.{key} -> {token}")
                    continue
                if key.endswith("CopyID") and key != "CopyID" and not isinstance(val, (dict, list)):
                    resolve_copyid(key, val, path)
                else:
                    walk_copyids(val, child)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                name = None
                if isinstance(item, dict):
                    name = item.get("Name") or item.get("Slug")
                walk_copyids(item, f"{path}.{name}" if name else f"{path}[{i}]")

    for schema in schemas:
        name = schema.get("Name") or schema.get("CopyID")
        for col in schema.get("Columns") or []:
            check_schema(
                f"DataSchema {name} column {col.get('Name')} ComplexType",
                col.get("ComplexType"),
                mapping_required=False,
            )

    listed_connectors = {
        (_norm(c.get("Guid")), str(c.get("Version") or "")) for c in (data.get("Connectors") or []) if c.get("Guid")
    }
    used_connectors: set[tuple[str | None, str]] = set()
    conn_cat = catalogs["connectors"]
    conn_vers = catalogs["connector_versions"]
    cfg_cat = catalogs["config_schemas"]
    cfg_vers = catalogs["config_schema_versions"]
    restrictions = catalogs["restrictions"]
    by_guid_kinds = {str(g).lower(): [k.lower() for k in kinds] for g, kinds in (restrictions.get("byGuid") or {}).items()}
    stale_conn: set[tuple[str, str]] = set()
    stale_cfg: set[tuple[str, str]] = set()

    bound_tasks: set[str] = set()
    task_step_names: dict[str, set[str]] = {}
    for task in data.get("Tasks") or []:
        tid = _norm(task.get("CopyID"))
        if tid:
            task_step_names[tid] = {
                s["Name"] for s in (task.get("Steps") or []) if s.get("Name")
            }
    task_bound_ep_names: dict[str, set[str]] = {}
    for endpoint in data.get("Endpoints") or []:
        slug = endpoint.get("Slug") or endpoint.get("Name") or endpoint.get("CopyID")
        ename = endpoint.get("Name")
        for key in ENDPOINT_SCHEMA_KEYS:
            check_schema(f"{slug} {key}", endpoint.get(key), mapping_required=False)
        for method in HTTP_METHODS:
            task_cid = _norm(endpoint.get(f"{method}InputTaskCopyID"))
            step_cid = _norm(endpoint.get(f"{method}OutputStepCopyID"))
            if task_cid:
                bound_tasks.add(task_cid)
                if ename:
                    task_bound_ep_names.setdefault(task_cid, set()).add(ename)
            if step_cid and task_cid:
                owner = step_to_task.get(step_cid)
                if owner and owner != task_cid:
                    issues.append(
                        f"{method}OutputStepCopyID not in {method}InputTaskCopyID task: {slug} -> {endpoint.get(f'{method}OutputStepCopyID')}"
                    )
            out_map = endpoint.get(f"{method}OutputMapping")
            if out_map and task_cid:
                roots = set(task_step_names.get(task_cid) or set())
                if ename:
                    roots.add(ename)
                check_mapping_roots(f"{slug} {method}OutputMapping", out_map, roots)

    top_cfg = {_norm(c.get("CopyID")): c for c in (data.get("Configurations") or []) if c.get("CopyID")}

    for cfg in data.get("Configurations") or []:
        label = f"Configuration {cfg.get('Name') or cfg.get('CopyID')}"
        if not cfg.get("Name"):
            issues.append(f"Configuration Name is null/empty: {label}")
        schema_ref = cfg.get("ConfigurationSchema")
        gv = _gv(schema_ref) if isinstance(schema_ref, dict) else None
        catalog_cfg = cfg_cat.get(gv) if gv else None
        if gv and not catalog_cfg and gv not in stale_cfg:
            stale_cfg.add(gv)
            extra = ""
            if gv[0] in cfg_vers:
                extra = f" (catalog has versions {sorted(cfg_vers[gv[0]])})"
            catalog_notes.append(
                f"configurationSchema not in data/configuration-schemas.json (catalog may be stale): {schema_ref}{extra}"
            )
        raw = cfg.get("Configuration")
        parsed: dict[str, Any] | None = None
        if raw is None:
            issues.append(f"Configuration field missing: {label}")
        elif isinstance(raw, dict):
            issues.append(f"Configuration must be a JSON string, not an object: {label}")
            parsed = raw
        else:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                issues.append(f"Configuration JSON is invalid: {label} -> {exc}")
        if isinstance(parsed, dict):
            if catalog_cfg:
                missing = [f for f in config_required_fields(gv[0], gv[1], parsed, catalog_cfg) if f not in parsed]
                if missing:
                    issues.append(f"missing required Configuration field: {label} -> {missing}")
            walk_copyids(parsed, label)

    id_scopes: dict[str, dict[int, str]] = {}

    def check_id(
        entity: dict[str, Any],
        label: str,
        scope: str,
        *,
        allow_zero: bool = False,
    ) -> None:
        if "ID" not in entity:
            return
        eid = entity.get("ID")
        if eid == 0 and allow_zero:
            return
        if not isinstance(eid, int):
            return
        seen = id_scopes.setdefault(scope, {})
        prev = seen.get(eid)
        if prev:
            issues.append(f"duplicate ID {eid} in {scope}: {prev} and {label}")
        else:
            seen[eid] = label

    for collection in ("DataSchemas", "Configurations", "Tasks", "Variables"):
        for entity in data.get(collection) or []:
            check_id(
                entity,
                f"{collection} {entity.get('Name') or entity.get('CopyID')}",
                collection,
            )
    for collection in ("TaskGroups", "EndpointGroups"):
        for entity in data.get(collection) or []:
            if not entity.get("ID"):
                issues.append(f"{collection} ID is 0/missing (silently skipped on import): {entity.get('Name')}")
            else:
                check_id(
                    entity,
                    f"{collection} {entity.get('Name') or entity.get('CopyID')}",
                    collection,
                )

    for schema in data.get("DataSchemas") or []:
        for col in schema.get("Columns") or []:
            check_id(col, f"Column {schema.get('Name')}.{col.get('Name')}", f"Columns[{schema.get('Name')}]", allow_zero=True)

    for task in data.get("Tasks") or []:
        tname = task.get("Name") or task.get("CopyID")
        tid = _norm(task.get("CopyID"))
        check_schema(f"{tname} VariablesSchema", task.get("VariablesSchema"), mapping_required=False)
        source_schemas: list = []
        for step in task.get("Steps") or []:
            source_schemas.append(resolve_schema(step.get("InputSchema")))
            source_schemas.append(resolve_schema(step.get("OutputSchema")))
            for extra in step.get("AdditionalInputs") or []:
                source_schemas.append(resolve_schema(extra.get("InputSchema")))
        for endpoint in data.get("Endpoints") or []:
            if tid and tid in {
                _norm(endpoint.get(f"{m}InputTaskCopyID")) for m in HTTP_METHODS
            }:
                for key in ENDPOINT_SCHEMA_KEYS:
                    source_schemas.append(resolve_schema(endpoint.get(key)))
        legal_roots = set(task_step_names.get(tid) or set()) | set(
            task_bound_ep_names.get(tid) or set()
        )
        roots = 0
        for step in task.get("Steps") or []:
            sname = step.get("Name") or step.get("CopyID")
            label = f"{tname} / {sname}"
            check_id(step, f"Step {label}", "Steps")
            if step.get("PrevStepCopyID") is None:
                roots += 1
            else:
                prev = _norm(step.get("PrevStepCopyID"))
                if prev and step_to_task.get(prev) not in (tid, None) and prev in step_to_task:
                    issues.append(f"PrevStepCopyID not in this Task: {label} -> {step.get('PrevStepCopyID')}")
            check_schema(f"{label} (InputSchema)", step.get("InputSchema"), step.get("InputSchemaMapping"))
            check_mapping_types(
                f"{label} (InputSchema)",
                resolve_schema(step.get("InputSchema")),
                step.get("InputSchemaMapping"),
                source_schemas,
            )
            check_mapping_roots(
                f"{label} (InputSchema)",
                step.get("InputSchemaMapping"),
                legal_roots,
            )
            check_schema(f"{label} (OutputSchema)", step.get("OutputSchema"), mapping_required=False)
            for i, extra in enumerate(step.get("AdditionalInputs") or []):
                check_schema(
                    f"{label} (AdditionalInputs[{i}])",
                    extra.get("InputSchema"),
                    extra.get("InputSchemaMapping"),
                )
                check_mapping_types(
                    f"{label} (AdditionalInputs[{i}])",
                    resolve_schema(extra.get("InputSchema")),
                    extra.get("InputSchemaMapping"),
                    source_schemas,
                )
                check_mapping_roots(
                    f"{label} (AdditionalInputs[{i}])",
                    extra.get("InputSchemaMapping"),
                    legal_roots,
                )
                extra_step = _norm(extra.get("StepCopyID"))
                if extra_step and step_to_task.get(extra_step) not in (tid, None) and extra_step in step_to_task:
                    issues.append(f"AdditionalInputs StepCopyID not in this Task: {label} [{i}] -> {extra.get('StepCopyID')}")

            connector = step.get("Connector") or {}
            gv = _gv(connector)
            if not gv:
                issues.append(f"step Connector missing Guid+Version: {label}")
                catalog_conn = None
            else:
                used_connectors.add(gv)
                if gv not in listed_connectors:
                    issues.append(f"connector not in Connectors[]: {label} -> {connector}")
                catalog_conn = conn_cat.get(gv)
                if not catalog_conn and gv not in stale_conn:
                    stale_conn.add(gv)
                    extra = ""
                    if gv[0] in conn_vers:
                        extra = f" (catalog has versions {sorted(conn_vers[gv[0]])})"
                    catalog_notes.append(
                        f"connector not in data/connectors.json (catalog may be stale): {connector}{extra}"
                    )
            action_code = step.get("SelectedActionCode")
            action = None
            if catalog_conn:
                actions = catalog_conn.get("actions") or []
                action = next((a for a in actions if a.get("code") == action_code), None)
                if action_code and action is None:
                    known = [a.get("code") for a in actions]
                    issues.append(f"SelectedActionCode not on connector: {label} -> {action_code} (known {known})")
            agent = _norm(step.get("AgentCopyID"))
            if not agent:
                issues.append(f"AgentCopyID missing: {label}")
            elif gv and gv[0] in by_guid_kinds:
                kinds = by_guid_kinds[gv[0]]
                kind = "shared" if agent == SHARED_AGENT else "remote"
                if kind not in kinds:
                    issues.append(f"connector not allowed on {kind} agent: {label} Guid {connector.get('Guid')} allowed {kinds}")

            refs = {(str(r.get("guid")).lower(), str(r.get("version"))) for r in (action.get("configurationRefs") or [])} if action else set()
            wraps = step.get("Configurations") or []
            if action is not None and refs and not wraps:
                issues.append(f"step missing Configuration for configurationRefs[]: {label}")
            for wrap in wraps:
                check_id(wrap, f"StepConfiguration {label} {wrap.get('CopyID')}", "StepConfigurations")
                ccid = _norm(wrap.get("ConfigurationCopyID"))
                tgt = top_cfg.get(ccid) if ccid else None
                if ccid and tgt is None:
                    issues.append(f"ConfigurationCopyID not in Configurations[]: {label} -> {wrap.get('ConfigurationCopyID')}")
                wrap_gv = _gv(wrap.get("ConfigurationSchema") if isinstance(wrap.get("ConfigurationSchema"), dict) else None)
                if wrap_gv and wrap_gv not in cfg_cat and wrap_gv not in stale_cfg:
                    stale_cfg.add(wrap_gv)
                    extra = ""
                    if wrap_gv[0] in cfg_vers:
                        extra = f" (catalog has versions {sorted(cfg_vers[wrap_gv[0]])})"
                    catalog_notes.append(
                        f"configurationSchema not in data/configuration-schemas.json (catalog may be stale): {wrap.get('ConfigurationSchema')}{extra}"
                    )
                if wrap_gv and refs and wrap_gv not in refs:
                    if any(r[0] == wrap_gv[0] for r in refs):
                        catalog_notes.append(
                            f"configurationSchema version not in action configurationRefs[] (catalog may be stale): {label} -> {wrap.get('ConfigurationSchema')}"
                        )
                    else:
                        issues.append(f"configurationSchema not in action configurationRefs[]: {label} -> {wrap.get('ConfigurationSchema')}")
                if tgt is not None:
                    tgt_gv = _gv(tgt.get("ConfigurationSchema") if isinstance(tgt.get("ConfigurationSchema"), dict) else None)
                    if wrap_gv and tgt_gv and wrap_gv != tgt_gv:
                        issues.append(f"ConfigurationSchema mismatch vs Configurations[]: {label}")

        if (task.get("Steps") or []) and roots != 1:
            issues.append(f"exactly one PrevStepCopyID null required: {tname} has {roots}")
        if task.get("Type") == 2 and tid and tid not in bound_tasks:
            issues.append(f"Task.Type Endpoint but no Endpoint *InputTaskCopyID: {tname}")

    conn_by_gv = {
        (_norm(c.get("Guid")), str(c.get("Version") or "")): c
        for c in (data.get("Connectors") or [])
        if c.get("Guid")
    }
    for unused in sorted(listed_connectors - used_connectors):
        row = conn_by_gv.get(unused) or {}
        name = row.get("Name") or ""
        guid, version = unused
        label = " ".join(p for p in (name, guid, version) if p)
        issues.append(f"unused connector in Connectors[]: {label}")

    walk_copyids(data, "transfer")

    for cfg in data.get("Configurations") or []:
        cid = _norm(cfg.get("CopyID"))
        if cid and cid not in used_configurations:
            name = cfg.get("Name") or ""
            guid = cfg.get("CopyID") or ""
            label = " ".join(p for p in (name, guid) if p)
            issues.append(f"unused configuration in Configurations[]: {label}")

    for collection, used, kind in (
        ("TaskGroups", used_task_groups, "task group"),
        ("EndpointGroups", used_endpoint_groups, "endpoint group"),
    ):
        for grp in data.get(collection) or []:
            cid = _norm(grp.get("CopyID"))
            if cid and cid not in used:
                name = grp.get("Name") or grp.get("Slug") or ""
                guid = grp.get("CopyID") or ""
                label = " ".join(p for p in (name, guid) if p)
                issues.append(f"unused {kind} in {collection}[]: {label}")

    # de-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for line in issues:
        if line not in seen:
            seen.add(line)
            out.append(line)
    seen_cat: set[str] = set()
    notes: list[str] = []
    for line in catalog_notes:
        if line not in seen_cat:
            seen_cat.add(line)
            notes.append(line)
    return out, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file",
        type=Path,
        help="Config Transfer JSON, or a split working/ directory",
    )
    parser.add_argument("--data-dir", type=Path, default=DATA, help="KB catalog directory (default: data/)")
    args = parser.parse_args()
    path: Path = args.file
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 2
    try:
        data = load_transfer_document(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 2
    catalogs = load_catalogs(args.data_dir)
    issues, catalog_notes = check_transfer(data, catalogs)
    for line in catalog_notes:
        print(line, file=sys.stderr)
    for line in issues:
        print(line)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
