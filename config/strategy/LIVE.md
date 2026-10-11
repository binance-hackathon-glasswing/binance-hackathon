# LIVE configuration — IDEA-040

Actual rehearsal/final profile files await Isaac's measured cost summary and
Yao Zhu's pinned predicate registry. No synthetic profile is shipped as LIVE.
`build_live_profiles(summary, registry)` returns both canonical Documents; write
their `.payload` bytes to separate files outside Git if captures are private,
review/freeze their hashes in the manifest, and run `schema.profile(snapshot)`
in release preflight. The LIVE label grants no signing permission.

The proposed consumer inputs are documented in `larp/strategy/profiles.py`,
`sessions.py`, `predicates.py`, and `larp/risk/accounting.py`. Producer agreement
and real captures remain I1/I2/I4/I8 integration gates. Tests are synthetic.

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
| Rehearsal (~100 USDT) | Oct 21 00:00 UTC | Oct 24 00:00 UTC | Oct 25 00:00 UTC | Oct 26 15:00 UTC |
| Final (~200 USDT) | Oct 29 00:00 UTC | Nov 9 00:00 UTC | Nov 10 00:00 UTC | Nov 11 15:00 UTC |

Signing end implements the decided IDEA-035 C4 deadline. Earlier cut/flatten
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

Runtime PR #13 now publishes `purpose: GAS_TOPUP` for its narrow BNB exception;
the resource intent/reservation retains that purpose as well as kind GAS_TOP_UP.
Its I4 receipt evidence is flat `tx_hash`, `block_hash`, `canonical: true`, plus
`settlement: FINAL`. Accounting consumes that form and validates an optional
detailed `receipt` if supplied. Keegan must preserve those fields and round_id
when calling accounting, and copy round_id/resource purpose into the committed
reservation view. PR #13 currently strips those fields; real-reconciler settlement
will deliberately reject until that integration change is made.

For gas rounds the live health port must explicitly provide
`new_spending_ok: true` after checking degraded/reconciliation/spending gates;
absence blocks resource spending. Gas quotes declare `receive_decimals` equal
to the portfolio's BNB decimals. These additions need Isaac/Keegan agreement.

One GAS_TOP_UP intent per dedicated resource round: BUY BNB, amount = exact USDT
input. Runtime/signer/audit must explicitly opt into this kind; a generic BNB
stock order is invalid. BNB is excluded from stock slots and turnover, included
in wallet equity, and reported separately in economic views. No top-up after
the new-risk cut or during flattening, loss/deep-cut/degraded spending blocks,
pending wallet intents, integrity or ownership failures.
