"""IDEA-103 FI3/FI4: the FINAL caps review and the fresh final-wallet capture (F0p M3). Synthetic packets only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.marketdata.port import TOKENS
from larp.research.fixtures import snapshot
from tools.deploy import review_rehearsal_caps as tool
from tools.deploy.ld10_readonly_packet import script

ROOT = tool.ROOT
FINAL_PROFILE = ROOT / 'docs/build/evidence/fs1-final-20261025/fs1-final-recovery.json'
REHEARSAL_PROFILE = ROOT / 'docs/build/evidence/s4-rehearsal-profile-20261025/rehearsal-s4-deterministic.json'
ROUTER_POLICY = ROOT / 'docs/build/evidence/untrusted-router-policy-ld03-20261020.json'
DECISION = ROOT / 'docs/build/evidence/signer-numeric-ceilings-20261021.json'
FINAL_WALLET = '0x' + 'ab' * 20
DEV_WALLET = '0x' + '12' * 20
BUILD = 'a' * 40
NOW = '2026-10-27T00:00:00+00:00'


def covered(inputs, *, now, base_dir):
    return dict(numeric_status='COVERED', blockers=['OWNER_REVIEW_REQUIRED'], missing_quote_coverage=[],
                gas_scope='INITIAL_ONLY')


class FinalCapsReview(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.ca = self.root / 'rds-ca.pem'
        self.ca.write_bytes(b'synthetic public CA bytes')
        self.policy = self.root / 'untrusted-router-policy.json'
        self.policy.write_bytes(ROUTER_POLICY.read_bytes())
        # The capture runs while the dev run is installed: its private portfolio is the dev run's.
        source = snapshot().context.read()['portfolio']
        source.update(mode='dev', run_id='larp-dev-rehearsal-20261025-s4', wallet_id=DEV_WALLET, bnb_decimals=18,
                      bnb_units=25 * 10**15, reservations={},
                      positions={s: dict(units=7 if s == 'GOOGLB' else 0, decimals=18, cost_basis_units=3)
                                 for s in TOKENS})
        keys = ('schema', 'wallet_id', 'run_id', 'mode', 'cash_units', 'bnb_units', 'bnb_decimals', 'positions',
                'reservations')
        usdt, bnb = 170_000_000, 30 * 10**15
        self.packet = dict(
            selected_profile_sha256=hashlib.sha256(FINAL_PROFILE.read_bytes()).hexdigest(), configs_unchanged=True,
            identity=dict(run_id='larp-dev-rehearsal-20261025-s4', target='FRESH_FINAL_WALLET'),
            holdings=dict(status='FRESH_TARGET', latest_nonce=0, pending_nonce=0, block=1, observation_sha256='0' * 64,
                          assets=dict({s: dict(chain=0, ledger=0, cls='MATCH') for s in TOKENS},
                                      USDT=dict(chain=usdt, ledger=0, cls='SURPLUS'),
                                      BNB=dict(chain=bnb, ledger=0, cls='SURPLUS'))),
            in_flight=dict(reservations={'USDT': dict(count=1, units=5)}, execution_pending=['dev-round']),
            router=dict(allowances_to_router={s: 0 for s in ('USDT', *TOKENS)}),
            private_caps_inputs=dict(wallet=FINAL_WALLET, portfolio={k: source[k] for k in keys},
                                     token_decimals={s: 18 for s in TOKENS}, quote_artifacts=[]))
        self.bindings = dict(schema='RehearsalSignerBindings.v1', run_id='larp-final-fs1', build_id=BUILD,
                             database_host='DO_NOT_ECHO.example', database_name='larp_final',
                             database_ca_file=str(self.ca),
                             database_ca_sha256=hashlib.sha256(self.ca.read_bytes()).hexdigest(),
                             region='ap-southeast-2', untrusted_router_policy_file=str(self.policy),
                             untrusted_router_policy_sha256=hashlib.sha256(self.policy.read_bytes()).hexdigest())

    def final(self, name='final', packet=None, **kwargs):
        kwargs.setdefault('profile', FINAL_PROFILE)
        kwargs.setdefault('environment', 'FINAL')
        kwargs.setdefault('fresh_wallet', FINAL_WALLET)
        kwargs.setdefault('allowance_recovery', True)
        with patch.object(tool, 'review', covered), patch('larp.signer.assembly.review', covered):
            return tool.assemble_hosted(packet or self.packet, self.root / (name + '-private'), self.bindings,
                                        self.root / (name + '-signer'), now=NOW, **kwargs)

    def test_fi3_final_uses_the_final_policy_live_mode_and_final_inputs(self):
        _, _, digest = self.final()
        private = self.root / 'final-private'
        decision = json.loads(DECISION.read_bytes())
        self.assertEqual(json.loads((private / 'signing-policy.json').read_bytes()),
                         dict(decision['policies']['final']['signing_policy'], allowance_recovery=True))
        execution = json.loads((private / 'execution-config.json').read_bytes())
        self.assertEqual((execution['mode'], execution['wallet_address'], execution['allowance_recovery']),
                         ('live', FINAL_WALLET, True))
        self.assertEqual(json.loads((private / 'inputs.json').read_bytes())['environment'], 'FINAL')
        signer = json.loads((self.root / 'final-signer/signer.json').read_bytes())
        self.assertEqual((signer['wallet_address'], signer['run_id'], signer['database_name']),
                         (FINAL_WALLET, 'larp-final-fs1', 'larp_final'))
        self.assertEqual(hashlib.sha256((self.root / 'final-signer/signer.json').read_bytes()).hexdigest(), digest)

    def test_fi4_the_fresh_book_comes_from_the_chain_only(self):
        self.final()
        book = json.loads((self.root / 'final-private/current-holdings.json').read_bytes())
        assets = self.packet['holdings']['assets']
        self.assertEqual((book['wallet_id'], book['run_id'], book['mode']), (FINAL_WALLET, 'larp-final-fs1', 'live'))
        self.assertEqual((book['cash_units'], book['bnb_units']), (assets['USDT']['chain'], assets['BNB']['chain']))
        self.assertEqual({s: (p['units'], p['cost_basis_units']) for s, p in book['positions'].items()},
                         {s: (0, 0) for s in TOKENS})
        self.assertEqual(book['reservations'], {})

    def test_fi4_refusals(self):
        def changed(edit):
            packet = deepcopy(self.packet)
            edit(packet)
            return packet
        cases = dict(
            dust=changed(lambda p: p['holdings']['assets']['TSLAB'].update(chain=1, cls='SURPLUS')),
            pending=changed(lambda p: p['holdings'].update(pending_nonce=1)),
            allowance=changed(lambda p: p['router']['allowances_to_router'].update(USDT=1)),
            not_fresh=changed(lambda p: p['holdings'].update(status='MATCH')),
            other_wallet=changed(lambda p: p['private_caps_inputs'].update(wallet='0x' + 'cd' * 20)))
        for name, packet in cases.items():
            with self.subTest(name), self.assertRaises(AssertionError):
                self.final(name, packet=packet)
            self.assertFalse((self.root / (name + '-signer')).exists())

    def test_fi3_profile_and_environment_must_agree(self):
        packet = deepcopy(self.packet)
        packet['selected_profile_sha256'] = hashlib.sha256(REHEARSAL_PROFILE.read_bytes()).hexdigest()
        with self.assertRaises(AssertionError):
            self.final('rehearsal-under-final', packet=packet, profile=REHEARSAL_PROFILE)
        with self.assertRaises(AssertionError):  # a FINAL profile under the REHEARSAL default
            tool.collect(self.packet, self.root / 'final-under-rehearsal', BUILD, now=NOW, profile=FINAL_PROFILE)
        for bad in (dict(environment='LIVE'), dict(environment='REHEARSAL'), dict(fresh_wallet='0x12')):
            with self.subTest(bad=bad), self.assertRaises((AssertionError, ValueError)):
                self.final('bad-' + str(len(str(bad))), **bad)


class FreshTargetProbe(unittest.TestCase):
    def test_fi4_without_a_target_the_probe_is_unchanged(self):
        raw = REHEARSAL_PROFILE.read_bytes()
        self.assertEqual(hashlib.sha256(script(raw).encode()).hexdigest(),
                         '379c476b90c24e6ba60e1e1839e53e892b16cb2b852187263a65b471505ab8fa')

    def test_fi4_a_target_probe_reads_the_target_wallet_and_marks_it_fresh(self):
        raw = FINAL_PROFILE.read_bytes()
        probe = script(raw, target_wallet=FINAL_WALLET)
        self.assertNotEqual(probe, script(raw))
        for needed in ("TARGET_WALLET = '" + FINAL_WALLET + "'", "'FRESH_TARGET'", 'FRESH_FINAL_WALLET'):
            self.assertIn(needed, probe)
        body = probe.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        compile(body, 'probe', 'exec')
        for bad in ('0x12', 'ab' * 20, '0x' + 'AB' * 20 + 'x'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                script(raw, target_wallet=bad)
