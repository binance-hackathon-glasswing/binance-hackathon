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
SEMANTICS_VERSION = "EventSemantics.v1"

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

# Occurrence predicates per event: a verb (or event-specific frame) asserting that the event happened.
_GENERIC_PAST = r"(?:recorded|recognized|recognised|incurred|took|booked|reported|identified|detected|" \
                r"discovered|experienced|suffered|determined|concluded|became\s+aware|occurred|announced|disclosed)"
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
                                    r"resignation\s+(?:was|became|is)\s+effective)\b" + "|" + _GENERIC_PAST, re.I),
}
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
OFFICER = re.compile(r"\b(?:chief\s+executive|chief\s+financial|CEO|CFO|president|chair(?:man|woman|person)?)\b", re.I)
COMPLEMENT_THIRD = re.compile(
    r"^\s*(?:at|of|involving|affecting|on|reported\s+by|disclosed\s+by|experienced\s+by)\s+(?:one\s+of\s+our\s+|"
    r"a\s+|an\s+|the\s+|our\s+|its\s+|certain\s+)?(?:\w+\s+)?(?:suppliers?|vendors?|customers?|competitors?|partners?|"
    r"third[\s-]+part\w+|peers?)\b", re.I)
CONJUNCT = re.compile(r"(?:,\s*|\s+)(?:and|but|while|whereas)\s+(?=(?:we|it|they|the|our|its|he|she|did|does|do|has|"
                      r"have|had|was|were|is|are|will|no|not|never|\w+ed)\b)", re.I)
QUOTE_CHARS = "\"“”"
SPEAKER = re.compile(r"(?:said|says|stated|according\s+to|told)\s+(?P<who>[^.,;\n]{1,60})", re.I)
HISTORICAL_MARK = re.compile(r"\bpreviously\s+(?:restated|recorded|recognized|reported|disclosed|experienced|"
                             r"identified|delisted)\b|\bin\s+(?:prior|previous|past)\s+(?:years|periods|quarters)\b|"
                             r"\bhistorically\b|\bin\s+the\s+past\b", re.I)
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"), 1)}
EFFECTIVE = re.compile(r"\beffective\s+(?:as\s+of\s+|on\s+)?(?P<month>January|February|March|April|May|June|July|August|"
                       r"September|October|November|December)\s+(?P<day>\d{1,2})(?:,\s*(?P<year>\d{4}))?", re.I)
CLAUSE_BREAK = re.compile(r"\n|;|(?<=[.!?])\s+(?=[A-Z(\"'“])|"
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
    return lo, hi


def _quoted(clause: str, position: int) -> bool:
    count = sum(1 for c in clause[:position] if c in QUOTE_CHARS)
    return count % 2 == 1


def _doc_date(document_ms):
    if type(document_ms) is not int:
        return None
    return datetime.fromtimestamp(document_ms / 1000, timezone.utc).date()


def effective_date(segment: str, document_ms=None):
    """ISO date of an explicit "effective <Month> <day>[, <year>]"; the year defaults to the document's year."""
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
    if not m.group("year") and doc and value < doc:
        value = date(year + 1, value.month, value.day)  # "effective January 5" stated in December
    return value.isoformat()


def _actor(segment: str, trigger_lo: int, trigger_hi: int, predicate, issuer_names: tuple, issuer_source: bool):
    """Subject/possessor of the predicate, or the trigger's own complement."""
    if COMPLEMENT_THIRD.match(segment[trigger_hi:]):
        return "THIRD_PARTY", COMPLEMENT_THIRD.match(segment[trigger_hi:]).group(0).strip()
    anchor = min(trigger_lo, predicate.start()) if predicate is not None else trigger_lo
    subject = segment[:anchor]
    if predicate is not None and predicate.start() > trigger_hi:
        subject = segment[:predicate.start()]  # "a cybersecurity incident at X occurred": subject includes trigger
    names = [n for n in issuer_names if n]
    mentions = [(m.start(), "THIRD_PARTY", m.group(0)) for m in THIRD_PARTY.finditer(subject)]
    mentions += [(m.start(), "ISSUER", m.group(0)) for m in ISSUER.finditer(subject)]
    for name in names:
        for m in re.finditer(re.escape(name), subject, re.I):
            mentions.append((m.start(), "ISSUER", m.group(0)))
    if mentions:  # the mention nearest the predicate governs: "our competitor" -> competitor; "after a
        _, who, what = max(mentions)  # competitor's report, we identified" -> we
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
    clause = NOT_A_CUE.sub(lambda m: " " * len(m.group(0)), text[lo:hi])
    raw_clause = text[lo:hi]
    t_lo, t_hi = start - lo, end - lo
    c_lo, c_hi = _conjunct(clause, t_lo, t_hi)
    segment, raw_segment = clause[c_lo:c_hi], raw_clause[c_lo:c_hi]
    t_lo, t_hi = t_lo - c_lo, t_hi - c_lo
    cues = []
    attribution = "SOURCE_ASSERTS"
    if _quoted(raw_clause, start - lo):
        who = SPEAKER.search(raw_clause[start - lo:])
        speaker = who.group("who") if who else ""
        is_issuer = bool(ISSUER.search(speaker)) or any(n and n.lower() in speaker.lower() for n in issuer_names)
        attribution = "QUOTED_ISSUER" if is_issuer else "QUOTED_THIRD_PARTY"
        cues.append("QUOTED")
    predicate = OCCURRENCE.get(event)
    # The trigger itself may be the predicate ("resigned", "restated", "delisted").
    pred = None
    if predicate is not None:
        found = [m for m in predicate.finditer(raw_segment)]
        inside = [m for m in found if t_lo <= m.start() < t_hi]
        pred = inside[0] if inside else (min(found, key=lambda m: abs(m.start() - t_lo)) if found else None)
    effective = effective_date(raw_segment, document_ms)
    doc = _doc_date(document_ms)
    actor, actor_text = _actor(raw_segment, t_lo, t_hi, pred, issuer_names, issuer_source)
    if attribution == "QUOTED_THIRD_PARTY":
        actor, actor_text = "THIRD_PARTY", "quoted speaker"

    if NEGATION.search(segment):
        assertion = "NEGATED"
        cues.append("NEGATION_IN_CONJUNCT")
    elif ATTRIBUTION.search(clause):
        assertion = "ATTRIBUTED_REPORT"
        attribution = "ATTRIBUTED_TO_OTHERS"
        cues.append("ATTRIBUTION_FRAME")
    elif CONDITIONAL.search(segment):
        assertion = "CONDITIONAL_RISK"
        cues.append("CONDITIONAL")
    elif (ANNOUNCE.search(segment) or DECISION.search(segment) or effective) and \
            (DECISION.search(segment) or (effective and doc is not None and effective > doc.isoformat())
             or (effective and doc is None and ANNOUNCE.search(segment))):
        assertion = "ANNOUNCED_FUTURE"
        cues.append("ANNOUNCEMENT_OF_FUTURE_EVENT")
    elif FORECAST.search(segment):
        assertion = "FORECAST"
        cues.append("FORWARD_LOOKING")
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
    ("PROPOSED_RULE", re.compile(r"\bproposed\s+rule|\bnotice\s+of\s+proposed\s+rulemaking\b|\bproposes?\b", re.I)),
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
    statement_type = "REGULATORY_ACTION" if source_kind == "AGENCY" and actions else (
        "DEVELOPMENT_CLAIM" if DEVELOPMENT.search(text) else "OTHER_STATEMENT")
    certainty = sorted({CERTAINTY[a] for a in actions}) if statement_type == "REGULATORY_ACTION" else (
        ["ATTRIBUTED_TO_ANNOUNCER"] if statement_type == "DEVELOPMENT_CLAIM" else ["SOURCE_STATES"])
    relations = [{"issuer_id": i, "relation": "MENTIONED_IN_SOURCE", "effect": "UNKNOWN",
                  "basis": "name appears in this source text"} for i in name_mentions(text, aliases)]
    return {"schema": "SourceStatement.v1", "statement_type": statement_type, "actor": actor,
            "actions": actions, "certainty": certainty, "issuer_relations": relations,
            "note": "verifies what the source said or did; not truth of allegations, not price direction"}
