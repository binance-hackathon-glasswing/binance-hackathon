"""IDEA-095 SD1-SD6: no whole-journal re-read on the hourly anchor or inside a trading cycle.

`operations once` is a new process every run, so before IDEA-095 each hourly anchor re-hashed the whole journal, and
balance adoption (`_quiet_since`) ran a full verification inside a runtime cycle. Here each run gets a fresh store,
as a new process would, and `_verify` is watched for the version it continues from (None = from genesis).
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from larp.contracts import Document
from larp.storage.postgres import IntegrityError, PostgresStore, digest
from tests.runtime.test_archive_budget import DAY_MS, HOUR_MS, T0, Harness, Killed, grow
from tests.runtime.test_host_units import directives, value

MINUTE = 60_000


@contextmanager
def bases(kill_full=False):
    """The `base` version of every `_verify` call (None: from genesis). `kill_full` kills a full one (oom/timeout)."""
    calls, original = [], PostgresStore._verify

    def watched(db, run_id, run, base=None):
        calls.append(None if base is None else base['version'])
        if kill_full and base is None:
            raise Killed()
        return original(db, run_id, run, base)
    with patch.object(PostgresStore, '_verify', staticmethod(watched)):
        yield calls


class Growth(Harness):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state = Path(directory.name)

    def run_fresh(self, now_ms, *, state=True, kill_full=False):
        """`operations once` in a new process: a new store (no in-memory checkpoint) and, if set, the state directory."""
        environment = {'STATE_DIRECTORY': str(self.state)} if state else {}
        saved, self.store = self.store, PostgresStore(self.store._dsn)
        try:
            with patch.dict(os.environ, environment), bases(kill_full) as calls:
                if 'STATE_DIRECTORY' in os.environ and not state:
                    del os.environ['STATE_DIRECTORY']
                result = self.run_once(now_ms)
            return result, calls
        finally:
            self.store = saved

    def anchors(self):
        """The delivered anchors, oldest first."""
        found = [Document(self.client.objects[key]['Body']).read() for key in self.objects('anchor')]
        return sorted(found, key=lambda a: a['slot_ms'])

    def saved(self):
        from larp.runtime.maintenance import VerificationState
        return VerificationState(self.state).load('run')

    def tamper(self, sequence, *, rehash=False):
        """Change one journal row's bytes; `rehash` also rewrites its batch hash (but not the head chain)."""
        with self.store.transaction() as db:
            raw = bytes(db.execute('SELECT batch FROM events WHERE sequence=%s', (sequence,)).fetchone()[0])
            changed = raw.replace(b'"SYNTHETIC"', b'"SYNTHETIX"')
            self.assertNotEqual(raw, changed)
            db.execute('UPDATE events SET batch=%s WHERE sequence=%s', (changed, sequence))
            if rehash:
                db.execute('UPDATE events SET batch_hash=%s WHERE sequence=%s', (digest(changed), sequence))


class Anchors(Growth):
    def test_sd1_later_anchors_verify_only_the_events_after_the_saved_checkpoint(self):
        grow(self, 0, 4, audit_every=None)
        (code, health), calls = self.run_fresh(T0 + MINUTE)
        self.assertEqual(0, code, health)
        self.assertEqual(None, calls[0])  # the first anchor of a host verifies from genesis
        grow(self, 4, 3, audit_every=None)
        (code, health), calls = self.run_fresh(T0 + HOUR_MS + MINUTE)
        self.assertEqual(0, code, health)
        self.assertEqual([4], calls)
        run = self.store.load('run').read()
        self.assertEqual((7, run['head']), (self.anchors()[-1]['sequence'], self.anchors()[-1]['head']))
        grow(self, 7, 2, audit_every=None)
        _, calls = self.run_fresh(T0 + 2 * HOUR_MS + MINUTE)
        self.assertEqual([7], calls)

    def test_sd2_an_unusable_checkpoint_means_a_full_verification(self):
        from larp.runtime.maintenance import VerificationState
        state = VerificationState(self.state)
        grow(self, 0, 4, audit_every=None)
        self.run_fresh(T0 + MINUTE)
        good = state.load('run')
        self.assertEqual(4, good['checkpoint']['version'])
        cases = [('missing', None), ('corrupt', b'{not json'), ('schema', dict(good, schema='Other.v1')),
                 ('other run', dict(good, run_id='other')),
                 ('replaced head', dict(good, checkpoint=dict(good['checkpoint'], head='f' * 64))),
                 ('malformed', dict(good, checkpoint=dict(good['checkpoint'], reservations='x')))]
        for hour, (name, content) in enumerate(cases, start=1):
            with self.subTest(name):
                path = state.path('run')
                if content is None:
                    path.unlink()
                else:
                    path.write_bytes(content if type(content) is bytes else json.dumps(content).encode())
                grow(self, 3 + hour, 1, audit_every=None)
                (code, health), calls = self.run_fresh(T0 + hour * HOUR_MS + MINUTE)
                self.assertEqual(0, code, health)
                self.assertEqual(None, calls[0])
                self.assertEqual(self.store.load('run').read()['head'], self.anchors()[-1]['head'])

    def test_sd2_an_event_changed_after_the_checkpoint_is_still_refused(self):
        grow(self, 0, 4, audit_every=None)
        self.run_fresh(T0 + MINUTE)
        grow(self, 4, 2, audit_every=None)
        self.tamper(6)
        (code, health), calls = self.run_fresh(T0 + HOUR_MS + MINUTE)
        self.assertEqual(4, calls[0])
        self.assertEqual(1, code)
        self.assertIn('IntegrityError', health['preparation_error'])
        self.assertEqual([T0], [a['slot_ms'] for a in self.anchors()])  # no anchor for the changed journal

    def test_sd2_an_unwritable_state_directory_never_costs_the_anchor(self):
        grow(self, 0, 4, audit_every=None)
        self.state = self.state / 'missing'
        (code, health), calls = self.run_fresh(T0 + MINUTE)
        self.assertEqual(None, calls[0])
        self.assertEqual(1, len(self.anchors()))
        self.assertEqual(1, code)  # the full check cannot record its attempt, so it does not run, and says so
        self.assertIn('FileNotFoundError', health['preparation_error'])

    def test_sd4_without_a_state_directory_every_anchor_verifies_in_full(self):
        grow(self, 0, 4, audit_every=None)
        self.run_fresh(T0 + MINUTE, state=False)
        grow(self, 4, 2, audit_every=None)
        (code, health), calls = self.run_fresh(T0 + HOUR_MS + MINUTE, state=False)
        self.assertEqual(0, code, health)
        self.assertEqual([None], calls)
        self.assertEqual([], list(self.state.iterdir()))


class FullCheck(Growth):
    def test_sd3_the_full_check_runs_once_per_backup_interval(self):
        grow(self, 0, 4, audit_every=None)
        _, calls = self.run_fresh(T0 + MINUTE)
        self.assertEqual(1, calls.count(None))  # the anchor's full verification counts for this interval
        _, calls = self.run_fresh(T0 + HOUR_MS + MINUTE)
        self.assertNotIn(None, calls)
        grow(self, 4, 2, audit_every=None)
        (code, health), calls = self.run_fresh(T0 + DAY_MS + MINUTE)
        self.assertEqual(0, code, health)
        self.assertEqual(1, calls.count(None))
        self.assertEqual(None, calls[-1])  # last: after the anchor, health and backup
        self.assertEqual(T0 + DAY_MS + MINUTE, self.saved()['full_ms'])
        _, calls = self.run_fresh(T0 + DAY_MS + HOUR_MS + MINUTE)
        self.assertNotIn(None, calls)

    def test_sd3_a_killed_full_check_is_not_retried_within_its_interval(self):
        grow(self, 0, 4, audit_every=None)
        self.run_fresh(T0 + MINUTE)
        with self.assertRaises(Killed):
            self.run_fresh(T0 + DAY_MS + MINUTE, kill_full=True)
        self.assertEqual(2, len(self.anchors()))  # the day's anchor was sent before the full check
        for minute in (2, 3, 4):
            (code, health), calls = self.run_fresh(T0 + DAY_MS + minute * MINUTE)
            self.assertNotIn(None, calls)
            self.assertEqual(0, code, health)
        _, calls = self.run_fresh(T0 + 2 * DAY_MS + MINUTE)
        self.assertEqual(None, calls[-1])  # attempted again in the next interval

    def test_sd3_a_row_changed_before_the_checkpoint_is_found_by_the_full_check(self):
        grow(self, 0, 4, audit_every=None)
        self.run_fresh(T0 + MINUTE)
        grow(self, 4, 2, audit_every=None)
        self.tamper(2)
        (code, health), _ = self.run_fresh(T0 + HOUR_MS + MINUTE)
        self.assertEqual(0, code, health)  # the incremental anchor does not re-hash row 2 (IDEA-095 tradeoff)
        (code, health), _ = self.run_fresh(T0 + DAY_MS + MINUTE)
        self.assertEqual(1, code)
        self.assertIn('IntegrityError', health['preparation_error'])
        self.assertIsNone(self.saved().get('checkpoint'))
        before = len(self.anchors())
        (code, health), calls = self.run_fresh(T0 + DAY_MS + HOUR_MS + MINUTE)
        self.assertEqual(None, calls[0])
        self.assertEqual(1, code)
        self.assertIn('ARCHIVE_PREPARATION_FAILED', health['reasons'])
        self.assertEqual(before, len(self.anchors()))

    def test_sd3_overdue_full_check_is_reported_after_two_intervals(self):
        from larp.runtime.maintenance import VerificationState
        grow(self, 0, 4, audit_every=None)
        self.run_fresh(T0 + MINUTE)
        state = VerificationState(self.state)
        now = T0 + HOUR_MS + MINUTE
        for full_ms, overdue in ((now - 2 * DAY_MS + MINUTE, False), (now - 2 * DAY_MS - MINUTE, True)):
            with self.subTest(overdue=overdue):
                state.save('run', full_ms=full_ms, attempt_ms=T0 + MINUTE)
                (code, health), _ = self.run_fresh(now)
                self.assertEqual(overdue, 'FULL_VERIFICATION_OVERDUE' in health['reasons'])
                self.assertEqual(int(overdue), code)


    def test_sd3_a_full_check_that_never_completes_is_reported_after_two_intervals(self):
        grow(self, 0, 4, audit_every=None)
        self.run_fresh(T0 + MINUTE, state=False)  # this hour's anchor exists before the state directory does
        (code, health), _ = self.run_fresh(T0 + 2 * MINUTE, kill_full=False)
        self.assertEqual(0, code, health)  # no completed full check yet, and not overdue
        self.assertEqual(T0 + 2 * MINUTE, self.saved()['full_ms'])
        self.saved_state_without_full()
        for day, overdue in ((1, False), (2, False), (3, True)):
            with self.assertRaises(Killed):
                self.run_fresh(T0 + day * DAY_MS + 3 * MINUTE, kill_full=True)
            (code, health), _ = self.run_fresh(T0 + day * DAY_MS + 4 * MINUTE)
            self.assertEqual(overdue, 'FULL_VERIFICATION_OVERDUE' in health['reasons'], day)

    def saved_state_without_full(self):
        from larp.runtime.maintenance import VerificationState
        state = VerificationState(self.state)
        value = state.load('run')
        value.pop('full_ms')
        value.pop('first_attempt_ms', None)
        state.path('run').write_text(json.dumps(value))

    def test_sd1_an_incident_backup_later_in_the_hour_continues_from_the_checkpoint(self):
        grow(self, 0, 4, audit_every=None)
        self.run_fresh(T0 + MINUTE)
        self.run_fresh(T0 + HOUR_MS + MINUTE)  # this hour's anchor: the next run has none to prepare
        grow(self, 4, 2, audit_every=None, incident_at=(5,))
        (code, health), calls = self.run_fresh(T0 + HOUR_MS + 30 * MINUTE)
        self.assertEqual(0, code, health)
        self.assertEqual(2, len(self.objects('backup')))  # the daily segment and the incident segment
        self.assertNotIn(None, calls)


class TradingCycle(Growth):
    def test_sd5_journal_suffix_continues_from_the_process_checkpoint(self):
        grow(self, 0, 6, audit_every=None)  # the commit path leaves this process's checkpoint at version 6
        full = [d.payload for d in self.store.journal('run', after_version=2, through_version=5)]
        with bases() as calls:
            suffix = self.store.journal('run', after_version=2, through_version=5, full=False)
        self.assertNotIn(None, calls)
        self.assertEqual(full, [d.payload for d in suffix])
        self.assertEqual(3, len(suffix))

    def test_sd5_journal_suffix_refuses_a_changed_row(self):
        self.refused(4, rehash=False)

    def test_sd5_journal_suffix_refuses_a_rehashed_row_off_the_head_chain(self):
        self.refused(5, rehash=True)

    def refused(self, sequence, *, rehash):
        grow(self, 0, 6, audit_every=None)
        self.store = PostgresStore(self.store._dsn)
        self.store.verified_snapshot('run', full=False)  # this process's checkpoint, at version 6
        self.tamper(sequence, rehash=rehash)
        with self.assertRaises(IntegrityError):
            self.store.journal('run', after_version=2, through_version=6, full=False)

    def test_sd5_balance_adoption_reads_the_journal_without_a_full_verification(self):
        from larp.runtime.driver import BalanceCheck
        check = BalanceCheck.__new__(BalanceCheck)
        check.coordinator = MagicMock()
        check.coordinator.store.journal.return_value = []
        check._quiet_since(dict(version=3, epoch=1, execution_state={}, portfolio={}, settled_block=1),
                           dict(version=3))
        self.assertIs(False, check.coordinator.store.journal.call_args.kwargs.get('full'))


class Unit(unittest.TestCase):
    def test_sd6_the_archive_unit_keeps_its_state_directory_private(self):
        d = directives('larp-archive')
        self.assertEqual(['larp-archive'], value(d, 'StateDirectory'))
        self.assertEqual(['0700'], value(d, 'StateDirectoryMode'))
