"""D-DN-09 (IDEA-049-B, #34, #52): a HALT is split by reason.

CLOCK (and any unlisted reason) blocks every signature. DELIVERY_DEADLINE and REPEATED_FAILURES pause only new spending
and discretionary trades: a planned mandatory bStock SELL still executes under every existing check.
"""
import hashlib
import unittest

from larp.contracts import Document
from larp.execution import Conflict as SigningConflict, Intent, USDT
from larp.execution_live.loop import RunAuthorization
from larp.execution_live.store import ExecutionStore
from larp.integration.runtime import RuntimePlanner
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy
from larp.runtime.supervision import Guard
from larp.storage.postgres import Conflict, doc
from tests.execution_fixtures import ROUTER, TOKEN
from tests.runtime import test_round_driver_service as svc
from tests.support import DatabaseCase, request

RUN, VERSION, SECOND = svc.RUN, svc.VERSION, svc.SECOND
NOW = 1791590400000


def intent(intent_id, side='SELL', mandatory=True, kind=None):
    value = dict(intent_id=intent_id, side=side, mandatory=mandatory, symbol='NVDAB')
    if kind is not None:
        value['kind'] = kind
    return value


def projection(reasons):
    p = dict(round_records=dict(r=dict(plan=dict(intents=[
        intent('m'), intent('n', mandatory=False), intent('b', side='BUY'),
        intent('g', side='BUY', kind='GAS_TOP_UP'), intent('k', kind='GAS_TOP_UP')]))))
    if reasons:
        p['halt'] = dict(reasons={r: dict(since_ms=1, latched=r == 'CLOCK') for r in reasons})
    return p


class Permits(unittest.TestCase):
    """HS1: one shared helper decides what a HALT still allows."""

    def test_hs1_pausing_reasons_allow_only_planned_mandatory_bstock_sells(self):
        from larp.runtime.halts import permits
        for reasons in (['DELIVERY_DEADLINE'], ['REPEATED_FAILURES'], ['DELIVERY_DEADLINE', 'REPEATED_FAILURES']):
            with self.subTest(reasons=reasons):
                p = projection(reasons)
                self.assertTrue(permits(p, 'r', 'm'))
                for other in ('n', 'b', 'g', 'k', 'missing'):
                    self.assertFalse(permits(p, 'r', other), other)
                self.assertFalse(permits(p, 'other-round', 'm'))

    def test_hs1_clock_mixed_or_unknown_reasons_allow_nothing(self):
        from larp.runtime.halts import permits
        for reasons in (['CLOCK'], ['CLOCK', 'DELIVERY_DEADLINE'], ['SOMETHING_NEW'],
                        ['DELIVERY_DEADLINE', 'SOMETHING_NEW']):
            with self.subTest(reasons=reasons):
                self.assertFalse(permits(projection(reasons), 'r', 'm'))

    def test_hs1_no_halt_leaves_every_planned_intent_to_the_other_gates(self):
        from larp.runtime.halts import permits
        p = projection([])
        self.assertTrue(all(permits(p, 'r', i) for i in 'mnbgk'))


class MixedPlanner(RuntimePlanner):
    """The real plan plus a non-mandatory copy of its SELL: the coordinator must drop the copy under a pausing HALT."""

    def __init__(self):
        super().__init__(job_validity_ms=86_400_000, job_max_attempts=3)

    def plan(self, snapshot, proposal):
        p = super().plan(snapshot, proposal).read()
        if len(p['intents']) != 1 or p['intents'][0]['side'] != 'SELL':
            return Document.from_dict(p)
        [i] = p['intents']
        identity = hashlib.sha256((i['intent_id'] + 'optional').encode()).hexdigest()
        extra = dict(i, intent_id=identity, decision_id='decision:' + identity, mandatory=False)
        deltas = p['reservation_deltas'] + [dict(intent_id=identity, asset=i['symbol'], units=i['token_units'])]
        return Document.from_dict(dict(p, intents=[i, extra], reservation_deltas=deltas))


class Split(svc.ServiceHarness):
    def halt(self, reason):
        Guard(self.store, RUN, max_failures=3, clear_after=2)._halt(reason, self.w.clock(), {})

    def round(self):
        [(round_id, record)] = self.planned().items()
        return round_id, record

    # ---------------------------------------------------------------- HS2
    def test_hs2_a_pausing_halt_still_plans_the_mandatory_sell(self):
        driver = self.service_driver()
        self.halt('DELIVERY_DEADLINE')
        driver.once(self.w.clock())
        round_id, record = self.round()
        [i] = record['plan']['intents']
        self.assertEqual((i['side'], i['mandatory']), ('SELL', True))
        self.assertIn('HALTED:DELIVERY_DEADLINE', record['errors'])
        self.assertEqual(self.commands(), [i['intent_id']])

    def test_hs2_a_clock_halt_plans_nothing(self):
        driver = self.service_driver()
        self.halt('CLOCK')
        driver.once(self.w.clock())
        self.assertEqual(self.planned(), {})
        self.assertEqual(self.commands(), [])

    def test_hs2_non_mandatory_intents_and_their_reservations_are_dropped(self):
        driver = self.service_driver(planner=MixedPlanner())
        self.halt('REPEATED_FAILURES')
        driver.once(self.w.clock())
        round_id, record = self.round()
        [kept] = record['plan']['intents']
        self.assertTrue(kept['mandatory'])
        [dropped] = record['plan']['halt_dropped']
        self.assertNotEqual(dropped, kept['intent_id'])
        self.assertEqual(self.commands(), [kept['intent_id']])
        held = {r['intent_id'] for r in self.store.load(RUN).read()['reservations']}
        self.assertEqual(held, {kept['intent_id']})

    # ---------------------------------------------------------------- HS3 and HS4
    def planned_then_halted(self, reason):
        driver = self.service_driver()
        driver.once(self.w.clock())
        round_id, record = self.round()
        [i] = record['plan']['intents']
        self.halt(reason)
        return round_id, i

    # The HALT event is a commit, so a command planned before it must be reauthorized (PR #66 R3) before a claim; the
    # driver does that every cycle, before it offers commands.
    def test_hs3_claim_gate_and_driver_offer_the_mandatory_sell_under_a_pausing_halt(self):
        round_id, i = self.planned_then_halted('DELIVERY_DEADLINE')
        driver = self.service_driver()
        self.assertEqual(driver.execution.reauthorize(self.w.clock()), [i['intent_id']])
        self.assertEqual(driver.execution.waiting(self.w.clock()), [i['intent_id']])
        self.store.command(RUN, i['intent_id'], self.epoch, self.w.clock())

    def test_hs3_claim_gate_and_driver_offer_nothing_under_clock(self):
        round_id, i = self.planned_then_halted('CLOCK')
        driver = self.service_driver()
        self.assertEqual(driver.execution.reauthorize(self.w.clock()), [])
        self.assertEqual(driver.execution.waiting(self.w.clock()), [])
        with self.assertRaisesRegex(Conflict, 'halted'):  # the HALT gate itself, checked before the version
            self.store.command(RUN, i['intent_id'], self.epoch, self.w.clock())

    def signing_intent(self, round_id, i):
        return Intent(RUN, round_id, i['decision_id'], i['intent_id'], VERSION, i['intent_id'], self.wallet, TOKEN,
                      USDT, 2000, 1, ROUTER, i['expires_ms'] // 1000, 2000, 1, 5000)

    def run_row(self):
        current = self.store.load(RUN).read()
        return dict(projection=doc(current['projection']).payload, mode='offline', wallet_id=self.wallet)

    def test_hs4_signing_gates_allow_the_mandatory_sell_under_a_pausing_halt(self):
        round_id, i = self.planned_then_halted('DELIVERY_DEADLINE')
        signing = self.signing_intent(round_id, i)
        facts = RunAuthorization(self.store, run_id=RUN, build_id=VERSION).facts(signing, self.w.clock() // SECOND)
        self.assertTrue(facts['risk_valid'])
        ExecutionStore.check_signing_run(self.run_row(), signing)  # no Conflict

    def test_hs4_signing_gates_refuse_under_clock(self):
        round_id, i = self.planned_then_halted('CLOCK')
        signing = self.signing_intent(round_id, i)
        facts = RunAuthorization(self.store, run_id=RUN, build_id=VERSION).facts(signing, self.w.clock() // SECOND)
        self.assertFalse(facts['risk_valid'])
        with self.assertRaises(SigningConflict):
            ExecutionStore.check_signing_run(self.run_row(), signing)

    # ---------------------------------------------------------------- HS5
    def approved(self, execution):
        return any(a.step == 'APPROVE' and a.state == 'FINAL_SUCCESS'
                   for k in self.keys() for a in execution.registry.load(k).attempts)

    def test_hs5_a_delivery_halt_after_the_approval_lets_the_mandatory_sell_finish(self):
        driver = self.service_driver()
        execution = svc.Execution(self, remote=False)
        execution.venue.finalize = True
        driver.once(self.w.clock())
        [round_id] = self.planned()
        self.assertTrue(self.run_both(driver, execution, until=lambda: self.approved(execution)))
        self.halt('DELIVERY_DEADLINE')
        self.assertTrue(self.run_both(driver, execution, ticks=90, until=lambda: self.closed(round_id)))
        [key] = self.keys()
        self.assertEqual([a.step for a in execution.registry.load(key).attempts], ['APPROVE', 'SWAP'])
        self.assertEqual(len(execution.venue.broadcasts), 2)
        self.assertEqual(self.store.load(RUN).read()['projection']['portfolio']['positions']['NVDAB']['units'], 0)


class ClaimGate(DatabaseCase):
    def test_hs3_a_pending_buy_is_refused_under_a_pausing_halt(self):
        c = Coordinator(self.store, FakeAssessor(), FakePolicy(), FakePlanner(), execution=FakeExecution(),
                        run_id='run', version_id='synthetic', profile_hash='a' * 64, address='0x' + '1' * 40,
                        clock_ms=lambda: NOW)
        c.start('r1', request('BUY'), NOW)
        command_id = self.store.load('run').read()['projection']['round_records']['r1']['plan']['intents'][0]['intent_id']
        Guard(self.store, 'run', max_failures=3, clear_after=2)._halt('DELIVERY_DEADLINE', NOW, {})
        with self.assertRaisesRegex(Conflict, 'halted'):  # the HALT gate itself, checked before the version
            self.store.command('run', command_id, self.epoch, NOW)


if __name__ == '__main__':
    unittest.main()
