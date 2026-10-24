"""IDEA-090 F1-F5 (S2-F2): a planner decision round in every cadence slot, independent of evidence.

Before the fix, `EvidenceWork._cadence` made no round in a slot whose rotating issuer had no evidence records, so in
runs 2-4 the planner could act in only 2 of every 5 slots. Real components as in IDEA-048's driver tests; external
ports synthetic, nothing signed.
"""
import unittest

from larp.intelligence.scenarios import EXMEM, EXSEMI
from larp.integration.replay import replay_live
from larp.integration.runtime import RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection
from larp.integration.settlement import ExecutionBridge, settle
from larp.research.fixtures import with_quotes
from larp.runtime.driver import digest
from larp.storage.postgres import doc
from tests.integration import test_evidence_pipeline as pipeline
from tests.runtime.test_driver import HOUR, RUN, DriverHarness
from tests.strategy.test_execution_bounds import at, run

# Two of five issuers have records, as in runs 2-4; the other three never do.
FIVE = (EXSEMI, EXMEM, 'FIXTURE-CIK-9900003', 'FIXTURE-CIK-9900004', 'FIXTURE-CIK-9900005')


class EverySlot(DriverHarness):
    def record(self, round_id):
        return self.store.event(RUN, 'plan:' + round_id)['record']

    def drain(self, driver):
        """Run the pending filing rounds first, so later ticks are cadence work."""
        for _ in range(10):
            summary = self.tick(driver)
            if not (summary['round_id'] or '').startswith('filing:'):
                return
        self.fail('filing rounds did not drain')

    def slot_round(self, driver, slot):
        self.w.clock.now = slot * HOUR
        summary = self.tick(driver)
        return summary['round_id']

    def first_slot(self, divisor):
        slot = self.w.clock() // HOUR + 2
        return slot + (-slot) % divisor  # slot % divisor == 0

    def test_f1_a_planning_round_in_every_slot_with_records_for_two_of_five_issuers(self):
        self.world(['EXSEMI_Q2_8K', 'EXMEM_Q3_6K'])
        driver = self.driver(issuers=FIVE)
        self.drain(driver)
        start = self.first_slot(5)
        for slot in range(start, start + 10):
            with self.subTest(slot=slot):
                round_id = self.slot_round(driver, slot)
                self.assertEqual(round_id, f'cadence:{slot}#1')
                record = self.record(round_id)
                issuer = FIVE[slot % 5]
                self.assertEqual(record['request']['issuer_id'], issuer)
                if issuer in (EXSEMI, EXMEM):  # an evidence round, as before
                    self.assertNotIn('accepted_evidence', record)
                    self.assertTrue(record['request']['evidence_refs'])
                else:  # planning only: prior accepted evidence, no new assessment and no assessment error
                    self.assertEqual(record['accepted_evidence'], 'ONLY')
                    self.assertIsNone(record['assessment'])
                    self.assertEqual(record['request']['evidence_refs'], [])
                    self.assertNotIn('ASSESSMENT_UNAVAILABLE', record['errors'])
                    self.assertIsNotNone(record['proposal_id'])  # the policy ran
        self.assertFalse(self.store.open_rounds(RUN))

    def test_f2_slots_whose_issuer_has_records_keep_todays_round(self):
        self.world(['EXSEMI_Q2_8K', 'EXMEM_Q3_6K'])
        driver = self.driver(issuers=(EXSEMI, EXMEM))
        self.drain(driver)
        start = self.first_slot(2)
        for slot in (start, start + 1):
            round_id = self.slot_round(driver, slot)
            self.assertEqual(round_id, f'cadence:{slot}#1')
            record = self.record(round_id)
            payload = dict(kind='REASSESS_ISSUER', issuer_id=(EXSEMI, EXMEM)[slot % 2], reason='SCHEDULED_CADENCE',
                           slot=slot)
            self.assertEqual(record['request']['job_id'],
                             'evidence:' + digest('larp.runtime.cadence-job.v1', payload))
            self.assertNotIn('accepted_evidence', record)
            self.assertIsNotNone(record['assessment'])

    def test_f3_a_mandatory_sell_is_planned_in_a_slot_whose_issuer_has_no_records(self):
        self.world(['EXSEMI_402_8K'])
        driver = self.driver('MANDATORY_REDUCTION', issuers=(EXSEMI, EXMEM))
        first = self.tick(driver)  # the 4.02 filing: its accepted falsifier makes the reduction mandatory
        self.assertTrue(first['round_id'].startswith('filing:'))
        slot = self.first_slot(2) + 1  # EXMEM's slot: EXMEM has no records
        round_id = self.slot_round(driver, slot)
        self.assertEqual(round_id, f'cadence:{slot}#1')
        record = self.record(round_id)
        self.assertEqual(record['accepted_evidence'], 'ONLY')
        sells = [i for i in record['plan']['intents'] if i['side'] == 'SELL' and i['mandatory']]
        self.assertTrue(sells, record['plan'])

    def test_f4_one_round_per_slot_across_ticks_and_restart_and_the_journal_replays(self):
        self.world(['EXSEMI_Q2_8K'])
        driver = self.driver('MANDATORY_REDUCTION', issuers=(EXSEMI, EXMEM))
        self.drain(driver)
        slot = self.first_slot(2) + 1  # EXMEM: planning only
        self.assertEqual(self.slot_round(driver, slot), f'cadence:{slot}#1')
        self.assertIsNone(self.tick(driver)['round_id'])  # same slot
        self.assertIsNone(self.tick(self.driver('MANDATORY_REDUCTION', issuers=(EXSEMI, EXMEM)))['round_id'])
        self.assertEqual(self.slot_round(driver, slot + 1), f'cadence:{slot + 1}#1')  # EXSEMI: evidence round
        self.assertEqual(self.slot_round(driver, slot + 2), f'cadence:{slot + 2}#1')
        mine = [r for r in self.logs() if r.startswith('cadence:') and int(r[8:].split('#')[0]) >= slot]
        self.assertEqual(mine, [f'cadence:{s}#1' for s in (slot, slot + 1, slot + 2)])
        journal, expected = self.store.journal(RUN), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        builder = driver.coordinator.context_builder
        dead = lambda *a: (_ for _ in ()).throw(AssertionError('live port called in replay'))
        builder.market = builder.health = builder.calendar = dead
        head = replay_live(journal, doc(initial_projection(pipeline.pipeline_ledger())), self.store, builder=builder,
                           run_id=RUN, wallet_id='fake-wallet', chain_id=56, version_id='integration-fixture',
                           profile_hash=self.h, address='0x' + '1' * 40, policy=StrategyPolicy(),
                           planner=RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                           execution=ExecutionBridge(), reducer=settle,
                           initial_policy_state=initial_policy_state(RUN, self.profile))
        self.assertEqual(head, expected)

    def test_f4_an_interrupted_planning_round_is_retried_under_the_next_attempt(self):
        self.world(['EXSEMI_Q2_8K'])
        driver = self.driver(issuers=(EXSEMI, EXMEM))
        self.drain(driver)
        slot = self.first_slot(2) + 1
        self.w.clock.now = slot * HOUR
        item = driver.work.next(self.w.clock(), self.epoch)
        self.assertEqual(item['round_id'], f'cadence:{slot}#1')
        self.store.open_round(RUN, item['round_id'],
                              driver.work.request(item, self.store.load(RUN).read(), self.w.clock()), self.epoch)
        self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot}#2')
        self.assertIsNone(self.tick(driver)['round_id'])


class OneLegPerPlan(unittest.TestCase):
    def test_f5_an_s1_plan_with_an_intent_reserves_no_attempt_for_another_leg(self):
        for name, snapshot in (('all names quoted', with_quotes(at('2026-10-10T14:00:00Z'))),):
            with self.subTest(name):
                result = run(snapshot)
                self.assertEqual(len(result['intents']), 1, result)
                leg = result['intents'][0]['execution_bounds']['leg']
                self.assertEqual(result['execution_attempt_budget']['counts'], {leg: 1})
                self.assertEqual([a['authority']['leg'] for a in result['execution_attempts']], [leg])
                self.assertEqual(result['quote_requests'], [])


class SignedReplay(DriverHarness):
    """IDEA-090 F10: a round started on accepted evidence with this round's assessment (the signed path's ready
    result) replays to the same head; replay must start it with the same evidence mode."""

    def replay(self, driver):
        journal, expected = self.store.journal(RUN), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        builder = driver.coordinator.context_builder
        dead = lambda *a: (_ for _ in ()).throw(AssertionError('live port called in replay'))
        builder.market = builder.health = builder.calendar = dead
        head = replay_live(journal, doc(initial_projection(pipeline.pipeline_ledger())), self.store, builder=builder,
                           run_id=RUN, wallet_id='fake-wallet', chain_id=56, version_id='integration-fixture',
                           profile_hash=self.h, address='0x' + '1' * 40, policy=StrategyPolicy(),
                           planner=RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                           execution=ExecutionBridge(), reducer=settle,
                           initial_policy_state=initial_policy_state(RUN, self.profile))
        return head, expected

    def test_f10_a_ready_assessment_round_on_accepted_evidence_replays(self):
        self.world(['EXSEMI_402_8K'])
        driver = self.driver('MANDATORY_REDUCTION')
        c = driver.coordinator
        item = driver.work.next(self.w.clock(), self.epoch)
        request = driver.work.request(item, self.store.load(RUN).read(), self.w.clock())
        result = c.assessor.assess(request)
        c.start(item['round_id'], request, self.w.clock(), assessment_override=result, use_accepted_evidence=True)
        record = self.store.event(RUN, 'plan:' + item['round_id'])['record']
        self.assertIsNotNone(record['assessment'])
        self.assertIn('assessment_available', record['policy_input']['context'])
        self.assertEqual(record['accepted_evidence'], 'WITH_ASSESSMENT')
        head, expected = self.replay(driver)
        self.assertEqual(head, expected)
