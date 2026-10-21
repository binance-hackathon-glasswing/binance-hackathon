"""LD21-H RG8 harness: a recorded run replays read-only into an isolated target with dead live ports (PostgreSQL)."""
import importlib.util
import json
from pathlib import Path
import uuid

from larp.integration.runtime import RuntimePlanner
from larp.intelligence.config import load_registry
from larp.storage.postgres import PostgresStore
from tests.integration import test_evidence_pipeline as pipeline
from tests.integration import test_live_replay as live_replay

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('drill_replay_day', ROOT / 'tools/deploy/drill_replay_day.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
RUN = pipeline.RUN
CALENDAR = ROOT / 'config/runtime/session-calendar.2026.json'


class ReplayHarness(pipeline.PipelineHarness):
    live = live_replay.LiveReplay.live
    settle_reduction = live_replay.LiveReplay.settle_reduction

    def target(self):
        import psycopg
        from psycopg.conninfo import make_conninfo
        schema = 'larp_test_' + uuid.uuid4().hex
        with psycopg.connect(self.admin) as db:
            db.execute('CREATE SCHEMA ' + schema)

        def drop():
            with psycopg.connect(self.admin) as db:
                db.execute('DROP SCHEMA ' + schema + ' CASCADE')
        self.addCleanup(drop)
        store = PostgresStore(make_conninfo(self.admin, options='-c search_path=' + schema))
        store.migrate()
        return store

    def recorded_day(self):
        c = self.live()
        self.round(c, 'r1', 'EXSEMI_Q2_8K')
        self.round(c, 'r2', 'EXSEMI_402_8K')
        self.settle_reduction(c, 'r2')
        self.round(c, 'r3', 'OCCURRED_8K')
        builder = c.context_builder
        builder.market = builder.calendar = builder.health = builder.series = harness.dead
        return builder

    def replay(self, builder, target, **options):
        return harness.replay_run(harness.read_only(self.store), target, run_id=RUN, builder=builder,
                                  planner=RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                                  profile=self.profile, profile_hash=self.h, version_id='integration-fixture',
                                  address='0x' + '1' * 40, test_rounds=False, require_version=False, **options)

    def test_recorded_day_replays_to_the_same_head_with_dead_ports(self):
        builder = self.recorded_day()
        expected = self.store.verify(RUN)
        report, code = self.replay(builder, self.target())
        self.assertEqual((code, report['status']), (0, 'PASS'))
        self.assertEqual(report['replayed_head'], expected)
        self.assertEqual(report['batches'], self.store.load(RUN).read()['version'])

    def test_a_prefix_replays_to_the_head_at_that_sequence(self):
        builder = self.recorded_day()
        report, code = self.replay(builder, self.target(), through_sequence=2)
        self.assertEqual((code, report['status'], report['batches']), (0, 'PASS', 2))
        with self.store.transaction() as db:
            self.assertEqual(report['replayed_head'],
                             db.execute("SELECT head FROM events WHERE run_id=%s AND sequence=2", (RUN,)).fetchone()[0])

    def test_a_live_port_call_or_a_non_empty_target_fails(self):
        builder = self.recorded_day()
        target = self.target()
        builder.market = harness.dead  # still dead; replace the recorded market with a port that must not be reached
        original = live_replay.RecordedPorts.builder_for

        def leaky(ports, record):
            recorded = original(ports, record)
            getattr(recorded, 'builder', recorded).market = harness.dead  # RecordedMode wraps the copied builder
            return recorded
        live_replay.RecordedPorts.builder_for = leaky
        try:
            report, code = self.replay(builder, target)
        finally:
            live_replay.RecordedPorts.builder_for = original
        self.assertEqual((code, report['status'], report['reason']), (1, 'FAIL', 'LIVE_PORT_CALLED'))
        report, code = self.replay(builder, target)  # the failed attempt left a run behind: refuse, never overwrite
        self.assertEqual((code, report['reason']), (2, 'TARGET_NOT_EMPTY'))

    def test_same_database_target_is_refused(self):
        config = dict(database_host='db.example', database_name='larp_trial2')
        self.assertTrue(harness.same_database(config, 'host=db.example dbname=larp_trial2 user=x'))
        self.assertFalse(harness.same_database(config, 'host=db.example dbname=larp_drill user=x'))


class BuilderFromConfig(pipeline.unittest.TestCase):
    def test_builder_matches_the_pinned_config_and_has_no_live_ports(self):
        import hashlib
        import tempfile
        entry = load_registry().entries[0]
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / 'profile.json'
            profile.write_text(json.dumps(dict(schema='StrategyProfile.v1', mode='LIVE', proposal_seconds=15)))
            config = dict(run_id=RUN, mode='offline', driver=dict(
                strategy_profile_file=str(profile), strategy_profile_sha256=hashlib.sha256(profile.read_bytes()).hexdigest(),
                session_calendar_file=str(CALENDAR), session_calendar_sha256=hashlib.sha256(CALENDAR.read_bytes()).hexdigest(),
                intelligence_mode='shadow', issuers={entry.issuer_id: dict(token=entry.token, underlying_id='U')}))
            builder, planner, loaded, profile_hash = harness.builder_from_config(config)
            self.assertEqual(loaded['proposal_seconds'], 15)
            self.assertEqual(builder.profile_hash, profile_hash)
            self.assertEqual(builder.issuers, {entry.issuer_id: dict(token=entry.token, underlying_id='U')})
            for port in (builder.market, builder.health):
                with self.assertRaises(harness.LivePortCalled):
                    port(0)
            config['driver']['session_calendar_sha256'] = '0' * 64
            with self.assertRaises(Exception):
                harness.builder_from_config(config)
