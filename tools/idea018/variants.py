"""Reproduce IDEA-012 §1 off-hours variance share under alternative 'on-hours' definitions (1h closes).
IDEA-018 §2.1 (review script, offline, reads only the given probe file).
Usage: python -I variants.py <candles_probe.json>"""
import json, math, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from larp.research.candles import closed_bstock_bars
def main(path):
    capture = json.load(open(path)); TOK = ["NVDAB", "GOOGLB", "SKHYB", "TSLAB", "MSFTB"]; H = 3600000
    captured = closed_bstock_bars(capture, "1h", H)
    def series(t):
        return {stamp: row[3] for stamp, row in captured[t].items()}
    def is_on(ms, mode):
        t = datetime.fromtimestamp(ms / 1000, tz=timezone.utc) - timedelta(hours=4)
        if t.weekday() >= 5 or t.strftime("%Y-%m-%d") == "2026-09-07": return False
        m = t.hour * 60 + t.minute
        return (9 * 60 <= m < 16 * 60) if mode in ("open-hour ON", "chained across 7-day hole") else (10 * 60 <= m < 16 * 60)
    for mode in ["open-hour ON", "open-hour OFF (IDEA-012?)", "chained across 7-day hole"]:
        out = []
        for t in TOK:
            d = series(t); ts = list(d); on = off = 0.0
            for a, b in zip(ts, ts[1:]):
                if (b - a) // H > 48 and not mode.startswith("chained"): continue
                if not mode.startswith("chained") and b - a != H: continue
                r = math.log(d[b] / d[a])
                if is_on(b, mode): on += r * r
                else: off += r * r
            out.append(f"{t} {off/(on+off):.0%}" if on + off > 0 else
                       f"{t} INCONCLUSIVE: insufficient nonconstant closed returns")
        print(f"{mode:28}", out)


if __name__ == "__main__":
    main(sys.argv[1])
