# FS1: the final live strategy profile (IDEA-093, 2026-10-25)

The candidate `StrategyProfile.v1` for the scored run (final wallet, `live` mode, AIand/ChatGPT routing). It is a
**candidate for review**: not approved, installed or bound to a `signer.json`. Isaac's approval of this hash and of the
final `signer.json`, Keegan's code/release review, the model-adoption reference and budget reconciliation, and the
final install (Yao) are still required. Install steps: [`docs/build/ops/final-fs1/README.md`](../../ops/final-fs1/README.md).
PR278-RV01 adds four explicit behavior fields below. Earlier receipts/pins in IDEA-093 are historical.

| File | SHA-256 |
|---|---|
| `fs1-block.json` (the profile's `s1` block; byte-identical to S2's `s2-block.json`) | `35e20c38e23657da6723e31b18f323e5f5ede778de938d73c72ff1a2c1408d03` |
| `fs1-final-recovery.json` (IDEA-098: FS1 plus IDEA-096 allowance-recovery gas; **the `PROFILE_SHA` to pin**) | `b8ba06e248b48b6406d77c1bda4110001324382e91bb63c71a27ce514731892f` |
| `fs1-final.json` (cleanup off; superseded for install by the recovery profile) | `19176e6c6537291bb41f440636f51d7f6313d2444ebf7242cc145316d840f291` |
| `StrategyProfile.v1` digest of the same profile | `969532f583ee0015533178d4ca4bd5917c6bb6340e9e396c47e8a38db91d559f` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile fs1-final.json`) | `5b642bd3b58638f9e7e495340ee6a0bb733a32f4effe90cf187bedcda900a289` |
| Model routing `config/intelligence/aiand-routing.fs1.json` | `9b86c7327eddca76e0739f6639211f9b609f18c027bc4e61bf83dc804dfcf1f4` |

## What it is

S1 (`TREND_GUARDED_VOL`) with the decided v1 FINAL scope (BOUNDED_FALSIFIER evidence, DISCRETIONARY_EXIT red-flag
exits, SHADOW statements), from the same pinned inputs as S2 (quote summary `quotes-complete-20261020`, red-flag
registry, L = 660 s / m = 30 s, initial-only gas budgets, two exit children per position), with:
- `s1.execution.hours` KIT_OPEN_STATE and 5 attempts per leg: stock entries, stock top-ups and exits at any hour on any day while
  `openState` is true (F-119, F-95), for both the planner and execution admission;
- the PF-04 calendar (IDEA-084): first buy 2026-10-29T14:00Z, new risk ends 2026-11-09T21:00Z, flatten from
  2026-11-10T19:00Z, signing ends 2026-11-11T14:45Z;
- `slippage_bps` 20 (S2 had 8; S2-F6 aborted 3 of run 4's 4 buys at the post-approve requote);
- equal weights 1/5, levels 95/60/30%, hard name line 35%, deterministic limiter, trend start UP;
- FINAL sizes: 200 USDT expected equity, 38.2 USDT per-trade cap, 0.2 USDT cost reserve, 18.637 USDT minimum trade.
- `entry_cost_basis=AUTHORIZED_MINIMUM`: entry cost/reserve tests include authorized slippage, fee and expected gas.
- `run_halt_recovery_bps=500`: PF02 clears only the 8% buy stop below5% drawdown with healthy reconciled valuation.
- `s1_reduction_cost_cap_bps=50`: pending level reductions may sell below the entry minimum only when the exact
  quote's authorized minimum clears both50bp and the cash cost reserve. Blocked reductions remain pending.
- `s1_capital_basis=EXCLUDE_GAS`: apply the nominal levels to cash plus marked stocks minus the cost reserve.
  F-125 requires a 30 USDT gas swap: at 170 USDT cash the high book targets 161.31 USDT, or 32.262 USDT per name,
  before fills/costs, instead of starving the fifth name. Actual funding fees and self-check costs change these
  numbers. Initial-only gas remains enabled; there are no agent BNB top-ups. Fixed-price BNB risk valuation and
  the final-wallet self-check/handover remain GAP-73/74 acceptance items.
- `activation_self_check` (IDEA-093 SC, GAP-74, F-125): before Oct 29, one BUY of about 32 USDT of SKHYB (cheapest measured round trip) between 2026-10-27T00:00Z and 2026-10-28T18:00Z, a mandatory SELL of the whole position, DONE before 2026-10-28T23:00Z; the same run then trades the scored run. Holding only the self-check does not block the later entry.

The runtime still supplies no trend series: the prior/start trend state is retained. These repairs do not prove
alpha or activate a predictive signal. See [PR278-RV01 research/review](../../../research/fs1-review-20261025.md).

**Models in decisions.** With the FS1 routing (ChatGPT `gpt-6.1-sol` first, Kimi K3 / GLM-5.3 reviewing through
AIand), the model assesses EDGAR evidence each round. A finding counts only once the deterministic verifier matches it
to the filing. Then a verified Item 4.02 forces an exit (mandatory SELL), and a verified Item 1.05 or 2.06 blocks buys
for five sessions. Models never size, sign or place orders.

`KIT_OPEN_STATE` is refused for this profile in any run mode but `live` (`execution_bounds.require_open_state_scope`).
A new run's install refuses a wallet holding any stock (`gate_a.initial_state`), so the final wallet must be stock-free
at install, and the scored run must remain one run (automatic restarts resume it; F-124).

## Against the generator's FINAL S1 profile from the same inputs

It differs only in `s1.execution.hours`, `trade_after`, `new_risk_end`, `flatten_start` (PF-04; `signing_end` is
already 14:45), `slippage_bps`, `policy_id`, `exit_gas_reserve_units` (two exit children, as S2) and the provenance of
those keys and of the two gas-budget formulas, plus the four PR278-RV01 fields/provenance above
(`tests/strategy/test_fs1_final.py`, S4-6). Fresh profile/cap/gas/signer/release review is required.

## Reproduce

```bash
python -m tools.deploy.build_final_candidate \
  --s1-config docs/build/evidence/fs1-final-20261025/fs1-block.json \
  --s1-decision "IDEA-093 FS1 (2026-10-25): S2's block (IDEA-084 PF-01 values; weights 1/5, start UP, legs 3, expiry 3, deterministic limiter) with hours KIT_OPEN_STATE and 5 attempts per leg, for the live FINAL" \
  --output /tmp/fs1-profile-check.json
```

It prints the `StrategyProfile.v1` digest above. The output must be byte-identical to `fs1-final.json`.

## IDEA-098: the recovery profile

`fs1-final-recovery.json` is `tools/deploy/build_final_candidate.py --allowance-recovery` on the same inputs. It differs
from `fs1-final.json` only in IDEA-096's recovery gas at the CAP-02 signed ceilings (1,200,000 gas × 160,000,000 wei):
`gas_action_budget_units` 1.536e15 wei (eight children: up to five other-token revokes, the approve, and the swap or the
pay-token revoke after an abort), `exit_gas_reserve_units` 1.536e16 wei (0.01536 BNB; five positions × two exit children),
and the provenance of those two keys and of `gas_sizing_budget_units` (value unchanged). The strategy, windows, sizes,
slippage and the activation self-check are unchanged. Without it, one swap aborted after its approve leaves an open
allowance that blocks every later trade in another token, as in run 4's flatten (IDEA-096, IDEA-098 RC1x).
