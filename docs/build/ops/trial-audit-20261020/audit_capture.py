"""PC-AUDIT01 read-only capture checks and offline rule baseline; never calls a hosted model."""
from pathlib import Path
import json,base64,collections,hashlib,sqlite3,sys,subprocess,statistics,copy,os,re
sys.path.insert(0,str(Path.cwd()))
from larp.contracts import Document
from larp.intelligence.config import load_config,load_registry
from larp.intelligence.agent import EvidenceAssessor,issuer_names
from larp.intelligence.models import RuleBaselineModel,parse_output
from larp.intelligence.tools import PortEvidenceReader
from larp.intelligence.verify import verify_claim,fact_as_claim
from larp.intelligence.text import text_from_saved
from larp.intelligence.bakeoff import metrics,_quantile
from larp.strategy.schema import market_view
from datetime import datetime,timezone
p=Path(os.environ['LARP_AUDIT_DATA_DIR']).resolve();root=p.parent
out=Path(os.environ['LARP_AUDIT_OUTPUT_DIR']).resolve();out.mkdir(mode=0o700,parents=True,exist_ok=True);out.chmod(0o700)
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
decode=lambda x:base64.b64decode(x['bytes']) if isinstance(x,dict) and set(x)=={'bytes'} else x
b=json.loads((p/'postgres-backup.json').read_bytes());assert sha(canon(b['tables']))==b['sha256']
t={k:[dict(zip(v['columns'],map(decode,row))) for row in v['rows']] for k,v in b['tables'].items()}
for line in (p/'SHA256SUMS').read_text().splitlines():
 h,n=line.split('  ',1);assert (p/n).resolve().is_relative_to(p) and not (p/n).is_symlink();assert sha((p/n).read_bytes())==h,n
run=t['runs'][0];head='0'*64;records=[];batches=[];expected_outbox={key:{} for key in ('audit','commands','jobs')}
for i,row in enumerate(sorted(t['events'],key=lambda r:r['sequence']),1):
 z=json.loads(row['batch']);assert sha(row['batch'])==row['batch_hash']
 assert sha(canon(z['event']))==row['event_hash']
 assert row['previous_hash']==head and row['sequence']==i
 head=sha(bytes.fromhex(head)+bytes.fromhex(row['batch_hash']));assert row['head']==head
 assert (z['run_id'],z['wallet_id'],z['chain_id'])==(run['run_id'],run['wallet_id'],run['chain_id'])
 batches.append(z)
 for key,ident in [('audit','event_id'),('commands','command_id'),('jobs','job_id')]:
  for item in z.get(key,[]):expected_outbox[key][item[ident]]=canon(item)
 r=(z.get('event') or {}).get('record') or {}
 if r.get('assessment'):records.append(r)
assert head==run['head'] and len(batches)==run['version']
for key in ('projection','policy_state','execution_state'):assert canon(batches[-1][key])==run[key]
for key,table,ident,value in [('audit','audit_events','event_id','document'),('commands','commands','command_id','payload'),('jobs','jobs','job_id','document')]:
 assert expected_outbox[key]=={r[ident]:r[value] for r in t[table]}
chunks={(a['event_id'],i):c.encode() for a in t['audit_events'] for i,c in enumerate(json.loads(a['document'])['chunks'])}
assert chunks=={(r['event_id'],r['chunk_index']):r['body'] for r in t['audit_chunks']}
assert all(r['status']=='ACK' for r in t['audit_chunks'])
assert all(r['status']=='CLOSED' for r in t['rounds'])
assert not any(t[k] for k in ('commands','reservations','execution_records','execution_journal','execution_signatures','signing_attempts','signing_requests','signing_refusals','execution_observations'))
# Pure local read ports: original immutable evidence plus an in-memory tool artifact sink.
db=sqlite3.connect('file:'+str(p/'evidence.sqlite')+'?mode=ro',uri=True)
evidence=[json.loads(x[0]) for x in db.execute('SELECT doc FROM erecords')];byid={x['record_id']:x for x in evidence}
class Store:
 def records(self,issuer):return tuple(Document.from_dict(x) for x in evidence if x['issuer_id']==issuer)
class Artifacts:
 def __init__(self):self.new={}
 def get(self,h):
  assert isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h)
  if h in self.new:return self.new[h]
  for base in ('source-artifacts','market/model'):
   q=p/base/h[:2]/h
   if q.is_file():
    raw=q.read_bytes();assert sha(raw)==h;return raw
  return None
 def put(self,raw):h=sha(raw);self.new[h]=raw;return h
art=Artifacts();reader=PortEvidenceReader(Store(),art);reg=load_registry();cfg=load_config('shadow')
class Clock:
 def __init__(self,ms):self.ms=ms
 def __call__(self):return self.ms
# Recover original config bytes without changing the snapshot or running old provider code.
oldbase=out/'historical-config';oldbase.mkdir(exist_ok=True)
for name in ('intelligence.shadow.v1.json','prompts/assessor.v2.txt'):
 q=oldbase/name;q.parent.mkdir(exist_ok=True,parents=True)
 q.write_bytes(subprocess.check_output(['git','show','ea25b52:config/intelligence/'+name]))
oldcfg=load_config('shadow',oldbase)
canonical=subprocess.check_output(['git','rev-parse','origin/codex/system-testing-20261012'],text=True).strip()
for name in ('agent.py','models.py','providers.py','routing.py','aiand.py','bakeoff.py','verify.py','tools.py','facts.py'):
 file='larp/intelligence/'+name
 assert Path(file).read_bytes()==subprocess.check_output(['git','show',canonical+':'+file]),'Working code differs from canonical: '+file
summary={'audit_id':'PC-AUDIT01','canonical_sha':subprocess.check_output(['git','rev-parse','origin/codex/system-testing-20261012'],text=True).strip(),
 'data_sha256':sha((root/'final.tar.gz').read_bytes()),'integrity':{'journal_events_verified':len(batches),'terminal_projection_matches':True,'outboxes_and_chunk_bytes_match':True,'audit_ACKs':len(chunks),'closed_rounds':len(t['rounds']),'execution_signing_commands':0},'historical_config_sha256':oldcfg.config_sha256}
case=[];stage_results=collections.defaultdict(list);artifact_refs=set();missing=[];claim_checks=collections.Counter();provider=collections.defaultdict(lambda:collections.Counter());baseline=[];market_counts=collections.Counter();rejects=collections.Counter();policy=collections.Counter();source_refs=collections.Counter();stage_counter=[]
def refs(v):
 if isinstance(v,dict):
  for k,x in v.items():
   if (k.endswith('_artifact') or k=='artifact') and isinstance(x,str) and len(x)==64:artifact_refs.add(x)
   refs(x)
 elif isinstance(v,list):
  for x in v:refs(x)
for rec in records:
 a=rec['assessment'];r=rec['request'];assert a['cutoff_ms']==r['cutoff_ms'];assert a['job_id']==r['job_id'];assert a['context_hash']==r['context_hash']
 assert a['completed_ms']<=rec['decision_ms'];assert a['started_ms']>=r['cutoff_ms']
 for ref in r['evidence_refs']:
  source=byid[ref['record_id']];assert source['available_ms']<=r['cutoff_ms'] and source['original_ms']<=r['cutoff_ms'];assert ref['content_hash']==source['content_hash'];source_refs[ref['record_id']]+=1
 for claim in a['claims']:
  texts={d['text_sha256']:text_from_saved(art.get(d['text_sha256'])) for e in evidence for d in e['documents'] if d.get('text_sha256')}
  entry=reg.by_issuer(a['issuer_id']);fact,reason=verify_claim(fact_as_claim(claim),texts,byid,issuer_names=issuer_names(entry))
  claim_checks[reason or 'PASS']+=1
 refs(a)
 for st in a['routing']['stages']:
  h=st.get('result_artifact')
  if h:
   raw=art.get(h)
   if raw is None:missing.append(h);continue
   z=json.loads(raw);assert z['result_id']==st['result_id'];assert z['status']==st['status'];stage_results[st['stage']].append(z)
 for st in a['model_io']['steps']:
  m=st['model']['model_id'];resp=st.get('response') or {};s=provider[m];s['recorded_steps']+=1;s[resp.get('status','NO_RESPONSE')]+=1
  if resp.get('served_model'):s['served_model_match']+=int(resp['served_model']==m)
  u=resp.get('usage') or {};s['input_tokens']+=u.get('input_tokens',0);s['output_tokens']+=u.get('output_tokens',0)
  if resp.get('status')=='OK':
   try:parse_output(resp['output']);s['schema_valid']+=1
   except Exception:s['schema_invalid']+=1
  if resp.get('cost',{}).get('amount_micro_usd') is not None:s['known_cost_micro_usd']+=resp['cost']['amount_micro_usd']
 ctx=rec['policy_input']['context'];prof=ctx['profile'];mv=market_view(ctx['markets'],tuple(x['symbol'] for x in ctx['markets']),datetime.fromtimestamp(rec['decision_ms']/1000,timezone.utc),prof)
 market_counts['rounds']+=1;market_counts['zero_usable_rows']+=int(not any(mv.values()));market_counts['usable_rows']+=sum(v is not None for v in mv.values());market_counts['basis_unverified_rows']+=sum(not v.get('basis_verified') for v in ctx['markets'])
 for x in rec['plan']['next_policy_state']['data'].get('evidence_rejections',[]):rejects[x['reason']]+=1
 for x in rec['policy_output']['targets']:policy[x['reason']]+=1
 clock=Clock(a['started_ms']);assessor=EvidenceAssessor(registry=reg,reader=reader,model=RuleBaselineModel(clock),config=oldcfg,clock_ms=clock)
 z=assessor.assess(Document.from_dict(r)).read();baseline.append(z)
 case.append({'job_id':a['job_id'],'issuer_id':a['issuer_id'],'source_record_ids':[x['record_id'] for x in r['evidence_refs']],'status':a['status'],'claims':len(a['claims']),'confirmed_claims':sum(x.get('model_confirmed',False) for x in a['claims']),'claim_metrics':[x['metric'] for x in a['claims']],
  'baseline_status':z['status'],'baseline_claims':len(z['claims']),'baseline_metrics':[x['metric'] for x in z['claims']], 'baseline_agreement':{f['type'] for f in z['findings']}=={f['type'] for f in a['findings']},
  'baseline_claim_metric_agreement':{x['metric'] for x in z['claims']}=={x['metric'] for x in a['claims']},'elapsed_ms':a['budget_used']['elapsed_ms'],'decision_age_ms':rec['decision_ms']-r['cutoff_ms'],'coverage_complete':a.get('coverage',{}).get('complete'),'thesis':(a.get('proposed_thesis') or {}).get('status'),
  'review_reasons':a['routing']['reasons'],'declared_budget':r['budget'],'model_calls':a['model_io']['requests_started'],'tools':a['model_io']['tool_calls']})
for h in artifact_refs:
 if art.get(h) is None:missing.append(h)
summary['artifact_refs']={'unique':len(artifact_refs),'missing':sorted(set(missing))};summary['claims_reverified']=dict(claim_checks)
summary['providers']={m:dict(v) for m,v in provider.items()}
summary['stages']={k:metrics(v) for k,v in stage_results.items()}
summary['by_issuer']={i:{'jobs':len([x for x in case if x['issuer_id']==i]),'statuses':dict(collections.Counter(x['status'] for x in case if x['issuer_id']==i)),'empty_claims':sum(x['claims']==0 for x in case if x['issuer_id']==i),'baseline_statuses':dict(collections.Counter(x['baseline_status'] for x in case if x['issuer_id']==i))} for i in sorted({x['issuer_id'] for x in case})}
summary['baseline']={'jobs':len(baseline),'status_counts':dict(collections.Counter(x['status'] for x in baseline)),'finding_set_agreement_jobs':sum(x['baseline_agreement'] for x in case),'claim_metric_agreement_jobs':sum(x['baseline_claim_metric_agreement'] for x in case),'independent_labels':False}
summary['population']={'jobs':len(case),'unique_source_reference_sets':len({tuple(sorted(x['source_record_ids'])) for x in case}),'referenced_records':dict(source_refs),'accepted_claim_metric_counts':dict(collections.Counter(m for x in case for m in x['claim_metrics'])),'theses':dict(collections.Counter(x['thesis'] or 'NONE' for x in case)),
 'review_reasons':dict(collections.Counter(r for x in case for r in x['review_reasons'])),'all_hold_targets':dict(policy),'market_usability':dict(market_counts),'evidence_rejections':dict(rejects)}
summary['latency']={'all_jobs':{f'p{int(q*100)}':_quantile([x['elapsed_ms'] for x in case],q) for q in (.5,.95)},'decision_delay_ms':{'min':min(x['decision_age_ms'] for x in case),'median':statistics.median(x['decision_age_ms'] for x in case),'max':max(x['decision_age_ms'] for x in case)}}
mismatch_counts=collections.Counter();mismatches=[]
for rec in records:
 for step in rec['assessment']['model_io']['steps']:
  h=(step.get('response') or {}).get('request_payload_artifact')
  if not h:continue
  wire=json.loads(art.get(h))
  sent=json.loads(wire['input'].split('\n',1)[1]) if 'input' in wire else json.loads(wire['messages'][-1]['content'])
  logged=step['request']['input'];mismatch_counts['compared']+=1
  if sent!=logged:
   keys=sorted(k for k in set(sent)|set(logged) if sent.get(k)!=logged.get(k))
   mismatch_counts['mismatched']+=1;mismatch_counts[step['model']['model_id']]+=1
   mismatches.append({'job_id':rec['assessment']['job_id'],'request_id':step['request']['request_id'],'different_fields':keys,'wire_tool_results':len(sent['tool_results']),'logged_tool_results':len(logged['tool_results']),'wire_request_sha256':h})
(out/'input-mismatches.json').write_text(json.dumps({'counts':dict(mismatch_counts),'cases':mismatches},sort_keys=True,indent=2)+'\n')
summary['normalized_input_vs_wire']=dict(mismatch_counts)
ledger=sqlite3.connect('file:'+str(p/'model-budget.sqlite')+'?mode=ro',uri=True)
responses={s['request']['request_id']:s['response'] for r in records for s in r['assessment']['model_io']['steps'] if s['model']['provider']=='openai'}
settled=ledger.execute("SELECT amount,request_id FROM charges WHERE state='SETTLED' AND id<>'initial'").fetchall()
assert len(responses)==len(settled)==103
assert all(responses[rid]['cost']['amount_micro_usd']==amount for amount,rid in settled)
summary['accounting']={'settled_usage_ledger_matches':len(settled),'settled_micro_usd':sum(v[0] for v in settled),'unknown_micro_usd':ledger.execute("SELECT sum(amount) FROM charges WHERE state='UNKNOWN'").fetchone()[0],'unknown_charges':ledger.execute("SELECT count(*) FROM charges WHERE state='UNKNOWN'").fetchone()[0],'routing_spec_unchanged':(p/'selected-configs/model-routing.json').read_bytes()==Path('config/intelligence/aiand-routing.openai-trial.example.json').read_bytes()}
ledger.close()
(out/'per-job.json').write_text(json.dumps(case,sort_keys=True,indent=2)+'\n');(out/'baseline-results.json').write_text(json.dumps(baseline,sort_keys=True,indent=2)+'\n');(out/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps(summary,sort_keys=True,indent=2))
