# IDEA-042 — Deployment build record: runtime, hosting and integration (Keegan)

- Date / author: 2026-10-11 / Keegan (drafted with Claude)
- Status: open (items 1, 3, 4, 5 and 8 complete for the repository side, each green in Linux CI on PR #13; their host drills are due at Gates A/B; items 2, 6, 7, 9 and 10 not started: they wait on Isaac's interfaces, the team's hosting inputs and the rehearsals)
- What: Keegan's part of the deployment build, prompt [09-runtime-deployment](../build/09-runtime-deployment.prompt.txt) under the common brief [DEPLOYMENT_BUILD.md](../build/DEPLOYMENT_BUILD.md) ([IDEA-038](IDEA-038.md)): reconciled baseline, settlement and execution wiring, official ai-seeds logging, live replay, restart/HALT, hourly anchoring, hosting, release/manifest/deviations, final-wallet switch, integration and the DR checklist evidence.
- Branch: `codex/deploy-runtime`, cut from `codex/deployment-prompts` (`e4ebff6`, the commit that adds the brief; PR #12 still open), with `origin/codex/engine-foundation` (`e8658ba`) merged in by an ordinary merge (`b583059`). Reviewer: Isaac.
- Decisions that govern: [IDEA-035](IDEA-035.md) and [IDEA-037](IDEA-037.md); where main's `a21d034` differs, those govern (IDEA-035 A11).
- Rules: criteria below are committed and pushed before anything they cover runs. Results are PASS, FAIL, NOT RUN or INCONCLUSIVE with the commit SHA. Synthetic results are engineering evidence, not market evidence. No secret, organiser message, signing, wallet use or merge to `main` is part of this record unless a later dated entry says so with the team's authorization.

## 0. Baseline before changes

- 2026-10-11, `e4ebff6` (brief commit, before the base merge), local Python 3.13.16 with disposable PostgreSQL 16, fresh venv from `deploy/requirements-test.lock` (`pip check` clean): **592 passed, 3 skipped, 770 subtests passed**. The 3 skips are the Linux bubblewrap isolation tests (the local sandbox has no bubblewrap). CI runs Python 3.12.15 with PostgreSQL 14.24.
- Found while merging: the base merge of main (`e8658ba`) kept main's `a21d034` plan.md and SKILL.md lines but dropped its GAP-51 sentence ("2026-10-10 team decision: replace the declared depth cap with a price-impact limit …"). Restored in item 1 below; no other `a21d034` line is missing (checked by counting `Decided 2026-10-10` in plan.md, the F-116 receipt note in SKILL.md and the `2026-10-10 team decision` notes in INCOMPLETE_WORK.md against `a21d034`).

## 1. Item 1 — reconciled baseline (due Oct 13)

### 1.1 Prospective criteria (written 2026-10-11, before running anything they cover)

- **B1 · main synced and annotated (A11).** `codex/deploy-runtime` contains `a21d034` through ordinary merges only (no rebase, no force-push). plan.md D-03, D-05, D-11 and D-12, SKILL.md Q-03, and the GAP-51 and GAP-57 lines carry a dated annotation from IDEA-035/037 where they differ from `a21d034`; GAP-51's lost `a21d034` sentence is restored. Check: `git merge-base --is-ancestor a21d034 HEAD`; the annotations are present; `git diff --check` clean.
- **B2 · PR #9 (`codex/integration-tests`).** The base is merged in by a merge commit. C1 passes. C3 is rewritten to exercise the current evidence-to-strategy path on the current golden output and passes. C2 is kept unchanged as the drift check: it is expected to **fail** until Keith re-captures `tests/strategy/fixtures/assessment-producer.json` (prompt 07 item 8), so PR #9 must not merge before that. C4's `expectedFailure` is re-checked against the current code and either kept with a stated reason or replaced by a passing test of the current coordinator path.
- **B3 · PR #10 closed and its parts ported.** PR #10 is closed with a note naming what superseded it (PR #7's `ContextBuilder`/`RuntimePlanner`) and what was ported. Its execution bridge and settlement reducer are ported to `larp/integration/settlement.py` for the projection layout `ledger_from` uses (`portfolio` + `balances` in the projection, reservations in the store), with interface I4's two boundaries:
  1. `BROADCAST_ATTEMPTED` changes only execution state and the round record (the order's `tx_hash`, one `swap_mappings` row per swap); balances, `portfolio` and store reservations are byte-identical before and after.
  2. Only `APPROVAL`, `FILL` and `REVERT` with `settlement: FINAL` change balances and gas, through Keith's `advance_accounting`; `projection.balances` stays equal to the ledger so `ledger_from` accepts the next round.
  3. A terminal `FILL` or `REVERT` releases every remaining store reservation of its intent: USDT, BNB and `INCOMING:<token>` (A9). An `APPROVAL` releases the BNB it spent.
  4. Terminal-round attestation is emitted only when the last intent of a round reaches a terminal final fact.
- **B4 · ports published (I3, I4, I7, I5 interface).** `larp/ports.py` defines one validator per document: `EXECUTION_REQUEST` command payload (I3, including the gas top-up kind of I7), `ExecutionObservation.v1` for both boundaries (I4), and the round-log builder protocol (I5). The producer test calls the validator on real output: `RuntimePlanner` output for I3; the settlement reducer refuses any observation the I4 validator rejects.
- **B5 · regressions on PostgreSQL** (`tests/integration/test_settlement.py`):
  1. SELL (MANDATORY_REDUCTION round from the evidence pipeline harness): broadcast leaves balances and reservations unchanged and maps the hash; a final FILL updates balances by the accounting result, leaves **no reservation row** for the intent, and the round closes with the `tx_hash` in its audit event.
  2. BUY (a planned intent through `RuntimePlanner`): a final FILL and, separately, a final REVERT each leave no USDT, BNB or `INCOMING:` row; REVERT changes only gas.
  3. Replaying the same observation (same event ID, same bytes) is a no-op with the same receipt; the same event ID with changed bytes is refused.
  4. An observation for an intent the round did not plan, a provisional (`settlement` not `FINAL`) fill, and a fill with another wallet's ID are refused and change nothing.
- **B6 · nothing else breaks.** Full suite locally (PostgreSQL) and in Linux CI: every test that passed at the baseline still passes; new tests pass; the only failure allowed on PR #9 is C2 as stated in B2.

### 1.2 Results (2026-10-11)

Criteria committed and pushed at `aaad51b` before any covered code ran.

- **B1 · PASS.** `b583059` merges `origin/codex/engine-foundation` (`e8658ba`, which contains `a21d034`) by an ordinary merge; `aaad51b` adds the dated A11 annotations to plan.md D-03, D-05, D-11 and D-12, SKILL.md Q-03, GAP-51 and GAP-57, and restores the GAP-51 sentence `e8658ba` dropped. `git diff --check` clean.
- **B2 · PASS (C2 failing as intended).** PR #9 (`codex/integration-tests`): base merged by `5498a0e`; `5609b26` rewrites C3 for the current path (golden `AssessmentResult.v2` → `IssuerEvidenceState.v2` → `EvidenceContext.v1` → `decide()`, no `evidence_rejections`) and restates C4's expected-failure reason (raw wiring without `ContextBuilder`; a real BUY waits for DR-08; the item 10 acceptance suite replaces it). Linux CI [run 38153321721](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38153321721): **1 failed (C2), 597 passed, 1 xfailed (C4), 770 subtests, no skips**; both Terraform jobs green. C2 stays red until Keith re-captures the strategy fixture (prompt 07 item 8); PR #9 must not merge before then.
- **B3 · PASS.** PR #10 closed with a note naming what superseded it and what was ported. `7145ac1` adds `larp/integration/settlement.py` (`ExecutionBridge`, `settle`) for the `ledger_from` layout with I4's two boundaries, and the coordinator now refuses a terminal-round attestation unless every planned intent of the round has a terminal final fact.
- **B4 · PASS.** `larp/ports.py` (`7145ac1`): `validate_execution_request` (I3, incl. `purpose: GAS_TOPUP` for I7), `validate_execution_observation` (I4), `RoundLogBuilder` (I5), and `decimal_string`, now the single implementation behind `integration.runtime.decimal_amount`. Real `RuntimePlanner` output passes the I3 validator; the settlement reducer and bridge validate every observation with the I4 validator first.
- **B5 · PASS.** `tests/integration/test_settlement.py`, 11 tests + 4 subtests on PostgreSQL: SELL broadcast then fill (balances and reservations unchanged by the broadcast; no reservation row after the fill; ledger accepted by `ledger_from`; round closes with the tx hash in its audit event); BUY fill and BUY revert (no USDT, BNB or `INCOMING:` row left; revert charges only gas; the reverted swap is still logged); approval releases only its gas; a repeated observation returns the same receipt and the same event ID with changed bytes is refused; unplanned intent, provisional fill, other wallet and unknown swap hash are refused with the store unchanged; `NOT_SUBMITTED` releases without accounting.
- **B6 · PASS.** Local (Python 3.13.16, PostgreSQL 16) at `7145ac1`: **603 passed, 3 skipped (bubblewrap), 774 subtests** (baseline 592 + 11 new). The evidence integration demo regenerates byte-identically. Linux CI on `7145ac1` ([run 38153737901](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38153737901), manual dispatch, Python 3.12.15, PostgreSQL 14.24): **606 passed, 774 subtests, no skips**; `pip check`, the offline runtime demo, Docker build and offline smoke passed; both Terraform jobs green.

**Item 1 status:** complete for the runtime side. PR #9 stays open and red on C2 until Keith's fixture re-capture; the §1.3 interface points go to Isaac on Oct 12.

### 1.3 Open points from item 1 (for Isaac, interface day Oct 12)

1. **I4 additions proposed by the runtime side, need Isaac's agreement:** `round_terminal` on final facts (the execution owner's attestation that every command of the round is terminal, checked by the coordinator), `step` (`approve`/`swap`) on broadcast attempts, receipt evidence as `block_hash` + `canonical: true`, and a `NOT_SUBMITTED` terminal kind for an intent that never reached the chain (expired or refused before signing). Without `NOT_SUBMITTED`, a round whose command expires unsent can never close.
2. **I3:** the payload is Keith's intent plus `decision_id`, `expires_ms`, `amount` and an optional `purpose`; Isaac publishes the mapping to `Intent.validate`. A `GAS_TOPUP` intent passes I3 today, but `check_orders` (audit) and `Intent.validate` (execution) still refuse BNB; both narrow exceptions are item 3 and prompt 06.
3. **Logging of unsent intents:** a `NOT_SUBMITTED` intent still appears in the round's `orders`. Item 3 derives `orders` only from executed intents (DR-07).
4. **Gas top-up accounting:** `advance_accounting` has no BNB position, so a `GAS_TOPUP` fill cannot settle yet; Keith (prompt 07, B11) and Keegan (item 2) to agree the accounting form.

## 2. Items 3, 4, 5 and 8 — prospective criteria (written 2026-10-11, before running anything they cover)

Authorized by the user on 2026-10-11 ("continue with items 3, 4, 5 and 8 … push to a PR to engine foundation and ensure that CI passes each time"). Work is pushed to PR #13 (`codex/deploy-runtime` → `codex/engine-foundation`, draft); every push waits for green CI before the next step. Synthetic fixtures only: no secret, signing, wallet, organiser upload or live source.

### 2.1 Item 3 — official ai-seeds round logging (DR-07, GAP-46)

Interpretation recorded before building: prompt 09 says `orders` are "derived only from executed intents". The kit defines `orders` as what the code "finally decided to place this round (after risk checks …)" (F-99), and its reference code logs an aborted order **without** `tx_hash`, with the reason in `output` (participant-kit.md, conventions after L14). So `orders` lists the intents committed as execution requests: each broadcast swap carries its `tx_hash`, and an intent that never reached the chain is logged without one, with its reason in `output.aborted`. Proposals, rejected plans and approvals are never orders.

- **L1 · content.** `input` holds `version_id`, `round_id`, the decision IDs, the request, the complete assessment including its `model_io` (every model request and response and every tool call, so system prompt, tool definitions and context are in the log) and the policy input. `cot` is the assessment's provider reasoning summaries in order (`model_io.cot`) when a model ran. Otherwise it is an explicit statement beginning `No model call this round.` that names the deterministic path (Q-16, F-106 (a)). `output` holds status, errors, the plan and the policy output.
- **L2 · orders.** `orders` are the round's committed intents: BUY `amount` = USDT paid, SELL `amount` = tokens sold (A10). Every broadcast swap, including a reverted one, carries its `tx_hash`. An intent that ended `NOT_SUBMITTED` has no `tx_hash` and appears in `output.aborted` with its reason. A round with no committed intent logs `orders: []`. An approval never appears.
- **L3 · one log per round on every path.** Each of these closes with exactly one audit event with non-empty `input`/`cot`/`output`: hold; assessment unavailable; context unavailable; planner unavailable; plan invalid; commit rejected; interrupted round closed by recovery; executed round; gas top-up round.
- **L4 · gas top-up (I7, B11).** `check_orders` accepts `symbol: "BNB"` only in an event whose `round_kind` is `GAS_TOPUP`, and then only as exactly one BUY. That round's `cot` says it is a gas top-up. A BNB order in a trade round is refused at planning (`PLAN_INVALID`) and by `verify_event`. Events without `round_kind` keep their exact bytes (no change to existing records).
- **L5 · test rounds marked.** A coordinator constructed for development or rehearsal (`test_rounds=True`) puts `"example": true` in every log's `input` (kit convention). Without the flag nothing is added.
- **L6 · size limits.** A round whose log exceeds the protocol budget still closes with exactly one log (the existing deterministic fallback with the full record's hash) and commits no command.
- **L7 · delivery proof.** `delivery_status(run_id)` reports an event `DELIVERED` only when every one of its chunks is `ACK` with a stored acknowledgement. A lost ACK resends the same event ID and bytes and then reports `DELIVERED`. A 4xx response leaves the event `FAILED` (visible). An empty outbox reports zero pending as health only, and lists no event as delivered without ACK rows.
- **L8 · no fill without a log.** Every tx hash of a FILL or REVERT settled in a round is mapped to that round's audit event (`swap_owners`).

### 2.2 Item 4 — live replay (DR-19, IDEA-035 A2)

- **P1 · recorded ports.** `RecordedPorts` replays a `ContextBuilder` round from its journal record alone: market, calendar, health and series come from the round's recorded policy input, and no live port is called (the live ports raise if touched). A recorded `CONTEXT_UNAVAILABLE` round re-raises with the same recorded cause, so the replayed batch is identical.
- **P2 · MANDATORY_REDUCTION replay.** A MANDATORY_REDUCTION round with its execution command, reservations, broadcast and FILL observations (`ExecutionBridge` + `settle`) and its close replays into an empty store to the same verified head (the regression IDEA-035 A2 still lists).
- **P3 · a rehearsal day.** At least five rounds with a SHADOW adverse finding, a MANDATORY_REDUCTION round settled by observations, a context-failure round and holds, using ports whose answers change from round to round and which fail after the run, replay to the identical head with recorded ports only.
- **P4 · tampering is detected.** Changing one recorded market value in a copy of the journal makes the replayed head differ from the original, so `verify(anchored_head=…)` refuses it.

### 2.3 Item 5 — supervisor restart and autonomous HALT (DR-13, C5)

Design note: the supervisor restarts the same process on the same host only after systemd has ended the previous one (`KillMode=control-group`), so the restarted process keeps the run's owner epoch. Epoch takeover stays reserved for standby promotion, which remains disabled (GAP-02). No human action is part of restart or HALT (F-114, never-do #1).

- **H1 · restart incident and fixed version.** Process sessions are durable. A start after an unclean end commits exactly one `INCIDENT` journal event of kind `RESTART`, naming the previous session and the build. A clean restart commits none. A start whose build differs from the run's registered build is refused.
- **H2 · supervisor unit.** `deploy/systemd/larp-runtime.service` runs the release preflight before every start and restarts always with a fixed delay. It has no start limit that would leave the agent stopped, no manual step, and the same hardening as the archive unit. A test checks the directives.
- **H3 · autonomous HALT triggers.** A guard evaluated before each round commits a `HALT` journal event, with an incident reason, on any of: journal integrity failure; a decision clock behind the last committed decision time; an audit delivery deadline breach; N consecutive failed rounds (N from configuration).
- **H4 · HALT effect.** While halted, every round still runs and is logged (no orders, error `HALTED:<reason>`). No command or reservation is committed, and `store.command()` refuses every pending command (the signing gate).
- **H5 · automatic clearing only.** Integrity and clock HALTs are latched for the run. A delivery-deadline HALT clears automatically once no overdue event remains unacknowledged. A repeated-failure HALT clears after the configured number of consecutive successful rounds. Each clear is a journal event. Nothing clears by elapsed time alone or by hand.
- **H6 · replay.** HALT, clear and incident events replay to the same head.

### 2.4 Item 8 — release, manifest, services and deviations (DR-18, GAP-62; draft due Oct 19)

- **R1 · services list (F-61).** `config/release/services.v1.json` lists every principal model and data service the build may call (provider, purpose, scope, terms reference, status). The B8 assessor model is listed as pending with both candidates and the deterministic fallback. A validator refuses missing fields.
- **R2 · deviations register.** `config/release/deviations.v1.json` has one row per deviation from the submitted proposal decided so far (IDEA-035 §2–§5, IDEA-037, plan.md D-08/D-09/D-11 and GAP-51). Each row has the declared text quoted verbatim from `docs/proposal/proposal_answers.md`, the v1.0 behaviour, the reason and evidence IDs. A test checks every quote against the proposal file and every evidence ID against the repository. Rows from IDEA-039–041 are added when those records exist.
- **R3 · one source.** plan.md §6.5 shows the register as rendered by `tools/render_deviations.py`; a test fails on drift.
- **R4 · manifest.** `build_manifest` embeds the services list and the deviations register with their hashes. Release preflight refuses a manifest whose register or services list is missing or invalid.
- **R5 · version event before trading.** `Coordinator.register_version` commits a `VERSION_REGISTERED` journal event (build ID, manifest, services and deviations hashes). A coordinator constructed with `require_version=True` commits no execution command unless the registered build equals its `version_id`. Replay supports the event.

**Amendment to H3 (2026-10-11, before any item 5 test ran):** a journal that fails verification cannot accept a commit, so an **integrity failure quarantines the run** (every write and every signature fenced) and is reported through the health check, instead of committing a `HALT` event. The other three triggers commit `HALT` events as written.

### 2.5 Results

Criteria pushed at `5b80e7e` (CI green, [run 38154687328](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38154687328)) before any covered code ran.

**Item 3 — PASS** at `55d8222`, Linux CI green on `0551587` (that commit plus a no-change merge of the base after PR #12 merged; [run 38156600082](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38156600082)). Local: 621 passed, 3 skipped (bubblewrap), 774 subtests.
- L1–L7: `tests/audit/test_round_logging.py`, 18 tests on PostgreSQL. Every path (hold, assessment unavailable, context unavailable, planner unavailable, plan invalid incl. BNB in a trade round, commit rejected, interrupted, executed, gas top-up, mixed top-up refused) closes with exactly one log. `cot` is the providers' summaries in order, "Model called; the provider returned no reasoning summary …", or "No model call this round. …". Test rounds are marked only when asked. An oversize round logs once and places nothing. An event is DELIVERED only after every chunk is ACKed, a lost ACK resends identical bytes, and a 400 leaves it FAILED with an empty outbox.
- L2 and L8: `tests/integration/test_settlement.py`. An unsent intent is logged without a tx hash, with `output.aborted[0].reason == "QUOTE_EXPIRED"`, and a settled swap's hash is owned by its round and decision in `swap_owners`.
- Code: `larp/audit/protocol.py` (`round_kind`, BNB only in GAS_TOPUP rounds; trade-round envelopes unchanged), `larp/runtime/coordinator.py` (`round_kind`, `round_cot`, decision IDs and `example` in `input`, `output.aborted`), `larp/audit/delivery.py` (`delivery_status`), `larp/integration/settlement.py` (aborted orders), `larp/ports.py` (optional `reason` on NOT_SUBMITTED), `larp/runtime/replay.py` (`test_rounds` passthrough).

**Item 4 — PASS** at `cd97ed3`, Linux CI green ([run 38156955583](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38156955583)). `larp/integration/replay.py` (`RecordedPorts`, `replay_live`) and `builder_for` in `larp/runtime/replay.py`. `tests/integration/test_live_replay.py`, 4 tests on PostgreSQL:
- P2: a MANDATORY_REDUCTION round with broadcast, FILL and close replays to the same head. Control: the same replay through the live ports, now dead, raises `IntegrityError`.
- P1, P3: a five-round day (clean hold, adverse mandatory reduction settled by observations, a context failure caused by a market port outage, two holds), with a market port whose prices change every call, replays to the identical head after every live port is made to raise. A recorded failure re-raises with its recorded cause name.
- P4: one recorded market price changed in a copy of the journal is refused (`IntegrityError`).
- Local: 625 passed, 3 skipped, 774 subtests.

**Item 5 — PASS** at `ecc5687`, Linux CI green ([run 38157258842](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38157258842)). Local: 635 passed, 3 skipped, 774 subtests.
- Code: `larp/runtime/supervision.py` (`Sessions`, `Guard`), `larp/runtime/service.py` (`Service`, exit codes), `deploy/systemd/larp-runtime.service`, `migrations/007_process_sessions.sql`. The coordinator records `round_health` and `last_decision_ms` with each round and, while halted, skips policy and planner and logs `HALTED:<reasons>`. `store.command()` refuses every command while halted. Replay recommits `INCIDENT`/`HALT`/`HALT_CLEARED` as recorded facts.
- `tests/runtime/test_supervision.py`, 10 tests:
  - H1: a clean restart records no incident; a crash followed by two restarts records exactly one RESTART incident naming the crashed session; another build or a reused session ID is refused.
  - H2: the unit has `Restart=always`, `RestartSec=10`, no start limit, `KillMode=control-group`, `RestartPreventExitStatus=2 3`, preflight before start, and every hardening directive of the archive unit.
  - H3, H4: a clock behind the last decision halts. The signing gate refuses a command it accepted before the HALT, and a halted BUY round logs once with no new command. The clock HALT stays latched while a later delivery HALT is added.
  - H3, H5: a delivery-deadline HALT is raised and clears once the log is ACKed. Three failed rounds raise REPEATED_FAILURES, which clears after two successful (halted, logged) rounds.
  - H3 (amended): a tampered projection quarantines the run, and the service then exits with code 3 without running a round.
  - H6: incident, HALT and clear events replay to the same head.
- Not yet shown, due on the host: the kill-and-restart drill (Gate A) and the HALT drill (Gate B). The runtime database role and its grants (including `process_sessions`) belong to item 7 (provisioning). `larp.runtime.service run` exits with code 2 (not integrated) until item 10 supplies the round driver.

**Item 8 — PASS** at `0378c47`, Linux CI green ([run 38157822943](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38157822943)). Local: 641 passed, 3 skipped, 777 subtests. Draft due Oct 19; final at the Oct 26 freeze.
- R1: `config/release/services.v1.json` lists six services: Web3 Open API, ai-seeds event log, SEC EDGAR, the official free sources, the assessor model (PENDING_DECISION: Claude or ChatGPT, deterministic fallback) and AWS hosting (PROVISIONING).
- R2: `config/release/deviations.v1.json` has 20 rows, DEV-01–DEV-20. Each declared text is checked as a verbatim quote of the proposal and every evidence ID is resolved in the repository. 17 rows are decided; 3 are OPEN (DEV-18 standby, DEV-19 assessor model, DEV-20 event planner). Sources: D-08/D-09/D-11, GAP-51, IDEA-035, IDEA-037 and IDEA-009 §F.
- R3: plan.md §6.5 is generated by `tools/render_deviations.py --write`; `--check` and a test fail on drift.
- R4: `build_manifest` embeds `release_register` (both file hashes, row counts, open rows). `verify_release` refuses a manifest without it, a register changed after the build, or a missing file.
- R5: `Coordinator.register_version` commits `VERSION_REGISTERED` (build, manifest, services and deviations hashes). With `require_version=True`, a BUY round before the event commits no command (`VERSION_NOT_REGISTERED`) and one after it does. Another build's manifest is refused, and a process session for another build is refused. The event replays to the same head.
- Tests: `tests/runtime/test_release_register.py` (6). The fixture in `tests/runtime/test_operations.py` now carries a register.
- Remaining for DR-18: add IDEA-039–041 rows when those records exist, decide the three OPEN rows, and produce the rehearsal build's manifest on the host (Gate A).

## 3. Remaining work that needs no other PR — prospective criteria (written 2026-10-11, before running anything they cover)

Authorized by the user on 2026-10-11 ("go ahead with item 2 and the live-mode refusals; complete every task that can be done without the other PRs"). Same process as §2: each push to PR #13 waits for green CI. Synthetic fixtures only.

**Not possible without others, and not attempted:** Isaac's execution service and its I3 → W04 mapping (prompt 06); the four-way integration (item 10); anything needing the AWS account, secrets or a host (items 6 and 7 drills, Terraform apply, restore drill on RDS, alert delivery, rehearsals, the host rehearsal of the wallet switch).

### 3.1 Item 2 — execution store side (DR-04, DR-05)
- **E1 · W04 store on PostgreSQL.** `PostgresExecutionStore` implements `larp.execution.Store`:
  - compare-and-swap on the execution revision;
  - the owner epoch and guard version fence every commit;
  - one active execution per wallet and chain across runs;
  - state and event commit in one transaction;
  - signed bytes live only in a separate signature registry, never in state or events.
- **E2 · Isaac's suite as the contract.** Isaac's W04 suite (`tests/test_w04_execution.py::ExecutionTests`) runs unchanged against PostgreSQL through a subclass that swaps only the storage fixture. This includes:
  - crashes before and after signing and after broadcast;
  - storage failures;
  - a cold restart after each transition;
  - the cross-run wallet barrier;
  - "never sends twice".
- **E3 · command consumption.** `claim_command` hands a pending `EXECUTION_REQUEST` to exactly one W04 execution key. It applies the same fencing as `command()`: current owner epoch, current state version, not halted, not expired. A second claim with another key is refused, and the same claim again is idempotent.

### 3.2 Live-mode refusals and the final-wallet switch (item 9, DR-17; prompt 09 acceptance)
- **W1 · refusals.** `check_live_start` (modes `dev` and `live`) refuses to start, naming the reason but never a secret value, when:
  - any port is a fake or synthetic fixture;
  - a required secret is missing or empty;
  - a wallet key is present on the runtime host;
  - `AI_SEEDS_ADDRESS`, the configured wallet and the run's wallet disagree;
  - the `.ai-seeds/` or nonce directory belongs to another wallet.

  `offline` and `paper` modes are not affected.
- **W2 · per-wallet records.** Each `.ai-seeds/` and nonce directory carries a wallet marker. A directory marked for another wallet is refused.
- **W3 · switch procedure.** `switch_wallet` refuses when:
  - the old run still has open rounds, reservations or pending commands;
  - the old run holds any token;
  - the new wallet equals the old one;
  - a directory would be shared.

  Otherwise it opens a fresh run for the new wallet (quarantined until takeover) with its own directories, and returns a switch record (old run, final head, new run). It is rehearsed with a throwaway configuration in tests. The host rehearsal stays at Gate C.
- **W4 · the service applies W1.** `larp.runtime.service run` in `dev`/`live` mode exits with code 1 before opening a session when `check_live_start` refuses.

### 3.3 Item 6 — hourly anchoring, repository side (DR-15; IDEA-036 criteria 1, 3, 5, 6)
- **A1 · verify every anchor.** `verify_anchors` checks each anchor's sequence and head against the verified journal. Altering one journal event after it was anchored makes verification fail (IDEA-036 #3).
- **A2 · stale restore.** A restore whose journal is behind the latest anchor is rejected as stale (IDEA-036 #5, local part).
- **A3 · no secrets.** Anchor payloads contain only identifiers, times, sequence, head and epoch (IDEA-036 #6).
- **A4 · retention floor.** Terraform refuses an archive retention shorter than 81 days, which is what reaches 2026-12-31 from the earliest anchor (IDEA-036 #1). A `terraform test` run checks the refusal. Cadence (#2), storage-enforced immutability (#4) and the RDS restore drill wait for the host.

### 3.4 Item 7 — database roles, repository side (DR-16)
- **G1 · least-privilege roles.** `deploy/postgres/roles.sql` adds `larp_runtime` (coordinator and journal), `larp_execution` (the W04 store) and `larp_signer` (signature registry only).
- **G2 · roles tested.** A PostgreSQL test applies the script, then shows:
  - a round, its settlement and its close run as `larp_runtime`;
  - the W04 store runs as `larp_execution`;
  - each role is refused outside its grants: the runtime cannot touch signatures, and execution cannot write the journal.

### 3.5 Item 10 — repository-side acceptance and runbook (DR-20 partial, DR-22 draft)
- **T1 · acceptance day.** `tests/integration/test_acceptance.py` runs one synthetic day through every real component on this branch:
  - evidence assessor with fake EDGAR;
  - strategy and independent risk;
  - coordinator with the version event and `require_version`;
  - scripted I4 execution facts, settlement and close;
  - round-log delivery with ACK proof;
  - guard;
  - anchor and `verify_anchors`;
  - replay with recorded ports to the same head.

  Isaac's execution service replaces the scripted facts at integration.
- **T2 · runbook draft.** `docs/build/runbook.md` covers start, automatic restart, HALT and its automatic clearing, restore, version event and final-wallet switch, each tied to code and tests. The on-call rota is marked as owed by the team (GAP-37).
