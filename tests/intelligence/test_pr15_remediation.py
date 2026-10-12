"""IDEA-041 / IDEA-043: real storage, provider and item-verification boundaries."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.intelligence.models import parse_output, RuleBaselineModel
from larp.intelligence.providers import ACTION_SCHEMA, AnthropicMessagesModel
from larp.intelligence.scenarios import build_world, EXSEMI
from larp.intelligence.tools import PortEvidenceReader
from larp.sources.store import SQLiteEvidenceStore
from tests.intelligence.test_providers import Adapters, FINISH, anthropic_reply, request
from tests.intelligence.test_red_flags import BY_ID, Run, spec, enabled_profile
from larp.integration.contract import red_flag_directives


class DurableReader(unittest.TestCase):
    def test_real_assessor_reads_sqlite_records_from_its_worker(self):
        world = build_world(['EXSEMI_Q2_8K', 'EXSEMI_Q3_8K'])
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteEvidenceStore(str(Path(tmp) / 'evidence.db'))
            self.addCleanup(store.close)
            for d in world.store.records(EXSEMI):
                store.db.execute('INSERT INTO erecords VALUES (?,?,?)',
                                 (d.read()['record_id'], EXSEMI, d.payload))
            assessor = world.assessor(RuleBaselineModel(world.clock))
            assessor.reader = PortEvidenceReader(store, world.artifacts)
            result = assessor.assess(world.request(['EXSEMI_Q3_8K'], issuer_id=EXSEMI)).read()
            self.assertEqual(result['status'], 'ASSESSED')
            self.assertTrue(result['evidence_used'])


class ProviderFailures(Adapters):
    def test_raw_reply_saved_before_overflow_or_recursive_json_is_parsed(self):
        for raw in (b'{"model":"example-model-id","stop_reason":"end_turn","content":[{"type":"text","text":"{}"}],"usage":{"input_tokens":1e400,"output_tokens":0}}',
                    b'[' * 2000 + b'0' + b']' * 2000):
            model = self.build(AnthropicMessagesModel, transport=lambda *a: (200, raw))
            result = model.step(request(), 60_000).read()
            self.assertEqual(result['status'], 'ERROR')
            self.assertEqual(self.artifacts.get(result['raw_response_artifact']), raw)
            self.assertIsNotNone(result['request_payload_artifact'])

    def test_every_provider_object_is_closed_and_real_outputs_fit(self):
        def walk(value):
            if isinstance(value, dict):
                if value.get('type') == 'object':
                    self.assertIs(value.get('additionalProperties'), False)
                for v in value.values(): walk(v)
            elif isinstance(value, list):
                for v in value: walk(v)
        walk(ACTION_SCHEMA)
        for output in (FINISH, {'action':'CALL_TOOL','tool':'fetch_document',
                               'args':{'accession':'0009900001-26-000101','name':'report.htm'}},
                       {'action':'CALL_TOOL','tool':'compare_facts','args':{'metric':'REVENUE'}}):
            model = self.build(AnthropicMessagesModel, anthropic_reply(output))
            self.assertEqual(parse_output(model.step(request(), 60_000).read()['output']), output)
        claim = ACTION_SCHEMA['properties']['claims']['items']['properties']
        self.assertIn('span', claim)
        self.assertIn('source', claim)
        self.assertIn('statement', claim)


class ItemSections(unittest.TestCase):
    def run_text(self, paragraphs, *, amendment=False):
        f = copy.deepcopy(BY_ID['RF1-4.02-AMENDED' if amendment else 'RF1-4.02-SUPPORTED'])
        f['filing']['paragraphs'] = paragraphs
        run = Run(f['fixture_id'])
        world = build_world([f['fixture_id']], extra_filings={f['fixture_id']: spec(f)})
        run.w = world
        result = run.assess(f['fixture_id'])
        return result, red_flag_directives(run.context(), enabled_profile())

    def test_body_cross_reference_cannot_create_a_section(self):
        result, directives = self.run_text(['Item 8.01 Other Events.',
            'We discussed the disclosure requirements under Item 4.02 in our training materials.',
            'Our previously issued statements should no longer be relied upon.'])
        self.assertEqual(directives, [])
        self.assertEqual(result['red_flag_checks'][0]['reason'], 'NO_ITEM_SECTION')

    def test_cross_reference_does_not_end_section_and_relied_on_works(self):
        _, directives = self.run_text(['Item 4.02 Non-Reliance on Previously Issued Financial Statements.',
            'As described in Item 8.01 below.',
            'On October 7, 2026, the Audit Committee concluded our financial statements should no longer be relied on.'])
        self.assertEqual([d['kind'] for d in directives], ['EXIT'])

    def test_same_paragraph_heading_leaves_asserted_body_readable(self):
        _, directives = self.run_text(['Item 4.02 Non-Reliance on Previously Issued Financial Statements '
            'On October 7, 2026, the Audit Committee concluded our financial statements should no longer be relied upon.'])
        self.assertEqual([d['kind'] for d in directives], ['EXIT'])

    def test_fresh_amendment_of_old_report_never_refreshes_event(self):
        result, directives = self.run_text([
            'Amendment No. 1 amends the Current Report on Form 8-K filed on July 8, 2026.',
            'Item 4.02 Non-Reliance on Previously Issued Financial Statements.',
            'On July 7, 2026, the Audit Committee concluded our financial statements should no longer be relied upon.'],
            amendment=True)
        self.assertEqual(directives, [])
        self.assertEqual(result['red_flag_checks'][0]['reason'], 'STALE_EVENT')
