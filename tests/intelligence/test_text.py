"""HTML tables, encodings and portable UTF-8 hashes (IDEA-013 R5/R6). Synthetic inputs only."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from larp.intelligence.text import decode_bytes, document_text, html_to_text, text_from_saved


class TableBoundaryTests(unittest.TestCase):
    def test_compact_cells_are_not_concatenated(self):
        text = html_to_text("<table><tr><td>Revenue</td><td>100</td><td>90</td></tr></table>")
        self.assertEqual(text, "Revenue | 100 | 90")
        self.assertNotIn("10090", text)

    def test_spacer_and_symbol_cells_merge_into_numbers(self):
        html = ("<table><tr><td></td><td>Q3 FY27</td><td></td><td>Q2 FY27</td></tr>"
                "<tr><td>Revenue</td><td>$</td><td>35,082</td><td>$</td><td>30,040</td></tr>"
                "<tr><td>Net loss</td><td>(</td><td>1,234</td><td>)</td><td>(5)</td></tr>"
                "<tr><td>Gross margin</td><td>74.6</td><td>%</td><td>75.1</td><td>%</td></tr></table>")
        self.assertEqual(html_to_text(html).split("\n"), [
            "Q3 FY27 | Q2 FY27", "Revenue | $35,082 | $30,040", "Net loss | (1,234) | (5)",
            "Gross margin | 74.6% | 75.1%"])

    def test_source_newlines_inside_cells_are_whitespace(self):
        self.assertEqual(html_to_text("<tr><td>Total\nnet\r\nrevenue</td><td>\n12\n</td></tr>"), "Total net revenue | 12")

    def test_scripts_styles_and_inline_xbrl_header_are_dropped(self):
        html = ("<html><head><style>p{}</style><script>var x=1</script></head><body>"
                "<ix:header><ix:hidden>dei:Hidden 999</ix:hidden></ix:header><p>Visible 1</p>"
                "<div style='display:none'>Hidden but kept as untrusted data</div></body></html>")
        text = html_to_text(html)
        self.assertNotIn("999", text)
        self.assertNotIn("var x", text)
        self.assertIn("Visible 1", text)
        self.assertIn("Hidden but kept as untrusted data", text)

    def test_nested_tables_keep_their_own_row_counts(self):
        html = "<table><tr><td>A</td><td><table><tr><td>B</td><td>C</td></tr></table></td><td>D</td></tr></table>"
        self.assertEqual(html_to_text(html), "A\n\nB | C\nD")  # never "ABCD"


class PortableHashTests(unittest.TestCase):
    def test_hash_is_of_the_exact_saved_utf8_bytes(self):
        raw = ("<html><head><meta charset='utf-8'></head><body><p>Café ₩1,000 — "
               "실적</p>\r\n<p>Line two</p></body></html>").encode("utf-8")
        saved = document_text(raw, "x.htm", None)
        self.assertEqual(saved.text_sha256, hashlib.sha256(saved.saved_bytes).hexdigest())
        self.assertEqual(saved.raw_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(text_from_saved(saved.saved_bytes), saved.text)
        self.assertNotIn(b"\r", saved.saved_bytes)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "saved.txt"
            path.write_bytes(saved.saved_bytes)  # what the EDGAR path writes, on any platform
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), saved.text_sha256)

    def test_unicode_normalization_makes_equivalent_text_hash_equal(self):
        composed = document_text("<p>Résumé</p>".encode("utf-8"), "a.htm")
        decomposed = document_text("<p>Résumé</p>".encode("utf-8"), "a.htm")
        self.assertEqual(composed.text_sha256, decomposed.text_sha256)
        self.assertNotEqual(composed.raw_sha256, decomposed.raw_sha256)

    def test_plain_text_documents_are_normalized_not_parsed(self):
        saved = document_text(b"Revenue <b>not a tag</b>\r\nNext", "doc.txt", "text/plain")
        self.assertEqual(saved.text, "Revenue <b>not a tag</b>\nNext")


class DecodingTests(unittest.TestCase):
    def test_latin1_label_decodes_as_windows_1252(self):
        raw = "<meta charset='iso-8859-1'><p>The board’s “dividend”</p>".encode("cp1252")
        text, encoding, lossy = decode_bytes(raw)
        self.assertEqual((encoding, lossy), ("cp1252", False))
        self.assertIn("’s “dividend”", text)

    def test_header_charset_wins_and_bom_is_removed(self):
        self.assertEqual(decode_bytes("é".encode("utf-8"), "text/html; charset=UTF-8")[:2], ("é", "utf-8"))
        self.assertEqual(decode_bytes(b"\xef\xbb\xbfabc")[0], "abc")

    def test_undeclared_invalid_utf8_falls_back_and_flags_loss(self):
        text, encoding, lossy = decode_bytes(b"caf\xe9")
        self.assertEqual((text, encoding, lossy), ("café", "cp1252", False))
        _, encoding, lossy = decode_bytes(b"bad \x81 byte \xff\xfe\xfa")
        self.assertEqual(encoding, "cp1252")
        self.assertTrue(lossy)


if __name__ == "__main__":
    unittest.main()
