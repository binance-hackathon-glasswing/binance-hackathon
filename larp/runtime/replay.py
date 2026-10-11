"""Exact downstream replay from captured assessment outputs, without venue writes.

Re-runs the injected deterministic policy/planner/execution/reducer. Recommitting
saved projections alone is restore verification, not this conformance check.
Rounds recorded with a context builder (larp/integration/runtime.py) replay only with
that builder and initial policy state, and only if its ports return what they returned
then, failures included (IDEA-033 R27). For live rounds, larp/integration/replay.py feeds
the recorded port answers back (IDEA-042 item 4).
"""

import json

from larp.contracts import ContractError,Document
from larp.runtime.coordinator import Coordinator
from larp.storage.postgres import IntegrityError,digest,doc


RECORDED_FACTS=('INCIDENT','HALT','HALT_CLEARED')


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
           policy,planner,execution,reducer,context_builder=None,initial_policy_state=None,test_rounds=False,
           builder_for=None):
    """builder_for(record), when given, supplies each planned round's context builder (recorded ports,
    larp/integration/replay.py); otherwise context_builder is used for every round."""
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
                    execution=execution,run_id=run_id,version_id=version_id,profile_hash=profile_hash,address=address,
                    context_builder=builder_for(record) if builder_for else context_builder,
                    initial_policy_state=initial_policy_state,test_rounds=test_rounds,
                    clock_ms=lambda:record.get('decision_ms',record['started_ms']))
                if kind=='PLAN_REJECTED':
                    target.open_round(run_id,record['round_id'],doc(record['request']),current['epoch'])
                    runtime.record_rejection(record['round_id'],record)
                else:
                    runtime.start(record['round_id'],doc(record['request']),record['started_ms'],defer_close=True)
            elif kind in RECORDED_FACTS:
                # Supervision facts (larp/runtime/supervision.py) are recorded, not computed: recommit them as they are.
                target.commit(batch)
            elif kind=='OBSERVATION':
                if runtime is None: raise IntegrityError('Replay observation has no round context')
                runtime.observe(b['event_id'],doc(event['observation']),reducer)
            elif kind=='ROUND_CLOSED':
                audit=b['audit'][0]
                request=event.get('request')
                if request is not None:
                    target.open_round(run_id,audit['round_id'],doc(request),current['epoch'])
                if runtime is None:
                    if request is None:
                        request=json.loads(audit['log'])['data']['input'].get('request')
                    if request is None:
                        raise IntegrityError('Replay closure lacks its durable round request')
                    target.open_round(run_id,audit['round_id'],doc(request),current['epoch'])
                    runtime=Coordinator(target,RecordedAssessment(request,None),policy,planner,execution=execution,
                        run_id=run_id,version_id=version_id,profile_hash=profile_hash,address=address,
                        context_builder=context_builder,initial_policy_state=initial_policy_state,test_rounds=test_rounds)
                runtime.close(audit['round_id'],audit['timestamp_ms'],event['status'])
            else:
                raise ContractError('Unsupported replay event; register an owner reducer')
        receipt=target.receipt(run_id,b['event_id'])
        if receipt is None or receipt.read()['batch_hash']!=digest(batch.payload):
            raise IntegrityError('Deterministic replay diverged')
    return target.verify(run_id)
