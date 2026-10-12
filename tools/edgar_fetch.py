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

2026-10-10 corrections (IDEA-013 R5/R6, IDEA-025): HTML is converted by larp.intelligence.text, which keeps
table-cell boundaries (" | ") instead of concatenating adjacent cells; saved text is written as explicit UTF-8
bytes ("\n" newlines, NFC) and `text_sha256` is the SHA-256 of exactly those saved bytes on every platform.
The runtime ingestion path is larp/intelligence/ingest.py; this script stays a research fetcher.

Run from the team network:
  python tools/edgar_fetch.py --user-agent "Glasswing research <contact email>"
  python tools/edgar_fetch.py --forms 8-K,6-K --per-company 3 --window 2025-10-29:2025-11-12
  (or put LARP_SEC_USER_AGENT=... (legacy SEC_USER_AGENT) in the git-ignored .env, loaded automatically, or the environment)
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for larp.intelligence
from larp.intelligence.text import document_text  # noqa: E402

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
        except OSError as e:  # requests.RequestException subclasses IOError (OSError)
            _last = time.monotonic()
            rec["error"] = repr(e)[:300]
            RAW.append(rec)
            return None, None, repr(e)[:200]
    return None, None, "retry exhausted"


def html_to_text(raw: bytes) -> str:
    """Filing bytes -> portable text with table-cell boundaries (larp.intelligence.text)."""
    return document_text(raw, "document.htm", None).text


def save_document_text(path: Path, raw: bytes, name: str, content_type=None) -> dict:
    """Write the exact portable UTF-8 bytes and hash those same bytes (IDEA-013 R6)."""
    saved = document_text(raw, name, content_type)
    path.write_bytes(saved.saved_bytes)
    return {"raw_sha256": saved.raw_sha256, "text_sha256": saved.text_sha256, "text_bytes": len(saved.saved_bytes),
            "text_chars": len(saved.text), "text_encoding": "utf-8", "source_encoding": saved.encoding,
            "decode_lossy": saved.lossy, "text_sha256_basis": "exact saved file bytes"}


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
    try:  # Credentials/configuration are loaded only by the CLI, never helper imports.
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user-agent", default=os.environ.get("LARP_SEC_USER_AGENT") or os.environ.get("SEC_USER_AGENT"),
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
    if (os.environ.get("LARP_SEC_USER_AGENT") and os.environ.get("SEC_USER_AGENT")
            and os.environ["LARP_SEC_USER_AGENT"] != os.environ["SEC_USER_AGENT"]):
        sys.exit("Refusing to run: LARP_SEC_USER_AGENT and SEC_USER_AGENT disagree.")
    import requests  # imported here so the helpers above can be tested without the dependency
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
                    fname = f"{sym}_{r['accessionNumber']}_{doc}.txt"
                    saved = save_document_text(out / "docs" / fname, raw, doc)
                    rec["document"] = {
                        "url": base + doc, "chosen_because": why, "source_ts_utc": r["acceptanceDateTime"],
                        "fetched_utc": RAW[-1]["fetched_utc"], "http_status": st4, **saved,
                        "saved_as": f"docs/{fname}"}
                    text = (out / "docs" / fname).read_bytes().decode("utf-8")
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

    (out / "report.json").write_bytes(json.dumps(report, indent=1, default=str).encode("utf-8"))
    (out / "requests.json").write_bytes(json.dumps(RAW, indent=1).encode("utf-8"))
    print(f"Saved {out}/report.json, requests.json and docs/ (git-ignored). Requests made: {len(RAW)}.")


if __name__ == "__main__":
    main()
