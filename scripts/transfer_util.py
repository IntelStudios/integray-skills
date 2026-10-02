"""Helpers for Config Transfer JSON on disk (Statement, stamp, conventions)."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

GENERATED_RE = re.compile(r"generated \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
PRAGUE = ZoneInfo("Europe/Prague")

CONVENTION_KEYS = {
    "publish": re.compile(
        r"Publish after dry-run:\**\s*(ask|auto)", re.IGNORECASE
    ),
    "download": re.compile(
        r"Download after publish:\**\s*(ask|auto)", re.IGNORECASE
    ),
}


def load_transfer(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def save_transfer(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_configuration_payload(raw: Any) -> tuple[Any, dict[str, Any], bool]:
    """Return (original, object, was_json_string)."""
    if isinstance(raw, str):
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError("Configuration JSON string is not an object")
        return raw, obj, True
    if isinstance(raw, dict):
        return raw, raw, False
    raise ValueError(f"Configuration is {type(raw).__name__}, expected object or JSON string")


def dump_configuration_payload(obj: dict[str, Any], *, was_json_string: bool) -> Any:
    if was_json_string:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return obj


def statement_of(cfg: dict[str, Any]) -> str | None:
    raw = cfg.get("Configuration")
    if raw is None:
        return None
    try:
        _, obj, _ = parse_configuration_payload(raw)
    except (ValueError, json.JSONDecodeError):
        return None
    stmt = obj.get("Statement")
    return stmt if isinstance(stmt, str) else None


def set_statement(cfg: dict[str, Any], statement: str) -> None:
    raw = cfg.get("Configuration")
    _, obj, was_str = parse_configuration_payload(raw)
    obj["Statement"] = statement
    cfg["Configuration"] = dump_configuration_payload(obj, was_json_string=was_str)


def now_prague_stamp() -> str:
    return datetime.now(PRAGUE).strftime("%Y-%m-%d %H:%M:%S")


def stamp_generated(text: str, when: str | None = None) -> tuple[str, str]:
    """Replace `generated YYYY-MM-DD HH:MM:SS`. Returns (new_text, new_stamp_line)."""
    stamp = f"generated {when or now_prague_stamp()}"
    matches = list(GENERATED_RE.finditer(text))
    if not matches:
        raise ValueError(
            "no `generated YYYY-MM-DD HH:MM:SS` in Statement"
        )
    if len(matches) > 1:
        raise ValueError(f"Statement has {len(matches)} generated stamps; expected 1")
    return GENERATED_RE.sub(stamp, text, count=1), stamp


def find_configuration(
    data: dict[str, Any],
    *,
    copy_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    configs = data.get("Configurations") or []
    if not isinstance(configs, list):
        raise ValueError("Configurations[] missing")
    if copy_id:
        cid = copy_id.strip().lower()
        hits = [
            c
            for c in configs
            if isinstance(c, dict) and str(c.get("CopyID") or "").lower() == cid
        ]
        if not hits:
            raise KeyError(f"no Configuration CopyID {copy_id}")
        if len(hits) > 1:
            raise KeyError(f"multiple Configurations with CopyID {copy_id}")
        return hits[0]
    if not name:
        raise ValueError("pass --copy-id or --name")
    by_id = {
        str(c.get("CopyID")): c
        for c in configs
        if isinstance(c, dict) and c.get("CopyID")
    }
    hits: list[dict[str, Any]] = []
    for c in configs:
        if isinstance(c, dict) and c.get("Name") == name:
            hits.append(c)
    for task in data.get("Tasks") or []:
        if not isinstance(task, dict):
            continue
        for step in task.get("Steps") or []:
            if not isinstance(step, dict) or step.get("Name") != name:
                continue
            for wrap in step.get("Configurations") or []:
                if not isinstance(wrap, dict):
                    continue
                cid = wrap.get("ConfigurationCopyID")
                if cid and cid in by_id:
                    hits.append(by_id[cid])
    # de-dupe by CopyID
    uniq: dict[str, dict[str, Any]] = {}
    for c in hits:
        uniq[str(c.get("CopyID"))] = c
    found = list(uniq.values())
    if not found:
        raise KeyError(f"no Configuration or Step named {name!r}")
    if len(found) > 1:
        ids = ", ".join(str(c.get("CopyID")) for c in found)
        raise KeyError(f"name {name!r} matches multiple CopyIDs: {ids}")
    return found[0]


def step_labels_by_configuration(data: dict[str, Any]) -> dict[str, list[str]]:
    labels: dict[str, list[str]] = {}
    for task in data.get("Tasks") or []:
        if not isinstance(task, dict):
            continue
        tname = task.get("Name") or "?"
        for step in task.get("Steps") or []:
            if not isinstance(step, dict):
                continue
            sname = step.get("Name") or "?"
            for wrap in step.get("Configurations") or []:
                if not isinstance(wrap, dict):
                    continue
                cid = wrap.get("ConfigurationCopyID")
                if cid:
                    labels.setdefault(str(cid), []).append(f"{tname} / {sname}")
    return labels


def parse_conventions(path: Path | None) -> dict[str, str]:
    """ask | auto for publish and download. Missing file or key → ask.

    Backup before Process is always; it is not a convention.
    """
    out = {"publish": "ask", "download": "ask"}
    if path is None or not path.is_file():
        return out
    text = path.read_text(encoding="utf-8")
    for key, cre in CONVENTION_KEYS.items():
        m = cre.search(text)
        if m:
            out[key] = m.group(1).lower()
    return out
