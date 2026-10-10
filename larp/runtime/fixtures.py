"""Synthetic development fakes. No fixture in this file may enter live mode.

This is deliberately tiny arithmetic for integration, not Keith's financial engine
or Isaac's transaction machine. Swaps are labelled simulated in every observation.
"""

from datetime import datetime,timedelta,timezone
from fractions import Fraction
import json

from larp.contracts import Document,PolicyState,Proposal,Target,TargetKind
from larp.storage.postgres import doc


def assess(request):
    r=request.read()
    return doc(dict(schema='AssessmentResult.v1',**{k:r[k] for k in
        ('job_id','run_id','issuer_id','context_hash','policy_profile_hash')},
        model_hash='synthetic',prompt_hash='synthetic',claims=[],novelty='unknown',conflicts=[],
        missingness=[],confidence='unknown',falsifiers=[],expiry_ms=r['cutoff_ms']+60000,
        review_requests=[],rationale='Synthetic fixture; no model inference or market claim.',
        model_io=dict(request=r,response='synthetic assessment')))


def policy(request):
    r=request.read()
    return doc(dict(action=r['context']['request'].get('fixture_action','HOLD')))


def hang(request):
    while True:
        pass


def fail(request):
    raise RuntimeError('Synthetic failure')


def inspect_capabilities(request):
    import os
    import socket
    from pathlib import Path
    connected=False
    try:
        socket.create_connection(('1.1.1.1',443),timeout=.05).close(); connected=True
    except OSError:
        pass
    return doc(dict(environment=dict(os.environ),home_exists=Path('/home').exists(),
                    env_exists=Path('/app/.env').exists(),network=connected))


class FakeAssessor:
    def assess(self,request):
        return assess(request)


class SandboxAssessor:
    def __init__(self,worker,entrypoint='larp.runtime.fixtures:assess'):
        self.worker,self.entrypoint=worker,entrypoint

    def assess(self,request):
        return self.worker.call(self.entrypoint,request)


class FakePolicy:
    def decide(self,snapshot,state):
        action=snapshot.context.read()['request'].get('fixture_action','HOLD')
        return self.proposal(snapshot,state,action)

    @staticmethod
    def proposal(snapshot,state,action):
        targets=() if action=='HOLD' else (Target('NVDAB',TargetKind.TARGET_WEIGHT,'SYNTHETIC',Fraction(1,10)),)
        return Proposal(snapshot.snapshot_id,state.policy_id,snapshot.observed_at+timedelta(seconds=60),targets,
            PolicyState(state.run_id,state.policy_id,state.schema,state.version+1,doc(dict(last_action=action))))


class SandboxPolicy(FakePolicy):
    def __init__(self,worker):
        self.worker=worker

    def decide(self,snapshot,state):
        result=self.worker.call('larp.runtime.fixtures:policy',doc(dict(snapshot_id=snapshot.snapshot_id,
            context=snapshot.context.read(),state=state.record())))
        return self.proposal(snapshot,state,result.read()['action'])


class FakePlanner:
    def __init__(self):
        self.calls=0

    def plan(self,snapshot,proposal_or_none):
        self.calls+=1
        request=snapshot.context.read()['request']
        intents=[]; reservations=[]
        if proposal_or_none is not None and proposal_or_none.targets:
            identity=request['job_id']
            intents=[dict(intent_id='intent:'+identity,decision_id='decision:'+identity,symbol='NVDAB',
                side='BUY',amount='10',pay_units=10,receive_units=2,gas_units=1,
                expires_ms=request['cutoff_ms']+60000)]
            reservations=[dict(intent_id='intent:'+identity,asset=a,units=n) for a,n in [('USDT',10),('BNB',1)]]
        return doc(dict(schema='PlanResult.v1',snapshot_id=snapshot.snapshot_id,reasons=['SYNTHETIC'],
            intents=intents,reservation_deltas=reservations,proposed_state={},jobs=[]))


def settle(current,observation):
    c=current.read(); o=observation.read()
    if o.get('simulated') is not True or o['kind'] not in ('BROADCAST_ATTEMPTED','FINAL_SUCCESS','FINAL_REVERT'):
        raise ValueError('Fixture reducer accepts only simulated observations')
    projection=c['projection']; seen=projection.setdefault('observations',[])
    if o['observation_id'] in seen:
        raise ValueError('Duplicate semantic observation')
    seen.append(o['observation_id'])
    record=projection['round_records'][o['round_id']]
    intent=record['plan']['intents'][0]
    execution=c['execution_state']
    state=execution.get(intent['intent_id'],{})
    deltas=[]
    if o['kind']=='BROADCAST_ATTEMPTED':
        if state:
            raise ValueError('Repeated broadcast authorization')
        record['orders'][0]['tx_hash']=o['tx_hash']
        record['swap_mappings'].append(dict(tx_hash=o['tx_hash'],decision_id=intent['decision_id']))
    else:
        if state.get('kind')!='BROADCAST_ATTEMPTED' or state['tx_hash']!=o['tx_hash']:
            raise ValueError('Outcome without matching durable attempt')
        projection['balances']['BNB']-=intent['gas_units']
        if o['kind']=='FINAL_SUCCESS':
            projection['balances']['USDT']-=intent['pay_units']
            projection['balances']['NVDAB']+=intent['receive_units']
        deltas=[dict(intent_id=intent['intent_id'],asset=a,units=-n) for a,n in
                [('USDT',intent['pay_units']),('BNB',intent['gas_units'])]]
    execution[intent['intent_id']]=o
    return doc(dict(projection=projection,execution_state=execution,reservation_deltas=deltas))


class FakeReceiver:
    def __init__(self,*,lose_ack=False,code=200):
        self.stored={}; self.lose_ack=lose_ack; self.code=code

    def deliver(self,event):
        e=event.read(); key=(e['event_id'],e['chunk_index'])
        if self.code!=200:
            return doc(dict(status_code=self.code,body={}))
        if key in self.stored and self.stored[key]!=e['body']:
            raise ValueError('Immutable receiver record changed')
        self.stored[key]=e['body']
        if self.lose_ack:
            self.lose_ack=False
            raise OSError('Synthetic lost acknowledgement')
        return doc(dict(status_code=200,body=dict(eventId=key[0],chunkIndex=key[1],status='STORED')))
