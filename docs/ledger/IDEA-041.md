# IDEA-041 — Deployment build record: evidence (Yao Zhu)

- Date / author: 2026-10-11 / Yao Zhu (drafted with Claude)
- Status: open (acceptance criteria written before building; implementation in progress on `codex/deploy-evidence`)
- What: the live evidence path from prompt [08-evidence-live](../build/08-evidence-live.prompt.txt) under the common brief [DEPLOYMENT_BUILD.md](../build/DEPLOYMENT_BUILD.md) (IDEA-038). It covers six parts: live sources (DR-12), the assessor model with a deterministic fallback (B8, DR-11, I5), red-flag predicate records (B1, DR-10, I8), evidence authority and review jobs (IDEA-035 A2/A4/A8), model I/O for the official round log (DR-07, I5), and the real-document evaluation (GAP-67 T01).
- Branch: `codex/deploy-evidence`, based on `origin/codex/deployment-prompts` at `e4ebff6` (the commit that adds DEPLOYMENT_BUILD.md; PR #12 was not yet merged into `codex/engine-foundation` when work started). Reviewer: Keith.
- Owned paths (brief): `larp/intelligence/`, `larp/sources/`, `larp/integration/contract.py`, `config/intelligence/`, `config/sources/`, `tests/intelligence/`, `tests/sources/`, `tests/redteam/`, `tools/edgar_fetch.py`, `tools/probe_free_sources.py`. Shared docs (LEDGER, INCOMPLETE_WORK, SKILL.md, plan.md) belong to Keegan; the edits this build needs are listed in §6.
- Baseline at `e4ebff6`, before any change (Linux, Python 3.13, no disposable PostgreSQL): 509 passed, 86 skipped (PostgreSQL-only), 754 subtests passed.

## 1. Acceptance criteria (written and pushed before building or running anything)

Results are reported as PASS, FAIL, NOT RUN or INCONCLUSIVE, with the commit SHA. Synthetic fixtures are engineering checks, not market evidence.

**Whole build**
- AC-0.1 All existing tests still pass, including both red-team suites (`tests/redteam/`) and the 13 foundation tests (`tests/test_contracts.py`). Tests that need PostgreSQL are reported as SKIPPED, never as passed.
- AC-0.2 No secret, credential, `.env` file, source text or private label data is committed. Model credentials are read from the environment only and never appear in a record, repr or log.

**Part 1 · Live sources (DR-12, GAP-23/24)**
- AC-1.1 Live mode refuses to start when any enabled source has a null `terms_evidence_sha256`, when a source that needs a User-Agent has no real one (`LARP_SEC_USER_AGENT`; placeholders are refused), or when `LARP_ARTIFACT_ROOT` is unset or inside the repository. Each refusal is a test.
- AC-1.2 A terms-capture tool stores each enabled source's terms page bytes in the artifact store and prints the dated SHA-256 to record in the register. The register loader rejects a hash that is not 64 lowercase hex characters.
- AC-1.3 A live runner polls each enabled source at no more than its `min_interval_ms`, and the five issuers' EDGAR filings at a declared cadence of at most 5 requests/s. It writes one durable line per poll and computes a gap report: the longest interval between successful polls per source, compared against twice the source's cadence. Tested with fake transports and a fake clock.
- AC-1.4 Evidence: a 24-hour live ingestion run on the hosted environment, with no gap larger than twice a source's cadence unless an incident explains it, and the report recorded here with the commit SHA. **Cannot run in this session** (needs the SEC contact identity, the terms captures and the host): NOT RUN until then.
- AC-1.5 A licence-register row for each enabled source is listed in §6 for Keegan.

**Part 2 · Assessor model (B8, DR-11, I5)**
- AC-2.1 Hosted adapters exist for both candidate providers (Anthropic Messages, OpenAI Responses). Each needs a pinned snapshot ID (aliases such as "latest" are refused), an endpoint allowlist, a credential from the environment and an artifact sink. Each stores the exact request and response bytes before parsing, rejects a reply that names a different model, records usage and cost, and returns the provider's reasoning summary. Tested against recorded-shape fake responses. Not verified against a live provider in this session.
- AC-2.2 The deterministic assessor (`RuleBaselineModel`) remains the default and the fallback. A model timeout or error gives UNAVAILABLE, and invalid output gives ABSTAIN. Neither one ever clears evidence.
- AC-2.3 Budget: no assessment makes more than 6 tool calls. An assessment whose model exceeds the 60 s deadline returns a non-ASSESSED result (UNAVAILABLE) within the deadline plus a small join margin, so the round is not blocked. Tested with a slow fake model.
- AC-2.4 A bake-off harness runs the baseline and each configured candidate on the same 15–25 real 8-K/6-K filings for the five issuers, fetched by our own tools. It reports the schema-valid rate, the claim-verification pass rate, p50/p95/max latency, tool calls and cost per assessment, with the commit SHA. **The run needs an API key, a budget and the SEC User-Agent:** NOT RUN until the team provides them. The recommendation is due Oct 19 and the decision Oct 22.

**Part 3 · Red-flag predicate records (B1, DR-10, I8)**
- AC-3.1 A versioned record per class: Class 1 Item 4.02 (exit), Class 2 Items 1.05 and 2.06 (no new buys for 5 sessions, then expiry), Class 3 statements (SHADOW). Each record states the factual condition, issuer scope, affected period, required sources and fields, action, block/expiry/reset/re-entry conditions, resolution rule and fixtures. The set has a SHA-256.
- AC-3.2 An item finding becomes a red flag only when the filer's item code (submissions metadata) and an issuer-asserted, current, non-negated occurrence in that item's section of the saved filing text agree. An item code alone is not enough (IDEA-032 S1).
- AC-3.3 Fixtures, run through the real assessor, verifier and evidence state, for each enabled item: supported, unsupported (code without text), negated, stale (event older than the record's bound), amended (8-K/A), corrected (a newer revision without the item, read completely) and wrong issuer. Expected outcomes are frozen in the fixture file before the test runs. **Pass: every supported fixture yields exactly the record's directive, and zero unsupported, negated, stale, wrong-issuer or ambiguous fixtures yield a directive that authorizes action.** A corrected fixture releases the latch only after a complete read of the newer revision. An incomplete read keeps or reopens it (R25).
- AC-3.4 Records are published for Keith on Oct 14. Keith's policy tests consume these real records (I8).

**Part 4 · Authority and review jobs**
- AC-4.1 `contract.authority` exposes per-predicate red-flag authority. A predicate acts only if the profile enables it by ID and the profile's set hash equals the loaded set. Anything else stays SHADOW. Unknown IDs or a hash mismatch are refused. Existing profiles behave exactly as before.
- AC-4.2 GAP-28 follow-up (IDEA-035 A4): a statement review attempt is counted only for a result of that statement's own review job. An unrelated accepted result after the due time no longer counts. A test shows both cases, and that a review job still reaches REVIEW_EXHAUSTED after `max_review_attempts`.
- AC-4.3 Restart and replay (A2): the issuer evidence state, including red-flag latches, round-trips through its canonical document. Replaying the same accepted results from the initial state reproduces the same state hash, and replaying an already accepted result is a DUPLICATE with no change.
- AC-4.4 A8 with R25: a resolved red-flag latch makes the name eligible again only after the newer revision is read completely. An incomplete read of a newer revision reopens it.

**Part 5 · Model I/O for the official round log (DR-07, I5)**
- AC-5.1 Every AssessmentResult passes `larp.runtime.schema.assessment_result`. Its `model_io` holds every model request and response (or the SHA-256 and artifact address of the stored bytes), the reasoning summaries, tool calls and results, and an explicit `model_called` flag with a reason when no model was called (rejected request, no usable evidence, deadline).
- AC-5.2 A `ModelTrace.v1` builder gives Keegan's round-log builder a `cot` text built only from provider reasoning summaries and the harness's own recorded steps. It invents no reasoning, and it states "no model call" where there was none. It is tested on ASSESSED, ABSTAIN, UNAVAILABLE and REJECTED_REQUEST results. Testing against Keegan's builder waits for its publication (Oct 14): NOT RUN until then.

**Part 6 · Real-document evaluation (GAP-67 T01)**
- AC-6.1 Run the prepared evaluation (`larp/intelligence/realeval.py`, criteria frozen in `config/intelligence/real_eval_criteria.v1.json`) on a small rights-cleared set of real filings labelled by an annotator who did not implement the verifier. Report PASS, FAIL or INCONCLUSIVE with sample counts. **Needs the annotator:** NOT RUN until then. It informs B8 and B1 and is not a profit claim.

## 2. Results

(Filled in as each part lands, with commit SHAs.)

## 6. Requested shared edits (for Keegan)

(Filled in as each part lands.)
