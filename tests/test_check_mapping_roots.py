"""Mapping paths must start at a Step or bound Endpoint Name."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "check_transfer_schemas", ROOT / "scripts" / "check-transfer-schemas.py"
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
check_transfer = _mod.check_transfer


def _empty_catalogs() -> dict:
    return {
        "connectors": {},
        "connector_versions": {},
        "config_schemas": {},
        "config_schema_versions": {},
        "restrictions": {},
    }


GUID = "a1865bf9-504c-43c7-89d5-b9a940432d44"
SHARED = "11111111-1111-1111-1111-111111111111"
TASK = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
STEP = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
EP = "cccccccc-cccc-cccc-cccc-cccccccccccc"
SCHEMA = "dddddddd-dddd-dddd-dddd-dddddddddddd"
COL_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"


def _transfer(*, mapping: dict, endpoint_name: str, output_mapping: dict | None = None) -> dict:
    return {
        "TransferType": "ConfigTransfer",
        "Connectors": [{"Name": "Delay", "Guid": GUID, "Version": "3.0.3"}],
        "DataSchemas": [
            {
                "ID": 1,
                "Name": "In",
                "CopyID": SCHEMA,
                "Columns": [
                    {
                        "Order": 0,
                        "Type": 2,
                        "AllowNull": False,
                        "ID": 1,
                        "Name": "ID",
                        "CopyID": COL_ID,
                    }
                ],
            }
        ],
        "Tasks": [
            {
                "ID": 1,
                "Name": "Runner",
                "CopyID": TASK,
                "Type": 2,
                "Steps": [
                    {
                        "ID": 1,
                        "Name": "Run",
                        "CopyID": STEP,
                        "PrevStepCopyID": None,
                        "AgentCopyID": SHARED,
                        "Connector": {"Guid": GUID, "Version": "3.0.3"},
                        "InputSchema": {"CopyID": SCHEMA},
                        "InputSchemaMapping": mapping,
                    }
                ],
            }
        ],
        "Endpoints": [
            {
                "ID": 1,
                "Name": endpoint_name,
                "Slug": "run",
                "CopyID": EP,
                "PostInputTaskCopyID": TASK,
                "PostInputSchema": {"CopyID": SCHEMA},
                "PostOutputMapping": output_mapping,
            }
        ],
    }


class MappingRootTests(unittest.TestCase):
    def test_stale_endpoint_name_is_flagged(self) -> None:
        data = _transfer(
            mapping={"ID": "05 Starter run.ID"},
            endpoint_name="004 Starter Runner",
        )
        issues, _ = check_transfer(data, _empty_catalogs())
        hits = [line for line in issues if line.startswith("mapping path root unknown")]
        self.assertEqual(len(hits), 1)
        self.assertIn("05 Starter run.ID", hits[0])

    def test_bound_endpoint_name_is_ok(self) -> None:
        data = _transfer(
            mapping={"ID": "004 Starter Runner.ID"},
            endpoint_name="004 Starter Runner",
        )
        issues, _ = check_transfer(data, _empty_catalogs())
        hits = [line for line in issues if line.startswith("mapping path root unknown")]
        self.assertEqual(hits, [])

    def test_step_name_root_is_ok(self) -> None:
        data = _transfer(
            mapping={"ID": "Run.ID"},
            endpoint_name="004 Starter Runner",
        )
        issues, _ = check_transfer(data, _empty_catalogs())
        hits = [line for line in issues if line.startswith("mapping path root unknown")]
        self.assertEqual(hits, [])

    def test_stale_output_mapping_is_flagged(self) -> None:
        data = _transfer(
            mapping={"ID": "004 Starter Runner.ID"},
            endpoint_name="004 Starter Runner",
            output_mapping={"ID": "Old Step.ID"},
        )
        issues, _ = check_transfer(data, _empty_catalogs())
        hits = [line for line in issues if "PostOutputMapping" in line]
        self.assertEqual(len(hits), 1)
        self.assertIn("Old Step.ID", hits[0])


if __name__ == "__main__":
    unittest.main()
