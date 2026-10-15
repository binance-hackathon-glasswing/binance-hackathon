"""WR-B (IDEA-049-B, 2026-10-15): review fixes for #45, #46, #57 and #64 item 3; synthetic only."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from larp.contracts import ContractError, Document
from larp.research.fixtures import changed, fill_fixture, reserve_fixture, snapshot, with_quotes
from larp.risk.accounting import advance_accounting
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.schema import instant, market_view
from tests.integration import test_evidence_pipeline as pipeline
from tests.integration import test_settlement as settlement
from tests.strategy.live_fixtures import live_snapshot
from tests.strategy.test_red_flag_classes import evidence

FLATTEN = datetime.fromisoformat("2026-11-10T14:00:00+00:00")

# WRB-45-1: row-level defects; each makes only its own symbol unusable.
ROW_DEFECTS = {
    "schema": lambda m: m.update(schema="MarketObservation.v0"),
    "underlying_id": lambda m: m.pop("underlying_id"),
    "token_id": lambda m: m.update(token_id=""),
    "currency": lambda m: m.update(currency="USD"),
    "money_scale": lambda m: m.update(money_scale=100),
    "decimals_high": lambda m: m.update(decimals=31),
    "decimals_type": lambda m: m.update(decimals="4"),
    "decimals_missing": lambda m: m.pop("decimals"),
    "price_zero": lambda m: m.update(price_units=0),
    "price_missing": lambda m: m.pop("price_units"),
    "roundtrip": lambda m: m.update(measured_roundtrip_bps=-1),
}


def spoil(s, symbol, defect):
    markets = s.context.read()["markets"]
    ROW_DEFECTS[defect](next(m for m in markets if m["symbol"] == symbol))
    return changed(s, markets=markets)


def requirement(result, symbol):
    return next(r for r in result["requirements"] if r["symbol"] == symbol)


# --- WRB-45 (#45) -------------------------------------------------------------------------------

@pytest.mark.parametrize("defect", sorted(ROW_DEFECTS))
def test_wrb_45_1_bad_row_is_unusable_with_a_recorded_reason(defect):
    s = spoil(live_snapshot(), "TSLAB", defect)
    invalid = {}
    view = market_view(s.context.read()["markets"], s.universe, s.observed_at,
                       s.context.read()["profile"], invalid=invalid)
    assert view["TSLAB"] is None
    assert type(invalid["TSLAB"]) is str and invalid["TSLAB"]
    assert all(view[symbol] is not None for symbol in ("NVDAB", "GOOGLB", "MSFTB"))
    assert set(invalid) == {"TSLAB"}


@pytest.mark.parametrize("problem", ["duplicate", "unknown", "missing_symbol", "fake_origin", "fake_source",
                                     "not_list", "not_object"])
def test_wrb_45_2_set_level_problems_still_raise(problem):
    s = live_snapshot()
    markets, p = s.context.read()["markets"], s.context.read()["profile"]
    if problem == "duplicate":
        markets.append(deepcopy(markets[0]))
    elif problem == "unknown":
        markets[0]["symbol"] = "FAKEB"
    elif problem == "missing_symbol":
        markets[0].pop("symbol")
    elif problem == "fake_origin":
        markets[0]["origin"] = "SCRIPTED_FAKE"
    elif problem == "fake_source":
        markets[0]["source_id"] = "SYNTHETIC"
    elif problem == "not_list":
        markets = {"rows": markets}
    else:
        markets.append("row")
    with pytest.raises(ContractError):
        market_view(markets, s.universe, s.observed_at, p, invalid={})


@pytest.mark.parametrize("defect", sorted(ROW_DEFECTS))
def test_wrb_45_3_bad_unheld_row_does_not_block_the_flatten(defect):
    s = spoil(live_snapshot(held={"NVDAB": 1000, "GOOGLB": 1000}, quoted=True, now=FLATTEN), "TSLAB", defect)
    result = plan(s, None).read()
    assert not any(r["reason"] == "INVALID_REQUIRED_INPUT" for r in result["rejections"])
    for symbol in ("NVDAB", "GOOGLB"):
        assert "TERMINAL_FLATTEN" in requirement(result, symbol)["reasons"]
    assert [(i["side"], i["mandatory"]) for i in result["intents"]] == [("SELL", True)]
    assert result["intents"][0]["symbol"] in ("NVDAB", "GOOGLB")
    bad = [r for r in result["rejections"] if r["reason"] == "INVALID_MARKET_ROW"]
    assert [r["symbol"] for r in bad] == ["TSLAB"] and bad[0]["detail"]


@pytest.mark.parametrize("defect", sorted(ROW_DEFECTS))
def test_wrb_45_4_bad_held_row_blocks_only_that_name_and_is_recorded(defect):
    s = spoil(live_snapshot(held={"NVDAB": 1000, "GOOGLB": 1000}, quoted=True, now=FLATTEN), "NVDAB", defect)
    result = plan(s, None).read()
    nvdab = requirement(result, "NVDAB")
    assert nvdab["status"] == "BLOCKED_INPUT"
    assert nvdab["held_units"] == nvdab["remaining_sell_units"] == 1000
    assert "TERMINAL_FLATTEN" in nvdab["reasons"]
    assert [(i["symbol"], i["side"], i["mandatory"]) for i in result["intents"]] == [("GOOGLB", "SELL", True)]
    assert [r["symbol"] for r in result["rejections"] if r["reason"] == "INVALID_MARKET_ROW"] == ["NVDAB"]
    assert "NVDAB" in result["unvalued_symbols"]
    assert any(r["reason"] == "PARTIAL_VALUATION_NEW_RISK_BLOCKED" for r in result["rejections"])


def test_wrb_45_5_bad_unheld_row_does_not_block_a_position_cap_trim():
    base = snapshot(held={"NVDAB": 6000})
    s = spoil(with_quotes(base, policy=False), "TSLAB", "currency")
    result = plan(s, None).read()
    assert "POSITION_CAP" in requirement(result, "NVDAB")["reasons"]
    assert [(i["symbol"], i["side"], i["mandatory"]) for i in result["intents"]] == [("NVDAB", "SELL", True)]


def test_wrb_45_5_policy_still_proposes_with_a_bad_unheld_row():
    s = spoil(live_snapshot(held={"NVDAB": 1000}), "TSLAB", "underlying_id")
    proposal = decide(s, s.policy_state)
    assert {t.symbol for t in proposal.targets} >= {"NVDAB", "GOOGLB", "MSFTB"}


def test_wrb_45_6_runtime_evidence_reduction_survives_a_bad_unheld_row():
    from tests.integration.test_published_red_flag_policy import PublishedPredicatePolicy
    from larp.integration.runtime import ContextBuilder, initial_projection
    case = PublishedPredicatePolicy("test_real_rf1_producer_is_mandatory_even_without_policy")
    s, record, c, now_ms = case.producer_context("RF1-4.02-SUPPORTED", "4.02")
    next(m for m in c["markets"] if m["symbol"] == "TSLAB")["currency"] = "USD"
    builder = ContextBuilder(profile=s.context.read()["profile"], profile_hash=s.policy_profile_hash,
                             run_id=s.run_id, issuers={}, market=None, health=None, calendar=None,
                             universe=s.universe)
    current = {"run_id": s.run_id, "wallet_id": s.wallet_id, "projection": initial_projection(c["portfolio"]),
               "policy_state": s.policy_state.record(), "reservations": []}
    reductions = builder._reductions([record], current, {"NVDAB": 2000}, c["markets"], now_ms)
    assert reductions == [{"symbol": "NVDAB", "max_units": 0, "reason": "CLASS_1_EXIT"}]


# --- WRB-46 (#46) -------------------------------------------------------------------------------

def sell_round():
    s = live_snapshot(held={"NVDAB": 1000}, quoted=True, now=FLATTEN)
    result = plan(s, None)
    intent = result.read()["intents"][0]
    reserved = reserve_fixture(s, result).context.read()["portfolio"]
    reserved["mode"] = "LIVE"
    reserved["reservations"][intent["intent_id"]]["round_id"] = "synthetic-round"
    return s, intent, Document.from_dict(reserved)


def final(s, intent, *, kind, gas, tx):
    terminal = kind != "APPROVAL"
    e = fill_fixture(s, intent, kind=kind, gas=gas, terminal=terminal).read()
    e.update(origin="EXECUTION_RECONCILER", round_id="synthetic-round", round_terminal=terminal,
             tx_hash="0x" + tx * 64, block_hash="0x" + "b" * 64, canonical=True,
             receipt={"tx_hash": "0x" + tx * 64, "block_hash": "0x" + "b" * 64, "block_number": 99,
                      "canonical": True, "finality": "FINAL", "chain_id": 56,
                      "status": 0 if kind == "REVERT" else 1})
    return Document.from_dict(e)


def test_wrb_46_1_fill_gas_above_reservation_is_charged_and_releases_it():
    s, intent, before = sell_round()
    reserved = before.read()["reservations"][intent["intent_id"]]["bnb_units"]
    gas = reserved + 3000
    assert gas <= before.read()["bnb_units"]
    after = advance_accounting(before, final(s, intent, kind="FILL", gas=gas, tx="a")).read()
    assert after["bnb_units"] == before.read()["bnb_units"] - gas
    assert after["accounting"]["gas_value_units"] == before.read()["accounting"]["gas_value_units"] + gas
    assert after["accounting"]["gas_over_reserve_bnb_units"] == 3000
    assert intent["intent_id"] not in after["reservations"]
    assert after["positions"]["NVDAB"]["units"] == 0


def test_wrb_46_2_approve_plus_swap_above_the_quote_is_applied():
    s, intent, before = sell_round()
    assert before.read()["reservations"][intent["intent_id"]]["bnb_units"] == 10_000
    approved = advance_accounting(before, final(s, intent, kind="APPROVAL", gas=8000, tx="c"))
    assert approved.read()["reservations"][intent["intent_id"]]["bnb_units"] == 2000
    after = advance_accounting(approved, final(s, intent, kind="FILL", gas=15_000, tx="a")).read()
    assert after["bnb_units"] == before.read()["bnb_units"] - 23_000
    assert after["accounting"]["gas_over_reserve_bnb_units"] == 13_000
    assert not after["reservations"]


def test_wrb_46_3_gas_above_actual_balance_is_still_an_integrity_error():
    s, intent, before = sell_round()
    with pytest.raises(ContractError):
        advance_accounting(before, final(s, intent, kind="FILL", gas=before.read()["bnb_units"] + 1, tx="a"))
    with pytest.raises(ContractError):
        advance_accounting(before, final(s, intent, kind="APPROVAL", gas=before.read()["bnb_units"] + 1, tx="c"))


class WRB46Settlement(pipeline.PipelineHarness):
    """WRB-46-2 through the runtime settlement path (PostgreSQL store reservations)."""

    bridge, rows, observe, planned = (settlement.Settlement.bridge, settlement.Settlement.rows,
                                     settlement.Settlement.observe, settlement.Settlement.planned)

    def test_wrb_46_2_settled_approve_plus_swap_above_reservation_releases_every_row(self):
        c = self.bridge(self.coordinator("MANDATORY_REDUCTION"))
        self.round(c, "r1", "EXSEMI_402_8K")
        intent = self.planned("r1")["plan"]["intents"][0]
        reserved = {r["asset"]: r["units"] for r in self.rows(intent["intent_id"])}["BNB"]
        before = self.store.load(pipeline.RUN).read()["projection"]["balances"]["BNB"]
        approve_tx = "0x" + "ef" * 32
        self.observe(c, settlement.observation(intent, "r1", "a0", "BROADCAST_ATTEMPTED", step="approve", tx_hash=approve_tx))
        self.observe(c, settlement.observation(intent, "r1", "a1", "APPROVAL", step="approve", tx_hash=approve_tx,
                                    gas_bnb_units=reserved - 2000))
        self.observe(c, settlement.observation(intent, "r1", "o1", "BROADCAST_ATTEMPTED"))
        self.observe(c, settlement.observation(intent, "r1", "o2", "FILL", symbol="NVDAB", side="SELL",
                                    token_units=intent["token_units"], cash_units=intent["min_receive_units"],
                                    fee_units=0, gas_bnb_units=reserved + 5000))
        self.assertEqual(self.rows(intent["intent_id"]), [])
        after = self.store.load(pipeline.RUN).read()["projection"]["balances"]["BNB"]
        self.assertEqual(after, before - (2 * reserved + 3000))


# --- WRB-57 (#57) -------------------------------------------------------------------------------

def latched(held):
    """A Class 1 latch set by the policy's own IDEA-035 rule, persisted for the next round."""
    s = evidence(live_snapshot(held=held), "4.02")
    first = decide(s, s.policy_state)
    assert first.next_policy_state.data.read()["blocked"]["NVDAB"]["reason"] == "CLASS_1_EXIT"
    return replace(changed(s, assessments=[]), policy_state=first.next_policy_state)


def with_sell_quote(s, symbol):
    request = changed(s, reduction_constraints=[{"symbol": symbol, "max_units": 0, "reason": "QUOTE_FIXTURE"}])
    markets = with_quotes(request, policy=False).context.read()["markets"]
    for m in markets:
        for q in m["quotes"]:
            q["origin"] = "WEB3_OPEN_API"
    return changed(s, markets=markets)


def stale(s, symbol):
    markets = s.context.read()["markets"]
    old = (s.observed_at - timedelta(hours=1)).isoformat()
    next(m for m in markets if m["symbol"] == symbol).update(observed_at=old, available_at=old, close_at=old)
    return changed(s, markets=markets)


def test_wrb_57_1_persisted_latch_reaches_the_planner_without_proposal_or_evidence():
    s = stale(with_sell_quote(latched({"NVDAB": 1000, "GOOGLB": 1000}), "NVDAB"), "GOOGLB")
    with pytest.raises(ContractError):
        decide(s, s.policy_state)  # the scenario: a stale mark elsewhere leaves no proposal
    assert not s.context.read()["reduction_constraints"] and not s.context.read()["assessments"]
    result = plan(s, None).read()
    nvdab = requirement(result, "NVDAB")
    assert nvdab["max_units"] == 0 and nvdab["remaining_sell_units"] == 1000
    assert "CLASS_1_EXIT" in nvdab["reasons"]
    assert requirement(result, "GOOGLB")["status"] == "BLOCKED_MARK"
    assert [(i["symbol"], i["side"], i["mandatory"]) for i in result["intents"]] == [("NVDAB", "SELL", True)]


def test_wrb_57_2_latch_on_a_flat_name_adds_no_requirement():
    s = latched({"GOOGLB": 1000})
    result = plan(s, None).read()
    assert not [r for r in result["requirements"] if r["symbol"] == "NVDAB"]


def test_wrb_57_3_latch_holds_until_the_idea_035_rule_clears_it():
    s = latched({"NVDAB": 1000})
    assert "CLASS_1_EXIT" in requirement(plan(s, None).read(), "NVDAB")["reasons"]
    # A round with no evidence keeps the latch; the next persisted state still drives the exit.
    kept = decide(s, s.policy_state).next_policy_state
    s = replace(s, policy_state=kept)
    assert "CLASS_1_EXIT" in requirement(plan(s, None).read(), "NVDAB")["reasons"]
    # A complete review with no Class 1 finding resolves it (A8); that round still exits (one-round lag).
    cleared = evidence(s, None, version=2)
    resolving = decide(cleared, cleared.policy_state)
    assert not resolving.next_policy_state.data.read()["blocked"]
    assert "CLASS_1_EXIT" in requirement(plan(cleared, resolving).read(), "NVDAB")["reasons"]
    after = replace(changed(cleared, assessments=[]), policy_state=resolving.next_policy_state)
    assert not any("CLASS_1_EXIT" in r.get("reasons", []) for r in plan(after, None).read()["requirements"])


@pytest.mark.parametrize("blocked", ["bad", {"NVDAB": "CLASS_1_EXIT"}, {"NVDAB": {"reason": 1}}])
def test_wrb_57_4_malformed_latch_state_fails_closed(blocked):
    s = live_snapshot(held={"NVDAB": 1000})
    s = replace(s, policy_state=replace(s.policy_state, data=Document.from_dict({"blocked": blocked})))
    result = plan(s, None).read()
    assert result["rejections"][0]["reason"] == "INVALID_REQUIRED_INPUT"
    assert requirement(result, "NVDAB")["status"] == "BLOCKED_INPUT"
    assert not result["intents"]


# --- WRB-64.3 (#64 item 3) ----------------------------------------------------------------------

def priced(s, symbol, price_units, cash_units):
    c = s.context.read()
    next(m for m in c["markets"] if m["symbol"] == symbol)["price_units"] = price_units
    c["portfolio"]["cash_units"] = cash_units  # keep equity at the 200 USDT anchor: no loss latches
    return changed(s, markets=c["markets"], portfolio=c["portfolio"])


def test_wrb_64_2_larger_notional_goes_first_not_more_token_units():
    s = priced(snapshot(held={"NVDAB": 1000, "GOOGLB": 3000}), "GOOGLB", 10_000_000, 186_000_000)
    s = changed(s, reduction_constraints=[{"symbol": "NVDAB", "max_units": 0, "reason": "MANDATORY_REDUCTION_BY_RISK"},
                                          {"symbol": "GOOGLB", "max_units": 0, "reason": "MANDATORY_REDUCTION_BY_RISK"}])
    s = with_quotes(s, policy=False)
    result = plan(s, None).read()
    assert requirement(result, "GOOGLB")["remaining_sell_units"] > requirement(result, "NVDAB")["remaining_sell_units"]
    assert [(i["symbol"], i["mandatory"]) for i in result["intents"]] == [("NVDAB", True)]


def test_wrb_64_3_class1_exit_goes_before_a_larger_position_cap_trim():
    s = changed(snapshot(held={"NVDAB": 5000, "GOOGLB": 500}),
                reduction_constraints=[{"symbol": "GOOGLB", "max_units": 0, "reason": "CLASS_1_EXIT"}])
    s = with_quotes(s, policy=False)
    result = plan(s, None).read()
    trim = requirement(result, "NVDAB")
    assert "POSITION_CAP" in trim["reasons"] and "CLASS_1_EXIT" not in trim["reasons"]
    assert trim["remaining_sell_units"] > requirement(result, "GOOGLB")["remaining_sell_units"]
    assert [(i["symbol"], i["mandatory"]) for i in result["intents"]] == [("GOOGLB", True)]
