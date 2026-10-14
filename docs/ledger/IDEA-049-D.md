# IDEA-049-D — Final review D: accountability and operations

- Date / reviewer: 2026-10-14 / Yao Zhu, with Claude.
- Branch: `review/final-d-20261014`, cut from `codex/system-testing-20261012` at **`c1b6daf`** (merge of PR #66).
- Catalogue: [`docs/build/final-review/D-catalogue.md`](../build/final-review/D-catalogue.md).
- Protocol: [`00-common-protocol.md`](../build/final-review/00-common-protocol.md) and [the D prompt](../build/final-review/D-accountability-operations.prompt.md).
- Status: phase 1 frozen. Phase 2 not started.

## 0. Preconditions (protocol §0.1), checked 2026-10-14 before section work

| Input | Disposition | Evidence |
|---|---|---|
| PR #20 merged into `codex/system-testing-20261012` | **Merged** 2026-10-14T11:27:54Z, merge commit `faf9adc` | `gh pr view 20 --json state,baseRefName,mergedAt,mergeCommit` |
| PR #21 (review prompts and runner change) integrated | **Merged** 2026-10-14T11:41:42Z, merge commit `c829fae` | `gh pr view 21 …` |
| Round driver (IDEA-048) | **Merged** through PR #66 (`claude/round-driver-20261014` → `codex/system-testing-20261012`) 2026-10-14T15:09:51Z, merge commit **`c1b6daf`**; PR head `6085347`, tested base `c829fae`. It merges the IDEA-048 branch `claude/pre-deployment-review-4zxz7p` with history kept, and PR #41 (C's profile-bound quotes / native gas quote port). | `gh pr view 66 --json mergeCommit,baseRefOid,headRefOid,body` |
| Driver's accepted scope | **Signed-execution path wired, live signing still gated** (per the PR description): `execution: "shadow" \| "service"`; the service path drives I3 → execution service → `RemoteSigner` → `SignerService` → `FencedRelease` → I4 → settlement → close, tested with a throwaway key and synthetic ports. Live signing stays blocked by C's capability gates: fake-only `Executor` (`EXECUTOR_CAPABILITY_GATE`, `larp-execution` exits 2 `NOT_INTEGRATED`), unverified router decoder (GAP-29), native top-up receipts refused (C-OPEN-005). | PR #66 description; to be verified against the code in phase 2 |
| Consequence for D | The driver is on the review base, so no §0.1 exclusion is needed. Requirements that depend on the live signer path (Gate B) stay `NOT-OFFLINE`/blocked until C's gates lift; a shadow or gated path is not proof of the live `ExecutionService`/signer path. | — |

No AWS action, wallet key, `AI_SEEDS_SECRET`, ai-seeds `log()`, signing, broadcast or organiser contact is part of this review (§0.6).

## 1. Environment (protocol §0.4)

- macOS (darwin), Python **3.12.14** venv in the session scratch directory from `deploy/requirements-test.lock` (installed as CI does, `pip install -r`; `pip check` clean).
  - Observation (setup only): `pip install --require-hashes -r deploy/requirements-test.lock` fails because `psycopg==3.3.6` has no hash line; recorded as D-ASM-020, to be checked in phase 2.
- PostgreSQL **14.24** from `deploy/compose.test.yml` (pinned digest), project `larpd`, loopback port 55432, database `larp_test`.
- Docker 29.4.3 (Docker Desktop started for this review).
- Terraform 1.13.5: **not installed on this machine**. Phase 2 will use the official `hashicorp/terraform:1.13.5` image or report the Terraform tests as NOT RUN locally and rely on Linux CI.

## 2. Phase 1

Catalogue frozen in the commit that adds this file: 92 requirements, 30 assumptions, 69 use cases, 13 conflicts, coverage of every item in D's scope inventory. Input gap: the kit's demo code and SDK `examples/` are not preserved in the repo, so F-106/F-111 cannot be re-checked against verbatim text (D-ASM-029).

## 3. Baseline (protocol §0.5)

To be run after the freeze is pushed, at the unchanged base, before any phase-2 change.

## 4. Pre-registered criteria, findings, retests

Not started.

## 5. DECISION-NEEDED

Candidates from phase 1 (to be confirmed in phase 2): D-CON-03 (standby vs two hosts), D-CON-04 (rehearsal length), D-CON-09 (latched HALTs vs autonomous recovery).

## 6. Deployment risks

To be filled.

## 7. For other sections

To be filled.

## 8. Requested shared edits

To be filled at integration.
