"""IDEA-049 A: source-derived regressions; real stores/artifacts, synthetic external boundaries."""
from dataclasses import replace
from pathlib import Path
import copy
import json
import tempfile
import unittest

from larp.contracts import Document
from larp.intelligence.agent import build_request, context_hash
from larp.intelligence.common import IntelligenceError, digest, sha256_hex
from larp.intelligence.config import load_config, load_registry
from larp.intelligence.edgar import parse_acceptance_ms
from larp.intelligence.fakes import FakeClock, FakeFilingSource
from larp.intelligence.gate import accept, consume, initial_state, lifecycle_policy_from
from larp.intelligence.ingest import Ingestor
from larp.intelligence.models import HostedChatModel, RuleBaselineModel
from larp.intelligence.providers import AnthropicMessagesModel, OpenAIResponsesModel
from larp.intelligence.roundlog import model_trace
from larp.intelligence.scenarios import World, doc, page, p, prior_thesis
from larp.integration.contract import build_evidence_context, context_hash as evidence_hash, problem, red_flag_directives
from larp.marketdata.port import MarketPort
from larp.sources.store import FileArtifacts, SQLiteEvidenceStore
from tests.marketdata.test_live_port import Client
from tests.intelligence.test_red_flags import enabled_profile
from tests.intelligence.test_providers import SECRET, FINISH, request, anthropic_reply

PROFILE = 'a' * 64
RUN = 'final-a-synthetic-run'
ACCEPTANCE = '2026-10-09T20:00:00+00:00'
T0 = parse_acceptance_ms(ACCEPTANCE) + 300_000
NONRELIANCE = 'The Audit Committee concluded that our financial statements should no longer be relied upon and should be restated.'


class RealEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / 'evidence.sqlite')
        self.store = SQLiteEvidenceStore(self.path, journal_mode='DELETE')
        self.addCleanup(lambda: self.store.close())
        self.artifacts = FileArtifacts(str(Path(self.tmp.name) / 'artifacts'))
        self.registry, self.config, self.clock = load_registry(), load_config(), FakeClock(T0)
        self.source = FakeFilingSource(self.clock, {e.cik: e.entity_name for e in self.registry.entries})
        self.ingestor = Ingestor(registry=self.registry, source=self.source, store=self.store,
                                artifacts=self.artifacts, config=self.config, clock_ms=self.clock,
                                run_id=RUN, synthetic=True)
        self.w = World(self.registry, self.clock, self.source, self.store, self.artifacts, self.config, self.ingestor, {})
        self.entry = self.registry.by_token('NVDAB')
        context = prior_thesis(self.config, self.entry.issuer_id)
        self.state = dict(initial_state(self.entry.issuer_id, PROFILE, lifecycle_policy=lifecycle_policy_from(self.config)),
                          context=context, context_hash=context_hash(context))
        self.n = 0

    def add(self, suffix, text, item='4.02', entry=None, form='8-K'):
        entry = entry or self.entry
        accession = f'{entry.cik:010d}-26-{suffix:06d}'
        body = page(p('FORM ' + form), p(entry.entity_name), p('Item ' + item), p(text))
        self.source.add(entry.cik, accession=accession, form=form, items=[item], acceptance=ACCEPTANCE,
                        documents=[doc('filing.htm', form, body)])
        self.ingestor.poll(entry.issuer_id)
        return next(r.read() for r in self.store.records(entry.issuer_id) if r.read()['accession'] == accession)

    def assess(self, record, model=None):
        self.n += 1
        self.w.filings['active'] = dict(cik=self.entry.cik, accession=record['accession'])
        cursor = self.store.read_cursor('sec-edgar', self.entry.issuer_id).read()
        req = build_request(job={'job_id': f'a-job-{self.n}'}, run_id=RUN, issuer_id=self.entry.issuer_id,
                            records=[record], cutoff_ms=self.clock(), context=self.state['context'],
                            policy_profile_hash=PROFILE, allowed_tools=list(self.config.tools), tool_calls=6,
                            deadline_ms=60000, source_health=cursor['health'])
        r = self.w.assessor(model or RuleBaselineModel(self.clock)).assess(req)
        decision, after = accept(self.state, r, profile_hash=PROFILE, now_ms=self.clock())
        self.assertEqual(decision, 'ACCEPT', r.read().get('reasons'))
        self.state = after
        return r.read()

    def context(self, ticker='NVDA'):
        return build_evidence_context(consume(self.state, self.clock()), self.state, run_id=RUN,
                                      token=self.entry.token, underlying_id=ticker, policy_profile_hash=PROFILE)

    def persist_restart(self):
        batch = dict(schema='EvidenceStateBatch.v1', issuer_id=self.entry.issuer_id,
                     expected_state_version=0, state=self.state, jobs=[])
        batch['batch_id'] = digest('final-a.state', batch)
        self.store.commit(Document.from_dict(batch))
        self.store.close()
        self.store = SQLiteEvidenceStore(self.path, journal_mode='DELETE')
        self.w.store = self.store
        self.ingestor.store = self.store
        self.state = self.store.read_state(self.entry.issuer_id).read()


class IssuerContract(RealEvidence):
    def test_a_req_020_real_market_ticker_accepts_registered_issuer_and_class1(self):
        record = self.add(701, NONRELIANCE)
        self.assess(record)
        markets = {m['symbol']: m for m in MarketPort(Client(), '0x' + '1' * 40)(0)}
        self.assertEqual(markets['NVDAB']['underlying_id'], 'NVDA')
        context = self.context()
        self.assertNotEqual(context['issuer_id'], context['underlying_id'])
        self.assertIsNone(problem(context, markets=markets, universe=tuple(markets)))
        self.assertEqual([d['kind'] for d in red_flag_directives(context, enabled_profile())], ['EXIT'])
        for field, value in (('issuer_id', self.registry.by_token('MSFTB').issuer_id), ('underlying_id', 'MSFT')):
            changed = dict(context, **{field: value})
            changed['context_hash'] = evidence_hash(changed)
            self.assertEqual(problem(changed, markets=markets), 'WRONG_ISSUER')

    def test_a_req_020_wrong_market_security_cannot_borrow_the_correct_token_issuer(self):
        record = self.add(702, NONRELIANCE)
        self.assess(record)
        context = self.context('MSFT')
        self.assertEqual(problem(context, markets={'NVDAB': {'underlying_id': 'MSFT'}}), 'WRONG_ISSUER')


class NonReliance(RealEvidence):
    def test_a_req_043_both_clause_orders_produce_class1(self):
        for n, clause in enumerate((NONRELIANCE,
                'The Audit Committee concluded that our financial statements should be restated and should no longer be relied upon.'), 711):
            with self.subTest(clause=clause):
                self.assess(self.add(n, clause))
                checks = self.state['unresolved_adverse']
                self.assertTrue(any(a.get('red_flag', {}).get('accession') == f'{self.entry.cik:010d}-26-{n:06d}' for a in checks))
                self.assertTrue(any(d['kind'] == 'EXIT' for d in red_flag_directives(self.context(), enabled_profile())))

    def test_a_req_028_nonreliance_negation_hypothesis_and_other_actor_do_not_act(self):
        clauses = ['The Audit Committee declined to conclude that our financial statements should be restated and should no longer be relied upon.',
                   'If errors are discovered, our financial statements should be restated and should no longer be relied upon.',
                   'Our competitor concluded that its financial statements should be restated and should no longer be relied upon.']
        for n, clause in enumerate(clauses, 721):
            with self.subTest(clause=clause):
                result = self.assess(self.add(n, clause))
                self.assertFalse(any(c['verified'] for c in result['red_flag_checks']))
                self.assertEqual(red_flag_directives(self.context(), enabled_profile()), [])


class PendingRedFlags(RealEvidence):
    def test_a_req_017_unverified_item_survives_clean_filing_and_restart(self):
        original = self.add(731, 'The company is reviewing the disclosure.', '4.02')
        self.assess(original)
        self.assertEqual(self.state['evidence_gate'], 'UNKNOWN')
        self.persist_restart()
        self.clock.advance(60_000)
        clean = self.add(732, 'The company held its annual stockholders meeting.', '8.01')
        self.assess(clean)
        self.assertEqual(self.state['evidence_gate'], 'UNKNOWN')
        self.assertIn('PENDING_RED_FLAG_REVIEW', self.state['gate_reasons'])
        self.assertTrue(any(x['accession'] == original['accession'] for x in self.state.get('pending_red_flags', [])))
        self.assertFalse(self.context()['review_complete'])

    def test_a_req_047_only_complete_same_source_correction_resolves_pending(self):
        original = self.add(741, 'The company is reviewing the disclosure.', '4.02')
        self.assess(original)
        self.assertTrue(self.state.get('pending_red_flags'))
        spec = self.source.filings[self.entry.cik][0]
        spec['items'] = ['8.01']
        self.source.replace_document(original['accession'], 'filing.htm', page(p('FORM 8-K'), p(self.entry.entity_name),
                                     p('Item 8.01 Other Events'), p('The company held its annual stockholders meeting.')))
        self.clock.advance(60_000)
        self.ingestor.poll(self.entry.issuer_id, recheck=frozenset({original['accession']}))
        latest = max((r.read() for r in self.store.records(self.entry.issuer_id)), key=lambda r: r['revision'])
        text_hash = next(d['text_sha256'] for d in latest['documents'] if d['role'] == 'PRIMARY')
        artifact = self.artifacts.root / text_hash[:2] / text_hash
        hidden = artifact.with_suffix('.held')
        artifact.rename(hidden)
        self.assess(latest)
        self.assertTrue(self.state.get('pending_red_flags'), 'partial correction cannot clear uncertainty')
        hidden.rename(artifact)
        self.clock.advance(1_000)
        self.assess(latest)
        self.assertEqual(self.state.get('pending_red_flags'), [])
        self.assertTrue(any(x['accession'] == original['accession'] and x['resolution'] == 'SOURCE_CORRECTED'
                            for x in self.state.get('resolved_red_flag_reviews', [])))


class CredentialCapture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.artifacts = FileArtifacts(self.tmp.name)
        self.config, self.clock = load_config(), FakeClock(T0)
        self.calls = []

    def hosted(self, cls, transport=None):
        def send(*args):
            self.calls.append(args)
            return 503, b'{}'
        opts = dict(api_key=SECRET, model_id='example-model-id', prompt_text=self.config.prompt_text,
                    prompt_sha256=self.config.prompt_sha256, clock_ms=self.clock, artifacts=self.artifacts,
                    transport=transport or send)
        if cls is HostedChatModel:
            opts.update(provider='fixture', revision='example-snapshot-20261001',
                        endpoint='https://api.openai.com/v1/chat/completions', allowed_hosts=frozenset({'api.openai.com'}))
        return cls(**opts)

    def test_a_req_039_reflected_request_key_is_refused_before_capture_or_send(self):
        for cls in (AnthropicMessagesModel, OpenAIResponsesModel, HostedChatModel):
            with self.subTest(adapter=cls.__name__):
                model = self.hosted(cls)
                with self.assertRaises(IntelligenceError):
                    model.step(request({'document': SECRET}), 60000)
        self.assertEqual(self.calls, [])
        self.assertFalse(list(Path(self.tmp.name).iterdir()))

    def test_a_req_039_exception_code_is_sanitized(self):
        def send(*args):
            exc = OSError('unsafe transport exception')
            exc.code = SECRET
            raise exc
        for cls in (AnthropicMessagesModel, OpenAIResponsesModel):
            with self.subTest(adapter=cls.__name__):
                r = self.hosted(cls, send).step(request(), 60000)
                self.assertNotIn(SECRET.encode(), r.payload)
                self.assertEqual(r.read()['status'], 'ERROR')


class AuditRecovery(RealEvidence):
    def test_a_req_052_complete_multistep_original_io_and_tool_results_after_reopen(self):
        original = self.add(751, 'For the fourth quarter of fiscal 2026, we expect revenue of $5 billion.', '2.02')
        bodies, replies = [], []
        def send(url, headers, body, timeout):
            self.clock.advance(20)
            sent = json.loads(body)
            state = json.loads(sent['messages'][0]['content'])
            output = ({'action': 'CALL_TOOL', 'tool': state['gaps'][0]['tool'], 'args': state['gaps'][0]['args']}
                      if state['gaps'] and state['remaining_tool_calls'] else FINISH)
            reply = anthropic_reply(output, summary=f'readable summary {len(bodies)}')(sent)
            reply['content'].append({'type': 'redacted_thinking', 'data': 'opaque-synthetic-encrypted'})
            raw = json.dumps(reply).encode()
            bodies.append(body); replies.append(raw)
            return 200, raw
        model = AnthropicMessagesModel(model_id='example-model-id', api_key=SECRET, prompt_text=self.config.prompt_text,
                    prompt_sha256=self.config.prompt_sha256, clock_ms=self.clock, artifacts=self.artifacts, transport=send)
        result = self.assess(original, model)
        saved = self.artifacts.put(Document.from_dict(result).payload)
        self.persist_restart()
        recovered = Document(self.artifacts.get(saved)).read()
        trace = model_trace(recovered)
        self.assertGreaterEqual(len(trace['calls']), 2)
        for index, call in enumerate(trace['calls']):
            self.assertEqual(self.artifacts.get(call['request_artifact']), bodies[index])
            self.assertEqual(self.artifacts.get(call['response_artifact']), replies[index])
            sent = json.loads(bodies[index])
            self.assertEqual(sent['system'], self.config.prompt_text)
            self.assertEqual(sent['output_config']['format']['schema']['properties']['tool']['enum'], list(self.config.tools))
            self.assertIn(f'readable summary {index}', trace['cot'])
        self.assertNotIn('opaque-synthetic-encrypted', json.dumps(trace))
        self.assertTrue(recovered['model_io']['tool_calls'])
        for call in recovered['model_io']['tool_calls']:
            if call['result_sha256'] is not None:
                self.assertIn('result', call, 'tool result hash alone does not reconstruct the returned content')
                self.assertEqual(digest('larp.intel.tool.v1', {'r': call['result']}), call['result_sha256'])

    def test_a_req_065_fourteen_daily_writer_restarts_preserve_reader_and_artifacts(self):
        self.add(761, NONRELIANCE)
        self.assess(self.w.record('active') if 'active' in self.w.filings else self.store.records(self.entry.issuer_id)[-1].read())
        reader = SQLiteEvidenceStore(self.path, read_only=True)
        self.addCleanup(reader.close)
        for day in range(14):
            self.state['version'] = day + 1
            batch = Document.from_dict(dict(schema='EvidenceStateBatch.v1', batch_id=f'day-{day}',
                issuer_id=self.entry.issuer_id, expected_state_version=day, state=self.state, jobs=[]))
            self.store.commit(batch)
            self.assertEqual(reader.read_state(self.entry.issuer_id).read()['version'], day + 1)
            self.store.close(); self.store = SQLiteEvidenceStore(self.path, journal_mode='DELETE')
        self.assertFalse(Path(self.path + '-wal').exists())
        with self.assertRaises(Exception): reader.commit(batch)

    def test_a_req_077_foreign_private_filer_cannot_inherit_domestic_red_flags(self):
        entry = self.registry.by_token('SKHYB')
        original = self.add(771, NONRELIANCE, entry=entry, form='6-K')
        self.entry = entry
        context = prior_thesis(self.config, entry.issuer_id)
        self.state = dict(initial_state(entry.issuer_id, PROFILE), context=context, context_hash=context_hash(context))
        self.assess(original)
        self.assertEqual(red_flag_directives(self.context('SKHY'), enabled_profile()), [])
        self.assertEqual(entry.filer_class, 'FOREIGN_PRIVATE')
        self.assertNotIn('8-K', entry.forms)
