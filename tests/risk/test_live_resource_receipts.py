"""P06/P07 synthetic receipt and resource counterexamples; no chain proof."""

from copy import deepcopy

import pytest

from larp.contracts import ContractError, Document
from larp.research.fixtures import changed, reserve_fixture, fill_fixture
from larp.risk.accounting import advance_accounting, economic_views
from larp.risk.planner import plan
from larp.strategy.policy import decide
from tests.strategy.live_fixtures import live_snapshot


def gas_quote(s):
    p = s.context.read()["profile"]
    return {"kind": "GAS_TOP_UP", "symbol": "BNB", "side": "BUY", "receive_asset": "BNB", "receive_decimals": 6,
            "origin": "WEB3_OPEN_API", "quote_id": "synthetic-gas-quote", "amount_kind": "EXACT_IN",
            "pay_asset": "USDT", "pay_units": p["gas_top_up_cash_units"],
            "cash_units": p["gas_top_up_cash_units"], "fee_units": 0, "gas_bnb_units": 10000,
            "token_units": p["gas_top_up_min_receive_units"] + 1,
            "min_receive_units": p["gas_top_up_min_receive_units"], "route_valid": True,
            "slippage_bps": 20, "impact_bps": 10, "observed_at": s.observed_at.isoformat(),
            "available_at": s.observed_at.isoformat(), "expires_at": "2026-10-29T14:00:30Z"}


def resource_plan():
    s = live_snapshot(gas_low=True)
    s = changed(s, gas_quotes=[gas_quote(s)])
    result = plan(s, decide(s, s.policy_state))
    return s, result


def receipt(s, result, *, kind="FILL", terminal=True):
    intent = result.read()["intents"][0]
    reserved = reserve_fixture(s, result).context.read()["portfolio"]
    reserved["mode"] = "LIVE"
    reserved["reservations"][intent["intent_id"]]["round_id"] = "synthetic-round"
    e = fill_fixture(s, intent, kind=kind, terminal=terminal).read()
    e.update(origin="EXECUTION_RECONCILER", round_id="synthetic-round", tx_hash="0x" + "a" * 64,
        receipt={"tx_hash": "0x" + "a" * 64, "block_hash": "0x" + "b" * 64,
                 "block_number": 99, "canonical": True, "finality": "FINAL", "chain_id": 56,
                 "status": 0 if kind == "REVERT" else 1})
    return Document.from_dict(reserved), e


def test_top_up_own_round_does_not_occupy_stock_slot_or_gross():
    s = live_snapshot(gas_low=True, held={"NVDAB": 4000, "GOOGLB": 4000, "TSLAB": 4000, "MSFTB": 4000})
    s = changed(s, gas_quotes=[gas_quote(s)])
    r = plan(s, None).read()
    assert len(r["intents"]) == 1
    assert r["intents"][0]["kind"] == "GAS_TOP_UP" and r["intents"][0]["own_round"] is True
    assert r["worst_case_gross_units"] == 160_000_000
    assert r["reservation_deltas"][0]["symbol"] == "BNB"
    assert r["reservation_deltas"][0]["cash_units"] == r["intents"][0]["cash_units"]


@pytest.mark.parametrize("block", ["zero_gas", "cash", "pending", "daily", "run", "deep", "integrity", "degraded", "terminal"])
def test_top_up_respects_all_spending_and_wallet_barriers(block):
    s = live_snapshot(gas_low=True)
    c = s.context.read()
    if block == "zero_gas":
        c["portfolio"]["bnb_units"] = 0
    elif block == "cash":
        c["portfolio"]["cash_units"] = 0
    elif block == "pending":
        c["portfolio"]["reservations"] = {"pending": {"symbol": "NVDAB", "side": "SELL", "cash_units": 0,
            "bnb_units": 1, "token_units": 1}}
    elif block in ("daily", "run", "deep"):
        c["portfolio"]["risk"][{"daily": "daily_halt", "run": "run_halt", "deep": "deep_cut"}[block]] = True
    elif block == "integrity":
        c["health"]["integrity_ok"] = False
    elif block == "degraded":
        c["health"]["new_spending_ok"] = False
    elif block == "terminal":
        # No top-up even after the cut, before flatten starts.
        from dataclasses import replace
        from larp.strategy.schema import instant
        s = replace(s, observed_at=instant("2026-11-09T00:00:00Z"))
    s = changed(s, **c)
    s = changed(s, gas_quotes=[gas_quote(s)])
    r = plan(s, None).read()
    assert not [i for i in r["intents"] if i.get("kind") == "GAS_TOP_UP"]


def test_top_up_requires_actual_quote_then_accounts_actual_bnb_separately():
    s = live_snapshot(gas_low=True)
    r = plan(s, None).read()
    assert not r["intents"] and r["quote_requests"][0]["kind"] == "GAS_TOP_UP"
    s, result = resource_plan()
    before, e = receipt(s, result)
    after = advance_accounting(before, Document.from_dict(e))
    a = after.read()
    assert a["bnb_units"] == before.read()["bnb_units"] - e["gas_bnb_units"] + e["token_units"]
    assert a["positions"] == before.read()["positions"]
    assert a["accounting"]["turnover_units"] == 0
    assert not a["reservations"]
    assert advance_accounting(after, Document.from_dict(e)) == after
    views = economic_views(after, equity_units=200_000_000).read()
    assert views["bnb_units"] == a["bnb_units"]
    assert views["gas_top_up_cash_units"] == e["cash_units"]


@pytest.mark.parametrize("kind", ["APPROVAL", "REVERT"])
def test_approval_and_revert_spend_gas_only(kind):
    s, result = resource_plan()
    before, e = receipt(s, result, kind=kind, terminal=kind == "REVERT")
    after = advance_accounting(before, Document.from_dict(e)).read()
    assert after["cash_units"] == before.read()["cash_units"]
    assert after["bnb_units"] == before.read()["bnb_units"] - e["gas_bnb_units"]
    assert after["positions"] == before.read()["positions"]
    assert bool(after["reservations"]) == (kind == "APPROVAL")


@pytest.mark.parametrize("bad", ["BROADCAST_ATTEMPTED", "PROVISIONAL", "canonical", "block_hash", "tx_hash", "round", "status", "fake"])
def test_receipt_rejects_unfinal_unbound_or_fake_facts_without_mutation(bad):
    s, result = resource_plan()
    before, original = receipt(s, result)
    e = deepcopy(original)
    if bad == "BROADCAST_ATTEMPTED":
        e["kind"] = bad
    elif bad == "PROVISIONAL":
        e["settlement"] = bad
    elif bad == "canonical":
        e["receipt"]["canonical"] = False
    elif bad == "block_hash":
        e["receipt"].pop("block_hash")
    elif bad == "tx_hash":
        e["tx_hash"] = "0x" + "c" * 64
    elif bad == "round":
        e["round_id"] = "other-round"
    elif bad == "status":
        e["receipt"]["status"] = 0
    else:
        e["origin"] = "SCRIPTED_FAKE"
    saved = before.payload
    with pytest.raises(ContractError):
        advance_accounting(before, Document.from_dict(e))
    assert before.payload == saved


def test_real_fill_uses_variable_actual_output_not_estimated_output():
    s = live_snapshot(quoted=True)
    result = plan(s, decide(s, s.policy_state))
    before, e = receipt(s, result)
    e["token_units"] += 1
    after = advance_accounting(before, Document.from_dict(e)).read()
    assert after["positions"][e["symbol"]]["units"] == e["token_units"]
    assert after["positions"][e["symbol"]]["cost_basis_units"] == e["cash_units"] + e["fee_units"]


def test_duplicate_approval_receipt_cannot_spend_gas_again_with_new_event_id():
    s, result = resource_plan()
    before, e = receipt(s, result, kind="APPROVAL", terminal=False)
    after = advance_accounting(before, Document.from_dict(e))
    e["event_id"] = "synthetic-duplicate-receipt"
    with pytest.raises(ContractError):
        advance_accounting(after, Document.from_dict(e))


def test_actual_sell_proceeds_fee_and_basis_are_used():
    from larp.strategy.schema import instant
    s = live_snapshot(held={"NVDAB": 1000}, now=instant("2026-11-10T00:00:00Z"), quoted=True)
    result = plan(s, None)
    before, e = receipt(s, result)
    e.update(cash_units=e["cash_units"] + 1000, fee_units=100)
    after = advance_accounting(before, Document.from_dict(e)).read()
    assert after["cash_units"] == before.read()["cash_units"] + e["cash_units"] - 100
    assert after["accounting"]["realized_units"] == e["cash_units"] - 100 - 10_000_000
    assert after["positions"]["NVDAB"]["units"] == 0


def test_low_gas_spending_block_does_not_hide_an_affordable_class1_exit():
    from tests.strategy.test_red_flag_classes import evidence
    from larp.research.fixtures import with_quotes
    s = evidence(live_snapshot(held={"NVDAB": 1000}, gas_low=True), "4.02")
    c = s.context.read()
    c["health"]["new_spending_ok"] = False
    s = with_quotes(changed(s, health=c["health"]))
    c = s.context.read()
    for m in c["markets"]:
        for q in m["quotes"]:
            q["origin"] = "WEB3_OPEN_API"
    s = changed(s, markets=c["markets"])
    r = plan(s, decide(s, s.policy_state)).read()
    assert r["intents"][0]["side"] == "SELL" and r["intents"][0]["symbol"] == "NVDAB"
