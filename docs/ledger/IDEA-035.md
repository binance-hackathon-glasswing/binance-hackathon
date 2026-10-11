# IDEA-035 — Team decisions 2026-10-11: PR #7 review answers and pre-live choices

- Date / author: 2026-10-11 / SYZ (team decisions relayed by SYZ; drafted with Claude)
- Status: open (decision record; B1 and the B5 stock mix decided later on 2026-10-11, §10; B7–B9 deferred to after system testing)
- What: the team's answers to Keegan's PR #7 question list (A1–A11 merge questions, B1–B11 team decisions, C1–C8 organiser questions; PR #7 comments of 2026-10-11 06:01 UTC) and to the backlog items GAP-02/03/04/05/35/62. Also records three stock-mix options for the new 80% invested target (§5), a red-flag severity proposal (§6), the features still missing before live trading (§7) and conflicts the decisions leave open (§8).
- Why: AGENTS.md requires every decision to be written down with an ID before the session ends. Several of these decisions change the submitted proposal and must reach the deviations register (GAP-62).
- Cost / risk: the 80% target (§5) roughly doubles market exposure compared with the declared sizing (≈ 42–54% gross, plan.md D-12). Several choices are deferred to "after system testing", and every one of them must be settled before final activation (Oct 27–29, F-14), because the registered build runs unchanged for the whole scored run (F-117).
- Links: PR #7; IDEA-033 (R15–R27), IDEA-034, IDEA-032 S1, IDEA-018 §4, IDEA-036 (hourly anchoring build); plan.md D-03, D-05, D-11, D-12; SKILL.md Q-03, Q-04, Q-06, Q-08, Q-32, Q-33, Q-35, Q-39, Q-40; GAP-02/03/04/05/13/35/37/44/49/51/52/62/64/65.

**Where this is recorded.** This branch (`codex/evidence-hardening`) has not yet received main's `a21d034` (A11). That commit also edits plan.md D-08/D-09/D-11, SKILL.md Q-03 and the GAP-51/56/57 lines, so this change leaves those lines alone to avoid merge conflicts. Annotate plan.md D-03, D-05, D-11 and D-12, SKILL.md Q-03 and the GAP-51/57 lines from this entry when main is merged in (A11). B4 (GAP-51) and B8 (GAP-57) are recorded only here until then.

## 1. PR #7 merge questions (A1–A11)

| Item | Decision | Effect |
|---|---|---|
| A1 · R15 review-job due time | Follow the recommendation | "First decision time of the session" is accepted for the merge; switch to the calendar's session open once the calendar port supplies it. |
| A2 · R16 evidence on a CONTEXT_UNAVAILABLE round, and replay | Follow the recommendation | Committing evidence on a failed-context round is kept. Replay of deterministic evidence-pipeline rounds is fixed (IDEA-033 R27). **Remaining from the recommendation:** a replay regression for a MANDATORY_REDUCTION round (the R27 tests cover SHADOW and CONTEXT_UNAVAILABLE only), and the recorded-port adapter for live rounds (GAP-65). |
| A3 · R17 strategy extraction | Passes | `accept_records` / `market_view` extraction accepted as behaviour-preserving. |
| A4 · R18 review attempts | Follow the recommendation | Any accepted result after the due time counts as an attempt for v1.0 (statements are SHADOW, B2). Follow-up under GAP-28: count only results of the statement's own review job. |
| A5 · R24 / GAP-09 support rule | Accept the recommendation | Answered by IDEA-034: a positive absolute after-cost return is required under every support rule, plus the R26 draw minimum. EXP-001 is not run for v1.0 (D-08). |
| A6 · ledger renumbering | Confirmed | IDEA-032 = proposed solutions, IDEA-033 = PR #7 review record. |
| A7 · W04 test import | Confirmed | Package-qualified `tests.execution_fixtures` import. |
| A8 · re-entry after a resolved latch | **The bot may buy again** | When an adverse finding is corrected or withdrawn at the source (`EVIDENCE_LATCH_RESOLVED`), the name becomes eligible again. This overrides the "no re-entry for the rest of the run" recommendation (IDEA-032 S1, IDEA-018 §4.2) and settles the re-entry part of GAP-64. Note: R25 reopens a resolved latch if a newer revision of its filing cannot be fully read, so re-entry also depends on that revision being read completely. |
| A9 · `INCOMING:` reservation | Clarification requested; explained in the PR reply | A pending buy records the tokens it expects as `INCOMING:<token>`, a claim rather than a settled balance, so the bot does not count or buy the same position twice. Nothing releases it yet because execution is still a fake port; settlement must release it (GAP-65). Recommendation unchanged: accept for the merge. |
| A10 · order amount convention | Follow the competition rules | BUY `amount` = USDT spent, SELL `amount` = tokens sold (kit `PROTOCOL.md:28`). |
| A11 · sync main's `a21d034` | Later | Do it after the merge, as an ordinary merge commit. Reminder kept in GAP-65's merge notes and here. |

Housekeeping (team statement 2026-10-11): the team agrees with the current decisions. At the time of writing, the PR's track boxes B–H were still unticked on GitHub and its 20 review threads unresolved; reviewers still tick their own tracks.

## 2. Pre-live team decisions (B1–B11)

| Item | Decision | Status |
|---|---|---|
| B1 · D-11 red flags | Classify each red flag by how serious it is, and set the action by class | **Proposal in §6, to confirm** (Keith + SYZ). |
| B2 · statement authority | Recommendation accepted: statements stay SHADOW for v1.0; `ENTRY_BLOCK` is not adopted | Decided. |
| B3 · D-09 token candles → sessions | Follow the recommendation: one bar per US regular session closing 16:00 ET, fixed in UTC; no Ondo extension of short histories; check GOOGLB/SKHYB first candle dates | Decided (implementation: Keith, review SYZ). |
| B4 · GAP-51 price-impact limit | Follow the recommendation: impact ≤ min(50 bp, 2 × logged median) and total entry cost (spread + impact + gas ÷ size) ≤ 50 bp; recorded as a deviation | Decided (values checked against quote-logger data by Isaac). |
| B5 · D-12 exposure | **Invest 80% of equity.** Unlike the current structure, where sale proceeds stay in cash, the bot reinvests until 80% of equity is invested. The method for choosing the stock mix is still to be picked (options in §5). | Target decided; stock-mix method open. Deviation from the declared sizing (GAP-62). |
| B6 · GAP-13 operating parameters | Set mathematically from the literature (inputs from measured quote costs, never from P&L) | Decided as a method; values still due. |
| B7 · GAP-64 trading policy | Wait until after system testing | Deferred, except re-entry (A8, decided). |
| B8 · GAP-57 / D-03 model | Claude or ChatGPT, chosen after system testing | Deferred. See §8.2 (cost and declaration). |
| B9 · deployment inputs | After system testing | Deferred. Reminder: S3 Object Lock COMPLIANCE retention cannot be shortened once set. |
| B10 · GAP-37 availability | Everyone is available (team statement) | Availability confirmed; the dated rota and backup cover remain under GAP-37. |
| B11 · logging a gas top-up | Log it, to be safe: its own round, `{symbol: "BNB", side: "BUY", amount: <USDT spent>, tx_hash}`, `cot` says it is a gas top-up | Decided (Keegan + SYZ, in GAP-46). |

## 3. Organiser items (C1–C8): team positions

These are team positions and working assumptions, not organiser answers.

| Item | Team position |
|---|---|
| C1 · Q-03 first BNB | BNB should be converted automatically from USDT. **Still open:** automatic top-ups solve every later top-up, but the first conversion is itself a transaction paid in BNB (F-93, Guide p.5). It needs some BNB in the wallet first, and adding our own is prohibited (F-25, F-64). See §8.1. |
| C2 · Q-39 scoring | Maximise profit, using the competition website's formula (final vs opening wallet equity, F-43), until the organisers say otherwise. |
| C3 · Q-04 valuation | Wallet equity; the bot sells everything to USDT before the end, so the valuation source matters only for drawdown. |
| C4 · Q-06 run window | Follow the published dates exactly: scored run Oct 29 – Nov 12 (F-15). Sell everything before the last day to be safe. Concretely: finish flattening by **Nov 11 15:00 UTC** (Nov 11 23:00 SGT), before Nov 12 starts in either UTC or SGT. That window matches IDEA-018 §4.6. |
| C5 · Q-40 restarts | The bot may restart itself automatically (same registered version, supervisor-driven, logged as an incident; no human action). Not confirmed by the organisers: F-114 says "no changes allowed — period" and does not name restarts. |
| C6 · Q-33 registration | Resolved per team statement: the GitHub repository registration is done. |
| C7 · Q-35 final-wallet secret | Yes: assume a new `AI_SEEDS_SECRET` for the final wallet. **Remind the team before final activation** (by Oct 26), GAP-52. |
| C8 · Q-32 trading hours | 24/7 (team position). The kit's instruction still applies: never place an order while `openState` is false (F-95). The guard stays in code, so the bot simply skips a round if a name is ever closed. |

## 4. Backlog items

| Item | Decision |
|---|---|
| GAP-02 (D-05 primary + fenced cold standby) | Decide after exploring AWS; **remind the team then**. |
| GAP-03 (three-tool limit) | Follow the newest changes; the proposal is outdated. The current assessor exposes exactly three tools: `fetch_document`, `prior_context`, `compare_facts` (`larp/intelligence/tools.py`, `TOOLS`). Feature lookup is internal context construction, not a tool. Recorded as a deviation under GAP-62. |
| GAP-04 (rehearsal) | Start the rehearsal about Oct 12–13, right after system testing. See §8.3: until the live blockers close, it can only run in shadow mode. |
| GAP-05 (Oct 22 cut line) | The team plans to finish everything on time and will name what to drop if it cannot. The missing features are listed in §7. |
| GAP-35 (hourly anchoring) | Keep it: anchor the logs hourly, as declared. Build record: IDEA-036. |
| GAP-62 (deviations) | The plan has changed from the proposal; follow the latest decisions and record each change in the deviations register. |

## 5. B5: 80% invested, reinvestment, and three stock-mix options

**What changes.** Today, when the bot sells a name it keeps the proceeds as cash, so gross exposure only falls over the run. Under B5 the bot keeps total holdings near 80% of equity: after a sale it buys other eligible names until it is back at 80%.

**Constraint from the declared caps** (plan.md "Declared values", G-21): ≤ 4 positions, ≤ 20% per name, ≤ 80% gross. With those caps, 80% invested is only reachable as **exactly four names at 20% each**. Any unequal weighting, or holding all five names, needs a cap change, and that change is a deviation (GAP-62). At the 200 USDT final funding (F-107), 20% is about 40 USDT per name.

**Rules that still apply after B5.** These are recommendations, not decisions:
- The 80% is a ceiling for *new buys*. Price moves can push holdings above it, and the bot does not sell just because of that drift, which would cost spread and gas.
- Reinvest only when holdings are below about 75% (a rebalance band), so small gaps do not trigger trades.
- Every reinvestment still passes the price-impact rule (B4), the minimum trade size (B6), `openState` (C8) and the loss controls. Daily loss ≥ 3%, or drawdown ≥ 8%, means no new positions. Drawdown ≥ 12% cuts gross to ≤ 40% (declared values).
- **No reinvestment during the end-of-run flatten window (C4).**
- Risk: at 80% in five correlated tech names, a 10% fall across the names costs about 8% of equity, which reaches the 8% stop on new positions. Under the declared sizing the same fall costs about 4–5%.

**Option 1: equal weight, four names at 20% (recommended).**
- How: hold four of the five names at 20% each. To pick the four:
  1. drop any name with an unresolved red flag (§6);
  2. then drop the name that is most expensive to trade (highest measured entry cost, B4). IDEA-018 §4.1 already identifies SKHYB as the likely one: it has the most expensive gas route (F-93) and the shortest history.
- After a sale, the freed 20% goes to the fifth name if it is eligible; otherwise it stays in cash.
- Why: needs no cap change and no estimation, and is the simplest to test and explain. With few assets and short histories, estimated weights rarely beat 1/N out of sample (DeMiguel, Garlappi & Uppal 2009, *Review of Financial Studies* 22(5); [PRIMARY, not re-checked this session]).

**Option 2: inverse-volatility weights across all five names.**
- How: weight each eligible name in proportion to 1 / (its trailing volatility), scaled so the total is 80%. Cap each name at 20% and give any excess to the others. This uses the D-09 token-candle volatility already being built (B3).
- Needs: "≤ 4 positions" raised to 5 (a deviation).
- Why: calmer names get more money, so the same 80% carries less risk of hitting the 8% drawdown stop. Basis: risk-parity and volatility-managed portfolios (Maillard, Roncalli & Teiletche 2010, *Journal of Portfolio Management* 36(4); Moreira & Muir 2017, *Journal of Finance* 72(4); [PRIMARY, not re-checked this session]).
- Caveat: with five names, a 20% cap and an 80% total, the cap often binds, and the weights end up close to equal.

**Option 3: momentum, the four strongest names at 20%.**
- How: rank the eligible names by trailing return (for example the last 60 sessions, matching the features window) and hold the top four at 20%. Re-rank at a fixed cadence, not every round.
- Why: momentum is a well-documented return pattern (Jegadeesh & Titman 1993, *Journal of Finance* 48(1); Moskowitz, Ooi & Pedersen 2012, *Journal of Financial Economics* 104(2); [PRIMARY, not re-checked this session]).
- Caveat, lowest confidence: that evidence comes from broad cross-sections over 3–12 month horizons, not five correlated names over two weeks. Re-ranking adds turnover and costs. IDEA-012 measured short-horizon token moves that mostly reverse.

**Recommendation:** Option 1 for v1.0. It fits the declared caps, adds no estimation risk, and can be built and tested before Oct 22. Option 2 is the alternative if the team accepts a cap change. Option 3 is not recommended without a pre-registered test.

## 6. B1: red-flag severity classes (proposal, to confirm)

This stays within D-11 (decided on main, `a21d034`): only verified 8-K Items 4.02, 1.05 and 2.06 on a held name may force an exit, and the LLM only assesses.

| Class | Red flags | Proposed action | Reason |
|---|---|---|---|
| **1 · Critical** | Item 4.02: past financial statements can no longer be relied on (restatement) | Sell the position (`DISCRETIONARY_EXIT`). No new buys while the latch is unresolved. Buying again is allowed once the finding is corrected or withdrawn (A8). | The clearest and rarest signal that the reported numbers were wrong (IDEA-032 S1 enables 4.02 first). |
| **2 · Serious** | Item 1.05: material cybersecurity incident. Item 2.06: material impairment. | No forced sale. No new buys or adds for the name for a fixed period (proposal: 5 sessions), then the block expires. The finding stays logged. | For very large issuers these filings often move the price little. A block with an expiry avoids B2's "blocks forever" problem. |
| **3 · Watch** | Statements: risks, guidance, attributed claims, future events | SHADOW: logged only, no effect on trading (B2). | No prospective test has passed. |

To decide: whether Class 2 gets the entry block at all (it is new behaviour; `ENTRY_BLOCK` as built has no expiry), and the block length. Each enabled class needs a versioned predicate record and verification fixtures (IDEA-018 §4.4) before Oct 22.

## 7. Features still missing before live trading (GAP-05)

The team asked to be told about missing features. Items marked **blocks trading** must exist before the bot can trade at all.

1. **Real execution path (blocks trading).** The runtime still uses a fake execution port. Needed:
   - wire W04 into commands and reservations;
   - release `INCOMING:` reservations in settlement (A9);
   - signer registry and release checks;
   - receipt, fill and gas settlement.

   Owner: Isaac + Keegan (GAP-65).
2. **Venue capability (blocks trading).**
   - The router ABI, encoded expiry and wallet nonce/finality are unproven.
   - Gas estimation fails before approval.

   Owner: Isaac (W08, EXP-005).
3. **First BNB plus automatic top-ups (blocks trading).** The first BNB is §8.1. Then: a top-up trigger and size, and a BNB floor of two transactions (GAP-49, B11).
4. **Official round logging (blocks trading).** The ai-seeds round/`cot`/`orders` contract, including crash-safe delivery. Without it every fill is flagged "fill without log" (F-101). Owner: Keegan (GAP-46).
5. **Entry inputs (blocks entries).** Entries are rejected today:
   - `INSUFFICIENT_60_SESSION_HISTORY` and `MISSING_MARKET_OR_BASIS` until the token-candle sessions are built (B3, D-09);
   - `DECLARED_DEPTH_INPUT_UNAVAILABLE` until the price-impact rule is built (B4, GAP-51).
6. **New sizing (blocks the decided behaviour).** Target 80%, reinvestment, and the stock-mix method chosen from §5 (B5).
7. **Red-flag classes wired to authority (blocks the decided behaviour).** §6. Evidence authority still defaults to SHADOW in code.
8. **Assessor model connected.** Claude or ChatGPT (B8), with the deterministic verifier; or the deterministic assessor if no model is chosen.
9. **Live sources switched on.** SEC contact User-Agent, dated terms captures (`terms_evidence_sha256` is null), artifact store outside Git, polling cadence (GAP-23/24).
10. **Automatic restart and an autonomous HALT.** Supervisor restart of the same version, logged as an incident (C5).
11. **End-of-run flatten schedule.** Sell everything by Nov 11 15:00 UTC, with no reinvestment in that window (C4).
12. **Hourly anchoring.** IDEA-036 (GAP-35).
13. **Hosting.** AWS account and region, database, backups, the audit archive with Object Lock, monitoring and alerts (B9; architecture-deployment.md steps 3–7).
14. **Final-wallet switch.** New wallet, its secret, a separate `.ai-seeds/` directory, refusal on an address mismatch (GAP-52, C7).
15. **Version manifest and deviations register.** Including §4 and §5 here (GAP-62).
16. **Live replay.** A recorded-port adapter so live rounds replay exactly (GAP-65, A2).

## 8. Conflicts and open points created by these decisions

1. **C1: the first BNB cannot come from automatic conversion.**
   - Converting USDT to BNB is a transaction, and every transaction pays its fee in BNB (F-93: "This swap itself also needs a little BNB for gas"). EXP-005 observed the dev wallet with 100 USDT and no BNB entry.
   - If the Oct 11 deposit included any BNB, automatic top-ups work from then on. If not, the first BNB must come from the organisers, because adding our own is prohibited (F-25, F-64).
   - Action: check the wallet's BNB balance. If it is zero, ask the organisers (Q-03).
2. **B8: model cost and declaration.**
   - IDEA-031 and GAP-57 assume an "authorised no-additional-cost model". Claude and ChatGPT APIs are paid, so the team needs either a budget or free credits.
   - The submitted proposal named an OpenAI model (T-12), so choosing ChatGPT keeps the declared service and choosing Claude is a deviation (GAP-62).
   - Both are assessment-only (D-11). Training on Claude outputs stays banned (Anthropic AUP, GAP-57), but assessment use is not training.
3. **GAP-04: a rehearsal from Oct 12–13 can only run in shadow mode.**
   - Shadow mode means real data, real decisions, logged rounds, no signing.
   - Signing needs the §7 items 1–4.
   - Every run with the dev wallet's ai-seeds credentials uploads logs that auditors see. It must be committed, manifested code with test rounds marked (never-do #13, F-103).
   - The proposal declared "5+ days including a weekend at minimum size". A shadow-only rehearsal is a deviation unless signing starts in time (weekends Oct 17–18 and 24–25).
4. **"After system testing" against the fixed dates.**
   - The organiser dates are fixed: development Oct 12–26 (F-13), final activation Oct 27–29 (F-14). The build registered at final activation runs unchanged (F-117).
   - B7, B8 and B9 therefore need answers by about Oct 22 (our parameter freeze), and code changes by about Oct 26.
   - System testing needs some policy and assessor to test with. Recommended: test with the current default policy and the deterministic assessor, then choose.
5. **C5 and C8 are team positions, not organiser answers.** Both are cheap to include in the organiser message alongside C1.

## 9. Reminders

| When | Reminder | Record |
|---|---|---|
| After PR #7 merges | Merge main's `a21d034` into `codex/engine-foundation` (A11); annotate plan.md D-03/D-05/D-11/D-12, SKILL.md Q-03 and GAP-51/57 from this entry | GAP-65 merge notes |
| After exploring AWS | Decide D-05 primary + fenced cold standby (GAP-02) | GAP-02 |
| By Oct 26, before final activation | Confirm the final wallet's new `AI_SEEDS_SECRET` (C7) | GAP-52 |
| Before enabling S3 Object Lock | Choose retention deliberately (it cannot be shortened later) | B9, GAP-36 |

## 10. Update later on 2026-10-11 (SYZ; drafted with Claude)

### 10.1 Further decisions
- **B5 stock mix: Option 1** (§5): equal weight, four names at 20% each, chosen by dropping any name with an unresolved red flag and then the most expensive name to trade. After a sale, the freed 20% goes to the fifth name if it is eligible; otherwise it stays in cash. No cap change is needed.
- **B1 red-flag classes: adopted as proposed in §6.**
  - Class 1, Item 4.02: sell (`DISCRETIONARY_EXIT`).
  - Class 2, Items 1.05 and 2.06: no forced sale; no new buys for 5 sessions, then the block expires.
  - Class 3, statements: SHADOW.

  Still needed before Oct 22: the versioned predicate record, verification fixtures (IDEA-018 §4.4) and the Class 2 expiring entry block, which is new code (`ENTRY_BLOCK` as built has no expiry).
- **A9: build the `INCOMING:` release.** It is not built yet. `larp/runtime/fixtures.py` `settle` releases the USDT and BNB reservations on FINAL_SUCCESS/FINAL_REVERT but never `INCOMING:<token>`, and no production settlement reducer exists (the runtime still uses a fake execution port). To build, with the execution wiring:
  - the settlement reducer emits a delta that releases `INCOMING:<token>` when the swap is final (success or revert);
  - a PostgreSQL regression shows no `INCOMING:` row left after either outcome, and none after recovery replays the same observation.

  Owner Isaac + Keegan (GAP-65).
- **C1: the team will test whether USDT → BNB auto-converts on the dev wallet.** The test is itself an on-chain transaction from the dev wallet. It must therefore run from committed, pushed code with a decision record and a logged round (never-do #2, #5, #13; F-103). If the wallet holds no BNB, the expected outcome is that the swap cannot be paid for (F-93, Guide p.5): that confirms Q-03, and the organisers must be asked.
- **Tracks B–H** are signed off (team statement 2026-10-11). The integrator ticked them in the PR description on the reviewers' behalf.

### 10.2 Finding: starting exposure (synthetic simulation, not market data)
Question: what starting investment maximises wallet equity after two weeks?

**Assumptions:**
- Measured full-history daily vols NVDA/GOOGL/TSLA/MSFT 2.39/1.95/2.90/1.70% (IDEA-009 D.1).
- Correlation 0.55, Student-t (df 4) tails, equal weight across four names, 10 daily steps.
- Premium 8%/yr (and 0%) × β 1.3.
- Spread per side 5/20/50 bp on entry and exit, gas $0.035 per leg on 200 USDT.
- The declared 12% drawdown cut to 40% gross.

Run with `numpy==2.5.3` and seed 11, 200,000 paths.

At 8%/yr premium and 5 bp/side:

| Starting gross | Mean | SD | P(< −5%) | P(hit 8% stop) | P(12% cut) | P(> +5%) |
|---|---|---|---|---|---|---|
| 40% | −0.01% | 2.3% | 1.6% | 0.2% | 0.0% | 1.8% |
| 60% | +0.06% | 3.5% | 6.5% | 1.7% | 0.2% | 7.3% |
| 80% | +0.13% | 4.6% | 12.2% | 5.8% | 0.9% | 13.4% |
| 90% | +0.16% | 5.2% | 14.9% | 8.9% | 1.6% | 16.3% |
| 100% | +0.19% | 5.8% | 17.3% | 12.4% | 2.6% | 18.8% |

**Sensitivity to the spread:**
- At 20 bp/side the mean is about −0.12% at every level: break-even is about 20 bp per side.
- At 50 bp/side the mean falls as exposure rises (80%: −0.60%).
- At 0% premium every level loses its costs.

**Reading:**
- 80%, built on day one with one trade per name, is the most the declared caps allow.
- 80% → 100% adds about +0.06 pp of mean while doubling P(hit 8% stop), which would stop reinvestment for the rest of the run.
- The outcome is dominated by the market path (SD about 35 × the mean).
- The measured bStock spread decides whether being invested has a positive expectation. Measure it before Oct 19 (GAP-50/51).
- Limits: daily closes only (24/7 trading makes excursions larger), assumed premium, no fitted alpha.

### 10.3 Finding: buy-the-dip and the optional momentum mode
- **Buy-the-dip is not supported by the evidence for these names.**
  - Daily reversal is about 0 for large caps in calm markets (Nagel 2012), and short-term reversal does not survive trading costs (Novy-Marx & Velikov 2016).
  - The negative hourly autocorrelation in the token candles (IDEA-012 §1) is consistent with bid-ask bounce, which a taker pays rather than earns. Those estimates need recomputing after IDEA-022 R1–R3.
  - IDEA-018 found no overnight reversal (low power), and rejects off-hours dip buying and daily/weekly reversal as negative after costs (IDEA-018 table, line "Overnight/intraday … off-hours dip buying").
  - A dip rule could be adopted only through a pre-registered EXP with measured costs; none exists.
- **The momentum mode exists but is off and untested.**
  - `larp/strategy/policy.py` supports `baseline: "PRICE_MOMENTUM"` (added in `e9e3671` as a price-only comparison arm). It enters only if the 5-session return exceeds +`price_threshold_bps`, and exits a held name if it is below −`price_threshold_bps`.
  - It is trend-following, the opposite of buy-the-dip. The exit check runs every round, but re-entry waits for a fresh review, so it whipsaws.
  - No test exercises it, and the only strategy config (`config/strategy/offline-fixture.json`) uses `DECLARED_EXPOSURE`.
  - It conflicts with the 80% invested goal, because it sits in cash whenever the 5-session trend is down.
  - Five-session momentum is not supported for large caps; the momentum evidence is for multi-month horizons (Moskowitz, Ooi & Pedersen 2012).

### 10.4 Code used for §10.2

```python
"""Two-week outcome by starting gross exposure. Assumptions (stated, not measured unless noted):
daily vols NVDA/GOOGL/TSLA/MSFT 2.39/1.95/2.90/1.70% (IDEA-009 D.1, full history, measured on Ondo history);
pairwise corr 0.55; Student-t df 4 tails; 10 sessions; equal weight over the 4 names;
premium p/yr x beta 1.3; spread s bp per side paid on entry and exit; gas 0.035 USD per leg on 200 USDT equity;
declared ladder: drawdown >= 12% from peak (daily closes) -> cut gross to 40% (paying spread)."""
import numpy as np
rng = np.random.default_rng(11)
N, T = 200_000, 10
vol = np.array([0.0239, 0.0195, 0.0290, 0.0170])
C = np.full((4, 4), 0.55); np.fill_diagonal(C, 1)
L = np.linalg.cholesky(np.outer(vol, vol) * C)
df = 4
z = rng.standard_normal((N, T, 4)) @ L.T
chi = rng.chisquare(df, (N, T, 1)) / df
shock = z / np.sqrt(chi) * np.sqrt((df - 2) / df)   # unit-variance t
def run(gross, prem, spread_bp, ladder=True):
    mu = 1.3 * prem / 252
    r = mu + shock                                    # daily simple returns per name
    port = r.mean(axis=2)                             # equal-weight basket
    gas = 4 * 2 * 0.035 / 200                         # 4 names, entry + exit legs
    cost_in = gross * spread_bp / 1e4
    W = np.full(N, 1.0 - cost_in - gas / 2); g = np.full(N, gross)
    peak = W.copy(); cut = np.zeros(N, bool); hit8 = np.zeros(N, bool); mdd = np.zeros(N)
    for t in range(T):
        W = W * (1 + g * port[:, t])
        peak = np.maximum(peak, W); dd = 1 - W / peak; mdd = np.maximum(mdd, dd)
        hit8 |= dd >= 0.08
        if ladder:
            trig = (dd >= 0.12) & ~cut & (g > 0.40)
            W[trig] -= (g[trig] - 0.40) * W[trig] * spread_bp / 1e4
            g[trig] = 0.40; cut |= trig
    W = W - g * W * spread_bp / 1e4 - gas / 2          # flatten at the end
    ret = W - 1
    return ret.mean(), ret.std(), np.median(ret), (ret < -0.05).mean(), hit8.mean(), cut.mean(), np.mean(np.log(W)), (ret > 0.05).mean()
print("prem  spread  gross | mean%  sd%  median%  P(<-5%)  P(hit 8% stop)  P(12% forced cut)  E[log W] bp  P(>+5%)")
for prem in (0.08, 0.0):
    for sp in (5, 20, 50):
        for g in (0.4, 0.6, 0.8, 0.9, 1.0):
            m, s, med, pl, h8, c12, el, pw = run(g, prem, sp)
            print(f"{prem:4.0%} {sp:4d}bp  {g:4.0%} | {m*100:+.2f}  {s*100:.1f}  {med*100:+.2f}   {pl:5.1%}    {h8:5.1%}          {c12:5.1%}         {el*1e4:+6.1f}    {pw:5.1%}")
        print()
```

- 2026-10-11 note (SYZ/Claude): the B5 rebalance rule and cap semantics are decided, and Option 1 is built offline, in [IDEA-037](IDEA-037.md): reinvest only into unheld names while gross < 75%; no sell on drift; forced trims only above 25% per name / 90% gross. §7 item 6 is built offline; a live profile and Linux CI acceptance remain.
