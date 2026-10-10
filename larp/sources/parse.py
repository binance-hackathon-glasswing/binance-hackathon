"""Listing parsers for the free sources. Input bytes are untrusted; output is a list of plain item dicts.

Every item: item_id (source-native, stable), url, title, body_html (permitted original text, may be None),
published_raw, published_ms, published_precision (SECOND | DAY | NONE), event_times (named source dates such as
effective_on, comments_close_on, filed_at, each with its precision), changed_raw, withdrawn, doc_type.
A scheduled or publication date is a claim by the source; it never proves when the fetched text first existed.
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import json
import re
import xml.etree.ElementTree as ET

from larp.sources.transport import SourceError

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_TAG = re.compile(r"<time[^>]*\bdatetime=[\"']([^\"']+)[\"']", re.I)


def _day_ms(value: str) -> int:
    return int(datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def when(value) -> tuple:
    """(ms, precision) from an RFC 822 date, ISO date-time, ISO date or epoch seconds; (None, NONE) if absent."""
    if value is None or value == "":
        return None, "NONE"
    text = str(value).strip()
    tag = _TIME_TAG.search(text)  # DOJ API: '<time datetime="2026-10-09T07:30:28-04:00">1791545428</time>'
    if tag:
        text = tag.group(1)
    if text.isdigit():
        return int(text) * 1000, "SECOND"
    if _DATE.match(text):
        return _day_ms(text), "DAY"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("naive")
        return int(parsed.timestamp() * 1000), "SECOND"
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            if not text.rstrip().endswith("-0000"):
                raise ValueError("naive")
            parsed = parsed.replace(tzinfo=timezone.utc)  # RFC 5322 "-0000": UTC, local zone unknown
        return int(parsed.timestamp() * 1000), "SECOND"
    except (TypeError, ValueError, IndexError):
        raise SourceError("UNPARSEABLE_TIMESTAMP") from None


def safe_when(value) -> tuple:
    """`when`, but an unparseable value is (None, "UNPARSEABLE") so one bad item cannot block a page (S4-B d04)."""
    try:
        return when(value)
    except SourceError:
        return None, "UNPARSEABLE"


def _event_times(record: dict, names: tuple) -> dict:
    out = {}
    for name in names:
        ms, precision = safe_when(record.get(name))
        if precision == "UNPARSEABLE":
            out[name] = {"raw": record.get(name), "ms": None, "precision": "UNPARSEABLE"}
            continue
        if ms is not None:
            out[name] = {"raw": record.get(name), "ms": ms, "precision": precision}
    return out


def _safe_xml(body: bytes):
    head = body[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in body.lower():
        raise SourceError("XML_DTD_REFUSED")  # no entity expansion from untrusted feeds
    try:
        return ET.fromstring(body)
    except ET.ParseError:
        raise SourceError("XML_UNPARSEABLE") from None


def rss(body: bytes, limit: int) -> tuple:
    root = _safe_xml(body)
    items = []
    truncated = False
    for node in root.iter("item"):
        if len(items) >= limit:
            truncated = True
            break
        get = lambda tag: (node.findtext(tag) or "").strip() or None
        link, guid = get("link"), get("guid")
        ms, precision = safe_when(get("pubDate"))
        items.append({"item_id": guid or link, "url": link, "title": get("title"), "body_html": get("description"),
                      "published_raw": get("pubDate"), "published_ms": ms, "published_precision": precision,
                      "event_times": {}, "changed_raw": None, "withdrawn": False, "doc_type": "PRESS_RELEASE"})
    return [i for i in items if i["item_id"]], None, truncated


def _json(body: bytes) -> dict:
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise SourceError("JSON_UNPARSEABLE") from None
    if type(data) is not dict:
        raise SourceError("JSON_SHAPE")
    return data


def fr_documents(body: bytes, limit: int) -> tuple:
    data = _json(body)
    results = data.get("results") or []
    items = []
    for r in results[:limit]:
        ms, precision = safe_when(r.get("publication_date"))
        action = r.get("action") or ""
        items.append({"item_id": r.get("document_number"), "url": r.get("html_url"), "title": r.get("title"),
                      "body_html": "\n".join(x for x in (r.get("action"), r.get("abstract")) if x) or None,
                      "published_raw": r.get("publication_date"), "published_ms": ms, "published_precision": precision,
                      "event_times": _event_times(r, ("effective_on", "comments_close_on", "signing_date")),
                      "changed_raw": None, "announces_withdrawal": "withdraw" in action.lower(), "withdrawn": False,
                      "doc_type": (r.get("type") or "UNKNOWN").upper().replace(" ", "_")})
    return [i for i in items if i["item_id"]], data.get("next_page_url"), len(results) > limit


def fr_public_inspection(body: bytes, limit: int) -> tuple:
    data = _json(body)
    results = data.get("results") or []
    items = []
    for r in results[:limit]:
        filed_ms, filed_precision = safe_when(r.get("filed_at"))
        items.append({"item_id": r.get("document_number"), "url": r.get("html_url") or r.get("pdf_url"),
                      "title": r.get("title"), "body_html": None,
                      "published_raw": r.get("filed_at"), "published_ms": filed_ms,
                      "published_precision": filed_precision,
                      "event_times": _event_times(r, ("publication_date", "pdf_updated_at")),
                      "changed_raw": r.get("pdf_updated_at"), "withdrawn": bool(r.get("withdrawn")),
                      "doc_type": "PUBLIC_INSPECTION:" + (r.get("type") or "UNKNOWN").upper().replace(" ", "_")})
    return [i for i in items if i["item_id"]], None, len(results) > limit


def doj_press(body: bytes, limit: int, page_url: str) -> tuple:
    data = _json(body)
    results = data.get("results") or []
    items = []
    for r in results[:limit]:
        text = r.get("body")
        if type(text) is dict:
            text = text.get("value")
        ms, unparsed = safe_when(r.get("date"))
        # DOJ `date` is the release's listed date, delivered as epoch seconds at a fixed hour (observed 12:00 UTC on
        # 2026-10-10), so it is kept at DAY precision; `created`/`changed` carry second-precision times.
        items.append({"item_id": r.get("uuid"), "url": r.get("url"), "title": r.get("title"), "body_html": text,
                      "published_raw": r.get("date"), "published_ms": None if ms is None else ms - ms % 86_400_000,
                      "published_precision": "DAY" if ms is not None else unparsed,
                      "event_times": _event_times(r, ("created", "changed")), "changed_raw": r.get("changed"),
                      "withdrawn": False, "doc_type": "PRESS_RELEASE",
                      "excluded_fields": sorted(k for k in ("attachment", "image") if r.get(k))})
    page_size = int((dict(parse_qsl(urlsplit(page_url).query)).get("pagesize") or 20))
    next_url = None
    if len(results) >= page_size:
        parts = urlsplit(page_url)
        query = dict(parse_qsl(parts.query))
        query["page"] = str(int(query.get("page", "0")) + 1)
        next_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    return [i for i in items if i["item_id"]], next_url, len(results) > limit


def parse(source, body: bytes, page_url: str) -> tuple:
    """Return (items, next_url, item_truncated); pagination alone cannot recover discarded page items."""
    limit = source.limits.get("max_items_per_page", 50)
    if source.format == "RSS":
        return rss(body, limit)
    if source.format == "FR_DOCUMENTS_JSON":
        return fr_documents(body, limit)
    if source.format == "FR_PUBLIC_INSPECTION_JSON":
        return fr_public_inspection(body, limit)
    if source.format == "DOJ_PRESS_JSON":
        return doj_press(body, limit, page_url)
    raise SourceError("FORMAT_NOT_IMPLEMENTED")
