# Read-only (primary; SJ-08): what the agent decided and did. Rounds, plans and rejection reasons, execution records,
# signer refusals, incidents/HALT/low-gas, and the run's own portfolio. One READ ONLY transaction; prints public
# values only (no config, DSN, URL or key).
#   python3.12 -I ssm_run.py checks/trading-status.sh            (then read results/trading-status-stdout.txt)
set -eu
for u in larp-runtime larp-execution larp-evidence larp-uploader; do
  echo "$u $(systemctl is-active $u || true) restarts=$(systemctl show $u -p NRestarts --value)"
done
cd /opt/larp/current
# larp_execution can SELECT every table read here (deploy/postgres/roles.sql); larp_runtime cannot.
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
import json, re, time
from larp.runtime.database import IamPostgresStore, rds_client
class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY'); yield db
c = json.loads(Path('/etc/larp/execution.json').read_text()); r = c['run_id']
s = RO(c, rds_client(c['region']))
KEEP = re.compile(r'kind|status|reason|symbol|side|action|units|amount|price|qty|quantity|notional|tx_hash|nonce|gas|'
                  r'fee|round_id|economic_key|rejection|blocked|halt|incident|low_gas|mandatory|cap|slippage|min_out|'
                  r'expires|_ms$|_s$|outcome|terminal|stage|code|detail', re.I)
SKIP = re.compile(r'host|dsn|url|secret|key_file|credential|signature|raw|payload_bytes|signed', re.I)
def load(b):
    try: return json.loads(bytes(b))
    except Exception: return None
def leaves(x, p='', out=None, depth=0, limit=40):
    out = [] if out is None else out
    if len(out) >= limit or depth > 9: return out
    if isinstance(x, dict):
        for k, v in x.items():
            if not SKIP.search(k): leaves(v, f'{p}.{k}' if p else k, out, depth + 1, limit)
    elif isinstance(x, list):
        for i, v in enumerate(x[:8]): leaves(v, f'{p}[{i}]', out, depth + 1, limit)
    elif (isinstance(x, (int, float, bool)) or (isinstance(x, str) and len(x) <= 120)) and KEEP.search(p.split('.')[-1]):
        out.append([p, x])
    return out
now = time.time_ns() // 1000000
with s.transaction() as db:
    q, epoch, ver, mode, clock, proj = db.execute(
        'SELECT quarantined,epoch,version,mode,clock_ms,projection FROM runs WHERE run_id=%s', (r,)).fetchone()
    p = load(proj) or {}
    port = p.get('portfolio') or {}
    print(json.dumps(dict(section='run', run_id=r, now_ms=now, quarantined=q, epoch=epoch, version=ver, mode=mode,
                          clock_ms=clock, projection_keys=sorted(p), registered_build=(p.get('registered_version') or {}).get('build_id'),
                          portfolio=dict(cash_units=port.get('cash_units'), bnb_units=port.get('bnb_units'),
                                         positions={k: (v or {}).get('units') for k, v in (port.get('positions') or {}).items()}),
                          halt=leaves({k: p[k] for k in p if 'halt' in k.lower() or 'gas' in k.lower() or 'quarant' in k.lower()}))))
    rounds = db.execute('SELECT round_id,status FROM rounds WHERE run_id=%s ORDER BY round_id', (r,)).fetchall()
    print(json.dumps(dict(section='rounds', total=len(rounds), by_status=dict(Counter(st for _, st in rounds)),
                          last=[list(x) for x in rounds[-8:]])))
    events = db.execute('SELECT sequence,batch FROM events WHERE run_id=%s ORDER BY sequence', (r,)).fetchall()
    kinds, reasons, recent = Counter(), Counter(), []
    for seq, b in events:
        e = (load(b) or {}).get('event') or {}
        k = e.get('kind'); kinds[k] += 1
        for path, v in leaves(e, limit=200):
            if path.split('.')[-1] in ('reason', 'code') and isinstance(v, str): reasons[(k, v)] += 1
        if k not in ('ROUND_LOGGED', 'ROUND_SEALED', 'DAY_ROLLED'): recent.append(dict(seq=seq, kind=k, fields=leaves(e, limit=30)))
    print(json.dumps(dict(section='events', total=len(events), by_kind=dict(kinds),
                          reasons=[[k, v, n] for (k, v), n in reasons.most_common(25)])))
    for e in recent[-15:]:
        print(json.dumps(dict(section='event', **e), default=str))
    recs = db.execute('SELECT economic_key,terminal,revision,state FROM execution_records WHERE run_id=%s', (r,)).fetchall()
    for key, term, rev, st in recs[-12:]:
        print(json.dumps(dict(section='execution', key=key[:24], terminal=term, revision=rev, state=leaves(load(st) or {}, limit=30)), default=str))
    print(json.dumps(dict(section='execution_summary', records=len(recs), terminal=sum(1 for x in recs if x[1]),
                          signing_requests=db.execute('SELECT count(*) FROM signing_requests WHERE run_id=%s', (r,)).fetchone()[0],
                          signatures=db.execute('SELECT count(*) FROM execution_signatures WHERE run_id=%s', (r,)).fetchone()[0],
                          refusals=[list(x) for x in db.execute('SELECT reason,count(*) FROM signing_refusals WHERE run_id=%s GROUP BY reason', (r,)).fetchall()],
                          reservations=db.execute('SELECT count(*) FROM reservations WHERE run_id=%s', (r,)).fetchone()[0])))
PY
for u in larp-runtime larp-execution; do
  echo "== $u journal (fixed JSON status lines, last 30 min)"
  journalctl -u $u --since "-30 min" --no-pager -o cat | grep -E '^\{' | grep -v -i -E 'https?://|dsn' | tail -5 || true
done
