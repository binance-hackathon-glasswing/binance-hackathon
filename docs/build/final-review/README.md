# Final pre-deployment review: four parallel prompts (IDEA-049)

The last comprehensive review of the whole system before hosts are started and anything is deployed. Four people work in parallel, each with an LLM, one section each. Each section:
1. rebuilds its requirements from the authoritative sources only (the official page, the participant kit, organiser answers, the submitted proposal and explicit team decisions), without being steered by our inferences or the current code;
2. tests the code base against them;
3. fixes what fails;
4. repeats until a full pass over the sources finds nothing new and every assumption is validated or recorded as a deployment risk.

**Start only after PR #20 is merged into `codex/system-testing-20261012`.**

## How to use

1. Pick a section below.
2. Give your LLM this instruction:

   > Read `docs/build/final-review/00-common-protocol.md` and `docs/build/final-review/<your section file>` in this repository, and follow them exactly.

3. The protocol is part of every prompt; the LLM must read both files.
4. Keep the person-in-the-loop points:
   - every DECISION-NEEDED item comes back to the team;
   - no AWS, wallet, ai-seeds logging or organiser contact happens during the review.

| Section | Prompt | Covers | Branch | Record |
|---|---|---|---|---|
| A: Inputs | [A-inputs-evidence-model.prompt.md](A-inputs-evidence-model.prompt.md) | Data sources and rights, point-in-time, EDGAR and source ingestion, evidence agent, claim verification, red-flag findings, model or deterministic assessor, F-49 retention | `review/final-a-<date>` | `docs/ledger/IDEA-049-A.md` |
| B: Decisions | [B-decisions-strategy-risk.prompt.md](B-decisions-strategy-risk.prompt.md) | Policy, eligible instruments, sizing and caps, loss controls, HALT precedence, `openState`, costs, accounting, equity valuation, end-of-run, scoring alignment | `review/final-b-<date>` | `docs/ledger/IDEA-049-B.md` |
| C: Actions | [C-actions-execution-signing.prompt.md](C-actions-execution-signing.prompt.md) | Web3 Open API venue, signing, signer service and key file, allow-list, nonce and finality, gas and first BNB, funding, final-wallet switch, execution store and service | `review/final-c-<date>` | `docs/ledger/IDEA-049-C.md` |
| D: Accountability and operations | [D-accountability-operations.prompt.md](D-accountability-operations.prompt.md) | Coordinator, decision records, journal, ai-seeds logs and delivery, versioning, manifests, release, deviations, supervision, HALT, recovery, storage, anchors, restore, AWS hosting and monitoring, timeline; **runs the final integration** | `review/final-d-<date>` | `docs/ledger/IDEA-049-D.md` |

Why this split: it follows the system's own flow. A is what the agent knows, B what it decides, C what it does, D how it is recorded and kept running. Each section's code paths are exclusive (listed in each prompt), so the four branches rarely touch the same files. Each source item (F-, K-, G-items, never-do lines, declared sentences, DR and AT items) has one owning section, with split items assigned by aspect. D's integration step checks that nothing ended up unowned.

## Rules in one place

- Everything in `AGENTS.md`, in particular: ordinary commits only, nothing force-pushed, and code pushed before it runs.
- Pass criteria are written and pushed before each run.
- Requirements are frozen and pushed before the code is read (protocol §1.8).
- Tests assert requirements, not the current implementation. Never weaken a test to make it pass.
- Team decisions are never changed to fit the code: such items are recorded as DECISION-NEEDED.
- Shared docs (`docs/LEDGER.md`, `docs/INCOMPLETE_WORK.md`, `README.md`, runbooks) are edited only by D at integration. Other sections list "Requested shared edits" in their record. The exception is corrections to `SKILL.md` summaries that are proven wrong against the verbatim sources.
- Cross-section problems go in the record's "For other sections" list, with a failing test, and to the owning person.

## Timing

Team dates (`docs/skill/SKILL.md` §0.4, IDEA-035): parameters freeze at the Oct 22 cut line, and the build freezes at final activation, Oct 27–29. After that no change is allowed (F-114, F-117). Plan the review so that its fixes and the team's DECISION-NEEDED answers land before Oct 22, leaving room for the hosted rehearsal (`docs/build/AWS_RUNBOOK.md`).
