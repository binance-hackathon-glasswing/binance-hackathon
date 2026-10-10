# IDEA-032 — PR #7 integration review and fixes

- Date / author: 2026-10-10 / Keith request, Codex implementation.
- Status: review and implementation in progress; verification NOT RUN.
- Scope: PR #7 (`codex/evidence-hardening`), IDEA-031, GAP-65/67. No policy adoption, deployment, live data, signing, trading or organiser log upload.

## R01 — Missing owner fixes

PR head `7e2075c` omitted strategy/risk commits through `968971e` and execution commits through `4d07102`. Integrate both by ordinary merges, retaining the canonical EvidenceContext.v1 strategy boundary and all financial/quote/accounting fixes. Preserve the older AssessmentResult.v1 compatibility consumer's regression coverage independently; it is not a second strategy input path. Preserve arbitrary persisted policy data when updating lifecycle state.

## Prospective verification

Commit and push every code change before execution. Run the full secret-free synthetic pytest suite on Python 3.12, including both `tests/redteam/` files, strategy/risk, W04/W08 and PostgreSQL integration if a disposable local server can be provisioned. Pass only when all runnable tests pass, no merge markers remain, `git diff --check` passes, canonical evidence tests retain their authority/freshness behavior, and owner quote/accounting regressions pass. Skipped Linux isolation or unavailable PostgreSQL checks must be reported separately. Add regression fixtures for any further concrete review defect before running its fix. These are engineering checks, not economic experiments or real-text accuracy evidence.

## Remaining owners

Yao Zhu / independent annotator: real-document semantics and model-value evaluation (GAP-26/57/67). Team: authority/policy/source/parameter decisions (GAP-23/24/51/56/64). Isaac + Keegan: real execution/settlement integration, Linux isolation, capability proof and rehearsal (GAP-65). This review does not close those backlog items.

## Verification history

NOT RUN. Append results after executing pushed revisions.
