"""IDEA-047 R5: service-level signals for CloudWatch, read with the larp_archive grants only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from larp.contracts import Document
from larp.runtime.maintenance import HOUR_MS, RUNTIME_HEARTBEAT_MS, SIGNER_ANSWER_S, Maintenance
from larp.runtime.operations import main, publish_health
from larp.runtime.supervision import Guard
from larp.storage.postgres import Unavailable
from tests.runtime.test_anchors_roles import ROOT, RoleStore
from tests.support import DatabaseCase

NOW = 1791590400000  # 2026-10-10 00:00 UTC
NOW_S = NOW // 1000


class ServiceHealth(DatabaseCase):
    def setUp(self):
        super().setUp()
        import psycopg
        script = (ROOT / 'deploy/postgres/roles.sql').read_text()
        with psycopg.connect(self.store._dsn) as db:
            if not db.execute("SELECT 1 FROM pg_roles WHERE rolname='rds_iam'").fetchone():
                db.execute('CREATE ROLE rds_iam')
            database = db.execute('SELECT current_database()').fetchone()[0]
            db.execute(script.replace('ON DATABASE larp ', 'ON DATABASE ' + database + ' ')
                       .replace('SCHEMA public ', 'SCHEMA ' + self.schema + ' '))
        # The health check runs as the archive role, exactly as larp-archive.service does.
        self.health = Maintenance(RoleStore(self.store._dsn, 'larp_archive'), archive=None,
                                  backup_interval_ms=24 * HOUR_MS).service_health

    def sql(self, statement, *args):
        with self.store.transaction() as db:
            db.execute(statement, args)

    def session(self, name, heartbeat_ms, ended_ms=None):
        self.sql('INSERT INTO process_sessions(run_id,session_id,build_id,started_ms,heartbeat_ms,ended_ms) '
                 'VALUES(%s,%s,%s,%s,%s,%s)', 'run', name, 'b' * 40, heartbeat_ms, heartbeat_ms, ended_ms)

    def signing_request(self, name, requested_s):
        self.sql('INSERT INTO signing_attempts VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                 'attempt-' + name, 'run', 'key-' + name, 'p' * 64)
        self.sql('INSERT INTO signing_requests VALUES(%s,%s,%s,%s,%s,%s)',
                 'request-' + name, 'run', 'attempt-' + name, 'p' * 64, b'{}', requested_s)

    def test_r5_fresh_run_reports_no_runtime_and_nothing_else(self):
        h = self.health('run', NOW).read()
        self.assertEqual((h['runtime_heartbeat_age_ms'], h['runtime_alive']), (None, False))
        self.assertEqual((h['halt_reasons'], h['quarantined'], h['audit_overdue'], h['signing_unanswered']),
                         ([], False, 0, 0))

    def test_r5_runtime_heartbeat_is_fresh_or_stale(self):
        self.session('ended', NOW, ended_ms=NOW)  # a cleanly stopped session is not a running runtime
        self.assertFalse(self.health('run', NOW).read()['runtime_alive'])
        self.session('current', NOW - RUNTIME_HEARTBEAT_MS)
        h = self.health('run', NOW).read()
        self.assertEqual((h['runtime_heartbeat_age_ms'], h['runtime_alive']), (RUNTIME_HEARTBEAT_MS, True))
        h = self.health('run', NOW + 1).read()
        self.assertEqual((h['runtime_heartbeat_age_ms'], h['runtime_alive']), (RUNTIME_HEARTBEAT_MS + 1, False))

    def test_r5_halt_and_quarantine_are_reported(self):
        guard = Guard(self.store, 'run', max_failures=3, clear_after=3)
        guard._halt('REPEATED_FAILURES', NOW, dict(consecutive_failures=3))
        guard._halt('CLOCK', NOW, dict(last_decision_ms=NOW + 1))
        self.assertEqual(self.health('run', NOW).read()['halt_reasons'], ['CLOCK', 'REPEATED_FAILURES'])
        self.store.quarantine('run')
        self.assertTrue(self.health('run', NOW).read()['quarantined'])

    def test_r5_overdue_audit_logs_are_counted(self):
        self.sql("INSERT INTO audit_events VALUES('run','late','round-1','{}'::bytea,%s)", NOW - 3 * 24 * HOUR_MS)
        self.sql("INSERT INTO audit_chunks(run_id,event_id,chunk_index,body) VALUES('run','late',0,'x'::bytea)")
        self.sql("INSERT INTO audit_events VALUES('run','recent','round-2','{}'::bytea,%s)", NOW)
        self.sql("INSERT INTO audit_chunks(run_id,event_id,chunk_index,body) VALUES('run','recent',0,'x'::bytea)")
        self.assertEqual(self.health('run', NOW).read()['audit_overdue'], 1)
        self.sql("UPDATE audit_chunks SET status='ACK',acknowledgement='a'::bytea WHERE event_id='late'")
        self.assertEqual(self.health('run', NOW).read()['audit_overdue'], 0)

    def test_r5_only_old_unanswered_signing_requests_count(self):
        old = NOW_S - SIGNER_ANSWER_S - 1
        for name in ('unanswered', 'signed', 'refused', 'other-payload'):
            self.signing_request(name, old)
        self.signing_request('fresh', NOW_S - SIGNER_ANSWER_S)
        self.sql("INSERT INTO execution_signatures VALUES('attempt-signed','run',%s,'\\x00','g')", 'p' * 64)
        self.sql("INSERT INTO signing_refusals VALUES('request-refused','run','synthetic refusal',%s)", NOW_S)
        # A signature for another payload of the attempt does not answer this request.
        self.sql("INSERT INTO execution_signatures VALUES('attempt-other-payload','run',%s,'\\x00','g')", 'q' * 64)
        h = self.health('run', NOW).read()
        self.assertEqual((h['signing_unanswered'], h['signing_oldest_unanswered_s']), (2, SIGNER_ANSWER_S + 1))


class Publishing(unittest.TestCase):
    SERVICES = dict(runtime_alive=True, halt_reasons=['CLOCK'], quarantined=False, audit_overdue=2,
                    signing_unanswered=0)

    def sent(self, client):
        (kwargs,) = [c.kwargs for c in client.put_metric_data.call_args_list]
        self.assertEqual(kwargs['Namespace'], 'LARP/Runtime')
        metrics = {}
        for m in kwargs['MetricData']:
            self.assertEqual([d['Name'] for d in m['Dimensions']], ['Deployment', 'Service'])
            self.assertEqual(m['Dimensions'][0]['Value'], 'larp-dev')
            metrics[(m['Dimensions'][1]['Value'], m['MetricName'])] = m['Value']
        self.assertEqual(len(metrics), len(kwargs['MetricData']))
        return metrics

    def test_r5_every_signal_is_published_with_its_dimensions(self):
        client = MagicMock()
        publish_health(client, 'larp-dev', True, self.SERVICES)
        self.assertEqual(self.sent(client), {
            ('archive', 'Heartbeat'): 1, ('archive', 'Healthy'): 1, ('runtime', 'Heartbeat'): 1,
            ('runtime', 'Halted'): 1, ('runtime', 'Quarantined'): 0, ('runtime', 'GasPairUnaffordable'): 0,
            ('uploader', 'OverdueLogs'): 2,
            ('signer', 'UnansweredRequests'): 0})

    def test_r5_a_database_failure_reports_the_runtime_down(self):
        worker = MagicMock()
        worker.health.side_effect = Unavailable('synthetic outage')
        c = dict(run_id='run', deployment='larp-dev', archive_bucket='fixture', account_id='123456789012',
                 kms_key='synthetic', archive_prefix='archive/dev', retention_days=82, max_archive_bytes=1,
                 backup_interval_hours=24, max_attempts=2, retry_seconds=60)
        clients = {key: MagicMock() for key in ('s3', 'rds', 'cloudwatch')}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text('{}')
            with patch('larp.runtime.operations.validate_config', return_value=c), \
                    patch('larp.runtime.operations.cloud_clients', return_value=clients), \
                    patch('larp.runtime.operations.S3Archive'), \
                    patch('larp.runtime.operations.Maintenance', return_value=worker), \
                    patch('builtins.print') as output:
                self.assertEqual(main(['health', '--config', str(path)]), 1)
        self.assertEqual(json.loads(output.call_args.args[0])['reason'], 'OPERATIONS_FAILED')
        self.assertEqual(self.sent(clients['cloudwatch']),
                         {('archive', 'Heartbeat'): 1, ('archive', 'Healthy'): 0, ('runtime', 'Heartbeat'): 0})

    def test_r5_health_output_includes_the_services(self):
        worker = MagicMock()
        worker.health.return_value = Document.from_dict(dict(healthy=True, reasons=[]))
        worker.service_health.return_value = Document.from_dict(dict(self.SERVICES, schema='ServiceHealth.v1'))
        c = dict(run_id='run', deployment='larp-dev', archive_bucket='fixture', account_id='123456789012',
                 kms_key='synthetic', archive_prefix='archive/dev', retention_days=82, max_archive_bytes=1,
                 backup_interval_hours=24, max_attempts=2, retry_seconds=60)
        clients = {key: MagicMock() for key in ('s3', 'rds', 'cloudwatch')}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text('{}')
            with patch('larp.runtime.operations.validate_config', return_value=c), \
                    patch('larp.runtime.operations.cloud_clients', return_value=clients), \
                    patch('larp.runtime.operations.S3Archive'), \
                    patch('larp.runtime.operations.Maintenance', return_value=worker), \
                    patch('builtins.print') as output:
                self.assertEqual(main(['health', '--config', str(path)]), 0)
        self.assertEqual(json.loads(output.call_args.args[0])['services']['audit_overdue'], 2)
        self.assertEqual(self.sent(clients['cloudwatch'])[('uploader', 'OverdueLogs')], 2)


if __name__ == '__main__':
    unittest.main()
