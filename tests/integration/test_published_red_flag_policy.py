"""IDEA-043: actual published verifier directives reach policy and independent risk."""
from dataclasses import replace
from datetime import datetime, timezone
import unittest
from larp.contracts import Document, TargetKind
from larp.integration.contract import build_evidence_context, red_flag_predicates
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
    def test_real_rf1_producer_is_mandatory_even_without_policy(self):
        run=Run('RF1-4.02-SUPPORTED'); original_context=run.state['context']
        result=run.assess('RF1-4.02-SUPPORTED')
        _,sha=red_flag_predicates()
        s=snapshot(held={'NVDAB':2000},now=instant('2026-10-10T14:00:00Z'),profile_changes={
            'baseline':'EQUAL_WEIGHT','operating_name_weight':[1,5],'operating_gross_weight':[4,5],
            'regime_gross_weight':[4,5],'top_up_below_gross_weight':[3,4], 'red_flag_policy':'IDEA-035-B1',
            'falsifier_ids':['F-ITEM-4.02'], 'red_flag_authority':{'set_sha256':sha,'enabled':['RF1-ITEM-4.02']}})
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
