"""Read-only SEC EDGAR test pipeline for the five eligible names (IDEA-009 §C.2; EDGAR usable since 2026-10-08,
IDEA-001 §15).

For each issuer it:
  1. reads the filing list from data.sec.gov submissions JSON (form, 8-K items, acceptanceDateTime);
  2. for the newest N filings of the chosen forms, reads the filing's index page and picks the document to read:
     from the filing index page (<accession>-index.htm, Type column): the first EX-99.x exhibit if there is one
     (8-K press release, 6-K announcement), else the primary document;
  3. converts that document to plain text and stores it with source time (acceptanceDateTime, UTC),
     retrieval time (UTC), URL, HTTP status and sha256 — the point-in-time fields G-05 needs;
  4. optionally counts filings inside a date window (e.g. last year's equivalent of the scored run).

SEC fair-access rules (https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data): declare a
User-Agent with contact details and stay at or below 10 requests/second. This script waits 0.2 s between requests
(<= 5/s) and refuses to run without a User-Agent. Content terms (https://www.sec.gov/privacy): "Information presented
on sec.gov is considered public information and may be copied or further distributed".

No keys, no signing, no ai-seeds calls. Output goes to data/edgar/<UTC stamp>/ (git-ignored, F-61).

Run from the team network:
  python tools/edgar_fetch.py --user-agent "Glasswing research <contact email>"
  python tools/edgar_fetch.py --forms 8-K,6-K --per-company 3 --window 2025-10-29:2025-11-12
  (or put SEC_USER_AGENT=... in the git-ignored .env, loaded automatically, or the environment)
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

try:  # read the git-ignored .env (SEC_USER_AGENT) if python-dotenv is installed (requirements.in)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Issuer CIKs for the five eligible bStocks (SKILL.md F-91). SK hynix: CIK 2120882, Nasdaq SKHY, files 6-K
# (data.sec.gov submissions, checked 2026-10-08, IDEA-009 §C.2). The script checks each name in the response.
ISSUERS = {
    "NVDAB": (1045810, "NVIDIA"),
    "GOOGLB": (1652044, "Alphabet"),
    "TSLAB": (1318605, "Tesla"),
    "MSFTB": (789019, "Microsoft"),
    "SKHYB": (2120882, "SK hynix"),
}
ITEMS_8K = {  # Form 8-K item numbers (SEC Form 8-K general instructions); used only to label output
    "1.01": "Material definitive agreement", "1.02": "Termination of material agreement",
    "1.05": "Material cybersecurity incident", "2.01": "Acquisition/disposition of assets",
    "2.02": "Results of operations (earnings)", "2.03": "Direct financial obligation",
    "2.05": "Exit/disposal costs", "2.06": "Material impairments", "3.01": "Delisting notice",
    "4.01": "Auditor change", "4.02": "Non-reliance on prior financials (restatement)",
    "5.01": "Change in control", "5.02": "Director/officer departure or appointment",
    "5.03": "Charter/bylaw amendment", "5.07": "Shareholder vote results", "7.01": "Regulation FD disclosure",
    "8.01": "Other events", "9.01": "Financial statements and exhibits",
}
SUBMISSIONS = "https://data.sec.gov/submissions/"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data/"
SPACING_S = 0.2

RAW = []
_last = 0.0


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def get(session, url, want_json=True):
    """GET with spacing and one retry on 429/503; never raises. Returns (status, body, error)."""
    global _last
    for attempt in (1, 2):
        wait = SPACING_S - (time.monotonic() - _last)
        if wait > 0:
            time.sleep(wait)
        rec = {"url": url, "fetched_utc": now_utc(), "attempt": attempt}
        try:
            r = session.get(url, timeout=30)
            _last = time.monotonic()
            rec |= {"status": r.status_code, "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest()}
            RAW.append(rec)
            if r.status_code in (429, 503) and attempt == 1:
                time.sleep(2.0)
                continue
            if r.status_code != 200:
                return r.status_code, None, f"HTTP {r.status_code}: {r.text[:200]!r}"
            if want_json:
                try:
                    return r.status_code, r.json(), None
                except ValueError:
                    return r.status_code, None, "not JSON"
            return r.status_code, r.content, None
        except requests.RequestException as e:
            _last = time.monotonic()
            rec["error"] = repr(e)[:300]
            RAW.append(rec)
            return None, None, repr(e)[:200]
    return None, None, "retry exhausted"


class _Text(HTMLParser):
    """Minimal HTML -> text (stdlib only): drops script/style, keeps block breaks."""
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(raw: bytes) -> str:
    p = _Text()
    p.feed(raw.decode("utf-8", errors="replace"))
    text = "".join(p.out).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def rows_from(block):
    """Turn the column-oriented 'recent' block of the submissions JSON into row dicts."""
    keys = ["accessionNumber", "filingDate", "acceptanceDateTime", "form", "items", "primaryDocument",
            "primaryDocDescription", "reportDate"]
    n = len(block.get("accessionNumber", []))
    return [{k: (block.get(k) or [None] * n)[i] for k in keys} for i in range(n)]


def filing_documents(index_html: bytes):
    """Rows of the filing index page (<accession>-index.htm): (type, file name, description).
    The page's document table has columns Seq | Description | Document | Type | Size."""
    out = []
    html = index_html.decode("utf-8", errors="replace")
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
        if len(cells) < 4:
            continue
        href = re.search(r'href="([^"]+)"', cells[2], re.I)
        if not href:
            continue
        name = href.group(1).split("/")[-1].split("?")[0]
        strip = lambda x: re.sub(r"<[^>]+>", "", x).strip()
        out.append((strip(cells[3]).upper(), name, strip(cells[1])))
    return out


def pick_document(form, docs, primary):
    """Prefer the first EX-99.x exhibit (press release / announcement) in HTML or text; else the primary document.
    `docs` are (type, name, description) rows from the filing index page."""
    readable = [d for d in docs if d[1].lower().endswith((".htm", ".html", ".txt"))]
    ex99 = sorted((d for d in readable if d[0].startswith("EX-99")), key=lambda d: d[0])
    if ex99:
        return ex99[0][1], f"{ex99[0][0]} per the filing index ({ex99[0][2] or 'no description'})"
    if not docs:  # index page unavailable: fall back to a file-name match
        return primary, "primary document (filing index not read)"
    return primary, "primary document (no EX-99 exhibit in the filing index)"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"),
                    help="required by the SEC: who you are + contact, e.g. 'Glasswing research you@example.com' (team name: Glasswing)")
    ap.add_argument("--forms", default="8-K,6-K", help="comma-separated form types to read (default 8-K,6-K)")
    ap.add_argument("--per-company", type=int, default=2, help="newest filings per company to read (default 2)")
    ap.add_argument("--window", help="YYYY-MM-DD:YYYY-MM-DD; count filings of --forms with filingDate in it")
    ap.add_argument("--no-text", action="store_true", help="list filings only; do not download documents")
    ap.add_argument("--names", default=",".join(ISSUERS), help="subset of " + ",".join(ISSUERS))
    args = ap.parse_args()
    if not args.user_agent:
        sys.exit("Refusing to run: the SEC requires a declared User-Agent with contact details. "
                 "Pass --user-agent or set SEC_USER_AGENT.")
    forms = {f.strip().upper() for f in args.forms.split(",") if f.strip()}
    window = tuple(args.window.split(":")) if args.window else None

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent, "Accept-Encoding": "gzip, deflate"})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path("data/edgar") / stamp
    (out / "docs").mkdir(parents=True, exist_ok=True)
    report = {"run_utc": stamp, "forms": sorted(forms), "window": window, "issuers": {}}

    for sym in [s.strip() for s in args.names.split(",") if s.strip()]:
        cik, expected = ISSUERS[sym]
        print(f"== {sym}  CIK {cik}")
        st, sub, err = get(session, f"{SUBMISSIONS}CIK{cik:010d}.json")
        if err:
            print(f"   submissions: {err}")
            report["issuers"][sym] = {"error": err}
            continue
        name = sub.get("name", "")
        rows = rows_from(sub.get("filings", {}).get("recent", {}))
        entry = {"cik": cik, "name": name, "name_ok": expected.lower() in name.lower(),
                 "tickers": sub.get("tickers"), "recent_filings": len(rows),
                 "recent_oldest": rows[-1]["filingDate"] if rows else None}
        print(f"   {name} {sub.get('tickers')}  name check: {'ok' if entry['name_ok'] else 'MISMATCH'}; "
              f"{len(rows)} recent filings back to {entry['recent_oldest']}")

        # older filing pages, only if the window reaches before the 'recent' block
        if window and rows and window[0] < rows[-1]["filingDate"]:
            for f in sub.get("filings", {}).get("files", []):
                if f.get("filingTo", "") >= window[0] and f.get("filingFrom", "9999") <= window[1]:
                    st2, more, err2 = get(session, SUBMISSIONS + f["name"])
                    if not err2:
                        rows += rows_from(more)

        chosen = [r for r in rows if (r["form"] or "").upper() in forms][: args.per_company]
        entry["latest"] = []
        for r in chosen:
            items = [i for i in (r["items"] or "").split(",") if i]
            rec = {k: r[k] for k in ("form", "filingDate", "acceptanceDateTime", "accessionNumber", "primaryDocument")}
            rec["items"] = {i: ITEMS_8K.get(i, "?") for i in items}
            print(f"   {r['form']:<5} filed {r['filingDate']}  accepted {r['acceptanceDateTime']}  "
                  f"items {','.join(items) or '-'}  {r['accessionNumber']}")
            if not args.no_text:
                acc = r["accessionNumber"].replace("-", "")
                base = f"{ARCHIVES}{cik}/{acc}/"
                st3, idx, err3 = get(session, f"{base}{r['accessionNumber']}-index.htm", want_json=False)
                docs = filing_documents(idx) if not err3 else []
                rec["documents_in_filing"] = docs
                doc, why = pick_document(r["form"] or "", docs, r["primaryDocument"])
                st4, raw, err4 = get(session, base + doc, want_json=False)
                if err4:
                    rec["document"] = {"url": base + doc, "error": err4}
                    print(f"         document: {err4}")
                else:
                    text = html_to_text(raw) if doc.lower().endswith((".htm", ".html")) else raw.decode("utf-8", "replace")
                    fname = f"{sym}_{r['accessionNumber']}_{doc}.txt"
                    (out / "docs" / fname).write_text(text)
                    rec["document"] = {
                        "url": base + doc, "chosen_because": why, "source_ts_utc": r["acceptanceDateTime"],
                        "fetched_utc": RAW[-1]["fetched_utc"], "http_status": st4,
                        "raw_sha256": hashlib.sha256(raw).hexdigest(),
                        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "text_chars": len(text), "saved_as": f"docs/{fname}"}
                    head = re.sub(r"\s+", " ", text)[:240]
                    print(f"         read {doc} ({why}); {len(text):,} chars of text")
                    print(f"         \"{head}…\"")
            entry["latest"].append(rec)

        if window:
            inwin = [r for r in rows if window[0] <= (r["filingDate"] or "") <= window[1]
                     and (r["form"] or "").upper() in forms]
            entry["window_count"] = len(inwin)
            entry["window_filings"] = [(r["filingDate"], r["form"], r["items"]) for r in inwin]
            print(f"   {window[0]}..{window[1]}: {len(inwin)} filing(s) of {sorted(forms)} "
                  f"{[(r['filingDate'], r['items']) for r in inwin]}")
        report["issuers"][sym] = entry
        print()

    (out / "report.json").write_text(json.dumps(report, indent=1, default=str))
    (out / "requests.json").write_text(json.dumps(RAW, indent=1))
    print(f"Saved {out}/report.json, requests.json and docs/ (git-ignored). Requests made: {len(RAW)}.")


if __name__ == "__main__":
    main()
