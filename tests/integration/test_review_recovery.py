"""PR #3 regression criteria: no re-planning, premature sealing or replay drift."""

import json
from unittest.mock import patch

from larp.contracts import Document
from larp.runtime.fixtures import FakeAssessor,FakePolicy,FakePlanner,FakeExecution,settle
from larp.runtime.coordinator import Coordinator
from larp.runtime.replay import replay
from larp.storage.postgres import Conflict,doc
from tests.support import DatabaseCase,request

NOW=1791590400000


class ReviewRecovery(DatabaseCase):
    def runtime(self):
        self.planner=FakePlanner()
        return Coordinator(self.store,FakeAssessor(),FakePolicy(),self.planner,execution=FakeExecution(),
            run_id='run',version_id='synthetic',profile_hash='a'*64,address='0x'+'1'*40)

    def assert_replay(self):
        journal=self.store.journal('run')
        expected=self.store.verify('run')
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        replay(journal,doc(dict(balances=dict(USDT=100,BNB=10,NVDAB=0))),self.store,
            run_id='run',wallet_id='wallet',chain_id=56,version_id='synthetic',profile_hash='a'*64,
            address='0x'+'1'*40,policy=FakePolicy(),planner=FakePlanner(),execution=FakeExecution(),reducer=settle)
        self.assertEqual(expected,self.store.verify('run'))

    def test_restart_after_durable_rejection_never_replans_and_replays(self):
        runtime=self.runtime()
        commit=self.store.commit
        def conflict_once(batch):
            if batch.read()['event_id']=='plan:r':
                raise Conflict('Synthetic transient version race')
            return commit(batch)
        with patch.object(self.store,'commit',side_effect=conflict_once), \
                patch.object(runtime,'close',side_effect=RuntimeError('Crash after rejection')):
            with self.assertRaises(RuntimeError): runtime.start('r',request('BUY'),NOW)
        self.assertIsNotNone(self.store.receipt('run','rejected:r'))
        restarted=self.runtime()
        restarted.start('r',request('BUY'),NOW+10)
        self.assertEqual(0,self.planner.calls)
        self.assertEqual('REJECTED',self.store.event('run','close:r')['status'])
        with self.store.transaction() as db:
            self.assertEqual(0,db.execute('SELECT count(*) FROM commands').fetchone()[0])
        self.assert_replay()

    def test_restart_after_hold_plan_closes_complete_and_replays_later_time(self):
        runtime=self.runtime()
        with patch.object(runtime,'close',side_effect=RuntimeError('Crash after plan')):
            with self.assertRaises(RuntimeError): runtime.start('r',request(),NOW)
        self.runtime().start('r',request(),NOW+100)
        self.assertEqual(0,self.planner.calls)
        self.assertEqual('COMPLETE',self.store.event('run','close:r')['status'])
        self.assert_replay()

    def test_recovery_before_broadcast_waits_through_final_revert(self):
        runtime=self.runtime()
        runtime.start('r',request('BUY'),NOW)
        self.assertEqual([],runtime.recover(NOW+1))
        with self.assertRaises(Conflict): runtime.close('r',NOW+1,'COMPLETE')
        tx='0x'+'c'*64
        for i,kind in enumerate(('BROADCAST_ATTEMPTED','FINAL_REVERT')):
            runtime.observe(str(i),doc(dict(kind=kind,observation_id=str(i),round_id='r',tx_hash=tx,simulated=True)),settle)
        runtime.recover(NOW+2)
        with self.store.transaction() as db:
            audit=Document(bytes(db.execute('SELECT document FROM audit_events').fetchone()[0])).read()
        self.assertEqual(tx,json.loads(audit['log'])['data']['orders'][0]['tx_hash'])
        self.assertEqual(tx,audit['swap_mappings'][0]['tx_hash'])
        self.assertEqual(9,self.store.load('run').read()['projection']['balances']['BNB'])
        self.assert_replay()

    def test_closed_rounds_do_not_accumulate_in_projection(self):
        sizes=[]
        for i in range(8):
            self.runtime().start('r'+str(i),request(job='job'+str(i)),NOW)
            projection=self.store.load('run').read()['projection']
            self.assertEqual({},projection.get('round_records',{}))
            self.assertNotIn('closed_rounds',projection)
            sizes.append(len(doc(projection).payload))
        self.assertEqual(1,len(set(sizes)))
        self.assertIsNotNone(self.store.event('run','plan:r0')['record']['request'])
        self.assert_replay()

    def test_fallback_audit_replays_without_request_in_remote_log(self):
        large=request().read(); large['synthetic_large_input']='x'*2200000
        self.runtime().start('r',doc(large),NOW)
        with self.store.transaction() as db:
            audit=Document(bytes(db.execute('SELECT document FROM audit_events').fetchone()[0])).read()
        self.assertNotIn('request',json.loads(audit['log'])['data']['input'])
        self.assert_replay()

    def test_completed_execution_history_is_not_copied_into_later_rounds(self):
        for i in range(4):
            round_id='r'+str(i)
            runtime=self.runtime()
            runtime.start(round_id,request('BUY',job=round_id),NOW)
            tx='0x'+str(i+1)*64
            for kind in ('BROADCAST_ATTEMPTED','FINAL_SUCCESS'):
                identity=round_id+kind
                runtime.observe(identity,doc(dict(kind=kind,observation_id=identity,
                    round_id=round_id,tx_hash=tx,simulated=True)),settle)
            runtime.recover(NOW+1)
            current=self.store.load('run').read()
            self.assertEqual({},current['projection']['round_records'])
            self.assertNotIn('observations',current['projection'])
            self.assertEqual({},current['execution_state']['intents'])
            self.assertEqual([],current['reservations'])
        self.assert_replay()

    def test_unplanned_crash_closure_replays_from_durable_request(self):
        self.store.open_round('run','r',request(),self.epoch)
        self.runtime().recover(NOW)
        self.assert_replay()
