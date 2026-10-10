import os
from pathlib import Path
import subprocess
import sys
import tempfile

from larp.audit.delivery import DeliveryWorker
from larp.contracts import Document
from larp.runtime.fixtures import FakeReceiver
from tests.audit.test_protocol import event
from tests.support import DatabaseCase


class ProcessCrashes(DatabaseCase):
    def kill_at(self,phase,*args):
        env={k:v for k,v in os.environ.items() if k in ('PATH','SYSTEMROOT','WINDIR','LD_LIBRARY_PATH')}
        env['LARP_TEST_DATABASE_URL']=self.store._dsn
        result=subprocess.run([sys.executable,'-m','tests.storage.crash_worker',phase,*args],
                              env=env,timeout=15,capture_output=True)
        self.assertEqual(73,result.returncode,result.stderr.decode())

    def test_process_death_before_commit_rolls_back_all_rows(self):
        self.kill_at('before_commit')
        self.assertEqual(0,self.store.load('run').read()['version'])
        self.assertEqual([],self.store.load('run').read()['reservations'])
        self.assertEqual(0,self.store.metrics('run').read()['audit_pending'])

    def test_process_death_after_commit_preserves_every_row(self):
        self.kill_at('after_commit')
        self.assertEqual(1,self.store.load('run').read()['version'])
        self.assertEqual(10,self.store.load('run').read()['reservations'][0]['units'])
        self.assertEqual(1,self.store.metrics('run').read()['audit_pending'])
        self.store.verify('run')

    def test_process_death_after_receiver_write_resends_identical_bytes(self):
        self.store.commit(self.batch(audit=[event()]))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receiver.json'
            self.kill_at('after_send',str(path))
            sent=Document(path.read_bytes()).read()
        receiver=FakeReceiver()
        receiver.stored[(sent['event_id'],sent['chunk_index'])]=sent['body']
        DeliveryWorker(self.store,receiver,retry_ms=1).once('run',self.epoch,102)
        self.assertEqual(1,len(receiver.stored))
        self.assertEqual(0,self.store.metrics('run').read()['audit_pending'])
