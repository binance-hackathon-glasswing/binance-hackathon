"""LD10-P03: complete mandatory exits split into balanced children, never a cap-ratio residual."""

from datetime import timedelta
from fractions import Fraction

import pytest

from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.schema import instant, value
from tests.strategy.live_fixtures import live_snapshot

TERMINAL = instant("2026-11-10T00:00:00Z")


def terminal(units):
    return live_snapshot(held={"NVDAB": units}, now=TERMINAL)


def quoted(s):
    s = with_quotes(s, policy=False)
    c = s.context.read()
    for q in c["markets"][0]["quotes"]:
        q["origin"] = "WEB3_OPEN_API"
    return changed(s, markets=c["markets"])


def cap_units(s):
    p, m = s.context.read()["profile"], s.context.read()["markets"][0]
    return p["per_trade_cap_units"] * 10**m["decimals"] // m["price_units"]


def exit_sequence(units):
    """Settle each planned child exactly (exact-in) and replan until the position is gone."""
    children, held = [], units
    while held:
        s = quoted(terminal(held))
        r = plan(s, None).read()
        assert len(r["intents"]) == 1 and r["intents"][0]["mandatory"]
        child = r["intents"][0]
        assert child["side"] == "SELL" and child["pay_units"] == child["token_units"]
        children.append(child)
        held -= child["token_units"]
        assert len(children) < 10
    return children


@pytest.mark.parametrize("ratio", [Fraction(3, 2), Fraction(4021, 4020), Fraction(197, 100)])
def test_over_cap_exit_children_are_balanced_and_sum_to_position(ratio):
    s = terminal(1)
    cap = s.context.read()["profile"]["per_trade_cap_units"]
    units = int(cap_units(s) * ratio)
    children = exit_sequence(units)
    assert sum(c["token_units"] for c in children) == units
    assert len(children) == 2
    m = s.context.read()["markets"][0]
    for c in children:
        mark = value(c["token_units"], m)
        assert mark * 10100 <= cap * 10000          # at most cap/1.01 at the mark
        assert mark * 202 > cap * 100               # never a dust-sized residual (> cap/2.02)
        assert c["cash_units"] + c["fee_units"] <= cap


def test_first_request_for_one_and_a_half_caps_is_half_the_position():
    s = terminal(1)
    units = cap_units(s) * 3 // 2
    r = plan(terminal(units), None).read()
    assert r["quote_requests"][0]["pay_units"] == units // 2
    assert r["quote_requests"][0]["mandatory"] is True


def test_position_below_split_threshold_exits_in_one_unchanged_child():
    s = terminal(1)
    units = cap_units(s) * 100 // 102
    children = exit_sequence(units)
    assert [c["token_units"] for c in children] == [units]


def test_over_cap_mandatory_quote_resizes_to_balanced_half_not_cap_ratio():
    s = terminal(1)
    p = s.context.read()["profile"]
    units = cap_units(s) * 97 // 100            # one child by mark value
    s = terminal(units)
    assert plan(s, None).read()["quote_requests"][0]["pay_units"] == units
    c = s.context.read()
    cash = p["per_trade_cap_units"] + 1          # quote proceeds above the mark and the cap
    c["markets"][0]["quotes"] = [{"quote_id": "over-cap", "side": "SELL", "token_units": units,
        "amount_kind": "EXACT_IN", "pay_asset": "NVDAB", "pay_units": units,
        "min_receive_units": cash * (10000 - p["slippage_bps"]) // 10000 + 1, "cash_units": cash,
        "fee_units": 0, "gas_bnb_units": 10000, "route_valid": True, "slippage_bps": p["slippage_bps"],
        "impact_bps": 1, "available_at": TERMINAL.isoformat(), "observed_at": TERMINAL.isoformat(),
        "expires_at": (TERMINAL + timedelta(seconds=30)).isoformat(), "origin": "WEB3_OPEN_API"}]
    r = plan(changed(s, markets=c["markets"]), None).read()
    assert not r["intents"]
    assert r["quote_requests"][0]["pay_units"] == units // 2
    assert {"symbol": "NVDAB", "reason": "EXECUTABLE_TRADE_CAP"} in r["rejections"]


def test_exit_parts_boundaries():
    from larp.risk.planner import exit_parts
    assert exit_parts(0, 100) == 1
    assert exit_parts(Fraction(10000, 101), 100) == 1   # exactly cap/1.01
    assert exit_parts(Fraction(10000, 101) + Fraction(1, 10**9), 100) == 2
    assert exit_parts(101, 100) == 2
    assert exit_parts(Fraction(20000, 101), 100) == 2
    assert exit_parts(199, 100) == 3
    for bad in (-1, True, 1.5):
        with pytest.raises((TypeError, ValueError)):
            exit_parts(bad, 100)
    with pytest.raises((TypeError, ValueError)):
        exit_parts(1, 0)


def test_full_portfolio_flatten_completes_on_the_bnb_held_at_new_risk_end():
    """#56 / WR14 with LD10-P03: four positions above the split threshold, no top-up, 15-minute rounds."""
    s = terminal(1)
    p = s.context.read()["profile"]
    units = cap_units(s) * 6 // 5                       # 1.2 x cap each: two balanced children per name
    held = {sym: units for sym in ("NVDAB", "GOOGLB", "TSLAB", "MSFTB")}
    now, rounds, children = TERMINAL, 0, []
    bnb = 8 * 10000                                       # exactly eight children of fixture quote gas; no top-up
    while any(held.values()):
        snap = live_snapshot(held={k: v for k, v in held.items() if v}, now=now)
        c = snap.context.read()
        c["portfolio"]["bnb_units"] = bnb
        snap = with_quotes(changed(snap, portfolio=c["portfolio"]), policy=False)
        c = snap.context.read()
        for m in c["markets"]:
            for q in m["quotes"]:
                q["origin"] = "WEB3_OPEN_API"
        r = plan(changed(snap, markets=c["markets"]), None).read()
        assert len(r["intents"]) == 1, r["rejections"]
        child = r["intents"][0]
        assert child["side"] == "SELL" and child["mandatory"]
        assert child["cash_units"] + child["fee_units"] <= p["per_trade_cap_units"]
        held[child["symbol"]] -= child["token_units"]
        bnb -= child["gas_bnb_units"]
        assert bnb >= 0
        children.append(child)
        rounds += 1
        now += timedelta(minutes=15)
        assert rounds <= 16
    assert len(children) == 8 and sum(c["token_units"] for c in children) == 4 * units
    assert now <= instant(p["signing_end"])
