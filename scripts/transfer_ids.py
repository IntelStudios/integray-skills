"""Collect numeric entity IDs from a Config Transfer (for allocating new ones)."""

from __future__ import annotations

from typing import Any

from transfer_split import load_transfer_document


def collect_entity_ids(obj: Any) -> set[int]:
    """Positive `ID` values on entity-like objects. Does not rewrite anything."""
    found: set[int] = set()
    _walk(obj, found)
    return found


def _walk(obj: Any, found: set[int]) -> None:
    if isinstance(obj, dict):
        eid = obj.get("ID")
        if isinstance(eid, int) and eid > 0 and _is_entity(obj):
            found.add(eid)
        for key, val in obj.items():
            if key == "Configuration" and isinstance(val, str):
                continue
            _walk(val, found)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, found)


def _is_entity(obj: dict[str, Any]) -> bool:
    if obj.get("CopyID") or obj.get("EntityCopyID"):
        return True
    if obj.get("Guid") and obj.get("Version"):
        return True
    if obj.get("TransferType"):
        return True
    return False


def next_transfer_ids(data: dict[str, Any], count: int = 1) -> list[int]:
    if count < 1:
        raise ValueError("count must be >= 1")
    used = collect_entity_ids(data)
    start = max(used) + 1 if used else 1
    return list(range(start, start + count))


def next_transfer_ids_from_path(path, count: int = 1) -> list[int]:
    return next_transfer_ids(load_transfer_document(path), count)
