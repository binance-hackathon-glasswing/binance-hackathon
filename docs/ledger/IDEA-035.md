# IDEA-035 — Team decisions 2026-10-11: PR #7 review answers and pre-live choices

- Date / author: 2026-10-11 / SYZ (team decisions relayed by SYZ; drafted with Claude)
- Status: open (decision record; items marked "proposal" or "deferred" are not decided)
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
