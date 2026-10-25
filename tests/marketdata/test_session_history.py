"""IDEA-103 TH-01: all history/semantics here are synthetic; no network or real credentials."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from larp.contracts import ContractError, Document
from larp.marketdata.history import SessionHistory, configuration, settings, HOUR_MS, RETRY_MS
from larp.marketdata.port import TOKENS
from larp.marketdata.web3 import Unavailable
from larp.strategy.schema import instant
from tests.strategy.test_s1_plan import snap

SEMANTICS = dict(schema='TokenHistoryConfig.v1', timestamp_kind='OPEN',
                 timestamp_evidence_sha256='e'*64, token_adjustment_version='SYNTHETIC-no-actions')
DATES = ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23', '2026-10-26']
CALENDAR = dict(schema='USRegularSessions.v1', calendar_id='SYNTHETIC-HISTORY', sessions=[
    dict(session_index=75+i, open_at=d+'T13:30:00Z', close_at=d+'T20:00:00Z') for i,d in enumerate(DATES)])
ISSUERS = {s: dict(token=s, underlying_id='SYNTHETIC-'+s) for s in TOKENS}
NOW = int(instant('2026-10-23T20:20:00Z').timestamp()*1000)


def rows(prices=(100,100,100,100,100,100), calendar=CALENDAR):
    out = []
    for session, price in zip(calendar['sessions'], prices):
        start = instant(session['open_at']) - timedelta(minutes=30)
        close = instant(session['close_at'])
        while start < close:
            out.append([price, price, price, price, '5', int(start.timestamp()*1000), 1])
            start += timedelta(hours=1)
    return out


class Port:
    def __init__(self, source=None, available=NOW-1):
        self.source, self.available, self.calls = rows() if source is None else source, available, []
        self.fail = False
        self.page_size = 300
        self.ignore_cursor = False
        self.transform = lambda s, r: r

    def candles(self, symbol, *, bar, limit, after=None):
        self.calls.append((symbol, after))
        if self.fail:
            raise Unavailable('synthetic failure; private text must not reach decision context')
        eligible = [r for r in self.source if after is None or self.ignore_cursor or int(r[5]) <= after]
        return dict(schema='RawTokenCandles.v1', symbol=symbol, token_id=TOKENS[symbol], bar=bar,
            rows=self.transform(symbol, deepcopy(eligible[-self.page_size:])), content_hash='a'*64,
            available_at=datetime.fromtimestamp(self.available/1000, timezone.utc).isoformat())


def reader(tmp_path, port=None, calendar=CALENDAR, profile=None):
    return SessionHistory(port or Port(), profile=profile or snap().context.read()['profile'], calendar=calendar,
        calendar_sha256=Document.from_dict(calendar).digest('synthetic-calendar'), issuers=ISSUERS,
        semantics=SEMANTICS, root=tmp_path)


def test_all_five_series_use_only_completed_session_closes(tmp_path):
    port = Port(source=rows(prices=(100.5,100.5,100.5,100.5,100.5,999)))
    output = reader(tmp_path, port)(NOW)
    assert set(output) == set(TOKENS)
    for symbol, series in output.items():
        assert series['quality'] == 'VALID' and series['history_status'] == 'READY'
        assert series['token_id'] == TOKENS[symbol]
        assert [b['session_index'] for b in series['bars']] == list(range(75,80))
        assert [b['close_units'] for b in series['bars']] == [100_500_000]*5
        assert all(instant(b['available_at']) <= instant('2026-10-23T20:20:00Z') for b in series['bars'])
    assert len(port.calls) == 5


def test_cached_session_survives_restart_and_refreshes_after_next_close_delay(tmp_path):
    port = Port()
    history = reader(tmp_path, port)
    first = history(NOW)
    assert history(NOW+RETRY_MS) == first
    assert reader(tmp_path, port)(NOW+2*RETRY_MS) == first
    monday = int(instant('2026-10-26T20:14:59Z').timestamp()*1000)
    assert reader(tmp_path, port)(monday) == first
    assert len(port.calls) == 5
    output = reader(tmp_path, port)(monday+1000)
    assert len(port.calls) == 10
    assert all(s['bars'][-1]['session_index'] == 80 for s in output.values())


def test_fetch_after_cutoff_is_only_available_on_later_decision(tmp_path):
    port = Port(available=NOW+2000)
    history = reader(tmp_path, port)
    assert {s['history_status'] for s in history(NOW).values()} == {'AWAITING_CAPTURE_CUTOFF'}
    assert all(s['quality'] == 'VALID' for s in history(NOW+2000).values())
    assert len(port.calls) == 5


@pytest.mark.parametrize('defect', ['missing', 'no-trades', 'future-capture', 'nan', 'bad-volume', 'misaligned'])
def test_incomplete_or_invalid_data_does_not_fabricate_a_window(tmp_path, defect):
    port = Port()
    if defect == 'missing':
        port.source.pop(5)
    elif defect == 'no-trades':
        port.source[5][6] = None
    elif defect == 'future-capture':
        port.available = NOW + 86_400_000
    elif defect == 'nan':
        port.source[5][3] = 'NaN'
    elif defect == 'bad-volume':
        port.source[5][4] = '-1'
    else:
        port.source[5][5] += 1
    result = reader(tmp_path, port)(NOW)
    assert all(s['quality'] == 'UNAVAILABLE' for s in result.values())


def test_transport_errors_are_throttled_and_never_exposed(tmp_path):
    port = Port(); port.fail = True
    history = reader(tmp_path, port)
    result = history(NOW)
    assert all(s['history_status'] == 'HISTORY_UNAVAILABLE' for s in result.values())
    assert 'private text' not in json.dumps(result)
    history(NOW+1)
    reader(tmp_path, port)(NOW+2)
    assert len(port.calls) == 1
    port.fail = False
    assert all(s['quality'] == 'VALID' for s in history(NOW+RETRY_MS).values())
    assert len(port.calls) == 6


def test_two_page_budget_and_ignored_cursor_refuse_silently_repeating_source(tmp_path):
    port = Port(); port.page_size = 25
    result = reader(tmp_path, port)(NOW)
    assert len(port.calls) == 10
    assert all(s['quality'] == 'VALID' for s in result.values())
    port = Port(); port.page_size = 25; port.ignore_cursor = True
    result = reader(tmp_path/'ignored', port)(NOW)
    assert len(port.calls) == 2
    assert all(s['quality'] == 'UNAVAILABLE' for s in result.values())


def test_cache_corruption_and_changed_semantics_do_not_supply_prices(tmp_path):
    port = Port()
    history = reader(tmp_path, port)
    history(NOW)
    history.path.write_text('{broken')
    reader(tmp_path, port)(NOW)
    assert len(port.calls) == 10
    value = dict(SEMANTICS, token_adjustment_version='SYNTHETIC-v2')
    changed = SessionHistory(port, profile=snap().context.read()['profile'], calendar=CALENDAR,
        calendar_sha256=Document.from_dict(CALENDAR).digest('synthetic-calendar'), issuers=ISSUERS,
        semantics=value, root=tmp_path)
    changed(NOW)
    assert len(port.calls) == 15


def test_dst_and_early_close_follow_frozen_calendar(tmp_path):
    dates = [('2026-10-29','13:30','20:00'), ('2026-10-30','13:30','20:00'),
             ('2026-11-02','14:30','21:00'), ('2026-11-03','14:30','21:00'),
             ('2026-11-27','14:30','18:00')]
    cal = dict(schema='USRegularSessions.v1', calendar_id='SYNTHETIC-DST-EARLY', sessions=[dict(
        session_index=i, open_at=d+'T'+o+':00Z', close_at=d+'T'+c+':00Z') for i,(d,o,c) in enumerate(dates)])
    now = int(instant('2026-11-27T18:15:00Z').timestamp()*1000)
    output = reader(tmp_path, Port(source=rows(calendar=cal), available=now-1), calendar=cal)(now)
    assert all(s['quality'] == 'VALID' for s in output.values())
    assert [b['close_at'] for b in output['NVDAB']['bars']][-3:] == [
        '2026-11-02T21:00:00+00:00','2026-11-03T21:00:00+00:00','2026-11-27T18:00:00+00:00']


@pytest.mark.parametrize('defect', ['missing', 'half', 'relative', 'hash'])
def test_fs1_refuses_missing_or_unpinned_configuration(defect):
    profile = dict(snap().context.read()['profile'], policy_id='larp-fs1-final-v1')
    driver = dict(token_history_file='/etc/larp/token-history.json', token_history_sha256='a'*64)
    if defect == 'missing': driver = {}
    if defect == 'half': del driver['token_history_sha256']
    if defect == 'relative': driver['token_history_file'] = 'relative.json'
    if defect == 'hash': driver['token_history_sha256'] = 'bad'
    with pytest.raises(ContractError): settings(driver, profile)
    assert settings({}, dict(profile, policy_id='old-s1')) is None


def test_semantics_are_explicit_and_not_inferred_from_candle_labels():
    assert configuration(SEMANTICS) == SEMANTICS
    for bad in (dict(SEMANTICS,timestamp_kind='CLOSE'), dict(SEMANTICS,timestamp_evidence_sha256=''),
                dict(SEMANTICS,token_adjustment_version=''), dict(SEMANTICS,extra=True)):
        with pytest.raises(ContractError): configuration(bad)
