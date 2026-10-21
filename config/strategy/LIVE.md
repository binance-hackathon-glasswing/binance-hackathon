# LIVE configuration — IDEA-040

Actual rehearsal/final profile files await Isaac's measured cost summary and
the published RedFlagPredicateSet.v1 and its pinned set hash. No synthetic profile is shipped as LIVE.
`build_live_profiles(summary, registry)` returns both canonical Documents; write
their `.payload` bytes to separate files outside Git if captures are private,
review/freeze their hashes in the manifest, and run `schema.profile(snapshot)`
in release preflight. The LIVE label grants no signing permission.

The versioned consumer inputs are documented in `larp/strategy/profiles.py`,
`sessions.py`, `predicates.py`, and `larp/risk/accounting.py`. Producer agreement
and real captures remain I1/I2/I4/I8 integration gates. Tests are synthetic.

S1 profiles additionally need explicit `s1.execution` delay, close-buffer and
per-leg attempt values (IDEA-076 EB-01, Isaac B6). Construction, session/attempt
semantics and the still-proposed example values are in
[`S1_EXECUTION_BOUNDS.md`](../../docs/build/S1_EXECUTION_BOUNDS.md).

## B6 algebra (no P&L input)

All money is USDT micro-units; BNB/token quantities retain explicit decimals.
For each symbol let `g` be measured approve+swap gas valued in USDT, `s` measured
spread bp excluding impact, `i` median impact bp, `f` fee bp. The conservative
entry impact limit is `min(50, 2*i)`; remaining gas budget is
`b = 50 - s - min(50, 2*i) - f`. Require `b > 0` and minimum size
`ceil(10000*g/b)`. Profile minimum is the largest across all five names;
reject generation if it exceeds a 20% position on either wallet. Quotes use the
actual executable cash/token difference plus fees and gas, which already
includes spread and impact; impact is not added to this difference again.

Let `G` be the largest measured approve+swap BNB gas. Exit reserve = `4*G`;
gas trigger floor = `6*G` (four exits, one top-up, next entry). Top-up min receive
= `12*G`; USDT spend = its marked value divided by `0.995`, rounded up (50 bp
execution allowance). Top-up max gas = `G`. A zero-BNB wallet is still blocked.
The proposed trigger is conservative resource policy, not an organiser rule.
An affordable mandatory sale is planned before replenishment; the gas budget of
another token cannot preempt it.

Per-trade cap = `equity/5 + cost_reserve`, completing a full 20% position.
Cost reserve = 50 bp of that full position. Slippage cap = min(50, largest
measured slippage); quote age = min(30 seconds, shortest measured RFQ TTL);
proposal lifetime = min(15 seconds, quote age). Feature age = four calendar days
to cover a normal weekend (gaps in the supplied session calendar remain missing).
Minimum remaining sessions = 0 under EQUAL_WEIGHT (no predictive holding horizon);
review horizon = five sessions; optional momentum threshold = 0 and unused.
Dust = 0 token units: no unknown venue minimum is invented. Failed execution
remains a visible unresolved requirement, not a completed/dust flatten.

## Windows and release evidence

| Environment | Start | New risk ends | Flatten starts | Signing ends |
|---|---|---|---|---|
| Rehearsal (~100 USDT) | Oct 21 00:00 UTC | Oct 22 00:00 UTC | Oct 23 00:00 UTC | Oct 26 14:45 UTC |
| Final (~200 USDT) | Oct 29 00:00 UTC | Nov 9 00:00 UTC | Nov 10 00:00 UTC | Nov 11 14:45 UTC |

The candidate signing cut leaves 15 minutes before the IDEA-035 C4 completion deadline;
this is a provisional engineering margin to freeze/rehearse, not a guarantee of finality. Earlier cut/flatten
offsets are conservative IDEA-040 candidate choices for owner/team review;
source data, values and profile hashes must be frozen by Oct 22. These dates
do not prove every sale will execute. Clock/market/gas failures preserve
outstanding terminal requirements. Rehearsal order-size mode and five-day
minimum-size evidence belong to Keegan's runtime/DR-21; a profile does not prove it.

`schema.profile` rejects missing/unsourced values and invalid/future measurements;
`schema.market_view` rejects fake LIVE markets; quote validators reject fake LIVE
quotes. Keegan must set `PortfolioState.v1.mode=LIVE`, preserve `round_id` on each
reservation, and attach final receipt facts to prevent fake settlement. The
execution owner supplies chain proof: canonical/finality flags alone are trusted
producer assertions, not independent RPC verification.

I3 uses `kind: GAS_TOP_UP` for the narrow BNB exception; the obsolete `purpose`
field is refused. I4 retains `round_id`, `tx_hash`, `block_hash`, `canonical`,
`settlement: FINAL`, and optional detailed receipt evidence through accounting.
The committed reservation carries its round and resource kind. Actual runtime
mode controls receipt provenance; fake receipts require an explicitly offline ledger.
The integrated execution service/receipt/settlement/audit/replay regression is
`tests/integration/test_service_system.py` (synthetic transports only).

Published I8 directives are enabled only by the profile's exact set hash and IDs.
Class 1 creates an independent mandatory sell requirement, including when policy
is unavailable; Class 2 blocks retain their five-session clock through a Class 1
latch and clear. Legacy offline fixture registries are compatibility inputs.

For stock purchases and gas rounds the live health port must explicitly provide
`new_spending_ok: true` after checking degraded/reconciliation/spending gates;
absence blocks new spending in LIVE. Mandatory stock reductions retain their
independent risk path. Gas quotes declare `receive_decimals` equal
to the portfolio's BNB decimals. These additions need Isaac/Keegan agreement.

One GAS_TOP_UP intent per dedicated resource round: BUY BNB, amount = exact USDT
input. Runtime/signer/audit must explicitly opt into this kind; a generic BNB
stock order is invalid. BNB is excluded from stock slots and turnover, included
in wallet equity, and reported separately in economic views. No top-up after
the new-risk cut or during flattening, loss/deep-cut/degraded spending blocks,
pending wallet intents, integrity or ownership failures.

## Initial-only candidates after LD07 (2026-10-20)

Use `python -m larp.strategy.profiles ... --initial-gas-only` for the decided v1
gas scope. It emits explicit `initial_gas_only: true` with LD07 provenance and
no top-up sizing fields. Existing full-exit reserve and provenance checks stay
mandatory; the builder does not establish measured gas or owner acceptance.
LD08-IG01 also requires positive, sourced `gas_action_budget_units`. The builder
sets it to the largest summary approve+swap pair. Selected cleanup requires a
reviewed larger budget where needed: the reserve must cover four such actions
(five for S1), and minimum-trade cost feasibility uses that whole action budget.
This is a candidate formula; FALLBACK measurements do not qualify its value.
LD09-B (IDEA-061, decided 2026-10-21) adds an optional sourced
`gas_sizing_budget_units` for initial-only profiles: the action budget is set at
the signer's cap gas price and keeps the reserve and `InitialGasCheck`; the
sizing budget (expected gas price, between the summary pair and the action
budget) sets minimum-trade feasibility. Builder: `--gas-action-budget-units`,
`--gas-sizing-budget-units`, `--gas-budget-decision`, `--gas-budget-evidence`.

At a quiet boundary after balance reconciliation, `InitialGasCheck` journals
transitions to `BELOW_EXIT_RESERVE`, `PAIR_UNAFFORDABLE`, or recovered `OK` in
`projection.gas_health`. Exact equality with the action budget remains affordable.
The monitor preserves unsettled reservations and waits for open rounds/commands;
it neither HALTs nor changes financial state. Existing planner/executor checks
still decide each actual action. `GasPairUnaffordable` has a dedicated CloudWatch
alarm; actual installation and notification delivery remain operator acceptance.
`tools/deploy/propose_signer_caps.py --initial-gas-only ...` excludes native BNB
from the independent signer token policy while retaining unapproved example caps.
Legacy CLI calls/fixtures remain available for historical top-up work and do not
select v1 scope. Both candidates and any changed profile require fresh review
and release binding; nothing is installed by construction.

Remaining measurement/decision/release/host gates and owners:
[OG-01](../../docs/build/POST_REVIEW_GATES_20261020.md).
Detailed [LD08 acceptance matrix](../../docs/build/INITIAL_GAS_ONLY.md).
