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
- red_flag_authority (IDEA-041, B1, interface I8): {"set_sha256": <RedFlagPredicateSet.v1 file hash>,
  "enabled": [predicate IDs]}. Absent, every red-flag predicate is SHADOW. An enabled predicate's action is
  the one its versioned record declares (Class 1 EXIT, Class 2 BLOCK_NEW_BUYS for its block_sessions,
  Class 3 SHADOW); the profile only enables it, and only for the exact predicate set it names.
  `red_flag_directives(record, profile)` turns an accepted record's verified red flags into those
  directives; the session-aware policy applies them (block start, expiry and reset are policy state).
"""

from functools import lru_cache

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError, digest
from larp.intelligence.redflags import load_predicates

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


@lru_cache(maxsize=1)
def red_flag_predicates() -> tuple:
    """(predicates by id, set sha256) of the committed RedFlagPredicateSet.v1."""
    return load_predicates()


def _red_flag_authority(profile: dict) -> dict:
    """A profile without red_flag_authority never depends on the predicate set: if the set cannot be loaded, every
    predicate is still SHADOW (an empty map) and nothing else changes (IDEA-041 R14). A profile that names the
    set needs it to load."""
    spec = profile.get("red_flag_authority")
    if spec is None:
        try:
            predicates, set_sha = red_flag_predicates()
        except (IntelligenceError, OSError, ValueError, KeyError, TypeError):
            return {"set_sha256": None, "predicates": {}}
        return {"set_sha256": set_sha, "predicates": {pid: "SHADOW" for pid in sorted(predicates)}}
    if type(spec) is not dict or set(spec) != {"set_sha256", "enabled"} or type(spec["enabled"]) is not list:
        raise AuthorityError("red_flag_authority must be {set_sha256, enabled}")
    try:
        predicates, set_sha = red_flag_predicates()
    except (IntelligenceError, OSError, ValueError, KeyError, TypeError) as exc:
        raise AuthorityError(f"red_flag_authority names a predicate set this build cannot load: {exc}") from None
    rights = {pid: "SHADOW" for pid in sorted(predicates)}
    if spec["set_sha256"] != set_sha:
        raise AuthorityError("red_flag_authority names a different red-flag predicate set than this build")
    unknown = sorted(set(map(str, spec["enabled"])) - set(predicates))
    if unknown or len(set(spec["enabled"])) != len(spec["enabled"]):
        raise AuthorityError(f"red_flag_authority enables unknown or repeated predicates: {unknown}")
    for pid in spec["enabled"]:
        rights[pid] = predicates[pid]["directive"]["kind"]
    return {"set_sha256": set_sha, "predicates": rights}


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
    return {"falsifier": falsifier, "statement": statement, "max_context_age_ms": age,
            "red_flags": _red_flag_authority(profile)}


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
        finding = {"predicate_id": _predicate(latch["type"]), "finding_id": latch["finding_id"],
                   "supported": True, "verifier_accepted": True,
                   "supporting_spans": [s.get("accession") for s in latch.get("sources") or []
                                        if s.get("accession")] or [latch["result_id"]],
                   "resolution_rule": latch["resolution_rule"]}
        if latch.get("red_flag"):
            finding["red_flag"] = _red_flag_view(latch)
        findings.append(finding)
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
        "due_reviews": view["due_reviews"], "review_due_ms": view.get("review_due_ms"),
        "thesis_status": view["thesis"],
        "last_rejection": view["last_rejection"],
        # Only Class 2 (expiring) red-flag latches stand between this issuer and a complete, fresh review. The policy
        # may treat the name as reviewed once it has counted those blocks out (IDEA-041, B1).
        "review_complete_excluding_timed_blocks": view.get("evidence_gate_excluding_timed") == "CLEAR",
        "assessed_until_excluding_timed_ms": view.get("assessed_until_excluding_timed_ms"),
    }
    record["context_hash"] = context_hash(record)
    return record


def _red_flag_view(latch: dict) -> dict:
    flag = latch["red_flag"]
    return {"predicate_id": flag["predicate_id"], "predicate_version": flag["predicate_version"],
            "class": flag["class"], "set_sha256": flag["set_sha256"], "item": flag["item"],
            "accession": flag["accession"], "record_id": flag["record_id"], "form": flag["form"],
            "amendment": flag["amendment"], "event_original_ms": flag["event_original_ms"],
            "event_time_basis": flag.get("event_time_basis"), "amends_accession": flag.get("amends_accession"),
            "latched_ms": latch.get("latched_ms"), "span": flag["span"],
            "affected_periods": flag["affected_periods"]}


def red_flag_directives(record: dict, profile: dict) -> list:
    """Directives for an accepted EvidenceContext.v1 record's verified red flags under the profile's authority.

    One directive per (predicate, accession); only predicates the profile enables for this exact predicate set,
    with the record's predicate version. SHADOW predicates yield none. Each directive: symbol, issuer_id,
    predicate_id, predicate_version, class, kind (EXIT | BLOCK_NEW_BUYS), block_sessions, accession, finding_ids,
    amendment, restarts_block (an original filing restarts a Class 2 block; an 8-K/A never does) and latched_ms.
    """
    rights = authority(profile)["red_flags"]["predicates"]
    if set(rights.values()) <= {"SHADOW"}:
        return []  # nothing enabled: no directive, and no need to load the predicate set
    predicates, set_sha = red_flag_predicates()
    out = {}
    for finding in record.get("falsifier_findings", []):
        flag = finding.get("red_flag")
        if type(flag) is not dict or flag.get("set_sha256") != set_sha:
            continue
        predicate = predicates.get(flag.get("predicate_id"))
        kind = rights.get(flag.get("predicate_id"), "SHADOW")
        if predicate is None or kind == "SHADOW" or flag.get("predicate_version") != predicate["version"] \
                or flag.get("class") != predicate["class"]:
            continue
        key = (flag["predicate_id"], flag["accession"])
        if key in out:
            out[key]["finding_ids"].append(finding["finding_id"])
            continue
        out[key] = {"symbol": record["token"], "issuer_id": record["issuer_id"],
                    "predicate_id": flag["predicate_id"], "predicate_version": flag["predicate_version"],
                    "class": flag["class"], "kind": kind, "block_sessions": predicate["directive"]["block_sessions"],
                    "accession": flag["accession"], "finding_ids": [finding["finding_id"]],
                    "amendment": flag["amendment"], "restarts_block": kind == "BLOCK_NEW_BUYS" and not flag["amendment"],
                    "latched_ms": flag.get("latched_ms")}
    return [dict(d, finding_ids=sorted(d["finding_ids"])) for _, d in sorted(out.items())]


def _ms(snapshot) -> int:
    return int(snapshot.observed_at.timestamp() * 1000)


def _finding_ok(f) -> bool:
    return (type(f) is dict and type(f.get("predicate_id")) is str and f.get("supported") is True
            and f.get("verifier_accepted") is True and type(f.get("supporting_spans")) is list
            and bool(f["supporting_spans"]))


def problem(record, *, run_id=None, profile_hash=None, markets=None, now_ms=None, max_age_ms=None,
            universe=None) -> str | None:
    """The first reason `record` is unusable, or None. Intrinsic checks (schema, field types, hash, internal
    consistency) always run; identity and time checks run for whichever context arguments are given. Strategy
    acceptance (`accept_records`) is this check plus version and duplicate checks; the runtime builds planner
    reduction constraints only from records `accept_records` accepts (IDEA-031 S4-B c02/c03, IDEA-033 R17)."""
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
    timed = record.get("review_complete_excluding_timed_blocks", False)
    if type(timed) is not bool or (timed and record["status"] != "CLEAR" and any(
            (f.get("red_flag") or {}).get("class") != 2 for f in record["falsifier_findings"])):
        return "INCONSISTENT"  # only Class 2 red flags may stand between this record and a clear review
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
    accepted, rejections = accept_records(records, run_id=snapshot.run_id, profile_hash=snapshot.policy_profile_hash,
                                          now_ms=_ms(snapshot), markets=markets, known_versions=known_versions,
                                          profile=profile, universe=snapshot.universe)
    if profile.get("assessment_required"):
        for symbol in snapshot.universe:
            if markets.get(symbol) is not None and symbol not in accepted:
                rejections.append({"reason": "MISSING", "symbol": symbol, "schema": None})
    return accepted, rejections


def accept_records(records: list, *, run_id: str, profile_hash: str, now_ms: int, markets: dict, known_versions: dict,
                   profile: dict, universe) -> tuple:
    """The strategy's acceptance of EvidenceContext.v1 records, without needing a DecisionSnapshot: the runtime
    applies exactly this before turning a record into a planner constraint. Returns ({symbol: view}, [rejections])."""
    now, limits = now_ms, authority(profile)
    accepted, rejections = {}, []
    for record in records:
        symbol = record.get("token") if type(record) is dict else None
        reason = problem(record, run_id=run_id, profile_hash=profile_hash, markets=markets,
                         now_ms=now, max_age_ms=limits["max_context_age_ms"], universe=universe)
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
        timed_until = record.get("assessed_until_excluding_timed_ms")
        timed = (record.get("review_complete_excluding_timed_blocks") is True and type(timed_until) is int
                 and now < timed_until)
        accepted[symbol] = dict(record, status=status, review_complete=status == "CLEAR",
                                review_complete_excluding_timed_blocks=timed)
    return accepted, rejections


def mandatory_reductions(records: list, profile: dict, held: dict, **context) -> list:
    """Planner reduction constraints for verified falsifier findings, only under MANDATORY_REDUCTION authority.

    Only records that pass `problem` (intrinsic checks always; identity/time checks for the `context` given:
    run_id, profile_hash, markets, now_ms, max_age_ms, universe) can create a constraint. The runtime passes only
    records `accept_records` accepted, so version, duplicate and market checks apply too. These are requests to the
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
