"""Supervisor restart incidents and the autonomous HALT (DR-13; IDEA-042 item 5, criteria H1-H6)."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

from larp.audit.delivery import DeliveryWorker
from larp.contracts import ContractError
from larp.runtime.coordinator import Coordinator, halt_reasons
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy, FakeReceiver, settle
from larp.runtime.replay import replay
from larp.runtime.service import EXIT_QUARANTINED, EXIT_REFUSED, Service, StartRefused, main
from larp.runtime.supervision import Guard, Sessions
from larp.storage.postgres import Conflict, doc
from tests.support import DatabaseCase, request

NOW = 1791590400000
DAY = 86_400_000
ROOT = Path(__file__).resolve().parents[2]


class Raising:
    def plan(self, *args):
        raise RuntimeError('synthetic planner outage')


class Toggle:
    """A planner that fails until it is repaired."""

    def __init__(self):
        self.broken, self.calls = True, 0

    def plan(self, snapshot, proposal):
        self.calls += 1
        if self.broken:
            raise RuntimeError('synthetic planner outage')
        return FakePlanner().plan(snapshot, proposal)


class Rounds:
    """A driver that runs one coordinator round per cycle."""

    def __init__(self, coordinator, action='HOLD'):
        self.coordinator, self.action, self.n = coordinator, action, 0

    def once(self, now_ms):
        self.n += 1
        self.coordinator.start(f'round-{now_ms}-{self.n}', request(self.action, job=f'job-{now_ms}-{self.n}'), now_ms)


class Crash:
    def once(self, now_ms):
        raise RuntimeError('synthetic crash')


class Supervision(DatabaseCase):
    def coordinator(self, *, planner=None, clock=NOW):
        return Coordinator(self.store, FakeAssessor(), FakePolicy(), planner or FakePlanner(), execution=FakeExecution(),
                           run_id='run', version_id='synthetic', profile_hash='a' * 64, address='0x' + '1' * 40,
                           clock_ms=lambda: clock)

    def guard(self, **limits):
        return Guard(self.store, 'run', **dict(dict(max_failures=3, clear_after=2), **limits))

    def kinds(self):
        return [d.read()['event']['kind'] for d in self.store.journal('run')]

    def incidents(self):
        return [d.read()['event']['incident'] for d in self.store.journal('run')
                if d.read()['event']['kind'] == 'INCIDENT']

    def service(self, driver, build='build-1', session=None):
        return Service(self.store, 'run', build, guard=self.guard(), driver=driver, clock_ms=lambda: NOW,
                       sleep=lambda s: None, session_id=session)

    def projection(self):
        return self.store.load('run').read()['projection']

    def commands(self):
        with self.store.transaction() as db:
            return db.execute("SELECT count(*) FROM commands WHERE run_id='run'").fetchone()[0]

    # ---------------------------------------------------------------- H1
    def test_h1_clean_restart_records_no_incident(self):
        self.assertEqual(self.service(Rounds(self.coordinator()), session='s1').run(max_cycles=1), 0)
        self.assertEqual(self.service(Rounds(self.coordinator()), session='s2').run(max_cycles=1), 0)
        self.assertEqual(self.incidents(), [])

    def test_h1_crash_then_restart_records_one_incident(self):
        with self.assertRaises(RuntimeError):
            self.service(Crash(), session='s1').run()
        self.service(Rounds(self.coordinator()), session='s2').run(max_cycles=1)
        self.service(Rounds(self.coordinator()), session='s3').run(max_cycles=1)
        (incident,) = self.incidents()
        self.assertEqual((incident['type'], incident['session_id'], incident['previous_sessions'], incident['build_id']),
                         ('RESTART', 's2', ['s1'], 'build-1'))

    def test_h1_a_different_build_is_refused(self):
        self.service(Rounds(self.coordinator()), session='s1').run(max_cycles=1)
        with self.assertRaises(ContractError):
            Sessions(self.store, 'run').begin(session_id='s2', build_id='build-2', now_ms=NOW)
        with self.assertRaises(ContractError):
            Sessions(self.store, 'run').begin(session_id='s1', build_id='build-1', now_ms=NOW)  # reused ID

    # ---------------------------------------------------------------- H3, H4, H5
    def test_h3_h4_clock_halt_is_latched_and_stops_signing(self):
        c = self.coordinator()
        c.start('r1', request('BUY'), NOW)  # leaves a pending execution command
        command_id = self.store.load('run').read()['projection']['round_records']['r1']['plan']['intents'][0]['intent_id']
        self.assertEqual(self.store.command('run', command_id, self.epoch, NOW).read()['command_id'], command_id)
        self.assertEqual(self.guard().evaluate(NOW - 1), ['HALT:CLOCK'])
        with self.assertRaises(Conflict):
            self.store.command('run', command_id, self.epoch, NOW)  # signing gate
        self.coordinator(clock=NOW + 1).start('r2', request('BUY', job='j2'), NOW + 1)
        record = self.store.load('run').read()['projection']['round_records'].get('r2')
        self.assertIsNone(record)  # nothing to execute, so the halted round closed at once with its log
        with self.store.transaction() as db:
            logged = db.execute("SELECT count(*) FROM audit_events WHERE run_id='run' AND round_id='r2'").fetchone()[0]
            commands = db.execute("SELECT count(*) FROM commands WHERE run_id='run'").fetchone()[0]
        self.assertEqual((logged, commands), (1, 1))  # one log; only r1's command exists
        self.assertEqual(self.guard().evaluate(NOW + 2), [])  # latched: a later clock does not clear it
        # Ten days on, the undelivered logs add a delivery HALT; the clock HALT stays.
        self.assertEqual(self.guard().evaluate(NOW + 10 * DAY), ['HALT:DELIVERY_DEADLINE'])
        self.assertEqual(sorted(self.projection()['halt']['reasons']), ['CLOCK', 'DELIVERY_DEADLINE'])

    def test_h3_h5_delivery_deadline_halt_clears_when_delivered(self):
        self.coordinator().start('r1', request('HOLD'), NOW)
        late = NOW + 2 * DAY
        self.assertEqual(self.guard().evaluate(late), ['HALT:DELIVERY_DEADLINE'])
        self.assertEqual(self.guard().evaluate(late + 1), [])  # still overdue, still halted
        DeliveryWorker(self.store, FakeReceiver(), retry_ms=1).once('run', self.epoch, late + 2)
        self.assertEqual(self.guard().evaluate(late + 3), ['CLEAR:DELIVERY_DEADLINE'])
        self.assertNotIn('halt', self.projection())

    def test_r1_a_long_receiver_outage_past_the_deadline_still_clears_the_halt(self):
        """IDEA-047 R1: many failed sends, the deadline passes, then the receiver recovers: the HALT clears."""
        self.coordinator().start('r1', request('HOLD'), NOW)
        receiver = FakeReceiver(code=503)
        worker = DeliveryWorker(self.store, receiver, retry_ms=1000, max_backoff_ms=60_000)
        now = NOW
        for _ in range(30):  # far more failures than the old 8-attempt cap
            now += 60_000
            self.assertTrue(worker.once('run', self.epoch, now))
        late = NOW + 2 * DAY
        self.assertEqual(self.guard().evaluate(late), ['HALT:DELIVERY_DEADLINE'])
        receiver.code = 200
        while worker.once('run', self.epoch, late + 1):
            pass
        self.assertEqual(self.guard().evaluate(late + 2), ['CLEAR:DELIVERY_DEADLINE'])
        self.assertNotIn('halt', self.projection())

    def test_h3_h5_v1_repeated_failures_halt_clears_only_when_the_planner_works(self):
        planner = Toggle()
        c = self.coordinator(planner=planner)
        for n in range(3):
            c.start(f'f{n}', request('BUY', job=f'f{n}'), NOW)
        self.assertEqual(self.projection()['round_health'], {'failures': 3, 'successes': 0})
        self.assertEqual(self.guard().evaluate(NOW), ['HALT:REPEATED_FAILURES'])
        for n in range(4):  # halted rounds probe the planner; it still fails, so the HALT holds (IDEA-042 V1)
            c.start(f'h{n}', request('BUY', job=f'h{n}'), NOW)
        self.assertEqual(self.guard().evaluate(NOW), [])
        self.assertEqual(halt_reasons(self.projection()), ['REPEATED_FAILURES'])
        planner.broken = False
        calls = planner.calls
        for n in range(2):  # the repaired planner is probed; its plans are discarded
            c.start(f'p{n}', request('BUY', job=f'p{n}'), NOW)
        self.assertEqual(planner.calls, calls + 2)
        self.assertEqual(self.commands(), 0)  # a probe places nothing
        self.assertEqual(self.guard().evaluate(NOW), ['CLEAR:REPEATED_FAILURES'])
        c.start('after', request('BUY', job='after'), NOW)
        self.assertEqual(self.commands(), 1)
        self.assertEqual(self.kinds().count('HALT'), 1)

    def test_v1_a_round_blocked_by_the_clock_does_not_count(self):
        self.coordinator().start('r1', request('HOLD'), NOW)
        before = self.projection()['round_health']
        self.assertEqual(self.guard().evaluate(NOW - 1), ['HALT:CLOCK'])
        for n in range(3):
            self.coordinator(clock=NOW + 1).start(f'c{n}', request('HOLD', job=f'c{n}'), NOW + 1)
        self.assertEqual(self.projection()['round_health'], before)

    def test_h3_integrity_failure_quarantines(self):
        self.coordinator().start('r1', request('HOLD'), NOW)
        with self.store.transaction() as db:
            db.execute("UPDATE runs SET projection=%s WHERE run_id='run'", (doc(dict(balances={})).payload,))
        self.assertEqual(self.guard().evaluate(NOW), ['QUARANTINED:INTEGRITY'])
        self.assertTrue(self.store.metrics('run').read()['quarantined'])
        driver = Rounds(self.coordinator())
        self.assertEqual(self.service(driver, session='s1').run(max_cycles=1), EXIT_QUARANTINED)
        self.assertEqual(driver.n, 0)  # no round ran on the quarantined run

    def test_service_does_not_start_on_a_quarantined_run(self):
        with self.assertRaises(RuntimeError):
            self.service(Crash(), session='s1').run()  # leaves an unclean session behind
        self.store.quarantine('run')  # e.g. a restore
        self.assertEqual(self.service(Rounds(self.coordinator()), session='s2').run(max_cycles=1), EXIT_QUARANTINED)
        self.assertEqual(self.incidents(), [])

    def test_service_stops_when_quarantined(self):
        class Tamper:
            def once(inner, now_ms):
                with self.store.transaction() as db:
                    db.execute("UPDATE runs SET projection=%s WHERE run_id='run'", (doc(dict(x=1)).payload,))
        self.assertEqual(self.service(Tamper(), session='s1').run(max_cycles=3), EXIT_QUARANTINED)

    def test_v4_a_session_refusal_is_a_start_refusal_and_a_crash_is_not(self):
        self.service(Rounds(self.coordinator()), session='s1').run(max_cycles=1)
        with self.assertRaises(StartRefused):  # another build: restarting cannot cure it (exit 4)
            self.service(Rounds(self.coordinator()), build='build-2', session='s2').run(max_cycles=1)
        with self.assertRaises(RuntimeError) as crash:  # a failure inside a round still restarts (exit 1)
            self.service(Crash(), session='s3').run()
        self.assertNotIsInstance(crash.exception, StartRefused)

    # ---------------------------------------------------------------- H6
    def test_h6_supervision_events_replay(self):
        with self.assertRaises(RuntimeError):
            self.service(Crash(), session='s1').run()
        self.service(Rounds(self.coordinator()), session='s2').run(max_cycles=1)
        self.coordinator().start('late', request('HOLD', job='late'), NOW)
        self.guard().evaluate(NOW + 2 * DAY)
        DeliveryWorker(self.store, FakeReceiver(), retry_ms=1).once('run', self.epoch, NOW + 2 * DAY)
        DeliveryWorker(self.store, FakeReceiver(), retry_ms=1).once('run', self.epoch, NOW + 2 * DAY)
        self.guard().evaluate(NOW + 2 * DAY + 1)
        self.assertTrue({'INCIDENT', 'HALT', 'HALT_CLEARED'} <= set(self.kinds()))
        expected, journal = self.store.verify('run'), self.store.journal('run')
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        head = replay(journal, doc(dict(balances=dict(USDT=100, BNB=10, NVDAB=0))), self.store, run_id='run',
                      wallet_id='wallet', chain_id=56, version_id='synthetic', profile_hash='a' * 64,
                      address='0x' + '1' * 40, policy=FakePolicy(), planner=FakePlanner(), execution=FakeExecution(),
                      reducer=settle)
        self.assertEqual(head, expected)


class SupervisorUnit(unittest.TestCase):
    """H2: the unit restarts the same verified build, always, with no manual step."""

    def directives(self, name):
        lines = (ROOT / 'deploy/systemd' / name).read_text(encoding='utf-8').splitlines()
        return [line.strip() for line in lines if '=' in line and not line.lstrip().startswith('#')]

    def test_h2_runtime_unit(self):
        d = self.directives('larp-runtime.service')
        for required in ('Restart=always', 'RestartSec=10', 'StartLimitIntervalSec=0', 'KillMode=control-group',
                         'RestartPreventExitStatus=2 3 4', 'User=larp-runtime'):
            self.assertIn(required, d)
        self.assertTrue(any(x.startswith('ExecStart=') and 'larp.runtime.launch --manifest' in x for x in d))
        self.assertTrue(any(x.startswith('ExecStart=') and 'larp.runtime.service run' in x for x in d))
        hardening = [x for x in self.directives('larp-archive.service') if x.split('=')[0] in (
            'NoNewPrivileges', 'ProtectSystem', 'ProtectHome', 'PrivateTmp', 'PrivateDevices', 'ProtectKernelTunables',
            'ProtectKernelModules', 'ProtectControlGroups', 'RestrictSUIDSGID', 'LockPersonality',
            'RestrictAddressFamilies', 'CapabilityBoundingSet', 'UMask')]
        self.assertTrue(hardening)
        for line in hardening:
            self.assertIn(line, d)

    def test_v4_unfixable_start_errors_exit_4(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as out:
            config = Path(directory) / 'runtime.json'
            config.write_text('{"schema": "RuntimeService.v1"}', encoding='utf-8')  # settings missing
            args = ['--config', str(config), '--manifest', str(Path(directory) / 'missing.json'), '--root', directory]
            self.assertEqual(main(['check'] + args), EXIT_REFUSED)
            self.assertEqual(main(['run'] + args), EXIT_REFUSED)
        self.assertIn('START_REFUSED', out.getvalue())
