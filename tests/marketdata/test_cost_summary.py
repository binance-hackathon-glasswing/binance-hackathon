"""IDEA-057 Q1-Q6: the QuoteCostSummary.v1 producer. Synthetic Web3 responses only; no credentials or network."""

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from larp.contracts import ContractError, Document
from larp.execution import USDT
from larp.marketdata.port import NATIVE, TOKENS, MarketPort
from larp.marketdata.web3 import READS, Unavailable

WALLET = '0x' + '4' * 40
CASH = 40_000_000  # 40 USDT in money units
PAY_RAW = CASH * 10**12
GAS_PRICE = 50_000_000  # 0.05 gwei
PRICES = dict(NVDAB=180, GOOGLB=250, SKHYB=120, TSLAB=430, MSFTB=510)  # USDT per token


class FakeClient:
    """Answers the read endpoints like the Web3 Open API, records every call, and stores no credential."""

    def __init__(self, *, cost=Decimal('0.0008'), impact='0.05', drift=Decimal('0.0004'), fail=(), estimate=True,
                 at='2026-10-17T14:00:00.000Z'):
        self.calls, self.cost, self.impact, self.drift = [], cost, impact, drift
        self.fail, self.estimate, self.at, self.n = set(fail), estimate, at, 0
        self.quotes = {}

    def record(self, data):
        self.n += 1
        return dict(response=dict(code=0, data=data), available_at=self.at, artifact_sha256=format(self.n, '064x'))

    def request(self, method, endpoint, params):
        assert (method, endpoint) in READS, (method, endpoint)
        self.calls.append((method, endpoint, deepcopy(params)))
        if endpoint == 'aggregator/quote-and-swap':
            src, dst, amount = params['fromTokenAddress'].lower(), params['toTokenAddress'].lower(), int(params['amount'])
            if dst == NATIVE:
                received = amount * 10**18 // (600 * 10**18)  # 600 USDT per BNB
                return self.record([dict(routerResult=dict(fromToken=dict(tokenContractAddress=USDT, decimal='18'),
                    toToken=dict(tokenContractAddress=NATIVE, decimal='18'), fromTokenAmount=str(amount),
                    toTokenAmount=str(received), priceImpactPercent='0.01', vendorName='LiquidMesh'),
                    tx=dict(to='0x' + '7' * 40, data='0x', value='0', gas='450000', gasPrice=str(GAS_PRICE)))])
            symbol = next(s for s, t in TOKENS.items() if t in (src, dst))
            if symbol in self.fail:
                raise Unavailable('api_or_http_error')
            price = Decimal(PRICES[symbol])
            if src == USDT.lower():
                key = (symbol, 'BUY')
                factor = 1 - self.cost / 2 - (self.drift if key in self.quotes else 0)
                received = int(Decimal(amount) / price * factor)
                self.quotes[key] = received
                pair = (USDT, TOKENS[symbol])
            else:
                received = int(Decimal(amount) * price * (1 - self.cost / 2))
                pair = (TOKENS[symbol], USDT)
            return self.record([dict(routerResult=dict(
                fromToken=dict(tokenContractAddress=pair[0], decimal='18'),
                toToken=dict(tokenContractAddress=pair[1], decimal='18'), fromTokenAmount=str(amount),
                toTokenAmount=str(received), priceImpactPercent=self.impact, vendorName='LiquidMesh', tradeFee='0'),
                tx=dict(to='0x' + '7' * 40, data='0xabcdef', value='0', gas='450000', gasPrice=str(GAS_PRICE)))])
        if endpoint == 'aggregator/approve-transaction':
            return self.record([dict(gasLimit='60000', gasPrice=str(GAS_PRICE), dexContractAddress='0x' + '7' * 40)])
        if endpoint == 'pre-transaction/gas-limit':
            if not self.estimate:
                raise Unavailable('api_or_http_error')
            return self.record([dict(gasLimit='700000')])
        raise AssertionError(endpoint)


def capture(client=None, **options):
    from larp.marketdata.cost_summary import capture_round
    client = client or FakeClient()
    return client, capture_round(MarketPort(client, WALLET), cash_units=CASH, sleep=lambda s: None, **options)


# ------------------------------------------------------------------------------------------------ Q1, Q2 capture
class Capture(unittest.TestCase):
    def test_q1_one_round_reads_quotes_approvals_and_estimates_per_token(self):
        client, records = capture()
        samples = [r for r in records if r['kind'] == 'SAMPLE']
        self.assertEqual(sorted(r['symbol'] for r in samples), sorted(TOKENS))
        [bnb] = [r for r in records if r['kind'] == 'BNB_PRICE']
        self.assertEqual(bnb['received_wei'], PAY_RAW * 10**18 // (600 * 10**18))
        quotes = [c for c in client.calls if c[1] == 'aggregator/quote-and-swap']
        self.assertEqual(len(quotes), 3 * len(TOKENS) + 1)  # buy, sell, re-quote per token; one BNB quote
        nvdab = next(r for r in samples if r['symbol'] == 'NVDAB')
        sells = [c[2] for c in quotes if c[2]['fromTokenAddress'].lower() == TOKENS['NVDAB']]
        self.assertEqual([int(p['amount']) for p in sells], [nvdab['buy_received']])  # exactly the bought units
        self.assertEqual(nvdab['pay_raw'], PAY_RAW)
        self.assertEqual(nvdab['approve_gas_wei'], 60_000 * GAS_PRICE)
        self.assertEqual(nvdab['swap_gas_wei'], [840_000 * GAS_PRICE] * 2)  # max(450k, ceil(1.2 x 700k))
        self.assertEqual(nvdab['gas_methods'], ['ESTIMATED', 'ESTIMATED'])
        self.assertEqual(len(nvdab['artifacts']), 7)  # buy, sell, re-quote, two approves, two estimates
        approvals = [c[2] for c in client.calls if c[1] == 'aggregator/approve-transaction']
        self.assertEqual({a['tokenContractAddress'].lower() for a in approvals}, {USDT.lower(), *TOKENS.values()})
        self.assertNotIn('secret', json.dumps(records).lower())

    def test_q2_failures_are_recorded_and_estimates_fall_back(self):
        client, records = capture(FakeClient(fail={'TSLAB'}, estimate=False))
        [failure] = [r for r in records if r['kind'] == 'FAILURE']
        self.assertEqual((failure['symbol'], failure['stage']), ('TSLAB', 'BUY_QUOTE'))
        self.assertNotIn('TSLAB', [r['symbol'] for r in records if r['kind'] == 'SAMPLE'])
        nvdab = next(r for r in records if r.get('symbol') == 'NVDAB')
        self.assertEqual(nvdab['gas_methods'], ['FALLBACK', 'FALLBACK'])
        self.assertEqual(nvdab['swap_gas_wei'], [1_116_000 * GAS_PRICE] * 2)

    def test_q1_the_real_client_still_refuses_to_broadcast(self):
        from larp.marketdata.web3 import Artifacts, Web3Client
        with tempfile.TemporaryDirectory() as tmp:
            client = Web3Client('key', 'secret', artifacts=Artifacts(tmp))
            with self.assertRaises(Unavailable):
                client.request('POST', 'pre-transaction/broadcast-transaction', {})


# ------------------------------------------------------------------------------------------------ Q3, Q4 summary
def sample(symbol, day, *, roundtrip_bps=20, buy_impact='3', sell_impact='4', drift_bps=2, approve=3_000_000_000_000,
           swap=(35_000_000_000_000, 40_000_000_000_000), methods=('ESTIMATED', 'ESTIMATED'), n=0):
    buy = 10**18
    requote = buy - buy * drift_bps // 10000
    proceeds = PAY_RAW - PAY_RAW * roundtrip_bps // 10000
    return dict(kind='SAMPLE', symbol=symbol, at=f'{day}T14:{n:02d}:00.000Z', pay_raw=PAY_RAW, token_decimals=18,
                buy_received=buy, sell_proceeds=proceeds, requote_received=requote, buy_impact_bps=buy_impact,
                sell_impact_bps=sell_impact, approve_gas_wei=approve, swap_gas_wei=list(swap),
                gas_methods=list(methods), trade_fee='0', artifacts=[format(n + 1, '064x')])


def bnb(day, price=600, n=0):
    return dict(kind='BNB_PRICE', at=f'{day}T14:{n:02d}:00.000Z', pay_cash_units=CASH,
                received_wei=CASH * 10**18 // (price * 10**6), artifact=format(900 + n, '064x'))


DAYS = ('2026-10-16', '2026-10-17', '2026-10-18')  # Friday, Saturday, Sunday (UTC)


def complete(per_day=4, **changes):
    records = []
    for d, day in enumerate(DAYS):
        for n in range(per_day):
            records += [sample(s, day, n=n, **changes) for s in TOKENS]
            records.append(bnb(day, n=n))
    return records


class Summary(unittest.TestCase):
    def summarize(self, records, **options):
        from larp.marketdata.cost_summary import summarize
        return summarize(records, **options)

    def test_q3_each_field_follows_its_rule(self):
        records = complete()
        # NVDAB: impacts 3..6 bp, round trips with a known residual, drifts and gas spread out for the p90.
        records = [r for r in records if r.get('symbol') != 'NVDAB']
        for i in range(10):
            day = DAYS[i % 3]
            records.append(sample('NVDAB', day, n=20 + i, roundtrip_bps=20 + i, buy_impact=str(3 + i % 2),
                                  sell_impact='4.2', drift_bps=i + 1, approve=(i + 1) * 10**12,
                                  swap=((i + 1) * 10**13, (i + 2) * 10**13)))
        summary, report = self.summarize(records)
        self.assertEqual((summary['schema'], summary['origin'], summary['bnb_decimals']),
                         ('QuoteCostSummary.v1', 'RECORDED_WEB3', 18))
        self.assertEqual(summary['bnb_price_units'], 600 * 10**6)
        n = summary['symbols']['NVDAB']
        self.assertEqual(n['samples'], 10)
        self.assertEqual(n['median_impact_bps'], 5)  # median of {3,4}x5 and 4.2x10 = 4.2 -> ceil 5
        self.assertEqual(n['spread_bps'], 17)  # median(20..29 - impact) = 24.5 - 7.7 = 16.8 -> 17
        self.assertEqual(n['fee_bps'], 0)
        self.assertEqual(n['approve_gas_bnb_units'], 9 * 10**12)  # p90 nearest rank of 1..10
        self.assertEqual(n['swap_gas_bnb_units'], 10 * 10**13)  # p90 of the 20 buy/sell values 1..11
        self.assertEqual(n['slippage_bps'], 9)  # p90 of drifts 1..10
        self.assertEqual(n['quote_ttl_seconds'], 30)
        self.assertEqual(summary['observed_at'], max(r['at'] for r in records))
        self.assertEqual(report['coverage']['utc_days'], list(DAYS))
        self.assertEqual(report['coverage']['weekend_days'], ['2026-10-17', '2026-10-18'])

    def test_q3_clamps(self):
        records = complete(roundtrip_bps=1, buy_impact='0', sell_impact='0', drift_bps=0)
        s = self.summarize(records)[0]['symbols']['MSFTB']
        self.assertEqual((s['median_impact_bps'], s['spread_bps'], s['slippage_bps']), (1, 1, 1))
        negative = complete(roundtrip_bps=0, buy_impact='3', sell_impact='4', drift_bps=80)
        s = self.summarize(negative)[0]['symbols']['MSFTB']
        self.assertEqual((s['spread_bps'], s['slippage_bps']), (0, 50))

    def test_q4_refusals(self):
        cases = {
            'too few samples': (complete(per_day=3), {}),
            'too few days': ([r for r in complete(per_day=6) if not r['at'].startswith(DAYS[0])], {}),
            'no weekend': ([dict(r, at=r['at'].replace('2026-10-17', '2026-10-14').replace('2026-10-18', '2026-10-15'))
                            for r in complete()], {}),
            'costs fail the consumer': (complete(roundtrip_bps=60), {}),
            'malformed record': (complete() + [dict(kind='SAMPLE', symbol='NVDAB')], {}),
            'no BNB price': ([r for r in complete() if r['kind'] != 'BNB_PRICE'], {}),
        }
        for name, (records, options) in cases.items():
            with self.subTest(name), self.assertRaises(ContractError):
                self.summarize(records, **options)
        relaxed = [r for r in complete(per_day=6) if not r['at'].startswith(DAYS[0])]
        self.summarize(relaxed, min_days=2)  # the coverage bounds are parameters, recorded in the report

    def test_q4_fallback_gas_is_reported(self):
        records = complete(methods=('ESTIMATED', 'FALLBACK'))
        report = self.summarize(records)[1]
        self.assertEqual(report['symbols']['NVDAB']['fallback_gas_estimates'], 12)
        self.assertEqual(report['parameters']['quote_ttl_seconds_source'], 'KIT_STATED')


# ------------------------------------------------------------------------------------------------ Q5 end to end
class EndToEnd(unittest.TestCase):
    def test_q5_captures_become_a_summary_the_profile_builder_accepts(self):
        from larp.marketdata.cost_summary import summarize
        from larp.strategy.profiles import build_live_profiles, quote_summary
        from larp.intelligence.redflags import CONFIG
        records = []
        for d, day in enumerate(DAYS):
            for n in range(4):
                records += capture(FakeClient(at=f'{day}T1{n}:00:00.000Z'))[1]
        summary, report = summarize(records)
        quote_summary(summary)
        profiles = build_live_profiles(Document.from_dict(summary),
                                       Document.from_dict(json.loads(Path(CONFIG).read_text())))
        self.assertEqual(set(profiles), {'REHEARSAL', 'FINAL'})
        self.assertEqual(report['capture_hash'], summary['capture_hash'])
        changed = deepcopy(records)
        next(r for r in changed if r['kind'] == 'SAMPLE')['sell_proceeds'] -= 1
        self.assertNotEqual(summarize(changed)[0]['capture_hash'], summary['capture_hash'])


# ------------------------------------------------------------------------------------------------ Q6 CLI
class Cli(unittest.TestCase):
    def test_q6_capture_needs_the_key_pair_and_summarize_never_overwrites(self):
        from unittest.mock import patch
        from larp.marketdata import cost_summary
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {}, clear=True), \
                patch.object(cost_summary, 'capture_round', side_effect=AssertionError('called')):
            self.assertEqual(cost_summary.main(['capture', '--address', WALLET, '--out-dir', tmp]), 2)
        with tempfile.TemporaryDirectory() as tmp:
            captures = Path(tmp) / 'captures'
            captures.mkdir()
            (captures / 'capture-1.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in complete()))
            out = Path(tmp) / 'summary.json'
            args = ['summarize', '--captures', str(captures), '--output', str(out)]
            self.assertEqual(cost_summary.main(args), 0)
            summary = json.loads(out.read_text())
            self.assertEqual(summary['schema'], 'QuoteCostSummary.v1')
            self.assertTrue((Path(tmp) / 'summary.report.json').exists())
            self.assertEqual(cost_summary.main(args), 2)  # an existing summary is never replaced
            self.assertEqual(json.loads(out.read_text()), summary)


# ------------------------------------------------------------------------------------------------ Q8-Q10 runner
class Clock:
    def __init__(self, start):
        self.t = start

    def now(self):
        from datetime import datetime, timezone
        return datetime.fromtimestamp(self.t, timezone.utc)

    def sleep(self, seconds):
        self.t += seconds


def epoch(text):
    from datetime import datetime
    return datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()


class Runner(unittest.TestCase):
    def run_capture(self, tmp, round_fn, **options):
        from larp.marketdata.cost_summary import run_capture
        clock = Clock(epoch('2026-10-17T23:40:00Z'))
        done = run_capture(object(), Path(tmp), round_fn=round_fn, now=clock.now, sleep=clock.sleep, **options)
        return done, clock

    def test_q8_until_loops_and_writes_one_file_per_utc_day(self):
        calls = []

        def round_fn(market, **kw):
            calls.append(kw)
            return [dict(kind='SAMPLE', symbol='NVDAB', n=len(calls))]
        with tempfile.TemporaryDirectory() as tmp:
            done, clock = self.run_capture(tmp, round_fn, until='2026-10-18T00:15:00Z', interval_seconds=600)
            self.assertEqual(done, 4)  # 23:40, 23:50, 00:00, 00:10
            files = sorted(p.name for p in Path(tmp).glob('capture-*.jsonl'))
            self.assertEqual(files, ['capture-2026-10-17.jsonl', 'capture-2026-10-18.jsonl'])
            lines = [json.loads(l) for f in files for l in (Path(tmp) / f).read_text().splitlines()]
            self.assertEqual([r['n'] for r in lines], [1, 2, 3, 4])

    def test_q9_a_failed_round_is_recorded_and_the_loop_continues(self):
        calls = []

        def round_fn(market, **kw):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError('network went away')
            return [dict(kind='SAMPLE', symbol='NVDAB')]
        with tempfile.TemporaryDirectory() as tmp:
            done, _ = self.run_capture(tmp, round_fn, until='2026-10-17T23:59:00Z', interval_seconds=300)
            records = [json.loads(l) for p in Path(tmp).glob('capture-*.jsonl') for l in p.read_text().splitlines()]
            self.assertEqual(len(calls), 4)
            failures = [r for r in records if r['kind'] == 'FAILURE']
            self.assertEqual([(f['stage'], f['reason']) for f in failures], [('ROUND', 'RuntimeError')])
            past, _ = self.run_capture(tmp, round_fn, until='2026-10-17T00:00:00Z', interval_seconds=300)
            self.assertEqual(past, 0)
            three, _ = self.run_capture(tmp, round_fn, rounds=3, interval_seconds=300)
            self.assertEqual(three, 3)
            with self.assertRaises(ContractError):
                self.run_capture(tmp, round_fn, rounds=3, until='2026-10-18T00:00:00Z', interval_seconds=300)

    def test_q10_the_wrapper_needs_the_key_pair_and_never_prints_it(self):
        import os
        import subprocess
        script = Path(__file__).resolve().parents[2] / 'tools' / 'run_quote_capture.sh'
        self.assertTrue(script.is_file())
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in os.environ.items() if not k.startswith('BINANCE_')}
            result = subprocess.run(['bash', str(script), WALLET, '2026-10-19T00:00:00Z', tmp], cwd=tmp, env=env,
                                    capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('BINANCE_API_KEY', result.stderr)
            (Path(tmp) / '.env').write_text('BINANCE_API_KEY=k-synthetic-123\nBINANCE_SECRET_KEY=s-synthetic-456\n')
            result = subprocess.run(['bash', str(script), '--dry-run', WALLET, '2026-10-19T00:00:00Z', tmp], cwd=tmp,
                                    env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('synthetic-123', result.stdout + result.stderr)
            self.assertNotIn('synthetic-456', result.stdout + result.stderr)
            self.assertIn('--until 2026-10-19T00:00:00Z', result.stdout)
        usage = subprocess.run(['bash', str(script)], capture_output=True, text=True, timeout=30)
        self.assertIn('weekend', usage.stderr.lower())


# ------------------------------------------------------------------------------------------------ PR 88 review fixes
class ReviewFixes(unittest.TestCase):
    def test_r1_rejected_credentials_stop_the_capture_instead_of_looping(self):
        from larp.marketdata.cost_summary import capture_round, run_capture

        class Rejected(FakeClient):
            def request(self, method, endpoint, params):
                raise Unavailable('authentication_error')
        with self.assertRaises(Unavailable):
            capture(Rejected())
        with tempfile.TemporaryDirectory() as tmp:
            clock = Clock(epoch('2026-10-17T00:00:00Z'))
            with self.assertRaises(Unavailable):
                run_capture(MarketPort(Rejected(), WALLET), Path(tmp), until='2026-10-19T00:00:00Z',
                            now=clock.now, sleep=clock.sleep, cash_units=CASH)
            [record] = [json.loads(l) for p in Path(tmp).glob('capture-*.jsonl') for l in p.read_text().splitlines()]
            self.assertEqual((record['stage'], record['reason']), ('ROUND', 'authentication_error'))
            with self.assertRaises(ContractError):  # invalid parameters fail every round: stop at the first
                run_capture(MarketPort(FakeClient(), WALLET), Path(tmp), until='2026-10-19T00:00:00Z',
                            now=clock.now, sleep=clock.sleep, round_fn=capture_round, cash_units=0)

    def test_r1_transient_errors_still_become_failures(self):
        class Limited(FakeClient):
            def request(self, method, endpoint, params):
                raise Unavailable('rate_limited')
        _, records = capture(Limited())
        self.assertEqual({r['kind'] for r in records}, {'FAILURE'})
        self.assertEqual(len(records), len(TOKENS) + 1)

    def test_r2_each_token_needs_its_own_days_and_weekend(self):
        from larp.marketdata.cost_summary import summarize
        weekday_only = [dict(r, at=r['at'].replace('2026-10-17', '2026-10-14').replace('2026-10-18', '2026-10-15'))
                        if r.get('symbol') == 'TSLAB' else r for r in complete()]
        with self.assertRaisesRegex(ContractError, 'TSLAB: no weekend sample'):
            summarize(weekday_only)
        one_day = [dict(r, at=r['at'][:8] + '17' + r['at'][10:]) if r.get('symbol') == 'SKHYB' else r
                   for r in complete()]
        with self.assertRaisesRegex(ContractError, 'SKHYB: 1 UTC days < 3'):
            summarize(one_day)
        report = summarize(complete())[1]
        self.assertEqual(report['symbols']['NVDAB']['utc_days'], list(DAYS))

    def test_r3_until_must_name_its_offset(self):
        from larp.marketdata.cost_summary import run_capture
        with tempfile.TemporaryDirectory() as tmp:
            for until in ('2026-10-19T00:00:00', 'next sunday'):
                with self.subTest(until), self.assertRaises(ContractError):
                    run_capture(object(), Path(tmp), round_fn=lambda m: [], until=until,
                                now=Clock(epoch('2026-10-20T00:00:00Z')).now)  # past: never loops on real time

    def test_r4_a_record_error_names_its_own_stage(self):
        class NoImpact(FakeClient):
            def record(self, data):
                for row in data:
                    row.get('routerResult', {}).pop('priceImpactPercent', None)
                return super().record(data)
        _, records = capture(NoImpact())
        self.assertEqual({r['stage'] for r in records if r.get('symbol') in TOKENS}, {'RECORD'})

    def test_r5_the_wrapper_reports_a_capture_that_dies_at_startup(self):
        import os
        import subprocess
        script = Path(__file__).resolve().parents[2] / 'tools' / 'run_quote_capture.sh'
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / 'python'
            fake.write_text('#!/bin/sh\necho "refused: authentication_error" >&2\nexit 2\n')
            fake.chmod(0o755)
            env = {k: v for k, v in os.environ.items() if not k.startswith('BINANCE_')}
            env.update(BINANCE_API_KEY='k-synthetic-123', BINANCE_SECRET_KEY='s-synthetic-456', PYTHON=str(fake),
                       STARTUP_CHECK_SECONDS='1')
            result = subprocess.run(['bash', str(script), WALLET, '2026-10-19T00:00:00Z', str(Path(tmp) / 'out')],
                                    cwd=tmp, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn('authentication_error', result.stderr)
            self.assertNotIn('synthetic', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
