# FS1 fixes in the selected rehearsal release

Runtime release: `3ae830981b9ce1c4b80a46dbeb086825d91ae7ec`. `package.json` records 19 verified ancestor merge
commits; staging checks those exact commits against the selected source. No experimental S6/S7/S8 branch is used.

This release retains the documentation-only PR312 research dispositions and adds PR314 cash/cost separation. The selected S5 profile explicitly adopts zero extra USDT cushion and a separately sourced 0.40USDT cost ceiling under Yao approval; the existing200bp entry check, gas protection and FINAL profiles remain unchanged.

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
| 314 | Independent S5 economic-cost ceiling and optional zero USDT cash cushion |

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
