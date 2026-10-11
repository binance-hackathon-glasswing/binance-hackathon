"""Thin ordered coordinator. Financial and execution semantics are injected ports.

Only a reducer supplied by the owning component may change settled balances.
Fixture reducers live in fixtures.py and never qualify a live deployment.
"""

from datetime import datetime,timezone
import time

from larp.audit.protocol import build_event,check_orders,event_id_for
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


class RecoveryIncomplete(ContractError):
    """Some rounds could not close; every other closable round was closed."""
    def __init__(self,receipts,failures):
        super().__init__('Rounds not closed: '+', '.join(f'{r} ({e})' for r,e in failures))
        self.receipts,self.failures=receipts,failures


class Coordinator:
    def __init__(self,store,assessor,policy,planner,*,execution,run_id,version_id,profile_hash,address,
                 context_builder=None,initial_policy_state=None,clock_ms=None):
        self.store,self.assessor,self.policy,self.planner=store,assessor,policy,planner
        self.run_id,self.version_id,self.profile_hash,self.address=run_id,version_id,profile_hash,address
        self.execution=execution
        self.clock=clock_ms if clock_ms is not None else lambda: time.time_ns()//1_000_000
        # Optional versioned adapter (larp/integration/runtime.py, IDEA-031): builds the policy context from the
        # journaled projection, the request and the assessment, and returns projection updates (evidence state)
        # committed atomically with the round. Without it the original fixture context is used.
        self.context_builder,self.initial_policy_state=context_builder,initial_policy_state

    def snapshot(self,current,now_ms,context):
        c=current.read()
        state=c['policy_state'] or self.initial_policy_state or dict(run_id=self.run_id,policy_id='fixture',
            schema='PolicyState.v1',version=0,data={})
        return DecisionSnapshot(self.run_id,c['wallet_id'],self.version_id,self.profile_hash,c['version'],
            datetime.fromtimestamp(now_ms/1000,timezone.utc),('NVDAB','GOOGLB','SKHYB','TSLAB','MSFTB'),
            PolicyState(state['run_id'],state['policy_id'],state['schema'],state['version'],doc(state['data'])),doc(context))

    def start(self,round_id,request,now_ms,*,defer_close=False):
        if type(round_id) is not str or not round_id:
            raise ContractError('Round ID must be a non-empty string')
        current=self.store.load(self.run_id)
        self.store.open_round(self.run_id,round_id,request,current.read()['epoch'])
        closed=self.store.receipt(self.run_id,'close:'+round_id)
        if closed:
            return closed
        rejected=self.store.receipt(self.run_id,'rejected:'+round_id)
        if rejected:
            return rejected if defer_close else self.close(round_id,now_ms,'REJECTED')
        previous=self.store.receipt(self.run_id,'plan:'+round_id)
        if previous:
            record=current.read()['projection']['round_records'][round_id]
            if not defer_close and not record.get('execution_pending',True):
                return self.close(round_id,now_ms,'COMPLETE')
            return previous
        assessment=None; proposal=None; errors=[]
        started_ms=now_ms
        try:
            assessment_request(request,self.run_id,self.profile_hash,now_ms)
            assessment=self.assessor.assess(request)
        except Exception:
            errors.append('ASSESSMENT_UNAVAILABLE'); assessment=None
        now_ms=self.clock()
        if type(now_ms) is not int or now_ms<started_ms:
            raise ContractError('Decision clock moved backward or is invalid; reconciliation required')
        if assessment is not None:
            try:
                assessment_result(assessment,request,now_ms)
            except Exception:
                errors.append('ASSESSMENT_UNAVAILABLE'); assessment=None
        # Runtime history is journal data, not recursively embedded policy context.
        portfolio={k:v for k,v in current.read()['projection'].items()
                   if k not in ('round_records','closed_rounds','observations')}
        updates={}; context_ok=True
        if self.context_builder is None:
            context=dict(projection=portfolio,reservations=current.read()['reservations'],
                         request=request.read(),assessment=assessment.read() if assessment else None)
        else:
            try:
                context,updates=self.context_builder(current.read(),request.read(),
                                                     assessment.read() if assessment else None,now_ms)
            except Exception as exc:
                cause=type(exc.__cause__ or exc).__name__
                errors.append('CONTEXT_UNAVAILABLE:'+cause)
                context=dict(projection=portfolio,reservations=current.read()['reservations'],
                             request=request.read(),assessment=None,context_error=cause)
                # Evidence the builder already accepted is still committed with the round, so a port failure
                # cannot drop an adverse finding (IDEA-033 R16). No policy runs without its context.
                updates=getattr(exc,'updates',None) or {}
                context_ok=False
        snapshot=self.snapshot(current,now_ms,context)
        if assessment is not None and context_ok:
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
            plan=self.empty_plan(snapshot,'PLANNER_UNAVAILABLE')
        else:
            # An order the audit log cannot record is never committed or executed:
            # its round could not be closed truthfully afterwards.
            try:
                if type(plan.get('intents')) is not list:
                    raise ContractError('Planner intents must be a list')
                check_orders([dict(symbol=i.get('symbol'),side=i.get('side'),amount=i.get('amount'))
                              if type(i) is dict else i for i in plan['intents']])
            except ContractError:
                errors.append('PLAN_INVALID')
                plan=self.empty_plan(snapshot,'PLAN_INVALID')
        projection=current.read()['projection']
        projection.update(updates)
        if plan.get('risk_state') is not None:
            projection['risk_state']=plan['risk_state']  # persisted independent risk state (IDEA-031 AC-I03)
        # The policy saw `context`; its request and assessment are stored once, at the top level.
        policy_input=(dict(projection=context['projection'],reservations=context['reservations'],
                           includes=['request','assessment']) if self.context_builder is None else
                      dict(context={k:v for k,v in context.items() if k not in ('request',)},includes=['request']))
        record=dict(round_id=round_id,request=request.read(),assessment=assessment.read() if assessment else None,
                    proposal_id=proposal.proposal_id if proposal else None,plan=plan,errors=errors,
                    policy_input=policy_input,policy_state=snapshot.policy_state.record(),
                    policy_output=None if proposal is None else dict(targets=[t.record() for t in proposal.targets],
                        next_policy_state=proposal.next_policy_state.record(),valid_until=proposal.valid_until.isoformat()),
                    started_ms=started_ms,orders=[dict(symbol=i['symbol'],side=i['side'],amount=i['amount'])
                        for i in plan['intents']],swap_mappings=[])
        if now_ms!=started_ms:
            record['decision_ms']=now_ms  # absent in historical zero-duration fixture records
        if updates.get('evidence_decisions'):
            record['evidence_decisions']=updates['evidence_decisions']
        projection.setdefault('round_records',{})[round_id]=record
        commands=[dict(command_id=i['intent_id'],kind='EXECUTION_REQUEST',payload=i,round_id=round_id,
                       decision_id=i['decision_id'],expires_ms=i['expires_ms']) for i in plan['intents']]
        reservation_deltas=plan['reservation_deltas']
        try:
            self.audit_record(record,round_id,now_ms,'PREFLIGHT',current.read()['head'])
            # Leave space for later hashes/outcome metadata; this is a development
            # serialization budget, not an adopted trading parameter.
            if len(doc(record).payload)>4*1024*1024:
                raise ContractError('Round exceeds pre-execution audit budget')
        except ContractError:
            record['errors'].append('AUDIT_CONTENT_UNSUPPORTED')
            record['audit_fallback']=True
            # Nothing is placed, so the log lists no orders (kit K11: orders finally placed).
            record['orders']=[]
            commands=[]; reservation_deltas=[]
        record['execution_pending']=bool(commands)
        # Holdings remain byte-identical: the planner can only REQUEST reservations.
        try:
            receipt=self.store.commit(batch_for(current,'plan:'+round_id,dict(kind='ROUND_PLANNED',record=record),
                projection=projection,policy_state=proposal.next_policy_state.record() if proposal else None,
                reservation_deltas=reservation_deltas,jobs=plan['jobs'],commands=commands))
        except Conflict:
            # Rejection is itself a durable outcome, never a silent lost round.
            record['errors'].append('COMMIT_REJECTED')
            receipt=self.record_rejection(round_id,record)
            return receipt if defer_close else self.close(round_id,now_ms,'REJECTED')
        if not commands and not defer_close:
            return self.close(round_id,now_ms,'COMPLETE')
        return receipt

    @staticmethod
    def empty_plan(snapshot,reason):
        return dict(schema='PlanResult.v1',snapshot_id=snapshot.snapshot_id,reasons=[reason],
                    intents=[],reservation_deltas=[],jobs=[],proposed_state={})

    def record_rejection(self,round_id,record):
        """Persist an observed rejection; replay must not retry its rejected plan."""
        current=self.store.load(self.run_id)
        # A rejected plan places nothing, so its log lists no orders (kit K11).
        record=dict(record,execution_pending=False,orders=[])
        projection=current.read()['projection']
        projection.setdefault('round_records',{})[round_id]=record
        return self.store.commit(batch_for(current,'rejected:'+round_id,
            dict(kind='PLAN_REJECTED',record=record),projection=projection))

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
        # Only the execution owner can attest that ALL commands for a round are
        # terminal. Missing attestations keep its immutable audit record unsealed.
        terminal=transition.get('terminal_rounds',[])
        if type(terminal) is not list or any(type(r) is not str for r in terminal):
            raise ContractError('Invalid terminal round attestation')
        for round_id in terminal:
            record=change['projection'].get('round_records',{}).get(round_id)
            if record is None:
                raise ContractError('Terminal execution has no open round record')
            # A reducer that tracks final facts (larp/integration/settlement.py) lets the attestation be checked
            # independently: every planned intent must have reached a terminal final fact (IDEA-042 B3).
            if 'final_intents' in record and not ({i['intent_id'] for i in record['plan'].get('intents',[])}
                                                  <= set(record['final_intents'])):
                raise ContractError('Terminal attestation before every planned intent is final')
            record['execution_pending']=False
        return self.store.commit(batch_for(current,event_id,expected,
            projection=change['projection'],execution_state=transition['next_state'],
            reservation_deltas=change.get('reservation_deltas',[]),commands=transition.get('commands',[])))

    def audit_record(self,record,round_id,now_ms,status,head):
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
        return build_event(event_id=event_id_for(self.run_id,self.address,round_id,head,now_ms),round_id=round_id,version_id=self.version_id,
            decision_ids=decisions,address=self.address,timestamp_ms=now_ms,input_record=inputs,rationale=rationale,
            output=output,orders=record['orders'],swap_mappings=record['swap_mappings'])

    def close(self,round_id,now_ms,status):
        previous=self.store.receipt(self.run_id,'close:'+round_id)
        if previous:
            return previous
        current=self.store.load(self.run_id)
        record=current.read()['projection'].get('round_records',{}).get(round_id)
        close_event=dict(kind='ROUND_CLOSED',status=status,round_id=round_id)
        if record is None:
            request=dict(self.store.open_rounds(self.run_id))[round_id].read()
            close_event['request']=request
            record=dict(request=request,assessment=None,proposal_id=None,plan={},errors=['PROCESS_INTERRUPTED'],
                        started_ms=now_ms,orders=[],swap_mappings=[])
        elif record.get('execution_pending',bool(record['plan'].get('intents'))):
            raise Conflict('Round awaits terminal execution reconciliation')
        audit=self.audit_record(record,round_id,now_ms,status,current.read()['head'])
        projection=current.read()['projection']
        projection.get('round_records',{}).pop(round_id,None)
        projection.pop('closed_rounds',None)
        return self.store.commit(batch_for(current,'close:'+round_id,close_event,
                                           projection=projection,audit=[audit]))

    def recover(self,now_ms):
        # No attempts are released or re-signed here. Isaac reconciles commands.
        # One round that cannot close must not stop later rounds from closing.
        receipts=[]; failures=[]
        for round_id,_ in self.store.open_rounds(self.run_id):
            try:
                record=self.store.load(self.run_id).read()['projection'].get('round_records',{}).get(round_id)
                if record and record.get('execution_pending',bool(record['plan'].get('intents'))):
                    continue
                status=('REJECTED' if self.store.receipt(self.run_id,'rejected:'+round_id) else
                        'COMPLETE' if record else 'INTERRUPTED_UNRESOLVED')
                receipts.append(self.close(round_id,now_ms,status))
            except ContractError as exc:
                failures.append((round_id,type(exc).__name__))
        if failures:
            raise RecoveryIncomplete(receipts,failures)
        return receipts
