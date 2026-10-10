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
STATUSES = ("CLEAR", "UNKNOWN", "ADVERSE", "STALE")
REJECTIONS = ("UNSUPPORTED_SCHEMA", "MALFORMED", "INCONSISTENT", "WRONG_RUN", "PROFILE_MISMATCH", "UNKNOWN_TOKEN", "WRONG_ISSUER",
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
    age = profile.get("evidence_max_age_ms", DEFAULT_MAX_AGE_MS)
    if type(age) is not int or age <= 0:
        raise AuthorityError("evidence_max_age_ms must be a positive integer")
    return {"falsifier": falsifier, "statement": statement, "max_context_age_ms": age}


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


def _finding_ok(f) -> bool:
    return (type(f) is dict and type(f.get("predicate_id")) is str and f.get("supported") is True
            and f.get("verifier_accepted") is True and type(f.get("supporting_spans")) is list
            and bool(f["supporting_spans"]))


def problem(record, *, run_id=None, profile_hash=None, markets=None, now_ms=None, max_age_ms=None,
            universe=None) -> str | None:
    """The first reason `record` is unusable, or None. Intrinsic checks (schema, field types, hash, internal
    consistency) always run; identity and time checks run for whichever context arguments are given. The strategy
    and the planner-constraint builder use this same function, so a record the strategy rejects can never become
    a mandatory reduction (IDEA-031 red team S4-B c02/c03)."""
    if type(record) is not dict:
        return "MALFORMED"
    if record.get("schema") != SCHEMA:
        return "UNSUPPORTED_SCHEMA"
    if (record.get("status") not in STATUSES or type(record.get("state_version")) is not int
            or record["state_version"] < 0 or type(record.get("as_of_ms")) is not int
            or type(record.get("falsifier_findings")) is not list
            or type(record.get("statements_pending")) is not list or type(record.get("token")) is not str
            or record.get("assessed_until_ms") is not None and type(record["assessed_until_ms"]) is not int):
        return "MALFORMED"
    try:
        if record.get("context_hash") != context_hash(record):
            return "HASH_MISMATCH"
    except (TypeError, ValueError):
        return "MALFORMED"
    if any(not _finding_ok(f) for f in record["falsifier_findings"]):
        return "MALFORMED"
    if record["status"] == "CLEAR" and (record["falsifier_findings"] or record["statements_pending"]):
        return "INCONSISTENT"
    if run_id is not None and record.get("run_id") != run_id:
        return "WRONG_RUN"
    if profile_hash is not None and record.get("policy_profile_hash") != profile_hash:
        return "PROFILE_MISMATCH"
    if markets is not None:
        market = markets.get(record["token"])
        if (universe is not None and record["token"] not in universe) or market is None:
            return "UNKNOWN_TOKEN"
        if record.get("issuer_id") != market.get("underlying_id") or \
                record.get("underlying_id") != market.get("underlying_id"):
            return "WRONG_ISSUER"
    if now_ms is not None:
        if record["as_of_ms"] > now_ms:
            return "FUTURE_CONTEXT"
        if max_age_ms is not None and now_ms - record["as_of_ms"] > max_age_ms:
            return "EXPIRED_CONTEXT"
    return None


def accept_for_strategy(records: list, snapshot, markets: dict, known_versions: dict, profile: dict) -> tuple:
    """Validate EvidenceContext.v1 records for the strategy. Returns ({symbol: view}, [typed rejections]).

    `markets`: symbol -> MarketObservation (or None) as the strategy parsed them; the context's issuer must be
    that market's `underlying_id`. `known_versions`: symbol -> last accepted state_version (policy state), so an
    older or replayed context is rejected rather than silently used.
    """
    now, limits = _ms(snapshot), authority(profile)
    accepted, rejections = {}, []
    for record in records:
        symbol = record.get("token") if type(record) is dict else None
        reason = problem(record, run_id=snapshot.run_id, profile_hash=snapshot.policy_profile_hash, markets=markets,
                         now_ms=now, max_age_ms=limits["max_context_age_ms"], universe=snapshot.universe)
        if reason is None and record["state_version"] < known_versions.get(symbol, -1):
            reason = "STALE_EVIDENCE_VERSION"
        if reason is None and symbol in accepted:
            reason = "DUPLICATE_CONTEXT"
        if reason is not None:
            rejections.append({"reason": reason, "symbol": symbol if type(symbol) is str else None,
                               "schema": record.get("schema") if type(record) is dict else None})
            continue
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


def mandatory_reductions(records: list, profile: dict, held: dict, **context) -> list:
    """Planner reduction constraints for verified falsifier findings, only under MANDATORY_REDUCTION authority.

    Only records that pass `problem` (intrinsic checks always; identity/time checks for the `context` given:
    run_id, profile_hash, markets, now_ms, max_age_ms, universe) can create a constraint. These are requests to the
    independent planner, which still enforces affordability, market, integrity, ownership, clock and signing
    gates. Not every policy EXIT is mandatory: only these listed predicates.
    """
    if authority(profile)["falsifier"] != "MANDATORY_REDUCTION":
        return []
    out = []
    for record in records:
        if problem(record, **context) is not None:
            continue
        hits = sorted({f["predicate_id"] for f in record["falsifier_findings"]
                       if f["predicate_id"] in profile.get("falsifier_ids", [])})
        if hits and held.get(record["token"], 0) > 0:
            out.append({"symbol": record["token"], "max_units": 0,
                        "reason": "EVIDENCE_FALSIFIER_MANDATORY:" + ",".join(hits)})
    return out


def document(record: dict) -> Document:
    return Document.from_dict(record)
