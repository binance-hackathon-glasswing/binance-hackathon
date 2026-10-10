"""Thin ordered coordinator. Financial and execution semantics are injected ports.

Only a reducer supplied by the owning component may change settled balances.
Fixture reducers live in fixtures.py and never qualify a live deployment.
"""

from datetime import datetime,timezone

from larp.audit.protocol import build_event
from larp.contracts import ContractError,DecisionSnapshot,Document,PolicyState,validate_proposal
from larp.storage.postgres import Conflict,IntegrityError,doc
from larp.runtime.schema import assessment_request,assessment_result


def batch_for(current,event_id,event,*,projection=None,policy_state=None,execution_state=None,
              reservation_deltas=(),jobs=(),commands=(),audit=()):
    c=current.read()
    return doc(dict(schema='CommitBatch.v1',run_id=c['run_id'],wallet_id=c['wallet_id'],chain_id=c['chain_id'],
        event_id=event_id,expected_version=c['version'],owner_epoch=c['epoch'],event=event,
        projection=c['projection'] if projection is None else projection,
        policy_state=c['policy_state'] if policy_state is None else policy_state,
        execution_state=c['execution_state'] if execution_state is None else execution_state,
        reservation_deltas=list(reservation_deltas),jobs=list(jobs),commands=list(commands),
        audit=[a.read() if isinstance(a,Document) else a for a in audit]))


class Coordinator:
    def __init__(self,store,assessor,policy,planner,*,execution,run_id,version_id,profile_hash,address):
        self.store,self.assessor,self.policy,self.planner=store,assessor,policy,planner
        self.run_id,self.version_id,self.profile_hash,self.address=run_id,version_id,profile_hash,address
        self.execution=execution

    def snapshot(self,current,now_ms,context):
        c=current.read()
        state=c['policy_state'] or dict(run_id=self.run_id,policy_id='fixture',schema='PolicyState.v1',version=0,data={})
        return DecisionSnapshot(self.run_id,c['wallet_id'],self.version_id,self.profile_hash,c['version'],
            datetime.fromtimestamp(now_ms/1000,timezone.utc),('NVDAB','GOOGLB','SKHYB','TSLAB','MSFTB'),
            PolicyState(state['run_id'],state['policy_id'],state['schema'],state['version'],doc(state['data'])),doc(context))

    def start(self,round_id,request,now_ms):
        current=self.store.load(self.run_id)
        self.store.open_round(self.run_id,round_id,request,current.read()['epoch'])
        closed=self.store.receipt(self.run_id,'close:'+round_id)
        if closed:
            return closed
        previous=self.store.receipt(self.run_id,'plan:'+round_id)
        if previous:
            return previous
        assessment=None; proposal=None; errors=[]
        try:
            assessment_request(request,self.run_id,self.profile_hash,now_ms)
            assessment=self.assessor.assess(request)
            assessment_result(assessment,request,now_ms)
        except Exception:
            errors.append('ASSESSMENT_UNAVAILABLE'); assessment=None
        # Runtime history is journal data, not recursively embedded policy context.
        portfolio={k:v for k,v in current.read()['projection'].items()
                   if k not in ('round_records','closed_rounds','observations')}
        context=dict(projection=portfolio,reservations=current.read()['reservations'],
                     request=request.read(),assessment=assessment.read() if assessment else None)
        snapshot=self.snapshot(current,now_ms,context)
        if assessment is not None:
            try:
                proposal=self.policy.decide(snapshot,snapshot.policy_state)
                validate_proposal(snapshot,proposal,now=datetime.fromtimestamp(now_ms/1000,timezone.utc))
            except Exception:
                errors.append('POLICY_REJECTED'); proposal=None
        # Mandatory risk is called even when there is no policy output.
        try:
            plan=self.planner.plan(snapshot,proposal).read()
            if plan['schema']!='PlanResult.v1' or plan['snapshot_id']!=snapshot.snapshot_id:
                raise ContractError('Mismatched planner result')
        except Exception:
            errors.append('PLANNER_UNAVAILABLE')
            plan=dict(schema='PlanResult.v1',snapshot_id=snapshot.snapshot_id,reasons=['PLANNER_UNAVAILABLE'],
                      intents=[],reservation_deltas=[],jobs=[],proposed_state={})
        projection=current.read()['projection']
        record=dict(round_id=round_id,request=request.read(),assessment=assessment.read() if assessment else None,
                    proposal_id=proposal.proposal_id if proposal else None,plan=plan,errors=errors,
                    policy_input=context,policy_state=snapshot.policy_state.record(),
                    policy_output=None if proposal is None else dict(targets=[t.record() for t in proposal.targets],
                        next_policy_state=proposal.next_policy_state.record(),valid_until=proposal.valid_until.isoformat()),
                    started_ms=now_ms,orders=[dict(symbol=i['symbol'],side=i['side'],amount=i['amount'])
                        for i in plan['intents']],swap_mappings=[])
        projection.setdefault('round_records',{})[round_id]=record
        commands=[dict(command_id=i['intent_id'],kind='EXECUTION_REQUEST',payload=i,round_id=round_id,
                       decision_id=i['decision_id'],expires_ms=i['expires_ms']) for i in plan['intents']]
        reservation_deltas=plan['reservation_deltas']
        try:
            self.audit_record(record,round_id,now_ms,'PREFLIGHT')
            # Leave space for later hashes/outcome metadata; this is a development
            # serialization budget, not an adopted trading parameter.
            if len(doc(record).payload)>4*1024*1024:
                raise ContractError('Round exceeds pre-execution audit budget')
        except ContractError:
            record['errors'].append('AUDIT_CONTENT_UNSUPPORTED')
            record['audit_fallback']=True
            commands=[]; reservation_deltas=[]
        # Holdings remain byte-identical: the planner can only REQUEST reservations.
        try:
            receipt=self.store.commit(batch_for(current,'plan:'+round_id,dict(kind='ROUND_PLANNED',record=record),
                projection=projection,policy_state=proposal.next_policy_state.record() if proposal else None,
                reservation_deltas=reservation_deltas,jobs=plan['jobs'],commands=commands))
        except Conflict:
            # Rejection is itself a durable outcome, never a silent lost round.
            current=self.store.load(self.run_id)
            record['errors'].append('COMMIT_REJECTED')
            projection=current.read()['projection']
            projection.setdefault('round_records',{})[round_id]=record
            self.store.commit(batch_for(current,'rejected:'+round_id,dict(kind='PLAN_REJECTED',record=record),
                                         projection=projection))
            return self.close(round_id,now_ms,'REJECTED')
        if not commands:
            return self.close(round_id,now_ms,'COMPLETE')
        return receipt

    def observe(self,event_id,observation,reducer):
        expected=dict(kind='OBSERVATION',observation=observation.read())
        old=self.store.event(self.run_id,event_id)
        if old is not None:
            if old!=expected:
                raise IntegrityError('Observation ID reused with changed facts')
            return self.store.receipt(self.run_id,event_id)
        current=self.store.load(self.run_id)
        state=current.read()['execution_state'] or dict(schema='ExecutionState.v1',intents={})
        transition=self.execution.advance(doc(state),observation).read()
        if transition.get('schema')!='ExecutionTransition.v1':
            raise ContractError('Invalid execution transition')
        # reducer returns the owner's explicit atomic transition document.
        change=reducer(current,observation).read()
        return self.store.commit(batch_for(current,event_id,expected,
            projection=change['projection'],execution_state=transition['next_state'],
            reservation_deltas=change.get('reservation_deltas',[]),commands=transition.get('commands',[])))

    def audit_record(self,record,round_id,now_ms,status):
        assessment=record['assessment']
        rationale=(assessment['rationale'] if assessment else
                   'Deterministic runtime record: assessment unavailable; no model reasoning is claimed.')
        decisions=sorted({m['decision_id'] for m in record['swap_mappings']} |
                         {i['decision_id'] for i in record['plan'].get('intents',[])})
        inputs=dict(version_id=self.version_id,round_id=round_id,request=record['request'],
                    assessment=assessment,policy_input=record.get('policy_input'),policy_state=record.get('policy_state'))
        output=dict(status=status,errors=record['errors'],plan=record['plan'],proposal_id=record['proposal_id'],
                    policy_output=record.get('policy_output'))
        if record.get('audit_fallback'):
            inputs=dict(version_id=self.version_id,round_id=round_id,
                        local_record_hash=doc(record).digest('larp.round.v1'),
                        omitted_content='Original complete I/O retained in the durable ROUND_PLANNED record; serialization budget exceeded.')
            output=dict(status='AUDIT_CONTENT_UNSUPPORTED',errors=record['errors'],trading_blocked=True)
            rationale='Deterministic serialization failure; original reasoning retained locally, not fabricated or truncated.'
        return build_event(event_id='round:'+round_id,round_id=round_id,version_id=self.version_id,
            decision_ids=decisions,address=self.address,timestamp_ms=now_ms,input_record=inputs,rationale=rationale,
            output=output,orders=record['orders'],swap_mappings=record['swap_mappings'])

    def close(self,round_id,now_ms,status):
        previous=self.store.receipt(self.run_id,'close:'+round_id)
        if previous:
            return previous
        current=self.store.load(self.run_id)
        record=current.read()['projection'].get('round_records',{}).get(round_id)
        if record is None:
            request=dict(self.store.open_rounds(self.run_id))[round_id].read()
            record=dict(request=request,assessment=None,proposal_id=None,plan={},errors=['PROCESS_INTERRUPTED'],
                        started_ms=now_ms,orders=[],swap_mappings=[])
        audit=self.audit_record(record,round_id,now_ms,status)
        projection=current.read()['projection']
        projection.setdefault('closed_rounds',[]).append(round_id)
        return self.store.commit(batch_for(current,'close:'+round_id,dict(kind='ROUND_CLOSED',status=status),
                                           projection=projection,audit=[audit]))

    def recover(self,now_ms):
        # No attempts are released or re-signed here. Isaac reconciles commands.
        return [self.close(round_id,now_ms,'INTERRUPTED_UNRESOLVED')
                for round_id,_ in self.store.open_rounds(self.run_id)]
