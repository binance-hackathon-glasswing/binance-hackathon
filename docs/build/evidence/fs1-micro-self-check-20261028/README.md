# FS1 with the micro activation self-check (IDEA-110, 2026-10-28 SGT)

A **candidate for review**: not approved, installed or bound to a `signer.json`. It is
`fs1-final-recovery.json` (the FS1 install pin, `b8ba06e2…`) with only `activation_self_check` and its provenance
changed, so the final-wallet self-check is a 0.9 USDT round trip instead of a 32 USDT one. The same approvals as
any FS1 profile are needed (Isaac: profile and signer; Keegan: code and release; Yao: install). Record:
[IDEA-110](../../../ledger/IDEA-110.md).

| File | SHA-256 |
|---|---|
| `fs1-final-recovery-micro.json` | `a9c0675620541bee0ad64b15d9599954855b8ed9d7ba685d0a9560c300613fac` |
| `StrategyProfile.v1` digest of it (printed by the builder) | `1d16eb1328ac6d759755a0b197c9e3e68b48307d1c229fe0a5675c07ca5e3f9a` |

## What changes

```json
"activation_self_check": {"symbol": "SKHYB", "pay_units": 900000, "max_cost_units": 150000,
  "buy_after": "2026-10-27T17:00:00Z", "buy_until": "2026-10-28T08:00:00Z", "flat_by": "2026-10-28T09:30:00Z"}
```

- **Amount:** the self-check BUY pays at most 0.9 USDT of SKHYB (the existing cheapest-round-trip rule).
- **Cost:** that one BUY skips the 18.64 USDT minimum trade and the 50 bp entry-cost cap, which no sub-1-USDT leg can
  pass (gas alone is about 0.054 USDT). Instead its authorized-minimum cost (slippage/spread + fee + expected gas) must
  be at most 0.15 USDT, or it is refused as `SELF_CHECK_COST_CAP`. Expected: about 0.056 USDT per leg.
- **Timing (SGT, UTC in brackets):** no buy before 01:00 Oct 28 (Oct 27 17:00), so the primary services and the signer
  can be installed first. Buys stop 16:00 Oct 28 (08:00). The mandatory SELL of the whole position follows once the
  BUY settles, and the check must be flat by 17:30 Oct 28 (09:30), before the F-127 pause at 18:00 SGT (10:00).
  If it is not flat by then, it becomes EXPIRED and nothing is forced. FS1's own window (flat by 07:00 Oct 29 SGT)
  runs past the pause; this one does not.

## What stays the same

The pipeline is FS1's: each round the runtime gathers market, quote and evidence data, the policy decides, the
independent planner admits, execution requests and validates the exact quote and signs through the signer, settlement
is awaited, and round logs are delivered. Still enforced for the self-check BUY: the window, run/daily halts,
`new_spending_ok` health, market open state, the measured round trip, quote validity/age/route/slippage/impact,
`ENTRY_IMPACT_CAP`, the cost reserve, gas/BNB, cash and exit-gas reserve, the execution attempt budget and the
signer's own checks. Every other trade, including all of the scored run from Oct 29 22:00 SGT, uses FS1's minimum
trade and cost caps unchanged.

## Not yet known

- The Web3 Open API's smallest accepted bStock order has not been measured. If it refuses a 0.9 USDT quote, the
  check waits and then expires; it never falls back to a bigger trade.
- The gas cost is from the Oct 20 quote summary; a higher gas price on the day can make the 0.15 USDT cap refuse it.

## Reproduce

```bash
python -m tools.deploy.build_final_candidate \
  --s1-config docs/build/evidence/fs1-final-20261025/fs1-block.json \
  --s1-decision "<the decision string in ../fs1-final-20261025/README.md>" \
  --allowance-recovery --micro-self-check --output /tmp/fs1-micro-check.json
```

The output must be byte-identical to `fs1-final-recovery-micro.json`
(`tests/strategy/test_micro_self_check.py` checks this).
