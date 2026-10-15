# IDEA-058 — Gate A input tools: initial-state builder and issuers-map generator

- Date / owner: 2026-10-15 SGT / built with Claude Code at the user's request. Runs belong to the team (dev wallet's public address, the manifested BSC RPC, the Web3 key pair); outputs need review before they are pinned.
- Status: open (criteria written before any test or code)
- Branch: `claude/gate-a-inputs`, on top of PR #84 (IDEA-055), whose balance reader (`larp/execution_live/balances.py`) the builder reuses.
- Links: DEPLOYMENT_DAY.md "Inputs the shadow run still needs" items 3 and 5; `larp/runtime/service.py` (`init_run`, `build_driver` issuer check); `larp/execution_live/gate_b.py` DR-06; `larp/integration/contract.py` `_issuer_matches`; #25.

## What and why

Two Gate A inputs are files nobody has a tool to produce: the pinned initial state that `service init` builds the run from (item 5), and the `driver.issuers` map (item 3, unblocked since #25 was fixed). Each tool reads; neither decides anything.

## Design

**`python -m larp.runtime.initial_state`**
- Reads the wallet with `read_balances` at one finalized block over the manifested RPC, and refuses when latest ≠ pending nonce.
- Writes a `PortfolioState.v1`:
  - `cash_units`: USDT floored to the 6-decimal money scale. The dust stays on chain and is a recorded surplus, as in IDEA-055.
  - `bnb_units`: native wei, with `bnb_decimals` 18 (gate_b DR-06 requires exact wei).
  - Five positions at chain decimals.
  - `bnb_price_units` from the pinned LIVE profile's `quote_cost_summary` (IDEA-055 D6).
  - `opening_equity_units`, `peak_units` and `day_anchor_units`: cash plus BNB valued at that price.
  - `risk.day`: the observation's UTC date.
  - Empty accounting, reservations and applied events. `mode` is `dev` or `LIVE`.
- Refuses a wallet that holds any stock token: its cost basis would have to be invented. The dev wallet is funded in USDT only (F-107).
- Before writing, it checks its own output: `ledger_from(initial_projection(state), [])` must pass, `compare_balances` against the same observation must give `MATCH` or `SURPLUS_ONLY` with USDT dust only, and the DR-06 conditions must hold.
- Writes `<output>.provenance.json` beside it (block number and hash, observation SHA-256, profile SHA-256), never overwrites, and prints the state's SHA-256 for `runtime.json` `initial_state_sha256`.

**`python -m larp.runtime.issuers_map`**
- Reads `market/rwa/tokens` once (`MarketPort.metadata`).
- For each registry issuer, it maps `issuer_id → {token, underlying_id: underlyingTicker}`.
- Refuses unless `_issuer_matches` (the evidence contract's own rule, with `source_id` `BINANCE_WEB3`) accepts the pair, and unless the map passes `build_driver`'s registry check.
- Writes the JSON for `driver.issuers` plus a provenance sidecar (metadata artifact SHA-256, registry SHA-256), and never overwrites.

## Pass criteria (recorded before any test is written)

Synthetic RPC and Web3 responses; no credentials or network.

| ID | Check |
|---|---|
| G1 | Builder, from a synthetic chain: USDT floored (dust not booked), BNB in exact wei, positions at chain decimals and zero, the BNB price from the profile, opening equity = cash + BNB value, `risk.day` = the block's observation date, `mode` as asked. `ledger_from(initial_projection(…))` passes, `compare_balances` gives `MATCH` (or `SURPLUS_ONLY` with only USDT dust), and gate_b's DR-06 conditions hold. |
| G2 | Builder refusals: a held stock token, pending ≠ latest nonce, zero BNB (DR-06 requires native funding), a profile that is not LIVE or has no summary, an existing output file. |
| G3 | Builder CLI writes the state, the provenance sidecar and prints the SHA-256 of the exact bytes written. `service init` (`init_run`) accepts the file when pinned by that hash. |
| G4 | Issuers map: for synthetic metadata whose tickers are the registry's (`NVDA`, `GOOGL`, `TSLA`, `MSFT`, `SKHY`), the five entries come out keyed by canonical issuer ID with token and ticker, and each passes `_issuer_matches(…, source_id='BINANCE_WEB3')`. |
| G5 | Issuers-map refusals: a ticker the registry does not list for that token (e.g. `GOOGLB` → `AAPL`), a missing ticker, a duplicate or missing token row (from `MarketPort.metadata`), an existing output file. `build_driver`'s issuer check accepts the written map. |
| G6 | Full suite: the base count plus only these tests, no new failure or skip. |
