"""GB-CHAIN/REPORT: read-only evidence cannot become signing permission."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.execution import Blocked
from larp.execution_live.chain import Rpc
from larp.marketdata.web3 import Artifacts
from tests.marketdata.test_transport import Response
from tests.execution import test_execution_loop as composition
from tests.strategy.live_fixtures import summary, registry
from larp.strategy.profiles import build_live_profiles
from larp.research.fixtures import snapshot

WALLET = '0x' + '5' * 40
ROUTER = '0x' + '2' * 40
BLOCK = '0x' + 'b' * 64
STAMP = '2026-10-15T01:00:00Z'


USDT_UNITS = 199 * 10**18  # equals the snapshot ledger's 199000000 micro-USDT (GB-2)


class ChainOpener:
    def __init__(self, *, bad=None, usdt=USDT_UNITS, tokens=None):
        self.bad, self.calls, self.blocks = bad, [], 0
        self.usdt, self.tokens = usdt, tokens or {}

    def open(self, request, timeout):
        req = json.loads(request.data)
        method, params = req['method'], req['params']
        self.calls.append((method, params))
        if method == 'eth_chainId': result = '0x1' if self.bad == 'chain' else '0x38'
        elif method == 'eth_getBlockByNumber':
            self.blocks += 1
            result = dict(number='0xa', hash=('0x' + 'e' * 64 if self.bad == 'reorg' and self.blocks > 2 else BLOCK))
        elif method == 'eth_getBalance': result = '0x0' if self.bad == 'zero' else hex(10**18)
        elif method == 'eth_getTransactionCount':
            result = ('0x4' if self.bad == 'pending' and params[-1] == 'pending'
                      else '0x2' if self.bad == 'unfinalized' and params[-1] == '0xa' else '0x3')
        elif method == 'eth_call':
            from larp.execution import USDT
            target, tag = params
            assert tag == '0xa', tag
            if target['data'] == '0x313ce567':
                result = '0x' + format(18, '064x')
            else:
                assert target['data'] == '0x70a08231' + '0' * 24 + WALLET[2:], target['data']
                units = self.usdt if target['to'] == USDT else self.tokens.get(target['to'], 0)
                result = '0x' + format(units, '064x')
        elif method == 'eth_getCode': result = '0x60006000'
        else: raise AssertionError('unexpected endpoint: ' + method)
        return Response(json.dumps(dict(jsonrpc='2.0', id=req['id'], result=result)).encode())


class ChainEvidenceTests(unittest.TestCase):
    def probe(self, root, opener):
        from larp.execution_live.gate_b import probe_chain
        rpc = Rpc('https://rpc.invalid/', artifacts=Artifacts(root), source_id='fixture', opener=opener)
        return probe_chain(rpc, wallet=WALLET, router=ROUTER, observed_at=STAMP)

    def test_gb_chain_finalized_balance_nonce_and_code_are_read_only(self):
        with tempfile.TemporaryDirectory() as root:
            opener = ChainOpener()
            evidence = self.probe(root, opener)
        self.assertEqual(evidence['schema'], 'GateBChainEvidence.v1')
        self.assertEqual(evidence['native_balance_wei'], 10**18)
        self.assertEqual(evidence['finalized_block_hash'], BLOCK)
        self.assertEqual(evidence['router_code_sha256'], hashlib.sha256(bytes.fromhex('60006000')).hexdigest())
        self.assertEqual(evidence['latest_nonce'], evidence['pending_nonce'])
        self.assertFalse(evidence['signing_enabled'])
        self.assertEqual(next(p for m, p in opener.calls if m == 'eth_getBalance'), [WALLET, '0xa'])
        self.assertFalse(any('send' in m.lower() or 'sign' in m.lower() for m, _ in opener.calls))

    def test_gb_chain_wrong_network_and_reorg_refuse(self):
        for bad in ('chain', 'reorg'):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as root, self.assertRaises(Blocked):
                self.probe(root, ChainOpener(bad=bad))

    def test_gb_chain_zero_gas_and_pending_nonce_are_observations_not_readiness(self):
        for bad, reason in (('zero', 'FIRST_BNB_REQUIRED'), ('pending', 'PENDING_NONCE_REQUIRES_RECONCILIATION')):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as root:
                evidence = self.probe(root, ChainOpener(bad=bad))
            self.assertIn(reason, evidence['blockers'])
            self.assertFalse(evidence['signing_enabled'])


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = composition.Composition()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        profile = build_live_profiles(summary(), registry())['REHEARSAL'].read()
        raw = json.dumps(profile).encode()
        (self.root / 'profile.json').write_bytes(raw)
        config = dict(self.fixture.config, strategy_profile_sha256=hashlib.sha256(raw).hexdigest())
        config_raw = json.dumps(config).encode()
        path = self.root / 'execution.json'
        path.write_bytes(config_raw)
        self.inputs = dict(schema='GateBInputs.v1', build_id='a' * 40, run_id='run', wallet=WALLET,
            chain_max_age_seconds=300, files=dict(execution_config=dict(path=str(path),
                sha256=hashlib.sha256(config_raw).hexdigest())))

    def report(self, inputs=None):
        from larp.execution_live.gate_b import readiness_report
        return readiness_report(self.inputs if inputs is None else inputs, now=STAMP, base_dir=self.root)

    def test_gb_report_uses_real_profile_validator_and_never_authorizes_signing(self):
        result = self.report()
        self.assertEqual(result['checks']['DR-09']['status'], 'VALIDATED')
        self.assertEqual(result['checks']['DR-04']['status'], 'VALIDATED')
        self.assertEqual(result['checks']['DR-02']['status'], 'BLOCKED')
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertFalse(result['signing_enabled'])
        self.assertEqual(set(result['checks']), {'DR-' + str(i).zfill(2) for i in [*range(1, 17), 18, 19, 20]})

    def test_gb_report_tampered_config_or_profile_cannot_validate(self):
        for name, dr in (('execution.json', 'DR-04'), ('profile.json', 'DR-09')):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            try:
                self.assertEqual(self.report()['checks'][dr]['status'], 'BLOCKED')
            finally:
                path.write_bytes(original)

    def test_gb_report_rejects_stale_or_wrong_wallet_chain_capture(self):
        with tempfile.TemporaryDirectory() as root:
            capture = ChainEvidenceTests().probe(root, ChainOpener())
        capture['source_id'] = 'fixture-rpc'
        raw = json.dumps(capture).encode()
        path = self.root / 'chain.json'
        path.write_bytes(raw)
        inputs = deepcopy(self.inputs)
        inputs['files']['chain'] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest())
        self.assertIn('snapshot checked', self.report(inputs)['checks']['DR-03']['detail'])
        for changes in (dict(wallet=ROUTER), dict(chain_id=1), dict(observed_at='2026-10-14T01:00:00Z')):
            with self.subTest(changes=changes):
                raw = json.dumps(dict(capture, **changes)).encode()
                path = self.root / 'chain.json'
                path.write_bytes(raw)
                inputs = deepcopy(self.inputs)
                inputs['files']['chain'] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest())
                self.assertEqual(self.report(inputs)['checks']['DR-03']['status'], 'BLOCKED')
                self.assertIn('missing, blocked, stale or mismatched', self.report(inputs)['checks']['DR-03']['detail'])

    def test_gb_report_initial_projection_checks_exact_funded_native_scale(self):
        with tempfile.TemporaryDirectory() as root:
            capture = ChainEvidenceTests().probe(root, ChainOpener())
        capture['source_id'] = 'fixture-rpc'
        ledger = snapshot().context.read()['portfolio']
        ledger.update(mode='dev', run_id='run', wallet_id=WALLET, bnb_decimals=18, bnb_units=10**18)
        inputs = deepcopy(self.inputs)
        for name, value in (('chain', capture), ('initial_state', ledger)):
            path = self.root / (name + '.json')
            raw = json.dumps(value).encode()
            path.write_bytes(raw)
            inputs['files'][name] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest())
        self.assertIn('funding/18-decimal ledger checked', self.report(inputs)['checks']['DR-06']['detail'])
        ledger['bnb_decimals'] = 6
        raw = json.dumps(ledger).encode()
        path.write_bytes(raw)
        inputs['files']['initial_state']['sha256'] = hashlib.sha256(raw).hexdigest()
        self.assertIn('absent or mismatched', self.report(inputs)['checks']['DR-06']['detail'])

    def test_gb_report_untrusted_ready_flag_is_rejected(self):
        with self.assertRaises(Blocked):
            self.report(dict(self.inputs, ready=True))

    def test_gb_report_cli_writes_external_artifact_without_reading_secrets(self):
        from larp.execution_live.gate_b import main
        with tempfile.TemporaryDirectory() as root, io.StringIO() as output, \
                patch.dict('os.environ', dict(WALLET_PRIVATE_KEY='DO_NOT_READ_KEY', AI_SEEDS_SECRET='DO_NOT_READ_AUDIT')), \
                redirect_stdout(output):
            code = main(['report', '--artifact-root', root])
            self.assertEqual(code, 2)
            reports = list(Path(root).glob('*.json'))
            self.assertEqual(len(reports), 1)
            result = json.loads(reports[0].read_bytes())
            self.assertEqual(reports[0].stem, hashlib.sha256(reports[0].read_bytes()).hexdigest())
            self.assertFalse(result['signing_enabled'])
            self.assertNotIn('DO_NOT_READ', reports[0].read_text() + output.getvalue())


class ChainGaps(unittest.TestCase):
    """IDEA-039 GB-CHAIN-20261016: GB-1 unfinalized transactions, GB-2 full starting-balance cross-check."""

    def setUp(self):
        self.reports = ReportTests('test_gb_report_untrusted_ready_flag_is_rejected')
        self.reports.setUp()
        self.addCleanup(self.reports.doCleanups)

    def capture(self, **kw):
        with tempfile.TemporaryDirectory() as root:
            capture = ChainEvidenceTests().probe(root, ChainOpener(**kw))
        capture['source_id'] = 'fixture-rpc'
        return capture

    def pinned(self, **values):
        inputs = deepcopy(self.reports.inputs)
        for name, value in values.items():
            raw = json.dumps(value).encode()
            path = self.reports.root / (name + '.json')
            path.write_bytes(raw)
            inputs['files'][name] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest())
        return self.reports.report(inputs)['checks']

    @staticmethod
    def ledger():
        ledger = snapshot().context.read()['portfolio']
        ledger.update(mode='dev', run_id='run', wallet_id=WALLET, bnb_decimals=18, bnb_units=10**18)
        return ledger

    def test_gb1a_a_mined_but_unfinalized_transaction_is_a_blocker(self):
        good, bad = self.capture(), self.capture(bad='unfinalized')
        self.assertEqual((good['finalized_nonce'], good['latest_nonce']), (3, 3))
        self.assertNotIn('UNFINALIZED_TRANSACTION_REQUIRES_RECONCILIATION', good['blockers'])
        self.assertEqual(bad['finalized_nonce'], 2)
        self.assertIn('UNFINALIZED_TRANSACTION_REQUIRES_RECONCILIATION', bad['blockers'])

    def test_gb1b_dr03_refuses_missing_or_mismatched_finalized_nonce(self):
        capture = self.capture()
        self.assertIn('snapshot checked', self.pinned(chain=capture)['DR-03']['detail'])
        missing = dict(capture); missing.pop('finalized_nonce')
        for value in (missing, dict(capture, finalized_nonce=2), dict(capture, finalized_nonce='3'),
                      dict(capture, finalized_nonce=3.0)):  # equal to 3, but not an integer quantity
            with self.subTest(value=value.get('finalized_nonce')):
                # DR-03 is always BLOCKED pending owner acceptance; the detail says whether the snapshot passed.
                self.assertIn('missing, blocked, stale or mismatched', self.pinned(chain=value)['DR-03']['detail'])

    def test_gb2a_usdt_and_every_bstock_are_read_at_the_finalized_block(self):
        from larp.execution import USDT
        from larp.marketdata.port import TOKENS
        capture = self.capture(tokens={TOKENS['NVDAB']: 7})
        self.assertEqual(set(capture['tokens']), {'USDT', *TOKENS})
        self.assertEqual(capture['tokens']['USDT'], dict(contract=USDT, decimals=18, units=USDT_UNITS))
        self.assertEqual(capture['tokens']['NVDAB']['units'], 7)

    def test_gb2b_dr06_cross_checks_cash_and_positions(self):
        from larp.marketdata.port import TOKENS
        ok = 'funding/18-decimal ledger checked'
        self.assertIn(ok, self.pinned(chain=self.capture(), initial_state=self.ledger())['DR-06']['detail'])
        held = self.ledger()
        held['positions']['NVDAB'] = dict(units=5 * 10**18, decimals=18, cost_basis_units=1)
        self.assertIn(ok, self.pinned(chain=self.capture(tokens={TOKENS['NVDAB']: 5 * 10**18}),
                                      initial_state=held)['DR-06']['detail'])
        unknown = self.ledger()
        unknown['positions']['XYZB'] = dict(units=0, decimals=18, cost_basis_units=0)
        for name, chain, ledger in (
                ('usdt differs', self.capture(usdt=USDT_UNITS + 10**12), self.ledger()),
                ('chain holds a bStock the ledger lacks', self.capture(tokens={TOKENS['SKHYB']: 1}), self.ledger()),
                ('ledger holds more than chain', self.capture(tokens={TOKENS['NVDAB']: 4 * 10**18}), held),
                ('unknown position', self.capture(), unknown)):
            with self.subTest(name):
                checks = self.pinned(chain=chain, initial_state=ledger)
                self.assertEqual(checks['DR-06']['status'], 'BLOCKED')
                self.assertIn('absent or mismatched', checks['DR-06']['detail'])
