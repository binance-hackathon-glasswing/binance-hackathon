# IDEA-018 — Review and red team of IDEA-017, with a final-design candidate for U1

- Date / author: 2026-10-10 / SYZ (requested); drafted by Claude (Cowork) with three literature subagents (L1 rebalancing, drawdown and tournaments; L2 short-horizon and event returns; L3 LLM reliability) and four red-team subagents (R1 rules and declarations; R2 quantitative model of the run; R3 design and buildability; R4 devil's advocate for more trading). Claude merged the reports and re-checked the key facts itself (§6).
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** Changes no D-item, no live behaviour and no declared value. Input to the Oct 11 direction meeting and the Oct 19 D-08/D-12 pre-registration.
- What: a complete review of [IDEA-017](IDEA-017.md) against the user objective U1 (IDEA-017 §1: "maximum net profit with regular trading when opportunities justify costs"). §1 gives the verdict per IDEA-017 item. §2 gives new facts and corrections. §3 gives the economics that should drive the final design. §4 gives one consolidated final-design candidate. §5 lists the decisions. §6 gives sources and limits.
- Cost / risk: desk review, literature and offline analysis of committed probe data only. No Binance, ai-seeds or wallet calls; no `.env` read. Seven subagents of one model: shared blind spots are possible. Raw subagent reports (≈ 26k words) stay in the session scratchpad. Everything decision-relevant is below, and the calculation scripts are committed in `tools/idea018/` (§6).
- Links: IDEA-009..017; D-04, D-08, D-11, D-12; H-01, H-02; F-43, F-48, F-50, F-66, F-95, F-99, F-100, F-105, F-115, F-117; G-11, G-18, G-22, G-24, G-25, G-46, G-53; Q-06, Q-32, Q-39, Q-40; GAP-08..15, 26, 50, 51, 62, 64.

Labels: [V] checked here (file:line, URL with date, or recomputed), [E] estimate with stated inputs, [L] literature (what was read is stated in §6), [I] inference, [O] opinion.

## 0. Summary

1. **IDEA-017's diagnosis mostly holds.** Its arithmetic is correct [V]. The literature supports R2 (exposure is a variance lever), R4 (interior trim targets under fixed costs), R5 (no profit lock-in) and R6 (vote share is not calibrated). Its rejection of manufactured volume is right.
2. **It is not yet a design.** It mostly says "specify X". Taken literally, three of its items raise the risk of a stuck or zero-trade run under the freeze (F-117):
   - R3's shadow-only default for the LLM;
   - R1's evidence-gated re-entry;
   - R8's endorsement of a hard signing halt with no autonomous way to clear it.
3. **R3 misquotes the proposal.** The validation clause covers the *decision model*: "The evidence-assisted model trades only if it passes on held-out data" (`proposal_answers.md` "Your Proposal"). A fired thesis falsifier is a separately declared exit trigger with no validation condition. A shadow-only LLM is therefore the larger deviation from the declarations, not the safer default (§1, R3).
4. **The economics are starker than any entry has said.** At 200 USDT:
   - Gas alone for the base book's 8 swaps (0.07–0.14% of equity) is about the size of the whole expected equity premium over the run (≈ 0.10–0.17% at 48% gross).
   - The base book's expected net is **−0.61% to +0.06%** of equity across the cost grid [E, R2 Monte Carlo].
   - A discretionary round trip on a 20 USDT position needs **≥ 45 / 65 / 95 / 135 bp** of edge at 5 / 15 / 30 / 50 bp spread per side.
   - No signal in the literature clears that for these names [L].
   - Under U1, the only "opportunity" that can justify cost is being invested, and only if the measured spread is below ≈ 11–17 bp per side. Every other trade is either a risk control or a cost paid for activity (§3).
5. **New facts:**
   - IDEA-012 §1's off-hours variance share counted the 09:00–10:00 ET bar, which contains the 09:30 open, as off-hours. Corrected, off-hours per-hour variance is **0.13–0.49×** regular hours, not ≈ 1×. IDEA-016 §3.3's "about the same" is wrong.
   - In the kit's `rwa/tokens` response, `tokenPrice` = `referencePrice` × `tokenToShareRatio` exactly, so "buy when the token trades below its reference" cannot be computed from those fields.
   - The probe's "600 bars" contain a 7-day hole (§2).
6. **The final-design candidate (§4)** is a base book built once on Oct 29 at the declared sizing and held. Only verified hard 8-K events {4.02, 1.05, 2.06} can force an EXIT; everything else from the LLM is a bounded soft block. The rest is the declared ladder and regime governor, a per-name lifecycle with no evidence-gated re-entry, explicit precedence with autonomous clears, frozen execution rules and a UTC terminal schedule. **Activity comes from the build, mandatory actions and the flatten.** Whether to pay for extra visible trading is priced in §3.3 and left to the team.

## 1. Verdict on IDEA-017, item by item

| Item | Verdict | Why | Change |
|---|---|---|---|
| U1 / V1 | Holds | — | Add the price of activity (§3.3) to U1 so "regular" has a number |
| V2 | Holds, two wording fixes [V] | It omits F-115's first sentence, "We want you to keep a stable, reliable trading state". F-117 is a paraphrase, and its freeze point is Q-40, so "F-117 settles" overstates it | Quote F-115 in full; say "as relayed (F-117); freeze point per Q-40" |
| §2 verdict table | Mostly holds | The 015 row inherits the R3 error below | — |
| **R1** lifecycle | Right problem; risky remedy | "Expiry makes a name eligible for reassessment, not to buy" plus "re-entry requires fresh valid evidence" leaves a name in cash forever when the LLM runs only on filings (≈ 0–3 calls in the run, IDEA-011 X8). If applied to the first build, that means zero trades. The base book needs no evidence to enter (IDEA-010 L.5) | Use the §4.2 state machine. Hard blocks are permanent; soft blocks last one session; code re-enables entry without an LLM call. Evidence may only exit, block or shrink, never enter or raise a target (IDEA-010 L.4; architecture PDF "can only veto or shrink risk-adding actions") |
| **R2** profit vs variance | **Holds** [L, E] | Vol scaling changes risk, not expected return (Cederburg et al. 2020). High-vol names do not earn more (Frazzini & Pedersen 2014; Ang et al. 2006). From 48% to 80% gross, expected profit changes by +0.04 to +0.09 pp at 5 bp/side and −0.25 pp at 50 bp, while P(drawdown > 5%) rises from 4% to 32% [E, R2] | One fix [V]: declared sizing is **binding** under G-11 (plan.md "Declared values"), not "provisional". Changing it needs a version event with a non-P&L reason before Oct 26 |
| **R3** exit-only overlay | **Economics hold; compliance reasoning is wrong** | [L] No significant post-filing drift for large caps after 4.02 (Lerman & Livnat 2010) or 1.05 (+0.43% for mid/large/mega, Block 2025); large-cap PEAD gone (Martineau 2022). So an exit's expected value is ≈ 0, as R3 says. But [V] the validation clause is about the decision model ("The evidence-assisted model trades only if it passes on held-out data"). The exits are declared as "a confident DOWN signal on a held name, a fired thesis falsifier, a risk-limit trigger", and falsifiers are "re-checked every cycle". H-02 is an internal hypothesis, ranked below POLICY (SKILL.md §0.2); its V0/V2 presume a decision model that will not exist, so it is **NOT RUN**, not unmet | **Reverse the default.** Ship the narrow declared falsifier EXIT ({4.02, 1.05, 2.06}, item code + verbatim quote, ≤ 1 per name, permanent block). Record it as "not validated for edge; expected value ≈ 0; kept as the declared risk control". Shadow-only would drop the proposal's stated distinctive idea and need ≥ 3 more deviation rows (F-48, F-66), and the assessed logs (F-115) would show an LLM that never changes anything |
| **R4** cap trims | Holds in theory; severity overstated | [L] With fixed costs, rebalance to an interior target, not the boundary (Liu 2004 JF; Irle & Sass 2006; Altarovici, Muhle-Karbe & Soner 2015). [E] Under declared sizing (≈ 8–15% per name) a name must rise 37–200% relative to the book to breach 20%: 0 of 20,000 simulated paths trimmed. At 4 × 20% targets, exact-boundary hourly trims add ≈ 100 swaps and cost 1.6–1.8 pp; an interior target removes 96% of them | Severity: P1 only if D-12 sets targets within ≈ 2 pp of a hard cap, otherwise P3. Rule in §4.1. R4's complaint that a wide band "suppresses most discretionary adjustments" is the profit-maximising outcome without an edge (R2: 2–4 pp bands make 0 extra trades; weekly rebalancing costs 0.10–0.15 pp) |
| **R5** lock-in and clock | Holds [L, E] | "Flatten if up X%" is optimal only for target or rank objectives (Browne 1999; Basak, Pavlova & Shapiro 2007). Its expected effect here is ≤ 0.01 pp | IDEA-017 misses the second reason for the flatten: F-115's "completed trades' PnL" (Q-39 reading R2a), and Binance's earlier bStocks contest "scored realised PnL by FIFO" (E-18). It drops no declared value but adds exit triggers, so it needs register rows (§5) |
| **R6** voting | Holds [L] | Agreement over k samples is miscalibrated (Xiong et al. 2024, ICLR). Semantic entropy cannot see consistent errors (Farquhar et al. 2024, Nature). T = 0 API calls are not deterministic (Atil et al. 2024; AlphaForgeBench 2602.18481). R-VOTE's "k = 5 at low temperature" contradicts Wang et al., who sample at T = 0.5–0.7 | **Drop R-VOTE from v1.0.** Prevent flips by assessing each accession once and storing the result keyed by accession. Fixture acceptance in §4.4 |
| **R7** execution | Holds; incomplete | — | Concrete rule in §4.5. Add a **pre-quote cost check before the approve**, so a failed cost gate does not spend approve gas |
| **R8** precedence | Right order; two gaps | (a) The hard signing halt (IDEA-013 R1) has no autonomous clear; under F-114/F-117 one dropped transaction can freeze the Nov 10 flatten. (b) It treats as open what the declarations settle [V]: adds are new risk ("no new positions … new-risk halt"), and the daily halt lasts "for the rest of the UTC day". Only the 8% reset and how long the 12% cut persists are open | §4.3 table, with an autonomous clear for UNRESOLVED and a two-mark confirmation for the 12% cut |
| **R9** reproducibility | Right conclusion; misses the real error | The 0.63–1.07 ratio is correct arithmetic on misclassified inputs (§2.1) | Correct IDEA-012 §1 and IDEA-016 §3.3; record the candle sha256 |
| §4 metrics | Good; add three [V] | F-99: `amount` is shares for a sell, so sell proceeds come from receipts. F-100: reverts carry a `tx_hash`. Q-08: BNB top-ups appear as orders | Add a reconciled count of official-trace orders, realised FIFO round-trip PnL next to terminal equity, and a per-swap cost split (gas, spread, impact; USDT and bp of the swap). Reword "a cash benchmark does not meet F-115": a deployed cash default conflicts with F-115; a cash comparison does not |
| §5 order of work | Holds | Capacity is the binding constraint: ≈ 21–31 pd available vs ≈ 48–52 needed (IDEA-011 X1). Taken literally, IDEA-017 adds ≈ 6–9 pd [E, R3] | Use §4, which is ≈ 2–3 pd smaller than IDEA-010 §4, and keep the X1 fallback |

**What IDEA-017 misses** [V, R1/R3]:
- **(a) The declared regime governor.** It appears in `proposal_answers.md` four times and in the PDF ("a rule-based regime governor that sets the exposure budget from realised volatility and drawdown"). It is absent from every draft in IDEA-012–017. G-11 makes it binding.
- **(b) The declared failure mode.** "A data, model, tool or schema failure means HOLD, no new risk" conflicts with IDEA-010 K ("LLM unavailable → base book runs"). Read literally, an EDGAR or LLM outage before Nov 4 gives a zero-trade run. It needs a scoped interpretation row (§4.3).
- **(c) Wash-trade appearance.** Binance banned wash trades in its previous bStocks contest (E-18), and trim/re-buy loops or quick re-entries look like them.
- **(d) The safety path still has limits.** It must still respect the per-trade cap (F-105), the declared exit slippage cap and the gas floor.
- **(e) The dominant cost number (§3.1).**

## 2. New facts and corrections

### 2.1 IDEA-012 §1 off-hours variance: bar misclassified [V]
- **Data facts.**
  - The candle file `data/probe/candles_probe_20261007T142342Z.json` has sha256 `e7b74496c902fcbb360acbf6409e7f74907d71f8f2bef6058a7b73bd1f999df9`. Its "600 1h bars, Sep 5 – Oct 7" are two 300-bar windows with a hole from Sep 18 03:00 to Sep 25 03:00 UTC.
  - Hours with no trades are 0–0.5% at 1h. At 1m they are 2–81% (MSFTB 81%).
- **Reproduction.** IDEA-012's 77/79/73/75/82% reproduce (77/79/74/75/83%) only when the 09:00–10:00 ET bar is counted as off-hours. That bar contains the 09:30 open.
- **Corrected.**
  - Off-hours share of variance: 63/68/50/35/63%, against 81% of time.
  - Off/on per-hour ratio: 0.40/0.49/0.24/0.13/0.39 (NVDAB/GOOGLB/SKHYB/TSLAB/MSFTB). Weekend hours: 0.19–0.57× regular hours.
  - The opening hour alone holds 11–40% of each name's variance.
  - IDEA-012's "pre-market 32–51%" has the same flaw; pure 04:00–09:00 ET is 9–21%.
- **Consequences.**
  - IDEA-016 §3.3's "per-hour variance is about the same on and off hours" is withdrawn.
  - Holding over nights and weekends carries less risk per hour than feared.
  - Risk is concentrated at the US open, which is where any discretionary trade should *not* be timed (§4.5).
- **Cost proxies from prints (not quotes).**
  - Roll spreads on 1m bars within the same window are 13–37 bp full spread.
  - Implied per-side spread is ≈ 4–34 bp.
- **Overnight reversal not found.** Overnight token moves do not reverse at the open: pooled vol-standardised corr(close→pre-open, pre-open→close) = −0.02 ± 0.24, n = 70 name-days. That contradicts IDEA-012 §2's "overnight token moves tend to reverse at the open" for these tokens. The test has low power.

### 2.2 `tokenPrice` is a scaled reference mark, not an on-chain price [V]
- **The finding.** In the 46 `rwa/tokens` records in the probe file, `tokenPrice` − `referencePrice` × `tokenToShareRatio` = 0 to 10⁻¹⁹ (Decimal arithmetic, checked by Claude on all records). The trading guide calls `tokenPrice` "the on-chain price in USD" (F-95). The probe shows it is a reference mark scaled by the dividend multiplier.
- **Comparison with trades.** The last on-chain 1m closes at the same moment differed from it by −28 to +4 bp.
- **Consequences.**
  - (a) "Buy when token ≤ reference" cannot be computed from `rwa/price`/`rwa/tokens`. Those are the same number.
  - (b) The only real premium is executable quote ÷ (`referencePrice` × ratio) − 1. That is what IDEA-010 T.3's entry-cost gate already measures, so log it on every quote.
  - (c) IDEA-010 S.3's `MARK_SANITY` compares quotes with a reference feed, not with on-chain trades. Document it that way.
  - (d) Whether the reference is live or stale off-hours is unmeasured (Q-32, GAP-44).
- **Records to correct.** participant-kit.md K6 and F-95's description need a dated note. The verbatim kit copy is not edited.

### 2.3 Smaller corrections
- **IDEA-011 X3 DST slip [V].** On Oct 29 (EDT) close−60 is 19:00 UTC, not 20:00 UTC.
- **IDEA-012 §2 [L].** "Unprofitable at 20 bp round-trip" (Lopez-Lira & Tang v6) refers to the long–short daily overnight-news strategy, not to the ≈ 8 bp/day long leg. IDEA-017 §6 reads it correctly.
- **IDEA-012 §4.1 [L].** "Only wide (≥ 10%) disaster stops cut drawdown" misreads Lo & Remorov's 10-day window.
- **literature.md L-40 [L].** Busse's (2001) abstract says the tournament effect "disappears" with daily data, not "weakens".
- **IDEA-016 §3.4 [V].** The "0.24–0.68% build+liquidate" figure is for 80% gross; at the declared ≈ 48% gross it is 0.14–0.41%. The 15–25 USDT minimum behind its band is stale: IDEA-010 S.4 gives 6.8–14 USDT.
- **IDEA-015 B4 [V].** It holds at minute scale for earnings. NVIDIA's Aug 26, 2026 release is stamped 4:20 PM ET on GlobeNewswire, and the 8-K was accepted at 16:21:19 ET. Other 8-K items may be filed up to four business days after the event.

## 3. The economics that should drive the final design

### 3.1 Costs vs premium at 200 USDT [E, R2 Monte Carlo]
- **Model.** 20,000 paths; 293 h from the Oct 29 build to the Nov 10 flatten (9 US sessions). Hour-of-week variance profile from §2.1. ρ = 0.5 (0.25 as a sensitivity). Fat tails via a daily variance mixer. β = 1.3. Script: `tools/idea018/mc_run.py`.

| Base book (declared sizing ≈ 48% gross, build + hold + flatten) | Spread 5 bp/side | 15 | 30 | 50 |
|---|---|---|---|---|
| Premium 5%/yr, gas 0.035 USDT/swap | −0.08% | −0.17% | −0.31% | −0.50% |
| Premium 8%/yr, gas 0.017 USDT/swap | **+0.06%** | −0.04% | −0.18% | −0.37% |
| sd of outcome / E[max drawdown] | 2.3% / 2.6% | | | |

- **Gas.** Gas for 8 swaps is 0.07–0.14% of equity. That is about the whole expected premium (0.10% at 5%/yr).
- **Breaking even.** The book breaks even only if the premium exceeds ≈ 9%/yr at 5 bp/side, or ≈ 13%/yr at 15 bp/side (gas 0.035).
- **Cash.** Strictly, cash maximises expected net profit at most spreads. F-115 rules it out.
- **What the design is for.** It *minimises the cost of being an active, invested agent*. It cannot claim an expected profit.

### 3.2 What a trade must clear [E]
- **Hurdle.** A discretionary round trip of size S pays off only if edge > 2s + 2g/S.
- **Values at S = 20 USDT and g = 0.035:** 45 / 65 / 95 / 135 bp at s = 5 / 15 / 30 / 50 bp.
- **Literature [L, L2]:**

| Opportunity | Expected net for this book | Verdict |
|---|---|---|
| Being built by the Oct 29 close, for turn-of-month days Oct 30 and Nov 2–4 (McConnell & Xu 2008; Etula et al. "Dash for Cash"; contested after 1990, Waggoner & Maberly) and macro announcement days NFP Nov 6 / CPI Nov 10 (Savor & Wilson 2013; Ai, Bansal & Guo 2023; ≈ half once selection is controlled for, Ernst, Gilbert & Hrdlicka) | Part of the ≈ 0 base-book result; free if the build is not delayed | **Adopt as timing**: build on Oct 29, no macro buy-block, hold through releases |
| In-session execution placement (quote vs reference mark) | +1 to +5 bp | Adopt as a cost gate, not alpha |
| Entry block on a verified adverse 8-K | 0 to +5 bp | Adopt (soft block) |
| Exit on a verified adverse 8-K | ≈ 0 (no large-cap drift) | Keep as the declared risk control (§1 R3) |
| Overnight/intraday, intraday momentum, daily/weekly reversal or rotation (Nagel 2012; Novy-Marx & Velikov 2016), LLM news trading, off-hours dip buying | Negative after costs | **Reject** |

- **No FOMC** in the window: Oct 27–28 and Dec 8–9 [V, Fed calendar]. The midterm effect is not robust after risk adjustment (Anderson, Białkowski & Wagner 2023).

### 3.3 The price of "regular trading" [E]
- **Default activity.** About 8 swaps (4 buys on Oct 29–30, 4 sells on Nov 10), plus mandatory actions when they fire. Between the build and the flatten, about 7 sessions may have no swap. Every round still logs a decision and a falsifier check.
- **What extra visible activity costs** (R2 and R4 estimates):
  - one name round-tripped each session: **0.05–0.16% of equity per session**, 0.43–1.42 pp over the run;
  - a weekly rebalance: 0.10–0.15 pp;
  - a capped "activity budget" of genuine re-sizes towards the current vol target (R4: e.g. Nov 2 close−60 only, |Δ| ≥ max(25% of target, MinTrade), no same-name reversal within 24 h, total cost ≤ 0.25%): **≈ 0.05–0.25 pp**.
- **Recommendation [O].** Under U1 none of these is justified by an opportunity, so the default is **no activity budget**. Whether F-115's unknown weights (Q-39) are worth ≈ 0.05–0.25 pp of expected equity as insurance is a team choice. If chosen, it must be pre-registered, capped, labelled in `output` as "rebalance toward target", and never a same-name reversal.

### 3.4 Exposure (D-12)
- **What it trades off.** Break-even spread for adding exposure: 10.9 bp/side at 5%/yr and 17.4 bp/side at 8%/yr [E]. Above it, more exposure lowers expected profit; below it, the gain is ≤ 0.1 pp (≈ 0.2 USDT). The risk cost is certain: sd 2.3% → 4.0%, P(3% daily halt) 1.9% → 16%, P(8% halt) 0.1% → 6%.
- **Recommendation [O].** Keep the declared formula, which needs no version event. If the team wants exposure at the caps, pre-register by Oct 19 a rule conditioned only on the logged median round-trip cost at intended size (e.g. ≤ 30 bp), labelled a variance choice. That is a version event with a register row.

## 4. Final-design candidate (consolidates IDEA-010 §4, IDEA-011, IDEA-015/016, IDEA-017 and this review)

Markers: **[D]** declared; **[C]** changes a declaration (needs a GAP-62 row); **[N]** new inside the declarations (manifest note). Brackets are frozen by Oct 22 from data or arithmetic, never from P&L (G-46).

### 4.1 Base book
- **Universe** [N]: NVDAB, GOOGLB, TSLAB, MSFTB. SKHYB is excluded: its declared weight is 3.7–4.7%, below MinTrade. On Oct 19, if logged quotes show MSFTB (median 353 on-chain trades/day vs 1,020–5,819 for the others) is much wider, swap it for SKHYB only if SKHYB passes MinTrade. Otherwise run 3 names.
- **Sizing** [D]: 1% ÷ (2 × σ₆₀ × √5) × R. Hard caps are 20% per name, 80% gross and ≤ 4 positions [D]. Operating ceiling 16% per name [N].
- **Trims** [N]: fire only when the post-cost mark exceeds a hard cap. Trim to the ceiling, at most once per name per session. They never fire at declared sizing.
- **MinTrade** [N]: frozen G ÷ 25 bp. G is the median gas per approve+swap over ≥ 6 dev-wallet swaps by Oct 19 (default 0.035, giving 14 USDT). Fixes IDEA-011 X5.
- **Feasibility gate at the freeze** [N]: drop any name whose target × 200 USDT < MinTrade, and list it in the manifest. Check the 100 USDT dev wallet separately (IDEA-010 S.4).
- **No band trades** [N]: no re-sizes or band trades unless the team buys the §3.3 activity budget. This is consistent with the declared no-trade band.
- **Regime governor** [D]: IDEA-010 §4 R thresholds 2.0 / 3.0 / 1.5. Restores only before `T_new_risk_end`.

### 4.2 Lifecycle per name (replaces IDEA-017 R1's open questions) [N]
- **States:** `UNBUILT` → `HELD` → `EXIT_PENDING` → {`CLOSED_HARD`, `CASH_RISK`, `FLAT_TERMINAL`}; `SKIPPED`.
  - `UNBUILT` → `SKIPPED` after 3 consecutive own build failures. Cost skips and outages do not count.
  - `CLOSED_HARD` is terminal: no re-entry, and the block also applies if the name was never held.
  - `CASH_RISK` returns to `HELD` only by a regime restore before `T_new_risk_end` with no halt active.
- **Soft block** (buys only):
  - Set by: verification failure, `entry_concern`, the 5.02 / 2.02 / GUIDANCE_CUT classes, a 10-Q/10-K concern, or an LLM failure with a filing pending.
  - Expiry: the next session's close−60 round. Not renewable on the same accession. Budget: 6 name-sessions, then `BLOCK_BUDGET_EXHAUSTED`. Expiry re-enables buying without an LLM call.
- **Thesis object** [D]: 5-session horizon. Code renews it with no trade.
- **Per-round falsifier check** [D]: falsifiers are "re-checked every cycle". Code checks each held name for queued hard-class accessions and regime state every round, and logs a rule-statement `cot` (F-106 (a)).
- **Evidence never enters or raises a target** [D]: a favourable assessment maps to HOLD.

### 4.3 Risk precedence and resets
| Layer (highest first) | Contents | Bypasses |
|---|---|---|
| 0 Integrity | version/tree hash, address, clock, unknown outgoing tx (G-03/G-09) | nothing |
| 0b Wallet pending | UNRESOLVED tx | nothing. **Autonomous clear** [N, to be checked by Keith against G-18 (g)–(i)]: once the swap's own quote deadline + 10 min has passed, the next action may be signed at the **same nonce** with a ≥ 15% gas-price bump. Never nonce + 1. Either the old swap is mined (and reverts with `DeadlinePassed`) or the new one is; never both |
| 1 Market and quote | `openState` true (buys: both endpoints; sells: `rwa/tokens`), fresh quote, payload and recipient/min-out (G-01, F-95) | nothing |
| 2 Mandatory reductions | flatten > R = 0 > 12% delever > hard-cap trim > R = 0.5 | MinTrade, entry-cost cap, cadence, soft blocks. **Not** the per-trade cap (F-105), the exit slippage cap or the gas floor (declared) |
| 3 Evidence | hard-class EXIT (whole position); soft blocks (buys only) | MinTrade |
| 4 Baseline buys | first build, regime restore | nothing |

- **One target per name per round.** Sells that count towards a delever also count towards an EXIT; nothing is sold twice.
- **Any buy is new risk** [D].
- **Daily 3% halt** [D]: resets at the next 00:00 UTC.
- **8% halt** [N]: latched for the run. This is stricter than declared, so it is a manifest note only.
- **12% delever** [D]: fires after two consecutive marks ≥ 5 min apart. Gross ≤ 40% [D] (implemented as 36% for cost headroom [N]). Latched; no restore.
- **Marks** [D/N]: executable sell quote at held size. If the quote fails or deviates by > 3%, fall back to the reference mark × 0.99 (IDEA-010 S.3).
- **Declared failure mode, scoped** [C, interpretation row]:
  - A model failure blocks new risk only on names with a pending, unassessed filing.
  - EDGAR unreachable < 24 h → no buys. EDGAR unreachable ≥ 24 h → base-book buys continue, logged as `DEGRADED_EVIDENCE`.
  - Data failures in prices or quotes always block buys.

### 4.4 LLM path (assessment only)
- **Trigger** [N]: a durable EDGAR queue (IDEA-015 A.2) on 8-K/8-K/A for the four CIKs. 10-Q/10-K are triggers for soft blocks only, keeping the declared scope (IDEA-011 X8 (a)).
- **Call** [C: no tool loop]: one call per accession with the text pushed in. The result is stored keyed by accession and never re-asked. No voting.
- **Schema** [D: no action field]: `adverse_class`, verbatim `quote`s, `entry_concern`, `falsifier`, `summary`.
- **Verifier** [D G-53]: item code from the submissions JSON plus whitespace-normalised verbatim quote.
- **Map M** [D falsifier exit]:
  - EXIT only for {4.02, 1.05, 2.06} verified on a held name.
  - Everything else, including judgement-only classes (L3: a 2026 8-K event-tagging study, arXiv 2607.08346, reports overall precision 0.73 with near-miss errors), can only soft-block.
- **Fixtures before Oct 19** (L3 thresholds; zero failures in N bounds the error rate at ≈ 3/N):
  - Verifier rejects 100% of planted fabricated or altered quotes.
  - Schema valid ≥ 99% within 2 retries.
  - 0 human-labelled-unsupported claims pass on EXIT-capable classes.
  - Two labellers, κ ≥ 0.6, or the field cannot drive a block.
  - Acceptance is judged on post-cutoff and counterfactually edited slices, because 2024–2026 filings of these four firms are likely memorised (Lopez-Lira, Tang & Zhu 2025).
- **The LLM never runs inside a trading round, and no round waits on it** [N].

### 4.5 Execution [N unless marked]
- **When buys run.** Only in scheduled rounds at open+30 and close−60 in the US session. Not 09:30–10:00 ET (§2.1). Sells run in any round while `openState` is true.
- **Merged rounds.** A scheduled round and the hourly monitor in the same hour are one round with one log (G-19).
- **Swap sequence.**
  1. Pre-quote and check: entry cost (spread + impact + G ÷ size) ≤ 50 bp per name [D], and impact ≤ min(50 bp, 2 × logged median) [C: replaces the depth cap, GAP-51]. Skip with a reason code before approving.
  2. Exact approve, then re-quote and payload checks (G-01).
  3. Sign within 10 s of the quote, write the journal entry, broadcast, then poll every 3 s up to 120 s.
- **Buy failure.** ≤ 2 re-quotes, then retry next scheduled round, up to `T_new_risk_end`.
- **Sell failure.** 3 attempts per round (5 / 15 / 45 s), then `EXIT_PENDING` with hourly retries. Mandatory sells use a slippage ladder of 1% → 2% after two failed rounds → 3% on Nov 11 [D: "exits have their own slippage cap", value frozen].
- **Ordering.** One transaction in flight. Sells largest first, then buys smallest first. USDT ≥ order + 2.
- **Caps.** Per-trade cap ≤ 50 USDT (F-105). Gas floor checked before every approve (G-28).
- **Same-name reversals** [N, anti-wash]: no opposite-side trade in the same name within 24 h, except mandatory actions. Every order's `output` states its economic reason.
- **Logging.** Log quote ÷ (`referencePrice` × ratio) − 1 on every quote (§2.2).

### 4.6 Terminal schedule (absolute UTC, DST-safe) [N; from IDEA-010 §2, tightened by R3]
| Gate | UTC | Note |
|---|---|---|
| `trade_after` | Oct 29 14:00 | First build round (open+30, EDT). No macro buy-block, no gap rule (IDEA-011 X3) |
| `T_new_risk_end` | Nov 4 21:00 | Last instant for any buy (build retry or restore). A later buy cannot recover its round trip before the flatten; replaces IDEA-010's Nov 9 `last_buy` and settles X4 |
| `flatten_start` | Nov 10 19:00 and 20:00 | Target 0 for all names (mandatory path) |
| exit retries | hourly while `openState` is true | sells only |
| `flatten_by` | Nov 11 15:00 | No signing after this |
| `END_OF_RUN` | after `flatten_by` | Hold-only logs until stopped |

- **No profit lock-in** [N].
- **If Q-06 is answered before the freeze,** recompute `flatten_start` by IDEA-010 §2's rule.
- **The flatten is a new exit trigger** [C], justified by Q-06 and Q-39 R2a (E-18 FIFO precedent).

### 4.7 Expected outcome [E]
- About 8 swaps plus mandatory actions.
- Net ≈ −0.5% to +0.1% of equity, depending on the spread.
- sd ≈ 2.3%; E[max drawdown] ≈ 2.6%.
- P(any ladder step fires) ≈ 2%.
- The result is decided by the market path, the measured spread and whether the build and flatten execute cleanly.

## 5. Decisions and actions

| # | Decision / action | Owner (suggested; GAP-37) | By |
|---|---|---|---|
| 1 | Adopt §1's R3 reversal: narrow declared falsifier EXIT live, not shadow; H-02/EXP-001 recorded NOT RUN; plan.md D-11 note corrected | SYZ + team | Oct 11 |
| 2 | Adopt the §4 lifecycle, precedence and terminal schedule as the GAP-64 spec skeleton | Isaac + SYZ (policy), Keith + Keegan (precedence, execution) | Oct 11 skeleton; Oct 19 pre-registered |
| 3 | Keith checks the same-nonce autonomous clear against G-18 (g)–(i) and the swap calldata deadline | Keith | Oct 15 |
| 4 | Quote + `openState` logger at 10/15/25/40 USDT, buy and sell, all names, US session and off-hours; per-swap cost split. Everything in §3 hinges on s | Isaac (Keegan for the R8 fix) | start now; readout Oct 19 |
| 5 | D-12: keep the declared formula, or pre-register the cost-conditional cap rule (§3.4); universe swap rule (§4.1) | Isaac proposes, team decides | Oct 19 |
| 6 | Activity budget: none (recommended) or a pre-registered capped re-size (§3.3) | team | Oct 19 |
| 7 | Deviation register rows: decision model not shipped; H-02 NOT RUN; invested by default; exit triggers (falsifier set, flatten, regime cut, cap trim); no tool loop; scoped failure mode; depth cap → impact cap; no human HALT / safe-mode build / in-run releases; branch protection; cold standby, PostgreSQL and hourly anchoring if cut; event planner if static; off-hours entries are timing only (H-01 NOT RUN). Full list of 34 candidate rows with quotes in R1's report; to be copied into GAP-62 | Keegan | draft Oct 19; final Oct 26 |
| 8 | L3 fixtures for §4.4 | SYZ | Oct 19 |
| 9 | Dated corrections: IDEA-012 §1, §2, §4.1; IDEA-016 §3.3, §3.4; IDEA-011 X3; participant-kit.md K6 (`tokenPrice`); literature.md L-40 | SYZ | Oct 11 |
| 10 | Capacity: hours per person (IDEA-011 X1). If below ≈ 40 pd, take the X1 fallback on Oct 11: base book + risk + terminal + must-haves, with a minimal or no LLM path and a deviation row | all | Oct 11 |

## 6. Sources, checks and limits

- **Repository read [V].**
  - Claude: SKILL.md, plan.md, proposal_answers.md, INCOMPLETE_WORK.md, LEDGER.md, AGENTS.md, IDEA-009..017 in full, literature.md, strategy-opinions.md.
  - Subagents between them: everything else, including the architecture PDF and Participant Guide (pdftotext), participant-kit.md, environment.md, inferences.md and the kit copies.
- **Claude's own checks [V].**
  - `tokenPrice` = `referencePrice` × ratio on all 46 records.
  - The candle sha256.
  - Reproduction of IDEA-012's shares under the misclassified bar (`variants.py` output).
  - The §3 break-even formulas.
  - Calendar: Oct 31 2026 is a Saturday, so Oct 30 is the last October session; DST ends Nov 1.
- **Literature [L].** Most items were read as abstracts, publisher or IDEAS pages, arXiv HTML, or full text through a summarising fetch. Numbers were not hand-checked against every PDF.
  - Rebalancing: Liu 2004 (JF); Irle & Sass 2006; Altarovici, Muhle-Karbe & Soner 2015.
  - Drawdown and stops: Grossman & Zhou 1993; Kaminski & Lo 2014; Lo & Remorov 2017.
  - Target and rank objectives: Browne 1999; Basak, Pavlova & Shapiro 2007.
  - Volatility and beta: Cederburg et al. 2020; Frazzini & Pedersen 2014; Ang et al. 2006.
  - Turn of month: McConnell & Xu 2008 (FAJ); Etula, Rinne, Suominen & Vaittinen; Waggoner & Maberly 2000.
  - Announcement days: Savor & Wilson 2013 (JFQA); Ai, Bansal & Guo (NBER w31923); Ernst, Gilbert & Hrdlicka (2022 WP).
  - Pre-FOMC drift: Kurov, Wolfe & Gilbert 2021.
  - Elections: Anderson, Białkowski & Wagner 2023.
  - 8-K events: Lerman & Livnat 2010; Palmrose et al. 2004; Hennes, Leone & Miller 2008; Block 2025 (arXiv 2512.06144).
  - Post-earnings drift and news speed: Martineau 2022; Busse & Green 2002; Ke, Kelly & Xiu 2019; Chan 2003; Rogers, Skinner & Zechman 2017.
  - Tokenized stocks: Cong et al. 2026 (slides).
  - Reversal and costs: Nagel 2012; Novy-Marx & Velikov 2016.
  - Lopez-Lira & Tang v6.
  - LLM calibration: Wang et al. (self-consistency); Xiong et al. 2024; Farquhar et al. 2024.
  - LLM nondeterminism: Atil et al. 2024; AlphaForgeBench.
  - LLM on filings: arXiv 2607.08346 (8-K tagging); Wallat et al. (citation faithfulness).
  - Memorisation: Lopez-Lira, Tang & Zhu 2025.
  - LLM trading benchmarks: L-12..L-16, verified as cited, with the note that none models fees.
- **Scripts** (offline, `python -I`, no data committed): `tools/idea018/analyse_candles.py <candle file>` (§2.1 tables, cost proxies), `tools/idea018/variants.py <candle file>` (reproduces IDEA-012's shares), `tools/idea018/mc_run.py [rho] [paths] [vol_scale]` (§3 Monte Carlo).
- **Limits.**
  - Print-based costs; no executable quotes (GAP-50).
  - One month of token data in one regime.
  - β, premium and the variance mixer are assumptions.
  - Off-hours `openState` unmeasured (Q-32).
  - The window end is ±1 session (Q-06), which moves the premium by ≈ ±10% of its value.
  - Scoring weights unknown (Q-39).
  - Nothing here is a profitability or readiness claim.

## 7. Updates (append-only)
- 2026-10-10 (SYZ, drafted by Claude): [IDEA-019](IDEA-019.md) (Isaac, drafted by Codex) was written in parallel and merged without editing it; it reserves IDEA-018 for this entry. Points where the two differ, for the Oct 11 meeting (nothing here amends IDEA-019):
  - **Inconclusive default:** IDEA-019 R2 keeps evidence effects in shadow (as IDEA-017 R3); this entry §1 R3 recommends the narrow declared falsifier EXIT live, because the proposal's validation clause covers the decision model and the falsifier exit is declared separately.
  - **Re-entry:** IDEA-019 §5 requires a fresh reassessment before re-entry; this entry §1 R1 / §4.2 flags that as a stuck-in-cash risk when the LLM runs only on filings, and lets code re-enable entry after a soft block expires (hard blocks stay permanent).
  - **Objective:** IDEA-019 §5 targets prize placement (Isaac's follow-up); this entry targets U1 net profit. Both keep declared sizing and the 3/8/12 ladder and reject the +6% lock-in; IDEA-019's conditional exposure escalation matches §3.4 here (a variance choice to be pre-registered, not a profit claim).
- 2026-10-10 correction (SYZ, drafted by Claude): §4.3 layer 1 let sells check only `rwa/tokens`. The kit says "When `openState` is `False` (here or in `rwa/underlying-market`) … don't place orders" (`docs/official/kit/bstocks-trading-guide.md` line 102), so every order, sells included, needs both flags true; closed-market sells wait as `EXIT_PENDING`. Adopted from IDEA-019 §5 in [IDEA-020](IDEA-020.md) §1, §5.1.

- 2026-10-10 correction (Keith/Codex; PR #5 review): The historical Roll/AR/session-variance and simulation outputs require recomputation after IDEA-022 R1-R3 (pre-return midnight anchor, actual time-adjacent pairs, separate gap returns) and IDEA-021 C07 (terminal-gas MDD). Source repairs and deterministic regression evidence are in IDEA-026 §1/§4. No market-data rerun, sampled simulation comparison or revised coefficients/results are claimed; Keith owns a coordinated prospective rerun, Yao Zhu reviews.
