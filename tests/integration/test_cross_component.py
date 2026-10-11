"""Cross-component integration criteria (IDEA-028 RT20).

C1-C3 check boundaries that already agree; C2 is the fixture drift check and fails
until the strategy fixture is re-captured (prompt 07 item 8). C4 records the raw
coordinator-to-strategy wiring as an expected failure (IDEA-042 B2): PR #7's
ContextBuilder/RuntimePlanner replaced that wiring, and a BUY through them stays
blocked by entry inputs until the token-candle sessions and price-impact rule land
(DR-08). The deployment acceptance suite (IDEA-042 item 10) replaces C4.
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
        """Current path (PR #7): AssessmentResult.v2 -> IssuerEvidenceState.v2 -> EvidenceContext.v1 -> decide()."""
        from larp.integration.contract import build_evidence_context
        from larp.intelligence.agent import context_hash
        from larp.intelligence.gate import accept, consume, initial_state
        from larp.research.fixtures import changed, snapshot
        from larp.strategy.policy import decide
        request, result = golden()
        now_ms = result['completed_ms']
        s = snapshot(held={'NVDAB': 2000}, now=datetime.fromtimestamp(now_ms / 1000, timezone.utc),
                     profile_changes={'evidence_mode': 'SHADOW',
                                      'falsifier_ids': [f['falsifier_id'] for f in result['falsifiers']]})
        # Only run/profile identity is rebound to the strategy fixture; content is the producer's.
        result.update(run_id=s.run_id, policy_profile_hash=s.policy_profile_hash)
        issuer = result['issuer_id']
        state = dict(initial_state(issuer, s.policy_profile_hash), context=request['context'],
                     context_hash=context_hash(request['context']))
        decision, state = accept(state, Document.from_dict(result), profile_hash=s.policy_profile_hash, now_ms=now_ms)
        self.assertEqual(decision, 'ACCEPT')
        evidence = build_evidence_context(consume(state, now_ms), state, run_id=s.run_id, token='NVDAB',
                                          underlying_id=issuer, policy_profile_hash=s.policy_profile_hash)
        c = s.context.read()
        c['markets'][0]['underlying_id'] = issuer
        c['series']['NVDAB']['entity_id'] = issuer
        s = changed(s, markets=c['markets'], series=c['series'], assessments=[evidence])
        data = decide(s, s.policy_state).next_policy_state.data.read()
        self.assertEqual(data['evidence_rejections'], [])
        self.assertEqual(data['evidence_versions'], {'NVDAB': state['version']})

from tests.support import DatabaseCase, request as runtime_request


class CoordinatorWithStrategy(DatabaseCase):
    @unittest.expectedFailure  # raw wiring without ContextBuilder; superseded by PR #7 adapters (IDEA-042 B2)
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
