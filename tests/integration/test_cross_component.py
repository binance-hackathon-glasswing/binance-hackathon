"""Cross-component integration criteria (IDEA-028 RT20).

C1-C3 check boundaries that already agree; C2 is the fixture drift check and fails
until the strategy fixture is re-captured (prompt 07 item 8). C4 exercises the supported ContextBuilder/RuntimePlanner coordinator path against
disposable PostgreSQL, with synthetic complete inputs and explicit resource reservations.
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
    def test_c4_coordinator_commits_strategy_baseline_intent(self):
        """Supported adapter path commits an executable plan and atomically reserves resources."""
        from larp.integration.runtime import (ContextBuilder, RuntimePlanner, StrategyPolicy,
                                             initial_policy_state, initial_projection)
        from larp.research.fixtures import snapshot, with_quotes
        from larp.runtime.coordinator import Coordinator
        from larp.runtime.fixtures import FakeAssessor, FakeExecution
        from larp.storage.postgres import doc
        fixture = with_quotes(snapshot(profile_changes={'baseline':'EQUAL_WEIGHT',
            'operating_name_weight':[1,5], 'operating_gross_weight':[4,5],
            'regime_gross_weight':[4,5], 'top_up_below_gross_weight':[3,4]}))
        context = fixture.context.read()
        profile = context['profile']
        profile_hash = Document.from_dict(profile).digest('StrategyProfile.v1')
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        self.store.initialize('run','wallet',56,doc(initial_projection(context['portfolio'])))
        self.epoch = self.store.takeover('run',1,offline=True)
        builder = ContextBuilder(profile=profile, profile_hash=profile_hash, run_id='run', issuers={},
            market=lambda now:context['markets'], health=lambda current:context['health'],
            calendar=lambda now:{'index':80,'remaining':10}, series=lambda now:context['series'],
            universe=fixture.universe)
        runtime = Coordinator(self.store, FakeAssessor(), StrategyPolicy(),
            RuntimePlanner(job_validity_ms=60000,job_max_attempts=3), execution=FakeExecution(),
            run_id='run',version_id='synthetic',profile_hash=profile_hash,address='0x'+'1'*40,
            context_builder=builder,initial_policy_state=initial_policy_state('run',profile))
        now = int(fixture.observed_at.timestamp()*1000)
        request = runtime_request('BUY').read()
        request.update(policy_profile_hash=profile_hash,cutoff_ms=now)
        runtime.start('r',doc(request),now,defer_close=True)
        with self.store.transaction() as db:
            commands = db.execute("SELECT payload FROM commands WHERE run_id='run'").fetchall()
        self.assertEqual(len(commands),1)
        command = Document(bytes(commands[0][0])).read()
        self.assertEqual(command['kind'],'EXECUTION_REQUEST')
        self.assertEqual(command['payload']['side'],'BUY')
        self.assertTrue(self.store.load('run').read()['reservations'])
