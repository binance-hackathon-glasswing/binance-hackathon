"""Two synthetic end-to-end traces of the evidence path (offline; no network or credentials).

1. tool-selection-thesis-revision: the agent sees only an 8-K cover page, fetches the press
   release exhibit, retrieves prior guidance from the previously available filing, compares,
   finds revenue guidance lowered, fires the declared falsifier and proposes thesis v4 BROKEN.
   The 0-tool baseline on the same input cannot see any of this.
2. justified-abstention: an 8-K/A reports a third-quarter revenue figure that contradicts the
   original filing found through prior context; the agent abstains and requests reassessment.

Each trace records the ingested records it used, the request, model I/O and tool calls, the
result, the gate decision, the persisted evidence-state batch (with review jobs) and the
exported feature row.

    python -m larp.intelligence.demo --out tests/intelligence/golden
"""

import argparse
import json
from pathlib import Path

from larp.contracts import Document
from larp.intelligence.agent import context_hash
from larp.intelligence.common import digest
from larp.intelligence.features import feature_row
from larp.intelligence.gate import accept, initial_state
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXSEMI, PROFILE, build_world, prior_thesis


def _persist(world, issuer_id, before, decision, after, result):
    """Gate state and review jobs go to the store port, never a private database or scheduler."""
    if decision != "ACCEPT":
        return None
    held = world.store.read_state(issuer_id)
    batch = {"schema": "EvidenceStateBatch.v1", "issuer_id": issuer_id,
             "expected_state_version": held.read()["version"] if held else 0,
             "state": after, "result_id": result["result_id"],
             "jobs": [r["job"] for r in result["review_requests"]]}
    batch["batch_id"] = "state:" + digest("larp.intel.state-batch.v1", batch)
    receipt = world.store.commit(Document.from_dict(batch)).read()
    return {"batch": batch, "receipt": receipt}


def _trace(name, filings, refs, purpose):
    world = build_world(filings)
    context = prior_thesis(world.config, EXSEMI)
    records = [world.record(k) for k in refs]
    request = world.request(refs, issuer_id=EXSEMI, job_id=f"demo:{name}", context=context)
    result_doc = world.assessor(RuleBaselineModel(world.clock)).assess(request)
    baseline_request = world.request(refs, issuer_id=EXSEMI, job_id=f"demo:{name}:baseline", context=context,
                                     tool_calls=0)
    baseline = world.assessor(RuleBaselineModel(world.clock)).assess(baseline_request).read()
    state = dict(initial_state(EXSEMI, PROFILE), context=context, context_hash=context_hash(context))
    decision, after = accept(state, result_doc, profile_hash=PROFILE, now_ms=world.clock())
    result = result_doc.read()
    return {
        "schema": "IntelligenceTrace.v1", "trace": name, "synthetic": True, "purpose": purpose,
        "records_used": records, "request": request.read(), "result": result,
        "gate": {"decision": decision, "state_after": after},
        "persisted": _persist(world, EXSEMI, state, decision, after, result),
        "feature_row": feature_row(result_doc, after).read(),
        "baseline_comparison": {"status": baseline["status"], "claims": len(baseline["claims"]),
                                "findings": [f["type"] for f in baseline["findings"]],
                                "falsifiers": {f["falsifier_id"]: f["state"] for f in baseline["falsifiers"]},
                                "proposed_thesis_status": (baseline["proposed_thesis"] or {}).get("status"),
                                "missingness": baseline["missingness"], "rationale": baseline["rationale"]},
    }


def traces() -> dict:
    return {
        "trace-tool-selection-thesis-revision.json": _trace(
            "tool-selection-thesis-revision", ["EXSEMI_Q2_8K", "EXSEMI_Q3_8K"], ["EXSEMI_Q3_8K"],
            "Autonomous tool selection (fetch exhibit, prior context, compare) and thesis revision"),
        "trace-justified-abstention.json": _trace(
            "justified-abstention", ["EXSEMI_Q2_8K", "EXSEMI_Q3_8K", "EXSEMI_Q3_8KA"], ["EXSEMI_Q3_8KA"],
            "Contradiction with previously available filing found through tools; justified abstention"),
    }


def render(trace: dict) -> bytes:
    return (json.dumps(trace, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, trace in traces().items():
        (out / name).write_bytes(render(trace))
        r = trace["result"]
        print(f"{name}: status={r['status']} reasons={r['reasons']} tool_calls={r['budget_used']['tool_calls']} "
              f"thesis={(r['proposed_thesis'] or {}).get('status')} gate={trace['gate']['state_after']['evidence_gate']}")


if __name__ == "__main__":
    main()
