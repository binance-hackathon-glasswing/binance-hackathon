# IDEA-022 — Review of the pulled engine design and research scripts

- Date / author: 2026-10-10 / Codex, requested by Keegan.
- Status: open; review findings, not policy adoption or trading authorization.
- Scope: fast-forward pull from `1f86cc4` to `3cb8765` (12 commits, including merges; 16 changed files). Review of the new IDEA-015..021 documents, related specification changes and all three new `tools/idea018/` scripts.
- Why: distinguish corrected design contracts from implementation evidence and identify remaining errors in the research calculations.
- Cost / risk: source review only; no private probe data or credentials inspected, no market simulation rerun, no API, signing or ai-seeds calls.
- Links: IDEA-013, IDEA-017..021; GAP-37, GAP-63..66.
- Labels: [V] observed in the pulled source; [I] consequence inferred by tracing the source; [O] recommendation. No independent reproduction of the historical market measurements or verification of the literature claims is claimed.

## 1. New findings

### R1 [P2] Reset the daily-loss anchor before the midnight interval

**Location:** `tools/idea018/mc_run.py:83-86`.

[V] `calendar()` defines `NEWDAY[t]` using the start of the interval. `run()` first applies that interval's return, then copies the resulting equity into `day_eq` and clears the daily halt. [I] A portfolio that is flat before midnight, loses 4% during 00:00-01:00 UTC and is flat thereafter has its loss absorbed into the new anchor; the 3% daily-loss flag never fires. This understates daily-halt incidence and can admit later simulated purchases that the declared ladder would block. [O] Set the day-start equity and reset the latch at the interval boundary before applying the interval's return; make the simulated check/trade timestamps explicit.

### R2 [P2] Preserve time adjacency in the spread estimators

**Location:** `tools/idea018/analyse_candles.py:115-119`; related `roll()` at 99-101 and `ar_spread()` at 103-108.

[V] Individual hourly/minute returns are filtered for adjacent bars, but their timestamps are then discarded. `roll()` pairs adjacent entries of the resulting array, including entries on opposite sides of a missing-data gap. Filtering to RTH or weekend returns also joins separate sessions. `ar_spread()` pairs adjacent observed bars without any duration check, including the large hole the variance calculation excludes. [I] The reported covariance, autocorrelation and spread proxies therefore include pairs that are not consecutive at the stated sampling interval. This is particularly relevant to the sparse minute series and any cost conclusion based on these proxies. [O] Carry timestamps through estimation, form lag pairs only within uninterrupted runs at the requested interval, and require both returns to satisfy the category filter. Report valid pair counts; distinguish an intentional transaction-time estimator from a clock-time estimator.

### R3 [P2] Keep cross-session gap returns out of category variance estimates

**Location:** `tools/idea018/analyse_candles.py:72-75`; related `tools/idea018/variants.py:26-29`.

[V] Every gap up to 48 hours contributes its entire squared return and elapsed-hour count to `cat(b)`, the category of the ending bar. [I] For example, a gap from the bar starting at 14:00 ET to the bar starting at 17:00 ET covers both regular and after-hours close-to-close intervals, but all three hours and the entire squared return go to after-hours. Dividing by elapsed hours does not recover the unobserved returns or their session allocation. This contaminates the category ratios subsequently hard-coded as `PROF` in `mc_run.py`. [O] Use contiguous one-hour intervals for the category estimate, disclose missing coverage, and report gap returns separately. Treat multi-hour attribution as an explicit modeling assumption if retained; do not present it as measured session variance. `variants.py` needs the same treatment for its normal modes; retain its explicitly labeled seven-day-hole reproduction as historical reproduction only.

## 2. Design and readiness assessment

- [V] IDEA-021 supplies corrected engine contracts, acceptance cases and a component allocation. Its wallet-wide nonce barrier, action-specific recovery, durable audit delivery and prohibition on timeout-to-buy address the corresponding unsafe assumptions in IDEA-020. Those older assumptions are explicitly corrected by IDEA-020 §10; they are not new findings here.
- [V] The pulled update contains research scripts and specifications, not an implemented production engine. IDEA-021's runtime acceptance cases remain NOT RUN. The allocation in §8 does not establish actual team availability (GAP-37) or close implementation/rehearsal work (GAP-65).
- [V] IDEA-013's existing tool defects remain tracked in GAP-63. IDEA-021 C07 already identifies omitted terminal-liquidation gas in simulated drawdown; this review does not claim that as a new discovery.
- [O] Resolve R1-R3 and C07 before reusing the affected statistics for a policy comparison. Record any rerun as a new, prospectively registered experiment and append corrections to historical results rather than overwriting them. None of these findings establishes the size or direction of a change in expected profit.

## 3. Verification and remaining work

Verification scope set before checks: all three new scripts must parse as Python; the review-only diff must pass whitespace checks and contain only this entry, its ledger row and its backlog item. These checks do not validate statistical estimates or runtime behavior. The examples in §1 are static source traces, not executed regression tests. No experiment is run by this review.

- 2026-10-10 verification: Python AST parsing passed for `analyse_candles.py`, `mc_run.py` and `variants.py` without importing or executing them. `git diff --check` passed for the tracked review changes; the staged check covers the new entry before commit. Only the three planned documentation files were changed. Runtime, market-data and statistical regression tests remain NOT RUN.

Remaining: fix R1-R3 and add deterministic fixtures for a midnight loss, lag pairs separated by missing bars/session filters, and a gap crossing session categories. Suggested owner: Keith (simulation/analytics), reviewer Yao Zhu, following IDEA-021 §8; availability remains unconfirmed under GAP-37. Recorded in GAP-66. Existing engine and credential/funding readiness gaps remain open; this review does not verify balances or onboarding completion.

- 2026-10-10 correction (Keith/Codex; PR #5 review): R1-R3 source repairs are implemented: midnight anchor precedes the interval return, lag/AR pairs retain exact timestamp adjacency, and only contiguous hourly returns enter session variance while gaps are reported separately. IDEA-026 §4 records pushed-code deterministic counterexamples among 48 passing tests. Existing historical statistics are retained, not numerically corrected; Keith owns the prospective rerun/evidence integration with Yao Zhu reviewing, so GAP-66 remains open.
