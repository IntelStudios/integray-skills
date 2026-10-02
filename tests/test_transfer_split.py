"""Roundtrip split/assemble of a Config Transfer JSON."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from transfer_split import (  # noqa: E402
    WorkingBundle,
    WorkingOccupiedError,
    assembled_upload_filename,
    assemble_transfer,
    is_split_dir,
    split_data,
    split_transfer,
    working_is_occupied,
)

EXAMPLE = ROOT / "examples" / "generic_worked_example.json"


class TransferSplitTests(unittest.TestCase):
    def test_roundtrip_generic_example(self) -> None:
        src = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        dest = Path(tempfile.mkdtemp()) / "working"
        stats = split_data(src, dest)
        self.assertTrue(is_split_dir(dest))
        self.assertEqual(stats.name, "Generic Worked Example")
        self.assertGreater(stats.counts.get("Tasks", 0), 0)
        self.assertTrue((dest / "tasks").is_dir())
        assembled = assemble_transfer(dest)
        self.assertEqual(assembled, src)

    def test_split_transfer_cli_shape(self) -> None:
        dest = Path(tempfile.mkdtemp()) / "working"
        stats = split_transfer(EXAMPLE, dest)
        lines = stats.format_lines(EXAMPLE)
        self.assertTrue(lines[0].startswith("Wrote "))
        self.assertTrue(any(line.startswith("Name=") for line in lines))
        self.assertTrue(any(line.startswith("tasks=") for line in lines))

    def test_system_schema_uses_guid_version_filename(self) -> None:
        src = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        dest = Path(tempfile.mkdtemp()) / "working"
        split_data(src, dest)
        schemas = list((dest / "data-schemas").glob("*.json"))
        self.assertTrue(schemas)
        named = {p.name for p in schemas}
        for ds in src.get("DataSchemas") or []:
            guid = ds.get("Guid")
            version = ds.get("Version")
            if guid and version:
                self.assertIn(f"{guid}_{version}.json", named)
            else:
                self.assertIn(f"{ds['CopyID']}.json", named)

    def test_occupied_working_refuses_without_replace(self) -> None:
        dest = Path(tempfile.mkdtemp()) / "working"
        split_transfer(EXAMPLE, dest)
        self.assertTrue(working_is_occupied(dest))
        with self.assertRaises(WorkingOccupiedError):
            split_transfer(EXAMPLE, dest)
        split_transfer(EXAMPLE, dest, replace=True)
        empty = Path(tempfile.mkdtemp()) / "working"
        empty.mkdir()
        (empty / ".gitkeep").write_text("", encoding="utf-8")
        self.assertFalse(working_is_occupied(empty))
        split_transfer(EXAMPLE, empty)

    def test_assembled_upload_filename_is_company_and_stamp(self) -> None:
        when = datetime(2026, 10, 2, 12, 27, 13)
        self.assertEqual(
            assembled_upload_filename("Self test", when),
            "Self_test_20261002_122713.json",
        )

    def test_working_bundle_temp_uses_transfer_name(self) -> None:
        dest = Path(tempfile.mkdtemp()) / "working"
        split_data(json.loads(EXAMPLE.read_text(encoding="utf-8")), dest)
        bundle = WorkingBundle(dest.parent, dest)
        try:
            self.assertRegex(
                bundle.path.name,
                r"^Generic_Worked_Example_\d{8}_\d{6}(_.*)?\.json$",
            )
        finally:
            bundle.close()
        self.assertFalse(bundle.path.exists())


if __name__ == "__main__":
    unittest.main()
