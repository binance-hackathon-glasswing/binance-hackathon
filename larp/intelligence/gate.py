"""Consumer-side acceptance of AssessmentResult.v2 and the per-issuer evidence state (IssuerEvidenceState.v2).

`accept` is a pure reducer: (state, result, current profile, now) -> (decision, next state). It rejects
results computed for an obsolete thesis context or policy profile, expired or out-of-order results,
and duplicates. `consume(state, now)` is the as-of view every consumer must read instead of the stored
gate: freshness is assessed at consumption time (IDEA-030 R07).

Evidence status, descriptive only:
- CLEAR only after an ASSESSED, fresh, conflict-free result with complete coverage, every numerical
  fact checked against earlier filings, no untrusted instructions, no statement pending review, no
  unresolved adverse finding, and only while `now < assessed_until_ms`;
- STALE when an accepted CLEAR has aged past its validity (an expired incoming result cannot refresh it);
- ADVERSE while any adverse latch is unresolved;
- UNKNOWN otherwise, including after ABSTAIN, UNAVAILABLE, timeouts, stale sources and pending reviews.

What these values mean for orders is NOT decided here (IDEA-031 S2.4): the integration layer applies a
separately configured authority, whose default for statements and new evidence is SHADOW.

State v2 adds, relative to v1 (IDEA-030 R06/R07):
- `statements`: registry of event statements with review lifecycle (lifecycle.py). An unrelated clean
  result never erases a pending statement; a reread of the same filing never re-opens a review; reviews
  are bounded (attempts, exponential backoff, REVIEW_EXHAUSTED).
- `unresolved_adverse` latches carry an explicit `resolution_rule`. The only rule implemented is
  SOURCE_CORRECTED_OR_WITHDRAWN: the latch resolves when every record supporting it has been superseded by
  a revision in which the finding no longer appears, or withdrawn. Latches are never cleared by expiry,
  abstention, timeout or an unrelated clean filing.
- `assessed_until_ms` and `last_rejection` for consumption-time freshness.
"""

from larp.contracts import Document
from larp.intelligence import lifecycle
from larp.intelligence.agent import context_hash
from larp.intelligence.common import INCOMPLETE_EVIDENCE, IntelligenceError, digest

SCHEMA = "IssuerEvidenceState.v2"
RESULT_SCHEMAS = ("AssessmentResult.v2",)
DECISIONS = ("ACCEPT", "DUPLICATE", "REJECT_STALE_CONTEXT", "REJECT_PROFILE", "REJECT_EXPIRED",
             "REJECT_OUT_OF_ORDER", "REJECT_WRONG_ISSUER", "REJECT_MALFORMED")
INCOMPLETE = INCOMPLETE_EVIDENCE
RESOLUTION_RULE = "SOURCE_CORRECTED_OR_WITHDRAWN"
_LISTS = ("findings", "event_findings", "claims", "falsifiers", "event_statements", "evidence_used", "missingness",
          "conflicts", "reasons")
_LEGACY = object()  # marker: the result has no review_scope field at all
MAX_RECORDS = 2000  # records_seen / records_assessed bound, besides protected correction baselines
DEFAULT_LIFECYCLE = {"review_base_delay_ms": 21_600_000, "max_review_attempts": 3, "max_backoff_ms": 172_800_000,
                     "statement_retention_ms": 7_776_000_000, "max_statements": 400}


def initial_state(issuer_id: str, policy_profile_hash: str, max_known_facts: int = 200,
                  lifecycle_policy: dict | None = None) -> dict:
    context = {"thesis": None, "known_facts": []}
    return {"schema": SCHEMA, "issuer_id": issuer_id, "version": 0,
            "policy_profile_hash": policy_profile_hash, "context": context, "context_hash": context_hash(context),
            "latest_cutoff_ms": None, "accepted_result_ids": [], "accepted_keys": [],
            "unresolved_adverse": [], "resolved_adverse": [], "statements": {}, "records_seen": {},
            "records_assessed": {},
            "availability": "NONE", "evidence_gate": "UNKNOWN", "gate_reasons": ["NO_ASSESSMENT"],
            "assessed_until_ms": None, "gate_excluding_timed": "UNKNOWN",
            "gate_excluding_timed_reasons": ["NO_ASSESSMENT"], "assessed_until_excluding_timed_ms": None, "last_rejection": None, "max_known_facts": max_known_facts,
            "lifecycle": dict(DEFAULT_LIFECYCLE, **(lifecycle_policy or {}))}


def lifecycle_policy_from(config) -> dict:
    """Lifecycle parameters from an IntelligenceConfig (synthetic development defaults until set live)."""
    return {"review_base_delay_ms": config.p("reassess_delay_ms"),
            "max_review_attempts": config.p("max_review_attempts"),
            "max_backoff_ms": config.p("max_review_backoff_ms"),
            "statement_retention_ms": config.p("statement_retention_ms"),
            "max_statements": config.limits["max_statements_registry"]}


def _reject(state, decision, now_ms, result_id=None):
    """A rejection never changes evidence; it is recorded so consumers can see that fresher input failed."""
    if decision in ("DUPLICATE",):
        return decision, state
    return decision, dict(state, last_rejection={"decision": decision, "at_ms": now_ms, "result_id": result_id})


def accept(state: dict, result: Document, *, profile_hash: str, now_ms: int) -> tuple:
    if state.get("schema") != SCHEMA:
        raise IntelligenceError("Unknown evidence state schema (expected IssuerEvidenceState.v2)")
    r = result.read()
    rid = r.get("result_id") if type(r.get("result_id")) is str else None
    if r.get("schema") not in RESULT_SCHEMAS or rid is None:
        return _reject(state, "REJECT_MALFORMED", now_ms, rid)
    if r.get("issuer_id") != state["issuer_id"]:
        return _reject(state, "REJECT_WRONG_ISSUER", now_ms, rid)
    if rid in state["accepted_result_ids"] or r.get("assessment_key") in state["accepted_keys"]:
        return "DUPLICATE", state
    if r.get("policy_profile_hash") != profile_hash or profile_hash != state["policy_profile_hash"]:
        return _reject(state, "REJECT_PROFILE", now_ms, rid)
    if r.get("context_hash") != state["context_hash"]:
        return _reject(state, "REJECT_STALE_CONTEXT", now_ms, rid)
    if type(r.get("expiry_ms")) is not int or r["expiry_ms"] <= now_ms:
        return _reject(state, "REJECT_EXPIRED", now_ms, rid)
    if (any(type(r.get(k)) is not int or r[k] < 0 for k in ("cutoff_ms", "started_ms", "completed_ms"))
            or not r["cutoff_ms"] <= r["started_ms"] <= r["completed_ms"] <= now_ms):
        return _reject(state, "REJECT_MALFORMED", now_ms, rid)
    if state["latest_cutoff_ms"] is not None and r.get("cutoff_ms", -1) < state["latest_cutoff_ms"]:
        return _reject(state, "REJECT_OUT_OF_ORDER", now_ms, rid)
    if r.get("status") == "REJECTED_REQUEST":
        return _reject(state, "REJECT_MALFORMED", now_ms, rid)
    if r.get("status") not in ("ASSESSED", "ABSTAIN", "UNAVAILABLE") or type(r.get("cutoff_ms")) is not int or \
            type(r.get("assessment_key")) is not str or any(type(r.get(k)) is not list for k in _LISTS) or \
            type(r.get("coverage")) is not dict or (r["status"] == "ASSESSED" and "proposed_thesis" not in r):
        return _reject(state, "REJECT_MALFORMED", now_ms, rid)

    scope = r.get("review_scope", _LEGACY)
    if scope is None:
        scope = frozenset()  # not a review job: no statement's review attempt
    elif scope is not _LEGACY:
        if type(scope) is not dict or scope.get("job_id") != r.get("job_id") or \
                type(scope.get("statement_ids")) is not list or \
                any(type(x) is not str for x in scope["statement_ids"]):
            return _reject(state, "REJECT_MALFORMED", now_ms, rid)
        scope = frozenset(scope["statement_ids"])
    else:
        scope = None  # a result written before review scopes existed: the v1.0 rule replays unchanged

    policy = state["lifecycle"]
    nxt = dict(state, version=state["version"] + 1, latest_cutoff_ms=r["cutoff_ms"], last_rejection=None,
               accepted_result_ids=(state["accepted_result_ids"] + [rid])[-500:],
               accepted_keys=(state["accepted_keys"] + [r["assessment_key"]])[-500:])
    adverse = [dict(a, source_revisions=dict(a.get("source_revisions", {})),
                    source_resolutions=dict(a.get("source_resolutions", {}))) for a in state["unresolved_adverse"]]
    resolved = list(state["resolved_adverse"])
    held = {a["finding_id"] for a in adverse}
    statements = {k: dict(v) for k, v in state["statements"].items()}
    records_seen = dict(state["records_seen"])
    records_assessed = dict(state.get("records_assessed", {}))
    used_by_id = {u.get("record_id"): u for u in r["evidence_used"]}

    def supporting_revisions(sources):
        revisions = {}
        for source in sources:
            record_id = source.get("record_id")
            record = used_by_id.get(record_id) or records_seen.get(source.get("accession")) or {}
            if record_id and record.get("record_id") == record_id:
                revisions[record_id] = record.get("revision", 0)
        return revisions

    # Upgrade older v2 latches only from matching record identities, never assume a partial observation
    # proves the supporting version was assessed. Unknown legacy support revisions stay fail-closed.
    for a in adverse:
        a["source_revisions"] = supporting_revisions(a.get("sources") or []) | a["source_revisions"]

    def latch(finding_id, kind, sources, red_flag=None):
        if finding_id in held:
            return
        held.add(finding_id)
        entry = {"finding_id": finding_id, "type": kind, "result_id": rid, "cutoff_ms": r["cutoff_ms"],
                 "sources": sources, "source_revisions": supporting_revisions(sources),
                 "source_resolutions": {}, "resolution_rule": RESOLUTION_RULE}
        if type(red_flag) is dict and red_flag.get("verified") is True:
            # The verified red-flag predicate (IDEA-041) travels with the latch to the EvidenceContext; the
            # consumer looks its action up in the predicate record and the profile's authority.
            entry["red_flag"] = red_flag
            entry["latched_ms"] = now_ms
        adverse.append(entry)

    # A correction can only be established by a complete assessment of the new version: partial coverage could
    # simply have missed the event (red team S4-B g01).
    complete = (r["status"] == "ASSESSED" and (r.get("coverage") or {}).get("complete") is True
                and not any(m.startswith(INCOMPLETE) for m in r["missingness"])
                and not r["conflicts"] and not (r.get("novelty") or {}).get("prior_not_checked"))
    # Revisions and withdrawals first: they can resolve latches and correct statements from the old version.
    present_findings = {f["type"] for f in r.get("event_findings", []) + r.get("findings", [])}
    present_findings.update("FALSIFIER_FIRED:" + f["falsifier_id"] for f in r["falsifiers"] if f["state"] == "FIRED")
    def still_present(kind, accession):
        if kind not in present_findings:
            return False
        if kind.startswith("FALSIFIER_FIRED:"):
            return True
        return any(f["type"] == kind and (not f.get("sources") or any(s.get("accession") == accession
                   for s in f["sources"])) for f in r["event_findings"] + r["findings"])

    invalidated = set()  # statements whose correction proof this result invalidated (R25)
    for used in r.get("evidence_used", []):
        accession, revision = used.get("accession"), used.get("revision", 0)
        seen = records_seen.get(accession)
        assessed = records_assessed.get(accession)
        withdrawn = used.get("quality") == "WITHDRAWN"
        current = (seen is None or revision >= seen["revision"]) and \
                  (assessed is None or revision >= assessed["revision"])
        if current:
            # A newer partial observation cannot inherit correction evidence from its older revision.
            for sid, entry in list(statements.items()):
                keys = {s.get("record_id") for s in entry["records"] if s.get("accession") == accession}
                corrections = entry.get("source_resolutions", {})
                invalid = {k for k in keys if k in corrections and
                           corrections[k]["superseding_hash"] != used.get("content_hash")}
                if invalid:
                    statements[sid] = dict(entry, source_resolutions={k: v for k, v in corrections.items()
                                                                      if k not in invalid})
                    invalidated.add(sid)
            for a in adverse:
                for source in a.get("sources") or []:
                    key = source.get("record_id")
                    correction = a["source_resolutions"].get(key)
                    if source.get("accession") == accession and correction and revision > correction["revision"]:
                        a["source_resolutions"].pop(key)
            if not complete:
                # Nor does a resolved latch keep a resolution proved on an older revision: until the newer one is
                # completely read, the finding may still be there (IDEA-033 R25). A complete read is handled below.
                for a in list(resolved):
                    proof = a.get("source_resolutions") or {}
                    stale = {s.get("record_id") for s in a.get("sources") or [] if s.get("accession") == accession
                             and s.get("record_id") in proof and revision > proof[s.get("record_id")]["revision"]}
                    if stale and a["finding_id"] not in held:
                        resolved.remove(a)
                        held.add(a["finding_id"])
                        adverse.append(dict({k: v for k, v in a.items()
                                             if k not in ("resolved_ms", "resolved_by", "resolution")},
                                            source_revisions=dict(a.get("source_revisions", {})),
                                            source_resolutions={k: v for k, v in proof.items() if k not in stale},
                                            reopened_ms=now_ms))
        if complete and current:
            revised_statement = assessed is None and any(
                source.get("accession") == accession and source.get("content_hash") != used.get("content_hash")
                for entry in statements.values() for source in entry["records"])
            if revised_statement or (assessed is not None and revision > assessed["revision"]) or withdrawn:
                local_statements = [s for s in r["event_statements"] if s.get("accession") == accession]
                present_statements = {s["statement_id"] for s in local_statements}
                # observe() can unify synonymous statement IDs from different records.
                for sid, entry in statements.items():
                    if entry.get("fingerprint") and any(s.get("fingerprint") and
                            lifecycle.relation(s["fingerprint"], entry["fingerprint"]) in ("EXACT", "SEMANTIC_SAME")
                            for s in local_statements):
                        present_statements.add(sid)
                lifecycle.revise(statements, accession=accession, superseding_hash=used.get("content_hash"),
                                 still_present=present_statements, withdrawn=withdrawn, now_ms=now_ms)
            for a in list(adverse):
                srcs = a.get("sources") or []
                corrections = a["source_resolutions"]
                for source in srcs:
                    key = source.get("record_id")
                    baseline = a["source_revisions"].get(key)
                    if source.get("accession") != accession or not key:
                        continue
                    superseded = baseline is not None and revision > baseline and used.get("record_id") != key
                    present = still_present(a["type"], accession)
                    if withdrawn or (superseded and not present):
                        corrections[key] = {"record_id": used.get("record_id"), "revision": revision,
                                            "accession": accession, "resolved_ms": now_ms,
                                            "resolution": "WITHDRAWN" if withdrawn else "CORRECTED"}
                    elif present:
                        corrections.pop(key, None)
                if srcs and all(x.get("record_id") in corrections for x in srcs):
                    adverse.remove(a)
                    held.discard(a["finding_id"])
                    resolved.append(dict(a, resolved_ms=now_ms, resolved_by=used.get("record_id"),
                                         resolution="WITHDRAWN" if all(c["resolution"] == "WITHDRAWN"
                                                                      for c in corrections.values()) else "CORRECTED"))
            records_assessed[accession] = {"revision": revision, "record_id": used.get("record_id"),
                                           "content_hash": used.get("content_hash"), "seen_ms": now_ms}
        if seen is None or revision >= seen["revision"]:
            records_seen[accession] = {"revision": revision, "record_id": used.get("record_id"),
                                       "content_hash": used.get("content_hash"), "seen_ms": now_ms}

    for finding in r.get("event_findings", []):  # re-verified filer/keyword events, any status
        if finding["impact"] == "ADVERSE":
            latch(finding["finding_id"], finding["type"], finding.get("sources") or [], finding.get("red_flag"))
    if r["status"] == "ASSESSED":
        for finding in r["findings"]:
            if finding["impact"] == "ADVERSE":
                latch(finding["finding_id"], finding["type"], finding.get("sources") or [], finding.get("red_flag"))
        for falsifier in r["falsifiers"]:
            fid = "falsifier:" + digest("larp.intel.fired.v1", {"f": falsifier["falsifier_id"], "r": rid})
            if falsifier["state"] == "FIRED":
                sources = [{"accession": u["accession"], "record_id": u["record_id"]} for u in r["evidence_used"]]
                latch(fid, "FALSIFIER_FIRED:" + falsifier["falsifier_id"], sources, falsifier.get("red_flag"))
        # Acknowledgment needs an actual statement-history lookup that completed (S4-B g05).
        history_checked = (r.get("coverage") or {}).get("prior_history", {}).get("STATEMENTS") is True
        for s in r.get("event_statements", []):
            lifecycle.observe(statements, s, result_id=rid, now_ms=now_ms, complete=complete and history_checked,
                              policy=policy, review_scope=scope)
        known = list(state["context"]["known_facts"])
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
    # Correction proof invalidated above and not re-established by this result reopens the review (R25).
    lifecycle.reopen(statements, invalidated, result_id=rid, now_ms=now_ms, policy=policy)
    # A result of a statement's own review job at or after its due time that did not observe it is one attempt (R18,
    # narrowed to the statement's own review job by IDEA-035 A4 / GAP-28).
    lifecycle.missed_reviews(statements, result_id=rid, now_ms=now_ms, policy=policy, review_scope=scope)
    lifecycle.expire(statements, now_ms=now_ms, retention_ms=policy["statement_retention_ms"],
                     max_entries=policy["max_statements"])
    # Correction baselines still needed by an unresolved latch or a registry statement are never evicted (R23).
    keep = {s.get("accession") for a in adverse for s in a.get("sources") or []}
    keep |= {rec.get("accession") for entry in statements.values() for rec in entry["records"]}
    nxt.update(unresolved_adverse=adverse, resolved_adverse=resolved[-200:], statements=statements,
               records_seen=_bounded(records_seen, keep), records_assessed=_bounded(records_assessed, keep))
    gate, reasons = _gate(r, adverse, nxt["availability"], statements, complete)
    # The same reading without Class 2 red-flag latches (IDEA-041, B1): their buy block expires after a set number
    # of sessions, which only the session-aware policy can count. Their latches stay (the finding stays logged), so
    # the plain gate stays ADVERSE; this view lets the policy tell "only expiring blocks remain" from anything else.
    untimed = [a for a in adverse if (a.get("red_flag") or {}).get("class") != 2]
    timed_gate, timed_reasons = _gate(r, untimed, nxt["availability"], statements, complete)
    nxt.update(evidence_gate=gate, gate_reasons=reasons,
               assessed_until_ms=r["expiry_ms"] if gate == "CLEAR" else None,
               gate_excluding_timed=timed_gate, gate_excluding_timed_reasons=timed_reasons,
               assessed_until_excluding_timed_ms=r["expiry_ms"] if timed_gate == "CLEAR" else None)
    return "ACCEPT", nxt


def _bounded(records: dict, keep: set, limit: int = MAX_RECORDS) -> dict:
    """At most `limit` accessions besides those in `keep`, dropping the least recently seen first.

    Accession numbers begin with the filer agent's CIK, so their string order is not their age (IDEA-033 R23).
    Entries written before `seen_ms` existed count as oldest.
    """
    if len(records) > limit:
        ranked = sorted(records, key=lambda a: (a in keep, records[a].get("seen_ms", 0), a))
        for accession in ranked[: len(records) - limit]:
            if accession not in keep:
                del records[accession]
    return dict(sorted(records.items()))


def _gate(r: dict, adverse: list, availability: str, statements: dict, complete: bool) -> tuple:
    if adverse:
        return "ADVERSE", sorted({a["type"] for a in adverse})
    pending = sorted(s["statement_id"] for s in statements.values() if s["status"] == "PENDING_REVIEW")
    if availability != "AVAILABLE":
        return "UNKNOWN", [f"LATEST_{availability}"] + list(r.get("reasons", [])) + (
            ["PENDING_STATEMENT_REVIEW"] if pending else [])
    reasons = [m for m in r["missingness"] if m.startswith(INCOMPLETE)]
    if not complete:
        reasons.append("COVERAGE_INCOMPLETE")
    if r["conflicts"]:
        reasons.append("CONFLICTS")
    if pending:
        reasons.append("PENDING_STATEMENT_REVIEW")  # not erased by an unrelated clean result
    if (r.get("novelty") or {}).get("prior_not_checked"):
        reasons.append("PRIOR_NOT_CHECKED")  # a contradiction with earlier filings cannot be excluded
    if r["proposed_thesis"] is None or r["proposed_thesis"]["status"] in ("UNKNOWN",):
        reasons.append("THESIS_UNKNOWN")
    return ("UNKNOWN", sorted(set(reasons))) if reasons else ("CLEAR", [])


def consume(state: dict, now_ms: int) -> dict:
    """As-of view of the stored state at `now_ms`. Consumers read this, never `evidence_gate` directly.

    CLEAR becomes STALE once `now_ms >= assessed_until_ms`; ADVERSE latches stay; pending, exhausted and
    corrected statements are listed separately as evidence uncertainty (not permission).
    """
    gate, reasons = state["evidence_gate"], list(state["gate_reasons"])
    if gate == "CLEAR" and (state["assessed_until_ms"] is None or now_ms >= state["assessed_until_ms"]):
        gate, reasons = "STALE", ["ASSESSMENT_EXPIRED"]
    # States written before IDEA-041 have no timed view: they read as UNKNOWN, never as clear.
    timed, timed_reasons = state.get("gate_excluding_timed", "UNKNOWN"), list(state.get(
        "gate_excluding_timed_reasons", ["NO_TIMED_VIEW"]))
    timed_until = state.get("assessed_until_excluding_timed_ms")
    if timed == "CLEAR" and (timed_until is None or now_ms >= timed_until):
        timed, timed_reasons = "STALE", ["ASSESSMENT_EXPIRED"]
    due = lifecycle.due_reviews(state["statements"], now_ms)
    by_status = {}
    for s in state["statements"].values():
        by_status.setdefault(s["status"], []).append(s["statement_id"])
    return {"schema": "EvidenceView.v1", "issuer_id": state["issuer_id"], "state_version": state["version"],
            "as_of_ms": now_ms, "evidence_gate": gate, "gate_reasons": reasons,
            "assessed_until_ms": state["assessed_until_ms"], "latest_cutoff_ms": state["latest_cutoff_ms"],
            "availability": state["availability"], "last_rejection": state["last_rejection"],
            "adverse": [{"finding_id": a["finding_id"], "type": a["type"], "resolution_rule": a["resolution_rule"]}
                        for a in state["unresolved_adverse"]],
            "evidence_gate_excluding_timed": timed, "gate_excluding_timed_reasons": timed_reasons,
            "assessed_until_excluding_timed_ms": timed_until,
            "statements": {k: sorted(v) for k, v in sorted(by_status.items())},
            "due_reviews": [s["statement_id"] for s in due],
            # When the earliest listed review fell due: fixes the review job's definition (IDEA-033 R15).
            "review_due_ms": due[0]["review"]["next_due_ms"] if due else None,
            "thesis": (state["context"]["thesis"] or {}).get("status")}


def state_document(state: dict) -> Document:
    if state.get("schema") != SCHEMA:
        raise IntelligenceError("Unknown evidence state schema")
    return Document.from_dict(state)
