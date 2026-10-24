# Current strategy baseline — source findings and boundaries

PR276-RV01; checked 2026-10-24 SGT against canonical `59c878c0`. Status: reviewed research, no behaviour change.
The [report](../report.md) and [IDEA-091](../../../ledger/IDEA-091.md) distinguish findings from decisions.

## Runtime findings

- [service.py](../../../../larp/runtime/service.py) constructs `ContextBuilder` without `series`;
  [integration/runtime.py](../../../../larp/integration/runtime.py) defaults it to an empty mapping.
  [s1.evaluate_trend](../../../../larp/strategy/s1.py) preserves a valid previous state, otherwise its configured start,
  on missing data. UP initialization plus missing series gives UP without a new trend observation. Persisted DOWN
  would remain DOWN. This path does not prove 95% actual holdings or successful execution.
- [exposure.py](../../../../larp/integration/exposure.py) produces Class 2 red-flag evidence; restriction, suspension
  and scheduled-event evidence are unsupported. This producer cannot newly supply the SEVERE path's inputs.
  It does not establish that all prior state is NORMAL or make every risk control inert.
- [accounting.py](../../../../larp/risk/accounting.py) latches the 8% drawdown buy halt with `|=`. PF-02's reset below
  5%, with fresh complete reconciled valuation and without clearing other latches, is not implemented here.
- [policy.py](../../../../larp/strategy/policy.py) checks target-value gaps against `minimum_trade_units`. At fully
  built five-name equal weights, 200 USDT equity and no reserve/drift, a 95% to 60% cut is 14 USDT per name.
  The [selected S1 rehearsal candidate](../../../build/evidence/s1-rehearsal-profile-20261023/README.md) uses
  18.637420 USDT. The cut would require weight at least `18.637420 / (0.35 × 200) ≈ 0.266249` under these assumptions.
  Actual weight, equity, reserve, holdings and other controls change the conclusion.
- [planner.py](../../../../larp/risk/planner.py) uses S1's high level for its ordinary gross limit and has no ordinary
  S1 gross-trim line; deep cut lowers the gross limit to 40%. Hard-name and mandatory exit paths remain separate.
  “The deep cut is the only loss control that acts” would incorrectly omit those controls.

## Profiles and policy

[IDEA-084](../../../ledger/IDEA-084.md) PF-01 chooses S1 with high/mid/low targets 95/60/30%, frozen inverse-volatility
weights and a 30% weight cap, with a separate 35% hard-name line. These are team choices. Rehearsal equal fifths are
not evidence that final inverse-volatility inputs are already frozen. EXP-007's frozen criteria remain authoritative:
SUPPORTED/INCONCLUSIVE retain the guard; NOT_SUPPORTED fixes exposure as specified. Missing series, exploratory
EXP-008 diagnostics or a very wide band do not produce that registered experiment's outcome.

EQUAL_WEIGHT is a different fallback: four 20% names, 80% target, cheapest recorded round-trip rank, 75% gross buy
trigger and one discretionary swap per session. The [WR-38 fixtures](../../../../tests/strategy/test_wr38_conventions.py)
pin a fresh four-name build taking four distinct sessions under their conditions. S1 can admit multiple legs in a
session, but actual completion is conditional on all gates and attempts; it is not guaranteed to build in one session.

S2 is a dev-rehearsal execution test. [execution_bounds.py](../../../../larp/strategy/execution_bounds.py) permits its
`KIT_OPEN_STATE` mode only with REHEARSAL, SHADOW evidence/falsifiers and dev scope. Five attempts there do not change
PF-01's three, and neither the rehearsal profile nor its quote validation is a FINAL release acceptance.

[profiles.py](../../../../larp/strategy/profiles.py)'s FINAL generator windows still differ from PF-04. PF-04's UTC
calendar is first buy Oct 29 14:00; new-risk end Nov 9 21:00; flatten Nov 10 19:00; signing end Nov 11 14:45; flat by
Nov 11 15:00. These are team POLICY. There is no profit forecast for repairing the mismatch. New York session
conversion must use the frozen calendar across the Nov 1 DST change, not a fixed UTC offset.

## Required decisions and ownership

Keith owns PF-IMPL01 source/input/feasibility work; Keegan reviews bindings; Yao supplies sources and selects the
next strategy; Isaac accepts exact profile, signer, gas and caps. See [INCOMPLETE_WORK](../../../INCOMPLETE_WORK.md).
Any adopted alternative needs a decision ID, prospective criteria, parameter-cut exception if applicable, a new hash,
coverage review, run pins and release qualification. A documentation merge supplies none of those approvals.

Rules checked: [official page](../../../official/source_page.md), [trading guide](../../../official/kit/bstocks-trading-guide.md),
[kit reference](../../../skill/reference/participant-kit.md) and [SKILL](../../../skill/SKILL.md) F/K/Q items. F-117's
build freeze, F-119's hours clarification, retained `openState`, F-120's settled first-gas process and unresolved
Q-39 scoring/BNB valuation must not be replaced by the original note's strategic assumptions.

## Provenance and original source leads

The [original research text](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/5d5b5e284fd0e70586ba83767a2d22b0fd726d1e/docs/research/strategy-alternatives-20261024/notes/current_strategy_baseline.md) is retained immutably.
PR276-RV01 replaces unsupported conclusions and repairs local references. The register preserves the original
external URLs for follow-up; inclusion does not verify availability, quality, rights or any claimed result. Only
sources explicitly assessed above have been rechecked; all other entries remain unverified leads.
