set -eu
cd /opt/larp/current
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from contextlib import contextmanager
from pathlib import Path
import json
from larp.runtime.database import IamPostgresStore, rds_client
class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY'); yield db
c = json.loads(Path('/etc/larp/runtime.json').read_text()); r = c['run_id']
s = RO(c, rds_client(c['region']))
with s.transaction() as db:
    rows = db.execute('SELECT sequence,batch FROM events WHERE run_id=%s AND sequence>3 ORDER BY sequence', (r,)).fetchall()
for q, b in rows:
    e = json.loads(bytes(b)).get('event') or {}
    a = ((e.get('record') or {}).get('assessment')) or {}
    if not a:
        print(json.dumps(dict(seq=q, kind=e.get('kind'), status=e.get('status'), round_id=e.get('round_id')))); continue
    io = a.get('model_io') or {}
    steps = [dict(stage=s_.get('routing_stage'), model=(s_.get('model') or {}).get('model_id'),
                  status=(s_.get('response') or {}).get('status'), served=(s_.get('response') or {}).get('served_model'),
                  latency_ms=(s_.get('response') or {}).get('latency_ms'), usage=(s_.get('response') or {}).get('usage'),
                  error=(s_.get('response') or {}).get('error'))
             for s_ in io.get('steps') or []]
    print(json.dumps(dict(seq=q, kind=e.get('kind'), status=a.get('status'), reasons=a.get('reasons'),
                          decision=a.get('decision') if not isinstance(a.get('decision'), dict) else sorted(a['decision']),
                          budget_used=a.get('budget_used'), requests_started=io.get('requests_started'),
                          in_flight=[dict(stage=x.get('routing_stage'), model=(x.get('model') or {}).get('model_id'),
                                          status=x.get('status')) for x in io.get('in_flight_calls') or []],
                          steps=steps, top_keys=sorted(a)), default=str)[:6000])
PY
cd /var/lib/larp-runtime/market/model
python3 - <<'PY'
import json, pathlib
for prefix in ('297f491d', '9bbb47c9'):
    for p in pathlib.Path('.').rglob(prefix + '*'):
        d = json.loads(p.read_bytes()); inp = d.get('input')
        print(json.dumps(dict(name=p.name[:16], input_first_line=inp.split('\n', 1)[0] if isinstance(inp, str) else type(inp).__name__)))
for prefix in ('152220799c437cfe', '5d0336e3efc856e2', '3e4fb23ea7acb00f'):
    for p in pathlib.Path('.').rglob(prefix + '*'):
        d = json.loads(p.read_bytes())
        print(json.dumps(dict(name=p.name[:16], status=d.get('status'), reasons=d.get('reasons'), model=(d.get('model') or {}).get('model_id'))))
PY
