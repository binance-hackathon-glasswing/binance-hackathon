"""Assessor bake-off (B8, IDEA-041 AC-2.4): the deterministic baseline and each candidate model on the same filings.

`run(candidates, requests, make_assessor)` assesses every request with every candidate through the real assessor,
verifier and budget, and `report(...)` computes, per candidate:

- schema-valid rate: model replies that parse as one allowed assessor action / model replies received. A reply is
  an HTTP-200 provider message; HTTP errors (429, 5xx), provider error objects and timeouts are `provider_errors`,
  reported separately and never counted as schema-invalid (IDEA-041 R15);
- claim-verification pass rate: claims the model proposed at FINISH that the verifier accepted / proposed;
- latency: assessment elapsed time p50/p95/max on the assessor clock, and how many stayed within 60 s;
- tool calls: max and mean (the declared ceiling is 6);
- cost per assessment from the adapters' token usage and declared price (UNKNOWN when no price was given). A call
  still in flight when an assessment was abandoned at its deadline, a timed-out call and an adapter failure have
  no usage record although the provider may bill them: they are counted (`calls_abandoned_at_deadline`,
  `calls_without_usage`) and the cost is then a lower bound (R10);
- status counts, and agreement of finding types with the baseline on the same filing.

This is an engineering comparison on real filings, not a profit claim and not a validated accuracy estimate:
there are no independent labels here (that is T01, `realeval.py`). The live wiring (EDGAR fetch, artifact
store, credentials) is `python -m larp.sources.live bakeoff`.
"""

from larp.intelligence.common import IntelligenceError
from larp.intelligence.models import parse_output

SCHEMA = "AssessorBakeoff.v1"
DEADLINE_MS = 60_000


def run(candidates: dict, requests: list, make_assessor) -> dict:
    """{candidate name: [AssessmentResult dicts in request order]}. `candidates`: {name: model adapter}."""
    out = {}
    for name, model in candidates.items():
        assessor = make_assessor(model)
        out[name] = [assessor.assess(request).read() for request in requests]
    return out


def _quantile(values: list, q: float):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1) + 0.5))]


def _proposed_claims(result: dict) -> int:
    finish = [s["response"]["output"] for s in result["model_io"].get("steps", [])
              if "response" in s and type(s["response"].get("output")) is dict
              and s["response"]["output"].get("action") == "FINISH"]
    claims = finish[-1].get("claims") if finish else None
    return len(claims) if type(claims) is list else 0


def _provider_error(reply: dict) -> bool:
    """No model message came back: a timeout, an HTTP error status or the provider's own error object."""
    error = reply.get("error") or ""
    return reply["status"] == "TIMEOUT" or error.startswith("HTTP ") or error == "PROVIDER_ERROR" or (
        reply["status"] == "ERROR" and reply.get("raw_response_sha256") is None)


def metrics(results: list, baseline: list | None = None) -> dict:
    replies = valid = proposed = rejected = provider_errors = abandoned = unmetered = 0
    elapsed, tools, costs, unknown_cost, statuses, agree = [], [], [], 0, {}, []
    for i, r in enumerate(results):
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        io = r["model_io"]
        if (io.get("in_flight") or {}).get("status") == "IN_FLIGHT_AT_DEADLINE":
            abandoned += 1
        for step in io.get("steps", []):
            reply = step.get("response")
            if reply is None or reply["status"] == "TIMEOUT":
                unmetered += 1  # an adapter defect or a timed-out call: the provider may have billed it
            if reply is None:
                continue
            if _provider_error(reply):
                provider_errors += 1
                continue
            replies += 1
            try:
                if reply["status"] == "OK":
                    parse_output(reply["output"])
                    valid += 1
            except IntelligenceError:
                pass
        if r["status"] != "REJECTED_REQUEST":
            proposed += _proposed_claims(r)
            rejected += len(r.get("rejected_claims") or [])
            elapsed.append(r["budget_used"]["elapsed_ms"])
            tools.append(r["budget_used"]["tool_calls"] or 0)
            amount = (r.get("cost") or {}).get("amount_micro_usd")
            if amount is None:
                unknown_cost += 1
            else:
                costs.append(amount)
        if baseline is not None:
            agree.append({f["type"] for f in r.get("findings", [])} == {f["type"] for f in baseline[i].get("findings", [])})
    n = len(results)
    return {
        "assessments": n, "status_counts": dict(sorted(statuses.items())),
        "model_replies": replies, "provider_errors": provider_errors,
        "schema_valid_rate": None if not replies else round(valid / replies, 4),
        "claims_proposed": proposed, "claims_rejected": rejected,
        "claim_verification_pass_rate": None if not proposed else round((proposed - rejected) / proposed, 4),
        "latency_ms": {"p50": _quantile(elapsed, 0.5), "p95": _quantile(elapsed, 0.95),
                       "max": max(elapsed, default=None),
                       "within_deadline": sum(1 for e in elapsed if e <= DEADLINE_MS)},
        "tool_calls": {"max": max(tools, default=None), "mean": None if not tools else round(sum(tools) / len(tools), 3)},
        "cost_micro_usd": {"total_known": sum(costs), "per_assessment_mean": None if not costs else sum(costs) // len(costs),
                           "assessments_with_unknown_cost": unknown_cost,
                           "calls_abandoned_at_deadline": abandoned, "calls_without_usage": unmetered,
                           "lower_bound": abandoned + unmetered > 0},
        "finding_agreement_with_baseline": None if baseline is None or not agree else round(sum(agree) / len(agree), 4),
    }


def report(results: dict, *, baseline_name: str, filings: list, commit: str, generated_ms: int, identities: dict) -> dict:
    """AssessorBakeoff.v1. `filings`: [{accession, issuer_id, form, record_id}] in request order."""
    if baseline_name not in results:
        raise IntelligenceError("The bake-off needs the deterministic baseline as a candidate")
    baseline = results[baseline_name]
    return {"schema": SCHEMA, "commit": commit, "generated_ms": generated_ms, "baseline": baseline_name,
            "filings": filings,
            "candidates": {name: {"model": identities[name], "metrics": metrics(rs, None if name == baseline_name
                                                                                else baseline)}
                           for name, rs in sorted(results.items())},
            "per_filing": [{"accession": f["accession"],
                            **{name: {"status": rs[i]["status"], "reasons": rs[i]["reasons"],
                                      "findings": sorted(x["type"] for x in rs[i].get("findings", [])),
                                      "result_id": rs[i].get("result_id")} for name, rs in sorted(results.items())}}
                           for i, f in enumerate(filings)],
            "note": "Engineering comparison on real filings; no independent labels (T01 is separate); not a profit "
                    "claim. Report as PASS/FAIL/INCONCLUSIVE against IDEA-041 AC-2.4 with this commit."}


__all__ = ["run", "metrics", "report", "SCHEMA"]
