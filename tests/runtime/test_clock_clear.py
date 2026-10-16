"""D-DN-10 (IDEA-049-D CK1-CK6): a CLOCK HALT clears itself after 30 minutes of a monotonic, NTP-synchronised clock.

No person clears it (F-114). Without a synchronisation signal it stays latched, as before. The integrity quarantine is
separate and never clears here.
"""
import unittest

from larp.runtime.coordinator import Coordinator, halt_reasons
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy
from larp.runtime.supervision import Guard
from tests.support import DatabaseCase, request

NOW = 1791590400000
MINUTE = 60_000
WINDOW = 30 * MINUTE


class Signal(unittest.TestCase):
    """CK1: the kernel's own clock status, fail closed."""

    def test_ck1_only_a_clean_synchronised_kernel_state_counts(self):
        from larp.runtime.supervision import kernel_clock_synchronized
        cases = {(0, 0): True, (1, 0): True, (5, 0): False, (0, 0x40): False, (-1, 0): False, (0, 0x40 | 0x1): False}
        for (state, status), expected in cases.items():
            with self.subTest(state=state, status=status):
                self.assertIs(kernel_clock_synchronized(call=lambda: (state, status)), expected)

    def test_ck1_a_failing_or_missing_call_is_not_synchronised(self):
        from larp.runtime.supervision import kernel_clock_synchronized

        def broken():
            raise OSError('adjtimex unavailable')
        self.assertIs(kernel_clock_synchronized(call=broken), False)
        self.assertIn(kernel_clock_synchronized(), (True, False))  # the real call answers with a bool


class Clock:
    def __init__(self, synced=True):
        self.synced = synced

    def __call__(self):
        return self.synced


class ClockClear(DatabaseCase):
    def coordinator(self, clock=NOW):
        return Coordinator(self.store, FakeAssessor(), FakePolicy(), FakePlanner(), execution=FakeExecution(),
                           run_id='run', version_id='synthetic', profile_hash='a' * 64, address='0x' + '1' * 40,
                           clock_ms=lambda: clock)

    def guard(self, sync=None):
        if sync is None:
            return Guard(self.store, 'run', max_failures=3, clear_after=2)
        return Guard(self.store, 'run', max_failures=3, clear_after=2, clock_sync=sync, clock_clear_after_ms=WINDOW)

    def reasons(self):
        return halt_reasons(self.store.load('run').read()['projection'])

    def commands(self):
        with self.store.transaction() as db:
            return db.execute("SELECT count(*) FROM commands WHERE run_id='run'").fetchone()[0]

    def halted(self, guard):
        self.coordinator().start('r1', request('BUY'), NOW)
        self.assertEqual(guard.evaluate(NOW - 1), ['HALT:CLOCK'])
        self.assertEqual(self.reasons(), ['CLOCK'])

    # ---------------------------------------------------------------- CK2
    def test_ck2_clears_after_thirty_synchronised_monotonic_minutes_and_trading_resumes(self):
        guard = self.guard(Clock())
        self.halted(guard)
        opened = NOW + 1
        self.assertEqual(guard.evaluate(opened), [])  # the window opens
        self.assertEqual(guard.evaluate(opened + 10 * MINUTE), [])
        self.assertEqual(guard.evaluate(opened + WINDOW - 1), [])  # not a millisecond early
        self.assertEqual(self.reasons(), ['CLOCK'])
        self.assertEqual(guard.evaluate(opened + WINDOW), ['CLEAR:CLOCK'])
        self.assertEqual(self.reasons(), [])
        [cleared] = [d.read()['event'] for d in self.store.journal('run')
                     if d.read()['event']['kind'] == 'HALT_CLEARED']
        self.assertEqual((cleared['reason'], cleared['detail']['synchronized_since_ms']), ('CLOCK', opened))
        self.coordinator(clock=opened + WINDOW + 1).start('r2', request('BUY', job='j2'), opened + WINDOW + 1)
        [record] = [d.read()['event']['record'] for d in self.store.journal('run')
                    if d.read()['event']['kind'] == 'ROUND_PLANNED' and d.read()['event']['record']['round_id'] == 'r2']
        self.assertFalse([e for e in record['errors'] if e.startswith('HALTED')])  # a later round is no longer halted
        self.assertNotEqual(record['plan']['reasons'], ['HALTED'])  # and the planner ran

    # ---------------------------------------------------------------- CK3
    def test_ck3_an_unsynchronised_reading_restarts_the_window(self):
        clock = Clock()
        guard = self.guard(clock)
        self.halted(guard)
        guard.evaluate(NOW + 1)
        clock.synced = False
        self.assertEqual(guard.evaluate(NOW + 20 * MINUTE), [])
        clock.synced = True
        reopened = NOW + 21 * MINUTE
        self.assertEqual(guard.evaluate(reopened), [])
        self.assertEqual(guard.evaluate(NOW + 1 + WINDOW), [])  # the first window no longer counts
        self.assertEqual(guard.evaluate(reopened + WINDOW), ['CLEAR:CLOCK'])

    def test_ck3_a_step_back_between_evaluations_restarts_the_window(self):
        guard = self.guard(Clock())
        self.halted(guard)
        guard.evaluate(NOW + 1)
        guard.evaluate(NOW + 10 * MINUTE)
        stepped = NOW + 5 * MINUTE  # earlier than the previous evaluation, still after the last decision
        self.assertEqual(guard.evaluate(stepped), [])
        self.assertEqual(guard.evaluate(NOW + 1 + WINDOW), [])
        self.assertEqual(guard.evaluate(stepped + WINDOW), ['CLEAR:CLOCK'])

    def test_ck3_a_time_behind_the_last_decision_restarts_the_window(self):
        guard = self.guard(Clock())
        self.halted(guard)
        guard.evaluate(NOW + 1)
        self.assertEqual(guard.evaluate(NOW - 5), [])  # still halted; nothing new to journal
        self.assertEqual(self.reasons(), ['CLOCK'])
        self.assertEqual(guard.evaluate(NOW + 1 + WINDOW), [])  # the window restarted there
        self.assertEqual(guard.evaluate(NOW + 1 + 2 * WINDOW), ['CLEAR:CLOCK'])

    # ---------------------------------------------------------------- CK4
    def test_ck4_without_a_signal_the_clock_halt_stays_latched(self):
        guard = self.guard()
        self.halted(guard)
        for t in (NOW + 1, NOW + WINDOW + 1, NOW + 3 * WINDOW):
            self.assertNotIn('CLEAR:CLOCK', guard.evaluate(t))
        self.assertIn('CLOCK', self.reasons())

    def test_ck4_clearing_the_clock_leaves_other_reasons_in_place(self):
        guard = self.guard(Clock())
        self.halted(guard)
        guard._halt('REPEATED_FAILURES', NOW + 1, {})
        guard.evaluate(NOW + 2)
        actions = guard.evaluate(NOW + 2 + WINDOW)
        self.assertIn('CLEAR:CLOCK', actions)
        self.assertNotIn('CLOCK', self.reasons())


class Wiring(unittest.TestCase):
    """CK5: the production service passes the kernel signal and 30 minutes."""

    def test_ck5_runtime_guard_uses_the_kernel_signal_and_thirty_minutes(self):
        from larp.runtime.service import runtime_guard
        from larp.runtime.supervision import kernel_clock_synchronized
        guard = runtime_guard(object(), dict(run_id='run', max_failures=3, clear_after=2))
        self.assertIs(guard.clock_sync, kernel_clock_synchronized)
        self.assertEqual(guard.clock_clear_after_ms, 30 * MINUTE)


if __name__ == '__main__':
    unittest.main()
