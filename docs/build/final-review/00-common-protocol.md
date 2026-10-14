# Final pre-deployment review: common protocol (IDEA-049)

This file is part of every section prompt (A, B, C, D). Read it in full before your section prompt, and follow both. Where they differ, your section prompt narrows this file but never relaxes a rule in it.

## Goal

Before anything is deployed, establish **from the project's requirements, not from its code** that the system does what it must. Concretely:

1. Rebuild the requirements and specifications for your section from the authoritative sources only.
2. Enumerate every use case they imply.
3. Test the code base against them.
4. Fix every error, inconsistency and invalid assumption you find.
5. Repeat until a full pass finds nothing new.

Earlier reviews checked the code against itself and against our own write-ups. This one deliberately does not trust those write-ups: summaries, inferences and implementations are things to verify, not sources of truth.

## 0. Preconditions and setup

1. **PR #20 must be merged** into `codex/system-testing-20261012`. Check with `gh pr view 20 --json state`. If it is not merged, stop and tell the person you work for.
2. Read `AGENTS.md`. Its hard rules apply to everything you do:
   - no secrets in Git;
   - no force-push, rebase, amend or other history rewriting;
   - code that affects decisions, trades or logging is committed **and pushed** before it runs;
   - pass criteria are written before running;
   - never edit `docs/official/kit/` or `vendor/`.
3. Branch from the current head of `codex/system-testing-20261012`: `review/final-<section letter>-<yyyymmdd>`, for example `review/final-a-20261016`. Work in your own clone or worktree, and record the base commit SHA.
4. **Environment.**
   - Python 3.12 venv from `deploy/requirements-test.lock`.
   - A disposable PostgreSQL 14.24 (`deploy/compose.test.yml`, or the pinned image used in `.github/workflows/runtime.yml`), with `LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:<port>/larp_test`.
   - Terraform 1.13.5 for `deploy/` work.
   - Docker for `tools/test_host_bundle.sh`.
   - The system test runner is `tools/system_test.py`; see `docs/build/SYSTEM_TESTING.md`. It only accepts `codex/system-testing-*` branches, so push an alias branch at your exact commit to run it, then delete the alias.
5. **Baseline before any change.** Run the full suite, record `passed / skipped / subtests` and the commit, and write it in your record (§6). Every later count is compared with it.
6. **What you may never do in this review:**
   - use or request the registered wallets' keys or `AI_SEEDS_SECRET`;
   - call ai-seeds `log()`;
   - sign or broadcast anything;
   - touch AWS (no plan, apply or login);
   - contact the organisers.

   Read-only public data is allowed only through tools already committed in the repo, from a pushed commit. Examples: SEC EDGAR with the configured contact User-Agent; Web3 Open API quotes with a Web3 API key the person you work for already holds. Record every such call (command, time, artifact hash) and never put raw artifacts in Git.

## 1. Phase 1: requirements catalogue, built independently

**Independence rule.** In phase 1, do not open `larp/`, `tests/`, `tools/`, `deploy/`, `migrations/`, the ledger entries (`docs/ledger/`), build briefs or prompts, or any review record. The only exception is when the requirement sources below point you to an exact decision record. Write the catalogue from the sources. You will compare with the code in phase 2.

### 1.1 Requirement sources, by authority (highest first)

| Label | Source | Notes |
|---|---|---|
| `RULE-PAGE` | `docs/official/source_page.md` | Verbatim official page. The official competition rules have not been issued (F-90). |
| `RULE-KIT` | `docs/official/kit/` (incl. `AI_Seeds_Participant_Guide.pdf`, `PROTOCOL.md`, `web3-open-api.md`, `bstocks-trading-guide.md`, `logging.md`), `vendor/ai-seeds-sdk-0.3.0/` | Organiser-issued. Lines marked as demo behaviour are not rules (F-106, F-111). |
| `ORGANISER` | `docs/skill/SKILL.md` §1.10 (F-113..F-118), and F-107 | Organiser answers relayed by the team. Quote them as recorded and say they are relayed. |
| `DECLARED` | `docs/proposal/proposal_answers.md` (the exact submitted text) | Binding commitments (G-11) unless a recorded deviation in `config/release/deviations.v1.json` changes them. A deviation must carry its reason and evidence. |
| `DECIDED` | Explicit team decisions only. See the decision records below. | Only text marked decided or adopted, with its date and decider. Never "recommended", "proposed" or "NOT DECIDED". |

Decision records you may read in phase 1 (only the decided parts):
- `docs/skill/larp/plan.md`: "Declared values", D-items marked decided, §6.5.
- `docs/skill/SKILL.md`: Q-items marked answered or team position.
- `docs/ledger/IDEA-035.md`: §4 and §10.1 decisions.
- `docs/ledger/IDEA-037.md`: decided parts.
- `docs/ledger/IDEA-046.md`: B1–B4.
- `docs/ledger/IDEA-047.md`: the scope and R3 decision.
- `docs/build/DEPLOYMENT_BUILD.md`: the DR-01..DR-22 list, as a team readiness checklist.
- `docs/ledger/IDEA-021.md`: AT01–AT20, as engineering acceptance tests the team adopted.

**Not requirement sources:** `I-`, `H-`, `S-` and unadopted `P-` items; `E-` items other than `[PRIMARY]`; ledger analyses and recommendations; code, tests, comments, docstrings and config files; earlier review findings. In phase 1 they are at most *assumptions to check* (§1.4).

### 1.2 Verify the summaries

`SKILL.md` and `reference/participant-kit.md` summarise the verbatim sources (F- and K-items). For every F- or K-item in your scope:
- open the verbatim text it cites and check that the summary is faithful;
- if it is not, the verbatim text wins (SKILL.md §0.2): record a finding and correct the summary in your PR.

Do the same for every `DECIDED` item: find its record, check the decider and date, and confirm it was not later superseded.

### 1.3 Requirement records

One row per testable requirement, in `docs/build/final-review/<letter>-catalogue.md`:

| Field | Content |
|---|---|
| ID | `<letter>-REQ-NNN` (e.g. `B-REQ-014`) |
| Statement | One testable sentence: "When X, the system must Y." |
| Source | Label + exact location, with a short quote (≤ 25 words) |
| Obligation | MUST (RULE, ORGANISER, DECLARED, DECIDED-as-MUST) or SHOULD |
| Acceptance | The observable outcome that proves it, and how it would be observed offline |
| Use cases | IDs from §1.5 |
| Offline-testable? | yes / only on a host / only in rehearsal / only live, with the reason |

Rules for writing them:
- Split compound sentences.
- Write ambiguous text in its conservative reading, and log the ambiguity (§1.6).
- Never strengthen or weaken a source to fit what you expect the code does.
- A team policy value (e.g. 20 % per name) is a `DECIDED` requirement only if a decision record sets it. Otherwise it is an assumption.

### 1.4 Assumptions register

An assumption is anything the system relies on that is not a requirement source. Examples:
- a kit observation used as a constant (quote expiry ≈ 30 s, swap gas 450k–930k);
- API behaviour (`openState` semantics, rate limits, decimals);
- an environment fact (the AWS Free plan's 1-day RDS backups, Sydney region);
- a team statement (wallet funding, "tokens trade 24/7");
- any inference from the docs, and any default value in code with no source.

For each, record:

| Field | Content |
|---|---|
| ID | `<letter>-ASM-NNN` |
| Assumption and where it is relied on | |
| Status | `VALIDATED`: a primary-source quote, or a reproducible measurement with artifact hash. `PARTIAL`. `UNVALIDATED`. `CONTRADICTED`: the evidence says otherwise. |
| How to validate | The offline test, read-only measurement, organiser question or rehearsal check |
| If wrong | What breaks, and whether it blocks deployment |

An assumption may be marked VALIDATED only with evidence you produced or checked yourself in this review. "Someone said so in a ledger entry" is not validation.

### 1.5 Use cases

Enumerate use cases systematically. Do not stop at the happy path. Cross every requirement group in your scope with each axis below, and write a use case wherever the cross product is meaningful:

1. **Phase:** development (Oct 12–26); final activation (Oct 27–29, fresh final wallet); scored run (Oct 29 – Nov 12, **no human action, no version change**, F-114/F-117); after the run (provisional ranking Nov 13, winner audit Nov 16–20).
2. **Time:** UTC midnight; the 02:00 UTC log deadline; US DST end (Nov 1); weekends; US market holidays; market closed or `openState=false`; clock skew and a backward clock; the end-of-run window.
3. **Dependencies:** each external dependency slow, 429, 5xx, timing out, returning malformed or inconsistent data, or down for minutes, hours or days. These include the Web3 API, the chain and receipts, SEC/EDGAR, the model provider, the ai-seeds receiver, PostgreSQL, S3 and CloudWatch.
4. **Data:** empty, boundary values, duplicates, late, out of order, future-dated, revised or amended, oversized, wrong types, hostile (prompt injection, crafted documents).
5. **Process:** a crash at every durable step; a restart; two processes at once; a stale owner; restore from backup; replay.
6. **Resources:** BNB exhausted, USDT insufficient, dust, disk full, database full, AWS credits running out.
7. **Security:** secret leakage paths (logs, errors, reprs, manifests); a compromised or buggy component on another host; tampered release; wrong wallet.
8. **Audit:** an auditor samples any trade, round or version and asks for its full trail (F-47, F-48, F-49).

Record each as `<letter>-UC-NNN`: trigger and state, then expected behaviour, then the requirement IDs.

### 1.6 Conflicts and ambiguities

Where sources disagree (e.g. F-115 vs F-43/F-45/F-50 on scoring) or are silent, record:
- both texts;
- the conservative reading the system must follow until the official rules arrive (SKILL.md §0.2);
- the open question, in the organisers' wording and without our IDs, for the team to send.

Never present a question as open when an F-, K- or Q-item already settles it (AGENTS.md "Answering rule questions").

### 1.7 Completeness closure (before freezing)

Produce a coverage table in your catalogue. Every item in your section's "scope inventory" (section prompt) maps to requirement IDs, or to "owned by section X", or to "not applicable because …". The inventory covers:
- each F-item;
- each K section;
- each never-do line (SKILL.md §0.3);
- each `[RULE]` and `[RULE-DERIVED]` G-item;
- each sentence of the declared proposal;
- each DR and AT item.

Nothing may be unaccounted for. Anything you think belongs to nobody, or to two sections: claim it, and note it in your record's "For other sections" list.

### 1.8 Freeze and push

Commit and push the catalogue (requirements, assumptions, use cases, conflicts, coverage) **before** phase 2, with the message `docs: freeze <letter> requirements catalogue before code review (IDEA-049)`. This commit is the evidence that the requirements came first.

Later additions are allowed only as dated amendments, each with a reason. Never edit frozen rows silently.

## 2. Phase 2: trace and test design

Now read the code, tests, configs and records.

1. **Trace matrix**, in the catalogue under "Trace". Per requirement:
   - the implementing code (`path:function`);
   - the existing tests (`path::test`);
   - a verdict: `COVERED` (a test asserts exactly the acceptance), `WEAK` (a test exists but would pass if the requirement were broken), `MISSING`, `CONTRADICTED` (the code does something else), or `NOT-OFFLINE` (needs a host, rehearsal or live; name the exact later check).
2. **Assumptions in the code.** Find the constants, defaults and behaviours the code relies on. Add them to the register (amendment) and validate them.
3. **Pre-register.** Before running anything new, write in your record (§6):
   - the pass criteria for each new test;
   - each suspected defect.

   Commit and push.
4. **Write tests for every `WEAK` and `MISSING` MUST requirement and every validatable assumption.**
   - **Assert the requirement, not the implementation.** A test that only mirrors the current code is not a test of the requirement.
   - Use real components. Fakes are allowed only at external boundaries (HTTP, chain, model, S3, receiver). Use real PostgreSQL. Tests must be deterministic and free of secrets.
   - Name tests after the requirement ID (`test_b_req_014_…`).
   - Commit and push the tests, then run them. A red test is a finding.

## 3. Phase 3: find, fix, retest

Record each finding as `<letter>-FND-NNN`:

| Field | Content |
|---|---|
| Severity | `P0`: a broken RULE or ORGANISER requirement, or anything that could cause an unmapped trade, a manual intervention, a prohibited transaction, a lost or late log, a leaked secret or an unrecoverable halt. `P1`: a broken DECLARED or DECIDED requirement, or a failure without autonomous recovery. `P2`: wrong but contained. `P3`: hygiene. |
| Evidence | The failing test (or proof) committed before the fix |
| Fix | Commit SHA |
| Retest | Focused tests plus the full suite, with counts |

Fix rules:
1. **Failing test first,** pushed, then the fix, pushed, then the run. Never weaken, skip or delete a test to make it pass. A skip needs a stated environmental reason.
2. **Never change a decided value or policy to make code pass.** If a requirement needs a team decision (a missing value, a conflict, an unclear source):
   - record `DECISION-NEEDED` with options and a recommendation;
   - leave that item blocked;
   - tell the person you work for.
3. **Stay in your exclusive paths** (section prompt). If the fix belongs to another section's code, record it under "For other sections" with the failing test, and tell that section. If both of you agree, the owner makes the fix, or you make it with their written OK in the PR.
4. **Invalid assumptions.** Fix the code so that it no longer depends on the assumption, or validate the assumption. If neither is possible offline, record it as a deployment risk with owner, validation step and deadline in `docs/INCOMPLETE_WORK.md` (requested edit, §6).
5. **After each round of fixes,** rerun:
   - the full suite;
   - `tools/system_test.py`;
   - Terraform tests if you touched `deploy/aws` or `deploy/bootstrap`;
   - `tools/test_host_bundle.sh` if you touched `deploy/host`, `deploy/systemd`, `tools/build_release_bundle.py` or locks.

   Push, and check that Linux CI is green.

## 4. Phase 4: repeat until done

Loop phases 2–3 until **all** of the following hold:
1. Every MUST requirement is `COVERED` by a passing test, or `NOT-OFFLINE`. A `NOT-OFFLINE` item must name its host, rehearsal or live check and appear in `docs/build/AWS_RUNBOOK.md` or `docs/INCOMPLETE_WORK.md`.
2. Every assumption is `VALIDATED`, or recorded as a deployment risk with owner, validation step, deadline and blocking flag. No assumption may be `CONTRADICTED` while the code still relies on it.
3. No open P0 or P1 finding. Each P2 is fixed or accepted in writing by the team.
4. Full suite, system test and CI are green, and counts are recorded against the baseline.
5. **A final adversarial pass found nothing new.** Re-read every source in §1.1 for your scope from top to bottom, asking only: "Which requirement or use case is still missing?" Anything new goes back to phase 1 as an amendment and loops. You are done only after a complete pass adds nothing.

## 5. Honesty rules

- Not run is `NOT RUN`, never PASS. A synthetic test is never evidence of real-market, real-source or profitability claims. Say exactly what each result covers.
- Quote counts, commits and CI run IDs exactly. If you could not do something, say so and why.
- If a source is ambiguous, say so. Do not pick a reading silently.
- Do not invent sources, quotes, dates or answers.

## 6. Deliverables (per section)

1. `docs/build/final-review/<letter>-catalogue.md`: requirements, assumptions, use cases, conflicts, coverage and the trace matrix.
2. `docs/ledger/IDEA-049-<letter>.md`: your record, containing:
   - the base SHA and baseline counts;
   - the pre-registered criteria, with commit SHAs that predate their runs;
   - findings with severities, fixes and retests;
   - DECISION-NEEDED items;
   - the deployment risks;
   - final counts and CI links;
   - "For other sections";
   - "Requested shared edits".

   For the requested shared edits, give exact text for `docs/LEDGER.md`, `docs/INCOMPLETE_WORK.md`, `docs/skill/SKILL.md`, `README.md` and the runbooks. **Only section D applies shared edits**, at integration, to avoid conflicts. Corrections to SKILL.md summaries (§1.2) are the exception: make them in your own PR.
3. Code and test changes inside your exclusive paths.
4. One PR from your branch into `codex/system-testing-20261012`, titled `Final review <letter>: <section name>`. In the description, give:
   - the counts;
   - the open P2s, DECISION-NEEDED items and deployment risks;
   - a link to your record.
