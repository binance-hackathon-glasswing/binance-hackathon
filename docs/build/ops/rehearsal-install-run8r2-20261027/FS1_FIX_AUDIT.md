# FS1 fixes in the selected rehearsal release

Runtime release: `a22527603ad34c545ff30b5ef996f575b3435b53`. `package.json` records 18 verified ancestor merge
commits; staging checks those exact commits against the selected source. No experimental S6/S7/S8 branch is used.

Canonical advanced to `fd6b6719003795e21038947014de67f6de8808e2` via PR312 during preparation. Its six changed
files are documentation only; no code, test, config or profile changed relative to the pinned runtime. The package
branch includes those records: EXP-007 is INCONCLUSIVE and the trend guard ships under the pre-registered O2
choice; S6/S7 are NOT SUPPORTED and S8 INCONCLUSIVE, all excluded from deployment. This records the latest
research disposition without changing the tested release or adopting experimental strategy code.

| Included PR | Correction or prerequisite |
|---|---|
| 278 | FS1 policy refinements, gas-excluded capital, execution and parallel assessment integration |
| 280 | Incremental archive/anchor reads and journal OOM mitigation (does not complete ARCH-01) |
| 282, 283 | Zero-only allowance recovery and FS1 sell/flatten path |
| 286 | Released zero-unit reservation rows do not block fresh caps assembly |
| 287 | Reason summaries in decision/round logs |
| 290 | Refund unclaimed discretionary attempts |
| 291 | Mandatory SELL cadence retries rather than discretionary attempt cap |
| 292 | Database-load mitigation and operational instrumentation |
| 295, 297, 298 | Bounded five-name token history, timestamp evidence, qualified history configuration |
| 296 | FS1 model-routing startup checks and standalone FINAL preparation |
| 303 | Flat-run late daily roll and restartable transient startup errors |
| 305 | S5 proportional targets in DOWN regimes, scoped small-wallet economics and infrastructure settings |
| 306 | F-127 pause/install run-sheet correction |
| 310 | Live API-compatible zero revoke (API amount1 validated, signed amount0) |
| 311 | Bounded fresh quote retry after transient post-approval provider failure |

## What this audit does not mark complete

This short S5 development rehearsal is not FINAL production acceptance. The source/backlog still requires:

- **ARCH-01**: full-projection journal growth remains. Run7's first daily segment exceeded the archive bound;
  shrinking per-event payloads and qualifying long-run restart/backup/storage behavior remain required before FINAL.
  PR280/292 do not close that requirement. Do not treat a successful short rehearsal as its acceptance.
- **DB-01 / IDEA-109 S-06/S-07**: actual RDS monitoring, resource capacity, pinned maintenance/backup windows,
  alarms, pending maintenance and host restart behavior require operator readback. A free-plan instance-size
  refusal is not permission to silently ignore the capacity problem.
- **GAP-73**: fixed-price BNB risk valuation and actual final-wallet funding/caps/reserve acceptance remain.
- **GAP-74 / F-127**: FINAL self-check profile bounds and pause/handover acceptance remain separate from this S5
  window. This package never changes FINAL profiles, funding or the registered FINAL wallet.
- **OBS03-B2**: fresh quotes were observed after approval; the upstream RFQ still expired within seconds.
  PR311 adds bounded resilience, not a provider route-validity guarantee. Record actual retry/quote/sign timings.
- **Live gates**: exact signer/config approval, history/model/receiver/source/RPC/host qualification, real buy/sell
  receipts, accounting, zero allowances and delivered logs are still measured at installation/rehearsal.
- **Release checks**: see VALIDATION.json for checks actually run and any blocked cases. Host provisioning smoke
  tests install units; they do not establish a running real-systemd service or real provider qualification.

If “all fixes for FS1” means every production backlog item above, that condition is not met by the repository.
This package includes all listed merged fixes and makes the remaining work visible; it cannot certify FINAL ready.
