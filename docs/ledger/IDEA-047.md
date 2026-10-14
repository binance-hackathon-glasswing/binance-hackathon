# IDEA-047 — Host services for the two-host deployment: signer key file, signer service, service units and host images

- Date / owner: 2026-10-14 / Yao Zhu (scope decision) with Claude. Hosting owners remain Keegan + Isaac (review).
- Status: **implemented and validated offline** (every row PASS, 2026-10-14; hosted checks NOT RUN, see results). Pre-registered at `67e26bd`.
- Branch: `codex/hosting-option-b-20261012` (PR #20, stacked on #19 → #18). Nothing is applied to AWS.
- Links: IDEA-046 (two-host layout, B1/B2), IDEA-045 (IAM database login), IDEA-042 (runtime service, exit codes, S1–S3
  secrets), G-01/G-18 (signer allow-list, at-most-once signing), G-03 (version gate covers configs), G-09 (key
  separation), GAP-29 (verified swap decoder, still open), F-61/F-62 (no secrets in repo or logs).

## Scope (Yao Zhu, 2026-10-14)

PR #20's remaining code items except the round driver: (1) signer key-file loader and a database-polled signer service;
(2) systemd units and entry points for the execution, signer, uploader and evidence services; (3) host images as a
provisioning script plus an S3-delivered release bundle (no Packer, no AWS cost to build). The round driver
(`build_driver` → `NOT_INTEGRATED`) stays a separate PR: it waits on the I4 receipt shape (Isaac + Keith). The stack is
pushed to PR #20 only; the team reviews and merges #18 → #19 → #20.

## Design (recommended, for review)

- **Signer channel = the database.** The signer has no internet and reaches only RDS and the S3 gateway (IDEA-046 B2),
  so `primary` cannot call it. The execution service writes an immutable **signing request** (attempt, payload hash,
  epoch, authority version and the gate snapshot it just evaluated); the signer polls, re-checks independently and
  either writes the signature through the existing fenced registry (`execution_signatures`) or records a **refusal**
  with a reason code. The signer trusts `primary`'s observed gate facts (nonce, market open, risk, health), which it
  cannot observe offline; everything it *can* check it checks itself: run fencing and quarantine, the hash-chained
  execution record, the attempt being the last and `AUTHORIZED` with the same payload hash, the G-01 economic
  allow-list (`validate_payload`), the gas budget and its own clock against the gate window and intent expiry.
- **Swaps need a verified decoder.** No verified router decoder exists (GAP-29), so the signer refuses `SWAP` requests
  (`DECODER_NOT_VERIFIED`) and can sign only approvals until one lands. This is a stated gap, not a pass.
- **Wallet key via systemd `LoadCredential`.** The key stays a root-only file (`/etc/larp/signer/wallet.key`, `0600
  root`); systemd hands the service a private copy. The loader accepts only a regular, single-link file owned by root
  or the service user with no group/other bits, in a directory nobody else can write.
- **Config pins.** Each new service's configuration hash is recorded in the release manifest
  (`service_configs_sha256`) and checked at start (G-03), as `runtime_config_sha256` already is.
- **Python 3.12.15 on hosts** from python-build-standalone `20261001` (checksum-pinned in the repo), so the signer
  installs fully offline from the bundle.

## Prospective acceptance (before implementation/testing)

| ID | Expected outcome |
|---|---|
| K01 | `load_key_file` returns exactly one credential (`WALLET_PRIVATE_KEY` as 64 hex, optional `0x`, or a 12/15/18/21/24-word `WALLET_MNEMONIC`) from a regular file owned by root or the effective user, mode without any group/other bit, link count 1, in a directory owned by root or the effective user and not group/other-writable. The result feeds `LocalSigner.from_secret_store` unchanged. |
| K02 | It refuses, with a reason that names no key material: missing path, symlink (file or swapped after check: opened with `O_NOFOLLOW` and `fstat` must match), directory, FIFO, any group/other mode bit, other owner, extra hard link, unsafe directory, empty or > 4 KiB file, unrecognised content, two credentials. A test plants a marker in the file and checks no refusal text, traceback or repr contains it. |
| S01 | Migration `009` adds `signing_requests` (immutable; insert by `larp_execution`) and `signing_refusals` (insert by `larp_signer`); `roles.sql` grants exactly that plus reads the signer needs; the archive role can read both and the backup includes both. A re-sent identical request is a no-op; a different request for the same attempt is refused by the database. |
| S02 | `RemoteSigner` (primary side, `mode = 'live'`) writes the request with the current gate snapshot and waits a bounded time for the signature or a refusal: it returns verified `Signed` bytes, raises `Blocked` with the refusal reason, or raises `Blocked('signer timeout')`. It never holds a key. |
| S03 | `SignerService.once` signs a valid approve request exactly once (a second pass, a restart and a duplicate request do not re-sign or change bytes) and the signature verifies against the payload and the wallet. |
| S04 | It refuses (refusal row, no signature) a request whose run is another run, quarantined or fenced to another epoch; whose attempt is unknown, not last, not `AUTHORIZED` or `ABORTED`; whose payload hash or epoch/version differs from the attempt; whose gate window or intent has expired by the signer's clock; whose approve shape, spender, amount or destination fails `validate_payload`; or a `SWAP` without a verified decoder. Each case is a test on real PostgreSQL. |
| S05 | `python -m larp.signer.service check|run`: config `SignerService.v1` (run, build, wallet address, key path, poll interval, IAM settings for `larp_signer` only); the release and its config hash must verify; the key's address must equal the configured wallet and the run's wallet; mode `dev`/`live` only. Exit codes as the runtime: 0 stop, 1 failure, 3 quarantined, 4 refused. No output line contains key material (test with a marker key). |
| E01 | `python -m larp.execution_live.main check|run`: config `ExecutionService.v1` (IAM settings for `larp_execution`, no key fields: a config naming a key file or key value is refused); `run` verifies release and config hash, then exits 2 `NOT_INTEGRATED` until the round driver lands, without opening a signing path. |
| U01 | `python -m larp.audit.service check|run`: config `UploaderService.v1` (IAM settings for `larp_uploader`, `uploader_secret_id`); loads only `AI_SEEDS_SECRET` from that secret and refuses one that also carries a wallet key; each cycle reads the run's current epoch and drains due chunks with `DeliveryWorker`; SIGTERM stops cleanly; exit 4 on refused config; no secret in output. Tested with a fake receiver and real PostgreSQL. |
| V01 | `python -m larp.sources.live run --release-manifest M --release-root R` verifies the release instead of `git` (hosts have no checkout) and uses the manifest's build ID as the commit; an invalid release is refused; the existing git path is unchanged. |
| M01 | `preflight --build-output … --service-config NAME=PATH` records `service_configs_sha256`; `preflight --manifest … --service-config NAME=PATH` refuses a changed or unrecorded config; `--profile signer` also checks the installed signer lock. Existing manifests and flags keep working. |
| D01 | Units `larp-signer`, `larp-execution`, `larp-uploader`, `larp-evidence` exist; each has its own `User`, the existing hardening set, a release preflight naming the same config as `ExecStart`, `Restart=always` with `RestartPreventExitStatus=2 3 4` (evidence: restart on clean exit). The signer unit gets the key only through `LoadCredential`, sets no secret ID and does not run on `primary`; no unit puts a secret in `Environment=`. A static test checks every unit. |
| H01 | `tools/build_release_bundle.py` builds `larp-<build>-<arch>.tar` from a clean, pushed commit's tracked release files, a wheelhouse for the role's locks (Linux, CPython 3.12) and the pinned Python tarball, with a `SHA256SUMS` covering every file; it refuses a dirty tree, an unpinned Python checksum or a missing wheel. |
| H02 | `deploy/host/provision.sh <primary|signer> <bundle>` (root, idempotent) verifies every checksum, installs Python 3.12.15 and a venv **offline** (`--no-index`), creates one system user per service, installs a root-owned read-only release under `/opt/larp/releases/<build>` with `/opt/larp/current`, creates `/etc/larp` (and `/etc/larp/signer` `0700`), and installs only that role's units. Test: run it twice in an `amazonlinux:2023` container with `--network none`; then the venv imports `eth_account`/`psycopg`/`boto3`, `pip check` passes, the role's entry points answer `--help`, the signer host has no primary units and vice versa, and file ownership/modes match. |
| T01 | Full Python suite passes locally with real PostgreSQL 14 (baseline before this work: 1060 passed, 4 skipped); Terraform tests still 10/10 and 1/1; Linux CI green. |

Pass = every row PASS with evidence. A row that cannot be run offline is reported NOT RUN, never PASS.

- 2026-10-14 correction (Claude, before any S result): S01's "a different request for the same attempt is refused" is
  too strict. A request whose gate window expired (e.g. the signer was down) must be re-sendable with fresh gates for
  the same attempt, and `reauthorize_unbroadcast` keeps the attempt ID under a new epoch. Corrected S01: requests are
  immutable and keyed by their own content hash (an identical re-send is a no-op); a `signing_attempts` row binds each
  attempt ID to one payload hash, and the database refuses (foreign key) any request for that attempt with another
  payload hash. Refusals are per request.

## Validation results (2026-10-14)

Criteria committed at `67e26bd` (S01 corrected at `eac591f`) before implementation. Code `4310f0a` (services, units,
migration 009), `0ea7ca6` + `3e67bf4` (bundle, provisioning), `45e9d00` (CI job). Local: macOS, Python 3.12.14 venv
from `deploy/requirements-test.lock`, PostgreSQL 14.24 in Docker, Terraform 1.13.5.

| ID | Result | Evidence |
|---|---|---|
| K01 | PASS | `tests/signer/test_keyfile.py`: hex key with/without `0x`, 12–24-word mnemonics, `0400`/`0600`, readable `0755` directory; the result builds a `LocalSigner` for the same address. |
| K02 | PASS | Same file: missing, symlinked file and parent, directory, FIFO, every group/other bit, other owner, second hard link, group/other-writable directory, swap between check and open (`changed`), empty/oversized/unrecognised/double content; a marker key never appears in any refusal, traceback or repr. |
| S01 | PASS (as corrected) | Migration `009`; `SigningProtocol.test_s01_*`: identical re-send is a no-op, another payload for the attempt is refused by the code and by the database foreign key. `SigningRoles` (real `roles.sql` grants): signing and refusing work as `larp_execution`/`larp_signer`; each role's forbidden inserts/updates/deletes fail; the runtime cannot read the tables; the archive role exports all three; backup `TABLES` include them. |
| S02 | PASS | `test_s02_timeout_and_refusal_reach_the_caller`: bounded timeout, refusal reason passed through, fresh request after a refusal is signed, payload mismatch refused. `RemoteSigner` holds no key. |
| S03 | PASS | `test_s03_*`: the W04 Executor signs an approve through `RemoteSigner` → `SignerService`; bytes verify and recover the wallet; a second pass, a restarted signer and a duplicate request leave the signature unchanged; the port returns stored bytes without a new request. |
| S04 | PASS | `SignerRefusals`: quarantined, fenced epoch, unknown attempt, aborted attempt, payload hash, authority, gate window and intent expiry by the signer's clock, signer clock behind, nonce, approve spender/amount/destination/selector authorized by a patched (compromised) primary, swap without a verified decoder (signed once a decoder is supplied: the decoder is the only barrier), another run's request never answered. |
| S05 | PASS | `SignerCommand`: `check`, quarantined run → 3, running loop → 0; unpinned config, offline mode, secret ID, key value, two key sources, other build, wrong database role, wallet or mode different from the run → 4; group-readable key file and another wallet's key → 4 `KEY_REFUSED`; systemd credentials directory path; no output contains the key. |
| E01 | PASS | `tests/execution/test_service_main.py`: `check` → 0, `run` → 2 `NOT_INTEGRATED`; key fields, paper mode, unpinned config, other build, wrong role, wallet/mode mismatch → 4. |
| U01 | PASS | `tests/audit/test_uploader_service.py`: only `AI_SEEDS_SECRET` (+ matching address) accepted, foreign names and provider errors refused without the secret in tracebacks; repr hides it while HMAC uses it; delivery bounded per cycle, follows a new owner epoch, continues while quarantined; CLI check/run and refusals → 4. |
| V01 | PASS | `tests/sources/test_release_mode.py`: verified release names the build; tampered or incomplete release refused; `run` never calls git in release mode; git path unchanged. |
| M01 | PASS | `tests/runtime/test_service_configs.py`: `service_configs_sha256` recorded only when given (old manifests unchanged); changed or unrecorded config refused through the CLI; `--profile host` checks the signer lock. |
| D01 | PASS | `tests/runtime/test_host_units.py` over the four new units and the example configs in `config/hosts/`. |
| H01 | PASS | `tests/runtime/test_release_bundle.py` (throwaway repo and remote): contents, checksums, committed bytes only, root ownership; refuses uncommitted tracked change, unpushed commit, unpinned arch, Python checksum mismatch, missing wheel, unknown arch. Real bundles built for `aarch64` and `x86_64` at `3e67bf4` (Python checksum verified, every locked package has a wheel). |
| H02 | PASS | `tools/test_host_bundle.sh` in `amazonlinux:2023` with `--network none`, both roles, twice each: `aarch64` native and `x86_64` emulated, PASS. Checks: Python 3.12.15, imports, `pip check`, seven entry points answer `--help`, everything root-owned and not world-writable, correct users/units per role, `/etc/larp/signer` `0700`, the service user cannot read the root-only key but can read a `0400` credential copy, a group-readable copy is refused, the other role and a tampered bundle are refused. CI job `host-bundle` repeats it natively on Linux x86_64. |
| T01 | PASS locally; CI pending at writing | Local: 1117 passed, 4 skipped (baseline 1060 + 57 new), Terraform 10/10 and 1/1. Linux CI: see PR #20 checks. |

**Not established (NOT RUN, need hosts):** systemd `LoadCredential` ownership and mode on the real AMI (the loader
refuses group bits, so an ACL-based copy would be refused, failing closed); the units under real systemd; RDS IAM
login as `larp_signer`/`larp_execution`/`larp_uploader`; clock sync on the signer (Amazon Time Sync). **Known limits:**
the signer trusts gate facts it cannot observe offline (nonce, market, risk, health) from the request; it does not
check the run's registered version against its release, because `larp_signer` cannot read the journal (`events`);
swaps stay refused until a verified router decoder exists (GAP-29); the execution service stops `NOT_INTEGRATED`
until the round driver lands.

- 2026-10-14 CI (Claude): T01 → PASS. Linux CI run [38510435235](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38510435235) at `3aaa19c`: infrastructure (Terraform `deploy/aws`, `deploy/bootstrap`), runtime (pytest with PostgreSQL 14, demo, Docker smoke) and `host-bundle` (x86_64 bundle built from the pushed head and provisioned offline, both roles) all succeeded.

## Review fixes R1–R2 (2026-10-14, Claude for the user). Prospective criteria

From the PR #20 review (comments on `larp/audit/service.py` and `larp/execution_live/signing.py`). Written and pushed before any change or test run below. Synthetic receivers and requests only; no credentials, network or hosts.

- **R1 · Round logs are retried until acknowledged.** Before this fix, `DeliveryWorker` marks a chunk `EXHAUSTED` after `max_attempts` transient failures (8 × 30 s by default) and never sends it again. The chunk then stays overdue, and the runtime guard's `DELIVERY_DEADLINE` HALT never clears for the rest of the run.
  - A transient failure (network error, 429, 5xx, a non-ACK 200) leaves the chunk `PENDING`, at any attempt count. Delivery is retried with capped exponential backoff: `min(retry_ms × 2^(attempts−1), max_backoff_ms)`, with defaults 30 s and 300 s. `max_attempts` no longer exists. Permanent 4xx other than 429 stays `PERMANENT`, as before.
  - The uploader configuration refuses `max_attempts` (exit 4, so an old file cannot silently keep the cap). It accepts `max_backoff_ms` ≥ `retry_ms`. `config/hosts/uploader.example.json` is updated.
  - Tests:
    1. 20 failed sends followed by a recovered receiver still end `ACK`.
    2. The backoff grows and stops at the cap.
    3. With the runtime guard: an outage past the delivery deadline raises the `DELIVERY_DEADLINE` HALT, and it clears once the receiver recovers and the chunk is ACKed.
    4. The old test expecting `EXHAUSTED` is replaced by test 1.
    5. The uploader configuration refuses `max_attempts`.
- **R2 · One malformed signing request cannot stop the signer.**
  - `read_request` checks every `Gates` field's type:
    - `int` for `epoch`, `state_version`, `observed_at` and `expires_at`;
    - `int` or `None` for `nonce` and `execution_version`;
    - `bool` for the flags.
    - A `bool` is never accepted where an `int` is required.
  - In `SignerService.once`, a data-shape error while evaluating one request (`TypeError`, `ValueError`, `KeyError`, `AttributeError`, `OverflowError`) becomes a refusal for that request. A database outage (`larp.storage.postgres.Unavailable`) still stops the cycle unrefused, as documented.
  - Tests:
    1. A request with a string `observed_at`, a null `expires_at`, a `bool` epoch or a non-bool flag is refused with a reason, and the next valid request is still signed in the same cycle.
    2. A database outage while evaluating is not turned into a refusal.

Pass: the tests above, the full suite against PostgreSQL and Linux CI on the pushed head.

### R1–R2 results (2026-10-14)

Criteria pushed at `5c6fbe9` before any change. Code and tests at `0ae5684`. Local run: Python 3.13 venv from `deploy/requirements-test.lock`, disposable PostgreSQL 16, synthetic receivers and requests only.

| ID | Result | Evidence |
|---|---|---|
| R1 | PASS | `DeliveryWorker` has no attempt cap. Backoff is `min(retry_ms·2^(n−1), max_backoff_ms)`, defaults 30 s / 300 s. Tests: `test_r1_transient_failures_never_exhaust_and_deliver_once_the_receiver_recovers` (20 × 503, then ACK), `test_r1_backoff_doubles_up_to_its_cap`, and `test_r1_a_long_receiver_outage_past_the_deadline_still_clears_the_halt` in `tests/runtime/test_supervision.py` (30 failures, `HALT:DELIVERY_DEADLINE`, then `CLEAR`). The uploader refuses `max_attempts` and `max_backoff_ms < retry_ms` with exit 4 (`test_u01_refusals_exit_4_without_secrets`). The example config is updated. |
| R2 | PASS | `read_request` type-checks every `Gates` field. In `SignerService.once`, `TypeError`/`ValueError`/`KeyError`/`AttributeError`/`OverflowError` while evaluating one request becomes a refusal for that request. Tests: `test_r2_mistyped_gates_are_refused_and_the_cycle_continues` (string, null, bool, float and int-for-bool fields refused; the valid request is signed in the same cycle) and `test_r2_an_unexpected_data_error_is_a_refusal_but_an_outage_is_not` (`Unavailable` propagates, no refusal row). |

- **Tests catch the bugs:** every new R1/R2 test, and both new uploader refusal subtests, fail against the pre-fix `larp/` files (7 failed). They pass at `0ae5684`.
- **Full suite:** 1121 passed, 4 skipped (three Linux bubblewrap, one opt-in recorded-market), 1451 subtests.
- **Linux CI:** [run 38515356112](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38515356112) at `0ae5684`, all jobs passed: runtime, host-bundle, Terraform `deploy/aws` and `deploy/bootstrap`.
- **Not changed:** the archive outbox (`larp/runtime/maintenance.py`) keeps its own `max_attempts` → `EXHAUSTED` rule. An exhausted archive item makes maintenance unhealthy, which the archive alarm reports, but it does not HALT trading. Whether it should also retry indefinitely is left to its owner (Keegan).

## Review fixes R3–R7 (2026-10-14, Claude for the user). Prospective criteria

From the rest of Keegan's PR #20 review (items 3–5 and the bundle note). Written and pushed before any change or test run below. Decision (Yao Zhu, 2026-10-14): the evidence store is shared through a group, read-only on the runtime side, not moved into PostgreSQL. Synthetic data only; no credentials, network or hosts.

- **R3 · The runtime can read the evidence store, read-only.**
  - `larp-evidence.service`: `StateDirectoryMode=0770` and `UMask=0007`, so the store, its WAL files and the artifacts are group `larp-evidence`, with no access for others.
  - `larp-runtime.service`: `SupplementaryGroups=larp-evidence` and `ReadWritePaths=/var/lib/larp-evidence`. SQLite readers of a WAL database must write its `-shm` lock file; the runtime gets no other write path.
  - `SQLiteEvidenceStore(path, read_only=True)` opens `file:<path>?mode=ro` without creating tables or changing the journal mode, and refuses `commit`. Its reads see what a writer has committed in WAL mode; any write through it fails. `FileArtifacts.get` already verifies each artifact's hash.
  - Tests:
    1. Static unit test of both units.
    2. A read-only store reads a live WAL writer's committed batches and refuses `commit` and raw writes.
    3. In the H02 container (primary role): a writer running as `larp-evidence` with umask `0007` keeps a WAL store open under a `0770` state directory. `larp-runtime` with the `larp-evidence` group reads it read-only; `larp-runtime` without that group is refused; no file is world-accessible.
- **R4 · A refused evidence start stops the unit visibly.**
  - In `python -m larp.sources.live run`, a start refusal exits 4 and prints its reasons to stderr: the live preflight (`_env_root`), an unverified or incomplete release, and the dirty or unpushed git checks. Other commands keep their exit codes.
  - `larp-evidence.service` sets `RestartPreventExitStatus=4`. A clean exit after 24 h still restarts.
  - Tests: the CLI returns 4 for null live parameters, null terms hashes and an invalid release. The static unit test checks the setting.
- **R5 · Service-level signals reach CloudWatch, with alarms.**
  - `Maintenance.service_health(run_id, now_ms)` (database only, `larp_archive` grants) reports:
    - the newest open runtime session heartbeat age (`process_sessions`);
    - active HALT reasons (run projection) and quarantine;
    - the number of audit events past their upload deadline;
    - the number and oldest age of signing requests older than 120 s that have neither a refusal nor a signature for their attempt and payload.
  - `python -m larp.runtime.operations once|health` publishes these to `LARP/Runtime` on every run (every 15 minutes, by the existing timer), next to the archive metrics:
    - `Service=runtime`: `Heartbeat` (1 if a heartbeat is at most 600 s old, else 0), `Halted` (count of HALT reasons) and `Quarantined` (0/1);
    - `Service=uploader`: `OverdueLogs`;
    - `Service=signer`: `UnansweredRequests`.

    If the database read fails, it publishes `Heartbeat=0` for the runtime, as well as the archive `Healthy=0` it already sends.
  - Terraform adds one alarm per metric (`Heartbeat < 1`, each count `> 0`), each with `treat_missing_data = "breaching"`. An optional `alarm_notification_emails` (sensitive, never committed) creates an SNS topic with email subscriptions, and every alarm notifies it plus `alarm_topic_arns`.
  - Tests:
    1. On real PostgreSQL: a fresh run reports no heartbeat; a recent session heartbeat is fresh and a stale one is not; HALT reasons and quarantine are reported; an overdue audit chunk is counted; an unanswered old signing request is counted, while a signed one, a refused one and a fresh one are not.
    2. Publishing sends exactly the listed metrics and dimensions, and sends `Heartbeat=0` on a database failure.
    3. Terraform test: the alarms exist with breaching missing data; without emails there is no topic; with emails, a topic and one subscription per address.
- **R6 · Bundles are checked against the CI-built hash before provisioning.**
  - `provision.sh` takes the bundle's expected SHA-256 as a required argument (`--expect-sha256 <64 hex>`), and refuses a missing, malformed or different hash before extracting anything.
  - `tools/build_release_bundle.py` prints the bundle's SHA-256. The CI `host-bundle` job writes it to the job summary, where it is recorded for the activation pack.
  - `tools/test_host_bundle.sh` passes the hash and checks that a wrong or missing hash is refused.
- **R7 · Docs.** `docs/build/architecture-deployment.md` and the PR checklist state:
  - the signer trust boundary next to signer version binding: on two hosts `larp_execution` can write `execution_records`, so the signer independently enforces only the payload (the G-01 allow-list, the gas budget and the swap block);
  - that the evidence unit cannot start until the live intelligence parameters and the terms hashes are set (DR-12, GAP-23);
  - where signer logs live and how they are collected: refusals and signatures are in the archived database, and journald stays on the signer's disk, collected at teardown from an EBS snapshot;
  - the bundle hash comparison;
  - the shared evidence group;
  - the new alarms.

Pass: every test above, the full suite against PostgreSQL 14, Terraform `deploy/aws` and `deploy/bootstrap` tests, the H02 container test locally, and Linux CI on the pushed head.

- 2026-10-14 correction (Claude, before any R3–R7 change): R5 says the timer runs every 15 minutes. It runs every minute (`larp-archive.timer`, `OnUnitInactiveSec=60s`). The metrics publish on each run. The new alarms use 300 s periods with 2 evaluation periods, like the existing archive alarms. R3 also changes the D01 hardening set for `larp-evidence` only: `UMask=0007` replaces `UMask=0077`.
- 2026-10-14 amendments (Claude, with the R3–R7 code, before any R3–R7 test run):
  - R5: the service alarms exist only while `enable_hosts` is true. With hosts off, every one would sit in ALARM on missing data and, with emails set, notify continuously. The Terraform test checks both states.
  - R3: the runtime's path is `ReadWritePaths=-/var/lib/larp-evidence`. The `-` lets the runtime start before the poller has first created the directory.

### R3–R7 results (2026-10-14)

Criteria pushed at `ddc4d62` (cadence correction `f2fd317`) before any change. Code, tests and docs at `d82020b`, plus a Terraform test-fixture fix at `7065595`. Local run: macOS, Python 3.12.14 venv from `deploy/requirements-test.lock`, PostgreSQL 14.24 in Docker, Terraform 1.13.5. Synthetic data only.

| ID | Result | Evidence |
|---|---|---|
| R3 | PASS | `tests/sources/test_evidence_sharing.py`: a read-only store sees a live WAL writer's commits as they land; it refuses `commit`, inserts, deletes, DDL and a journal-mode change; it never creates a missing file; units are as specified, and no other unit joins the group. H02 container (aarch64, `--network none`): a writer as `larp-evidence` (umask `0007`, `0770` state directory) holds a WAL store open, `larp-runtime` with the `larp-evidence` group reads it and cannot write, without the group it is refused, and no file is accessible to others. |
| R4 | PASS | `RefusedStart`: null live parameters and terms hashes give exit 4 with `Live preflight refused` / `INTELLIGENCE_CONFIG_REFUSED:live` on stderr and no store created; a changed or incomplete release gives exit 4; `preflight` still returns 1. `test_v01_git_path_is_unchanged` now expects exit 4 for a dirty checkout. The unit sets `RestartPreventExitStatus=4` and keeps `Restart=always`. |
| R5 | PASS | `tests/runtime/test_service_health.py`, run as `larp_archive` with the real `roles.sql` grants on PostgreSQL 14: no session gives no heartbeat, and an ended one does not count; a heartbeat of exactly 600 s is fresh and 600 s + 1 ms is stale; HALT reasons and quarantine are reported; only the overdue unacknowledged audit event counts; only old requests count as unanswered (signed, refused and fresh ones do not, but a signature for another payload does not answer). Publishing sends the 7 metrics with `Deployment`/`Service` dimensions; a database failure sends archive `Healthy=0` and runtime `Heartbeat=0`. Terraform `deploy/aws` 13/13: five service alarms with breaching missing data while hosts run, none without hosts, an SNS topic with one subscription per address only when emails are given. |
| R6 | PASS | H02 container, both roles: a missing, upper-case or different hash is refused before anything is installed, and the correct hash installs (twice, idempotent). A tampered bundle is refused against the original hash, and also against its own hash (by `SHA256SUMS`). The CI job writes the hash to its summary (to confirm in the CI run). |
| R7 | PASS | `docs/build/architecture-deployment.md`: bundle hash procedure, evidence sharing, evidence-unit prerequisites, monitoring signals and alarm emails, signer log collection, and the signer trust boundary next to version binding. The teardown target list includes the new alarms and topic. Open items are in `docs/INCOMPLETE_WORK.md`. |

- **Tests catch the bugs:** against the pre-fix `larp/` and `deploy/` files (`f2fd317`) with the new tests, 9 tests fail and `test_service_health.py` fails at import (no `service_health`). They pass at `d82020b`.
- **Full suite:** 1138 passed, 4 skipped (three Linux bubblewrap, one opt-in recorded-market), 1466 subtests, at `d82020b`. Terraform: `deploy/aws` 13/13 and `deploy/bootstrap` 1/1 at `7065595`.
- **Process note:** the first Terraform test run, at `d82020b`, failed 1 of 13 runs because the new host-enabled test runs gave no AMI (a precondition). I fixed the fixture and ran the tests once before committing the fix. The recorded 13/13 is the rerun on the pushed `7065595`.
- **H02:** `tools/test_host_bundle.sh` on the aarch64 bundle built from pushed `7065595` (SHA-256 `5cc6cf94…f630`): PASS for both roles.
- **Linux CI:** see the PR #20 checks on the pushed head.
- **Not established (need hosts):** the units under real systemd (`SupplementaryGroups`, `ReadWritePaths`, `StateDirectoryMode`); alarms and email delivery in AWS; a persistent journal on the signer.

## Offline readiness check before starting hosts (2026-10-14, Claude). Prospective criteria

Yao Zhu asked for proof that everything works offline (including the simulation) before any host is started, and wants teammates to review and fix first. This reruns IDEA-043's existing system test runner on PR #20's head. Nothing about it is new or changed.

- **Command:** `tools/system_test.py`, full mode: the system cases, the complete pytest suite, and the offline runtime demonstration.
  - Run from a clean, pushed head of `codex/hosting-option-b-20261012`, against a disposable `larp_test` PostgreSQL 14.24.
  - On macOS the demo needs Linux bubblewrap, so it is proven by the Linux CI run on the same runtime tree (`--linux-ci-run <id>`). It is never reported as locally executed.
- **Pass:** every phase exits zero, every skip is listed with its reason, and a SystemTestReport.v1 is written. It is committed under `docs/build/evidence/` with the tested commit, counts and log hashes.
- **Not covered by this check:** real market, source or model data; a real wallet or signing; hosts. These stay open in `docs/INCOMPLETE_WORK.md`.

### Offline readiness result (2026-10-14): PASS

- **Tested:** `bd79da9`, the head of `codex/hosting-option-b-20261012`.
  - The runner accepts only `codex/system-testing-*` branches, so it ran on the alias branch `codex/system-testing-pr20-20261014`, pushed at that identical commit and removed afterwards.
  - Disposable PostgreSQL 14.24 in Docker; macOS with Python 3.12.14.
- **Report:** `docs/build/evidence/system-test-20261014-pr20.json` (SystemTestReport.v1, status PASS).
- **System cases:** 112 passed, 70 subtests. They cover the real coordinator, the PostgreSQL execution store and service, receipt settlement, reservation release, audit ACK, restart and recovery, restore, replay and release-manifest checks, with synthetic transports.
- **Full suite:** 1138 passed, 4 skipped, 1466 subtests. The skips are three Linux-bubblewrap worker-isolation tests, which run in Linux CI, and one opt-in test that needs external recorded-market artifacts.
- **Offline demo:** PASS on Linux CI [run 38532479457](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38532479457) at `1a6ae58`, whose runtime/config/deploy/migration tree is identical to `bd79da9` (checked by the runner).
- **Scope:** synthetic engineering checks only. No real market, source or model data, wallet, signing or host is involved.

## PR #20 review follow-up R8–R13 (2026-10-14, Isaac / Codex)

User requested implementation of the remaining PR review findings. This section is prospective: criteria are
committed and pushed before changed runtime code is tested. Scope is the six review defects, with no AWS apply,
host startup, live credential use or change to trading policy. Existing deployment dependencies remain open.

| ID | Pass criterion |
|---|---|
| R8 | The proposal required by the deviations register is included in the release file set, manifest hashes and host bundle. A generated manifest verifies against the extracted/provisioned release; altering the proposal fails verification. |
| R9 | Signing requests larger than 64 KiB or nested beyond 64 JSON containers are refused before recursive parsing/canonicalization. A nested poison row is durably refused and the next valid request is signed in the same cycle; database outages still propagate. |
| R10 | The monthly usage budget explicitly excludes credit offsets. Mock Terraform tests assert this. Docs distinguish monthly usage alerts from remaining lifetime credits across the October/November boundary. |
| R11 | Development SSM attaches only to primary, requires development mode and primary HTTPS egress, and refuses unsupported configurations in mock plans. Signer provisioning remains a named, unselected dependency; no new network path or AWS resources are introduced. |
| R12 | The live evidence writer explicitly publishes artifacts at 0640 before atomic linking/fsync; private artifact stores retain 0600. A separate runtime user in the evidence group reads actual artifact bytes in the host container check; an unrelated user cannot. Docs give an offline permissions migration for earlier artifacts. |
| R13 | A main-process launch wrapper runs release preflight for coordinator, evidence, execution, signer and uploader, then execs the service only after success. A refusal exits 4 and RestartPreventExitStatus prevents restarts; transient service failures and clean evidence-cycle exits still restart. Static unit checks and a real-systemd Linux CI regression cover this, alongside extracted-release preflight in the host-bundle check. |

Validation required: targeted regressions, full Python suite (PostgreSQL-dependent cases run in Linux CI), mock
Terraform tests and host-bundle CI. Local unavailable capabilities are reported explicitly. No whole GAP item is
claimed complete by these corrections. Results will be appended after testing the pushed implementation.

R13 correction before the next implementation/test (2026-10-14): CI run 38537570547's real-systemd check found
ExecCondition still auto-restarts on Ubuntu 22.04's older systemd with Restart=always (upstream issue
[22257](https://github.com/systemd/systemd/issues/22257)). Its preflight also exits 1, not 4; the earlier review's
exit-code description was inaccurate, though the ExecStartPre failure loop was real. Replace the condition design
with the main-process wrapper above, mapping any preflight refusal to 4 and retaining direct exec/PID and signal
behavior. Pass also requires a real valid-release failure/restart fixture and a clean exit/restart fixture. The
initial failure is retained here as evidence; it does not validate R13.

### R8–R13 results (2026-10-14, Isaac / Codex): PASS offline

Criteria pushed at `68d4fb2`; implementation `8288195`, Terraform format correction `c9535b5`, R13 revised criteria
`53409d4`, final runtime implementation `9bfffcd`. Every runtime test ran after its code was committed/pushed.
All four jobs pass in [Linux CI 38538487692](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38538487692).

| ID | Result / evidence |
|---|---|
| R8 | PASS: extracted bundle verifies through `verify_release`; editing the proposal fails its manifest hash. The AL2023 host-bundle check now constructs a synthetic registration manifest and runs actual `preflight --profile host` on both provisioned roles. |
| R9 | PASS: byte/depth checks run before JSON decoding; escaped string delimiters and the allowed depth boundary parse correctly; RecursionError becomes a refusal. Real PostgreSQL test refuses the 10,000-level poison request and signs the following valid request in one cycle, with no work on the second cycle. Existing outage propagation tests also pass. |
| R10 | PASS: `cost_types.include_credit=false`, asserted by `budget_alerts_with_recipient`. Deployment guide distinguishes monthly usage from remaining lifetime credits. The deployed budget is not modified; an owner-approved saved plan/apply is still needed. |
| R11 | PASS: SSM attaches only to primary, rejects missing egress, and rejects final-mode access; three mock plan cases pass. Signer provisioning remains the open decision in AWS_RUNBOOK step 5. |
| R12 | PASS: private stores publish 0600; the live writer explicitly publishes 0640 via fchmod before fsync/link. AL2023 host check reads real artifact bytes as the runtime service user with the evidence group. An unrelated user cannot access the store. Earlier-file migration is documented, not run. |
| R13 | PASS: `larp.runtime.launch` maps preflight refusal to main-process exit 4, and execs the service on success. Real Ubuntu systemd: all five units refuse a changed manifest with no service marker and zero restarts; a valid release still restarts an exit-1 service and a clean exit-0 evidence cycle. Three tests plus five subtests pass. |

- Local Python 3.12.14 temporary environment with project test pins: **940 passed, 214 skipped, 1364 subtests**.
  PostgreSQL, Linux/systemd and opt-in checks are unavailable locally. The first sandboxed suite had two localhost
  bind failures; rerunning with localhost access passed. `pip check` and shell syntax checks pass.
- Linux Python 3.12.15 / disposable PostgreSQL 14.24 full suite: **1150 passed, 4 skipped, 1472 subtests**. Three
  skipped systemd tests then run explicitly: **3 passed, 5 subtests**; the other skip is the opt-in recorded market.
- Mock Terraform: **deploy/aws 15/15**, **deploy/bootstrap 1/1**; fmt/validate pass. The initial AWS job failed fmt
  on variables.tf; `c9535b5` corrected it without rewriting history.
- Host-bundle: PASS, both provisioned AL2023 roles with network disabled, packaged release preflight and actual
  artifact sharing. Linux offline demo and Docker smoke: PASS.
- No AWS apply, production-host migration/start, registered audit upload, real signing/trading, or live data/model
  evaluation occurred. No whole GAP is complete. Remaining owners and work are in INCOMPLETE_WORK and the runbook:
  Keegan + Isaac for signer access/first-host checks and integration; Keegan for signer version binding/log shipping;
  Yao Zhu for live evidence inputs and approval of any infrastructure update; team for rehearsal/final freeze.

## New PR #20 review R14–R15 (2026-10-14, Isaac / Codex): prospective criteria

Review at `185704e` (wtvlol, review submitted 09:24 UTC) reports two valid additional failure paths. User requested
assessment and fixes. Criteria are pushed before implementation/testing; no AWS action or live credential use.

| ID | Pass criterion / implementation decision |
|---|---|
| R14 | Exceptions fetching the uploader secret become a sanitized retryable failure (exit 1), so Restart=always retries after provider recovery. Invalid configuration, malformed secret response/content, wrong wallet and foreign credentials remain exit-4 refusals. A pinned-release test exercises failure then recovery, including queued-log delivery with disposable PostgreSQL; no credential or arbitrary provider exception text appears in output/tracebacks. |
| R15 | Keep SQLite and use DELETE rollback journaling for the **shared live evidence writer only**, leaving private stores' WAL default unchanged. The read-only runtime needs no writable evidence mount and cannot create WAL/SHM sidecars. A two-user AL2023 regression closes the writer, opens the reader first, restarts the writer, verifies new commits while the reader stays open, then reopens again after reader close; data survives and no incompatible WAL/SHM files appear. Test conversion from legacy WAL with committed data and document a stopped-services ownership repair for legacy sidecars; never delete a WAL that may hold committed data. |

R15 rationale: group-writable database modes plus setgid would share sidecars but broaden database write access.
Rollback journaling removes that dependency and lets ProtectSystem=strict protect the evidence directory on the
runtime. Ingestion is low cadence; concurrent reads remain supported through SQLite locking. A crash with a hot
rollback journal requires writer recovery before read-only consumption; the runtime cannot repair or mutate it.
SQLite's documented modes/source were checked: [WAL read-only caveats](https://sqlite.org/wal.html#read_only_databases).

Required evidence: focused and full offline tests, two-user host-bundle CI, PostgreSQL CI, existing real-systemd
and mock Terraform checks. Hosted/performance/rehearsal gates remain open. No whole GAP is completed by this scope.
