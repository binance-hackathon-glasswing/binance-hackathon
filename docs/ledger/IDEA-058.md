# IDEA-058 — Gate A configuration assembly and startup qualification

- 2026-10-15 renumbered (Claude Code session, at Keegan's request): this entry was first written as IDEA-057, which PR #88 (QuoteCostSummary producer) had already claimed five minutes earlier. It is now IDEA-058 (freed by closing PR #89). Commit messages before the rename still say IDEA-057.

- Date / owner: 2026-10-16 SGT / Keegan with Codex.
- Status: repository implementation and local Linux qualification PASS at `5e4e974`; PR review/integration and hosted Gate A remain open.
- Request: work on remaining readiness tasks and remove Gate A functional blockers. The user is concurrently building the quote-cost summary / live strategy profile tool; do not duplicate or modify that work.
- Base: current main `e410e49` (PR81), fetched 2026-10-16. The earlier assessment used stale local `c829fae`; its missing-driver/activation/calendar findings are superseded by IDEA-050/054 and the review merges. No hosted state is inferred from Git.
- Scope: assemble and validate a strictly unsigned dev-shadow deployment from measured, pinned inputs, supply missing input producers where possible, and verify the production composition with synthetic external transports and disposable PostgreSQL. Never fabricate measured costs, balances, exchange identities, terms captures or hosted acceptance. Preserve signed/live refusals and all gates.
- Dependencies: the user owns QuoteCostSummary/profile generation; team owns SEC contact, approval of operational parameters, AWS-connected deployment, and real measurements. AWS spending follows AWS_RUNBOOK; no host starts or wallet transaction is implied by this coding work.

## Prospective acceptance (before implementation or execution)

| ID | Pass criterion |
|---|---|
| GA01 | A shadow preparation path consumes explicit infrastructure, reviewed LIVE profile, initial state and public token metadata, pins exact bytes and validates all five issuer IDs separately from their observed underlying tickers. Wrong/missing/duplicate contracts, tickers or scales refuse; no unverified share ratio becomes verified. |
| GA02 | It emits only a dev-shadow runtime (no signing), uploader/operations configuration and the pinned input files into ignored deployment storage; names all missing prerequisites; refuses overwrite, fixture profiles, wrong wallet/run, invalid state and incompatible inputs. No secrets are read or printed. |
| GA03 | Operational shadow settings are explicit and scoped to unsigned development only. Signed/final settings remain gated. No silent development-mode fallback in a live/signed run. The user's settings answer is recorded before enabling proposed values. |
| GA04 | A pushed-code read-only input capture can supply public token metadata and the wallet's actual balances without signing, sending transactions or uploading round logs. Artifacts remain outside tracked files; unknown/unrepresentable holdings and malformed responses refuse initialization. Provenance and hashes accompany the state. |
| GA05 | Qualification checks identify configuration/manifest/input/startup blockers without starting services, fetching secrets or authorizing a run. Host-only checks (receiver ACK, routes, IAM/TLS, time, restart, alarms, anchoring, 24h ingest) remain separately NOT RUN until evidenced. |
| GA06 | Exercise the assembled runtime through init/activate, real build_driver, one unsigned round, settlement/round log and restart/replay where local PostgreSQL is available; synthetic transports and credentials only. Negative tests prove service/live execution cannot use shadow-only settings. |
| GA07 | Run focused regressions and the full feasible suite from committed/pushed code. Record exact SHA, environment, skips, failures and remaining host/Gate B work. Update ledger/backlog/runbooks without closing partially complete GAPs. |

## Findings and results

- 2026-10-16 user decision: use existing bounded evidence defaults explicitly for unsigned dev-shadow operation, 15-minute cadence and 5-minute UTC day-roll window. Deployment will use Yao Zhu's AWS environment. SEC contact not supplied; it remains a required host input. Signed/final parameters stay unadopted. Implementation uses a separate `shadow` evidence mode, never fills the pending `live` values.

- 2026-10-16: `git fetch origin` succeeded after sandbox elevation; branch `codex/gate-a-readiness-20261016` starts at current main. The current tree already contains the driver and `init`/`activate`; Gate A's active blockers are deployment inputs and host evidence. Python 3.14 is on PATH; Linux/PostgreSQL availability still to be checked. No application code or tests run in this session yet.

### GA-V01 (2026-10-16)

- Implementation/criteria pushed before execution (`0e47430`, then composition test `ab00c52`). New WSL Ubuntu 22.04 / Python 3.12.15 environment with `deploy/requirements-test.lock`; disposable PostgreSQL database. Initial Windows-mounted test run: 56 passed / 3 failures caused by CRLF shell files and mount permissions. A clean Linux scratch checkout of the pushed commit resolves these without changing scripts or permissions assertions: 59 passed / 59 subtests across Gate A, driver, complete driver service and deployment pre-setup tests. `ab00c52` focused Gate A: 11 passed / 24 subtests; actual prepared inputs initialize and activate a dev run, compose the driver, run and restart, write test-round logs and receive durable fake-receiver ACKs. No external calls or real signing/upload.
- Full suite at `ab00c52`: 1513 passed / 22 failed / 4 skipped / 2099 passed subtests. Twenty failures are fixture admin-role privileges (normal local role lacks CREATE ROLE), one is the expected new public evidence-mode setting absent from the unit test's list, and golden-trace subtest failures are caused by adding shadow values to the shared development configuration hash. Corrective implementation: a separate `intelligence.shadow.v1.json` preserves original development/live bytes and hashes; the exact non-secret unit setting contract is updated, and the next full run uses a dedicated disposable PostgreSQL cluster whose fixture admin is superuser only in that cluster. No golden trace is regenerated.
- NYSE source verified directly on 2026-10-16: https://www.nyse.com/trade/hours-calendars lists all ten 2026 holidays, Nov 27/Dec 24 13:00 ET closes, and 09:30–16:00 core hours, matching IDEA-054. Exact HTML retained outside Git at `C:/Users/keega/.codex/visualizations/2026/10/15/01a1404f-da28-76f1-b94e-5db43e2044ff/nyse-calendar-20261016.html`, SHA-256 `79602f7be5a8f1d39c2b1cac4dd02c4c07f18cf9f92d70602834069154719bad`. The pinned calendar bytes are unchanged. Owner review stays separate.
- Local `.env` contains only the Web3 API key names, no dev wallet address or SEC contact. Values were not printed. Real wallet capture/SEC ingestion cannot be supplied from this checkout without the team's public address/contact or local setup by Yao Zhu. No AWS CLI/profile is available here; deployment stays on his AWS-connected environment.
- User confirmation 2026-10-16: Yao Zhu will set both the dev wallet public address and SEC User-Agent contact locally on deployment day. These are external handoff inputs, not an unanswered chat question.

### GA-R01: actual dev-shadow replay (2026-10-16; before repair)

- At `fbc27e3`, golden/host-unit and dedicated-cluster role checks pass after UTF-8 fixture correction, but GA06's newly added exact replay fails with `Deterministic replay diverged`. `replay()` correctly initializes an offline target; `ContextBuilder` overwrites its portfolio context mode from the target run, replacing the original DEV mode with OFFLINE and changing snapshot/batch identities. Existing offline-origin replay tests did not cover this. Repair acceptance: replay uses the recorded portfolio-context mode only inside its copied context builder; the target run remains offline and cannot gain signing authority. A full dev-shadow journal, including version registration and activation, must reproduce the same head without Web3 calls. Do not relax the head comparison, mutate audit events or activate the replay target.

### GA-V02 final qualification (2026-10-16)

- Tested application/test tree: `5e4e974` (pushed before execution). Clean Linux scratch checkout in `/var/tmp/larp-gate-a-checkout`, Ubuntu 22.04 WSL, Python 3.12.15, exact `deploy/requirements-test.lock`, PostgreSQL **14.24** in a separate loopback-only cluster on port 55436; UTF-8 disposable database `larp_test_gate_a_utf8`. `pip check`: no broken requirements.
- **Full suite PASS:** 1534 passed, 4 skipped, 2147 subtests passed, 191.49 s. Skips: one opt-in recorded-market artifact check and three opt-in real-systemd tests.
- **Real systemd PASS separately:** 3 passed, 5 subtests passed, 3.99 s, `LARP_TEST_SYSTEMD=1`. The normal Linux user could not run the fixture's `sudo -n`; the authorized WSL test administrator ran the same unchanged tests, which create/clean only uniquely named `larp-review-*` inert fixture units. No production LARP unit started.
- **Focused Gate A PASS:** 12 passed / 24 subtests, including all-five issuer binding, wrong/duplicate/altered metadata, balance identity/coverage and raw units, unknown holdings refusal, stale/future inputs, non-overwrite, no signer/execution configs, separate approved shadow parameters, signed/final/development-fallback refusals, and manifest-bound ingestion scope.
- **GA06 PASS:** prepared LIVE rehearsal-profile inputs -> quarantined init -> reviewed activation/version registration -> actual `build_driver` with real component code -> unsigned test round -> restart -> stored fake-receiver chunk/event ACKs -> exact journal replay. Context and planner remain available, balances stay unchanged, no reservation/execution record remains, every order lacks a tx hash, and the signing-command claim is trapped. Replay makes no Web3 call, reproduces the exact head and leaves its target run in **offline** mode. All external transports, filings, credentials and receiver ACKs here are synthetic; these are engineering proofs, not hosted or economic evidence.
- No golden trace was regenerated; original `intelligence.v1.json` bytes match main. Shadow settings are in their own versioned file. An unrelated token cannot override eligible-token decimals in starting-state assembly.
- Draft review: [PR #87](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/87), targeting main. Head `d2e967c` changes documentation only after tested `5e4e974`. Its Actions run `38770752764` reports all four jobs failed in 11 seconds and produced no verified bundle; Code Review diagnostics returned HTTP 404, so the precise new failure reason is unverified (earlier main runs were billing-blocked). Exact-release CI/bundle qualification remains open; local PASS is not substituted for it. The PR is attached to this chat.
- Test cleanup: stopped only the task's `/var/tmp/larp-gate-a-pgdata` cluster; removed the task-created database `larp_test_gate_a_20261016` and its temporary local DB role. Existing PostgreSQL service left running. Linux scratch checkout/venv and synthetic reports are retained outside the repository; no task temp files remain in the repo.
- Evidence outside Git: `C:/Users/keega/.codex/visualizations/2026/10/15/01a1404f-da28-76f1-b94e-5db43e2044ff/gate-a-full-5e4e974.xml`, SHA-256 `7409e155c645db896ab6a7d21867b008d9013a7832eb4202ca51aa0db1bf0806`; `gate-a-systemd-5e4e974.xml` in the same directory, SHA-256 `f0e060778572e16fc1d99db6acf3a7e7cb96dd4167491b9455d760c0b5ea2148`.

| Criterion | Result / remaining evidence |
|---|---|
| GA01 | PASS on synthetic attributed capture fixtures; real public captures run locally by Yao Zhu with the supplied tool |
| GA02 | PASS; exact pins, state/identity/scale validation and ignored exclusive-write tests |
| GA03 | PASS; explicit user decision, separate shadow config and negative signed/final scope tests |
| GA04 | PASS on recorded-shape synthetic inputs; real wallet/address/balance capture remains deployment input |
| GA05 | PASS for honest preparation report and input refusals; all host checks stay NOT RUN |
| GA06 | PASS, including exact dev-shadow replay and offline target |
| GA07 | PASS for feasible full Linux and separate systemd tests, docs and backlog; PR/CI integration and hosted acceptance remain open |

## Remaining work and ownership

1. User: complete the concurrent measured `QuoteCostSummary.v1`/LIVE rehearsal-profile tool and review its output. No costs, gas estimates or funding were fabricated in this change.
2. Yao Zhu (confirmed by the user): set the public dev wallet address and SEC contact locally; capture actual wallet/metadata inputs; capture missing SEC terms, transfer every retained terms artifact to the host and preserve its hash. See `docs/build/GATE_A.md`.
3. Yao Zhu + Keegan: reviewed saved AWS plan/spend, start/provision primary, migrate/grant roles, install the reviewed bundle/inputs and bind the manifest, run init/activate and host-only qualification (real receiver ACK, 24h ingestion, restart, hourly anchoring, IAM/TLS, routes, time sync, alarm delivery). No AWS CLI/profile is available in this Windows session and no AWS action occurred.
4. Keegan + reviewer: review/integrate this branch; obtain exact-release CI/bundle evidence. Repository Actions were already unable to start on main (PR81 run 38757589514); do not substitute this local suite for a built/verified deployment bundle.
5. Isaac/Keegan/Keith: existing Gate B decoder/route/provider proof, signer isolation/version binding and provisioning, first BNB/top-ups, recorded-real candles/cost/profile evidence, logged dev approve/swap and hosted crash/HALT/restore/shadow-day replay remain open. Gate C and signed rehearsal are not claimed.

No whole GAP line is closed by this change. No secret, populated environment file, wallet key, private dataset or raw source artifact was added to Git. No signing, broadcast, official round-log upload, AWS provisioning or organiser contact occurred.

## Checks ported from PR #89 (2026-10-15, Claude Code session at Keegan's request; criteria recorded before the tests)

PR #89 (initial-state builder and issuers map, stacked on #84) is closed in favour of this PR. Of its checks, these were not yet here and are ported:

| ID | Check |
|---|---|
| GA07 | Issuers: every pair `issuer_map` returns must also pass the evidence contract's own rule, `larp.integration.contract._issuer_matches(…, source_id='BINANCE_WEB3')`. A pair that the local ticker check accepts but that rule refuses is refused here too, so real filings are never later refused as `WRONG_ISSUER`. |
| GA08 | Initial state self-checks before it is pinned: `ledger_from(initial_projection(state), [])` passes, and gate_b DR-06's shape holds (`schema`, run and wallet identity, `bnb_decimals` 18, `mode` dev, every unit a non-negative integer). A state that fails either is refused with its reason. |
| GA09 | No BNB is not a refusal for the shadow run, which needs no gas. But `preparation-report.json` lists `FIRST_BNB (Q-03)` in `missing_inputs` whenever the captured native balance is 0, because Gate B (DR-06) refuses an unfunded wallet. |

Not ported, because they need #84's finalized-block reader (`larp/execution_live/balances.py`), which this branch does not have: the pending-nonce refusal and a block-bound balance read. The kit's balance endpoint has no block identity. Follow-up after #84 merges: capture balances with `read_balances` and refuse while latest ≠ pending.

### GA07–GA09 results (2026-10-15)

- **Order of commits:** renumbering `d123272`; criteria `5a3bc9f`; red tests (3 failing for the predicted reasons: issuer rule not consulted, no self-check function, no `FIRST_BNB` entry); port `1c3edca`.
- **Mutations.** Each was reverted, and each was caught: issuer rule not consulted; self-check not called; no `ledger_from` check; wei not required; no `FIRST_BNB` flag.
- **Full suite.** Python 3.12.3 venv from `deploy/requirements-test.lock`, PostgreSQL 14.24 (the CI image's digest), bubblewrap installed.
  - Before (`ef71126`): 1533 passed, 5 skipped, 2147 subtests.
  - After (`1c3edca`): **1536 passed, 5 skipped, 2152 subtests** (+3 tests: this change only).
  - `tests/runtime/test_gate_a.py` with the database: 15 passed, including GA06's PostgreSQL composition.
- Mirror CI: not yet run on this head.

| ID | Result | Evidence |
|---|---|---|
| GA07 | PASS | `PortedFromPr89.test_ga07_*` |
| GA08 | PASS | `PortedFromPr89.test_ga08_*` |
| GA09 | PASS | `PortedFromPr89.test_ga09_*` |

### GA10: integration-branch base and #84's balance settings (2026-10-15, criteria recorded before the fix)

#87 is retargeted from `main` to `codex/system-testing-20261012` (merge `7812c5c`), which now includes #84 (IDEA-055). #84 requires `balance_rpc_url` and `balance_rpc_source_id` for a `dev` start, and the assembled config has neither, so GA06 fails on the merged tree with `Missing balance-check settings` (observed before any fix).

| ID | Check |
|---|---|
| GA10 | `prepare(…, balance_rpc_url=…, balance_rpc_source_id=…)` writes both into `runtime.json` `driver`, keeping the example's interval and max age. Without them, `preparation-report.json` lists `BALANCE_RPC` in `missing_inputs` and the values stay null, so the runtime still refuses a `dev` start (IDEA-055 intent). A non-HTTPS URL is refused. `tools/deploy/prepare_shadow.py` takes `--balance-rpc-url` and `--balance-rpc-source-id`. GA06 passes with fixture values: the real `build_driver` builds the balance check, and the round, restart and replay still hold. |

### GA10 results (2026-10-16)

- **Order of commits:** merge of `codex/system-testing-20261012` at `7a8a246` (with #84) as `7812c5c`; the `LEDGER.md` conflict was resolved by keeping the newer IDEA-049-D row plus the IDEA-055 and IDEA-058 rows. GA10 red tests next (13 failing on `prepare()`'s missing parameters; GA06 had already failed on the merged tree with `Missing balance-check settings`). Fix: `1008037`.
- **GA06** keeps #84's balance check offline: `Rpc.call` is patched to raise `DependencyUnavailable`, so the check journals `SKIPPED:RPC_UNAVAILABLE` and replay recommits it without network.
- **Mutations.** Each was reverted, and each was caught: settings not written; `BALANCE_RPC` not reported.
- **Full suite.** Python 3.12.3 venv from `deploy/requirements-test.lock`, PostgreSQL 16.15 (the 14.24 container was lost when the session container was recycled), bubblewrap installed.
  - Base `7a8a246`: 1546 passed, 7 skipped, 2147 subtests.
  - This branch at `1008037`: **1562 passed, 7 skipped, 2176 subtests**, 0 failed.
  - `tests/runtime/test_gate_a.py`: 16 passed.
- **PR #87 is retargeted from `main` to `codex/system-testing-20261012`.** `main` added only the PR #81 promotion docs (3 commits), which this branch now carries.
- Mirror CI: not yet run on this head.

### GA11: no starting state while a wallet transaction is in flight (pre-registered 2026-10-16)

This is the last follow-up from #89, possible now that #84 is merged. The kit's balance endpoint has no block identity. If a transaction from the wallet is still pending, or is mined but not finalized, the captured balances can change after the starting state is pinned. That would give the ledger a wrong opening position.

**Design.**
- `capture_inputs(client, wallet, rpc=None)`: when the manifested balance RPC is given, it also captures `ChainBalances.v1` with #84's `read_balances` (finalized block), plus the wallet nonce at that finalized block.
- The CLI `capture` takes `--balance-rpc-url` and `--balance-rpc-source-id`.
- The capture is checked before it is written, and checked again by `prepare()`.

**Pass criteria.**
- **GA11a:** `prepare()` refuses if the finalized nonce, the `latest` nonce and the `pending` nonce are not all equal. This covers a transaction pending or not yet finalized. `capture_inputs` refuses the same before writing anything.
- **GA11b:** `prepare()` refuses if the chain capture's finalized balances differ from the kit's balances for native BNB, USDT or any of the five bStocks. It also refuses a chain capture for another wallet or chain, or one older than five minutes (or future-dated) at `now`.
- **GA11c:** a capture without a chain read is not refused for the shadow run, but `preparation-report.json` lists `CHAIN_BALANCE_CAPTURE`. This matches GA09's FIRST_BNB pattern; Gate B would need it.
- **GA11d:** the RPC calls are only #84's allowlisted read methods. There is no `eth_sendRawTransaction` and no signing.
- **GA11e:** each refusal names its cause, and a mutation of each check is caught. The full suite passes with no new failures against `1008037` (1562 passed, 7 skipped).

### GA11 results (2026-10-16)

- **Order of commits:** criteria in `86a46a3`, red tests in `d584a72` (9 failing: `chain_capture` missing), fix in `b2496d4`.
- **GA11a–d: PASS.**
  - A pending nonce, or one not yet finalized, refuses at capture and at `prepare()`, with "in flight".
  - BNB, USDT or bStock balances that differ from the kit refuse with "differ".
  - A capture for another wallet or chain refuses, as does one that is stale or future-dated.
  - A capture without a chain read is reported as `CHAIN_BALANCE_CAPTURE`.
  - The RPC calls are #84's allowlisted read methods only.
  - The capture CLI passes the RPC through, and on refusal it writes nothing and exits 4.
- **GA11e mutations:** 7, each reverted and each caught:
  - nonce check;
  - balance comparison;
  - wallet check;
  - age check;
  - report entry;
  - capture-time check;
  - prepare-time check.
- **Full suite** (PostgreSQL 16.15, Python 3.12.3): **1569 passed, 7 skipped, 2181 subtests, 0 failed**. That is +7 against `1008037`'s 1562. `tests/runtime/test_gate_a.py`: 23 passed.
- **Docs:** `docs/build/GATE_A.md` capture and prepare steps now pass `--balance-rpc-url` / `--balance-rpc-source-id`.
- **Scope:** an incoming transfer between the finalized block and the kit read also refuses through the balance comparison, and a fresh capture clears it. This makes no claim about the Gate B balance check, which is #84's `BalanceCheck` at runtime.
- **Mirror CI:** not yet run on this head.

### GA12: the chain read is mandatory when the balance RPC is configured (pre-registered 2026-10-16)

Until now, GA11c only reported a missing chain read. When `prepare()` is given the balance RPC, a capture without the chain read now has no excuse.

- **GA12a:** with `balance_rpc_url` given, `prepare()` refuses a capture that has no chain read ("chain balance capture required").
- **GA12b:** the chain capture records the RPC's `source_id`. `prepare()` refuses if it differs from `balance_rpc_source_id` ("another RPC source"). This is the same binding Gate B's DR-03 applies to its own probe.
- **GA12c:** without `balance_rpc_url`, nothing changes. The report lists `BALANCE_RPC` and `CHAIN_BALANCE_CAPTURE`, and #84's runtime refuses to start anyway.
- **GA12d:** each new check's mutation is caught. The full suite passes with no new failures against `b2496d4` (1569 passed, 7 skipped).

### GA12 results and the Gate B check (2026-10-16)

- **Order of commits:** criteria in `2688c6d`, red tests in `8686410` (2 failing), fix in `aa89f31`. The fix commit also moves the shared test fixture to a capture with the chain read, because every assembly with an RPC now requires one; the tests of the no-chain path pass one explicitly. Disclosed here because those fixture edits land with the fix, not with the red tests.
- **GA12a–c: PASS.**
  - With the RPC configured, a capture without the chain read refuses ("chain balance capture required").
  - A chain read from another RPC source refuses ("another RPC source").
  - Without the RPC, both `BALANCE_RPC` and `CHAIN_BALANCE_CAPTURE` are reported.
- **GA12d mutations:** 3, each caught:
  - mandatory check;
  - source binding;
  - `source_id` not recorded.
- **Full suite:** **1572 passed, 7 skipped, 2181 subtests, 0 failed**. That is +3 against `b2496d4`. `test_gate_a.py`: 26 passed.

**Gate B (`larp/execution_live/gate_b.py`), read 2026-10-16, no change made.**

Gate B does not read Gate A's capture. `probe_chain` takes its own finalized-block snapshot, and DR-03 refuses it unless the snapshot meets all of these:
- It is fresh and from the configured `rpc_source_id`.
- `latest_nonce == pending_nonce` (blocker `PENDING_NONCE_REQUIRES_RECONCILIATION`).
- BNB is non-zero and router code is present.

DR-06 then requires the pinned initial state's `bnb_units` to equal that finalized native balance. Two gaps against GA11:

- **GB-1, a transaction mined but not finalized:** Gate B does not read the nonce at the finalized block. If a wallet transaction is mined but not yet finalized, `latest == pending`, and the finalized BNB still equals the old opening balance, so DR-03 and DR-06 pass. The transaction then finalizes and changes the balances. Fix: read `eth_getTransactionCount(wallet, <finalized height>)` in `probe_chain` and block unless it equals `latest`. This is the GA11 rule. BSC's fast finality makes the window short, and #84's runtime `BalanceCheck` would detect the change after start.
- **GB-2, only BNB cross-checked:** DR-06 compares only BNB against the chain. USDT and the five bStocks in the pinned state are not checked at Gate B. They were checked at Gate A capture by GA11, and #84 checks them at runtime.

Both gaps are in section C's execution code (owner Isaac) and are recorded in `docs/INCOMPLETE_WORK.md`.
