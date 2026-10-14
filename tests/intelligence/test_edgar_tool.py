"""tools/edgar_fetch.py corrections: table-cell boundaries and the saved-bytes hash (IDEA-013 R5/R6).

The research tool is loaded from its path without running main(); no network request is made.
"""

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOL = Path(__file__).resolve().parents[2] / "tools" / "edgar_fetch.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("edgar_fetch_under_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EdgarToolTests(unittest.TestCase):
    def setUp(self):
        self.tool = load_tool()

    def test_tool_keeps_table_cell_boundaries(self):
        raw = b"<table><tr><td>Revenue</td><td>100</td><td>90</td></tr></table>"
        self.assertEqual(self.tool.html_to_text(raw), "Revenue | 100 | 90")

    def test_import_does_not_load_private_environment(self):
        with patch("dotenv.load_dotenv") as load:
            load_tool()
            load.assert_not_called()

    def test_recorded_hash_equals_hash_of_saved_file_bytes(self):
        raw = "<p>Café ₩1,000\r\n— 실적</p>".encode("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.txt"
            record = self.tool.save_document_text(path, raw, "doc.htm")
            data = path.read_bytes()
        self.assertEqual(record["text_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(record["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(record["text_bytes"], len(data))
        self.assertEqual(record["text_encoding"], "utf-8")
        self.assertEqual(data.decode("utf-8"), "Café ₩1,000 — 실적")

    def test_tool_source_no_longer_uses_locale_dependent_writes_for_documents(self):
        source = TOOL.read_text(encoding="utf-8")
        self.assertNotIn("write_text(text)", source)
        self.assertNotIn("text.encode()", source)


if __name__ == "__main__":
    unittest.main()
