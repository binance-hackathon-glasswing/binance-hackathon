"""PR #3 second-review cleanup criteria (IDEA-028 RT18 #6-#10)."""

import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

from larp.audit.delivery import DeliveryWorker
from larp.audit.protocol import DAY_MS,UPLOAD_GRACE_MS,breach_cutoff_ms
from larp.contracts import ContractError,Document
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor,FakePolicy,FakePlanner,FakeExecution
from larp.runtime.preflight import release_files,tracked_release_files
from larp.storage import backup
from larp.storage.postgres import IntegrityError
from tests.audit.test_protocol import event
from tests.support import DatabaseCase,request

NOW=1791590400000


class DeadlineRule(unittest.TestCase):
    """#6: the SQL cutoff is the old per-event formula."""

    def test_cutoff_matches_next_midnight_plus_grace(self):
        stamps=[NOW+k*DAY_MS//4+d for k in range(-8,8) for d in (-1,0,1)]
        nows=[s+o for s in stamps for o in (0,UPLOAD_GRACE_MS-1,UPLOAD_GRACE_MS,DAY_MS,DAY_MS+UPLOAD_GRACE_MS)]
        for ts in stamps:
            for now in nows:
                old=now>=(ts//DAY_MS+1)*DAY_MS+UPLOAD_GRACE_MS
                self.assertEqual(old,ts<breach_cutoff_ms(now),(ts,now))


class ReleaseFiles(unittest.TestCase):
    """#10: host-local and untracked files never enter the manifest."""

    def tree(self,directory):
        root=Path(directory)
        for name in ('larp/runtime/operations.py','config/x/deployment.local.json',
                     'deploy/aws/.terraform/m/main.tf','deploy/aws/main.tf','larp/extra.py'):
            path=root/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('# fixture\n',encoding='utf-8')
        return root

    def test_host_local_files_are_not_release_files(self):
        with tempfile.TemporaryDirectory() as directory:
            files=release_files(self.tree(directory))
        self.assertEqual({'larp/runtime/operations.py','deploy/aws/main.tf','larp/extra.py'},files)

    def test_ignored_release_file_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.tree(directory)
            (root/'.gitignore').write_text('larp/extra.py\n',encoding='utf-8')
            def git(*args):
                return subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,
                                      timeout=30,check=True).stdout.strip()
            git('init','-q'); git('add','.')
            with self.assertRaises(ContractError): tracked_release_files(root,git)
            (root/'.gitignore').unlink(); git('add','.')
            self.assertIn('larp/extra.py',tracked_release_files(root,git))

    def test_dead_anchor_path_is_removed(self):  # #9
        self.assertFalse(hasattr(backup,'anchor'))
        self.assertNotIn('anchors',backup.TABLES)


class Cleanups(DatabaseCase):
    def test_audit_timestamp_column_is_verified(self):  # #6
        self.store.commit(self.batch('first',audit=[event()]))
        worker=DeliveryWorker(self.store,None)
        self.assertEqual([],worker.deadline_breaches('run',NOW+DAY_MS+UPLOAD_GRACE_MS-1))
        self.assertEqual(['evt'],worker.deadline_breaches('run',NOW+DAY_MS+UPLOAD_GRACE_MS))
        with self.store.transaction() as db:
            db.execute('UPDATE audit_events SET timestamp_ms=timestamp_ms+%s',(DAY_MS,))
        with self.assertRaises(IntegrityError): self.store.verify('run')

    def test_reads_do_not_wait_for_the_run_row_lock(self):  # #7
        import psycopg
        with psycopg.connect(self.store._dsn) as other:
            other.execute("SELECT run_id FROM runs WHERE run_id='run' FOR UPDATE")
            results={}
            def read():
                results['load']=self.store.load('run').read()['version']
                results['metrics']=self.store.metrics('run').read()['version']
            reader=threading.Thread(target=read); reader.start(); reader.join(3)
            self.assertFalse(reader.is_alive())
        self.assertEqual(dict(load=0,metrics=0),results)

    def test_request_and_assessment_are_stored_once(self):  # #8
        Coordinator(self.store,FakeAssessor(),FakePolicy(),FakePlanner(),execution=FakeExecution(),
            run_id='run',version_id='synthetic',profile_hash='a'*64,address='0x'+'1'*40).start('r',request(),NOW)
        with self.store.transaction() as db:
            audit=Document(bytes(db.execute('SELECT document FROM audit_events').fetchone()[0])).read()
        data=json.loads(audit['log'])['data']['input']
        self.assertEqual(request().read(),data['request'])
        self.assertIsNotNone(data['assessment'])
        self.assertEqual({'projection','reservations','includes'},set(data['policy_input']))
        self.assertEqual(['request','assessment'],data['policy_input']['includes'])
        record=self.store.event('run','plan:r')['record']
        self.assertNotIn('request',record['policy_input'])

    def test_anchors_table_is_dropped_and_backups_round_trip(self):  # #9
        with self.store.transaction() as db:
            self.assertIsNone(db.execute("SELECT to_regclass('anchors')").fetchone()[0])
        self.store.commit(self.batch('first',audit=[event()]))
        exported=backup.export(self.store)
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        backup.restore(self.store,exported)
        self.store.verify('run')
