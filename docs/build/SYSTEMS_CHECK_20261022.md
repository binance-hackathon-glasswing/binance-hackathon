# Pre-deployment systems check: canonical `d03bbb1` (IDEA-043 SC-01, 2026-10-22)

**Result: every runnable engineering check PASSES locally. Deployment is BLOCKED by one binding
finding (SC-01-F1): no approved build and signer configuration currently start together.**

Tested commit: `d03bbb16cf51277c73d7f381b08f9551d0c10415`, the pushed head of
`codex/system-testing-20261012` (PR243 merge), fetched 2026-10-22 ~11:00Z. Machine receipt:
[evidence/syscheck-20261022.json](evidence/syscheck-20261022.json). Record: [IDEA-043 SC-01](../ledger/IDEA-043.md).

## Pass criteria (fixed before this run)

The criteria were already written before this run: the [LD15 §3](LD15_SIGNED_RELEASE_CHECKLIST.md) table
(four CI jobs) and §2 `render_deviations --check`, plus the IDEA-043 runner (`tools/system_test.py`: system cases,
full suite and offline demo, all PASS). Added for deployment: the signed-rehearsal start path (LV-01 LV4) and the
signer build binding must agree on one installable build.

## Results

| Check | Where | Result |
|---|---|---|
| IDEA-043 system phase (15 system files) | Ubuntu 22.04 arm64 container, Python 3.12.15, PostgreSQL 14.24 (CI digest `5a05f61a…`), non-root `ci` user, local-only network guard | **PASS** 121 tests / 230 subtests |
| Full suite (`pytest -q -p no:cacheprovider`) | same | **PASS** 2470 passed / 7 skipped / 3882 subtests / 0 failures (610.9 s) |
| Skips | same | All 7 explained: 5 real-systemd (run below), the optional private `LARP_INJ01_SOURCE_FILE` fixture, and the external `LARP_RECORDED_MARKET_ROOT` artifact |
| Real systemd (`LARP_TEST_SYSTEMD=1`) | same container booted with systemd 249 as PID 1 | **PASS** 5/5, 5 subtests |
| Offline demo (`python -m larp.runtime.demo`, bubblewrap) | same | **PASS** |
| `pip check`; installed packages vs `deploy/requirements-test.lock` closure | same | **PASS**; package set is identical to the lock closure |
| Terraform 1.13.5 `fmt`/`init -lockfile=readonly`/`validate`/`test` | linux/amd64 container (CI-pinned zip `0dbe3fcc…`) | **PASS** `deploy/aws` 19/19, `deploy/bootstrap` 1/1 |
| Docker build `deploy/Dockerfile`; `run --network none --read-only --cap-drop ALL` | Docker 29.8.2, arm64 | **PASS** (exit 0, inspection banner only) |
| Host bundle build `--arch x86_64` | macOS, from a fresh clone of the pushed head | **PASS** (local dry run, see below) |
| `tools/test_host_bundle.sh` both roles, twice, `--network none` | amazonlinux:2023 pinned digest, linux/amd64 emulated | **PASS** primary and signer; `release_verified: true`, `signing_enabled: false` |
| `render_deviations.py --check` | macOS, Python 3.12.14 | **PASS**; 15 FINAL, 9 DRAFT (DEV-01–04/07/19/22/23/24, already tracked for LD24) |
| Secrets/key hygiene (tracked files) | `git grep` | **PASS**: no private-key blocks, AWS key IDs, provider tokens or filled `.env` values; `.env.example` has no values |
| History | `git merge-base` | **PASS**: RC2 `b22207e`, RC3 `5bee006` and RC3a `fa1b6c9` are ancestors of the head |
| Org GitHub Actions run 39764684229 for `d03bbb1` | GitHub | **UNAVAILABLE**: all four jobs ran zero steps (billing/spending limit). Not a code result |
| Mirror CI for `d03bbb1` | `Keegan4/Keegan4-larp-ci-mirror` | **NOT VISIBLE** to this account (HTTP 404); no run is recorded in the repository for this commit |

The dry-run bundle is `larp-d03bbb16cf51-x86_64.tar.gz` `0286e727…f216f8`, release manifest `339de5e6…a8f621`
(205 files, host bindings null), Python `0e56475e…` and RDS CA `d7389074…`, both unchanged. **Do not install it.**
LD15 §3 requires the original CI artifact; a local build is a dry run only.

## Findings

### SC-01-F1 (P1, blocks LD16/LD17): the approved signer candidate binds a build that cannot start a signed run

1. **RC3a cannot start the rehearsal.** At `fa1b6c9`, every `parameters.*.live` value in
   `config/intelligence/intelligence.v1.json` is null. `load_config('live')` raises
   `Live parameter 'initial_backfill_ms' is unset; live startup refused` (`larp/intelligence/config.py:75`).
   A `dev`/`service` driver requires `intelligence_mode: live` (`larp/runtime/service.py:249`). Reproduced here: the
   head's `test_lv01_deterministic_signed_rehearsal_builds_with_the_real_live_settings` passes at `d03bbb1` and fails
   against `fa1b6c9`'s code and config. IDEA-049-A amendment 32 states the same.
2. **The head can start it, but it is a different release.** Since `fa1b6c9`, 2 of the 205 manifested release files
   have changed: `config/intelligence/intelligence.v1.json` (LV-01) and `larp/sources/live.py` (docstring). Any release
   that carries LV-01 has a new `build_id`.
3. **The signer candidate is pinned to RC3a.** The owner-approved key-free `signer.json` `f632bbcb…` (SJ-04-OA01) and the
   SJ-05 `check` bind `build_id` `fa1b6c9`. `larp.signer.service` refuses a configured build that differs from the
   verified release (`larp/signer/service.py:233`, tested in `tests/signer/test_service.py`). SJ-04-OA01 says any
   different hash needs a new decision.
4. **No qualified artifact exists for the head.** LV-01's LV5 criterion (mirror CI on the merged commit, all four
   jobs, new bundle) is still pending. Org CI is billing-blocked, and no mirror run for `d03bbb1` is recorded.
5. **Status pages still point at RC3a.** [CURRENT_STATUS](CURRENT_STATUS.md) still calls `fa1b6c9` the installable
   candidate, with "pre-install recapture with the same hashes" remaining. LD15 says the LD16 recheck "must bind
   `fa1b6c9`". The backlog SA-01 line says the same, and the LV-01 line lists only the final-run confirmation.

**Required before LD16/LD17 (owners as in the backlog):**
- Keegan: cut RC4 from `d03bbb1` or later on the mirror. All four jobs must pass; download and verify the original
  artifact.
- Yao/coordinator: re-run SJ-04 hosted assembly with the RC4 `build_id`. This gives a new `signer.json` hash.
- Isaac: a new owner decision for that hash, plus a fresh coverage capture.
- Re-run SJ-05 `check` against the original RC4 artifact.
- Only then do the LD16 bindings and LD17 installation.

The `larp_rehearsal1` schema check (SJ-04-DB01) compared migrations, which have not changed since `fa1b6c9`.

### SC-01-F2 (P3, tracking): the rehearsal database name has no supported activation path in the repository

The only database-retargeting helper in the repository,
`docs/build/ops/llm-trial-20261018/mac/prepare_trial_db.py:13`, does `assert TARGET.startswith('larp_trial')`.
For `larp_rehearsal1` it stops with an `AssertionError`, and under `python -O` the check is removed altogether
(the same failure class as SJ-04-RV01). SJ-04-DB01 notes that activation needs a renderer override for this name,
but no backlog line tracks it. The fix: track it, and implement the override with an explicit refusal rather than
an `assert` before activation.

## Observations (no change needed)

- `max_clock_skew_ms` live = 0 is deliberate (IDEA-049-A amendment 14: strict ingestion until a measured offset
  justifies tolerance; it rejects future-dated rows, which a later poll retries). Under SHADOW authority it cannot
  move trades.
- On linux/arm64, `terraform validate` with `-lockfile=readonly` fails the provider checksum (the lock file's `h1:`
  hashes do not cover that platform). CI and the x86_64 hosts are amd64, where all checks pass. This only matters
  for local arm64 runs.

## Evidence boundaries

All results are local and offline, with synthetic transports and a disposable database. The runtime suite ran on
arm64 Linux (CI is x86_64), and Terraform and the host-bundle test ran emulated on amd64. None of this is hosted CI,
a qualified release artifact, signed-release, host, AWS/RDS IAM/TLS, signer-session, funding or live-trading
evidence. No AWS, database host, key, wallet or paid-model action occurred. Raw logs are outside Git, and their
SHA-256 hashes are in the receipt. All readiness flags stay false.
