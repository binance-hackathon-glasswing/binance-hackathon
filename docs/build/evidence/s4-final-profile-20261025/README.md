# S4 FINAL profile: the final strategy, 24/7 (IDEA-093, 2026-10-25)

The candidate `StrategyProfile.v1` for the scored run (final wallet, `live` mode). It is a **candidate for review**: not
approved, installed or bound to a `signer.json`. Isaac's approval of this hash and of the final `signer.json`, Keegan's
code/release review and the final install (Yao) are still required.

| File | SHA-256 |
|---|---|
| `s4-block.json` (the profile's `s1` block; byte-identical to S2's `s2-block.json`) | `35e20c38e23657da6723e31b18f323e5f5ede778de938d73c72ff1a2c1408d03` |
| `final-s4.json` (file bytes; the `PROFILE_SHA` to pin) | `bb59b1908fb45c962fe6f655acf6da59f73aee87e4368b8337f76d00446ff791` |
| `StrategyProfile.v1` digest of the same profile | `429b702549170d646b681877d309e2533462911566fc3c1ccb2d9c79e142fac4` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile final-s4.json`) | `14257e77b68514b6b9eff5c1537f37a0831d740de7de51572eaee759496f489a` |

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

`KIT_OPEN_STATE` is refused for this profile in any run mode but `live` (`execution_bounds.require_open_state_scope`).

## Against the generator's FINAL S1 profile from the same inputs

It differs only in `s1.execution.hours`, `trade_after`, `new_risk_end`, `flatten_start` (PF-04; `signing_end` is
already 14:45), `slippage_bps`, `policy_id`, `exit_gas_reserve_units` (two exit children, as S2) and the provenance of
those keys and of the two gas-budget formulas (`tests/strategy/test_s4_final.py`, S4-6).

## Reproduce

```bash
python -m tools.deploy.build_final_candidate \
  --s1-config docs/build/evidence/s4-final-profile-20261025/s4-block.json \
  --s1-decision "IDEA-093 S4 (2026-10-25): S2's block (IDEA-084 PF-01 values; weights 1/5, start UP, legs 3, expiry 3, deterministic limiter) with hours KIT_OPEN_STATE and 5 attempts per leg, for the live FINAL" \
  --output /tmp/s4-profile-check.json
```

It prints the `StrategyProfile.v1` digest above. The output must be byte-identical to `final-s4.json`.
