# IDEA-049: Final pre-deployment review against first-principles requirements

- Date / owner: 2026-10-14 / Yao Zhu (requested) with Claude (prompts). Sections assigned by random draw at Yao Zhu's request: A Keith, B Keegan, C Isaac, D Yao Zhu (D integrates).
- Status: **planned; PR #21 amendments in progress.** The four-section review is NOT RUN; runner prerequisite regressions are recorded separately below.
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
