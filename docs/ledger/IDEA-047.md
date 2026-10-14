# IDEA-047 — Host services for the two-host deployment: signer key file, signer service, service units and host images

- Date / owner: 2026-10-14 / Yao Zhu (scope decision) with Claude. Hosting owners remain Keegan + Isaac (review).
- Status: **pre-registered** (criteria below committed before implementation).
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
