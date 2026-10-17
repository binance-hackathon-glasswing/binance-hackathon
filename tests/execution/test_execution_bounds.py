"""IDEA-076 EB4: independent signer, durable release and unbroadcast revocation."""
from unittest.mock import Mock, patch

from larp.execution import Conflict, Executor
from larp.execution_live.loop import FencedRelease, RunAuthorization
from larp.execution_live.service import ExecutionService
from larp.execution_live.store import ExecutionStore
from larp.runtime.coordinator import batch_for
from larp.strategy.execution_bounds import permitted
from tests.execution.test_postgres_execution import ExecutionGuards, RegistrySigner
from tests.execution_fixtures import FakeDecoder, FakeVenue, WALLET, finalized, intent
from tests.signer.test_service import SigningCase as _SigningCase
from tests.strategy.test_execution_bounds import round_record
from tests.support import DatabaseCase


def short_record():
    record = round_record()
    context = record['policy_input']['context']
    context['profile']['s1']['execution'].update(open_delay_seconds=0, close_buffer_seconds=0)
    context['execution_session'].update(open_ms=0, close_ms=100000, next_open_ms=200000)
    record['plan']['intents'][0]['execution_bounds'].update(valid_from_ms=0, valid_until_ms=100000)
    return record


def record_in(store, record):
    current = store.load('run')
    projection = current.read()['projection']
    projection['round_records'] = {'round': record}
    projection['execution_attempt_budget'] = record['plan']['execution_attempt_budget']
    store.commit(batch_for(current, 'bounds-fixture', dict(kind='SYNTHETIC'), projection=projection))


class SignerWindow(_SigningCase):
    def test_expired_window_refuses_even_when_primary_supplies_true_gates(self):
        state, attempt = self.authorized()
        record_in(self.store, short_record())
        request_id, request = self.request(state, attempt)
        self.assertTrue(request['gates']['risk_valid'])
        self.signer_now = 100
        with patch.object(self.service.signer.account, 'sign_transaction',
                          wraps=self.service.signer.account.sign_transaction) as sign:
            self.service.once()
        sign.assert_not_called()
        self.assertFalse(self.signatures())
        self.assertIn('S1 execution window/attempt authority expired', self.refusals()[request_id])

    def test_window_check_accepts_in_window_request_without_changing_policy(self):
        state, attempt = self.authorized()
        record_in(self.store, short_record())
        self.request(state, attempt)
        self.service.once()
        self.assertEqual(len(self.signatures()), 1)


class ExecutionWindow(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.registry = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.guards = ExecutionGuards(self.registry)
        self.venue = FakeVenue(self.registry)
        self.executor = Executor(self.registry, self.guards, self.venue, RegistrySigner(self.registry), FakeDecoder())
        self.i = intent()
        self.executor.create(self.i, 10)
        record_in(self.store, short_record())
        self.seen = []
        self.service = ExecutionService(store=self.store, executor=self.executor, mapping={}, observe=self.seen.append,
            wallet_id=WALLET, epoch=self.epoch, authority_version=self.epoch,
            admission=lambda i, now: permitted(self.store.load('run').read()['projection'], i, now*1000))

    def sign(self):
        self.executor.prepare(self.i.key, 11)
        self.executor.authorize(self.i.key, 12)
        return self.executor.sign(self.i.key, 13)

    def test_unsigned_work_aborts_when_window_closes_and_keeps_its_attempt_count(self):
        self.assertEqual(self.service.advance(self.i.key, 100).status, 'ABORTED')
        self.assertFalse(self.venue.broadcasts)
        state = ExecutionStore(self.store, run_id='run', wallet=WALLET).load(self.i.key)
        self.assertEqual(state.status, 'ABORTED')
        self.assertEqual(self.store.load('run').read()['projection']['execution_attempt_budget']['counts'],
                         {'DISCRETIONARY:BUY:NVDAB': 1})
        self.service.advance(self.i.key, 101)
        self.assertEqual(self.seen[-1]['kind'], 'NOT_SUBMITTED')

    def test_signed_but_unsent_work_is_revoked_at_boundary(self):
        signed = self.sign()
        self.assertEqual(signed.attempts[-1].state, 'SIGNED_DURABLE')
        aborted = self.service.advance(self.i.key, 100)
        self.assertEqual((aborted.status, aborted.attempts[-1].state), ('ABORTED', 'ABORTED'))
        self.assertFalse(self.venue.broadcasts)
        with self.assertRaises(Conflict):
            self.registry.lookup(signed.attempts[-1].attempt_id, signed.attempts[-1].payload.hash)

    def test_release_rechecks_current_time_after_broadcast_intent_is_durable(self):
        signed = self.sign()
        self.executor.broadcast(self.i.key, 14)
        attempt = signed.attempts[-1]
        bytes_to_send = self.registry.lookup(attempt.attempt_id, attempt.payload.hash)
        submitter = Mock()
        release = FencedRelease(self.registry, submitter, clock_s=lambda: 100)
        with self.assertRaisesRegex(Conflict, 'S1 execution window/attempt authority expired'):
            release(bytes_to_send, self.epoch, self.epoch)
        submitter.send.assert_not_called()

    def test_pending_submission_reconciles_after_the_window_and_never_resends(self):
        self.sign()
        sent = self.executor.broadcast(self.i.key, 14)
        result = self.service.advance(self.i.key, 100)
        self.assertNotEqual(result.status, 'ABORTED')
        self.assertEqual(len(self.venue.broadcasts), 1)
        a = sent.attempts[-1]
        self.venue.outcomes[a.tx_hash] = finalized(a)
        result = self.service.advance(self.i.key, 105)
        self.assertEqual(result.attempts[-1].state, 'FINAL_SUCCESS')
        self.assertEqual(len(self.venue.broadcasts), 1)

