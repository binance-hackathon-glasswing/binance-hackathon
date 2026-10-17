# IDEA-082 — Incident backups fail on S3's whole-second Object Lock dates

- Date / author: 2026-10-17 UTC / Yao Zhu, with Claude.
- Status: open — fix on `claude/archive-retain-seconds-20261017`; pass criteria below written before the changed code ran.
- Found: IDEA-066 PC-AWS09. On `primary`, the restart drill's incident backup (slot `1792235176666`, 11:06:16.666 UTC) was written and locked by S3 (`COMPLIANCE` until `2027-01-07T11:06:16Z`), but `S3Archive.put` asked for `…16.666` and its read-back check `ObjectLockRetainUntilDate < retain_until` failed, raising `IntegrityError` (a `ContractError`), so the outbox row became `PERMANENT`, `operations health` reports `ARCHIVE_DELIVERY_BLOCKED` and `larp-archive.service` exits 1 each minute until a newer backup is acknowledged.
- Why it matters: the declared journal upload "after any incident" (IDEA-049 D-FND-008) fails on every restart or HALT, including automatic restarts during the scored run, and each one blocks archive health for up to a backup interval. Anchors and scheduled backups use whole-hour slots and are unaffected. `tests/storage/test_archive.py`'s `FakeS3` echoed the exact requested date, so the tests could not see it.

## Change

`S3Archive.put` rounds the retain-until time **up** to the next whole second before the request, so the requested date is one S3 can store exactly, never earlier than `created_ms + retention_days`. The read-back check is unchanged. Whole-second times (all anchors and scheduled backups) produce byte-identical requests.

## Prospective pass criteria

| ID | Criterion |
|---|---|
| AR1 | With a fake that stores Object Lock dates to whole seconds (as S3 does), `put` at `created_ms = 1792235176666` returns a `STORED` receipt, and the stored retain-until is ≥ `created_ms + retention_days × 86 400 000` ms. Without the fix the same test raises `IntegrityError` (red proof run first). |
| AR2 | For whole-second `created_ms` the `put_object` request (including `ObjectLockRetainUntilDate`) and the receipt are unchanged from the base. |
| AR3 | The receipt's `retain_until_ms` equals the date actually requested and stored. |
| AR4 | `tests/storage/test_archive.py` and the runtime maintenance tests pass; the full suite shows no new failures against the base `a428bab`. |

Out of scope: the existing `PERMANENT` row on the live run (it stays recorded; the next acknowledged backup supersedes it, IDEA-049 D-FND-009) and the hosted check, which needs a bundle with this change.

## Results — 2026-10-17 UTC (local, macOS, Anaconda Python 3.14)

- **Red proof first:** with the second-precision fake and the unfixed code, AR1 failed with `IntegrityError: Archive retention/encryption verification failed`, the same error the host recorded. AR2 passed (it guards unchanged behaviour).
- **After the fix: AR1, AR2, AR3 PASS.** `tests/storage/test_archive.py`: 5 passed; the sixth (`test_real_sdk_request_shape_is_supported`) fails only because `boto3` is not installed in this environment, as on the base.
- **AR4 PASS (local):** full suite 1438 passed vs 1436 on the base `a428bab`, with the same 10 failures and 4 collection errors on both (environment). The PostgreSQL-backed maintenance tests are skipped here (no `LARP_TEST_DATABASE_URL`); mirror CI on Linux/3.12 with PostgreSQL still to run.
- NOT RUN: a hosted incident backup with the fixed code (needs a bundle with this change; the next restart or HALT on a host running it is the check).
