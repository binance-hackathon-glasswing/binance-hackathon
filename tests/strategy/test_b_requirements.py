"""Source-derived final-review B requirements; synthetic external inputs only."""

from dataclasses import replace
from fractions import Fraction
import random

import pytest

from larp.contracts import ContractError, Document
from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.schema import profile
from tests.strategy.live_fixtures import live_snapshot
from tests.strategy.test_equal_weight import five_names


def bind_profile(snapshot, values):
    return replace(changed(snapshot, profile=values),
                   policy_profile_hash=Document.from_dict(values).digest("StrategyProfile.v1"))


@pytest.mark.parametrize("field,changed_value", [
    ("operating_name_weight", [1, 10]),
    ("operating_gross_weight", [7, 10]),
    ("hard_name_weight", [6, 25]),
    ("hard_gross_weight", [17, 20]),
    ("top_up_below_gross_weight", [7, 10]),
])
def test_b_req_050_live_profile_cannot_change_adopted_caps(field, changed_value):
    snapshot = live_snapshot()
    values = snapshot.context.read()["profile"]
    values[field] = changed_value
    with pytest.raises(ContractError):
        profile(bind_profile(snapshot, values))


def test_b_req_010_equivalent_fractions_and_separate_stress_budget_are_valid():
    snapshot = live_snapshot()
    values = snapshot.context.read()["profile"]
    values.update(operating_name_weight=[2, 10], operating_gross_weight=[8, 10],
                  hard_name_weight=[2, 8], hard_gross_weight=[18, 20],
                  top_up_below_gross_weight=[6, 8], regime_gross_weight=[2, 5])
    assert profile(bind_profile(snapshot, values))["regime_gross_weight"] == [2, 5]


def test_b_req_001_generated_portfolios_cannot_create_short_leveraged_or_ineligible_positions():
    # Deterministic boundary/state exploration, not a profitability experiment.
    rng = random.Random(20261014)
    for _ in range(100):
        snapshot = five_names()
        context = snapshot.context.read()
        ledger = context["portfolio"]
        ledger["cash_units"] = rng.choice([0, 1, 40_000_000, 200_000_000])
        for pos in ledger["positions"].values():
            pos["units"] = rng.choice([0, 1, 100, 4000, 5000, 12000])
        snapshot = with_quotes(changed(snapshot, portfolio=ledger))
        proposal = decide(snapshot, snapshot.policy_state)
        assert all(t.symbol in snapshot.universe for t in proposal.targets)
        assert all(t.weight is None or Fraction(0) <= t.weight <= Fraction(1, 5) for t in proposal.targets)
        result = plan(snapshot, proposal).read()
        assert len(result["intents"]) <= 1
        for intent in result["intents"]:
            assert intent["symbol"] in {"NVDAB", "GOOGLB", "SKHYB", "TSLAB", "MSFTB"}
            assert intent["side"] in ("BUY", "SELL") and intent["token_units"] > 0
            if intent["side"] == "SELL":
                assert intent["pay_units"] <= ledger["positions"][intent["symbol"]]["units"]
            else:
                assert intent["cash_units"] + intent["fee_units"] <= ledger["cash_units"]
                assert sum(pos["units"] > 0 for pos in ledger["positions"].values()) <= 4


def test_b_req_034_opening_200_usdt_without_bnb_needs_bootstrap_and_cannot_spend():
    snapshot = live_snapshot(quoted=True)
    ledger = snapshot.context.read()["portfolio"]
    ledger.update(cash_units=200_000_000, bnb_units=0)
    snapshot = changed(snapshot, portfolio=ledger)
    result = plan(snapshot, decide(snapshot, snapshot.policy_state)).read()
    assert not result["intents"]
    assert any(r["reason"] == "FIRST_BNB_REQUIRED" for r in result["rejections"])
    assert all(pos["units"] == 0 for pos in ledger["positions"].values())
