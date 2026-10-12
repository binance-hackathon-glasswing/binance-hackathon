"""Consume PR #4's millisecond AssessmentResult vocabulary without trade authority.

The runtime supplies the exact request and current issuer context. This is a
policy input validator, not Yao's evidence verifier or thesis-state reducer.
"""

from datetime import datetime, timezone

from larp.contracts import ContractError, Document
from .schema import integer


def epoch_ms(now):
    delta = now - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000


def _hash(value):
    return (type(value) is str and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def consume(snapshot, state, market, falsifier_ids):
    c, accepted, diagnostics = snapshot.context.read(), {}, []
    issuer_symbols = {m["underlying_id"]: symbol for symbol, m in market.items() if m is not None}
    now = epoch_ms(snapshot.observed_at)
    seen = set()
    for a in c.get("assessments", []):
        symbol = issuer_symbols.get(a.get("issuer_id")) if type(a) is dict else None
        reason = None
        try:
            required = {"job_id", "issuer_id", "cutoff_ms", "completed_ms", "expiry_ms",
                        "status", "falsifiers", "claims", "proposed_thesis", "evidence_used"}
            if type(a) is not dict or a.get("schema") not in ("AssessmentResult.v1", "AssessmentResult.v2") or not required <= a.keys():
                raise ContractError("ASSESSMENT_SCHEMA_UNRECOGNISED")
            if symbol is None:
                raise ContractError("ASSESSMENT_ISSUER_UNAVAILABLE")
            if symbol in seen:
                accepted.pop(symbol, None)
                raise ContractError("ASSESSMENT_DUPLICATE_ISSUER")
            seen.add(symbol)
            request = c.get("assessment_requests", {}).get(a["issuer_id"])
            if not request or request.get("schema") != "AssessmentRequest.v1":
                raise ContractError("ASSESSMENT_REQUEST_MISSING")
            context = state.data.read().get("evidence_contexts", {}).get(
                a["issuer_id"], {"thesis": None, "known_facts": []})
            expected_hash = Document.from_dict(context).digest("larp.intel.context.v1")
            if request.get("context") != context or request.get("context_hash") != expected_hash:
                raise ContractError("ASSESSMENT_STALE_CONTEXT")
            for key, expected in (("run_id", snapshot.run_id), ("issuer_id", a["issuer_id"]),
                                  ("policy_profile_hash", snapshot.policy_profile_hash),
                                  ("context_hash", expected_hash), ("job_id", request.get("job_id"))):
                if a.get(key) != expected or request.get(key) != expected:
                    raise ContractError("ASSESSMENT_IDENTITY_MISMATCH")
            cutoff, completed, expiry = [integer(a[k]) for k in ("cutoff_ms", "completed_ms", "expiry_ms")]
            if cutoff != request.get("cutoff_ms") or not cutoff <= completed <= now < expiry:
                raise ContractError("ASSESSMENT_STALE_OR_FUTURE")
            if a["schema"] == "AssessmentResult.v2":
                from larp.runtime.schema import assessment_result
                assessment_result(Document.from_dict(a), Document.from_dict(request), now)
            if not all(_hash(a.get(k)) for k in ("model_hash", "prompt_hash")):
                raise ContractError("ASSESSMENT_PROVENANCE_INVALID")
            if a["status"] != "ASSESSED":
                raise ContractError("ASSESSMENT_NOT_ASSESSED")
            if any(type(a.get(k)) is not list for k in ("claims", "falsifiers", "evidence_used")):
                raise ContractError("ASSESSMENT_SCHEMA_UNRECOGNISED")
            records = {r["record_id"] for r in a["evidence_used"]
                       if integer(r["available_ms"]) <= cutoff and _hash(r.get("content_hash"))}
            prior = {f["fact_id"]: f for f in context["known_facts"]}
            claims = {f["fact_id"]: f for f in a["claims"]}
            facts = {**prior, **claims}
            def supported(fact):
                if not fact or fact.get("source", {}).get("record_id") not in records:
                    # Earlier comparison facts belong to the committed issuer context.
                    if not fact or fact.get("fact_id") not in prior:
                        return False
                source = fact.get("source", {})
                if integer(source["available_ms"]) > cutoff:
                    return False
                span = fact.get("span")
                return (bool(span and span.get("text") and _hash(span.get("doc")))
                        or (fact.get("basis") == "ITEM_METADATA"
                            and fact.get("metric", "").startswith("ITEM:") and bool(source.get("accession"))))
            findings = []
            thesis = a["proposed_thesis"] or {}
            for f in a["falsifiers"]:
                ids = f.get("fact_ids", [])
                if f.get("falsifier_id") not in falsifier_ids or f.get("state") != "FIRED" or not ids:
                    continue
                support = [facts.get(i) for i in ids]
                direct_support = all(supported(fact) for fact in support)
                # PR #4 emits verified comparison findings, but only CURRENT facts
                # in claims. A prior fact fetched during the call is not necessarily
                # in the initial context. Consume the harness comparison, never a
                # model-I/O summary or a reconstructed price/semantic comparison.
                comparison = next((finding for finding in a.get("findings", [])
                    if f.get("type") in ("GUIDANCE_LOWERED", "REPORTED_BELOW_PRIOR_GUIDANCE")
                    and finding.get("type") == f["type"] and finding.get("fact_ids") == ids
                    and finding.get("impact") == "ADVERSE"
                    and finding.get("finding_id") in thesis.get("finding_ids", [])
                    and f["falsifier_id"] in thesis.get("fired_falsifiers", [])
                    and finding.get("finding_id") == "find:" + Document.from_dict(
                        {k: v for k, v in finding.items() if k != "finding_id"}).digest("larp.intel.finding.v1")), None)
                producer_support = (comparison is not None
                                    and any(fact and supported(fact) for fact in support)
                                    and all(fact is None or supported(fact) for fact in support))
                if direct_support or producer_support:
                    findings.append({"predicate_id": f["falsifier_id"], "fact_ids": ids,
                        "verification_basis": "SUPPORTED_FACTS" if direct_support else "PRODUCER_VERIFIED_COMPARISON"})
                    if not direct_support:
                        diagnostics.append({"symbol": symbol, "reason": "ASSESSMENT_PRIOR_SUPPORT_IN_PRODUCER_FINDING",
                                            "finding_id": comparison["finding_id"],
                                            "prior_fact_ids": [i for i in ids if i not in facts]})
                else:
                    diagnostics.append({"symbol": symbol, "reason": "ASSESSMENT_FALSIFIER_UNSUPPORTED"})
            clear = (thesis.get("status") == "INTACT" and thesis.get("based_on_context_hash") == expected_hash
                     and bool(claims) and all(supported(fact) for fact in claims.values())
                     and not a.get("missingness") and not a.get("conflicts")
                     and not (a.get("novelty") or {}).get("prior_not_checked")
                     and not any(f.get("state") in ("FIRED", "UNKNOWN") for f in a["falsifiers"])
                     and not any(f.get("impact") == "ADVERSE" for f in a.get("findings", []))
                     and not any(h.get("novelty") != "REPEATED" for h in a.get("hypothetical_events", [])))
            accepted[symbol] = {"findings": findings, "fresh_review": clear}
        except (KeyError, TypeError, AttributeError, ContractError) as exc:
            reason = str(exc) if isinstance(exc, ContractError) else "ASSESSMENT_SCHEMA_UNRECOGNISED"
        diagnostics.append({"symbol": symbol, "reason": reason or "ASSESSMENT_ACCEPTED"})
    return accepted, diagnostics
