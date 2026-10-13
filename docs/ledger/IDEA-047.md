# IDEA-047 — Round driver for the supervised runtime (shadow, no signing)

- Date / owner: 2026-10-13 / Claude for the user (pre-deployment review session). Runtime files are Keegan's (IDEA-038); this entry asks for his review, and Isaac's for the execution boundary.
- Status: open; prospective criteria written before any implementation or test run.
- Base: `claude/pre-deployment-review-4zxz7p`, fast-forwarded to the head of the PR #18 → #19 → #20 stack (`79abab4`), because the stack changes `larp/runtime/service.py` (configuration binding, IAM database). `main` is not touched.
- Links: IDEA-042 item 10 (the missing round driver), DR-07, DR-13, DR-19, Gate A in `docs/build/DEPLOYMENT_BUILD.md`, GAP-65.

## What and why

`larp.runtime.service.build_driver` raises `NotIntegrated`, so `service run` exits 2 and the runtime cannot run a single round. Every component the loop needs exists and is tested (`tests/integration/test_service_system.py` wires them with fake external ports). This entry adds the driver: one bounded cycle per `Service` tick that turns pending evidence work into coordinator rounds and ends every planned intent without signing. It is the Gate A (hosted shadow) path only. Signing stays out until DR-02/03/04 have evidence; a configuration asking for it is refused.

## Design (recorded before implementation)

- **One cycle (`RoundDriver.once(now_ms)`):** (1) end every open round's pending intents through the shadow execution and close the round; (2) `Coordinator.recover` closes any other closable round; (3) take at most one unit of work and run it as one round with `Coordinator.start`; (4) repeat step 1 so a round planned this cycle closes in the same cycle.
- **Work, in priority order:**
  1. review jobs the planner committed to the PostgreSQL scheduler (lane `evidence`), claimed and finished through `Scheduler`;
  2. ingestion jobs (`ASSESS_FILING`) that the separate ingestion process wrote to the evidence SQLite store, highest priority first, skipping expired jobs and jobs whose round already exists;
  3. a cadence round when nothing else is due: one `REASSESS_ISSUER` job per cadence slot (`floor(now / cadence_ms)`), issuers in registry order by slot, on the issuer's latest record available at the cutoff; an issuer with no record is skipped for that slot.
  Round IDs are derived from the job ID or the slot, so a restart never runs the same work twice.
- **Shadow execution:** each pending intent ends with an `ExecutionObservation.v1` of kind `NOT_SUBMITTED`, reason `SHADOW_NO_SIGNING`, through the existing settlement reducer (`larp.integration.settlement.settle`). Reservations are released, balances do not change, and the round log lists the order without a `tx_hash`, with the reason in `output.aborted` (kit convention, F-100). The signing gate `store.command()` is never called. The observation's `origin` is `EXECUTION_RECONCILER`, the only final-fact origin that is not a scripted fake; in shadow the driver is the execution owner.
- **Health port** (planner gates): `integrity_ok` = run not quarantined; `ownership_ok` = the run's epoch is the driver's; `clock_ok` = decision time not behind the last decision; `journal_ok` = the store's incremental journal verification (`verified_snapshot(full=False)`) passes; `new_spending_ok` = all four and no intent still pending. In shadow this shows what the agent would have done; nothing is signed.
- **Session calendar:** a `USRegularSessions.v1` file supplies `session_index` (the latest session whose open time has passed) and `remaining_sessions` (sessions not yet closed). A decision time after the calendar's last session is refused.
- **Composition (`build_driver(config, store, secrets)`):** a `driver` block in the runtime configuration (whose bytes are already bound to the release manifest) names the strategy profile file and session calendar file with their SHA-256, the evidence root, the intelligence configuration mode, the cadence, `issuers` (issuer ID → token and market `underlying_id`, tokens checked against the issuer registry) and `assessor: "deterministic"`. It builds the real `MarketPort` over `Web3Client` (read-only endpoints, runtime secrets), the real `EvidenceAssessor` with `RuleBaselineModel`, `ContextBuilder`, `StrategyPolicy`, `RuntimePlanner` and a `Coordinator` with `require_version=True`. Refusals: `signing: true` and any hosted model assessor are `NotIntegrated` (exit 2); a missing or mismatched file, hash, mode or issuer is a start refusal (exit 4), never a restart loop.

Out of scope (recorded as remaining work): signing and the I3 → execution-service path (Gate B); the quote-request loop (`quote_requests` are logged, not fetched: `MarketPort.observe` returns no executable quote until router decoding is verified); round-log upload (the uploader holds `AI_SEEDS_SECRET` and runs as its own process); initializing a dev/live run, committing its version event and the reviewed takeover that lifts a production run's quarantine (no code does this today); the LIVE profile values and the frozen session calendar (data inputs, DR-09).

## Prospective acceptance (synthetic external ports, disposable PostgreSQL; no credentials, network, signing or upload)

| ID | Expected outcome |
|---|---|
| D1 | A cycle with one ingested filing job runs exactly one round through the real assessor, context builder, strategy and planner, closes it and writes exactly one audit event. The next cycle, and a new driver over the same stores (restart), do not run that job again. |
| D2 | Shadow: a round whose planner commits intents ends each one `NOT_SUBMITTED` / `SHADOW_NO_SIGNING`; no reservation row remains; settled balances are unchanged; the round log lists the orders without `tx_hash` and with `output.aborted` reasons; `store.command` is never called. |
| D3 | Cadence: with no jobs, one round per slot for the slot's issuer on its latest record; the same slot does not run twice; an issuer without records is skipped. |
| D4 | A planner review job in the scheduler's `evidence` lane is claimed, run as a round and finished (`DONE`), ahead of ingestion jobs. |
| D5 | The journal the driver produced replays to the same head through `replay_live` with no live port called. |
| D6 | Session calendar: index and remaining sessions at, before and after session boundaries; a time past the last session is refused. |
| D7 | `build_driver`: `signing: true` and a model assessor raise `NotIntegrated`; a missing driver block, a profile or calendar hash mismatch, an unknown issuer token or a missing evidence store refuse the start (exit 4 through `main`); a valid configuration builds a driver whose ports pass `check_live_start` (no fakes) in `dev` mode. |
| D8 | Full suite against disposable PostgreSQL and Linux CI pass; any skip reported with its reason. |

- 2026-10-13 amendment (before running it): **D1b** — a round that opened but crashed before its plan committed is closed by `recover` as interrupted (logged `PROCESS_INTERRUPTED`) and its work runs again under the next attempt number (`#2`), at most three attempts; a planned round is never rerun. Added because a mutation check showed nothing tested this retry rule.

## Results

NOT RUN.
