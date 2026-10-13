"""Split a Config Transfer JSON into per-entity files and assemble it back.

Working layout (projects/<name>/working/):
  _transfer.json   envelope (scalars only)
  _meta.json       collection key order + filenames
  <folder>/<id>.json
    Guid+Version → {guid}_{version}.json (system DataSchemas, Connectors)
    else CopyID → {copyId}.json
    EntityComments → {EntityCopyID}.json
  Task includes Steps (one file). One DataSchemas[] row per file.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

TRANSFER_FILE = "_transfer.json"
META_FILE = "_meta.json"
META_FORMAT = 1

COLLECTION_FOLDERS: dict[str, str] = {
    "Tasks": "tasks",
    "Connectors": "connectors",
    "DataSchemas": "data-schemas",
    "Agents": "agents",
    "TaskGroups": "task-groups",
    "EndpointGroups": "endpoint-groups",
    "Endpoints": "endpoints",
    "SecondaryTokens": "secondary-tokens",
    "Configurations": "configurations",
    "Variables": "variables",
    "EntityComments": "entity-comments",
    "VariableGroups": "variable-groups",
    "Templates": "templates",
    "Tags": "tags",
    "TagMappings": "tag-mappings",
    "AuthConnections": "auth-connections",
}

_PASCAL_BREAK_1 = re.compile(r"(.)([A-Z][a-z]+)")
_PASCAL_BREAK_2 = re.compile(r"([a-z0-9])([A-Z])")
_UNSAFE_FILE = re.compile(r"[^A-Za-z0-9._-]+")


def pascal_to_kebab(name: str) -> str:
    s1 = _PASCAL_BREAK_1.sub(r"\1-\2", name)
    return _PASCAL_BREAK_2.sub(r"\1-\2", s1).lower()


def folder_for_key(key: str) -> str:
    return COLLECTION_FOLDERS.get(key) or pascal_to_kebab(key)


def is_split_dir(path: Path) -> bool:
    return path.is_dir() and (path / TRANSFER_FILE).is_file() and (path / META_FILE).is_file()


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def entity_filename(entity: dict[str, Any]) -> str:
    guid = str(entity.get("Guid") or "").strip()
    version = str(entity.get("Version") or "").strip()
    if guid and version:
        return _safe_name(f"{guid}_{version}") + ".json"
    copy_id = str(entity.get("CopyID") or "").strip()
    if copy_id:
        return _safe_name(copy_id) + ".json"
    entity_copy = str(entity.get("EntityCopyID") or "").strip()
    if entity_copy:
        return _safe_name(entity_copy) + ".json"
    raise ValueError(
        "entity has neither Guid+Version, CopyID, nor EntityCopyID "
        f"(Name={entity.get('Name')!r} keys={list(entity)})"
    )


def _safe_name(name: str) -> str:
    cleaned = _UNSAFE_FILE.sub("_", name).strip("._")
    if not cleaned:
        raise ValueError(f"empty filename from {name!r}")
    return cleaned


def assembled_upload_filename(company: str, when: datetime | None = None) -> str:
    """Upload basename: company Name + ApplicationBackup-style ``yyyyMMdd_HHmmss``."""
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    base = _safe_name((company or "").strip() or "transfer")
    return f"{base}_{stamp}.json"


@dataclass
class SplitStats:
    name: str
    dest: Path
    files: int
    counts: dict[str, int] = field(default_factory=dict)
    sensitive_names: list[str] = field(default_factory=list)

    def format_lines(self, snapshot: Path | None = None) -> list[str]:
        lines: list[str] = []
        if snapshot is not None:
            lines.append(f"Wrote {snapshot} ({snapshot.stat().st_size} bytes)")
        lines.append(f"Split {self.dest} ({self.files} files)")
        lines.append(f"Name={self.name}")
        alias = {
            "Tasks": "tasks",
            "Endpoints": "endpoints",
            "DataSchemas": "dataSchemas",
            "Configurations": "configurations",
            "Connectors": "connectors",
            "Agents": "agents",
            "TaskGroups": "taskGroups",
            "EndpointGroups": "endpointGroups",
            "Variables": "variables",
            "EntityComments": "entityComments",
        }
        for key, label in alias.items():
            if key in self.counts:
                lines.append(f"{label}={self.counts[key]}")
        if self.sensitive_names:
            lines.append("sensitiveVariables=" + ", ".join(self.sensitive_names))
        else:
            lines.append("sensitiveVariables=")
        return lines


def split_transfer(src: Path, dest: Path) -> SplitStats:
    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{src}: expected a JSON object")
    dest = dest.resolve()
    return split_data(data, dest)


def split_data(data: dict[str, Any], dest: Path) -> SplitStats:
    dest = dest.resolve()
    staging = dest / ".split-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    envelope: dict[str, Any] = {}
    collections: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    file_count = 0

    for key, value in data.items():
        if isinstance(value, list):
            folder = folder_for_key(key)
            files: list[str] = []
            used: set[str] = set()
            for i, item in enumerate(value):
                if not isinstance(item, dict):
                    raise ValueError(f"{key}[{i}]: expected an object")
                name = entity_filename(item)
                if name in used:
                    raise ValueError(f"{key}: duplicate filename {name}")
                used.add(name)
                dump_json(staging / folder / name, item)
                files.append(name)
                file_count += 1
            counts[key] = len(files)
            collections.append({"key": key, "folder": folder, "files": files})
        else:
            envelope[key] = value

    dump_json(staging / TRANSFER_FILE, envelope)
    dump_json(
        staging / META_FILE,
        {"format": META_FORMAT, "collections": collections},
    )
    file_count += 2

    _replace_working(dest, staging)

    sensitive = [
        str(v.get("Name") or v.get("Code") or "")
        for v in (data.get("Variables") or [])
        if isinstance(v, dict) and v.get("IsSensitive")
    ]
    sensitive = [n for n in sensitive if n]
    return SplitStats(
        name=str(envelope.get("Name") or ""),
        dest=dest,
        files=file_count,
        counts=counts,
        sensitive_names=sensitive,
    )


def _replace_working(dest: Path, staging: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    _clear_split_artifacts(dest)
    for child in staging.iterdir():
        target = dest / child.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(child), str(target))
    shutil.rmtree(staging, ignore_errors=True)


def _clear_split_artifacts(dest: Path) -> None:
    """Wipe working/ so a new split cannot leave leftover entity files."""
    keep = {".gitkeep", ".split-staging"}
    if not dest.is_dir():
        return
    for child in dest.iterdir():
        if child.name in keep:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def assemble_transfer(src: Path) -> dict[str, Any]:
    src = src.resolve()
    if not is_split_dir(src):
        raise ValueError(f"{src}: not a split working directory (_transfer.json + _meta.json)")
    envelope = json.loads((src / TRANSFER_FILE).read_text(encoding="utf-8"))
    if not isinstance(envelope, dict):
        raise ValueError(f"{src / TRANSFER_FILE}: expected a JSON object")
    meta = json.loads((src / META_FILE).read_text(encoding="utf-8"))
    collections = meta.get("collections")
    if not isinstance(collections, list):
        raise ValueError(f"{src / META_FILE}: collections must be a list")
    out = dict(envelope)
    for col in collections:
        if not isinstance(col, dict):
            continue
        key = col.get("key")
        folder = col.get("folder")
        listed = col.get("files") or []
        if not key or not folder:
            raise ValueError(f"{src / META_FILE}: collection missing key/folder")
        dir_path = src / str(folder)
        items: list[Any] = []
        seen: set[str] = set()
        for name in listed:
            seen.add(str(name))
            path = dir_path / str(name)
            if not path.is_file():
                continue
            items.append(json.loads(path.read_text(encoding="utf-8")))
        if dir_path.is_dir():
            extra = sorted(
                p.name
                for p in dir_path.glob("*.json")
                if p.is_file() and p.name not in seen and not p.name.startswith("_")
            )
            for name in extra:
                items.append(json.loads((dir_path / name).read_text(encoding="utf-8")))
        out[str(key)] = items
    return out


def assemble_to(src: Path, dest: Path) -> Path:
    dump_json(dest, assemble_transfer(src))
    return dest


def load_transfer_document(path: Path) -> dict[str, Any]:
    path = Path(path)
    if path.is_dir():
        return assemble_transfer(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def iter_collection_files(working: Path, key: str) -> Iterator[Path]:
    meta = json.loads((working / META_FILE).read_text(encoding="utf-8"))
    for col in meta.get("collections") or []:
        if not isinstance(col, dict) or col.get("key") != key:
            continue
        folder = working / str(col.get("folder") or folder_for_key(key))
        listed = [str(n) for n in (col.get("files") or [])]
        seen: set[str] = set()
        for name in listed:
            seen.add(name)
            path = folder / name
            if path.is_file():
                yield path
        if folder.is_dir():
            for path in sorted(folder.glob("*.json")):
                if path.name not in seen and path.is_file():
                    yield path
        return
    folder = working / folder_for_key(key)
    if folder.is_dir():
        yield from sorted(p for p in folder.glob("*.json") if p.is_file())


def find_configuration_path(
    working: Path,
    *,
    copy_id: str | None = None,
    name: str | None = None,
) -> Path:
    from transfer_util import find_configuration

    configs: list[dict[str, Any]] = []
    paths: dict[str, Path] = {}
    for path in iter_collection_files(working, "Configurations"):
        cfg = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            continue
        configs.append(cfg)
        cid = str(cfg.get("CopyID") or "")
        if cid:
            paths[cid] = path
    tasks: list[dict[str, Any]] = []
    for path in iter_collection_files(working, "Tasks"):
        task = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(task, dict):
            tasks.append(task)
    found = find_configuration(
        {"Configurations": configs, "Tasks": tasks},
        copy_id=copy_id,
        name=name,
    )
    cid = str(found.get("CopyID") or "")
    if cid not in paths:
        raise KeyError(f"Configuration {cid} file missing under {working}")
    return paths[cid]


class WorkingBundle:
    """JSON file to schema-check / Upload. Split working/ is assembled to a temp file."""

    def __init__(self, project: Path, file: Path | None = None) -> None:
        self.project = Path(project)
        self.split_dir: Path | None = None
        self.path: Path
        self._temp = False
        explicit = Path(file) if file is not None else None
        if explicit is not None and explicit.is_dir():
            if not is_split_dir(explicit):
                raise ValueError(f"{explicit}: not a split working directory")
            self.split_dir = explicit
            self.path = self._assemble_temp(explicit)
            self._temp = True
            return
        if explicit is not None:
            if not explicit.is_file():
                raise ValueError(f"{explicit}: file not found")
            self.path = explicit
            return
        working = self.project / "working"
        if is_split_dir(working):
            self.split_dir = working
            self.path = self._assemble_temp(working)
            self._temp = True
            return
        jsons = sorted(p for p in working.glob("*.json") if p.is_file())
        if len(jsons) == 1:
            self.path = jsons[0]
            return
        if not jsons:
            raise ValueError(
                f"{working}: no split tree and no *.json. Run /download-config first."
            )
        names = ", ".join(p.name for p in jsons)
        raise ValueError(f"{working}: multiple JSON files ({names}). Pass --file path.")

    @staticmethod
    def _assemble_temp(src: Path) -> Path:
        envelope: dict[str, Any] = {}
        transfer_path = src / TRANSFER_FILE
        if transfer_path.is_file():
            loaded = json.loads(transfer_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                envelope = loaded
        company = str(envelope.get("Name") or "").strip() or src.parent.name
        filename = assembled_upload_filename(company)
        dest = Path(tempfile.gettempdir()) / filename
        if dest.exists():
            handle, name = tempfile.mkstemp(
                prefix=f"{dest.stem}_",
                suffix=".json",
                dir=dest.parent,
            )
            os.close(handle)
            dest = Path(name)
        assemble_to(src, dest)
        return dest

    def refresh(self) -> None:
        if self.split_dir is not None:
            assemble_to(self.split_dir, self.path)

    def close(self) -> None:
        if self._temp:
            self.path.unlink(missing_ok=True)

    def __enter__(self) -> WorkingBundle:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
