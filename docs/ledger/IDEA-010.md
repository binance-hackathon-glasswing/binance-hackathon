# IDEA-010 — Three-reviewer review of IDEA-009: assessment-only LLM, window gates, base-book spec v1, must-haves and schedule

- Date / author: 2026-10-08 / Keegan (requested); three Claude review subagents (A rules/audit, B strategy/risk, C feasibility), two rounds each (independent review, then cross-review of the other two), merged by Claude
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** Feeds the IDEA-009 §8 decisions due Sun Oct 11. Nothing here changes live behaviour or any D-item.
- What: reviews and improves [IDEA-009](IDEA-009.md) (direction for v1.0) and the plan.md items it points to; settles where the three reviews disagreed; gives a pre-registerable base-book + LLM-mapping spec, a merged v1.0 must-have list with tests, a revised Oct 9–29 schedule and an Oct 9–11 action list.
- Why it might help: round 1 found one critical conflict with the submitted architecture, two critical spec bugs and a build estimate about 2× too low; fixing them before Oct 11 is cheap.
- Cost / risk: desk review only. Reviewers were read-only on the repo; no Binance, ai-seeds, wallet, SEC or web calls; no `.env` read. Reviewer B recomputed IDEA-009 §D with scripts on stated inputs (no market data). Raw reports (≈ 19k words) stayed in the session scratchpad and are not committed; everything decision-relevant is below.
- Links: IDEA-009, IDEA-004, IDEA-005, IDEA-006, D-03, D-04, D-05, D-08, D-11, D-12, G-01, G-03, G-11, G-13, G-14, G-18, G-19, G-21..G-30, G-40, G-46, G-50..G-53, F-07, F-15, F-42..F-50, F-61, F-64, F-93, F-101, F-109, F-113..F-117, Q-03, Q-06, Q-08, Q-33, Q-35, Q-39, Q-40, GAP-03, GAP-04, GAP-05, GAP-35, GAP-37, GAP-42, GAP-44, GAP-46, GAP-50, GAP-51, GAP-62

Labels as in IDEA-009: [V] checked in this review (file and quote), [E] estimate with inputs, [O] opinion. Every item below is [POLICY] unless tagged otherwise.

## 0. Summary
**Keep B5's effect, change who holds authority.** The submitted architecture PDF (not read by IDEA-009) says the LLM may never decide a trade. So the LLM becomes an evidence assessor, and a pre-registered code map turns *verified* adverse evidence into EXIT or an entry block (§1). Also:
1. **Two spec bugs:** the 25 USDT minimum trade blocks three of the four E1 positions (§3), and "flat by the Nov 11 close" can be ~5 h after the earliest plausible window end (§2).
2. **The build is ~2× IDEA-009's estimate:** ≈ 48–52 person-days against ≈ 38–49 of capacity to Oct 26 [E]. It fits only with the cut list in §6 and with build work continuing into the Oct 20–22 soak days.
3. **Expected net return of the base book is ≈ 0** (≈ −0.13% to +0.10% of equity at 5–20 bp spreads [E]); being invested is justified by F-115 ("if you don't trade at all? That's definitely not what this competition is about"), not by expected gain. Do not add round trips to raise the trade count.
4. **Two run-stoppers missing from IDEA-009 §G.2:** the fresh final wallet may also start with 0 BNB (Q-03 recurs on Oct 27–29), and a wrong or late final-wallet `AI_SEEDS_SECRET` gives `UploadError`, which the SDK neither retries nor saves (F-109).

## 1. LLM authority: assessment only (A1, critical)
- **Source [V]:** `docs/proposal/LARP_System_Architecture.pdf` (submitted): "LLM zone: authority over evidence only, never over trades"; "The output schema cannot express a trade. A timeout or schema failure means HOLD."; "Guardrails: the LLM has no trade authority; deterministic layers act." IDEA-009 §2 calls the "schema forbids trade actions" point "mis-sourced" after checking only `proposal_answers.md`; the PDF is the source. IDEA-009 §1 does not list the PDF as read.
- **Problem:** B5 as written lets the LLM choose EXIT per name, i.e. a trade action, which contradicts the submitted architecture (F-48 "no material misrepresentation").
- **Recommended form:** the LLM returns an assessment per new filing with **no action field** (§4 L.2). Code verifies it (G-53) and a pre-registered map M (§4 L.4) produces EXIT or ENTRY_BLOCK. This keeps the declared design, is ≈ 0.5 pd less work than the menu [E, C], and the audit trail shows code deciding.
- **External wording (logs, manifest, docs):** "A pre-registered rule book sets targets; an LLM evidence agent reviews new filings; code decides, sizes and executes." Do not describe the LLM as deciding.
- **Fix in IDEA-009 (append-only, as a dated note):** §1 add the PDF; §2 row "§5.6" corrected; §B/§H "LLM" replaced by this section; plan.md D-11 recommendation follows.

## 2. Run-window gates (A3 + B2 + C, reconciled)
- **Why [V]:** F-07: the organiser set DoraHacks times on UTC+8 boundaries. If the 14 days are Oct 29 00:00 → Nov 12 00:00 UTC+8, the window ends **Nov 11 16:00 UTC**, 90 min into the Nov 11 US session (EST after Nov 1: session 14:30–21:00 UTC). IDEA-009 §A's "earliest plausible end Nov 12 00:00 UTC" and "flat by the Nov 11 close (21:00 UTC)" are then ~5 h late. A round-1 timing error (EDT used for Nov 10) was corrected in round 2.
- **Recommended gates (config, hashed before the freeze):**

| Gate | UTC | SGT | Reason |
|---|---|---|---|
| `trade_after` | Oct 29 14:00 (first open+30 round) | Oct 29 22:00 | Inside every plausible window |
| Last first-build of a name | Nov 4 21:00 | Nov 5 05:00 | A late build is mostly cost |
| `last_buy` | Nov 9 20:00 round | Nov 10 04:00 | A buy on Nov 10 would be sold within hours: premium ≈ 0.02% vs round trip 0.03–0.17% [E, B] |
| `flatten_start` | Nov 10 19:00 and 20:00 rounds (close−120, close−60) | Nov 11 03:00, 04:00 | Last full session before the earliest end |
| Retries | Every round, and hourly while `openState` is true on both endpoints | — | Exits only |
| `flatten_by` (hard stop for trading) | Nov 11 15:00 | Nov 11 23:00 | 60 min before the earliest plausible end |
| After | Hold-only rounds (`END_OF_RUN`) until stopped after Nov 13 | — | One log per round continues |

- If the organisers publish the window end `T_end` before the freeze, set `flatten_start` to the last close−120 round before `T_end − 20 h`; after the freeze nothing can change (F-117).
- Cost: 1–2 sessions without exposure ≈ 0.02–0.05% of equity in forgone expected premium [E, B].
- Settled disagreement: A and C had `last_buy` Nov 10 14:30 and a 15:30 hard stop; B's earlier `last_buy` and 15:00 stop are adopted (cheaper, more margin).

## 3. Arithmetic re-check of IDEA-009 §D (B, script on IDEA-009's own inputs)
Mostly correct. Corrections:

| Claim | IDEA-009 | Recomputed [E] |
|---|---|---|
| SKHYB σ per session / weight | 5–6% / 3.7–4.5% | 4.7–6.0% / 3.7–4.7% |
| §D.3 10-session dispersion at gross 0.4 / 0.55 / 0.8 | 2.3 / 3.2 / 4.6% (equal weights) | 2.2 / 3.0 / 4.4% (vol-scaled weights) |
| §D.3 "each unnecessary round trip costs about as much as the whole expected premium" | — | True only for a whole-book round trip or at ~50 bp spreads; one name at 5 bp costs far less |
| Minimum trade 25 USDT vs E1 positions at 200 USDT | consistent | **Bug:** NVDA 18.7, GOOGL 22.9, TSLA 15.4 USDT (full-history vols) are all below 25, so the book holds 1–3 names; band trades on ~20 USDT positions are 2–6 USDT, so F2 gives ≈ 4 round trips, not 4–8 |
| Expected net of E1 over the run | not stated | ≈ −0.13% to +0.10% at 5–20 bp/side; −0.31% to −0.46% at 50 bp |
| G-22 at E1 (11-session simulation, fat tails) | "rarely fire" (I-62) | daily ≥ 3%: 2.4% of runs; drawdown ≥ 8%: 0.25%; ≥ 12%: 0.02% |
| Regime rule at 2× with no real vol change | — | fires in ≈ 7% of runs; each halve-and-restore costs 0.10–0.41% of equity → needs hysteresis |
| Off-hours `openState: true` (K6b) | hints at off-hours trading | The field was `ondoStatusInfo` in a Skill response, not the bStock endpoint; GAP-44 must measure `rwa/tokens` directly |

## 4. Base-book + LLM-mapping spec v1 (pre-registerable; B round 2, simplified per C)
Everything inside the declared values (≤ 4 positions, ≤ 20% per name, ≤ 80% gross, 1% ÷ 2σ₅ sizing, G-22 3% / 8% / 12% → 40%, ≤ 50 bp one-way entry cost). Brackets are frozen by Oct 22 from data or the stated method, never from P&L (G-46). UTC internally; NYSE sessions from `America/New_York` (zoneinfo + pinned `tzdata`).

**U. Universe.** Fixed: NVDAB, GOOGLB, TSLAB, MSFTB. SKHYB not held (target 3.7–4.7% of equity, highest σ; ≤ 4 positions). Deviation row: none needed (the proposal names no universe); state it in the manifest.

**S. Sizing and marks.**
1. σ_i = sd of log returns of bStock `tokenPrice` sampled at close−60 from 1 h candles, last 60 NYSE sessions (GOOGLB has ≈ 75 sessions by Oct 29, so no fallback source is needed).
2. w_i = min(20%, 1% ÷ (2 × σ_i × √5)) × R; gross cap 80% (not expected to bind).
3. **Equity marks (settled disagreement):** the proposal declares "equity measured on executable quotes", so equity = USDT + executable sell-quote value per position + BNB value. If a sell quote fails or deviates from `tokenPrice` by > [3]%, mark at `tokenPrice` × (1 − [1]%) and log `MARK_SANITY`. This keeps the declaration and stops one bad quote from firing G-22 (B's concern).
4. **Minimum position / trade (settled disagreement):** MinPos = G ÷ 0.0025, where G = median USDT gas per approve+swap over the last 20 own legs (default 0.035, F-93 high), i.e. 6.8–14 USDT. Same code and config on both wallets. At 200 USDT all four names are held; at the ~95 USDT dev wallet 2–4 are (B). C preferred 6% of equity so the dev soak holds the full book; **team choice** — if the dev soak must test four names, use max(G ÷ 0.0025, 6% of equity) only in the rehearsal config and record that the scored config differs in that one value. 12.5% of equity (C round 1) is rejected: it blocks 3 of 4 names at any equity.
5. Re-size only when |Δ| ≥ max(30% × target, MinPos). Exits, flatten and risk cuts are exempt from MinPos and band.

**R. Regime.** Basket = weight-normalised mean of the four names' session returns; ρ = RMS(last 5) ÷ sd(last 60). At each close−60 round: ρ > 2.0 → R = 0.5; ρ > 3.0 or a basket session return ≤ −4σ₆₀ → R = 0. Restore one step only after ρ < 1.5 on 2 consecutive sessions; at most one step per session. Thresholds fixed at 2.0 / 3.0 / 1.5; a 0.5 pd report shows their exceedance rates on Ondo + bStock history (expected 2–10% / 0.2–2% of sessions), without looking at returns after exceedances. No data fitting (C).

**C. Cadence.**
- Scheduled rounds at open+30 and close−60 on NYSE sessions; event rounds on a new allow-listed filing (L.1); one round at a time.
- Hourly hold-only monitor rounds 24/7 (G-22 marks, gas, spool, reconciliation); they never call the LLM and quote only held names (Q-38 quota).
- Event class "macro" (GDP/PCE Oct 29, midterms Nov 3, NFP Nov 6, CPI Nov 10): hold existing positions, no new buys in the two scheduled rounds around the release (declared per-event-class rule, G-23). No earnings for the four names fall inside the run (Alphabet and Microsoft Oct 28; NVIDIA after).

**T. Order generation per round, in order.**
1. Gates: G-03, G-09, G-18 UNRESOLVED (per name), G-27, `openState` true on both endpoints (an endpoint error counts as closed **for buys only**), spool older than [30] min, gas ≥ floor. A failing gate → no buys; exits run wherever `openState` is true.
2. Risk exits: R = 0 → sell all; G-22 12% → cut to ≤ 40% gross; flatten (§2); mapped EXITs (L.4); regime cuts to target.
3. Buys only if none of: G-22 3% (until 00:00 UTC) or 8% (rest of run); ENTRY_BLOCK or cooldown; gap rule (name's session return beyond ±[3]σ_i this or the previous session); after `last_buy`; entry cost (spread + impact vs `tokenPrice`, plus G) > 50 bp; median measured spread > [15] bp/side for discretionary re-sizes. Buys happen at the first build (first scheduled round after `trade_after`; retried each scheduled round; none after Nov 4 21:00 UTC), at re-sizes (Monday close−60 rounds Nov 2 and Nov 9, and on an R restore) and at re-entry after a cooldown.
4. Execution: sells first (largest first), then buys (smallest first); one name at a time: approve → confirm → re-quote → `tx.to` check → swap → confirm; USDT ≥ order + 2 USDT before each buy; a failed buy's cash is not reallocated in the round.
5. Price-impact caps (replace the depth cap, GAP-51): entries ≤ min(50 bp, 2 × logged median one-way cost at that size); exits ≤ 4 × that median; failed exits retried each round.

**G. Gas.** Floor = 2 × (held names + 1) × [0.00005] BNB; top-up of [0.0005] BNB below the floor, as its own logged round (`symbol: "BNB"`, Q-08 assumption); from Nov 9 top up only enough for the flatten; `NO_GAS` → hold rounds, no crash. No BNB → USDT sale at the end (not "for gas", G-13, F-64).

**L. LLM assessment and deterministic map M.**
1. **Trigger:** a filing for the four CIKs with form ∈ {8-K, 8-K/A} and `acceptanceDateTime` after the previous round. Forms 4, 144, 10-Q, 10-K, S-8, 424B, SC 13G, DEF 14A, 6-K are logged as seen, never trigger and are never citable (scope reduction from the declared "8-K, 10-Q and 10-K": deviation row).
2. **LLM output (JSON schema, no action field):** `cik`, `accession`; `adverse_class` ∈ {NONE, ITEM_4_02_NON_RELIANCE, ITEM_2_06_IMPAIRMENT, ITEM_5_02_CEO_CFO_DEPARTURE, ITEM_1_05_CYBER_IMPACT, GUIDANCE_CUT}; `claims[]` {`text`, `quote` ≤ 300 chars verbatim}; `entry_concern` ∈ {NONE, ADVERSE_UNSPECIFIED}; `summary` ≤ 3 sentences. One call per filing with the filing text pushed in (no tool loop: deviation row).
3. **Verifier (code, G-53):** each quote appears verbatim in the stored filing text (whitespace-normalised); `adverse_class` matches the submissions JSON `items` (4.02 / 2.06 / 5.02 / 1.05; GUIDANCE_CUT needs 2.02 or 7.01). Judgement-only checks (whether a 5.02 departure is "unplanned", 2.06 materiality, numeric guidance comparison) are not verifiable by string match: they may only produce a soft block, never an EXIT (C).
4. **Map M:** verified class ≠ NONE and name held → **EXIT** (≤ 1 per name per run; if `openState` is false, queued to the next open+30 round, citing the original `decision_id`); verified class ≠ NONE and not held → ENTRY_BLOCK until the cooldown ends; verification fails, `entry_concern` set, or LLM failure (timeout or schema failure after ≤ 2 retries) with a filing pending → **soft ENTRY_BLOCK** for that name only, expiring at the next session's close−60 round, not renewable on the same accession. Nothing in M can raise a target.
5. **Bounds:** soft blocks capped at [6] name-sessions per run, ≤ 1 active per name (C's single counter; B's extra "≤ 2 names at once" dropped for build time). Beyond the cap M returns NONE and logs `BLOCK_BUDGET_EXHAUSTED`. Cooldown after EXIT or verified block: [2] full sessions; re-entry at the next scheduled round subject to T.3. Unbounded "any concern → no entry" is rejected: an LLM that flags every filing would drift the book to cash against F-115. This does not override the declared "If the core claim fails, the agent takes no new risk": base-book entries carry no catalyst claim.
6. **Expected value [E, B]:** ≈ 0–0.5 qualifying filings in the run and mega caps reprice within minutes, so the map's expected effect on score is ≈ 0; its value is risk control, the audit trail and the agentic-depth story. Say so in logs and docs.
7. **Logging:** evidence round: `input` = full request, `cot` = provider summary, `output` = assessment + verifier results + M result, `orders` = what code placed. Deterministic round: `cot` = "no model call: <rule, inputs>; EDGAR poll <ok/failed> at <UTC>; LLM <ok/unavailable>". Every round logs the base-book counterfactual target beside the actual one (lets the overlay be evaluated afterwards, IDEA-005 R4).

**K. Fallbacks.** A name whose build fails > [3] times in a row is skipped for the run; LLM unavailable → base book runs, soft blocks only for names with pending filings; EDGAR unreachable → logged as a health state, never as "no new filings"; never route around a block (G-17).

## 5. Merged v1.0 must-have list (replaces IDEA-009 §G.2; failure of any blocks activation)

| # | Must-have | Test |
|---|---|---|
| 1 | G-09: signing key address = `AI_SEEDS_ADDRESS` = manifest `wallet_address`, else refuse to start | Mismatch → exit ≠ 0, nothing signed |
| 2 | G-03: remote presence checked at start-up; local tree hash vs manifest before every order; hash excludes `manifests/`; wallet address and secrets from env | Dirty tree → no order, hold log; GitHub unreachable after start → trading continues |
| 3 | G-01: approve only to {4 bStocks, USDT}, exact amount, spender = `dexContractAddress`; swap `tx.to` = spender, chain 56, `value` 0; allow-listed swap selectors with **recipient and min-out decoded** (≈ 0.5 pd); routers seen in dev pinned, a new router blocks buys and is allowed for exits only after the recipient check; USDT → BNB only for gas | 8 crafted payloads rejected (dry run) |
| 4 | Symbol allow-list in `orders` (F-110); gas top-up logged as its own round | Bad symbol rejected before `log()` |
| 5 | G-04 write-ahead journal (SQLite WAL, one transaction per state change); signed raw tx and locally computed tx hash journalled before broadcast | `kill -9` at each of 9 steps → terminal or UNRESOLVED, no duplicate swap |
| 6 | G-18: at-most-once signing, reconcile before re-sign, no blind nonce + 1; 120 s → UNRESOLVED; `ORPHAN_APPROVE` state; nonce reconcile on restart | Injected nonce error and timeout behave as specified |
| 7 | G-19: one log per round on every path; re-log after a crash before any new round; two round types with health line | Fault at each step → exactly one valid log per round, every swap `tx_hash` present |
| 8 | ai-seeds **realtime mode only** (batch can lose a day on restart, F-109, and its fallback `manual_push.sh` is a human action); start-up self-test hold log delivered (spool empty) before any order; own `UploadError` retry queue (hourly); spool > [30] min → incident, > [2] h → no buys | Endpoint blocked → spooled → restart → delivered; wrong secret → no orders, queue retries |
| 9 | Round-log size cap [2] MB (cited sections + URL + sha256; full text in the journal) | Largest recent 8-K → log < 2 MB |
| 10 | G-30 `openState` on both endpoints; error = closed for buys; EXIT queue while closed | Mocked false/error → no buy; exit queued |
| 11 | G-28 gas floor and top-up; `NO_GAS` hold state | 0-BNB wallet → hold rounds, no crash |
| 12 | Autonomous HALT of **buys** (exits and logs continue; clears when reconciliation resolves, since no human can reset it): unknown outgoing tx / nonce gap, version mismatch, address mismatch, UNRESOLVED > [6] h | Each trigger injected; state persists across restart |
| 13 | G-22 halts and G-27 degraded mode with §4 S.3 marks | One bad quote cannot fire G-22; 3/8/12% scenarios |
| 14 | Base book per §4 (universe, MinPos, Monday re-size, sequencer, caps, 50 bp entry cap) | Build day on mocks, then one live build on the dev wallet |
| 15 | Regime rule §4 R | Synthetic paths → expected R sequence |
| 16 | LLM path §4 L | Fixture filings (adverse, benign, Form 4) → expected code actions; provider down 3 days → book still builds |
| 17 | Window gates §2 | Clock-shifted simulation over Oct 29 and Nov 9–11 |
| 18 | DST-safe sessions (zoneinfo + pinned `tzdata`), UTC internal; G-05 clock check (chrony) | Oct 30 (EDT) and Nov 2 (EST) unit tests; offset > 500 ms → no orders |
| 19 | Event-class rule, gap rule (§4 C, T.3) | Config fixtures |
| 20 | systemd `Restart=always`, `flock` single instance, heartbeat, daily reconciliation report (G-43) | Kill → restart < 60 s; second instance refuses |
| 21 | LLM snapshot pinned, deprecation date after Nov 20, credit prepaid through Nov 20; EDGAR declared User-Agent, ≤ 1 req/s | Activation checklist |

## 6. Capacity, cuts and deviations (C, with A's conditions)
- **Estimate [E, C]:** no runtime code exists yet (tools/ holds read-only probes and fetchers). Bottom-up ≈ 38–40 pd + 15–20% integration ≈ 44–48 pd; after the cuts below and A+B's additions ≈ 48–52 pd; capacity to Oct 26 ≈ 38–49 pd (≈ 22–29 to Oct 19). IDEA-009 §E's "≈ 20–24 pd" should be replaced.
- **Cuts, each a deviations-register row quoting the declared text and giving an evidence-based reason (A: "schedule" alone is not enough):**

| Cut | Declared text | Row must say |
|---|---|---|
| Cold standby | "one primary runtime plus a fenced cold standby" | Under F-114/F-117 no human may fail over during the run, so a standby could never be used; single instance + `flock` + automatic restart of the same version (Q-40 assumption); G-18 (c) epochs dropped, the rest stays MUST |
| PostgreSQL → SQLite | "Stack: Python, PostgreSQL, and write-once object storage" | Same append-only, sequence-numbered, hash-chained journal; implementation change |
| Hourly anchoring | "anchored hourly" | Chain head in every ai-seeds round log `input` (stored byte for byte by the organisers, F-101), i.e. per round; nightly off-box journal copy (F-47); I-68 (d), GAP-35 |
| Bounded tool loop | "capped at 6 calls and 60 s per decision"; four named tools | One call per filing with the text pushed in; GAP-03 |
| Free-form thesis memory | "thesis memory with falsifiers" | **Not cut:** keep a minimal stored thesis object per held name (catalyst "base-book holding", horizon = run end, falsifiers = §4 L.2 classes, evidence IDs appended after verification); row says falsifiers are a fixed pre-registered list |
| Full calldata decoder | (G-01) | **Not cut:** recipient + min-out decode kept (#3 above) |
| Skills context, GDELT, Ondo fallback, data-fitted regime thresholds, dual off-hours mode, numeric falsifier checks | GDELT "second independent source" | Claim verification is against primary EDGAR text only |

- **If still behind on Oct 18, cut in order:** soft-block budget (keep expiry) → regime hysteresis (keep a plain threshold) → the LLM path entirely (base book + risk rules, recorded as a deviation; IDEA-009 §G.3 #5). Never cut §5.
- **Further deviation rows IDEA-009 §F misses (A):** branch protection — the proposal says "The challenge branch is protected" but G-40 records it is unavailable on our GitHub plan (upgrade before activation, or a row); event-calendar planner (static calendar only); per-event-class rule (§4 C); memorisation tests and the post-cutoff evaluation (not run); off-hours hypothesis (execution guard only, as declared); release-calendar source; signer as a separate service (in-process module); "Improvements are versioned releases, at most one a day" (none during the run); "Humans can halt the agent" (no human action, autonomous HALT of buys); 8-K-only triggers vs "8-K, 10-Q and 10-K". **H-02 / EXP-001 is recorded as "NOT RUN"** (training data on hold; "The evidence-assisted model trades only if it passes on held-out data" was never met, so the pre-registered default runs), not as "inconclusive". Rule for the register: every row quotes both submitted documents (answers and PDF).
- **Kept from the declarations (A):** the ≤ 50 bp one-way entry-cost cap. If the Oct 19 logger readout shows median one-way cost > 40 bp, the cap blocks the whole build: treat that as a **team escalation**, not a silent zero-trade run. Exits are never subject to it (G-25).
- **Not added:** extra round trips to raise the trade count (cost 0.03–0.68% of equity each [E, B]; resemble the wash trades Binance banned in its Aug–Sep bStocks contest, E-18).

## 7. Revised schedule (SGT) and Oct 9–11 actions (C round 2, with §2 gates)

| Dates | Yao Zhu (Agent) | Isaac (Markets/Risk) | Keith (Execution) | Keegan (Platform/Audit) | Exit criterion |
|---|---|---|---|---|---|
| Oct 9–11 | Send organiser questions; IDEA-009 corrections; LLM accounts | Quote + `openState` logger on a separate API key | Adapter quote-only with fixtures | VM probe; skeleton, interfaces, CI, lock split, mock ai-seeds; GitHub plan | Direction, cut list and owners decided Oct 11; host chosen; logger running |
| Oct 12–14 | EDGAR poller (8-K trigger); bake-off set | Scheduler, window gates, σ | Allow-list, nonce, state machine | Journal, round runner (two types), release script; agent on host under systemd (quote-only) | Quote-only rounds logging on the host |
| Oct 15 | Bake-off → D-03 | Sizing, MinPos | First minimum-size round trip **if** BNB and secret have arrived, else mocks | Spool monitor, `UploadError` queue, self-test | Round trip reconciled, or fallback recorded |
| Oct 16–18 | Assessment schema, verifier, map M | Regime, G-22, marks, sequencer | Gas top-up, HALT triggers, `ORPHAN_APPROVE` | Supervisor, heartbeat, reconciliation report, deviations draft | Oct 17 full pipeline in shadow; Oct 18 week-one checkpoint |
| Oct 19 | Integration | Logger readout → band, caps, spread escalation check | Signer on at v1.0 sizing | Manifest rc0 | D-08 base book pre-registered by commit |
| Oct 20–22 | Fault matrix (LLM rows) | Fault matrix (window/flatten) | Fault matrix (execution) | Fault matrix (logging/restart) | **Oct 22 cut line = feature freeze** |
| Oct 23 | Fixes | Fixes | Fixes | rc1 tagged | rc1 running unchanged |
| Oct 23–26 | Observe; deviations final | Rehearsal flatten at the Oct 23 close (rehearsal config) | Recovery drills ×2 | Self-check evidence bundle | Final rc ≥ 48 h unchanged, incl. one session with trades and two 00:00 UTC rollovers |
| Oct 27–29 | — | — | Final key on host; offline backup | Activation runbook: `.env`, manifest commit, start, self-test log | Agent holding until `trade_after`; integrity check passed |

**Oct 9–11 actions** (≈ 51 h [E]; items 4–6 may spill into Oct 12, none gates the Oct 11 decision):

| # | Action | Owner | Hours | By |
|---|---|---|---|---|
| 1 | Send organiser questions (in their wording, no internal IDs): exact scored-window start and end instants; how to register the repository and the audit account; whether BNB for the first gas is provided for **both** wallets and whether BNB counts in equity; whether an automatic restart of the same registered version, or a coded pause, counts as manual intervention; whether the final wallet gets a new log-signing secret and when; plus the remaining IDEA-009 §8 #3 items (scoring composition, trading hours, valuation source) | SYZ | 1 | Fri Oct 9 |
| 2 | Singapore cloud VM probe (signed read call, one quote, `tools/edgar_fetch.py --per-company 1`); choose the host; fallback a home machine on UPS; never a VPN or relay (G-17; E-15 reports `40304` from Singapore servers) | Keegan | 3 | Sat Oct 10 |
| 3 | Quote + `openState` logger (GAP-44, GAP-50) on a separate Developer Portal key, committed before it runs, no wallet or `AI_SEEDS_*` variables; record `rwa/tokens` and `underlying-market` separately | Isaac | 6 | Start Fri Oct 9 |
| 4 | Repo skeleton, interfaces (intent, round record, assessment schema, journal rows), CI, runtime/research lock split, `tzdata` | Keegan | 6 | Sun Oct 11 |
| 5 | Mock ai-seeds endpoint (`AI_SEEDS_URL`) and round-runner skeleton with the G-19 finally-path | Keegan | 5 | Sun Oct 11 |
| 6 | Adapter quote-only with recorded fixtures; balances, `rwa/tokens`, rate limiter | Keith | 10 | Sun Oct 11 |
| 7 | LLM provider accounts, snapshot deprecation dates, prepaid credit | Yao Zhu | 2 | Sat Oct 10 |
| 8 | GitHub plan decision (branch protection) or deviation row | Keegan | 1 | Sat Oct 10 |
| 9 | Dated corrections to IDEA-009 (§1 PDF; §2 row; §A window; stale items in §8 below) | SYZ | 3 | Sun Oct 11 |
| 10 | Team meeting: §1 form of B5, cut list, §5 must-haves, owners and backups (GAP-37), daily 15-min stand-up | All | 2 each | Sun Oct 11 |
| 11 | Base-book spec §4 as the D-08 candidate | Isaac | 4 | Sun Oct 11 |

**Testing with real money (C):** dev wallet budget ≈ $2–4 of gas and spread, ≥ 80 USDT untouched until the rehearsal; plumbing round trips at ~2 USDT; every dev transaction from a committed, manifested version as scheduled test-mode agent rounds (`version_id` and `"test_mode": true` in `input`, F-106 (c)), never a one-shot script a human launches (F-64, never-do #13). A test schedule file is config, so each batch is a version event.

## 8. Stale or inconsistent items found (A)
- IDEA-009 §9 says GAP-61 (Skills probe) was added; no GAP-61 is in INCOMPLETE_WORK.md now. The probe ran on 2026-10-08 (IDEA-009 §10), so the item was presumably removed as completed (AGENTS.md checklist rule); nothing to restore. IDEA-009 §8 #5 (Skills probe) is likewise done; mark it so in a dated note.
- Several files still cite "Oct 10 declarations" or "by Oct 10" (e.g. IDEA-007 §4, IDEA-001 §12, IDEA-008 §7 R1) although Q-33 re-dated them; correct by dated notes, not rewrites.
- SKILL.md G-14 ("Register a hold/exit-only build before Oct 29 … when a normal deploy is impossible") conflicts with G-46 (no manual switch to a safe-mode build during the run); G-14 should point to G-46.
- IDEA-009 §C.2 allows Anthropic `web_fetch` as an EDGAR fetcher; drop it: our own fetcher gives the complete request/response record (F-49 (c)) and the declared User-Agent.

## 9. Decisions needed (add to IDEA-009 §8; owners per GAP-37)
1. Adopt the assessment-only form of B5 (§1) — SYZ with all, Oct 11.
2. Window gates (§2) as config — Isaac, Oct 11 (changed only by an organiser answer before the freeze).
3. Base-book spec §4 as the D-08 default, including the MinPos choice for the dev soak — Isaac + Yao Zhu, Oct 19.
4. Cut list and deviation rows (§6) — Keegan drafts by Oct 19, final Oct 26.
5. §5 replaces IDEA-009 §G.2 — Keegan + Keith, Oct 11.
6. GitHub branch protection: upgrade or declare — Keegan, Oct 10.
7. Host after the VM probe — Keegan, Oct 11.

## 10. Updates
- 2026-10-08 (Keegan, drafted with Claude): `tools/probe_quote.py` added for the §7 action 2 VM probe and the first quote-cost sample (GAP-50): signed read with a `40304` check, clock check, `rwa/tokens` market state, buy + sell quotes per token and size, round-trip cost in bp; GET only, no signing, no ai-seeds, never reads wallet or ai-seeds secrets; raw responses to `data/probe/` (git-ignored). Tested only against mocked responses; the first real run confirms the `quote-and-swap` field names.

## 11. Handoff: main points of contention (2026-10-08, Keegan, drafted with Claude)
For anyone picking this up before or at the Oct 11 meeting. Nothing here is decided.

**Readiness.** Building can start now on the parts every direction needs: adapter (quote-only first), write-ahead journal, one log per round, version gate, signer allow-list, supervisor, quote/`openState` loggers. The decision logic (base book, LLM map, window gates) waits for the Oct 11 direction decision and the D-08 pre-registration (Oct 19).

**Points of contention (team call needed):**

| # | Question | Positions | Current recommendation | Decides |
|---|---|---|---|---|
| 1 | Who holds trade authority? | IDEA-009 B5: the LLM picks CONFIRM / VETO_ENTRY / EXIT. Reviewer A: the submitted PDF says "the LLM has no trade authority" | LLM assesses only; code maps verified adverse 8-K evidence to EXIT or an entry block (§1) | SYZ + all, Oct 11 |
| 2 | Agentic depth vs safety | Under §1 the LLM runs only on new 8-Ks (≈ 0–0.5 qualifying filings expected in the run), so its visible role is modest; logs and repo may be assessed (F-115) | Accept, and restore the bounded tool loop (G-50, +2.5–3 pd) only if the build is green on Oct 18; the alternative is to budget it from the start and cut elsewhere | Team, Oct 11 / Oct 18 |
| 3 | Model-layer track | None (IDEA-009 §E) vs IDEA-007 Track A (trained veto classifier, kill check Oct 17) vs IDEA-008 (Keith's three-model fusion) | None for v1.0; Track A only with spare capacity | SYZ + Keith, Oct 11 (GAP-57) |
| 4 | Build size | IDEA-009: ≈ 20–24 pd. Reviewer C: ≈ 48–52 pd vs ≈ 38–49 capacity | Use C's estimate; adopt the §6 cut list with a deviation row per cut | Team, Oct 11 |
| 5 | Which cuts | C: cut standby, PostgreSQL, anchoring, tool loop, thesis memory, calldata decoding. A: thesis object and recipient/min-out decode are declared or safety items | Cut the first four; keep a minimal thesis object and the recipient/min-out decode (§6) | Keegan + Keith, Oct 11 |
| 6 | Minimum position | B: gas-based (gas per leg ÷ 25 bp ≈ 7–14 USDT; dev wallet holds 2–4 names). C: 6% of equity so the dev soak holds all four. 12.5% of equity rejected | Gas-based for the scored config; team decides whether the dev rehearsal uses a different value (§4 S.4) | Isaac, Oct 19 |
| 7 | Run-window gates | A/C: last buy Nov 10 14:30 UTC, hard stop 15:30. B: last buy Nov 9 20:00, hard stop 15:00 | B's earlier times (§2); any organiser answer on the window end (Q-06) before the freeze replaces them | Isaac, Oct 11 |
| 8 | Equity marks for G-22 | A: executable quotes, as declared. B/C: `tokenPrice` (quote noise could fire G-22) | Executable quotes with a `tokenPrice` fallback and sanity band (§4 S.3) | Isaac, Oct 19 |
| 9 | Soft entry blocks | A (round 1): any flagged concern → no new entry. B/C: unbounded blocks let a noisy LLM drive the book to cash | Expire after one session, cap 6 name-sessions per run (§4 L.5) | Yao Zhu, Oct 19 |
| 10 | 50 bp entry-cost cap | Declared, so keep it (A); but if spreads exceed ≈ 40 bp/side it blocks every buy, i.e. zero trades (B) | Keep; an Oct 19 readout above 40 bp is a team escalation, not a silent zero-trade run (§6) | Isaac, Oct 19 |
| 11 | Regime thresholds | B: fit from data by Oct 22. C: fixed 2.0 / 3.0 / 1.5 plus a report | Fixed values + report (§4 R) | Isaac, Oct 22 |
| 12 | GitHub branch protection | The proposal says "The challenge branch is protected"; G-40 says our plan cannot | Upgrade the plan before activation, or add a deviation row | Keegan, Oct 10 |

**Risks to the deployed agent that no design choice removes** (each has an owner in §7 or §9):
- The bStock spread is unmeasured. Run `tools/probe_quote.py` and start the logger now (Isaac).
- First gas (BNB) for **both** wallets (Q-03) and the dev and final `AI_SEEDS_SECRET` (F-113, Q-35). Ask the organisers by Oct 9 (SYZ).
- Host access: a cloud IP may get `40304` from the Web3 API or be blocked by the SEC. Run the VM probe by Oct 10 (Keegan); never use a VPN or relay.
- Unanswered rules: window end (Q-06), scoring composition (Q-39), automatic restart (Q-40), off-hours trading (Q-32). The design survives either answer at a small cost.
- The freeze (F-117): no fix is possible during the run, so the §5 must-haves and a final release candidate running ≥ 48 h unchanged are the safeguards.
- Owners and backups are not named (GAP-37).

**Ranked options** (feasibility by Oct 26 / agentic depth; opinion):
1. This entry's assessment-only design (high / medium).
2. Plus the bounded tool loop (medium / medium-high).
3. IDEA-007 Track C forward data (high / low; a prerequisite).
4. B4, rules + LLM veto (high / low-medium; the fallback).
5. IDEA-007 Track A (low-medium / medium).
6. IDEA-006 risk-constrained Kelly sizing (medium-high / low).

Rejected for v1.0:
- IDEA-009 B5 menu, B2 and B3: they give the LLM trade authority, which conflicts with the submitted PDF.
- B1 / IDEA-004 fitted overlay: cannot be validated.
- IDEA-002, IDEA-008: no rights-clear corpus or timeline.
- H-01: `openState` unknown, sample too small.

**Next steps:**
1. Oct 9: send the organiser questions; start the loggers.
2. Oct 10: VM probe; GitHub plan; LLM accounts.
3. Oct 11: decide rows 1–5, 7 and 12 above, plus owners.
4. Oct 19: pre-register the base book (D-08) with rows 6 and 8–11.
5. Oct 22: cut line.
6. Oct 26: freeze the v1.0 candidate.
