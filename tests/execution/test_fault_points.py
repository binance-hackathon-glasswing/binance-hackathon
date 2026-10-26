"""IDEA-042 RG2-H01 H5: armed fault points kill a real child process (SIGKILL); a restarted executor recovers.
Disposable PostgreSQL, fake venue and registry signer; no keys, network or host."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile

from larp.execution import Executor
from larp.execution_live.store import ExecutionStore
from larp.runtime import faults
from tests.execution import test_postgres_execution as base
from tests.execution_fixtures import FakeDecoder, FakeVenue, WALLET, finalized, intent
from tests.support import DatabaseCase

ROOT = Path(__file__).resolve().parents[2]


class FaultPointCrashes(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.execution_store = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.execution_store.install_test_schema()
        self.guards = base.ExecutionGuards(self.execution_store)
        self.venue = FakeVenue(self.execution_store)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.restart()

    def restart(self):
        adapter = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.executor = Executor(adapter, self.guards, self.venue, base.RegistrySigner(adapter), FakeDecoder())

    def prepared(self):
        i = intent()
        self.executor.create(i, 10)
        self.executor.prepare(i.key, 11)
        self.executor.authorize(i.key, 12)
        return i.key

    def crash(self, point, step, key, now):
        token = Path(self.tmp.name) / (point + '.token')
        token.write_text('armed')
        env = {'LARP_TEST_DATABASE_URL': self.store._dsn, 'PATH': os.environ.get('PATH', ''),
               faults.POINT_ENV: point, faults.TOKEN_ENV: str(token)}
        result = subprocess.run([sys.executable, '-m', 'tests.execution.fault_worker', step, key, str(now)],
                                env=env, cwd=ROOT, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr.decode()[-800:])
        self.assertFalse(token.exists())  # consumed: a restart cannot fire it again
        self.restart()
        return self.execution_store.load(key).attempts[-1]

    def signature_rows(self):
        with self.store.transaction() as db:
            return db.execute('SELECT attempt_id, count(*) FROM execution_signatures GROUP BY 1').fetchall()

    def test_f5_signature_written_then_recovered_with_the_same_bytes(self):
        key = self.prepared()
        attempt = self.crash('F5', 'sign', key, 13)
        self.assertEqual(attempt.state, 'AUTHORIZED')  # SIGNED_DURABLE was never committed
        self.assertEqual([n for _, n in self.signature_rows()], [1])
        stored = self.executor.signer.lookup(attempt.attempt_id, attempt.payload.hash)
        recovered = self.executor.recover_signature(key, 14).attempts[-1]
        self.assertEqual((recovered.state, recovered.tx_hash), ('SIGNED_DURABLE', stored.tx_hash))
        self.assertEqual([n for _, n in self.signature_rows()], [1])

    def test_f7a_possible_send_is_never_blindly_resent(self):
        key = self.prepared()
        self.executor.sign(key, 13)
        attempt = self.crash('F7a', 'broadcast', key, 14)
        self.assertEqual((attempt.state, attempt.broadcast_at), ('BROADCAST_ATTEMPTED', 14))
        again = self.executor.broadcast(key, 15).attempts[-1]
        self.assertEqual(again.state, 'BROADCAST_ATTEMPTED')
        self.assertEqual(self.venue.broadcasts, [])
        self.assertEqual([n for _, n in self.signature_rows()], [1])

    def test_f7b_sent_bytes_reconcile_to_final_without_a_resend(self):
        key = self.prepared()
        self.executor.sign(key, 13)
        attempt = self.crash('F7b', 'broadcast', key, 14)
        self.assertEqual(attempt.state, 'BROADCAST_ATTEMPTED')  # the PENDING phase commit was lost
        self.executor.broadcast(key, 15)
        self.assertEqual(self.venue.broadcasts, [])
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt)
        final = self.executor.reconcile(key, 16).attempts[-1]
        self.assertEqual(final.state, 'FINAL_SUCCESS')
        self.assertEqual(self.venue.broadcasts, [])
        self.assertEqual([n for _, n in self.signature_rows()], [1])

    def test_f8_receipt_read_then_final_exactly_once(self):
        key = self.prepared()
        self.executor.sign(key, 13)
        sent = self.executor.broadcast(key, 14).attempts[-1]
        attempt = self.crash('F8', 'reconcile', key, 15)
        self.assertEqual(attempt.state, sent.state)  # the receipt was read, the FINAL phase never committed
        self.assertEqual(attempt.probes, sent.probes + 1)  # the probe itself was durable
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt)
        final = self.executor.reconcile(key, attempt.next_probe).attempts[-1]
        self.assertEqual(final.state, 'FINAL_SUCCESS')
        again = self.executor.reconcile(key, attempt.next_probe + 100).attempts[-1]
        self.assertEqual((again.state, again.finalized_at), ('FINAL_SUCCESS', final.finalized_at))
        self.assertEqual(len(self.venue.broadcasts), 1)
        self.assertEqual([n for _, n in self.signature_rows()], [1])
