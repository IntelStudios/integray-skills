"""Task-run snapshot identity keys vs split working/."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from snapshot_tree import (  # noqa: E402
    collect_identity_keys,
    load_identity_names,
    summarize_snapshot,
    working_beside_connection,
)

SAMPLE = {
    "Schema": {
        "Name": "",
        "Columns": [
            {
                "Name": "{ts:6ce65480-6e47-43bd-a788-aaf6e0bc5e53}",
                "AllowNull": True,
                "DataType": 7,
                "Schema": {
                    "Name": "Text",
                    "Guid": "b76c3662-4903-4512-97a9-72f32eaecd01",
                    "Version": "1.0.0",
                    "Columns": [
                        {"Name": "Text", "AllowNull": False, "DataType": 2}
                    ],
                },
            },
            {
                "Name": "{ts:5214ad46-bc75-4369-aa30-c4731e561851}",
                "AllowNull": True,
                "DataType": 7,
                "Schema": {
                    "Name": "User",
                    "Columns": [
                        {
                            "Name": "{dsc:fc302299-f3fc-41c1-aaa5-b583cf99dd55}",
                            "AllowNull": True,
                            "DataType": 1,
                        },
                        {
                            "Name": "{dsc:58af2346-c9da-4044-b4ca-033de61cd1dc}",
                            "AllowNull": True,
                            "DataType": 2,
                        },
                        {
                            "Name": "{ts:7bb2ea54-be03-47f5-a563-3cf63205b43f}",
                            "AllowNull": True,
                            "DataType": 7,
                            "Schema": {
                                "Name": "User",
                                "Columns": [
                                    {
                                        "Name": "{dsc:fc302299-f3fc-41c1-aaa5-b583cf99dd55}",
                                        "AllowNull": True,
                                        "DataType": 1,
                                    },
                                    {
                                        "Name": "{dsc:58af2346-c9da-4044-b4ca-033de61cd1dc}",
                                        "AllowNull": True,
                                        "DataType": 2,
                                    },
                                ]
                            },
                        },
                    ],
                },
            },
        ],
    },
    "Rows": [
        {
            "{ts:6ce65480-6e47-43bd-a788-aaf6e0bc5e53}": [
                {"Text": "Text 1"},
                {
                    "Text": "Text 2 - this text should be a data ref in stored in a shared location"
                },
            ],
            "{ts:5214ad46-bc75-4369-aa30-c4731e561851}": [
                {
                    "{dsc:fc302299-f3fc-41c1-aaa5-b583cf99dd55}": 1,
                    "{dsc:58af2346-c9da-4044-b4ca-033de61cd1dc}": "Sed ut perspiciatis",
                    "{ts:7bb2ea54-be03-47f5-a563-3cf63205b43f}": [
                        {
                            "{dsc:fc302299-f3fc-41c1-aaa5-b583cf99dd55}": 1,
                            "{dsc:58af2346-c9da-4044-b4ca-033de61cd1dc}": "Sed ut perspiciatis",
                        }
                    ],
                }
            ],
        }
    ],
    "HasDefinedRows": True,
}


class SnapshotTreeTests(unittest.TestCase):
    def test_collect_identity_keys(self) -> None:
        keys = collect_identity_keys(SAMPLE)
        self.assertIn("{ts:6ce65480-6e47-43bd-a788-aaf6e0bc5e53}", keys)
        self.assertIn("{ts:5214ad46-bc75-4369-aa30-c4731e561851}", keys)
        self.assertIn("{ts:7bb2ea54-be03-47f5-a563-3cf63205b43f}", keys)
        self.assertIn("{dsc:fc302299-f3fc-41c1-aaa5-b583cf99dd55}", keys)
        self.assertIn("{dsc:58af2346-c9da-4044-b4ca-033de61cd1dc}", keys)

    def test_summarize_without_working(self) -> None:
        text = summarize_snapshot(SAMPLE, {})
        self.assertIn("root rows=1 HasDefinedRows=True", text)
        self.assertIn("{ts:6ce65480-6e47-43bd-a788-aaf6e0bc5e53}", text)
        self.assertIn("schema='Text'", text)
        self.assertIn("schema='User'", text)
        self.assertIn("Text=\"Text 1\"", text)
        self.assertIn("# unresolved", text)

    def test_load_working_and_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            working = Path(raw)
            (working / "tasks").mkdir()
            (working / "data-schemas").mkdir()
            (working / "endpoints").mkdir()
            (working / "tasks" / "t.json").write_text(
                json.dumps(
                    {
                        "CopyID": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        "Name": "Demo",
                        "Steps": [
                            {
                                "CopyID": "6ce65480-6e47-43bd-a788-aaf6e0bc5e53",
                                "Name": "Make Text",
                            },
                            {
                                "CopyID": "5214ad46-bc75-4369-aa30-c4731e561851",
                                "Name": "Users",
                            },
                            {
                                "CopyID": "7bb2ea54-be03-47f5-a563-3cf63205b43f",
                                "Name": "Nested User",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (working / "data-schemas" / "s.json").write_text(
                json.dumps(
                    {
                        "CopyID": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                        "Name": "User",
                        "Columns": [
                            {
                                "CopyID": "fc302299-f3fc-41c1-aaa5-b583cf99dd55",
                                "Name": "Id",
                            },
                            {
                                "CopyID": "58af2346-c9da-4044-b4ca-033de61cd1dc",
                                "Name": "Bio",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            names = load_identity_names(working)
            text = summarize_snapshot(SAMPLE, names)
            self.assertIn("Step  Make Text", text)
            self.assertIn("Step  Users", text)
            self.assertIn("column  Id", text)
            self.assertNotIn("# unresolved", text)
            self.assertIn("Make Text rows=2 schema='Text'", text)
            self.assertIn("Id=1 Bio=\"Sed ut perspiciatis\"", text)
            self.assertIn("Nested User rows=1 schema='User'", text)

    def test_working_beside_connection(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            conn = root / ".integray-connection.json"
            conn.write_text("{}", encoding="utf-8")
            self.assertIsNone(working_beside_connection(conn))
            (root / "working" / "tasks").mkdir(parents=True)
            self.assertEqual(
                working_beside_connection(conn),
                (root / "working").resolve(),
            )


if __name__ == "__main__":
    unittest.main()
