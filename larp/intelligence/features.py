"""FeatureRow.v1 export from assessment results, for optional fusion research (IDEA-008).

Rows are point-in-time: `as_of_ms` is the assessment cutoff (what evidence could be seen) and
`available_ms` the time the row itself existed, the result's `completed_ms`. A queued, retried
or backfilled assessment runs after its cutoff, so cutoff + elapsed would date the row before
it existed (look-ahead). Values are integers, booleans or short
codes; there is no trade, size or direction-to-trade field. The rule baseline has no fitted
parameters, so it cannot leak fitted information; any hosted/local model's rows inherit that
model's knowledge-cutoff (hindsight) risk (I-67) and must be used out-of-fold. Models here do
not select portfolio trades.
"""

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError, assert_no_trade_fields

IMPACT_ORDINAL = {"ADVERSE": -1, "MIXED": 0, "IMMATERIAL": 0, "FAVOURABLE": 1}


def feature_row(result: Document, gate_state: dict | None = None) -> Document:
    r = result.read()
    if type(r.get("completed_ms")) is not int:
        raise IntelligenceError("AssessmentResult has no completed_ms; its availability time is unknown")
    novelty = r.get("novelty") or {}
    falsifiers = r.get("falsifiers") or []
    hypothetical = r.get("hypothetical_events") or []
    row = {
        "schema": "FeatureRow.v1", "issuer_id": r.get("issuer_id"), "result_id": r.get("result_id"),
        "assessment_key": r.get("assessment_key"), "model_hash": r.get("model_hash"),
        "as_of_ms": r.get("cutoff_ms"),
        "available_ms": r["completed_ms"],
        "status": r.get("status"), "assessed": r.get("status") == "ASSESSED",
        "impact_ordinal": IMPACT_ORDINAL.get(r.get("impact")), "severity": r.get("severity"),
        "n_verified_claims": len(r.get("claims") or []), "n_rejected_claims": len(r.get("rejected_claims") or []),
        "n_conflicts": len(r.get("conflicts") or []),
        "n_new": novelty.get("new", 0), "n_changed": novelty.get("changed", 0),
        "n_unchanged": novelty.get("unchanged", 0), "n_no_prior": novelty.get("no_prior_available", 0),
        "n_hypothetical_new": sum(1 for h in hypothetical if h["novelty"] != "REPEATED"),
        "n_hypothetical_repeated": sum(1 for h in hypothetical if h["novelty"] == "REPEATED"),
        "hypothetical_types_new": sorted({h["event"] for h in hypothetical if h["novelty"] != "REPEATED"}),
        "n_falsifiers_fired": sum(1 for f in falsifiers if f["state"] == "FIRED"),
        "n_falsifiers_unknown": sum(1 for f in falsifiers if f["state"] == "UNKNOWN"),
        "finding_types": sorted({f["type"] for f in r.get("findings") or []}),
        "missing_codes": sorted({m.split(":")[0] for m in r.get("missingness") or []}),
        "source_stale": bool((r.get("freshness") or {}).get("source_stale")),
        "evidence_age_ms": (r.get("freshness") or {}).get("evidence_age_ms"),
        "confidence_level": (r.get("confidence") or {}).get("level"), "confidence_calibrated": False,
        "tool_calls": (r.get("budget_used") or {}).get("tool_calls"),
        "evidence_gate": None if gate_state is None else gate_state["evidence_gate"],
    }
    assert_no_trade_fields(row, "FeatureRow")
    return Document.from_dict(row)
