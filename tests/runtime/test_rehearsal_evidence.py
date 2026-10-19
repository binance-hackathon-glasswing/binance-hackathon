"""Synthetic offline packet checks; no host drill acceptance."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from tools.deploy import rehearsal_evidence as gates


class RehearsalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.identity = dict(source_commit='a'*40, bundle_sha256='b'*64,
                             manifest_sha256='c'*64, profile_sha256='d'*64,
                             bound_config_sha256='e'*64, run_id='dev-rehearsal',
                             wallet_public_address='0x'+'1'*40)
        self.file = self.root/'sanitized.json'
        self.file.write_text('{"synthetic": true}')
        self.artifact = dict(file=self.file.name, sha256=hashlib.sha256(self.file.read_bytes()).hexdigest())
        self.packet = gates.template()
        self.packet['identity'] = self.identity.copy()
        for row in self.packet['gates']:
            row.update(status='REVIEWED', identity=self.identity.copy(), evidence_scope='OBSERVED_HOST',
                       operator='operator', reviewer='reviewer', procedure_ref='pushed procedure',
                       approval_ref='dated approval', review_ref='dated review',
                       started_at_utc='2026-10-21T00:00:00Z', ended_at_utc='2026-10-21T01:00:00Z',
                       artifacts=[self.artifact.copy()], criteria=dict.fromkeys(row['criteria'], 'PASS'))

    def result(self):
        return gates.check(self.packet, self.identity, self.root)

    def test_complete_index_never_claims_host_or_gate_acceptance(self):
        result = self.result()
        self.assertTrue(result['packet_complete'])
        for key in ('gate_c_accepted', 'signing_enabled', 'host_results_verified'):
            self.assertIs(result[key], False)

    def test_new_template_cannot_count_as_observed(self):
        self.packet = gates.template()
        self.packet['identity'] = self.identity
        result = self.result()
        self.assertFalse(result['packet_complete'])
        self.assertEqual(len(result['results']), 10)

    def test_tampered_or_missing_artifact_blocks_all_claims(self):
        self.file.write_text('changed')
        self.assertTrue(all('ARTIFACT_INTEGRITY' in row['reasons'] for row in self.result()['results']))
        self.file.unlink()
        self.assertFalse(self.result()['packet_complete'])

    def test_record_and_packet_identity_mismatch(self):
        self.packet['gates'][0]['identity']['source_commit'] = 'f'*40
        self.assertIn('IDENTITY_MISMATCH', self.result()['results'][0]['reasons'])
        self.packet['identity'] = dict(self.identity, profile_sha256='f'*64)
        with self.assertRaises(gates.Refused): self.result()

    def test_duplicate_or_missing_gate_rejected(self):
        self.packet['gates'][-1] = copy.deepcopy(self.packet['gates'][0])
        with self.assertRaises(gates.Refused): self.result()
        self.packet['gates'].pop()
        with self.assertRaises(gates.Refused): self.result()

    def test_missing_criteria_and_review_or_synthetic_scope(self):
        row = self.packet['gates'][8]
        row['criteria'].pop('five_days_and_weekend_or_reviewed_shortfall')
        row['review_ref'] = None
        row['evidence_scope'] = 'SYNTHETIC'
        reasons = self.result()['results'][8]['reasons']
        for reason in ('CRITERIA_INCOMPLETE', 'ATTRIBUTION_REQUIRED', 'HOST_EVIDENCE_REQUIRED'):
            self.assertIn(reason, reasons)

    def test_same_reviewer_and_invalid_time_rejected(self):
        row = self.packet['gates'][0]
        row['reviewer'] = row['operator']
        for value in ('2026-10-21T01:00:00+00:00', '2026-02-30T00:00:00Z', '2026-10-20T00:00:00Z'):
            with self.subTest(value=value):
                row['ended_at_utc'] = value
                reasons = self.result()['results'][0]['reasons']
                self.assertIn('INDEPENDENT_REVIEW_REQUIRED', reasons)
                self.assertTrue('TIME_ORDER' in reasons or 'INVALID_UTC_INTERVAL' in reasons)

    def test_path_escape_and_symlink_and_fifo_refused(self):
        for name in ('../sanitized.json', str(self.file), 'sub/file.json'):
            with self.subTest(name=name):
                self.packet['gates'][0]['artifacts'] = [dict(self.artifact, file=name)]
                self.assertIn('ARTIFACT_INTEGRITY', self.result()['results'][0]['reasons'])
        link = self.root/'link.json'
        link.symlink_to(self.file)
        self.packet['gates'][0]['artifacts'] = [dict(self.artifact, file=link.name)]
        self.assertIn('ARTIFACT_INTEGRITY', self.result()['results'][0]['reasons'])
        import os
        os.mkfifo(self.root/'fifo')
        self.packet['gates'][0]['artifacts'] = [dict(self.artifact, file='fifo')]
        self.assertIn('ARTIFACT_INTEGRITY', self.result()['results'][0]['reasons'])

    def test_duplicate_json_keys_and_oversized_input(self):
        path = self.root/'index.json'
        path.write_text('{"gate":"RG1","gate":"RG2"}')
        with self.assertRaises(gates.Refused): gates.load(path)
        path.write_bytes(b' '* (gates.MAX_JSON+1))
        with self.assertRaises(gates.Refused): gates.load(path)

    def test_cli_refusal_does_not_echo_input_or_overwrite(self):
        path = self.root/'private-token-example.json'
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(gates.main(['init', '--out', str(path)]), 0)
            saved = path.read_bytes()
            self.assertEqual(gates.main(['init', '--out', str(path)]), 2)
        self.assertEqual(path.read_bytes(), saved)
        self.assertNotIn(path.name, output.getvalue())
        path.write_text('https://user:secret@provider.invalid')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(gates.main(['check', '--packet', str(path), '--identity', str(path), '--evidence-root', str(self.root)]), 2)
        for token in ('secret', 'provider.invalid', path.name):
            self.assertNotIn(token, output.getvalue())

    def test_empty_and_oversized_artifacts_refused(self):
        self.file.write_bytes(b'')
        self.assertFalse(self.result()['packet_complete'])
        with self.file.open('wb') as stream: stream.truncate(gates.MAX_ARTIFACT+1)
        self.assertFalse(self.result()['packet_complete'])


if __name__ == '__main__':
    unittest.main()
