# IDEA-037 — Trading policy v1 candidate: equal weight, top-up rebalancing, buy-time caps with hard trim lines

- Date / author: 2026-10-11 / SYZ (decision); drafted and implemented with Claude
- Status: open (decided by SYZ 2026-10-11; pass criteria written before implementation; offline only)
- What: builds the decided B5 policy (80% invested, Option 1 equal weight at 20% per name, IDEA-035 §5 and §10.1) as a new strategy baseline `EQUAL_WEIGHT`, and decides and builds the rebalance rule and the cap semantics that the B5 decision left open.
- Why: with the 20% per-name and 80% gross targets equal to the hard caps, the current planner forces a sale on every small rally above 20% or 80%, and those forced sales skip the minimum trade size ([planner.py](../../larp/risk/planner.py) POSITION_CAP / GROSS_OR_REGIME_CAP; mandatory actions are exempt from `minimum_trade_units`). That is the "cap-trim micro-trade" problem in IDEA-017 and contradicts IDEA-035 §5's "the bot does not sell just because of that drift". Separately, the current baselines keep sale proceeds in cash, so the decided reinvestment does not exist in code (IDEA-035 §7 item 6).
- Cost / risk: about 80% invested in five correlated tech names (IDEA-035 §10.2: P(hit the 8% stop) ≈ 5.8% in the synthetic simulation). The hard lines let gross drift up to 90% (cash down to 10%) before a forced trim, which loosens the declared "cash ≥ 20%" (G-21) from a continuous limit to a buy-time limit: a deviation (GAP-62).
- Links: IDEA-035 B5, §5, §7 item 6, §10.1–10.3; IDEA-016 (band vs minimum order); IDEA-017 (cap-trim micro-trades, operating targets below hard caps); plan.md G-21, G-22, G-29, D-12; GAP-10, GAP-13, GAP-50, GAP-62, GAP-64.

## 1. Decision (SYZ, 2026-10-11)

The team member asked for the recommendation given in the session to be followed: "Fix A" plus the 75% top-up threshold.

| Rule | Value | Status |
|---|---|---|
| Stock mix | Equal weight, four names at 20%; drop any name with an unresolved red flag, then the most expensive to trade | Decided earlier (IDEA-035 §10.1); built here |
| Buy ceiling (new buys only) | 20% per name, 80% gross; ≤ 4 positions | Built here |
| Top-up (reinvestment) | Buy only while gross < **75%** of equity, and only into **unheld** eligible names (the freed slot), cheapest round trip first | Decided here |
| Drift | Never sell because prices moved a name above 20% or the book above 80% | Decided here |
| Hard trim lines | A name above **25%** of equity → forced sale back to 20%. Gross above **90%** → forced proportional sale back to 80% | Decided here (Fix A) |
| Deep drawdown | Unchanged: drawdown ≥ 12% → gross cut to ≤ 40% immediately, no hard-line delay | Unchanged (declared) |
| Daily loss / 8% drawdown | Unchanged: no new buys | Unchanged (declared) |
| End of run | Unchanged: flatten window, no reinvestment in it (IDEA-035 C4) | Unchanged |

## 2. Design

**Strategy (`larp/strategy/policy.py`, baseline `EQUAL_WEIGHT`).**
- Held names: always `KEEP_QUANTITY` (low turnover; reviews still scheduled every 5 sessions). Not resized on drift, and **not topped up after a fall**. Topping up a fallen name would be a dip-buying rule, which IDEA-035 §10.3 found unsupported for these names. Partial builds therefore stay partial: `per_trade_cap_units` must be at least one full position (20% of equity, ≈ 40 USDT at 200 USDT), so that each entry completes in one trade (GAP-13).
- Unheld names: an entry candidate at weight `operating_name_weight` (20%) only while current gross / equity < `top_up_below_gross_weight` (75%), with the same entry gates as today: entry window (`trade_after` ≤ now < `new_risk_end`), minimum remaining sessions, a fresh review for a previously held name, `assessment_required`, and the statement entry block. Candidates are ranked by `measured_roundtrip_bps`, then symbol, and allocated while slots (≤ 4) and gross budget (`min(operating_gross_weight, regime_gross_weight)`) remain. A red-flagged (blocked) name is never a candidate.
- No price-history features are needed: equal weight has no estimate, so `INSUFFICIENT_FEATURES` does not block `EQUAL_WEIGHT` entries. The market observation, its freshness and `basis_verified` are still required. `DECLARED_EXPOSURE` and `PRICE_MOMENTUM` are unchanged.
- `rebalance_band` is not used by `EQUAL_WEIGHT`.

**Risk planner (`larp/risk/planner.py`).** Two optional profile fields set the hard lines; when absent, behaviour is exactly as before:
- `hard_name_weight` (default 1/5): forced sale when a held name (plus pending buys) exceeds this share of safe equity; the trim target stays `operating_name_weight`.
- `hard_gross_weight` (default: none, meaning trim at the gross limit as today): forced proportional sale when gross exceeds this share; the trim target stays the gross limit (`min(4/5, regime_gross_weight)`). When `deep_cut` is set, the trigger is the 40% limit itself, as today.
- Buy capacity, the cash-after-buy ≥ 20% check, the position count and every other gate are unchanged.

**Profile validation (`larp/strategy/schema.py`).** `EQUAL_WEIGHT` is a known baseline and requires `top_up_below_gross_weight` with 0 < value ≤ `operating_gross_weight`. If present: 1/5 ≤ `hard_name_weight` ≤ 1/4 and ≥ `operating_name_weight`; 4/5 ≤ `hard_gross_weight` ≤ 9/10. Values outside these bounds are rejected. The profile is still accepted only in `OFFLINE_FIXTURE` mode; there is no live profile.

**Known consequences and limits.**
- A regime gross weight below 80% limits new buys only; it no longer forces sales below the 90% hard line. The regime governor is a static profile value today, so this changes nothing at runtime yet; a dynamic regime cut would need its own trim rule.
- The effective top-up trigger is 75% only if the minimum trade is ≤ 5% of equity (10 USDT at 200 USDT). A new entry is a full 20% (≈ 40 USDT), so entries are not affected (IDEA-016).
- Price-impact (B4), minimum trade (B6), per-trade cap and live dates remain open parameters (GAP-13/50/51). Values in tests are synthetic.
- The Class 2 expiring entry block (IDEA-035 §10.1) is separate work and is not built here.

## 3. Pass criteria (written and committed before implementation)

All on synthetic fixtures (`larp/research/fixtures.py`), with an `EQUAL_WEIGHT` profile: `operating_name_weight` 1/5, `operating_gross_weight` 4/5, `regime_gross_weight` 4/5, `top_up_below_gross_weight` 3/4, `hard_name_weight` 1/4, `hard_gross_weight` 9/10. Equity ≈ 200 USDT.

- **P01 Initial build.** Flat book, five eligible names with distinct `measured_roundtrip_bps`: `TARGET_WEIGHT` 1/5 for the four cheapest; the most expensive gets `KEEP_QUANTITY` `NO_PORTFOLIO_CAPACITY`; total target weight 4/5.
- **P02 Red flag excluded.** As P01, but one of the four cheapest is blocked by a verified falsifier: it gets no `TARGET_WEIGHT`, and the most expensive name takes the fourth slot.
- **P03 No buy at or above the threshold.** Three held names with gross ≥ 75% and one unheld eligible name: no `TARGET_WEIGHT` for it (reason `ABOVE_TOP_UP_THRESHOLD`).
- **P04 Reinvest after a sale.** Three held names at 20% (gross 60%) and one unheld eligible name: `TARGET_WEIGHT` 1/5 for it; the planner emits one non-mandatory BUY for that name whose spend is ≤ 20% of safe equity.
- **P05 No sell on drift, no dip top-up.** Held names at about 22% and 15% with gross < 75%: both `KEEP_QUANTITY`; the planner creates no requirement or intent for either.
- **P06 Hard per-name line.** A held name at about 26% of equity: a mandatory SELL requirement whose `max_units` keeps it at ≤ 20% of safe equity, reason `POSITION_CAP`. At about 24%: no requirement.
- **P07 Hard gross line.** Four held names at about 21.25% (gross ≈ 85%): no requirement. Four at about 23% (gross ≈ 92%): requirements whose `max_units` bring gross to ≤ 80% of safe equity, reason `GROSS_OR_REGIME_CAP`.
- **P08 Deep drawdown unchanged.** `deep_cut` set, gross ≈ 60%: requirements bring gross to ≤ 40%, reason `DEEP_DRAWDOWN`, despite `hard_gross_weight` 9/10.
- **P09 Gates retained.** Under `EQUAL_WEIGHT`: in the flatten window every held name gets `EXIT`; after `new_risk_end` no entry; a previously held name without a fresh review is not re-entered; with `run_halt` set the planner rejects the BUY (`NEW_RISK_HALTED`).
- **P10 No history needed.** A name with too short a price history is still an entry candidate under `EQUAL_WEIGHT`, and is still blocked (`INSUFFICIENT_FEATURES`) under `DECLARED_EXPOSURE`.
- **P11 Validation.** Rejected: `EQUAL_WEIGHT` without `top_up_below_gross_weight`, or with it above `operating_gross_weight`; `hard_name_weight` below 1/5, above 1/4 or below `operating_name_weight`; `hard_gross_weight` below 4/5 or above 9/10.
- **P12 Backward compatibility.** Profiles without the new fields behave exactly as before: every pre-existing test passes unmodified, including the stored strategy examples (`tests/research/fixtures/strategy-examples.json`).
- **P13 Full suite.** No new failures against the pre-change baseline on this machine at `ee4a9e5` (Python 3.14.6): 488 passed, 86 skipped (PostgreSQL / Linux-only), 1 failed (`tests/storage/test_archive.py::test_real_sdk_request_shape_is_supported`: `boto3` not installed locally; unrelated). Linux CI is the authoritative run.

## 4. Results

**V01 (local, `1a7aedd`, Python 3.14.6, synthetic fixtures only).**

| Criterion | Result |
|---|---|
| P01–P11 | PASS: `tests/strategy/test_equal_weight.py`, 11 tests |
| P12 | PASS: every pre-existing test passes unmodified (stored strategy examples included) |
| P13 | PASS: 499 passed, 86 skipped, 1 failed (the same `boto3`-missing archive test as the baseline); 754 subtests. `tests.test_contracts` OK |
| Linux CI (PostgreSQL / integration tests skipped locally) | PASS: run 38147033478 on `54534d2` (PR #7), 586 passed + 770 subtests, no skips; Terraform jobs pass. Against V16 (575 + 764), that is the 11 new tests and 6 new subtests |

**Mutation check.** Each behaviour was reverted in turn and the suite rerun. Every mutation was caught:
- no hard per-name line → P04–P07 fail;
- no hard gross line → P07 fails;
- free BNB not counted → P04 fails;
- deep cut delayed to the hard line → P08 fails;
- no top-up threshold → P03 fails;
- held names resized to 20% → P05 fails.

These are synthetic fixtures: they show the rules behave as specified, not that the policy is profitable.

- 2026-10-11 correction (SYZ/Claude): §2 said the cash-after-buy ≥ 20% check was unchanged. During implementation it proved incompatible with the 80% target. Gas BNB counts toward equity but not cash, so with any BNB in the wallet the fourth 20% buy was rejected (`CASH_OR_EXIT_RESERVE`) and the book stopped at 60%. Fix in `1a7aedd`: the floor counts free BNB (after this trade's gas) as uninvested, so it means "invested ≤ 80%", the declared "gross ≤ 80%, cash ≥ 20%" read as complements. The separate exit-gas reserve check is unchanged. This applies to every baseline and slightly loosens the old floor by the BNB value (≈ 0.5–1% of equity), still bounded by the gross buy capacity. P04 covers it.

## 5. Addendum 2026-10-11: top up held names (decided by SYZ)

**Decision.** When gross is below the 75% threshold, a **held** name below 20% is also bought back up to 20%. Before this addendum, only unheld names were bought. This supersedes the "not topped up after a fall" clause of §2 and the "no dip top-up" half of P05. Unchanged: no sale on drift, no resize of a name at or above 20%, the hard trim lines and every entry gate.

**Why, and the risk.** It completes partial builds and keeps the book near equal weight after a sale. It is a mild buy-the-dip rule, which IDEA-035 §10.3 found unsupported for these names. Two things limit it:
- the minimum trade size skips small gaps;
- price falls alone can push gross below 75% only after holdings fall ≥ 25%, i.e. a ≥ 20% drawdown, and by then the 8% stop already blocks new buys.

It mostly acts when a sale has left cash idle with no eligible fifth name. The team accepted this trade-off.

**Design.** Under `EQUAL_WEIGHT`, a held name gets `TARGET_WEIGHT` `operating_name_weight` (reason `TOP_UP_TO_EQUAL_WEIGHT`) when all of these hold:
- gross / equity < `top_up_below_gross_weight`;
- its value < `operating_name_weight` × (equity − `cost_reserve_units`). This is the same base the planner sizes against, so the planner never sees a dust SELL;
- the entry window is open, and `assessment_required` / statement-block gates pass. No previously-held check applies, since the name is held.

Otherwise the name gets `KEEP_QUANTITY`. The planner is unchanged: buy capacity (≤ 80%), the cash floor, the minimum trade, `NEW_RISK_HALTED` and the one-intent-per-round rule apply as before.

**Pass criteria (written before implementation).**
- **P14 Top-up held.** NVDAB ≈ 15%, GOOGLB and TSLAB 20%, MSFTB ≈ 17.5% (gross ≈ 72.5%): NVDAB and MSFTB get `TARGET_WEIGHT` 1/5 `TOP_UP_TO_EQUAL_WEIGHT`, while GOOGLB and TSLAB get `KEEP_QUANTITY`. The planner emits one non-mandatory BUY for NVDAB (gap ≈ 10 USDT).
- **P15 Small gaps skipped.** Same case: MSFTB's ≈ 5 USDT gap is below the fixture minimum trade and is rejected `MINIMUM_TRADE`.
- **P16 Not at or above the threshold.** NVDAB ≈ 15% with gross ≈ 77.5%: NVDAB `KEEP_QUANTITY`.
- **P17 Loss stop blocks top-ups.** The P14 case with `run_halt`: no intent, rejection `NEW_RISK_HALTED`.
- **P05 (revised).** NVDAB ≈ 22%, GOOGLB ≈ 15%, gross ≈ 37%: NVDAB `KEEP_QUANTITY` (no sale on drift); GOOGLB `TARGET_WEIGHT` 1/5; no requirement and no SELL intent for either.
- P01–P04 and P06–P13 must still pass. Full suite: no new failures against V01 (499 passed locally, 586 + 770 in Linux CI before the new tests).

**Addendum results: V02 (`148a994`, synthetic fixtures only).**

| Criterion | Result |
|---|---|
| P14–P17, P05 revised | PASS. P09 is extended with a held name outside the entry window |
| P01–P04, P06–P13 | PASS |
| Local full suite (Python 3.14.6) | 502 passed, 86 skipped, 1 failed (the same `boto3`-missing archive test) |
| Linux CI | PASS: run 38147628647 on `148a994` (PR #7), 589 passed + 770 subtests, no skips; Terraform jobs pass |

**Mutation check.** Each mutation was caught:
- no held top-up → P05, P14 and P17 fail;
- top-up ignores the 75% threshold → P16 fails;
- top-up ignores the entry gates → P09 fails;
- a held name resized even at or above 20% → P05 and P14 fail.

A first batch of mutations misreported because the M8 and M9 edits had the same file size and were written within the same second, so Python reused stale bytecode. Rerun individually, with a fresh write, each mutation was caught as listed.

## 6. R01 — Retain triggered trims across settlement (Isaac/Codex, 2026-10-11)

Review of PR #7 at `0ad5426` reproduced premature completion: a 92% gross book sells one child and stops near 89%; a 26% position with a 6 USDT child cap stops near 23%. Each round rechecks the hard trigger instead of retaining the obligation to reach the operating target. Existing P06/P07 check initial bounds only.

Design: persist active name/gross trim latches in the planner's `risk_state`, which Coordinator already commits and ContextBuilder restores. A breached hard line starts the latch; subsequent rounds re-evaluate reductions against current safe equity until the operating target is satisfied. Preserve a latch when valuation is incomplete; clear it on observed satisfaction, including a flat position. No policy proposal is required for continued reductions. Existing execution barriers remain binding; no live activation.

Prospective acceptance (before running changed decision code):
- `tests/strategy/test_trim_replanning.py`: real reservation/settlement reducer and serialized risk-state reload retain gross reductions below 90% through completion at 80%, and capped per-name reductions below 25% through completion at 20%.
- Untouched drift below hard lines creates no reductions. An integrity block or missing mark cannot erase an outstanding name trim.
- Existing strategy/risk tests and stored golden traces pass unchanged. Profiles without hard-line fields retain their historical output shape.
- Commit and push the decision code before running it. Latest Linux runtime/infrastructure CI passes. Tests use synthetic ports only; no credentials, network sources, wallet or audit uploads.

Verification: complete; see R01 V03 below.

R01 implementation refinement: the first pushed regression run (`61eb3d9`) passed 64 of 65 targeted tests. The gross completion case exposed a second issue: a boolean latch with newly calculated proportions generates an asymptotic micro-trade tail (23 child fills in the fixture before dust). Retain the original gross allocation shares across child fills, while sizing against current safe equity and the current gross limit. The completion control uses zero-cost quotes to isolate the obligation; an additional positive-cost fixture verifies that an unexecutable dust residual remains explicitly outstanding, rather than falsely completed. The existing dust/gas policy remains binding.

R01 second targeted run (`30ab128`): 65/66 passed; the new dust fixture assumed a two-unit residual was unexecutable under the default one-unit dust threshold. Correct the fixture to explicitly register a two-unit threshold. Code inspection also requires complete valuation before establishing gross allocation shares; partial valuation uses conservative provisional bounds without freezing incomplete allocations. Historical profiles without hard lines keep their original proportional replanning behaviour and output shape.

R01 local acceptance on `78aba50` (Python 3.12.14, secret-free): 97 tests ran, **92 passed, 5 PostgreSQL-dependent skips** across strategy, risk, research, intelligence golden, integration contract and shared contract suites. All pre-existing assertions pass unchanged. Add a final regression for partial valuation: defer gross allocation shares until all marks recover, then establish equal 1/4 shares from the complete four-name book. Full PostgreSQL/isolation acceptance is delegated to Linux CI.

**R01 V03 (2026-10-11, `b2ec500`, decision code `78aba50`).** All six new regressions pass. Local secret-free Python 3.12.14: **93 passed, 5 PostgreSQL-dependent skips** (98 tests run); existing strategy/risk/research/shared contracts and intelligence golden checks pass unchanged. [Linux CI run 38150888280](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38150888280): **595 passed, 770 subtests passed, no skips**; runtime offline demo, Docker build/smoke, AWS Terraform (3 tests) and bootstrap Terraform (1 test) all pass. `git diff --check 0ad5426..HEAD` passes. Implementation and tests were committed/pushed before each changed-code run.

R01 is fixed and verified offline: gross allocation shares and active name trims are durable risk state, obligations survive settlement/reload and execution barriers, and observed satisfaction clears them. Tiny residuals below configured dust limits stay explicitly outstanding; this fix does not make such quantities executable. No golden/fixture files, policy defaults, live activation, credentials or execution adapters changed. Broader live-policy and execution work remains in GAP-64/65 with the existing owners.
