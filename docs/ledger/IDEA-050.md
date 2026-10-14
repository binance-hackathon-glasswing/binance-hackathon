# IDEA-050 — Complete round driver: execution hand-off, observation ingestion and run activation

- Date / owner: 2026-10-14 / Keegan (runtime owner, IDEA-038), built with Claude. Isaac reviews the execution-service side (`larp/execution_live/`), which is his module; nothing in it lifts one of his capability gates.
- Status: E1–E11 PASS on synthetic ports, disposable PostgreSQL and Linux CI (run 38574664846). Live signing remains blocked by the capability gates listed under "What stays gated".
- Base: `claude/round-driver-20261014` = integration head `c829fae` + IDEA-048 shadow driver (`claude/pre-deployment-review-4zxz7p`, ordinary merge) + PR #41 section C (`review/final-c-20261014`, ordinary merge; this branch depends on #41).
- Links: IDEA-048 (shadow driver and its "Still open" list), IDEA-049 protocol §0.1 and C-OPEN-001, IDEA-042 item 10, DR-07/13/19, I3/I4 (`docs/build/DEPLOYMENT_BUILD.md`), issues #24, #26, #31, #40, #52 and tracker #42.

## What and why

IDEA-048 built a shadow driver: rounds run, every intent ends `NOT_SUBMITTED` and nothing reaches execution. The final review (IDEA-049 §0.1, C-OPEN-001) blocks overall completion until the driver and the execution entry point are integrated. This entry completes both processes' loops so that a committed intent can travel I3 → execution service → signer → chain → I4 → settlement → round close, with every capability gate that is not mine left exactly where it is.

What stays gated (not changed here, and each still blocks live signing on its own):
- `Executor` accepts only fake capability bundles (`larp/execution.py`, Isaac). `build_execution` composes the live ports and stops at that gate with exit 2.
- `UnverifiedRouter` refuses every swap payload (GAP-29); the signer refuses swaps for the same reason.
- `MarketPort` exposes no executable quote without a quote verifier (GAP-29); native top-up receipts are refused (C-OPEN-005).
- Hosted model assessors stay `NotIntegrated` (DR-11).

## Design (recorded before implementation)

### Runtime process (`larp/runtime/driver.py`, `larp/runtime/service.py`)

Driver configuration gains `execution: "shadow" | "service"` (replaces IDEA-048's `signing: false`; a configuration still naming `signing` is refused).

One cycle (`RoundDriver.once(now_ms)`):
1. **Execution step.** Shadow: as IDEA-048. Service: (a) ingest the execution service's observations (`execution_observations`, read-only to `larp_runtime`) into the journal through `Coordinator.observe` with the settlement reducer, each event ID once, in an order the reducer accepts (repeated passes until no progress; a row whose bytes do not hash to its stored hash is refused and reported, never committed); (b) end every planned intent that has no execution record and whose command expired more than `expiry_grace_ms` ago with `NOT_SUBMITTED`, reason `COMMAND_EXPIRED_UNCLAIMED` (#26, second path).
2. `Coordinator.recover` closes every closable round.
3. **Hand-off window (I3).** While a planned intent has no execution record, is not final, and its command is still claimable (not expired, its `state_version` is the run's version, run not halted), the driver commits nothing else this cycle. Any other commit would make the command stale (`PostgresStore.command` requires the current version) and strand it (#26).
4. **Day roll (#31).** On the first cycle of a new UTC day within `day_roll_window_ms` of midnight, if every held position has a usable mark in the prefetched market observations, commit one `DAY_ROLLED` event: `roll_day` with the equity at those marks as the anchor. Otherwise record nothing and leave new risk blocked for the day (the planner already refuses new risk when `risk.day` is not today). Replay recommits `DAY_ROLLED` as a recorded fact.
5. **Quote follow-up (#40 wiring).** If the last round planned no intent but asked for quotes, fetch each requested quote through `MarketPort.observe` (bounded by `max_quote_requests`), with the profile as `quote_limits` so the request carries the profile slippage (PR #41). Only if at least one observation now holds an executable quote, run one follow-up round (`<round>/quote<n>`, at most `max_quote_rounds`) whose market port returns the quoted observations. Gas top-up quotes come from PR #41's `NativeGasQuotePort` as the context builder's `gas_quotes`, when the profile defines a gas floor.
6. **Evidence work** as IDEA-048 (review jobs, ingested filings, cadence).

**Decision cutoff (#24).** Before every round the driver fetches the market observations, then starts the round; the coordinator reads its decision clock after assessment, so the decision time is never before the observations' `available_at`. The context builder's market port returns that prefetched list.

### Execution process (`larp/execution_live/loop.py`, `larp/execution_live/main.py`)

- **`RunAuthorization`** supplies the guard facts from the journal at every snapshot (`Guards` calls it for create, prepare, authorize, sign, broadcast and reconcile):
  - `version_valid`: the run's registered build is the execution service's build;
  - `risk_valid`: no HALT reason and not quarantined; this makes a HALT stop the next signature of an execution already under way (#52), consistent with the existing rule that HALT stops every signature;
  - `reservation_valid`: the intent is still planned in an open round, is not final, and still holds a reservation;
  - `audit_durable`: the round's `ROUND_PLANNED` event (the durable pre-execution record) is in the journal and lists the intent;
  - `health_valid`: the incremental journal verification passes;
  - `clock_trusted`: no `CLOCK` HALT and the execution clock is not behind the last decision;
  - `expires_at`: the intent's own deadline;
  - `native_resource_route_valid`: false (C-OPEN-005).
- **`ExecutionLoop.once(now_ms)`**: claim each pending command that has no execution record, is unexpired and current (`ExecutionService.create_from_command`); advance every non-terminal execution record, and terminal ones whose final observation is not yet published; publish every observation to `execution_observations` (idempotent, fenced by the run epoch). The round-terminal attestation is true when every other planned intent of the round is already final.
- **Broadcast release boundary**: `FencedRelease` re-checks the durable possible-send record (`ExecutionStore.check_broadcast`) and submits through the Web3 Open API `broadcast-transaction` endpoint (`Web3Broadcaster`, PR #66 R1; the first version used RPC and was replaced), accepting only the signed transaction's own hash back.
- **`build_execution(config, store)`** composes ExecutionStore, MarketPort (profile limits), ChainEvidence, RunAuthorization, Guards, LiveVenue (UnverifiedRouter, FencedRelease), RemoteSigner, ReceiptFacts and the command mapping (profile per-trade cap and slippage, configured gas limits). The `Executor` refuses the live bundle; that refusal is reported as exit 2 `NOT_INTEGRATED` with reason `EXECUTOR_CAPABILITY_GATE`.

### Run lifecycle (`larp/runtime/service.py`)

- `service init`: creates a quarantined `dev`/`live` run from a `PortfolioState.v1` file pinned by SHA-256 in the runtime configuration; refuses an existing run.
- `service activate --reviewer NAME --review-ref REF`: the reviewed step that authorizes a run, run by a person before the scored run (and after a restore). It verifies the full journal and the release, refuses if any round is open or any execution record is non-terminal, lifts the quarantine with a new epoch (`PostgresStore.activate`), commits `VERSION_REGISTERED` for the running build if none is registered (and refuses a different registered build: never-do #5), then commits `RUN_ACTIVATED` naming the reviewer and reference. Replay recommits both as recorded facts.

Out of scope (unchanged, recorded as remaining): lifting `Executor`'s fake-only gate, the verified router decoder and quote verifier (GAP-29, Isaac), native top-up settlement (C-OPEN-005), hosted model assessors (DR-11), live profile/calendar/intelligence values (DR-09/DR-12), the team decisions on HALT semantics (#34) and proposal/signing lifetimes (#27), and every hosted check.

## Prospective acceptance (synthetic external ports, disposable PostgreSQL; no credentials, network, signing key of a real wallet or upload)

| ID | Expected outcome |
|---|---|
| E1 | Hand-off: in service mode a round that commits a command makes the next cycles commit nothing (no cadence round, no ingestion) until the execution loop has claimed it; the claim succeeds because the command is still current. |
| E2 | Ingestion: observations written to `execution_observations` are journaled exactly once each, in an order the reducer accepts, also after a driver restart; a row whose bytes no longer match its hash is refused, reported and never committed. |
| E3 | End to end with fake capability ports: driver + `ExecutionLoop` + `RemoteSigner` + `SignerService` (fake decoder) take a mandatory sell from evidence to approve, swap, FILL, settlement and round close; no reservation remains; the round log lists the order with its `tx_hash` and swap mapping; the uploader delivers it; `replay_live` reproduces the head. |
| E4 | Expiry (#26): an unclaimed command past `expires_ms + expiry_grace_ms` ends `NOT_SUBMITTED` / `COMMAND_EXPIRED_UNCLAIMED`; reservations are released; the round closes with the reason in `output.aborted`; a later claim attempt by the execution loop creates nothing. Before the grace ends nothing is ended. |
| E5 | HALT (#52): a HALT raised after the approval is final stops the swap: no signing request is written for it; reconciliation of an already broadcast attempt still completes. |
| E6 | Quote loop: a plan with quote requests makes the driver request each quote with the profile slippage (`slippagePercent` from `slippage_bps`); with an executable quote one follow-up round plans an intent in the same cycle; without one, no follow-up round runs; never more than `max_quote_rounds`. |
| E7 | Cutoff (#24): with observations whose `available_at` is the fetch completion time, the round's decision time is not before any of them and the planner does not reject them as future data. |
| E8 | Day roll (#31): one `DAY_ROLLED` per UTC day inside the window, anchor = equity at the prefetched marks, `risk.day` advances and buys are no longer refused for the stale day; no roll outside the window or with a held name unmarked; replay reproduces the event. |
| E9 | `build_execution`: a valid configuration composes the live ports and exits 2 `NOT_INTEGRATED` (`EXECUTOR_CAPABILITY_GATE`); an invalid or key-naming configuration exits 4. `build_driver` with `execution: "service"` builds; `execution` missing or unknown, or a leftover `signing` key, is refused (exit 4). |
| E10 | Lifecycle: `init` creates a quarantined dev run from the pinned file and refuses an existing run or a hash mismatch; `activate` lifts quarantine, registers the version and records the reviewer; it refuses a mode mismatch, a different registered build, an open round, a non-terminal execution record, an unverifiable journal and an already active run; replay reproduces both events. |
| E11 | Full suite against disposable PostgreSQL and Linux CI pass; every skip has its reason. Mutation checks (each reverted): dropping the hand-off wait, ending an intent before the grace, ignoring HALT in `RunAuthorization`, and skipping the hash check on ingestion each make at least one test fail. |

## Results

- Baseline before any IDEA-050 code, at merge `f565f19` (Python 3.13 venv from `deploy/requirements-test.lock`, disposable PostgreSQL 16): **1194 passed, 7 skipped, 1541 subtests**. Skips: three Linux bubblewrap checks, three opt-in real-systemd checks and the opt-in recorded-market test.
- Every run below used pushed commits; synthetic fixtures only, with a throwaway signing key generated per test. No credentials, network, real wallet, broadcast or upload.

Commits: criteria `7efd41f`; implementation and tests `8fc135c`; fixes found by the first runs `11a7dfa` (init refuses a wallet that already has a run) and `c21a58e` (causal order), test corrections `3f33b93`, `acd462f`, `21cfe49`, `6d20e12`; configuration examples `131b16e`.

Findings from the first runs (each fixed in its own pushed commit before the counted run):
1. **Ingestion order (real defect, caught by E2).** Event-ID order journaled a swap's FILL before its approval; the approval facts were then refused as the intent was already final, so the approval gas was never accounted. Facts are now applied in causal order (approval before swap, broadcast before final); E2 asserts both receipts' gas is accounted.
2. **`init` on a wallet that already has a run** raised a database error (exit 1). Runs are unique per wallet and chain; it now refuses (exit 4).
3. **IDEA-047 E01 expectation.** A new dev run is quarantined until `activate`, so the execution entry point now exits 3 before the gate; after activation a full configuration exits 2 `EXECUTOR_CAPABILITY_GATE`. The test was updated to check both.

| ID | Result | Evidence |
|---|---|---|
| E1 | PASS | `HandOff.test_e1_nothing_is_committed_until_the_execution_service_claims_the_command` (three cycles: no commit, cadence due; then the claim succeeds) |
| E2 | PASS | `Ingestion.test_e2_every_observation_is_journaled_once_…` (four facts after a runtime restart, once each, both gas charges accounted); `…_a_changed_outbox_row_is_refused_and_never_journaled` |
| E3 | PASS | `EndToEnd.test_e3_evidence_to_fill_settlement_round_log_upload_and_replay`: SELL NVDAB from a 4.02 filing → approve and swap signed by `SignerService` through `RemoteSigner`, both broadcasts through `FencedRelease` → FILL → no reservation, position 0 → round log with the swap `tx_hash` and mapping → uploader DELIVERED → `replay_live` head equal |
| E4 | PASS | `Expiry.test_e4_…`: nothing ended 1 ms before the grace; then `COMMAND_EXPIRED_UNCLAIMED`, reservations released, round closed, no later claim, `reservation_valid` false |
| E5 | PASS | `Halt.test_e5_a_halt_after_the_approval_stops_the_swap_signature` (one signature, one broadcast, intent aborted before the swap); `…_reconciliation_of_a_broadcast_swap_continues_under_halt` |
| E6 | PASS | `Quotes.test_e6_*` (one follow-up round with the executable quote; none without one; bound 0 requests nothing); profile bound to the market port in `test_e9_service_execution_builds_and_binds_the_profile_to_quotes` |
| E7 | PASS | `Cutoff.test_e7_the_decision_time_is_never_before_the_market_observations`; `…_without_the_prefetch_the_same_market_is_future_data` shows the #24 defect the prefetch removes |
| E8 | PASS | `DayRolls.test_e8_one_roll_per_day_at_the_prefetched_marks` (anchor = equity at the marks, not repeated, replay equal); `…_no_roll_outside_the_window_or_without_a_mark` |
| E9 | PASS | `tests/execution/test_execution_loop.py` (gate, refusals, exit codes, release boundary, submit-only client); `tests/execution/test_service_main.py`; `Composition.test_e9_*` in `tests/runtime/test_driver.py` |
| E10 | PASS | `Lifecycle.test_e10_init_then_activate_…` (reviewer journaled, replay equal); `Lifecycle.test_e10_refusals` (pinned file, mode, other build, open round, unfinished execution, journal, offline run, wallet with a run) |
| E11 | PASS | Full suite at `6d20e12`, disposable PostgreSQL 16, Python 3.13: **1218 passed, 7 skipped, 1564 subtests** (baseline 1194/1541); the same seven environment skips as the baseline. Mutations, each reverted: no hand-off wait → E1 fails; ending before the grace → E4 fails; HALT ignored in `RunAuthorization` → E5 fails; no hash check → E2 fails; no causal order → E2 fails; no prefetch → E7 fails. Linux CI at `6d20e12` (workflow_dispatch): all four jobs PASS — runtime (pytest with PostgreSQL, isolated demo, Docker smoke), host bundle, Terraform `deploy/aws` and `deploy/bootstrap`: [run 38574664846](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38574664846). |

## Still open (not done here)

1. **Capability gates (Isaac):** the `Executor`'s fake-only check, the verified router decoder and quote verifier (GAP-29), native top-up settlement (C-OPEN-005). Until they are lifted, `larp-execution` exits 2 and `execution: "service"` plans commands that expire unclaimed (`COMMAND_EXPIRED_UNCLAIMED`), which is truthful but trades nothing. Gate A rehearsals should use `execution: "shadow"`.
2. **Team decisions:** what each HALT reason blocks (#34; this build keeps "HALT stops every signature", now also for executions under way, #52); proposal, signing and router lifetimes (#27); the day-roll window and cadence (null in `config/runtime/runtime.example.json`, so a start refuses until set).
3. **Review:** Keegan (runtime) and Isaac (`larp/execution_live/loop.py`, `main.py`; the guard facts and the round-terminal attestation) before merge. This branch depends on PR #41.
4. **Hosted checks:** `init`/`activate` on the real database, both units under systemd with their state directories, and the kill/HALT drills.

## R — PR #66 review fixes (Isaac, 2026-10-14; criteria recorded before the tests and fixes)

Source: Isaac's review comment on PR #66 at `223c7ae`. All three findings were verified against the code and the kit before this entry.

| ID | Finding | Prospective check |
|---|---|---|
| R1 (P1) | `RawTransactionSubmitter` sends through RPC `eth_sendRawTransaction`; the kit's only order channel is the Web3 Open API (F-104, never-do #3; `POST /api/v1/dex/pre-transaction/broadcast-transaction`, body `binanceChainId`, `signedTransaction`, `address`, answer `txHash`). | The release boundary submits through an authenticated Web3 client that allows that one endpoint and nothing else; the read client still refuses it. The request carries exactly those three fields; the returned `txHash` must equal the signed transaction's hash; the stored artifact does not keep the signed bytes; a transport or API failure leaves the attempt as a possible send (never re-signed with another nonce). No RPC submission path or `broadcast_rpc_url` setting remains. |
| R2 (P1) | `DayRoll` values the marks at the cycle's clock, read before the fetch; the real client stamps `available_at` after the response, so a held position is never usable and the anchor never rolls. | With a market whose fetch advances the clock and stamps observations at completion, the roll succeeds (fails before the fix). The decision time is read after the fetch, and the day and window are checked again at that time; a fetch that ends past the window does not roll. |
| R3 (P2) | A runtime restart commits a RESTART incident, which makes a planned but unclaimed command stale; nothing reauthorizes it, so it expires `NOT_SUBMITTED`. | Through real `Service` startup after a simulated crash between planning and claiming: the restart incident is journaled, then one `COMMAND_REAUTHORIZED` event re-binds the still-valid command to the current version, and the execution loop claims it. Not reauthorized: an expired intent, a halted or quarantined run, an intent with an execution record, a final intent or one without its reservation, or another registered build. Replay reproduces the event. The command's bytes never change; only its authority (epoch, state version) moves forward, in the same journaled commit. |

Order: these tests are pushed and run first (expected red for R1–R3), then the fixes are pushed and the same tests, the full suite and Linux CI are run.

Results (2026-10-14):
- Red at test commit `cc7c06f`: R1 module import fails (`Web3Broadcaster` absent); both R2 tests return `MARK_UNAVAILABLE` (Isaac's finding reproduced); the R3 restart test finds no reauthorization. The three R3 refusal tests pass trivially before the fix (nothing reauthorizes).
- Fix `b9260c7`: all R tests and the affected modules pass (97 passed, 1 skipped, 118 subtests). Mutations, each reverted, each caught: R3 without the HALT, expiry or claim check; R2 with the clock read before the fetch.
- Full suite at `b9260c7`, disposable PostgreSQL 16: **1225 passed, 7 skipped, 1561 subtests** (the RPC submitter test, with three subtests, was replaced by two R1 tests; the same seven environment skips).
- Linux CI at `b9260c7`: pull_request [run 38581176409](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38581176409) and workflow_dispatch [run 38581342042](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38581342042), both green.

| ID | Result | Evidence |
|---|---|---|
| R1 | PASS | `test_r1_orders_are_broadcast_only_through_the_web3_open_api` (method, URL, exact three-field body, signed header, artifact without the signed bytes, submit-only client, failure = possible send, read client still refuses); `test_r1_no_rpc_submission_path_remains` |
| R2 | PASS | `test_r2_the_roll_values_marks_at_a_time_read_after_the_fetch`; `test_r2_a_fetch_that_ends_after_the_window_does_not_roll` |
| R3 | PASS | `Restart.test_r3_a_restart_reauthorizes_the_unclaimed_command_and_execution_claims_it` (real `Service` start: RESTART incident, one COMMAND_REAUTHORIZED, claim succeeds, command bytes unchanged, replay equal); expired, halted (latched CLOCK) and claimed intents are not reauthorized |
