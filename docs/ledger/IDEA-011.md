# IDEA-011 — Review and red team of IDEA-010 (Keegan's three-reviewer review of IDEA-009)

- Date / author: 2026-10-09 / SYZ (requested); drafted by Claude (Cowork), one reviewer. Read-only on everything except this entry, its index row and a dated pointer in IDEA-010 §10.
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** Input to the Sun Oct 11 meeting. Changes no D-item, no code, no live behaviour.
- What: checks IDEA-010's sources, arithmetic and spec against the repo; red-teams the base-book + map spec (§4), the must-haves (§5), the schedule (§6–§7) and `tools/probe_quote.py` (commit `dde9d1e`).
- Cost / risk: desk review only. Read IDEA-009 and IDEA-010 in full; `docs/proposal/LARP_System_Architecture.pdf` (pdftotext) and `proposal_answers.md`; SKILL.md F-07, F-93, F-101, F-107, F-109, F-113..F-117, Q-03, Q-06, Q-32, Q-39, Q-40, G-14, G-46; plan.md G-22..G-28, G-40, G-53; participant-kit.md K6a, K6b; kit `bstocks-trading-guide.md` §3–4; `binance_test.py`. Recomputed IDEA-010 §3/§4 S.4 sizing with a script on IDEA-009 §D.1 vols. No Binance, ai-seeds, wallet, SEC or web calls; `probe_quote.py` was read and parsed, not run. One model reviewing another model's output: shared blind spots are possible.
- Links: IDEA-009, IDEA-010, D-08, D-11, D-12, F-07, F-49, F-107, F-109, F-115, F-117, G-01, G-14, G-22, G-25, G-46, G-53, Q-06, Q-32, GAP-03, GAP-37, GAP-44, GAP-50, GAP-62

Labels as in IDEA-009: [V] checked here (file and quote, or recomputed), [E] estimate with inputs, [I] inference, [O] opinion.

## 0. Verdict
IDEA-010 is a clear improvement on IDEA-009, and its main corrections hold (§1). Adopt its §1 (assessment-only LLM), §2 (window gates), §3 (arithmetic fixes) and §5 (must-haves, with X9). Its weakness is the opposite of IDEA-009's: the spec has grown to about a dozen rules and 21 must-haves on a capacity figure nobody has confirmed (X1, X2), several of its own rules collide at the first build (X3, X4), and the LLM it keeps would run about 0–3 times in the scored run (X8). Fix those before the D-08 pre-registration (Oct 19).

## 1. Checked and holds
| IDEA-010 claim | Check | Verdict |
|---|---|---|
| §1 PDF forbids LLM trade authority | pdftotext: "LLM zone: authority over evidence only, never over trades"; "The output schema cannot express a trade. A timeout or schema failure means HOLD."; "Guardrails: the LLM has no trade authority; deterministic layers act." IDEA-009 §1 does not list the PDF; docs/README.md lists it as uploaded with the proposal | **Holds** [V]. IDEA-009 §2's "mis-sourced" verdict was wrong |
| §2 window may end Nov 11 16:00 UTC | Nov 12 00:00 UTC+8 = Nov 11 16:00 UTC; US DST ends Sun Nov 1, 2026, so the Nov 11 session is 14:30–21:00 UTC; Nov 9 = Mon, Nov 11 = Wed (NYSE open on Veterans Day); gate times are self-consistent | **Holds** [V], but F-07 is about the DoraHacks submission timeline; carrying it to the scored window is [I], not [V] |
| §3 25 USDT minimum blocks 3 of 4 E1 names | 200 USDT × declared weights: full-history vols → NVDA 18.7, GOOGL 22.9, TSLA 15.4, MSFT 26.3 (3 of 4 below 25); EWMA vols → 27.3, 29.6, 19.7, 30.8 (1 of 4 below) | **Holds as a bug** [V]; "1–3 of 4" is the accurate range |
| §4 S.1 GOOGLB ≈ 75 sessions by Oct 29 | Jul 15 – Oct 28 NYSE sessions: 13 + 21 + 21 + 20 = 75 | **Holds** [V] |
| §0 expected net ≈ −0.13% to +0.10% | Re-derived: premium ≈ 0.19% (8%/yr, β 1.3, gross ≈ 0.48, 9 sessions) minus 4 round trips (gas 0.07–0.14%, spread 0.05–0.20% at 5–20 bp) ≈ −0.15% to +0.07% | **Holds** [E] |
| §3 K6b off-hours `openState` was `ondoStatusInfo` | participant-kit.md K6b line on crypto-market-rank token-rank | **Holds** [V] |
| §5 #8 realtime only; wrong secret → `UploadError`, not retried or saved | SKILL.md F-109 | **Holds** [V] |
| §8 G-14 conflicts with G-46 | G-14 "Register a hold/exit-only build … when a normal deploy is impossible" vs G-46 "no manual switch to the registered safe-mode build" | **Holds** [V] |
| `probe_quote.py` signing and quote parameters | Same signing as `binance_test.py` / `probe_candles.py`; quote params match kit guide §3 (`binanceChainId`, `vendor=LiquidMesh`, `slippagePercent`) | **Holds** [V] |

## 2. Findings
Severity: **H** could cost the run or the audit; **M** spec bug or wasted build time; **L** wording, process or tooling.

**X1 (H) Capacity is an unchecked assumption.** IDEA-010 §6's "≈ 38–49 pd" capacity comes from IDEA-009 §E's [A] "4 people × 4–5 effective person-days per week [ask the team]", which was never asked. That is 32–40 h per person per week during NUS term. At 2–3 pd/week each, capacity to Oct 26 is ≈ 21–31 pd against ≈ 48–52 needed [E]: even after the §6 cuts the plan is 1.5–2.5× over. The Oct 9–11 list alone is ≈ 51 h over three days (Keegan ≈ 17 h, Keith ≈ 12 h). **Fix:** each person states realistic hours per week at the Oct 11 meeting; if the total is under ≈ 40 pd, take IDEA-010 §6's Oct 18 fallback cut (LLM path → base book + risk rules, a deviation row) on Oct 11, before work is spent on it.

**X2 (H) Rule count versus the freeze.** §4 adds regime thresholds with hysteresis, a gap rule, a macro event rule, Monday re-sizes, a band, MinPos, a mark sanity band, a soft-block budget, cooldowns and skip counters. IDEA-010 itself estimates the base book's net ≈ 0 and the map's score effect ≈ 0 (§4 L.6), and none of these rules can be patched after activation (F-117). Under F-115 a crash, stuck state or missing log costs more than any of them can gain [O]. **Fix:** pre-register a minimal base book: build once; hold; regime cut without restore inside 2 sessions; G-22; mapped exits; flatten. Keep what the proposal declares (regime governor, event-class rule, no-trade band, ≤ 50 bp entry cap); the event-class rule can be "macro: hold", logged. Add the gap rule, Monday re-sizes and the soft-block budget only if green on Oct 18.

**X3 (M) The first build collides with three of IDEA-010's own rules.**
- GDP/PCE is released Oct 29 08:30 ET = 12:30 UTC, before `trade_after` (14:00 UTC). §4 C blocks buys "in the two scheduled rounds around the release" without saying which two, so the first build moves to Oct 29 20:00 UTC or to Oct 30.
- Alphabet and Microsoft report Oct 28 after the close. An earnings move often exceeds 3σ (≈ 5–6% at σ 1.7–2%), so the gap rule ("this or the previous session") blocks GOOGL and MSFT on Oct 29 and Oct 30; they are built Nov 2 at the earliest.
- Their Oct 28 Item 2.02 8-Ks arrive before `trade_after`; an LLM flag gives soft blocks on the same names.

Half the book can miss 2 of ≈ 9 sessions by design [E]. **Fix:** define the macro window precisely and exempt the first build; exempt scheduled pre-run earnings from the gap rule, or drop the gap rule (X2).

**X4 (M) The Nov 9 re-size contradicts §2.** §4 T.3 re-sizes at the Monday close−60 rounds Nov 2 and Nov 9; Nov 9 20:00 UTC is also `last_buy`, and the flatten starts Nov 10 19:00 UTC. A Nov 9 buy is held about one session: the "mostly cost" case §2 used to set `last_buy`. **Fix:** the Nov 9 re-size may only reduce.

**X5 (M) MinPos from the live own-gas median: bootstrap and divergence.** §4 S.4 sets G = median of the last 20 own legs, default 0.035 USDT → MinPos 14 USDT.
- A fresh wallet has no legs, so both wallets start at the high default.
- Dev wallet ≈ 95 USDT at MinPos 14 [V, recomputed]: full-history vols → positions 7.3–12.5 USDT → **0 names held**; EWMA → 2 (IDEA-010 says 2–4). A soak that holds nothing never measures gas, so G never falls.
- The scored run computes MinPos from a different wallet's history: same code, different behaviour, and a parameter fitted live rather than pre-registered.

**Fix:** G is a frozen config value, measured on the dev wallet by Oct 19 and hashed in the manifest. At 200 USDT, TSLAB (15.4 USDT at full-history vol) sits near MinPos 14; re-check with the Oct 19 σ.

**X6 (M) Map M: which classes can EXIT is ambiguous.** §4 L.3 says judgement-only checks (an "unplanned" 5.02, a guidance comparison) give soft blocks only; §4 L.4 says any verified class ≠ NONE on a held name → EXIT. Item 5.02 is filed for every officer change, including planned retirements and pay (5.02(e)); 2.02 accompanies every earnings release. As written, a planned CFO retirement with a verbatim quote verifies and exits. **Fix:** state the EXIT set: {4.02, 1.05, 2.06}, verified by item code + verbatim quote; 5.02 and GUIDANCE_CUT → soft block only.

**X7 (M) "≤ 1 EXIT per name per run" plus re-entry after a 2-session cooldown** leaves a re-entered name with no evidence exit. **Fix:** no re-entry after a verified-adverse EXIT (also removes the re-entry code), or allow repeat EXITs.

**X8 (M) Agentic depth is lower than "medium".** With 8-K-only triggers the LLM may run 0–3 times in 14 days: last year's window had 4 8-Ks for the five issuers, two of them earnings that fall before this run (IDEA-009 §10). That is ≈ 99% of round logs with "no model call" (≈ 20 scheduled + ≈ 336 hourly rounds). F-115 says logs and repo are assessed; the page asks for an "LLM-powered Agentic AI system". Dropping 10-Q/10-K narrows the declared "8-K, 10-Q and 10-K" with a weak reason: Microsoft and Alphabet usually file the 10-Q within about a day of earnings (≈ Oct 28–30) [E, unchecked; count with `tools/edgar_fetch.py` on last year's window]. Options (IDEA-010 §11 row 2):
- (a) keep 10-Q/10-K as triggers, soft block only (≈ 0.5 pd [E], same schema, no deviation row);
- (b) a daily held-book review call with no action field that re-checks each thesis's falsifiers (the proposal declares falsifiers "re-checked every cycle"); tokens only; described honestly as a review, not a decision.

Recommend (a) now and (b) only if green on Oct 18 [O].

**X9 (M) Must-have #3 recipient/min-out decode as an activation blocker.** The swap goes to the LiquidMesh/RFQ router (`tx.to`, e.g. `0xB44446…`, K6); the kit gives no ABI. If the contract is unverified or the calldata is an opaque RFQ payload, decoding may be impossible, and as a MUST it would block activation. "≈ 0.5 pd" is untested. **Fix:** MUST = `to`/chain/`value`/selector allow-list, approve spender = `dexContractAddress` = `tx.to`, and `minReceiveAmount` within [x]% of the quote; the recipient decode becomes MUST only if Keith confirms the ABI by Oct 15.

**X10 (M) The 50 bp cap escalation should include gas.** Entry cost = spread + impact + G ÷ position. At MinPos, G ÷ position = 25 bp by construction; TSLAB at ≈ 15 USDT with G 0.035 → 23 bp. So the cap blocks small names at ≈ 25–30 bp/side of spread, not at the 40 bp in §6. **Fix:** state the Oct 19 escalation per name: escalate if median spread + impact > 50 bp − G ÷ position size.

**X11 (L) `tools/probe_quote.py`.**
- a. Lines 175–177: HTTP 401/403 prints "REFUSED: this host cannot use the Web3 API" and exits 2. A 401 is also a bad key or a timestamp outside the receive window, and the clock check is skipped on this path, so a good host could be rejected for a bad `.env` or clock. Only code 40304 means refused; on 401/403 print code and message and the local-vs-`Date`-header skew.
- b. Line 60: `load_dotenv()` loads the whole `.env` into the process environment, so the docstring's "never reads WALLET_PRIVATE_KEY … AI_SEEDS_SECRET" is not literally true (nothing is printed or saved). Use `dotenv_values()` and take only the two API variables.
- c. Line 108: `int(Retry-After)` raises on a non-integer header.
- d. "Round-trip cost" excludes the four gas legs: label it spread + impact; GAP-50 adds G separately.
- e. Records `rwa/tokens` market state only; the GAP-44 logger must also record `underlying-market` (IDEA-010 §7 action 3).
- f. Buy and sell are quoted ≥ 0.35 s apart; take repeated samples and use the median.

**X12 (L) Reproducibility of [E] numbers.** Reviewer B's scripts (G-22 simulation, regime firing ≈ 7% of runs, halve-and-restore 0.10–0.41%) stayed in a session scratchpad. Re-deriving the last from IDEA-010's stated inputs gives ≈ 0.10–0.24% at 5–20 bp [E]; its inputs are not stated. Commit the scripts (no data) under `tools/`, or mark these numbers "not reproducible".

**X13 (L) Labels and process.**
- "Three-reviewer" = three subagents of one model: one review with three passes, not independent reviewers.
- INCOMPLETE_WORK.md was not updated for IDEA-010 (§7 actions, §9 decisions; GAP-62 still points only to IDEA-009 §F; §5 replaces IDEA-009 §G.2). AGENTS.md checklist rule.

## 3. IDEA-009 → IDEA-010 → this review
| Topic | IDEA-009 | IDEA-010 | This review |
|---|---|---|---|
| LLM authority | B5: LLM picks CONFIRM / VETO_ENTRY / EXIT | Assessment only; code map M | Agree; explicit EXIT set (X6); 10-Q/10-K triggers (X8) |
| Base book | Outline (§H) | Full spec v1 (§4) | Simplify (X2); fix first build (X3), Nov 9 (X4), re-entry (X7) |
| Minimum trade | 25 USDT | Gas ÷ 25 bp from live own legs | Frozen config G (X5) |
| End of run | Flat by Nov 11 21:00 UTC | Last buy Nov 9; hard stop Nov 11 15:00 UTC | Agree |
| Build size | ≈ 20–24 pd | ≈ 48–52 pd vs ≈ 38–49 capacity | Agree on size; capacity unverified (X1) |
| Must-haves | 13 (§G.2) | 21 with tests | Agree; #3 conditional (X9) |
| Deviations | 14 rows | ≈ 10 more; H-02 "NOT RUN" | Agree |
| Expected value | Not stated | Net ≈ 0; exposure justified by F-115 | Agree (re-derived) |

## 4. Suggested additions to the Oct 11 agenda
1. Hours per person (X1) → cut depth decided Oct 11 — all.
2. IDEA-010 §1 with the explicit EXIT set (X6) and 10-Q/10-K soft-block triggers (X8 a) — SYZ.
3. Minimal base book (X2) with the X3, X4, X7 fixes, for D-08 — Isaac.
4. G as frozen config (X5); per-name cap escalation (X10) — Isaac, Oct 19.
5. Must-have #3 conditional on the router ABI (X9) — Keith, Oct 15.
6. `probe_quote.py` X11 a–c before the VM probe — Keegan, Oct 10.

## 5. Updates
- (none yet)
