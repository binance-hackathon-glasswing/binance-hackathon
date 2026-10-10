"""Exact downstream replay from captured assessment outputs, without venue writes.

Re-runs the injected deterministic policy/planner/execution/reducer. Recommitting
saved projections alone is restore verification, not this conformance check.
"""

import json

from larp.contracts import ContractError,Document
from larp.runtime.coordinator import Coordinator
from larp.storage.postgres import IntegrityError,digest,doc


class RecordedAssessment:
    def __init__(self,request,result):
        self.request,self.result=request,result

    def assess(self,request):
        if request.read()!=self.request:
            raise IntegrityError('Replay assessment request changed')
        if self.result is None:
            raise ContractError('Recorded assessment unavailable')
        return doc(self.result)


def replay(batches,initial,target,*,run_id,wallet_id,chain_id,version_id,profile_hash,address,
           policy,planner,execution,reducer):
    target.initialize(run_id,wallet_id,chain_id,initial)
    runtime=None
    for batch in batches:
        b=batch.read(); event=b['event']; kind=event['kind']
        current=target.load(run_id).read()
        while current['epoch']<b['owner_epoch']:
            target.takeover(run_id,current['epoch'],offline=True)
            current=target.load(run_id).read()
        existing=target.receipt(run_id,b['event_id'])
        if existing is None:
            if kind in ('ROUND_PLANNED','PLAN_REJECTED'):
                record=event['record']
                runtime=Coordinator(target,RecordedAssessment(record['request'],record['assessment']),policy,planner,
                    execution=execution,run_id=run_id,version_id=version_id,profile_hash=profile_hash,address=address)
                runtime.start(record['round_id'],doc(record['request']),record['started_ms'])
            elif kind=='OBSERVATION':
                if runtime is None: raise IntegrityError('Replay observation has no round context')
                runtime.observe(b['event_id'],doc(event['observation']),reducer)
            elif kind=='ROUND_CLOSED':
                audit=b['audit'][0]
                if runtime is None:
                    request=json.loads(audit['log'])['data']['input']['request']
                    target.open_round(run_id,audit['round_id'],doc(request),current['epoch'])
                    runtime=Coordinator(target,RecordedAssessment(request,None),policy,planner,execution=execution,
                        run_id=run_id,version_id=version_id,profile_hash=profile_hash,address=address)
                runtime.close(audit['round_id'],audit['timestamp_ms'],event['status'])
            else:
                raise ContractError('Unsupported replay event; register an owner reducer')
        receipt=target.receipt(run_id,b['event_id'])
        if receipt is None or receipt.read()['batch_hash']!=digest(batch.payload):
            raise IntegrityError('Deterministic replay diverged')
    return target.verify(run_id)
