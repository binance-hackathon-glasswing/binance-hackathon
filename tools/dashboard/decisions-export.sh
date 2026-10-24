# Read-only (primary; IDEA-087 DX): the agent's decisions for the dashboard. One JSON line per round (the latest N,
# default 30), bounded to 22,000 UTF-8 bytes including a summary for SSM inline output. One READ ONLY transaction.
# With SINCE (IDEA-091 E1), only the events after that sequence are read: oldest first within the budget, a closure
# line for a round planned earlier, and a summary naming the last sequence covered (the next run's SINCE). Events are
# streamed through a server-side cursor either way, so memory and reads follow the new events, not the run's length.
# Fields are allow-listed (codes, symbols, amounts, times): no free text, model text, IDs, hashes, config or URLs.
#   python3.12 -I ssm_run.py ../../../tools/dashboard/decisions-export.sh [N] [SINCE]     (from the copied run folder)
#   python -m tools.dashboard.decisions merge results/decisions-export-stdout.txt --monitor-dir deploy/activation/rehearsal-monitor
set -eu
LIMIT=${1:-30}
SINCE=${2:-}
case "$LIMIT" in ''|*[!0-9]*) echo "N must be a number" >&2; exit 2;; esac
case "$SINCE" in *[!0-9]*) echo "SINCE must be a sequence number" >&2; exit 2;; esac
cd /opt/larp/current
# larp_execution can SELECT every table read here (deploy/postgres/roles.sql); larp_runtime cannot.
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 LIMIT="$LIMIT" SINCE="$SINCE" .venv/bin/python - <<'PY'
from collections import deque
import json, os, re
CODE = re.compile(r'^[A-Z][A-Z0-9_]{0,63}$')
SYMBOL = re.compile(r'^[A-Z][A-Z0-9]{0,15}$')
ROUND = re.compile(r'^[A-Za-z0-9_.:#-]{1,160}(?:/quote[1-9][0-9]*(?:#[1-9][0-9]*)?)*$')
AMOUNT = re.compile(r'^[0-9]{1,30}(\.[0-9]{1,30})?$')
HEX = re.compile(r'0x[0-9a-fA-F]{8,}')
SCHEMA = 'LarpDecisionExport.v1'
MAX_EXPORT_BYTES = 22000  # leave room below SSM's 24,000-character stdout limit


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
    lines = deque(json.dumps(dict(d, status=closed.get(d['round_id'])), sort_keys=True, separators=(',', ':'))
                  for d in latest)
    summary = dict(section='decisions_summary', schema=SCHEMA, run_id=run_id, rounds=len(decisions),
                   exported=len(latest), closed=len(closed))
    size = lambda line: len(line.encode('utf-8')) + 1  # print adds one newline per line
    total = sum(map(size, lines))
    while True:
        tail = json.dumps(summary, sort_keys=True, separators=(',', ':'))
        if total + size(tail) <= MAX_EXPORT_BYTES:
            return [*lines, tail]
        if not lines:
            raise ValueError('Decision export summary exceeds output budget')
        total -= size(lines.popleft())  # preserve the newest complete rows, never a truncated JSON line
        summary['exported'] -= 1
        summary['omitted_for_size'] = len(latest) - summary['exported']


def emit_since(rows, run_id, since, load, budget=MAX_EXPORT_BYTES):
    """Incremental lines (IDEA-091 E1) for `(sequence, raw batch)` pairs: only events after `since` are decoded. Rows
    go oldest first while they fit the budget; `last_seq` is the last sequence whose output is complete, so the next
    run (SINCE=last_seq) picks up anything trimmed. A closure of a round planned before `since` is a closure line."""
    entries, planned, last, decoded = [], {}, since, 0
    for seq, raw in rows:
        if type(seq) is not int or seq <= since:
            continue
        decoded += 1
        event = (load(raw) or {}).get('event')
        row = shape(seq, event)
        if row:
            row['status'] = None
            planned[row['round_id']] = row
            entries.append((seq, row))
        done = closing(event)
        if done:
            rid, status = done
            if rid in planned:
                planned[rid]['status'] = status
            elif ROUND.match(rid) and not HEX.search(rid):
                entries.append((seq, dict(section='closure', schema=SCHEMA, seq=seq, round_id=rid, status=status)))
        last = seq
    size = lambda line: len(line.encode('utf-8')) + 1
    lines, total, covered = [], 0, last
    for seq, entry in entries:
        line = json.dumps(entry, sort_keys=True, separators=(',', ':'))
        if total + size(line) + 400 > budget:  # 400 bytes kept for the summary
            covered = seq - 1
            break
        lines.append(line)
        total += size(line)
    summary = dict(section='decisions_summary', schema=SCHEMA, run_id=run_id, since=since, last_seq=covered,
                   exported=len(lines), complete=covered == last, decoded=decoded)
    return lines + [json.dumps(summary, sort_keys=True, separators=(',', ':'))]


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
since = int(os.environ['SINCE']) if os.environ.get('SINCE') else None
with s.transaction() as db:
    # A named (server-side) cursor streams the batches 20 at a time: never the whole journal in memory (IDEA-091).
    with db.cursor(name='larp_dashboard_export') as cur:
        cur.itersize = 20
        cur.execute('SELECT sequence,batch FROM events WHERE run_id=%s AND sequence>%s ORDER BY sequence', (r, since or 0))
        if since is None:
            lines = emit(((seq, (load(b) or {}).get('event')) for seq, b in cur), int(os.environ['LIMIT']), r)
        else:
            lines = emit_since(((seq, bytes(b)) for seq, b in cur), r, since, load)
for line in lines:
    print(line)
PY
