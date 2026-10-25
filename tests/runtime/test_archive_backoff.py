"""IDEA-100 DB5 (archive backoff and daily export cap) and DB2's read-only top-queries check.

Run 4's archive loop re-ran a heavy export every minute and drained the database's CPU credits (IDEA-100). DB5 adds
two bounds on top of IDEA-094's once-per-slot latch: at most three backup exports per UTC day, counted from the
durable outbox, and an exponential pause of the heavy steps after a failed `operations once`, while the hourly
anchor and the health metrics keep their one-minute cadence.
"""

import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from larp.contracts import ContractError
from larp.runtime.maintenance import HOUR_MS, Maintenance
from tests.runtime.test_archive_budget import DAY_MS, T0, grow
from tests.runtime.test_journal_growth import Growth

MINUTE = 60_000
REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / 'docs/build/ops/rehearsal-install-s4-20261025/checks/db-top-queries.sh'


class DailyCap(Growth):
    def capped(self):
        return Maintenance(self.store, self.archive(), backup_interval_ms=DAY_MS, retry_ms=1000,
                           max_payload_bytes=64 * 1024 * 1024, max_exports_per_day=3)

    def test_db5_a_fourth_export_in_a_utc_day_is_refused_and_named(self):
        worker = self.capped()
        grow(self, 0, 3, audit_every=None)
        self.assertEqual(T0, worker.prepare_backup('run', T0 + MINUTE))  # the day's scheduled backup
        for hour, i in ((1, 3), (2, 4)):                                 # two incident backups, one per hour
            grow(self, i, 1, audit_every=None, incident_at=(i,))
            self.assertIsNotNone(worker.prepare_backup('run', T0 + hour * HOUR_MS + MINUTE))
        grow(self, 5, 1, audit_every=None, incident_at=(5,))
        self.assertIsNone(worker.prepare_backup('run', T0 + 3 * HOUR_MS + MINUTE))  # the fourth is refused
        self.assertEqual(3, len(self.rows()))
        self.assertIn('BACKUP_DAILY_CAP', worker.health('run', T0 + 3 * HOUR_MS + MINUTE).read()['reasons'])

    def test_db5_the_count_is_durable_across_a_new_process(self):
        grow(self, 0, 3, audit_every=None)
        for hour, i in ((0, None), (1, 3), (2, 4), (3, 5)):
            if i is not None:
                grow(self, i, 1, audit_every=None, incident_at=(i,))
            self.capped().prepare_backup('run', T0 + hour * HOUR_MS + MINUTE)  # a new Maintenance each time
        self.assertEqual(3, len(self.rows()))

    def test_db5_the_next_utc_day_exports_again(self):
        worker = self.capped()
        grow(self, 0, 3, audit_every=None)
        worker.prepare_backup('run', T0 + MINUTE)
        for hour, i in ((1, 3), (2, 4)):
            grow(self, i, 1, audit_every=None, incident_at=(i,))
            worker.prepare_backup('run', T0 + hour * HOUR_MS + MINUTE)
        self.assertEqual(T0 + DAY_MS, worker.prepare_backup('run', T0 + DAY_MS + MINUTE))
        self.assertNotIn('BACKUP_DAILY_CAP', worker.health('run', T0 + DAY_MS + MINUTE).read()['reasons'])

    def test_db5_without_a_cap_behaviour_is_unchanged(self):
        worker = self.worker()
        grow(self, 0, 3, audit_every=None)
        worker.prepare_backup('run', T0 + MINUTE)
        for hour, i in ((1, 3), (2, 4), (3, 5)):
            grow(self, i, 1, audit_every=None, incident_at=(i,))
            self.assertIsNotNone(worker.prepare_backup('run', T0 + hour * HOUR_MS + MINUTE))

    def test_db5_operations_once_uses_three_by_default(self):
        seen = []
        original = Maintenance.__init__

        def spy(worker, *args, **kwargs):
            seen.append(kwargs.get('max_exports_per_day'))
            original(worker, *args, **kwargs)
        grow(self, 0, 2, audit_every=None)
        with patch.object(Maintenance, '__init__', spy):
            self.run_fresh(T0 + MINUTE)
        self.assertEqual([3], seen)

    def test_db5_the_cap_must_be_a_positive_integer(self):
        for bad in (0, -1, True, '3', 1.5):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                Maintenance(self.store, self.archive(), backup_interval_ms=DAY_MS, max_exports_per_day=bad)


class Backoff(Growth):
    def once(self, now_ms, *, fail=True, state=True):
        """`operations once` in a new process. With `fail`, the backup step raises on every attempt (a database or
        export failure that repeats). Returns (health, number of backup attempts, number of full checks)."""
        calls = dict(backup=0, full=0)
        full = Maintenance.full_check

        def backup(worker, *args):
            calls['backup'] += 1
            if fail:
                raise RuntimeError('synthetic repeated failure')
            return None

        def counted_full(worker, *args):
            calls['full'] += 1
            return full(worker, *args)
        saved, self.store = self.store, type(self.store)(self.store._dsn)
        environment = {'STATE_DIRECTORY': str(self.state)} if state else {}
        try:
            with patch.dict('os.environ', environment), \
                    patch.object(Maintenance, 'prepare_backup', backup), \
                    patch.object(Maintenance, 'full_check', counted_full):
                if not state:
                    os.environ.pop('STATE_DIRECTORY', None)
                _, health = self.run_once(now_ms)
        finally:
            self.store = saved
        return health, calls['backup'], calls['full']

    def test_db5_failures_pause_the_heavy_steps_on_the_backoff_schedule(self):
        grow(self, 0, 3, audit_every=None)
        now = T0 + MINUTE
        health, backups, _ = self.once(now)
        self.assertEqual(1, backups)
        self.assertIn('ARCHIVE_PREPARATION_FAILED', health['reasons'])
        waits = []
        for _ in range(8):
            # Probe every 30 s until the heavy steps run again (and fail again).
            step = 0
            while True:
                step += 30_000
                health, backups, fulls = self.once(now + step)
                if backups:
                    break
                self.assertIn('ARCHIVE_BACKOFF', health['reasons'])
                self.assertFalse(health['healthy'])
                self.assertEqual(0, fulls)
            waits.append(step // 1000)
            now += step
        self.assertEqual([60, 120, 240, 480, 960, 1920, 3600, 3600], waits)

    def test_db5_anchors_and_health_continue_during_backoff(self):
        grow(self, 0, 3, audit_every=None)
        self.once(T0 + MINUTE)                                   # fails: 60 s pause
        self.once(T0 + 2 * MINUTE)                               # runs the heavy steps, fails again: 120 s pause
        grow(self, 3, 1, audit_every=None)
        health, backups, _ = self.once(T0 + HOUR_MS)             # next hour, still inside the pause
        self.assertEqual(0, backups)
        self.assertIn('ARCHIVE_BACKOFF', health['reasons'])
        self.assertEqual(2, len(self.anchors()))                 # the new hour's anchor was prepared and delivered
        self.assertTrue(self.published())                        # and health was published

    def test_db5_a_clean_run_clears_the_backoff(self):
        grow(self, 0, 3, audit_every=None)
        self.once(T0 + MINUTE)
        health, backups, _ = self.once(T0 + 3 * MINUTE, fail=False)   # the pause is over and nothing fails
        self.assertEqual(1, backups)
        self.assertNotIn('ARCHIVE_BACKOFF', health['reasons'])
        health, backups, _ = self.once(T0 + 3 * MINUTE + 10_000, fail=False)
        self.assertEqual(1, backups)                                  # no pause after a clean run
        self.assertNotIn('ARCHIVE_BACKOFF', health['reasons'])

    def test_db5_without_a_state_directory_there_is_no_backoff(self):
        grow(self, 0, 3, audit_every=None)
        self.once(T0 + MINUTE, state=False)
        health, backups, _ = self.once(T0 + MINUTE + 10_000, state=False)
        self.assertEqual(1, backups)
        self.assertNotIn('ARCHIVE_BACKOFF', health['reasons'])
        self.assertEqual([], list(self.state.iterdir()))


class TopQueries(unittest.TestCase):
    def test_db2_the_check_is_read_only_and_bounded(self):
        text = CHECK.read_text()
        subprocess.run(['bash', '-n', str(CHECK)], check=True)
        for needed in ('READ ONLY', 'pg_stat_statements', 'LIMIT 15', '160', 'statement_timeout', 'TOP_QUERIES_DONE'):
            self.assertIn(needed, text)
        sql = text.upper()
        for write in ('INSERT ', 'UPDATE ', 'DELETE ', 'CREATE ', 'DROP ', 'ALTER ', 'TRUNCATE', 'PG_STAT_STATEMENTS_RESET'):
            self.assertNotIn(write, sql)
