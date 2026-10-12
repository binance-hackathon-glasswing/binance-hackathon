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
3. a loaded document of the filing has the item's own section (its heading), and inside that section, outside
   any heading clause, a condition clause that `semantics.classify_event` reads as the issuer's current,
   occurred, source-asserted event (not negated, conditional, attributed or a third party's).

The result is a `RedFlagVerification.v1` dict. A verified one is attached to the finding as `red_flag`; it names
the predicate and the evidence span, never an action. What the predicate may do is looked up from its record
by the consumer and enabled only by the strategy profile (`larp.integration.contract.authority`): code owns
the action, the assessment only establishes the fact.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
import re

from larp.intelligence.common import IntelligenceError, sha256_hex
from larp.intelligence.semantics import classify_event, clause_bounds, finding_eligible

CONFIG = Path(__file__).resolve().parents[2] / "config" / "intelligence" / "red_flags.v1.json"
SCHEMA = "RedFlagPredicateSet.v1"
VERIFICATION = "RedFlagVerification.v1"
CLASSES = {1: "EXIT", 2: "BLOCK_NEW_BUYS", 3: "SHADOW"}
REASONS = ("VERIFIED", "OUT_OF_SCOPE_FORM", "OUT_OF_SCOPE_FILER", "ITEM_NOT_IN_METADATA", "BACKFILL_NOT_ACTIONABLE",
           "STALE_EVENT", "NO_ITEM_SECTION", "NO_CONDITION_TEXT", "NEGATED", "THIRD_PARTY", "NOT_CURRENT",
           "NOT_ASSERTED", "AMENDMENT_ORIGIN_UNKNOWN")
REQUIRED = ("predicate_id", "version", "class", "factual_condition", "issuer_scope", "trigger", "required_sources",
            "required_fields", "affected_period", "freshness", "directive", "reset", "resolution", "reentry", "fixtures")
ANY_ITEM_HEADING = re.compile(r"^[ \t]*Item\s+(\d{1,2}\.\d{2})\b", re.I | re.M)
SECTION_MAX_CHARS = 20_000
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
            for key in ("heading_pattern", "condition_pattern"):
                re.compile(trigger[key])
            age = record["freshness"].get("max_event_age_ms")
            if type(age) is not int or age <= 0:
                raise IntelligenceError(f"Item predicate {pid!r} needs a positive max_event_age_ms")
        out[pid] = record
    return out, sha256_hex(raw)


def item_predicates(predicates: dict) -> dict:
    """{item code: record} for the item classes (1 and 2)."""
    return {r["trigger"]["item"]: r for r in predicates.values() if r["class"] in (1, 2)}


def _heading_clause(text: str, lo: int, hi: int) -> bool:
    """The condition sits in an item heading's own clause, e.g. 'Item 4.02 Non-Reliance on ...'. Only that clause
    is excluded: a heading and its body in one paragraph still leave the body's sentences readable."""
    c_lo, c_hi = clause_bounds(text, lo, hi)
    clause = text[c_lo:c_hi]
    heading = ANY_ITEM_HEADING.match(clause.lstrip())
    if not heading:
        return False
    # A body sentence in the heading paragraph still asserts an occurrence.
    return not re.search(r"\b(?:the\s+(?:company|board|audit\s+committee)|our|we|on\s+[A-Z][a-z]+)\b",
                         clause[heading.end():], re.I)


def sections(text: str, item: str, heading: re.Pattern) -> list:
    """(start, end) of each section that starts at the item's heading and ends at the next other item's heading."""
    out = []
    for m in ANY_ITEM_HEADING.finditer(text):
        if m.group(1) != item or not heading.search(m.group(0)):
            continue
        end = min(len(text), m.end() + SECTION_MAX_CHARS)
        for other in ANY_ITEM_HEADING.finditer(text, m.end(), end):
            if other.group(1) != item:
                end = other.start()
                break
        if end > m.end():
            out.append((m.start(), end))
    return out


def verify_item(predicate: dict, *, record: dict, texts: dict, issuer_names: tuple, filer_class: str,
                cutoff_ms: int, set_sha256: str) -> dict:
    """RedFlagVerification.v1 for one item of one assessed record. `texts`: {text_sha256: loaded text}."""
    trigger, item = predicate["trigger"], predicate["trigger"]["item"]
    out = {"schema": VERIFICATION, "predicate_id": predicate["predicate_id"], "predicate_version": predicate["version"],
           "class": predicate["class"], "set_sha256": set_sha256, "item": item, "accession": record["accession"],
           "record_id": record["record_id"], "revision": record.get("revision", 0), "form": record["form"],
           "amendment": record["form"].endswith("/A"), "event_original_ms": record.get("original_ms"),
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
    original = record.get("original_ms")
    if record["form"].endswith("/A"):
        # SEC acceptance of an amendment does not refresh the underlying occurrence.
        dates = []
        reference = re.compile(r"(?:Current\s+Report\s+on\s+)?Form\s+8-K(?:\s+originally)?\s+filed\s+(?:on\s+)?"
                               r"([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", re.I)
        for doc in record.get("documents") or []:
            for match in reference.finditer(texts.get(doc.get("text_sha256"), "")):
                try:
                    dates.append(int(datetime.strptime(match.group(1), "%B %d, %Y").replace(
                        tzinfo=timezone.utc).timestamp() * 1000))
                except ValueError:
                    continue
        if not dates:
            return fail("AMENDMENT_ORIGIN_UNKNOWN")
        original = min(dates)
        out["event_original_ms"] = original
    if type(original) is not int or original > cutoff_ms or cutoff_ms - original > freshness["max_event_age_ms"]:
        return fail("STALE_EVENT")
    heading = re.compile(trigger["heading_pattern"], re.I)
    condition = re.compile(trigger["condition_pattern"], re.I)
    found_section, seen = False, []
    for doc in record.get("documents") or []:
        text = texts.get(doc.get("text_sha256"))
        if text is None:
            continue
        for lo, hi in sections(text, item, heading):
            found_section = True
            for m in condition.finditer(text, lo, hi):
                if _heading_clause(text, m.start(), m.end()):
                    continue
                sem = classify_event(text, m.start(), m.end(), event=trigger["event"],
                                     document_ms=original, issuer_names=issuer_names)
                seen.append(sem)
                if finding_eligible(sem) and sem.get("attribution") == "SOURCE_ASSERTS":
                    clause_lo, clause_hi = clause_bounds(text, m.start(), m.end())
                    clause = text[max(lo, clause_lo): min(hi, clause_hi)].strip()
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
              "NOT_CURRENT" if assertions == {"OCCURRED"} else "NOT_ASSERTED", "AMENDMENT_ORIGIN_UNKNOWN")
    return fail(reason, checked=[s["assertion"] for s in seen])


__all__ = ["load_predicates", "item_predicates", "verify_item", "sections", "CLASSES", "REASONS"]
