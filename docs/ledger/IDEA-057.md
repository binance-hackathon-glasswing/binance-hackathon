# IDEA-057 — Gate A configuration assembly and startup qualification

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
