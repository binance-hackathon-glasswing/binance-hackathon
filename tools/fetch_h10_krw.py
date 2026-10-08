"""Download the Federal Reserve H.10 won-per-dollar history (public domain; cite the Board) and parse it.

Replaces FRED `DEXKOUS` (same underlying series): FRED's terms forbid use in connection with machine learning,
the Board's own site does not (federalreserve.gov/disclaimer.htm, checked 2026-10-08).

Run from the team network (Claude's sandboxes cannot reach federalreserve.gov):
  python tools/fetch_h10_krw.py
Writes data/raw/fed_h10/dat00_ko_<fetched_utc>.htm (raw, append-only) and a .csv (date, krw_per_usd; ND -> empty),
and prints the sha256, row count and date range. data/ is git-ignored.
"""
import csv
import hashlib
import pathlib
import re
import sys
import urllib.request
from datetime import datetime, timezone

URL = "https://www.federalreserve.gov/releases/h10/hist/dat00_ko.htm"
ROW = re.compile(r"(\d{1,2}-[A-Z]{3}-\d{2})\s*(?:</t[dh]>\s*<t[dh][^>]*>\s*)?([\d.]+|ND)")


def parse(html):
    rows = []
    for d, v in ROW.findall(html):
        date = datetime.strptime(d, "%d-%b-%y").date().isoformat()
        rows.append((date, "" if v == "ND" else v))
    return rows


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "LARP research (binance-hackathon team)"})
    raw = urllib.request.urlopen(req, timeout=30).read()
    fetched = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = pathlib.Path("data/raw/fed_h10")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"dat00_ko_{fetched}.htm").write_bytes(raw)
    rows = parse(raw.decode("utf-8", "replace"))
    if not rows:
        sys.exit("no rows parsed: page layout changed; inspect the saved .htm")
    with open(out / f"dat00_ko_{fetched}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "krw_per_usd"])
        w.writerows(rows)
    print(f"sha256 {hashlib.sha256(raw).hexdigest()}  rows {len(rows)}  {rows[0][0]} .. {rows[-1][0]}  "
          f"ND {sum(1 for _, v in rows if not v)}  source {URL}")


if __name__ == "__main__":
    main()
