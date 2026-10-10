"""Cross-component integration criteria (IDEA-028 RT20).

C1-C3 check boundaries that already agree; C4 records the coordinator-to-strategy
gap as an expected failure, so it turns into an unexpected success once the
StrategyContext and PlanResult adapters land (then remove the decorator).
"""

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from larp.contracts import Document
from larp.runtime.schema import assessment_request, assessment_result

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / 'tests/intelligence/golden/trace-tool-selection-thesis-revision.json'
PRODUCER = ROOT / 'tests/strategy/fixtures/assessment-producer.json'


def golden():
    trace = json.loads(GOLDEN.read_text(encoding='utf-8'))
    return trace['request'], trace['result']


class AssessmentBoundary(unittest.TestCase):
    def test_c1_evidence_output_passes_runtime_validators(self):
        request, result = golden()
        now = result['completed_ms']
        req = assessment_request(Document.from_dict(request), request['run_id'],
                                 request['policy_profile_hash'], now)
        assessment_result(Document.from_dict(result), req, now)

    def test_c2_strategy_fixture_matches_current_evidence_output(self):
        fixture = json.loads(PRODUCER.read_text(encoding='utf-8'))
        request, result = golden()
        self.assertEqual(fixture['request'], request,
                         'Re-capture tests/strategy/fixtures/assessment-producer.json from the evidence golden trace')
        self.assertEqual(fixture['result'], result,
                         'Re-capture tests/strategy/fixtures/assessment-producer.json from the evidence golden trace')

    def test_c3_current_evidence_output_reaches_strategy_policy(self):
        from larp.research.fixtures import changed, snapshot
        from larp.strategy.policy import decide
        request, result = golden()
        s = snapshot(held={'NVDAB': 2000}, now=datetime.fromtimestamp(result['completed_ms'] / 1000, timezone.utc),
                     profile_changes={'evidence_mode': 'SHADOW',
                                      'falsifier_ids': [f['falsifier_id'] for f in result['falsifiers']]})
        # Only run/profile identity is rebound to the strategy fixture; content is the producer's.
        for document in (request, result):
            document.update(run_id=s.run_id, policy_profile_hash=s.policy_profile_hash)
        c = s.context.read()
        c['markets'][0]['underlying_id'] = result['issuer_id']
        c['series']['NVDAB']['entity_id'] = result['issuer_id']
        state = replace(s.policy_state, data=Document.from_dict(
            {'evidence_contexts': {result['issuer_id']: request['context']}}))
        s = replace(changed(s, markets=c['markets'], series=c['series'], assessments=[result],
                            assessment_requests={result['issuer_id']: request}), policy_state=state)
        data = decide(s, state).next_policy_state.data.read()
        self.assertIn('ASSESSMENT_ACCEPTED', [d['reason'] for d in data['assessment_diagnostics']])


from tests.support import DatabaseCase, request as runtime_request


class CoordinatorWithStrategy(DatabaseCase):
    @unittest.expectedFailure  # RT20 G1/G2: no StrategyContext provider or PlanResult adapter yet
    def test_c4_coordinator_commits_strategy_baseline_intent(self):
        """Target behaviour: a BUY-eligible round through the real coordinator, store and
        strategy modules commits the strategy's baseline intent as an execution request."""
        from larp.risk import planner
        from larp.runtime.coordinator import Coordinator
        from larp.runtime.fixtures import FakeAssessor, FakeExecution
        from larp.strategy import policy

        class Policy:
            decide = staticmethod(policy.decide)

        class Planner:
            plan = staticmethod(planner.plan)

        runtime = Coordinator(self.store, FakeAssessor(), Policy(), Planner(), execution=FakeExecution(),
                              run_id='run', version_id='synthetic', profile_hash='a' * 64,
                              address='0x' + '1' * 40)
        runtime.start('r', runtime_request('BUY'), 1791590400000, defer_close=True)
        with self.store.transaction() as db:
            commands = db.execute('SELECT count(*) FROM commands').fetchone()[0]
        self.assertGreaterEqual(commands, 1)
