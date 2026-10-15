# IDEA-057 — QuoteCostSummary.v1 producer: measure quote costs read-only, then summarise (Gate A input 1)

- Date / owner: 2026-10-15 SGT / built with Claude Code at the user's request ("create the summary tool"). Runs with real quotes belong to Isaac or Keith (dev-wallet Web3 API key); the summary and profiles need Isaac's and Keith's review before they are pinned.
- Status: open (criteria written before any test or code)
- Links: DEPLOYMENT_DAY.md "Inputs the shadow run still needs" item 1; `larp/strategy/profiles.py` (`quote_summary`, `build_live_profiles`); `config/strategy/LIVE.md`; `larp/execution_live/gate_b.py` DR-01 ("raw capture attribution and three-day/weekend coverage still required"); participant-kit.md K4, K8 (quote-and-swap, approve-transaction, gas-limit); ledger rule 4.

## What and why

A `dev` or `live` run needs a LIVE strategy profile. `build_live_profiles(summary, registry)` builds one, but its input, a `QuoteCostSummary.v1` measured from real Web3 Open API quotes, has no producer. Without it, Gate A cannot start. This entry adds the producer. It measures; it decides nothing. The profile algebra and its thresholds stay as IDEA-035/037/040 fixed them.

All results are quoted costs, not realised fills (ledger rule 4).

## Design

`larp/marketdata/cost_summary.py`, two subcommands.

**`capture`** (needs the Web3 key pair; read-only). Each round, for each of the five bStocks, at a configurable size (default 40 USDT, a full 20 % position of the final 200 USDT):
1. Buy quote USDT → token (`aggregator/quote-and-swap`, through `MarketPort.quote`, so production's vendor and slippage parameters apply).
2. Sell quote for exactly the token units the buy quote returned.
3. A re-quote of the same buy after `--requote-seconds` (default 15 s, the profile's proposal lifetime): drift between quotes.
4. `aggregator/approve-transaction` for USDT and for the token, with that sample's amounts: approve `gasLimit × gasPrice`.
5. `pre-transaction/gas-limit` for the buy and the sell transaction: swap gas = `max(tx.gas, ceil(1.2 × gasLimit)) × tx.gasPrice` (the kit's rule). An estimate that fails is recorded, and the sample then uses `--fallback-gas-limit` (default 1 116 000 = 1.2 × the kit's largest observed route, 930 k gas).

It also takes one USDT → native-BNB quote per round for the BNB price. Each sample is appended to a JSON-lines capture file with the raw response artifact hashes (`Web3Client` stores every response, with credentials redacted). A failed quote is recorded as a failure, never as a value. The tool never signs, approves or broadcasts, and never reads a wallet key or `AI_SEEDS_SECRET` (never-do #13 does not apply: nothing is logged to ai-seeds).

**`summarize`** (offline). It reads every capture file and writes the summary and a report beside it.

| Field | Rule |
|---|---|
| `samples` | successful samples for the token |
| `median_impact_bps` | median of all buy and sell `priceImpactPercent × 100`, ceiled, at least 1 |
| `spread_bps` | median of (round trip − buy impact − sell impact), ceiled, at least 0. Round trip = (USDT paid − USDT from the sell quote) / USDT paid. |
| `fee_bps` | 0. Fees are netted in the quoted amounts, which the round trip already measures; settlement nets all USDT transfers the same way (`ALL_USDT_TRANSFERS_INCLUDED_IN_NET_CASH`). The report keeps any `tradeFee` the API returns. |
| `approve_gas_bnb_units` | 90th percentile (nearest rank) of the sample's larger approve gas, in wei |
| `swap_gas_bnb_units` | 90th percentile of buy and sell swap gas, in wei |
| `slippage_bps` | 90th percentile of the re-quote drift, ceiled, between 1 and 50 |
| `quote_ttl_seconds` | `--quote-ttl-seconds` (default 30, the kit's "expire after about 30 s"); recorded as kit-stated, since the API returns no expiry |
| `bnb_price_units` / `bnb_decimals` | median USDT money units per BNB from the BNB quotes / 18 (wei) |
| `observed_at` | the latest sample's `available_at` |
| `capture_hash` | SHA-256 of the canonical sorted sample records (each names its raw artifacts) |

**Refusals.** Fewer than `--min-samples` (default 10) per token; fewer than `--min-days` (default 3) distinct UTC days; no weekend sample when `--require-weekend` is on (the default; DR-01 asks for weekend coverage); any token that fails the consumer's own check (`quote_summary`). The report lists coverage, failures, fallback-gas counts and every parameter, so a reviewer can see how each number arose.

## Pass criteria (recorded before any test is written)

Synthetic Web3 responses only; no credentials or network.

| ID | Check |
|---|---|
| Q1 | `capture`, against a fake client: per token one buy, one sell (for exactly the bought units), one re-quote, approves for USDT and the token, two gas estimates; one BNB quote per round. Sample records carry the artifact hashes and no credential. No endpoint outside the read allowlist is called (the real `Web3Client` refuses broadcast). |
| Q2 | A failed quote becomes a failure record, never a value; a failed gas estimate uses the fallback and is marked. |
| Q3 | `summarize` computes each field exactly as in the table, from synthetic samples with known values (median, ceiling, p90 nearest rank, clamps). |
| Q4 | Refusals: too few samples, too few days, no weekend, a token whose costs fail `quote_summary`, a capture file with a malformed record. |
| Q5 | End to end: synthetic captures → `summarize` → the summary passes `quote_summary`, and `build_live_profiles` with the repo's predicate set builds both profiles. `capture_hash` changes when any sample changes. |
| Q6 | CLI: `capture` without the key pair exits 2 without a call; `summarize` refuses to overwrite an existing summary. |
| Q7 | Full suite: the base count plus only these tests, no new failure or skip. |

Not in scope: running real captures (owners, with the dev wallet's key), choosing the size or coverage for the frozen profile (owners' review), and pinning the summary or profiles.
