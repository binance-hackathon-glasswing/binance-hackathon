"""#27 / C-OPEN-003 Option A finite execution authority (IDEA-049-C LD04, criteria A1-A8).

Synthetic profiles, fake execution ports and a virtual clock. The L/m values used here are test values, not the
adopted settings: those wait for measured host timings (LD02).
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import tempfile
from pathlib import Path
import unittest

from larp.contracts import ContractError
from larp.execution import Blocked, Executor, Gates, Payload, SwapEconomics, canonical, validate_payload
from larp.execution_live.service import map_command
from larp.integration.runtime import RuntimePlanner
from larp.marketdata.port import TOKENS
from larp.ports import validate_execution_request
from larp.research.fixtures import snapshot, with_quotes
from larp.strategy.policy import decide
from larp.strategy.schema import execution_authority
from tests.execution_fixtures import (FakeDecoder, FakeGuards, FakeSigner, FakeVenue, SQLiteFixture, finalized,
                                      intent)
from tests.support import DatabaseCase

NOW = datetime(2026, 10, 10, 14, tzinfo=timezone.utc)
FINITE = dict(execution_authority_seconds=120, submission_margin_seconds=10)


def ms(when):
    return int(when.timestamp() * 1000)


def planned(*, now=NOW, held=None, changes=None):
    s = with_quotes(snapshot(now=now, held=held, profile_changes=changes))
    proposal = decide(s, s.policy_state)
    rp = RuntimePlanner(job_validity_ms=60_000, job_max_attempts=3)
    first, second = rp.plan(s, proposal), rp.plan(s, proposal)
    return s, proposal, first, second


class Planner(unittest.TestCase):  # A1-A3
    def test_a1_without_settings_the_plan_is_unchanged(self):
        s, proposal, plan, _ = planned()
        for i in plan.read()['intents']:
            self.assertNotIn('authority', i)
            if not i['mandatory']:
                self.assertLessEqual(i['expires_ms'], ms(proposal.valid_until))

    def test_a2_a3_finite_authority_replaces_the_proposal_and_quote_bound(self):
        s, proposal, plan, again = planned(changes=FINITE)
        self.assertEqual(plan.payload, again.payload)  # replanning the same snapshot is byte-identical
        intents = plan.read()['intents']
        self.assertTrue(intents)
        for i in intents:
            a = i['authority']
            self.assertEqual(i['expires_ms'], ms(NOW) + 120_000)
            self.assertGreater(i['expires_ms'], ms(proposal.valid_until))
            self.assertGreater(i['expires_ms'], ms(datetime.fromisoformat(i['quote_expiry'])))
            self.assertEqual(a, dict(decision_ms=ms(NOW), proposal_expires_ms=ms(proposal.valid_until),
                                     authority_ms=i['expires_ms'], authority_seconds=120, margin_seconds=10))

    def test_signing_end_caps_mandatory_exit_authority(self):
        end = datetime(2026, 10, 22, tzinfo=timezone.utc)
        _, _, plan, _ = planned(now=end - timedelta(seconds=60), held={'NVDAB': 15_000}, changes=FINITE)
        intents = plan.read()['intents']
        self.assertTrue(intents)
        self.assertTrue(all(i['mandatory'] and i['side'] == 'SELL' for i in intents))
        self.assertEqual({i['expires_ms'] for i in intents}, {ms(end)})

    def test_s1_window_caps_finite_authority(self):
        from tests.strategy.test_execution_bounds import at
        s = with_quotes(at('2026-10-10T19:44:00Z', profile_changes=FINITE))
        plan = RuntimePlanner(job_validity_ms=60_000, job_max_attempts=3).plan(s, decide(s, s.policy_state))
        intents = plan.read()['intents']
        self.assertTrue(intents)
        end = ms(NOW.replace(hour=19, minute=45))
        self.assertEqual({i['expires_ms'] for i in intents}, {end})
        self.assertTrue(all(i['authority']['authority_ms'] == i['execution_bounds']['valid_until_ms']
                            for i in intents))

    def test_a2_new_risk_end_caps_a_discretionary_buy_but_not_a_mandatory_sell(self):
        end = datetime(2026, 10, 20, tzinfo=timezone.utc)  # the fixture profile's new_risk_end
        buy_time = end - timedelta(seconds=60)
        _, _, plan, _ = planned(now=buy_time, changes=FINITE)
        buys = [i for i in plan.read()['intents'] if i['side'] == 'BUY' and not i['mandatory']]
        self.assertTrue(buys)
        self.assertEqual({i['expires_ms'] for i in buys}, {ms(end)})
        _, _, plan, _ = planned(now=end + timedelta(hours=1), held={'NVDAB': 15_000}, changes=FINITE)
        sells = [i for i in plan.read()['intents'] if i['side'] == 'SELL' and i['mandatory']]
        self.assertTrue(sells)
        self.assertEqual({i['expires_ms'] for i in sells}, {ms(end + timedelta(hours=1)) + 120_000})


def command_for(i):
    return dict(kind='EXECUTION_REQUEST', command_id=i['intent_id'], round_id='round', decision_id=i['decision_id'],
                expires_ms=i['expires_ms'], payload=i)


class Command(unittest.TestCase):  # A4
    def setUp(self):
        _, _, plan, _ = planned(changes=FINITE)
        self.intent = next(i for i in plan.read()['intents'] if i['symbol'] in TOKENS)

    def test_a4_schema_binds_authority_to_expiry(self):
        validate_execution_request(command_for(self.intent))
        broken = {
            'other end': dict(self.intent['authority'], authority_ms=self.intent['expires_ms'] + 1),
            'margin above lifetime': dict(self.intent['authority'], margin_seconds=120),
            'end beyond lifetime': dict(self.intent['authority'], authority_seconds=1),
            'missing field': {k: v for k, v in self.intent['authority'].items() if k != 'decision_ms'},
            'not an object': 'A',
        }
        for name, authority in broken.items():
            with self.subTest(name), self.assertRaises(ContractError):
                validate_execution_request(command_for(dict(self.intent, authority=authority)))

    def test_a4_mapping_carries_the_planned_end_and_margin_across_restart(self):
        def mapped():
            return map_command(command_for(self.intent), run_id='run', wallet='0x' + '1' * 40, version_id='v',
                               router='0x' + '2' * 40, token_decimals={s: 4 for s in TOKENS},
                               limits=dict(per_trade_cap_units=10**12, max_gas=10**6, max_gas_price=10,
                                           gas_budget=10**18),
                               now_ms=ms(NOW))
        first, second = mapped(), mapped()
        self.assertEqual(first, second)
        self.assertEqual((first.valid_until, first.authority_margin), (self.intent['expires_ms'] // 1000, 10))


def gates(now):
    return Gates(1, 1, 0, now, now + 30, audit_durable=True, reservation_valid=True, version_valid=True,
                 risk_valid=True, health_valid=True, token_market_open=True, underlying_market_open=True,
                 clock_trusted=True)


def fake_swap(i, deadline, nonce=0):
    economics = SwapEconomics(i.pay_token, i.receive_token, i.amount, i.wallet, i.minimum_output, deadline, 0)
    return Payload(56, i.wallet, i.router, 0, nonce, 100000, 1, '0xfafafafa' + canonical(economics.__dict__).encode().hex())


class Payloads(unittest.TestCase):  # A5, A7 (the signer runs this same validate_payload on the stored intent)
    def test_local_signer_refuses_both_margins_before_signing(self):
        from unittest.mock import Mock
        from larp.signer.local import LocalSigner
        from tests.signer.test_local import Registry
        i = intent(valid_until=1060, authority_margin=5)
        for now, deadline in ((1055, 1059), (1026, 1030)):
            with self.subTest(now=now, deadline=deadline):
                account, registry = Mock(address=i.wallet), Registry()
                signer = LocalSigner(account=account, expected_address=i.wallet, registry=registry,
                                     authorization=lambda *args: (i, 'SWAP', gates(now), now, FakeDecoder()),
                                     signer_host=True)
                with self.assertRaises(Blocked):
                    signer.sign('margin-refusal', fake_swap(i, deadline), 1, 1)
                account.sign_transaction.assert_not_called()
                self.assertEqual(registry.rows, {})

    def test_a5_margin_bounds_steps_and_deadlines(self):
        i = intent(valid_until=1060, authority_margin=5)
        decoder = FakeDecoder()
        validate_payload(i, 'SWAP', fake_swap(i, 1030), gates(1000), 1000, decoder)
        for name, now, deadline in (('deadline inside the margin', 1026, 1030), ('deadline after A', 1000, 1061),
                                    ('no margin left before A', 1055, 1059)):
            with self.subTest(name), self.assertRaises(Blocked):
                validate_payload(i, 'SWAP', fake_swap(i, deadline), gates(now), now, decoder)

    def test_a5_zero_margin_is_the_existing_rule(self):
        i = intent(valid_until=1060)
        validate_payload(i, 'SWAP', fake_swap(i, 1030), gates(1029), 1029, FakeDecoder())
        with self.assertRaises(Blocked):
            validate_payload(i, 'SWAP', fake_swap(i, 1030), gates(1030), 1030, FakeDecoder())


class Sequence(unittest.TestCase):  # A6: 15 s proposal, deadline 30 s after each quote, L=60, m=5
    T0 = 1000

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'fixture.sqlite'
        self.economic = intent(valid_until=self.T0 + 60, authority_margin=5)
        self.key = self.economic.key
        self.attach()

    def attach(self):
        self.store = SQLiteFixture(self.path)
        self.addCleanup(self.store.close)
        self.guards, self.venue = FakeGuards(self.store), FakeVenue(self.store)
        self.engine = Executor(self.store, self.guards, self.venue, FakeSigner(self.store), FakeDecoder())
        self.now = self.T0
        # Each quote's route deadline is 30 s after the quote, as the venue would encode it.
        self.venue.quote_mutation = lambda payload: fake_swap(self.economic, self.now + 30, payload.nonce)

    def at(self, now):
        self.now = now
        return now

    def approve(self, final_at):
        self.engine.create(self.economic, self.at(self.T0))
        self.engine.prepare(self.key, self.T0)
        self.engine.authorize(self.key, self.T0)
        self.engine.sign(self.key, self.T0)
        state = self.engine.broadcast(self.key, self.T0 + 1)
        self.venue.outcomes[state.attempts[-1].tx_hash] = finalized(state.attempts[-1])
        self.engine.reconcile(self.key, self.at(final_at))
        self.guards.nonce = 1

    def test_a6_approve_finality_requote_and_sign_fit_the_authority(self):
        self.approve(final_at=self.T0 + 10)
        state = self.engine.prepare(self.key, self.at(self.T0 + 10))  # re-quote deadline T0+40 <= A=T0+60
        self.assertEqual(state.attempts[-1].step, 'SWAP')
        self.engine.authorize(self.key, self.T0 + 10)
        state = self.engine.sign(self.key, self.T0 + 11)
        self.assertEqual(state.attempts[-1].state, 'SIGNED_DURABLE')

    def test_a6_late_requote_restart_and_late_approval(self):
        self.approve(final_at=self.T0 + 35)
        self.attach()  # restart: the stored intent keeps A = T0 + 60
        self.assertEqual(self.store.load(self.key).intent.valid_until, self.T0 + 60)
        state = self.engine.prepare(self.key, self.at(self.T0 + 35))  # re-quote deadline T0+65 > A
        self.assertIn('expired', state.blocked_reason)
        self.assertEqual(state.attempts[-1].step, 'APPROVE')
        state = self.engine.prepare(self.key, self.at(self.T0 + 56))  # now + m >= A: no time left
        self.assertIn('margin', state.blocked_reason)


class Profile(unittest.TestCase):  # A8
    def test_a8_settings_validation(self):
        base = dict(proposal_seconds=15)
        self.assertIsNone(execution_authority(base))
        self.assertEqual(execution_authority(dict(base, **FINITE)), (120, 10))
        for name, values in (('one setting', dict(execution_authority_seconds=120)),
                             ('margin not below L', dict(execution_authority_seconds=60, submission_margin_seconds=60)),
                             ('L below proposal', dict(execution_authority_seconds=10, submission_margin_seconds=5)),
                             ('L above one hour', dict(execution_authority_seconds=3601, submission_margin_seconds=5)),
                             ('not integers', dict(execution_authority_seconds=120.0, submission_margin_seconds=5))):
            with self.subTest(name), self.assertRaises(ContractError):
                execution_authority(dict(base, **values))
        with self.assertRaises(ContractError):  # the full profile validator applies it too
            planned(changes=dict(execution_authority_seconds=120))


class ReleaseAuthority(DatabaseCase):
    def setUp(self):
        super().setUp()
        from tests.execution.test_postgres_execution import ExecutionGuards, RegistrySigner
        from larp.execution_live.store import ExecutionStore
        self.registry = ExecutionStore(self.store, run_id='run', wallet=intent().wallet)
        self.guards = ExecutionGuards(self.registry)
        self.venue = FakeVenue(self.registry)
        self.engine = Executor(self.registry, self.guards, self.venue, RegistrySigner(self.registry), FakeDecoder())
        self.i = intent(amount=100 * 10**12, valid_until=100, authority_margin=5)
        self.engine.create(self.i, 10)
        self.engine.prepare(self.i.key, 11)
        self.engine.authorize(self.i.key, 12)
        self.engine.sign(self.i.key, 13)

    def test_release_rechecks_margin_after_the_durable_possible_send_write(self):
        from unittest.mock import Mock
        from larp.execution import Conflict
        from larp.execution_live.loop import FencedRelease
        submitter = Mock()
        self.venue.broadcast = FencedRelease(self.registry, submitter, clock_s=lambda: 95)
        with self.assertRaises(Conflict):
            self.engine.broadcast(self.i.key, 14)
        submitter.send.assert_not_called()
        state = self.registry.load(self.i.key)
        self.assertEqual(state.attempts[-1].state, 'BROADCAST_ATTEMPTED')
        self.assertIsNotNone(self.registry.lookup(state.attempts[-1].attempt_id, state.attempts[-1].payload.hash))

    def test_finite_release_requires_a_current_clock(self):
        from unittest.mock import Mock
        from larp.execution import Conflict
        from larp.execution_live.loop import FencedRelease
        submitter = Mock()
        self.venue.broadcast = FencedRelease(self.registry, submitter)
        with self.assertRaises(Conflict):
            self.engine.broadcast(self.i.key, 14)
        submitter.send.assert_not_called()

    def swap_ready(self):
        sent = self.engine.broadcast(self.i.key, 14)
        self.venue.outcomes[sent.attempts[-1].tx_hash] = finalized(sent.attempts[-1])
        self.engine.reconcile(self.i.key, 15)
        self.guards.nonce = 1
        self.venue.quote_mutation = lambda payload: fake_swap(self.i, 50, payload.nonce)
        self.engine.prepare(self.i.key, 16)
        self.engine.authorize(self.i.key, 17)
        return self.engine.sign(self.i.key, 18)

    def test_swap_release_checks_decoded_deadline_with_fresh_clock(self):
        from unittest.mock import Mock
        from larp.execution import Conflict
        from larp.execution_live.loop import FencedRelease
        self.swap_ready()
        submitter = Mock()
        self.venue.broadcast = FencedRelease(self.registry, submitter, clock_s=lambda: 45, decoder=FakeDecoder())
        with self.assertRaisesRegex(Conflict, 'deadline submission margin'):
            self.engine.broadcast(self.i.key, 19)  # tick fits; fresh release clock exhausts route margin
        submitter.send.assert_not_called()
        self.assertEqual(self.registry.load(self.i.key).attempts[-1].state, 'BROADCAST_ATTEMPTED')

    def test_swap_release_inside_both_margins_sends_exact_bytes(self):
        from unittest.mock import Mock
        from larp.execution_live.loop import FencedRelease
        state = self.swap_ready()
        submitter = Mock()
        submitter.send.return_value = state.attempts[-1].tx_hash
        self.venue.broadcast = FencedRelease(self.registry, submitter, clock_s=lambda: 44, decoder=FakeDecoder())
        result = self.engine.broadcast(self.i.key, 19)
        self.assertEqual(result.attempts[-1].state, 'PENDING')
        submitter.send.assert_called_once_with(state.attempts[-1].raw_hex)


if __name__ == '__main__':
    unittest.main()
