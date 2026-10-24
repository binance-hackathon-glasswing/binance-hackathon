# Complete-position exit sizing — LD10-P03

**Selected for the rehearsal under Keegan's delegation; fresh child-quote coverage
is still required.** This packet resolves the design half of LD10-P02
(`BLOCKED_EXECUTION_CASH_CAP`). It does not replace the private fresh quote packet,
Isaac's coverage rerun, release qualification or any owner/host acceptance.

## What the actual path did

| Path | Before P03 | Effect |
|---|---|---|
| Planner, mandatory SELL | Child capped at `per_trade_cap_units` at the mark; remainder left for later rounds | A position just over the cap leaves an arbitrarily small residual (≈0.007 USDT for the P02 NVDAB numbers) whose quote may be unroutable and whose gas exceeds its value |
| Planner, over-cap quote | Resize to `pay × cap / (cash + fee)` | Same tiny-residual problem |
| `MarketPort` consumer check | Validated every quote as **non-mandatory** | An over-cap SELL is refused before the planner can resize it; the next round asks for the same size. A mandatory exit above the 2 bp impact limit is also refused, although the planner accepts mandatory impact |
| Profile reserve | One approve+swap action per position (4 × 384,000,000,000,000 wei) | Does not cover a position needing two children |

None of these signed anything above a limit: `ExecutionService` and `LiveVenue`
still refuse over-cap commands and quotes. They were liveness gaps in a
complete exit.

## Decision (limits unchanged)

- **Balanced children.** A mandatory SELL of remaining quantity R worth V at the
  mark uses k = ceil(V × 1.01 / cap) children and sizes this child floor(R / k).
  Each child is at most cap/1.01 at the mark and, once split, above cap/2.02
  (≈9.95 USDT). A position worth at most cap/1.01 (19.90 USDT) exits in one child.
  An over-cap mandatory quote resizes to floor(pay / k′), k′ = ceil((cash + fee) × 1.01 / cap).
  Discretionary and BUY sizing are unchanged.
- **Port parity.** `MarketPort` validates with the request's own `mandatory` flag.
  The cash cap, slippage, freshness, route and proof checks are unchanged.
- **Count.** At most four EQUAL_WEIGHT positions. Hard-name trims bound a held
  position near 1/4 of safe equity (25 USDT at the expected 100 USDT), so k ≤ 2
  for any position up to 39.80 USDT. That needs safe equity above about 159 USDT
  to break, a gain of more than 60% within the rehearsal.
- **Reserve and funding.** Exit reserve = 4 × 2 × 384,000,000,000,000 =
  **3,072,000,000,000,000 wei**. The N = 15 whole-run planning target becomes
  (15 + 8) × 0.000384 = **0.008832 BNB**. Against the dated 14:10:31Z balance
  (0.002694498869362886 BNB) the additional amount is **0.006137501130637114 BNB**.
  Cleanup stays disabled. Expected-cost sizing (80,004,608,000,000 wei) and the
  18.637420 USDT minimum are unchanged. Not funded; the funding owner decides.
- **Timing.** Each child is its own command with the unchanged 660 s authority
  and 30 s margin. With one child per wallet per 15-minute cadence round, eight
  exit children need at least 2 h of open rounds; the flatten window
  (Oct 26 00:00 to 14:45 UTC) is 14.75 h. The planner still sells only while
  both token and underlying are open.

## Files

| File | SHA-256 |
|---|---|
| `rehearsal-deterministic.json` (file) | `e95d5842d15c07e0e2bb5dab761e6a1730f69aed4af4cfce2596eec68e070250` |
| StrategyProfile.v1 document | `ddb8281374239cd5626f0b8432e7913ab44ea30ea2f2165fbbf176e47a7d8b17` |
| `rehearsal-deterministic-scope.json` | same scope as LD11-RH01, rebound to this profile; `selected_coverage_file` is null |

The profile differs from the LD10-Q01 selection
(`41332056…` / `eb61ca86…`) only in `exit_gas_reserve_units` and its provenance.
CAP-02 policy `3241abd3…` and router policy `05759e90…` are unchanged. The
Q01, P02 and RC2 files are byte-identical; `build()` without arguments still
reproduces the Q01 bytes.

```sh
python -m tools.deploy.build_rehearsal_candidate --exit-children 2 --output /tmp/p03-profile.json
PYTHONPATH=. python3 docs/build/evidence/rehearsal-exit-split-20261021/verify.py
```

`verify.py` also replays the P02 NVDAB hypothetical: full 91,560,616,415,214,999 raw
units, proceeds 20.106983099120719276 USDT, planned children
45,780,308,207,607,499 and 45,780,308,207,607,500. These are a sizing check only,
not fresh quotes.

## Coverage review changes

`caps_review` now replays the split on each symbol's largest recorded SELL. If that
exit is split, the full-size quote is `EXIT_SIZING_ONLY` evidence and every
planned child needs its own quote with proceeds ≤ cap (`QUOTE_CASH_CAP`);
`FULL_EXIT_CHILD_QUOTE_MISSING_<symbol>` and `FULL_EXIT_CHILDREN_<symbol>` block
otherwise. `FULL_BOOK_EXIT_RESERVE` requires positions × children × action ≤ the
profile reserve. Quoted proceeds stand in for the runtime mark. Near the 19.90 USDT
threshold the runtime may choose one child where the review chose two (or the
reverse). Both stay within the two-child reserve, and execution checks the cap
again on every child. `ld10_readonly_packet.py` requests the child sizes after the
full-size quote, using a self-contained copy of the split that a test pins to the
reviewer. `review_rehearsal_caps.py` now reads this profile.

## Remaining (owners)

1. Done in LD10-P04 ([record](ld10-p04-coverage.json)): a fresh read-only primary-host packet built from this
   profile (`ld10_readonly_packet.py --profile …/rehearsal-deterministic.json`):
   holdings, nonce, allowances, minimum/max BUY, full-size SELL and child SELL
   quotes. Isaac reruns `review_rehearsal_caps.py` on the qualified build. The
   recorded 0.002694 BNB will report `INITIAL_BNB_EXIT_RESERVE` as blocked until
   funding.
2. Funding owner: confirm or revise the 0.008832 BNB target and fund through the
   approved process; then fresh reconciliation.
3. Done as AB-REL-RC3 ([receipt](../ab-rel-rc3-20261021.json)): requalified the new canonical source and kept its original artifact. RC2
   does not qualify this code.
4. Residual risk, accepted for the rehearsal: a fresh quote more than 1% above
   the mark is still refused (safely) and retried at the next round's mark. A
   position above 39.80 USDT would need a third child beyond the reserve.

No network, AWS/SSM, database, key, signer assembly, funding, installation or
trade was performed for this packet.
