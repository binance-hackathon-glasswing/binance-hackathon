"""Static wallet dashboard from the SJ-08 chain monitor's files, plus the agent's decisions (IDEA-087, DX).

  python -m tools.dashboard.build --monitor-dir deploy/activation/rehearsal-monitor --out <site dir> [--full]

Reads only snapshots.jsonl, transactions.jsonl and alerts.jsonl from the monitor folder
(docs/build/ops/rehearsal-install-20261022/mac/chain-monitor.py), and decisions.jsonl when present (merged there by
tools/dashboard/decisions.py from the primary's read-only decisions export), and writes index.html (one self-contained page with
the data embedded), data.json and .nojekyll. No network, no credentials and no clock: the same input always gives
byte-identical output, and the page works out staleness in the browser.

Redacted by default, because a Pages site on the Free plan is public: output fields are allow-listed, and the wallet,
transaction hashes, contract and spender addresses, block numbers, nonces and round IDs are left out unless --full
is given.
Equity excludes BNB and uses the monitor's Web3 prices; it is not the official score.
"""
import argparse
import bisect
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

FILES = ('snapshots.jsonl', 'transactions.jsonl', 'alerts.jsonl')
DECISIONS = 'decisions.jsonl'  # optional; written by tools/dashboard/decisions.py, not by the monitor
OUTPUTS = ('index.html', 'data.json', '.nojekyll')
TEMPLATE = Path(__file__).with_name('template.html')
PLACEHOLDER = '__DASHBOARD_DATA__'
STOCKS = ('NVDAB', 'GOOGLB', 'SKHYB', 'TSLAB', 'MSFTB')
MAX_BUCKETS = 600  # chart buckets; each keeps its extremes, so troughs survive downsampling
MAX_TRANSACTIONS = 500
MAX_DECISIONS = 300
E18 = 10**18
NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,39}$')  # symbols, kinds, error class names; never an 0x address
HASH = re.compile(r'^0x[0-9a-fA-F]{64}$')
UTC = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')
CODE = re.compile(r'^[A-Z][A-Z0-9_]{0,63}$')  # reason, status and error codes
AMOUNT = re.compile(r'^[0-9]{1,30}(\.[0-9]{1,30})?$')
ROUND_ID = re.compile(r'^[A-Za-z0-9_.:#/-]{1,160}$')
HEX = re.compile(r'0x[0-9a-fA-F]{8,}')
ROUND_SOURCES = ('cadence', 'filing', 'review', 'safety')
# Alert kinds written by chain-monitor.py. Unknown kinds show as warnings.
CRITICAL = {'TX_FAILED', 'UNEXPECTED_TOKEN', 'SWAP_WITHOUT_ONE_STOCK_LEG', 'BUY_WITHOUT_USDT_DEBIT',
            'SELL_WITHOUT_USDT_CREDIT', 'TX_NOT_APPROVE_OR_ROUTER_SWAP', 'APPROVAL_TO_OTHER_SPENDER',
            'HOLDING_DIFFERS_FROM_FILLS'}


def read_jsonl(path):
    """Rows of one monitor file, skipping what cannot be read. A last line without a newline that does not parse is
    the monitor mid-write (truncated); any other unreadable line is malformed."""
    report = dict(present=path.is_file(), rows=0, malformed=0, truncated_tail=False)
    if not report['present']:
        return [], report
    text = path.read_bytes().decode('utf-8', errors='replace')
    lines = text.split('\n')
    rows = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        if isinstance(row, dict):
            rows.append(row)
        elif i == len(lines) - 1:
            report['truncated_tail'] = True
        else:
            report['malformed'] += 1
    report['rows'] = len(rows)
    return rows, report


def num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def wei(value):
    return value / E18 if isinstance(value, int) and not isinstance(value, bool) else None


def utc(value):
    return value if isinstance(value, str) and UTC.match(value) else None


def name(value):
    return value if isinstance(value, str) and NAME.match(value) else 'OTHER'


def symbol_order(symbol):
    return (STOCKS.index(symbol), '') if symbol in STOCKS else (len(STOCKS), symbol)


def equity_series(snapshots, start):
    """[utc, equity, drawdown %] per priced snapshot. The opening equity counts as the first peak."""
    points, peak = [], start
    for s in snapshots:
        equity, when = num(s.get('equity_ex_bnb_usdt')), utc(s.get('utc'))
        if equity is None or when is None:
            continue
        peak = equity if peak is None else max(peak, equity)
        points.append([when, equity, (equity - peak) / peak * 100 if peak > 0 else 0.0])
    return points


def max_drawdown(points, start):
    worst, peak, peak_utc, out = 0.0, start, None, dict(pct=0.0, peak_utc=None, trough_utc=None)
    for when, equity, _ in points:
        if peak is None or equity > peak:
            peak, peak_utc = equity, when
        fall = (peak - equity) / peak * 100 if peak > 0 else 0.0
        if fall > worst:
            worst, out = fall, dict(pct=fall, peak_utc=peak_utc, trough_utc=when)
    return out


def downsample(points):
    """At most about 4 points per bucket: first, last, lowest and highest equity, deepest drawdown."""
    if len(points) <= MAX_BUCKETS * 2:
        return points
    keep, size = {0, len(points) - 1}, len(points) / MAX_BUCKETS
    for b in range(MAX_BUCKETS):
        idx = range(int(b * size), max(int((b + 1) * size), int(b * size) + 1))
        keep |= {min(idx, key=lambda i: points[i][1]), max(idx, key=lambda i: points[i][1]),
                 min(idx, key=lambda i: points[i][2]), idx[-1]}
    return [points[i] for i in sorted(keep)]


def holdings(snapshot):
    units = snapshot.get('units') if isinstance(snapshot.get('units'), dict) else {}
    values = snapshot.get('value_usdt') if isinstance(snapshot.get('value_usdt'), dict) else {}
    equity, cash = num(snapshot.get('equity_ex_bnb_usdt')), num(snapshot.get('usdt'))
    rows = []
    for symbol in sorted((k for k in units if num(units[k])), key=symbol_order):
        value = num(values.get(symbol))
        rows.append(dict(symbol=name(symbol), units=num(units[symbol]), value_usdt=value,
                         weight_pct=value / equity * 100 if value is not None and equity else None))
    if cash is not None:
        rows.append(dict(symbol='USDT', units=cash, value_usdt=cash,
                         weight_pct=cash / equity * 100 if equity else None))
    return rows


def seen_at(snapshots):
    """The poll that first reported a block: transactions carry a block, snapshots a block and a time."""
    pairs = sorted((s['block'], utc(s.get('utc'))) for s in snapshots
                   if isinstance(s.get('block'), int) and not isinstance(s.get('block'), bool))
    blocks = [b for b, _ in pairs]

    def lookup(block):
        if not isinstance(block, int) or isinstance(block, bool):
            return None
        i = bisect.bisect_left(blocks, block)
        return pairs[i][1] if i < len(pairs) else None
    return lookup


def transaction(tx, seen, redact):
    fill = tx.get('fill') if isinstance(tx.get('fill'), dict) else {}
    approvals = [a for a in tx.get('approvals') or [] if isinstance(a, dict)]
    symbol = fill.get('symbol') or (approvals[0].get('token') if approvals else None)
    row = dict(seen_utc=seen(tx.get('block')), kind=name(tx.get('kind')),
               ok=tx.get('status') == 1, gas_bnb=wei(tx.get('gas_bnb_wei')),
               side=fill.get('side') if fill.get('side') in ('BUY', 'SELL') else None,
               symbol=name(symbol) if symbol else None, units=wei(fill.get('units')), usdt=wei(fill.get('usdt')),
               price=num(fill.get('price')), realized_usdt=num(fill.get('realized_usdt')))
    if not redact:
        row.update(hash=tx.get('hash') if HASH.match(str(tx.get('hash'))) else None,
                   block=tx.get('block') if isinstance(tx.get('block'), int) else None,
                   nonce=tx.get('nonce') if isinstance(tx.get('nonce'), int) else None)
    return row


def alert_groups(alerts, latest_block, redact):
    """One row per alert kind (and symbol): the monitor repeats an open condition on every poll."""
    groups = {}
    for a in alerts:
        kind, when = name(a.get('kind')), utc(a.get('utc'))
        symbol = name(a['symbol']) if a.get('symbol') else None
        g = groups.setdefault((kind, symbol or ''), dict(kind=kind, symbol=symbol, count=0, first_utc=when,
                                                         last_utc=when, last_block=None, detail=None))
        g['count'] += 1
        g['first_utc'] = g['first_utc'] or when
        g['last_utc'] = when or g['last_utc']
        g['last_block'] = a.get('block') if isinstance(a.get('block'), int) else g['last_block']
        g['detail'] = {k: v for k, v in a.items() if k not in ('kind', 'utc', 'block')}
    rows = []
    for g in sorted(groups.values(), key=lambda g: (g['kind'] not in CRITICAL, g['kind'], g['symbol'] or '')):
        row = dict(kind=g['kind'], symbol=g['symbol'], count=g['count'], first_utc=g['first_utc'],
                   last_utc=g['last_utc'], severity='critical' if g['kind'] in CRITICAL else 'warning',
                   active=latest_block is not None and g['last_block'] == latest_block)
        if not redact:
            row['detail'] = json.dumps(g['detail'], sort_keys=True, default=str)[:300]
        rows.append(row)
    return rows


def dashboard_data(monitor_dir, *, redact=True):
    root = Path(monitor_dir)
    (snapshots, s_report), (txs, t_report), (alerts, a_report) = (read_jsonl(root / f) for f in FILES)
    decided, d_report = read_jsonl(root / DECISIONS)
    snapshots = [s for s in snapshots if utc(s.get('utc'))]
    snapshots.sort(key=lambda s: s['utc'])  # stable: polls that share a finalized block keep file order
    latest = snapshots[-1] if snapshots else {}
    priced = [s for s in snapshots if num(s.get('equity_ex_bnb_usdt')) is not None]
    last_priced = priced[-1] if priced else {}
    with_start = [s for s in priced if num(s.get('pnl_vs_start_ex_bnb_usdt')) is not None]
    start = (num(with_start[-1]['equity_ex_bnb_usdt']) - num(with_start[-1]['pnl_vs_start_ex_bnb_usdt'])
             if with_start else None)
    points = equity_series(snapshots, start)
    equity = num(last_priced.get('equity_ex_bnb_usdt'))
    dd = max_drawdown(points, start)
    seen = seen_at(snapshots)
    rows = [transaction(t, seen, redact) for t in txs]
    latest_block = latest.get('block') if isinstance(latest.get('block'), int) else None
    summary = dict(
        as_of_utc=latest.get('utc'), priced_as_of_utc=last_priced.get('utc'),
        equity_usdt=equity, start_equity_usdt=start,
        return_usdt=equity - start if equity is not None and start is not None else None,
        return_pct=(equity - start) / start * 100 if equity is not None and start else None,
        max_drawdown_pct=dd['pct'], max_drawdown_peak_utc=dd['peak_utc'], max_drawdown_trough_utc=dd['trough_utc'],
        current_drawdown_pct=-points[-1][2] if points else None,
        realized_usdt=num(latest.get('realized_usdt')), unrealized_usdt=num(last_priced.get('unrealized_usdt')),
        gas_spent_bnb=num(latest.get('gas_spent_bnb')), bnb=num(latest.get('bnb')), usdt=num(latest.get('usdt')),
        swaps=latest.get('trades') if isinstance(latest.get('trades'), int) else None,
        failed_txs=latest.get('failed_txs') if isinstance(latest.get('failed_txs'), int) else None,
        price_error=name(latest['price_error']) if latest.get('price_error') else None,
        snapshots=len(snapshots), priced_snapshots=len(priced))
    if not redact:
        summary.update(block=latest_block, nonce=latest.get('nonce') if isinstance(latest.get('nonce'), int) else None)
    return dict(
        schema='LarpDashboard.v1', redacted=redact,
        inputs=dict(zip(FILES + (DECISIONS,), (s_report, t_report, a_report, d_report))),
        summary=summary,
        equity=dict(total=len(points), points=[[w, round(e, 6), round(d, 4)] for w, e, d in downsample(points)]),
        holdings=holdings(latest),
        transactions=dict(total=len(rows), rows=rows[::-1][:MAX_TRANSACTIONS]),
        alerts=alert_groups(alerts, latest_block, redact),
        decisions=decisions_data(decided, redact))


def code(value):
    return value if isinstance(value, str) and CODE.match(value) else 'OTHER'


def side(value):
    return value if value in ('BUY', 'SELL') else None


def items(value, limit=16):
    return [v for v in value[:limit] if isinstance(v, dict)] if isinstance(value, list) else []


def ms_utc(value):
    if type(value) is not int or value <= 0:
        return None
    return datetime.fromtimestamp(value // 1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def reason_row(r):
    row = dict(symbol=name(r['symbol']) if r.get('symbol') else None, reason=code(r.get('reason')))
    if isinstance(r.get('symbols'), list):
        row['symbols'] = [name(s) for s in r['symbols'][:10]]
    if isinstance(r.get('gates'), list):
        row['gates'] = [code(g) for g in r['gates'][:10]]
    return row


def decision(d, redact):
    """One round's decision, allow-listed again here: the export already is, but the page must not trust a file."""
    rid = d.get('round_id') if isinstance(d.get('round_id'), str) else ''
    source = rid.split(':', 1)[0]
    weight = lambda w: (w[0] / w[1] * 100 if isinstance(w, list) and len(w) == 2 and all(type(x) is int for x in w)
                        and w[1] > 0 else None)
    a = d.get('assessment') if isinstance(d.get('assessment'), dict) else None
    row = dict(
        utc=ms_utc(d.get('decision_ms')) or ms_utc(d.get('started_ms')),
        source=source.upper() if source in ROUND_SOURCES else 'OTHER',
        follow_up='/quote' in rid,  # a quote follow-up of the round before it (IDEA-050 E6)
        event=d.get('event') if d.get('event') in ('PLANNED', 'REJECTED') else 'OTHER',
        status=code(d['status']) if d.get('status') is not None else None,
        round_kind=code(d.get('round_kind')), execution_pending=d.get('execution_pending') is True,
        errors=[code(e) for e in (d.get('errors') or [])[:12]] if isinstance(d.get('errors'), list) else [],
        orders=[dict(symbol=name(o.get('symbol')), side=side(o.get('side')),
                     amount=o['amount'] if isinstance(o.get('amount'), str) and AMOUNT.match(o['amount']) else None)
                for o in items(d.get('orders'))],
        intents=[dict(symbol=name(i.get('symbol')), side=side(i.get('side')), mandatory=i.get('mandatory') is True,
                      reasons=[code(r) for r in (i.get('reasons') or [])[:6]] if isinstance(i.get('reasons'), list)
                      else []) for i in items(d.get('intents'))],
        targets=[dict(symbol=name(t.get('symbol')), kind=code(t.get('kind')), reason=code(t.get('reason')),
                      weight_pct=weight(t.get('weight'))) for t in items(d.get('targets'))],
        rejections=[reason_row(r) for r in items(d.get('rejections'), 20)],
        clamps=[reason_row(r) for r in items(d.get('clamps'), 8)],
        assessment=None if a is None else dict(
            issuer=name(a['issuer']) if a.get('issuer') else None, status=code(a.get('status')),
            reasons=[code(r) for r in (a.get('reasons') or [])[:6]] if isinstance(a.get('reasons'), list) else []))
    if not redact:
        row['round_id'] = rid if ROUND_ID.match(rid) and not HEX.search(rid) else None
    return row


def decisions_data(rows, redact):
    """Newest first, with counts by close status and side and the most frequent reason codes."""
    def key(d):
        seq = d.get('seq')
        return (seq if type(seq) is int and not isinstance(seq, bool) else -1,
                d.get('round_id') if isinstance(d.get('round_id'), str) else '')
    shaped = [decision(d, redact) for d in sorted(rows, key=key)]
    by_status, sides, reasons = {}, dict(BUY=0, SELL=0), {}
    for d in shaped:
        status = d['status'] or 'OPEN'
        by_status[status] = by_status.get(status, 0) + 1
        for o in d['orders']:
            if o['side']:
                sides[o['side']] += 1
        for r in [x['reason'] for x in d['rejections']] + d['errors']:
            reasons[r] = reasons.get(r, 0) + 1
    top = sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    return dict(total=len(shaped), by_status=by_status, with_orders=sum(1 for d in shaped if d['orders']),
                buys=sides['BUY'], sells=sides['SELL'], top_reasons=[[k, n] for k, n in top],
                latest_utc=max((d['utc'] for d in shaped if d['utc']), default=None),
                rows=shaped[::-1][:MAX_DECISIONS])


def encode(data):
    """Canonical JSON that is also safe inside a <script> element."""
    text = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    return text.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def build(monitor_dir, out_dir, *, redact=True):
    data = dashboard_data(monitor_dir, redact=redact)
    text = encode(data)
    template = TEMPLATE.read_bytes().decode('utf-8')
    if template.count(PLACEHOLDER) != 1:
        raise RuntimeError('Dashboard template must contain the data placeholder exactly once')
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'index.html').write_bytes(template.replace(PLACEHOLDER, text).encode('utf-8'))
    (out / 'data.json').write_bytes(text.encode('ascii') + b'\n')
    (out / '.nojekyll').write_bytes(b'')
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--monitor-dir', required=True, help='chain-monitor output folder (LARP_MONITOR_DIR)')
    ap.add_argument('--out', required=True, help='folder for index.html, data.json and .nojekyll')
    ap.add_argument('--full', action='store_true',
                    help='keep transaction hashes, blocks, nonces and alert details (do not publish publicly)')
    args = ap.parse_args()
    s = build(args.monitor_dir, args.out, redact=not args.full)['summary']
    print(json.dumps(dict(out=args.out, as_of_utc=s['as_of_utc'], equity_usdt=s['equity_usdt'],
                          snapshots=s['snapshots'], redacted=not args.full), sort_keys=True))


if __name__ == '__main__':
    main()
