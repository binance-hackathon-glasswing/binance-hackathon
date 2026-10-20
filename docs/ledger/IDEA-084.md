# IDEA-084 — Profit-focused v1 decisions — PF-01

- Date: 2026-10-21 SGT. Base: canonical `31bd06d`.
- Authority: Isaac explicitly delegated the remaining team decisions, preferring
  a greater chance of profit even with higher risk, and requested PR133 documentation.
- Status: **decided for implementation and qualification**. No runtime/config,
  signed release, host, wallet, model call or readiness flag changes here.
- These are delegated policy choices, not attributed Keith/Keegan/Yao signoffs.
  PR133 remains noticeboard-only; the authoritative record uses a separate PR.

## PF-00 — Objective and evidence

Prioritize the probability that final eligible-wallet equity exceeds documented
opening equity after actual wallet execution costs; expected net profit is the
secondary objective. Report model/hosting costs separately; never double-count
settled fees/gas. More variance, turnover or model spend is not itself a benefit.

There is no calibrated distribution or held-out result proving an optimum for
this14-day window. The choices accept market/concentration/coverage risk while
preferring the existing S1 design and avoiding unnecessary turnover or unreliable
execution. They are not a claim that95% exposure has a higher probability of
profit than every lower-exposure policy. No development/scored PnL is used to
tune these settings.

Checked IDEA075, frozen EXP007, IDEA049-B B-DEC01–08/WR38, C05-RV01, backlog,
PR133, PR204/206 audit/repairs, PR205/207 and the completed quote-capture receipt.
The trial's two assessed filing records establish no economic uplift; DC01's
3,848 swap gas figures remain FALLBACK. No return forecast is invented.

External primary sources checked Oct21 SGT: SEC Investor.gov
[allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation)
explains willingness to bear loss for potential return and limited diversification
from narrow-sector holdings; its
[fees page](https://www.investor.gov/introduction-investing/getting-started/understanding-fees)
describes transaction/ongoing costs. These support risk/cost discipline, not a
14-day profit forecast. Five eligible technology names remain a correlated basket.

## PF-01 — S1 parameters and O2

Choose **TREND_GUARDED_VOL / S1**, up to **95% gross**, with the existing independent
cost, gas, eligibility and safety gates. Adopt these previously proposed values
as the implementation target, without claiming statistical optimality:

| Setting | Decision |
|---|---|
| Trend / verified-evidence levels | 95% /60% /30%; target is min(trend, deterministic limiter, risk cap) |
| Trend | Five sessions, ±1% hysteresis; session-close+15min evaluation |
| Weights | Inverse token-session volatility over60 sessions, minimum20, through Oct21 close; existing median-of-qualified-names rule for a missing name; freeze exact weights/data hashes once |
| Weight cap / hard name line | Weight≤0.30 (target≤28.5% equity at95% gross); hard line35%, trim to target |
| Turnover | No drift sales; replenish below target−5 percentage points; required sells before buys; sequential execution, no trade-count quota |
| Execution | Regular-session open+30min to close−15min for discretionary legs; at most3 attempts/name/leg/session; existing mandatory windows and all integrity/quote checks |
| Loss ladder | Keep3% daily buy stop,8% drawdown buy stop,12% deep cut to40%; only PF02 changes recovery |

Honor EXP007's frozen three-outcome rule: SUPPORTED/INCONCLUSIVE retains the
declared guard; NOT_SUPPORTED fixes trend at95%, retaining limiter/ladder.
The real experiment remains NOT_RUN. No retrospective cutoff/threshold change.
Prefer qualified S1; preserve SP-D2's measured EQUAL_WEIGHT rehearsal fallback
if S1 inputs/wiring fail qualification. That fallback is not five-name95% S1.

## PF-02 — O1 recovery

After the8% buy stop, clear that block only when complete, fresh, reconciled
valuation shows drawdown **strictly below5%** from the persisted run peak.
At5% it stays blocked; never lower the peak to manufacture recovery. This does
not clear a12% deep cut, daily stop, adverse-event latch, HALT, quarantine or
pending nonce. Accept possible repeated drawdowns to participate in a recovery.
Keith implements and tests threshold/restart/replay behavior; current no-reset
code is not silently changed by this document.

## PF-03 — O3 / #39 universe

Keep all five names including SKHYB, subject to fresh basis/metadata/quote/cost/
liquidity/gas checks. Do not force an expensive entry or automatically redistribute
a blocked name's weight. **Accept SKHYB's asymmetric foreign-filer adverse-event
coverage** and common technology exposure. Never invent domestic8-K authority
from6-K text or promote SHADOW statements. This is opportunity/coverage-risk
acceptance, not a forecast of outperformance or broad diversification. Yao/Keith
record the deviation and verify manifested scope/tests before closing #39.

## PF-04 — O4/O5 / #107 calendar

Adopt one final calendar, **all UTC**:

| Gate | Target |
|---|---|
| First final buy eligibility | Oct29 14:00 |
| New risk ends | Nov9 21:00 |
| Flatten starts | Nov10 19:00 |
| Signing ends | Nov11 14:45 |
| Flat-by target | Nov11 15:00 |

Choose the later S1 Nov9 cutoff to preserve recovery-buy opportunities. Keep
Nov11's flat-by target; do not extend to Nov12 on an unconfirmed end instant.
Extra time exposed does not automatically improve profit probability. Accept
terminal opportunity loss to limit failure-to-flatten/valuation uncertainty.
Keegan/Keith reconcile current generator midnight gates, S1 windows, calendar
and DR14 tests; they are not already equal. Scheduled events alone still cause
no cut (decided DEV20 omission). Keep SP-D1 rehearsal windows; a missed window
requires a reviewed development-window/version change, not backdating.

## PF-05 — B-DEC02/03 / #38 / #55 valuation and concentration

Use fresh token-mark NAV for ordinary risk/weight triggers; report executable
liquidation NAV and complete costs separately when attributable quotes exist.
Do not turn liquidation spreads into a new underlying price crash or charge
settled fees twice. Rank eligible discretionary entries by **current intended
size's all-in round-trip cost**, not an old static sample; missing cost is not0.

Block buys under incomplete valuation. Suppress discretionary healthy-name
cap trims caused solely by another missing mark being counted as0. Use a last
usable mark only within its existing approved freshness bound; after expiry
retain unknown valuation, not an extended timestamp. Preserve independent
Class1/terminal/deep-cut requirements and trims proven by complete valid marks;
incomplete data cannot clear risk latches or peaks. Accept temporary concentration
uncertainty rather than unnecessary sales. Keith implements/tests #55's stale-
name/near-cap case. Preserve the already-decided bounded price-jump hold.

Accept correlated-basket/staggered-entry risk without demonstrated alpha. Prefer
S1's bounded same-session sequential opening over adding a new four-session
build constraint. Economic reports keep their original unsupported/inconclusive
verdicts; this written risk acceptance is not a result upgrade.
Choose no additional unbuilt regime/covariance governor beyond S1's trend,
limiter and declared ladder for v1 (B-DEC04); record that omission. This does
not remove existing hard constraints or assert a stress detector was built.

## PF-06 — B-DEC06/08 / #44 / #56 costs, gas and execution

Retain measured entry-cost/impact gates and finite slippage≤50bp; do not widen
slippage automatically on retry. Required safety sales retain existing minimum/
profit/cadence bypasses, never quote/payload/fee/nonce bypasses. Reserve all
actual required exit children, including appreciated/capped positions and
selected cleanup; five nominal pairs alone are not full-exit proof.

Choose full bounded-action gas reservation, not an optimistic quote alone:
attributable qualified step estimate/observed bound with20% gas-limit headroom,
multiplied by the selected gas-price cap and rounded up. Include approve/swap,
all selected zero-approval steps and bounded retries. FALLBACK gas is ineligible.
Whole-run seeding covers reviewed non-terminal actions/margin plus the complete
exit reserve. If it cannot fit fee/cash/BNB/equity caps, reduce feasible activity
or refuse the candidate. Keith supplies measurements; Isaac approves exact
derived profile/policy/input hashes. **No raw gas limit, gas-price cap, #44 value
or seeding amount is numerically approved without those inputs.**
The20% limit headroom is a team engineering choice following the kit demo's
estimate multiplier, not a proven coverage level or organizer requirement.

Choose LD06 bounded zero-only allowance recovery for the preferred candidate
after gas/timing review, with both independent opt-ins, original authority,
per-token attempt bounds and aggregate fees. Retain initial-gas-only scope,
API-trusted pinned router, exact approvals, L=660s/m=30s and PR205's reviewed
policy SHA256 `05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5`.
Signer/approve timing and live preflight still need qualification.

Select BSC_BNBCHAIN_PUBLIC then BSC_NODEREAL_PUBLIC for ordinary chain56 execution
**read-side qualification**, expanding the previous balance-only policy scope.
Exact endpoints and nonce/finality/code/storage/allowance/failover capability
must pass before activation. No URLs are published, RPC send path enabled,
native tracing claimed, signer internet route added or probe run here.

## PF-07 — O6 / LD11 model

Choose the **OpenAI-primary LLM assessor** direction with independently verified
external review and the **deterministic reduce-only exposure limiter**; no extra
model call solely for exposure. Prefer PR206's detached-input/usage/reporting
repairs and pinned review prompt. Select its v4 stage-cap direction for
qualification:4096 primary/routine and16000 external-review tokens, retaining
existing model/effort choices. These are ceilings, not spending targets.

Accept **unproven economic uplift** after operational/veracity/rights/budget/audit
qualification. Record43.56h versus the frozen72h criterion and the two-filing
population as explicit adoption shortfalls; never call them a pass, fabricate
labels or restart the retired trial under expired authorization. Private replay
and independent labels remain owed reports; unchanged frozen metrics remain.

Keep maximum-cost reservation, rejected/late usage and UNKNOWN charges. Set
exact live day/run budgets from verified remaining private credits/prices and
worst-case stage/cadence cost; do not reuse an expired trial budget. Prefer fewer
optional/redundant calls over removing verification if affordability fails.
Keith/Yao supply facts; Keegan records exact config/prompt/budget/release adoption.
No paid call, account purchase, ledger reset or installation occurs here.

## PF-08 — LD14 operations

Keep no standby, current automatic same-build supervision and restored-run
quarantine. Prefer the existing host footprint, without speculative resizing.
Choose the earliest delivery-age bound covering the observed worst normal
positive-ACK tail plus one bounded complete-cycle/drain allowance; preserve the
independent hard upload deadline. Choose the smallest watchdog/memory bounds
passing worst-path/stalled-call/simultaneous-peak tests with documented headroom,
including the selected token ceilings. Do not restart healthy bounded work
merely to shorten a timer.

Exact B/watchdog/memory values are **MISSING_MEASUREMENT**, not an open preference
or adoption of historical2h/600s examples. Yao/operator supplies the packet;
Isaac freezes tested numbers with Keith/Keegan analysis. A measured capacity
failure needs scoped-work reduction or separate cost/resize review before install.

## PF-09 — LD05 and qualification

Choose accurate anomalous outcome/gas/incident accounting plus **sustained
quarantine** for unresolved abnormal fills; no late automatic trading-resume
path. Continuing from uncertain ownership has no demonstrated profit edge.
Bounded allowance cleanup cannot recover a bad fill or authorize unknown assets.
Keith implements/tests LD05 and Keegan reviews.

Keep D-DN02's conditional shorter-rehearsal disposition if signed gates miss
Oct21; record actual intervals/deviation without manufacturing duration. Retain
exact signed release, protected signer session, identity/nonce/audit, gas/policy
acceptance and real approve/swap/ACK/recovery evidence. Risk delegation is not
technical proof or independent owner signoff. Keegan finalizes declarations and
go/no-go; this record chooses scope, not activation.

## Prospective document checks

Before checks: PFV1 every O1–O6/category has a disposition or named missing
factual input; PFV2 frozen experiment/history preserved and policy not mislabeled
implemented/tested; PFV3 no app/config/test/release/official/vendor bytes change;
PFV4 local links/IDs/whitespace pass; PFV5 push and link this record in PR133
without replacing concurrent work. No runtime experiment is part of this change.

Rules checked: verbatim source-page rules/scoring/trace; kit trading-guide flow,
quotes/gas; SKILL §0.2/0.3, F95/F105/F114/F117/F119–124 and Q06/Q39/Q40 including
settled notes. Choices above are team policy, not new organizer rules/answers.
