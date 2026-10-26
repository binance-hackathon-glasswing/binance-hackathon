"""#120 independent analysis of the DC-01 raw daily files (offline, no network).
Usage (repo root): PYTHONPATH=. python dc01_review.py CAPTURE_DIR > out.json"""
import json, sys
from decimal import Decimal
from pathlib import Path
from larp.marketdata import cost_summary as cs
from larp.runtime.driver import SessionCalendar

cap = Path(sys.argv[1])
rows = [json.loads(l) for f in sorted(cap.glob('capture-*.jsonl')) for l in open(f)]
sessions = SessionCalendar(json.loads(Path(cs.SESSION_CALENDAR).read_bytes())).sessions
samples = [r for r in rows if r['kind'] == 'SAMPLE']


def q(values, p):
    v = sorted(values)
    return float(v[min(len(v) - 1, int(round(p * (len(v) - 1))))]) if v else None


out = {}
for symbol in sorted({r['symbol'] for r in samples}):
    out[symbol] = {}
    for regime in ('US_SESSION', 'OFF_SESSION'):
        mine = [r for r in samples if r['symbol'] == symbol and cs._regime(r['at'], sessions) == regime]
        rt, resid, imp, drift, opens, size = [], [], [], [], {}, set()
        for r in mine:
            pay = int(r['pay_raw'])
            size.add(pay / 10**18)
            roundtrip = Decimal(pay - int(r['sell_proceeds'])) * 10000 / pay
            b, s = Decimal(r['buy_impact_bps']), Decimal(r['sell_impact_bps'])
            rt.append(roundtrip); resid.append(roundtrip - b - s); imp += [b, s]
            buy = int(r['buy_received'])
            drift.append(abs(Decimal(buy - int(r['requote_received']))) * 10000 / buy)
            k = str(r.get('token_open')).lower(); opens[k] = opens.get(k, 0) + 1
        out[symbol][regime] = dict(
            samples=len(mine), quote_size_usdt=sorted(size), token_open=opens,
            roundtrip_bp=dict(p10=q(rt, .1), median=q(rt, .5), p90=q(rt, .9), max=q(rt, 1)),
            spread_residual_bp=dict(median=q(resid, .5), p90=q(resid, .9), max=q(resid, 1)),
            impact_bp=dict(median=q(imp, .5), p90=q(imp, .9), max=q(imp, 1)),
            requote_drift_bp=dict(median=q(drift, .5), p90=q(drift, .9), max=q(drift, 1)))
print(json.dumps(dict(samples=len(samples), bnb_quotes=sum(r['kind'] == 'BNB_PRICE' for r in rows),
                      first=min(r['at'] for r in rows), last=max(r['at'] for r in rows), symbols=out), indent=1))
