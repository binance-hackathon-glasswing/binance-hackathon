"""IDEA-058 GA01..GA06. Synthetic responses only; no network, real keys, signing or upload."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.execution import USDT
from larp.intelligence.config import load_config, load_registry
from larp.marketdata.port import TOKENS, NATIVE
from larp.marketdata.web3 import encoded
from larp.runtime import gate_a
from larp.runtime.service import build_driver
from larp.sources.live import Refused, check_shadow_scope
from tests.integration.test_evidence_pipeline import PipelineHarness
from tests.runtime.test_deploy_presetup import terraform_output
from tests.strategy.live_fixtures import summary, registry
from larp.strategy.profiles import build_live_profiles
import sys
sys.path.insert(0, str(gate_a.ROOT / 'tools/deploy'))
import prepare_shadow
import render_host_configs

WALLET = '0x' + '1' * 40
NOW = '2026-10-19T12:00:00Z'


def observed(endpoint, method, rows, params):
    value = dict(schema='Web3Observation.v1', source_id='BINANCE_WEB3', endpoint=endpoint,
                 method=method, outcome='ok', available_at=NOW, params=params,
                 response=dict(code=0, data=rows))
    return dict(value, artifact_sha256=gate_a.digest(encoded(value)))


def captured():
    tickers = dict(NVDAB='NVDA', GOOGLB='GOOGL', TSLAB='TSLA', MSFTB='MSFT', SKHYB='SKHY')
    rows = [dict(tokenContractAddress=token, tokenSymbol=s, underlyingTicker=tickers[s],
                 decimals='18', binanceChainId='56') for s, token in TOKENS.items()]
    params = dict(address=WALLET, tokenContractAddresses=[dict(binanceChainId='56', tokenContractAddress=t)
                                                        for t in ('', USDT, *TOKENS.values())])
    balances = [dict(tokenContractAddress=USDT, rawBalance=str(100 * 10**18)),
                dict(tokenContractAddress=NATIVE, rawBalance=str(10**15))]
    return dict(schema='GateAInputs.v1', wallet=WALLET, observed_at=NOW,
                metadata=observed('market/rwa/tokens', 'GET', rows, dict(binanceChainId='56', platformId='bstock')),
                balances=observed('balance/token-balances-by-address', 'POST', [dict(tokenAssets=balances)], params))


def rehash(capture):
    for name in ('metadata', 'balances'):
        r = capture[name]
        r['artifact_sha256'] = gate_a.digest(encoded({k: v for k, v in r.items() if k != 'artifact_sha256'}))
    return capture


def profile():
    s = summary().read()
    s['bnb_decimals'] = 18
    s['bnb_price_units'] = 700_000_000
    for row in s['symbols'].values():
        row.update(approve_gas_bnb_units=10**10, swap_gas_bnb_units=2 * 10**10)
    published = Document.from_dict(json.loads((gate_a.ROOT / 'config/intelligence/red_flags.v1.json').read_bytes()))
    return build_live_profiles(Document.from_dict(s), published)['REHEARSAL'].read()


def assembled(**changes):
    configs = render_host_configs.render(render_host_configs.outputs(terraform_output()), WALLET, 'c' * 64)
    args = dict(profile_raw=encoded(profile()), capture_raw=encoded(captured()),
                calendar_raw=(gate_a.ROOT / 'config/runtime/session-calendar.2026.json').read_bytes(),
                run_id='gate-a-test', build_id='b' * 40, now=NOW,
                balance_rpc_url='https://rpc.invalid/', balance_rpc_source_id='synthetic-rpc')
    args.update(changes)
    return gate_a.prepare(configs, **args)


class GateAInputs(unittest.TestCase):
    def test_ga01_observed_tickers_map_to_separate_sec_issuers_without_verifying_ratios(self):
        entries = load_registry()
        result = gate_a.issuer_map(captured())
        self.assertEqual(len(result), 5)
        self.assertEqual(result['SEC-CIK-0001045810'], dict(token='NVDAB', underlying_id='NVDA'))
        self.assertTrue(all(e.token_underlying_status == 'UNVERIFIED' for e in entries.entries))

    def test_ga01_wrong_duplicate_missing_or_changed_metadata_refuses(self):
        for defect in ('wrong_token', 'wrong_ticker', 'wrong_chain', 'duplicate', 'missing', 'decimals', 'tamper'):
            c = captured()
            rows = c['metadata']['response']['data']
            if defect == 'wrong_token': rows[0]['tokenSymbol'] = 'TSLAB'
            if defect == 'wrong_ticker': rows[0]['underlyingTicker'] = 'MSFT'
            if defect == 'wrong_chain': rows[0]['binanceChainId'] = '1'
            if defect == 'duplicate': rows.append(copy.deepcopy(rows[0]))
            if defect == 'missing': rows.pop()
            if defect == 'decimals': rows[0]['decimals'] = '31'
            if defect == 'tamper': rows[0]['underlyingTicker'] = 'GOOGL'
            else: rehash(c)
            with self.subTest(defect), self.assertRaises(ContractError):
                gate_a.issuer_map(c)

    def test_ga04_actual_cash_and_native_units_preserved_and_stock_holdings_refused(self):
        c = captured()
        c['balances']['response']['data'][0]['tokenAssets'][0]['rawBalance'] = str(100 * 10**18 + 123)
        rehash(c)
        state = gate_a.initial_state(c, profile(), 'run')
        self.assertEqual((state['cash_units'], state['bnb_units'], state['bnb_decimals']), (100_000_000, 10**15, 18))
        self.assertEqual(state['opening_equity_units'], 100_700_000)
        self.assertTrue(all(p['units'] == 0 for p in state['positions'].values()))
        c['balances']['response']['data'][0]['tokenAssets'].append(
            dict(tokenContractAddress=TOKENS['NVDAB'], rawBalance='1'))
        rehash(c)
        with self.assertRaises(ContractError): gate_a.initial_state(c, profile(), 'run')

    def test_ga04_an_unrelated_token_cannot_override_an_eligible_tokens_decimals(self):
        c = captured()
        c['metadata']['response']['data'].append(dict(tokenSymbol='NVDAB', decimals='4',
            tokenContractAddress='0x' + '3' * 40, binanceChainId='56', underlyingTicker='NVDA'))
        rehash(c)
        gate_a.issuer_map(c)
        self.assertEqual(gate_a.initial_state(c, profile(), 'run')['positions']['NVDAB']['decimals'], 18)

    def test_ga04_balance_identity_duplicates_scales_and_request_coverage_refuse(self):
        for defect in ('wallet', 'request', 'duplicate', 'negative', 'fraction', 'unknown', 'chain'):
            c = captured()
            rows = c['balances']['response']['data'][0]['tokenAssets']
            if defect == 'wallet': c['wallet'] = '0x' + '2' * 40
            if defect == 'request': c['balances']['params']['tokenContractAddresses'].pop()
            if defect == 'duplicate': rows.append(copy.deepcopy(rows[0]))
            if defect == 'negative': rows[0]['rawBalance'] = '-1'
            if defect == 'fraction': rows[0]['rawBalance'] = '1.5'
            if defect == 'unknown': rows[0]['tokenContractAddress'] = '0x' + '3' * 40
            if defect == 'chain': rows[0]['binanceChainId'] = '1'
            rehash(c)
            with self.subTest(defect), self.assertRaises((ContractError, RuntimeError)):
                gate_a.raw_balances(c)

    def test_ga04_capture_calls_only_metadata_and_balances(self):
        c = captured()
        class Client:
            def __init__(self): self.calls = []
            def request(self, method, endpoint, params):
                self.calls.append((method, endpoint))
                return c['metadata' if endpoint == 'market/rwa/tokens' else 'balances']
        client = Client()
        gate_a.capture_inputs(client, WALLET)
        self.assertEqual(client.calls, [('GET', 'market/rwa/tokens'), ('POST', 'balance/token-balances-by-address')])

    def test_ga02_assembly_pins_inputs_and_never_emits_execution_or_signer_config(self):
        files = assembled()
        runtime = json.loads(files['runtime.json'])
        self.assertEqual((runtime['mode'], runtime['driver']['execution'], runtime['driver']['intelligence_mode']),
                         ('dev', 'shadow', 'shadow'))
        self.assertEqual(runtime['driver']['cadence_ms'], 900_000)
        self.assertEqual(runtime['driver']['day_roll_window_ms'], 300_000)
        for key, name in (('strategy_profile', 'strategy-profile.json'), ('session_calendar', 'session-calendar.json')):
            self.assertEqual(runtime['driver'][key + '_sha256'], gate_a.digest(files[name]))
        self.assertEqual(runtime['initial_state_sha256'], gate_a.digest(files['initial-state.json']))
        self.assertNotIn('execution.json', files)
        self.assertNotIn('signer.json', files)
        report = json.loads(files['preparation-report.json'])
        self.assertFalse(report['gate_a_passed'])
        self.assertIn('SEC_CONTACT', report['missing_inputs'])
        self.assertTrue(all(s == 'NOT_RUN' for s in report['host_checks'].values()))

    def test_ga02_stale_future_fixture_final_and_bad_build_refuse(self):
        for changes in (dict(now='2026-10-19T12:05:01Z'), dict(now='2026-10-19T11:59:59Z'),
                        dict(build_id='uncommitted'), dict(run_id='../escape'),
                        dict(profile_raw=encoded(dict(profile(), mode='OFFLINE_FIXTURE'))),
                        dict(profile_raw=encoded(dict(profile(), environment='FINAL')))):
            with self.subTest(changes), self.assertRaises(ContractError): assembled(**changes)

    def test_ga02_missing_contact_has_no_silent_example_identity_and_new_writes_only(self):
        self.assertNotIn('evidence.env', assembled())
        files = assembled(sec_contact='LARP Test test-contact@larp.test')
        self.assertIn(b'LARP_EVIDENCE_CONFIG_MODE=shadow', files['evidence.env'])
        with tempfile.TemporaryDirectory() as tmp, patch.object(render_host_configs, 'ignored_by_git', return_value=True):
            out = Path(tmp) / 'new'
            prepare_shadow.write_new(out, files)
            with self.assertRaises(ContractError): prepare_shadow.write_new(out, files)

    def test_ga03_shadow_settings_are_explicit_and_live_still_refuses(self):
        c = load_config('shadow')
        self.assertEqual((c.mode, c.p('initial_backfill_ms'), c.p('max_clock_skew_ms')), ('shadow', 30*86400000, 300000))
        with self.assertRaises(ValueError): load_config('live')
        for mode, execution, intelligence in (('live', 'shadow', 'shadow'), ('dev', 'service', 'shadow'),
                                              ('dev', 'shadow', 'development'), ('live', 'service', 'development')):
            config = json.loads(assembled()['runtime.json'])
            config['mode'] = mode
            config['driver'].update(execution=execution, intelligence_mode=intelligence)
            with self.subTest(mode=mode, execution=execution), self.assertRaises(ContractError):
                build_driver(config, None, {})  # rejects before any DB, key or external I/O

    def test_ga03_ingestion_checks_unsigned_scope_and_manifest_runtime_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'runtime.json'
            for mode, execution in (('dev', 'service'), ('live', 'shadow'), ('offline', 'shadow')):
                p.write_text(json.dumps(dict(mode=mode, driver=dict(execution=execution, intelligence_mode='shadow'))))
                with self.assertRaises(Refused): check_shadow_scope(p)
            p.write_bytes(assembled()['runtime.json'])
            check_shadow_scope(p)
            m = Path(tmp) / 'release.json'
            m.write_text('{}')
            with patch('larp.runtime.preflight.verify_release'), self.assertRaises(Refused):
                check_shadow_scope(p, release_manifest=m, release_root=tmp)
            with self.assertRaises(Refused): check_shadow_scope(None)


class GateAComposition(PipelineHarness):
    def test_ga06_prepared_inputs_initialize_activate_build_run_and_restart_real_components(self):
        from larp.audit.delivery import DeliveryWorker
        from larp.intelligence.fakes import FakeClock, FakeFilingSource
        from larp.intelligence.ingest import Ingestor
        from larp.intelligence.scenarios import cover, doc
        from larp.marketdata.web3 import Unavailable
        from larp.runtime.fixtures import FakeReceiver
        from larp.runtime.service import Service, init_run, activate_run, verify_registered_manifest
        from larp.runtime.supervision import Guard
        from larp.sources.store import SQLiteEvidenceStore, FileArtifacts
        from larp.runtime.live import check_live_start

        files = assembled()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, raw in files.items(): (root / name).write_bytes(raw)
            config = json.loads(files['runtime.json'])
            config['initial_state_file'] = str(root / 'initial-state.json')
            config.update(ai_seeds_dir=str(root / 'ai-seeds'), nonce_dir=str(root / 'nonce'))
            for key, name in (('strategy_profile_file', 'strategy-profile.json'),
                              ('session_calendar_file', 'session-calendar.json')):
                config['driver'][key] = str(root / name)
            config['driver'].update(evidence_root=str(root / 'evidence'), market_artifact_root=str(root / 'market'))
            clock = FakeClock(int(gate_a.instant(NOW).timestamp() * 1000))
            evidence_root = root / 'evidence'
            evidence_root.mkdir()
            evidence = SQLiteEvidenceStore(str(evidence_root / 'evidence.sqlite'), journal_mode='DELETE')
            artifacts = FileArtifacts(str(evidence_root / 'artifacts'), group_readable=True)
            source = FakeFilingSource(clock, {1045810: 'NVIDIA'})
            source.add(1045810, accession='0001045810-26-000001', form='8-K', items=['2.02'],
                       acceptance='2026-10-19T11:59:00Z', documents=[doc('fixture.htm', '8-K', cover(
                           'NVIDIA', '8-K', ['2.02'], ['Synthetic transport fixture: results were announced.']))])
            ingestor = Ingestor(registry=load_registry(), source=source, store=evidence, artifacts=artifacts,
                                config=load_config('shadow'), clock_ms=clock, run_id='fixture-ingest', synthetic=True)
            result = ingestor.poll('SEC-CIK-0001045810').read()
            self.assertEqual(result['status'], 'OK')
            self.assertTrue(result['new_records'])
            evidence.close()
            init_run(config, self.store)
            manifest = Document.from_dict(dict(schema='ReleaseManifest.v1', build_id=config['build_id'],
                repository='synthetic', runtime_config_sha256=gate_a.digest(encoded(config)),
                release_register=dict(services_sha256='a'*64, deviations_sha256='c'*64)))
            activate_run(config, self.store, manifest, reviewer='synthetic-reviewer',
                         review_ref='IDEA-058-GA06', now_ms=clock())
            verify_registered_manifest(self.store, config, manifest)
            original = copy.deepcopy(self.store.load(config['run_id']).read()['projection']['portfolio'])
            secrets = dict(AI_SEEDS_ADDRESS=WALLET, BINANCE_API_KEY='synthetic-key', BINANCE_SECRET_KEY='synthetic-secret')

            def transport(client, method, endpoint, params):
                if endpoint == 'market/rwa/tokens': return captured()['metadata']
                if endpoint in ('market/rwa/underlying-market', 'market/rwa/price'):
                    row = dict(tokenContractAddress=params.get('tokenContractAddress', params.get('tokenContractAddresses')),
                               tokenPrice='100', statusInfo=dict(openState=True))
                    return observed(endpoint, method, [row], params)
                raise Unavailable('SYNTHETIC_UNQUALIFIED_QUOTE')

            from larp.execution import DependencyUnavailable

            def node_down(rpc, method, params):  # IDEA-055's balance check, kept offline: the node is unavailable
                raise DependencyUnavailable('RPC unavailable')
            with patch('larp.marketdata.web3.Web3Client.request', transport), \
                    patch('larp.execution_live.chain.Rpc.call', node_down), \
                    patch.object(self.store, 'command', side_effect=AssertionError('shadow must never claim signing authority')):
                for attempt in range(2):
                    driver = build_driver(config, self.store, secrets, clock_ms=clock)
                    self.addCleanup(driver.ports['evidence'].close)
                    check_live_start(mode='dev', ports=driver.ports, secrets=secrets,
                                     wallet_address=WALLET, run_wallet=WALLET,
                                     ai_seeds_dir=config['ai_seeds_dir'], nonce_dir=config['nonce_dir'])
                    service = Service(self.store, config['run_id'], config['build_id'],
                                      guard=Guard(self.store, config['run_id'], max_failures=3, clear_after=2),
                                      driver=driver, clock_ms=clock, session_id='shadow-test-' + str(attempt))
                    self.assertEqual(service.run(max_cycles=1), 0)
                    clock.advance(1000)
            current = self.store.load(config['run_id']).read()
            self.assertEqual(current['projection']['portfolio'], original)
            self.assertFalse(current['reservations'])
            self.assertFalse(self.store.open_rounds(config['run_id']))
            # Closed rounds are intentionally pruned from the projection; their
            # immutable planned records remain in the journal.
            records = [b.read()['event']['record'] for b in self.store.journal(config['run_id'])
                       if b.read()['event']['kind'] == 'ROUND_PLANNED']
            self.assertTrue(records)
            for record in records:
                self.assertFalse([e for e in record['errors'] if e.startswith(('CONTEXT_UNAVAILABLE', 'PLANNER_UNAVAILABLE'))])
                self.assertEqual(record['policy_input']['context']['portfolio']['mode'], 'DEV')
            with self.store.transaction() as db:
                logs = db.execute('SELECT document FROM audit_events WHERE run_id=%s', (config['run_id'],)).fetchall()
                executions = db.execute('SELECT count(*) FROM execution_records WHERE run_id=%s', (config['run_id'],)).fetchone()[0]
            self.assertTrue(logs)
            self.assertEqual(executions, 0)
            for (raw,) in logs:
                log = json.loads(Document(bytes(raw)).read()['log'])['data']
                self.assertTrue(log['input']['example'])
                self.assertTrue(all('tx_hash' not in order for order in log['orders']))
            receiver = DeliveryWorker(self.store, FakeReceiver(), retry_ms=1)
            while receiver.once(config['run_id'], current['epoch'], clock()): pass
            self.assertEqual(len(receiver.status(config['run_id'])['delivered']), len(logs))
            # Replay re-executes policy/planner from recorded ports; it must never call Web3.
            from larp.integration.replay import replay_live
            from larp.integration.runtime import initial_projection, initial_policy_state, StrategyPolicy, RuntimePlanner
            from larp.integration.settlement import ExecutionBridge, settle
            from larp.storage.postgres import doc as document
            batches, head = self.store.journal(config['run_id']), self.store.verify(config['run_id'])
            with self.store.transaction() as db:
                db.execute('TRUNCATE runs CASCADE')  # only this harness's disposable schema
            with patch('larp.marketdata.web3.Web3Client.request', side_effect=AssertionError('replay must be offline')):
                replayed = replay_live(batches, document(initial_projection(original)), self.store,
                    builder=driver.coordinator.context_builder, run_id=config['run_id'], wallet_id=WALLET,
                    chain_id=56, version_id=config['build_id'], profile_hash=driver.coordinator.profile_hash,
                    address=WALLET, policy=StrategyPolicy(), planner=driver.coordinator.planner,
                    execution=ExecutionBridge(), reducer=settle, test_rounds=True, require_version=True,
                    initial_policy_state=initial_policy_state(config['run_id'], json.loads(files['strategy-profile.json'])))
            self.assertEqual(replayed, head)
            self.assertEqual(self.store.load(config['run_id']).read()['mode'], 'offline')


class PortedFromPr89(unittest.TestCase):
    """IDEA-058 GA07-GA09: checks ported from the closed PR #89."""

    def test_ga07_each_pair_must_pass_the_evidence_contracts_issuer_rule(self):
        from unittest.mock import patch
        from larp.integration import contract
        real = contract._issuer_matches
        seen = []

        def rule(record, underlying, *, source_id=None):
            seen.append((record['issuer_id'], underlying, source_id))
            return False if record['token'] == 'TSLAB' else real(record, underlying, source_id=source_id)
        with patch.object(contract, '_issuer_matches', side_effect=rule):
            with self.assertRaisesRegex(ContractError, 'TSLAB'):
                gate_a.issuer_map(captured())
        self.assertTrue(seen and all(s == 'BINANCE_WEB3' for _, _, s in seen))
        self.assertEqual(len(gate_a.issuer_map(captured())), 5)  # the real rule accepts every registry pair

    def test_ga08_the_initial_state_is_self_checked_before_it_is_pinned(self):
        from unittest.mock import patch
        capture = captured()
        state = gate_a.initial_state(capture, profile(), 'gate-a-test')
        gate_a.check_initial_state(state, capture)  # the real state passes
        bad = {
            'wei': dict(bnb_decimals=6),
            'mode': dict(mode='LIVE'),
            'wallet': dict(wallet_id='0x' + '2' * 40),
            'negative': dict(cash_units=-1),
            'schema': dict(schema='PortfolioState.v0'),
        }
        for name, change in bad.items():
            with self.subTest(name), self.assertRaises(ContractError):
                gate_a.check_initial_state(dict(state, **change), capture)
        with patch('larp.integration.runtime.ledger_from', side_effect=ValueError('disagrees')), \
                self.assertRaisesRegex(ContractError, 'ledger'):
            gate_a.check_initial_state(state, capture)
        with patch.object(gate_a, 'check_initial_state', side_effect=ContractError('self-check called')), \
                self.assertRaisesRegex(ContractError, 'self-check called'):
            gate_a.initial_state(capture, profile(), 'gate-a-test')

    def test_ga09_no_bnb_is_reported_for_gate_b_not_refused_for_shadow(self):
        funded = json.loads(assembled()['preparation-report.json'])
        self.assertNotIn('FIRST_BNB (Q-03)', funded['missing_inputs'])
        capture = captured()
        capture['balances']['response']['data'][0]['tokenAssets'] = [
            dict(tokenContractAddress=USDT, rawBalance=str(100 * 10**18))]
        unfunded = json.loads(assembled(capture_raw=encoded(rehash(capture)))['preparation-report.json'])
        self.assertIn('FIRST_BNB (Q-03)', unfunded['missing_inputs'])


class BalanceRpcSettings(unittest.TestCase):
    """IDEA-058 GA10: #84 (IDEA-055) requires the balance RPC for a dev start."""

    def test_ga10_the_balance_rpc_is_written_or_reported_missing(self):
        driver = json.loads(assembled()['runtime.json'])['driver']
        self.assertEqual((driver['balance_rpc_url'], driver['balance_rpc_source_id']),
                         ('https://rpc.invalid/', 'synthetic-rpc'))
        self.assertEqual((driver['balance_check_interval_ms'], driver['balance_check_max_age_ms']), (600000, 1800000))
        files = assembled(balance_rpc_url=None, balance_rpc_source_id=None)
        self.assertIsNone(json.loads(files['runtime.json'])['driver']['balance_rpc_url'])
        self.assertIn('BALANCE_RPC', json.loads(files['preparation-report.json'])['missing_inputs'])
        self.assertNotIn('BALANCE_RPC', json.loads(assembled()['preparation-report.json'])['missing_inputs'])
        with self.assertRaises(ContractError):
            assembled(balance_rpc_url='http://rpc.invalid/')


class Node:
    """A synthetic BSC node for GA11: one finalized block, balances matching `captured()`, nonces per tag."""

    def __init__(self, *, finalized=4, latest=4, pending=4, native=10**15, usdt=100 * 10**18, tokens=None):
        self.nonce = dict(finalized=finalized, latest=latest, pending=pending)
        self.native, self.usdt, self.tokens, self.calls, self.chain_id = native, usdt, tokens or {}, [], 56

    def call(self, method, params):
        self.calls.append(method)
        if method == 'eth_chainId':
            return hex(self.chain_id)
        if method == 'eth_getBlockByNumber':
            return dict(number=hex(500), hash='0x' + 'd' * 64)
        if method == 'eth_getBalance':
            return hex(self.native)
        if method == 'eth_call':
            target = params[0]
            if target['data'] == '0x313ce567':
                return '0x' + format(18, '064x')
            units = self.usdt if target['to'] == USDT else self.tokens.get(target['to'], 0)
            return '0x' + format(units, '064x')
        if method == 'eth_getTransactionCount':
            return hex(self.nonce['finalized' if params[1] == hex(500) else params[1]])
        raise AssertionError(method)


def with_chain(node=None, **changes):
    capture = captured()
    capture['chain'] = gate_a.chain_capture(node or Node(), WALLET, observed_at=NOW)
    capture['chain'].update(changes)
    return capture


class PendingNonce(unittest.TestCase):
    """IDEA-058 GA11: no starting state while a wallet transaction is in flight; chain and kit balances agree."""

    def refused(self, capture, cause):
        with self.assertRaises(ContractError) as caught:
            assembled(capture_raw=encoded(capture))
        self.assertIn(cause, str(caught.exception))

    def test_ga11a_pending_or_unfinalized_transaction_refuses(self):
        for nonces in (dict(pending=5), dict(latest=5, pending=5)):
            with self.subTest(**nonces):
                self.refused(with_chain(Node(**nonces)), 'in flight')

    def test_ga11a_capture_refuses_before_writing(self):
        class Client:
            def request(self, method, endpoint, params):
                c = captured()
                name = 'metadata' if endpoint == 'market/rwa/tokens' else 'balances'
                return c[name]
        with patch.object(gate_a, 'MarketPort') as port:
            port.return_value.metadata.return_value = {next(iter(TOKENS)): (None, captured()['metadata'])}
            port.return_value.balances.return_value = captured()['balances']
            with self.assertRaises(ContractError) as caught:
                gate_a.capture_inputs(Client(), WALLET, rpc=Node(pending=5))
            self.assertIn('in flight', str(caught.exception))
            value = gate_a.capture_inputs(Client(), WALLET, rpc=Node())
            self.assertEqual(value['chain']['pending_nonce'], 4)

    def test_ga11b_chain_and_kit_balances_must_agree(self):
        for node in (Node(native=10**15 + 1), Node(usdt=1), Node(tokens={TOKENS['NVDAB']: 1})):
            with self.subTest(node=vars(node)):
                self.refused(with_chain(node), 'differ')

    def test_ga11b_other_wallet_chain_or_stale_capture_refuses(self):
        self.refused(with_chain(wallet='0x' + '2' * 40), 'another wallet')
        self.refused(with_chain(chain_id=1), 'another wallet')
        self.refused(with_chain(observed_at='2026-10-19T11:54:00Z'), 'stale')
        self.refused(with_chain(observed_at='2026-10-19T12:01:00Z'), 'stale')

    def test_ga11c_missing_chain_read_is_reported_not_refused(self):
        report = json.loads(assembled()['preparation-report.json'])
        self.assertIn('CHAIN_BALANCE_CAPTURE', report['missing_inputs'])
        report = json.loads(assembled(capture_raw=encoded(with_chain()))['preparation-report.json'])
        self.assertNotIn('CHAIN_BALANCE_CAPTURE', report['missing_inputs'])

    def test_ga11d_only_read_methods_are_called(self):
        node = Node()
        gate_a.chain_capture(node, WALLET, observed_at=NOW)
        self.assertLessEqual(set(node.calls), {'eth_chainId', 'eth_getBlockByNumber', 'eth_getBalance', 'eth_call',
                                               'eth_getTransactionCount'})
        from larp.execution_live.chain import METHODS
        self.assertLessEqual(set(node.calls) - {'eth_call'}, METHODS)
