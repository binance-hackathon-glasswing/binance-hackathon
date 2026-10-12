"""P01 synthetic raw Web3 rows on an explicit fixture calendar, including DST."""

from datetime import timedelta
from dataclasses import replace

import pytest

from larp.contracts import ContractError, Document, TargetKind
from larp.strategy.schema import instant
from larp.strategy.sessions import token_sessions
from larp.strategy.features import features
from larp.strategy.policy import decide
from larp.research.fixtures import changed
from tests.strategy.live_fixtures import live_snapshot


def inputs():
    # Friday before and Monday after US DST ends. Their calendar indexes are consecutive.
    sessions = [{"session_index": i, "open_at": opened, "close_at": closed}
        for i, opened, closed in ((10, "2026-10-30T13:30:00Z", "2026-10-30T20:00:00Z"),
                                  (11, "2026-11-02T14:30:00Z", "2026-11-02T21:00:00Z"))]
    rows = []
    for session in sessions:
        start = instant(session["open_at"]) - timedelta(minutes=30)
        for i in range(7):
            ts = int((start + timedelta(hours=i)).timestamp() * 1000)
            rows.append(["10", "11", "9", str(10 + i), "5", ts, 1])
    capture = {"schema": "TokenCandles.v1", "symbol": "GOOGLB", "token_id": "fixture-googl-token",
               "entity_id": "fixture-googl-issuer", "source_id": "SYNTHETIC_WEB3_ROWS", "content_hash": "a" * 64,
               "available_at": "2026-11-02T21:00:01Z", "timestamp_kind": "OPEN", "bar_seconds": 3600,
               "token_adjustment_version": "synthetic-no-actions", "candles": rows}
    calendar = {"schema": "USRegularSessions.v1", "calendar_id": "synthetic-2026-calendar",
                "content_hash": "b" * 64, "sessions": sessions}
    return capture, calendar


def build(capture, calendar):
    return token_sessions(Document.from_dict(capture), Document.from_dict(calendar),
                          cutoff=instant("2026-11-02T21:00:02Z")).read()


def test_fixed_us_close_utc_dst_and_first_date():
    capture, calendar = inputs()
    result = build(capture, calendar)
    assert [b["close_at"] for b in result["bars"]] == ["2026-10-30T20:00:00+00:00", "2026-11-02T21:00:00+00:00"]
    assert result["first_candle_at"] == "2026-10-30T13:00:00+00:00"
    assert result["instrument_kind"] == "TOKEN"
    assert not result["missing_sessions"]


def test_missing_trade_interval_remains_missing_session():
    capture, calendar = inputs()
    capture["candles"].pop(3)
    result = build(capture, calendar)
    assert result["missing_sessions"] == [10]
    assert [b["session_index"] for b in result["bars"]] == [11]
    capture["candles"] = []
    assert build(capture, calendar)["first_candle_at"] is None


def test_duplicate_future_capture_wrong_timestamp_and_bad_calendar_reject():
    for case in ("duplicate", "future", "timestamp", "calendar"):
        capture, calendar = inputs()
        if case == "duplicate":
            capture["candles"].append(capture["candles"][0])
        elif case == "future":
            capture["available_at"] = "2026-11-03T00:00:00Z"
        elif case == "timestamp":
            capture["timestamp_kind"] = "UNKNOWN"
        else:
            calendar["sessions"][1]["session_index"] = 12
        with pytest.raises(ContractError):
            build(capture, calendar)


def test_short_session_and_bar_crossing_close_cannot_supply_1600_close():
    capture, calendar = inputs()
    calendar["sessions"][0]["close_at"] = "2026-10-30T17:00:00Z"
    assert 10 in build(capture, calendar)["missing_sessions"]
    capture, calendar = inputs()
    capture["bar_seconds"] = 7200
    with pytest.raises(ContractError):
        build(capture, calendar)  # overlapping source intervals, not silently resampled


def test_token_history_is_explicit_optional_and_not_underlying_share_history():
    capture, calendar = inputs()
    doc = Document.from_dict(build(capture, calendar))
    result = features(doc, cutoff=instant("2026-11-02T21:00:02Z"),
                      expected_entity="fixture-googl-issuer", max_age_seconds=86400).read()
    assert result["reasons"] == ["IDENTITY_UNITS_OR_PROVENANCE"]
    token = features(doc, cutoff=instant("2026-11-02T21:00:02Z"), expected_entity="fixture-googl-issuer",
                     expected_instrument="TOKEN", expected_token="fixture-googl-token", max_age_seconds=86400).read()
    assert token["reasons"] == ["INSUFFICIENT_60_SESSION_HISTORY"]
    s = changed(live_snapshot(), series={})
    assert any(t.kind is TargetKind.TARGET_WEIGHT for t in decide(s, s.policy_state).targets)
