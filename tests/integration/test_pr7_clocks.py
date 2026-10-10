"""IDEA-033 R10: elapsed assessment time is not future evidence or free validity."""

from larp.contracts import ContractError
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakePolicy, FakePlanner, FakeExecution, settle
from larp.runtime.replay import replay
from larp.storage.postgres import doc
from tests.support import DatabaseCase, request

NOW = 1791590400000


class CompletionClocks(DatabaseCase):
    def runtime(self, elapsed=250, expiry=None):
        class DelayedAssessor(FakeAssessor):
            def assess(inner, req):
                value = super().assess(req).read()
                value.update(schema='AssessmentResult.v2', cutoff_ms=NOW, started_ms=NOW,
                             completed_ms=NOW + 250)
                if expiry is not None:
                    value['expiry_ms'] = expiry
                return doc(value)
        runtime = Coordinator(self.store, DelayedAssessor(), FakePolicy(), FakePlanner(),
                              execution=FakeExecution(), run_id='run', version_id='synthetic',
                              profile_hash='a'*64, address='0x'+'1'*40)
        runtime.clock = lambda: NOW + elapsed
        return runtime

    def test_elapsed_assessment_is_accepted_and_replays(self):
        self.runtime().start('r', request(), NOW)
        record = self.store.event('run', 'plan:r')['record']
        self.assertIsNotNone(record['assessment'])
        self.assertNotIn('ASSESSMENT_UNAVAILABLE', record['errors'])
        self.assertEqual(record['started_ms'], NOW)
        self.assertEqual(record['decision_ms'], NOW + 250)
        journal, expected = self.store.journal('run'), self.store.verify('run')
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        replay(journal, doc(dict(balances=dict(USDT=100, BNB=10, NVDAB=0))), self.store,
               run_id='run', wallet_id='wallet', chain_id=56, version_id='synthetic',
               profile_hash='a'*64, address='0x'+'1'*40, policy=FakePolicy(), planner=FakePlanner(),
               execution=FakeExecution(), reducer=settle)
        self.assertEqual(expected, self.store.verify('run'))

    def test_expiry_is_checked_at_consumption(self):
        runtime = self.runtime(elapsed=60000)
        runtime.assessor = FakeAssessor()  # v1 previously passed expiry against the stale start clock
        runtime.start('r', request('BUY'), NOW)
        record = self.store.event('run', 'plan:r')['record']
        self.assertIsNone(record['assessment'])
        self.assertEqual(record['orders'], [])

    def test_backward_clock_prevents_planning_and_leaves_recoverable_round(self):
        with self.assertRaises(ContractError):
            self.runtime(elapsed=-1).start('r', request('BUY'), NOW)
        self.assertIsNone(self.store.receipt('run', 'plan:r'))
        self.assertEqual(self.store.load('run').read()['reservations'], [])
        self.runtime().recover(NOW + 250)
        self.assertIsNotNone(self.store.receipt('run', 'close:r'))
