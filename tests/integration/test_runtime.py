import json

from larp.audit.delivery import DeliveryWorker
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor,FakePolicy,FakePlanner,FakeReceiver,FakeExecution,settle
from larp.storage.postgres import doc,Conflict
from larp.storage.backup import export,restore
from larp.runtime.replay import replay
from tests.support import DatabaseCase,request


class IntegratedRuntime(DatabaseCase):
    def coordinator(self,assessor=None,policy=None):
        self.planner=FakePlanner()
        return Coordinator(self.store,assessor or FakeAssessor(),policy or FakePolicy(),self.planner,
                           execution=FakeExecution(),run_id='run',version_id='synthetic',profile_hash='a'*64,address='0x'+'1'*40)

    def test_restartable_round_settlement_audit_backup_and_exact_replay(self):
        coordinator=self.coordinator(); now=1791590400000
        coordinator.start('r',request('BUY'),now)
        value=self.store.load('run').read()
        self.assertEqual(100,value['projection']['balances']['USDT'])
        self.assertEqual(2,len(value['reservations']))
        tx='0x'+'b'*64
        broadcast=doc(dict(kind='BROADCAST_ATTEMPTED',observation_id='broadcast',round_id='r',tx_hash=tx,simulated=True))
        coordinator.observe('broadcast',broadcast,settle)
        # Crash after durable possibly-sent hash; restart closes truthfully.
        coordinator=self.coordinator()
        coordinator.recover(now+1)
        receiver=FakeReceiver(lose_ack=True)
        uploader=DeliveryWorker(self.store,receiver,retry_ms=1)
        uploader.once('run',self.epoch,now+2)
        uploader.once('run',self.epoch,now+3)
        self.assertEqual(1,len(receiver.stored))
        audit_before=list(receiver.stored.values())[0]
        final=doc(dict(kind='FINAL_SUCCESS',observation_id='settled',round_id='r',tx_hash=tx,simulated=True))
        coordinator.observe('settled',final,settle)
        # A repeated identical receipt after restart is idempotent at the port too.
        coordinator.observe('settled',final,settle)
        value=self.store.load('run').read()
        self.assertEqual(dict(USDT=90,BNB=9,NVDAB=2),value['projection']['balances'])
        self.assertTrue(all(r['units']==0 for r in value['reservations']))
        self.assertEqual(audit_before,list(receiver.stored.values())[0])
        log=json.loads(json.loads(audit_before)['payload'])
        self.assertEqual(tx,log['data']['orders'][0]['tx_hash'])
        self.assertEqual('INTERRUPTED_UNRESOLVED',log['data']['output']['status'])
        expected_head=self.store.verify('run')
        journal=self.store.journal('run')
        backup=export(self.store)
        # Re-run deterministic policy/planning/execution/accounting with captured
        # assessment output. Do not simply reinsert the saved projections.
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        replay(journal,doc(dict(balances=dict(USDT=100,BNB=10,NVDAB=0))),self.store,
               run_id='run',wallet_id='wallet',chain_id=56,version_id='synthetic',profile_hash='a'*64,
               address='0x'+'1'*40,policy=FakePolicy(),planner=FakePlanner(),execution=FakeExecution(),reducer=settle)
        self.assertEqual(expected_head,self.store.verify('run'))
        self.assertEqual(value['projection'],self.store.load('run').read()['projection'])
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        restore(self.store,backup)
        self.assertEqual(expected_head,self.store.verify('run'))
        self.assertEqual(0,self.store.metrics('run').read()['audit_pending'])
        self.assertTrue(self.store.load('run').read()['quarantined'])

    def test_hold_and_failed_assessment_each_log_once_and_risk_runs(self):
        class Failed:
            def assess(self,request): raise RuntimeError('synthetic')
        coordinator=self.coordinator(Failed())
        now=1791590400000
        coordinator.start('failed',request(),now)
        self.assertEqual(1,self.planner.calls)
        coordinator.close('failed',now+100,'different late call')
        with self.store.transaction() as db:
            self.assertEqual(1,db.execute('SELECT count(*) FROM audit_events').fetchone()[0])
        coordinator=self.coordinator()
        coordinator.start('hold',request(job='hold'),now)
        self.assertEqual(2,self.store.metrics('run').read()['audit_pending'])

    def test_crash_before_plan_has_truthful_round(self):
        self.store.open_round('run','crash',request(),self.epoch)
        coordinator=self.coordinator()
        coordinator.recover(1791590400000)
        self.assertEqual([],self.store.open_rounds('run'))
        with self.store.transaction() as db:
            raw=db.execute('SELECT document FROM audit_events').fetchone()[0]
        from larp.contracts import Document
        log=json.loads(Document(bytes(raw)).read()['log'])
        self.assertEqual([],log['data']['orders'])
        self.assertIn('PROCESS_INTERRUPTED',log['data']['output']['errors'])

    def test_stale_completion_cannot_overwrite_current_projection(self):
        old=self.batch('old')
        self.store.commit(self.batch('new'))
        with self.assertRaises(Conflict): self.store.commit(old)

    def test_reservation_rejection_is_logged_without_mutation(self):
        self.store.commit(self.batch(reservation_deltas=[dict(intent_id='other',asset='USDT',units=100)]))
        coordinator=self.coordinator()
        coordinator.start('blocked',request('BUY'),1791590400000)
        self.assertEqual(0,self.store.metrics('run').read()['open_rounds'])
        self.assertEqual(1,self.store.metrics('run').read()['audit_pending'])
        self.assertEqual(100,self.store.load('run').read()['projection']['balances']['USDT'])
