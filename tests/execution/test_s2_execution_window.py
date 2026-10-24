"""IDEA-089 S2-8: KIT_OPEN_STATE hours on the execution side: the signer's and the execution service's own
`permitted` checks accept a weekend leg until the next session opens. Synthetic store and signer; no keys or network."""
from unittest.mock import patch

from larp.execution import Executor
from larp.execution_live.service import ExecutionService
from larp.execution_live.store import ExecutionStore
from larp.strategy.execution_bounds import permitted
from tests.execution.test_execution_bounds import record_in, short_record
from tests.execution.test_postgres_execution import ExecutionGuards, RegistrySigner
from tests.execution_fixtures import FakeDecoder, FakeVenue, WALLET, intent
from tests.signer.test_service import SigningCase as _SigningCase
from tests.support import DatabaseCase


def weekend_record(hours):
    """Session open 0 s, close 5 s, next open 200 s; `hours` None is today's NYSE interval."""
    record = short_record()
    context = record['policy_input']['context']
    context['execution_session'].update(close_ms=5000)
    end = 5000
    if hours is not None:
        context['profile']['s1']['execution']['hours'] = hours
        end = 200000 if hours == 'KIT_OPEN_STATE' else 5000
    record['plan']['intents'][0]['execution_bounds'].update(valid_until_ms=end)
    return record


class OpenStateSigner(_SigningCase):
    def sign_at(self, hours, now):
        state, attempt = self.authorized(amount=100*10**12)
        record_in(self.store, weekend_record(hours))
        request_id, _ = self.request(state, attempt)
        self.signer_now = now
        with patch.object(self.service.signer.account, 'sign_transaction',
                          wraps=self.service.signer.account.sign_transaction) as sign:
            self.service.once()
        return request_id, sign

    def test_signer_signs_a_weekend_leg_after_the_close(self):
        _, sign = self.sign_at('KIT_OPEN_STATE', 12)
        sign.assert_called_once()
        self.assertEqual(len(self.signatures()), 1)

    def test_signer_refuses_the_same_leg_under_nyse_hours(self):
        request_id, sign = self.sign_at(None, 12)
        sign.assert_not_called()
        self.assertIn('S1 execution window/attempt authority expired', self.refusals()[request_id])

    def test_signer_refuses_a_weekend_leg_at_the_next_open(self):
        request_id, sign = self.sign_at('KIT_OPEN_STATE', 200)
        sign.assert_not_called()
        self.assertIn('S1 execution window/attempt authority expired', self.refusals()[request_id])


class OpenStateExecution(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.registry = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.executor = Executor(self.registry, ExecutionGuards(self.registry), FakeVenue(self.registry),
                                 RegistrySigner(self.registry), FakeDecoder())
        self.i = intent(amount=100*10**12)
        self.executor.create(self.i, 1)
        self.service = ExecutionService(store=self.store, executor=self.executor, mapping={}, observe=lambda e: None,
            wallet_id=WALLET, epoch=self.epoch, authority_version=self.epoch,
            admission=lambda i, now: permitted(self.store.load('run').read()['projection'], i, now*1000))

    def test_admission_holds_until_the_next_open_then_aborts(self):
        record_in(self.store, weekend_record('KIT_OPEN_STATE'))
        self.assertNotEqual(self.service.advance(self.i.key, 100).status, 'ABORTED')
        self.assertEqual(self.service.advance(self.i.key, 200).status, 'ABORTED')

    def test_nyse_hours_abort_after_the_close(self):
        record_in(self.store, weekend_record(None))
        self.assertEqual(self.service.advance(self.i.key, 12).status, 'ABORTED')
