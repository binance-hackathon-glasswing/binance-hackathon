# IDEA-049: Final pre-deployment review against first-principles requirements

- Date / owner: 2026-10-14 / Yao Zhu (requested) with Claude (prompts). Sections assigned by random draw at Yao Zhu's request: A Keith, B Keegan, C Isaac, D Yao Zhu (D integrates).
- Status: **planned; PR #21 comments amended, focused regressions and merged-tree CI PASS.** The four-section review is NOT RUN; runner prerequisite regressions and CI are recorded separately below.
- Prompts: `docs/build/final-review/` (README, common protocol, four section prompts).
- Starts after: PR #20 and amended PR #21 are merged into `codex/system-testing-20261012`, with the IDEA-048 driver integrated or an explicitly recorded partial-scope disposition (protocol §0.1).
- Links: IDEA-043/044 (earlier system testing and review), IDEA-045–047 (hosting), `docs/build/DEPLOYMENT_BUILD.md` (DR-01..DR-22), IDEA-021 (AT01–AT20), `docs/build/AWS_RUNBOOK.md`.

## Request (Yao Zhu, 2026-10-14)

One final comprehensive review of the entire system before deployment. Its workflow:
1. Set up tests according to the specifications and requirements. Re-examine them thoroughly, using only objective facts and validated assumptions, without being influenced by other inferences or implementations.
2. Run the code base against them.
3. Spot and fix errors, inconsistencies and invalid assumptions.
4. Retest or add tests, and repeat until the requirements are fully met, no use case is missed and the assumptions are validated.

The work is split four ways for parallel work.

## Design

- **Requirement sources and authority:** `RULE-PAGE` > `RULE-KIT` > `ORGANISER` > `DECLARED` > `DECIDED`. Inferences, hypotheses, opinions, code, tests and earlier reviews are not sources; at most they are assumptions to validate (protocol §1.1).
- **Independence:** each section freezes and pushes its requirements catalogue before reading the code (protocol §1.8).
- **Completeness:** each section's scope inventory lists F-, K- and G-items, never-do lines, declared sentences, DR and AT items, and GAP items. D's integration merges the coverage tables and checks that every item has exactly one owner (MASTER coverage).
- **Exit:** every MUST requirement is covered by a passing test or is a named non-offline check; every assumption is validated or recorded as a deployment risk; no open P0 or P1; all suites green; a final adversarial pass over the sources adds nothing (protocol §4).

## Prospective acceptance

Each section pre-registers its own criteria in `IDEA-049-<letter>.md` (protocol §2.3).

The review as a whole passes when D's integration record shows:
1. All four sections' exit criteria are met.
2. The full suite, `tools/system_test.py`, the Terraform tests and the host-bundle test pass on the merged head, and Linux CI is green.
3. MASTER coverage has no unowned item.
4. The open DECISION-NEEDED items and deployment risks are listed with owner, validation step and deadline.

## Results

NOT RUN.

## PR21-R — prompt review amendments (2026-10-14)

Task: the user requested review of PR #21 and implementation of its comments.
Source: Keegan4 review (GitHub review node PRR_kwDOU5Ify88AAAABSMDOfQ)
at `767b4d1`. Scope is amendment of the review package and its runner prerequisite;
the four section reviews themselves remain NOT RUN. PR #20 is still OPEN.

Prospective checks, recorded before execution:
- PR21-R1: the common protocol names `claude/pre-deployment-review-4zxz7p`, requires
  an integrated reviewed driver or explicit partial-scope disposition, and never
  treats the current `build_driver` stub or the shadow-only driver as live proof.
- PR21-R2: every finding #23–#40 under tracker #22 has a primary section and any
  cross-section consumers; external P1 cannot be downgraded out of the exit gate.
  Hosting IDEA-046 remains distinct from the tracker using the same ID. The missing
  original review/GAP-68 record is explicitly assigned for publication/reconciliation.
- PR21-R3/R6: C owns DR-01 measurements, B consumes the cost summary; B owns
  `tools/fetch_h10_krw.py`. All DR-01..22 and tracked issues have an owner.
- PR21-R4: clean pushed `review/final-[a-d]-<8-digit-date>` branches reach the
  disposable-local-database guard without aliases. Dirty/unpublished heads and
  unrelated/malformed branches remain refused; existing system branches work.
  Run `tests/runtime/test_system_test_branch.py` before the fix (expected four
  section subcases fail at branch refusal), then after the pushed fix (all pass).
- PR21-R5/R7/R8: the stale BNB-decimal hint becomes a regression check; milestone
  dates and slip handling are explicit; D's temporary shared-doc responsibility
  is cross-referenced in the older build brief without relaxing AGENTS hard rules.
- Final verification: `git diff --check`, inspect the complete amended diff, run
  the focused branch-guard regressions, and require PR-head Linux CI. No AWS,
  credentials, signing, broadcast, organiser contact or full final review here.

Results: NOT RUN at this criteria/test commit. No backlog item is completed by
publishing prompts. Driver integration and original review-record publication
remain work for their owners, not implied results of this PR.

### PR21-R0 — verified inputs and red regression

Read-only checks on 2026-10-14: PR #20 is OPEN at `185704e`; PR #21's base is
`codex/hosting-option-b-20261012`. The current review tree's `build_driver` raises
NotIntegrated. IDEA-048 is on `claude/pre-deployment-review-4zxz7p` at
`2caeaed93aa27aac3d502cf8e7f65a0f74d55851`; GitHub compare found six commits ahead
and 35 behind the hosting branch, with no open driver PR. The driver record on
that branch describes shadow-only scope and explicitly deferred signed integration.
No driver implementation or history was copied/merged by this amendment task.

Tracker #22 now publishes all eighteen findings #23–#40 (14 P1, four P2).
The original trading-review ledger/GAP-68 record is absent from this tree;
`IDEA-046.md` is hosting and remains intact. The phase-2 inventory preserves
access to the published issues without inventing the missing author record.

Pushed criteria/tests `0b200d6`, Windows Python 3.12.14:
`python -m pytest -q -p no:cacheprovider tests/runtime/test_system_test_branch.py`
produced **5 failed, 4 passed, 7 subtests passed**. Four failures are the A/B/C/D
allowed-review branch subcases; the fifth is the unpublished-head test being
rejected too early by the branch guard. No child suite, database or network call
was made by these patched preflight tests. This is the expected defect evidence;
the same tests must pass unchanged after the pushed runner fix.

### PR21-R1–R8 — amendment disposition

| Review point | Change / remaining dependency |
|---|---|
| R1 driver missing | Protocol §0.1 names the actual branch, reviewed-merge or explicit partial exclusion, and blocks overall readiness until the needed driver is integrated. C/D distinguish shadow and signed paths. Keegan + Isaac own driver PR/review; D records disposition before section work. |
| R2 missing findings / ID clash | Phase-2 inventory owns all #23–#40, protocol §2.1 maps severity and preserves phase-1 independence; §4/D integration includes current tracker blockers. Keith must publish original review/evidence under an unused ID by Day 3; D reconciles index/GAP-68/cross-references. No original author evidence was fabricated. |
| R3 DR-01 | C owns five-name market/logger measurements and dated hashed cost summary; B consumes it for DR-09/GAP-13. Missing measured data blocks profile derivation. |
| R4 alias branches | Runner accepts exact section branch format; original push/clean/disposable/network guards remain. Common protocol and SYSTEM_TESTING use direct section branches; prerequisite regression is fail-first. |
| R5 stale BNB hint | B verifies the existing `9bfffcd` decimal fix as a regression rather than reporting the old disagreement as open. |
| R6 unowned tool | B's exclusive paths include `tools/fetch_h10_krw.py`. |
| R7 schedule | README sets Day 2 catalogue, Day 3 pre-registration, Oct 20 fix closure and pre-Oct 22 decisions; slip handling preserves phases and rehearsal risk. Targets are coordination proposals, not completed milestones. |
| R8 shared docs | Common protocol, D prompt and DEPLOYMENT_BUILD clarify D's temporary review integration role; AGENTS hard rules and lock stewardship remain. |

Additional consistency correction: the baseline run occurs after catalogue freeze
and before phase-2 implementation changes, so preflight failures cannot steer
the independent phase-1 catalogue. This is a workflow amendment, not a runtime
or trading-policy change. No section review, cloud action or issue remediation
was run. Open inputs remain in protocol §0.1/§2.1 and the prior-issue inventory.

### PR21-V — focused verification (2026-10-14)

At pushed implementation `7498d17`, the unchanged fail-first test file passes:
**5 tests and 11 subtests passed** on Windows Python 3.12.14 (0.29 s), with
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. This verifies direct section-branch acceptance
and dirty/unpublished/malformed branch refusal through the runner's actual CLI
preflight; accepted clean pushed branches still hit the disposable database guard.
No downstream child suite or database/network operation is executed by this test.
`git diff --check` passes. The complete amendment diff and all eighteen issue-owner
rows were inspected. The runtime change is restricted to branch admission in
`tools/system_test.py`; no trading/decision/signing code or policy value changed.

PR-head Linux CI is to be dispatched/checked separately: GitHub had not attached
checks to the new pushed heads when queried. Earlier CI at `767b4d1` is not evidence
for these amendments. Full runtime/PostgreSQL/demo/container, Terraform and host
bundle results must come from the new run; no local full-suite claim is made.

Remaining before the final review: PR #20/#21 integration (D), reviewed driver
PR and execution-scope disposition (Keegan + Isaac/team), and original tracker
#22 record/evidence publication with a unique ID (Keith, reconciliation by D).
The eighteen runtime findings are review inputs, not fixed by this prompt PR.

PR21-V base reconciliation: PR #21's ledger conflicted with base `185704e` because
it lacked the hosting R8–R13 updates. Merge the hosting branch with an ordinary
merge commit, preserve its full IDEA-047 result row and this IDEA-049 row, and
re-run the focused tests and final CI on the merged head. The earlier manual run
38544874242 at `40ac02a` is not the final merged-tree verification. Incoming
runtime/host changes remain PR #20's work, not new fixes attributed to PR #21.

### PR21-V2 — merged-tree CI PASS (2026-10-14)

At pushed merge `1c90f53f708e76f6be9e931c18aeec6a6ccf87e8`, all four jobs pass in
[CI 38545108167](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38545108167):
- Linux Python 3.12.15 / disposable PostgreSQL 14.24 full suite: **1155 passed,
  4 skipped, 1483 subtests passed**, 143.74 s. This is +5 tests/+11 subtests
  against the hosting baseline recorded in IDEA-047. The four skips retain the
  systemd opt-in and external recorded-market limitations.
- Separate real-systemd opt-in run: **3 passed, 5 subtests**, 7.70 s.
- `pip check`, isolated offline demo, Docker build and restricted smoke: PASS.
- Terraform mocked tests: **deploy/aws 15 passed**, **deploy/bootstrap 1 passed**;
  formatting, init and validate PASS. No actual cloud plan/apply.
- Host bundle build and AL2023 offline provisioning/release/artifact checks: PASS.
- The unchanged focused runner regression also passes locally at `1c90f53`:
  **5 tests and 11 subtests**, 0.15 s.

This verifies the combined PR tree's existing engineering checks and the branch
admission amendment. It does not execute IDEA-049's four review catalogues or
remediate tracker #22's eighteen findings. This section is later documentation;
its commit is not the SHA tested above. The PR description carries current CI
status; no earlier successful run is presented as a test of a different code tree.

All review topics are dispositioned above. The driver and original trading-review
record remain explicit owner inputs. PR #21 is open/mergeable, still stacked on
#20; no PR was approved, retargeted or merged into its target by this task. Local
main was fast-forwarded to its already-published origin/main for synchronization.

### PR21-V3 — retarget after PR #20 merge (D, 2026-10-14)

Inputs checked read-only before this entry: PR #20 MERGED into
`codex/system-testing-20261012` at 2026-10-14T11:27:54Z (19:27 SGT) as merge
commit `faf9adc`, so **Day 0 = 2026-10-14 SGT** for the README milestones
(catalogues frozen by end of 2026-10-16 SGT, phase-2 pre-registration by end of
2026-10-17 SGT), counted only once PR #21 is integrated and the driver
disposition is recorded. PR #21 conflicted with the new base (DIRTY) on
`docs/LEDGER.md` only. Tracker #22 still lists exactly #23–#40 (no new child
findings). The driver branch `claude/pre-deployment-review-4zxz7p` is unchanged
at `2caeaed` with no PR, so the driver disposition remains open.

Action: ordinary merge of `origin/codex/system-testing-20261012` (`faf9adc`)
into this branch as `8d6cc4a`, keeping the incoming IDEA-047 row (R14–R15) and
this IDEA-049 row; retarget PR #21 to `codex/system-testing-20261012`.

Prospective checks, recorded before execution:
- PR21-V3a: the PR #21 diff against its new base contains only this package's
  files (prompts, records, shared-doc entries, runner change and its test); no
  incoming PR #20 file appears as a PR #21 change.
- PR21-V3b: `tests/runtime/test_system_test_branch.py` passes unchanged
  (expect 5 tests, 11 subtests) on the merged head.
- PR21-V3c: PR-head Linux CI passes all four jobs (runtime full suite with
  real-systemd run, both Terraform roots, host bundle) on the pushed merged head;
  full-suite counts are at least the base's recorded 1158 tests / 1480 subtests
  plus this PR's +5 tests / +11 subtests, with no new failures or skips.
- No AWS, credentials, signing, broadcast, organiser contact or section review.

Results: NOT RUN at this criteria commit.
