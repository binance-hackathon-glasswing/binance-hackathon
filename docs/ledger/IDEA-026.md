# IDEA-026 — Strategy, independent risk/accounting and economic evaluation build

- Date / author: 2026-10-10 / Keith's requested build prompt, implemented by Codex.
- Status: open; offline development implementation, **tests NOT RUN at initial commit**. No selected live strategy, profitability claim, real adapter or activation authorization.
- Branch / baseline: `codex/strategy-risk-research` from shared kickoff `e10eae2` on `origin/codex/engine-foundation`; foundation `5a6f4d7` with 13 original tests preserved.
- Scope: `larp/strategy`, `larp/risk`, `larp/research`, corresponding tests, `config/strategy`, `tools/realised_vol.py`, `tools/idea018`. Shared contracts, dependencies/lock, ledger index/backlog and other owners' modules unchanged per PARALLEL_BUILD.
- Links: IDEA-014/017/018/019/021/022; foundation's IDEA-023/024; AT02/04/05/13/15/16/18; GAP-26/37/44/50/51/62/64/65/66.

## 1. Decisions and increment

Entity-keyed closed/available underlying-share features with 61 consecutive session closes, explicit calendar/corporate-action/source/version/price scales and missingness. Declared sizing `1%/(2*sigma60*sqrt(5))` uses deterministic Decimal volatility rounded upward to integer ppb; no insufficient-history sizing substitution. Token/share basis is a required fixture flag, not proved by this branch.

Pure explicit-state low-turnover candidate with quantity holds, entry, five-session review without forced churn, cost-aware planner resize/exit, fresh-review re-entry and terminal requirements. Default evidence SHADOW; allowlisted, verified-context bounded-falsifier research configuration is explicit and blocks re-entry for the run. Not a live policy selection. No calibrated forecast, profit lock or trading quota. Baseline return premise remains unvalidated.

Independent reduction planning composes name/gross/regime/deep-loss/terminal/additional upper bounds before execution gates, even without a valid policy. The 3% daily/8% run/12%→40% declared ladder persists. Day boundaries require a trusted pre-return anchor; missing anchors block new risk. Operating caps and cost reserves are visibly synthetic validated configuration; actual live values remain unavailable. Mandatory reductions bypass minimum-size/cadence/entry-cost filters but retain market/integrity/route/gas/slippage checks. Requirements remain pending/blocked/dust until real settlement.

Integer-unit planner uses conservative post-cost equity, worst pending buys, held quantities and cash/gas reservation requests. No unconfirmed proceeds finance entries. One wallet child at a time; parent residuals re-plan after observed fills. Exact-size quote requests precede intents. Average-cost accounting applies actual final fills/fees/gas once, never creates holdings on approval/revert, separates off-wallet service costs, and is shared with replay. Atomic persistence, resource ownership and execution authorization remain Keegan/Isaac boundaries.

Recorded snapshot replay and seeded interface-level fake observations call production functions; no second accounting/execution engine. Research pipeline checks registration/data identity, costs, matched portfolios, common calendar clusters, incomplete outcomes, chronological OOF fusion inputs and purge/embargo. No rights-cleared historical data supplied, no trained fusion model, no EXP independently allocated, no simulation comparison or profitability experiment run. Tests exercise only synthetic correctness/counterexamples.

Research corrections: IDEA-022 R1 midnight anchor now precedes first interval return; R2 timestamped lag/AR adjacency is retained; R3 only contiguous-hour returns enter measured session variance and gap coverage is reported. IDEA-021 C07 terminal gas now enters drawdown. The normal `variants.py` modes also exclude gaps; its labelled seven-day-hole reproduction remains historical. Saved volatility probe failures cannot shift another issuer's label; short/nonfinite data and still-open calendar-day bars are rejected. Probe estimates remain research, not declared US-session runtime sizing.

## 2. Prospective engineering acceptance — commit/push BEFORE running

Commands from repo root, Python 3.12.14 environment:

```sh
/Users/keith/anaconda3/envs/binance-hackathon/bin/python -m unittest discover -s tests -v
/Users/keith/anaconda3/envs/binance-hackathon/bin/python -m larp.research.demo
```

Pass only if original 13 foundation tests remain green and added checks establish:

1. Future/unavailable bars cannot change earlier feature values or semantic actions; missing/gapped/zero/mismatched history has no sizing fallback; corporate-action/basis/identity distinctions persist.
2. Evidence starts shadow; a separately configured bounded variant requires supported verifier-accepted allowlisted findings and matching run/issuer/profile/prior-thesis context. Stale evidence cannot clear re-entry. Horizon expiry requests review rather than forced turnover.
3. Invalid or absent policy still computes mandatory risk; competing upper bounds use the strictest; mandatory reductions bypass cadence/minimum but blocked markets/integrity retain holdings/requirements.
4. Pending buys/sells block conflicting allocation; worst-case exposure and actual cash are reported, unconfirmed proceeds unused; child exits respect caps, preserve residuals and report dust; exit reserves may pay valid exits.
5. Midnight resets only daily latch, first-hour losses count, 8%/12% persist; approvals/reverts consume observed gas without acquiring holdings; fills are idempotent; conflicting event IDs fail; fees/services/net equity are separated; final liquidation gas enters simulated drawdown.
6. Exact snapshot replay matches hashes; policy failure falls back to independent planner; seeded exogenous observations are invariant to call/order. These are local fake-port checks, not full runtime/OS replay proof.
7. Gap-separated lag pairs and cross-session gaps never become contiguous measurements; failed daily response cannot relabel another issuer; MC tests use two fixed paths only (no path sampling or policy comparison).
8. Incomplete/unpaired/overlapping research data is NOT RUN/INCONCLUSIVE; costs and rejected allocations enter paired metrics; in-sample/future-label upstream fusion predictions fail; no-data fusion remains INCONCLUSIVE. Synthetic statistical unit checks do not constitute financial evidence.

Also require whitespace checks and examples showing a baseline intent, rejected costly opportunity and blocked mandatory exit. Results appended after testing pushed code. No credentials/private captures read; no network/market/model/signer/ai-seeds call is part of verification. NumPy for legacy simulator regression is already pinned; no lock change requested.

## 3. Remaining integration and policy decisions

- Yao Zhu reviews feature/evidence semantics and supplies verified AssessmentResult/chronological OOF model outputs; held-out evidence/forecast/fusion merit is NOT RUN, not established by engineering fixtures. GAP-26/64 and real dataset availability remain open.
- Keegan integrates owner-local payload detail with shared ports, transactional commit/state versions/risk latch persistence, scheduler boundary marks and reservation ownership; all cross-component AT cases remain open. Keegan updates the reserved IDEA-026 ledger row and shared backlog using the evidence here, per PARALLEL_BUILD.
- Isaac supplies actual token metadata, marks, executable exact-size quotes, nonce/finality and observed receipts. Real depth is unavailable under the current declaration: entries reject missing depth until GAP-51's replacement is adopted. Gas controller/top-up, finality/reorg/provisional reversals, corporate actions, unsolicited changes and live accounting reconciliation need integrated tests before use.
- Team selects live baseline/evidence/default and parameters/provenance, approved headroom/minimum/cost/gas/slippage/time budgets, calendar/basis/valuation and terminal UTC gates. Live configuration rejects activation here; fixture defaults cannot be promoted as calibrated settings. GAP-37 capacity and full-pipeline rehearsal remain unverified.
- Keith owns subsequent rights-cleared, prospectively coordinated EXP registration/reruns. Historical IDEA-012/018 estimates are **not recomputed** by source corrections; retain their original results and append dated corrections after any registered rerun. GAP-66 therefore remains open for reproduction/evidence integration, with code-level corrections recorded here.
- Integration notice: `main` commit `91af281` uses IDEA-023 for the prior proposed-solutions document, while the kickoff branch separately uses IDEA-023 for engine contracts. This pre-existing ID/path collision must be reconciled by Keegan in an integrating commit without losing either record; this branch does not rewrite either history or the shared index.

Documentation references describe current work and remaining boundaries. A fake reservation installer/quote producer is explicitly temporary and restricted to offline fixtures. No automatic merge to main, organiser messages or live capability verification is authorized by this branch.
