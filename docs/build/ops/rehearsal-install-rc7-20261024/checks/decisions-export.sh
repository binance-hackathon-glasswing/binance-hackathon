# Read-only (primary; IDEA-087 DX): the agent's decisions for the dashboard. One JSON line per round (the latest N,
# default 30, to stay under SSM's 24,000-character inline output), then one summary line. One READ ONLY transaction.
# Fields are allow-listed (codes, symbols, amounts, times): no free text, model text, IDs, hashes, config or URLs.
#   python3.12 -I ssm_run.py checks/decisions-export.sh [N]
#   python -m tools.dashboard.decisions merge results/decisions-export-stdout.txt --monitor-dir deploy/activation/rehearsal-monitor
set -eu
LIMIT=${1:-30}
case "$LIMIT" in ''|*[!0-9]*) echo "N must be a number" >&2; exit 2;; esac
cd /opt/larp/current
# larp_execution can SELECT every table read here (deploy/postgres/roles.sql); larp_runtime cannot.
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 LIMIT="$LIMIT" .venv/bin/python - <<'PY'
import json, os, re
CODE = re.compile(r'^[A-Z][A-Z0-9_]{0,63}$')
SYMBOL = re.compile(r'^[A-Z][A-Z0-9]{0,15}$')
ROUND = re.compile(r'^[A-Za-z0-9_.:#-]{1,160}$')
AMOUNT = re.compile(r'^[0-9]{1,30}(\.[0-9]{1,30})?$')
HEX = re.compile(r'0x[0-9a-fA-F]{8,}')
SCHEMA = 'LarpDecisionExport.v1'


def code(v):
    return v if isinstance(v, str) and CODE.match(v) else 'OTHER'


def symbol(v):
    return v if isinstance(v, str) and SYMBOL.match(v) else None


def codes(v, n=12):
    return [code(x) for x in v[:n]] if isinstance(v, list) else []


def ms(v):
    return v if type(v) is int and v > 0 else None


def rows(v, n=12):
    return [x for x in v[:n] if isinstance(x, dict)] if isinstance(v, list) else []


def weight(v):
    ok = isinstance(v, list) and len(v) == 2 and all(type(x) is int for x in v) and v[1] > 0
    return v if ok else None


def reason(r):
    """A planner rejection or clamp: a code string, or an object with symbol(s), reason and gate codes."""
    if isinstance(r, str):
        return dict(symbol=None, reason=code(r))
    out = dict(symbol=symbol(r.get('symbol')), reason=code(r.get('reason')))
    if isinstance(r.get('symbols'), list):
        out['symbols'] = [s for s in map(symbol, r['symbols'][:10]) if s]
    if isinstance(r.get('gates'), list):
        out['gates'] = codes(r['gates'], 10)
    return out


def shape(seq, event):
    """One ROUND_PLANNED or PLAN_REJECTED event as an allow-listed decision row, else None."""
    if not isinstance(event, dict) or event.get('kind') not in ('ROUND_PLANNED', 'PLAN_REJECTED'):
        return None
    rec = event.get('record') if isinstance(event.get('record'), dict) else {}
    rid = rec.get('round_id')
    if not isinstance(rid, str) or not ROUND.match(rid) or HEX.search(rid):
        return None
    plan = rec.get('plan') if isinstance(rec.get('plan'), dict) else {}
    out = rec.get('policy_output') if isinstance(rec.get('policy_output'), dict) else {}
    a = rec.get('assessment') if isinstance(rec.get('assessment'), dict) else None
    return dict(
        section='decision', schema=SCHEMA, seq=seq if type(seq) is int else None, round_id=rid,
        event='PLANNED' if event['kind'] == 'ROUND_PLANNED' else 'REJECTED',
        started_ms=ms(rec.get('started_ms')), decision_ms=ms(rec.get('decision_ms')),
        round_kind=code(rec.get('round_kind') or 'TRADE'), errors=codes(rec.get('errors')),
        execution_pending=rec.get('execution_pending') is True,
        orders=[dict(symbol=symbol(o.get('symbol')), side=o.get('side') if o.get('side') in ('BUY', 'SELL') else None,
                     amount=o.get('amount') if isinstance(o.get('amount'), str) and AMOUNT.match(o['amount']) else None)
                for o in rows(rec.get('orders'))],
        intents=[dict(symbol=symbol(i.get('symbol')), side=i.get('side') if i.get('side') in ('BUY', 'SELL') else None,
                      mandatory=i.get('mandatory') is True, reasons=codes(i.get('reasons'), 6))
                 for i in rows(plan.get('intents'))],
        targets=[dict(symbol=symbol(t.get('symbol')), kind=code(t.get('kind')), reason=code(t.get('reason')),
                      weight=weight(t.get('weight'))) for t in rows(out.get('targets'), 16)],
        rejections=[reason(r) for r in (plan.get('rejections') or [])[:16] if isinstance(r, (str, dict))]
        + [dict(symbol=None, reason=code(r)) for r in (plan.get('reasons') or [])[:4]],
        clamps=[reason(r) for r in (plan.get('clamps') or [])[:8] if isinstance(r, (str, dict))],
        assessment=None if a is None else dict(issuer=symbol(a.get('issuer_id')), status=code(a.get('status')),
                                               reasons=codes(a.get('reasons'), 6)))


def closing(event):
    """(round_id, status) for a ROUND_CLOSED event, else None."""
    if not isinstance(event, dict) or event.get('kind') != 'ROUND_CLOSED' or not isinstance(event.get('round_id'), str):
        return None
    return event['round_id'], code(event.get('status'))


def emit(events, limit, run_id):
    """The export's lines for (sequence, event) pairs in order: the latest `limit` rounds, then a summary."""
    decisions, closed = {}, {}
    for seq, e in events:
        row = shape(seq, e)
        if row:
            decisions[row['round_id']] = row
        done = closing(e)
        if done:
            closed[done[0]] = done[1]
    latest = sorted(decisions.values(), key=lambda d: d['seq'] or 0)[-limit:] if limit > 0 else []
    lines = [json.dumps(dict(d, status=closed.get(d['round_id'])), sort_keys=True, separators=(',', ':'))
             for d in latest]
    lines.append(json.dumps(dict(section='decisions_summary', schema=SCHEMA, run_id=run_id, rounds=len(decisions),
                                 exported=len(latest), closed=len(closed)), sort_keys=True, separators=(',', ':')))
    return lines


# ---- database (not run by the offline tests) ----
from contextlib import contextmanager
from pathlib import Path
from larp.runtime.database import IamPostgresStore, rds_client
class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY'); yield db
def load(b):
    try: return json.loads(bytes(b))
    except Exception: return None
c = json.loads(Path('/etc/larp/execution.json').read_text()); r = c['run_id']
s = RO(c, rds_client(c['region']))
with s.transaction() as db:
    events = [(seq, (load(b) or {}).get('event'))
              for seq, b in db.execute('SELECT sequence,batch FROM events WHERE run_id=%s ORDER BY sequence', (r,)).fetchall()]
for line in emit(events, int(os.environ['LIMIT']), r):
    print(line)
PY
