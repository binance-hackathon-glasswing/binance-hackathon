"""EvidenceContext.v1: the one record the strategy reads about an issuer's evidence (IDEA-030 R02, IDEA-031 S1).

Producer: `build_evidence_context(view, ...)` from `gate.consume(state, now)` (IssuerEvidenceState.v2), so
freshness is assessed at consumption time and adverse latches/statement reviews come from durable state,
not from one assessment. Consumer: `accept_for_strategy(...)`, which validates identity, versions, times
and the context hash and returns either a strategy view or a typed rejection.

Times are UTC epoch milliseconds. The context hash is domain-separated over the canonical record without
its own hash field. Token, issuer and underlying identities are explicit and must match the market
record the strategy uses; no conversion between listings, shares and tokens is implied.

Authority (what evidence may do to a portfolio) is NOT in this record. It is read from the strategy
profile by `authority(profile)`:

- falsifier_authority: NONE | SHADOW | DISCRETIONARY_EXIT | MANDATORY_REDUCTION. Default SHADOW (from the
  legacy evidence_mode: SHADOW -> SHADOW, BOUNDED_FALSIFIER -> DISCRETIONARY_EXIT). No adoption record makes
  falsifier exits live or mandatory (IDEA-031 S0); MANDATORY_REDUCTION is a tested capability, not enabled.
- statement_authority: SHADOW | ENTRY_BLOCK. Default SHADOW: statements pending review are recorded but are
  not an entry veto (IDEA-030 R06).
"""

from larp.contracts import Document
from larp.intelligence.common import digest

SCHEMA = "EvidenceContext.v1"
FALSIFIER_AUTHORITIES = ("NONE", "SHADOW", "DISCRETIONARY_EXIT", "MANDATORY_REDUCTION")
STATEMENT_AUTHORITIES = ("SHADOW", "ENTRY_BLOCK")
LEGACY_EVIDENCE_MODE = {"SHADOW": "SHADOW", "BOUNDED_FALSIFIER": "DISCRETIONARY_EXIT"}
REJECTIONS = ("UNSUPPORTED_SCHEMA", "MALFORMED", "WRONG_RUN", "PROFILE_MISMATCH", "UNKNOWN_TOKEN", "WRONG_ISSUER",
              "HASH_MISMATCH", "FUTURE_CONTEXT", "EXPIRED_CONTEXT", "STALE_EVIDENCE_VERSION", "DUPLICATE_CONTEXT",
              "MISSING")
DEFAULT_MAX_AGE_MS = 3_600_000


class AuthorityError(ValueError):
    """The profile names an authority this build does not implement."""


def authority(profile: dict) -> dict:
    falsifier = profile.get("falsifier_authority") or LEGACY_EVIDENCE_MODE.get(profile.get("evidence_mode"))
    statement = profile.get("statement_authority", "SHADOW")
    if falsifier not in FALSIFIER_AUTHORITIES or statement not in STATEMENT_AUTHORITIES:
        raise AuthorityError("Unknown evidence authority")
    if profile.get("evidence_mode") == "BOUNDED_FALSIFIER" and falsifier not in ("DISCRETIONARY_EXIT",
                                                                                "MANDATORY_REDUCTION"):
        raise AuthorityError("evidence_mode BOUNDED_FALSIFIER cannot be weakened silently by falsifier_authority")
    return {"falsifier": falsifier, "statement": statement,
            "max_context_age_ms": profile.get("evidence_max_age_ms", DEFAULT_MAX_AGE_MS)}


def context_hash(record: dict) -> str:
    return digest("larp.evidence-context.v1", {k: v for k, v in record.items() if k != "context_hash"})


def _predicate(latch_type: str) -> str:
    return latch_type[len("FALSIFIER_FIRED:"):] if latch_type.startswith("FALSIFIER_FIRED:") else latch_type


def build_evidence_context(view: dict, state: dict, *, run_id: str, token: str, underlying_id: str,
                           policy_profile_hash: str) -> dict:
    """EvidenceContext.v1 from an EvidenceView.v1 (gate.consume) and the state it was read from."""
    if view.get("schema") != "EvidenceView.v1" or view["issuer_id"] != state["issuer_id"]:
        raise ValueError("Expected the EvidenceView.v1 of this issuer's state")
    findings = []
    for latch in state["unresolved_adverse"]:
        findings.append({"predicate_id": _predicate(latch["type"]), "finding_id": latch["finding_id"],
                         "supported": True, "verifier_accepted": True,
                         "supporting_spans": [s.get("accession") for s in latch.get("sources") or []
                                              if s.get("accession")] or [latch["result_id"]],
                         "resolution_rule": latch["resolution_rule"]})
    statements = view["statements"]
    gate = view["evidence_gate"]
    record = {
        "schema": SCHEMA, "run_id": run_id, "issuer_id": state["issuer_id"], "underlying_id": underlying_id,
        "token": token, "policy_profile_hash": policy_profile_hash, "state_version": state["version"],
        "as_of_ms": view["as_of_ms"], "latest_cutoff_ms": view["latest_cutoff_ms"],
        "assessed_until_ms": view["assessed_until_ms"], "status": gate, "status_reasons": view["gate_reasons"],
        "availability": view["availability"],
        "quality": "VERIFIED" if view["availability"] == "AVAILABLE" and gate in ("CLEAR", "ADVERSE") else "UNVERIFIED",
        # A complete, fresh review exists only while the evidence is CLEAR at consumption time.
        "review_complete": gate == "CLEAR",
        "falsifier_findings": sorted(findings, key=lambda f: f["finding_id"]),
        "statements_pending": statements.get("PENDING_REVIEW", []),
        "statements_exhausted": statements.get("REVIEW_EXHAUSTED", []),
        "due_reviews": view["due_reviews"], "thesis_status": view["thesis"],
        "last_rejection": view["last_rejection"],
    }
    record["context_hash"] = context_hash(record)
    return record


def _ms(snapshot) -> int:
    return int(snapshot.observed_at.timestamp() * 1000)


def accept_for_strategy(records: list, snapshot, markets: dict, known_versions: dict, profile: dict) -> tuple:
    """Validate EvidenceContext.v1 records for the strategy. Returns ({symbol: view}, [typed rejections]).

    `markets`: symbol -> MarketObservation (or None) as the strategy parsed them; the context's issuer must be
    that market's `underlying_id`. `known_versions`: symbol -> last accepted state_version (policy state), so an
    older or replayed context is rejected rather than silently used.
    """
    now, limits = _ms(snapshot), authority(profile)
    accepted, rejections = {}, []

    def reject(reason, record, symbol=None):
        rejections.append({"reason": reason, "symbol": symbol,
                           "schema": record.get("schema") if type(record) is dict else None})

    for record in records:
        if type(record) is not dict:
            reject("MALFORMED", {})
            continue
        symbol = record.get("token")
        if record.get("schema") != SCHEMA:
            reject("UNSUPPORTED_SCHEMA", record, symbol)
            continue
        try:
            if record.get("context_hash") != context_hash(record):
                reject("HASH_MISMATCH", record, symbol)
                continue
        except (TypeError, ValueError):
            reject("MALFORMED", record, symbol)
            continue
        if record.get("run_id") != snapshot.run_id:
            reject("WRONG_RUN", record, symbol)
        elif record.get("policy_profile_hash") != snapshot.policy_profile_hash:
            reject("PROFILE_MISMATCH", record, symbol)
        elif symbol not in snapshot.universe or markets.get(symbol) is None:
            reject("UNKNOWN_TOKEN", record, symbol)
        elif record.get("issuer_id") != markets[symbol].get("underlying_id") or \
                record.get("underlying_id") != markets[symbol].get("underlying_id"):
            reject("WRONG_ISSUER", record, symbol)
        elif type(record.get("as_of_ms")) is not int or record["as_of_ms"] > now:
            reject("FUTURE_CONTEXT", record, symbol)
        elif now - record["as_of_ms"] > limits["max_context_age_ms"]:
            reject("EXPIRED_CONTEXT", record, symbol)
        elif record.get("state_version", -1) < known_versions.get(symbol, -1):
            reject("STALE_EVIDENCE_VERSION", record, symbol)
        elif symbol in accepted:
            reject("DUPLICATE_CONTEXT", record, symbol)
        else:
            # An as-of CLEAR whose validity ended between production and use is read as STALE here too.
            status = record["status"]
            if status == "CLEAR" and (record["assessed_until_ms"] is None or now >= record["assessed_until_ms"]):
                status = "STALE"
            accepted[symbol] = dict(record, status=status, review_complete=status == "CLEAR")
    if profile.get("assessment_required"):
        for symbol in snapshot.universe:
            if markets.get(symbol) is not None and symbol not in accepted:
                rejections.append({"reason": "MISSING", "symbol": symbol, "schema": None})
    return accepted, rejections


def mandatory_reductions(records: list, profile: dict, held: dict) -> list:
    """Planner reduction constraints for verified falsifier findings, only under MANDATORY_REDUCTION authority.

    These are requests to the independent planner, which still enforces affordability, market, integrity,
    ownership, clock and signing gates. Not every policy EXIT is mandatory: only these listed predicates.
    """
    if authority(profile)["falsifier"] != "MANDATORY_REDUCTION":
        return []
    out = []
    for record in records:
        hits = sorted({f["predicate_id"] for f in record.get("falsifier_findings", [])
                       if f["predicate_id"] in profile.get("falsifier_ids", []) and f["supported"]
                       and f["verifier_accepted"] and f["supporting_spans"]})
        if hits and held.get(record["token"], 0) > 0:
            out.append({"symbol": record["token"], "max_units": 0,
                        "reason": "EVIDENCE_FALSIFIER_MANDATORY:" + ",".join(hits)})
    return out


def document(record: dict) -> Document:
    return Document.from_dict(record)
