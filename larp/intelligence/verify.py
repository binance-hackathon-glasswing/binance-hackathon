"""Claim verification (G-53) and conflict detection.

A claim is accepted only if its quoted span is the exact substring at the stated offsets of a
loaded document, the metric/event is named in the span, every stated number (value, range
bounds, tolerance) appears in the span, the scale and currency are stated in the span or a
cited scale span, and the period parses from the cited period span. Claims about consensus,
estimates, ratings or prices have no admissible source and are always rejected.
"""

from fractions import Fraction
import re

from larp.intelligence.common import frac
from larp.intelligence.facts import (
    KEYWORD_EVENTS, METRIC_NAMES, METRIC_ONE, PERCENT_METRICS, SCALES, finish_fact, half_unit,
    normalized, parse_period, stated_numbers, token_decimals, values_agree,
)

ALLOWED_KINDS = ("REPORTED", "GUIDANCE", "EVENT")
_DECIMAL = re.compile(r"^-?\d+(?:\.\d+)?$")
_EVENTS = dict(KEYWORD_EVENTS)
_SCALE_WORDS = re.compile(r"\b(thousands?|millions?|billions?|trillions?)\b", re.I)
_CURRENCY = {"USD": re.compile(r"\$|\bUSD\b|U\.S\.\s+dollars", re.I),
             "KRW": re.compile(r"\bKRW\b|\u20a9|\bwon\b", re.I)}


def _check_span(span, texts):
    if type(span) is not dict or set(span) != {"doc", "start", "end", "text"}:
        return None, "SPAN_MALFORMED"
    text = texts.get(span["doc"])
    if text is None:
        return None, "SPAN_DOCUMENT_NOT_LOADED"
    start, end = span["start"], span["end"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
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


def verify_claim(claim: dict, texts: dict, records: dict) -> tuple:
    """Return (fact, None) if verified, else (None, reason). `texts` maps text_sha256 -> text."""
    if type(claim) is not dict:
        return None, "CLAIM_MALFORMED"
    kind, metric = claim.get("kind"), claim.get("metric")
    if kind not in ALLOWED_KINDS:
        return None, "KIND_NOT_ALLOWED"  # consensus/estimates/prices have no admissible source
    record = records.get((claim.get("source") or {}).get("record_id")) if claim.get("source") else None
    if kind == "EVENT" and type(metric) is str and metric.startswith("ITEM:"):
        if record is None or metric[5:] not in record["items"]:
            return None, "ITEM_NOT_IN_RECORD"
        return _fact(claim, record, None), None
    span_text, reason = _check_span(claim.get("span"), texts)
    if reason:
        return None, reason
    if kind == "EVENT":
        if metric not in _EVENTS or not _EVENTS[metric].search(span_text):
            return None, "EVENT_NOT_IN_SPAN"
        return _fact(claim, record, texts), None
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
    context = span_text
    if claim.get("scale_span") is not None:
        scale_text, reason = _check_span(claim["scale_span"], texts)
        if reason:
            return None, "SCALE_" + reason
        context += " " + scale_text
    words = {SCALES[w.lower()] for w in _SCALE_WORDS.findall(context)}
    if (scale == 0 and unit != "PERCENT" and words) or (scale != 0 and scale not in words):
        return None, "SCALE_NOT_STATED"
    if unit == "PERCENT":
        if metric not in PERCENT_METRICS and "%" not in span_text and "percent" not in span_text.lower():
            return None, "UNIT_NOT_STATED"
    elif unit not in _CURRENCY or not _CURRENCY[unit].search(context):
        return None, "UNIT_NOT_STATED"
    period = claim.get("period")
    if period is not None:
        source = span_text
        if claim.get("period_span") is not None:
            source, reason = _check_span(claim["period_span"], texts)
            if reason:
                return None, "PERIOD_" + reason
        if parse_period(source) != period:
            return None, "PERIOD_NOT_STATED"
    # Precision comes from the written tokens in the span, never from the claim itself.
    written = [token_decimals(span_text, n) for n in ([value] if value is not None else bounds)]
    precision = scale - max(d or 0 for d in written)
    normalized_claim = dict(claim, value=None if value is None else frac(value),
                            range=None if not bounds else [frac(b) for b in bounds],
                            tolerance_pct=None if tolerance is None else frac(tolerance),
                            precision_exp10=precision)
    return _fact(normalized_claim, record, texts), None


_FACT_KEYS = ("kind", "metric", "period", "value", "range", "tolerance_pct", "unit", "scale_exp10",
              "precision_exp10", "direction", "security_scope", "span", "period_span", "scale_span", "basis")


def _fact(claim, record, texts):
    fact = {k: claim.get(k) for k in _FACT_KEYS}
    fact["basis"] = fact["basis"] or "MODEL_CLAIM_VERIFIED"
    fact["security_scope"] = fact["security_scope"] or "ISSUER"
    fact["scale_exp10"] = fact["scale_exp10"] or 0
    if fact["precision_exp10"] is None:
        fact["precision_exp10"] = fact["scale_exp10"]
    source = claim.get("source") or {}
    if record is not None:
        source = {"record_id": record["record_id"], "accession": record["accession"],
                  "doc_name": source.get("doc_name"), "available_ms": record["available_ms"],
                  "original_ms": record["original_ms"]}
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
