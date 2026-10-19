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

## Independent all-PR review — 2026-10-17 SGT

Reviewed published `d703ae3`; no additional defect found. AR4 was exercised in
Linux/Python3.12.14 with disposable PostgreSQL14.24 and the pinned boto3/test
stack: archive plus runtime maintenance **10 passed, 4 subtests, no skips**.
The combined branch `codex/all-pr-review-validation-20261017` at pushed
`7328e0a` contains unchanged archive code from this PR and all seven other open
PRs: **1957 passed, 6 expected skips, 2931 subtests**, 326.89s. The six skips are
one external recorded corpus and five opt-in systemd checks; PostgreSQL-backed
maintenance and the real SDK request-shape check ran and passed. Full scope and
heads: IDEA-049 ALLPR-20261017 on PR158. This follow-up changes docs only.

The owner also reports all four mirror CI jobs green for `d703ae3`,
run39045756102 (PR163 comment); this session's private-mirror API read returned
404, so that is owner-reported evidence. The hosted incident check still needs
a bundle containing this fix and a newly acknowledged backup; historical
PERMANENT rows stay recorded. No host or AWS changes were made by this review.


## Verified mirror result and merge — 2026-10-18

Yao Zhu dispatched the mirror build. Independently verified exact head
`19339bdc7e72b8cf79f8d5c54d069072c49bd585` on
[run39091506616](https://github.com/Cookiemunchrr/larp-ci-mirror/actions/runs/39091506616):
**all four jobs SUCCESS**. Runtime: **1931 passed, 6 skipped, 2859 subtests**,
415.24s; explicit systemd check: **5 passed, 5 subtests**, 17.00s. Terraform AWS
19/19 and bootstrap1/1; host-bundle tests, demo and restricted Docker smoke pass.
The six full-suite skips retain the external-corpus and separately run systemd
scope; they are not hosted acceptance. Results posted on PR163.

PR163 merged at `2b4f397` on Oct18 02:51:57 UTC. The combined PR158 head7a0ea14
also contains the fix. A candidate bundle was downloaded and verified locally;
its final combined CI result and release evidence are recorded in IDEA066
PC-CI02. Nothing uploaded to AWS or installed. Hosted incident-backup ACK on the
fixed release remains required. PC-AWS11 healthy status comes from the newer
scheduled backup superseding the old failure; its PERMANENT row stays recorded.
