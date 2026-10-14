# Final review B: decisions (strategy, risk, accounting, scoring)

**Assigned to: Keegan** (random draw, 2026-10-14).

You are one of four reviewers running LARP's final pre-deployment review (IDEA-049). LARP is our agent for the Binance Agentic AI Challenge. Your section is **how the agent turns information into positions, and what it may hold**:
- the trading policy;
- eligible instruments;
- sizing and caps;
- loss controls and HALT precedence;
- market-state gating;
- costs and minimum trade size;
- portfolio accounting and equity valuation;
- the end-of-run schedule;
- how all of this lines up with how the run is scored.

**Before anything else, read `docs/build/final-review/00-common-protocol.md` in full. It is part of this prompt.** Then read `AGENTS.md`, and `docs/skill/SKILL.md` §0 (reading contract, never-do list). Follow the protocol's phases exactly:
1. Independent requirements catalogue.
2. Trace and tests.
3. Fix loop.
4. Repeat until a full pass finds nothing new.

Branch `review/final-b-<yyyymmdd>`. Record: `docs/ledger/IDEA-049-B.md`. Catalogue: `docs/build/final-review/B-catalogue.md`.

## Scope inventory (every item must appear in your coverage table)

Where an item is split between sections, you own only the aspect named here.

- **Official page:** F-20 ("reasons, decides, manages its own risk"), F-35 (instruments, opening value, valuation, scoring the same for all), F-42, F-43, F-44 (fees and gas reduce the final figure), F-45 (tie-break: max drawdown), F-46, F-50, F-52, F-64 (the leverage, shorting and derivatives aspect), F-73 (instruments subject to final requirements).
- **Kit:**
  - F-91: eligible instruments only, never other tokenized versions, decimals from the API. The contract addresses belong to C.
  - F-93: gas reduces equity; BNB accounting.
  - F-95: `openState=false` means "don't place orders"; `tokenPrice` vs `referencePrice`; candles only for periods with trades.
  - F-105: the per-trade cap and "no endless retries or repeated orders", decision aspect.
  - F-107: funding of 100 USDT dev and 200 USDT final, USDT only.
  - K3 and K6 (market data semantics). Check each against the verbatim Guide pages.
- **Organiser:** F-115 (how the run is assessed: completed trades' PnL, drawdown, logs and code repo "all together"; not trading at all is not the point), against F-42..F-50. Record the conflict and the conservative design consequence. F-114 and F-117 (no changes once the run starts), as they constrain what the policy must do autonomously.
- **Never-do lines (SKILL.md §0.3):** #1 (the agent decides trades; humans never choose trades), #4 (long-only, five bStocks against USDT, BNB only for gas).
- **Guardrails:** G-02, G-11 (enforce what is declared), G-13 (decision aspect), G-15; G-20..G-30 (default HOLD, caps, loss controls, event policy, end-of-window, liquidity and cost, staleness, degraded mode, gas floor, sizing, market-state awareness), G-46, each as adopted by a decision record or declared.
- **Declared proposal** (`docs/proposal/proposal_answers.md`):
  - "Position & risk management", every sentence;
  - the decision and strategy parts of "Your Proposal";
  - the declared values in `docs/skill/larp/plan.md` "Declared values".
- **Decided items:**
  - plan.md D-05..D-12 as decided;
  - IDEA-035 (A8, B4, B5, B6, B11, C1, C8, §5, §10.1, §10.2: 80 % invested, equal weight 4 × 20 %, red-flag class actions, flatten by Nov 11 15:00 UTC, price-impact rule, gas top-up rounds);
  - IDEA-037 and its addendum (EQUAL_WEIGHT, top-ups below 75 % gross, trims above 25 % per name or 90 % gross, durable trims);
  - IDEA-040 decided parts;
  - the deviations register rows that change declared behaviour (`config/release/deviations.v1.json`, reasons and evidence).
- **Readiness and acceptance:** DR-06 (BNB floor, decision side), DR-08 (token-candle sessions and price-impact entry inputs), DR-09 (live strategy profile with every value sourced), DR-10 (red-flag class actions: sell, 5-session buy block, SHADOW), DR-14 (end-of-run schedule); AT items about policy, risk, accounting and replay (`docs/ledger/IDEA-021.md`).
- **Backlog items to resolve or re-state:** GAP-06, 08, 09, 10, 11, 12, 13, 14, 15, 32 (financial arithmetic), 50, 51, 53, 54, 64, 66.

## Exclusive paths (you may edit)

- Code: `larp/strategy/`, `larp/risk/`, `larp/research/`.
- Config: `config/strategy/`. Profile **values** need a team decision: propose them as DECISION-NEEDED with derivations.
- Tests: `tests/strategy/`, `tests/risk/`, `tests/research/`.
- Tools: `tools/realised_vol.py`, `tools/idea018/`.
- Records: your catalogue and record.

## Use-case prompts (in addition to protocol §1.5)

Make sure your use cases include at least:
- the opening allocation from 200 USDT with no BNB;
- each cap reached exactly and exceeded by drift;
- a red-flag Class 1 sale while a Class 2 block is active;
- a block expiring across a weekend or US holiday or the Nov 1 DST change;
- daily loss and drawdown thresholds crossed intraday and reset;
- HALT while holding positions (mandatory reductions still allowed?);
- `openState=false` for days;
- a quote's price impact above the limit for every name;
- a fill differing from the quote;
- dust left after a sale;
- gas top-up rounds competing with stock buys;
- the terminal window: no new risk after the cut, flatten finished by Nov 11 15:00 UTC, what happens if a flatten swap fails;
- equity valuation when a quote is missing or stale;
- the final wallet starting fresh on Oct 27–29;
- the scored-run constraint that nothing may be changed by hand.

## After your catalogue is frozen (not before)

Only then compare with these areas, which earlier work left open or flagged. They are hints for phase 2, not requirements:
- the live strategy profile still needs measured quote costs and an Oct 22 freeze (`config/strategy/LIVE.md`, GAP-13);
- the per-trade cap must cover one full 20 % position (IDEA-037);
- Isaac's I3 mapping and Keith's intent disagreed on the BNB receive decimals (IDEA-042 §4);
- correlated-exposure treatment and simultaneous-order reservations are open (GAP-10);
- risk precedence and reset semantics (GAP-12);
- what the policy does when the registered default itself loses money (GAP-09).

For profile values, derive each from the requirements and measured inputs, and mark them for team approval.

## Done means

Protocol §4, plus:
- every declared limit (G-11) is either enforced by a passing test or covered by a recorded deviation with reason;
- a test shows the policy never produces a prohibited position (non-eligible token, short, leverage) from any reachable state;
- a replay of a synthetic 14-day run (including the terminal window) satisfies every decided risk rule.
