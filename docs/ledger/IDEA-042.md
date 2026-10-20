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

### 3.6 Results (2026-10-11)

Criteria pushed at `4694785` (CI green, [run 38158943819](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38158943819)) before any covered code ran.

- **E1–E3 · PASS** at `fa8c069`, Linux CI green ([run 38159355897](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38159355897)). `larp/storage/execution_store.py` and migration 008.
  - Isaac's 43 W04 tests run unchanged against PostgreSQL through `PostgresW04` (`tests/integration/test_execution_store.py`), together with 4 new tests: 47 passed + 42 subtests. This covers crashes before and after signing and after broadcast, storage faults, cold restarts after each transition, the cross-run wallet barrier and "never sends twice".
  - `claim_command` binds one command to one execution key. It refuses another key, a stale owner, an expired command and a halted run.
- **W1–W4 · PASS** at `fa8c069`, same CI run. `larp/runtime/live.py`; `tests/runtime/test_live_start.py` (7).
  - W1: every refusal is shown, and no refusal text contains the secret value. `offline` and `paper` are unaffected.
  - W2: a directory marked for another wallet, or holding unmarked records, is refused.
  - W3: the switch is refused while the old run has an open round, reservations or a pending command, and while it is not flat. It is also refused for an invalid wallet or a shared directory. The throwaway-configuration rehearsal opens a quarantined live run for the new wallet and returns the old head.
  - W4: the service refuses before opening a session.
- **A1–A4, G1–G2 · PASS** at `fc7a759`, Linux CI green incl. Terraform ([run 38159712464](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38159712464)). `tests/runtime/test_anchors_roles.py` (6).
  - A1: both hourly anchors verify, and a self-consistent rewrite of round 1 is refused against them.
  - A2: a restore behind the latest anchor is refused as stale.
  - A3: anchor fields are identifiers and hashes only, and an extra field is refused.
  - A4: the `archive_retention_reaches_end_of_2026` Terraform test refuses 80 days.
  - G1–G2: as `larp_runtime`, a round, its settlement and its close run, while signatures, executions, the run's `initial` and deleting events are refused. As `larp_execution`, claims and the W04 store work, while journal writes, signatures and projection writes are refused. As `larp_signer`, only the registry is reachable.
  - Found and fixed on the way: backups and restores did not include the new tables. They now cover process sessions and the execution store, with the event sequence reset after a restore.
- **T1, T2 · PASS** at `f1fae29`, Linux CI green.
  - T1: `tests/integration/test_acceptance.py`, one day covering the version event; a clean hold; an Item 4.02 mandatory reduction claimed by one execution, settled by I4 facts and closed with no reservation left; both logs DELIVERED; the guard idle; the anchor verified; and a replay with every live port disabled reproducing the head.
  - T2: `docs/build/runbook.md` drafted (start, restart, HALT, restore, switch), with the host drills and the on-call rota marked as owed.
  - Found while writing the runbook: a quarantined run (for example after a restore) with an unclean session would have made the service fail and restart every 10 s. The service now exits with code 3 before opening a session, and systemd does not restart on 3 (`test_service_does_not_start_on_a_quarantined_run`).
- Local full suite at `f1fae29`: 703 passed, 3 skipped (bubblewrap), 829 subtests.

**What remains in prompt 09 after §3:**
- Isaac's execution service and its I3 → W04 mapping (prompt 06).
- The four-way integration and the shadow-mode path with real read-only adapters.
- Every host step: provisioning, alerts, restore and anchor drills on AWS, restart and HALT drills, the rehearsal-build manifest, the switch rehearsal, rehearsals and Gate reviews.
- The team's inputs: B9, secrets, rota, and the three OPEN deviation rows.

## 4. Integration round 1: reconciling with the three owner branches. Prospective criteria (written 2026-10-11, before any change below)

Authorized by the user on 2026-10-11 ("Continue", after the owner branches appeared). The owner branches at the time of writing: Isaac `codex/deploy-execution` `28613da` (draft PR #14), Keith `codex/deploy-strategy` `ab3adc1` (no PR; IDEA-040 says its tests were NOT RUN), Yao Zhu `codex/deploy-evidence` `92e4745` (PR #15). Base `codex/engine-foundation` `bd3f69a`.

**Diagnosis only, not a result.** Before these criteria were written, an exploratory local merge of all three into this branch (`c1271a6`) was run to see what breaks. It is reported as diagnosis and is not counted towards any criterion below. No textual conflicts. Full suite on PostgreSQL 16: 834 passed, 9 failed, 4 skipped:
- `tests/execution/test_postgres_execution.py` (5): my migration 008 already creates an `execution_signatures` table with other columns, so Isaac's `CREATE TABLE IF NOT EXISTS` keeps the wrong one. Two stores for the same thing: mine (`PostgresExecutionStore`, §3.1 E1) and Isaac's `larp/execution_live/store.py`, which his service uses and which IDEA-039 asks me to adopt in migrations, roles and backup. **Mine to fix (X1, X2).**
- `tests/execution/test_settlement.py` (2): Keith's `advance_accounting` now requires a `receipt` object (`tx_hash`, `block_hash`, `block_number`, `canonical`, `finality: FINAL`, `chain_id: 56`, `status`) for `EXECUTION_RECONCILER` facts; Isaac's receipt facts do not carry it. **Isaac ↔ Keith (I4); both owners must agree (brief §Interfaces).**
- `tests/strategy/test_live_profiles.py::test_live_cost_cap_still_blocks_without_double_counting_impact`: fails on Keith's branch alone. **Keith.**
- `tests/strategy/test_live_profiles.py::test_c2_fixture_matches_current_golden_trace_without_reconstruction`: Yao Zhu's branch regenerated the golden traces (new `review` field); Keith's fixture still holds the old request. **Keith re-captures** (same root cause as PR #9's C2).

Other mismatches found by reading the branches (not by tests):
- **I7 naming.** Isaac and Keith both mark a top-up with the intent field `kind: "GAS_TOP_UP"` (absent or `BSTOCK_TRADE` = a trade); Keith's top-up round is `GAS_TOP_UP` too. My `ports.py`, `check_orders` and coordinator use a separate field `purpose: "GAS_TOPUP"`. **Mine to fix (X3).**
- **I7 decimals.** Keith's top-up intent has `receive_decimals: 6`; Isaac's `map_command` requires 18 for native BNB. **Isaac ↔ Keith.**
- **I8 shape.** Yao Zhu publishes `config/intelligence/red_flags.v1.json` and `red_flag_directives(record, profile)`; Keith's consumer proposes a different `RedFlagPredicates.v1` registry in `context.red_flag_predicates`. **Keith ↔ Yao Zhu.**
- **I5.** IDEA-041 §6.3 asks Keith whether `larp.strategy.assessments.consume` (v1 only) is on the live path. **Keith.**

### 4.1 Criteria for this branch (L1)
- **X1 · one execution store.** Migration 008 creates exactly the tables and index of Isaac's proposed schema (`larp/execution_live/store.py:SCHEMA` at `28613da`: `execution_records`, `execution_wallet_barrier`, `execution_journal`, `execution_signatures`, `execution_observations`), same DDL, nothing else. Migration 008 has never been applied outside disposable test databases (it is not on `codex/engine-foundation`), so it is replaced rather than superseded by a 009. My duplicate is removed: `larp/storage/execution_store.py`, its tables, `commands.execution_key` and `PostgresStore.claim_command` (Isaac's service consumes commands through `PostgresStore.command`). A test shows that, on a tree that has Isaac's module, running his `SCHEMA` after the migrations changes nothing (same columns, types, nullability, keys and indexes); on this branch alone it is skipped. **Pass on the trial merge:** Isaac's `tests/execution/test_postgres_execution.py` passes against the migrated tables.
- **X2 · roles and backup for that store.** `deploy/postgres/roles.sql`:
  - `larp_execution`: SELECT, INSERT, UPDATE on `execution_records`; SELECT, INSERT on `execution_journal` and `execution_observations`; SELECT on `execution_signatures`; the existing command and journal reads.
  - `larp_signer`: SELECT, INSERT on `execution_signatures` only, plus SELECT on `runs` and UPDATE of `runs.clock_ms` (Isaac's fencing locks the run row).
  - `larp_runtime`: SELECT on `execution_journal` and `execution_observations`; nothing on `execution_records` or `execution_signatures`.
  - `larp_archive`: SELECT on `execution_journal` and `execution_observations` only.
  - No role has UPDATE or DELETE on `execution_journal`, `execution_signatures` or `execution_observations`.
  A PostgreSQL test shows each grant and each refusal. `larp/storage/backup.py` covers the four tables, and a test shows an export and restore round trip keeps their rows byte for byte.
- **X3 · I3/I7 naming agreed with the other two owners.** `validate_execution_request` reads the intent's `kind` (`BSTOCK_TRADE` when absent, or `GAS_TOP_UP`) and refuses `purpose`; the coordinator's round kind and `check_orders` use `GAS_TOP_UP`. `GAS_TOPUP` appears nowhere in code, and a test shows it is refused.
- **X4 · signer dependencies.** New `deploy/requirements-signer.lock` (runtime lock plus `eth-account==0.14.0` and its 22 transitive pins, all taken unchanged from `requirements.lock`), included by `deploy/requirements-test.lock` so CI runs the signer tests instead of skipping them. `pip check` passes in CI. The runtime image lock is unchanged.
- **X5 · requested shared edits.** Applied in the same change as the code, each worded to say what is built and what is still unproven:
  - `docs/LEDGER.md` rows for IDEA-039, IDEA-040 and IDEA-041.
  - `docs/INCOMPLETE_WORK.md` notes requested in IDEA-039 §5, IDEA-040 ("Requested shared edits") and IDEA-041 §6.1. No backlog item is removed: none is complete.
  - New deviation rows only where the register has none yet (IDEA-040 items 1–7 and IDEA-041 §6.1 (a)–(d) are checked against DEV-01..DEV-20 one by one, and the mapping is recorded in §4.3).
- **X6 · cross-owner findings handed over.** Every "Isaac ↔ Keith", "Keith ↔ Yao Zhu" and "Keith" item above is listed in §4.3 with its owner. I do not change another owner's paths.
- **X7 · re-run the trial merge** (the same owner SHAs) after X1–X4 are pushed and green. **Pass:** the 5 PostgreSQL execution failures are gone; every remaining failure is one of the cross-owner items above, and none is in a runtime-owned path. The integration branch `codex/deploy-integration` and its PR into `codex/engine-foundation` wait until each owner PR has passed CI and its reviewer (brief §Integration); this round does not create them.

Process as before: these criteria are pushed to PR #13 and CI is green before any change they cover; each later push also waits for green CI.

### 4.2 Results (2026-10-12)
Criteria pushed at `29e12fb` (CI green, [run 38186263133](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38186263133)) before any change below. Code at `b1795b9`, Linux CI green incl. Terraform ([run 38186751374](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38186751374)). Local PostgreSQL 16 run at `b1795b9`: 659 passed, 4 skipped, 806 subtests. Synthetic fixtures only.
- **X1 · PASS.** `migrations/008_execution_store.sql` is Isaac's DDL unchanged. `larp/storage/execution_store.py`, `tests/integration/test_execution_store.py`, `commands.execution_key` and `PostgresStore.claim_command` are removed; the acceptance day takes its command through `PostgresStore.command`. `tests/storage/test_execution_schema.py`: the four tables and the barrier exist and `execution_key` is gone; the equivalence test is skipped on this branch alone and **passed on the trial merge** (X7), where it drops the four tables, recreates them from Isaac's `SCHEMA` and compares columns, constraints and indexes. **§3.1 E1–E3 are superseded:** my W04 store and command claims no longer exist; Isaac's own PostgreSQL tests are now the store's evidence.
- **X2 · PASS, with one amendment.** Roles as written for `larp_execution`, `larp_signer` and `larp_runtime`, each grant and refusal tested in `tests/runtime/test_anchors_roles.py` (G2 tests rewritten). **Amendment:** the criterion gave `larp_archive` SELECT on the journal and observations only. That was wrong: the archive role takes the daily backup, which exports every table `larp.storage.backup` restores (`larp/runtime/maintenance.py`), and the first run failed `test_archive_role_can_operate_without_mutating_financial_state` and the new archive test. `larp_archive` now has SELECT on all four tables (as it had on my earlier schema) and no write on any; tested. Signed bytes therefore reach the encrypted, write-once backup archive, as they did before. Backup round trip of all four tables byte for byte: `test_x2_backup_round_trip_keeps_the_execution_rows`.
- **X3 · PASS.** `validate_execution_request` reads `kind` (`BSTOCK_TRADE` default, `GAS_TOP_UP`) and refuses `purpose`; round kind `GAS_TOP_UP` in the coordinator and `check_orders`. `GAS_TOPUP` is absent from `larp/` and `config/`; `tests/integration/test_settlement.py` names it only to show it is refused (3 subtests).
- **X4 · PASS.** `deploy/requirements-signer.lock`: the runtime lock plus 22 pins (`eth-account==0.14.0` and 21 transitive dependencies; `typing_extensions` comes from the runtime lock), every line present unchanged in `requirements.lock`. Included by `deploy/requirements-test.lock`; CI `pip check` green. On the trial merge Isaac's signer tests ran instead of skipping.
- **X5 · PASS.** Applied in this change: LEDGER rows IDEA-039/040/041; INCOMPLETE_WORK notes on GAP-13, 23, 24, 28, 49, 50, 51, 57, 62, 64, 65, 67 (none removed: none is complete); deviation DEV-21 and the mapping in §4.3. Isaac asked to keep his reservation link: kept, with the status updated. EXP-005 is unchanged (inconclusive): no new capability evidence.
- **X6 · PASS.** §4.3.
- **CI note.** The results commit `4477f6d` turned CI red: `test_r2_rows_quote_the_proposal_and_cite_existing_evidence` assumed the register's last row is an OPEN one, and DEV-21 (decided) is now last. I had not re-run the suite after the register change. Fixed by having the test pick an OPEN row explicitly; full suite green locally before the fix was pushed.
- **X7 · PASS.** Trial merge of `b1795b9` + `28613da` + `ab3adc1` + `92e4745` (local only, not pushed): no textual conflicts; 796 passed, 4 failed, 4 skipped (opt-in recorded responses and bubblewrap only), 969 subtests. Isaac's five PostgreSQL execution tests pass. The 4 failures are exactly the cross-owner items in §4.3 (I4 receipt shape ×2, Keith's cost-cap test, C2 fixture); none is in a runtime-owned path.

### 4.3 Handover: what other owners need to settle, and the deviation mapping
| # | Item | Owner(s) | Evidence |
|---|---|---|---|
| H-1 | **I4 receipt shape.** Keith's `advance_accounting` requires a `receipt` object (`tx_hash`, `block_hash`, `block_number`, `canonical`, `finality: FINAL`, `chain_id: 56`, `status`) on `EXECUTION_RECONCILER` facts; Isaac's receipt facts do not carry it. Consumer's validator is the contract (brief); both must agree. My `validate_execution_observation` follows whatever they agree. | Isaac + Keith | `tests/execution/test_settlement.py` ×2 on the trial merge |
| H-2 | **I7 BNB decimals.** Keith's top-up intent `receive_decimals: 6`; Isaac's `map_command` requires 18 for native BNB. | Isaac + Keith | Read from both branches |
| H-3 | **Keith's branch is red alone:** `test_live_cost_cap_still_blocks_without_double_counting_impact`. IDEA-040 says its tests were NOT RUN. | Keith | `ab3adc1` alone |
| H-4 | **C2 fixture stale** against Yao Zhu's regenerated golden traces (`review` field). Same root cause as PR #9's C2. | Keith | trial merge |
| H-5 | **I8 shape.** Yao Zhu publishes `red_flags.v1.json` + `red_flag_directives`; Keith proposes `RedFlagPredicates.v1` in `context.red_flag_predicates`. | Keith + Yao Zhu | IDEA-040 I8, IDEA-041 §6.3 |
| H-6 | **I5 `consume`.** Is `larp.strategy.assessments.consume` (v1 only) on the live path? | Keith | IDEA-041 §6.3 |
| H-7 | Keith's branch has no PR and Yao Zhu's and Isaac's PRs have not passed review: the integration branch and its PR wait (brief §Integration). | Keith, reviewers | — |

Runtime wiring still mine, after the owner PRs are integrated: `model_trace` as the round's `cot` and `build_request(job=...)` (IDEA-041 §6.1); `red_flags.v1.json` in the release manifest; I2 series, I6 profiles in preflight, `PortfolioState.mode=LIVE` and the I7 resource round (IDEA-040); the execution service's command loop and observation publication into settlement (IDEA-039).

Deviation requests checked against DEV-01..DEV-20:
- IDEA-040: (1) equal weight → DEV-03; (2) 25%/90% trims → DEV-04; (3) price impact → DEV-05; (4) token US-session series → DEV-06; (5) gas resource rounds → **new DEV-21**; (6) red-flag classes → DEV-07; (7) end-of-run cut and flatten → DEV-07. Keith's extra details (free gas BNB counted in the uninvested share; no substitution of underlying or other token prices) are added to DEV-04 and DEV-06 when his code is integrated and run.
- IDEA-041: (a) verified item-section text → DEV-07 ("verified"); (b) no red-flag class for 6-K filers → added to DEV-07 at integration; (c) Claude as assessor → DEV-19 (OPEN); (d) three tools → DEV-08.

### 4.4 Reviews of the owner branches (2026-10-12)
Each review was run independently on the owner's head and its main blocking claims re-checked against the code before posting.
- **PR #14 (Isaac, `28613da`): changes requested** ([review](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/14)).
  - Blocking:
    - B1: a SELL whose USDT output is not a multiple of 10^12 chain units cannot settle.
    - B2: a mistyped mnemonic is printed in the signer's exception.
    - B3: fencing on `runs.version` invalidates every authorized or signed attempt after any runtime commit or takeover, and nothing can release it.
  - Should-fix: S1–S5. Plus the integration items H-1, H-2 and the I1/I2 field mismatch.
  - **Open decision (Isaac + Keegan):** B3's rule. Proposed: a dedicated execution authority version that changes only on takeover, HALT or reauthorization, with a defined recovery path for AUTHORIZED and never-broadcast SIGNED_DURABLE attempts. Keegan adds the column and migration once it is agreed.
- **PR #15 (Yao Zhu, `92e4745`): comment, not a block** (Keith is the designated reviewer) ([review](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/15)). Core safety properties hold. To fix before RF1 is enabled or the bake-off is run:
  - an 8-K/A of an old event yields a fresh Class 1 EXIT;
  - the Claude structured-output schema is likely refused (not checked live);
  - raw bytes are stored after parsing;
  - the Class 1 text match is brittle.
- **Keith's branch (`ab3adc1`, no PR): needs changes before the PR** ([comment on PR #13](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/13#issuecomment-6116747515)). Blocking:
  - a gas top-up pre-empts mandatory sales;
  - the Class 1 exit is not treated as mandatory;
  - LIVE validation needs fields Isaac's port does not emit, which can block the end-of-run flatten;
  - the failing cost-cap test is a test bug (fix given).

### 4.5 Fixes for Yao Zhu's review of PR #13 (review 5486736446, 2026-10-12). Prospective criteria
Each of the ten comments was checked against the code at `092d9c5` before writing these; all ten hold.
- **V1 · HALT does not clear itself.** A round blocked only by `REPEATED_FAILURES` runs policy and planner as a *probe*. Its plan is discarded: no orders, commands, reservations, jobs, risk-state or policy-state change. Probe failures keep the HALT and probe successes clear it. A round blocked for any other reason (CLOCK, DELIVERY_DEADLINE, VERSION_NOT_REGISTERED) leaves the failure and success counts unchanged. Tests:
  - with a still-broken planner the HALT never clears;
  - with a fixed planner it clears after `clear_after` probes;
  - a probe round commits no command;
  - clock-halted rounds do not count.
- **V2 · Missing proposal file.** `load_register` raises ContractError when the register's `proposal` file is missing, instead of skipping the verbatim-quote check. Tested.
- **V3 · Gas top-up rounds always close.** A GAS_TOP_UP round may log zero orders (a top-up that placed nothing, e.g. rejected at commit or audit fallback), but never anything other than its single BNB buy. Test: a top-up round rejected at commit closes with its log written.
- **V4 · No restart loop on refusals.** `LiveStartRefused` and contract refusals (configuration, release, session build or reused ID) exit with code 4. The unit has `RestartPreventExitStatus=2 3 4`. Other failures stay 1 (restart). Tests on the exit codes and the unit. **Not fixed here:** delivering secrets to the runtime process (the unit reads none, and no loader from Secrets Manager exists). Recorded as an open item for the host step.
- **V5 · PR description** updated to the current state (Isaac's store adopted; no `claim_command`).
- **V6 · `switch_wallet` can pass.** The pending-execution check uses the execution service's `execution_records` (no non-terminal record for the old run) instead of `commands.status`, which nothing updates. Test without any owner-only UPDATE.
- **V7 · Delivery status in constant queries.** `delivery_status` uses one documents query, one grouped chunks query and the pending count, whatever the number of events, with the same results. Tested.
- **V8 · Backups never hold signed bytes.**
  - `larp_archive` gets column-level SELECT on `execution_signatures` without `signed`.
  - The export writes a fixed redaction marker for `signed`.
  - After a restore, a lookup of a redacted row fails closed (the registry digest no longer matches), and the restored run is quarantined as before.
  - Tests: the archive role cannot read `signed`; no backup contains the signed bytes; a restored registry lookup refuses.
- **V9 · Retention through all of Dec 31.** Terraform refuses `archive_retention_days` below 82; the test value 81 is refused.
- **V10 · One set of constants.** `larp/ports.py` and `larp/runtime/live.py` import `SYMBOLS`, `TX` and `ADDRESS` from `larp.audit.protocol` instead of copying them.

Pass: every test above, the full suite on PostgreSQL, and CI green. Each thread gets a reply naming the commit.

#### 4.5 Results (2026-10-12)
Criteria pushed at `e05a577` (CI green, [run 38207095863](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38207095863)) before any change below. Fixes at `6228b84`, Linux CI green incl. Terraform ([run 38207800824](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38207800824)). Local PostgreSQL 16 run: 665 passed, 4 skipped, 808 subtests. The V1 and V3 tests were also run against the old coordinator and protocol code, and all three fail there, so they catch the reported bugs.
- **V1 · PASS.** `larp/runtime/coordinator.py` (probe; `record_round_health(counted=...)`); `test_h3_h5_v1_repeated_failures_halt_clears_only_when_the_planner_works`, `test_v1_a_round_blocked_by_the_clock_does_not_count`. Runbook §3 updated.
- **V2 · PASS.** `larp/runtime/register.py`; `test_v2_a_register_without_its_proposal_is_refused`.
- **V3 · PASS.** `check_orders` accepts zero orders in a GAS_TOP_UP round; `test_v3_a_rejected_gas_top_up_round_still_closes_and_logs`.
- **V4 · PASS for the exit code; secrets delivery still OPEN.**
  - Exit 4 covers `LiveStartRefused` and start-phase contract refusals. Storage `Conflict` and `IntegrityError`, and anything raised inside a round, still exit 1 and restart.
  - The unit has `RestartPreventExitStatus=2 3 4`. Tests: `test_v4_*` and the unit test.
  - **Open (Keegan, host step):** nothing delivers the runtime secrets into the process (no `EnvironmentFile`, no Secrets Manager loader). Runbook §1. Its review thread is left open.
- **V5 · PASS.** PR #13 description updated.
- **V6 · PASS.** `switch_wallet` checks `execution_records`; the W3 test no longer updates `commands` as the owner.
- **V7 · PASS.** Three queries whatever the number of events; `test_v7_status_queries_do_not_grow_with_events`.
- **V8 · PASS.**
  - Column-level grant without `signed`, the redaction marker in the export, and the catalogue-based column list.
  - Tests: `test_g2_v8_archive_backs_up_execution_tables_without_signed_bytes`, `test_x2_v8_backup_round_trip_keeps_the_execution_rows_but_never_signed_bytes`. The second checks Isaac's `lookup` refusing a restored row once his module is merged (skipped until then).
  - Depends on the PR #14 B3 recovery rule for never-broadcast signed attempts after a restore. Its review thread is left open for the reviewer.
- **V9 · PASS.** `archive_retention_days >= 82`; Terraform test with 81 is refused (CI).
- **V10 · PASS.** Shared constants imported from `larp.audit.protocol`.

### 4.6 Secrets delivery to the runtime process (the open half of review comment V4). Prospective criteria (2026-10-12)
Authorized by the user on 2026-10-12 ("fix all the comments on the PR"). Finding behind it: nothing delivered the runtime secrets into the process. Checking that also showed `check_live_start` required `AI_SEEDS_SECRET` in the coordinator. The infrastructure design (`docs/build/runtime-infrastructure.md`, Secrets row) gives the audit secret to the uploader only, and only `larp/audit/delivery.py` uses it. Terraform also granted the primary host no secret at all.
- **S1 · Loader.** `larp/runtime/secrets.py` reads one Secrets Manager secret (one `GetSecretValue`). Its `SecretString` must be a JSON object of non-empty strings.
  - It returns only the runtime's names.
  - A wallet key or the audit secret in it is refused, as is malformed content.
  - No secret value appears in any exception text, log line or repr.
  - Tested with a fake client.
- **S2 · Never the environment.** The service takes secrets only from the loader, given the non-secret `runtime_secret_id` in its configuration, and never from `os.environ`.
  - A `dev` or `live` start without a secret ID is refused (exit 4).
  - `offline` and `paper` load nothing.
  - Tested, including a live check that ignores matching environment variables.
- **S3 · Least privilege.** The runtime needs `AI_SEEDS_ADDRESS`, `BINANCE_API_KEY` and `BINANCE_SECRET_KEY`. `AI_SEEDS_SECRET` (uploader only) is refused on the runtime host, like the wallet keys (signer only). The W1 tests are updated.
- **S4 · Terraform.** A `runtime` secret (metadata only; values are provisioned outside Terraform) is readable only by the primary and standby hosts. A Terraform test asserts the secret exists. CI validate and plan pass.

Pass: tests above, full suite, CI green; runbook §1 updated; the V4 review thread replied to and resolved.

#### 4.6 Results (2026-10-12)
Criteria pushed at `fa5bf74` (CI green, [run 38215968402](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38215968402)) before any change below.
- Code at `08ebb80`. Its Terraform test failed in CI: `safe_defaults` still asserted three service secrets, and I had not searched the tests for that count. Fixed at `1a388a8`, Linux CI green incl. Terraform ([run 38216749291](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38216749291)).
- Local PostgreSQL 16 run: 670 passed, 4 skipped, 808 subtests.

Results:
- **S1 · PASS.** `larp/runtime/credentials.py` (named so it cannot shadow the standard `secrets` module); `tests/runtime/test_credentials.py`. A provider error whose text carries a value surfaces only its type.
- **S2 · PASS.** `larp/runtime/service.py` no longer imports `os`, and a test checks that. `runtime_secrets` loads nothing for `offline` and `paper`, and refuses `dev` and `live` without a secret ID or region (exit 4). It returns the stored values even when the environment holds different ones.
- **S3 · PASS.** `RUNTIME_SECRETS` is `AI_SEEDS_ADDRESS`, `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`. `AI_SEEDS_SECRET` is refused on the runtime host (`UPLOADER_ONLY`). W1 is updated. **This supersedes §3.2 W1's list**, which required the audit secret in the runtime.
- **S4 · PASS.** `deploy/aws/hosts.tf`: `local.secret_readers` maps each secret to its only readers, with `runtime` read by primary and standby. The `runtime_secret_exists` test passes and `safe_defaults` counts four secrets.
- Runbook §1 and §6 (activation) updated. The V4 review thread is closed; review comment V8 also had no remaining work in this PR.

## 4.7 2026-10-12 combined PR remediation (IDEA-043) — prospective criteria

User authorizes review/fix all open PRs, ordinary target merges including PR11 to main, then a separate system-testing branch. Repository merge authorization does not activate Gate A/B/C. Integrate reviewed evidence/strategy/execution/test branches without rewriting history; actual I4 facts must reach the canonical settlement reducer with receipt provenance and committed round binding retained. Gas top-up reservations retain resource kind/valuation. Broadcast and final observations use actual validator; approval reverts map to their own broadcast identity, not a swap hash. No stale receipt can borrow current authority. Full suite with PostgreSQL, Linux CI and combined synthetic day/replay/ACK checks required. Record remaining host, economic, model and source gates; no production credentials or transactions.

4.7 additional prospective acceptance: exercise real published red-flag directives through both policy and the independent no-policy risk path; a Class 1 exit remains mandatory and precedes replenishment/buys. Wire the actual execution service, PostgreSQL execution store and receipt producer through coordinator settlement, then prove reservation release, order mapping, durable ACKs and same-head replay. Synthetic venue/chain/signer fixtures only; no live release.

4.7 release inspection finding: release_files includes JSON configuration but omits the assessor's deployed .txt prompts (G-03/G-12), and the runtime Dockerfile. Prospective pass: manifest includes both when present, changing only either invalidates verify_release; synthetic temp trees only. Add these files to the existing manifest inventory; do not relax startup/version gates.

## RG-01 — rehearsal gate packet (2026-10-19), prospective criteria

User asks to create/work on rehearsal gates. Prepare a repository-only operator
packet for C09/C10 in PR133. Account-owner details are resolved per the user's
2026-10-19 update; no host access or signed acceptance is inferred.

Pass criteria before verification:
1. Map every DR13–22 requirement and DR04/05 crash/reconciliation prerequisite
   to an ordered gate, observation, explicit failure condition and evidence.
2. Separate ready preparation, unsigned observation, signed drills and final
   acceptance; use existing adopted bounds, never invent numerical acceptance.
3. Supply reusable per-drill and daily records; all actual outcomes start NOT_RUN.
4. Reference existing supported commands/APIs; flag missing host-specific fault
   injection plans rather than inventing CLI options or unsafe generic mutations.
5. Check changed Markdown links and mapping coverage after pushing this packet;
   no cloud, receiver, signer, wallet or live trading operations. C09/C10 and
   all partially completed GAPs remain open pending measured host evidence.

Results: NOT_RUN at registration. Operational status: NOT_RUN; packet preparation
cannot approve a policy, qualify a release, or pass Gate A/B/C.

RG-01 repository verification (2026-10-19): PASS at `6e0373b` for all7 local
packet links, RG1–10 and DR13–22 mapping, three actual API definitions, existing
operations CLI choices/options and tracker/runbook/backlog links. Initial literal
DR coverage check failed on combined `DR18/20` formatting; references were made
explicit and the check passed. `git diff --check` PASS. Documentation-only change;
no runtime tests, cloud operations, fault injections or live drills run. Missing
host-specific harnesses/procedures are explicitly BLOCKED until pinned/reviewed.
C09/C10 and operational Gate A/B/C outcomes remain open/NOT_RUN.

## RG-02 — offline rehearsal evidence index (2026-10-19), prospective criteria

Next repository slice: implement a stdlib-only local packet initializer/checker
for RG-01. It makes no AWS, RPC, database, signer or receiver calls and cannot
approve a rehearsal or enable execution. Tool/code additions require their own
future release qualification; prior release evidence does not cover these bytes.

Prospective acceptance:
- Initialization creates a new packet with ten NOT_RUN gates, never overwrites.
- Checking requires exact source/bundle/manifest/profile/config/run/wallet binding;
  duplicate/missing gates and malformed inputs fail closed without raw input output.
- Reviewed evidence claims require UTC ordered times, distinct attributed operator
  and reviewer, procedure/approval refs, complete gate-specific criterion results,
  and actual local artifact hashes. Missing/refused/synthetic evidence cannot be
  reported as observed host evidence. Evidence completeness is never Gate C PASS.
- Artifact reads stay within an explicit sanitized evidence directory: refuse
  absolute/traversal/symlink/special-file paths and bound file/input sizes. No raw
  paths, provider URLs, input content or exception strings in reports.
- Synthetic tests exercise tamper, wrong identity, missing criteria/reviews,
  duplicate keys/gates, path escape, symlinks, malformed timestamps and overwrite
  refusal. Commit/push implementation before execution; targeted tests suffice
  for this independent offline utility. Live outcomes remain NOT_RUN.

RG-02 results at `0ca9621262cd32cc405a568c9e70a7303e4749da`: PASS,
`python -m unittest tests.runtime.test_rehearsal_evidence -q`, Python3.12.14,
14 tests,0 skips,0.043s. Initial11 tests passed at0628f62; added CLI completeness/
refusal distinctions and special-file input checks passed at the final source.
PASS all7 local packet links and `git diff --check`. Source was pushed before
execution. Tests use synthetic claims/artifacts only and explicitly retain
host_results_verified=false, gate_c_accepted=false, signing_enabled=false even
for complete packet indexes. No application path changed and no host/runtime
suite or new original release qualification was run. All live C09/C10 drill
results remain NOT_RUN. A01 wording and the handoff now acknowledge the user's
resolved account-owner details while retaining actual access/evidence requirements.

## RG-02-RV01 — Keegan review of PR188 (2026-10-19), criteria before the fix

Review of `510c3c0` found one defect against RG-02's "malformed inputs fail
closed without raw input output": a deeply nested JSON packet (well under the
1MiB bound) raises `RecursionError`, which `main` does not catch, so the CLI
prints a Python traceback and exits 1 (the "incomplete" code) instead of the
fixed `PACKET_REFUSED` report with exit 2. Operator/reviewer independence also
compares raw strings, so `"Isaac"` and `" isaac"` count as different people.

Pass criteria, written before the fix:
- RV01-1: a nested packet or identity file raises `Refused` from `load`, and
  the CLI prints only `PACKET_REFUSED` and exits 2 (red test pushed first).
- RV01-2: operator and reviewer that differ only by case or surrounding
  whitespace report `INDEPENDENT_REVIEW_REQUIRED`.
- RV01-3: all existing RG-02 tests still pass; no other behaviour changes.

RG-02-RV01 results at `fa04d5428aa7900c9d238989756d061d1d9bd226`: **PASS** RV01-1..3. Red first at `ddc9df0`
(1 failure, 1 error); after the fix `python -m unittest
tests.runtime.test_rehearsal_evidence -q` on Python 3.12, Linux: 16 tests,
0 skips. A 200,000-deep packet from the CLI now prints only `PACKET_REFUSED`
and exits 2. Not changed, recorded for the operator: the checker refuses an
evidence root with any symlinked ancestor, so on macOS a root under `/tmp` or
`/var/folders` (both behind symlinks) is refused, and so are these synthetic
tests' temporary directories. Keep the sanitized export under the home
directory, which is not a symlink. RG-02's own scope is unchanged:
`gate_c_accepted`, `signing_enabled` and `host_results_verified` stay false
and every live drill result stays NOT_RUN.

## RG-02-RV02 — PR188 integration review (2026-10-19), prospective

Review current PR188 merged with its checklist base. Native macOS synthetic
verification exposed the documented symlink-ancestor limitation in the test
fixture itself: tempfile returns a path through /var, so ordinary positive
cases never reach validation. Keep the checker strict; canonicalize only the
fresh synthetic fixture directory. Pass criteria before the fix: all16 tests
pass on macOS, including explicit symlink refusals and all CLI exit codes;
add a symlinked-ancestor regression; packet links and whitespace pass. No host
or release acceptance is transferred. GitHub run39240046615 never started:
its annotation reports failed account payments/spending limit, not test failure.

RG-02-RV02 results: PASS on native macOS/Python3.9.6,17 tests/0 skips,
including new symlinked-ancestor refusal. Canonical fixture paths fix only test
portability; production path refusal is unchanged. All7 packet local links and
`git diff --check` PASS. Reviewed the DR mapping, CLI/API references and complete
changed docs; no additional blocker. Application/runtime/config source is
unchanged from the current checklist base. Hosted CI remains billing-blocked;
new tools still need future release qualification and all live drills stay open.

## LD21-H — drill harnesses and procedures (2026-10-20)

Prepared for the approved operator (all drills NOT_RUN):
[LD21_DRILL_PROCEDURES.md](../build/LD21_DRILL_PROCEDURES.md) pins D1 restart, D2 DELIVERY_AGE HALT/clear,
D3 anchors, D4 restore/alert and D5 throwaway wallet switch, with pass/fail criteria written before any run.
Two harnesses close RG-01's "pinned invocation harness" blockers for RG4 and RG6:
`tools/deploy/drill_verify_anchors.py` (read-only `verify_anchors` over downloaded Anchor.v2 files, with hourly
coverage) and `tools/deploy/drill_wallet_switch.py` (read-only preflight that agrees with `switch_wallet`, and a
confirmed switch step). PostgreSQL tests: 3 + 6 passed. RG8 replay harness and signer-boundary crash injection
remain open.
