"""IDEA-094 AR1-AR7: the archive job on a growing journal (run-4 incident, 2026-10-25).

Run 4's archive job was OOM-killed inside the first daily backup export: the hour's anchor stayed queued, no metric
was published, and the timer re-ran the export every minute. The synthetic journal here grows like the fixture
measurement in IDEA-094: rows of about 100 KB plus 4 KB per event, with round logs and jobs in the outboxes.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tracemalloc
from unittest.mock import MagicMock, patch

from larp.contracts import ContractError, Document
from larp.runtime.coordinator import batch_for
from larp.runtime.maintenance import HOUR_MS, Maintenance
from larp.storage.archive import S3Archive
from larp.storage.postgres import IntegrityError, digest
from tests.audit.test_protocol import event
from tests.storage.test_archive import FakeS3
from tests.runtime.test_driver import HOUR, RUN, DriverHarness
from tests.support import DatabaseCase, job

MIB = 1024 * 1024
DAY_MS = 24 * HOUR_MS
T0 = 1793318400000  # 2026-10-29T00:00:00Z, a daily backup slot
REPO = Path(__file__).resolve().parents[2]


class Killed(BaseException):
    """The process dies inside the export (systemd's oom-kill); nothing after it runs."""


def blob(seed, size):
    """Text that compresses about as well as journal JSON: hashes between repeated words."""
    words, out, h = [], 0, seed.encode()
    while out < size:
        h = hashlib.sha256(h).digest()
        item = h.hex()[:16] + ' accepted evidence statement for the issuer review '
        words.append(item)
        out += len(item)
    return ''.join(words)[:size]


def grow(case, start, count, *, base_kb=100, step_kb=4, audit_every=2, incident_at=()):
    """`audit_every=None` journals no round logs (their synthetic timestamps would breach the delivery deadline)."""
    """Commit `count` events; each row's projection is `base_kb` + `step_kb` per event so far."""
    for i in range(start, start + count):
        current = case.store.load('run')
        projection = current.read()['projection']
        projection['series'] = blob('series', base_kb * 1024)
        projection.setdefault('evidence', []).append(blob(f'evidence-{i}', step_kb * 1024))
        prefix = 'incident:' if i in incident_at else 'e'
        audit = [event(identity=f'evt-{i}', round_id=f'round-{i}', text=blob(f'log-{i}', 3000))] \
            if audit_every and i % audit_every == 0 else []
        case.store.commit(batch_for(current, f'{prefix}{i}', dict(kind='SYNTHETIC', i=i), projection=projection,
                                    audit=audit, jobs=[job(identity=f'job-{i}', lane='evidence', due=i, until=i + 1)]))


class Harness(DatabaseCase):
    def archive(self, client=None):
        self.client = client or FakeS3()
        return S3Archive(self.client, bucket='fixture', account_id='123456789012', kms_key='arn:synthetic:key',
                         prefix='archive/development', retention_days=82)

    def worker(self, **kwargs):
        kwargs.setdefault('max_payload_bytes', 64 * MIB)
        return Maintenance(self.store, self.archive(), backup_interval_ms=DAY_MS, retry_ms=1000, **kwargs)

    def objects(self, kind):
        return sorted(k for k in self.client.objects if f'/{kind}/' in k)

    def rows(self, kind='backup'):
        with self.store.transaction() as db:
            return db.execute('SELECT slot_ms,status,last_error FROM archive_outbox WHERE kind=%s ORDER BY slot_ms',
                              (kind,)).fetchall()

    def run_once(self, now_ms, export_effect=None, *, max_bytes=64 * MIB):
        """`operations once` with this test's database, fake S3 and CloudWatch; `export_effect` replaces the export."""
        from larp.runtime import operations
        c = dict(run_id='run', deployment='fixture', archive_bucket='fixture', account_id='123456789012',
                 kms_key='arn:synthetic:key', archive_prefix='archive/development', retention_days=82,
                 max_archive_bytes=max_bytes, backup_interval_hours=24, max_attempts=3, retry_seconds=60)
        self.cloudwatch = MagicMock()
        clients = dict(s3=MagicMock(), rds=MagicMock(), cloudwatch=self.cloudwatch)
        archive = self.archive(getattr(self, 'client', None))
        patches = [patch.object(operations, 'validate_config', return_value=c),
                   patch.object(operations, 'cloud_clients', return_value=clients),
                   patch.object(operations, 'S3Archive', return_value=archive),
                   patch.object(operations, 'IamPostgresStore', return_value=self.store),
                   patch.object(operations.time, 'time', return_value=now_ms / 1000)]
        printer = patch('builtins.print')
        if export_effect is not None:
            # The export function the maintenance module calls, by either name (base: export; IDEA-094: segment).
            patches += [patch('larp.runtime.maintenance.export', side_effect=export_effect, create=True),
                        patch('larp.runtime.maintenance.export_segment', side_effect=export_effect, create=True)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'operations.json'
            path.write_text('{}')
            for p in patches:
                p.start()
            output = printer.start()
            try:
                code = operations.main(['once', '--config', str(path)])
            finally:
                printer.stop()
                for p in reversed(patches):
                    p.stop()
        return code, json.loads(output.call_args.args[0])

    def published(self):
        """Healthy values sent to CloudWatch by the last run_once."""
        return [m['Value'] for call in self.cloudwatch.put_metric_data.call_args_list
                for m in call.kwargs['MetricData'] if m['MetricName'] == 'Healthy']


class Decoupling(Harness):
    def test_ar1_a_process_killed_inside_the_export_has_delivered_the_anchor_and_published_health(self):
        grow(self, 0, 4, audit_every=None)
        with self.assertRaises(Killed):
            self.run_once(T0 + 60_000, Killed)
        self.assertEqual(1, len(self.objects('anchor')))
        self.assertTrue(self.published())

    def test_ar2_a_killed_export_is_not_retried_every_minute_and_health_names_it(self):
        grow(self, 0, 4, audit_every=None)
        calls = []

        def killed(*args, **kwargs):
            calls.append(1)
            raise Killed()
        with self.assertRaises(Killed):
            self.run_once(T0 + 60_000, killed)
        for minute in (2, 3, 4):
            self.run_once(T0 + minute * 60_000, killed)
        code, health = self.run_once(T0 + 40 * 60_000, killed)  # past the stale-preparation bound
        self.assertEqual(1, len(calls))
        self.assertEqual(1, len(self.objects('anchor')))  # the hour's anchor, delivered once
        self.assertEqual(1, code)
        self.assertIn('BACKUP_PREPARATION_FAILED', health['reasons'])
        self.assertEqual('PreparationInterrupted', health['backup_failure']['error'])
        self.assertEqual({0}, set(self.published()))

    def test_ar2_a_refused_export_is_attempted_once_per_slot(self):
        grow(self, 0, 4, audit_every=None)
        calls = []

        def refused(*args, **kwargs):
            calls.append(1)
            raise ContractError('synthetic refusal')
        for minute in range(1, 6):
            code, health = self.run_once(T0 + minute * 60_000, refused)
        self.assertEqual(1, len(calls))
        self.assertEqual(1, code)
        self.assertIn('BACKUP_PREPARATION_FAILED', health['reasons'])
        self.assertEqual('ContractError', health['backup_failure']['error'])
        self.assertEqual(1, len(self.objects('anchor')))
        self.assertEqual(0, len(self.objects('backup')))
        # The next day's slot is attempted again (a later acknowledged backup supersedes the refused one).
        code, health = self.run_once(T0 + DAY_MS + 60_000)
        self.assertEqual(0, code, health)
        self.assertEqual(1, len(self.objects('backup')))


class Budget(Harness):
    def test_ar3_an_oversized_backup_is_refused_within_its_byte_bound(self):
        grow(self, 0, 120)  # about 41 MB of raw journal rows
        bound = 1 * MIB
        worker = self.worker(max_payload_bytes=bound)
        tracemalloc.start()
        try:
            try:
                worker.prepare('run', T0 + 60_000)
            except ContractError:
                pass  # the base refuses after building the whole payload
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLessEqual(peak, 2 * bound + 16 * MIB)
        rows = self.rows()
        self.assertEqual([(T0, 'PERMANENT', 'BackupOverBound')], rows)
        while worker.once('run', T0 + 120_000):
            pass
        self.assertEqual(0, len(self.objects('backup')))

    def test_ar7_full_verification_memory_does_not_grow_with_the_journal(self):
        grow(self, 0, 120)
        largest = max(self.sizes())
        growth = probe(self.store, 'verify')
        print('AR7 RSS growth', growth, 'largest row', largest, 'journal', sum(self.sizes()))
        self.assertLessEqual(growth, 2 * largest + 16 * MIB, (growth, largest))

    def sizes(self):
        with self.store.transaction() as db:
            return [r[0] for r in db.execute('SELECT octet_length(batch) FROM events')]


def probe(store, mode, *args):
    """Peak RSS growth (bytes) of `mode` in a fresh process: tracemalloc cannot see libpq's result buffers."""
    env = dict(os.environ, PYTHONPATH=str(REPO))
    out = subprocess.run([sys.executable, '-m', 'tests.runtime.memory_probe', store._dsn, mode, *map(str, args)],
                         capture_output=True, text=True, cwd=REPO, env=env, timeout=600)
    if out.returncode:
        raise AssertionError(out.stderr[-2000:])
    return json.loads(out.stdout)['growth_bytes']


class Segments(Harness):
    def deliver(self, worker, now_ms):
        while worker.once('run', now_ms):
            pass

    def segments(self):
        return [self.client.objects[k]['Body'] for k in self.objects('backup')]

    def test_ar5_ar6_a_chain_of_daily_and_incident_segments_restores_the_exact_journal(self):
        from larp.runtime.maintenance import verify_anchors
        from larp.storage.backup import restore_chain, segment_header
        worker, versions = self.worker(), []
        grow(self, 0, 6)
        versions.append(self.store.load('run').read()['version'])
        worker.prepare('run', T0 + 60_000)                       # day 1: no base, genesis to now
        self.deliver(worker, T0 + 60_000)
        grow(self, 6, 5, incident_at=(8,))
        versions.append(self.store.load('run').read()['version'])
        worker.prepare('run', T0 + 2 * HOUR_MS)                  # incident backup, based on day 1
        self.deliver(worker, T0 + 2 * HOUR_MS)
        grow(self, 11, 6)
        versions.append(self.store.load('run').read()['version'])
        worker.prepare('run', T0 + DAY_MS + 60_000)              # day 2, based on the incident backup
        self.deliver(worker, T0 + DAY_MS + 60_000)
        self.assertEqual(['ACK', 'ACK', 'ACK'], [r[1] for r in self.rows()])
        segments = self.segments()
        headers = [segment_header(s) for s in segments]
        self.assertIsNone(headers[0]['base'])
        self.assertEqual(digest(segments[0]), headers[1]['base']['sha256'])
        self.assertEqual(digest(segments[1]), headers[2]['base']['sha256'])
        # AR6: each segment holds only the events after its acknowledged base.
        self.assertEqual([(1, versions[0]), (versions[0] + 1, versions[1]), (versions[1] + 1, versions[2])],
                         [tuple(h['events']['run']) for h in headers])
        expected = self.store.verify('run')
        anchors = [Document(self.client.objects[k]['Body']) for k in self.objects('anchor')]
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        restore_chain(self.store, list(reversed(segments)))      # any order: the chain follows the base pointers
        self.assertEqual(expected, self.store.verify('run'))
        self.assertTrue(self.store.load('run').read()['quarantined'])
        self.assertEqual(3, verify_anchors(self.store, 'run', anchors)['anchors'])

    def test_ar5_broken_tampered_or_foreign_chains_are_refused(self):
        from larp.storage.backup import restore_chain
        worker = self.worker()
        grow(self, 0, 4)
        worker.prepare('run', T0 + 60_000)
        self.deliver(worker, T0 + 60_000)
        grow(self, 4, 4)
        worker.prepare('run', T0 + DAY_MS + 60_000)
        self.deliver(worker, T0 + DAY_MS + 60_000)
        first, second = self.segments()
        import gzip
        tampered = gzip.compress(gzip.decompress(second).replace(b'SYNTHETIC', b'SYNTHETIX', 1), mtime=0)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        for chain in ([second], [tampered, first], [first, first], [b'not a backup']):
            with self.subTest(len(chain)), self.assertRaises(IntegrityError):
                restore_chain(self.store, chain)
        with self.store.transaction() as db:
            self.assertEqual(0, db.execute('SELECT count(*) FROM events').fetchone()[0])

    def test_ar5_a_segment_of_another_chain_is_refused(self):
        from larp.storage.backup import export_segment, restore_chain
        grow(self, 0, 4)
        own = export_segment(self.store, max_bytes=64 * MIB)
        foreign = export_segment(self.store, max_bytes=64 * MIB,
                                 base=dict(sha256='f' * 64, slot_ms=0, through={'run': 2}))
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        with self.assertRaises(IntegrityError):
            restore_chain(self.store, [foreign.payload, own.payload])

    def test_ar6_an_unacknowledged_backup_is_never_a_base(self):
        from larp.storage.backup import segment_header

        class Down:
            def put(self, *args, **kwargs):
                from larp.storage.postgres import Unavailable
                raise Unavailable('synthetic outage')
        worker = self.worker()
        grow(self, 0, 4)
        worker.prepare('run', T0 + 60_000)
        worker.archive = Down()
        self.deliver(worker, T0 + 60_000)                         # day 1 stays PENDING
        worker.archive = self.archive(self.client)
        grow(self, 4, 4)
        worker.prepare('run', T0 + DAY_MS + 60_000)
        with self.store.transaction() as db:
            raw = db.execute("SELECT payload FROM archive_outbox WHERE kind='backup' AND slot_ms=%s",
                             (T0 + DAY_MS,)).fetchone()[0]
        header = segment_header(bytes(raw))
        self.assertIsNone(header['base'])
        self.assertEqual([1, self.store.load('run').read()['version']], header['events']['run'])

    def test_ar5_v1_backups_still_restore(self):
        from larp.storage.backup import export, restore
        grow(self, 0, 4)
        backup = export(self.store)
        expected = self.store.verify('run')
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        restore(self.store, backup)
        self.assertEqual(expected, self.store.verify('run'))


class Fixture(DriverHarness):
    """AR4 on the IDEA-094 fixture journal (DriverHarness, one issuer, hourly rounds)."""

    def test_ar4_segment_export_memory_is_a_fraction_of_v1_and_flat_per_day(self):
        from larp.storage.backup import export, export_segment
        self.world(['EXSEMI_402_8K'])
        driver, peaks = self.driver(), {}

        def traced(fn):
            tracemalloc.start()
            try:
                fn()
                return tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
        for rounds in (24, 48, 72, 96):
            for _ in range(24):
                self.tick(driver, HOUR)
            if rounds in (24, 72):
                base = dict(sha256='0' * 64, slot_ms=0, through={RUN: self.store.load(RUN).read()['version']})
            else:
                peaks[rounds] = traced(lambda: export_segment(self.store, base=base, max_bytes=64 * MIB))
        peaks['v1'] = traced(lambda: export(self.store))
        peaks['full'] = traced(lambda: export_segment(self.store, max_bytes=64 * MIB))
        print('AR4 traced peaks (bytes):', peaks)
        self.assertLessEqual(peaks['full'], 0.25 * peaks['v1'])
        self.assertLessEqual(peaks[96], 2 * peaks[48])
