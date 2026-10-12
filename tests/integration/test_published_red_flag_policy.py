"""IDEA-043: actual published verifier directives reach policy and independent risk."""
from dataclasses import replace
from datetime import datetime, timezone
import unittest
from larp.contracts import Document, TargetKind
from larp.integration.contract import build_evidence_context, red_flag_predicates, context_hash as evidence_hash
from larp.integration.runtime import ContextBuilder, initial_projection
from larp.intelligence.agent import context_hash
from larp.intelligence.gate import accept, consume, initial_state
from larp.research.fixtures import snapshot, changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.schema import instant
from tests.intelligence.test_red_flags import Run
from larp.intelligence.scenarios import EXSEMI

class PublishedPredicatePolicy(unittest.TestCase):
    def producer_context(self, fixture, item, prior=None):
        run=Run(fixture); original_context=run.state['context']
        result=run.assess(fixture)
        _,sha=red_flag_predicates()
        s=snapshot(held={'NVDAB':2000},now=instant('2026-10-10T14:00:00Z'),profile_changes={
            'baseline':'EQUAL_WEIGHT','operating_name_weight':[1,5],'operating_gross_weight':[4,5],
            'regime_gross_weight':[4,5],'top_up_below_gross_weight':[3,4], 'red_flag_policy':'IDEA-035-B1',
            'falsifier_ids':['F-ITEM-4.02','F-ITEM-1.05'], 'red_flag_authority':{'set_sha256':sha,
            'enabled':['RF1-ITEM-4.02','RF2-ITEM-1.05']}})
        now_ms=int(s.observed_at.timestamp()*1000)
        # Consume promptly; only identity is rebound, evidence bytes remain the producer's.
        s=replace(s,observed_at=datetime.fromtimestamp(result['completed_ms']/1000,timezone.utc))
        now_ms=result['completed_ms']
        result.update(run_id=s.run_id,policy_profile_hash=s.policy_profile_hash)
        state=dict(initial_state(EXSEMI,s.policy_profile_hash),context=original_context,
                   context_hash=context_hash(original_context))
        decision,state=accept(state,Document.from_dict(result),profile_hash=s.policy_profile_hash,now_ms=now_ms)
        self.assertEqual(decision,'ACCEPT')
        record=build_evidence_context(consume(state,now_ms),state,run_id=s.run_id,token='NVDAB',
                                      underlying_id=EXSEMI,policy_profile_hash=s.policy_profile_hash)
        c=s.context.read()
        for m in c['markets']:
            m['observed_at']=m['available_at']=m['close_at']=s.observed_at.isoformat()
            if m['symbol']=='NVDAB': m['underlying_id']=EXSEMI
        s=changed(s,markets=c['markets'],assessments=[record])
        if prior is not None:
            s=replace(s,policy_state=replace(s.policy_state,data=Document.from_dict(prior)))
        return s,record,c,now_ms

    def test_real_rf1_producer_is_mandatory_even_without_policy(self):
        s,record,c,now_ms=self.producer_context('RF1-4.02-SUPPORTED','4.02')
        proposal=decide(s,s.policy_state)
        self.assertEqual(next(t for t in proposal.targets if t.symbol=='NVDAB').kind,TargetKind.EXIT)
        profile=s.context.read()['profile']
        builder=ContextBuilder(profile=profile,profile_hash=s.policy_profile_hash,run_id=s.run_id,
            issuers={},market=None,health=None,calendar=None,universe=s.universe)
        current={'run_id':s.run_id,'wallet_id':s.wallet_id,'projection':initial_projection(c['portfolio']),
                 'policy_state':s.policy_state.record(),'reservations':[]}
        reductions=builder._reductions([record],current,{'NVDAB':2000},c['markets'],now_ms)
        self.assertEqual(reductions,[{'symbol':'NVDAB','max_units':0,'reason':'CLASS_1_EXIT'}])
        s=with_quotes(changed(s,reduction_constraints=reductions))
        planned=plan(s,None).read()
        self.assertTrue(planned['intents'][0]['mandatory'])
        self.assertEqual(planned['intents'][0]['side'],'SELL')

    def test_resolved_critical_latch_does_not_survive_only_timed_adverse_evidence(self):
        s,record,_,_=self.producer_context('RF2-1.05-SUPPORTED','1.05')
        self.assertFalse(record['review_complete'])
        self.assertTrue(record['review_complete_excluding_timed_blocks'])
        flag=next(f['red_flag'] for f in record['falsifier_findings'] if f.get('red_flag'))
        key='NVDAB:RF2-ITEM-1.05:'+flag['accession']
        timed=dict(reason='CLASS_2_ENTRY_BLOCK',run_id=s.run_id,started_session=80,expires_session=85)
        prior=dict(blocked={'NVDAB':dict(reason='CLASS_1_EXIT',run_id=s.run_id,
                                        finding_ids=['old-critical'],timed_block=timed)},finding_sessions={key:80})
        s=replace(changed(s,session_index=82),policy_state=replace(s.policy_state,data=Document.from_dict(prior)))
        incomplete=dict(record,review_complete_excluding_timed_blocks=False)
        incomplete['context_hash']=evidence_hash(incomplete)
        kept=decide(changed(s,assessments=[incomplete]),s.policy_state)
        self.assertEqual(kept.next_policy_state.data.read()['blocked']['NVDAB']['reason'],'CLASS_1_EXIT')
        first=decide(s,s.policy_state)
        block=first.next_policy_state.data.read()['blocked']['NVDAB']
        self.assertEqual(block['reason'],'CLASS_2_ENTRY_BLOCK')
        self.assertEqual(block['expires_session'],85)
        s=replace(changed(s,session_index=85),policy_state=first.next_policy_state)
        self.assertNotIn('NVDAB',decide(s,s.policy_state).next_policy_state.data.read()['blocked'])
