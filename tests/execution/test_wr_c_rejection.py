"""WR-C #54 (WR12): a broadcast the node definitely rejected ends NOT_SUBMITTED (IDEA-049-C, WR-C criteria 6-8).

Fake HTTP for the broadcaster and disposable PostgreSQL for the execution record; arbitrary fixture bytes, never a
real transaction. A rejected attempt keeps the wallet barrier until its timeout has passed and the wallet's chain
nonce shows that its nonce was never used; a timeout or a lost response stays unresolved.
"""
from dataclasses import replace
import json
import tempfile
import unittest

from larp.execution import Conflict, DependencyUnavailable, Executor, Outcome, possible_swap_hashes
from larp.execution_live.loop import ExecutionLoop, Web3Broadcaster
from larp.execution_live.service import ExecutionService
from larp.execution_live.store import ExecutionStore
from tests.execution.test_postgres_execution import ExecutionGuards, RegistrySigner
from tests.execution_fixtures import WALLET, FakeDecoder, FakeVenue, finalized, intent
from tests.marketdata.test_transport import Opener, Response
from tests.support import DatabaseCase

RAW = '0x' + 'f8ab' * 40  # arbitrary fixture bytes, not an EVM signature


def rejection(message, code=50000):
    return json.dumps(dict(code=code, msg=message, data=[])).encode()


class Status(Response):
    def __init__(self, body, code):
        super().__init__(body)
        self.code = code


class StatusOpener:
    def __init__(self, body, code):
        self.body, self.code, self.calls = body, code, []

    def open(self, request, timeout):
        self.calls.append(request)
        return Status(self.body, self.code)


class Failing:
    def __init__(self, error):
        self.error, self.calls = error, []

    def open(self, request, timeout):
        self.calls.append(request)
        raise self.error


def broadcaster(root, opener):
    client = Web3Broadcaster('fixture-key', 'fixture-secret', wallet=WALLET, artifacts=root, opener=opener)
    client.client.min_interval = 0
    return client


class RejectionClassification(unittest.TestCase):
    """Criterion 6: only a definite node rejection is `Rejected`, with a fixed reason and never the response text."""

    def test_definite_node_rejections(self):
        from larp.execution import Rejected
        cases = {
            'insufficient funds for gas * price + value: balance 0, tx cost 120000': 'INSUFFICIENT_FUNDS',
            'Insufficient funds for gas': 'INSUFFICIENT_FUNDS',
            'nonce too low: next nonce 7, tx nonce 6': 'NONCE_TOO_LOW',
            'intrinsic gas too low': 'INTRINSIC_GAS_TOO_LOW',
            'exceeds block gas limit': 'GAS_LIMIT_EXCEEDED',
            'invalid sender': 'INVALID_SENDER',
            'insufficient funds for gas; echo ' + RAW: 'INSUFFICIENT_FUNDS',
        }
        for message, reason in cases.items():
            with self.subTest(message=message), tempfile.TemporaryDirectory() as root:
                opener = Opener(rejection(message))
                with self.assertRaises(Rejected) as error:
                    broadcaster(root, opener).send(RAW)
                self.assertEqual((error.exception.reason, str(error.exception)), (reason, reason))
                self.assertEqual(len(opener.calls), 1)

    def test_ambiguous_outcomes_stay_unknown(self):
        from larp.execution import Rejected
        openers = {
            'already known': lambda: Opener(rejection('already known')),
            'known transaction': lambda: Opener(rejection('known transaction: 0x' + 'c' * 64)),
            'mixed known and rejected': lambda: Opener(rejection('insufficient funds; already known')),
            'unrecognised error': lambda: Opener(rejection('internal error')),
            'replacement underpriced': lambda: Opener(rejection('replacement transaction underpriced')),
            'success code with a rejection text': lambda: Opener(rejection('insufficient funds', code=0)),
            'rate limited': lambda: StatusOpener(rejection('insufficient funds', code=42900), 429),
            'not json': lambda: Opener(b'insufficient funds'),
            'timeout': lambda: Failing(TimeoutError()),
            'lost connection': lambda: Failing(ConnectionResetError()),
        }
        for name, make in openers.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                with self.assertRaises(DependencyUnavailable) as error:
                    broadcaster(root, make()).send(RAW)
                self.assertNotIsInstance(error.exception, Rejected)


class Submitting(FakeVenue):
    """FakeVenue whose broadcast goes through the real Web3Broadcaster and a fake HTTP opener."""

    def __init__(self, store, root):
        super().__init__(store)
        self.root, self.response, self.fault = root, rejection('insufficient funds for gas * price + value'), None

    def broadcast(self, signed, epoch, guard_version):
        self.store.check_authority(epoch, guard_version)
        self.broadcasts.append(signed.tx_hash)
        if self.fault:
            raise self.fault
        broadcaster(self.root, Opener(self.response)).send('0x' + signed.raw_hex)
        return signed.tx_hash


class RejectedBroadcast(DatabaseCase):
    """Criteria 7-8 on PostgreSQL: the `execution_wallet_barrier` index is the real one."""

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.registry = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.registry.install_test_schema()
        self.guards = ExecutionGuards(self.registry)
        self.venue = Submitting(self.registry, self.tmp.name)
        self.executor = Executor(self.registry, self.guards, self.venue, RegistrySigner(self.registry),
                                 FakeDecoder())
        self.observed = []
        self.owner = self.registry.execution_authority()[0]
        self.service = ExecutionService(store=self.store, executor=self.executor, mapping={},
                                        observe=self.observed.append, wallet_id='fake-wallet', epoch=self.owner,
                                        authority_version=self.owner, settlement=self.settlement)

    def settlement(self, state, attempt):
        return dict(schema='ExecutionObservation.v1', settlement='FINAL', kind='APPROVAL',
                    intent_id=state.intent.intent_id, attempt_id=attempt.attempt_id, tx_hash=attempt.tx_hash)

    def signed(self, **changes):
        i = intent(**changes)
        self.executor.create(i, 10)
        self.executor.prepare(i.key, 11)
        self.executor.authorize(i.key, 12)
        self.executor.sign(i.key, 13)
        return i.key

    def absent(self, attempt):
        self.venue.outcomes[attempt.tx_hash] = Outcome(attempt.tx_hash, None, None, 'UNKNOWN')

    def barrier_held(self):
        with self.assertRaises(Conflict):
            self.executor.create(intent(intent_id='next'), 300)

    def test_insufficient_funds_rejection_ends_not_submitted_and_frees_the_barrier(self):
        key = self.signed()
        state = self.executor.broadcast(key, 14)
        attempt = state.attempts[-1]
        self.assertEqual((attempt.state, attempt.broadcast_at, state.status), ('REJECTED', 14, 'ACTIVE'))
        self.assertEqual(state.blocked_reason, 'broadcast rejected: INSUFFICIENT_FUNDS')
        self.absent(attempt)
        self.assertEqual(self.executor.reconcile(key, 60).attempts[-1].state, 'REJECTED')  # before the timeout
        self.barrier_held()
        final = self.executor.reconcile(key, 14 + 120)
        self.assertEqual((final.attempts[-1].state, final.status), ('NOT_SUBMITTED', 'ABORTED'))
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT terminal FROM execution_records WHERE economic_key=%s',
                                        (key,)).fetchone(), (True,))
        self.assertEqual(self.executor.create(intent(intent_id='next'), 300).status, 'ACTIVE')
        with self.assertRaises(Conflict):  # the rejected bytes can never be released again
            self.registry.lookup(attempt.attempt_id, attempt.payload.hash)

    def test_not_submitted_fact_releases_the_reservation_and_no_broadcast_is_logged(self):
        key = self.signed()
        self.service.advance(key, 14)  # SIGNED_DURABLE -> broadcast, rejected
        self.absent(self.registry.load(key).attempts[-1])
        self.service.advance(key, 14 + 120)  # reconcile -> NOT_SUBMITTED
        loop = ExecutionLoop(store=self.store, registry=self.registry, service=self.service, run_id='run',
                             wallet=WALLET, epoch=self.owner)
        self.assertEqual(loop._unpublished_terminal(), [key])
        self.service.advance(key, 200)
        self.assertEqual(loop._unpublished_terminal(), [])
        kinds = [o['kind'] for o in self.observed]
        self.assertEqual(kinds, ['NOT_SUBMITTED'])
        self.assertEqual((self.observed[0]['reason'], self.observed[0]['intent_terminal']),
                         ('BROADCAST_REJECTED', True))

    def test_rejected_swap_after_a_final_approve(self):
        key = self.signed()
        self.venue.response = json.dumps(dict(code=0, data=[dict(txHash='0x' + 'c' * 64)])).encode()
        approve = self.executor.broadcast(key, 14).attempts[-1]
        self.assertEqual(approve.state, 'PENDING')
        self.venue.outcomes[approve.tx_hash] = finalized(approve)
        self.executor.reconcile(key, 17)
        self.guards.nonce = 1
        self.executor.prepare(key, 18)
        self.executor.authorize(key, 19)
        self.executor.sign(key, 20)
        self.venue.response = rejection('insufficient funds for gas * price + value')
        state = self.service.advance(key, 21)
        swap = state.attempts[-1]
        self.assertEqual((swap.step, swap.state), ('SWAP', 'REJECTED'))
        self.absent(swap)
        state = self.service.advance(key, 21 + 120)
        self.assertEqual((state.attempts[-1].state, state.status), ('NOT_SUBMITTED', 'ABORTED'))
        self.assertEqual(possible_swap_hashes(state), ())
        self.service.advance(key, 200)
        kinds = [o['kind'] for o in self.observed]
        self.assertNotIn('swap', [o.get('step') for o in self.observed if o['kind'] == 'BROADCAST_ATTEMPTED'])
        self.assertEqual(kinds.count('NOT_SUBMITTED'), 1)

    def test_rejected_record_stays_non_terminal_when_the_chain_disagrees(self):
        cases = {
            'nonce moved past the attempt': (lambda a: self.absent(a), 1, 'REJECTED'),
            'nonce unknown': (lambda a: self.absent(a), None, 'REJECTED'),
            'hash pending on chain': (lambda a: self.venue.outcomes.__setitem__(
                a.tx_hash, Outcome(a.tx_hash, WALLET, a.payload.nonce, 'PENDING')), 0, 'PENDING'),
            'hash found with no receipt': (lambda a: self.venue.outcomes.__setitem__(
                a.tx_hash, Outcome(a.tx_hash, WALLET, a.payload.nonce, 'UNKNOWN')), 0, 'UNKNOWN'),
        }
        for number, (name, (outcome, nonce, phase)) in enumerate(cases.items()):
            with self.subTest(name=name):
                key = self.signed(intent_id=f'case-{number}')
                attempt = self.executor.broadcast(key, 14).attempts[-1]
                self.assertEqual(attempt.state, 'REJECTED')
                outcome(attempt)
                self.guards.nonce = nonce
                state = self.executor.reconcile(key, 14 + 120)
                self.assertEqual((state.attempts[-1].state, state.status), (phase, 'ACTIVE'))
                self.guards.nonce = 0  # a new intent needs nonce evidence to reach the barrier
                self.barrier_held()
                self.venue.outcomes[attempt.tx_hash] = finalized(attempt)  # resolve it to free the barrier
                self.executor.reconcile(key, 14 + 240)
                self.executor.store.commit(*self.ended(key))

    def ended(self, key):
        state = self.registry.load(key)
        epoch, version = self.registry.authority()
        return state, replace(state, status='COMPLETED'), {'type': 'TEST_END'}, epoch, version

    def test_timeout_or_lost_response_stays_unknown_after_the_timeout(self):
        for number, fault in enumerate((TimeoutError(), ConnectionError())):
            with self.subTest(fault=type(fault).__name__):
                self.venue.fault = fault
                key = self.signed(intent_id=f'lost-{number}')
                attempt = self.executor.broadcast(key, 14).attempts[-1]
                self.assertEqual(attempt.state, 'UNKNOWN')
                self.absent(attempt)
                self.guards.nonce = 0
                state = self.executor.reconcile(key, 14 + 120)
                self.assertEqual((state.attempts[-1].state, state.status), ('UNKNOWN', 'ACTIVE'))
                self.assertEqual(state.blocked_reason, 'transaction unresolved')
                self.barrier_held()
                self.executor.store.commit(*self.ended(key))
        self.venue.fault = None

    def test_store_accepts_not_submitted_only_from_a_rejected_attempt(self):
        self.venue.fault = TimeoutError()
        key = self.signed()
        state = self.executor.broadcast(key, 14)
        epoch, version = self.registry.authority()
        forged = replace(state, status='ABORTED',
                         attempts=state.attempts[:-1] + (replace(state.attempts[-1], state='NOT_SUBMITTED'),))
        with self.assertRaises(Conflict):
            self.registry.commit(state, forged, {'type': 'NOT_SUBMITTED'}, epoch, version)
