"""A-REQ-038: real ingest/assessor/gate/policy/planner/coordinator and PostgreSQL.

Only EDGAR/market/model HTTP and unused execution port are synthetic external boundaries.
"""
from pathlib import Path
import tempfile
from larp.intelligence.providers import AnthropicModel
from larp.intelligence.scenarios import build_world
from larp.sources.store import FileArtifacts, SQLiteEvidenceStore
from tests.integration.test_evidence_pipeline import PipelineHarness, EXTRA, RUN, EXSEMI
from tests.intelligence.test_providers import SECRET


class DurableIncident(PipelineHarness):
    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        evidence = SQLiteEvidenceStore(str(Path(tmp.name) / 'evidence.sqlite'), journal_mode='DELETE')
        self.addCleanup(evidence.close)
        self.w = build_world(['EXSEMI_Q2_8K', 'EXSEMI_402_8K', 'OCCURRED_8K'],
                             extra_filings=EXTRA, store=evidence, artifacts=FileArtifacts(str(Path(tmp.name) / 'artifacts')))

    def test_a_req_038_real_provider_failure_has_durable_sanitized_incident_and_retry(self):
        calls = []
        def unavailable(*args):
            calls.append(True)
            raise OSError(SECRET)
        model = AnthropicModel(api_key=SECRET, model_id='example-model-id', prompt_text=self.w.config.prompt_text,
                               prompt_sha256=self.w.config.prompt_sha256, clock_ms=self.w.clock,
                               artifacts=self.w.artifacts, transport=unavailable)
        coordinator = self.coordinator()
        coordinator.assessor = self.w.assessor(model)
        _, request = self.round(coordinator, 'provider-failed', 'EXSEMI_Q2_8K')
        planned = self.store.journal(RUN)[0].read()['event']['record']
        assessment = planned['assessment']
        self.assertEqual(assessment['status'], 'UNAVAILABLE')
        self.assertIn('MODEL_ERROR', assessment['reasons'])
        self.assertEqual(assessment['model_io']['requests_started'], 1)
        self.assertIn('RETRY_AFTER_UNAVAILABLE', [r['reason'] for r in assessment['review_requests']])
        self.assertNotEqual(self.store.load(RUN).read()['projection']['evidence'][EXSEMI]['evidence_gate'], 'CLEAR')
        self.assertEqual(self.commands(), [])
        coordinator.start('provider-failed', request, self.w.clock())
        self.assertEqual(len(calls), 1)
        with self.store.transaction() as db:
            rows = db.execute('SELECT document FROM audit_events WHERE run_id=%s', (RUN,)).fetchall()
        self.assertEqual(len(rows), 1)
        trail = b''.join(bytes(r[0]) for r in rows)
        self.assertNotIn(SECRET.encode(), trail)
        self.assertNotIn(SECRET.encode(), b''.join(d.payload for d in self.store.journal(RUN)))
        self.store.verify(RUN)
