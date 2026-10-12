# IDEA-012 — Fresh-start review: "LLM after the close, harness at the open"

- Date / author: 2026-10-09 / SYZ (requested); drafted by Claude (Cowork) with 3 literature subagents and 3 red-team subagents. Deliberately independent of IDEA-001..011's ideas; uses only facts (SKILL.md F/Q items, kit), the submitted proposal and new measurements in §1.
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** Changes no D-item, no code, no live behaviour.
- What: SYZ's plan — after the US close an LLM agent gathers data and predicts the next session; at the open a deterministic harness trades and "manages fluctuations" with heuristics (or a fast model). Goal: maximise profit with consistent trading volume.
- Links: F-43, F-45, F-50, F-99, F-106, F-115, F-117, Q-03, Q-06, Q-32, Q-39, Q-40; proposal_answers.md (sizing, caps); LARP_System_Architecture.pdf (LLM has no trade authority)

Labels: [V] measured/checked here, [E] estimate, [L] literature, [O] opinion.

## 1. New measurements [V]
Source: `data/probe/candles_probe_20261007T142342Z.json`, on-chain 1h closes Sep 5 – Oct 7 2026 (600 bars per name), 1m bars Oct 7.
| Name | Share of hourly variance outside US regular hours | Lag-1 autocorr (all / weekend) | VR(4h/1h) | Roll spread 1h / 1m |
|---|---|---|---|---|
| NVDAB | 77% | −0.34 / −0.47 | 0.42 | 56 / 43 bp |
| GOOGLB | 79% | −0.26 / −0.41 | 0.69 | 38 / 21 bp |
| SKHYB | 73% | −0.10 / −0.18 | 0.84 | 39 / 23 bp |
| TSLAB | 75% | −0.08 / −0.38 | 0.94 | 25 / 13 bp |
| MSFTB | 82% | −0.29 / −0.42 | 0.60 | 43 / 45 bp |
- Pre-market (04:00–09:30 ET) alone holds 32–51% of hourly variance; trades print every hour incl. weekends.
- Negative autocorrelation + VR < 1 = bid-ask bounce, not tradable reversion for a taker. Roll spreads are print-based estimates, not quotes.
- `tools/probe_quote.py` run from the Cowork device shell failed (ProxyError: web3.binance.com not reachable from that VM); quoted spreads and off-hours `openState` remain unmeasured (GAP-50, Q-32). Run it from the team network.

## 2. Literature (subagent summaries; primary sources cited in the session) [L]
- Short-horizon large-cap edges are ≤ ~10 bp/day on the long leg: overnight drift 2–5 bp/day (Cliff-Cooper-Gulen; Kelly-Clark), intraday momentum ~2.6 bp/day index-level only (Gao et al. 2018; Baltussen et al.), daily reversal ≈ 0 for large caps in calm markets and half is bounce (Nagel 2012), PEAD gone in large caps since 2006 (Martineau 2022), LLM news long leg ~8 bp/day and "unprofitable at 20 bps round-trip" (Lopez-Lira & Tang v6). Round trip here ≈ 30–85 bp incl. gas.
- Stops/take-profits lower mean return under IID and more so under negative autocorrelation and costs (Kaminski & Lo; Lo & Remorov; Dai et al.). Only wide (≥ 10%) disaster stops cut drawdown without large cost.
- Live LLM-agent studies (StockBench, LiveTradeBench, Agent Market Arena, DeepFund, AI-Trader): short-window rankings are driven by exposure and market regime; more trading hurt; model choice mattered less than the harness; no primary source shows > 52–55% next-day hit rate on single mega-caps.
- Tokenized stocks: off-hours token moves partly predict the underlying's next open (+0.28% per 1% move; Cong et al. 2026 WP); overnight token moves tend to reverse at the open.

## 3. Verdict on the plan [O]
Keep the split (slow LLM brain, fast deterministic hands) — it matches the submitted architecture. Three parts are wrong:
1. **Timing.** "Close" and "open" are not boundaries for 24/7 tokens; acting at 09:30 ET acts after the pre-market has priced the news.
2. **Harness job.** "Managing fluctuations" = paying the spread on bounce. Est. drag of 2 intraday round trips/day on half the book ≈ 11 × 2 × 0.5 × 50 bp ≈ 5.5% of equity [E].
3. **Volume as a goal.** Not scored (F-50); organisers only want regular activity (F-115). Each extra round trip costs about as much as the whole run's expected drift.
The biggest controllable lever for rank is exposure and concentration, not prediction.

## 4. Recommended changes [O]
1. **Harness = execution + guardrails only.** No intraday stops, take-profits or mean-reversion rules; no fast predictive model. One wide portfolio floor (e.g. −15% from peak → cut gross) instead of per-name stops (SKHY's 11-session σ ≈ 17–20% fires per-name stops on noise). Note: proposal_answers.md declares a 3%/8%/12% ladder — changing it needs a version event in the dev phase with a stated reason.
2. **LLM cadence on the token's 24/7 clock.** Scheduled assessment rounds (e.g. ~08:00 ET after the pre-market, and after the close) plus triggers on new 8-K/6-K filings for the five issuers. The LLM keeps evidence authority only (architecture PDF): it outputs assessments/postures; code maps them to target weights and sizes. Debounce any price trigger (bounce).
3. **Exposure to the declared caps.** Toy tournament sim (24 rivals, shared market factor; field assumptions are guesses) — P(top 3): 70% diversified 0.002–0.09; 80% inverse-vol diversified 0.005–0.15; **80% gross in 4 high-vol names at 20% each 0.07–0.27**; 95% in 2–3 names 0.18–0.35 (breaks the proposal's ≤ 20%/name and ≤ 80% gross caps → misrepresentation risk). Expected return is ~the same for all; only variance changes. The declared sizing formula gives ≈ 42–54% gross; moving to the caps is a version event in the dev phase.
4. **Activity without churn.** ≥ 1 logged round per scheduled slot; at most one executed rebalance/rotation per session, only if its size ≥ the gas-based minimum (≈ 15–25 USDT). Est. cost ≈ 0.3% of equity over the run [E].
5. **No "reduce before events."** Announcement days carry much of the equity premium (Savor & Wilson 2013). De-risk only on a material adverse filing the LLM cites by ID.
6. **End of run.** Conditional lock-in: if return ≥ ~+6% by Nov 10, flatten; otherwise flatten in the last session that is safely inside the window. The window may end Nov 11 16:00 UTC (IDEA-010 §2, [I]), so plan the final flatten for the Nov 10 US session unless Q-06 is answered.
7. **Drop basis-aware execution timing.** Power: ~100–150 effective samples by the freeze → minimum detectable ≈ 15–25 bp, larger than any plausible edge; also needs a licensed real-time underlying feed.
8. **Measure now:** quote logger (buy/sell, 25/50 USDT, all names, every 15 min, 24/7) and `openState` logger from the team network; throttle it during the run so it never competes with execution for rate limits.

## 5. Logging consequences [O]
- Every broadcast (swap, revert, BNB top-up) belongs to exactly one round log: an execution round whose `input` carries the parent assessment ID, target, quote and gate values, whose `cot` states the rule (F-106 (a)), and whose `orders` carry the `tx_hash`. Assessment rounds carry no hashes. Write the record locally before signing.
- Single in-flight transaction per wallet; never sign a new nonce while one is pending; restart reconciles pending hashes first.

## 6. Open blockers (unchanged facts)
Q-03 (first BNB), Q-06 (window timestamps), Q-32 (off-hours tradability), Q-39 (scoring weights), Q-40 (auto-restart).

## 7. Correction to a subagent claim
- 2026-10-09 (Claude): one red-team subagent said SK hynix is not an SEC filer; IDEA-009 §C.2 records it as CIK 2120882 (Nasdaq SKHY, files 6-K). The claim is wrong.

## 8. Round rules and roles (2026-10-09, SYZ: "put that down as rules for now") [O, draft rules, not decided]
### 8.1 Rounds
- Scheduled LLM rounds every 4 h, 24/7 (America/New_York clock), plus triggered rounds. Triggered rounds are debounced (≤ 3 per 4 h).
- **R-NEW. A round may change targets only if the harness has flagged at least one new event since the previous LLM round.** New events (computed by the harness, never by the LLM):
  - N1 Filing: an EDGAR filing for one of the five issuers, `acceptanceDateTime` after the previous round, on the allowlist (8-K items 1.01, 1.02, 2.02, 2.05, 2.06, 4.02, 5.02, 8.01; 6-K for SK hynix), not already assessed.
  - N2 Confirmed move: smoothed price (median of recent 1m closes or quote mid) moved > 2× daily σ from its value at the previous round, on two checks ≥ 30 min apart; tagged single-name or market-wide (all five same sign).
  - N3 Scheduled release passed: a calendar item (GDP/PCE Oct 29, US midterms Nov 3, NFP Nov 6, CPI Nov 10, an eligible issuer's earnings release).
  - N4 State change: portfolio floor hit, a drift-band breach, a fill or revert since the previous round, or `openState` reopening with a queued decision.
  - Not new: sub-threshold moves, a filing already assessed, restated news, time passing, the LLM changing its mind on the same inputs.
- **R-HOLD. "Hold, no change" (HOLD_NO_CHANGE)** = targets identical to the previous round, `orders = []`. The LLM still runs: it reviews each thesis and writes a short review note, and the round is logged (`input` includes the event check with every N-flag false; `cot` the review; `output` HOLD_NO_CHANGE). If no N-flag is set, the harness overrides any other LLM output to HOLD_NO_CHANGE and logs the override. Invalid or missing LLM output also becomes HOLD_NO_CHANGE.
- Trade limits stay: ≤ 1 rebalance per session, gas-based minimum order, ±5 pp drift band.

### 8.2 Harness (deterministic)
H1 data: prices, smoothing, `openState`, EDGAR polling and filtering, event calendar, wallet state from chain · H2 recognition: N1–N4 flags, move classification · H3 scheduling and debounce · H4 LLM output gate: schema, citation check (EXIT/ENTER must cite an evidence ID), R-NEW/R-HOLD override · H5 sizing: postures → target weights (≈ 80% gross, ≤ 20% per name, 4 names), band, min order, ≤ 1 rebalance/session · H6 risk: −15% portfolio floor → gross ≤ 40%, never loosened; cash and BNB reserve · H7 execution state machine (openState gate, approve, re-quote, gas estimate, sign, broadcast, confirm; one tx in flight; no blind retries) · H8 end of run: conditional lock-in, final flatten · H9 logging: every round, WAL before signing, upload before 02:00 UTC, on-chain reconciliation · H10 ops: supervisor restart, LLM failover → HOLD_NO_CHANGE.

### 8.3 LLM (evidence authority only; never sizes, signs, sets limits or times orders)
L1 initial assessment per name at run start (include / avoid, with evidence) · L2 filing rounds (N1): fetch and read the filing, verify claims against the text, output HOLD / EXIT / ENTER per affected name with the filing ID, thesis and falsifier · L3 flagged moves without a filing (N2): look for evidence; EXIT only with a cited evidence ID, else HOLD · L4 release rounds (N3): assess the release's effect on each thesis · L5 scheduled rounds with no N-flag: HOLD_NO_CHANGE plus review note · L6 memory: one thesis per position, past calls and their outcomes.

### 8.4 Voting on new-event rounds (2026-10-09, SYZ) [O, draft rule, not decided]
- **Why "changing its mind on the same inputs" is not new:** with no new information the position's expected return is unchanged; a flip is sampling noise and costs a round trip (≈ 30–85 bp). No outcome is knowable at decision time, so "optimal" here means "the output the evidence most consistently supports", not "the one that will make money".
- **R-VOTE.** In every round with an N-flag set, run the same input k = 5 times (pinned, dated model snapshot; low temperature). A non-hold posture (EXIT / ENTER) for a name is acted on only if ≥ 4 of 5 samples agree on it and each agreeing sample cites an evidence ID. Otherwise that name is HOLD. Self-consistency / majority voting: Wang et al. 2022.
- Vote share (e.g. 5/5 vs 3/5) is the confidence measure; the model's stated confidence is not used (LLMs are overconfident).
- Do not rely on temperature 0 alone: API outputs are not fully deterministic, and a single fixed answer hides the disagreement the vote exposes.
- **Logging:** all k samples (inputs and reasoning) go into the round's log; the vote tally and the rule outcome go in `output` (winner deliverables require complete model inputs and outputs, F-49).
- **Checks:** dev phase (Oct 12–26) — agreement rate across the k samples, and stability when logged rounds are re-run on identical inputs (consistency, not profit). Profitability of calls cannot be told from luck in-run (11 sessions, few events); score each call afterwards against the net-of-cost return 1–5 days later.
- Cost: 5 samples × ≈ 90 rounds is small.

## 9. Open items (2026-10-09)
- Decide: how the 4 names are chosen at run start (draft: LLM may veto with evidence, code takes the 4 highest-vol of the rest) and whether ENTER after an EXIT is allowed (draft: only on a new event with cited evidence). Owner: team (SYZ to raise).
- Run `tools/probe_quote.py` and an `openState` logger from the team network (blocked from the Cowork VM, §1). Owner: unassigned.
- Version events needed before Oct 26 if adopted: sizing to the declared caps (§4.3) and the −15% floor replacing the 3/8/12% ladder (§4.1).
- Unchanged blockers: Q-03, Q-06, Q-32, Q-39, Q-40.

## 10. Corrections after review (append-only)
- 2026-10-09 correction (SYZ, drafted by Claude): IDEA-013 R4 accepted — §8.3 L2/L3 and §8.4 give the LLM trade authority, contradicting the submitted architecture PDF. Superseded by IDEA-015 A.1: assessment-only schema (no action field) + pre-registered code map M; R-VOTE counts assessment fields.
- 2026-10-09 correction (SYZ, drafted by Claude): IDEA-013 R3 accepted — §8.1 N1's "accepted after the previous round" can lose filings. Superseded by IDEA-015 A.2: N1 = unassessed accession in a durable ingestion queue with its own cursor, overlap window and accession dedup.
- 2026-10-09 note (SYZ, drafted by Claude): IDEA-014's voting critique partly accepted (IDEA-015 A.3): R-VOTE stays draft until checked on labelled filing fixtures. By IDEA-013 R1, §8.2 H6's floor exit is also blocked by a hard signing halt (IDEA-015 A.4).
- 2026-10-10 correction (SYZ, drafted by Claude): second review accepted in part (IDEA-016). (a) §8.1–8.2: safety actions (drawdown ladder, end-of-run flatten, hard-cap trims) need precedence over R-NEW/R-HOLD, R-VOTE, the rebalance cap, the band and the minimum order, while still passing integrity checks (IDEA-016 §3.1). (b) §4.1/§8.2 H6: the −15% floor is weaker than the declared 3%/8%/12% portfolio ladder and is withdrawn; keep the ladder; exposure increase (§4.3) deferred to D-12 (IDEA-016 §3.2). (c) §1: the ~75% off-hours variance share is roughly the off-hours share of time (81%) and is withdrawn as a finding; "bounce" is an interpretation (IDEA-016 §3.3). (d) §4.4: 0.3% excluded building and liquidating the book (0.24–0.68% of equity); a ±5 pp band (10 USDT) is below the minimum order (IDEA-016 §3.4).

- 2026-10-10 correction (Keith/Codex; PR #5 review): The historical hourly-variance/lag claims and ladder simulations are not corrected numerical evidence: IDEA-022 R1-R3 identify midnight anchoring, filtered lag adjacency and cross-session variance defects, and IDEA-021 C07 identifies omitted terminal-gas drawdown. Source repairs and deterministic regression evidence are appended in IDEA-026 §1/§4; original numbers remain historical until Keith coordinates a pre-registered rerun, reviewed by Yao Zhu.
