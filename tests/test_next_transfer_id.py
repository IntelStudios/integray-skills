"""Allocate new transfer IDs without rewriting existing ones."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from transfer_ids import collect_entity_ids, next_transfer_ids  # noqa: E402

EXAMPLE = ROOT / "examples" / "generic_worked_example.json"


class NextTransferIdTests(unittest.TestCase):
    def test_example_next_is_above_max(self) -> None:
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        used = collect_entity_ids(data)
        self.assertTrue(used)
        nxt = next_transfer_ids(data, count=3)
        self.assertEqual(nxt, [max(used) + 1, max(used) + 2, max(used) + 3])
        self.assertTrue(set(nxt).isdisjoint(used))

    def test_does_not_use_zero(self) -> None:
        data = {"TransferType": "ConfigTransfer", "ID": 0, "Tasks": []}
        self.assertEqual(next_transfer_ids(data), [1])

    def test_ignores_id_inside_configuration_string(self) -> None:
        data = {
            "TransferType": "ConfigTransfer",
            "ID": 2,
            "Configurations": [
                {
                    "ID": 5,
                    "CopyID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "Configuration": '{"ID": 99, "Statement": "x"}',
                }
            ],
        }
        self.assertEqual(collect_entity_ids(data), {2, 5})
        self.assertEqual(next_transfer_ids(data), [6])


class NextTransferIdCliTests(unittest.TestCase):
    def test_copy_id_prints_uuid_after_numeric(self) -> None:
        import subprocess
        import uuid as uuid_mod

        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "next-transfer-id.py"),
                str(EXAMPLE),
                "--copy-id",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        int(lines[0])
        uuid_mod.UUID(lines[1])


if __name__ == "__main__":
    unittest.main()
