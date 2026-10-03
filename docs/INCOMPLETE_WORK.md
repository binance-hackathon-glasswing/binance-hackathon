# Incomplete work

Initial inventory: 2026-10-04, based on a review of all 17 repository Markdown files. These items identify missing specifications, conflicting commitments, and undocumented readiness evidence; they do not establish that implementation work has not happened. External claims and implementation were not independently verified in that review.

This is a live checklist. Remove an entire item once its work is fully completed and verified. Keep partial or blocked items, narrowing them to the remaining work. Preserve supporting decisions, test evidence, and experimental results in their authoritative documents before removal. IDs are stable; do not renumber surviving items. This checklist does not override the rules in `skill/SKILL.md` or the append-only experiment ledger.

## Commitments and scope

- [ ] GAP-01 — Establish the exact submitted proposal: confirm whether `proposal/proposal_answers.md` matches the submission, archive the exact submitted text, and reconcile the conflicting archive/draft descriptions in `skill/SKILL.md` and `README.md`.
- [ ] GAP-02 — Reconcile active decisions with the proposal: five-session horizon, trailing 60-session volatility and sizing formula, UTC loss boundary, 12% drawdown reduction to 40% gross, and primary plus fenced cold standby. Update D-05/D-06, G-22/G-29 and status tables; retain only genuinely unresolved choices. Sources: `skill/larp/plan.md`, `proposal/proposal_answers.md`.
- [ ] GAP-03 — Resolve the three-tool limit versus four listed tools; specify whether feature lookup is internal context construction or an exposed tool. Sources: G-50 and the proposal's tool list.
- [ ] GAP-04 — Freeze the live rehearsal requirement: reconcile five-plus days at minimum size in the proposal with at least two signer-enabled days plus shadow operation in the operating plan, and define acceptance evidence.
- [ ] GAP-05 — Define the Oct 22 cut line: distinguish removable features from mandatory safety, logging, verification and recovery components whose failure prevents activation. Source: plan §6.2.

## Trading and model decisions

- [ ] GAP-06 — Finish D-06/I-63's label specification: horizon, price series and observation timestamps, UP/FLAT/DOWN boundaries, absolute versus relative returns, cost convention and corporate-action handling before training.
- [ ] GAP-07 — Define the decision-model training and acceptance plan: pinned checkpoint, dataset size and class balance, training recipe, compute requirements, inference benchmarks and acceptance criteria. Address I-38/E-51's lack of financial validation.
- [ ] GAP-08 — Resolve D-07/D-08 before dependent evaluation: specify V0 inputs, sizing and exits; choose and pre-register the deployable default for inconclusive evidence; document any declaration implications.
- [ ] GAP-09 — Define a unified held-out deployment gate that combines improvement over V0 with absolute after-cost performance, calibration, coverage and operational reliability; reconcile H-02/EXP-001 with the proposal's entry-cost hurdle.
- [ ] GAP-10 — Specify portfolio construction: candidate ranking when slots are scarce, capital allocation, simultaneous-order reservations, repeated buys, target-weight updates and treatment of correlated exposures. Sources: G-21/G-29.
- [ ] GAP-11 — Specify position lifecycle: thesis expiry and renewal, behavior after the forecast horizon, confidence decay and re-entry after exit. Source: G-51.
- [ ] GAP-12 — Define risk-action precedence and reset rules: model/falsifier/event/drawdown conflicts, drawdown-halt reset, selection of positions for automatic reduction, and whether adding to existing holdings is prohibited during a new-risk halt. Sources: D-06, G-22/G-23 and proposal drawdown controls.
- [ ] GAP-13 — Freeze remaining operational parameters with owners, selection methods and deadlines: turnover, orders/day, sampling frequency, exit-cost allowance, slippage caps, freshness limits, gas reserves, regime thresholds and event rules. Sources: G-20–G-30 and the core placeholder checklist.
- [ ] GAP-14 — Define internal equity valuation under limited liquidity: quote size, liquidation-side marks, stale/missing quotes, gas holdings, unsolicited assets and balance adjustments. Sources: G-22/G-30, I-28.
- [ ] GAP-15 — Define bounded retry and escalation behavior when a required exit or reduction cannot execute within its freshness/slippage controls. Source: G-25.

## Experiments and validation

- [ ] GAP-16 — Complete and commit pre-registration for EXP-001, EXP-002 and EXP-003 before running them: owners, data snapshots and periods, frozen sample thresholds, code/config references and complete pass criteria. Follow `ledger/README.md`; add dated amendments rather than rewriting past criteria.
- [ ] GAP-17 — Complete EXP-001's statistical design: predefined coverage levels and matching procedure, confidence level, resampling unit for overlapping five-session outcomes, separate variant criteria and selection procedure for V1/V2.
- [ ] GAP-18 — Align EXP-002's hypothesis, comparison and pass criterion: specify how the matched no-catalyst baseline tests delayed reaction rather than merely positive returns, and how missing quotes enter the metric.
- [ ] GAP-19 — Complete EXP-003: fix stress episodes, coverage tolerance and minimum independent episode count; define the underlying trading policy, exposure-aware comparison and deployment decision for an inconclusive result.
- [ ] GAP-20 — Align evaluation dates with the five-session label horizon and Oct 22/activation deadlines: set last admissible observation dates and identify decisions that must rely on historical evidence.
- [ ] GAP-21 — Establish the post-cutoff evaluation dataset: verify relevant model cutoffs, event counts and data access; define a fallback for unknown cutoffs or insufficient samples. Sources: I-37/I-38.
- [ ] GAP-22 — Define the token-versus-share validation gate: divergence metrics, acceptable tolerances and behavior when underlying-share labels do not transfer. Source: proposal leakage and basis-risk section.

## Data and evidence

- [ ] GAP-23 — Complete data acquisition contracts and the licence register: historical-price vendor, historical news/token quote availability, source rights, rate limits, outage handling, revisions and retained content. Sources: proposal data section, G-42.
- [ ] GAP-24 — Define historical point-in-time timestamp semantics: distinguish historical availability from present-day collection time, preserve corrections/revisions, and reconcile historical replay with G-05's retrieval-time filter.
- [ ] GAP-25 — Define source independence and catalyst deduplication: detect syndicated copies and reports derived from a common release rather than treating GDELT retrieval as independent corroboration by itself.
- [ ] GAP-26 — Define and evaluate claim-verification quality: unsupported-claim acceptance, supported-claim rejection, citation correctness and numerical interpretation, with explicit acceptance thresholds. Source: G-53.
- [ ] GAP-27 — Specify untrusted-content defenses: isolate retrieved instructions, restrict tool destinations and prevent malicious content from entering verified thesis memory. Sources: G-50–G-54.
- [ ] GAP-28 — Specify scheduling and memory contracts: candidate selection, event priority, queue limits, held-position service guarantees, thesis expiry, conflicting updates and migration across versions. Sources: G-51/G-52.

## Execution, audit and recovery

- [ ] GAP-29 — Complete signer validation of the economic action: decoded tokens/amounts, recipient, chain/domain, native value, minimum output, deadlines and nested calls; bind the exact payload to the risk-approved intent. Sources: G-01, T-18.
- [ ] GAP-30 — Define identifiers and uniqueness constraints for multi-transaction actions such as approval plus swap: decision, order, authorization and transaction IDs, preserving duplicate-execution protection. Sources: G-04/G-18.
- [ ] GAP-31 — Complete execution state machines for swaps and RFQs: partial fills, confirmation/finality, reorgs, cancellation outcomes and the evidence required to declare an authorization no longer executable. Source: G-18.
- [ ] GAP-32 — Define atomic reservations and release rules for cash, holdings, gas and risk budgets across concurrent intents, signing, settlement and recovery; fencing alone does not reserve resources. Sources: G-18 and plan architecture.
- [ ] GAP-33 — Reconcile safe-mode operation during repository outages with the remote-presence version gate: specify durable proof of registration and compliant activation behavior. Sources: G-03/G-14, I-33.
- [ ] GAP-34 — Specify the audit journal schema and durability contract: canonical serialization, concurrent writer ordering, atomicity with signer state, schema migration, upload acknowledgments and restore verification, including full model/tool records and HOLD records.
- [ ] GAP-35 — Designate the authoritative hourly anchoring destination and canonical chain-head selection, addressing competing bundles in team-controlled write-once storage. Sources: I-30 and proposal logging commitments.
- [ ] GAP-36 — Define measurable security/recovery acceptance criteria: key provisioning, access boundaries, backup restoration, compromise response, recovery time, permitted data loss and retention capacity; attach test evidence. Sources: T-18, G-43–G-47.

## Delivery and external dependencies

- [ ] GAP-37 — Assign individual owners and backup coverage to decisions, experiments, onboarding questions and acceptance tests; publish the on-call rota. Named functional leads alone do not close this item.
- [ ] GAP-38 — Replace generic milestone criteria with artifact links and measurable readiness gates; update Adopted/Implemented/Tested status from evidence, including the Oct 4 skeleton milestone. Sources: plan adopted-scope table and §9.
- [ ] GAP-39 — Populate I-65's onboarding gate register: owner, answer deadline, evidence required, affected actions and fallback. Prioritize Q-12/Q-26 eligibility, Q-03/Q-08 gas, Q-04/Q-06 valuation/window, Q-16 reasoning output, Q-19 instruments and Q-14 upload grace; complete the core post-onboarding checklist when documents arrive. Pending organiser answers remain blocked items, not implicit approval.
- [ ] GAP-40 — Repair document provenance and navigation: distinguish historical drafts from current commitments, fix stale paths to retired/unavailable material, add direct evidence references for deployment-relevant E-items, and record S-01's cited internal Monte Carlo provenance/results in the ledger without implying retrospective pre-registration.

## Suggested order

Establish submitted commitments → reconcile the active plan → freeze target/baseline/fallback → assign onboarding gates → finish execution/audit contracts → pre-register experiments → attach readiness evidence to milestones.
