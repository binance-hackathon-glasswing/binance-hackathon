set -eu
cd /opt/larp/current
sudo env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import json,time,subprocess,sqlite3,collections
from pathlib import Path
c=json.loads(Path('/etc/larp/runtime.json').read_text());d=c['driver']
x={'section':'host_inventory','checked_at_ms':time.time_ns()//1000000,'build_id':c['build_id'],'mode':c['mode'],'assessor':d['assessor'],'execution':d['execution'],'model_routing_sha256':d.get('model_routing_sha256'),'budget_exists':Path('/var/lib/larp-runtime/model-budget/openai-budget.sqlite').exists(),'units':{}}
for u in ['larp-runtime','larp-evidence','larp-uploader','larp-execution','larp-archive.timer']:
 p=subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','SubState','-p','NRestarts','-p','MemoryCurrent'],capture_output=True,text=True,check=True);x['units'][u]=dict(v.split('=',1) for v in p.stdout.splitlines() if '=' in v)
p=Path('/var/lib/larp-evidence/live/polls.jsonl');last={};bad=0
for line in p.read_bytes().splitlines():
 try:r=json.loads(line)
 except ValueError:bad+=1;continue
 if r['target'] not in last or r['started_ms']>last[r['target']]['started_ms']:last[r['target']]={k:r.get(k) for k in ['started_ms','finished_ms','status','truncated','error']}
x['latest_source_polls']=last;x['corrupt_poll_lines']=bad
print(json.dumps(x,sort_keys=True))
PY
sudo -u larp-archive env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from contextlib import contextmanager
from pathlib import Path
import json,time
from larp.runtime.database import IamPostgresStore,rds_client
from larp.runtime.maintenance import Maintenance,HOUR_MS
class RO(IamPostgresStore):
 @contextmanager
 def transaction(self):
  with super().transaction() as db:
   db.execute('SET TRANSACTION READ ONLY');yield db
try:
 c=json.loads(Path('/etc/larp/operations.json').read_text());s=RO(c,rds_client(c['region']));w=Maintenance(s,None,backup_interval_ms=c['backup_interval_hours']*HOUR_MS);now=time.time_ns()//1000000;h=w.health(c['run_id'],now).read()
 x={'section':'read_only_operational_health','checked_at_ms':now,'healthy':h.get('healthy'),'reasons':h.get('reasons'),'health_fields':sorted(h)}
 with s.transaction() as db:
  x['audit_chunks_by_status']=dict(db.execute('SELECT status,count(*) FROM audit_chunks WHERE run_id=%s GROUP BY status',(c['run_id'],)).fetchall())
  x['archive_tasks_by_kind_status']=[{'kind':r[0],'status':r[1],'count':r[2],'last_slot_ms':r[3]} for r in db.execute('SELECT kind,status,count(*),max(slot_ms) FROM archive_outbox WHERE run_id=%s GROUP BY kind,status ORDER BY kind,status',(c['run_id'],)).fetchall()]
 print(json.dumps(x,sort_keys=True))
except Exception as e:
 print(json.dumps({'section':'read_only_operational_health','status':'REFUSED','error_type':type(e).__name__}));raise SystemExit(4)
PY
