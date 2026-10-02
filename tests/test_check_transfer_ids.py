"""ID uniqueness is per entity kind, not global."""

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


def _dup_lines(issues: list[str]) -> list[str]:
    return [line for line in issues if line.startswith("duplicate ID")]


class IdUniquenessTests(unittest.TestCase):
    def test_same_id_across_kinds_is_ok(self) -> None:
        data = {
            "TransferType": "ConfigTransfer",
            "DataSchemas": [
                {
                    "ID": 1,
                    "Name": "Schema",
                    "CopyID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "Columns": [
                        {
                            "Order": 0,
                            "Type": 2,
                            "AllowNull": True,
                            "ID": 1,
                            "Name": "Col",
                            "CopyID": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                        }
                    ],
                }
            ],
            "Tasks": [
                {
                    "ID": 1,
                    "Name": "Task",
                    "CopyID": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                    "Type": 1,
                    "Steps": [
                        {
                            "ID": 1,
                            "Name": "Step",
                            "CopyID": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                            "PrevStepCopyID": None,
                            "AgentCopyID": "11111111-1111-1111-1111-111111111111",
                            "Configurations": [
                                {
                                    "ID": 1,
                                    "CopyID": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                                    "ConfigurationCopyID": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                                }
                            ],
                        }
                    ],
                }
            ],
            "Configurations": [
                {
                    "ID": 1,
                    "Name": "Cfg",
                    "CopyID": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                    "IsShared": True,
                    "Configuration": "{}",
                }
            ],
        }
        issues, _ = check_transfer(data, _empty_catalogs())
        self.assertEqual(_dup_lines(issues), [])

    def test_same_kind_collision_is_flagged(self) -> None:
        data = {
            "TransferType": "ConfigTransfer",
            "Tasks": [
                {
                    "ID": 7,
                    "Name": "A",
                    "CopyID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "Type": 1,
                    "Steps": [],
                },
                {
                    "ID": 7,
                    "Name": "B",
                    "CopyID": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                    "Type": 1,
                    "Steps": [],
                },
            ],
        }
        issues, _ = check_transfer(data, _empty_catalogs())
        dups = _dup_lines(issues)
        self.assertEqual(len(dups), 1)
        self.assertIn("duplicate ID 7 in Tasks", dups[0])


class UnusedConnectorTests(unittest.TestCase):
    def test_listed_but_unused_connector_is_flagged(self) -> None:
        data = {
            "TransferType": "ConfigTransfer",
            "Connectors": [
                {
                    "Name": "Delay",
                    "Guid": "a1865bf9-504c-43c7-89d5-b9a940432d44",
                    "Version": "3.0.3",
                }
            ],
            "Tasks": [],
        }
        issues, _ = check_transfer(data, _empty_catalogs())
        unused = [line for line in issues if line.startswith("unused connector")]
        self.assertEqual(len(unused), 1)
        self.assertIn("3.0.3", unused[0])

    def test_used_connector_is_ok(self) -> None:
        guid = "a1865bf9-504c-43c7-89d5-b9a940432d44"
        data = {
            "TransferType": "ConfigTransfer",
            "Connectors": [{"Name": "Delay", "Guid": guid, "Version": "3.0.3"}],
            "Tasks": [
                {
                    "ID": 1,
                    "Name": "Task",
                    "CopyID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "Type": 1,
                    "Steps": [
                        {
                            "ID": 1,
                            "Name": "Step",
                            "CopyID": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                            "PrevStepCopyID": None,
                            "AgentCopyID": "11111111-1111-1111-1111-111111111111",
                            "Connector": {"Guid": guid, "Version": "3.0.3"},
                        }
                    ],
                }
            ],
        }
        issues, _ = check_transfer(data, _empty_catalogs())
        self.assertFalse(any(line.startswith("unused connector") for line in issues))


class UnusedEntityTests(unittest.TestCase):
    def test_unused_configuration_is_flagged(self) -> None:
        data = {
            "TransferType": "ConfigTransfer",
            "Configurations": [
                {
                    "ID": 1,
                    "Name": "Orphan",
                    "CopyID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "IsShared": True,
                    "Configuration": "{}",
                }
            ],
        }
        issues, _ = check_transfer(data, _empty_catalogs())
        unused = [line for line in issues if line.startswith("unused configuration")]
        self.assertEqual(len(unused), 1)
        self.assertIn("Orphan", unused[0])

    def test_configuration_referenced_by_step_is_ok(self) -> None:
        cid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        data = {
            "TransferType": "ConfigTransfer",
            "Configurations": [
                {
                    "ID": 1,
                    "Name": "Used",
                    "CopyID": cid,
                    "IsShared": True,
                    "Configuration": "{}",
                }
            ],
            "Tasks": [
                {
                    "ID": 1,
                    "Name": "Task",
                    "CopyID": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                    "Type": 1,
                    "Steps": [
                        {
                            "ID": 1,
                            "Name": "Step",
                            "CopyID": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                            "PrevStepCopyID": None,
                            "AgentCopyID": "11111111-1111-1111-1111-111111111111",
                            "Configurations": [
                                {
                                    "ID": 1,
                                    "CopyID": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                                    "ConfigurationCopyID": cid,
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        issues, _ = check_transfer(data, _empty_catalogs())
        self.assertFalse(any(line.startswith("unused configuration") for line in issues))

    def test_unused_task_and_endpoint_groups_are_flagged(self) -> None:
        data = {
            "TransferType": "ConfigTransfer",
            "TaskGroups": [
                {
                    "ID": 1,
                    "Name": "Empty Tasks",
                    "CopyID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                }
            ],
            "EndpointGroups": [
                {
                    "ID": 1,
                    "Name": "Empty Endpoints",
                    "Slug": "empty",
                    "CopyID": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                }
            ],
        }
        issues, _ = check_transfer(data, _empty_catalogs())
        task_unused = [line for line in issues if line.startswith("unused task group")]
        ep_unused = [line for line in issues if line.startswith("unused endpoint group")]
        self.assertEqual(len(task_unused), 1)
        self.assertEqual(len(ep_unused), 1)
        self.assertIn("Empty Tasks", task_unused[0])
        self.assertIn("Empty Endpoints", ep_unused[0])

    def test_groups_with_members_are_ok(self) -> None:
        tg = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        eg = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        data = {
            "TransferType": "ConfigTransfer",
            "TaskGroups": [
                {"ID": 1, "Name": "Used TG", "CopyID": tg},
            ],
            "EndpointGroups": [
                {"ID": 1, "Name": "Used EG", "Slug": "used", "CopyID": eg},
            ],
            "Tasks": [
                {
                    "ID": 1,
                    "Name": "Task",
                    "CopyID": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                    "TaskGroupCopyID": tg,
                    "Type": 1,
                    "Steps": [],
                }
            ],
            "Endpoints": [
                {
                    "ID": 1,
                    "Name": "Ep",
                    "Slug": "ep",
                    "CopyID": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                    "EndpointGroupCopyID": eg,
                }
            ],
        }
        issues, _ = check_transfer(data, _empty_catalogs())
        self.assertFalse(any("unused task group" in line or "unused endpoint group" in line for line in issues))


if __name__ == "__main__":
    unittest.main()
