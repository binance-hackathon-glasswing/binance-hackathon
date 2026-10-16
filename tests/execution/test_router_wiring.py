"""IDEA-070 R5-R7: the capability gates open only with a decoder pinned to router evidence.

Synthetic evidence only (see tests/execution/test_router_decoder.py). No network: composed clients are constructed,
never called.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from larp.contracts import ContractError
from larp.execution import USDT, Blocked, Executor
from larp.execution_live.main import NotIntegrated, build_execution, router_decoder
from larp.execution_live.router import PinnedRouterDecoder
from larp.execution_live.venue import UnverifiedRouter
from larp.signer import service as signer_service
from larp.signer.policy import SigningPolicy
from tests.execution import test_execution_loop as loop_fixtures
from tests.execution.test_router_decoder import ROUTER, TOKEN, calldata, evidence, payload
from tests.execution_fixtures import intent


class Port:
    def __init__(self, mode):
        self.mode = mode


class Imposter:
    mode = 'verified'

    def decode(self, payload):
        raise AssertionError('never called')


class ExecutorGate(unittest.TestCase):  # R5
    def build(self, ports, decoder):
        return Executor(object(), *(Port(mode) for mode in ports), decoder)

    def test_all_fake_still_works(self):
        self.build(('fake', 'fake', 'fake'), Port('fake'))

    def test_live_needs_a_pinned_decoder(self):
        self.build(('live', 'live', 'live'), PinnedRouterDecoder(evidence()))
        refused = {
            'unverified router': (('live', 'live', 'live'), UnverifiedRouter()),
            'imposter decoder': (('live', 'live', 'live'), Imposter()),
            'fake decoder with live ports': (('live', 'live', 'live'), Port('fake')),
            'mixed ports': (('live', 'fake', 'live'), PinnedRouterDecoder(evidence())),
            'fake ports with pinned decoder': (('fake', 'fake', 'fake'), PinnedRouterDecoder(evidence())),
            'unknown mode': (('live', 'live', None), PinnedRouterDecoder(evidence())),
        }
        for name, (ports, decoder) in refused.items():
            with self.subTest(name), self.assertRaises(Blocked):
                self.build(ports, decoder)


class ExecutionService(unittest.TestCase):  # R6
    setUp = loop_fixtures.Composition.setUp  # the E9 composition fixture, without re-running its tests

    def pin(self, value=None, router=ROUTER):
        raw = json.dumps(value or evidence(router=router)).encode()
        path = self.root / 'router-evidence.json'
        path.write_bytes(raw)
        return dict(self.config, router=router, router_evidence_file=str(path),
                    router_evidence_sha256=hashlib.sha256(raw).hexdigest())

    def test_without_evidence_the_gate_stays_closed(self):
        with self.assertRaises(NotIntegrated):
            build_execution(dict(self.config, router=ROUTER), loop_fixtures.Store(), self.secrets)

    def test_pinned_evidence_opens_the_gate_with_one_decoder(self):
        loop = build_execution(self.pin(), loop_fixtures.Store(), self.secrets)
        executor = loop.service.executor
        self.assertIsInstance(executor.decoder, PinnedRouterDecoder)
        self.assertIs(executor.venue.decoder, executor.decoder)

    def test_refusals(self):
        good = self.pin()
        cases = {
            'hash differs': dict(good, router_evidence_sha256='0' * 64),
            'only the file': {k: v for k, v in good.items() if k != 'router_evidence_sha256'},
            'only the hash': {k: v for k, v in good.items() if k != 'router_evidence_file'},
            'other router configured': dict(good, router='0x' + 'cd' * 20),
        }
        for name, config in cases.items():
            with self.subTest(name), self.assertRaises(ContractError):
                build_execution(config, loop_fixtures.Store(), self.secrets)
        invalid = self.pin(dict(evidence(), guarantees=dict(evidence()['guarantees'], deadline_enforced=False)))
        with self.assertRaises(ContractError):
            build_execution(invalid, loop_fixtures.Store(), self.secrets)

    def test_router_decoder_helper(self):
        self.assertIsInstance(router_decoder(dict(router=ROUTER)), UnverifiedRouter)


def policy(spenders=(ROUTER,)):
    return SigningPolicy.from_config(dict(cap_basis='TEST_FIXTURE', allowed_spenders=list(spenders),
                                          allowed_tokens=[USDT, TOKEN], max_input_units={USDT: '1000', TOKEN: '1000'},
                                          max_fee_wei=str(10**12)))


class Signer(unittest.TestCase):  # R7
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        raw = json.dumps(evidence()).encode()
        self.path = Path(tmp.name) / 'router-evidence.json'
        self.path.write_bytes(raw)
        self.config = dict(router_evidence_file=str(self.path), router_evidence_sha256=hashlib.sha256(raw).hexdigest())

    def test_without_evidence_swaps_stay_refused(self):
        decoder = signer_service.router_decoder({}, policy())
        self.assertIsInstance(decoder, UnverifiedRouter)
        swap = intent(wallet='0x' + '1' * 40, router=ROUTER)
        with self.assertRaises(Blocked):
            policy().check(swap, 'SWAP', payload(), decoder, swap.wallet)

    def test_pinned_evidence_lets_the_policy_decode_the_swap(self):
        decoder = signer_service.router_decoder(self.config, policy())
        self.assertIsInstance(decoder, PinnedRouterDecoder)
        swap = intent(wallet='0x' + '1' * 40, router=ROUTER)
        policy().check(swap, 'SWAP', payload(), decoder, swap.wallet)
        with self.assertRaises(Blocked):  # the policy's own recipient check now sees the decoded bytes
            policy().check(swap, 'SWAP', payload(calldata(recipient='0x' + '44' * 20)), decoder, swap.wallet)

    def test_router_outside_allowed_spenders_is_refused(self):
        with self.assertRaises(ContractError):
            signer_service.router_decoder(self.config, policy(spenders=('0x' + 'cd' * 20,)))

    def test_changed_evidence_is_refused(self):
        self.path.write_bytes(self.path.read_bytes() + b' ')
        with self.assertRaises(ContractError):
            signer_service.router_decoder(self.config, policy())

    def test_config_needs_both_settings_or_neither(self):
        from larp.execution_live.router import evidence_settings
        with self.assertRaises(ContractError):
            evidence_settings(dict(router_evidence_file=str(self.path)))


if __name__ == '__main__':
    unittest.main()


from tests.execution_fixtures import ROUTER as FIXTURE_ROUTER  # noqa: E402  (the signer fixture's allowed spender)
from tests.signer.test_service import CommandCase  # noqa: E402


class SignerStartup(CommandCase):  # R7, through `python -m larp.signer.service run` on real PostgreSQL
    def pinned(self, router):
        raw = json.dumps(evidence(router=router)).encode()
        path = self.dir / 'router-evidence.json'
        path.write_bytes(raw)
        return {**self.config, 'router_evidence_file': str(path),
                'router_evidence_sha256': hashlib.sha256(raw).hexdigest()}, hashlib.sha256(raw).hexdigest()

    def test_start_line_reports_the_decoder(self):
        self.unquarantine()
        code, out = self.main('run', self.write(), max_cycles=1)
        self.assertEqual((code, json.loads(out)['swap_decoder']), (0, 'UNVERIFIED'))
        config, sha = self.pinned(FIXTURE_ROUTER)
        code, out = self.main('run', self.write(config), max_cycles=1)
        line = json.loads(out)
        self.assertEqual((code, line['swap_decoder'], line['router_evidence_sha256']), (0, 'VERIFIED', sha))

    def test_evidence_for_another_router_refuses_start(self):
        self.unquarantine()
        config, _ = self.pinned('0x' + 'cd' * 20)
        code, out = self.main('run', self.write(config), max_cycles=1)
        self.assertEqual((code, json.loads(out)['reason']), (4, 'START_REFUSED'))
        changed = dict(config, router_evidence_sha256='0' * 64)
        code, out = self.main('run', self.write(changed), max_cycles=1)
        self.assertEqual((code, json.loads(out)['reason']), (4, 'START_REFUSED'))


from tests.execution.test_gate_b_evidence import ReportTests  # noqa: E402


class GateBReport(unittest.TestCase):  # DR-02 in the Gate B report reads the pinned evidence and a passing check
    setUp = ReportTests.setUp
    report = ReportTests.report

    def with_router(self, check_status='PASS', evidence_router=None):
        from larp.execution_live.router import load_evidence
        raw = json.dumps(evidence(router=evidence_router or self.fixture.config['router'])).encode()
        (self.root / 'router-evidence.json').write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()
        config = json.loads((self.root / 'execution.json').read_bytes())
        config.update(router_evidence_file=str(self.root / 'router-evidence.json'), router_evidence_sha256=sha)
        config_raw = json.dumps(config).encode()
        (self.root / 'execution.json').write_bytes(config_raw)
        routes = self.root / 'routes'
        routes.mkdir(exist_ok=True)
        check = dict(schema='RouterRouteCheck.v1', status=check_status, router=config['router'],
                     selector=load_evidence(self.root / 'router-evidence.json', sha).selector, evidence_sha256=sha)
        check_raw = json.dumps(check).encode()
        (self.root / 'router-check.json').write_bytes(check_raw)
        return dict(self.inputs, files=dict(
            execution_config=dict(path=str(self.root / 'execution.json'), sha256=hashlib.sha256(config_raw).hexdigest()),
            router_check=dict(path=str(self.root / 'router-check.json'), sha256=hashlib.sha256(check_raw).hexdigest())))

    def test_dr02_validated_only_with_pinned_evidence_and_passing_check(self):
        self.assertEqual(self.report()['checks']['DR-02']['status'], 'BLOCKED')
        result = self.report(self.with_router())
        self.assertEqual(result['checks']['DR-02']['status'], 'VALIDATED')
        self.assertIn('logged dev approve + swap still required', result['checks']['DR-02']['detail'])
        self.assertEqual((result['status'], result['signing_enabled']), ('BLOCKED', False))

    def test_dr02_blocked_on_failing_check(self):
        self.assertEqual(self.report(self.with_router('FAIL'))['checks']['DR-02']['status'], 'BLOCKED')
