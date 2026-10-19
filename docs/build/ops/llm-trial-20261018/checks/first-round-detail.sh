set -eu
cd /opt/larp/current
for u in larp-runtime larp-evidence larp-uploader larp-execution; do
  echo "$u $(systemctl show $u -p ActiveState --value) restarts=$(systemctl show $u -p NRestarts --value)"
done
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from contextlib import contextmanager
from pathlib import Path
import json, re, time, sqlite3
from larp.runtime.database import IamPostgresStore, rds_client
class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY'); yield db
c = json.loads(Path('/etc/larp/runtime.json').read_text()); r = c['run_id']
s = RO(c, rds_client(c['region']))
KEY = re.compile(r'model|stage|effort|routing|prompt|profile|build|assess|job|cutoff|provider|served|request|response|'
                 r'charge|reserv|usage|token|round|status|reason|outcome|kind|decision|_ms$|sha256|hash|artifact|trial|cost', re.I)
def leaves(x, p='', out=None, depth=0):
    out = [] if out is None else out
    if len(out) > 120 or depth > 9: return out
    if isinstance(x, dict):
        for k, v in x.items(): leaves(v, f'{p}.{k}' if p else k, out, depth + 1)
    elif isinstance(x, list):
        for i, v in enumerate(x[:6]): leaves(v, f'{p}[{i}]', out, depth + 1)
    elif (isinstance(x, (int, float, bool)) or (isinstance(x, str) and len(x) <= 100)) and KEY.search(p.split('.')[-1]):
        out.append([p, x])
    return out
def load(b):
    try: return json.loads(bytes(b))
    except Exception: return None
x = dict(now_ms=time.time_ns() // 1000000, run_id=r)
with s.transaction() as db:
    x['run_version'] = db.execute('SELECT version FROM runs WHERE run_id=%s', (r,)).fetchone()[0]
    x['rounds'] = [list(v) for v in db.execute('SELECT round_id,status FROM rounds WHERE run_id=%s ORDER BY round_id', (r,)).fetchall()]
    x['jobs'] = [[j[0], j[1], j[2], j[3]] for j in db.execute('SELECT job_id,lane,status,attempts FROM jobs WHERE run_id=%s', (r,)).fetchall()]
    ev = []
    for q, b in db.execute('SELECT sequence,batch FROM events WHERE run_id=%s AND sequence>3 ORDER BY sequence', (r,)).fetchall():
        e = (load(b) or {}).get('event') or {}
        ev.append(dict(seq=q, kind=e.get('kind'), fields=leaves(e)[:60]))
    x['events'] = ev
    x['audit_chunks'] = [[a, b_, cc, d_, (load(ack) if ack else None)] for a, b_, cc, d_, ack in db.execute(
        'SELECT event_id,chunk_index,status,attempts,acknowledgement FROM audit_chunks WHERE run_id=%s ORDER BY event_id,chunk_index LIMIT 6',
        (r,)).fetchall()]
print(json.dumps(x, sort_keys=True, default=str))
con = sqlite3.connect('file:/var/lib/larp-runtime/model-budget/openai-budget.sqlite?mode=ro', uri=True)
print(json.dumps(dict(charges=con.execute('SELECT id,amount,state,request_id FROM charges ORDER BY id').fetchall(),
                      trial_charges=con.execute('SELECT * FROM trial_charges').fetchall(),
                      trial=con.execute('SELECT stopped,reason,last_ms FROM trial').fetchall(),
                      switches=con.execute('SELECT * FROM switches').fetchall())))
m = Path('/var/lib/larp-runtime/market/model'); arts = []
for f in sorted(m.rglob('*')):
    if not f.is_file(): continue
    raw = f.read_bytes(); d = None
    try: d = json.loads(raw)
    except Exception: pass
    ident = {}
    if isinstance(d, dict):
        for k in ('model', 'schema', 'service_tier', 'status', 'object'):
            if isinstance(d.get(k), str): ident[k] = d[k][:80]
        for k in ('reasoning', 'usage'):
            if isinstance(d.get(k), dict): ident[k] = {a: b for a, b in d[k].items() if not isinstance(b, (dict, list)) or a.endswith('details')}
    arts.append(dict(name=f.name[:16], bytes=len(raw), mtime=int(f.stat().st_mtime), ident=ident))
print(json.dumps(dict(model_artifacts=arts[-30:], count=len(arts)), default=str))
PY
ls -la /var/lib/larp-runtime/ai-seeds | tail -5 | sed -E 's/ +/ /g'
journalctl -u larp-runtime --since "-20min" -o cat --no-pager | grep -v '^{"release_verified' | tail -n 12 | cut -c1-300
