"""Red-flag predicate records (RedFlagPredicateSet.v1) and their verification (B1, IDEA-041, interface I8).

The team adopted three severity classes (IDEA-035 §6, §10.1): Class 1 Item 4.02 exits, Class 2 Items 1.05 and
2.06 block new buys for 5 sessions, Class 3 statements stay SHADOW. Each enabled class has a versioned record in
`config/intelligence/red_flags.v1.json`; the set is identified by the SHA-256 of that file.

`verify_item(...)` decides whether one filer-assigned 8-K item code of an assessed filing is a verified red
flag. An accession plus an item code is not enough (IDEA-032 S1). All of these must hold:

1. the record's form and filer class are in the predicate's scope, and the item code is in the filing's
   submissions metadata (`record["items"]`);
2. the filing was ingested live (not BACKFILL) and its acceptance time is no older than `max_event_age_ms` at
   the assessment cutoff (an old event first seen late is history, not a new red flag);
3. a loaded document of the filing has the item's own section, and inside it, outside the heading itself, a
   condition clause that `semantics.classify_event` reads as the issuer's current, occurred, source-asserted
   event (not negated, conditional, attributed or a third party's).

Headings are block headings, not mentions (PR #15 review R03): an `Item x.xx` heading starts a line (or a table
row) and is not followed by a word that makes it a sentence ("Item 2.06 of Form 8-K requires ..."). A mention
inside a sentence neither starts nor ends a section. The item's heading, with its title (`trigger.title_pattern`),
is blanked before the section is read, so the title ("Material Cybersecurity Incidents") is never the occurrence
while a body sentence on the same line still is.

An amendment's event is as old as the filing it amends (R05): its event time is the earlier of the original filing
date the amendment states and the acceptance of the one original 8-K of the issuer listing the same item, at or
before the amendment, in the point-in-time evidence index (`event_time`). With neither, or with several indexed
originals and no stated date, the event time is unknown and the check fails (`AMENDED_ORIGINAL_UNKNOWN`). A
verified amendment clause that itself dates the event ("On July 7, 2026, the Audit Committee concluded ...") older
than `max_event_age_ms` is stale too (review V04).

The result is a `RedFlagVerification.v1` dict. A verified one is attached to the finding as `red_flag`; it names
the predicate and the evidence span, never an action. What the predicate may do is looked up from its record
by the consumer and enabled only by the strategy profile (`larp.integration.contract.authority`): code owns
the action, the assessment only establishes the fact.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import re

from larp.intelligence.common import IntelligenceError, sha256_hex
from larp.intelligence.semantics import classify_event, clause_bounds, finding_eligible

CONFIG = Path(__file__).resolve().parents[2] / "config" / "intelligence" / "red_flags.v1.json"
SCHEMA = "RedFlagPredicateSet.v1"
VERIFICATION = "RedFlagVerification.v1"
CLASSES = {1: "EXIT", 2: "BLOCK_NEW_BUYS", 3: "SHADOW"}
REASONS = ("VERIFIED", "OUT_OF_SCOPE_FORM", "OUT_OF_SCOPE_FILER", "ITEM_NOT_IN_METADATA", "BACKFILL_NOT_ACTIONABLE",
           "AMENDED_ORIGINAL_UNKNOWN", "STALE_EVENT", "NO_ITEM_SECTION", "NO_CONDITION_TEXT", "NEGATED", "THIRD_PARTY",
           "NOT_CURRENT", "NOT_ASSERTED")
EVENT_TIME_BASES = ("FILING_ACCEPTANCE", "AMENDED_FILING_IN_INDEX", "AMENDMENT_STATES_ORIGINAL_DATE")
REQUIRED = ("predicate_id", "version", "class", "factual_condition", "issuer_scope", "trigger", "required_sources",
            "required_fields", "affected_period", "freshness", "directive", "reset", "resolution", "reentry", "fixtures")
# A block heading: "Item x.xx" (or a list, "Items 2.05 and 2.06") at the start of a line (saved text puts table
# cells on one " | " row), not followed by a word or mark that makes it part of a sentence ("Item 2.06 of Form 8-K
# requires ..."). A mention inside a sentence is not a heading (IDEA-041 R03; lists: review V03).
_CODE = r"\d{1,2}\.\d{2}(?![\d.]*\d)"
BLOCK_HEADING = re.compile(
    r"^[ \t]*(?:[•·*\-–—][ \t]*)?Items?[ \t]+(?P<codes>" + _CODE
    + r"(?:[ \t]*(?:,|&|/|and)[ \t]*(?:Items?[ \t]+)?" + _CODE + r")*)"
    r"(?![ \t]*(?:[,;)]|(?:of|under|to|in|on|at|by|for|from|with|and|or|as|is|was|are|were|be|been|requires?|"
    r"required|which|that|above|below|herein|hereof|hereunder|thereof|has|have|also|further|this|these)\b))", re.I | re.M)
SIGNATURES = re.compile(r"^[ \t]*SIGNATURES?[ \t]*$", re.I | re.M)
_TITLE_GAP = r"[ \t]*[.:|\-–—]?[ \t]*(?:\|[ \t]*)?"
# A title is taken as part of the heading only when the heading ends after it (end of line, punctuation, a cell
# break) or a new sentence starts: "Item 2.06 Impairment charges ... were recorded" keeps its body (review V03).
_TITLE_END = r"(?=[ \t]*(?:[.:;|]|$|(?-i:[A-Z])))"
SECTION_MAX_CHARS = 20_000
MAX_SECTIONS = 50
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")
_DATE = r"(?P<month>" + "|".join(MONTHS) + r")\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})\b"
_NO_AMEND = r"(?:(?!amend|previous)[^\n])"
# "... amends the Current Report on Form 8-K filed [by the Company with the SEC] [on] July 8, 2026 ..." or "... dated
# July 31, 2026". The span between may not mention another amendment ("as previously amended on ...", review V04).
AMENDED_ORIGINAL_DATE = re.compile(
    r"\bamend(?:s|ed|ing)?\b" + _NO_AMEND + r"{0,240}?\bForm\s+8-K\b(?!/A)" + _NO_AMEND
    + r"{0,240}?\b(?:filed|furnished|submitted|dated)\b" + _NO_AMEND + r"{0,160}?\b" + _DATE, re.I)
# The verified clause's own leading event date ("On July 7, 2026, the Audit Committee concluded ...").
LEAD_DATE = re.compile(r"^\s*On\s+" + _DATE, re.I)
_HYPHENS = {0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-"}
PERIOD = re.compile(r"\b(?:(?:first|second|third|fourth)\s+(?:fiscal\s+)?quarter(?:\s+of\s+(?:fiscal\s+)?\d{4})?|"
                    r"(?:fiscal\s+)?(?:year|quarter|period|months?)s?\s+ended\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|"
                    r"fiscal\s+(?:year\s+)?\d{4})\b", re.I)


def load_predicates(path: Path = CONFIG) -> tuple:
    """({predicate_id: record}, set sha256). Refuses a malformed or inconsistent set."""
    raw = Path(path).read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if data.get("schema") != SCHEMA or type(data.get("set_version")) is not int:
        raise IntelligenceError("Unknown red-flag predicate set schema")
    out, items = {}, set()
    for record in data["predicates"]:
        missing = [k for k in REQUIRED if k not in record]
        if missing:
            raise IntelligenceError(f"Red-flag predicate lacks {missing}")
        pid, cls = record["predicate_id"], record["class"]
        if pid in out or cls not in CLASSES or record["directive"].get("kind") != CLASSES[cls]:
            raise IntelligenceError(f"Red-flag predicate {pid!r}: duplicate, unknown class or class/directive mismatch")
        if type(record["version"]) is not int or record["version"] < 1:
            raise IntelligenceError(f"Red-flag predicate {pid!r} needs a positive integer version")
        if cls == 2 and (type(record["directive"].get("block_sessions")) is not int
                         or record["directive"]["block_sessions"] <= 0):
            raise IntelligenceError(f"Class 2 predicate {pid!r} needs a positive block_sessions")
        if cls in (1, 2):
            trigger = record["trigger"]
            if trigger.get("item") in items or not trigger.get("forms") or not trigger.get("event"):
                raise IntelligenceError(f"Item predicate {pid!r}: duplicate item or missing trigger fields")
            items.add(trigger["item"])
            for key in ("title_pattern", "condition_pattern"):
                re.compile(trigger[key])
            age = record["freshness"].get("max_event_age_ms")
            if type(age) is not int or age <= 0:
                raise IntelligenceError(f"Item predicate {pid!r} needs a positive max_event_age_ms")
        out[pid] = record
    return out, sha256_hex(raw)


def item_predicates(predicates: dict) -> dict:
    """{item code: record} for the item classes (1 and 2)."""
    return {r["trigger"]["item"]: r for r in predicates.values() if r["class"] in (1, 2)}


def heading_pattern(item: str, title_pattern: str = "") -> re.Pattern:
    """What follows the item's block heading and still belongs to it: its title, when the title ends the heading
    (`Item 4.02. Non-Reliance on ...`), and a closing period or colon."""
    title = f"(?:{_TITLE_GAP}(?:{title_pattern}){_TITLE_END})?" if title_pattern else ""
    return re.compile(title + r"[ \t]*[.:]?", re.I | re.M)


def sections(text: str, item: str, title: re.Pattern) -> list:
    """(start of heading, end of heading, end of section) for each block heading that lists the item; a section ends
    at the next block heading that does not list it, a signature heading, or SECTION_MAX_CHARS. Consecutive headings
    of the item belong to one section; at most MAX_SECTIONS are read (linear in the text, review V06)."""
    heads = [(m.start(), m.end(), item in re.findall(r"\d{1,2}\.\d{2}", m.group("codes")))
             for m in BLOCK_HEADING.finditer(text)]
    stops = sorted([h[0] for h in heads if not h[2]] + [m.start() for m in SIGNATURES.finditer(text)])
    out, covered, k = [], -1, 0
    for start, head_end, mine in heads:
        if not mine or start < covered:
            continue
        while k < len(stops) and stops[k] <= start:
            k += 1
        stop = min(stops[k] if k < len(stops) else len(text), head_end + SECTION_MAX_CHARS)
        body = title.match(text, head_end).end()
        if stop > body:
            out.append((start, body, stop))
        covered = stop
        if len(out) >= MAX_SECTIONS:
            break
    return out


def _blank_headings(text: str, spans) -> str:
    """The text with each heading [start, end) blanked and closed by a line break: offsets are unchanged, and a body
    sentence on a heading's line becomes its own clause."""
    parts, at = [], 0
    for start, end in spans:
        if end > start:
            parts += [text[at:start], " " * (end - start - 1), "\n"]
            at = end
    return "".join(parts) + text[at:]


def _day_ms(year: str, month: str, day: str) -> int | None:
    try:
        when = datetime(int(year), MONTHS.index(month.lower()) + 1, int(day), tzinfo=timezone.utc)
    except ValueError:
        return None
    return int(when.timestamp() * 1000)


def event_time(record: dict, *, texts: dict, prior_records, item: str) -> tuple:
    """(event ms or None, basis, accession of the indexed original that set it or None).

    An original filing's event time is its acceptance. An amendment's is its original filing's (module docstring):
    the earliest original filing date the amendment states (a date after the amendment itself is ignored), and the
    original 8-K in the point-in-time index that lists the same item, at or before the amendment, when exactly one
    does. With several such originals and no stated date the amendment cannot be dated (review V04: never the
    latest one by default); with neither, `AMENDED_ORIGINAL_UNKNOWN`. A stated date counts from 00:00 UTC."""
    own = record.get("original_ms")
    if type(own) is not int:
        return None, "FILING_ACCEPTANCE", None
    if not (record.get("form") or "").endswith("/A"):
        return own, "FILING_ACCEPTANCE", None
    found = []
    for doc in record.get("documents") or []:
        text = (texts.get(doc.get("text_sha256")) or "").translate(_HYPHENS)
        for m in AMENDED_ORIGINAL_DATE.finditer(text):
            stated = _day_ms(m.group("year"), m.group("month"), m.group("day"))
            if stated is not None and stated <= own:
                found.append((stated, "AMENDMENT_STATES_ORIGINAL_DATE", None))
    originals = [r for r in prior_records
                 if r.get("accession") != record.get("accession") and r.get("form") == "8-K"
                 and item in (r.get("items") or []) and type(r.get("original_ms")) is int and r["original_ms"] <= own]
    if len(originals) == 1:
        found.append((originals[0]["original_ms"], "AMENDED_FILING_IN_INDEX", originals[0].get("accession")))
    if not found:
        return None, "AMENDED_ORIGINAL_UNKNOWN", None
    return min(found, key=lambda f: (f[0], f[1]))


def verify_item(predicate: dict, *, record: dict, texts: dict, issuer_names: tuple, filer_class: str,
                cutoff_ms: int, set_sha256: str, prior_records=()) -> dict:
    """RedFlagVerification.v1 for one item of one assessed record. `texts`: {text_sha256: loaded text};
    `prior_records`: the issuer's records available at the cutoff (latest revision each), to date an amendment."""
    trigger, item = predicate["trigger"], predicate["trigger"]["item"]
    out = {"schema": VERIFICATION, "predicate_id": predicate["predicate_id"], "predicate_version": predicate["version"],
           "class": predicate["class"], "set_sha256": set_sha256, "item": item, "accession": record["accession"],
           "record_id": record["record_id"], "revision": record.get("revision", 0), "form": record["form"],
           "amendment": record["form"].endswith("/A"), "event_original_ms": record.get("original_ms"),
           "event_time_basis": None, "amends_accession": None,
           "verified": False, "reason": None, "span": None, "semantics": None, "affected_periods": [],
           "checked": []}

    def fail(reason, **extra):
        return dict(out, reason=reason, **extra)

    if record["form"] not in trigger["forms"]:
        return fail("OUT_OF_SCOPE_FORM")
    if filer_class not in predicate["issuer_scope"]["filer_classes"]:
        return fail("OUT_OF_SCOPE_FILER")
    if item not in (record.get("items") or []):
        return fail("ITEM_NOT_IN_METADATA")
    freshness = predicate["freshness"]
    if record.get("ingest_mode") == "BACKFILL" and not freshness.get("backfill_actionable"):
        return fail("BACKFILL_NOT_ACTIONABLE")
    when, basis, amends = event_time(record, texts=texts, prior_records=prior_records, item=item)
    out.update(event_original_ms=when, event_time_basis=None if when is None else basis, amends_accession=amends)
    if when is None and basis == "AMENDED_ORIGINAL_UNKNOWN":
        return fail("AMENDED_ORIGINAL_UNKNOWN")
    if type(when) is not int or cutoff_ms - when > freshness["max_event_age_ms"]:
        return fail("STALE_EVENT")
    original = record.get("original_ms")  # the document's own date, for reading its tense and stated dates
    title = heading_pattern(item, trigger["title_pattern"])
    condition = re.compile(trigger["condition_pattern"], re.I)
    found_section, seen = False, []
    for doc in record.get("documents") or []:
        loaded = texts.get(doc.get("text_sha256"))
        if loaded is None:
            continue
        found = sections(loaded, item, title)
        text = _blank_headings(loaded, [(h_lo, lo) for h_lo, lo, _ in found])
        for h_lo, lo, hi in found:
            found_section = True
            for m in condition.finditer(text, lo, hi):
                sem = classify_event(text, m.start(), m.end(), event=trigger["event"],
                                     document_ms=original, issuer_names=issuer_names)
                seen.append(sem)
                if finding_eligible(sem) and sem.get("attribution") == "SOURCE_ASSERTS":
                    clause_lo, clause_hi = clause_bounds(text, m.start(), m.end())
                    clause = text[max(lo, clause_lo): min(hi, clause_hi)].strip()
                    lead = LEAD_DATE.match(clause) if out["amendment"] else None
                    stated = _day_ms(lead.group("year"), lead.group("month"), lead.group("day")) if lead else None
                    if stated is not None and cutoff_ms - stated > freshness["max_event_age_ms"]:
                        return fail("STALE_EVENT", checked=[s["assertion"] for s in seen])  # amendment of an old event
                    return dict(out, verified=True, reason="VERIFIED", semantics=sem,
                                span={"doc": doc["text_sha256"], "doc_name": doc.get("name"), "text": clause},
                                affected_periods=sorted({p.group(0) for p in PERIOD.finditer(clause)}),
                                checked=[s["assertion"] for s in seen])
    if not found_section:
        return fail("NO_ITEM_SECTION")
    if not seen:
        return fail("NO_CONDITION_TEXT")
    assertions = {s["assertion"] for s in seen}
    actors = {s["actor"] for s in seen}
    reason = ("NEGATED" if "NEGATED" in assertions else
              "THIRD_PARTY" if "THIRD_PARTY" in actors else
              "NOT_CURRENT" if assertions == {"OCCURRED"} else "NOT_ASSERTED")
    return fail(reason, checked=[s["assertion"] for s in seen])


__all__ = ["load_predicates", "item_predicates", "verify_item", "sections", "heading_pattern", "event_time", "CLASSES",
           "REASONS", "EVENT_TIME_BASES"]
