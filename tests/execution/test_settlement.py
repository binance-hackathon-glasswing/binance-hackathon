from dataclasses import replace
from datetime import datetime, timezone
import unittest

from larp.contracts import ContractError, Document
from larp.execution import Attempt, Blocked, Execution, Payload, USDT
from larp.execution_live.config import WalletBinding
from larp.execution_live.service import broadcast_observation
from larp.execution_live.settlement import TRANSFER, ReceiptFacts, final_observation
from larp.research.fixtures import snapshot
from larp.risk.accounting import advance_accounting
from tests.execution_fixtures import intent, TOKEN, WALLET, ROUTER

HASH = '0x' + 'a' * 64
BLOCK = '0x' + 'b' * 64
STAMP = '2026-10-11T16:00:00Z'


def log(token, source, destination, amount):
    return dict(address=token, topics=[TRANSFER, '0x' + '0' * 24 + source[2:],
                                       '0x' + '0' * 24 + destination[2:]], data='0x' + format(amount, '064x'))


class SettlementTests(unittest.TestCase):
    def setUp(self):
        self.intent = intent(run_id='synthetic-run', amount=40 * 10**18, minimum_output=3 * 10**17)
        self.payload = Payload(56, WALLET, ROUTER, 0, 3, 200000, 10, '0xdeadbeef')
        self.attempt = Attempt('a', 'SWAP', 'FINAL_SUCCESS', self.payload, 1, 1,
                               tx_hash=HASH, broadcast_at=100)
        self.state = Execution(self.intent, attempts=(self.attempt,), status='COMPLETED')
        self.proof = dict(finality_verified=True, block_hash=BLOCK, block_number=10, finalized_height=12,
            tx=dict(hash=HASH, nonce='0x3', to=ROUTER, input='0xdeadbeef', value='0x0', chainId='0x38',
                    gas=hex(200000), gasPrice='0xa', **{'from':WALLET}),
            receipt=dict(transactionHash=HASH, blockHash=BLOCK, blockNumber='0xa', gasUsed=hex(50000),
                         effectiveGasPrice='0xa', status='0x1', **{'from':WALLET},
                         logs=[log(USDT, WALLET, ROUTER, 40 * 10**18), log(TOKEN, ROUTER, WALLET, 4 * 10**17)]))
        p = snapshot().context.read()['portfolio']
        p.update(bnb_units=10**15, bnb_decimals=18, bnb_price_units=700000000)
        p['positions']['NVDAB'].update(units=0, decimals=18)
        p['reservations'][self.intent.intent_id] = dict(side='BUY', symbol='NVDAB', cash_units=40000000,
            bnb_units=10000000, token_units=4 * 10**17, pay_units=40000000, min_receive_units=3 * 10**17)
        self.portfolio = Document.from_dict(p)

    def observed(self):
        return Document.from_dict(final_observation(self.state, self.attempt, self.proof,
            wallet_id='fake-wallet', bnb_price_units=700000000, observed_at=STAMP))

    def test_actual_receipt_passes_accounting_and_replay(self):
        event = self.observed()
        after = advance_accounting(self.portfolio, event)
        self.assertEqual(after.read()['positions']['NVDAB']['units'], 4 * 10**17)
        self.assertEqual(after.read()['bnb_units'], 10**15 - 500000)
        self.assertEqual(advance_accounting(after, event), after)

    def test_broadcast_fact_cannot_change_accounting(self):
        event = Document.from_dict(broadcast_observation(self.state, self.attempt, wallet_id='fake-wallet'))
        with self.assertRaises(ContractError):
            advance_accounting(self.portfolio, event)

    def test_missing_finality_and_inconsistent_transfers_block(self):
        self.proof['finality_verified'] = False
        with self.assertRaises(Blocked):
            self.observed()
        self.proof['finality_verified'] = True
        self.proof['receipt']['logs'][1] = log(TOKEN, ROUTER, WALLET, 1)
        with self.assertRaises(Blocked):
            self.observed()

    def test_approval_and_revert_only_charge_actual_gas(self):
        self.attempt = replace(self.attempt, step='APPROVE')
        after = advance_accounting(self.portfolio, self.observed()).read()
        self.assertEqual(after['positions']['NVDAB']['units'], 0)
        self.assertIn(self.intent.intent_id, after['reservations'])
        self.proof['receipt']['status'] = '0x0'
        after = advance_accounting(self.portfolio, self.observed()).read()
        self.assertFalse(after['reservations'])

    def test_wallet_paths_and_nonce_namespace(self):
        one = WalletBinding.create('dev', WALLET, '/tmp/runtime', expected_wallet=WALLET)
        two = WalletBinding.create('final', ROUTER, '/tmp/runtime', expected_wallet=ROUTER)
        self.assertNotEqual(one.audit_directory, two.audit_directory)
        self.assertNotEqual(one.nonce_namespace, two.nonce_namespace)
        with self.assertRaises(Blocked):
            WalletBinding.create('dev', WALLET, '/tmp/runtime', expected_wallet=ROUTER)

    def test_receipt_retry_reuses_first_finality_proof_and_observation_bytes(self):
        class Registry:
            fact = None
            def lookup_observation(self, event_id):
                return self.fact
            def check_authority(self, epoch, version):
                if (epoch, version) != (1, 1):raise Blocked('fenced')
            def put_observation(self, fact, epoch, version):
                self.fact = fact
                return fact
        class Chain:
            calls = 0
            def receipt(chain, tx_hash):
                chain.calls += 1
                return self.proof
        registry, chain = Registry(), Chain()
        facts = ReceiptFacts(chain, wallet_id='fake-wallet', valuation=lambda _:700000000, registry=registry,
                             epoch=1, authority_version=1)
        attempt = replace(self.attempt, finalized_at=1791734400)
        first = facts(self.state, attempt)
        self.proof['finalized_height'] += 10
        second = facts(self.state, attempt)
        self.assertEqual(first, second)
        self.assertEqual(chain.calls, 1)

    def test_fractional_sell_cash_settles_with_exact_dust(self):
        self.intent = replace(self.intent, pay_token=TOKEN, receive_token=USDT,
                              amount=4 * 10**17, minimum_output=40 * 10**18)
        self.state = replace(self.state, intent=self.intent)
        actual = 40123456789012345678
        self.proof['receipt']['logs'] = [log(TOKEN, WALLET, ROUTER, self.intent.amount),
                                        log(USDT, ROUTER, WALLET, actual)]
        p=self.portfolio.read()
        p['positions']['NVDAB'].update(units=self.intent.amount,cost_basis_units=40000000)
        p['reservations'][self.intent.intent_id].update(side='SELL',token_units=self.intent.amount,
                                                      pay_units=self.intent.amount,min_receive_units=40000000)
        observation=self.observed()
        result=advance_accounting(Document.from_dict(p),observation).read()
        self.assertEqual(result['positions']['NVDAB']['units'],0)
        self.assertEqual(observation.read()['cash_units'],40123456)
        self.assertEqual(observation.read()['cash_dust_chain_units'],789012345678)
        self.assertEqual(observation.read()['actual_cash_chain_units'],actual)

    def test_final_fact_producer_cannot_borrow_current_authority(self):
        class Registry:
            def check_authority(self,e,v):raise Blocked('fenced')
            def lookup_observation(self,_):raise AssertionError('must fence before read')
            def put_observation(self,*_):raise AssertionError('must not write')
        facts=ReceiptFacts(None,wallet_id='fake-wallet',valuation=None,registry=Registry(),epoch=1,authority_version=1)
        with self.assertRaises(Blocked):facts(self.state,replace(self.attempt,finalized_at=1791734400))
