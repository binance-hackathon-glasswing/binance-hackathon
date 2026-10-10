# Strategy/risk/research increment — IDEA-026

Branch `codex/strategy-risk-research`, kickoff `e10eae2`. Offline only; no live
adapter, wallet key, signer or ai-seeds client. This is a candidate development
policy and portfolio arithmetic, not evidence of profitable trading or activation.

After committing/pushing decision code and its criteria, reproduce from repo root:

```sh
/Users/keith/anaconda3/envs/binance-hackathon/bin/python -m unittest discover -s tests -v
/Users/keith/anaconda3/envs/binance-hackathon/bin/python -m larp.research.demo
```

The first command preserves the original 13 foundation checks and adds owner-local
checks. NumPy is already pinned and used only by existing Monte Carlo regression
checks, never the strategy/planner. No dependency/lock changes are requested.
Private captures are not needed. Demo output is entirely synthetic; it includes a
baseline intent, a costly allocation rejected, a blocked mandatory exit retained,
and exact downstream replay hashes. Fixture timestamps, prices, costs and limits
are explicitly synthetic and differ from the final scored configuration.

## Integration contracts

Existing `larp.contracts` is unchanged. All added payloads use canonical `Document`.
The proposed detailed schemas here need reconciliation with Keegan's `larp/ports.py`
and Isaac/Yao Zhu adapters; they are owner-local v1 integration proposals.

- `decide(snapshot, state) -> Proposal` in `policy.py`: explicit state, quantities
  kept by default, five-session reassessment and no automatic round trips. Initial
  entry is labelled an unvalidated exposure baseline. Optional price momentum is
  transparent/frozen; it has no calibration or alpha claim. Re-entry after actual
  holdings needs a fresh context-matched review. Evidence starts SHADOW; the
  explicitly configured bounded variant blocks a name for the run after supported
  allowlisted findings. No live adoption is selected. `assessments.py` consumes
  PR #4's issuer IDs, UTC epoch-millisecond timestamps, `status`, verified `claims`
  and `falsifiers[].falsifier_id/state/fact_ids`. Legacy ISO/symbol payloads receive
  `ASSESSMENT_SCHEMA_UNRECOGNISED`, rather than disappearing from the trace.
- `plan(snapshot, proposal_or_none) -> PlanResult.v1` in `larp/risk/planner.py`:
  requirements, risk latch state, clamps/rejections, exact-size quote requests,
  one immediate child economic intent, reservation delta requests and proposed
  policy state. Keegan must atomically commit them with expected snapshot/state
  version. This output never authorizes signing. Isaac must revalidate route,
  market, risk, epoch and expiry at the side-effect boundary. Policy failure does
  not prevent mandatory constraints from being computed from a valid snapshot.
- `advance_accounting(PortfolioState.v1, ExecutionObservation.v1)`: settled actual
  fills, fees, approvals and reverts, average-cost basis and immutable observation
  IDs. Approvals/reverts only consume actual observed gas. Full-or-revert swaps
  settle one child's exact INPUT; buy output quantity and sell proceeds vary.
  Buys must spend the committed USDT input, receive at least the committed minimum
  and stay within the fee/cash reserve. Actual received quantity and actual cash
  enter holdings/cost basis; even a favorable surplus must be recorded and replanned.
  Sells consume the committed token input and respect minimum cash received.
  Portfolio plans can remain partly completed. A service-cost
  observation affects off-wallet economics only. Keegan supplies committed intent
  reservations; Isaac supplies verified final settlement. Unsolicited balances,
  corporate actions and reorg/provisional reversals need shared integration before
  real use; never fabricate execution observations from quotes.

USDT uses `money_scale=1000000`; quantities use token/BNB decimals. Prices mean
USDT base units per whole token. Decimal log-volatility is conservatively rounded
up to integer parts per billion; exact Fraction sizing retains `1%/(2*sigma5)`.
Sizing requires 61 closed, available, consecutive explicitly indexed US sessions
of underlying-share history, a pinned calendar/corporate-action version and a
verified token/share basis. No shorter/EWMA/token-calendar fallback is supplied.
Metadata, historical source availability and basis truth must come from adapters;
the fixture calendar/basis flags are not real capability evidence.

Daily loss requires an explicit midnight boundary mark passed to `roll_day`
BEFORE interval returns. Missing boundary anchors block buys; observed later
prices do not silently erase first-hour losses. Peak/8%/12% latches persist.
Strict simultaneous reduction bounds compose; all child orders are replanned
after actual fills. One pending wallet intent blocks further child issuance,
including exits, while every reduction remains visible. Exit reserve is spendable
by valid reductions. Infeasible gas, market, integrity, route or slippage never
turns a position into fictitious cash; dust is explicitly retained.

Exact quotes bind side and integer pay amount: USDT for buys, tokens for sells.
`MarketRequest.v1`/quotes/intents use `amount_kind=EXACT_IN`, `pay_asset`, `pay_units`;
requests identify `pay_decimals`, and quotes/intents carry `min_receive_units` in
the received asset's units (`receive_decimals` on intents). USDT here is normalized
to 6 decimals; Isaac's adapter must convert exactly to the chain token's decimals.
Buy `token_units` is an estimate, never a guaranteed settlement quantity.
Initial planning without a quote
returns `MarketRequest.v1` requests; a new observed quote creates a new snapshot
and requires fresh proposal/planning. `cost_reserve_units` is a configured planning
bound used for conservative post-cost cap sizing; discretionary quotes exceeding
it are rejected.
Mandatory reductions may exceed this planning estimate: their stricter post-quote
residuals remain explicit and are replanned after actual fills. Actual affordability
and exit slippage still gate execution. There is no hard-coded spread estimator in production planning. Missing quoted
depth blocks new entries under the currently declared depth rule (GAP-51); a
price-impact replacement must be adopted/manifested before the real adapter can
use it. Mandatory sells still obey their exit slippage and per-trade limits.
An over-cap executable quote requests a strictly smaller exact input; the next
snapshot can follow that observed quote chain. No scaled quote/proceeds are invented.

An unavailable held-name mark blocks that name's exits and all entries, while
healthy names can still reduce or flatten. `valuation_status=LOWER_BOUND` identifies
risk-only equity with unvalued holdings omitted; `worst_case_gross_units=null`
discloses that full exposure is unknown. This lower bound never updates PnL, peaks
or loss latches. A terminal obligation persists even at a zero lower bound.
Quote-cost rescaling occurs only after the child passes gas/fee/route gates, and
only its selected requirement receives a settlement/replan status.

Assessment integration: the runtime supplies `assessment_requests` keyed by issuer,
including the exact request/job/context/cutoff that produced the result. The current
issuer contexts are carried in `PolicyState.data.evidence_contexts` (initial empty
context is `{thesis: null, known_facts: []}`). Their hash domain is
`larp.intel.context.v1`, matching PR #4. Lifecycle changes do not change this hash.
Keegan must atomically synchronize these contexts with Yao's evidence reducer;
Keith's validator neither verifies raw filing text nor advances a second thesis
engine. Missing/stale/malformed/not-assessed inputs produce explicit diagnostics
and cannot clear re-entry. Fresh review additionally needs supported, complete,
conflict-free INTACT evidence with no unknown/fired falsifiers or new hypothetical events.
PR #4's comparison findings may cite a prior fact retrieved during the assessment
that is absent from `claims`/initial context. Matching verified harness findings and
thesis references are consumed with current supporting facts, and that reliance is
explicitly traced as `ASSESSMENT_PRIOR_SUPPORT_IN_PRODUCER_FINDING`. Opaque model-I/O
summaries confer no authority. Trusted producer identity and persistence/resolution
of the complete evidence graph remain Keegan/Yao's port responsibility.

Entry blockers requiring team decisions: Keith and Isaac own selecting a
rights-cleared sizing-price source, with Yao Zhu reviewing feature semantics and
SYZ/team adopting the choice. Current sizing requires underlying shares; D-09's
vendor remains on hold, and kit token candles cannot silently replace share
session closes. Isaac owns the GAP-51 depth-to-price-impact proposal, with team
adoption/manifest required. Until both decisions are resolved, real baseline entry
is unavailable; synthetic fixture series/depth are engineering inputs only.

## Research and open settings

`larp/research/replay.py` uses the same decision/planning/accounting functions and
recorded, interface-level fake observations. No execution engine or persistent
store is duplicated. `live_execution_parity=false` remains until integration.
Seeded fixtures key randomness by scenario/time/entity, independent of policy call
counts. They establish engineering behavior, not market probability or PnL.

`evaluation.py` checks registration completeness, rights/hash binding, aligned
calendar-cluster outcomes, all rejected allocations, wallet/model costs and paired
uncertainty. It does not authorize promotion. Real EXP allocation/pre-registration,
rights-cleared historical windows, actual availability/cost models and sample
thresholds remain open. Fusion inputs must be chronological out-of-fold predictions
with label-cutoff and purge/embargo checks; absent aligned rights-cleared data is
INCONCLUSIVE, and validated rows without training are NOT RUN. No model is trained.

Live mode always rejects startup. Needed later: source/basis/corporate-action and
valuation conventions, a real session calendar, measured size-specific costs and
availability, adopted baseline/evidence/default, terminal UTC gates, minimum size,
cost/gas/slippage/headroom budgets, accounting/finality/reorg conventions and atomic
store/signer integration. Review partner Yao Zhu; integrator Keegan; execution
observations Isaac. See IDEA-026 for reproducible evidence and backlog ownership.

Saved public/synthetic example inputs and outputs are in
`tests/research/fixtures/strategy-examples.json`. Generate exactly the same bytes:

```sh
/Users/keith/anaconda3/envs/binance-hackathon/bin/python -m larp.research.demo > /private/tmp/larp-strategy-examples.json
cmp tests/research/fixtures/strategy-examples.json /private/tmp/larp-strategy-examples.json
```

The three scenarios contain full immutable snapshot/state records. The baseline
has one intent; the costly opportunity has `ENTRY_COST_CAP` rejections; the blocked
mandatory exit retains its reduction with `BLOCKED_MARKET`. These outputs and 48
passing local tests are engineering evidence from pushed revision `21b8fdb`.
