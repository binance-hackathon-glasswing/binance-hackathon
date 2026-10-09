# IDEA-015 — Response to IDEA-013/014 feedback on IDEA-012, and review of IDEA-014

- Date / author: 2026-10-09 / SYZ (requested); drafted by Claude (Cowork).
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** Changes no D-item, no code, no live behaviour.
- What: (A) which IDEA-013/014 findings against IDEA-012 are accepted, and the fixes; (B) a review of IDEA-014.
- Links: IDEA-010 §1; IDEA-012 §4.7, §8, §10; IDEA-013 R1–R8; IDEA-014; F-48, F-50, F-115, F-117; G-46; GAP-44, GAP-50, GAP-54, GAP-62, GAP-63; D-11, D-12; ledger README rule 5.

Labels: [V] checked here, [E] estimate, [O] opinion.

## A. Feedback on IDEA-012

**Checked [V]:** the submitted `docs/proposal/LARP_System_Architecture.pdf` says "LLM zone: authority over evidence only, never over trades", "The output schema cannot express a trade" and "the LLM has no trade authority; deterministic layers act". `tools/edgar_fetch.py`: `_Text.BLOCK` has no `td`/`th`; docs are saved with `write_text(text)` (locale encoding) while `text_sha256` hashes `text.encode()` (UTF-8). R4, R5 and R6 hold as stated.

### A.1 R4 (LLM trade authority) — accepted
IDEA-012 §8.3 (HOLD / EXIT / ENTER output) and §8.4 (vote on postures) contradict the submitted architecture, which IDEA-010 §1 had already corrected. Fix [O, draft]:
- LLM output per affected name, **no action field:** `evidence_id`, `impact` ∈ {adverse, favourable, immaterial}, `thesis` ∈ {intact, broken, unchanged}, supporting quoted spans, `uncertainty` note.
- Code verifies the spans against the source text (G-53) and applies a pre-registered map M, e.g.: verified adverse + thesis broken → EXIT; verified adverse on a name not held → ENTRY_BLOCK; anything else → HOLD. ENTER after an EXIT stays an open question (IDEA-012 §9).
- R-VOTE counts agreement on the assessment fields (`impact`, `thesis`, `evidence_id`), not on actions; M acts only on a ≥ 4/5 agreement.
- External wording follows IDEA-010 §1: "code decides, sizes and executes".

### A.2 R3 (round time is not an ingestion watermark) — accepted
N1 becomes: "an accession in the durable ingestion queue that has not been assessed". EDGAR polling keeps its own per-source cursor with an overlap/backfill window and deduplicates by accession ID; the cursor advances only after the filing is retrieved and queued; assessed IDs are tracked separately and pending items survive LLM failures.

### A.3 Voting critique (IDEA-014 §2) — partly accepted
- Not accepted: IDEA-012 §8.4 never treats 5/5 as an 80% success probability; it says vote share is a consistency measure and that call profitability cannot be told from luck in-run.
- Accepted: R-VOTE's purpose is stability (no flips on the same evidence), and that should be shown on fixed labelled filing fixtures (agreement, evidence correctness, latency) before voting is built in. R-VOTE stays draft until then.

### A.4 Other IDEA-013 findings
R1/R2 target IDEA-010/011; R5–R8 are tool defects (owners in GAP-63). One consequence for IDEA-012: by R1, the −15% portfolio-floor exit (§8.2 H6) is also blocked by a hard signing halt (version/address/nonce mismatch); the floor bypasses entry filters only.

## B. Review of IDEA-014

**Agreed [O]:** costs before prediction; one frozen baseline; evaluation against the baseline, not zero; vetoed allocations held as cash with missed upside charged; no credit for price moves before detection; extraction of what is new rather than sentiment; no tuning on dev-wallet P&L (G-46, F-117). Arithmetic in §3 checks: 4 × 25 × 2 × 0.001 = 0.20 USDT = 0.10% of 200 USDT.

### B1. No default for the expected inconclusive outcome (main gap)
The promotion gate (positive lower confidence bound on paired net return, untouched post-cutoff rights-cleared data) cannot be met before the Oct 26 freeze: five issuers produce at most a few dozen material 8-K/6-K events in any post-cutoff window [E], far below what a paired test needs (IDEA-012 §4.7 found an MDE of ≈ 15–25 bp even at 100–150 samples). IDEA-014 keeps an "inconclusive fallback" but does not say what it is. Recommended [O]: decide now that, on inconclusive, v1.0 ships a **bounded exit-only overlay** (verified adverse evidence → EXIT / ENTRY_BLOCK via map M, A.1), justified by the declared architecture and risk control, and stated in logs and the deviations register (GAP-62) as **not validated for edge**. The alternative (overlay off) leaves the declared LLM layer inert.

### B2. Drop Variant A (execution timing) as an experiment
IDEA-014 §3's own arithmetic gives ≈ 0.1% of equity; at ≤ 1 rebalance per session this is undetectable (same conclusion as IDEA-012 §4.7). Instead, set a fixed execution rule from the quote/cost dataset (e.g. trade at the first round whose quoted cost ≤ the measured median for that name and size, with a deadline; mandatory risk exits never wait). Cost data is non-P&L evidence, so this is allowed during development (ledger README rule 5).

### B3. Do not gate quote collection on R7
R7 only changes a diagnostic message. R8 matters: an HTTP-date `Retry-After` crashes a long-running logger. Fix R8, then start the 24/7 quote + `openState` logger from the team network now (the Cowork device shell cannot reach the host, IDEA-012 §1); fix R7 in parallel.

### B4. EDGAR is structurally late for earnings
Earnings 8-Ks (item 2.02) typically follow the newswire release [E, to measure: release time vs `acceptanceDateTime` on the five issuers' past filings]. The tradable reaction has largely happened at detection, which makes IDEA-014 §1.3's test harder and supports exit-only use.

### B5. Novelty without consensus data
With no licensed consensus estimates, "what is new" for earnings is limited to comparisons with prior guidance and prior filings. IDEA-014 correctly forbids invented consensus; the limit should be stated in the extraction schema and in the deviations note.

### B6. The baseline decides most of the result
Exposure and concentration (D-12) dominate outcome variance; the overlay is small next to them. D-12 and the baseline spec should be settled before the dev phase starts on Oct 12, ahead of overlay work.

## C. Open items
- Rewrite IDEA-012 §8.3/§8.4 rules per A.1/A.2 in the spec that supersedes them (D-11). Owner: SYZ.
- Decide the inconclusive default (B1) with D-11/D-12. Owner: team (SYZ to raise).
- R8 fix and logger start (B3): GAP-63 / GAP-44 / GAP-50 owners.
- R5/R6 fixes in `tools/edgar_fetch.py`: SYZ (GAP-63).
- Labelled filing fixtures for the vote check (A.3): SYZ, before R-VOTE is built.
