"""IDEA-044: generated capture regressions, never original market-data reruns."""
from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path

import pytest

from larp.research.candles import BSTOCKS, capture_cutoff_ms, closed_bstock_bars
from tools.realised_vol import bstock_series, ondo_series, stats

DAY = 86_400_000


def capture(rows=None, *, bar="1d", cutoff="1970-01-03T00:00:00Z"):
    return {"report": {"run_utc": cutoff}, "raw": [
        {"endpoint": "rwa/underlying-market", "symbol": "NVDAB"},
        {"bar": bar, "response": {"code": 0, "data": rows if rows is not None else [row(0)]}},
    ]}


def row(stamp, close="100"):
    return ["100", "101", "99", close, "1", stamp, 1]


def save(tmp_path, data):
    path = tmp_path / "synthetic-capture.json"
    path.write_text(json.dumps(data))
    return path


def test_annualization_counts_return_intervals_not_closes():
    prices = [(i * DAY, 100 * (1.01 if i % 2 else 1)) for i in range(21)]
    result = stats(prices)
    assert result["bars_per_year"] == 365
    assert result["vol_ann"] == pytest.approx(result["vol_bar"] * math.sqrt(365))


def test_closed_capture_uses_utc_boundary_and_deduplicates_identical_pages(tmp_path):
    data = capture([row(0), row(DAY), row(2 * DAY)])
    data["raw"].append(deepcopy(data["raw"][1]))
    result = bstock_series(save(tmp_path, data))
    assert result["NVDAB"] == [(0, 100), (DAY, 100)]
    assert result["GOOGLB"] == []
    assert capture_cutoff_ms({"report": {"run_utc": "19700103T000000Z"}}) == 2 * DAY


def test_explicit_entity_metadata_wins_and_failed_bodies_supply_no_bars():
    data = capture()
    data["raw"][1]["symbol"] = "GOOGLB"
    data["raw"].append({"symbol": "NVDAB", "bar": "1d", "response": {"code": 500, "data": [row(0)]}})
    bars = closed_bstock_bars(data, "1d", DAY)
    assert list(bars["GOOGLB"]) == [0]
    assert not bars["NVDAB"]


@pytest.mark.parametrize("change", ["conflict", "nan", "zero", "negative", "fractional-time", "unknown-entity",
                                     "boolean-price", "boolean-volume"])
def test_ambiguous_or_invalid_capture_cannot_become_measured_evidence(change):
    data = capture()
    if change == "conflict":
        data["raw"][1]["response"]["data"].append(row(0, "110"))
    elif change == "unknown-entity":
        data["raw"][0]["symbol"] = "OTHER"
    elif change == "fractional-time":
        data["raw"][1]["response"]["data"][0][5] = 0.5
    elif change in ("boolean-price", "boolean-volume"):
        data["raw"][1]["response"]["data"][0][3 if change == "boolean-price" else 4] = True
    else:
        data["raw"][1]["response"]["data"][0][3] = {"nan": "nan", "zero": "0", "negative": "-1"}[change]
    with pytest.raises(ValueError):
        closed_bstock_bars(data, "1d", DAY)


@pytest.mark.parametrize("cutoff", [None, "1970-01-03T00:00:00", "bad"])
def test_capture_needs_an_explicit_trusted_cutoff(cutoff):
    data = capture(cutoff=cutoff)
    with pytest.raises(ValueError):
        closed_bstock_bars(data, "1d", DAY)
    assert closed_bstock_bars(data, "1d", DAY, as_of_ms=2 * DAY)["NVDAB"]


def ondo_capture():
    return {"report": {"run_utc": "19700103T000000Z", "B_tokenized_securities_info": {
                "NVDAB": {"ondo_token": {"symbol": "NVDAon", "contract": "0xabc"}}}},
            "raw": [{"url": "https://fixture.invalid/kline?contractAddress=0xabc", "status": 200,
                     "body": {"code": "000000", "data": {"klineInfos": [
                         [stamp, "100", "101", "99", "100", None, stamp + DAY - 1]
                         for stamp in (0, DAY, 2 * DAY)]}}}]}


def test_ondo_excludes_open_bar_and_deduplicates_pagination(tmp_path):
    data = ondo_capture()
    data["raw"].append(deepcopy(data["raw"][0]))
    assert ondo_series(save(tmp_path, data)) == {"NVDAon": [(0, 100), (DAY, 100)]}


def test_ondo_conflicting_versions_reject_and_error_payload_is_ignored(tmp_path):
    data = ondo_capture()
    data["raw"].append(deepcopy(data["raw"][0]))
    data["raw"][1]["body"]["data"]["klineInfos"][0][4] = "110"
    with pytest.raises(ValueError):
        ondo_series(save(tmp_path, data))
    data["raw"][1]["status"] = 500
    assert ondo_series(save(tmp_path, data))["NVDAon"] == [(0, 100), (DAY, 100)]


@pytest.mark.parametrize("column,value", [(0, True), (0, 0.5), (0, "0.5"),
                                          (6, True), (6, DAY - 0.5), (4, True)])
def test_ondo_rejects_coerced_boolean_or_fractional_values(tmp_path, column, value):
    data = ondo_capture()
    data["raw"][0]["body"]["data"]["klineInfos"][0][column] = value
    with pytest.raises(ValueError):
        ondo_series(save(tmp_path, data))


def test_ondo_accepts_digit_string_millisecond_timestamps(tmp_path):
    data = ondo_capture()
    for candle in data["raw"][0]["body"]["data"]["klineInfos"]:
        candle[0], candle[6] = str(candle[0]), str(candle[6])
    assert ondo_series(save(tmp_path, data))["NVDAon"] == [(0, 100), (DAY, 100)]


def module(name):
    path = Path(__file__).resolve().parents[2] / "tools" / "idea018" / (name + ".py")
    spec = importlib.util.spec_from_file_location("review_" + name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


@pytest.mark.parametrize("name", ["analyse_candles", "variants"])
@pytest.mark.parametrize("constant", [False, True])
def test_research_reports_missing_or_constant_data_inconclusive_without_crashing(tmp_path, capsys, name, constant):
    data = capture([], cutoff="1970-01-05T00:00:00Z")
    if constant:
        data["raw"] = [
            {"symbol": symbol, "bar": bar, "response": {"code": 0, "data": [row(i * interval) for i in range(3)]}}
            for symbol in BSTOCKS for bar, interval in (("1h", 3_600_000), ("1m", 60_000), ("1d", DAY))]
    module(name).main(save(tmp_path, data))
    output = capsys.readouterr().out
    assert "INCONCLUSIVE" in output
    assert "95% CI" not in output
