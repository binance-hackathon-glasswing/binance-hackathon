"""P05 UTC boundary/collision tests on synthetic market observations."""

from dataclasses import replace
from datetime import timedelta

import pytest

from larp.contracts import Document, TargetKind
from larp.research.fixtures import changed
from larp.risk.planner import plan
from larp.risk.accounting import advance_accounting
from larp.strategy.policy import decide
from larp.strategy.schema import instant
from tests.strategy.live_fixtures import live_snapshot
from tests.risk.test_live_resource_receipts import receipt


def test_no_buys_before_start_or_after_new_risk_cut():
    for now, can_buy in (("2026-10-28T23:59:59Z", False), ("2026-10-29T00:00:00Z", True),
                         ("2026-11-08T23:59:59Z", True), ("2026-11-09T00:00:00Z", False)):
        s = live_snapshot(now=instant(now))
        assert bool([t for t in decide(s, s.policy_state).targets if t.kind is TargetKind.TARGET_WEIGHT]) == can_buy


def test_terminal_survives_absent_policy_and_blocked_rounds_until_final_receipt():
    s = live_snapshot(held={"NVDAB": 1000}, now=instant("2026-11-10T00:00:00Z"), quoted=True)
    c = s.context.read()
    c["health"]["integrity_ok"] = False
    r = plan(changed(s, health=c["health"]), None).read()
    assert not r["intents"] and "TERMINAL_FLATTEN" in r["requirements"][0]["reasons"]
    ready = plan(s, None)
    assert ready.read()["intents"][0]["mandatory"] is True
    before, e = receipt(s, ready)
    after = advance_accounting(before, Document.from_dict(e))
    r = plan(changed(s, portfolio=after.read()), None).read()
    assert not r["requirements"] and not r["intents"]


@pytest.mark.parametrize("gate", ["market", "mark", "gas", "signing_end", "slippage"])
def test_terminal_retains_unfilled_position_when_execution_gate_blocks(gate):
    now = instant("2026-11-11T14:44:59Z" if gate != "signing_end" else "2026-11-11T14:45:00Z")
    s = live_snapshot(held={"NVDAB": 1000}, now=now, quoted=True)
    c = s.context.read()
    if gate == "market":
        c["markets"][0]["token_open"] = False
    elif gate == "mark":
        c["markets"][0]["quality"] = "STALE"
    elif gate == "gas":
        c["portfolio"]["bnb_units"] = 0
    elif gate == "slippage":
        c["markets"][0]["quotes"][0]["slippage_bps"] = 10000
    s = changed(s, **c)
    r = plan(s, None).read()
    assert not r["intents"]
    assert r["requirements"][0]["remaining_sell_units"] == 1000
    assert s.context.read()["portfolio"]["positions"]["NVDAB"]["units"] == 1000


def test_mandatory_sale_bypasses_impact_cost_minimum_and_cadence():
    s = live_snapshot(held={"NVDAB": 100}, now=instant("2026-11-10T00:00:00Z"), quoted=True)
    c = s.context.read()
    q = c["markets"][0]["quotes"][0]
    cash = q["cash_units"] // 2
    q.update(impact_bps=500, cash_units=cash, min_receive_units=cash * 9980 // 10000)
    s = changed(s, markets=c["markets"], last_discretionary_session=c["session_index"])
    r = plan(s, None).read()
    assert r["intents"][0]["side"] == "SELL" and r["intents"][0]["mandatory"]
    assert r["clamps"] and r["requirements"][0]["max_units"] == 0
