"""Synthetic evaluation: verified-extraction baseline (0 tool calls) vs bounded agent (<= 6).

Metrics (IDEA-025 §5): supporting-span accuracy, numerical correctness, unsupported-claim
acceptance, relevant-event recall, abstention recall / false abstention, stale-result
rejection, tool budget and elapsed time, plus comparison accuracy (novelty labels, findings,
falsifier states, thesis status and status) for the baseline-vs-agent comparison.

Thresholds are read from config/intelligence/eval_thresholds.v1.json, frozen before any run.
Results describe the synthetic pack only: they are not evidence about real filings, model
quality on live data or trading performance.

    python -m larp.intelligence.evaluation --out <report.json>
"""

from fractions import Fraction
import argparse
import json
import time

from larp.contracts import Document
from larp.intelligence.common import frac, sha256_hex
from larp.intelligence.config import CONFIG_DIR
from larp.intelligence.gate import accept, initial_state
from larp.intelligence.scenarios import (
    EMPTY_CONTEXT, EVAL_CASES, PROFILE, build_world, make_model, pack_digest, prior_thesis,
)
from larp.intelligence.agent import context_hash
from larp.intelligence.text import text_from_saved

NON_ASSESSED = ("ABSTAIN", "UNAVAILABLE", "REJECTED_REQUEST")


def _context(world, case):
    if case["context"] == "none":
        return EMPTY_CONTEXT
    return prior_thesis(world.config, case["issuer"])


def run_case(case: dict, variant: str) -> dict:
    world = build_world(case["filings"])
    if case.get("delete_artifact"):
        key, name = case["delete_artifact"]
        sha = next(d["text_sha256"] for d in world.record(key)["documents"] if d["name"] == name)
        del world.artifacts.blobs[sha]
    context = _context(world, case)
    health = "OK" if case.get("source_health", "ok") == "ok" else \
        {"status": "OK", "last_success_ms": world.clock() - 36_000_000}
    request = world.request(case["refs"], issuer_id=case["issuer"], job_id=f"eval:{case['case_id']}:{variant}",
                            tool_calls=0 if variant == "baseline" else 6, context=context, source_health=health)
    if case["context"] == "mismatched_hash":
        tampered = request.read()
        tampered["context_hash"] = "f" * 64
        request = Document.from_dict(tampered)
    model = make_model(world, case["model"])
    started = time.perf_counter_ns()
    result_doc = world.assessor(model).assess(request)
    wall_us = (time.perf_counter_ns() - started) // 1000
    result = result_doc.read()
    state = dict(initial_state(case["issuer"], PROFILE), context=context, context_hash=context_hash(context))
    decision, new_state = accept(state, result_doc, profile_hash=PROFILE, now_ms=world.clock())
    probes = []
    if case["case_id"] == "guidance_cut" and variant == "agent" and decision == "ACCEPT":
        probes.append(accept(new_state, result_doc, profile_hash=PROFILE, now_ms=world.clock())[0])
        again = world.request(case["refs"], issuer_id=case["issuer"], job_id="eval:late-old-context",
                              context=context)
        late = world.assessor(make_model(world, "rule")).assess(again)
        probes.append(accept(new_state, late, profile_hash=PROFILE, now_ms=world.clock())[0])
        probes.append(accept(state, result_doc, profile_hash=PROFILE, now_ms=result["expiry_ms"])[0])
        probes.append(accept(dict(state, policy_profile_hash="b" * 64), result_doc, profile_hash="b" * 64,
                             now_ms=world.clock())[0])
    spans_ok = all(_span_ok(world, c["span"]) for c in result.get("claims", []) if c.get("span"))
    return {"case": case, "variant": variant, "result": result, "decision": decision, "gate": new_state,
            "probes": probes, "wall_us": wall_us, "spans_ok": spans_ok}


def _span_ok(world, span) -> bool:
    saved = world.artifacts.get(span["doc"])
    return saved is not None and text_from_saved(saved)[span["start"]:span["end"]] == span["text"]


def _key(item):
    return (item["kind"], item["metric"], item["period"], item["unit"], item["scale_exp10"])


def _value(item):
    return Fraction(item["value"]) if type(item["value"]) is str else Fraction(*item["value"])


def score(runs: list) -> dict:
    span_hits = span_total = num_ok = num_total = 0
    planted = planted_accepted = events_hit = events_total = 0
    abst_hit = abst_total = false_abst = assessed_total = 0
    probes_rejected = probes_total = comp_ok = comp_total = 0
    max_calls = max_elapsed = 0
    for run in runs:
        labels, result = run["case"]["labels"], run["result"]
        claims = result.get("claims", [])
        max_calls = max(max_calls, (result.get("budget_used") or {}).get("tool_calls", 0))
        max_elapsed = max(max_elapsed, (result.get("budget_used") or {}).get("elapsed_ms", 0))
        expected_status = labels["status"]
        if expected_status in NON_ASSESSED:
            abst_total += 1
            abst_hit += result["status"] == expected_status
        else:
            assessed_total += 1
            false_abst += result["status"] in NON_ASSESSED
        expected_facts = labels.get("facts", [])
        keys = {_key(f) for f in expected_facts}
        for want in expected_facts:
            span_total += 1
            span_hits += any(_key(c) == _key(want) and _value(c) == _value(want) and c.get("span")
                             for c in claims) and run["spans_ok"]
        for claim in claims:
            if claim["kind"] != "EVENT" and _key(claim) in keys:
                num_total += 1
                num_ok += any(_key(w) == _key(claim) and _value(w) == _value(claim) for w in expected_facts)
        if labels.get("planted"):
            planted += labels["planted"]
            planted_values = {Fraction(v) for v in labels.get("planted_values", [])}
            leaked = result["status"] == "ASSESSED" or any(
                c["kind"] != "EVENT" and _value(c) in planted_values for c in claims)
            planted_accepted += labels["planted"] if leaked else 0
        for event in labels.get("events", []):
            events_total += 1
            events_hit += any(c["metric"] == event for c in claims)
        expectations = [(expected_status, result["status"])]
        by_key = {}
        for c in claims:
            by_key.setdefault(f"{c['metric']}|{c['kind']}|{c['period']}", set()).add(c.get("novelty"))
        expectations += [(label, label if label in by_key.get(k, set()) else sorted(by_key.get(k, set())))
                         for k, label in labels.get("novelty", {}).items()]
        found = {f["type"] for f in result.get("findings", [])}
        expectations += [(t, t if t in found else None) for t in labels.get("findings", [])]
        states = {f["falsifier_id"]: f["state"] for f in result.get("falsifiers", [])}
        expectations += [(v, states.get(k)) for k, v in labels.get("falsifiers", {}).items()]
        if "thesis_status" in labels:
            expectations.append((labels["thesis_status"], (result.get("proposed_thesis") or {}).get("status")))
        comp_total += len(expectations)
        comp_ok += sum(1 for want, got in expectations if want == got)
        probes_total += len(run["probes"])
        probes_rejected += sum(1 for p in run["probes"] if p != "ACCEPT")
    ratio = lambda a, b: frac(Fraction(a, b)) if b else None
    return {"span_accuracy": ratio(span_hits, span_total), "numerical_correctness": ratio(num_ok, num_total),
            "unsupported_acceptance": ratio(planted_accepted, planted), "event_recall": ratio(events_hit, events_total),
            "abstention_recall": ratio(abst_hit, abst_total), "false_abstention": ratio(false_abst, assessed_total),
            "stale_rejection": ratio(probes_rejected, probes_total), "comparison_accuracy": ratio(comp_ok, comp_total),
            "comparison_expectations": comp_total, "max_tool_calls": max_calls, "max_elapsed_ms": max_elapsed,
            "counts": {"expected_facts": span_total, "numeric_claims_checked": num_total, "planted": planted,
                       "events": events_total, "expected_non_assessed": abst_total,
                       "expected_assessed": assessed_total, "stale_probes": probes_total, "runs": len(runs)}}


def _check(name, value, threshold, kind):
    if value is None:
        return {"metric": name, "value": None, "threshold": threshold, "pass": False, "note": "no observations"}
    v = Fraction(*value) if type(value) is list else Fraction(value)
    t = Fraction(*threshold) if type(threshold) is list else Fraction(threshold)
    return {"metric": name, "value": value, "threshold": threshold, "pass": v >= t if kind == "min" else v <= t}


def evaluate(thresholds_path=CONFIG_DIR / "eval_thresholds.v1.json") -> dict:
    raw = thresholds_path.read_bytes()
    thresholds = json.loads(raw.decode("utf-8"))
    runs = {"baseline": [], "agent": []}
    for case in EVAL_CASES:
        if case.get("adversarial"):
            runs["agent"].append(run_case(case, "agent"))
        else:
            runs["baseline"].append(run_case(case, "baseline"))
            runs["agent"].append(run_case(case, "agent"))
    metrics = {variant: score(items) for variant, items in runs.items()}
    a, b = metrics["agent"], metrics["baseline"]
    checks = []
    for name, threshold in thresholds["agent"].items():
        metric, kind = name.rsplit("__", 1)
        checks.append(dict(_check(metric, a[metric], threshold, kind), variant="agent"))
    for name, threshold in thresholds["baseline"].items():
        metric, kind = name.rsplit("__", 1)
        checks.append(dict(_check(metric, b[metric], threshold, kind), variant="baseline"))
    comp = thresholds["comparison"]
    gain = Fraction(*a["comparison_accuracy"]) - Fraction(*b["comparison_accuracy"])
    if a["comparison_expectations"] < comp["min_expectations"]:
        verdict = "INCONCLUSIVE"
    elif gain >= Fraction(*comp["min_gain"]) and Fraction(*a["unsupported_acceptance"]) == 0:
        verdict = "SUPPORTED_ON_SYNTHETIC_PACK"
    else:
        verdict = "NOT_SUPPORTED"
    wall = sorted(r["wall_us"] for items in runs.values() for r in items)
    return {
        "schema": "IntelligenceEvalReport.v1", "synthetic": True, "pack_digest": pack_digest(),
        "thresholds_sha256": sha256_hex(raw), "metrics": metrics, "checks": checks,
        "acceptance": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "comparison": {"metric": comp["metric"], "agent": a["comparison_accuracy"], "baseline": b["comparison_accuracy"],
                       "gain": frac(gain), "min_gain": comp["min_gain"], "verdict": verdict},
        "wall_clock_us": {"min": wall[0], "median": wall[len(wall) // 2], "max": wall[-1],
                          "note": "measured locally on the test host; simulated model latencies are on the fake clock"},
        "cases": [{"case_id": r["case"]["case_id"], "variant": r["variant"], "expected": r["case"]["labels"]["status"],
                   "status": r["result"]["status"], "reasons": r["result"].get("reasons", []),
                   "tool_calls": (r["result"].get("budget_used") or {}).get("tool_calls"),
                   "elapsed_ms": (r["result"].get("budget_used") or {}).get("elapsed_ms"),
                   "gate_decision": r["decision"], "evidence_gate": r["gate"]["evidence_gate"]}
                  for items in runs.values() for r in items],
        "note": "Synthetic pack only; not evidence about real filings, live model behaviour or trading results.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", help="write the JSON report here")
    args = parser.parse_args()
    report = evaluate()
    text = json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.out:
        with open(args.out, "wb") as handle:
            handle.write(text.encode("utf-8"))
    print(json.dumps({"acceptance": report["acceptance"], "comparison": report["comparison"],
                      "checks": [(c["variant"], c["metric"], c["value"], c["pass"]) for c in report["checks"]]},
                     indent=1))


if __name__ == "__main__":
    main()
