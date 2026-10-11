"""IDEA-040 P02/P03/P08, entirely synthetic; no calibration evidence."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from larp.contracts import ContractError, Document
from larp.research.fixtures import changed
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.profiles import build_live_profiles
from larp.strategy.schema import profile, markets
from tests.strategy.live_fixtures import live_snapshot, registry, summary


def rebound(s, p):
    return replace(changed(s, profile=p), policy_profile_hash=Document.from_dict(p).digest("StrategyProfile.v1"))


def test_profiles_are_distinct_complete_and_full_position_capable():
    profiles = build_live_profiles(summary(), registry())
    for env, expected in (("REHEARSAL", 100_000_000), ("FINAL", 200_000_000)):
        p = profiles[env].read()
        s = live_snapshot()
        s = replace(rebound(s, p), policy_state=replace(s.policy_state, policy_id=p["policy_id"]))
        assert profile(s)["expected_equity_units"] == expected
        assert p["per_trade_cap_units"] >= expected // 5 + p["cost_reserve_units"]
        assert p["minimum_trade_units"] <= expected // 5
        assert p["gas_floor_bnb_units"] >= 20_000
        assert all(k in p["provenance"] for k in p if k not in ("schema", "mode", "values_origin", "provenance"))


@pytest.mark.parametrize("key", ["minimum_trade_units", "slippage_bps", "gas_floor_bnb_units", "new_risk_end", "quote_cost_summary"])
def test_missing_unsourced_and_unset_live_fields_reject(key):
    s = live_snapshot()
    for change in ("missing", "unset", "unsourced"):
        p = s.context.read()["profile"]
        if change == "missing":
            p.pop(key)
        elif change == "unset":
            p[key] = None
        else:
            p["provenance"].pop(key)
        with pytest.raises(ContractError):
            profile(rebound(s, p))


def test_bad_measurements_and_impossible_cost_budget_reject():
    for change in ("missing", "cost", "pnl", "future", "fake"):
        d = summary().read()
        if change == "missing":
            d["symbols"].pop("SKHYB")
        elif change == "cost":
            d["symbols"]["NVDAB"]["spread_bps"] = 50
        elif change == "pnl":
            d["pnl"] = 1
        elif change == "fake":
            d["origin"] = "SCRIPTED_FAKE"
        else:
            d["observed_at"] = "2026-11-01T00:00:00Z"
        with pytest.raises(ContractError):
            build_live_profiles(Document.from_dict(d), registry())


def test_live_entry_without_depth_passes_cost_and_impact_and_rejects_high_impact():
    s = live_snapshot(quoted=True)
    assert plan(s, decide(s, s.policy_state)).read()["intents"]
    c = s.context.read()
    for m in c["markets"]:
        for q in m["quotes"]:
            q["impact_bps"] = 21
    # Profile's global ceiling is 20, so >20 is rejected even before the per-name median gate.
    s = changed(s, markets=c["markets"])
    assert not plan(s, decide(s, s.policy_state)).read()["intents"]


def test_live_per_name_median_rule_cannot_use_larger_global_limit():
    s = live_snapshot(quoted=True)
    p = s.context.read()["profile"]
    p["impact_bps"] = 50
    s = rebound(s, p)
    c = s.context.read()
    for m in c["markets"]:
        for q in m["quotes"]:
            q["impact_bps"] = 21
    s = changed(s, markets=c["markets"])
    r = plan(s, decide(s, s.policy_state)).read()
    assert not r["intents"]
    assert "ENTRY_IMPACT_CAP" in {x["reason"] for x in r["rejections"]}


def test_live_fakes_rejected_at_market_and_quote_boundaries():
    s = live_snapshot(quoted=True)
    c = s.context.read()
    c["markets"][0]["origin"] = "SCRIPTED_FAKE"
    with pytest.raises(ContractError):
        markets(changed(s, markets=c["markets"]), profile(s))
    c = s.context.read()
    for m in c["markets"]:
        for q in m["quotes"]:
            q["origin"] = "SCRIPTED_FAKE"
    s = changed(s, markets=c["markets"])
    assert not plan(s, decide(s, s.policy_state)).read()["intents"]


def test_live_cost_cap_still_blocks_without_double_counting_impact():
    s = live_snapshot(quoted=True)
    c = s.context.read()
    for m in c["markets"]:
        for q in m["quotes"]:
            q["gas_bnb_units"] = 300_000
    # Raise the planning reserve only; the independent 50 bp economic cap remains.
    p = c["profile"]
    p.update(cost_reserve_units=1_000_000, per_trade_cap_units=41_000_000)
    s = rebound(changed(s, markets=c["markets"]), p)
    r = plan(s, decide(s, s.policy_state)).read()
    assert not r["intents"]
    assert "ENTRY_COST_CAP" in {x["reason"] for x in r["rejections"]}


def test_c2_fixture_matches_current_golden_trace_without_reconstruction():
    root = Path(__file__).parents[1]
    fixture = json.loads((root / "strategy/fixtures/assessment-producer.json").read_text())
    golden = json.loads((root.parent / fixture["source_trace"]).read_text())
    assert fixture["request"] == golden["request"]
    assert fixture["result"] == golden["result"]
    assert len(fixture["producer_commit"]) == 40
    assert fixture["synthetic"] is True
