# Final review A: inputs (evidence, data sources, model)

**Assigned to: Keith** (random draw, 2026-10-14).

You are one of four reviewers running LARP's final pre-deployment review (IDEA-049). LARP is our agent for the Binance Agentic AI Challenge. Your section is **everything the agent knows and how it reasons about it**:
- which sources it may use and the rights to them;
- point-in-time correctness;
- filing and source ingestion;
- the evidence agent and its tools;
- claim verification and red-flag findings;
- the model or deterministic assessor;
- what of all this must be retained for the audit.

**Before anything else, read `docs/build/final-review/00-common-protocol.md` in full. It is part of this prompt.** Then read `AGENTS.md`, and `docs/skill/SKILL.md` §0 (reading contract, never-do list). Follow the protocol's phases exactly:
1. Independent requirements catalogue.
2. Trace and tests.
3. Fix loop.
4. Repeat until a full pass finds nothing new.

Branch `review/final-a-<yyyymmdd>`. Record: `docs/ledger/IDEA-049-A.md`. Catalogue: `docs/build/final-review/A-catalogue.md`.

## Scope inventory (every item must appear in your coverage table)

Where an item is split between sections, you own only the aspect named here.

- **Official page:** F-08 (agentic aspect only), F-20 (acquires information, "using only information available to it at each decision point"), F-30, F-31, F-32, F-49, F-63, F-71 (rights to every data source, model and API).
- **Kit:** F-102 (filling `cot` per provider, encrypted reasoning excluded); F-104 (the data skills named for use and their limits; the trading-channel aspect belongs to C); K15 and the data parts of K2 and K18 in `docs/skill/reference/participant-kit.md`. Check each against the verbatim Guide pages.
- **Never-do lines (SKILL.md §0.3):** #8 (no future, non-public, Binance-internal, other teams' or unlicensed data), and #7 for model and evidence logs (no credentials).
- **Guardrails:** G-05 (point-in-time filter), G-06 (full model I/O capture), G-10 (clean information), G-12 (model and prompt pinning), G-42 (rights and declared services), G-31..G-39 (thesis, verifier, uncertainty, no hallucinated numbers, audited memory, cadence, shallow graph, HOLD logging of evidence, evaluation hygiene), G-50..G-54 (bounded tool loop, thesis memory and falsifiers, catalyst planner, claim verification, untrusted content). Treat `[POLICY]` G-items as requirements only where a decision record adopts them (protocol §1.1).
- **Declared proposal** (`docs/proposal/proposal_answers.md`):
  - every sentence about data sources, tools, the model approach and the harness;
  - "How would you prevent future leakage and overfitting?";
  - the evidence parts of "Reproducibility plan".
- **Decided items:**
  - plan.md D-03 (evidence model), D-09/D-10/D-11 as decided;
  - IDEA-035 B8 (assessor: Claude or ChatGPT, or the deterministic assessor), §6 and §10.1 red-flag classes;
  - the GAP-56/57 team decisions (2026-10-10: kit token candles as sizing series, rules first, no trained return model, LLM assessment-only);
  - IDEA-041's decided stale bound, only if a decision record adopts it.
- **Readiness and acceptance:** DR-10 (red-flag classes live: the evidence side), DR-11 (assessor connected with budget and fallback), DR-12 (live sources: SEC User-Agent, dated terms captures with hashes, artifact store outside Git, polling cadence); AT items about evidence and assessment (`docs/ledger/IDEA-021.md`).
- **Backlog items to resolve or re-state:** GAP-23, 24, 25, 26, 27, 28 (evidence parts), 56, 57, 67.

## Exclusive paths (you may edit)

- Code: `larp/intelligence/`, `larp/sources/`, `larp/integration/contract.py`.
- Config: `config/intelligence/` (except the `live` parameter **values**: these need a team decision, so propose them as DECISION-NEEDED with derivations), `config/sources/`, prompts under `config/intelligence/prompts/`.
- Tests: `tests/intelligence/`, `tests/sources/`.
- Tools: `tools/edgar_fetch.py`, `tools/probe_free_sources.py`, `tools/probe_kit_sources.py`.
- Records: your catalogue and record.

## Use-case prompts (in addition to protocol §1.5)

Make sure your use cases include at least:
- a filing that is accepted, then amended or withdrawn;
- an EDGAR listing that is late, malformed, partial or paginated into history files;
- the SEC rate limit and a missing contact User-Agent;
- a document with injected instructions;
- syndicated copies of the same release;
- a model timeout, refusal, malformed output, oversized output, or a reply echoing a credential;
- the provider's API unavailable for a day;
- the evidence store growing over 14 days;
- the poller restarting every 24 h;
- the runtime reading the store read-only while it is being written;
- a `cot` that would be empty or encrypted;
- a winner-audit request for the complete prompts, tool definitions and model I/O of one decision (F-49).

## After your catalogue is frozen (not before)

Only then compare with these areas, which earlier work left open or flagged. They are hints for phase 2, not requirements:
- the `parameters.*.live` values in `config/intelligence/intelligence.v1.json` are all null, so live mode refuses to start;
- every enabled source's `terms_evidence_sha256` is null (GAP-23);
- the real-document evaluation T01 and the provider bake-off are NOT RUN;
- the evidence store is shared read-only with the runtime (IDEA-047 R3);
- IDEA-044 V01/V12 coverage semantics: a dead-lettered filing marks only its own record; malformed rows of watched forms still mark the issuer INCOMPLETE.

For each, decide what the requirements say, test it, and either fix it or record it as DECISION-NEEDED or a deployment risk. For the null live parameters, give a derivation for every value from the requirements: cadence, staleness against the decision cadence, the review lifecycle, the 14-day run. Mark them for team approval; do not commit values as decided.

## Done means

Protocol §4, plus:
- every source the system can contact is in the licence register with its rights basis;
- every model input and output that F-49 requires is retained and retrievable for one sampled decision, shown by a test.
