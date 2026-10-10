"""PR #3 second-review regression criteria (IDEA-028 RT17 #1-#5)."""

import json
from unittest.mock import patch

from larp.audit.delivery import DeliveryWorker
from larp.audit.protocol import EVENT_ID,event_id_for
from larp.contracts import ContractError,Document
from larp.runtime.coordinator import Coordinator,RecoveryIncomplete
from larp.runtime.fixtures import FakeAssessor,FakePolicy,FakePlanner,FakeExecution,FakeReceiver,settle
from larp.runtime.replay import replay
from larp.storage.postgres import IntegrityError,doc
from tests.audit.test_protocol import event
from tests.support import DatabaseCase,job,request

NOW=1791590400000
ADDRESS='0x'+'1'*40
INITIAL=dict(balances=dict(USDT=100,BNB=10,NVDAB=0))


class AmountPlanner(FakePlanner):
    """Planner output the audit log cannot record: a numeric amount."""
    def plan(self,snapshot,proposal_or_none):
        plan=super().plan(snapshot,proposal_or_none).read()
        for intent in plan['intents']: intent['amount']=10
        return doc(plan)


class GasTopUpPlanner(FakePlanner):
    """A USDT->BNB swap: not one of the five eligible symbols."""
    def plan(self,snapshot,proposal_or_none):
        plan=super().plan(snapshot,proposal_or_none).read()
        for intent in plan['intents']: intent['symbol']='BNB'
        return doc(plan)


class Base(DatabaseCase):
    def runtime(self,planner=FakePlanner):
        self.planner=planner()
        return Coordinator(self.store,FakeAssessor(),FakePolicy(),self.planner,execution=FakeExecution(),
            run_id='run',version_id='synthetic',profile_hash='a'*64,address=ADDRESS)

    def assert_replay(self,planner=FakePlanner):
        journal=self.store.journal('run')
        expected=self.store.verify('run')
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        replay(journal,doc(INITIAL),self.store,run_id='run',wallet_id='wallet',chain_id=56,
            version_id='synthetic',profile_hash='a'*64,address=ADDRESS,policy=FakePolicy(),planner=planner(),
            execution=FakeExecution(),reducer=settle)
        self.assertEqual(expected,self.store.verify('run'))

    def audits(self):
        with self.store.transaction() as db:
            return [Document(bytes(r[0])).read() for r in
                    db.execute('SELECT document FROM audit_events ORDER BY event_id')]

    def commands(self):
        with self.store.transaction() as db:
            return db.execute('SELECT count(*) FROM commands').fetchone()[0]


class FallbackAudit(Base):
    """#1: every round closes with an accepted audit; one failure never blocks the rest."""

    def test_unrecordable_orders_never_commit_and_the_round_closes(self):
        for planner in (AmountPlanner,GasTopUpPlanner):
            with self.subTest(planner=planner.__name__):
                self.runtime(planner).start('r',request('BUY'),NOW)
                [audit]=self.audits()
                log=json.loads(audit['log'])['data']
                self.assertEqual([],log['orders'])
                self.assertIn('PLAN_INVALID',log['output']['errors'])
                self.assertEqual('COMPLETE',self.store.event('run','close:r')['status'])
                self.assertEqual(0,self.commands())
                self.assertEqual([],self.store.load('run').read()['reservations'])
                self.assert_replay(planner)
                with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
                self.store.initialize('run','wallet',56,doc(INITIAL))
                self.epoch=self.store.takeover('run',1,offline=True)

    def test_round_id_outside_the_protocol_charset_closes(self):
        self.runtime().start('round / with spaces',request(),NOW)
        [audit]=self.audits()
        self.assertTrue(EVENT_ID.fullmatch(audit['event_id']))
        self.assertEqual(0,self.store.metrics('run').read()['open_rounds'])
        self.assert_replay()

    def test_non_string_round_id_is_refused_before_any_write(self):
        version=self.store.load('run').read()['version']
        for round_id in ('',None,7):
            with self.subTest(round_id=round_id), self.assertRaises(ContractError):
                self.runtime().start(round_id,request(),NOW)
        self.assertEqual(version,self.store.load('run').read()['version'])
        self.assertEqual(0,self.store.metrics('run').read()['open_rounds'])

    def test_fallback_and_rejected_rounds_log_no_orders(self):
        large=request('BUY').read(); large['synthetic_large_input']='x'*2200000
        self.runtime().start('fallback',doc(large),NOW)
        runtime=self.runtime(); commit=self.store.commit
        def conflict_once(batch):
            if batch.read()['event_id']=='plan:rejected':
                from larp.storage.postgres import Conflict
                raise Conflict('Synthetic version race')
            return commit(batch)
        with patch.object(self.store,'commit',side_effect=conflict_once):
            runtime.start('rejected',request('BUY',job='job2'),NOW)
        audits={a['round_id']:json.loads(a['log'])['data'] for a in self.audits()}
        self.assertEqual({'fallback','rejected'},set(audits))
        for round_id,log in audits.items():
            with self.subTest(round_id=round_id):
                self.assertEqual([],log['orders'])
        self.assertEqual('AUDIT_CONTENT_UNSUPPORTED',audits['fallback']['output']['status'])
        self.assertEqual(0,self.commands())
        self.assert_replay()

    def test_one_failing_round_does_not_block_later_rounds(self):
        for round_id in ('a','b'):
            self.store.open_round('run',round_id,request(job=round_id),self.epoch)
        runtime=self.runtime(); build=runtime.audit_record
        def fail_a(record,round_id,*rest):
            if round_id=='a':
                raise ContractError('Synthetic unrecordable round')
            return build(record,round_id,*rest)
        with patch.object(runtime,'audit_record',side_effect=fail_a):
            with self.assertRaises(RecoveryIncomplete) as caught:
                runtime.recover(NOW)
        self.assertEqual([('a','ContractError')],caught.exception.failures)
        self.assertEqual(1,len(caught.exception.receipts))
        self.assertIsNotNone(self.store.receipt('run','close:b'))
        self.assertEqual(['a'],[r for r,_ in self.store.open_rounds('run')])


class IncrementalVerification(Base):
    """#2: writes verify only new events; corruption still fails closed."""

    def calls(self):
        seen=[]; verify=self.store._verify
        def record(db,run_id,run,base=None):
            seen.append(None if base is None else base['version'])
            return verify(db,run_id,run,base)
        return seen,patch.object(self.store,'_verify',side_effect=record)

    def test_writes_continue_from_the_checkpoint(self):
        self.store.commit(self.batch('first'))
        seen,patched=self.calls()
        with patched:
            for i in range(8):
                self.store.commit(self.batch('e'+str(i),commands=[dict(command_id='c'+str(i),expires_ms=999,kind='FAKE')]))
            self.store.command('run','c7',self.epoch,100)
        # Each write continues from the version verified before the previous write.
        self.assertEqual(list(range(0,9)),seen)
        self.store.verify('run')
        # A new process has no checkpoint: its first write verifies everything.
        fresh=type(self.store)(self.store._dsn); seen.clear()
        with patch.object(fresh,'_verify',side_effect=lambda db,run_id,run,base=None:
                          seen.append(base) or type(fresh)._verify(db,run_id,run,base)):
            fresh.commit(self.batch('from-fresh-process'))
        self.assertEqual([None],seen)

    def test_incremental_path_fails_closed(self):
        # One run per case in this schema; every statement is scoped to that run.
        cases={
            'projection':"UPDATE runs SET projection='{}'::bytea WHERE run_id=%s",
            'reservations':'UPDATE reservations SET units=units+1 WHERE run_id=%s',
            'extra chunk':"INSERT INTO audit_chunks(run_id,event_id,chunk_index,body) VALUES(%s,'evt',99,'x'::bytea)",
            'deleted chunk':'DELETE FROM audit_chunks WHERE run_id=%s',
            'deleted command':'DELETE FROM commands WHERE run_id=%s',
            'deleted job':'DELETE FROM jobs WHERE run_id=%s',
            'changed new command':"UPDATE commands SET payload='{}'::bytea WHERE run_id=%s",
        }
        for n,(name,sql) in enumerate(cases.items()):
            with self.subTest(name):
                run_id='case'+str(n)
                self.store.initialize(run_id,'wallet',56,doc(INITIAL))
                self.store.takeover(run_id,1,offline=True)
                def commit(event_id,**kwargs):
                    from larp.runtime.coordinator import batch_for
                    return self.store.commit(batch_for(self.store.load(run_id),event_id,
                                                       dict(kind='SYNTHETIC'),**kwargs))
                commit('first')
                commit('second',audit=[event()],jobs=[job()],
                       commands=[dict(command_id='c',expires_ms=999,kind='FAKE')],
                       reservation_deltas=[dict(intent_id='i',asset='USDT',units=20)])
                if name!='changed new command':
                    commit('third')  # the checkpoint now covers 'second'
                with self.store.transaction() as db: db.execute(sql,(run_id,))
                with self.assertRaises(IntegrityError):
                    commit('after')

    def test_full_verification_still_finds_changed_old_rows(self):
        self.store.commit(self.batch('first',audit=[event()]))
        self.store.commit(self.batch('second'))
        self.store.commit(self.batch('third'))
        for sql in ("UPDATE audit_chunks SET body='changed'::bytea",
                    'UPDATE events SET batch=(SELECT batch FROM events WHERE sequence=2) WHERE sequence=1'):
            with self.subTest(sql=sql):
                with self.store.transaction() as db:
                    db.execute('SAVEPOINT s')
                    db.execute(sql)
                    with self.assertRaises(IntegrityError):
                        type(self.store)._verify(db,'run',self.store._run(db,'run'))
                    db.execute('ROLLBACK TO SAVEPOINT s')


class DeliveryAttempts(Base):
    """#3: an older in-flight attempt never overwrites a newer attempt's result."""

    def overlap(self,newer,older):
        self.store.commit(self.batch(audit=[event()]))
        holder={}
        def response(code,value):
            e=value.read()
            if code=='ACK':
                return doc(dict(status_code=200,body=dict(eventId=e['event_id'],chunkIndex=e['chunk_index'],status='STORED')))
            return doc(dict(status_code=code,body={}))
        class Receiver(FakeReceiver):
            calls=0
            def deliver(inner,value):
                inner.calls+=1
                if inner.calls==1:
                    holder['worker'].once('run',self.epoch,10)  # newer attempt while this one is in flight
                    return response(older,value)
                return response(newer,value)
        holder['worker']=DeliveryWorker(self.store,Receiver(),retry_ms=1)
        holder['worker'].once('run',self.epoch,0)
        with self.store.transaction() as db:
            return db.execute('SELECT status,attempts,last_code FROM audit_chunks').fetchone()

    def test_newer_permanent_is_not_reset_by_older_transient(self):
        self.assertEqual(('PERMANENT',2,'400'),self.overlap(400,503))

    def test_newer_transient_is_not_made_permanent_by_older_rejection(self):
        self.assertEqual(('PENDING',2,'503'),self.overlap(503,400))

    def test_older_ack_always_counts(self):
        self.assertEqual(('ACK',2,'200'),self.overlap(503,'ACK'))


class ErrorClassification(Base):
    """#4: a constraint violation is permanent, not a transient outage."""

    def test_duplicate_swap_owner_is_integrity_error(self):
        tx='0x'+'d'*64
        order=dict(symbol='NVDAB',side='BUY',amount='1',tx_hash=tx)
        mapping=dict(tx_hash=tx,decision_id='d',step='swap')
        self.store.commit(self.batch('one',audit=[event('evt-1','r1',orders=[order],mappings=[mapping])]))
        with self.assertRaises(IntegrityError) as caught:
            self.store.commit(self.batch('two',audit=[event('evt-2','r2',orders=[order],mappings=[mapping])]))
        self.assertIn('swap_owners_pkey',str(caught.exception))
        self.assertNotIn(tx,str(caught.exception))
        self.assertEqual(1,self.store.load('run').read()['version'])


class RunScopedEventIds(Base):
    """#5: event IDs are scoped to run, wallet, round and journal position."""

    def test_ids_follow_the_kit_format_and_depend_on_scope(self):
        base=event_id_for('run',ADDRESS,'entry','0'*64,NOW)
        self.assertRegex(base,r'^evt-1791590400000-[0-9a-f]{12}$')
        self.assertEqual(event_id_for('run','0x'+'ab'*20,'entry','0'*64,NOW),
                         event_id_for('run','0x'+'aB'*20,'entry','0'*64,NOW))
        for other in (event_id_for('run2',ADDRESS,'entry','0'*64,NOW),event_id_for('run','0x'+'2'*40,'entry','0'*64,NOW),
                      event_id_for('run',ADDRESS,'exit','0'*64,NOW),event_id_for('run',ADDRESS,'entry','1'*64,NOW),
                      event_id_for('run',ADDRESS,'entry','0'*64,NOW+1)):
            self.assertNotEqual(base,other)

    def test_reinitialised_run_reusing_round_ids_gets_new_event_ids(self):
        self.runtime().start('entry',request('HOLD'),NOW)
        [first]=self.audits()
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        self.store.initialize('run','wallet',56,doc(INITIAL))
        self.epoch=self.store.takeover('run',1,offline=True)
        self.runtime().start('entry',request('HOLD',job='rehearsal-2'),NOW+60000)
        [second]=self.audits()
        self.assertNotEqual(first['event_id'],second['event_id'])
        self.assertTrue(EVENT_ID.fullmatch(second['event_id']))
        self.assert_replay()
        [replayed]=self.audits()
        self.assertEqual(second['event_id'],replayed['event_id'])
