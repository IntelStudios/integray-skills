"""Advisory connector version lines (outdated / mixed Guid)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from connector_versions import advise, newest_in_catalog, parse_version  # noqa: E402

NODE = "5a70dfd2-9803-4bcf-b090-652b156f7236"
PY = "e14ea2c1-42d4-4224-b308-8ed55168e0c8"


def _transfer(*steps: dict) -> dict:
    return {
        "Connectors": [
            {"Guid": NODE, "Version": "3.3.0", "Name": "Node.js processor"},
            {"Guid": PY, "Version": "3.2.0", "Name": "Python processor"},
        ],
        "Tasks": [{"Name": "T", "Steps": list(steps)}],
    }


def _step(guid: str, ver: str) -> dict:
    return {"Connector": {"Guid": guid, "Version": ver}}


class ConnectorVersionTests(unittest.TestCase):
    def test_parse_patch(self) -> None:
        self.assertLess(parse_version("4.0.1"), parse_version("4.0.11"))
        self.assertLess(parse_version("3.3.0"), parse_version("3.4.4"))

    def test_outdated_and_mixed(self) -> None:
        catalog = {
            NODE: ("3.4.4", "Node.js processor"),
            PY: ("3.3.1", "Python processor"),
        }
        data = _transfer(
            _step(NODE, "3.3.0"),
            _step(NODE, "3.4.4"),
            _step(PY, "3.2.0"),
            _step(PY, "3.2.0"),
        )
        lines = advise(data, catalog)
        self.assertEqual(len(lines), 2)
        mixed = next(line for line in lines if line.startswith("connector-mixed:"))
        old = next(line for line in lines if line.startswith("connector-outdated:"))
        self.assertIn("3.3.0 (1 step)", mixed)
        self.assertIn("3.4.4 (1 step)", mixed)
        self.assertIn("unify to 3.4.4", mixed)
        self.assertIn("3.2.0 (2 steps)", old)
        self.assertIn("catalog newest 3.3.1", old)

    def test_current_is_silent(self) -> None:
        catalog = {NODE: ("3.4.4", "Node.js processor")}
        data = _transfer(_step(NODE, "3.4.4"))
        self.assertEqual(advise(data, catalog), [])

    def test_unknown_guid_is_silent(self) -> None:
        data = _transfer(_step("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "1.0.0"))
        self.assertEqual(advise(data, {}), [])

    def test_newest_in_catalog_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "connectors.json"
            path.write_text(
                json.dumps(
                    [
                        {"guid": NODE, "version": "3.3.0", "name": "Node.js processor"},
                        {"guid": NODE, "version": "3.4.4", "name": "Node.js processor"},
                    ]
                ),
                encoding="utf-8",
            )
            best = newest_in_catalog(Path(raw))
            self.assertEqual(best[NODE][0], "3.4.4")


if __name__ == "__main__":
    unittest.main()
