# LD09-B: LIVE profile candidates with the decoupled gas budget

These are the LD04-P candidates (`../ld04-authority-profiles-20261020/`: DC-01 inputs, initial-gas-only, L = 660 s,
m = 30 s) rebuilt with Keegan's LD09-B decision (IDEA-061 LD09-B, 2026-10-21). The exit reserve and the action budget
are at the draft cap gas price. The minimum trade is sized at an expected gas price. **They are evidence candidates
only:** no runtime config, manifest pin or readiness flag changes.

| File | File SHA-256 | StrategyProfile.v1 |
|---|---|---|
| `rehearsal-live.json` | `cee1a869b3a0a31d9f1d579089218fa54413728778a1232dd82ff1010bd52be3` | `54eb6fba7a9796ec027de352fcd5bfe02c29493c188c69c3b7443fd2496f2ea4` |
| `final-live.json` | `0497a820821524cbcbd5234c937aa211b8b94da9409b6b8e787f49b33cde5f40` | `07e8e8c90b06440993052a0ce67ce6f24b103edac4dc7b168ba457a75267a542` |

| Value | LD04-P | LD09-B | Basis |
|---|---:|---:|---|
| `gas_action_budget_units` (wei) | 76,177,634,176,000 | **200,011,400,000,000** | 1,000,057 gas × 5/4 × 0.16 gwei (IDEA-070 LD02d maximum) |
| `gas_sizing_budget_units` (wei) | — | **80,004,560,000,000** | the same gas × 5/4 × 0.064 gwei |
| `exit_gas_reserve_units` (wei) | 304,710,536,704,000 | **800,045,600,000,000** | 4 × action budget (EQUAL_WEIGHT) |
| `minimum_trade_units` (USDT, 6 dp) | 19,443,104 | **18,637,420** | sizing gas value inside the 50 bp budget, worst DC-01 symbol (MSFTB) |

The minimum trade fits both the rehearsal (20 USDT) and the final (40 USDT) positions. Every other value is
unchanged from LD04-P. The four changed keys carry `decision_id` "IDEA-061 LD09-B (Keegan, 2026-10-21)" and
`data_hash` `0acea18f…02511a6`, the SHA-256 of [`ld02d-size-sell-20261021.json`](../ld02d-size-sell-20261021.json).

Reproduce from the repository root (no network); `tests/strategy/test_gas_budget_b.py` checks it byte for byte:

```sh
python -m larp.strategy.profiles \
  --summary docs/build/evidence/quotes-complete-20261020/quote-cost-summary.json \
  --predicates config/intelligence/red_flags.v1.json --output-dir NEW_DIR --initial-gas-only \
  --execution-authority-seconds 660 --submission-margin-seconds 30 \
  --authority-decision "IDEA-049-C LD04-V01 (Keegan, 2026-10-20)" \
  --authority-evidence docs/build/evidence/ld02-execution-packet-20261020.json \
  --gas-action-budget-units 200011400000000 --gas-sizing-budget-units 80004560000000 \
  --gas-budget-decision "IDEA-061 LD09-B (Keegan, 2026-10-21)" \
  --gas-budget-evidence docs/build/evidence/ld02d-size-sell-20261021.json
```

Still open before adoption:
- Keith's #120 profile review, including whether 0.064 gwei is the right expected price and a refreshed MSFTB spread.
- The #119 fee evidence and Isaac's #44 caps, including the 1.6 % `max_gas` margin.
- The measured S1 or permitted fallback profile and the final calendar (PF-01). These remain dated EQUAL_WEIGHT
  candidates on DC-01 windows.
- Keith's whole-run seeding input N.
- Selected cleanup gas, if LD06 cleanup is enabled.
