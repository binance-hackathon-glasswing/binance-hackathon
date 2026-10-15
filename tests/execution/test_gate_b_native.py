"""GB-NATIVE: transaction-bound native output reaches real I4/accounting."""
from copy import deepcopy
from dataclasses import replace
import unittest

from larp.contracts import Document
from larp.execution import Blocked, NATIVE_BNB, Execution
from larp.execution_live.chain import ChainEvidence
from larp.execution_live.settlement import final_observation
from larp.execution_live.settlement import ReceiptFacts
from larp.execution_live.loop import PlanValuation
from larp.execution_live.store import ExecutionStore
from larp.ports import validate_execution_observation
from larp.risk.accounting import advance_accounting
from tests.execution import test_settlement as fixtures
from tests.execution_fixtures import WALLET, ROUTER
from tests.support import DatabaseCase
from larp.runtime.coordinator import batch_for
from larp.storage.postgres import doc


class NativeSettlement(unittest.TestCase):
    def setUp(self):
        case = fixtures.SettlementTests()
        case.setUp()
        self.attempt, self.proof = case.attempt, deepcopy(case.proof)
        self.intent = replace(case.intent, kind='GAS_TOP_UP', receive_token=NATIVE_BNB,
                              minimum_output=10**15)
        self.state = Execution(self.intent, attempts=(self.attempt,), status='COMPLETED')
        self.proof['receipt']['logs'] = self.proof['receipt']['logs'][:1]
        self.proof['native_balance'] = dict(schema='TransactionNativeBalance.v1',
            method='GETH_PRESTATE_DIFF', source_id='synthetic-chain', tx_hash=fixtures.HASH,
            block_hash=fixtures.BLOCK, wallet=WALLET, nonce=3, before_wei=10**15,
            after_wei=3 * 10**15 - 500000, trace_sha256='d' * 64)
        p = case.portfolio.read()
        p['reservations'][self.intent.intent_id].update(kind='GAS_TOP_UP', symbol='BNB',
            min_receive_units=10**15, token_units=2 * 10**15)
        self.portfolio = Document.from_dict(p)

    def observed(self, **kwargs):
        return final_observation(self.state, self.attempt, self.proof, wallet_id='fake-wallet',
            bnb_price_units=700000000, observed_at=fixtures.STAMP, **kwargs)

    def test_gb_native_actual_output_and_gas_pass_existing_accounting_and_replay(self):
        event = self.observed()
        validate_execution_observation(event)
        after = advance_accounting(self.portfolio, Document.from_dict(event))
        self.assertEqual(event['symbol'], 'BNB')
        self.assertEqual(event['token_units'], 2 * 10**15)
        self.assertEqual(after.read()['bnb_units'], 3 * 10**15 - 500000)
        self.assertEqual(after.read()['positions'], self.portfolio.read()['positions'])
        self.assertFalse(after.read()['reservations'])
        self.assertEqual(advance_accounting(after, Document.from_dict(event)), after)

    def test_gb_native_missing_whole_block_or_unbound_proof_never_fills(self):
        original = deepcopy(self.proof)
        changes = [None, dict(original['native_balance'], method='BLOCK_BALANCE_DELTA'),
                   dict(original['native_balance'], tx_hash='0x' + 'e' * 64),
                   dict(original['native_balance'], block_hash='0x' + 'e' * 64),
                   dict(original['native_balance'], wallet=ROUTER),
                   dict(original['native_balance'], nonce=4),
                   dict(original['native_balance'], before_wei=True),
                   dict(original['native_balance'], trace_sha256='bad')]
        for change in changes:
            with self.subTest(change=change):
                self.proof = dict(original, native_balance=change)
                with self.assertRaises(Blocked):
                    self.observed()

    def test_gb_native_exact_pay_and_minimum_output_are_still_required(self):
        self.proof['native_balance']['after_wei'] = 10**15 - 500000 + 1
        with self.assertRaises(Blocked):
            self.observed()

    def test_gb_native_approval_and_revert_only_charge_gas(self):
        for step, status in (('APPROVE', '0x1'), ('SWAP', '0x0')):
            self.attempt = replace(self.attempt, step=step)
            self.proof['receipt']['status'] = status
            self.proof.pop('native_balance', None)
            event = self.observed()
            after = advance_accounting(self.portfolio, Document.from_dict(event)).read()
            self.assertEqual(after['bnb_units'], 10**15 - 500000)
            self.assertEqual(after['cash_units'], self.portfolio.read()['cash_units'])

    def test_gb_native_explicit_non18_scale_converts_gas_and_output_exactly(self):
        self.attempt = replace(self.attempt, payload=replace(self.attempt.payload, gas_price=10**9))
        self.proof['tx']['gasPrice'] = hex(10**9)
        self.proof['receipt'].update(gasUsed=hex(1000), effectiveGasPrice=hex(10**9))
        self.proof['native_balance']['after_wei'] = 3 * 10**15 - 10**12
        event = self.observed(bnb_decimals=6)
        self.assertEqual((event['gas_bnb_units'], event['token_units']), (1, 2000))
        self.assertEqual(event['receipt_evidence']['gas_chain_units'], 10**12)

    def test_gb_native_unrepresentable_gas_is_not_silently_rounded(self):
        with self.assertRaises(Blocked):
            self.observed(bnb_decimals=6)


class NativeRPC(unittest.TestCase):
    def rpc(self, *, enabled=True, bad=None):
        case = fixtures.SettlementTests()
        case.setUp()
        proof = case.proof
        calls = []
        class RPC:
            native_trace = enabled
            source_id = 'synthetic-chain'
            def call(self, method, params):
                calls.append((method, params))
                if method == 'eth_chainId': return '0x38'
                if method == 'eth_getTransactionByHash': return proof['tx'] | dict(blockHash=fixtures.BLOCK, blockNumber='0xa')
                if method == 'eth_getTransactionReceipt': return proof['receipt']
                if method == 'eth_getBlockByNumber':
                    return dict(hash=fixtures.BLOCK, number='0xa', transactions=[fixtures.HASH])
                if method == 'debug_traceTransaction':
                    if bad == 'reorg': proof['receipt']['blockHash'] = '0x' + 'e' * 64
                    if bad == 'missing': return dict(pre={}, post={})
                    if bad == 'nonce': return dict(pre={WALLET: dict(balance=hex(10**15), nonce=4)}, post={WALLET: dict(nonce=5)})
                    return dict(pre={WALLET: dict(balance=hex(10**15), nonce=3)},
                                post={WALLET: dict(balance=hex(3 * 10**15 - 500000), nonce=4)})
                raise AssertionError(method)
        return RPC(), calls

    def test_gb_native_tracing_is_explicit_and_receipt_is_rechecked(self):
        rpc, calls = self.rpc()
        proof = ChainEvidence(rpc).native_receipt(fixtures.HASH)
        self.assertEqual(proof['native_balance']['after_wei'], 3 * 10**15 - 500000)
        self.assertEqual(sum(m == 'eth_getTransactionReceipt' for m, _ in calls), 2)
        trace = next(p for m, p in calls if m == 'debug_traceTransaction')
        self.assertEqual(trace, [fixtures.HASH, dict(tracer='prestateTracer', tracerConfig=dict(
            diffMode=True, disableCode=True, disableStorage=True))])

    def test_gb_native_disabled_provider_has_no_trace_call(self):
        rpc, calls = self.rpc(enabled=False)
        with self.assertRaises(Blocked):
            ChainEvidence(rpc).native_receipt(fixtures.HASH)
        self.assertFalse(calls)

    def test_gb_native_missing_nonce_or_reorg_evidence_refuses(self):
        for bad in ('missing', 'nonce', 'reorg'):
            with self.subTest(bad=bad), self.assertRaises(Blocked):
                rpc, _ = self.rpc(bad=bad)
                ChainEvidence(rpc).native_receipt(fixtures.HASH)


class NativeDurability(DatabaseCase):
    def test_gb_native_real_pg_reuses_persisted_valuation_scale_and_observation(self):
        case = NativeSettlement()
        case.setUp()
        p = case.portfolio.read()
        p.update(run_id='native-run', wallet_id=WALLET)
        record = dict(policy_input=dict(context=dict(portfolio=p)), plan=dict(intents=[]))
        projection = dict(balances=dict(USDT=p['cash_units'], BNB=p['bnb_units']),
                          round_records={case.intent.round_id: record})
        self.store.initialize('native-run', WALLET, 56, doc(projection))
        epoch = self.store.takeover('native-run', 1, offline=True)
        self.store.commit(batch_for(self.store.load('native-run'), 'plan:' + case.intent.round_id,
            dict(kind='ROUND_PLANNED', record=record), projection=projection))
        registry = ExecutionStore(self.store, run_id='native-run', wallet=WALLET)
        economic = replace(case.intent, run_id='native-run')
        attempt = replace(case.attempt, finalized_at=1791734400)
        state = registry.commit(None, Execution(economic, attempts=(attempt,), status='COMPLETED'),
            dict(type='SYNTHETIC_NATIVE_FINAL'), epoch, self.store.load('native-run').read()['version'])
        valuation = PlanValuation(self.store, registry, run_id='native-run')
        class Chain:
            calls = 0
            def native_receipt(chain, tx_hash):
                chain.calls += 1
                return case.proof
            def receipt(chain, tx_hash):
                raise AssertionError('native output needs transaction trace')
        chain = Chain()
        callback = ReceiptFacts(chain, wallet_id=WALLET, valuation=valuation, bnb_decimals=valuation.bnb_decimals,
            registry=registry, epoch=epoch, authority_version=epoch, round_terminal=lambda _: True)
        first = callback(state, attempt)
        self.assertEqual(callback(state, attempt), first)
        self.assertEqual(chain.calls, 1)
        before = Document.from_dict(p)
        after = advance_accounting(before, Document.from_dict(first))
        self.assertEqual(after.read()['bnb_units'], 3 * 10**15 - 500000)
        self.assertEqual(advance_accounting(after, Document.from_dict(first)), after)
        self.assertEqual(registry.lookup_observation(attempt.attempt_id + ':final'), first)
