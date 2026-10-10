"""Allowlisted assessment tools over the point-in-time evidence index (G-50: <= 3 tool types).

Tools read only records already ingested for the request's issuer and available at or before
the request cutoff. They take identifiers, never URLs or free-form destinations, so text inside
a filing cannot redirect them. There is no web, wallet, signer, policy or upload tool, and the
registry rejects any name outside the configured allowlist.
"""

import re

from larp.intelligence.common import IntelligenceError, sha256_hex
from larp.intelligence.facts import HYPOTHETICAL_PREFIX, METRIC_NAMES, extract_document, item_events, values_agree
from larp.intelligence.text import text_from_saved
from larp.intelligence.verify import compare

_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_PERIOD = re.compile(r"^(?:FY)?\d{4}(?:-Q[1-4])?$")


class ToolError(Exception):
    """A tool failed; recorded as TOOL_ERROR and never retried within the same assessment."""


class PortEvidenceReader:
    """Reads EvidenceRecord.v1 documents and content-addressed text through the store ports."""

    def __init__(self, store, artifacts):
        self.store, self.artifacts = store, artifacts

    def records(self, issuer_id: str) -> list:
        return [doc.read() for doc in self.store.records(issuer_id)]

    def text(self, sha256: str) -> str:
        saved = self.artifacts.get(sha256)
        if saved is None:
            raise ToolError("ARTIFACT_MISSING")
        if sha256_hex(saved) != sha256:
            raise ToolError("ARTIFACT_INTEGRITY_ERROR")
        return text_from_saved(saved)


class EvidenceIndex:
    """Point-in-time view: one issuer, records with available_ms <= cutoff, latest revision each."""

    def __init__(self, reader, entry, cutoff_ms: int):
        self.reader, self.entry, self.cutoff = reader, entry, cutoff_ms
        latest, every = {}, {}
        for record in reader.records(entry.issuer_id):
            if record["issuer_id"] != entry.issuer_id or record["available_ms"] > cutoff_ms:
                continue
            every[record["record_id"]] = record
            held = latest.get(record["accession"])
            if held is None or record["revision"] > held["revision"]:
                latest[record["accession"]] = record
        self.by_accession = latest  # latest revision available at the cutoff, per accession
        self.all_by_id = every  # every revision available at the cutoff

    def text(self, sha256: str) -> str:
        return self.reader.text(sha256)


def doc_source(record: dict, doc: dict) -> dict:
    return {"record_id": record["record_id"], "accession": record["accession"], "doc_name": doc["name"],
            "available_ms": record["available_ms"], "original_ms": record["original_ms"]}


def load_document(state, record: dict, doc: dict) -> list:
    """Load one saved document into the assessment state; returns new fact IDs."""
    if doc["status"] != "OK" or not doc["text_sha256"]:
        raise ToolError("DOCUMENT_NOT_RETRIEVED")
    text = state.index.text(doc["text_sha256"])
    state.texts[doc["text_sha256"]] = text
    state.loaded.add((record["accession"], doc["name"]))
    state.injection |= suspicious_instructions(text)
    new = []
    for fact in extract_document(text, doc["text_sha256"], state.entry, doc_source(record, doc)):
        if fact["fact_id"] not in state.facts:
            state.facts[fact["fact_id"]] = fact
            new.append(fact["fact_id"])
    return new


INJECTION = re.compile(r"ignore\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instructions|"
                       r"\byou\s+are\s+now\b|^\s*(?:system|assistant)\s*:|\boutput\s+(?:buy|sell)\b|"
                       r"\b(?:call|fetch|visit|open)\s+https?://", re.I | re.M)


def suspicious_instructions(text: str) -> set:
    return {m.group(0).strip().lower()[:60] for m in INJECTION.finditer(text)}


def _text_arg(args, key, pattern=None, max_len=40):
    value = args.get(key)
    if type(value) is not str or not value or len(value) > max_len or (pattern and not pattern.match(value)):
        raise ToolError(f"BAD_ARGUMENT:{key}")
    return value


def fetch_document(state, args: dict) -> dict:
    accession = _text_arg(args, "accession", _ACCESSION)
    name = _text_arg(args, "name", max_len=120)
    record = state.index.by_accession.get(accession)
    if record is None:
        raise ToolError("NOT_FOUND_OR_NOT_AVAILABLE_AT_CUTOFF")
    doc = next((d for d in record["documents"] if d["name"] == name), None)
    if doc is None:
        raise ToolError("DOCUMENT_NOT_IN_FILING")
    if (accession, name) in state.loaded:
        return {"status": "ALREADY_LOADED", "accession": accession, "name": name}
    new = load_document(state, record, doc)
    text = state.texts[doc["text_sha256"]]
    limit = state.config.limits["max_tool_result_chars"]
    return {"status": "OK", "accession": accession, "name": name, "text_sha256": doc["text_sha256"],
            "chars": len(text), "excerpt": text[:limit], "truncated": len(text) > limit, "new_fact_ids": new}


HYPOTHETICAL = "HYPOTHETICAL"  # prior_context(metric="HYPOTHETICAL"): every hypothetical event, in one call


def _matches(fact: dict, metric: str) -> bool:
    return fact["metric"].startswith(HYPOTHETICAL_PREFIX) if metric == HYPOTHETICAL else fact["metric"] == metric


def prior_context(state, args: dict) -> dict:
    """Facts for one metric, or every hypothetical event, that were available before the assessed filing(s)."""
    metric = _text_arg(args, "metric")
    if metric not in METRIC_NAMES and metric != HYPOTHETICAL:
        raise ToolError("BAD_ARGUMENT:metric")
    state.queried_prior.add(metric)
    current = state.current_accessions
    first_original = min(state.index.all_by_id[r]["original_ms"] for r in state.current_records)
    found = [f["fact_id"] for f in state.context_facts
             if _matches(f, metric) and f["source"].get("accession") not in current]
    for record in sorted(state.index.by_accession.values(), key=lambda r: (r["original_ms"], r["accession"])):
        if record["accession"] in current or record["original_ms"] >= first_original or record["quality"] == "MISSING":
            continue
        for doc in record["documents"]:
            if doc["status"] == "OK" and (record["accession"], doc["name"]) not in state.loaded:
                load_document(state, record, doc)
        found += [f["fact_id"] for f in state.facts.values()
                  if f["source"].get("accession") == record["accession"] and _matches(f, metric)]
    found = sorted(set(found))
    state.prior_fact_ids.update(found)
    periods = sorted({state.facts[i]["period"] or "" for i in found})
    return {"status": "OK" if found else "NO_PRIOR", "metric": metric, "fact_ids": found, "periods": periods}


def comparable_pairs(state, metric: str) -> list:
    pairs = []
    for new in state.current_facts():
        if new["metric"] != metric or new["kind"] not in ("REPORTED", "GUIDANCE") or not new["period"]:
            continue
        for prior in state.prior_facts():
            if (prior["metric"], prior["period"], prior["unit"]) == (metric, new["period"], new["unit"]) and \
                    not (new["kind"] == "GUIDANCE" and prior["kind"] == "REPORTED"):
                pairs.append((new["fact_id"], prior["fact_id"]))
    return pairs


def _latest_revision(state, fact: dict) -> bool:
    record = state.index.all_by_id.get(fact["source"].get("record_id"))
    if record is None:
        return True  # verified context fact whose record is outside this index view
    return state.index.by_accession[record["accession"]]["record_id"] == record["record_id"]


def guidance_basis(state, new: dict, priors: list) -> dict:
    """Prior guidance fact ID -> None if it is the comparison basis for `new`, else why it is not.

    The basis is the latest guidance issued (acceptance time) before the filing that holds `new`,
    from the latest revision of each filing available at the cutoff. Earlier guidance is
    SUPERSEDED: kept for audit, never the basis of a finding. Disagreeing guidance issued at that
    latest time is CONFLICTING and gives no basis at all.
    """
    issued = new["source"].get("original_ms")
    reasons, usable = {}, []
    for prior in priors:
        if prior["kind"] != "GUIDANCE":
            continue
        when = prior["source"].get("original_ms")
        if not _latest_revision(state, prior):
            reasons[prior["fact_id"]] = "SUPERSEDED_REVISION"
        elif type(when) is not int or type(issued) is not int or when >= issued:
            reasons[prior["fact_id"]] = "NOT_ISSUED_BEFORE_ASSESSED_FILING"
        else:
            usable.append(prior)
    if usable:
        latest = max(p["source"]["original_ms"] for p in usable)
        group = [p for p in usable if p["source"]["original_ms"] == latest]
        conflict = any(not values_agree(a, b) for i, a in enumerate(group) for b in group[i + 1:])
        in_group = {p["fact_id"] for p in group}
        for prior in usable:
            reasons[prior["fact_id"]] = (("CONFLICTING_PRIOR_GUIDANCE" if conflict else None)
                                         if prior["fact_id"] in in_group else "SUPERSEDED_PRIOR_GUIDANCE")
    return reasons


def compare_facts(state, args: dict) -> dict:
    """Exact, rounding-aware comparison of every current fact of a metric with its prior facts.

    Every pair is compared and kept for audit; `applicable` marks the pairs a finding may use
    (all earlier reported values, but only the latest applicable prior guidance).
    """
    metric = _text_arg(args, "metric")
    if metric not in METRIC_NAMES:
        raise ToolError("BAD_ARGUMENT:metric")
    state.compared_metrics.add(metric)
    by_new = {}
    for new_id, prior_id in comparable_pairs(state, metric):
        by_new.setdefault(new_id, []).append(prior_id)
    results = []
    for new_id, prior_ids in by_new.items():
        new = state.facts[new_id]
        basis = guidance_basis(state, new, [state.facts[i] for i in prior_ids])
        if "CONFLICTING_PRIOR_GUIDANCE" in basis.values():
            state.missing.append(f"PRIOR_GUIDANCE_CONFLICT:{metric}:{new['period']}")
        for prior_id in prior_ids:
            result = compare(new, state.facts[prior_id])
            reason = basis.get(prior_id)
            result = dict(result, applicable=reason is None)
            if reason:
                result["not_applicable"] = reason
            state.comparisons[(new_id, prior_id)] = result
            results.append(result)
    return {"status": "OK" if results else "NOTHING_TO_COMPARE", "metric": metric, "comparisons": results}


TOOLS = {"fetch_document": fetch_document, "prior_context": prior_context, "compare_facts": compare_facts}


def run_tool(state, name: str, args: object) -> dict:
    if name not in state.allowed_tools or name not in TOOLS:
        raise ToolError("TOOL_NOT_ALLOWED")
    if type(args) is not dict:
        raise ToolError("BAD_ARGUMENTS")
    try:
        return TOOLS[name](state, args)
    except ToolError:
        raise
    except Exception as exc:  # a tool defect is a recorded tool error, never an agent crash
        raise ToolError(f"TOOL_EXCEPTION:{type(exc).__name__}") from exc


def check_allowlist(allowed: tuple, configured: tuple) -> tuple:
    if type(allowed) is not list or any(type(t) is not str for t in allowed) or set(allowed) - set(configured):
        raise IntelligenceError("Requested tools are outside the configured allowlist")
    return tuple(sorted(set(allowed)))


def load_items(state, record: dict) -> list:
    new = []
    for fact in item_events(record):
        if fact["fact_id"] not in state.facts:
            state.facts[fact["fact_id"]] = fact
            new.append(fact["fact_id"])
    return new
