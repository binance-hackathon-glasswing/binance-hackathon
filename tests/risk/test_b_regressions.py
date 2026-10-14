"""B-REG-01: malformed external quotes and explicit UTC loss observations."""

from copy import deepcopy
from datetime import datetime

import pytest

from larp.contracts import ContractError, Document
from larp.research.fixtures import changed
from larp.risk.accounting import update_risk
from larp.risk.planner import plan
from tests.risk.test_live_resource_receipts import gas_quote
from tests.strategy.live_fixtures import live_snapshot


def test_b_req_018_offset_loss_observation_uses_utc_day():
    snapshot = live_snapshot(now=datetime.fromisoformat("2026-10-29T23:30:00+00:00"))
    portfolio = Document.from_dict(snapshot.context.read()["portfolio"])
    anchor = portfolio.read()["risk"]["day_anchor_units"]
    utc = update_risk(portfolio, now=snapshot.observed_at, equity_units=anchor * 97 // 100)
    offset = update_risk(portfolio, now=datetime.fromisoformat("2026-10-30T07:30:00+08:00"),
                         equity_units=anchor * 97 // 100)
    assert utc.read()["risk"]["daily_halt"]
    assert offset == utc


def test_b_req_018_naive_loss_observation_is_rejected():
    snapshot = live_snapshot()
    portfolio = Document.from_dict(snapshot.context.read()["portfolio"])
    with pytest.raises(ContractError):
        update_risk(portfolio, now=datetime(2026, 10, 29, 14), equity_units=1)


@pytest.mark.parametrize("malformed", [None, 7, "quotes", [None], [{}, None]])
def test_b_req_044_bad_stock_quote_collection_retains_terminal_requirement(malformed):
    snapshot = live_snapshot(held={"NVDAB": 1000}, quoted=True,
                             now=datetime.fromisoformat("2026-11-10T14:00:00+00:00"))
    market = snapshot.context.read()["markets"]
    next(m for m in market if m["symbol"] == "NVDAB")["quotes"] = malformed
    result = plan(changed(snapshot, markets=market), None).read()
    assert not result["intents"]
    assert any(r["symbol"] == "NVDAB" and r["remaining_sell_units"] == 1000
               for r in result["requirements"])
    assert any(r.get("reason") == "QUOTE_COLLECTION_INVALID" for r in result["rejections"])


def test_b_req_044_duplicate_exact_stock_quotes_are_ambiguous():
    snapshot = live_snapshot(held={"NVDAB": 1000}, quoted=True,
                             now=datetime.fromisoformat("2026-11-10T14:00:00+00:00"))
    market = snapshot.context.read()["markets"]
    quotes = next(m for m in market if m["symbol"] == "NVDAB")["quotes"]
    quotes.append(deepcopy(quotes[0]))
    quotes[-1]["quote_id"] += "-competing"
    result = plan(changed(snapshot, markets=market), None).read()
    assert not result["intents"]
    assert result["requirements"][0]["remaining_sell_units"] == 1000
    assert any(r.get("reason") == "QUOTE_COLLECTION_AMBIGUOUS" for r in result["rejections"])


@pytest.mark.parametrize("malformed", [None, 7, "quotes", [None], [{}, None]])
def test_b_req_044_bad_gas_quote_collection_returns_blocked_outcome(malformed):
    snapshot = live_snapshot(gas_low=True)
    result = plan(changed(snapshot, gas_quotes=malformed), None).read()
    assert not result["intents"]
    assert any(r.get("reason") == "GAS_TOP_UP_QUOTE_COLLECTION_INVALID" for r in result["rejections"])


def test_b_req_044_duplicate_gas_quotes_cannot_choose_an_arbitrary_route():
    snapshot = live_snapshot(gas_low=True)
    quote = gas_quote(snapshot)
    competing = deepcopy(quote)
    competing["quote_id"] += "-competing"
    result = plan(changed(snapshot, gas_quotes=[quote, competing]), None).read()
    assert not result["intents"]
    assert any(r.get("reason") == "GAS_TOP_UP_QUOTE_COLLECTION_AMBIGUOUS" for r in result["rejections"])


def test_b_req_044_valid_stock_and_gas_quote_controls():
    stock = live_snapshot(held={"NVDAB": 1000}, quoted=True,
                          now=datetime.fromisoformat("2026-11-10T14:00:00+00:00"))
    assert plan(stock, None).read()["intents"][0]["side"] == "SELL"
    gas = live_snapshot(gas_low=True)
    assert plan(changed(gas, gas_quotes=[gas_quote(gas)]), None).read()["intents"][0]["kind"] == "GAS_TOP_UP"


@pytest.mark.parametrize("malformed", [None, 7, "markets", [None], [{}, None]])
def test_b_req_022_bad_market_collection_is_explicit_and_preserves_holdings(malformed):
    snapshot = live_snapshot(held={"NVDAB": 1000})
    result = plan(changed(snapshot, markets=malformed), None).read()
    assert not result["intents"]
    assert result["rejections"][0]["reason"] == "INVALID_REQUIRED_INPUT"
    assert result["requirements"][0]["symbol"] == "NVDAB"
    assert result["requirements"][0]["held_units"] == 1000


@pytest.mark.parametrize("malformed", [None, 7, [], {"positions": None}, {"positions": []}, {"positions": {"NVDAB": None}}])
def test_b_req_022_bad_portfolio_cannot_escape_the_input_rejection_path(malformed):
    result = plan(changed(live_snapshot(), portfolio=malformed), None).read()
    assert not result["intents"]
    assert result["rejections"][0]["reason"] == "INVALID_REQUIRED_INPUT"
