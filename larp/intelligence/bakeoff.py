"""Assessor bake-off (B8, IDEA-041 AC-2.4): the deterministic baseline and each candidate model on the same filings.

`run(candidates, requests, make_assessor)` assesses every request with every candidate through the real assessor,
verifier and budget, and `report(...)` computes, per candidate:

- schema-valid rate: model replies that parse as one allowed assessor action / model replies received. A reply is
  an HTTP-200 provider message; HTTP errors (429, 5xx), provider error objects and timeouts are `provider_errors`,
  reported separately and never counted as schema-invalid (IDEA-041 R15);
- claim-verification pass rate: claims the model proposed at FINISH that the verifier accepted / proposed;
- latency: assessment elapsed time and timeliness under its recorded request budget;
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

import json

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError, sha256_hex
from larp.intelligence.models import parse_output
from larp.intelligence.providers import reply_audit
from larp.intelligence.time_budget import MAX_ASSESSMENT_MS

SCHEMA = "AssessorBakeoff.v1"
DEADLINE_MS = 60_000  # frozen legacy computation only; public metrics requires bound metadata or explicit override


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


def _frozen_metrics(results: list, baseline: list | None = None) -> dict:
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


def _bound(value):
    return type(value) is int and 0 < value <= MAX_ASSESSMENT_MS


def _timing(result, request=None, historical_deadline_ms=None):
    allowed = result.get('budget_allowed')
    bound = allowed.get('deadline_ms') if type(allowed) is dict else None
    basis = 'RECORDED_REQUEST'
    if request is not None:
        request = request.read() if isinstance(request, Document) else request
        expected = result.get('request_sha256')
        if expected is not None and expected != sha256_hex(Document.from_dict(request).payload):
            raise IntelligenceError('Report request/result identity mismatch')
        budget = request.get('budget')
        supplied = budget.get('deadline_ms') if type(budget) is dict else None
        if bound is not None and bound != supplied:
            raise IntelligenceError('Report request/result budget mismatch')
        bound, basis = supplied, 'SUPPLIED_IMMUTABLE_REQUEST'
    if historical_deadline_ms is not None:
        if not _bound(historical_deadline_ms):
            raise IntelligenceError('Invalid explicit historical reporting deadline')
        bound, basis = historical_deadline_ms, 'EXPLICIT_HISTORICAL_PROTOCOL'
    elapsed = (result.get('budget_used') or {}).get('elapsed_ms')
    valid = _bound(bound) and type(elapsed) is int and elapsed >= 0
    timely = elapsed <= bound if valid else None
    accepted = result['status'] == 'ASSESSED' and timely is True
    started, completed = result.get('started_ms'), result.get('completed_ms')
    delay = completed-started if (accepted and type(started) is int and
            type(completed) is int and completed >= started) else None
    return dict(deadline_ms=bound if _bound(bound) else None, basis=basis if _bound(bound) else 'UNKNOWN',
                elapsed_ms=elapsed, within_deadline=timely, usable_within_deadline=accepted,
                usable_result_delay_ms=delay, delay_basis='ASSESSOR_START_TO_RESULT')


def _reply_diagnostics(reply, provider, artifact_reader):
    audit, recovered = {}, False
    if artifact_reader is not None and reply.get('raw_response_artifact'):
        ref = reply['raw_response_artifact']
        raw = artifact_reader(ref)
        if raw is not None:
            if type(raw) is not bytes or sha256_hex(raw) != ref or (
                    reply.get('raw_response_sha256') not in (None, ref)):
                raise IntelligenceError('Reporting raw response artifact hash mismatch')
            try:
                audit = reply_audit(json.loads(raw), provider)
            except (ValueError, UnicodeDecodeError, RecursionError):
                pass
    usage = audit.get('usage') or reply.get('usage') or {}
    known = (all(type(usage.get(k)) is int and 0 <= usage[k] <= 10**9
                 for k in ('input_tokens', 'output_tokens')) and
             ('usage' in audit or reply.get('usage_known') is True or
              (reply.get('usage_known') is None and reply.get('status') == 'OK')))
    if 'usage' in audit:
        recovered = audit['usage'] != reply.get('usage') or reply.get('usage_known') is False
    finish = audit.get('finish_reason') or reply.get('finish_reason')
    error = reply.get('error') or ''
    if finish in ('length', 'max_output_tokens', 'max_tokens') or error in ('AIAND_TOKEN_LIMIT', 'STOP_MAX_TOKENS'):
        cause = 'token_limit'
    elif error in ('AIAND_MULTIPLE_OR_MISSING_CHOICES', 'AIAND_INCOMPLETE_OR_MULTIPLE_CHOICES'):
        cause = 'choices_or_legacy_incomplete'
    elif reply.get('status') == 'TIMEOUT':
        cause = 'deadline'
    elif _provider_error(reply):
        cause = 'transport_or_provider'
    elif reply.get('status') != 'OK':
        cause = 'codec_or_schema'
    else:
        try:
            parse_output(reply.get('output'))
            cause = 'usable_action'
        except IntelligenceError:
            cause = 'codec_or_schema'
    return audit, usage if known else None, recovered, cause


def metrics(results: list, baseline: list | None = None, *, requests=None,
            historical_deadline_ms=None, artifact_reader=None, _stages=True) -> dict:
    """Frozen M5 denominator plus additive, request-bound diagnostics.

    Raw recovery reads hash-checked originals into a separate report, never into
    decision records or accounting. Historical thresholds require an explicit
    argument; missing stage/request budgets stay unknown.
    """
    if requests is not None and len(requests) != len(results):
        raise IntelligenceError('Report needs one immutable request per result')
    value = _frozen_metrics(results, baseline)
    timings, causes, usage, rejected_usage, recovered_usage = [], {}, dict(input_tokens=0, output_tokens=0), 0, 0
    unmetered = late_count = abandoned = reasoning = unknown_prices = unresolved = 0
    stages = {}
    for i, result in enumerate(results):
        timings.append(_timing(result, None if requests is None else requests[i], historical_deadline_ms))
        io = result['model_io']
        inflight = io.get('in_flight_calls') or ([io['in_flight']] if io.get('in_flight') else [])
        abandoned += len({x['request_id'] for x in inflight if x.get('status') == 'IN_FLIGHT_AT_DEADLINE'})
        seen = set()
        entries = [(s, False) for s in io.get('steps', [])]
        entries += [(dict(response=e['response'], model=e.get('model', {})), True)
                    for e in io.get('late_responses', [])]
        for step, late in entries:
            reply = step.get('response')
            if reply is None:
                unmetered += 1
                causes['adapter_error'] = causes.get('adapter_error', 0) + 1
                continue
            key = reply.get('request_id')
            if key in seen:
                continue
            seen.add(key)
            late_count += int(late)
            provider = (step.get('model') or step.get('request', {}).get('model') or result.get('model') or {}).get('provider')
            audit, tokens, recovered, cause = _reply_diagnostics(reply, provider, artifact_reader)
            causes[cause] = causes.get(cause, 0) + 1
            if tokens is None:
                unmetered += 1
            else:
                for k in usage:
                    usage[k] += tokens[k]
                details = audit.get('usage_details') or reply.get('usage_details') or {}
                reasoning += details.get('reasoning_tokens', 0)
                if reply['status'] != 'OK' or late:
                    rejected_usage += tokens['output_tokens']
                if recovered:
                    original = (reply.get('usage') or {}).get('output_tokens')
                    recovered_usage += max(0, tokens['output_tokens'] - (original if type(original) is int else 0))
            if (reply.get('cost') or {}).get('amount_micro_usd') is None:
                unknown_prices += 1
        unresolved += max(0, io.get('requests_started', len(io.get('steps', [])))
                          - len(io.get('steps', [])) - sum(late for _, late in entries))
        if _stages:
            for stage in result.get('routing', {}).get('stages', []):
                record = None
                if artifact_reader is not None and stage.get('result_artifact'):
                    raw = artifact_reader(stage['result_artifact'])
                    if raw is not None:
                        if sha256_hex(raw) != stage['result_artifact']:
                            raise IntelligenceError('Reporting stage artifact hash mismatch')
                        record = json.loads(raw)
                        if record.get('result_id') != stage['result_id']:
                            raise IntelligenceError('Reporting stage identity mismatch')
                if record is None:
                    record = dict(stage, reasons=stage.get('reasons', []),
                        model_io=dict(steps=[s for s in io.get('steps', []) if s.get('routing_stage') == stage['stage']],
                                      tool_calls=[]),
                        budget_used=stage.get('budget_used', dict(elapsed_ms=0, tool_calls=0)))
                stages.setdefault(stage['stage'], []).append(record)
    elapsed = value['latency_ms']
    elapsed.update(within_deadline=sum(t['within_deadline'] is True for t in timings),
                   unknown_deadline=sum(t['within_deadline'] is None for t in timings),
                   over_deadline=sum(t['within_deadline'] is False for t in timings),
                   usable_within_deadline=sum(t['usable_within_deadline'] for t in timings))
    delays = [t['usable_result_delay_ms'] for t in timings if t['usable_result_delay_ms'] is not None]
    value['timing'] = dict(per_result=timings, usable_result_delay_ms=dict(
        p50=_quantile(delays, .5), p95=_quantile(delays, .95), max=max(delays, default=None)),
        unavailable_jobs=sum(r['status'] == 'UNAVAILABLE' for r in results),
        busy_not_started_jobs=sum('ROUTING_GROUP_BUSY' in r.get('reasons', []) for r in results),
        late_audit_only_replies=late_count)
    value['failure_causes'] = dict(sorted(causes.items()),
        unsupported_claim_assessments=sum('UNSUPPORTED_CLAIM' in r.get('reasons', []) for r in results),
        deadline_failed_assessments=sum(any('DEADLINE' in x or 'TIME_BUDGET' in x or x == 'MODEL_TIMEOUT'
                                           for x in r.get('reasons', [])) for r in results))
    value['schema_valid_numerator'] = sum(
        1 for r in results for s in r['model_io'].get('steps', [])
        if _schema_valid(s.get('response')))
    value['schema_valid_denominator'] = value['model_replies']
    value['claim_verification_numerator'] = value['claims_proposed'] - value['claims_rejected']
    value['claim_verification_denominator'] = value['claims_proposed']
    value['usage'] = dict(known=usage, known_reasoning_tokens=reasoning,
        rejected_or_late_output_tokens=rejected_usage, recovered_output_tokens=recovered_usage,
        calls_without_trustworthy_usage=unmetered + unresolved, unrecorded_calls=unresolved,
        lower_bound=bool(unmetered or unresolved))
    value['cost_micro_usd'].update(calls_without_usage=unmetered, calls_abandoned_at_deadline=abandoned,
        replies_without_known_price=unknown_prices,
        lower_bound=bool(unmetered or abandoned or unknown_prices or
                         value['cost_micro_usd']['assessments_with_unknown_cost']))
    if _stages:
        value['by_stage'] = {name: metrics(rs, artifact_reader=artifact_reader, _stages=False)
                             for name, rs in sorted(stages.items())}
    return value


def _schema_valid(reply):
    if reply is None or _provider_error(reply) or reply['status'] != 'OK':
        return False
    try:
        parse_output(reply['output'])
        return True
    except IntelligenceError:
        return False


def report(results: dict, *, baseline_name: str, filings: list, commit: str, generated_ms: int, identities: dict,
           requests=None, historical_deadline_ms=None, artifact_reader=None) -> dict:
    """AssessorBakeoff.v1. `filings`: [{accession, issuer_id, form, record_id}] in request order."""
    if baseline_name not in results:
        raise IntelligenceError("The bake-off needs the deterministic baseline as a candidate")
    baseline = results[baseline_name]
    return {"schema": SCHEMA, "commit": commit, "generated_ms": generated_ms, "baseline": baseline_name,
            "filings": filings,
            "candidates": {name: {"model": identities[name], "metrics": metrics(rs, None if name == baseline_name
                                                                                else baseline,
                                                                                requests=requests,
                                                                                historical_deadline_ms=historical_deadline_ms,
                                                                                artifact_reader=artifact_reader)}
                           for name, rs in sorted(results.items())},
            "per_filing": [{"accession": f["accession"],
                            **{name: {"status": rs[i]["status"], "reasons": rs[i]["reasons"],
                                      "findings": sorted(x["type"] for x in rs[i].get("findings", [])),
                                      "result_id": rs[i].get("result_id"),
                                      "request_sha256": rs[i].get("request_sha256"),
                                      "config_sha256": rs[i].get("config_sha256"),
                                      "prompt_hash": rs[i].get("prompt_hash"),
                                      "evidence_used": rs[i].get("evidence_used"),
                                      "timing": _timing(rs[i], None if requests is None else requests[i],
                                                        historical_deadline_ms)}
                               for name, rs in sorted(results.items())}}
                           for i, f in enumerate(filings)],
            "note": "Engineering comparison on real filings; no independent labels (T01 is separate); not a profit "
                    "claim. Diagnostic recovery never changes frozen M5 denominators, source results or verdicts.",
            "reporting_protocol": dict(historical_deadline_ms=historical_deadline_ms,
                missing_budget="UNKNOWN", raw_usage_recovery=artifact_reader is not None),
            "request_sha256": None if requests is None else [
                sha256_hex((r if isinstance(r, Document) else Document.from_dict(r)).payload) for r in requests]}


__all__ = ["run", "metrics", "report", "SCHEMA"]
