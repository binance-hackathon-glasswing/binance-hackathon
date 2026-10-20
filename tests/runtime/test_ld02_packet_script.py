"""Offline checks for the LD02 operator packet script (IDEA-070 LD02 P1, P5, P6, P11); no host or network calls."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'docs/build/ops/ld02-20261020/execution-packet.sh'
MODULE = ROOT / 'larp/execution_live/untrusted_router.py'
USDT = '0x55d398326f99059ff775485246999027b3197955'
TOKENS = dict(NVDAB='0x' + '1' * 40)
WALLET = '0x' + 'ab' * 20


class Ld02PacketScriptTests(unittest.TestCase):
    def setUp(self):
        source = SCRIPT.read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        self.ns = {'__name__': 'offline_ld02_packet'}
        exec(compile(source, str(SCRIPT), 'exec'), self.ns)
        self.m = self.ns['load_router_module']()

    def calldata(self, deadline=1_800_000_500, amount=10**18, minimum=99):
        m = self.m
        w = lambda v: format(v, '064x')
        head = [0] * m.HEAD_WORDS
        head[m.PAY], head[m.AMOUNT], head[m.MINIMUM], head[m.QUOTED] = int(USDT, 16), amount, minimum, 100
        head[m.RECEIVE] = int(TOKENS['NVDAB'], 16)
        head[m.BLOB_OFFSET] = 32 * (m.BLOB_OFFSET + 1)
        length = 4 + 32 * m.INNER_WORDS
        head[m.BLOB_LENGTH] = length
        inner = [0] * m.INNER_WORDS
        inner[m.INNER_DEADLINE] = deadline
        blob = m.INNER_SELECTOR[2:] + ''.join(w(v) for v in inner)
        blob += '0' * (-len(blob) % 64)
        return m.SWAP_SELECTOR + ''.join(w(v) for v in head) + blob

    def record(self, data=None, amount=10**18, requested_at='2027-01-15T08:00:00.000Z'):
        tx = dict(to=self.m.ROUTER, value='0', data=data or self.calldata(), gas='250000', minReceiveAmount='99')
        rr = dict(fromToken=dict(tokenContractAddress=USDT, decimal='18'),
                  toToken=dict(tokenContractAddress=TOKENS['NVDAB'], decimal='18'),
                  fromTokenAmount=str(amount), toTokenAmount='100', vendorName='LiquidMesh', priceImpactPercent='0.01')
        return dict(endpoint='aggregator/quote-and-swap', outcome='ok', params=dict(amount=str(amount)),
                    response=dict(data=dict(routerResult=rr, tx=tx)), requested_at=requested_at,
                    elapsed_ms=420, artifact_sha256='c' * 64)

    def row(self, record, amount=10**18):
        return self.ns['quote_row']('NVDAB', 'BUY', amount // 10**12, amount, 18, record, self.m, TOKENS, USDT)

    def test_embedded_module_is_the_canonical_file(self):
        self.assertEqual(self.ns['ROUTER_MODULE_SHA256'], hashlib.sha256(MODULE.read_bytes()).hexdigest())
        self.assertEqual(self.m.SCHEMA, 'UntrustedRouterPolicy.v1')

    def test_tampered_embedded_module_is_refused(self):
        self.ns['ROUTER_MODULE_SHA256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'ROUTER_MODULE_HASH'):
            self.ns['load_router_module']()

    def test_inner_deadline_and_layout_refusals(self):
        self.assertEqual(self.ns['inner_deadline'](self.calldata(deadline=123456), self.m), 123456)
        for bad in ('0xdeadbeef' + self.calldata()[10:], self.calldata()[:200]):
            with self.subTest(bad=bad[:12]), self.assertRaises(ValueError):
                self.ns['inner_deadline'](bad, self.m)

    def test_quote_row_binds_request_and_reports_deadline(self):
        row = self.row(self.record(self.calldata(deadline=1_800_000_500), requested_at='2027-01-15T08:00:00.000Z'))
        start = self.ns['epoch_s']('2027-01-15T08:00:00.000Z')
        self.assertTrue(row['request_bound'] and row['router_pinned'] and row['selector_pinned'] and row['native_value_zero'])
        self.assertEqual(row['deadline_after_request_s'], round(1_800_000_500 - start, 1))
        self.assertEqual(row['minimum_below_quote_bps'], 100)
        self.assertNotIn('data', json.dumps(row).replace('calldata', ''))  # calldata only as a fingerprint
        self.assertFalse(self.row(self.record(amount=10**18), amount=2 * 10**18)['request_bound'])

    def test_undecodable_route_keeps_a_coded_gap(self):
        row = self.row(self.record(data='0xdeadbeef'))
        self.assertIsNone(row['deadline_after_request_s'])
        self.assertEqual(row['deadline_error'], 'ValueError:CALLDATA_SELECTOR')
        self.assertFalse(row['selector_pinned'])

    def test_observe_uses_this_runs_quotes_and_stays_unreviewed(self):
        records = [self.record(), dict(self.record(), outcome='rate_limited'), dict(endpoint='market/rwa/price')]
        self.assertEqual(len(list(self.ns['memory_quotes'](records))), 1)
        self.m._quotes = lambda _directory: self.ns['memory_quotes'](records)
        replies = {'eth_getBlockByNumber': dict(number='0x10'), 'eth_getStorageAt': '0x' + '0' * 24 + '2' * 40,
                   'eth_getCode': '0x6001'}
        with patch.object(self.m, '_json_rpc', lambda url, method, params: replies[method]):
            draft, block, count = self.m.observe('https://example.invalid', None)
        self.assertEqual((block, count), ('0x10', 1))
        self.assertEqual(draft['review'], dict(reviewed_by='REVIEW_REQUIRED', review_ref='REVIEW_REQUIRED'))
        with self.assertRaises(Exception):
            self.m.validate_policy(draft)

    def test_sanitizer_refuses_urls_wallet_secrets_and_hosts(self):
        forbidden = self.ns['forbidden_values'](
            dict(wallet_address=WALLET, database_host='larp-dev.abc.rds.amazonaws.com'),
            {'BINANCE_SECRET_KEY': 's3cr3t-value'}, [dict(url='https://rpc.example.org/key123', source_id='P')])
        clean = json.dumps(dict(source_id='P', fingerprint='0123456789abcdef'))
        self.assertEqual(self.ns['sanitize'](clean, forbidden), clean)
        for leak in ('https://x.y', WALLET.upper(), WALLET[2:], 's3cr3t-value', 'rpc.example.org',
                     'larp-dev.abc.rds.amazonaws.com'):
            with self.subTest(leak=leak), self.assertRaises(ValueError):
                self.ns['sanitize'](json.dumps(dict(value=leak)), forbidden)

    def test_rpc_helper_refuses_writes_and_other_calls_offline(self):
        rpc = self.ns['rpc']
        for url, method, params in [('https://a.b', 'eth_sendRawTransaction', ['0x00']),
                                    ('http://a.b', 'eth_gasPrice', []),
                                    ('https://a.b', 'eth_call', [dict(to=USDT, data='0xa9059cbb' + '0' * 128), 'latest'])]:
            with self.subTest(method=method), self.assertRaises(ValueError):
                rpc(url, 'P', method, params, [])

    def test_error_codes_never_carry_urls_or_values(self):
        code = self.ns['code']
        self.assertEqual(code(ValueError('RPC_REFUSED')), 'ValueError:RPC_REFUSED')
        self.assertEqual(code(RuntimeError('rate_limited')), 'RuntimeError:rate_limited')
        self.assertEqual(code(OSError('fail https://host/key')), 'OSError')
        self.assertEqual(code(KeyError('/etc/larp/runtime.json')), 'KeyError')

    def test_timed_opener_logs_method_and_duration(self):
        log = []

        class Inner:
            def open(self, request, timeout=None):
                return 'response'

        request = type('R', (), {'data': json.dumps(dict(method='eth_chainId')).encode()})()
        self.assertEqual(self.ns['TimedOpener'](Inner(), log, 'P').open(request, timeout=5), 'response')
        self.assertEqual(log[0][:2], ('P', 'eth_chainId'))
        summary = self.ns['timing_summary']([('P', 'm', 5), ('P', 'm', 9), ('Q', 'm', 1)])
        self.assertEqual(summary['P:m'], dict(n=2, min=5, median=7.0, max=9))

    def test_collect_end_to_end_with_fake_ports_is_sanitized(self):
        from larp.contracts import Document
        from larp.marketdata.port import TOKENS as REAL_TOKENS
        ns = self.ns
        wallet = WALLET
        config = dict(run_id='run', build_id='b', mode='dev', region='ap-southeast-2', wallet_address=wallet,
                      database_name='db', database_host='db.host.example', runtime_secret_id='x',
                      driver=dict(execution='shadow', balance_rpc_providers=[
                          dict(source_id='PRIMARY', url='https://primary.example/k'),
                          dict(source_id='BACKUP', url='https://backup.example/k')]))
        profile = dict(minimum_trade_units=5_000_000, per_trade_cap_units=20_000_000, slippage_bps=100,
                       exit_gas_reserve_units=50_000)
        raw = {'runtime': json.dumps(config).encode(), 'release_manifest': b'{}', 'strategy_profile': json.dumps(profile).encode()}
        portfolio = dict(wallet_id=wallet, cash_units=1, bnb_units=0, bnb_decimals=18, bnb_price_units=700_000_000, positions={})
        projection = dict(portfolio=portfolio, registered_version=dict(build_id='b', manifest_sha256=hashlib.sha256(b'{}').hexdigest()))
        run = (wallet, 5, 2, False, Document.from_dict(projection).payload)
        tokens = {'USDT': dict(contract=USDT, decimals=18, units=10**12)}
        tokens.update({s: dict(contract=a, decimals=18, units=0) for s, a in REAL_TOKENS.items()})
        observation = dict(schema='ChainBalances.v1', chain_id=56, wallet=wallet, block_number=7, block_hash='0x' + '1' * 64,
                           native_wei=3 * 10**15, tokens=tokens, latest_nonce=4, pending_nonce=4,
                           observed_at='2027-01-15T08:00:00+00:00', source_id='PRIMARY')
        compared = dict(status='MATCH', assets={'USDT': dict(**{'class': 'MATCH'}, ledger_units=1, chain_units=1)})

        class Providers:
            def __init__(self, *a, **k): pass
            def __call__(self, now_ms): return observation

        test = self

        def quote(port, symbol, side, amount, decimals, slippage=None):
            r = test.record(amount=amount)
            r['response']['data']['routerResult']['fromToken']['tokenContractAddress'] = USDT if side == 'BUY' else REAL_TOKENS[symbol]
            r['response']['data']['routerResult']['toToken']['tokenContractAddress'] = REAL_TOKENS[symbol] if side == 'BUY' else USDT
            port.client.artifacts.put(r)  # as Web3Client.request stores every response
            return r

        def rpc(url, source, method, params, log):
            log.append((source, method, 3))
            return {'eth_gasPrice': hex(10**8), 'eth_call': '0x0'}[method]

        module = ns['load_router_module']()
        with patch.dict(ns, read_configs=lambda: dict(raw), database=lambda c: (run, [], [('DONE', 2)], [('CLOSED', 3)]),
                        rpc=rpc, finality=lambda providers, log: [dict(source_id='PRIMARY', lag_blocks=2)],
                        load_router_module=lambda: module), \
                patch('larp.runtime.credentials.runtime_secrets', lambda c: {'BINANCE_API_KEY': 'key-value-1',
                                                                             'BINANCE_SECRET_KEY': 'secret-value-2'}), \
                patch('larp.execution_live.balances.BalanceProviders', Providers), \
                patch('larp.risk.reconcile.compare_balances', lambda *a, **k: compared), \
                patch('larp.marketdata.port.MarketPort.quote', quote), \
                patch.object(module, 'observe', lambda url, d: (dict(review=dict(reviewed_by='REVIEW_REQUIRED')), '0x10',
                                                                len(list(module._quotes(d))))):
            packet, forbidden = ns['collect']()
        text = ns['sanitize'](json.dumps(packet, sort_keys=True), forbidden)
        self.assertIn('AWAITING_KEEGAN_CONFIRMATION', text)
        self.assertEqual(packet['router']['status'], 'DRAFT_REVIEW_REQUIRED')
        self.assertEqual(packet['router']['quotes_used'], 15)
        self.assertEqual(packet['signer_timings']['status'], 'UNMEASURED')
        self.assertTrue(packet['identity']['wallet_consistent'] and packet['identity']['registered_manifest_matches'])
        self.assertTrue(packet['configs_unchanged'])
        self.assertEqual(len(packet['quotes']['rows']), 15)
        self.assertTrue(all(r['status'] == 'OK' and r['request_bound'] for r in packet['quotes']['rows']))
        self.assertEqual(packet['funding_input']['versus_exit_reserve'], 'AT_OR_ABOVE_EXIT_RESERVE')
        self.assertEqual(packet['funding_input']['indicative_swaps_affordable'], 3 * 10**15 // (250000 * 10**8))
        self.assertFalse(packet['signing_enabled'])


if __name__ == '__main__':
    unittest.main()
