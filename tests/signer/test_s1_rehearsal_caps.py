"""IDEA-049-C SJ-11-RH01 RH6: `review_rehearsal_caps --profile` for an S1 rehearsal packet. Synthetic, key-free."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import unittest
from unittest.mock import patch

from larp.contracts import Document
from tests.signer import test_hosted_rehearsal_assembly as hosted
from tests.strategy.test_s1_core import block
from tools.deploy import review_rehearsal_caps as tool

BUILD, NOW, PROFILE, covered = hosted.BUILD, hosted.NOW, hosted.PROFILE, hosted.covered


class S1ProfileArgument(unittest.TestCase):
    # The hosted-assembly fixture (synthetic packet, CA and bindings); importing its class would re-run its tests.
    setUp = hosted.HostedRehearsalAssembly.setUp
    capture_output = hosted.HostedRehearsalAssembly.capture_output

    def s1_profile(self, **changes):
        from tools.deploy.build_rehearsal_candidate import build
        p = build(2, s1_raw=json.dumps(block(), sort_keys=True).encode(), s1_decision='SJ-11-RH01 fixture').read()
        p.update(changes)
        path = self.root / ('s1-profile-%d.json' % len(list(self.root.glob('s1-profile-*'))))
        path.write_bytes(Document.from_dict(p).payload + b'\n')
        return path

    def packet_for(self, path):
        packet = deepcopy(self.packet)
        packet['selected_profile_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        return packet

    def test_default_profile_is_the_reviewed_equal_weight_one(self):
        self.assertEqual(tool.DEFAULT_PROFILE, PROFILE)
        _, result, _ = tool.collect(self.packet, self.root / 'ew-private', BUILD, now=NOW)
        self.assertEqual(result['evidence_hashes']['profile'], self.packet['selected_profile_sha256'])

    def test_s1_packet_is_reviewed_against_the_named_s1_profile(self):
        path = self.s1_profile()
        inputs, result, _ = tool.collect(self.packet_for(path), self.root / 's1-private', BUILD, now=NOW, profile=path)
        profile = json.loads((self.root / 's1-private/profile.json').read_bytes())
        self.assertEqual(profile['baseline'], 'TREND_GUARDED_VOL')
        self.assertEqual(inputs['files']['profile']['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(result['evidence_hashes']['profile'], inputs['files']['profile']['sha256'])
        reserve = [c for c in result['checks'] if c['check'] == 'FULL_BOOK_EXIT_RESERVE']
        self.assertEqual(reserve, [dict(check='FULL_BOOK_EXIT_RESERVE', required=str(10 * profile['gas_action_budget_units']),
                                        cap=str(profile['exit_gas_reserve_units']), covered=True)])
        # No quotes in this synthetic packet: coverage is missing, never a reserve or scope blocker.
        self.assertNotIn('FULL_BOOK_EXIT_RESERVE', result['blockers'])
        self.assertIn('QUOTE_COVERAGE_INCOMPLETE', result['blockers'])

    def test_one_child_s1_reserve_is_a_coverage_blocker(self):
        path = self.s1_profile(exit_gas_reserve_units=5 * 384000000000000)
        _, result, _ = tool.collect(self.packet_for(path), self.root / 'one-private', BUILD, now=NOW, profile=path)
        self.assertIn('FULL_BOOK_EXIT_RESERVE', result['blockers'])

    def test_profile_that_differs_from_the_packet_is_refused_before_any_output(self):
        s1 = self.s1_profile()
        cases = dict(s1_profile_ew_packet=(self.packet, s1), ew_profile_s1_packet=(self.packet_for(s1), PROFILE))
        for name, (packet, path) in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(AssertionError):
                    tool.collect(packet, self.root / (name + '-private'), BUILD, now=NOW, profile=path)
                self.assertFalse((self.root / (name + '-private')).exists())
                with self.assertRaises(AssertionError), patch.object(tool, 'review', covered), \
                        patch('larp.signer.assembly.review', covered):
                    tool.assemble_hosted(packet, self.root / (name + '-hosted'), self.bindings,
                                         self.root / (name + '-signer'), now=NOW, profile=path)
                self.assertFalse((self.root / (name + '-hosted')).exists())
                self.assertFalse((self.root / (name + '-signer')).exists())

    def cli(self, packet, *extra):
        raw = self.root / 'capture-stdout.txt'
        raw.write_bytes(self.capture_output(packet))
        bindings = self.root / 'bindings.json'
        bindings.write_text(json.dumps(self.bindings))
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(tool, 'review', covered), \
                patch('larp.signer.assembly.review', covered):
            code = tool.main(['--packet', str(raw), *extra])
        return code, stdout.getvalue()

    def test_cli_profile_argument_in_numeric_and_hosted_modes(self):
        s1 = self.s1_profile()
        code, out = self.cli(self.packet_for(s1), '--build-id', BUILD, '--output-dir', str(self.root / 'n-private'),
                             '--profile', str(s1))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((self.root / 'n-private/profile.json').read_bytes())['baseline'], 'TREND_GUARDED_VOL')
        code, out = self.cli(self.packet_for(s1), '--bindings', str(self.root / 'bindings.json'),
                             '--output-dir', str(self.root / 'h-private'), '--signer-out', str(self.root / 'h-signer'),
                             '--profile', str(s1))
        self.assertEqual((code, json.loads(out)['status']), (0, 'ASSEMBLED_REQUIRES_APPROVAL'))
        code, out = self.cli(self.packet, '--bindings', str(self.root / 'bindings.json'),
                             '--output-dir', str(self.root / 'x-private'), '--signer-out', str(self.root / 'x-signer'),
                             '--profile', str(s1))
        self.assertEqual((code, json.loads(out)['status']), (4, 'SIGNER_ASSEMBLY_REFUSED'))
        self.assertFalse((self.root / 'x-signer').exists())


if __name__ == '__main__':
    unittest.main()
