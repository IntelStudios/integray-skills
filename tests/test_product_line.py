"""productLine rel-YYYY-MM.patch comparison."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from integray_remote import (  # noqa: E402
    REMOTE_API_PRODUCT_LINE,
    SNAPSHOT_PRODUCT_LINE,
    product_line_at_least,
    product_line_tuple,
)


class ProductLineTests(unittest.TestCase):
    def test_tuple_and_order(self) -> None:
        self.assertEqual(product_line_tuple("rel-2025-03.017"), (2025, 3, 17))
        self.assertEqual(product_line_tuple("rel-2025-03.018"), (2025, 3, 18))
        self.assertIsNone(product_line_tuple("dev-main"))
        self.assertEqual(REMOTE_API_PRODUCT_LINE, "rel-2025-03.017")
        self.assertTrue(
            product_line_at_least("rel-2025-03.017", REMOTE_API_PRODUCT_LINE)
        )
        self.assertFalse(product_line_at_least("rel-2025-03.016", REMOTE_API_PRODUCT_LINE))
        self.assertFalse(product_line_at_least("rel-2025-03.017", SNAPSHOT_PRODUCT_LINE))
        self.assertTrue(product_line_at_least("rel-2025-03.018", SNAPSHOT_PRODUCT_LINE))
        self.assertTrue(product_line_at_least("rel-2025-04.001", SNAPSHOT_PRODUCT_LINE))
        self.assertFalse(product_line_at_least("not-a-line", SNAPSHOT_PRODUCT_LINE))


if __name__ == "__main__":
    unittest.main()
