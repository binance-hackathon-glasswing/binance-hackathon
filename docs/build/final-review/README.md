# Final pre-deployment review: four parallel prompts (IDEA-049)

The last comprehensive review of the whole system before hosts are started and anything is deployed. Four people work in parallel, each with an LLM, one section each. Each section:
1. rebuilds its requirements from the authoritative sources only (the official page, the participant kit, organiser answers, the submitted proposal and explicit team decisions), without being steered by our inferences or the current code;
2. tests the code base against them;
3. fixes what fails;
4. repeats until a full pass over the sources finds nothing new and every assumption is validated or recorded as a deployment risk.

**Start only after PR #20 and this review package (PR #21, including the runner
change) are merged into `codex/system-testing-20261012`.** The IDEA-048 driver on
`claude/pre-deployment-review-4zxz7p` must be reviewed and integrated, or the team
must record a partial-scope exclusion with owner/deadline (protocol §0.1). An
exclusion does not establish whole-system readiness.

## How to use

1. Find your section below (assigned by random draw, 2026-10-14).
2. Give your LLM this instruction:

   > Read `docs/build/final-review/00-common-protocol.md` and `docs/build/final-review/<your section file>` in this repository, and follow them exactly.

3. The protocol is part of every prompt; the LLM must read both files.
4. Keep the person-in-the-loop points:
   - every DECISION-NEEDED item comes back to the team;
   - no AWS, wallet, ai-seeds logging or organiser contact happens during the review.

| Section | Assigned to | Prompt | Covers | Branch | Record |
|---|---|---|---|---|---|
| A: Inputs | **Keith** | [A-inputs-evidence-model.prompt.md](A-inputs-evidence-model.prompt.md) | Data sources and rights, point-in-time, EDGAR and source ingestion, evidence agent, claim verification, red-flag findings, model or deterministic assessor, F-49 retention | `review/final-a-<date>` | `docs/ledger/IDEA-049-A.md` |
| B: Decisions | **Keegan** | [B-decisions-strategy-risk.prompt.md](B-decisions-strategy-risk.prompt.md) | Policy, eligible instruments, sizing and caps, loss controls, HALT precedence, `openState`, costs, accounting, equity valuation, end-of-run, scoring alignment | `review/final-b-<date>` | `docs/ledger/IDEA-049-B.md` |
| C: Actions | **Isaac** | [C-actions-execution-signing.prompt.md](C-actions-execution-signing.prompt.md) | Web3 Open API venue, signing, signer service and key file, allow-list, nonce and finality, gas and first BNB, funding, final-wallet switch, execution store and service | `review/final-c-<date>` | `docs/ledger/IDEA-049-C.md` |
| D: Accountability and operations | **Yao Zhu** | [D-accountability-operations.prompt.md](D-accountability-operations.prompt.md) | Coordinator, decision records, journal, ai-seeds logs and delivery, versioning, manifests, release, deviations, supervision, HALT, recovery, storage, anchors, restore, AWS hosting and monitoring, timeline; **runs the final integration** | `review/final-d-<date>` | `docs/ledger/IDEA-049-D.md` |

Why this split: it follows the system's own flow. A is what the agent knows, B what it decides, C what it does, D how it is recorded and kept running. Each section's code paths are exclusive (listed in each prompt), so the four branches rarely touch the same files. Each source item (F-, K-, G-items, never-do lines, declared sentences, DR and AT items) has one owning section, with split items assigned by aspect. D's integration step checks that nothing ended up unowned.

## Rules in one place

- Everything in `AGENTS.md`, in particular: ordinary commits only, nothing force-pushed, and code pushed before it runs.
- Pass criteria are written and pushed before each run.
- Requirements are frozen and pushed before the code is read (protocol §1.8).
- Tests assert requirements, not the current implementation. Never weaken a test to make it pass.
- Team decisions are never changed to fit the code: such items are recorded as DECISION-NEEDED.
- Shared docs (`docs/LEDGER.md`, `docs/INCOMPLETE_WORK.md`, `README.md`, runbooks) are edited only by D at integration. Other sections list "Requested shared edits" in their record. The exception is corrections to `SKILL.md` summaries that are proven wrong against the verbatim sources.
- For IDEA-049, D temporarily holds Keegan's earlier shared-doc integration role; `DEPLOYMENT_BUILD.md` cross-references this scoped handoff. AGENTS.md hard rules remain in force.
- Cross-section problems go in the record's "For other sections" list, with a failing test, and to the owning person.

## Timing

Team dates (`docs/skill/SKILL.md` §0.4, IDEA-035): parameters freeze at the Oct 22 cut line, and the build freezes at final activation, Oct 27–29. After that no change is allowed (F-114, F-117). Plan the review so that its fixes and the team's DECISION-NEEDED answers land before Oct 22, leaving room for the hosted rehearsal (`docs/build/AWS_RUNBOOK.md`).

Coordination targets for this review (not evidence that a milestone has happened):

| Milestone | Target | Owner / output |
|---|---|---|
| Start/base readiness | Day 0 = PR #20 merge date in SGT; PR #21 integrated and driver disposition recorded before section work | D checks merge SHAs and each section records its base |
| Catalogues frozen and pushed | By the end of Day 2 after the #20 merge | A/B/C/D; no phase-2 code reading before the freeze |
| Phase-2 trace and test criteria pre-registered | By the end of Day 3 | A/B/C/D; include tracker #22's findings only after catalogue freeze |
| Fix loops and combined verification closed | Oct 20 SGT | Section owners + D integration, green checks and issue dispositions |
| DECISION-NEEDED answers / parameter cut | Before Oct 22 cut line | Team; D records unresolved blockers and rehearsal impact |

If a late merge or driver dependency makes these dates infeasible, D records the
slip, owners and revised plan immediately. Do not compress the requirements-first
phases, waive open P0/P1 issues, or silently shorten the declared rehearsal to hit
the cut. The team must explicitly resolve the resulting decision/rehearsal risk.

## Prior findings (phase 2 only)

[The issue inventory](prior-issues.md) assigns all eighteen current findings
#23–#40 from tracker #22, including the later findings and P2s, to one primary
section with cross-section consumers. Read it after catalogue freeze. Tracker
#22's trading-review ID collision and missing original record remain assigned to
Keith for publication and D for integration; hosting IDEA-046 stays intact.
