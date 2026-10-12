"""IDEA-044: allocation priority and independent spending-health regressions."""
import pytest

from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from tests.strategy.live_fixtures import live_snapshot
from tests.strategy.test_equal_weight import five_names


def test_cheapest_selected_name_receives_the_first_execution_slot():
    s = with_quotes(five_names())
    for reversed_markets in (False, True):
        markets = s.context.read()["markets"]
        if reversed_markets:
            markets.reverse()
        candidate = changed(s, markets=markets)
        result = plan(candidate, decide(candidate, candidate.policy_state)).read()
        assert result["intents"][0]["symbol"] == "NVDAB"  # 20 bp; alphabetical GOOGLB costs 30 bp


def test_equal_cost_execution_priority_is_stable_by_symbol():
    s = five_names()
    markets = s.context.read()["markets"]
    for market in markets:
        market["measured_roundtrip_bps"] = 20
    s = with_quotes(changed(s, markets=markets))
    result = plan(s, decide(s, s.policy_state)).read()
    assert result["intents"][0]["symbol"] == "GOOGLB"


@pytest.mark.parametrize("spending", [False, None, 1, "true", "MISSING"])
@pytest.mark.parametrize("held", [{}, {"NVDAB": 3000}])
def test_live_buys_and_topups_require_explicit_spending_health(spending, held):
    s = live_snapshot(held=held, quoted=True)
    health = s.context.read()["health"]
    if spending == "MISSING":
        health.pop("new_spending_ok")
    else:
        health["new_spending_ok"] = spending
    s = changed(s, health=health)
    result = plan(s, decide(s, s.policy_state)).read()
    assert not result["intents"]
    assert not result["quote_requests"]
    assert any(r["reason"] == "NEW_RISK_HALTED" for r in result["rejections"])


def test_spending_block_preserves_mandatory_sales_and_healthy_buy_control():
    s = live_snapshot(quoted=True)
    assert plan(s, decide(s, s.policy_state)).read()["intents"][0]["side"] == "BUY"
    s = live_snapshot(held={"NVDAB": 6000}, quoted=True)
    health = s.context.read()["health"]
    health["new_spending_ok"] = False
    s = changed(s, health=health)
    intent = plan(s, None).read()["intents"][0]
    assert (intent["symbol"], intent["side"], intent["mandatory"]) == ("NVDAB", "SELL", True)


def test_explicit_offline_spending_block_is_respected():
    s = with_quotes(five_names())
    health = s.context.read()["health"]
    health["new_spending_ok"] = False
    s = changed(s, health=health)
    assert not plan(s, decide(s, s.policy_state)).read()["intents"]
