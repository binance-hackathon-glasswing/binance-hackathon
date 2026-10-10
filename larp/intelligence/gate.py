"""Consumer-side acceptance of AssessmentResult.v1 and the per-issuer evidence state.

`accept` is a pure reducer: (state, result, current profile, now) -> (decision, next state).
It rejects results computed for an obsolete thesis context or policy profile, expired or
out-of-order results, and duplicates. Its `evidence_gate` is descriptive evidence health:

- CLEAR only after an ASSESSED, fresh, conflict-free result with complete evidence and no
  adverse finding;
- ADVERSE while any accepted adverse finding or fired falsifier is unresolved;
- UNKNOWN otherwise, including after ABSTAIN, UNAVAILABLE, timeouts and stale sources.

Abstentions and timeouts never clear findings and never produce CLEAR, so a timeout cannot
re-enable new exposure. How findings are resolved, and what any gate value means for orders,
is policy (Keith's module); this reducer emits no actions.
"""

from larp.contracts import Document
from larp.intelligence.agent import context_hash
from larp.intelligence.common import IntelligenceError, digest

DECISIONS = ("ACCEPT", "DUPLICATE", "REJECT_STALE_CONTEXT", "REJECT_PROFILE", "REJECT_EXPIRED",
             "REJECT_OUT_OF_ORDER", "REJECT_WRONG_ISSUER", "REJECT_MALFORMED")
INCOMPLETE = ("SOURCE_STALE", "SOURCE_HEALTH_UNKNOWN", "TOOL_ERROR:", "EXHIBIT_NOT_LOADED:", "FILING_",
              "PRIMARY_UNREADABLE:", "TOOL_BUDGET_EXHAUSTED", "EVIDENCE_", "REVISION_SUPERSEDED_REF:")


def initial_state(issuer_id: str, policy_profile_hash: str, max_known_facts: int = 200) -> dict:
    context = {"thesis": None, "known_facts": []}
    return {"schema": "IssuerEvidenceState.v1", "issuer_id": issuer_id, "version": 0,
            "policy_profile_hash": policy_profile_hash, "context": context, "context_hash": context_hash(context),
            "latest_cutoff_ms": None, "accepted_result_ids": [], "accepted_keys": [],
            "unresolved_adverse": [], "availability": "NONE", "evidence_gate": "UNKNOWN",
            "gate_reasons": ["NO_ASSESSMENT"], "max_known_facts": max_known_facts}


def accept(state: dict, result: Document, *, profile_hash: str, now_ms: int) -> tuple:
    r = result.read()
    if r.get("schema") != "AssessmentResult.v1" or type(r.get("result_id")) is not str:
        return "REJECT_MALFORMED", state
    if r.get("issuer_id") != state["issuer_id"]:
        return "REJECT_WRONG_ISSUER", state
    if r["result_id"] in state["accepted_result_ids"] or r.get("assessment_key") in state["accepted_keys"]:
        return "DUPLICATE", state
    if r.get("policy_profile_hash") != profile_hash or profile_hash != state["policy_profile_hash"]:
        return "REJECT_PROFILE", state
    if r.get("context_hash") != state["context_hash"]:
        return "REJECT_STALE_CONTEXT", state
    if type(r.get("expiry_ms")) is not int or r["expiry_ms"] <= now_ms:
        return "REJECT_EXPIRED", state
    if state["latest_cutoff_ms"] is not None and r.get("cutoff_ms", -1) < state["latest_cutoff_ms"]:
        return "REJECT_OUT_OF_ORDER", state
    if r.get("status") == "REJECTED_REQUEST":
        return "REJECT_MALFORMED", state

    nxt = dict(state, version=state["version"] + 1, latest_cutoff_ms=r["cutoff_ms"],
               accepted_result_ids=(state["accepted_result_ids"] + [r["result_id"]])[-500:],
               accepted_keys=(state["accepted_keys"] + [r["assessment_key"]])[-500:])
    adverse = list(state["unresolved_adverse"])
    held = {a["finding_id"] for a in adverse}
    for finding in r.get("event_findings", []):  # verified filer/keyword events, any status
        if finding["impact"] == "ADVERSE" and finding["finding_id"] not in held:
            held.add(finding["finding_id"])
            adverse.append({"finding_id": finding["finding_id"], "type": finding["type"],
                            "result_id": r["result_id"], "cutoff_ms": r["cutoff_ms"]})
    if r["status"] == "ASSESSED":
        for finding in r["findings"]:
            if finding["impact"] == "ADVERSE" and finding["finding_id"] not in held:
                held.add(finding["finding_id"])
                adverse.append({"finding_id": finding["finding_id"], "type": finding["type"],
                                "result_id": r["result_id"], "cutoff_ms": r["cutoff_ms"]})
        for falsifier in r["falsifiers"]:
            fid = "falsifier:" + digest("larp.intel.fired.v1", {"f": falsifier["falsifier_id"], "r": r["result_id"]})
            if falsifier["state"] == "FIRED" and fid not in held:
                adverse.append({"finding_id": fid, "type": "FALSIFIER_FIRED:" + falsifier["falsifier_id"],
                                "result_id": r["result_id"], "cutoff_ms": r["cutoff_ms"]})
        known = [c for c in state["context"]["known_facts"]]
        known_ids = {f["fact_id"] for f in known}
        for claim in r["claims"]:
            fact = {k: v for k, v in claim.items() if k not in ("novelty", "model_confirmed")}
            if fact["fact_id"] not in known_ids:
                known.append(fact)
        known = sorted(known, key=lambda f: (f["source"].get("available_ms") or 0, f["fact_id"]))
        context = {"thesis": r["proposed_thesis"], "known_facts": known[-state["max_known_facts"]:]}
        nxt.update(context=context, context_hash=context_hash(context), availability="AVAILABLE")
    else:
        nxt["availability"] = "ABSTAINED" if r["status"] == "ABSTAIN" else "UNAVAILABLE"
    nxt["unresolved_adverse"] = adverse
    gate, reasons = _gate(r, adverse, nxt["availability"])
    nxt.update(evidence_gate=gate, gate_reasons=reasons)
    return "ACCEPT", nxt


def _gate(r: dict, adverse: list, availability: str) -> tuple:
    if adverse:
        return "ADVERSE", sorted({a["type"] for a in adverse})
    if availability != "AVAILABLE":
        return "UNKNOWN", [f"LATEST_{availability}"] + list(r.get("reasons", []))
    reasons = [m for m in r["missingness"] if m.startswith(INCOMPLETE)]
    if r["conflicts"]:
        reasons.append("CONFLICTS")
    if r["proposed_thesis"] is None or r["proposed_thesis"]["status"] in ("UNKNOWN",):
        reasons.append("THESIS_UNKNOWN")
    return ("UNKNOWN", sorted(set(reasons))) if reasons else ("CLEAR", [])


def state_document(state: dict) -> Document:
    if state.get("schema") != "IssuerEvidenceState.v1":
        raise IntelligenceError("Unknown evidence state schema")
    return Document.from_dict(state)
