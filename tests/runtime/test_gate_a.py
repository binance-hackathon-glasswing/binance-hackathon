"""IDEA-057 GA01..GA06. Synthetic responses only; no network, real keys, signing or upload."""
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
    return build_live_profiles(Document.from_dict(s), registry())['REHEARSAL'].read()


def assembled(**changes):
    configs = render_host_configs.render(render_host_configs.outputs(terraform_output()), WALLET, 'c' * 64)
    args = dict(profile_raw=encoded(profile()), capture_raw=encoded(captured()),
                calendar_raw=(gate_a.ROOT / 'config/runtime/session-calendar.2026.json').read_bytes(),
                run_id='gate-a-test', build_id='b' * 40, now=NOW)
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
