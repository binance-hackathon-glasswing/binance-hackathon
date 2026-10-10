"""Claim verification (G-53) and conflict detection.

A claim is accepted only if it is a well-formed claim object; its quoted span is the exact
substring at the stated offsets of a loaded document; with records, that document belongs to
the claimed source record, from which all provenance is taken; the metric/event is named in the
span, and an event is not negated in the surrounding source text; every stated number (value,
range bounds, tolerance) appears in the span; the scale and currency are stated in the span or
its cited scale span; and the period parses from the cited period span. Period and scale spans
come from the same statement: the same line for prose, and for a table cell its own column
header and the table's scale line, read exactly as the extractor reads them (per-share rows
keep their unscaled amounts under an "except per share" exception). Claims about consensus,
estimates, ratings or prices have no admissible source and are always rejected.
"""

from fractions import Fraction
import re

from larp.intelligence.common import frac
from larp.intelligence.facts import (
    KEYWORD_EVENTS, METRIC_NAMES, METRIC_ONE, PER_SHARE_EXCEPTION, PER_SHARE_METRICS, PERCENT_METRICS, SCALES,
    finish_fact, half_unit, negated, normalized, parse_period, row_metric, stated_numbers, table_cell,
    table_scale, table_unit, token_decimals, values_agree,
)

ALLOWED_KINDS = ("REPORTED", "GUIDANCE", "EVENT")
_DECIMAL = re.compile(r"^-?\d+(?:\.\d+)?$")
_EVENTS = dict(KEYWORD_EVENTS)
_SCALE_WORDS = re.compile(r"\b(thousands?|millions?|billions?|trillions?)\b", re.I)
_CURRENCY = {"USD": re.compile(r"\$|\bUSD\b|U\.S\.\s+dollars", re.I),
             "KRW": re.compile(r"\bKRW\b|\u20a9|\bwon\b", re.I)}
_FACT_KEYS = ("kind", "metric", "period", "value", "range", "tolerance_pct", "unit", "scale_exp10",
              "precision_exp10", "direction", "security_scope", "span", "period_span", "scale_span", "basis")
_CLAIM_KEYS = frozenset(_FACT_KEYS) | {"source"}
_TEXT_FIELDS = ("kind", "metric", "period", "unit", "direction", "security_scope", "basis")
_SOURCE_KEYS = frozenset({"record_id", "accession", "doc_name", "available_ms", "original_ms"})
_SPAN_KEYS = frozenset({"doc", "start", "end", "text"})


def _span_shape(span) -> bool:
    return (type(span) is dict and set(span) == _SPAN_KEYS and type(span["doc"]) is str
            and type(span["text"]) is str and type(span["start"]) is int and type(span["end"]) is int)


def claim_schema_error(claim) -> str | None:
    """Reason code if `claim` is not a well-formed claim object; checked before any field is used."""
    if type(claim) is not dict:
        return "CLAIM_MALFORMED"
    if set(claim) - _CLAIM_KEYS:
        return "CLAIM_UNKNOWN_FIELD"
    for key in _TEXT_FIELDS:
        if claim.get(key) is not None and type(claim[key]) is not str:
            return f"{key.upper()}_MALFORMED"
    for key in ("scale_exp10", "precision_exp10"):
        if claim.get(key) is not None and type(claim[key]) is not int:
            return "SCALE_MALFORMED"
    source = claim.get("source")
    if source is not None and (type(source) is not dict or set(source) - _SOURCE_KEYS
                               or any(v is not None and type(v) not in (str, int) for v in source.values())):
        return "SOURCE_MALFORMED"
    for key, reason in (("span", "SPAN_MALFORMED"), ("period_span", "PERIOD_SPAN_MALFORMED"),
                        ("scale_span", "SCALE_SPAN_MALFORMED")):
        if claim.get(key) is not None and not _span_shape(claim[key]):
            return reason
    if claim.get("range") is not None and (type(claim["range"]) is not list or len(claim["range"]) != 2):
        return "RANGE_MALFORMED"
    return None


def _check_span(span, texts):
    if not _span_shape(span):
        return None, "SPAN_MALFORMED"
    text = texts.get(span["doc"])
    if text is None:
        return None, "SPAN_DOCUMENT_NOT_LOADED"
    start, end = span["start"], span["end"]
    if not 0 <= start < end <= len(text):
        return None, "SPAN_OFFSETS_INVALID"
    if text[start:end] != span["text"]:
        return None, "SPAN_TEXT_MISMATCH"
    return span["text"], None


def _value(raw):
    """Model claims state decimals as strings; extracted facts carry exact [num, den] pairs."""
    if raw is None:
        return None
    if type(raw) is str and _DECIMAL.match(raw):
        return Fraction(raw)
    if type(raw) is list and len(raw) == 2 and all(type(v) is int for v in raw) and raw[1] > 0:
        return Fraction(raw[0], raw[1])
    raise ValueError("value")


def _offsets(span):
    return None if span is None else (span["start"], span["end"])


def _line(text: str, start: int, end: int) -> tuple:
    """Bounds of the line(s) holding [start, end): one prose statement in the saved text."""
    stop = text.find("\n", end)
    return text.rfind("\n", 0, start) + 1, len(text) if stop < 0 else stop


def verify_claim(claim: dict, texts: dict, records: dict | None = None) -> tuple:
    """Return (fact, None) if verified, else (None, reason). `texts` maps text_sha256 -> text.

    `records` maps record_id -> EvidenceRecord.v1. With records, the claim must name a known
    source record whose documents include the cited one, and the fact's provenance (record,
    accession, document name, timestamps) comes from that record, never from the claim. With
    records=None only the text is checked (extraction round trips); such a fact keeps the
    caller's source.
    """
    reason = claim_schema_error(claim)
    if reason:
        return None, reason
    kind, metric = claim.get("kind"), claim.get("metric")
    if kind not in ALLOWED_KINDS:
        return None, "KIND_NOT_ALLOWED"  # consensus/estimates/prices have no admissible source
    record_id = (claim.get("source") or {}).get("record_id")
    record = None if records is None or record_id is None else records.get(record_id)
    if records is not None and record_id is not None and record is None:
        return None, "SOURCE_RECORD_UNKNOWN"
    if kind == "EVENT" and metric is not None and metric.startswith("ITEM:"):
        if record is None or metric[5:] not in record["items"]:
            return None, "ITEM_NOT_IN_RECORD"
        return _fact(claim, record, None, event=True), None
    span = claim.get("span")
    span_text, reason = _check_span(span, texts)
    if reason:
        return None, reason
    doc_name = None
    if records is not None:
        if record is None:
            return None, "SOURCE_RECORD_UNKNOWN"
        doc = next((d for d in record["documents"] if d.get("text_sha256") == span["doc"]), None)
        if doc is None:
            return None, "SPAN_NOT_IN_SOURCE_RECORD"
        doc_name = doc["name"]
    text = texts[span["doc"]]
    side = {}
    for key, prefix in (("period_span", "PERIOD_"), ("scale_span", "SCALE_")):
        if claim.get(key) is None:
            continue
        side[key], reason = _check_span(claim[key], texts)
        if reason:
            return None, prefix + reason
        if claim[key]["doc"] != span["doc"]:
            return None, prefix + "SPAN_OTHER_DOCUMENT"
    if kind == "EVENT":
        matches = list(_EVENTS[metric].finditer(text, span["start"], span["end"])) if metric in _EVENTS else []
        if not matches:
            return None, "EVENT_NOT_IN_SPAN"
        if all(negated(text, m.start()) for m in matches):
            return None, "EVENT_NEGATED"  # "recorded no impairment" is not an impairment
        return _fact(claim, record, doc_name, event=True), None
    if metric not in METRIC_NAMES or not METRIC_ONE[metric].search(span_text):
        return None, "METRIC_NOT_IN_SPAN"
    try:
        value = _value(claim.get("value"))
        bounds = [_value(v) for v in (claim.get("range") or [])]
        tolerance = _value(claim.get("tolerance_pct"))
    except ValueError:
        return None, "VALUE_MALFORMED"
    if value is None and len(bounds) != 2:
        return None, "VALUE_MISSING"
    stated = stated_numbers(span_text)
    table = " | " in span_text
    if table and (value is None or not stated or stated[-1] != value):
        return None, "TABLE_VALUE_NOT_LAST_CELL"
    for number in [v for v in [value, tolerance, *bounds] if v is not None]:
        if number not in stated and -number not in stated:
            return None, "NUMBER_NOT_IN_SPAN"
    unit, scale = claim.get("unit"), claim.get("scale_exp10")
    if type(scale) is not int:
        return None, "SCALE_MALFORMED"
    context = " ".join([span_text, side.get("scale_span", "")])
    if table:
        cell = table_cell(text, span["start"], span["end"])
        if cell is None or "\n" in span_text or row_metric(cell["label"]) != metric:
            return None, "TABLE_CELL_NOT_VERIFIED"
        block = cell["block"]
        if unit != table_unit(metric, cell["cell"], block):
            return None, "UNIT_NOT_STATED"
        if scale != table_scale(metric, unit, block):
            return None, "SCALE_NOT_STATED"
        if _offsets(claim.get("scale_span")) != (None if unit == "PERCENT" else block["scale_span"]):
            return None, "SCALE_SPAN_NOT_TABLE_SCALE"
        if claim.get("period") is not None and _offsets(claim.get("period_span")) != cell["period"][1:]:
            return None, "PERIOD_NOT_TABLE_COLUMN"
    else:
        low, high = _line(text, span["start"], span["end"])
        for key, prefix in (("period_span", "PERIOD_"), ("scale_span", "SCALE_")):
            other = claim.get(key)
            if other is not None and not low <= other["start"] < other["end"] <= high:
                return None, prefix + "SPAN_OUTSIDE_STATEMENT"
        words = {SCALES[w.lower()] for w in _SCALE_WORDS.findall(context)}
        if metric in PER_SHARE_METRICS:
            if scale != 0 or (words and not PER_SHARE_EXCEPTION.search(context)):
                return None, "SCALE_NOT_STATED"
        elif (scale == 0 and unit != "PERCENT" and words) or (scale != 0 and scale not in words):
            return None, "SCALE_NOT_STATED"
    if unit == "PERCENT":
        if metric not in PERCENT_METRICS and "%" not in span_text and "percent" not in span_text.lower():
            return None, "UNIT_NOT_STATED"
    elif unit not in _CURRENCY or not _CURRENCY[unit].search(context):
        return None, "UNIT_NOT_STATED"
    period = claim.get("period")
    if period is not None and parse_period(side.get("period_span", span_text)) != period:
        return None, "PERIOD_NOT_STATED"
    # Precision comes from the written tokens in the span, never from the claim itself.
    written = [token_decimals(span_text, n) for n in ([value] if value is not None else bounds)]
    precision = scale - max(d or 0 for d in written)
    normalized_claim = dict(claim, value=None if value is None else frac(value),
                            range=None if not bounds else [frac(b) for b in bounds],
                            tolerance_pct=None if tolerance is None else frac(tolerance),
                            precision_exp10=precision)
    return _fact(normalized_claim, record, doc_name), None


def _fact(claim, record, doc_name, *, event=False):
    fact = {k: claim.get(k) for k in _FACT_KEYS}
    if event:  # an event asserts occurrence only: no value, unit, period or direction is verified
        fact.update(period=None, value=None, range=None, tolerance_pct=None, unit=None, scale_exp10=0,
                    precision_exp10=0, direction=None, period_span=None, scale_span=None)
    fact["basis"] = fact["basis"] or "MODEL_CLAIM_VERIFIED"
    fact["security_scope"] = fact["security_scope"] or "ISSUER"
    fact["scale_exp10"] = fact["scale_exp10"] or 0
    if fact["precision_exp10"] is None:
        fact["precision_exp10"] = fact["scale_exp10"]
    source = claim.get("source") or {}
    if record is not None:
        source = {"record_id": record["record_id"], "accession": record["accession"], "doc_name": doc_name,
                  "available_ms": record["available_ms"], "original_ms": record["original_ms"]}
    return finish_fact(fact, source)


def fact_as_claim(fact: dict) -> dict:
    """Extracted facts in the claim format, so the baseline passes through the same verifier."""
    claim = {k: fact[k] for k in _FACT_KEYS}
    claim["source"] = fact["source"]
    return claim


def detect_conflicts(facts: list) -> list:
    """Same metric/kind/period/unit/scope stated with different exact values.

    REPORTED values that differ across documents or filings conflict. Differing GUIDANCE for a
    period within ONE filing conflicts; across filings it is an update, compared separately.
    """
    groups = {}
    for fact in facts:
        if fact["kind"] == "EVENT" or fact["period"] is None:
            continue
        scope = fact["source"].get("accession") if fact["kind"] == "GUIDANCE" else None
        key = (fact["kind"], fact["metric"], fact["period"], fact["unit"], fact["security_scope"], scope)
        groups.setdefault(key, []).append(fact)
    conflicts = []
    for key, members in sorted(groups.items(), key=lambda kv: str(kv[0])):
        # Rounded text ("$35.1 billion") and a precise table cell ("35,082" million) agree.
        if any(not values_agree(a, b) for i, a in enumerate(members) for b in members[i + 1:]):
            conflicts.append({"kind": key[0], "metric": key[1], "period": key[2], "unit": key[3],
                              "fact_ids": sorted(f["fact_id"] for f in members),
                              "accessions": sorted({f["source"].get("accession") or "" for f in members})})
    return conflicts


def compare(new: dict, prior: dict) -> dict:
    """Exact comparison of two verified facts; INCOMPARABLE unless metric/unit/period/scope match."""
    base = {"new_fact_id": new["fact_id"], "prior_fact_id": prior["fact_id"]}
    if (new["metric"], new["unit"], new["security_scope"]) != (prior["metric"], prior["unit"], prior["security_scope"]):
        return dict(base, relation="INCOMPARABLE", reason="METRIC_UNIT_OR_INSTRUMENT_DIFFERS")
    if new["period"] is None or new["period"] != prior["period"]:
        return dict(base, relation="INCOMPARABLE", reason="PERIOD_DIFFERS_OR_UNKNOWN")
    a, b = normalized(new), normalized(prior)
    if a is None or b is None:
        return dict(base, relation="INCOMPARABLE", reason="NO_VALUE")
    if new["kind"] == "REPORTED" and prior["kind"] == "GUIDANCE":
        low, high = (b, b) if type(b) is not tuple else b
        if type(b) is not tuple and prior.get("tolerance_pct") is not None:
            band = b * Fraction(*prior["tolerance_pct"]) / 100
            low, high = b - band, b + band
        point = a if type(a) is not tuple else None
        if point is None:
            return dict(base, relation="INCOMPARABLE", reason="REPORTED_VALUE_IS_A_RANGE")
        relation = "BELOW" if point < low else "ABOVE" if point > high else "WITHIN"
        return dict(base, relation=relation, basis="REPORTED_VS_PRIOR_GUIDANCE",
                    delta=frac(point - (low + high) / 2))
    if new["kind"] != prior["kind"]:
        return dict(base, relation="INCOMPARABLE", reason="KIND_DIFFERS")
    mid = lambda v: (v[0] + v[1]) / 2 if type(v) is tuple else v
    delta = mid(a) - mid(b)
    tolerance = max(half_unit(new), half_unit(prior))
    relation = "EQUAL" if abs(delta) <= tolerance else "HIGHER" if delta > 0 else "LOWER"
    return dict(base, relation=relation, basis=f"{new['kind']}_VS_PRIOR_{prior['kind']}", delta=frac(delta),
                midpoint_derived=type(a) is tuple or type(b) is tuple)
