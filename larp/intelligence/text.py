"""Filing bytes -> portable text whose exact saved UTF-8 bytes are what gets hashed.

Fixes IDEA-013 R5 (adjacent table cells were concatenated) and R6 (saved text was
written in the locale encoding while its hash used UTF-8). Rules:

- Table cells are separated by " | " and rows by newlines. Spacer cells are dropped and
  a lone currency symbol, closing parenthesis or percent sign is merged into its number.
- Script/style and the hidden inline-XBRL header are dropped. Everything else, hidden or
  not, is kept as untrusted data; nothing here interprets instructions in the text.
- The saved form is NFC-normalized, uses "\n" newlines only and is encoded as UTF-8.
  `text_sha256` is the SHA-256 of exactly those bytes; character offsets used by spans
  refer to the decoded saved text.
"""

from dataclasses import dataclass
from html.parser import HTMLParser
import codecs
import re
import unicodedata

from larp.intelligence.common import sha256_hex

BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "table",
         "section", "article", "header", "footer", "blockquote", "pre", "hr", "caption",
         "thead", "tbody", "tfoot", "dl", "dt", "dd"}
CELL = {"td", "th"}
SKIP = {"script", "style", "head", "noscript", "ix:header", "template"}
CELL_SEP = " | "
_LATIN1_LABELS = {"iso-8859-1", "iso8859-1", "latin-1", "latin1", "us-ascii", "ascii", "l1"}
_META_CHARSET = re.compile(rb"<meta[^>]+charset\s*=\s*[\"']?([A-Za-z0-9_\-]+)", re.I)
_HEADER_CHARSET = re.compile(r"charset\s*=\s*[\"']?([A-Za-z0-9_\-]+)", re.I)
_MERGE_LEFT = {"$", "US$", "USD", "KRW", "\u20a9", "("}
_MERGE_RIGHT = {")", "%", ")%", "%)"}


class _Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip, self.rows, self.pre = [], 0, [], 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag == "tr":
            self.parts.append("\n")
            self.rows.append(0)
        elif tag in CELL:
            if self.rows and self.rows[-1]:
                self.parts.append(CELL_SEP)
            if self.rows:
                self.rows[-1] += 1
        elif tag in BLOCK:
            self.parts.append("\n")
            if tag == "pre":
                self.pre += 1

    def handle_startendtag(self, tag, attrs):
        if tag == "br" and not self.skip:
            self.parts.append("\n")
        elif tag in CELL and not self.skip:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "tr":  # rows start on a new line (handle_starttag); no blank line between rows
            if self.rows:
                self.rows.pop()
        elif tag in BLOCK:
            self.parts.append("\n")
            if tag == "pre" and self.pre:
                self.pre -= 1

    def handle_data(self, data):
        if self.skip:
            return
        # Source newlines are whitespace in HTML, never row or block breaks (except <pre>).
        self.parts.append(data if self.pre else re.sub(r"[\r\n]+", " ", data))


def _is_row(line: str) -> bool:
    return CELL_SEP in line or line.startswith("| ") or line.endswith(" |") or line == "|"


def _clean_row(line: str) -> str:
    cells = [c for c in (c.strip() for c in re.split(r"\s*\|\s*", line)) if c]
    merged = []
    for cell in cells:
        if merged and cell in _MERGE_RIGHT:
            merged[-1] += cell
        elif merged and merged[-1] in _MERGE_LEFT:
            merged[-1] = (merged[-1] + cell) if merged[-1] in {"$", "\u20a9", "("} else f"{merged[-1]} {cell}"
        else:
            merged.append(cell)
    return CELL_SEP.join(merged)


def normalize_text(text: str) -> str:
    """Canonical saved form: NFC, "\n" newlines, collapsed spaces, at most one blank line."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t\f\v]+", " ", line).strip()
        if _is_row(line):
            line = _clean_row(line)
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def html_to_text(html: str) -> str:
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    return normalize_text("".join(parser.parts))


def _declared_charset(raw: bytes, content_type: str | None) -> str | None:
    if content_type:
        match = _HEADER_CHARSET.search(content_type)
        if match:
            return match.group(1).lower()
    match = _META_CHARSET.search(raw[:4096])
    return match.group(1).decode("ascii").lower() if match else None


def decode_bytes(raw: bytes, content_type: str | None = None) -> tuple:
    """Return (text, encoding, lossy). Latin-1/ASCII labels decode as windows-1252 (WHATWG)."""
    declared = _declared_charset(raw, content_type)
    candidates = []
    if declared:
        candidates.append("cp1252" if declared in _LATIN1_LABELS else declared)
    candidates += ["utf-8-sig" if raw.startswith(codecs.BOM_UTF8) else "utf-8", "cp1252"]
    for encoding in candidates:
        try:
            codecs.lookup(encoding)
            return raw.decode(encoding), encoding, False
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("cp1252", errors="replace"), "cp1252", True


def is_html(name: str, content_type: str | None) -> bool:
    lowered = name.lower()
    return lowered.endswith((".htm", ".html", ".xhtml")) or "html" in (content_type or "").lower()


@dataclass(frozen=True, slots=True)
class SavedText:
    text: str
    saved_bytes: bytes
    text_sha256: str
    raw_sha256: str
    encoding: str
    lossy: bool


def document_text(raw: bytes, name: str, content_type: str | None = None) -> SavedText:
    decoded, encoding, lossy = decode_bytes(raw, content_type)
    text = html_to_text(decoded) if is_html(name, content_type) else normalize_text(decoded)
    saved = text.encode("utf-8")
    return SavedText(text, saved, sha256_hex(saved), sha256_hex(raw), encoding, lossy)


def text_from_saved(saved: bytes) -> str:
    """Inverse of the saved form; strict, so corrupted artifacts fail loudly."""
    return saved.decode("utf-8")
