"""IDEA-105 TS1-TS7: the TH-01 hourly candle timestamp probe, against a synthetic market. No network."""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from larp.marketdata.history import configuration
from larp.marketdata.port import TOKENS
from larp.marketdata.web3 import Unavailable
from tools import th01_candle_timestamps as th

MIN, HOUR = 60_000, 3_600_000


def ms(value):
    return int(datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp() * 1000)


def iso(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


class Clock:
    def __init__(self, start):
        self.now = ms(start)

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += int(round(seconds * 1000))


class Market:
    """Minute trades aggregated into hourly bars, labelled by their start ('open') or by their end ('end_live'
    includes the bar in progress, 'end_completed' only finished bars). `trading` selects names with trades."""

    def __init__(self, clock, mode='open', trading=tuple(TOKENS)):
        self.clock, self.mode, self.trading, self.calls = clock, mode, set(trading), []

    def minute(self, symbol, m):
        p = Decimal(100 + sorted(TOKENS).index(symbol)) + Decimal(m // MIN % 50) / 100
        return [p, p + Decimal('0.05'), p - Decimal('0.04'), p + Decimal('0.01'), Decimal('1.5'), m, 2]

    def bars(self, symbol, now, size):
        if symbol not in self.trading:
            return []
        done = self.mode == 'end_completed'
        minutes = [m for m in range(now - now % MIN - 5 * HOUR, now + 1, MIN) if not done or m + MIN <= now]
        groups = {}
        for m in minutes:
            groups.setdefault(m - m % size, []).append(self.minute(symbol, m))
        rows = []
        for start, items in sorted(groups.items()):
            if done and start + size > now:
                continue
            label = start if self.mode == 'open' else start + size
            rows.append([str(items[0][0]), str(max(i[1] for i in items)), str(min(i[2] for i in items)),
                         str(items[-1][3]), str(sum(i[4] for i in items)), label, sum(i[6] for i in items)])
        return rows

    def candles(self, symbol, *, bar='1m', limit=100, after=None):
        self.calls.append(('candles', symbol, bar, limit))
        now = self.clock()
        rows = self.bars(symbol, now, MIN if bar == '1m' else HOUR)[-limit:]
        return dict(symbol=symbol, token_id=TOKENS[symbol], bar=bar, rows=rows, available_at=iso(now),
                    content_hash=hashlib.sha256(json.dumps(rows).encode()).hexdigest())

    def metadata(self):
        self.calls.append(('metadata',))
        record = dict(available_at=iso(self.clock()), artifact_sha256='a' * 64)
        return {s: (dict(tokenToShareRatio='1.0', tokenPrice='100', statusInfo=dict(openState=True)), record)
                for s in TOKENS}


def collected(start='2026-10-26T13:40:00Z', **market):
    clock = Clock(start)
    port = Market(clock, **market)
    return th.collect(port, clock=clock, sleep=clock.sleep), port


@pytest.mark.parametrize('start,minutes', [('2026-10-26T13:40:00Z', 35), ('2026-10-26T13:52:00Z', 23),
                                           ('2026-10-26T13:53:00Z', 82), ('2026-10-26T14:00:00Z', 75)])
def test_plan_crosses_the_first_whole_hour_at_least_eight_minutes_away(start, minutes):
    boundary, end = th.plan(ms(start))
    assert boundary % HOUR == 0 and boundary - ms(start) >= 8 * MIN
    assert boundary - HOUR - ms(start) < 8 * MIN
    assert end == boundary + 15 * MIN and (end - ms(start)) // MIN == minutes


def test_ts2_ts3_start_labelled_live_bars_pass():
    record, port = collected()
    result = th.assess(record)
    assert result['verdict'] == 'PASS', result
    assert result['names_ok'] == sorted(TOKENS)
    for item in result['symbols'].values():
        assert item['ts1'] and item['ts2'] and item['ts3'] and not item['contradictions']
        assert item['ts4'] == dict(open_match=True, end_match=False)
    assert {c[0] for c in port.calls} == {'candles', 'metadata'}  # read-only: candles and token metadata only
    assert {(c[2], c[3]) for c in port.calls if c[0] == 'candles'} == {('1h', 3), ('1m', 150)}
    assert len(record['polls']) >= 30 and record['metadata_start'] and record['metadata_end']


def test_ts1_end_labelled_bar_in_progress_fails():
    result = th.assess(collected(mode='end_live')[0])
    assert result['verdict'] == 'FAIL'
    assert all('TS1' in item['contradictions'] for item in result['symbols'].values())


def test_ts4_end_labelled_completed_bars_fail():
    result = th.assess(collected(mode='end_completed')[0])
    assert result['verdict'] == 'FAIL'
    for item in result['symbols'].values():
        assert not item['ts2'] and item['ts4'] == dict(open_match=False, end_match=True)
        assert item['contradictions'] == ['TS4']


def test_no_trades_is_inconclusive():
    result = th.assess(collected(trading=())[0])
    assert result['verdict'] == 'INCONCLUSIVE' and result['names_ok'] == []


def test_fewer_than_three_trading_names_is_inconclusive():
    result = th.assess(collected(trading=('NVDAB', 'TSLAB'))[0])
    assert result['verdict'] == 'INCONCLUSIVE' and result['names_ok'] == ['NVDAB', 'TSLAB']
    assert th.assess(collected(trading=('NVDAB', 'TSLAB', 'MSFTB'))[0])['verdict'] == 'PASS'


def test_ts3_change_after_the_grace_is_a_contradiction():
    record = collected()[0]
    late = [p for p in record['polls'] if p['at_ms'] >= record['boundary_ms'] + th.GRACE_MS][-1]
    row = next(r for r in late['symbols']['GOOGLB']['1h']['rows'] if r[5] == record['boundary_ms'] - HOUR)
    row[3] = str(Decimal(row[3]) + 1)
    result = th.assess(record)
    assert result['verdict'] == 'FAIL' and 'TS3' in result['symbols']['GOOGLB']['contradictions']


def test_transport_errors_are_recorded_and_assessment_continues():
    clock = Clock('2026-10-26T13:40:00Z')
    port = Market(clock)
    original = port.candles

    def flaky(symbol, **kwargs):
        if symbol == 'SKHYB':
            raise Unavailable('rate_limited')
        return original(symbol, **kwargs)
    port.candles = flaky
    record = th.collect(port, clock=clock, sleep=clock.sleep)
    assert record['polls'][0]['symbols']['SKHYB'] == {'1h': {'error': 'rate_limited'}, '1m': {'error': 'rate_limited'}}
    result = th.assess(record)
    assert result['verdict'] == 'PASS' and 'SKHYB' not in result['names_ok'] and len(result['names_ok']) == 4


def run_probe(tmp_path, *args, mode='open', start='2026-10-26T13:40:00Z'):
    clock = Clock(start)
    seen = {}

    def factory(out):
        seen['out'] = out
        return Market(clock, mode=mode)
    code = th.main(['probe', '--out', str(tmp_path / 'probe'), *args], port_factory=factory,
                   clock=clock, sleep=clock.sleep)
    return code, tmp_path / 'probe'


def test_ts5_ts6_probe_writes_hash_bound_evidence_and_a_valid_config(tmp_path, capsys):
    code, out = run_probe(tmp_path, '--adjustment-version', 'synthetic-version')
    summary = json.loads(capsys.readouterr().out)
    raw = (out / 'timestamp-evidence.json').read_bytes()
    assert code == 0 and summary['verdict'] == 'PASS'
    assert summary['timestamp_evidence_sha256'] == hashlib.sha256(raw).hexdigest()
    evidence = json.loads(raw)
    assert evidence['schema'] == 'TokenHistoryTimestampEvidence.v1' and evidence['assessment']['verdict'] == 'PASS'
    config = json.loads((out / 'token-history.json').read_bytes())
    assert configuration(config) == config
    assert config == dict(schema='TokenHistoryConfig.v1', timestamp_kind='OPEN',
                          timestamp_evidence_sha256=hashlib.sha256(raw).hexdigest(),
                          token_adjustment_version='synthetic-version')
    assert summary['config_sha256'] == hashlib.sha256((out / 'token-history.json').read_bytes()).hexdigest()


@pytest.mark.parametrize('mode,code', [('end_live', 4), ('end_completed', 4)])
def test_ts6_failed_evidence_never_writes_a_config(tmp_path, capsys, mode, code):
    assert run_probe(tmp_path, '--adjustment-version', 'v', mode=mode)[0] == code
    assert json.loads(capsys.readouterr().out)['verdict'] == 'FAIL'
    assert (tmp_path / 'probe' / 'timestamp-evidence.json').exists()
    assert not (tmp_path / 'probe' / 'token-history.json').exists()


def test_ts6_config_later_from_pass_evidence_only(tmp_path, capsys):
    assert run_probe(tmp_path)[0] == 0
    out = tmp_path / 'probe'
    assert not (out / 'token-history.json').exists()
    capsys.readouterr()
    evidence = out / 'timestamp-evidence.json'
    target = tmp_path / 'token-history.json'
    assert th.main(['config', '--evidence', str(evidence), '--adjustment-version', 'v1', '--out-file', str(target)]) == 0
    assert configuration(json.loads(target.read_bytes()))['timestamp_evidence_sha256'] == \
        hashlib.sha256(evidence.read_bytes()).hexdigest()
    # Never overwrite; a blank version is refused by the runtime's own validator.
    assert th.main(['config', '--evidence', str(evidence), '--adjustment-version', 'v1', '--out-file', str(target)]) == 4
    assert th.main(['config', '--evidence', str(evidence), '--adjustment-version', ' ',
                    '--out-file', str(tmp_path / 'blank.json')]) == 4
    # The stored verdict is not trusted: edited polls are re-assessed.
    doc = json.loads(evidence.read_bytes())
    for poll in doc['record']['polls']:
        for entry in poll['symbols'].values():
            entry['1h'] = dict(error='rate_limited')
    tampered = tmp_path / 'tampered.json'
    tampered.write_text(json.dumps(doc))
    assert th.main(['config', '--evidence', str(tampered), '--adjustment-version', 'v1',
                    '--out-file', str(tmp_path / 'never.json')]) == 4
    assert not (tmp_path / 'never.json').exists()


def test_ts5_existing_output_directory_is_refused(tmp_path, capsys):
    (tmp_path / 'probe').mkdir()
    assert run_probe(tmp_path)[0] == 4
    assert json.loads(capsys.readouterr().out)['status'] == 'TH01_PROBE_REFUSED'


def test_ts5_production_port_uses_the_history_transport(tmp_path):
    port = th.production_port(dict(BINANCE_API_KEY='k' * 16, BINANCE_SECRET_KEY='s' * 16), tmp_path / 'raw')
    assert port.client.exact_decimals is True and port.client.timeout == 5
    assert port.client.artifacts.root == (tmp_path / 'raw').resolve()


def test_ts1_tolerates_a_slightly_slow_host_clock_but_not_an_hour_ahead_label():
    record = collected()[0]
    for poll in record['polls']:
        for entry in poll['symbols'].values():
            for bar in ('1h', '1m'):
                entry[bar]['available_at'] = iso(ms(entry[bar]['available_at']) - 20_000)
    assert th.assess(record)['verdict'] == 'PASS'
    late = collected(mode='end_live')[0]
    for poll in late['polls']:
        for entry in poll['symbols'].values():
            for bar in ('1h', '1m'):
                entry[bar]['available_at'] = iso(ms(entry[bar]['available_at']) + 20_000)
    assert th.assess(late)['verdict'] == 'FAIL'


def test_ts4_missing_trade_counts_compare_prices_only():
    record = collected()[0]
    for poll in record['polls']:
        for entry in poll['symbols'].values():
            for bar in ('1h', '1m'):
                for row in entry[bar]['rows']:
                    row[6] = None
    result = th.assess(record)
    assert result['verdict'] == 'PASS'
    assert all(v['ts4'] == dict(open_match=True, end_match=False) for v in result['symbols'].values())


def test_ts5_end_to_end_through_the_real_history_transport(tmp_path, capsys, monkeypatch):
    """Web3Client (exact decimals, credential screening, artifacts) and MarketPort parse the provider envelope."""
    from urllib.parse import parse_qs, urlparse
    import larp.marketdata.web3 as web3
    from larp.marketdata.port import MarketPort
    clock = Clock('2026-10-26T13:40:00Z')
    market = Market(clock)
    monkeypatch.setattr(web3.time, 'sleep', lambda seconds: None)
    monkeypatch.setattr(web3, 'utc', lambda: iso(clock()))  # the client stamps available_at with its own clock
    endpoints = []

    class Response:
        def __init__(self, raw):
            self.raw, self.code = raw, 200

        def read(self, n):
            return self.raw

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class Opener:
        def open(self, request, timeout):
            url = urlparse(request.full_url)
            endpoint = url.path.removeprefix('/build/api/v1/dex/')
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            endpoints.append((request.get_method(), endpoint))
            if endpoint == 'market/candles':
                symbol = next(s for s, t in TOKENS.items() if t == query['tokenContractAddress'])
                rows = market.bars(symbol, clock(), MIN if query['bar'] == '1m' else HOUR)[-int(query['limit']):]
                # Numbers as the provider sends them: JSON numbers, which exact_decimals keeps as decimal strings.
                body = '{"code":0,"msg":"success","data":[%s]}' % ','.join(
                    '[%s,%s,%s,%s,%s,"%d",%d]' % (*r[:5], r[5], r[6]) for r in rows)
            else:
                body = json.dumps(dict(code=0, msg='success', data=[dict(
                    tokenContractAddress=t, tokenSymbol=s, binanceChainId='56', decimals=18,
                    tokenToShareRatio='1.0', tokenPrice='100', statusInfo=dict(openState=True)) for s, t in TOKENS.items()]))
            return Response(body.encode())

    def factory(out):
        client = web3.Web3Client('k' * 16, 's' * 16, artifacts=web3.Artifacts(out / 'raw'), opener=Opener(),
                                 timeout=5, exact_decimals=True)
        return MarketPort(client, th.UNUSED_WALLET)
    code = th.main(['probe', '--out', str(tmp_path / 'probe'), '--adjustment-version', 'v'], port_factory=factory,
                   clock=clock, sleep=clock.sleep)
    assert code == 0, capsys.readouterr().out
    assert set(endpoints) == {('GET', 'market/candles'), ('GET', 'market/rwa/tokens')}
    evidence = json.loads((tmp_path / 'probe' / 'timestamp-evidence.json').read_bytes())
    row = evidence['record']['polls'][0]['symbols']['NVDAB']['1h']['rows'][-1]
    assert all(type(v) is str for v in row[:5])  # exact decimal lexemes, never floats
    hashes = {p['symbols']['NVDAB']['1h']['content_hash'] for p in evidence['record']['polls']}
    assert all((tmp_path / 'probe' / 'raw' / (h + '.json')).is_file() for h in hashes)
    assert evidence['record']['metadata_start']['NVDAB']['tokenToShareRatio'] == '1.0'
