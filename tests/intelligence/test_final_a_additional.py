"""Additional source-derived A catalogue probes, preregistered before their first run."""
from datetime import datetime, timezone
from larp.intelligence.agent import EvidenceAssessor
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import doc, page, p
from larp.integration.contract import red_flag_directives
from tests.intelligence.test_final_a_requirements import RealEvidence, NONRELIANCE
from tests.intelligence.test_red_flags import enabled_profile


class AdditionalEvidence(RealEvidence):
    def test_a_req_010_future_acceptance_within_clock_tolerance_is_not_decision_input(self):
        accession = f'{self.entry.cik:010d}-26-000781'
        future = datetime.fromtimestamp((self.clock() + 1000) / 1000, timezone.utc).isoformat()
        self.source.add(self.entry.cik, accession=accession, form='8-K', items=['2.02'], acceptance=future,
            visible_ms=self.clock(), documents=[doc('future.htm', '8-K', page(p('Item 2.02 Results of Operations'),
                p('For the fourth quarter of fiscal 2026, we expect revenue of $5 billion.')))])
        self.ingestor.poll(self.entry.issuer_id)
        record = next(r.read() for r in self.store.records(self.entry.issuer_id) if r.read()['accession'] == accession)
        result = self.assess(record)
        self.assertEqual(result['evidence_used'], [])
        self.assertEqual(result['claims'], [])
        self.assertNotEqual(result['status'], 'ASSESSED')
        self.clock.advance(2000)
        self.ingestor.poll(self.entry.issuer_id)
        after = self.assess(record)
        self.assertTrue(after['evidence_used'])
        self.assertTrue(after['claims'])

    def test_a_req_045_current_impairment_determination_is_not_a_forecast_only(self):
        record = self.add(791, 'The company determined that a material impairment charge is required and will record a goodwill impairment charge.', '2.06')
        self.assess(record)
        directives = red_flag_directives(self.context(), enabled_profile())
        self.assertEqual([d['kind'] for d in directives], ['BLOCK_NEW_BUYS'])
        self.assertEqual([d['block_sessions'] for d in directives], [5])

    def test_a_req_027_declared_assessment_dimensions_have_explicit_unknowns(self):
        result = self.assess(self.add(801, NONRELIANCE))
        assessment = result.get('structured_assessment')
        self.assertIsInstance(assessment, dict)
        self.assertTrue({'catalyst_type', 'direction', 'strength', 'novelty', 'durability',
                         'source_agreement', 'risks'} <= set(assessment))
        self.assertEqual(assessment['durability']['status'], 'UNKNOWN')
        self.assertFalse(assessment['strength']['calibrated'])
        self.assertEqual(assessment['source_agreement']['independent_origins'], 1)
