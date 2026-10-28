"""IDEA-112 ST-1..ST-5: idle signed safety rounds are throttled; any other commit, a new UTC day or the interval
plans one at once. Real PostgreSQL store and real signed driver; synthetic model, no keys or network."""
import json
from pathlib import Path
import unittest
from unittest.mock import PropertyMock, patch

from larp.contracts import ContractError
from larp.runtime.coordinator import batch_for
from larp.runtime.driver import RoundDriver
from tests.integration.test_evidence_pipeline import RUN
from tests.runtime.test_round_driver_service import SECOND, ServiceHarness
from tests.runtime.test_signed_models import Blocking

ROOT = Path(__file__).resolve().parents[2]
INTERVAL = 120 * SECOND


class SafetyThrottle(ServiceHarness):
    def setUp(self):
        super().setUp()
        self.planned_rounds = []

    def signed(self, interval):
        from larp.runtime.deferred_models import DeferredAssessments
        driver = self.service_driver()
        driver.safety_interval = interval
        model = Blocking()  # the filing's assessment never completes, so every cycle is idle unless a test writes
        self.addCleanup(model.release.set)
        driver.assessments = DeferredAssessments(model,
            root=Path(self.tmp.name) / 'deferred', run_id=driver.coordinator.run_id,
            build_id=driver.coordinator.version_id, profile_hash=driver.coordinator.profile_hash)
        return driver

    def tick(self, driver, seconds=5):
        self.w.clock.now += seconds * SECOND
        summary = driver.once(self.w.clock())
        if (summary.get('round_id') or '').startswith('safety:'):
            self.planned_rounds.append(summary['round_id'])
        return summary

    def safety_rounds(self):
        return self.planned_rounds

    def test_st1_without_an_interval_every_idle_cycle_plans(self):
        driver = self.signed(None)
        for _ in range(4):
            self.tick(driver)
        self.assertEqual(len(self.safety_rounds()), 4)

    def test_st2_idle_cycles_are_skipped_until_the_interval_passes(self):
        driver = self.signed(INTERVAL)
        self.assertIsNotNone(self.tick(driver)['round_id'])  # a (re)started process plans at once
        version = self.version()
        with patch.object(driver, '_quotes') as quotes:
            for _ in range(23):  # 115 s of 5 s ticks
                summary = self.tick(driver)
                self.assertTrue(summary.get('safety_skipped'))
                self.assertIsNone(summary['round_id'])
            quotes.assert_not_called()
        self.assertEqual(self.version(), version)  # an idle skipped cycle commits nothing
        self.assertEqual(len(self.safety_rounds()), 1)
        self.assertIsNotNone(self.tick(driver)['round_id'])  # +120 s
        self.assertEqual(len(self.safety_rounds()), 2)

    def test_st3_another_writers_commit_plans_at_once(self):
        driver = self.signed(INTERVAL)
        self.tick(driver)
        self.assertTrue(self.tick(driver).get('safety_skipped'))
        current = self.store.load(RUN)
        self.store.commit(batch_for(current, 'other-writer', dict(kind='TEST_OTHER_WRITER'),
                                    projection=current.read()['projection']))
        self.assertIsNotNone(self.tick(driver)['round_id'])
        self.assertTrue(self.tick(driver).get('safety_skipped'))  # its own round does not retrigger

    def test_st3_a_new_utc_day_plans_at_once(self):
        driver = self.signed(INTERVAL)
        day = 86_400_000
        self.w.clock.now += day - self.w.clock() % day - 10 * SECOND  # 10 s before midnight UTC
        self.tick(driver, 0)
        self.assertTrue(self.tick(driver, 5).get('safety_skipped'))
        self.assertIsNotNone(self.tick(driver, 6)['round_id'])  # 00:00:01Z

    def test_st4_a_skipped_cycle_still_settles_and_queues(self):
        driver = self.signed(INTERVAL)
        self.tick(driver)
        from larp.runtime.deferred_models import DeferredAssessments
        # The blocked model holds the slot; report it free so the queueing step runs as in production.
        with patch.object(driver.execution, 'settle_open', wraps=driver.execution.settle_open) as settle, \
                patch.object(DeferredAssessments, 'busy', new_callable=PropertyMock, return_value=False), \
                patch.object(driver.work, 'next', return_value=None) as queued:
            self.assertTrue(self.tick(driver).get('safety_skipped'))
            self.assertTrue(settle.called)
            self.assertTrue(queued.called)


class Settings(unittest.TestCase):
    def test_st5_invalid_intervals_are_refused(self):
        for bad in (0, -1, 1.5, '120000', True):
            with self.subTest(bad), self.assertRaises(ContractError):
                RoundDriver(None, None, safety_round_interval_ms=bad)

    def test_st5_service_validation_and_example(self):
        from larp.runtime.service import OPTIONAL_DRIVER_INTEGERS
        self.assertIn('safety_round_interval_ms', OPTIONAL_DRIVER_INTEGERS)
        example = json.loads((ROOT / 'config/runtime/runtime.example.json').read_text())
        self.assertEqual(example['driver']['safety_round_interval_ms'], 120000)

    def test_st5_fs1_standalone_preparation_carries_the_interval(self):
        from tests.runtime.test_fs1_standalone import prepare
        runtime = prepare()['runtime.json']
        runtime = json.loads(runtime) if isinstance(runtime, (bytes, str)) else runtime
        self.assertEqual(runtime['driver']['safety_round_interval_ms'], 120000)


if __name__ == '__main__':
    unittest.main()
