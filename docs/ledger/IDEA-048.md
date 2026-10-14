# IDEA-048 — Round driver for the supervised runtime (shadow, no signing)

- Date / owner: 2026-10-13 / Claude for the user (pre-deployment review session). Runtime files are Keegan's (IDEA-038); this entry asks for his review, and Isaac's for the execution boundary.
- Status: open; D1–D8 PASS on synthetic fixtures (locally and Linux CI); Gate A still blocked (see "Still open").
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

## Results (2026-10-13)

Commits: criteria `c8b2fdb`; implementation and tests `91a75ef`; D1b test and amendment `b6ce5e0`.

- **Procedure deviation:** the first local run of `tests/runtime/test_driver.py` (10 passed) happened on the uncommitted working tree, before `91a75ef` was pushed. That is against the commit-before-run rule (AGENTS.md). Everything was re-run from the pushed commits; only those runs count below. Synthetic fixtures only; no credentials, network, signing or upload in any run.
- Focused, at `b6ce5e0` against disposable PostgreSQL 16 (Python 3.13 venv from `deploy/requirements-test.lock`): **11 passed, 16 subtests**.
- Mutation checks (each reverted): a wrong abort reason, ingestion ahead of review jobs, no settlement after a new round, and rerunning an interrupted round under the same ID each make exactly one test fail. The last one survived before D1b was added.
- Full suite at `b6ce5e0`: **1071 passed, 4 skipped, 1353 subtests**. The skips are three Linux bubblewrap checks and the opt-in recorded-market test.
- Linux CI on `b6ce5e0` (workflow_dispatch, all jobs: pytest with PostgreSQL, isolated demo, Docker smoke, both Terraform directories): **PASS**, [run 38392373400](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38392373400).

| ID | Result | Evidence |
|---|---|---|
| D1 | PASS | `test_d1_an_ingested_filing_runs_once_across_cycles_and_restart` |
| D1b | PASS | `test_d1b_a_round_interrupted_before_planning_is_retried_under_the_next_attempt` |
| D2 | PASS | `test_d2_shadow_ends_every_intent_unsigned_and_releases_reservations` (`store.command` patched to fail) |
| D3 | PASS | `test_d3_cadence_rounds_run_once_per_slot_and_skip_issuers_without_records` |
| D4 | PASS | `test_d4_a_scheduled_review_job_runs_first_and_is_finished` |
| D5 | PASS | `test_d5_the_driver_journal_replays_to_the_same_head_without_live_ports` |
| D6 | PASS | `test_d6_index_and_remaining_across_session_boundaries` |
| D7 | PASS | four `test_d7_*` tests (composition, NotIntegrated, refusals, exit codes through `main`) |
| D8 | PASS | full suite and CI above |

## Still open before Gate A (not done here)

1. **No way to start a dev run.** Nothing initializes a `dev`/`live` run, commits its version event, or performs the reviewed takeover that lifts a production run's quarantine (`PostgresStore.takeover` leaves non-offline runs quarantined; `Service` exits 3 on a quarantined run). Owner Keegan + Isaac; a design decision, since it is the step that authorizes the run.
2. **Inputs the driver refuses to start without:** a `LIVE` strategy profile (DR-09; needs the quote-cost summary), a frozen `USRegularSessions.v1` calendar covering the run, live intelligence parameters (`config/intelligence/intelligence.v1.json` `live` values are all null), and the market `underlying_id` per token (the issuer registry marks every token↔share mapping UNVERIFIED).
3. **Uploader process:** round logs are written to the outbox but only `DeliveryWorker` sends them, and no deployed process runs it with `AI_SEEDS_SECRET` (DR-07 on the host).
4. **Ingestion process on the host:** `python -m larp.sources.live run` must run beside the runtime to fill the evidence store (DR-12).
5. **Gate B paths:** I3 → execution service → signer, and the planner's `quote_requests` loop (quotes stay non-executable until router decoding is verified).
6. Review by Keegan (runtime owner) and Isaac (the shadow `EXECUTION_RECONCILER` observations).
7. Evidence store access on the host: PR #20 makes `/var/lib/larp-evidence` `0700` to `larp-evidence`; the runtime user needs read access, or the store moves to PostgreSQL (PR #20 review, 2026-10-14).

- 2026-10-14 note: renumbered from IDEA-047 before merge. PR #20 (`codex/hosting-option-b-20261012`) had already used IDEA-047 for its host services, so this entry's earlier commits (`c8b2fdb`, `91a75ef`, `b6ce5e0`, `e30a054`) say IDEA-047. Nothing else changed.
- 2026-10-14 note: the PR #20 review found the evidence store is `0700` to `larp-evidence` on the host, so the driver's `evidence_root` cannot be read by `larp-runtime` as deployed. The sharing mechanism is now item 7 under "Still open".
