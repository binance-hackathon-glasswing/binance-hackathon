"""Restartable offline integration reproducer with real PostgreSQL and fake ports.

Run only against a disposable LARP_TEST_DATABASE_URL. Every run creates a separate
schema and retains it for inspection. No live read, signer or uploader is constructed.
"""

import argparse
import json
import os
import uuid

from larp.audit.delivery import DeliveryWorker
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakePlanner,FakeReceiver,FakeMarket,FakeExecution,SandboxAssessor,SandboxPolicy,settle
from larp.runtime.worker import IsolatedWorker
from larp.storage.postgres import PostgresStore,doc


def main():
    import psycopg
    from psycopg.conninfo import make_conninfo
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema',default='larp_demo_'+uuid.uuid4().hex[:12])
    args=parser.parse_args()
    if not args.schema.startswith('larp_demo_') or not args.schema.replace('_','').isalnum():
        parser.error('Schema must be a disposable larp_demo_ identifier')
    dsn=os.environ.get('LARP_TEST_DATABASE_URL')
    if not dsn:
        parser.error('Set LARP_TEST_DATABASE_URL to a disposable database')
    with psycopg.connect(dsn) as db:
        db.execute('CREATE SCHEMA '+args.schema)
    store=PostgresStore(make_conninfo(dsn,options='-c search_path='+args.schema))
    store.migrate(); store.initialize('run','synthetic-wallet',56,doc(dict(balances=dict(USDT=100,BNB=10,NVDAB=0))))
    epoch=store.takeover('run',1,offline=True)
    worker=IsolatedWorker(timeout=3)
    def coordinator(assessor=None):
        return Coordinator(store,assessor or SandboxAssessor(worker),SandboxPolicy(worker),FakePlanner(),
                           execution=FakeExecution(),run_id='run',version_id='synthetic-build',profile_hash='a'*64,address='0x'+'1'*40)
    now=1791590400000
    market=FakeMarket().observe(doc(dict(schema='MarketRequest.v1',request_id='market',run_id='run',
                                        token='NVDAB',underlying='NVDA',cutoff_ms=now)))
    request=doc(dict(schema='AssessmentRequest.v1',job_id='job',run_id='run',issuer_id='NVDA',cutoff_ms=now,
        market=market.read(),
        context_hash='c'*64,policy_profile_hash='a'*64,evidence_refs=[dict(source='synthetic',content_hash='e'*64,
        observed_ms=now,available_ms=now,quality='SYNTHETIC')],allowed_tools=[],
        budget=dict(tool_calls=6,deadline_ms=60000),fixture_action='BUY'))
    runtime=coordinator(); runtime.start('entry',request,now)
    if not store.load('run').read()['projection']['round_records']['entry']['plan']['intents']:
        raise RuntimeError('Isolated fixture failed; inspect audit record, no successful entry claimed')
    tx='0x'+'b'*64
    runtime.observe('broadcast',doc(dict(kind='BROADCAST_ATTEMPTED',observation_id='broadcast',round_id='entry',
                                       tx_hash=tx,simulated=True)),settle)
    # Reconstruct controller and reconnect database; no mutable policy object carries state.
    runtime=coordinator(); runtime.recover(now+1)
    runtime.observe('settled',doc(dict(kind='FINAL_SUCCESS',observation_id='settled',round_id='entry',
                                     tx_hash=tx,simulated=True)),settle)
    runtime.recover(now+2)
    rejected=request.read(); rejected['job_id']='failed'; rejected['fixture_action']='HOLD'
    coordinator(SandboxAssessor(worker,'larp.runtime.fixtures:fail')).start('rejected',doc(rejected),now+2)
    receiver=FakeReceiver(lose_ack=True)
    uploader=DeliveryWorker(store,receiver,retry_ms=1)
    for tick in range(10): uploader.once('run',epoch,now+tick+3)
    print(json.dumps(dict(schema=args.schema,mode='offline',simulated=True,head=store.verify('run'),
        state=store.load('run').read(),metrics=store.metrics('run').read(),
        journal=[b.read() for b in store.journal('run')],audit_chunks=list(receiver.stored.values())),indent=2))


if __name__=='__main__':
    main()
