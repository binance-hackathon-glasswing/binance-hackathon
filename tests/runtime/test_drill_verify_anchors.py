"""LD21-H RG4 harness: downloaded anchors verify read-only against the journal; tampering and gaps are reported."""
import importlib.util
import json
from pathlib import Path
import tempfile

from larp.runtime.maintenance import HOUR_MS
from tests.runtime import test_anchors_roles as roles
from tests.runtime.test_anchors_roles import NOW

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('drill_verify_anchors', ROOT / 'tools/deploy/drill_verify_anchors.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class AnchorHarness(roles.Rounds):
    anchor = roles.Anchors.anchor  # reuse the fixture without re-running Anchors' own tests

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def download(self, anchors):
        for n, a in enumerate(anchors):
            (self.dir / f'anchor-{n}.json').write_text(json.dumps(a))
        (self.dir / 'backup-receipt.json').write_text(json.dumps(dict(schema='Backup.v1')))  # not an anchor

    def test_downloaded_anchors_pass_and_report_coverage(self):
        self.hold('r1')
        self.anchor(NOW)
        self.hold('r2')
        self.download(self.anchor(NOW + 2 * HOUR_MS))  # slot NOW+1h never written
        report, code = harness.check(self.store, 'run', self.dir)
        self.assertEqual((code, report['status'], report['anchors'], report['skipped_files']), (0, 'PASS', 2, 1))
        self.assertEqual(report['hours_spanned'], 3)
        self.assertEqual(len(report['missing_slots']), 1)
        self.assertEqual(report['journal_head'], self.store.verify('run'))

    def test_a_changed_head_fails(self):
        self.hold('r1')
        anchors = self.anchor(NOW)
        self.download([dict(anchors[0], head='f' * 64)])
        report, code = harness.check(self.store, 'run', self.dir)
        self.assertEqual((code, report['status']), (1, 'FAIL'))

    def test_no_anchors_and_cli_exit_codes(self):
        report, code = harness.check(self.store, 'run', self.dir)
        self.assertEqual((code, report['status']), (3, 'NO_ANCHORS'))
        self.hold('r1')
        self.download(self.anchor(NOW))
        config = self.dir / 'operations.json'
        config.write_text(json.dumps(dict(run_id='run')))
        self.assertEqual(harness.main(['--config', str(config), '--anchors-dir', str(self.dir)],
                                     open_store=lambda c: self.store), 0)
