"""Visibly synthetic interface fixtures; this module has no live adapter."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from larp.contracts import DecisionSnapshot, Document, PolicyState
from larp.strategy.policy import decide
from larp.risk.planner import plan
from larp.strategy.schema import floor, value


def synthetic_profile(**changes):
    p = json.loads((Path(__file__).resolve().parents[2] / "config/strategy/offline-fixture.json").read_text())
    p.update(changes)
    return p


def snapshot(*, held=None, profile_changes=None, now=None, state=None):
    now = now or datetime(2026, 10, 10, 14, tzinfo=timezone.utc)
    p = synthetic_profile(**(profile_changes or {}))
    symbols = ("NVDAB", "GOOGLB", "TSLAB", "MSFTB")
    held = held or {}
    state = state or PolicyState("synthetic-run", p["policy_id"], "Lifecycle.v1", 0, Document.from_dict({}))
    cash = 199_000_000 - sum(held.values()) * 10_000
    ledger = {"schema": "PortfolioState.v1", "run_id": "synthetic-run", "wallet_id": "fake-wallet",
              "cash_units": cash, "bnb_units": 1_000_000, "bnb_price_units": 1_000_000,
              "bnb_decimals": 6, "opening_equity_units": 200_000_000,
              "positions": {s: {"units": held.get(s, 0), "decimals": 4,
                                "cost_basis_units": held.get(s, 0) * 10_000} for s in symbols},
              "reservations": {}, "applied_events": {},
              "accounting": {"realized_units": 0, "fees_units": 0, "gas_value_units": 0,
                             "service_units": 0, "turnover_units": 0},
              "risk": {"day": now.date().isoformat(), "day_anchor_units": 200_000_000,
                       "peak_units": 200_000_000, "daily_halt": False,
                       "run_halt": False, "deep_cut": False}}
    market, series = [], {}
    for symbol in symbols:
        issuer = "fixture-issuer-" + symbol
        market.append({"schema": "MarketObservation.v1", "symbol": symbol,
                       "underlying_id": issuer, "token_id": "fixture-token-" + symbol,
                       "decimals": 4, "currency": "USDT", "money_scale": 1_000_000,
                       "price_units": 100_000_000, "source_id": "SCRIPTED_FAKE",
                       "content_hash": "f" * 64, "quality": "VALID", "observed_at": now.isoformat(),
                       "available_at": now.isoformat(), "close_at": now.isoformat(),
                       "token_open": True, "underlying_open": True, "basis_verified": True,
                       "measured_roundtrip_bps": 20, "quotes": []})
        days, day = [], now - timedelta(days=1)
        while len(days) < 61:
            if day.weekday() < 5:
                days.append(day)
            day -= timedelta(days=1)
        days.reverse()
        close, bars = 100_000_000, []
        for i, day in enumerate(days):
            close = close * (102 if i % 2 else 98) // 100
            bars.append({"session_index": i, "close_units": close, "close_at": day.isoformat(),
                         "available_at": day.isoformat(), "corporate_action_version": "synthetic-no-actions",
                         "quality": "VALID"})
        series[symbol] = {"schema": "PriceSeries.v1", "entity_id": issuer,
                          "instrument_kind": "UNDERLYING_SHARE", "currency": "USD",
                          "price_scale": 1_000_000, "source_id": "SCRIPTED_FAKE", "quality": "VALID",
                          "content_hash": "e" * 64, "calendar_id": "SYNTHETIC_WEEKDAY_SESSIONS",
                          "corporate_action_version": "synthetic-no-actions", "bars": bars}
    context = {"schema": "StrategyContext.v1", "origin": "SYNTHETIC_VERIFICATION",
               "profile": p, "portfolio": ledger, "markets": market, "series": series,
               "session_index": 80, "remaining_sessions": 10, "assessments": [],
               "reduction_constraints": [], "last_discretionary_session": None,
               "health": {"integrity_ok": True, "journal_ok": True,
                          "ownership_ok": True, "clock_ok": True}}
    return DecisionSnapshot("synthetic-run", "fake-wallet", "fixture-build",
                            Document.from_dict(p).digest("StrategyProfile.v1"), 1,
                            now, symbols, state, Document.from_dict(context))


def changed(s, **changes):
    c = s.context.read()
    c.update(changes)
    return replace(s, context=Document.from_dict(c))


def with_quotes(s, *, spread_bps=10, gas=10000, policy=True):
    """Temporary fake observe(MarketRequest.v1) implementation, size bound."""
    proposal = decide(s, s.policy_state) if policy else None
    requests = plan(s, proposal).read()["quote_requests"]
    c = s.context.read()
    for request in requests:
        m = next(m for m in c["markets"] if m["symbol"] == request["symbol"])
        mark = floor(value(request["token_units"], m))
        cash = mark * (10000 + spread_bps if request["side"] == "BUY" else 10000 - spread_bps) // 10000
        m["quotes"].append({"quote_id": "fake-" + request["symbol"] + request["side"],
                            "side": request["side"], "token_units": request["token_units"],
                            "cash_units": cash, "fee_units": 0, "gas_bnb_units": gas,
                            "route_valid": True, "slippage_bps": 20, "impact_bps": spread_bps,
                            "quoted_depth_units": request["token_units"] * 100,
                            "available_at": s.observed_at.isoformat(), "observed_at": s.observed_at.isoformat(),
                            "expires_at": (s.observed_at + timedelta(seconds=30)).isoformat(),
                            "origin": "SCRIPTED_FAKE"})
    return changed(s, markets=c["markets"])


def reserve_fixture(s, result):
    """Fake external atomic-commit receipt; never a production store/authorization."""
    c = s.context.read()
    for r in result.read()["reservation_deltas"]:
        c["portfolio"]["reservations"][r["intent_id"]] = r
    return changed(s, portfolio=c["portfolio"])


def fill_fixture(s, intent, *, kind="FILL", gas=10000, terminal=True):
    return Document.from_dict({"schema": "ExecutionObservation.v1", "origin": "SCRIPTED_FAKE",
                               "run_id": s.run_id, "wallet_id": s.wallet_id,
                               "event_id": "fake-" + kind + "-" + intent["intent_id"],
                               "intent_id": intent["intent_id"], "observed_at": s.observed_at.isoformat(),
                               "settlement": "FINAL", "kind": kind, "gas_bnb_units": gas,
                               "gas_value_units": gas, "intent_terminal": terminal,
                               "symbol": intent["symbol"], "side": intent["side"],
                               "token_units": intent["token_units"], "cash_units": intent["cash_units"],
                               "fee_units": intent["fee_units"]})
