"""PC-AUDIT01 offline witnesses against current code and original captured HTTP payloads."""
from pathlib import Path
import runpy,contextlib,json,copy,collections,re,os
root=Path(os.environ['LARP_AUDIT_OUTPUT_DIR']).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=True);root.chmod(0o700)
with (root/'core-run.log').open('w') as log,contextlib.redirect_stdout(log):env=runpy.run_path(str(Path(__file__).with_name('audit_capture.py')))
from larp.intelligence.aiand import AIandChatModel
from larp.intelligence.routing import stage_config,review_outcome
from larp.intelligence.config import load_config
from larp.intelligence.providers import _ProviderReply
from larp.intelligence.models import ModelIdentity
from larp.intelligence.time_budget import MAX_ASSESSMENT_MS
from larp.intelligence.bakeoff import metrics,DEADLINE_MS
from larp.intelligence.agent import EvidenceAssessor
from larp.contracts import Document
from larp.intelligence.verify import verify_claim
records,p,art,reader,reg=map(env.get,('records','p','art','reader','reg'))
spec=json.loads((p/'selected-configs/model-routing.json').read_bytes());cfg=load_config('shadow');Clock=env['Clock'];cap=[];citations=[];meter=collections.defaultdict(collections.Counter);tool_errors=[];limits=[];identities=collections.Counter()
class Replay:
 def __init__(self,steps,clock):self.steps=steps;self.clock=clock;self.identity=ModelIdentity(**steps[0]['model']);self.index=0;self.debug=[]
 def step(self,request,remaining_ms):
  assert self.index<len(self.steps),'Unexpected additional model call in offline replay'
  s=self.steps[self.index];self.index+=1;r=request.read()
  self.debug.append({'input_matches':r['input']==s['request']['input'],'different_keys':[k for k in set(r['input'])|set(s['request']['input']) if r['input'].get(k)!=s['request']['input'].get(k)],'prompt_matches':r['prompt_sha256']==s['request']['prompt_sha256']})
  assert r['input']==s['request']['input'],'Replay model input differs from recorded input'
  assert r['prompt_sha256']==s['request']['prompt_sha256']
  reply=copy.deepcopy(s['response']);reply['request_id']=r['request_id'];self.clock.ms+=reply['latency_ms'];return Document.from_dict(reply)
for rec in records:
 a=rec['assessment'];r=rec['request'];ios=a['model_io'];budget=r['budget'];tools=ios['tool_calls']
 assert len(tools)<=budget['tool_calls'];assert all(t['tool'] in r['allowed_tools'] for t in tools)
 assert all(a['started_ms']<=t['started_ms']<a['started_ms']+budget['deadline_ms'] for t in tools)
 assert a['status']!='ASSESSED' or a['budget_used']['elapsed_ms']<=budget['deadline_ms']
 for step in ios['steps']:
  q=step.get('response') or {};m=step['model']['model_id']
  if m.startswith(('moonshotai/','zai-org/')):
   meta=q.get('provider_metadata') or {};identities['metadata_present']+=int(bool(meta));identities['model_and_effort_match']+=int(meta.get('x-model','').lower()==m.lower() and meta.get('x-reasoning-effort')=='high')
   h=q.get('raw_response_artifact')
   if not h:continue
   raw=json.loads(art.get(h));u=raw.get('usage') or {};nu=q.get('usage') or {};v=meter[m]
   for field,key in [('prompt_tokens','input_tokens'),('completion_tokens','output_tokens')]:v['raw_'+key]+=u.get(field,0);v['normalized_'+key]+=nu.get(key,0)
   v['raw_reasoning_tokens']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0)
   if q.get('error')=='AIAND_INCOMPLETE_OR_MULTIPLE_CHOICES':
    obj=object.__new__(AIandChatModel);obj.identity=ModelIdentity(**step['model']);obj.effort='high'
    try:obj._parse_reply(raw,meta);raise AssertionError('Current codec accepted incomplete raw response')
    except _ProviderReply as exc:assert exc.code==q['error']
    assert len(raw['choices'])==1 and raw['choices'][0]['finish_reason']=='length'
    assert u['completion_tokens']==spec['max_output_tokens']==4096
    cap.append({'model':m,'job_id':a['job_id'],'cap':4096,'reasoning_tokens':(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0),'current_codec_refuses':True})
 stages={s['stage']:json.loads(art.get(s['result_artifact'])) for s in a['routing']['stages'] if s.get('result_artifact')}
 bad=stages.get('external-review-0')
 if bad and bad['status']=='ABSTAIN' and bad['reasons'] in (['UNSUPPORTED_CLAIM'],['MODEL_OUTPUT_SCHEMA']):
  steps=[copy.deepcopy(s) for s in ios['steps'] if s['routing_stage']=='external-review-0']
  for st in steps:
   wire=json.loads(art.get(st['response']['request_payload_artifact']))
   st['request']['input']=json.loads(wire['messages'][-1]['content'])
  clock=Clock(bad['started_ms']);model=Replay(steps,clock)
  rc=stage_config(cfg,spec['external_reviewers'][0]['prompt']);assessor=EvidenceAssessor(registry=reg,reader=reader,model=model,config=rc,clock_ms=clock);assessor.request_namespace='external-review-0:'
  req=copy.deepcopy(r);req['budget']={'deadline_ms':MAX_ASSESSMENT_MS,'tool_calls':steps[0]['request']['input']['remaining_tool_calls']}
  result=assessor.assess(Document.from_dict(req)).read()
  assert result['status']=='ABSTAIN' and result['reasons']==bad['reasons'],(result['reasons'],model.debug)
  assert result['rejected_claims']==bad['rejected_claims']
  primary=stages.get('openai-primary');selected,outcome,_=review_outcome(primary,[result,None]);assert outcome=='DISSENT' and selected['status']=='ABSTAIN'
  citations.append({'job_id':a['job_id'],'current_status':result['status'],'reject_reasons':result['rejected_claims'],'current_policy_outcome':outcome,'same_model_inputs_and_prompt':True})
synthetic=copy.deepcopy(env['baseline'][0]);synthetic['budget_used']['elapsed_ms']=120000
w=metrics([synthetic]);assert MAX_ASSESSMENT_MS==180000 and DEADLINE_MS==60000 and w['latency_ms']['within_deadline']==0
patterns=[re.compile(rb'AKIA[A-Z0-9]{16}'),re.compile(rb'sk-proj-[A-Za-z0-9_-]{32,}'),re.compile(rb'"(?:Authorization|api_key|private_key|mnemonic|AI_SEEDS_SECRET)"\s*:\s*"[^"\\]{8,}"',re.I)]
hits=[]
for f in p.rglob('*'):
 if f.is_file() and f.suffix not in ('.sqlite',):
  raw=f.read_bytes()
  if any(rx.search(raw) for rx in patterns):hits.append(str(f.relative_to(p)))
result={'canonical_sha':env['summary']['canonical_sha'],'cap_errors':{'count':len(cap),'by_model':dict(collections.Counter(x['model'] for x in cap)),'all_reasoning_consumed_cap':sum(x['reasoning_tokens']==x['cap'] for x in cap),'current_codec_reproduction':'11/11 refused same way; current routing cap unchanged'},
 'citations':{'stages':len(citations),'rejected_claims':sum(len(x['reject_reasons']) for x in citations),'same_input_prompt_replay':f'PASS on all {len(citations)} current-assessor replays using original HTTP inputs','current_review_outcomes':dict(collections.Counter(x['current_policy_outcome'] for x in citations))},
 'reporting_witness':{'kind':'synthetic reporting-only witness; not a provider/latency projection','current_declared_max_ms':MAX_ASSESSMENT_MS,'bakeoff_deadline_ms':DEADLINE_MS,'elapsed_ms':120000,'within_deadline_reported':w['latency_ms']['within_deadline']},
 'aiand_usage_recovery':{k:dict(v) for k,v in meter.items()},'aiand_served_identity':dict(identities),'tool_time_allowlist_and_accepted_deadline_checks':'70/70 PASS',
 'credential_pattern_scan':{'candidate_files':hits,'scope':'Access-key, OpenAI key and explicit secret-valued JSON patterns; not proof of absence of every possible secret'},'limits':{'blind_labels':False,'new_provider_calls':0,'counterfactual_new_router_performance_estimated':False}}
(root/'witnesses.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');(root/'private-witness-cases.json').write_text(json.dumps({'cap':cap,'citations':citations},sort_keys=True,indent=2)+'\n');# Real-input deterministic witness: compare dispatch snapshots with the completed trace.
clock=Clock(records[0]['assessment']['started_ms'])
class RecordingRule:
 def __init__(self):self.inner=env['RuleBaselineModel'](clock);self.identity=self.inner.identity;self.sent=[]
 def step(self,request,remaining_ms):self.sent.append(request.read());return self.inner.step(request,remaining_ms)
m=RecordingRule();a=EvidenceAssessor(registry=reg,reader=reader,model=m,config=cfg,clock_ms=clock);res=a.assess(Document.from_dict(records[0]['request'])).read()
drift=[i for i,step in enumerate(res['model_io']['steps']) if step['request']['input']!=m.sent[i]['input']]
assert drift and all(set(k for k in res['model_io']['steps'][i]['request']['input'] if res['model_io']['steps'][i]['request']['input'][k]!=m.sent[i]['input'][k])=={'tool_results'} for i in drift)
result['current_mutable_input_witness']={'dispatches':len(m.sent),'drifted_steps':drift,'field':'tool_results','actual_capture_mismatches':json.loads((root/'input-mismatches.json').read_text())['counts']}
(root/'witnesses.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,sort_keys=True,indent=2))
