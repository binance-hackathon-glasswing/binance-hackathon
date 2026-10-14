"""SEC EDGAR parsing and an opt-in read-only HTTP source.

Parsing functions are pure. `EdgarHttpSource` is the only network path in this package
besides the hosted model adapter: it refuses to exist without a real declared User-Agent,
reaches only data.sec.gov and www.sec.gov, and spaces requests to <= 5 per second (SEC
fair-access limit is 10 per second). It is not exercised against the live service by the
offline tests; IDEA-001 §15 records the separate research runs of tools/edgar_fetch.py.

`acceptanceDateTime` carries an explicit offset in the submissions JSON and is parsed as
stated. One 6-K was checked to be true UTC (IDEA-001 §15, IDEA-009 C.2); IDEA-004 T1's
EDT/EST comparison against the index page is still open, so the raw string is retained.
"""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit
import json
import re
import time
import urllib.error
import urllib.request

from larp.intelligence.common import IntelligenceError, sha256_hex
from larp.intelligence.sources import FetchedDocument, FetchedFiling, Listing
from larp.intelligence.text import decode_bytes

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_FILE = "https://data.sec.gov/submissions/{name}"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/"
ALLOWED_HOSTS = frozenset({"data.sec.gov", "www.sec.gov"})
MAX_RESPONSE_BYTES = 8_000_000
READABLE = (".htm", ".html", ".txt", ".xhtml")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_MS = timedelta(milliseconds=1)
_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_HISTORY_FILE = re.compile(r"^CIK\d{10}-submissions-\d{3}\.json$")
_DAY_MS = 86_400_000


def parse_acceptance_ms(raw: object) -> int:
    if type(raw) is not str or not raw:
        raise IntelligenceError("Missing acceptanceDateTime")
    stamp = datetime.fromisoformat(raw)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise IntelligenceError("acceptanceDateTime has no explicit offset")
    return (stamp - _EPOCH) // _MS


def check_identity(submissions: dict, cik: int, entity_name: str) -> None:
    if type(submissions) is not dict:
        raise IntelligenceError("SUBMISSIONS_NOT_OBJECT")
    try:
        reported = int(str(submissions.get("cik", "")).lstrip("0") or "0")
    except ValueError:
        reported = -1
    if reported != cik or entity_name.lower() not in str(submissions.get("name", "")).lower():
        raise IntelligenceError("ISSUER_IDENTITY_MISMATCH: submissions response is not the registered issuer")


def listing_rows(submissions: dict, history: tuple = ()) -> tuple:
    """Rows of filings.recent and of any fetched history blocks, each with a parsed original
    timestamp; malformed rows are flagged; an accession listed twice is kept once."""
    rows, seen = [], set()
    filings = submissions.get("filings")
    if type(filings) is not dict or type(filings.get("recent")) is not dict:
        raise IntelligenceError("SUBMISSIONS_FILINGS_MALFORMED")
    for block in (filings["recent"], *history):
        if type(block) is not dict:
            raise IntelligenceError("SUBMISSIONS_COLUMNS_MALFORMED")
        for row in _block_rows(block):
            if row["malformed"] is None:
                if row["accession"] in seen:
                    continue
                seen.add(row["accession"])
            rows.append(row)
    return tuple(rows)


def _block_rows(block: dict) -> list:
    keys = ("accessionNumber", "form", "items", "acceptanceDateTime", "filingDate", "reportDate",
            "primaryDocument")
    if type(block.get("accessionNumber")) is not list or \
            any(block.get(k) is not None and type(block[k]) is not list for k in keys):
        raise IntelligenceError("SUBMISSIONS_COLUMNS_MALFORMED")
    n = len(block.get("accessionNumber") or [])
    if any(block.get(k) and len(block[k]) != n for k in keys):
        raise IntelligenceError("SUBMISSIONS_COLUMN_LENGTH_MISMATCH")
    columns = {k: (block.get(k) or [None] * n) for k in keys}
    rows = []
    for i in range(n):
        raw = {k: columns[k][i] if i < len(columns[k]) else None for k in keys}
        malformed = any(v is not None and type(v) is not str for v in raw.values())
        row = {"accession": raw["accessionNumber"],
               "form": raw["form"].strip().upper() if type(raw["form"]) is str else "",
               "items": [x.strip() for x in (raw["items"] if type(raw["items"]) is str else "").split(",")
                         if x.strip()],
               "acceptance_raw": raw["acceptanceDateTime"], "filing_date": raw["filingDate"],
               "report_date": raw["reportDate"] or None, "primary_document": raw["primaryDocument"],
               "original_ms": None, "malformed": None}
        if type(row["accession"]) is not str or not _ACCESSION.match(row["accession"]):
            row["malformed"] = "ACCESSION"
        elif type(row["primary_document"]) is not str or not row["primary_document"]:
            row["malformed"] = "PRIMARY_DOCUMENT"
        elif malformed:
            row["malformed"] = "COLUMN_VALUE"
        elif not row["form"]:
            row["malformed"] = "FORM"
        else:
            try:
                row["original_ms"] = parse_acceptance_ms(row["acceptance_raw"])
            except (IntelligenceError, ValueError):
                row["malformed"] = "ACCEPTANCE_TIME"
        rows.append(row)
    return rows


def _date_ms(raw: object) -> int | None:
    try:
        return (datetime.combine(date.fromisoformat(raw), datetime.min.time(), timezone.utc) - _EPOCH) // _MS
    except (TypeError, ValueError):
        return None


def history_files(submissions: dict, window: tuple) -> tuple:
    """(names to fetch, malformed entries) of `filings.files` that may hold filings in `window`.

    Each entry covers filing dates filingFrom..filingTo. Filing dates are US Eastern calendar
    dates while the window is acceptance time in UTC, so each range is widened by a day on both
    sides. An entry without readable dates is fetched (it cannot be excluded); one whose name is
    not an EDGAR submissions file name is never turned into a URL.
    """
    names, malformed = [], []
    filings = submissions.get("filings")
    if type(filings) is not dict:
        return (), ("filings",)
    files = filings.get("files")
    if files is not None and type(files) is not list:
        return (), ("filings.files",)
    for entry in files or []:
        name = entry.get("name") if type(entry) is dict else None
        if type(name) is not str or not _HISTORY_FILE.match(name):
            malformed.append(str(name)[:80])
            continue
        low, high = _date_ms(entry.get("filingFrom")), _date_ms(entry.get("filingTo"))
        if (low is not None and low - _DAY_MS > window[1]) or (high is not None and high + 2 * _DAY_MS < window[0]):
            continue
        names.append(name)
    return tuple(names), tuple(malformed)


def parse_filing_index(index_html: bytes) -> tuple:
    """(type, file name, description) rows of <accession>-index.htm (Seq|Description|Document|Type|Size)."""
    html, _, _ = decode_bytes(index_html, None)
    out = []
    strip = lambda x: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x)).strip()
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
        if len(cells) < 4:
            continue
        href = re.search(r'href="([^"]+)"', cells[2], re.I)
        if not href:
            continue
        name = href.group(1).split("/")[-1].split("?")[0]
        out.append((strip(cells[3]).upper(), name, strip(cells[1])))
    return tuple(out)


def select_documents(index_rows: tuple, primary: str, form: str, max_documents: int) -> tuple:
    """Primary document first, then readable EX-99.x exhibits (press releases/announcements).

    Unlike the research tool's first-EX-99-only choice, the primary document is always kept:
    its sections (e.g. 8-K item text) can carry evidence the exhibit omits (IDEA-021 §5).
    """
    by_name = {name: (doc_type, description) for doc_type, name, description in index_rows}
    chosen = [{"name": primary, "doc_type": by_name.get(primary, (form, ""))[0] or form, "role": "PRIMARY"}]
    exhibits = sorted((r for r in index_rows if r[0].startswith("EX-99") and r[1] != primary
                       and r[1].lower().endswith(READABLE)), key=lambda r: (r[0], r[1]))
    for doc_type, name, _ in exhibits:
        if len(chosen) >= max_documents:
            break
        chosen.append({"name": name, "doc_type": doc_type, "role": "EXHIBIT"})
    return tuple(chosen)


def _urllib_get(url: str, headers: dict, timeout_s: float) -> tuple:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    request = urllib.request.Request(url, headers=headers, method="GET")
    # A validated initial URL does not validate a Location header. Treat redirects as
    # unavailable; never allow urllib to escape the allowlist or use an ambient proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=timeout_s) as response:  # noqa: S310 - host allowlisted
            return response.status, response.headers.get("Content-Type"), response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type") if exc.headers else None, b""


class EdgarHttpSource:
    """Read-only EDGAR adapter. `http_get(url, headers, timeout_s) -> (status, content_type, body)`."""

    source_id = "sec-edgar"

    def __init__(self, user_agent: str, *, http_get=None, clock_ms=None, sleep=time.sleep,
                 spacing_s: float = 0.2, timeout_s: float = 30.0, max_history_files: int = 20):
        if not user_agent or "@" not in user_agent:
            raise IntelligenceError("EDGAR access requires a declared User-Agent with contact details")
        if spacing_s < 0.1:
            raise IntelligenceError("Request spacing below the SEC fair-access limit")
        self._headers = {"User-Agent": user_agent, "Accept-Encoding": "identity"}
        self._get = http_get or _urllib_get
        self._clock = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._sleep, self._spacing, self._timeout = sleep, spacing_s, timeout_s
        self._max_history, self._last = max_history_files, None

    def _fetch(self, url: str) -> tuple:
        try:
            parts = urlsplit(url)
            permitted = (parts.scheme == "https" and parts.hostname in ALLOWED_HOSTS
                         and parts.port in (None, 443) and not parts.username and not parts.password)
        except ValueError:
            permitted = False
        if not permitted:
            raise IntelligenceError("EDGAR adapter refuses a destination outside the SEC allowlist")
        now = time.monotonic()
        if self._last is not None and now - self._last < self._spacing:
            self._sleep(self._spacing - (now - self._last))
        try:
            status, content_type, body = self._get(url, dict(self._headers), self._timeout)
            error = None if status == 200 else f"HTTP {status}"
            if status == 200 and (type(body) is not bytes or len(body) > MAX_RESPONSE_BYTES):
                status, body, error = None, b"", "RESPONSE_TOO_LARGE_OR_INVALID"
        except OSError as exc:  # URLError, timeouts and connection errors
            status, content_type, body, error = None, None, b"", f"{type(exc).__name__}"
        self._last = time.monotonic()
        return status, content_type, body, error, self._clock()

    def list_filings(self, cik: int, window: tuple | None = None) -> Listing:
        """The submissions listing; with a (from_ms, to_ms) window, also every historical file
        (`filings.files`) that may hold filings in it, at most `max_history_files` requests.
        Anything not fetched or unreadable makes `history_status` PARTIAL, never a silent gap."""
        status, _, body, error, at = self._fetch(SUBMISSIONS.format(cik=cik))
        if error:
            return Listing("UNAVAILABLE", at, None, None, error)
        try:
            listing = Listing("OK", at, json.loads(body.decode("utf-8")), sha256_hex(body))
        except (UnicodeDecodeError, ValueError):
            return Listing("INVALID", at, None, sha256_hex(body), "Submissions response is not JSON")
        if window is None or type(listing.submissions) is not dict:
            return listing
        if type(listing.submissions.get("filings")) is not dict:
            return replace(listing, status="INVALID", error="SUBMISSIONS_FILINGS_MALFORMED")
        names, malformed = history_files(listing.submissions, window)
        blocks, files = [], [{"name": m, "status": "MALFORMED_ENTRY", "response_sha256": None, "error": None}
                             for m in malformed]
        for index, name in enumerate(names):
            if index >= self._max_history:
                files.append({"name": name, "status": "NOT_FETCHED", "response_sha256": None,
                              "error": "HISTORY_FILE_LIMIT"})
                continue
            _, _, data, err, _ = self._fetch(SUBMISSIONS_FILE.format(name=name))
            digest = None if err else sha256_hex(data)
            try:
                block = None if err else json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                block, err = None, "Historical submissions file is not JSON"
            if err is None and type(block) is not dict:
                err = "Historical submissions file is not an object"
            if err:
                files.append({"name": name, "status": "FAILED", "response_sha256": digest, "error": err})
                continue
            blocks.append(block)
            files.append({"name": name, "status": "OK", "response_sha256": digest, "error": None})
        complete = all(f["status"] == "OK" for f in files)
        return replace(listing, history=tuple(blocks), history_status="OK" if complete else "PARTIAL",
                       history_files=tuple(files))

    def fetch_filing(self, cik: int, row: dict, max_documents: int) -> FetchedFiling:
        base = ARCHIVES.format(cik=cik, acc=row["accession"].replace("-", ""))
        _, _, index, error, _ = self._fetch(f"{base}{row['accession']}-index.htm")
        index_rows = () if error else parse_filing_index(index)
        all_documents = select_documents(index_rows, row["primary_document"], row["form"], len(index_rows) + 1)
        chosen = all_documents[:max_documents]
        documents = []
        for doc in chosen:
            status, content_type, body, err, at = self._fetch(base + doc["name"])
            documents.append(FetchedDocument(doc["name"], doc["doc_type"], doc["role"], base + doc["name"],
                                             "FAILED" if err else "OK", at, None if err else body,
                                             content_type, err))
        return FetchedFiling(row["accession"], "FAILED" if error else "OK", tuple(documents),
                             truncated=len(all_documents) > len(chosen))
