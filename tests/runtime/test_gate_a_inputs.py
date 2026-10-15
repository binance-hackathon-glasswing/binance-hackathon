"""IDEA-058 G1-G5: the initial-state builder and the issuers-map generator. Synthetic chain and Web3 data only."""

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.execution import USDT
from larp.marketdata.port import TOKENS, MarketPort
from tests.runtime.test_balance_reconciliation import HASH, HEIGHT, WALLET, Chain, observe
from tests.strategy.live_fixtures import registry, summary

RUN = 'dev-run-1'
CASH_RAW = 100 * 10**18 + 123  # 100 USDT plus dust below one money unit
NATIVE = 3 * 10**15  # 0.003 BNB


def profile(env='REHEARSAL'):
    from larp.strategy.profiles import build_live_profiles
    return build_live_profiles(summary(), registry())[env].read()


def chain(**tokens):
    held = {'USDT': CASH_RAW, **{s: 0 for s in TOKENS}, **tokens}
    return Chain(native=held.pop('BNB', NATIVE), tokens=held, decimals={'USDT': 18, **{s: 18 for s in TOKENS}})


def build(o=None, **options):
    from larp.runtime.initial_state import build_initial_state
    args = dict(run_id=RUN, wallet=WALLET, mode='dev', profile=profile())
    args.update(options)
    return build_initial_state(o or observe(chain()), **args)


def dr06(state, native):
    """gate_b.py DR-06, as written there."""
    from larp.integration.runtime import initial_projection, ledger_from
    assert state['schema'] == 'PortfolioState.v1' and state['wallet_id'] == WALLET and state['run_id'] == RUN
    assert type(state['bnb_decimals']) is int and state['bnb_decimals'] == 18 and state.get('mode') in ('dev', 'LIVE')
    for units in [state['cash_units'], state['bnb_units'], *[p['units'] for p in state['positions'].values()]]:
        assert type(units) is int and units >= 0
    ledger_from(initial_projection(state), [])
    assert state['bnb_units'] == native and state['bnb_units'] != 0


class InitialState(unittest.TestCase):
    def test_g1_the_state_is_the_chain_at_one_block(self):
        from larp.risk.reconcile import compare_balances
        p = profile()
        o = observe(chain())
        state = build(o)
        self.assertEqual(state['cash_units'], 100_000_000)  # the dust is not booked
        self.assertEqual((state['bnb_units'], state['bnb_decimals']), (NATIVE, 18))
        self.assertEqual(set(state['positions']), set(TOKENS))
        self.assertTrue(all(pos == dict(units=0, decimals=18, cost_basis_units=0) for pos in state['positions'].values()))
        price = p['quote_cost_summary']['bnb_price_units']
        self.assertEqual(state['bnb_price_units'], price)
        equity = 100_000_000 + int(Fraction(NATIVE * price, 10**18))
        self.assertEqual(state['opening_equity_units'], equity)
        self.assertEqual((state['risk']['peak_units'], state['risk']['day_anchor_units']), (equity, equity))
        self.assertEqual(state['risk']['day'], '2026-10-20')
        self.assertEqual({k: state['risk'][k] for k in ('daily_halt', 'run_halt', 'deep_cut')},
                         dict(daily_halt=False, run_halt=False, deep_cut=False))
        self.assertEqual((state['mode'], state['reservations'], state['applied_events']), ('dev', {}, {}))
        self.assertEqual(set(state['accounting'].values()), {0})
        check = compare_balances(state, o, settled_block=None)
        self.assertEqual((check['status'], check['surplus']), ('MATCH', []))  # 123 wei of USDT floors away
        dr06(state, NATIVE)
        self.assertEqual(build(mode='live')['mode'], 'LIVE')

    def test_g2_refusals(self):
        held = observe(chain(NVDAB=5))
        pending = chain()
        pending.pending = 8
        cases = {
            'held stock token': dict(o=held),
            'pending transaction': dict(o=observe(pending)),
            'no BNB': dict(o=observe(chain(BNB=0))),
            'profile not LIVE': dict(profile=dict(profile(), mode='OFFLINE')),
            'profile without summary': dict(profile={k: v for k, v in profile().items() if k != 'quote_cost_summary'}),
            'unknown mode': dict(mode='paper'),
            'other wallet': dict(wallet='0x' + '5' * 40),
        }
        for name, change in cases.items():
            with self.subTest(name), self.assertRaises(ContractError):
                build(change.pop('o', None), **change)


class InitialStateCli(unittest.TestCase):
    def test_g3_cli_writes_pinnable_bytes_that_init_accepts(self):
        from larp.runtime import initial_state
        from larp.runtime.service import init_run
        from larp.storage.postgres import Conflict
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'profile.json').write_text(json.dumps(profile()))
            out = tmp / 'initial-state.json'
            args = ['--rpc-url', 'https://rpc.invalid/', '--rpc-source-id', 'synthetic', '--wallet', WALLET,
                    '--run-id', RUN, '--mode', 'dev', '--profile', str(tmp / 'profile.json'), '--output', str(out)]
            with patch.object(initial_state, 'observe', return_value=observe(chain())), \
                    patch('builtins.print') as printed:
                self.assertEqual(initial_state.main(args), 0)
            raw = out.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            self.assertIn(digest, ' '.join(str(a) for c in printed.call_args_list for a in c.args))
            provenance = json.loads((tmp / 'initial-state.json.provenance.json').read_text())
            self.assertEqual((provenance['block_number'], provenance['block_hash']), (HEIGHT, HASH))
            self.assertEqual(provenance['profile_sha256'], hashlib.sha256((tmp / 'profile.json').read_bytes()).hexdigest())
            with patch.object(initial_state, 'observe', return_value=observe(chain())):
                self.assertEqual(initial_state.main(args), 2)  # never overwrites
            self.assertEqual(out.read_bytes(), raw)

            class Store:
                def load(self, run_id):
                    raise Conflict('no run')

                def initialize(self, run_id, wallet, chain_id, projection, mode):
                    self.created = (run_id, wallet, chain_id, mode, projection.read())
            store = Store()
            config = dict(run_id=RUN, mode='dev', wallet_address=WALLET, initial_state_file=str(out),
                          initial_state_sha256=digest)
            self.assertEqual(init_run(config, store)['initialized'], True)
            self.assertEqual(store.created[4]['portfolio']['cash_units'], 100_000_000)


# ------------------------------------------------------------------------------------------------ issuers map
TICKERS = dict(NVDAB='NVDA', GOOGLB='GOOGL', TSLAB='TSLA', MSFTB='MSFT', SKHYB='SKHY')


class TokenMetadata:
    def __init__(self, tickers=None, rows=None):
        self.tickers = dict(TICKERS, **(tickers or {}))
        self.rows = rows

    def request(self, method, endpoint, params):
        assert (method, endpoint) == ('GET', 'market/rwa/tokens'), endpoint
        rows = self.rows if self.rows is not None else [
            dict(tokenContractAddress=t, tokenSymbol=s, binanceChainId='56', decimals='18',
                 underlyingTicker=self.tickers[s]) for s, t in TOKENS.items()]
        return dict(response=dict(code=0, data=rows), available_at='2026-10-15T00:00:00Z', artifact_sha256='e' * 64)


def issuers(client):
    from larp.runtime.issuers_map import build_issuers_map
    return build_issuers_map(MarketPort(client, WALLET))


class IssuersMap(unittest.TestCase):
    def test_g4_each_issuer_maps_to_its_token_and_ticker(self):
        from larp.integration.contract import _issuer_matches
        from larp.intelligence.config import load_registry
        mapping, provenance = issuers(TokenMetadata())
        reg = {e.token: e.issuer_id for e in load_registry().entries}
        self.assertEqual(mapping, {reg[s]: dict(token=s, underlying_id=TICKERS[s]) for s in TOKENS})
        self.assertEqual(mapping['SEC-CIK-0001045810'], dict(token='NVDAB', underlying_id='NVDA'))
        self.assertEqual(provenance['metadata_artifact_sha256'], 'e' * 64)
        for issuer_id, meta in mapping.items():
            record = dict(issuer_id=issuer_id, token=meta['token'], underlying_id=meta['underlying_id'])
            self.assertTrue(_issuer_matches(record, meta['underlying_id'], source_id='BINANCE_WEB3'), issuer_id)

    def test_g5_refusals_and_the_driver_check(self):
        from larp.intelligence.config import load_registry
        from larp.marketdata.web3 import Unavailable
        rows = TokenMetadata().request('GET', 'market/rwa/tokens', {})['response']['data']
        cases = {
            'unlisted ticker': TokenMetadata(tickers=dict(GOOGLB='AAPL')),
            'missing ticker': TokenMetadata(tickers=dict(TSLAB='')),
            'duplicate token row': TokenMetadata(rows=rows + rows[:1]),
            'missing token row': TokenMetadata(rows=rows[1:]),
        }
        for name, client in cases.items():
            with self.subTest(name), self.assertRaises((ContractError, Unavailable)):
                issuers(client)
        mapping, _ = issuers(TokenMetadata())
        registry_entries = load_registry().entries
        for issuer_id, meta in mapping.items():  # larp/runtime/service.py build_driver, as written there
            known = [e for e in registry_entries if e.issuer_id == issuer_id]
            self.assertTrue(known and type(meta) is dict and meta.get('token') == known[0].token
                            and type(meta.get('underlying_id')) is str and meta['underlying_id'])

    def test_g5_cli_never_overwrites(self):
        from larp.runtime import issuers_map
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'issuers.json'
            args = ['--address', WALLET, '--output', str(out)]
            with patch.dict('os.environ', {}, clear=True):
                self.assertEqual(issuers_map.main(args), 2)  # no key pair: nothing called
            self.assertEqual(issuers_map.main(args, client=TokenMetadata()), 0)
            written = json.loads(out.read_text())
            self.assertEqual(len(written), 5)
            self.assertTrue((Path(tmp) / 'issuers.json.provenance.json').exists())
            self.assertEqual(issuers_map.main(args, client=TokenMetadata()), 2)


if __name__ == '__main__':
    unittest.main()
