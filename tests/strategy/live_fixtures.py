"""Synthetic representations of PROPOSED live interfaces; no real captures."""

from dataclasses import replace

from larp.contracts import Document
from larp.research.fixtures import snapshot, changed, with_quotes
from larp.strategy.profiles import build_live_profiles
from larp.strategy.schema import SYMBOLS


def registry():
    d = {"schema": "RedFlagPredicates.v1", "version": "synthetic-test-v1",
         "producer_commit": "a" * 40, "records": [
             {"predicate_id": "F-ITEM-" + item, "item": item, "class": kind,
              "action": action, "block_sessions": length, "verification_fixture_hashes": ["b" * 64]}
             for item, kind, action, length in (("4.02", 1, "DISCRETIONARY_EXIT", 0),
                 ("1.05", 2, "ENTRY_BLOCK", 5), ("2.06", 2, "ENTRY_BLOCK", 5))]}
    d["records"].append({"predicate_id": "statement-watch", "item": "STATEMENTS", "kind": "STATEMENT",
        "class": 3, "action": "SHADOW", "block_sessions": 0, "verification_fixture_hashes": ["c" * 64]})
    d["content_hash"] = Document.from_dict(d).digest("RedFlagPredicates.v1")
    return Document.from_dict(d)


def summary():
    return Document.from_dict({"schema": "QuoteCostSummary.v1", "origin": "RECORDED_WEB3",
        "capture_hash": "d" * 64, "observed_at": "2026-10-19T00:00:00Z", "bnb_price_units": 1_000_000,
        "bnb_decimals": 6, "symbols": {symbol: {"samples": 10, "median_impact_bps": 10,
            "spread_bps": 5, "fee_bps": 1, "approve_gas_bnb_units": 10000,
            "swap_gas_bnb_units": 10000, "slippage_bps": 20, "quote_ttl_seconds": 30}
            for symbol in sorted(SYMBOLS)}})


def live_snapshot(*, held=None, now=None, gas_low=False, quoted=False):
    from larp.strategy.schema import instant
    p = build_live_profiles(summary(), registry())["FINAL"].read()
    s = snapshot(held=held, now=now or instant("2026-10-29T14:00:00Z"))
    c = s.context.read()
    c.update(profile=p, red_flag_predicates=registry().read())
    c["health"]["new_spending_ok"] = True
    for m in c["markets"]:
        m.update(origin="WEB3_OPEN_API", source_id="WEB3")
    if gas_low:
        c["portfolio"]["bnb_units"] = 60_000
    s = replace(s, policy_profile_hash=Document.from_dict(p).digest("StrategyProfile.v1"),
                policy_state=replace(s.policy_state, policy_id=p["policy_id"]), context=Document.from_dict(c))
    if quoted:
        s = with_quotes(s)
        c = s.context.read()
        for m in c["markets"]:
            for q in m["quotes"]:
                q["origin"] = "WEB3_OPEN_API"
                q.pop("quoted_depth_units", None)
        s = changed(s, markets=c["markets"])
    return s
