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

    def test_shadow_wrong_profile_corrupt_hash_and_missing_issuer_are_not_healthy(self):
        s, record, _, _, _ = self.setup_record()
        shadow = dict(s.context.read()['profile']); shadow.pop('red_flag_authority')
        self.assertEqual(self.produce(profile=shadow)['evidence'], [])
        for bad in [dict(record, policy_profile_hash='f'*64), dict(record, context_hash='a'*64)]:
            result = self.produce([bad])
            self.assertFalse(result['complete']); self.assertEqual(result['evidence'], [])
        self.assertFalse(self.produce([])['complete'])

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
