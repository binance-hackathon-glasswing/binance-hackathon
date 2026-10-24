# FS1: the final live strategy profile (IDEA-093, 2026-10-25)

The candidate `StrategyProfile.v1` for the scored run (final wallet, `live` mode, AIand/ChatGPT routing). It is a
**candidate for review**: not approved, installed or bound to a `signer.json`. Isaac's approval of this hash and of the
final `signer.json`, Keegan's code/release review, the model-adoption reference and budget reconciliation, and the
final install (Yao) are still required. Install steps: [`docs/build/ops/final-fs1/README.md`](../../ops/final-fs1/README.md).
(FS1 was first built as "S4"; it differs from that build only in `policy_id` and provenance text.)

| File | SHA-256 |
|---|---|
| `fs1-block.json` (the profile's `s1` block; byte-identical to S2's `s2-block.json`) | `35e20c38e23657da6723e31b18f323e5f5ede778de938d73c72ff1a2c1408d03` |
| `fs1-final.json` (file bytes; the `PROFILE_SHA` to pin) | `75767d3e4d202d0e25645f7015cde5dcf4b50c07609b9731ae1b6d52b8d62f76` |
| `StrategyProfile.v1` digest of the same profile | `9249bf118af7191043d46f2f8684f853d5f843d4fc1a6f719573b7238d85624e` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile fs1-final.json`) | `fcd18d03da1ff71ecfb33d0bbf5ad08eda9f6e435b26806eae00f17954648cc8` |
| Model routing `config/intelligence/aiand-routing.fs1.json` | `9b86c7327eddca76e0739f6639211f9b609f18c027bc4e61bf83dc804dfcf1f4` |

## What it is

S1 (`TREND_GUARDED_VOL`) with the decided v1 FINAL scope (BOUNDED_FALSIFIER evidence, DISCRETIONARY_EXIT red-flag
exits, SHADOW statements), from the same pinned inputs as S2 (quote summary `quotes-complete-20261020`, red-flag
registry, L = 660 s / m = 30 s, initial-only gas budgets, two exit children per position), with:
- `s1.execution.hours` KIT_OPEN_STATE and 5 attempts per leg: entries, top-ups and exits at any hour on any day while
  `openState` is true (F-119, F-95), for both the planner and execution admission;
- the PF-04 calendar (IDEA-084): first buy 2026-10-29T14:00Z, new risk ends 2026-11-09T21:00Z, flatten from
  2026-11-10T19:00Z, signing ends 2026-11-11T14:45Z;
- `slippage_bps` 20 (S2 had 8; S2-F6 aborted 3 of run 4's 4 buys at the post-approve requote);
- equal weights 1/5, levels 95/60/30%, hard name line 35%, deterministic limiter, trend start UP;
- FINAL sizes: 200 USDT expected equity, 38.2 USDT per-trade cap, 0.2 USDT cost reserve, 18.637 USDT minimum trade.

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
those keys and of the two gas-budget formulas (`tests/strategy/test_fs1_final.py`, S4-6).

## Reproduce

```bash
python -m tools.deploy.build_final_candidate \
  --s1-config docs/build/evidence/fs1-final-20261025/fs1-block.json \
  --s1-decision "IDEA-093 FS1 (2026-10-25): S2's block (IDEA-084 PF-01 values; weights 1/5, start UP, legs 3, expiry 3, deterministic limiter) with hours KIT_OPEN_STATE and 5 attempts per leg, for the live FINAL" \
  --output /tmp/fs1-profile-check.json
```

It prints the `StrategyProfile.v1` digest above. The output must be byte-identical to `fs1-final.json`.
