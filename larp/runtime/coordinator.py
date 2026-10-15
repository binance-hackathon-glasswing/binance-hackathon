"""Thin ordered coordinator. Financial and execution semantics are injected ports.

Only a reducer supplied by the owning component may change settled balances.
Fixture reducers live in fixtures.py and never qualify a live deployment.
"""

from datetime import datetime,timezone
import hashlib
import time

from larp.audit.protocol import build_event,check_orders,event_id_for
from larp.contracts import ContractError,DecisionSnapshot,Document,PolicyState,validate_proposal
from larp.storage.postgres import Conflict,IntegrityError,doc
from larp.runtime.schema import assessment_request,assessment_result


def batch_for(current,event_id,event,*,projection=None,policy_state=None,execution_state=None,
              reservation_deltas=(),jobs=(),commands=(),audit=(),reauthorize=()):
    c=current.read()
    batch=dict(schema='CommitBatch.v1',run_id=c['run_id'],wallet_id=c['wallet_id'],chain_id=c['chain_id'],
        event_id=event_id,expected_version=c['version'],owner_epoch=c['epoch'],event=event,
        projection=c['projection'] if projection is None else projection,
        policy_state=c['policy_state'] if policy_state is None else policy_state,
        execution_state=c['execution_state'] if execution_state is None else execution_state,
        reservation_deltas=list(reservation_deltas),jobs=list(jobs),commands=list(commands),
        audit=[a.read() if isinstance(a,Document) else a for a in audit])
    if reauthorize:
        batch['reauthorize']=list(reauthorize)  # absent otherwise, so existing batches keep their bytes
    return doc(batch)


def round_kind(intents):
    """GAS_TOP_UP when the plan is exactly one gas top-up intent (I7); TRADE otherwise. A top-up mixed with trades is
    refused: a gas top-up is its own round."""
    kinds=[i.get('kind','BSTOCK_TRADE') if type(i) is dict else None for i in intents]
    if 'GAS_TOP_UP' not in kinds:
        return 'TRADE'
    if kinds!=['GAS_TOP_UP']:
        raise ContractError('A gas top-up is its own round')
    return 'GAS_TOP_UP'


# Round errors that count towards a repeated-failure HALT (larp/runtime/supervision.py). A missing assessment is a
# normal hold, not a failure.
FAILURES=('PLANNER_UNAVAILABLE','PLAN_INVALID','COMMIT_REJECTED','POLICY_REJECTED','AUDIT_CONTENT_UNSUPPORTED')


def is_failure(errors):
    return any(e in FAILURES or e.startswith('CONTEXT_UNAVAILABLE') for e in errors)


def halt_reasons(projection):
    return sorted((projection.get('halt') or {}).get('reasons',{}))


def record_round_health(projection,errors,decision_ms,counted=True):
    """Consecutive failure/success counts and the last decision time, journaled with each round (DR-13).

    `counted=False` for a round blocked without exercising policy and planner (CLOCK, DELIVERY_DEADLINE or
    VERSION_NOT_REGISTERED): it says nothing about whether the planner works, so the counts stay as they are."""
    health=dict(projection.get('round_health') or {'failures':0,'successes':0})
    if counted:
        health=({'failures':health['failures']+1,'successes':0} if is_failure(errors) else
                {'failures':0,'successes':health['successes']+1})
    projection['round_health']=health
    projection['last_decision_ms']=max(decision_ms,projection.get('last_decision_ms',decision_ms))


GAS_TOP_UP_COT='Gas top-up round: USDT -> BNB swap to keep the BNB floor for transaction fees (B11); no trading decision.'


def round_cot(assessment,kind='TRADE'):
    """The round's chain of thought (Q-16, F-102, F-106 (a)): the provider's reasoning summaries in order when a model
    ran; otherwise an explicit statement that no model was called, with the deterministic path."""
    model_io=(assessment or {}).get('model_io')
    steps=model_io.get('steps') if type(model_io) is dict and type(model_io.get('steps')) is list else []
    summaries=[c for c in (model_io.get('cot') or []) if type(c) is str and c.strip()] if type(model_io) is dict else []
    if assessment is None:
        cot='No model call this round. Assessment unavailable; deterministic runtime record, no model reasoning is claimed.'
    elif summaries:
        cot=summaries
    elif any(type(s) is dict and 'response' in s for s in steps):
        cot='Model called; the provider returned no reasoning summary. Assessment rationale: '+assessment['rationale']
    else:
        cot='No model call this round. Deterministic assessment: '+assessment['rationale']
    if kind=='GAS_TOP_UP':
        return [GAS_TOP_UP_COT]+cot if type(cot) is list else GAS_TOP_UP_COT+' '+cot
    return cot


class _Halted(Exception):
    pass


class RecoveryIncomplete(ContractError):
    """Some rounds could not close; every other closable round was closed."""
    def __init__(self,receipts,failures):
        super().__init__('Rounds not closed: '+', '.join(f'{r} ({e})' for r,e in failures))
        self.receipts,self.failures=receipts,failures


class Coordinator:
    def __init__(self,store,assessor,policy,planner,*,execution,run_id,version_id,profile_hash,address,
                 context_builder=None,initial_policy_state=None,clock_ms=None,test_rounds=False,require_version=False):
        self.store,self.assessor,self.policy,self.planner=store,assessor,policy,planner
        self.run_id,self.version_id,self.profile_hash,self.address=run_id,version_id,profile_hash,address
        self.execution=execution
        self.clock=clock_ms if clock_ms is not None else lambda: time.time_ns()//1_000_000
        # Optional versioned adapter (larp/integration/runtime.py, IDEA-031): builds the policy context from the
        # journaled projection, the request and the assessment, and returns projection updates (evidence state)
        # committed atomically with the round. Without it the original fixture context is used.
        self.context_builder,self.initial_policy_state=context_builder,initial_policy_state
        # Development and rehearsal rounds are marked in every log the way the kit marks examples (IDEA-042 L5).
        self.test_rounds=test_rounds
        # Live and rehearsal coordinators commit no execution command until this build's version event is in the
        # journal (register_version; never-do #5, F-60/F-61; IDEA-042 R5).
        self.require_version=require_version

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
                   if k not in ('round_records','closed_rounds','observations','round_health','last_decision_ms','halt',
                                'registered_version')}
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
        halted=halt_reasons(current.read()['projection'])
        if halted:
            # HALT (larp/runtime/supervision.py): no new risk and no signing; the round still runs and is logged.
            errors.append('HALTED:'+','.join(halted))
        registered=(current.read()['projection'].get('registered_version') or {}).get('build_id')
        unregistered=self.require_version and registered!=self.version_id
        if unregistered:
            errors.append('VERSION_NOT_REGISTERED')
        blocked=bool(halted) or unregistered
        # A HALT for repeated failures alone probes policy and planner, so only a round that really works can clear
        # it (IDEA-042 V1). The probe's plan is discarded below: nothing is placed, reserved or advanced.
        probe=halted==['REPEATED_FAILURES'] and not unregistered
        if assessment is not None and context_ok and (not blocked or probe):
            try:
                proposal=self.policy.decide(snapshot,snapshot.policy_state)
                validate_proposal(snapshot,proposal,now=datetime.fromtimestamp(now_ms/1000,timezone.utc))
            except Exception:
                errors.append('POLICY_REJECTED'); proposal=None
        # Mandatory risk is called even when there is no policy output (unless blocked: nothing may be signed).
        try:
            if blocked and not probe:
                raise _Halted()
            plan=self.planner.plan(snapshot,proposal).read()
            if plan['schema']!='PlanResult.v1' or plan['snapshot_id']!=snapshot.snapshot_id:
                raise ContractError('Mismatched planner result')
        except _Halted:
            plan=self.empty_plan(snapshot,'HALTED' if halted else 'VERSION_NOT_REGISTERED')
        except Exception:
            errors.append('PLANNER_UNAVAILABLE')
            plan=self.empty_plan(snapshot,'PLANNER_UNAVAILABLE')
        else:
            # An order the audit log cannot record is never committed or executed:
            # its round could not be closed truthfully afterwards.
            try:
                if type(plan.get('intents')) is not list:
                    raise ContractError('Planner intents must be a list')
                kind=round_kind(plan['intents'])
                check_orders([dict(symbol=i.get('symbol'),side=i.get('side'),amount=i.get('amount'))
                              if type(i) is dict else i for i in plan['intents']],kind)
            except ContractError:
                errors.append('PLAN_INVALID')
                plan=self.empty_plan(snapshot,'PLAN_INVALID')
            else:
                if probe:
                    plan=self.empty_plan(snapshot,'HALTED')
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
        if plan['intents'] and round_kind(plan['intents'])=='GAS_TOP_UP':
            record['round_kind']='GAS_TOP_UP'  # absent for trade rounds, so their records keep their bytes
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
        record_round_health(projection,record['errors'],now_ms,counted=not blocked or probe)
        # Holdings remain byte-identical: the planner can only REQUEST reservations.
        try:
            receipt=self.store.commit(batch_for(current,'plan:'+round_id,dict(kind='ROUND_PLANNED',record=record),
                projection=projection,
                policy_state=proposal.next_policy_state.record() if proposal and not blocked else None,
                reservation_deltas=reservation_deltas,jobs=plan['jobs'],commands=commands))
        except Conflict:
            # Rejection is itself a durable outcome, never a silent lost round.
            record['errors'].append('COMMIT_REJECTED')
            receipt=self.record_rejection(round_id,record,updates)
            return receipt if defer_close else self.close(round_id,now_ms,'REJECTED')
        if not commands and not defer_close:
            return self.close(round_id,now_ms,'COMPLETE')
        return receipt

    @staticmethod
    def empty_plan(snapshot,reason):
        return dict(schema='PlanResult.v1',snapshot_id=snapshot.snapshot_id,reasons=[reason],
                    intents=[],reservation_deltas=[],jobs=[],proposed_state={})

    def record_rejection(self,round_id,record,updates=None):
        """Persist an observed rejection; replay must not retry its rejected plan.

        `updates` are the facts the context builder accepted this round (evidence state, adverse latches, versions).
        They are facts about the world, not part of the rejected plan, so they are committed with the rejection
        exactly as an accepted round would commit them, and journaled for replay (IDEA-049 D-FND-020, #51)."""
        current=self.store.load(self.run_id)
        # A rejected plan places nothing, so its log lists no orders (kit K11).
        record=dict(record,execution_pending=False,orders=[])
        projection=current.read()['projection']
        projection.update(updates or {})
        projection.setdefault('round_records',{})[round_id]=record
        record_round_health(projection,record['errors'],record.get('decision_ms',record['started_ms']))
        event=dict(kind='PLAN_REJECTED',record=record)
        if updates:
            event['updates']=updates  # absent otherwise, so earlier rejections keep their bytes
        return self.store.commit(batch_for(current,'rejected:'+round_id,event,projection=projection))

    def register_version(self,manifest,now_ms):
        """Commit the VERSION_REGISTERED event for this build before anything trades (F-60/F-61, never-do #5).

        `manifest` is the verified ReleaseManifest.v1 Document of the running build (larp/runtime/preflight.py)."""
        m=manifest.read()
        if m.get('schema')!='ReleaseManifest.v1' or m.get('build_id')!=self.version_id:
            raise ContractError('Version event needs the manifest of the running build')
        register=m.get('release_register') or {}
        if not register.get('services_sha256') or not register.get('deviations_sha256'):
            raise ContractError('Version event needs the manifested services list and deviations register')
        version=dict(build_id=m['build_id'],manifest_sha256=hashlib.sha256(manifest.payload).hexdigest(),
                     repository=m.get('repository'),services_sha256=register['services_sha256'],
                     deviations_sha256=register['deviations_sha256'],at_ms=now_ms)
        current=self.store.load(self.run_id)
        projection=current.read()['projection']
        projection['registered_version']=version
        return self.store.commit(batch_for(current,f"version:{m['build_id']}:{now_ms}",
                                           dict(kind='VERSION_REGISTERED',version=version),projection=projection))

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
        """One ai-seeds round log (interface I5, IDEA-042 item 3): input, cot, output and the orders committed."""
        assessment=record['assessment']
        kind=record.get('round_kind','TRADE')
        rationale=round_cot(assessment,kind)
        decisions=sorted({m['decision_id'] for m in record['swap_mappings']} |
                         {i['decision_id'] for i in record['plan'].get('intents',[])})
        inputs=dict(version_id=self.version_id,round_id=round_id,decision_ids=decisions,request=record['request'],
                    assessment=assessment,policy_input=record.get('policy_input'),policy_state=record.get('policy_state'))
        output=dict(status=status,errors=record['errors'],plan=record['plan'],proposal_id=record['proposal_id'],
                    policy_output=record.get('policy_output'))
        if record.get('aborted'):
            output['aborted']=record['aborted']  # committed orders that never reached the chain, with the reason
        if record.get('audit_fallback'):
            inputs=dict(version_id=self.version_id,round_id=round_id,
                        local_record_hash=doc(record).digest('larp.round.v1'),
                        omitted_content='Original complete I/O retained in the durable ROUND_PLANNED record; serialization budget exceeded.')
            output=dict(status='AUDIT_CONTENT_UNSUPPORTED',errors=record['errors'],trading_blocked=True)
            rationale='Deterministic serialization failure; original reasoning retained locally, not fabricated or truncated.'
        if self.test_rounds:
            inputs['example']=True
        return build_event(event_id=event_id_for(self.run_id,self.address,round_id,head,now_ms),round_id=round_id,version_id=self.version_id,
            decision_ids=decisions,address=self.address,timestamp_ms=now_ms,input_record=inputs,rationale=rationale,
            output=output,orders=record['orders'],swap_mappings=record['swap_mappings'],round_kind=kind)

    @staticmethod
    def disposed(record):
        """True when every planned intent of the round is final or has its swap broadcast: the round's orders, and
        every `tx_hash` they will ever carry, are then known (kit: tx_hash once broadcast, whatever the outcome)."""
        final=set(record.get('final_intents',[]))
        intents=record['plan'].get('intents',[])
        return bool(intents) and all(i['intent_id'] in final or record['orders'][n].get('tx_hash') is not None
                                     for n,i in enumerate(intents))

    def log_round(self,round_id,now_ms):
        """Commit the round's one ai-seeds log as soon as its orders are disposed, before receipts are final
        (IDEA-049 D-FND-002, #28). The round stays open in the projection until every intent is final, so later
        receipt facts still settle into the journal; `close` then writes no second log."""
        previous=self.store.receipt(self.run_id,'logged:'+round_id)
        if previous:
            return previous
        current=self.store.load(self.run_id)
        projection=current.read()['projection']
        record=projection.get('round_records',{}).get(round_id)
        if record is None or not record.get('execution_pending') or record.get('logged') or not self.disposed(record):
            raise Conflict('Round is not awaiting a log of its disposed orders')
        audit=self.audit_record(record,round_id,now_ms,'BROADCAST_PENDING_FINALITY',current.read()['head'])
        record['logged']=dict(event_id=audit.read()['event_id'],at_ms=now_ms)
        return self.store.commit(batch_for(current,'logged:'+round_id,
                                           dict(kind='ROUND_LOGGED',round_id=round_id,at_ms=now_ms),
                                           projection=projection,audit=[audit]))

    def close(self,round_id,now_ms,status):
        previous=self.store.receipt(self.run_id,'close:'+round_id)
        if previous:
            return previous
        current=self.store.load(self.run_id)
        record=current.read()['projection'].get('round_records',{}).get(round_id)
        if record is not None and record.get('logged'):
            # Its log was committed when its orders were disposed (log_round); closing only ends the round.
            if record.get('execution_pending'):
                raise Conflict('Round awaits terminal execution reconciliation')
            projection=current.read()['projection']
            projection['round_records'].pop(round_id)
            projection.pop('closed_rounds',None)
            return self.store.commit(batch_for(current,'close:'+round_id,
                dict(kind='ROUND_CLOSED',status=status,round_id=round_id,logged_event_id=record['logged']['event_id']),
                projection=projection))
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
        # open_rounds includes early-logged projection records until close removes them (IDEA-049 D-RV-01).
        if failures:
            raise RecoveryIncomplete(receipts,failures)
        return receipts
