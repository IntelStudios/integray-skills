"""Company conventions.md keys still used after Backup became mandatory."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from transfer_util import parse_conventions  # noqa: E402


class ParseConventionsTests(unittest.TestCase):
    def test_missing_file_is_ask(self) -> None:
        self.assertEqual(
            parse_conventions(Path("/no/such/conventions.md")),
            {"publish": "ask", "download": "ask"},
        )

    def test_reads_publish_and_download(self) -> None:
        path = Path(tempfile.mkdtemp()) / "conventions.md"
        path.write_text(
            "Publish after dry-run: auto\nDownload after publish: ask\n",
            encoding="utf-8",
        )
        self.assertEqual(
            parse_conventions(path),
            {"publish": "auto", "download": "ask"},
        )

    def test_ignores_legacy_backup_line(self) -> None:
        path = Path(tempfile.mkdtemp()) / "conventions.md"
        path.write_text(
            "Backup before process: auto\nPublish after dry-run: ask\n",
            encoding="utf-8",
        )
        parsed = parse_conventions(path)
        self.assertNotIn("backup", parsed)
        self.assertEqual(parsed["publish"], "ask")


if __name__ == "__main__":
    unittest.main()
