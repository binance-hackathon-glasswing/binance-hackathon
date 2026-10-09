# IDEA-016 — Response to a second review of IDEA-012 (action precedence, drawdown ladder, measurements, costs)

- Date / author: 2026-10-10 / SYZ (requested); drafted by Claude (Cowork). Review text: a read-only review of IDEA-012 shared by SYZ as a screenshot (reviewer not named); seven findings, summarised in §1.
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** Changes no D-item, no code, no live behaviour.
- Links: IDEA-012 §1, §4, §8, §10; IDEA-015; `docs/proposal/proposal_answers.md` (drawdown control); F-61, F-115; Q-39; D-11, D-12; GAP-62.

Labels: [V] checked here, [E] estimate, [O] opinion.

## 1. The review (summary)
Verdict: keep IDEA-012 as a design candidate; do not adopt its draft rules yet. Findings: #1 [High] ENTER/EXIT outputs breach the submitted authority boundary; #2 [High] safety actions need explicit precedence; #3 [High] N1 can permanently miss filings; #4 [High] concentration and the weaker drawdown control lack support; #5 [Medium] 4-of-5 agreement is not calibrated confidence; #6 [Medium] the measurements support weaker conclusions than drawn; #7 [Medium] the cost estimate and drift rules do not reconcile. Recommendation: repair action precedence and event handling first; defer the exposure increase and the −15% floor; validate evidence quality separately from output consistency.

## 2. Already covered by IDEA-015
- #1 = IDEA-013 R4 → IDEA-015 A.1. Addition: the assessment schema gets a `falsifier` field (the evidence that would break the thesis).
- #3 = IDEA-013 R3 → IDEA-015 A.2.
- #5 → IDEA-015 A.3 (voting is a stability diagnostic). Addition: separate checks that each cited span supports its claim and that the claim is factually correct, on labelled fixtures.

## 3. Accepted new findings
### 3.1 #2 Safety-action precedence — accepted
[V] IDEA-012 §8.1–8.2 lets HOLD_NO_CHANGE, ≤ 1 rebalance/session, the minimum order and R-VOTE apply to every order, so a risk reduction after a morning rebalance can be blocked. Rule [O, draft]:
- **Safety path:** drawdown-ladder actions, the end-of-run flatten, and trimming a breached hard cap (≤ 20%/name, ≤ 80% gross) bypass R-NEW/R-HOLD, R-VOTE, the per-session rebalance cap, the drift band and the minimum-order rule (a safety sell may be below the minimum or close a position entirely).
- Safety actions still pass every execution integrity check (IDEA-013 R1/R2: version, address, nonce reconciliation, recipient/min-out) and are logged as deterministic rounds (F-106 (a)).
- Safety actions only reduce risk; nothing on this path can buy.

### 3.2 #4 Drawdown control and concentration — accepted
[V] The submitted ladder (`proposal_answers.md`, "Drawdown control") is portfolio-level: daily loss ≥ 3% → no new positions for the UTC day; drawdown ≥ 8% → no new positions, exits continue; drawdown ≥ 12% → gross ≤ 40%. IDEA-012 §4.1 argued against **per-name** stops and then replaced this **portfolio** ladder with a single −15% floor, which fires later and has no entry halts: strictly weaker, and drawdown is part of the score (F-115). Recommendation [O]: **keep the declared ladder; drop the −15% floor proposal** (IDEA-012 §4.1, §8.2 H6). The exposure increase (IDEA-012 §4.3) is deferred to D-12 as a separate decision; the toy tournament simulation was never committed and its numbers should not be used for D-12 unless the script is committed and its assumptions stated. Q-39 (scoring weights) remains open.

### 3.3 #6 Measurements — accepted, one qualification
- [V] US regular hours are 6.5 h × 5 = 32.5 h of 168 h per week (19%); 81% of hours are outside them. IDEA-012 §1's 73–82% share of hourly variance outside regular hours is therefore roughly proportional to time and is not evidence of unusual off-hours activity. The "~75% of hourly variance off US hours" headline is withdrawn; per-hour variance is about the same on and off hours.
- Calling the negative autocorrelation "bounce" relies on Roll's model assumptions; treat it as consistent with bounce until executable quotes are logged.
- Qualification: the candle file is missing from other checkouts because `data/` is gitignored by design (F-61, reference by hash). Fix: record the file's sha256 in IDEA-012 and commit the calculation script (not done in IDEA-012).

### 3.4 #7 Costs and drift — accepted
- [V] Building and liquidating an 80% book at IDEA-012's own 30–85 bp round trip costs 0.8 × (0.30–0.85%) = **0.24–0.68% of equity**, before any rotation. IDEA-012 §4.4's "≈ 0.3% over the run" covered rotations only and did not say so.
- [V] A ±5 pp drift band on a 200 USDT wallet is a 10 USDT trade, below the 15–25 USDT gas-based minimum, so drift rebalancing almost never executes, and a position drifting past its 20% cap could not be trimmed. Rule [O, draft]: discretionary drift trades require band × equity ≥ minimum order (at 200 USDT: band ≥ 7.5–12.5 pp); hard-cap breaches are trimmed on the safety path (§3.1) regardless of size.

## 4. Open items
- Rewrite the IDEA-012 rules into one spec with: assessment schema (+ falsifier), map M, safety path (§3.1), declared ladder (§3.2), band/min-order rule (§3.4) (D-11). Owner: SYZ.
- Commit the IDEA-012 §1 calculation script and record the candle file's sha256. Owner: SYZ.
- D-12 (exposure, names) as a separate team decision; Q-39 unchanged.
