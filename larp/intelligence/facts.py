"""Deterministic extraction of numerical facts and events, each with an exact supporting span.

This is the verified extraction baseline: no fitted parameters and no model. Every fact it
emits must pass `verify.verify_claim` against the saved text (a round-trip test enforces it).
Values are exact Fractions as written in the source plus an explicit power-of-ten scale and
unit; nothing is converted between currencies, share classes, listings or tokens.

Periods are canonical labels taken from the text ("FY2027-Q3", "2026-Q1", "FY2027"). Fiscal
and calendar labels are different bases and are never matched to each other.
"""

from fractions import Fraction
import re

from larp.intelligence.common import digest, frac

METRICS = (
    ("revenue", r"(?:total\s+)?(?:net\s+)?revenues?|net\s+sales|total\s+sales"),
    ("net_income", r"net\s+(?:income|earnings|profit)"),
    ("operating_income", r"operating\s+(?:income|profit)|income\s+from\s+operations"),
    ("gross_margin", r"gross\s+margin"),
    ("eps_diluted", r"diluted\s+(?:earnings|net\s+income)\s+per\s+share|diluted\s+eps"),
)
METRIC_NAMES = tuple(name for name, _ in METRICS)
PERCENT_METRICS = frozenset({"gross_margin"})
PER_SHARE_METRICS = frozenset({"eps_diluted"})
METRIC_RE = re.compile("|".join(rf"(?P<{name}>\b(?:{pattern})\b)" for name, pattern in METRICS), re.I)
METRIC_ONE = {name: re.compile(rf"\b(?:{pattern})\b", re.I) for name, pattern in METRICS}

_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
SCALES = {"thousand": 3, "thousands": 3, "million": 6, "millions": 6, "billion": 9, "billions": 9,
          "trillion": 12, "trillions": 12}
MONEY = re.compile(
    rf"(?P<cur>US\$|\$|USD\s?|KRW\s?|\u20a9\s?)(?P<num>{_NUM})(?:\s*(?P<scale>trillion|billion|million|thousand)\b)?"
    rf"|(?P<num2>{_NUM})\s*(?P<scale2>trillion|billion|million|thousand)?\s*(?P<cur2>(?:Korean\s+)?won\b|KRW\b)",
    re.I)
PERCENT = re.compile(rf"(?P<num>{_NUM})\s?(?:%|percent\b)", re.I)
TOLERANCE = re.compile(rf"^,?\s*plus\s+or\s+minus\s+(?P<num>{_NUM})\s?(?:%|percent\b)", re.I)
NUM_TOKEN = re.compile(r"\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?|\(?-?\d+(?:\.\d+)?\)?")
TABLE_SCALE = re.compile(r"\bin\s+(thousands|millions|billions|trillions)\b", re.I)
GUIDANCE_WORDS = re.compile(r"\b(?:expects?|expected|expecting|outlook|guidance|forecasts?|anticipates?|"
                            r"projects?|projected|targets?\s+revenue)\b", re.I)
DIRECTION = (("RAISED", re.compile(r"\b(?:rais(?:e|es|ed|ing)|increas(?:e|es|ed|ing))\b", re.I)),
             ("LOWERED", re.compile(r"\b(?:lower(?:s|ed|ing)?|reduc(?:e|es|ed|ing)|cut(?:s|ting)?)\b", re.I)),
             ("MAINTAINED", re.compile(r"\b(?:reaffirm(?:s|ed)?|maintain(?:s|ed)?|reiterat(?:e|es|ed))\b", re.I)))
SENTENCE_END = re.compile(r"(?<=[.!?;])\s+(?=[A-Z(\"'])")

KEYWORD_EVENTS = (
    ("RESTATEMENT", re.compile(r"should\s+no\s+longer\s+be\s+relied\s+upon|\brestate(?:d|ment|ments)?\b", re.I)),
    ("CYBERSECURITY_INCIDENT", re.compile(r"\bcybersecurity\s+incident\b", re.I)),
    ("DELISTING", re.compile(r"\bdelist(?:ed|ing)?\b", re.I)),
    ("IMPAIRMENT", re.compile(r"\bimpairments?\b", re.I)),
    ("OFFICER_DEPARTURE", re.compile(
        r"\b(?:resign(?:s|ed|ation)?|step(?:s|ped)?\s+down|depart(?:s|ure|ed)?)\b[^.\n]{0,80}?"
        r"\b(?:chief\s+executive|chief\s+financial|CEO|CFO)\b|"
        r"\b(?:chief\s+executive\s+officer|chief\s+financial\s+officer|CEO|CFO)\b[^.\n]{0,80}?"
        r"\b(?:resign(?:s|ed|ation)?|step(?:s|ped)?\s+down|depart(?:s|ure|ed)?)\b", re.I)),
)
NEGATION = re.compile(r"\b(?:no|not|none|neither|nor|never|without|cannot|absence\s+of|unnecessary)\b|n't\b", re.I)
# Modal, conditional and forward-looking cues: the event is possible or planned, not reported as having happened.
HYPOTHETICAL = re.compile(r"\b(?:may|might|could|would|should|can|if|unless|whether|possible|possibly|potential|"
                          r"potentially|risks?|likely|unlikely|future|expects?|expected|anticipates?|anticipated|"
                          r"intends?|plans?\s+to|in\s+the\s+event)\b", re.I)
# Phrases that contain a cue word but are not cues: deadlines, the non-reliance event phrase itself, and the month.
NOT_A_CUE = re.compile(r"\b(?:no|not)\s+later\s+than\b|\bshould\s+no\s+longer\s+be\s+relied\s+upon\b|"
                       r"\b(?-i:May)\s+(?:\d{1,2}|\d{4})\b", re.I)
# Clause ends: a line or sentence end, a semicolon, or a contrastive join. A bare comma or ", and" does not end
# a clause, so negation in a list ("did not identify loss, damage, and impairment") still counts.
CLAUSE_BREAK = re.compile(r"\n|;|(?<=[.!?])\s+(?=[A-Z(\"'])|(?i:,\s+(?:but|whereas|while|although|though|however|yet)\b)")
PER_SHARE_EXCEPTION = re.compile(r"\bexcept\b[^)\n]{0,40}?\bper[\s-]+share\b", re.I)


def unasserted(text: str, start: int, end: int):
    """Why the event at text[start:end] is not reported as having happened, or None if it is.

    The whole clause holding the match is read, the match included. "NEGATED": a negation appears in it
    ("recorded no impairment", "an impairment charge was not required", "did not identify ... an impairment").
    "HYPOTHETICAL": a modal, conditional or forward-looking cue appears in it ("could result in an impairment",
    "if ... we might recognize an impairment", "we expect to record an impairment").

    Conservative: one cue anywhere in the clause rejects the event, so "recorded an impairment and did not
    record a restructuring charge" gives no IMPAIRMENT fact."""
    lo, hi = text.rfind("\n", 0, start) + 1, len(text)
    for m in CLAUSE_BREAK.finditer(text, lo):
        if m.end() <= start:
            lo = m.end()
        elif m.start() >= end:
            hi = m.start()
            break
    clause = NOT_A_CUE.sub(" ", text[lo:hi])  # the match too: "CFO may resign" has its cue inside the match
    if NEGATION.search(clause):
        return "NEGATED"
    return "HYPOTHETICAL" if HYPOTHETICAL.search(clause) else None


_QUARTER = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
_PERIODS = (
    re.compile(r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\s+(fiscal\s+)?quarter\s+(?:of\s+)?"
               r"(fiscal\s+(?:year\s+)?)?(\d{4})\b", re.I),
    re.compile(r"\b(?:(fiscal)\s+(?:year\s+)?|(FY)\s?)(\d{4}|\d{2})\s+(first|second|third|fourth)\s+quarter\b", re.I),
    re.compile(r"\bQ([1-4])\s*(?:of\s+)?(FY\s?|fiscal\s+(?:year\s+)?)?'?(\d{4}|\d{2})\b", re.I),
    re.compile(r"\b(?:fiscal\s+(?:year\s+)?|FY\s?)(\d{4}|\d{2})\b", re.I),
)


def _year(text: str) -> int:
    return int(text) + 2000 if len(text) == 2 else int(text)


def periods_in(text: str) -> list:
    """All non-overlapping (canonical, start, end) period mentions, in text order."""
    found = []
    for kind, pattern in enumerate(_PERIODS):
        for m in pattern.finditer(text):
            if kind == 0:
                label = f"{'FY' if (m.group(2) or m.group(3)) else ''}{_year(m.group(4))}-Q{_QUARTER[m.group(1).lower()]}"
            elif kind == 1:
                label = f"FY{_year(m.group(3))}-Q{_QUARTER[m.group(4).lower()]}"
            elif kind == 2:
                label = f"{'FY' if m.group(2) else ''}{_year(m.group(3))}-Q{m.group(1)}"
            else:
                label = f"FY{_year(m.group(1))}"
            if not any(s < m.end() and m.start() < e for _, s, e in found):
                found.append((label, m.start(), m.end()))
    return sorted(found, key=lambda x: x[1])


def parse_period(text: str) -> str | None:
    found = periods_in(text)
    return found[0][0] if len(found) == 1 else None


def parse_number(token: str) -> Fraction:
    negative = token.startswith("(") and token.endswith(")")
    body = token.strip("()").replace(",", "")
    value = Fraction(body)
    return -value if negative and value > 0 else value


def numbers_in(text: str) -> list:
    return [parse_number(m.group(0)) for m in NUM_TOKEN.finditer(text)]


DATE = re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
                  r"\s+\d{1,2},\s+\d{4}\b")


def stated_numbers(text: str) -> list:
    """Numbers stated as amounts: tokens inside period phrases ("fiscal 2027") or dates are excluded."""
    blocked = [(s, e) for _, s, e in periods_in(text)] + [m.span() for m in DATE.finditer(text)]
    return [parse_number(m.group(0)) for m in NUM_TOKEN.finditer(text)
            if not any(s < m.end() and m.start() < e for s, e in blocked)]


def money_parts(m: re.Match) -> tuple:
    """(number text, scale_exp10, unit) of a MONEY match."""
    if m.group("num") is not None:
        cur = m.group("cur").strip().upper()
        unit = "KRW" if cur in ("KRW", "\u20a9") else "USD"
        return m.group("num"), SCALES.get((m.group("scale") or "").lower(), 0), unit
    return m.group("num2"), SCALES.get((m.group("scale2") or "").lower(), 0), "KRW"


def _scope(metric: str, unit: str, entry) -> str:
    if metric not in PER_SHARE_METRICS:
        return "ISSUER"
    matches = [s.security_id for s in entry.securities if s.currency == unit]
    return matches[0] if len(matches) == 1 and len(entry.securities) == 1 else "AMBIGUOUS"


def _span(doc_sha: str, text: str, start: int, end: int) -> dict:
    return {"doc": doc_sha, "start": start, "end": end, "text": text[start:end]}


def finish_fact(fact: dict, source: dict) -> dict:
    fact = dict(fact, source=source)
    fact["fact_id"] = "fact:" + digest("larp.intel.fact.v1", {k: v for k, v in fact.items() if k != "fact_id"})
    return fact


def _sentences(text: str):
    offset = 0
    for line in text.split("\n"):
        if " | " not in line and line.strip():
            start = 0
            for m in SENTENCE_END.finditer(line):
                yield offset + start, line[start:m.start()]
                start = m.end()
            yield offset + start, line[start:]
        offset += len(line) + 1


def _sentence_facts(text, doc_sha, entry):
    facts = []
    for base, sentence in _sentences(text):
        metrics = [(m.lastgroup, m.start(), m.end()) for m in METRIC_RE.finditer(sentence)]
        periods = periods_in(sentence)
        for i, (metric, m_start, m_end) in enumerate(metrics):
            stop = metrics[i + 1][1] if i + 1 < len(metrics) else len(sentence)
            segment = sentence[m_end:stop]
            value = low = high = tolerance = o_number = None
            if metric in PERCENT_METRICS:
                amount = PERCENT.search(segment)
                if not amount:
                    continue
                number, scale, unit = amount.group("num"), 0, "PERCENT"
            else:
                amount = MONEY.search(segment)
                if not amount:
                    continue
                number, scale, unit = money_parts(amount)
            end = m_end + amount.end()
            between = re.search(r"\bbetween\s*$", segment[:amount.start()], re.I)
            second = re.match(r"\s+(?:and|to)\s+", segment[amount.end():]) if between else None
            if second:
                other = MONEY.match(segment, amount.end() + second.end()) if unit != "PERCENT" else \
                    PERCENT.match(segment, amount.end() + second.end())
                if other:
                    o_number, o_scale, o_unit = (money_parts(other) if unit != "PERCENT"
                                                 else (other.group("num"), 0, "PERCENT"))
                    scale = max(scale, o_scale) if scale == 0 or o_scale == 0 else scale
                    if o_unit == unit and (o_scale in (0, scale)):
                        low, high = parse_number(number), parse_number(o_number)
                        end = m_end + other.end()
            if low is None:
                value = parse_number(number)
                tol = TOLERANCE.match(sentence[end:])
                if tol:
                    tolerance = parse_number(tol.group("num"))
                    end += tol.end()
            written = [number] + ([o_number] if low is not None else [])
            precision = scale - max(decimals_of(w) for w in written)
            prefix = sentence[:m_end + amount.end()]
            kind = "GUIDANCE" if GUIDANCE_WORDS.search(prefix) else "REPORTED"
            direction = None
            if kind == "GUIDANCE":
                direction = next((name for name, rx in DIRECTION if rx.search(prefix)), None)
            before = [p for p in periods if p[1] < m_end + amount.start()]
            period = (before[-1] if before else (periods[0] if periods else None))
            facts.append({
                "kind": kind, "metric": metric, "period": period[0] if period else None,
                "value": None if value is None else frac(value),
                "range": None if low is None else [frac(low), frac(high)],
                "tolerance_pct": None if tolerance is None else frac(tolerance),
                "unit": unit, "scale_exp10": scale, "precision_exp10": precision, "direction": direction,
                "security_scope": _scope(metric, unit, entry),
                "span": _span(doc_sha, text, base + m_start, base + end),
                "period_span": None if period is None else _span(doc_sha, text, base + period[1], base + period[2]),
                "scale_span": None, "basis": "SENTENCE_V1"})
    return facts


def _lines(text: str) -> list:
    lines, offset = [], 0
    for line in text.split("\n"):
        lines.append((offset, line))
        offset += len(line) + 1
    return lines


def table_blocks(text: str) -> list:
    """Contiguous " | " line blocks with what the extractor reads around them.

    Each block has its rows, kind (from the title line above it), scale and the offsets of the
    whole line stating it (e.g. "(In billions of Korean won)"), whether that line exempts
    per-share amounts from the scale, the currency context and the period header cells.
    """
    lines, blocks, i = _lines(text), [], 0
    while i < len(lines):
        if " | " not in lines[i][1]:
            i += 1
            continue
        start = i
        while i < len(lines) and " | " in lines[i][1]:
            i += 1
        rows = lines[start:i]
        preamble = [ln for ln in lines[max(0, start - 3):start] if ln[1].strip()]
        title = preamble[-1][1] if preamble else ""
        scale_line = next(((o, ln, m) for o, ln in preamble + rows for m in [TABLE_SCALE.search(ln)] if m), None)
        context = " ".join(ln for _, ln in preamble + rows)
        header = None
        for off, line in rows:
            cells = _cells(line)
            if not METRIC_RE.match(cells[0][0]) and any(parse_period(c) for c, _ in cells):
                header = [h for h in ((parse_period(c), off + s, off + s + len(c)) for c, s in cells) if h[0]]
                break
        blocks.append({
            "rows": rows, "kind": "GUIDANCE" if GUIDANCE_WORDS.search(title) else "REPORTED",
            "scale": SCALES[scale_line[2].group(1).lower()] if scale_line else 0,
            "scale_span": None if not scale_line else (scale_line[0], scale_line[0] + len(scale_line[1])),
            "per_share_exception": bool(scale_line and PER_SHARE_EXCEPTION.search(scale_line[1])),
            "usd": "$" in context, "krw": bool(re.search(r"korean\s+won|\bKRW\b|\u20a9", context, re.I)),
            "header": header})
    return blocks


def row_metric(label: str) -> str | None:
    return next((name for name in METRIC_NAMES if METRIC_ONE[name].fullmatch(label.strip(" :")) or
                 (METRIC_ONE[name].match(label) and len(label) <= 40)), None)


def _row_values(cells: list) -> list:
    return [(c, s) for c, s in cells[1:] if NUM_TOKEN.fullmatch(c.lstrip("$\u20a9").rstrip("%").strip())]


def table_unit(metric: str, cell: str, block: dict) -> str | None:
    if metric in PERCENT_METRICS:
        return "PERCENT"
    if "$" in cell or (block["usd"] and not block["krw"]):
        return "USD"
    return "KRW" if block["krw"] else None  # currency not stated: no unit rather than a guess


def table_scale(metric: str, unit: str, block: dict) -> int | None:
    """Scale of one cell: none for percentages; per-share rows of a scaled table only under an
    explicit exception such as "(In millions, except per share data)", otherwise unknown (None)."""
    if unit == "PERCENT":
        return 0
    if metric in PER_SHARE_METRICS:
        return 0 if block["scale"] == 0 or block["per_share_exception"] else None
    return block["scale"]


def table_cell(text: str, start: int, end: int) -> dict | None:
    """The table row holding [start, end) and the period column of the value cell ending at `end`,
    aligned exactly as the extractor aligns values to header periods; None if it is not such a cell."""
    for block in table_blocks(text):
        for off, line in block["rows"]:
            if not off <= start < end <= off + len(line):
                continue
            cells, header = _cells(line), block["header"]
            values = _row_values(cells)
            hit = [k for k, (c, s) in enumerate(values) if off + s + len(c) == end]
            if not hit or header is None or len(values) > len(header):
                return None
            return {"block": block, "label": cells[0][0], "cell": values[hit[0]][0],
                    "period": header[len(header) - len(values) + hit[0]]}
    return None


def _table_facts(text, doc_sha, entry):
    facts = []
    for block in table_blocks(text):
        header = block["header"]
        if header is None:
            continue
        scale_span = None if not block["scale_span"] else _span(doc_sha, text, *block["scale_span"])
        for off, line in block["rows"]:
            cells = _cells(line)
            metric = row_metric(cells[0][0])
            if metric is None:
                continue
            values = _row_values(cells)
            if not values or len(values) > len(header):
                continue
            for (cell, s), period in zip(values, header[-len(values):]):
                unit = table_unit(metric, cell, block)
                fact_scale = None if unit is None else table_scale(metric, unit, block)
                if fact_scale is None:
                    continue  # unstated currency, or a per-share cell whose scale the table leaves open
                token = cell.lstrip("$\u20a9").rstrip("%").strip()
                facts.append({
                    "kind": block["kind"], "metric": metric, "period": period[0], "value": frac(parse_number(token)),
                    "range": None, "tolerance_pct": None, "unit": unit, "scale_exp10": fact_scale,
                    "precision_exp10": fact_scale - decimals_of(token), "direction": None,
                    "security_scope": _scope(metric, unit, entry),
                    "span": _span(doc_sha, text, off, off + s + len(cell)),
                    "period_span": _span(doc_sha, text, period[1], period[2]),
                    "scale_span": None if unit == "PERCENT" else scale_span, "basis": "TABLE_V1"})
    return facts


def _cells(line: str) -> list:
    out, pos = [], 0
    for cell in line.split(" | "):
        out.append((cell, pos))
        pos += len(cell) + 3
    return out


def _keyword_events(text, doc_sha):
    facts = []
    for event, pattern in KEYWORD_EVENTS:
        for m in pattern.finditer(text):
            if unasserted(text, m.start(), m.end()):
                continue
            facts.append({"kind": "EVENT", "metric": event, "period": None, "value": None, "range": None,
                          "tolerance_pct": None, "unit": None, "scale_exp10": 0, "precision_exp10": 0, "direction": None,
                          "security_scope": "ISSUER", "span": _span(doc_sha, text, m.start(), m.end()),
                          "period_span": None, "scale_span": None, "basis": "KEYWORD_V1"})
            break  # one supporting span per event type per document
    return facts


def extract_document(text: str, doc_sha: str, entry, source: dict) -> list:
    raw = _sentence_facts(text, doc_sha, entry) + _table_facts(text, doc_sha, entry) + _keyword_events(text, doc_sha)
    seen, out = set(), []
    for fact in raw:
        key = (fact["kind"], fact["metric"], fact["period"], fact["unit"], str(normalized(fact)))
        if key in seen:
            continue
        seen.add(key)
        out.append(finish_fact(fact, source))
    return out


def item_events(record: dict) -> list:
    """Filer-assigned 8-K item codes, verified against the record metadata, not text."""
    source = {"record_id": record["record_id"], "accession": record["accession"], "doc_name": None,
              "available_ms": record["available_ms"], "original_ms": record["original_ms"]}
    return [finish_fact({"kind": "EVENT", "metric": f"ITEM:{item}", "period": None, "value": None, "range": None,
                         "tolerance_pct": None, "unit": None, "scale_exp10": 0, "precision_exp10": 0, "direction": None,
                         "security_scope": "ISSUER", "span": None, "period_span": None, "scale_span": None,
                         "basis": "ITEM_METADATA"}, source) for item in record["items"]]


def decimals_of(token: str) -> int:
    body = token.strip("()$\u20a9%").replace(",", "")
    return len(body.split(".")[1]) if "." in body else 0


def token_decimals(text: str, number: Fraction):
    """Decimal places of the written token in `text` equal to `number` (sign-insensitive), else None."""
    for m in NUM_TOKEN.finditer(text):
        value = parse_number(m.group(0))
        if value == number or -value == number:
            return decimals_of(m.group(0))
    return None


def half_unit(fact: dict) -> Fraction:
    """Half a unit of the last written digit, in base units: the rounding tolerance of a statement."""
    return Fraction(10) ** fact.get("precision_exp10", fact["scale_exp10"]) / 2


def values_agree(a: dict, b: dict) -> bool:
    """Two statements agree if they differ by no more than the coarser one's rounding."""
    x, y = normalized(a), normalized(b)
    if x is None or y is None or (type(x) is tuple) != (type(y) is tuple):
        return x == y
    tolerance = max(half_unit(a), half_unit(b))
    pairs = zip(x, y) if type(x) is tuple else [(x, y)]
    return all(abs(p - q) <= tolerance for p, q in pairs)


def normalized(fact: dict):
    """Exact value(s) in base units (value x 10^scale); a (low, high) pair for ranges; None for events."""
    factor = Fraction(10) ** fact["scale_exp10"]
    if fact.get("value") is not None:
        return Fraction(*fact["value"]) * factor
    if fact.get("range") is not None:
        return tuple(Fraction(*v) * factor for v in fact["range"])
    return None
