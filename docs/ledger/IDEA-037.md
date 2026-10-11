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
| Linux CI (PostgreSQL / integration tests skipped locally) | Pending: runs on PR #7 after the push |

**Mutation check.** Each behaviour was reverted in turn and the suite rerun. Every mutation was caught:
- no hard per-name line → P04–P07 fail;
- no hard gross line → P07 fails;
- free BNB not counted → P04 fails;
- deep cut delayed to the hard line → P08 fails;
- no top-up threshold → P03 fails;
- held names resized to 20% → P05 fails.

These are synthetic fixtures: they show the rules behave as specified, not that the policy is profitable.

- 2026-10-11 correction (SYZ/Claude): §2 said the cash-after-buy ≥ 20% check was unchanged. During implementation it proved incompatible with the 80% target. Gas BNB counts toward equity but not cash, so with any BNB in the wallet the fourth 20% buy was rejected (`CASH_OR_EXIT_RESERVE`) and the book stopped at 60%. Fix in `1a7aedd`: the floor counts free BNB (after this trade's gas) as uninvested, so it means "invested ≤ 80%", the declared "gross ≤ 80%, cash ≥ 20%" read as complements. The separate exit-gas reserve check is unchanged. This applies to every baseline and slightly loosens the old floor by the BNB value (≈ 0.5–1% of equity), still bounded by the gross buy capacity. P04 covers it.
