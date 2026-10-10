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
  allowlisted findings. No live adoption is selected.
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
  settle one child; portfolio plans can remain partly completed. A service-cost
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

Exact quotes bind side and integer quantity. Initial planning without a quote
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
