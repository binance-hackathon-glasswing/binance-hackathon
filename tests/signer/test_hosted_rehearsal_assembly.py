"""SJ-04: hosted rehearsal signer assembly from one capture; synthetic, key-free, never Gate B acceptance."""
import base64
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

from larp.contracts import ContractError
from larp.marketdata.port import TOKENS
from larp.research.fixtures import snapshot
from tools.deploy import review_rehearsal_caps as tool

ROOT = tool.ROOT
PROFILE = ROOT / 'docs/build/evidence/rehearsal-exit-split-20261021/rehearsal-deterministic.json'
ROUTER_POLICY = ROOT / 'docs/build/evidence/untrusted-router-policy-ld03-20261020.json'
WALLET = '0x' + '12' * 20
BUILD = 'fa1b6c966f186103c8dfaee5438e0d00e4edec9a'
NOW = '2026-10-22T00:00:00+00:00'
PRIVATE_HOST = 'DO_NOT_ECHO_PRIVATE_HOST.example'


def covered(inputs, *, now, base_dir):
    """Numeric coverage itself is tested in test_caps_review; here only the hosted plumbing around it."""
    return dict(numeric_status='COVERED', blockers=['OWNER_REVIEW_REQUIRED'], missing_quote_coverage=[],
                gas_scope='INITIAL_ONLY')


class HostedRehearsalAssembly(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.ca = self.root / 'rds-ca.pem'
        self.ca.write_bytes(b'synthetic public CA bytes')
        self.policy = self.root / 'untrusted-router-policy.json'
        self.policy.write_bytes(ROUTER_POLICY.read_bytes())
        portfolio = snapshot().context.read()['portfolio']
        portfolio.update(mode='dev', run_id='larp-dev-retired-unsigned', wallet_id=WALLET, bnb_decimals=18,
                         bnb_units=5 * 10**15, reservations={},
                         positions={s: dict(units=0, decimals=18, cost_basis_units=0) for s in TOKENS})
        keys = ('schema', 'wallet_id', 'run_id', 'mode', 'cash_units', 'bnb_units', 'bnb_decimals', 'positions',
                'reservations')
        self.packet = dict(
            selected_profile_sha256=hashlib.sha256(PROFILE.read_bytes()).hexdigest(), configs_unchanged=True,
            identity=dict(run_id='larp-dev-retired-unsigned'),
            holdings=dict(status='MATCH', latest_nonce=4, pending_nonce=4, block=1, observation_sha256='0' * 64,
                          assets=dict({s: dict(chain=0, ledger=0, cls='MATCH') for s in TOKENS},
                                      USDT=dict(chain=portfolio['cash_units'], ledger=portfolio['cash_units'], cls='MATCH'),
                                      BNB=dict(chain=5 * 10**15, ledger=5 * 10**15, cls='MATCH'))),
            in_flight=dict(reservations=[], execution_pending=[]),
            router=dict(allowances_to_router={s: 0 for s in TOKENS}),
            private_caps_inputs=dict(wallet=WALLET, portfolio={k: portfolio[k] for k in keys},
                                     token_decimals={s: 18 for s in TOKENS}, quote_artifacts=[]))
        self.bindings = dict(schema='RehearsalSignerBindings.v1', run_id='larp-dev-rehearsal-20261022',
                             build_id=BUILD, database_host=PRIVATE_HOST, database_name='larp_rehearsal1',
                             database_ca_file=str(self.ca),
                             database_ca_sha256=hashlib.sha256(self.ca.read_bytes()).hexdigest(),
                             region='ap-southeast-2', untrusted_router_policy_file=str(self.policy),
                             untrusted_router_policy_sha256=hashlib.sha256(self.policy.read_bytes()).hexdigest())

    def run_hosted(self, name='run', *, bindings=None, packet=None, usdt_deficit=0):
        with patch.object(tool, 'review', covered), patch('larp.signer.assembly.review', covered):
            return tool.assemble_hosted(packet or self.packet, self.root / (name + '-private'),
                                        bindings or self.bindings, self.root / (name + '-signer'), now=NOW,
                                        usdt_deficit=usdt_deficit)

    def seeded(self, deficit=2_000_000, bnb_gain=2_631_126_185_967_125):
        """SJ-03's shape: a post-trial seed swapped USDT for BNB, unknown to the retired ledger."""
        packet = deepcopy(self.packet)
        holdings = packet['holdings']
        holdings['status'] = 'DEFICIT'
        holdings['assets']['USDT'].update(chain=holdings['assets']['USDT']['ledger'] - deficit, cls='DEFICIT')
        holdings['assets']['BNB'].update(chain=holdings['assets']['BNB']['ledger'] + bnb_gain, cls='SURPLUS')
        return packet

    def test_new_run_starts_from_chain_holdings_with_exactly_the_declared_seed_deficit(self):
        packet = self.seeded()
        self.run_hosted(packet=packet, usdt_deficit=2_000_000)
        holdings = json.loads((self.root / 'run-private/current-holdings.json').read_bytes())
        assets = packet['holdings']['assets']
        self.assertEqual(holdings['cash_units'], assets['USDT']['chain'])
        self.assertEqual(holdings['bnb_units'], assets['BNB']['chain'])
        rebinding = json.loads((self.root / 'run-private/portfolio-rebinding.json').read_bytes())
        self.assertEqual(rebinding['accepted_usdt_deficit_units'], 2_000_000)
        self.assertEqual(rebinding['assets'], assets)
        self.assertTrue((self.root / 'run-signer/signer.json').exists())

    def test_any_other_deficit_bnb_shortfall_or_stock_mismatch_refuses(self):
        cases = dict(more=(self.seeded(2_000_001), 2_000_000), less=(self.seeded(1_999_999), 2_000_000),
                     undeclared=(self.seeded(), 0), declared_without_deficit=(self.packet, 2_000_000),
                     bnb_deficit=(self.seeded(bnb_gain=-1), 2_000_000))
        stock = self.seeded()
        stock['holdings']['assets']['NVDAB'].update(chain=1, cls='SURPLUS')
        cases['stock'] = (stock, 2_000_000)
        surplus_only = self.seeded(0)
        surplus_only['holdings']['assets']['USDT']['cls'] = 'MATCH'
        cases['status_disagrees'] = (surplus_only, 0)
        for name, (packet, deficit) in cases.items():
            with self.subTest(case=name):
                if name == 'bnb_deficit':
                    packet['holdings']['assets']['BNB']['cls'] = 'DEFICIT'
                with self.assertRaises(AssertionError):
                    self.run_hosted(name, packet=packet, usdt_deficit=deficit)
                self.assertFalse((self.root / (name + '-signer')).exists())

    def test_bnb_surplus_alone_is_accepted_with_its_overall_status(self):
        packet = self.seeded(0)
        packet['holdings'].update(status='SURPLUS_ONLY')
        packet['holdings']['assets']['USDT']['cls'] = 'MATCH'
        self.run_hosted(packet=packet)
        holdings = json.loads((self.root / 'run-private/current-holdings.json').read_bytes())
        self.assertEqual(holdings['bnb_units'], packet['holdings']['assets']['BNB']['chain'])

    def test_numeric_only_mode_keeps_strict_match(self):
        with self.assertRaises(AssertionError):
            tool.collect(self.seeded(), self.root / 'numeric-private', BUILD, now=NOW)
        with self.assertRaises(AssertionError):
            tool.collect(self.packet, self.root / 'numeric2-private', BUILD, now=NOW, usdt_deficit=1)

    def test_signer_json_binds_exact_hosted_identity_and_signer_role(self):
        with patch('larp.runtime.database.open_service_store') as db, \
                patch('larp.runtime.database.rds_client') as aws, patch('socket.socket') as network:
            _, now, digest = self.run_hosted()
        for boundary in (db, aws, network):
            boundary.assert_not_called()
        self.assertEqual(now, NOW)
        raw = (self.root / 'run-signer/signer.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
        config = json.loads(raw)
        for field in ('run_id', 'build_id', 'database_host', 'database_name', 'database_ca_file',
                      'database_ca_sha256', 'region', 'untrusted_router_policy_file', 'untrusted_router_policy_sha256'):
            self.assertEqual(config[field], self.bindings[field])
        self.assertEqual(config['database_user'], 'larp_signer')
        self.assertEqual(config['wallet_address'], WALLET)
        self.assertNotIn('database_dsn_file', config)
        self.assertNotIn('router_evidence_file', config)
        report = json.loads((self.root / 'run-signer/signer-assembly-report.json').read_bytes())
        self.assertEqual(report['router_mode'], 'untrusted')
        for flag in ('ready_to_install', 'signing_enabled', 'gate_b_accepted'):
            self.assertIs(report[flag], False)

    def test_execution_config_and_holdings_are_rebound_to_the_signed_run_and_recorded(self):
        self.run_hosted()
        private = self.root / 'run-private'
        execution = json.loads((private / 'execution-config.json').read_bytes())
        self.assertEqual(execution['database_user'], 'larp_execution')
        self.assertEqual(execution['run_id'], self.bindings['run_id'])
        self.assertNotIn('database_dsn_file', execution)
        holdings = json.loads((private / 'current-holdings.json').read_bytes())
        self.assertEqual(holdings['run_id'], self.bindings['run_id'])
        source = deepcopy(self.packet['private_caps_inputs']['portfolio'])
        self.assertEqual({k: v for k, v in holdings.items() if k != 'run_id'},
                         {k: v for k, v in source.items() if k != 'run_id'})
        rebinding = json.loads((private / 'portfolio-rebinding.json').read_bytes())
        self.assertEqual(rebinding['source_run_id'], 'larp-dev-retired-unsigned')
        self.assertEqual(rebinding['run_id'], self.bindings['run_id'])

    def test_malformed_bindings_refuse_before_any_candidate(self):
        changes = dict(missing=lambda b: b.pop('region'), extra=lambda b: b.update(database_dsn_file='/x'),
                       unsafe_run=lambda b: b.update(run_id='../unsafe'), short_build=lambda b: b.update(build_id='fa1b6c9'),
                       relative_ca=lambda b: b.update(database_ca_file='rds-ca.pem'),
                       other_build=lambda b: b.update(build_id='a' * 40))
        for name, change in changes.items():
            with self.subTest(change=name):
                bindings = deepcopy(self.bindings)
                change(bindings)
                with self.assertRaises((ContractError, AssertionError)):
                    if name == 'other_build':
                        tool.collect(self.packet, self.root / (name + '-private'), BUILD, bindings=bindings, now=NOW)
                    else:
                        self.run_hosted(name, bindings=bindings)
                self.assertFalse((self.root / (name + '-signer')).exists())

    def test_changed_ca_or_router_policy_refuses(self):
        for path in (self.ca, self.policy):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b' ')
                with self.assertRaises(ContractError):
                    self.run_hosted(path.stem)
                self.assertFalse((self.root / (path.stem + '-signer')).exists())
                path.write_bytes(original)

    def test_unreconciled_or_in_flight_packets_refuse(self):
        changes = dict(holdings=lambda p: p['holdings'].update(status='SKIPPED'),
                       nonce=lambda p: p['holdings'].update(pending_nonce=5),
                       allowance=lambda p: p['router']['allowances_to_router'].update(NVDAB=1),
                       reservation=lambda p: p['in_flight'].update(reservations=['r']))
        for name, change in changes.items():
            with self.subTest(change=name):
                packet = deepcopy(self.packet)
                change(packet)
                with self.assertRaises(AssertionError):
                    self.run_hosted(name, packet=packet)
                self.assertFalse((self.root / (name + '-signer')).exists())

    def test_allowance_recovery_accepts_a_leftover_allowance_and_opts_execution_and_signer_in(self):
        # IDEA-097 S4: run 4 left an SKHYB allowance; the new run opts into IDEA-096 recovery and clears it itself.
        packet = deepcopy(self.packet)
        packet['router']['allowances_to_router'].update(SKHYB=68939879194155372)
        with self.assertRaises(AssertionError):
            self.run_hosted('strict', packet=packet)
        self.assertFalse((self.root / 'strict-signer').exists())
        with patch.object(tool, 'review', covered), patch('larp.signer.assembly.review', covered):
            tool.assemble_hosted(packet, self.root / 'rec-private', self.bindings, self.root / 'rec-signer', now=NOW,
                                 allowance_recovery=True)
        private = self.root / 'rec-private'
        self.assertIs(json.loads((private / 'execution-config.json').read_bytes())['allowance_recovery'], True)
        policy = json.loads((private / 'signing-policy.json').read_bytes())
        decision = json.loads((ROOT / 'docs/build/evidence/signer-numeric-ceilings-20261021.json').read_bytes())
        self.assertEqual(policy, dict(decision['policies']['development']['signing_policy'], allowance_recovery=True))
        signer = json.loads((self.root / 'rec-signer/signer.json').read_bytes())
        self.assertIs(signer['signing_policy']['allowance_recovery'], True)
        with self.assertRaises(AssertionError):
            tool.collect(packet, self.root / 'bad-private', BUILD, bindings=self.bindings, now=NOW,
                         allowance_recovery='yes')

    def test_uncovered_numeric_review_writes_no_candidate(self):
        # The real reviewer on a packet without quotes: missing coverage, never a signer.json.
        result, _, digest = tool.assemble_hosted(self.packet, self.root / 'real-private', self.bindings,
                                                 self.root / 'real-signer', now=NOW)
        self.assertNotEqual(result['numeric_status'], 'COVERED')
        self.assertIsNone(digest)
        self.assertFalse((self.root / 'real-signer').exists())

    def capture_output(self, packet):
        text = json.dumps(packet, sort_keys=True, separators=(',', ':')).encode()
        return (base64.b64encode(zlib.compress(text, 9)) + b'\n'
                + json.dumps(dict(packet_sha256=hashlib.sha256(text).hexdigest())).encode() + b'\n')

    def test_capture_stdout_is_decoded_only_with_its_matching_hash(self):
        raw = self.capture_output(self.packet)
        self.assertEqual(tool.read_packet(raw), self.packet)
        self.assertEqual(tool.read_packet(json.dumps(self.packet).encode()), self.packet)
        lines = raw.splitlines()
        with self.assertRaises(ContractError):
            tool.read_packet(lines[0] + b'\n' + json.dumps(dict(packet_sha256='0' * 64)).encode())
        with self.assertRaises(ContractError):
            tool.read_packet(lines[0])

    def invoke(self, *extra, raw=None, packet=None):
        packet = packet or self.root / 'capture-stdout.txt'
        if raw is not False:
            packet.write_bytes(raw or self.capture_output(self.packet))
        bindings = self.root / 'bindings.json'
        bindings.write_text(json.dumps(self.bindings))
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(tool, 'review', covered), \
                patch('larp.signer.assembly.review', covered):
            code = tool.main(['--packet', str(packet), '--bindings', str(bindings), *extra])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_assembles_once_and_refusals_never_echo_private_values(self):
        code, out, _ = self.invoke('--output-dir', str(self.root / 'cli-private'), '--signer-out', str(self.root / 'cli'))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result['status'], 'ASSEMBLED_REQUIRES_APPROVAL')
        self.assertFalse(result['ready_to_install'])
        self.assertNotIn(PRIVATE_HOST, out)
        # A second run never overwrites the first private directories.
        code, out, _ = self.invoke('--output-dir', str(self.root / 'cli-private'), '--signer-out', str(self.root / 'cli2'))
        self.assertEqual(code, 4)
        self.assertEqual(json.loads(out)['status'], 'SIGNER_ASSEMBLY_REFUSED')
        self.ca.write_bytes(b'changed CA')
        code, out, _ = self.invoke('--output-dir', str(self.root / 'cli3-private'), '--signer-out', str(self.root / 'cli3'))
        self.assertEqual(code, 4)
        self.assertNotIn(PRIVATE_HOST, out)
        self.assertFalse((self.root / 'cli3').exists())

    def test_cli_refuses_signer_output_inside_the_checkout(self):
        code, _, _ = self.invoke('--output-dir', str(self.root / 'in-private'),
                                 '--signer-out', str(ROOT / 'must-not-create-signer-candidate'))
        self.assertEqual(code, 4)
        self.assertFalse((ROOT / 'must-not-create-signer-candidate').exists())
        self.assertFalse((self.root / 'in-private').exists())

    def test_cli_refuses_private_output_inside_the_checkout_before_writing(self):
        # PR239 review: the intermediate execution-config.json names the private database host.
        code, out, _ = self.invoke('--output-dir', str(ROOT / 'must-not-create-hosted-private'),
                                   '--signer-out', str(self.root / 'in-signer'))
        self.assertEqual(code, 4)
        self.assertEqual(json.loads(out)['status'], 'SIGNER_ASSEMBLY_REFUSED')
        self.assertFalse((ROOT / 'must-not-create-hosted-private').exists())
        self.assertFalse((self.root / 'in-signer').exists())
        with self.assertRaises(ContractError):
            tool.collect(self.packet, ROOT / 'must-not-create-hosted-private', BUILD, bindings=self.bindings, now=NOW)
        self.assertFalse((ROOT / 'must-not-create-hosted-private').exists())

    def test_cli_packet_failures_refuse_without_traceback_or_private_path(self):
        good = self.capture_output(self.packet).splitlines()
        cases = dict(mismatched_hash=good[0] + b'\n' + json.dumps(dict(packet_sha256='0' * 64)).encode(),
                     corrupt_compressed=base64.b64encode(b'not zlib') + b'\n' + good[1],
                     not_utf8=b'\xff\xfe', missing=False)
        for name, raw in cases.items():
            with self.subTest(case=name):
                packet = self.root / ('private-dir-' + name) / 'capture-stdout.txt'
                packet.parent.mkdir()
                code, out, err = self.invoke('--output-dir', str(self.root / (name + '-private')),
                                             '--signer-out', str(self.root / (name + '-signer')),
                                             raw=raw, packet=packet)
                self.assertEqual(code, 4)
                self.assertEqual(json.loads(out)['status'], 'SIGNER_ASSEMBLY_REFUSED')
                self.assertNotIn('private-dir-', out + err)
                self.assertFalse((self.root / (name + '-private')).exists())
                self.assertFalse((self.root / (name + '-signer')).exists())

    def test_packet_checks_still_refuse_under_python_optimize(self):
        # The checks must not be plain asserts, which python -O strips.
        name = 'tests.signer.test_hosted_rehearsal_assembly.HostedRehearsalAssembly.'
        result = subprocess.run([sys.executable, '-O', '-m', 'unittest', '-q',
                                 name + 'test_any_other_deficit_bnb_shortfall_or_stock_mismatch_refuses',
                                 name + 'test_unreconciled_or_in_flight_packets_refuse'],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
