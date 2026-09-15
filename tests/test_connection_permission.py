"""Permission gate on .integray-connection.json."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from integray_remote import (  # noqa: E402
    PERMISSION_FULL,
    PERMISSION_READ_ONLY,
    PERMISSION_READ_WRITE,
    ConnectionConfig,
    ConnectionPermissionError,
    process_config_transfer,
    upload_config_transfer,
)


class ConnectionPermissionTests(unittest.TestCase):
    def _write(self, payload: dict) -> Path:
        tmp = Path(tempfile.mkdtemp()) / ".integray-connection.json"
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        return tmp

    def _base(self, **extra: object) -> dict:
        data: dict = {
            "baseUrl": "http://localhost:4200",
            "companySlug": "self-test",
            "token": "secret-token",
        }
        data.update(extra)
        return data

    def test_missing_or_empty_defaults_read_only(self) -> None:
        config = ConnectionConfig.load(self._write(self._base()))
        self.assertEqual(config.permission, PERMISSION_READ_ONLY)
        self.assertFalse(config.can_write)
        self.assertFalse(config.can_publish)
        with self.assertRaisesRegex(ConnectionPermissionError, "read-only"):
            config.require_write()
        with self.assertRaisesRegex(ConnectionPermissionError, "needs full"):
            config.require_publish()

        empty = ConnectionConfig.load(self._write(self._base(permission="  ")))
        self.assertEqual(empty.permission, PERMISSION_READ_ONLY)

    def test_read_write_and_full(self) -> None:
        rw = ConnectionConfig.load(
            self._write(self._base(permission=PERMISSION_READ_WRITE))
        )
        self.assertTrue(rw.can_write)
        self.assertFalse(rw.can_publish)
        rw.require_write()
        with self.assertRaisesRegex(ConnectionPermissionError, "needs full"):
            rw.require_publish()

        full = ConnectionConfig.load(self._write(self._base(permission=PERMISSION_FULL)))
        self.assertTrue(full.can_write)
        self.assertTrue(full.can_publish)
        full.require_write()
        full.require_publish()

    def test_invalid_permission_raises(self) -> None:
        path = self._write(self._base(permission="admin"))
        with self.assertRaisesRegex(ValueError, "invalid permission"):
            ConnectionConfig.load(path)

    def test_repr_redacts_token_and_shows_permission(self) -> None:
        config = ConnectionConfig.load(self._write(self._base()))
        text = repr(config)
        self.assertNotIn("secret-token", text)
        self.assertIn("permission='read-only'", text)

    def test_upload_and_only_test_need_write(self) -> None:
        config = ConnectionConfig.load(self._write(self._base()))
        dummy = Path(tempfile.mkdtemp()) / "transfer.json"
        dummy.write_text('{"TransferType": "ConfigTransfer"}', encoding="utf-8")
        with self.assertRaisesRegex(ConnectionPermissionError, "needs read-write or full"):
            upload_config_transfer(config, dummy)
        with self.assertRaisesRegex(ConnectionPermissionError, "needs read-write or full"):
            process_config_transfer(config, 1, only_test=True)

    def test_publish_and_apply_need_full(self) -> None:
        config = ConnectionConfig.load(
            self._write(self._base(permission=PERMISSION_READ_WRITE))
        )
        with self.assertRaisesRegex(ConnectionPermissionError, "needs full"):
            process_config_transfer(config, 1, publish=True)
        with self.assertRaisesRegex(ConnectionPermissionError, "needs full"):
            process_config_transfer(config, 1, only_test=False, publish=False)


if __name__ == "__main__":
    unittest.main()
