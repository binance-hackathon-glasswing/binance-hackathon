# IDEA-029 — Runtime news and event sources beyond EDGAR

- Date / author: 2026-10-10 / Keegan (drafted with Claude)
- Status: open (research and recommendation; no source is adopted, fetched into the repo or added to a manifest)
- ID note: IDEA-024–028 are used on open PR branches (PR #3, PR #4), so this entry takes IDEA-029.
- What: which sources, besides SEC EDGAR, the agent could read at runtime for news and scheduled events on NVDAB, GOOGLB, SKHYB, TSLAB and MSFTB, checked against the contest's data rules.
- Builds on, does not repeat: [IDEA-009](IDEA-009.md) §C.2 (runtime text-source comparison: EDGAR **use**; issuer newsrooms, newswires and hosted LLM web search **exclude**; GDELT and OpenDART optional), [IDEA-001](IDEA-001.md) §§11–15 (kit-first decision; EDGAR off hold for runtime use; source-rights review; free training-source register) and IDEA-007 §§1, 6. Scope here is runtime (live) use only, not training.

## 1. Tests every source must pass

From the rules, not preferences:

1. **Rights** [RULE: F-32, F-63, F-71]: "Hold the rights to every data source"; "no source you aren't authorized to use". A prize contest with a team of four is not "personal use".
2. **Audit disclosure** [RULE: F-49 (c)]: winners hand over "complete model inputs and outputs". A source whose terms forbid sharing data or derived results with third parties conflicts with this unless the provider agrees in writing.
3. **Point in time** [G-05]: each item needs a source timestamp and our retrieval time. Anything later than the decision time is rejected.
4. **Clean information** [G-10]: no human-authored market views in the agent's context during the scored run. Commentary and analyst notes are out even when licensed. Facts, filings and official releases are in.
5. **Version freeze** [F-114, F-117]: whatever is chosen must be in the build registered at final activation. A source cannot be added during the scored run.

## 2. Findings (checked 2026-10-10)

Labels: [PRIMARY] the provider's own page, read today; [SECONDARY] third-party description; [NOT FOUND] the terms could not be read.

### 2.1 Usable: official sources, public domain or open licence, timestamped

| Source | What it adds | Terms | Timestamps / access | Verdict |
|---|---|---|---|---|
| **EDGAR "latest filings" Atom feed** (`sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom`, filterable by CIK and form) [PRIMARY: sec.gov/about/rss-feeds] | Faster discovery of new 8-K / 6-K for the five CIKs than polling each submissions JSON | Same as EDGAR (IDEA-001 §15: "may be copied or further distributed") | Acceptance time per entry; same fair-access rules (declared User-Agent, ≤ 10 req/s) | **Use** as the trigger; still read the filing itself through the existing EDGAR path |
| **SEC press, litigation-release and trading-suspension RSS** (`sec.gov/news/pressreleases.rss`, `…/litigation-releases/rss`, `…/trading-suspensions/rss`) [PRIMARY: same page] | Enforcement actions or suspensions naming one of the five issuers | sec.gov dissemination policy | RSS item dates; feed update frequency not stated | **Use**, filtered to the five issuer names |
| **Federal Register API** (`federalregister.gov/api/v1/documents.json`, agency `industry-and-security-bureau`) [PRIMARY: live call today returned 2,987 BIS documents, no key sent] | **Export controls**: BIS rules on advanced chips and memory move NVDA and SK hynix (example in today's results: a 2026-09-24 BIS rule on polysilicon stockpiling). Also USTR / Commerce tariff notices | US-government work, generally public domain (17 U.S.C. §105). IDEA-001 §14 left the international (Singapore) scope of US public domain open | Publication date and a **public-inspection** copy, usually filed 8:45 a.m. ET the business day before publication [SECONDARY: 1 CFR part 17]; urgent BIS rules may be special filings. Web pages sit behind a bot check (`unblock.federalregister.gov`), but the API answered | **Use** for event flags (new BIS rule naming advanced computing or semiconductors). Logging the public-inspection time matters: that is when the market can first see it |
| **Federal Reserve press feeds** (`federalreserve.gov/feeds/press_monetary.xml`) [PRIMARY: feeds page; disclaimer page] | FOMC decisions and statements: scheduled market-wide event days | "in the public domain and may be copied and distributed without permission"; cite the Board | Item times; FOMC dates are published a year ahead | **Use as a calendar and event flag**, not as company evidence |
| **BLS release calendar and releases** (CPI, jobs) [PRIMARY: bls.gov/bls/linksite.htm] | Scheduled macro-risk days (IDEA-009 §2.1: macro announcement days carry most of the market premium) | "everything that we publish … is in the public domain" except prior-copyrighted images; cite BLS | Release times fixed in advance (08:30 ET) | **Use as a calendar** |
| **European Commission press releases** (antitrust and DMA decisions on Alphabet and Microsoft) [PRIMARY: commission.europa.eu/legal-notice_en] | Fines and DMA non-compliance decisions are material for GOOGLB and MSFTB | CC BY 4.0 by default (Commission Decision of 12 Dec 2011); credit and indicate changes; third-party material and logos excluded | Press release date and time (CET/CEST) | **Use**, with attribution kept in the audit record. Feed or API access not yet checked |

### 2.2 Conditional: useful, but one check is still open

| Source | What it adds | Open check |
|---|---|---|
| **Nasdaq Trader trade-halt RSS** (`nasdaqtrader.com/rss.aspx?feed=tradehalts`) [PRIMARY: feed and field-code pages] | Halt time and reason for the underlying share: T1 "news pending", T2 news released, LUDP / M volatility pauses, MWC1–3 market-wide circuit breakers. A hard fact for a "don't trade into a halt" rule | Described as a "free service"; at most one query a minute. **Its Terms & Conditions PDF was not read.** Read it before use; it is served over plain HTTP |
| **OpenDART** (SK hynix Korean disclosures) | Korean-language filings that may come out before the 6-K | Unchanged from IDEA-001 §13 / IDEA-009 §C.2: key required; contest use and audit disclosure not addressed; date-only `rcept_dt` |
| **Korea Customs Service 10-day export figures** | Chip exports for the first 10 and 20 days of each month, out around the 11th–13th and 21st [SECONDARY: news reports]; known to move SK hynix | Official release calendar, API and licence (probably KOGL on data.go.kr) **not verified** |
| **GDELT** | Discovery flags (URL, title, time) | Still on hold (IDEA-001 §11); IDEA-009 §C.2: may only block entries |

### 2.3 Exclude unless the provider agrees in writing

| Source | Why |
|---|---|
| **Finnhub** (company news) [PRIMARY: finnhub.io/terms-of-service, undated] | "strictly for personal use unless explicitly stated otherwise"; "can't be used by any business even internally without a written approval"; "not … redistribute or share access to data or derived results" (conflicts with F-49 (c)); "All data must be deleted should your subscription … end" |
| **Alpha Vantage** (NEWS_SENTIMENT) [PRIMARY in part: alphavantage.co/terms_of_service, via search; the PDF could not be parsed here] | Licence is "personal, non-commercial use" unless agreed in writing; commercial use is defined to include "investment analysis, research, testing, monitoring". Storage and redistribution clauses not read |
| **NewsAPI.org** [PRIMARY: newsapi.org/terms, 2020-04-30] | Developer plan "for development and testing … only", "cannot be used in a staging or production environment (including internally)"; no republishing of copyrighted material |
| **Tiingo, EODHD** | Already excluded on their terms (IDEA-001 §13) |
| **Benzinga** (direct, or via Massive/Polygon or Alpaca) | [NOT FOUND] Benzinga's terms page returned 403; Massive and Alpaca news terms not found. Secondary sources say storage and redistribution need a business contract. Benzinga also carries analyst commentary, which G-10 keeps out |
| **Marketaux** | [NOT FOUND] Terms page 404; only pricing seen (free tier: 100 requests a day) |
| Issuer newsrooms, newswires, hosted LLM web search | Excluded in IDEA-009 §C.2; nothing found today changes that. Issuer releases still arrive as 8-K / 6-K exhibits through EDGAR |
| Social media (X, Reddit, StockTwits) | **Not researched here.** It would also mostly be human-authored market views (G-10) |

## 3. Recommendation (not decided)

1. **Keep EDGAR as the only source of verified company claims.** Nothing licensed and auditable found today adds company news that EDGAR lacks; commercial news APIs fail the rights or audit test on their standard terms.
2. **Add three official event feeds as flags, not claims:** BIS rules through the Federal Register API (NVDAB, SKHYB), the European Commission's antitrust and DMA releases (GOOGLB, MSFTB), and SEC enforcement and suspension feeds. Use the EDGAR Atom feed only to detect new filings sooner.
3. **Add a scheduled-event calendar** from public-domain sources (FOMC, CPI, jobs) plus each issuer's announced earnings date. Earnings dates are announced in company releases that reach EDGAR or IR pages; record each date with its source and retrieval time, entered as configuration before the freeze. A calendar of dates is a fact, not a market view (G-10).
4. **Before relying on them:** read the Nasdaq halt-feed T&C; check the Korea Customs data licence; decide whether US-government public domain is enough for use from Singapore (IDEA-001 §14 open point).
5. **If the team wants a commercial news feed anyway,** the request to the vendor must name: a four-person team, prize-contest use in an automated trading agent, retained raw copies for the audit, and disclosure of inputs to the organisers (F-49 (c)). Without written agreement to all four, do not use it (IDEA-001 §13 makes the same point for price vendors).

Every adopted source needs a licence-register row (GAP-23), a line in the manifest's services list (F-61) and acceptance-time / retrieval-time logging (G-05). Owners suggested in IDEA-001 §13 (source rights: Isaac; audit and retention: Keegan; evidence agent: Yao Zhu) — suggestions, not assignments.

## 4. Limits of this research

- Desk research on 2026-10-10. The only live call was one Federal Register API request; no feed was polled over time, so latency and reliability are unmeasured.
- Terms pages change. Each one must be re-read and its hash stored when a source is adopted.
- Alpha Vantage's terms PDF could not be parsed here; Benzinga, Marketaux and the Massive/Alpaca news terms could not be read; the Nasdaq T&C PDF was not opened.
- Whether any of these events helps returns is untested. IDEA-009 §2.1 and IDEA-005 R4 still apply: the evidence supports text as a veto or exit signal, not as proof that a veto adds value.

## Sources

- SEC RSS feeds: https://www.sec.gov/about/rss-feeds
- Federal Register API: https://www.federalregister.gov/reader-aids/developer-resources/rest-api ; live call https://www.federalregister.gov/api/v1/documents.json?conditions[agencies][]=industry-and-security-bureau
- Public inspection timing: https://law.cornell.edu/cfr/text/1/part-17/subpart-C
- Federal Reserve feeds and disclaimer: https://www.federalreserve.gov/feeds/feeds.htm ; https://www.federalreserve.gov/disclaimer.htm
- BLS copyright: https://www.bls.gov/bls/linksite.htm
- European Commission legal notice: https://commission.europa.eu/legal-notice_en
- Nasdaq Trader halts: https://www.nasdaqtrader.com/Trader.aspx?id=TradeHaltRSS ; https://www.nasdaqtrader.com/Trader.aspx?id=TradeHaltCodes
- Finnhub terms: https://finnhub.io/terms-of-service
- Alpha Vantage terms: https://alphavantage.co/terms_of_service
- NewsAPI terms: https://newsapi.org/terms
- Marketaux pricing: https://marketaux.com/pricing
- Alpaca news API: https://alpaca.markets/docs/news-api
- Korea 10-day exports (example report): https://www.koreatimes.co.kr/economy/20260713/exports-up-54-in-first-10-days-of-july
