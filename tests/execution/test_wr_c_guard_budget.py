"""WR-C #53 (WR11): guard snapshots fit an approve->swap inside the 15 s intent (IDEA-049-C, WR-C criteria 9-10).

The real `Web3Client` (0.35 s minimum spacing) runs on a virtual clock behind a fake HTTP opener, so the forced
spacing is measured exactly without sleeping. Arbitrary fixture bytes; nothing is signed or sent.
"""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from larp.execution import Blocked, Executor, Outcome, SwapEconomics, USDT, canonical
from larp.execution_live.guards import LiveGuards
from larp.execution_live.loop import Web3Broadcaster
from larp.execution_live.service import ExecutionService
from larp.execution_live.venue import LiveVenue
from larp.marketdata.port import MarketPort, TOKENS
from larp.marketdata.web3 import Artifacts, Web3Client
from tests.execution_fixtures import BLOCK, ROUTER, TOKEN, WALLET, FakeDecoder, FakeSigner, SQLiteFixture, intent
from tests.marketdata.test_transport import Response

EXPIRY_S = 15  # the intent lifetime the issue measures against
START = 100


class Clock:
    """`time` for larp.marketdata.web3: monotonic time advances only through the client's own spacing sleeps."""

    def __init__(self):
        self.t, self.spacing = 1000.0, 0.0

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds
        self.spacing += seconds

    def now_s(self):
        return START + int(self.t - 1000.0)


class Web3(object):
    """Fake HTTP for every Web3 endpoint the execution path calls; records the endpoint of each request."""

    def __init__(self):
        self.calls, self.token_open, self.underlying_open, self.tx_hash = [], True, True, None

    def open(self, request, timeout):
        url = urlsplit(request.full_url)
        endpoint = url.path.split('/api/v1/dex/', 1)[1]
        params = {k: v[0] for k, v in parse_qs(url.query).items()}
        self.calls.append(endpoint)
        return Response(json.dumps(dict(code=0, data=self.data(endpoint, params))).encode())

    def data(self, endpoint, params):
        if endpoint == 'market/rwa/tokens':
            return [dict(tokenContractAddress=token, tokenSymbol=symbol, binanceChainId='56', decimals='18',
                         underlyingTicker=symbol[:-1], statusInfo=dict(openState=self.token_open))
                    for symbol, token in TOKENS.items()]
        if endpoint == 'market/rwa/underlying-market':
            return [dict(tokenContractAddress=params['tokenContractAddress'],
                         statusInfo=dict(openState=self.underlying_open))]
        if endpoint == 'market/rwa/price':
            return [dict(tokenContractAddress=params['tokenContractAddresses'], tokenPrice='100')]
        if endpoint == 'aggregator/quote-and-swap':
            economics = SwapEconomics(USDT, TOKEN, 100, WALLET, 100, START + EXPIRY_S, 0)
            data = '0xfafafafa' + canonical(asdict(economics)).encode().hex()
            return [dict(executionMode='SWAP', rfq=None, routerResult=dict(vendorName='LiquidMesh', toTokenAmount='100'),
                         tx=dict(to=ROUTER, value='0', gas='100000', gasPrice='1', data=data, minReceiveAmount='100'))]
        if endpoint == 'aggregator/approve-transaction':
            return [dict(dexContractAddress=ROUTER, gasLimit='100000', gasPrice='1',
                         data='0x095ea7b3' + '0' * 24 + ROUTER[2:] + format(100, '064x'))]
        if endpoint == 'pre-transaction/gas-limit':
            return [dict(gasLimit='100000')]
        if endpoint == 'pre-transaction/broadcast-transaction':
            return [dict(txHash=self.tx_hash)]
        raise AssertionError('unexpected endpoint ' + endpoint)


class Chain:
    """Chain evidence: three RPC calls per nonce read (chain id, latest, pending), as ChainEvidence.nonce makes."""
    mode = 'live'

    def __init__(self):
        self.nonce_value, self.sent, self.rpc = 0, {}, 0

    def nonce(self, wallet):
        self.rpc += 3
        return self.nonce_value

    def outcome(self, tx_hash):
        self.rpc += 1
        nonce = self.sent[tx_hash]
        self.nonce_value = max(self.nonce_value, nonce + 1)
        return Outcome(tx_hash, WALLET, nonce, 'SUCCESS', BLOCK, BLOCK, 10, 12, True, 50000)


class Store(SQLiteFixture):
    def execution_authority(self):
        return self.authority()


def facts(intent, epoch, state_version, now):
    return dict(expires_at=intent.valid_until, audit_durable=True, reservation_valid=True, version_valid=True,
                risk_valid=True, health_valid=True, clock_trusted=True)


class BudgetCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.clock = Clock()
        patcher = patch('larp.marketdata.web3.time', self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.web3, self.chain = Web3(), Chain()
        root = Path(self.tmp.name)
        self.client = Web3Client('fixture-key', 'fixture-secret', artifacts=Artifacts(root / 'market'),
                                 opener=self.web3)  # real 0.35 s spacing
        self.market = MarketPort(self.client, WALLET)
        self.store = Store(str(root / 'w04.sqlite'))
        self.addCleanup(self.store.close)

    def guards(self, **kwargs):
        class Guards(LiveGuards):
            mode = 'fake'  # the W04 Executor accepts fake bundles only; the ports underneath are the live ones
        return Guards(store=self.store, market=self.market, chain=self.chain, authorization=facts, **kwargs)


class ApproveSwapBudget(BudgetCase):
    def run_approve_swap(self, confirmation_s=0):
        """One approve->swap through ExecutionService.advance; returns the final state."""
        broadcaster = Web3Broadcaster('fixture-key', 'fixture-secret', wallet=WALLET,
                                      artifacts=str(Path(self.tmp.name) / 'broadcast'), opener=self.web3)

        def release(signed, epoch, guard_version):
            self.web3.tx_hash = signed.tx_hash
            self.chain.sent[signed.tx_hash] = self.chain.nonce_value
            return broadcaster.send('0x' + signed.raw_hex)

        class Venue(LiveVenue):
            mode = 'fake'
        venue = Venue(self.client, self.chain, decoder=FakeDecoder(), release=release)
        executor = Executor(self.store, self.guards(), venue, FakeSigner(self.store), FakeDecoder())
        service = ExecutionService(store=None, executor=executor, mapping={}, observe=lambda fact: None,
                                   wallet_id=WALLET, epoch=1, authority_version=1,
                                   settlement=lambda state, attempt: dict(
                                       schema='ExecutionObservation.v1', settlement='FINAL', kind='APPROVAL',
                                       intent_id=state.intent.intent_id, attempt_id=attempt.attempt_id,
                                       tx_hash=attempt.tx_hash))
        economic = intent(amount=100, minimum_output=90, valid_until=START + EXPIRY_S, max_gas=200000,
                          max_gas_price=10, gas_budget=1000000)
        executor.create(economic, self.clock.now_s())
        state = None
        for _ in range(40):
            try:
                state = service.advance(economic.key, self.clock.now_s())
            except Blocked:  # e.g. the intent expired mid-way and the fixture store cannot revoke
                state = self.store.load(economic.key)
                break
            if state.status != 'ACTIVE':
                break
            if state.attempts and (state.attempts[-1].step, state.attempts[-1].state) == ('APPROVE', 'PENDING'):
                self.clock.t += confirmation_s  # waiting for the approve on chain, not request spacing
        return state

    def test_wr11_approve_swap_fits_inside_the_intent_expiry(self):
        state = self.run_approve_swap()
        requests, spacing = len(self.web3.calls), self.clock.spacing
        print(f'\nWR11 approve->swap: {requests} Web3 requests {sorted(set(self.web3.calls))}, '
              f'{spacing:.2f} s spacing, {self.chain.rpc} RPC calls')
        self.assertEqual(state.status, 'COMPLETED', state.blocked_reason)
        self.assertLessEqual(requests, 12)
        self.assertLessEqual(spacing, EXPIRY_S / 2)
        self.assertNotIn('market/rwa/price', self.web3.calls)
        self.assertEqual(self.web3.calls.count('aggregator/quote-and-swap'), 2)  # the venue's quotes only

    def test_wr11_a_slow_approve_confirmation_refreshes_market_facts_and_still_fits(self):
        state = self.run_approve_swap(confirmation_s=10)  # the facts are then older than the 10 s window
        print(f'\nWR11 approve->swap, 10 s approve confirmation: {len(self.web3.calls)} Web3 requests, '
              f'{self.clock.spacing:.2f} s spacing')
        self.assertEqual(state.status, 'COMPLETED', state.blocked_reason)
        self.assertEqual(self.web3.calls.count('market/rwa/tokens'), 2)
        self.assertLessEqual(len(self.web3.calls), 12)
        self.assertLessEqual(self.clock.spacing, EXPIRY_S / 2)


class GuardFreshness(BudgetCase):
    def test_wr11_guards_read_open_state_only(self):
        gates = self.guards().snapshot(intent(), START)
        self.assertTrue(gates.token_market_open and gates.underlying_market_open)
        self.assertEqual(self.web3.calls, ['market/rwa/tokens', 'market/rwa/underlying-market'])

    def test_wr11_facts_are_reused_inside_the_window_and_per_round(self):
        guards = self.guards(market_freshness_s=10)
        guards.snapshot(intent(), START)
        guards.snapshot(intent(), START + 9)
        self.assertEqual(len(self.web3.calls), 2)
        guards.snapshot(intent(round_id='next-round'), START + 9)  # a new round reads the list again
        self.assertEqual(self.web3.calls.count('market/rwa/tokens'), 2)

    def test_wr11_a_close_is_seen_once_the_window_passes(self):
        guards = self.guards(market_freshness_s=10)
        self.assertTrue(guards.snapshot(intent(), START).token_market_open)
        self.web3.token_open = False
        self.assertTrue(guards.snapshot(intent(), START + 9).token_market_open)  # still inside the window
        closed = guards.snapshot(intent(), START + 10)
        self.assertFalse(closed.token_market_open)
        with self.assertRaises(Blocked):
            closed.check(intent(), START + 10)
        self.web3.token_open, self.web3.underlying_open = True, False
        self.assertFalse(guards.snapshot(intent(), START + 20).underlying_market_open)

    def test_wr11_a_failed_observation_blocks_and_is_not_cached(self):
        guards = self.guards()
        working = self.web3.data
        self.web3.data = lambda endpoint, params: {} if endpoint == 'market/rwa/underlying-market' else working(
            endpoint, params)
        failed = guards.snapshot(intent(), START)
        self.assertFalse(failed.token_market_open or failed.underlying_market_open)
        with self.assertRaises(Blocked):
            failed.check(intent(), START)
        self.web3.data = working
        self.assertTrue(guards.snapshot(intent(), START + 1).underlying_market_open)  # retried, not cached

    def test_wr11_clock_regression_refetches(self):
        guards = self.guards()
        guards.snapshot(intent(), START + 5)
        guards.snapshot(intent(), START)
        self.assertEqual(self.web3.calls.count('market/rwa/tokens'), 2)

    def test_wr11_freshness_window_is_bounded(self):
        for value in (0, 31, 1.5, True, None):
            with self.subTest(value=value), self.assertRaises(Blocked):
                self.guards(market_freshness_s=value)
