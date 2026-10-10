"""Fixture demonstration of the integrated evidence path (IDEA-031). Synthetic inputs only; no network or store.

    python -m larp.integration.demo [--out <file>]

Fake EDGAR filings -> real Ingestor -> real EvidenceAssessor (deterministic rule model) -> real verifier and
IssuerEvidenceState.v2 -> EvidenceContext.v1 -> real strategy policy -> real risk planner -> runtime plan adapter,
once under the default SHADOW authority and once under MANDATORY_REDUCTION (a tested capability that no team
decision has adopted). The market port is a fake external observation with one exit quote and no basis
validation, price history or quoted depth, so entries stay blocked and the blockers are shown.
"""

from datetime import datetime, timedelta, timezone
import argparse
import json

from larp.contracts import Document
from larp.intelligence.agent import build_request
from larp.intelligence.gate import accept, consume, initial_state, lifecycle_policy_from
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXSEMI, build_world
from larp.integration.contract import build_evidence_context, mandatory_reductions
from larp.integration.runtime import RuntimePlanner
from larp.research.fixtures import changed, snapshot, synthetic_profile
from larp.strategy.policy import decide

RUN = "synthetic-run"


def _market(s, held):
    c = s.context.read()
    at = s.observed_at
    markets = []
    for m in c["markets"]:
        m = dict(m, basis_verified=False, quotes=[])
        if m["symbol"] == "NVDAB":
            m["underlying_id"] = EXSEMI
            m["quotes"] = [{"quote_id": "fake-exit", "side": "SELL", "token_units": held, "cash_units": held * 9990,
                            "amount_kind": "EXACT_IN", "pay_asset": "NVDAB", "pay_units": held,
                            "min_receive_units": held * 9990 * 9980 // 10000,
                            "fee_units": 0, "gas_bnb_units": 10000, "route_valid": True, "slippage_bps": 20,
                            "impact_bps": 10, "available_at": at.isoformat(), "observed_at": at.isoformat(),
                            "expires_at": (at + timedelta(seconds=30)).isoformat()}]
        markets.append(m)
    return markets


def trace() -> dict:
    world = build_world(["EXSEMI_Q2_8K", "EXSEMI_402_8K", "EXSEMI_STATEMENTS_8K"])
    steps = {}
    for authority in ("SHADOW", "MANDATORY_REDUCTION"):
        profile = synthetic_profile(falsifier_ids=["F-ITEM-4.02"], falsifier_authority=authority)
        h = Document.from_dict(profile).digest("StrategyProfile.v1")
        state = initial_state(EXSEMI, h, lifecycle_policy=lifecycle_policy_from(world.config))
        decisions = []
        for key in ("EXSEMI_STATEMENTS_8K", "EXSEMI_402_8K"):
            cursor = world.store.read_cursor("sec-edgar", EXSEMI).read()
            request = build_request(job={"job_id": f"demo:{authority}:{key}"}, run_id=RUN, issuer_id=EXSEMI,
                                    records=[world.record(key)], cutoff_ms=world.clock(), context=state["context"],
                                    policy_profile_hash=h, allowed_tools=list(world.config.tools), tool_calls=6,
                                    deadline_ms=60000, source_health={"status": "OK",
                                                                      "last_success_ms": cursor["health"]["last_success_ms"]})
            result = world.assessor(RuleBaselineModel(world.clock)).assess(request)
            decision, state = accept(state, result, profile_hash=h, now_ms=world.clock())
            r = result.read()
            decisions.append({"filing": key, "status": r["status"], "decision": decision,
                              "findings": sorted({f["type"] for f in r["event_findings"] + r["findings"]}),
                              "statements": sorted([s["event"], s["semantics"]["assertion"], s["novelty"]]
                                                   for s in r["event_statements"]),
                              "coverage_complete": r["coverage"]["complete"]})
        held = 2000
        now = datetime.fromtimestamp(world.clock() / 1000, timezone.utc)
        s = snapshot(held={"NVDAB": held}, profile_changes={"falsifier_ids": ["F-ITEM-4.02"],
                                                           "falsifier_authority": authority}, now=now)
        ctx = build_evidence_context(consume(state, world.clock()), state, run_id=RUN, token="NVDAB",
                                     underlying_id=EXSEMI, policy_profile_hash=s.policy_profile_hash)
        s = changed(s, markets=_market(s, held), series={}, assessments=[ctx],
                    reduction_constraints=mandatory_reductions([ctx], profile, {"NVDAB": held}))
        proposal = decide(s, s.policy_state)
        plan = RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3).plan(s, proposal).read()
        data = proposal.next_policy_state.data.read()
        steps[authority] = {
            "assessments": decisions,
            "evidence_context": {k: ctx[k] for k in ("schema", "status", "status_reasons", "review_complete",
                                                     "statements_pending", "due_reviews")}
            | {"falsifier_predicates": sorted(f["predicate_id"] for f in ctx["falsifier_findings"])},
            "policy": {"targets": [[t.symbol, t.kind.value, t.reason] for t in proposal.targets],
                       "evidence_rejections": data["evidence_rejections"], "shadow": data["shadow_findings"]},
            "plan": {"intents": [{k: i[k] for k in ("symbol", "side", "token_units", "amount", "mandatory",
                                                    "decision_id")} for i in plan["intents"]],
                     "reservation_deltas": plan["reservation_deltas"], "jobs": [j["payload"] for j in plan["jobs"]],
                     "requirements": plan["requirements"], "rejections": plan["rejections"]},
        }
    return {"schema": "IntegrationDemo.v1", "synthetic": True, "steps": steps,
            "note": "Synthetic fixtures; real modules; no network, store, model or execution. Not evidence of live "
                    "readiness or profit. MANDATORY_REDUCTION is a capability, not an adopted policy."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out")
    args = parser.parse_args()
    text = json.dumps(trace(), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
