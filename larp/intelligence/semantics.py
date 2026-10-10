"""What a source sentence asserts about an event: occurrence, announcement, report, forecast or risk.

IDEA-030 R04 showed that keyword support was being taken for event entailment: a heading, a
competitor's incident, a rumour and an announced future departure were all accepted as the
issuer's occurred event. This module separates the dimensions a statement can carry, and both
the extractor (facts.py) and the verifier (verify.py) call the same function, so a claim can only
be verified with the semantics its own source text supports (IDEA-031 S2.1-S2.2).

`classify_event(text, start, end, ...)` reads the clause holding an event trigger and returns

- assertion: OCCURRED | ANNOUNCED_FUTURE | ATTRIBUTED_REPORT | FORECAST | CONDITIONAL_RISK |
  NEGATED | MENTION_ONLY. MENTION_ONLY means the text names the event without any predicate that
  asserts it happened (a heading such as "Impairment of goodwill", or a list item).
- actor: ISSUER | THIRD_PARTY | UNSPECIFIED, from the subject/possessor of the occurrence
  predicate and the trigger's own complement ("an incident at one of our suppliers").
- attribution: SOURCE_ASSERTS | ATTRIBUTED_TO_OTHERS | QUOTED_THIRD_PARTY | QUOTED_ISSUER.
- temporal: CURRENT | HISTORICAL | FUTURE | UNKNOWN, relative to the document date.
- effective: ISO date of an explicitly stated effective date, if any.

The rules are structural (predicate present, who governs it, attribution frame, negation scope
within the conjunct that holds the trigger, quotation, dates relative to the document) rather
than a longer list of modal words. They are deterministic and conservative: a statement is an
issuer occurrence only when every dimension says so. They are not a validated parser of real
filings; real-text error rates are IDEA-030 T01 work (NOT RUN without independent labels).

`classify_source_statement` reads regulator/agency releases (SEC, DOJ, Federal Register, EC):
what the authority did (proposed vs final rule, complaint/charge = allegation, settlement,
penalty, entity-list action) and which eligible issuers the same source names. Source authority
verifies that the authority said or did it; it does not make an allegation true or establish
price direction.
"""

from datetime import date, datetime, timezone
import re

ASSERTIONS = ("OCCURRED", "ANNOUNCED_FUTURE", "ATTRIBUTED_REPORT", "FORECAST", "CONDITIONAL_RISK", "NEGATED",
              "MENTION_ONLY")
ACTORS = ("ISSUER", "THIRD_PARTY", "UNSPECIFIED")
TEMPORAL = ("CURRENT", "HISTORICAL", "FUTURE", "UNKNOWN")
SEMANTICS_VERSION = "EventSemantics.v2"

NEGATION = re.compile(r"\b(?:no|not|none|neither|nor|never|without|cannot|absence\s+of|unnecessary)\b|n't\b", re.I)
# Phrases containing a cue word that is not a cue: deadlines, the non-reliance event phrase, the month, list idioms.
NOT_A_CUE = re.compile(r"\b(?:no|not)\s+later\s+than\b|\bshould\s+no\s+longer\s+be\s+relied\s+upon\b|"
                       r"\b(?-i:May)\s+(?:\d{1,2}|\d{4})\b|\bbut\s+not\s+limited\s+to\b|\bwithout\s+limitation\b|"
                       r"\bnot\s+only\b", re.I)
ATTRIBUTION = re.compile(
    r"\b(?:rumou?r(?:s|ed)?|reportedly|allegedly|alleg(?:e|es|ed|ing|ation|ations)|according\s+to|"
    r"sources?\s+(?:said|say|says|familiar|close)|people\s+(?:familiar|close)|(?:is|are|was|were)\s+said\s+to|"
    r"speculat\w*|unconfirmed|purported(?:ly)?|press\s+reports?|media\s+reports?|claim(?:s|ed)?\s+that)\b", re.I)
CONDITIONAL = re.compile(r"\b(?:may|might|could|would|should|can|if|unless|whether|possible|possibly|potential|"
                         r"potentially|risks?|susceptible|vulnerable|in\s+the\s+event|any\s+future|"
                         r"there\s+can\s+be\s+no\s+assurance)\b", re.I)
FORECAST = re.compile(r"\b(?:expects?|expected|expecting|anticipates?|anticipated|projects?|projected|forecasts?|"
                      r"estimates?|likely|unlikely|intends?\s+to|plans?\s+to|future|will|outlook)\b", re.I)
ANNOUNCE = re.compile(r"\b(?:announc(?:e|es|ed|ing)|notif(?:y|ies|ied)|inform(?:s|ed)|advis(?:es|ed)|"
                      r"tender(?:s|ed)|submit(?:s|ted)|disclos(?:es|ed))\b", re.I)
DECISION = re.compile(r"\b(?:decision|intention|intent|plans?|agreed|will)\s+to\b|\bwill\s+(?:resign|retire|step|"
                      r"depart|leave|be\s+delisted|restate)\b", re.I)
REPORT_VERB = re.compile(r"\b(?:reported|disclosed|announced|said|stated|confirmed)\b", re.I)

# Occurrence predicates per event: a past/perfect verb (or event-specific frame) asserting that the event happened.
_GENERIC_PAST = r"\b(?:recorded|recognized|recognised|incurred|took|booked|reported|identified|detected|" \
                r"discovered|experienced|suffered|determined|concluded|became\s+aware|occurred|announced|disclosed)\b"
OCCURRENCE = {
    "IMPAIRMENT": re.compile(_GENERIC_PAST + r"|\bwr(?:ote|itten)\s+down\b|\b(?:was|were|is|are|been)\s+impaired\b|"
                             r"\bimpairment\s+(?:charges?|loss(?:es)?)\s+(?:of|totall?ing|amounting|was|were)\b", re.I),
    "CYBERSECURITY_INCIDENT": re.compile(_GENERIC_PAST + r"|\b(?:affect(?:ed|ing)|compromised|breached|"
                                         r"(?:was|were)\s+(?:the\s+)?(?:target|subject|victim))\b|\bis\s+investigating\b",
                                         re.I),
    "RESTATEMENT": re.compile(_GENERIC_PAST + r"|\brestated\b|\brestating\b|\bwill\s+restate\b|"
                              r"\bshould\s+no\s+longer\s+be\s+relied\s+upon\b|\bnon-?reliance\b", re.I),
    "DELISTING": re.compile(_GENERIC_PAST + r"|\b(?:was|were|been)\s+(?:delisted|suspended)\b|\bdelisted\b|"
                            r"\breceived\s+(?:a\s+)?(?:notice|notification|letter|determination)\b|\bfiled\s+(?:a\s+)?Form\s+25\b",
                            re.I),
    "OFFICER_DEPARTURE": re.compile(r"\b(?:resigned|stepped\s+down|departed|left|retired|terminated|was\s+removed|"
                                    r"accepted|resignation\s+(?:was|became|is)\s+effective)\b|" + _GENERIC_PAST, re.I),
}
# A generic present-tense passive ("an impairment loss is recognized when ...") describes a policy or process, not
# an occurrence.
GENERIC_PRESENT = re.compile(r"\b(?:is|are)\s+(?:\w+ly\s+)?(?:recorded|recognized|recognised|detected|identified|"
                             r"reported|discovered|determined|incurred|booked|disclosed)\b", re.I)
GENERIC_FRAME = re.compile(r"\b(?:when|whenever|once|if\s+and\s+when|in\s+which|in\s+the\s+case\s+of)\b", re.I)
# Scenario, exercise and counterfactual frames assert no occurrence even without a modal verb.
SCENARIO = re.compile(r"\b(?:scenarios?|simulat\w*|tabletop|drills?|exercises?|hypothetical\w*|assum(?:e|es|ed|ing)|"
                      r"suppose|supposing|were\s+to|had\s+we|stress[\s-]+tests?)\b", re.I)
TOC = re.compile(r"\.{4,}\s*\d+\s*$|\btable\s+of\s+contents\b", re.I)
FUTURE_MARK = re.compile(r"\b(?:upcoming|planned|pending|forthcoming|impending|anticipated\s+departure)\b", re.I)
# A clause with no finite verb at all is a heading or list label.
FINITE = re.compile(r"\b(?:is|are|was|were|be|been|being|has|have|had|do|does|did|will|shall|would|could|may|"
                    r"might|must|can|should)\b|\b\w+(?:ed|es)\b", re.I)

THIRD_PARTY = re.compile(
    r"\b(?:competitors?|rivals?|peers?|customers?|suppliers?|vendors?|partners?|counterpart(?:y|ies)|"
    r"third[\s-]+part(?:y|ies)|another\s+company|other\s+companies|an?\s+(?:\w+[\s-])?based\s+company|"
    r"analysts?|investors?|short\s+sellers?|industry|(?:an?|the)\s+(?:former\s+)?employee\s+of\s+another|"
    r"the\s+market|media|newspapers?|reporters?|journalists?)\b", re.I)
ISSUER = re.compile(r"\b(?:we|our|us|the\s+company|the\s+registrant|the\s+issuer|the\s+board|"
                    r"the\s+audit\s+committee|management|(?:its|our|the)\s+(?:chief\s+\w+\s+officer|CEO|CFO|"
                    r"president|chair(?:man|woman|person)?|director))\b", re.I)
# A named company other than the issuer: a corporate suffix, or a capitalised possessive ("Acme's").
NAMED = re.compile(r"\b(?:[A-Z][\w&.-]*\s+){0,3}(?:Corp(?:oration)?|Inc|Ltd|LLC|plc|Holdings|Group)\b\.?|"
                   r"\b[A-Z][A-Za-z&.-]+['’]s\b")
NOT_NAMED = re.compile(r"^(?:The\s+)?(?:Company|Registrant|Board|Corporation|Issuer)['’]s$", re.I)
PREPOSITION_BEFORE = re.compile(r"\b(?:to|of|for|with|by|from|at|about|regarding|against|than)\s+$", re.I)
BY_AGENT = re.compile(r"^\s*by\s+(?P<agent>[^,.;:\n]{1,80})", re.I)
OBJECT = re.compile(r"^\s*(?P<obj>(?:the\s+|our\s+|its\s+|an?\s+|one\s+of\s+our\s+)?(?:\w+\s+){0,2}\w+)", re.I)
OFFICER = re.compile(r"\b(?:chief\s+executive|chief\s+financial|CEO|CFO|president|chair(?:man|woman|person)?)\b", re.I)
COMPLEMENT_THIRD = re.compile(
    r"^\s*(?:at|of|involving|affecting|on|reported\s+by|disclosed\s+by|experienced\s+by)\s+(?:one\s+of\s+our\s+|"
    r"a\s+|an\s+|the\s+|our\s+|its\s+|certain\s+)?(?:\w+\s+)?(?:suppliers?|vendors?|customers?|competitors?|partners?|"
    r"third[\s-]+part\w+|peers?)\b", re.I)
CONJUNCT = re.compile(r"(?:,\s*|\s+)(?:and|but|while|whereas)\s+(?=(?:we|it|they|the|our|its|he|she|did|does|do|has|"
                      r"have|had|was|were|is|are|will|no|not|never|\w+ed)\b)", re.I)
# Non-restrictive relative clauses and leading concessive clauses: their negation, years and modality do not scope
# over the main predicate ("we recorded an impairment, which did not affect liquidity").
RELATIVE = re.compile(r",\s*(?:which|who|whom|whose|where)\b[^,;]*(?:,|$)", re.I)
CONCESSIVE = re.compile(r"^\s*(?:although|though|even\s+though|while|whereas|despite)\b[^,]*,", re.I)
QUOTE_PAIRS = (("\"", "\""), ("“", "”"), ("‘", "’"))
SPEAKER = re.compile(r"(?:said|says|stated|according\s+to|told|:)\s*(?P<who>[^.;\n]{1,120})", re.I)
HISTORICAL_MARK = re.compile(r"\bpreviously\s+(?:restated|recorded|recognized|reported|disclosed|experienced|"
                             r"identified|delisted)\b|\bin\s+(?:prior|previous|past)\s+(?:years|periods|quarters)\b|"
                             r"\bhistorically\b|\bin\s+the\s+past\b|\b(?:in\s+)?the\s+prior[\s-]+year(?:\s+period)?\b|"
                             r"\bprior[\s-]+year\s+period\b|\blast\s+year\b|\ba\s+year\s+ago\b|\byear[\s-]+ago\b|"
                             r"\bthe\s+previous\s+year\b", re.I)
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"), 1)}
EFFECTIVE = re.compile(r"\beffective\s+(?:as\s+of\s+)?(?:the\s+(?:close|end|opening)\s+of\s+business\s+)?"
                       r"(?:on\s+|no\s+later\s+than\s+)?(?P<month>January|February|March|April|May|June|July|August|"
                       r"September|October|November|December)\s+(?P<day>\d{1,2})(?:,\s*(?P<year>\d{4}))?", re.I)
CLAUSE_BREAK = re.compile(r"\n|;|(?<=[.!?])\s+(?=[A-Z(\"'“‘])|"
                          r"(?i:,\s+(?:but|whereas|while|although|though|however|yet)\b)")


def clause_bounds(text: str, start: int, end: int) -> tuple:
    """(lo, hi) of the clause holding text[start:end]: a line or sentence, split at ';' and contrastive joins."""
    lo, hi = text.rfind("\n", 0, start) + 1, len(text)
    for m in CLAUSE_BREAK.finditer(text, lo):
        if m.end() <= start:
            lo = m.end()
        elif m.start() >= end:
            hi = m.start()
            break
    return lo, hi


def _conjunct(clause: str, start: int, end: int) -> tuple:
    """Bounds, within `clause`, of the coordinated conjunct holding [start, end): negation and modality are read
    there, so "recorded an impairment and did not record a restructuring charge" keeps the impairment."""
    lo, hi = 0, len(clause)
    for m in CONJUNCT.finditer(clause):
        if m.end() <= start:
            lo = m.end()
        elif m.start() >= end:
            hi = m.start()
            break
    concessive = CONCESSIVE.match(clause, lo)
    if concessive and concessive.end() <= start:
        lo = concessive.end()
    return lo, hi


def _blank(text: str, spans) -> str:
    out = list(text)
    for lo, hi in spans:
        out[lo:hi] = " " * (hi - lo)
    return "".join(out)


def _relatives(segment: str, t_lo: int, t_hi: int) -> tuple:
    """(segment with non-restrictive relative clauses blanked, the relative clause holding the trigger or None)."""
    holding, blanked = None, []
    for m in RELATIVE.finditer(segment):
        if m.start() <= t_lo and t_hi <= m.end():
            holding = (m.start(), m.end())
        else:
            blanked.append((m.start(), m.end()))
    return _blank(segment, blanked), holding


def _quote(text: str, position: int):
    """(open, close) offsets of the quotation holding `position`, or None. Straight or typographic quotes."""
    for left, right in QUOTE_PAIRS:
        if left == right:
            positions = [i for i, c in enumerate(text) if c == left]
            for a, b in zip(positions[::2], positions[1::2]):
                if a < position < b:
                    return a, b
        else:
            depth_open = text.rfind(left, 0, position)
            if depth_open >= 0:
                close = text.find(right, position)
                between = text.rfind(right, depth_open, position)
                if close > position and between < 0:
                    return depth_open, close
    return None


def _doc_date(document_ms):
    if type(document_ms) is not int:
        return None
    return datetime.fromtimestamp(document_ms / 1000, timezone.utc).date()


def effective_date(segment: str, document_ms=None, *, roll_forward: bool = True):
    """ISO date of an explicit effective date; the year defaults to the document's year. A month/day earlier than
    the document date rolls into the next year only for a forward-looking statement (`roll_forward`)."""
    m = EFFECTIVE.search(segment)
    if not m:
        return None
    doc = _doc_date(document_ms)
    year = int(m.group("year")) if m.group("year") else (doc.year if doc else None)
    if year is None:
        return None
    try:
        value = date(year, MONTHS[m.group("month").lower()], int(m.group("day")))
    except ValueError:
        return None
    if not m.group("year") and doc and value < doc and roll_forward:
        value = date(year + 1, value.month, value.day)  # "will resign effective January 5" stated in December
    return value.isoformat()


def _mentions(region: str, issuer_names: tuple) -> list:
    """(position, actor, text) actor mentions in `region`; issuer words inside a prepositional phrase are not actors
    ("a supplier to the company", "one of our suppliers")."""
    out = [(m.start(), "THIRD_PARTY", m.group(0)) for m in THIRD_PARTY.finditer(region)]
    for m in ISSUER.finditer(region):
        if not PREPOSITION_BEFORE.search(region[max(0, m.start() - 14):m.start()]):
            out.append((m.start(), "ISSUER", m.group(0)))
    names = [n for n in issuer_names if n]
    for m in NAMED.finditer(region):
        text = m.group(0).strip()
        if NOT_NAMED.match(text) or any(n.lower() in text.lower() or text.lower().rstrip("'’s") in n.lower()
                                        for n in names):
            continue
        out.append((m.start(), "THIRD_PARTY", text))
    for name in names:
        for m in re.finditer(re.escape(name), region, re.I):
            out.append((m.start(), "ISSUER", m.group(0)))
    return out


def _actor(segment: str, t_lo: int, t_hi: int, pred, issuer_names: tuple, issuer_source: bool, verb_trigger: bool):
    """Who the event happened to: the trigger's complement, a by-agent, the object of a verb trigger, else the
    mention nearest before the predicate (subject or possessor)."""
    after_trigger = segment[t_hi:]
    if COMPLEMENT_THIRD.match(after_trigger):
        return "THIRD_PARTY", COMPLEMENT_THIRD.match(after_trigger).group(0).strip()
    pred_end = pred.end() if pred is not None else t_hi
    agent = BY_AGENT.match(segment[max(pred_end, t_hi):])
    if agent:
        found = _mentions(agent.group("agent"), issuer_names)
        if found:  # the head of the agent phrase is its last mention: "by our largest customer" -> customer
            _, who, what = max(found)
            return who, what
    if verb_trigger and pred is not None:
        obj = OBJECT.match(segment[pred.end():])
        if obj:
            found = _mentions(obj.group("obj"), issuer_names)
            if found and max(found)[1] == "THIRD_PARTY":  # "delisted our competitor": the object's head noun
                return "THIRD_PARTY", max(found)[2]
    anchor = pred.start() if pred is not None else t_lo
    found = [m for m in _mentions(segment[:anchor], issuer_names)]
    if pred is not None and pred.start() > t_hi:  # "a cybersecurity incident at X occurred": include the trigger
        found += [(t_lo + p, w, x) for p, w, x in _mentions(segment[t_lo:pred.start()], issuer_names)
                  if (t_lo + p, w, x) not in found]
    if found:  # the mention nearest the predicate governs: "our competitor" -> competitor;
        _, who, what = max(found)  # "after a competitor's report, we identified" -> we
        return who, what
    if issuer_source:
        return "ISSUER", "issuer's own filing (no other actor named)"
    return "UNSPECIFIED", None


def classify_event(text: str, start: int, end: int, *, event: str, document_ms=None, issuer_names: tuple = (),
                   issuer_source: bool = True) -> dict:
    """Semantics of the event trigger at text[start:end] (see module docstring). Deterministic.

    `issuer_source`: the text is the issuer's own disclosure (an EDGAR filing), so an occurrence with no other
    actor named is the issuer's. For third-party sources (news, regulators) such an actor is UNSPECIFIED.
    """
    lo, hi = clause_bounds(text, start, end)
    raw_clause = text[lo:hi]
    clause = NOT_A_CUE.sub(lambda m: " " * len(m.group(0)), raw_clause)
    t_lo, t_hi = start - lo, end - lo
    cues, attribution = [], "SOURCE_ASSERTS"
    quote = _quote(raw_clause, t_lo)
    speaker_actor = None
    if quote is not None:
        tail = raw_clause[quote[1]:]
        head = raw_clause[:quote[0]]
        speaker = SPEAKER.search(tail).group("who") if SPEAKER.search(tail) else head  # "X said: '...'"
        found = _mentions(speaker, issuer_names)
        is_issuer = bool(found) and max(found)[1] == "ISSUER" and not any(f[1] == "THIRD_PARTY" for f in found)
        attribution = "QUOTED_ISSUER" if is_issuer else "QUOTED_THIRD_PARTY"
        speaker_actor = "ISSUER" if is_issuer else "THIRD_PARTY"
        cues.append("QUOTED")
        # Read the quoted statement on its own terms (its subject is the speaker's "we").
        clause = _blank(clause, [(0, quote[0] + 1), (quote[1], len(clause))])
        raw_view = _blank(raw_clause, [(0, quote[0] + 1), (quote[1], len(raw_clause))])
    else:
        raw_view = raw_clause
    c_lo, c_hi = _conjunct(clause, t_lo, t_hi)
    segment, raw_segment = clause[c_lo:c_hi], raw_view[c_lo:c_hi]
    t_lo, t_hi = t_lo - c_lo, t_hi - c_lo
    segment, holding = _relatives(segment, t_lo, t_hi)
    raw_segment, _ = _relatives(raw_segment, t_lo, t_hi)
    antecedent = None
    if holding is not None:  # the event is inside "X, who resigned as CEO of Acme Corp,": read that clause
        antecedent = raw_segment[:holding[0]]
        segment = _blank(segment, [(0, holding[0]), (holding[1], len(segment))])
        raw_segment = _blank(raw_segment, [(0, holding[0]), (holding[1], len(raw_segment))])
        cues.append("RELATIVE_CLAUSE")
    predicate = OCCURRENCE.get(event)
    pred = None
    if predicate is not None:
        found = [m for m in predicate.finditer(raw_segment)]
        inside = [m for m in found if t_lo <= m.start() < t_hi]
        pred = inside[0] if inside else (min(found, key=lambda m: abs(m.start() - t_lo)) if found else None)
    verb_trigger = pred is not None and t_lo <= pred.start() < t_hi
    future = bool(DECISION.search(segment) or FUTURE_MARK.search(segment))
    effective = effective_date(raw_segment, document_ms, roll_forward=future or pred is None)
    doc = _doc_date(document_ms)
    actor, actor_text = _actor(raw_segment, t_lo, t_hi, pred, issuer_names, issuer_source, verb_trigger)
    if antecedent is not None and actor == "ISSUER" and actor_text.startswith("issuer's own filing"):
        found = _mentions(antecedent, issuer_names)
        actor, actor_text = (max(found)[1], max(found)[2]) if found else ("UNSPECIFIED", "relative clause antecedent")
    if speaker_actor == "THIRD_PARTY":
        actor, actor_text = "THIRD_PARTY", "quoted speaker"

    if TOC.search(raw_clause):
        assertion = "MENTION_ONLY"
        cues.append("TABLE_OF_CONTENTS")
    elif NEGATION.search(segment):
        assertion = "NEGATED"
        cues.append("NEGATION_IN_CONJUNCT")
    elif ATTRIBUTION.search(clause):
        assertion = "ATTRIBUTED_REPORT"
        attribution = "ATTRIBUTED_TO_OTHERS"
        cues.append("ATTRIBUTION_FRAME")
    elif CONDITIONAL.search(segment) or SCENARIO.search(segment):
        assertion = "CONDITIONAL_RISK"
        cues.append("CONDITIONAL" if CONDITIONAL.search(segment) else "SCENARIO")
    elif (ANNOUNCE.search(segment) or future or effective) and \
            (future or (effective and doc is not None and effective > doc.isoformat())
             or (effective and doc is None and ANNOUNCE.search(segment))):
        assertion = "ANNOUNCED_FUTURE"
        cues.append("ANNOUNCEMENT_OF_FUTURE_EVENT")
    elif FORECAST.search(segment):
        assertion = "FORECAST"
        cues.append("FORWARD_LOOKING")
    elif pred is not None and (GENERIC_PRESENT.search(raw_segment[max(0, pred.start() - 20):pred.end()])
                               or (GENERIC_FRAME.search(segment) and GENERIC_PRESENT.search(raw_segment))):
        assertion = "MENTION_ONLY"
        cues.append("GENERIC_PRESENT_TENSE")
    elif pred is None or not FINITE.search(segment):
        assertion = "MENTION_ONLY"
        cues.append("NO_OCCURRENCE_PREDICATE")
    else:
        assertion = "OCCURRED"
    if attribution == "QUOTED_THIRD_PARTY" and assertion == "OCCURRED":
        assertion = "ATTRIBUTED_REPORT"

    temporal = "UNKNOWN"
    if assertion in ("ANNOUNCED_FUTURE", "FORECAST"):
        temporal = "FUTURE"
    elif assertion == "OCCURRED":
        years = [int(y) for y in YEAR.findall(raw_segment)]
        historical = HISTORICAL_MARK.search(raw_segment) or (doc is not None and years and max(years) < doc.year - 1)
        temporal = "HISTORICAL" if historical else "CURRENT"
    return {"schema": SEMANTICS_VERSION, "event": event, "assertion": assertion, "actor": actor,
            "actor_text": actor_text, "attribution": attribution, "temporal": temporal, "effective": effective,
            "cues": sorted(set(cues))}


def finding_eligible(semantics: dict) -> bool:
    """Only the issuer's own, current, occurred event may become a configured finding."""
    return (semantics.get("assertion") == "OCCURRED" and semantics.get("actor") == "ISSUER"
            and semantics.get("temporal") == "CURRENT")


# ------------------------------------------------------------------ regulator / agency releases
REGULATORY_ACTIONS = (
    ("PROPOSED_RULE", re.compile(r"\bpropos(?:e|es|ed|ing|al|als)\b|\bnotice\s+of\s+proposed\s+rulemaking\b", re.I)),
    ("INTERIM_FINAL_RULE", re.compile(r"\binterim\s+final\s+rule\b", re.I)),
    ("FINAL_RULE", re.compile(r"\bfinal\s+rule\b|\badopt(?:s|ed)\s+(?:final\s+)?(?:rules?|amendments)\b", re.I)),
    ("ENTITY_LIST_ACTION", re.compile(r"\bentity\s+list\b", re.I)),
    ("COMPLAINT_OR_CHARGE", re.compile(r"\b(?:filed\s+(?:a\s+)?(?:civil\s+)?(?:complaint|lawsuit|suit)|charged|"
                                       r"charges|indicted|indictment|sued|alleg\w+)\b", re.I)),
    ("SETTLEMENT", re.compile(r"\bsettle(?:d|s|ment)\b|\bconsent\s+(?:decree|order)\b|\bagreed\s+to\s+pay\b", re.I)),
    ("PENALTY_OR_ORDER", re.compile(r"\b(?:fined?|penalt(?:y|ies)|ordered\s+to|cease[\s-]and[\s-]desist|"
                                    r"suspend(?:s|ed)?\s+trading|trading\s+suspension)\b", re.I)),
    ("INVESTIGATION", re.compile(r"\b(?:opens?|opened|launch(?:es|ed))\s+(?:an?\s+)?(?:formal\s+)?"
                                 r"(?:investigation|in-depth\s+investigation|probe|inquiry)\b", re.I)),
    ("DECISION", re.compile(r"\b(?:decision|decides?|decided|approves?|approved|prohibits?|prohibited|"
                            r"clears?|cleared|accepts?\s+commitments)\b", re.I)),
)
DEVELOPMENT = re.compile(r"\b(?:developed|unveil(?:s|ed)|launch(?:es|ed)|introduc(?:es|ed)|announc(?:es|ed))\b"
                         r"[^.\n]{0,120}?\b(?:chip|processor|accelerator|GPU|memory|HBM|model|technology|"
                         r"product|node|fab)\b", re.I)
CERTAINTY = {"PROPOSED_RULE": "PROPOSAL_NOT_EFFECTIVE", "INTERIM_FINAL_RULE": "AGENCY_ACTION_TAKEN",
             "FINAL_RULE": "AGENCY_ACTION_TAKEN", "ENTITY_LIST_ACTION": "AGENCY_ACTION_TAKEN",
             "COMPLAINT_OR_CHARGE": "ALLEGATION_NOT_FINDING", "SETTLEMENT": "AGENCY_ACTION_TAKEN",
             "PENALTY_OR_ORDER": "AGENCY_ACTION_TAKEN", "INVESTIGATION": "INVESTIGATION_NOT_FINDING",
             "DECISION": "AGENCY_ACTION_TAKEN"}


def name_mentions(text: str, aliases: dict) -> list:
    """Eligible issuers named in `text`: {issuer_id: [aliases]} -> sorted issuer IDs whose alias appears as a word."""
    found = []
    for issuer_id, names in sorted(aliases.items()):
        for name in names:
            if name and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I):
                found.append(issuer_id)
                break
    return found


def classify_source_statement(text: str, *, source_kind: str, actor: str, aliases: dict) -> dict:
    """What a regulator/agency release (or attributed development report) establishes.

    `actor`: the publishing authority (e.g. "SEC", "DOJ", "BIS", "European Commission"). `aliases`: eligible
    issuer aliases. Relations are only the issuers this same source names (MENTIONED_IN_SOURCE) with effect
    UNKNOWN; nothing is inferred about competitors, suppliers or price direction.
    """
    actions = [name for name, rx in REGULATORY_ACTIONS if rx.search(text)]
    # A proposed rule is never effective; "final rule" wins over a generic "propose" only when both are present.
    if "INTERIM_FINAL_RULE" in actions and "FINAL_RULE" in actions:
        actions.remove("FINAL_RULE")
    if "PROPOSED_RULE" in actions:  # "proposed amendments to the final rule adopted in 2024": still a proposal
        actions = [a for a in actions if a not in ("FINAL_RULE", "INTERIM_FINAL_RULE")]
    statement_type = "REGULATORY_ACTION" if source_kind == "AGENCY" and actions else (
        "DEVELOPMENT_CLAIM" if DEVELOPMENT.search(text) else "OTHER_STATEMENT")
    certainty = sorted({CERTAINTY[a] for a in actions}) if statement_type == "REGULATORY_ACTION" else (
        ["ATTRIBUTED_TO_ANNOUNCER"] if statement_type == "DEVELOPMENT_CLAIM" else ["SOURCE_STATES"])
    relations = [{"issuer_id": i, "relation": "MENTIONED_IN_SOURCE", "effect": "UNKNOWN",
                  "basis": "name appears in this source text"} for i in name_mentions(text, aliases)]
    return {"schema": "SourceStatement.v1", "statement_type": statement_type, "actor": actor,
            "actions": actions, "certainty": certainty, "issuer_relations": relations,
            "note": "verifies what the source said or did; not truth of allegations, not price direction"}
