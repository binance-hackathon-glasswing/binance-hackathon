"""IDEA-057 SG-8: real prepared configuration, synthetic external boundaries only."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.intelligence.common import IntelligenceError
from larp.intelligence.routing import build_routed_assessor, validate_routing_spec
from larp.marketdata.web3 import encoded
from larp.runtime import gate_a, gate_a_check
from tests.runtime.test_gate_a import NOW, WALLET, assembled, prepare_shadow

RAW = (gate_a.ROOT / 'config/intelligence/aiand-routing.example.json').read_bytes()
PIN = gate_a.digest(RAW)


def routed(**changes):
    return assembled(**dict(model_routing_raw=RAW, model_routing_sha256=PIN, **changes))


class ModelPreparation(unittest.TestCase):
    def test_opt_in_pins_original_bytes_and_reports_unrun_host_requirements(self):
        # Whitespace is intentionally retained in the reviewed file's byte identity.
        raw = RAW + b'\n'
        with ExitStack() as stack:
            for name in ('ModelBudget', 'AIandChatModel', 'OpenAIResponsesModel'):
                stack.enter_context(patch('larp.intelligence.routing.' + name,
                                          side_effect=AssertionError('Preparation must be offline')))
            files = assembled(model_routing_raw=raw, model_routing_sha256=gate_a.digest(raw))
        config = json.loads(files['runtime.json'])
        driver = config['driver']
        self.assertEqual((config['mode'], driver['execution'], driver['intelligence_mode']),
                         ('dev', 'shadow', 'shadow'))
        self.assertEqual(driver['assessor'], 'aiand_routed')
        self.assertEqual(driver['model_routing_file'], '/etc/larp/model-routing.json')
        self.assertEqual(driver['model_budget_root'], '/var/lib/larp-runtime/model-budget')
        self.assertEqual(files['model-routing.json'], raw)
        self.assertEqual(driver['model_routing_sha256'], gate_a.digest(raw))
        report = json.loads(files['preparation-report.json'])
        self.assertEqual(report['input_hashes']['model-routing.json'], gate_a.digest(raw))
        self.assertEqual(report['model_routing']['reviewer'], 'gpt-6.1-sol')
        self.assertEqual(report['model_routing']['routine'], 'zai-org/glm-5.3')
        self.assertEqual(set(report['model_routing']['checks'].values()), {'NOT_RUN'})
        self.assertFalse(report['gate_a_passed'])
        self.assertFalse(report['signing_enabled'])
        self.assertNotIn('signer.json', files)

    def test_default_preparation_remains_deterministic_without_model_inputs(self):
        files = assembled()
        driver = json.loads(files['runtime.json'])['driver']
        self.assertEqual(driver['assessor'], 'deterministic')
        self.assertNotIn('model-routing.json', files)
        self.assertFalse(any(k.startswith('model_') for k in driver))
        self.assertNotIn('model_routing', json.loads(files['preparation-report.json']))

    def test_mismatched_missing_oversize_and_malformed_routing_inputs_refuse(self):
        for raw, pin in ((RAW, None), (None, PIN), (RAW, '0' * 64), (RAW + b' ', PIN),
                         (b'x' * (gate_a.MAX_ROUTING_BYTES + 1), '0' * 64),
                         (b'{bad JSON', gate_a.digest(b'{bad JSON'))):
            with self.subTest(raw_length=len(raw) if raw else None, pin=pin), self.assertRaises(ContractError):
                assembled(model_routing_raw=raw, model_routing_sha256=pin)

    def test_shared_spec_validation_refuses_invalid_models_before_any_budget_or_model(self):
        base = json.loads(RAW)
        mutations = [lambda s: s.update(openai_model='auto'), lambda s: s.update(openai_effort='invalid'),
                     lambda s: s.update(budget_account=''), lambda s: s.update(audit_sample_bps=True),
                     lambda s: s.update(audit_seed=''), lambda s: s.update(max_output_tokens=True),
                     lambda s: s.update(max_output_tokens=16001), lambda s: s.update(external_reviewers=[]),
                     lambda s: s.update(external_reviewers=s['external_reviewers'] * 2),
                     lambda s: s.update(endpoint='PRIVATE_INPUT_SENTINEL'),
                     lambda s: s['routine'].update(model_id='zai-org/glm-5.3-flash'),
                     lambda s: s['routine'].update(effort='none'),
                     lambda s: s['routine'].update(api_key='PRIVATE_INPUT_SENTINEL'),
                     lambda s: s['routine']['catalog'].update(context_window=1),
                     lambda s: s['routine']['catalog'].update(capabilities='reasoning'),
                     lambda s: s['routine']['catalog'].update(price_per_mtok=0.5),  # runtime Document refuses floats
                     lambda s: s['external_reviewers'][0]['catalog'].update(id='other/model')]
        with ExitStack() as stack:
            for name in ('ModelBudget', 'AIandChatModel', 'OpenAIResponsesModel'):
                stack.enter_context(patch('larp.intelligence.routing.' + name,
                                          side_effect=AssertionError('Invalid spec reached construction')))
            for mutate in mutations:
                value = deepcopy(base)
                mutate(value)
                raw = encoded(value)
                with self.subTest(mutation=mutate):
                    with self.assertRaises(IntelligenceError):
                        validate_routing_spec(value)
                    with self.assertRaises(ContractError) as error:
                        assembled(model_routing_raw=raw, model_routing_sha256=gate_a.digest(raw))
                    self.assertNotIn('PRIVATE_INPUT_SENTINEL', str(error.exception))
                    with self.assertRaises(IntelligenceError):
                        build_routed_assessor(value, registry=None, reader=None, config=None, clock_ms=None,
                                              artifacts=None, secrets={}, budget_root='/must-not-open')

    def test_cli_assembles_a_new_package_without_credentials_or_calls(self):
        from tests.runtime.test_deploy_presetup import terraform_output
        from tests.runtime.test_gate_a import profile, with_chain
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = {'terraform.json': encoded(terraform_output()), 'profile.json': encoded(profile()),
                      'capture.json': encoded(with_chain()), 'routing.json': RAW}
            for name, raw in values.items():
                (root / name).write_bytes(raw)
            args = ['prepare', '--terraform-output', str(root / 'terraform.json'), '--profile', str(root / 'profile.json'),
                    '--capture', str(root / 'capture.json'), '--run-id', 'model-test', '--build-id', 'b' * 40,
                    '--rds-ca-sha256', 'c' * 64, '--balance-rpc-url', 'https://rpc.invalid/',
                    '--balance-rpc-source-id', 'synthetic-rpc', '--out', str(root / 'new')]
            with patch.object(prepare_shadow, 'utc', return_value=NOW), \
                    patch.object(prepare_shadow.renderer, 'ignored_by_git', return_value=True), \
                    patch.object(prepare_shadow, 'credentials', side_effect=AssertionError('No credentials')), \
                    patch('socket.create_connection', side_effect=AssertionError('No network')):
                output = StringIO()
                with redirect_stdout(output):
                    self.assertEqual(prepare_shadow.main(args + ['--model-routing', str(root / 'routing.json')]), 4)
                self.assertFalse((root / 'new').exists())
                with redirect_stdout(StringIO()):
                    self.assertEqual(prepare_shadow.main(args + ['--model-routing', str(root / 'routing.json'),
                                                                '--model-routing-sha256', PIN]), 0)
                self.assertEqual((root / 'new' / 'model-routing.json').read_bytes(), RAW)
                files, report = gate_a_check.package_files(root / 'new')
                gate_a_check.check_scope({n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}, report)

    def test_routed_package_qualifies_locally_without_model_or_budget_access(self):
        # Use the existing full synthetic CI/terms fixture with real package consumers.
        from tests.runtime.test_gate_a_check import GateAPackageCheck
        fixture = GateAPackageCheck()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        files = routed(sec_contact='LARP Test test-contact@larp.test')
        for name in ('runtime.json', 'uploader.json', 'operations.json'):
            config = json.loads(files[name])
            config['database_ca_sha256'] = gate_a.digest(fixture.ca.read_bytes())
            files[name] = encoded(config)
        fixture.files = files
        fixture.write_package()
        before = {p: p.read_bytes() for p in fixture.root.rglob('*') if p.is_file()}
        with ExitStack() as stack:
            for name in ('ModelBudget', 'AIandChatModel', 'OpenAIResponsesModel'):
                stack.enter_context(patch('larp.intelligence.routing.' + name,
                                          side_effect=AssertionError('Qualification must be offline')))
            result = fixture.qualify()
        self.assertTrue(result['local_ready'], result)
        self.assertFalse(result['gate_a_passed'])
        self.assertFalse(result['remote_ci_verified'])
        self.assertFalse(result['signing_enabled'])
        self.assertEqual(before, {p: p.read_bytes() for p in fixture.root.rglob('*') if p.is_file()})
        originals = dict(fixture.files)
        for mutation in ('missing', 'tamper', 'unpin', 'budget', 'live', 'service', 'deterministic'):
            fixture.files = dict(originals)
            if mutation == 'missing':
                fixture.files.pop('model-routing.json')
            elif mutation == 'tamper':
                fixture.files['model-routing.json'] += b' '
            else:
                config = json.loads(fixture.files['runtime.json'])
                if mutation == 'unpin': config['driver']['model_routing_sha256'] = '0' * 64
                if mutation == 'budget': config['driver']['model_budget_root'] = '/different-budget'
                if mutation == 'live': config['mode'] = 'live'
                if mutation == 'service': config['driver']['execution'] = 'service'
                if mutation == 'deterministic': config['driver']['assessor'] = 'deterministic'
                fixture.files['runtime.json'] = encoded(config)
            fixture.write_package()  # Re-sealing outer package hashes must not bypass the inner pin/scope.
            with self.subTest(mutation=mutation):
                self.assertFalse(fixture.qualify()['local_ready'])

    def test_prepared_runtime_uses_glm_then_openai_and_budget_fallback_on_original_evidence(self):
        self.check_prepared_runtime(preferred=False)

    def test_prepared_runtime_uses_openai_then_high_effort_aiand_with_temporary_pacing(self):
        self.check_prepared_runtime(preferred=True)

    def check_prepared_runtime(self, *, preferred):
        from larp.intelligence.agent import build_request, EMPTY_CONTEXT
        from larp.intelligence.config import load_config, load_registry
        from larp.intelligence.fakes import FakeClock, FakeFilingSource
        from larp.intelligence.ingest import Ingestor
        from larp.intelligence.model_budget import ModelBudget
        from larp.intelligence.scenarios import cover, doc
        from larp.runtime.schema import assessment_result
        from larp.runtime.service import build_driver
        from larp.sources.store import FileArtifacts, SQLiteEvidenceStore
        from tests.intelligence.test_aiand_routing import chat_reply, decide
        from tests.runtime.test_driver import Store

        clock = FakeClock(int(gate_a.instant(NOW).timestamp() * 1000))
        issuer = 'SEC-CIK-0001045810'
        calls, texts = [], []
        fail_kimi = False

        def aiand(url, headers, raw, timeout):
            body = json.loads(raw)
            calls.append(body['model'])
            state = json.loads(body['messages'][1]['content'])
            texts.append(json.dumps(state))
            if fail_kimi and body['model'] == 'moonshotai/kimi-k3':
                return 402, b'{"error":{"code":"insufficient_credits"}}', {}
            return 200, encoded(chat_reply(body, decide(state))), {
                'x-model': body['model'], 'x-reasoning-effort': body['reasoning_effort']}

        def openai(url, headers, raw, timeout):
            body = json.loads(raw)
            calls.append(body['model'])
            state = json.loads(body['input'].split('\n', 1)[1])  # after the JSON label
            texts.append(json.dumps(state))
            return 200, encoded(dict(model=body['model'], status='completed', output=[dict(type='message',
                content=[dict(type='output_text', text=json.dumps(decide(state)))])],
                usage=dict(input_tokens=100, output_tokens=20)))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routing_raw = (gate_a.ROOT / 'config/intelligence/aiand-routing.openai-preferred.example.json').read_bytes() \
                if preferred else RAW
            files = assembled(model_routing_raw=routing_raw, model_routing_sha256=gate_a.digest(routing_raw))
            for name, raw in files.items(): (root / name).write_bytes(raw)
            config = json.loads(files['runtime.json'])
            driver = config['driver']
            for key, name in (('strategy_profile_file', 'strategy-profile.json'),
                              ('session_calendar_file', 'session-calendar.json'),
                              ('model_routing_file', 'model-routing.json')):
                driver[key] = str(root / name)
            driver.update(evidence_root=str(root / 'evidence'), market_artifact_root=str(root / 'market'),
                          model_budget_root=str(root / 'budget'))
            (root / 'evidence').mkdir()
            (root / 'budget').mkdir(mode=0o700)
            budget_options = dict(initial_spent=2_000_000, reserve=0,
                                  pacing=json.loads(routing_raw)['openai_pacing'], clock_ms=clock) \
                if preferred else dict(initial_spent=0)
            budget = ModelBudget.initialize(root / 'budget' / 'openai-budget.sqlite', 'larp-openai-2026',
                                            **budget_options)
            evidence = SQLiteEvidenceStore(str(root / 'evidence' / 'evidence.sqlite'), journal_mode='DELETE')
            source = FakeFilingSource(clock, {1045810: 'NVIDIA'})
            sentence = 'Prior financial statements should no longer be relied upon.'
            source.add(1045810, accession='0001045810-26-000001', form='8-K', items=['4.02'],
                       acceptance='2026-10-19T11:59:00Z', documents=[doc('fixture.htm', '8-K', cover(
                           'NVIDIA', '8-K', ['4.02'], [sentence]))])
            intelligence = load_config('shadow')
            ingestor = Ingestor(registry=load_registry(), source=source, store=evidence,
                                artifacts=FileArtifacts(str(root / 'evidence' / 'artifacts')),
                                config=intelligence, clock_ms=clock, run_id='synthetic-ingest', synthetic=True)
            self.assertEqual(ingestor.poll(issuer).read()['status'], 'OK')
            records = [r.read() for r in evidence.records(issuer)]
            evidence.close()
            request = build_request(job={'job_id': 'routed-preparation'}, run_id=config['run_id'], issuer_id=issuer,
                records=records, cutoff_ms=clock(), context=EMPTY_CONTEXT,
                policy_profile_hash=Document.from_dict(json.loads(files['strategy-profile.json'])).digest('StrategyProfile.v1'),
                allowed_tools=list(intelligence.tools), tool_calls=6, deadline_ms=60000,
                source_health=dict(status='OK', last_success_ms=clock()))
            secrets = dict(AI_SEEDS_ADDRESS=WALLET, BINANCE_API_KEY='synthetic-binance-key',
                           BINANCE_SECRET_KEY='synthetic-binance-secret', LARP_AIAND_API_KEY='synthetic-aiand-key',
                           LARP_MODEL_API_KEY='synthetic-openai-key')
            with patch('larp.intelligence.aiand.https_post_metadata', side_effect=aiand), \
                    patch('larp.intelligence.providers.https_post', side_effect=openai):
                runtime = build_driver(config, Store(), secrets, clock_ms=clock)
            self.assertFalse(runtime.signing)
            router = runtime.coordinator.assessor
            self.addCleanup(router.make_assessor(router.routine).reader.store.close)
            result = router.assess(request)
            assessment_result(result, request, clock())
            self.assertEqual([s['stage'] for s in result.read()['routing']['stages']],
                             ['openai-primary', 'external-review-0', 'external-review-1'] if preferred else ['routine', 'openai-review'])
            self.assertEqual(set(calls), {'moonshotai/kimi-k3', 'zai-org/glm-5.3', 'gpt-6.1-sol'} if preferred
                             else {'zai-org/glm-5.3', 'gpt-6.1-sol'})
            if preferred: self.assertEqual(calls[0], 'gpt-6.1-sol')
            self.assertTrue(all(sentence in text for text in texts))  # Each tier sees original filing text.
            self.assertGreater(budget.snapshot()['charged_micro_usd'], 0)
            budget.admit(budget.snapshot()['available_micro_usd'], 'synthetic-other-usage')
            for secondary in (False, True):
                calls.clear()
                fail_kimi = secondary
                value = router.assess(request).read()
                self.assertNotIn('gpt-6.1-sol', calls)
                self.assertIn('moonshotai/kimi-k3', calls)
                # The first refused admission is retained as an OpenAI stage without a POST;
                # subsequent assessments use the persisted external-only latch directly.
                expected = (['openai-primary'] if preferred else ['routine'] + ([] if secondary else ['openai-review'])) \
                    + ['external-review-0']
                expected += ['external-review-1'] if preferred or secondary else []
                self.assertEqual([s['stage'] for s in value['routing']['stages']], expected)
                self.assertEqual(budget.snapshot()['external_only'], not preferred)
                self.assertLessEqual(value['budget_used']['tool_calls'], 6)
                self.assertLessEqual(value['budget_used']['model_steps'], 10)
                self.assertLessEqual(value['budget_used']['elapsed_ms'], 60000)
                self.assertTrue(value['model_io']['steps'])
            self.assertEqual(budget.snapshot()['reserve_micro_usd'], 0 if preferred else 10_000_000)
