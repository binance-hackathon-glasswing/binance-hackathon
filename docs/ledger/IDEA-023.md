# IDEA-023 — Proposed solutions for evidence exits, economic evidence and engine proof

- Date / author: 2026-10-10 SGT / Codex, requested by the user following the latest-pull evaluation.
- Status: open — recommendations only; **NOT ADOPTED, IMPLEMENTED OR TESTED**.
- What: concrete proposals addressing issues 1–3 in the review of `1f86cc4..9fe13b1`: the live evidence-exit dispute, economic conclusions stronger than their evidence, and the implementation evidence needed for IDEA-021.
- Why it might help: give policy effects explicit authority and acceptance gates, prevent model assumptions from becoming profit claims, and expose critical execution/audit limitations before the full build.
- Cost / risk: narrower evidence behavior can miss useful exits; verification can reject valid evidence; historical samples remain small; real adapter capabilities may block activation. This entry does not select exposure or establish trading edge.
- Links: IDEA-017..022; D-07/08/11/12; H-02; G-11/18/19/46/51/53; GAP-26/37/44/50/62/64/65/66.
- Labels: [V] checked source/document observation; [I] inference; [R] proposal; [OPEN] decision/input still needed. Prospective gates below are **NOT RUN** and are not a complete experiment pre-registration.

## 1. S1 — Adopt a narrow factual-risk contract separately from predictive overlays [R]

[V] The submitted proposal separately lists thesis falsifiers as exit triggers and makes the evidence-assisted model conditional on held-out performance. The SEC Form 8-K describes disclosure categories, not a position-specific liquidation rule. [I] Neither making all evidence effects shadow-only nor treating every item 4.02/1.05/2.06 as a broken thesis resolves that distinction.

Recommended v1.0 direction: retain declared deterministic portfolio controls; allow a small, explicitly adopted factual-risk/falsifier policy to affect live behavior only after its evidence and operational gate passes. Keep additional predictive evidence effects in shadow unless their own H-02 gate passes. Record adoption and declaration implications in GAP-62; do not call factual-risk adoption validation for edge.

| Evidence class | Proposed v1.0 treatment | Required condition |
|---|---|---|
| Item 4.02, non-reliance | First candidate for a live falsifier, not an automatic item-code exit | Verified current filing explicitly withdraws reliance on statements used by the active thesis, or violates a separately adopted issuer-reporting-integrity condition. Define affected-period relevance and resolution evidence before enabling it. |
| Item 1.05, cybersecurity; item 2.06, impairment | Assessment/review and shadow effect initially | Live effect requires a predefined position-specific falsifier and supported semantic match; filing category or adverse tone alone is insufficient. |
| Fabricated span, wrong issuer, duplicate/old event, ambiguous meaning, unavailable source/assessment | No evidence-authorized sell; retain independently valid portfolio controls | Explicit unknown/rejected result and bounded recheck. Block risk-adding actions whose declared dependencies are invalid; timeout does not clear the block. |

Define every enabled predicate as a versioned record containing: factual condition, issuer, affected period, required sources, supported evidence fields, thesis/risk-premise link, action map, block/reset/re-entry conditions and verification fixtures. A base book without a company-specific catalyst must state any issuer-integrity premise directly rather than inventing a catalyst thesis after the filing arrives.

The LLM returns facts, spans, affected periods, semantic support and uncertainty; no action or sizing field. A verifier checks issuer/source identity, exact saved source bytes, supported interpretation and the frozen predicate. Code owns the action. An accession plus item code and quote occurrence is insufficient. Do not let two agreeing models or 4-of-5 sampling votes substitute for evidence support.

For v1.0 simplicity, an unresolved triggered issuer-integrity condition blocks re-entry for the remainder of the scored run. Any alternative automatic clearance must be frozen and tested before activation; elapsed time, restart or five-session renewal alone cannot resolve the condition. This is a proposed conservative policy with an opportunity cost, not a universal economic optimum. Pending exit persists until reconciled execution, documented dust or explicit execution blockage; it cannot bypass market/signing integrity.

**Prospective acceptance:** freeze a test-suite inventory and expected labels before execution, with independently adjudicated real examples and counterfactual negatives covering issuer mismatch, stale/amended/resolved disclosures, negation, non-thesis-related assets/periods, fabricated quotations and prompt injection. Every explicit supported predicate fixture must map correctly; zero unsupported or ambiguous fixtures may authorize an evidence exit. Test duplicate/restart/outage/re-entry behavior through the engine. Suite coverage and size must be recorded before running; zero errors in curated fixtures does not establish a population false-positive rate. If this gate cannot be completed, that predicate remains disabled and the team must record the resulting declaration/default decision, rather than claiming the problem solved.

Suggested lead: Yao Zhu; team adopts policy; Keith reviews evidence-to-risk behavior. Availability remains GAP-37. Tracks GAP-26/62/64.

## 2. S2 — Repair the measurements and separate feasibility from edge [R]

1. Fix IDEA-022 R1–R3 and IDEA-021 C07 before using their affected outputs: reset the UTC anchor before the midnight return; retain timestamp adjacency through spread/category filtering; exclude unobservable gap attribution from measured session variance; include terminal gas in equity/drawdown. Add the stated deterministic regression fixtures. Preserve historical results and append corrections, including the ledger/plan summaries when corrected evidence exists.
2. Complete the read-only cost/availability dataset in GAP-44/50 at proposed order sizes for both 100 and 200 USDT configurations. Save both market states, timestamps, token metadata, route, quote amounts, size-specific costs, gas-estimation provenance and failure outcomes. No orders or ai-seeds uploads are needed for this collection. The logger's affected defects must be fixed before use under GAP-63.
3. Report quote-based entry cost, explicit future-exit cost allowance, approve/swap gas, failed-attempt gas and latency separately. A quoted round trip is an estimate, not a realised fill. Missing/closed/rejected opportunities remain in the denominator. Print-based spread estimates are diagnostics, not substitutes for executable quotes. The declared entry-cost and validation-buffer commitments remain unless explicitly changed; a mathematical break-even floor does not override them.
4. Freeze a small comparison: one fully specified baseline and one evidence treatment, plus cash as a research comparator. Give each policy its own portfolio/execution path on common exogenous scenarios. Keep risk controls equal when comparing a predictive overlay. A factual-risk policy can be assessed for cost/opportunity tradeoffs without silently changing its adoption rationale into an alpha claim.
5. Write a separate EXP entry and commit its dataset hashes, available-at rules, windows, parameters, sample/coverage minima, uncertainty method and pass/inconclusive rule before rerunning. Untouched historical final data, not development-wallet PnL, decides any predictive promotion. Count independent calendar/event clusters; simulated paths, overlapping horizons and correlated issuers do not create more independent historical observations.

**Reporting contract:** separate (a) operational correctness, (b) cost feasibility, (c) sensitivity under assumed return/correlation/volatility/cost scenarios, and (d) held-out economic evidence. Report terminal equity, realised PnL, drawdown including liquidation, turnover, costs, coverage and missed opportunities separately while Q-39 remains unresolved. A result conditional on a 5% or 8% annual premium must retain that condition; it cannot establish the premium, universal absence of edge or prize-optimal exposure.

**Proposed predictive promotion gate:** preserve H-02's positive lower confidence bound for paired after-cost improvement at matched coverage, and resolve GAP-09's absolute after-cost criterion before execution. Insufficient aligned data or unidentifiable fills/costs is inconclusive. On not-supported/inconclusive, retain only the separately adopted baseline/factual-risk policy; no automatic overlay promotion. Any baseline based on market exposure must be labelled with its unvalidated return premise. F-115 makes silently replacing the deployable default with all cash inappropriate; cash remains useful as a comparator. No baseline or exposure is selected here.

Suggested lead: Keith, reviewer Yao Zhu, following IDEA-021's analytics allocation; real quote/transaction integration with Isaac. Tracks GAP-44/50/64/65/66. No experiment or collection is run by this entry.

## 3. S3 — Prove a small end-to-end engine and its two critical integrations [R]

Use IDEA-021 ENG-01–12 as the candidate implementation contract, preserving manifested commitments. Begin with one compact controller, PostgreSQL, the isolated signer boundary and fake external ports. Keep production reducer/planner/accounting/execution/audit logic shared with tests; fixture policies do not choose a profitable strategy.

| Delivery gate | Concrete artifact | Required evidence |
|---|---|---|
| Day 1–3 capability investigation, in parallel with the core | Route/calldata decoder and nonce/finality capability report; durable ai-seeds adapter contract | Show which permitted reads reveal approve/swap nonce consumption and canonical settlement. SDK history alone omits approves. Prove or explicitly reject each required capability. Register/manifest any new read service before depending on it; submission stays on the permitted Web3 path. Prove stable event IDs/bytes and chunk acknowledgements with protocol vectors/mock receiver first. |
| Day 3 thin integrated path | Fixture proposal -> risk/planner -> atomic reservations/intent -> fake approve/requote/swap -> settlement -> durable round event | Kill/restart at durable boundaries; identical offline replay; no doubled fill, released unresolved reservation, lost hash or duplicate logical audit event. This is a delivery target, not evidence that integration can already meet it. |
| Before dev signing | Real read/quote adapters and action validation; signer ownership/fencing; durable outboxes and recovery | Applicable pre-live AT04–12/17/18/20 gates pass; secret-free paper/replay has no signing/broadcast capability. All decision/trading/logging code is committed/pushed and manifested before running it. Unproved required capability blocks activation. |
| Before final activation | Complete AT01–20 applicability report and full-pipeline rehearsal | Every applicable gate passes with commit/config, reproducer, result and artifact; declared 5+ days including a weekend, with evidence for the actual candidate. No design review or short paper run substitutes for this evidence. |

Keep same-nonce replacement disabled initially. Start with one unresolved outgoing step per wallet; preserve reservations and reconcile all issued hashes before progression. A timeout, absent history row, expired swap quote or reconciled balance does not prove exclusive nonce ownership or transaction death. Unknown ownership or failed local journal blocks signing; retain bounded probes and an explicit externally blocked state. Do not promise exits from other tokens can bypass a wallet nonce gap.

For audit delivery, durably store each final logical event ID, canonical bytes and chunk metadata before sending; retry the same event, record acknowledgements and distinguish local durability from remote upload health. Use a first-party protocol-compatible adapter or an equally durable demonstrated integration; leave the vendored SDK untouched. A stored receiver event with a lost response must be an idempotent resend, not another random-ID `log()` invocation.

Sequence ownership per IDEA-021 §8: Yao Zhu integrates core/evidence jobs; Isaac proves execution/nonce/finality and signer enforcement; Keith supplies accounting/reservations/replay/fault fixtures; Keegan supplies atomic storage, audit delivery, epochs and release evidence. Re-estimate after the Day 3 slice. All applicable acceptance cases remain mandatory for activation; optional replacement and richer market simulation/reporting can be deferred. The exact replay, basic explicit-cost simulation, paper mode and safety/audit controls remain.

**Limits:** correct idempotency/replay design is not production proof. Safe persistent UNRESOLVED may be the only supported response to an external capability gap. No live probe, signer, LLM, audit upload or runtime acceptance case was executed in this proposal.

## 4. Sources, verification and remaining decisions

[V] Sources checked: core SKILL.md reading/guardrail contract and F-114..117; ledger table; INCOMPLETE_WORK.md relevant gaps; IDEA-017..022 reviewed in the preceding turn, with IDEA-021 contracts and IDEA-022 reread; plan.md D-08/11/12 and G-51/53; submitted proposal's validation, exits and failure modes; verbatim official source-page restrictions, trading-guide execution/nonce/timeout section, PROTOCOL §1, and participant-kit K12/K13 protocol details. No fresh organiser answer or exhaustive literature audit is claimed.

Primary external sources reopened 2026-10-10:

- [SEC Form 8-K](https://www.sec.gov/files/form8-k.pdf): categories 1.05/2.06/4.02 checked in the preceding review; disclosure meaning does not prescribe our trade response. Candidate treatment and relevance predicates above are our recommendations.
- [AWS, Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/): durable request identity, ACID mutation boundary and same-ID/changed-content rejection; does not make local state and blockchain settlement atomic.
- [Temporal workflow definition](https://docs.temporal.io/workflow-definition): deterministic downstream command history and external/LLM results outside replay; architectural reference, not a required dependency.

Verification scope fixed before checks: documentation-only changes confined to this entry, its ledger row and a cross-reference on the existing backlog; whitespace and ledger-link checks. No runtime or economic checks. Remaining decisions: team adoption of enabled factual predicates and fallback; exact affected-period/relevance criteria and fixture inventory; baseline/exposure/objective; committed EXP registration; adapter capabilities and activation parameters. Existing GAP-26/37/44/50/62/64/65/66 remain open; no checklist item is completed by this proposal.

- 2026-10-10 pre-commit verification: tracked `git diff --check` passed; the new entry passed explicit trailing-whitespace/final-newline checks; exactly one ledger row and the backlog cross-reference resolve to the existing new entry. The three-file documentation scope was verified with `git status --short`. No runtime, economic, credential or wallet check was run.
