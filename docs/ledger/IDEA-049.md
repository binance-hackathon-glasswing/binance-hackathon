# IDEA-049: Final pre-deployment review against first-principles requirements

- Date / owner: 2026-10-14 / Yao Zhu (requested) with Claude (prompts). Sections assigned by random draw at Yao Zhu's request: A Keith, B Keegan, C Isaac, D Yao Zhu (D integrates).
- Status: **planned.** Prompts are written. Nothing has run.
- Prompts: `docs/build/final-review/` (README, common protocol, four section prompts).
- Starts after: PR #20 is merged into `codex/system-testing-20261012`.
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
Source: Keegan4 review 5515562621 (GitHub review node PRR_kwDOU5Ify88AAAABSMDOfQ)
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
