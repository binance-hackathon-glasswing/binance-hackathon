# IDEA-049: Final pre-deployment review against first-principles requirements

- Date / owner: 2026-10-14 / Yao Zhu (requested) with Claude (prompts). Four reviewers, sections A–D. D integrates.
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
