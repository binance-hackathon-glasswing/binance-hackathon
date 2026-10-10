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

## Additional review findings and prospective regressions

- R02 (P1): RuntimePlanner serializes BUY order `amount` from received token units, although BUY logs must record USDT spent (SKILL.md F-99). SELL units are correct. The existing red-team control asserts the same wrong BUY convention. Regression: a real baseline BUY records `pay_units / MONEY_SCALE`, excluding separately charged fees, and differs from token quantity; retain the SELL control.
- R03 (P2): SourceIngestor discards `next_url` at `max_pages`, then sends a conditional listing request. An unchanged first page can forever hide later items. Retain a durable continuation across bounded polls/restarts; coverage remains incomplete until pagination finishes. Regression: three pages with a one-page poll budget ingest all three over a store restart before sending conditional requests; report truncation as impaired coverage.
- R04 (P1): Evidence gate accepts future cutoffs/completion times and the runtime validator does not bind the result cutoff to the request. Reject malformed, future or out-of-order result clocks without changing accepted evidence/latches. Regression: mutate real producer timestamps, verify rejection and unchanged evidence state; runtime refuses a result with a different cutoff. Update synthetic gate fixtures to include the real producer's started/completed fields.

All regressions use fake sources/model/market only. First run targets the pushed pre-fix implementation; append observed failures before implementing corrections.
