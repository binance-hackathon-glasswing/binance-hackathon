"""PC-S1WIRE01: production evidence adapter and frozen-close jobs; synthetic externals only."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest

from larp.contracts import Document
from larp.integration.contract import context_hash, red_flag_predicates
from larp.integration.runtime import RuntimePlanner
from larp.runtime.driver import SessionCalendar
from larp.strategy import s1
from tests.integration import test_published_red_flag_policy as published
from tests.strategy.test_s1_core import cfg
from tests.strategy.test_s1_plan import snap


class ExposureInputs(unittest.TestCase):
    def setup_record(self):
        s, record, _, now = published.PublishedPredicatePolicy().producer_context('RF2-1.05-SUPPORTED', '1.05')
        markets = {m['symbol']: m for m in s.context.read()['markets']}
        # A frozen synthetic calendar surrounds the actual verifier fixture's event.
        event = record['falsifier_findings'][0]['red_flag']['event_original_ms']
        cal = SessionCalendar(dict(schema='USRegularSessions.v1', calendar_id='SYNTHETIC', sessions=[
            dict(session_index=n, open_at=datetime.fromtimestamp((event+(n-2)*86400000-3600000)/1000, timezone.utc).isoformat(),
                 close_at=datetime.fromtimestamp((event+(n-2)*86400000+3600000)/1000, timezone.utc).isoformat())
            for n in range(6)]))
        return s, record, now, markets, cal

    def produce(self, records=None, **changes):
        from larp.integration.exposure import exposure_inputs
        s, record, now, markets, cal = self.setup_record()
        kwargs = dict(records=[record] if records is None else records, profile=s.context.read()['profile'],
            run_id=s.run_id, profile_hash=s.policy_profile_hash, now_ms=now, markets=markets,
            known_versions={}, universe=('NVDAB',), session=cal(now)['index'], calendar=cal)
        kwargs.update(changes)
        return exposure_inputs(**kwargs)

    def test_verified_class2_uses_original_event_session_and_stable_identity(self):
        _, record, _, _, _ = self.setup_record()
        first = self.produce()
        self.assertEqual(len(first['evidence']), 1)
        item = first['evidence'][0]
        self.assertEqual((item['class'], item['symbols'], item['session_index']), ('CLASS_2_RED_FLAG', ['NVDAB'], 2))
        changed = deepcopy(record); changed['state_version'] += 1; changed['context_hash'] = context_hash(changed)
        second = self.produce([changed])
        self.assertEqual(item['evidence_id'], second['evidence'][0]['evidence_id'])
        self.assertTrue(first['complete'])

    def test_two_eligible_names_cut_without_counting_incomplete_input_as_healthy(self):
        _, record, _, _, _ = self.setup_record()
        first = self.produce()['evidence'][0]
        second = dict(first, evidence_id='different-original-filing', symbols=['GOOGLB'])
        state, audit = s1.limiter_step(None, session=2, cfg=cfg(), evidence=[first, second],
                                      assessment=None, input_complete=False)
        self.assertEqual(state['level'], 'CAUTION')
        self.assertTrue(audit['accepted']); self.assertFalse(audit['healthy'])

    def test_amendment_keeps_original_identity_and_missing_origin_cannot_renew(self):
        _, record, _, _, _ = self.setup_record()
        original = self.produce()['evidence'][0]
        amended = deepcopy(record)
        flag = amended['falsifier_findings'][0]['red_flag']
        flag.update(amendment=True, amends_accession=flag['accession'], accession='synthetic-amendment')
        amended['context_hash'] = context_hash(amended)
        result = self.produce([amended])
        self.assertEqual(result['evidence'][0]['evidence_id'], original['evidence_id'])
        flag['amends_accession'] = None; amended['context_hash'] = context_hash(amended)
        refused = self.produce([amended])
        self.assertFalse(refused['complete'])
        # The fixture also retains an independent original finding: keep that
        # valid fact, but the malformed amendment must add no renewal identity.
        self.assertLessEqual({i['evidence_id'] for i in refused['evidence']}, {original['evidence_id']})

    def test_shadow_wrong_profile_corrupt_hash_and_missing_issuer_are_not_healthy(self):
        s, record, _, _, _ = self.setup_record()
        shadow = dict(s.context.read()['profile']); shadow.pop('red_flag_authority')
        self.assertEqual(self.produce(profile=shadow)['evidence'], [])
        for bad in [dict(record, policy_profile_hash='f'*64), dict(record, context_hash='a'*64)]:
            result = self.produce([bad])
            self.assertFalse(result['complete']); self.assertEqual(result['evidence'], [])
        self.assertFalse(self.produce([])['complete'])

    def test_unmappable_event_time_is_incomplete_not_a_healthy_empty_review(self):
        _, record, _, _, _ = self.setup_record()
        for finding in record['falsifier_findings']:
            if finding.get('red_flag'):finding['red_flag']['event_original_ms'] = None
        record['context_hash'] = context_hash(record)
        result = self.produce([record])
        self.assertFalse(result['complete']); self.assertEqual(result['evidence'], [])

    def test_old_event_is_not_restamped_and_incomplete_input_cannot_expire_cut(self):
        first = self.produce(session=7)
        self.assertEqual(first['evidence'], [])
        previous = dict(level='CAUTION', healthy_sessions=2, counted_session=6, used_evidence_ids=['old'])
        state, report = s1.limiter_step(previous, session=7, cfg=cfg(), evidence=[], assessment=None,
                                        input_complete=False)
        self.assertEqual(state['level'], 'CAUTION'); self.assertFalse(report['healthy'])

    def test_fresh_cut_remains_usable_when_another_issuer_is_missing(self):
        report = self.produce(universe=('NVDAB', 'GOOGLB'))
        self.assertFalse(report['complete']); self.assertEqual(len(report['evidence']), 1)

    def test_adverse_latch_cannot_hide_incomplete_or_expired_review(self):
        _, record, now, _, _ = self.setup_record()
        for changes in [
            dict(review_complete_excluding_timed_blocks=False),
            dict(assessed_until_excluding_timed_ms=now),
        ]:
            with self.subTest(changes=changes):
                incomplete = dict(record, **changes)
                incomplete['context_hash'] = context_hash(incomplete)
                report = self.produce([incomplete])
                self.assertFalse(report['complete'])
                self.assertEqual(len(report['evidence']), 1)
                previous = dict(level='CAUTION', healthy_sessions=2, counted_session=1,
                                used_evidence_ids=[report['evidence'][0]['evidence_id']])
                following, audit = s1.limiter_step(previous, session=2, cfg=cfg(),
                    evidence=report['evidence'], assessment=None, input_complete=report['complete'])
                self.assertEqual(following['level'], 'CAUTION')
                self.assertFalse(audit['healthy'])


class SessionCloseJobs(unittest.TestCase):
    def test_frozen_close_delay_and_identity_survive_later_planning(self):
        s = snap()
        planner = RuntimePlanner(job_validity_ms=60000, job_max_attempts=2,
                                 issuers={'issuer': {'token': 'NVDAB'}})
        now = int(s.observed_at.timestamp()*1000)
        jobs = planner._jobs(s, None, now)
        close = [j for j in jobs if j['payload']['reason'] == 'S1_SESSION_CLOSE']
        self.assertEqual(len(close), 1)
        expected = s.context.read()['execution_session']['close_ms'] + 900000
        self.assertEqual(close[0]['due_ms'], expected)
        self.assertEqual(close, [j for j in planner._jobs(s, None, now+1000)
                                 if j['payload']['reason'] == 'S1_SESSION_CLOSE'])
        self.assertEqual(close[0]['payload']['issuer_id'], 'issuer')


# A real store/Coordinator/RuntimePlanner/scheduler/replay path; all external ports
# and prices are synthetic. No service mode or signing capability is activated.
from larp.integration.runtime import ContextBuilder, StrategyPolicy, initial_projection, initial_policy_state
from larp.integration.settlement import ExecutionBridge, settle
from larp.integration.replay import replay_live
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor
from larp.runtime.scheduler import Scheduler
from larp.storage.postgres import doc
from tests.support import DatabaseCase, request


class S1Durability(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.snapshot = snap()
        self.context = self.snapshot.context.read()
        self.profile = self.context['profile']
        self.h = Document.from_dict(self.profile).digest('StrategyProfile.v1')
        self.now = int(self.snapshot.observed_at.timestamp()*1000)
        bounds = self.context['execution_session']
        self.cal = SessionCalendar(dict(schema='USRegularSessions.v1', calendar_id='FROZEN_SYNTHETIC', sessions=[
            dict(session_index=bounds['index']+n,
                 open_at=datetime.fromtimestamp((bounds['open_ms']+n*86400000)/1000, timezone.utc).isoformat(),
                 close_at=datetime.fromtimestamp((bounds['close_ms']+n*86400000)/1000, timezone.utc).isoformat())
            for n in range(2)]))
        self.initial = initial_projection(self.context['portfolio'])
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        self.store.initialize('run', 'wallet', 56, doc(self.initial))
        self.store.takeover('run', 1, offline=True)
        self.builder = ContextBuilder(profile=self.profile, profile_hash=self.h, run_id='run',
            issuers={}, universe=self.snapshot.universe, calendar=self.cal,
            market=lambda now: self.context['markets'], health=lambda current: self.context['health'])
        self.planner = RuntimePlanner(job_validity_ms=60000, job_max_attempts=2,
                                     issuers={'issuer': {'token': 'NVDAB'}})

    def coordinator(self):
        return Coordinator(self.store, FakeAssessor(), StrategyPolicy(), self.planner,
            execution=ExecutionBridge(), run_id='run', version_id='synthetic-s1', profile_hash=self.h,
            address='0x'+'1'*40, context_builder=self.builder,
            initial_policy_state=initial_policy_state('run', self.profile), clock_ms=lambda: self.now)

    def start(self, identity):
        req = request(job=identity, cutoff=self.now).read(); req['policy_profile_hash'] = self.h
        self.coordinator().start(identity, doc(req), self.now)

    def test_jobs_audit_and_frozen_calendar_replay_survive_restart(self):
        self.start('first')
        event = self.store.event('run', 'plan:first')['record']
        self.assertIn('exposure_input', event['policy_input']['context'])
        self.assertFalse(event['policy_input']['context']['exposure_input']['complete'])
        jobs = [j for j in event['plan']['jobs'] if j['payload']['reason'] == 'S1_SESSION_CLOSE']
        self.assertEqual(len(jobs), 1)
        self.assertIsNone(Scheduler(self.store).claim('run', self.epoch, 'evidence', self.now))
        # A fresh Coordinator does not change the calendar/job identity.
        self.now += 1000
        self.start('after-restart')
        again = self.store.event('run', 'plan:after-restart')['record']
        self.assertEqual(jobs, [j for j in again['plan']['jobs'] if j['payload']['reason'] == 'S1_SESSION_CLOSE'])
        expected, journal = self.store.verify('run'), self.store.journal('run')
        # Replay must use recorded calendar data as well as market ports.
        def dead(*args):raise AssertionError('live port called by replay')
        self.builder.market = self.builder.calendar = self.builder.health = dead
        with self.store.transaction() as db:db.execute('TRUNCATE runs CASCADE')
        actual = replay_live(journal, doc(self.initial), self.store, builder=self.builder,
            run_id='run', wallet_id='wallet', chain_id=56, version_id='synthetic-s1', profile_hash=self.h,
            address='0x'+'1'*40, policy=StrategyPolicy(), planner=self.planner,
            execution=ExecutionBridge(), reducer=settle, initial_policy_state=initial_policy_state('run', self.profile))
        self.assertEqual(actual, expected)
        scheduler = Scheduler(self.store)
        claim = scheduler.claim('run', self.store.load('run').read()['epoch'], 'evidence', jobs[0]['due_ms'])
        self.assertEqual(claim.read()['job'], jobs[0])
        scheduler.finish('run', claim)
        self.assertIsNone(scheduler.claim('run', claim.read()['epoch'], 'evidence', jobs[0]['due_ms']+1))
