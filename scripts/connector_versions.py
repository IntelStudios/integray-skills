"""Company connector Guid+Version vs KB catalog newest (advisory)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_version(token: str) -> tuple[int, ...]:
    parts: list[int] = []
    for bit in str(token).split("."):
        try:
            parts.append(int(bit))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def newest_in_catalog(data_dir: Path) -> dict[str, tuple[str, str]]:
    """guid → (version, name) for the highest Version in data/connectors.json."""
    items = json.loads((data_dir / "connectors.json").read_text(encoding="utf-8"))
    best: dict[str, tuple[str, str]] = {}
    for item in items:
        guid = str(item.get("guid") or "").lower()
        ver = str(item.get("version") or "")
        name = str(item.get("name") or guid)
        if not guid or not ver:
            continue
        prev = best.get(guid)
        if prev is None or parse_version(ver) > parse_version(prev[0]):
            best[guid] = (ver, name)
    return best


def used_by_guid(data: dict[str, Any]) -> dict[str, dict[str, int]]:
    """guid → {version: step_count} from Steps[].Connector."""
    used: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for task in data.get("Tasks") or []:
        if not isinstance(task, dict):
            continue
        for step in task.get("Steps") or []:
            if not isinstance(step, dict):
                continue
            conn = step.get("Connector") or {}
            guid = str(conn.get("Guid") or "").lower()
            ver = str(conn.get("Version") or "")
            if guid and ver:
                used[guid][ver] += 1
    return used


def names_from_transfer(data: dict[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for item in data.get("Connectors") or []:
        if not isinstance(item, dict):
            continue
        guid = str(item.get("Guid") or "").lower()
        name = str(item.get("Name") or "")
        if guid and name:
            names[guid] = name
    return names


def advise(
    data: dict[str, Any], catalog_newest: dict[str, tuple[str, str]]
) -> list[str]:
    used = used_by_guid(data)
    names = names_from_transfer(data)
    lines: list[str] = []
    for guid in sorted(used):
        versions = used[guid]
        name = names.get(guid) or (
            catalog_newest[guid][1] if guid in catalog_newest else guid
        )
        listed = ", ".join(
            f"{ver} ({n} step{'s' if n != 1 else ''})"
            for ver in sorted(versions, key=parse_version)
            for n in (versions[ver],)
        )
        newest = catalog_newest[guid][0] if guid in catalog_newest else ""
        max_used = max(versions, key=parse_version)
        if len(versions) > 1:
            target = newest or max_used
            lines.append(
                f"connector-mixed: {name} {guid} used {listed}; unify to {target}"
                + (
                    f"; if {target} is not on the instance, "
                    "update connectors in Integray first"
                    if newest
                    else ""
                )
            )
        elif newest and parse_version(max_used) < parse_version(newest):
            lines.append(
                f"connector-outdated: {name} {guid} used {listed}; "
                f"catalog newest {newest}; "
                "if that version is not on the instance, "
                "update connectors in Integray first"
            )
    return lines
