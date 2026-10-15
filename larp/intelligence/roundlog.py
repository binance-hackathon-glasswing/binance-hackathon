"""ModelTrace.v1: what Keegan's round-log builder needs from an assessment (DR-07, interface I5, IDEA-041 part 5).

`model_trace(result)` reads an AssessmentResult (v2) and returns, for the official ai-seeds round log and our own
journal:

- every model call: request ID, status, error, latency, usage, cost, served model, and the SHA-256 plus artifact
  address of the exact request and reply bytes when the adapter stored them (hosted adapters always do), otherwise
  the canonical hash of the in-record request/response (the rule baseline keeps both in the record);
- every tool call with its arguments, status and result hash;
- `model_called` with `no_model_call_reason`, so a round with no model call says so;
- `cot`: text built only from the provider's own reasoning summaries (verbatim) and the harness's recorded steps
  and verified rationale. Nothing is paraphrased or invented; where no summary was returned the text says so.

Raw chain of thought is not required in daily traces (F-62); provider summaries go in `cot` (F-102, participant-kit
K15, SKILL.md Q-16). Encrypted or redacted reasoning is never put in `cot`; those bytes stay in the stored reply.
`max_cot_chars` truncates with an explicit marker; the full records stay in the result's `model_io` and artifacts.
"""

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError

SCHEMA = "ModelTrace.v1"
TRUNCATED = " [cot truncated; complete records are in the assessment's model_io and stored artifacts]"


def _hash(value) -> str:
    return Document.from_dict({"v": value}).digest("larp.intel.model-io.v1")


def _call(step: dict, index: int) -> dict:
    if "response" not in step:  # the adapter raised: no reply exists
        value = {"index": index, "request_id": step.get("request_id"), "status": "ADAPTER_ERROR",
                "error": step.get("error"), "latency_ms": None, "usage": None, "cost": None, "served_model": None,
                "request_sha256": None, "request_artifact": None, "response_sha256": None, "response_artifact": None,
                "reasoning_summary": None}
        if step.get('routing_stage'):
            value.update(routing_stage=step['routing_stage'], model=step['model'])
        return value
    request, reply = step["request"], step["response"]
    value = {"index": index, "request_id": reply["request_id"], "status": reply["status"], "error": reply["error"],
            "latency_ms": reply["latency_ms"], "usage": reply["usage"], "cost": reply["cost"],
            "served_model": reply["served_model"],
            # Exact bytes when stored; otherwise the canonical hash of the in-record request (rule baseline).
            "request_sha256": reply["request_payload_sha256"] or _hash(request),
            "request_artifact": reply["request_payload_artifact"],
            "response_sha256": reply["raw_response_sha256"], "response_artifact": reply["raw_response_artifact"],
            "reasoning_summary": reply["reasoning_summary"]}
    if step.get('routing_stage'):
        value['routing_stage'] = step['routing_stage']
        value['model'] = request.get('model', {})
    if reply.get('provider_metadata'):
        value['provider_metadata'] = reply['provider_metadata']
    return value


def model_trace(result: dict, *, max_cot_chars: int | None = None) -> dict:
    if result.get("schema") != "AssessmentResult.v2" or type(result.get("model_io")) is not dict:
        raise IntelligenceError("model_trace needs an AssessmentResult.v2 with model_io")
    io = result["model_io"]
    calls = [_call(step, i) for i, step in enumerate(io.get("steps", []))]
    called = io.get("model_called", bool(calls))
    reason = io.get("no_model_call_reason") or (None if called else io.get("note") or "NOT_CALLED")
    tools = [{"index": t["index"], "tool": t["tool"], "args": t["args"], "status": t["status"], "error": t["error"],
              "result_sha256": t["result_sha256"], "result_artifact": t.get("result_artifact"),
              "latency_ms": t.get("latency_ms")} for t in io.get("tool_calls", [])]
    model = result.get("model") or {}
    lines = [f"Evidence assessment for {result.get('issuer_id')}: {result.get('status')}"
             + (f" ({', '.join(result.get('reasons') or [])})" if result.get("reasons") else "") + "."]
    if not called:
        lines.append(f"No model call: {reason}.")
    for call in calls:
        summary = call["reasoning_summary"]
        actual_model = call.get('model') or model
        lines.append(f"Model call {call['index'] + 1} ({actual_model.get('provider')}/{actual_model.get('model_id')}, "
                     f"{call['status']}{', ' + call['error'] if call['error'] else ''}): "
                     + (f"provider reasoning summary: {summary}" if summary else "no reasoning summary returned."))
    for tool in tools:
        lines.append(f"Tool {tool['tool']} {Document.from_dict(tool['args']).payload.decode()} -> {tool['status']}"
                     + (f" ({tool['error']})" if tool["error"] else "") + ".")
    if io.get("requests_started", len(calls)) > len(calls):
        lines.append(f"{io['requests_started'] - len(calls)} model call(s) were in flight at the deadline; "
                     f"their replies are not part of this assessment.")
    if result.get("rationale"):
        lines.append(f"Verified result: {result['rationale']}")
    cot = "\n".join(lines)
    if max_cot_chars is not None and len(cot) > max_cot_chars:
        cot = cot[: max(0, max_cot_chars - len(TRUNCATED))] + TRUNCATED
    trace = {"schema": SCHEMA, "result_id": result.get("result_id"), "job_id": result.get("job_id"),
            "issuer_id": result.get("issuer_id"), "status": result.get("status"), "reasons": result.get("reasons"),
            "model": model, "model_hash": result.get("model_hash"), "prompt_hash": result.get("prompt_hash"),
            "model_called": called, "no_model_call_reason": None if called else reason,
            "requests_started": io.get("requests_started", len(calls)), "calls": calls, "tool_calls": tools,
            "cost": result.get("cost"), "cot": cot}
    if result.get('routing'):
        trace['routing'] = result['routing']
        trace['in_flight_calls'] = io.get('in_flight_calls', [])
    return trace


__all__ = ["model_trace", "SCHEMA"]
