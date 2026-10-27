# FS1-ALIGN01 — recent-PR alignment (2026-10-28 SGT)

FS1's selected source/configuration is aligned with the merged cleanup, retry and RFQ changes, but the shared
build still lacks the reviewed preparation-fence stack. It is not yet evidence of a qualified FINAL release.
Audited canonical: `3f8e16506a61d8995257054e997aae2ef1fb32ec`.

## Recent changes

| PR | Canonical at audit | FS1 consequence |
|---|---|---|
| 303 | Included | Flat-only late UTC day roll supports the pause across midnight; transient startup errors are restartable. A held self-check position still prevents the late flat roll. |
| 305 / 314 | Included | Small-wallet/200bp/independent-cost options remain restricted to S5 REHEARSAL. FINAL retains its selected values. `initial_gas_only` is also used by FS1 and is not itself a rehearsal-only field. |
| 310 | Included (`05b7aa6d`) | Shared `LiveVenue.revoke` validates API approve(router,1), then builds only zero-amount cleanup bytes; FS1's recovery opt-in reaches this path. |
| 311 | Included (`a2252760`) | Post-approval dependency failures can retry the original intent within its existing authority/probe bounds. It does not restart authority or promise route validity. |
| 318 | Included (`3f8e1650`) | Both FS1 planning `MarketPort` and execution `LiveVenue` request non-RFQ bStock routes; execution refuses RFQ-named legs before approval, including the tighter re-quote. Native top-up request scope is preserved. |
| 317 + 319 | **Missing** | PR319 merged into PR317's branch (`7484274a`); PR317 remains OPEN against canonical. FS1 uses the same executor, so its prepare path still needs that combined fence/completion-time repair. |

GitHub PR state/base/head and local merge ancestry were checked directly. Source trace:
`larp/runtime/service.py:build_driver`, `larp/execution_live/main.py:build_execution`,
`larp/marketdata/port.py:MarketPort.quote`, `larp/execution_live/venue.py:LiveVenue`,
`larp/strategy/schema.py:review_options` / `discretionary_cost_limit`, and `tools/deploy/prepare_fs1.py`.
Standalone preparation pins the FINAL profile and routing, enables recovery, compares final bindings and
requires independent numeric/signer assembly; no extra FS1 feature flag is needed for PR310/311/318.

## Pins and release-selection repair

Recomputed selected file SHA-256 values:

| Input | SHA-256 |
|---|---|
| FINAL recovery profile | `b8ba06e248b48b6406d77c1bda4110001324382e91bb63c71a27ce514731892f` |
| FS1 model routing | `9b86c7327eddca76e0739f6639211f9b609f18c027bc4e61bf83dc804dfcf1f4` |
| Qualified history config | `5e572570bc24fb2ca7b692dccf71f67a37c5fac3d75330e4558634cf45417be9` |

The FS1 run sheet still selected a bundle merely from PR278's merge. That permits older source without the
later execution fixes. Its Build/M1 instructions now require a qualified canonical descendant containing
PR310/311/318 and the merged PR317/319 stack, with exact source/bundle hashes and both-host manifest binding.
No FINAL release hash is invented while PR317 remains open. The historical S5-COST01 package pins `3ae83098`,
which includes PR310/311/314 but predates PR318 and the fence stack; its FS1-fix audit describes that recorded
release, not the currently complete set of fixes or an installed FINAL build.

No runtime, strategy, profile, policy, routing or history bytes changed. FS1 keeps 20bp slippage, the 50bp
authorized-minimum entry-cost gate, minimum18.637420USDT, per-trade cap38.2USDT, action gas0.001536BNB and
exit reserve0.01536BNB. Actual executable AMM quotes and final-wallet funding/caps must still qualify these
values; the old RFQ quoted price cannot establish cost admission.

## Verification

Criteria were recorded in IDEA-093 before these checks. Focused existing regressions on Linux/Python3.12.15/
PostgreSQL14.24: **168 passed, 52 subtests passed, zero failures or skips**, 30.06s. Covered FS1 profile rebuilding,
scope and strategy gates, independent FINAL preparation and caps/signer assembly, recovery, clean routed
startup, actual shell startup order against synthetic services, PostgreSQL self-check/restart/replay and
pause/day-roll persistence, mandatory cadence, API-anchored zero cleanup, bounded post-approval retries,
RFQ refusal/request scope, and S5 cost-option scope/refusal. Profile/routing/history hashes and PR ancestry
were checked separately. [Machine receipt](evidence/fs1-alignment-20261028.json).

This audit does not rerun the full suite. For the pending combined PR317/319 stack, the reviewed source
`65e6ed91` already has 3134 distinct passing tests, with five real-systemd and two optional fixture cases unrun;
see [PR319's review](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/319) and its
`docs/build/PR319_REVIEW_20261027.md` on PR317's branch. Those results are not relabeled as canonical or a host
qualification. All new checks used synthetic inputs and disposable local PostgreSQL; no live account/key,
provider/model, AWS/host, version registration, signing or transaction action occurred.

## Remaining owners

- Integration/release owner Keegan, installer Yao: merge PR317 (containing PR319), select/build/qualify the exact
  canonical release and bind it on both hosts. Runtime owner retains the fence review's receipt-reconciliation
  stale-version and command-claim follow-up disposition. No merge or deployment is performed by this audit.
- Isaac with Keith/Keegan: fresh FINAL AMM quote economics, recovery/caps/gas/BNB and exact signer/profile
  acceptance; registered cleanup/live RQ-5/RQ-8 evidence remains open. Existing FLAT-01/OBS03 items apply.
- Keith/Keegan/Yao and account owners: history/model adoption and budget, GAP-73 funding/BNB valuation,
  GAP-74 self-check/pause/handover and exact-host evidence, DB-01/ARCH-01 capacity/archive qualification.
  The self-check profile's18:00Z/23:00Z outer bounds remain later than the run sheet's earlier pause deadline;
  that already-recorded GAP-74 decision is not closed here.

No whole incomplete-work item is closed: implementation ancestry is distinct from the remaining measured
release/host/live acceptance. [Updated run sheet](ops/final-fs1/README.md) /
[criteria and results](../ledger/IDEA-093.md#fs1-align01--recent-pr-alignment-audit-2026-10-28-criteria-before-checks).
