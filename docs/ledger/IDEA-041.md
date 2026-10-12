# IDEA-041 — Deployment build record: evidence (Yao Zhu)

- Date / author: 2026-10-11 / Yao Zhu (drafted with Claude)
- Status: open (code for all six parts built and tested on `codex/deploy-evidence`, last code commit `8d6e5ce`; live ingestion run, bake-off and T01 NOT RUN pending team inputs, §3)
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

## 2. Results (2026-10-11, Linux, Python 3.13, no disposable PostgreSQL)

Full suite at `8d6e5ce`: **558 passed, 86 skipped (PostgreSQL-only), 904 subtests passed**; red-team suites 95 passed, 2 skipped; foundation `tests/test_contracts.py` 13 passed. This build's new tests: 49 passed. Everything below is synthetic or uses fake transports, unless marked NOT RUN. It is engineering evidence, not market evidence.

| Criterion | Result | Commit | Evidence |
|---|---|---|---|
| AC-0.1 existing tests, red teams, foundation | PASS | `8d6e5ce` | Counts above. Two pinned expectations changed on purpose: the golden traces were regenerated for the new result fields (`red_flag_set_sha256`, `red_flag_checks`, `review_scope`, `model_called`; the diffs show only these fields and the hashes they change), and `test_c01` now also checks the red-flag default (SHADOW). |
| AC-0.2 no secrets or private data | PASS | all | No key, `.env` or source text committed. The test User-Agent uses the reserved `.invalid` domain. Credentials are read from the environment only, and tests assert that they appear in no stored request byte, record or repr. |
| AC-1.1 live refusals | PASS | `b09de21` | `larp.sources.register.live_preflight`; `tests/sources/test_live.py::Preflight`. Today `python -m larp.sources.live preflight` refuses: no terms hashes for the 5 enabled sources, no SEC User-Agent, no artifact root, and the evidence path's live parameters are still null. |
| AC-1.2 terms captures | PASS (tool) / NOT RUN (captures) | `b09de21` | `live terms [--write-register]` stores the page bytes outside Git and records the dated SHA-256 in the register. It edits only those values (tested on a copy). A malformed hash is refused at load. |
| AC-1.3 runner and gap report | PASS | `b09de21` | `LiveRunner`, `PollLog`, `gap_report`; cadence, failure isolation, restart without a burst, PASS/FAIL/INCONCLUSIVE and incident explanations are tested. The real ingestors run under the runner, with the new durable `SQLiteEvidenceStore`. |
| AC-1.4 24 h live run | NOT RUN | — | Needs §3 items 1, 2 and 4, and the host. |
| AC-1.5 licence rows | Listed | — | §6.2. |
| AC-2.1 provider adapters | PASS (fakes) / NOT VERIFIED live | `1ab2bae` | `larp/intelligence/providers.py`; `tests/intelligence/test_providers.py`. |
| AC-2.2 deterministic default and fallback | PASS | `1ab2bae` | `RuleBaselineModel` stays the default. Timeout or error gives UNAVAILABLE, invalid output gives ABSTAIN, and neither proposes a thesis. |
| AC-2.3 budget | PASS | `1ab2bae` | A greedy model stops at exactly 6 tool calls, and the result is marked incomplete. A model sleeping 2 s against a 300 ms deadline returns UNAVAILABLE in under 1.5 s wall time; a 61 s reply on the assessor clock gives MODEL_TIMEOUT. |
| AC-2.4 bake-off | PASS (harness) / NOT RUN (real filings) | `b09de21` | `larp/intelligence/bakeoff.py`, `live bakeoff`. Needs §3 items 1 and 3. |
| AC-3.1 predicate records | PASS | `9a079bf` | `config/intelligence/red_flags.v1.json`, set SHA-256 `b0cdbae023b677184fd83d1b43a0a279805282de31fb8c0a178b293b925ce364`. |
| AC-3.2 code plus section text | PASS | `9a079bf`, `8d6e5ce` | `larp/intelligence/redflags.py`. An unverified item code is never a finding and never lets the evidence look clear (`EVIDENCE_RED_FLAG_UNVERIFIED:`). |
| AC-3.3 fixtures | **PASS: 26 fixtures + 2 sequences; 0 unsupported, negated, ambiguous, stale or wrong-issuer fixtures produced a directive; every supported or amended fixture produced exactly its predicate's directive** | `8d6e5ce` | `tests/intelligence/fixtures/red_flag_fixtures.v1.json` (24 frozen before the first run; 2 inline cases added before running at `8d6e5ce`), `tests/intelligence/test_red_flags.py`. Synthetic text: this shows the paths, not real-world error rates (T01). |
| AC-3.4 publish for Keith | Ready | `9a079bf` | Records, `red_flag_directives` and the I8 notes in §6.3. Due Oct 14. |
| AC-4.1 authority | PASS | `9a079bf` | `contract.authority(...)["red_flags"]`; default SHADOW; an unknown ID, repeated ID or set-hash mismatch is refused; profiles without the key behave as before. |
| AC-4.2 review attempts (GAP-28, A4) | PASS | `ba6fd85` | `tests/intelligence/test_review_scope.py`. Results that predate review scopes (no field) keep the v1.0 rule, so journaled results replay to the same state. The R18 integration test is unchanged and passes. |
| AC-4.3 restart and replay | PASS | `ba6fd85`, `9a079bf` | Canonical state round trip, replay to identical state bytes, duplicates inert, and the red-flag latch survives the round trip. |
| AC-4.4 A8 with R25 | PASS | `9a079bf` | The corrected sequence: an unreadable newer revision keeps the EXIT directive, and a complete read resolves it. |
| AC-5.1 model I/O | PASS | `1ab2bae` | Results pass `larp.runtime.schema.assessment_result`. `model_io` has `model_called`, `requests_started` and `no_model_call_reason`. A deadline result keeps the completed calls for audit and counts the one in flight. |
| AC-5.2 ModelTrace.v1 | PASS (producer) / NOT RUN (against Keegan's builder) | `1ab2bae` | `larp/intelligence/roundlog.py`; `tests/intelligence/test_roundlog.py`. The builder is due Oct 14. |
| AC-6.1 T01 real documents | NOT RUN | — | Needs an independent annotator (§3 item 5). |

### 2.1 Design notes a reviewer should check
- **Red flags need text, not just the item code.** A Class 1 or 2 finding needs both the filer's item code and an issuer-asserted, current, non-negated occurrence in that item's own section. The heading's own clause is excluded, because "Item 4.02 Non-Reliance on …" otherwise reads as an occurrence. Before this build, the metadata code alone latched a finding. This is stricter, as IDEA-032 S1 requires, and fails closed: an unverified code makes the evidence UNKNOWN instead of ADVERSE. That is a behaviour change, recorded in §6.1 as a deviation.
- **One disclosure, one class.** The filing's keyword event of the same kind (RESTATEMENT, CYBERSECURITY_INCIDENT, IMPAIRMENT) and the fired item falsifier carry the same red flag. Without this, a Class 2 disclosure would also leave an unclassed ADVERSE latch, and its 5-session block could never expire.
- **Class 2 expiry is the policy's job.** The evidence state keeps Class 2 latches (the finding stays logged), so `status` stays ADVERSE. The new `review_complete_excluding_timed_blocks` says that only expiring blocks stand in the way. The session-aware policy counts the 5 sessions.
- **No server-side model fallback.** Anthropic's `fallbacks` would answer with a model other than the declared one, so a refusal is recorded as UNAVAILABLE and the deterministic path covers it.
- **Raw HTTP, not provider SDKs.** The exact request and reply bytes are stored before parsing (F-49 (c)), and the dependency lock (Keegan's) is unchanged.
- **The stale bound** (`max_event_age_ms` = 7 days) is an IDEA-041 engineering value for the team to confirm at the Oct 22 cut line.

## 3. NOT RUN, and what each run needs (owners)
1. **SEC contact identity** for `LARP_SEC_USER_AGENT` (Yao Zhu, from the team; due Oct 13). Needed for EDGAR, SEC news, the terms capture's SEC row and the bake-off.
2. **Terms captures** (Yao Zhu, once 1 and the artifact root exist): `python -m larp.sources.live terms --write-register` on the host, then commit the register change. Live mode refuses until every enabled source has a hash.
3. **Model provider, exact model ID, API key and budget**, or the decision to ship the deterministic assessor (team + Yao Zhu; bake-off recommendation Oct 19, decision Oct 22). Then run `python -m larp.sources.live bakeoff --candidate anthropic:<id>:<effort> --candidate openai:<id>:<effort> --price ...` from a pushed commit and record the report and its SHA here. **For the team:** choosing ChatGPT keeps the proposal's declared provider (T-12); choosing Claude is a deviation (IDEA-035 §8.2, GAP-62). Either needs a budget or free credits. Training on Claude outputs stays banned; assessment use is not training (GAP-57).
4. **Evidence-path live parameters** in `config/intelligence/intelligence.v1.json` (`initial_backfill_ms`, `max_clock_skew_ms`, `max_source_staleness_ms`, `result_ttl_ms`, review and job parameters; all `live: null`). Team decision with provenance; until then `--config-mode live` refuses. Then run the 24 h ingestion on the host: `python -m larp.sources.live run --hours 24`, then `report --from ... --to ...` (Yao Zhu with Keegan's host; Gate A, Oct 14–16).
5. **Independent annotator for T01** (team): label a small rights-cleared set of real filings, then run `realeval.py` with its frozen criteria and report PASS, FAIL or INCONCLUSIVE with counts.
6. **Keegan's round-log builder** (Oct 14): test `model_trace` output against it (AC-5.2).

## 6. Requested shared edits and notes for other owners

### 6.1 For Keegan (shared docs; I do not edit them)
- `docs/LEDGER.md`: IDEA-041 status → "open (code for parts 1–6 built and tested at `8d6e5ce`; 24 h run, bake-off and T01 NOT RUN pending team inputs)".
- `docs/INCOMPLETE_WORK.md`:
  - **GAP-23:** append "2026-10-11 IDEA-041: live preflight refuses enabled sources without a terms hash; capture tool ready; captures NOT RUN (needs the SEC contact and the host)".
  - **GAP-24:** append "red-flag staleness bound 7 days, BACKFILL never actionable (IDEA-041)".
  - **GAP-28:** replace the 2026-10-11 follow-up sentence with "done in IDEA-041 (`ba6fd85`): attempts counted only for the statement's own review job; remaining: real source scheduling and measured service guarantees".
  - **GAP-57:** append "adapters for both candidates and the bake-off harness ready (IDEA-041); choice pending".
  - **GAP-67:** item (2) now has its harness (`live bakeoff`); (1) T01 still NOT RUN.
- **Deviations register (GAP-62):**
  - (a) A red-flag finding needs verified item-section text, not only the item code (stricter than the pre-build evidence path, IDEA-032 S1).
  - (b) Foreign private issuers (SK hynix, 6-K) have no red-flag class in v1.0 (no item codes).
  - (c) If Claude is chosen, the assessor provider changes from the declared OpenAI model (T-12).
  - (d) The tool count stays at three (GAP-03, unchanged).
- **Runtime wiring:**
  - Pass the whole job dict, including its `payload`, to `larp.intelligence.agent.build_request(job=...)`. A `STATEMENT_REVIEW_DUE` job then carries its review scope automatically.
  - Use `larp.intelligence.roundlog.model_trace(result)` for the round's `cot` and model-call records; use `max_cot_chars` for your size limit.
  - `SQLiteEvidenceStore` (`larp/sources/store.py`) is the interim durable EDGAR store until the PostgreSQL store takes that role.
  - Live evidence needs `LARP_SEC_USER_AGENT` and `LARP_ARTIFACT_ROOT` in the runtime environment, plus a provider key (`LARP_MODEL_*`, or `LARP_ANTHROPIC_API_KEY` / `LARP_OPENAI_API_KEY` for the bake-off) in the secret store only.
- **Version manifest:** add `config/intelligence/red_flags.v1.json` (set hash above) next to the intelligence config and prompt hashes.

### 6.2 Licence-register rows (GAP-23; enabled sources)

Terms SHA-256 is "pending capture" for every row until AC-1.2 is run on the host. Every row has the same retention: raw permitted bytes and saved text are kept in the artifact store outside Git, by content hash, available for the F-49 audit. Every row is **accepted, pending the terms capture**.

| Source | Endpoint | Basis / licence | Terms URL (checked) | Attribution, exclusions | Cadence and limits |
|---|---|---|---|---|---|
| SEC EDGAR filings | data.sec.gov submissions, www.sec.gov Archives | SEC public dissemination | https://www.sec.gov/privacy (2026-10-10) | "Source: U.S. Securities and Exchange Commission (sec.gov)"; third-party exhibits as filed | 5 min per issuer, ≤ 5 requests/s (SEC limit 10/s), declared User-Agent |
| sec-press | SEC press RSS | SEC_PUBLIC_DISSEMINATION / US-GOV-SEC-WEBSITE | https://www.sec.gov/privacy (2026-10-10) | As in the register; excludes third-party material, images, attachments | ≥ 10 min, 1 page |
| fr-bis | Federal Register API, BIS documents | EXPRESS_REPRODUCTION_PERMISSION / NARA-FEDERAL-REGISTER-REUSE | archives.gov Federal Register "about" (2026-10-10) | As in the register; excludes incorporated third-party standards, logos, images | ≥ 15 min, ≤ 3 pages |
| fr-public-inspection | Federal Register public inspection | same as fr-bis | same | same | ≥ 15 min, 1 page |
| doj-press | DOJ press API | EXPRESS_COPY_DISTRIBUTE_PERMISSION / DOJ-LEGAL-POLICIES | https://www.justice.gov/legalpolicies (2026-10-10) | As in the register; excludes third-party text, images, seals | ≥ 10 min, ≤ 3 pages, page size 50 |
| ec-press | EC press corner RSS | OPEN_LICENCE / CC-BY-4.0 | https://commission.europa.eu/legal-notice_en (2026-10-10) | CC BY 4.0 attribution; items with contrary or third-party notices excluded per item | ≥ 15 min, 1 page |

FTC stays disabled: its feeds returned 404 (2026-10-10), and no permitted path with failure handling has been verified.

### 6.3 For Keith (I8 consumer; reviewer)
- Use `larp.integration.contract.red_flag_directives(record, profile)` on accepted EvidenceContext records. It returns one directive per (predicate, accession) with `kind` EXIT or BLOCK_NEW_BUYS, `block_sessions`, `restarts_block` and `latched_ms`. Enable the predicates in the live profile with `red_flag_authority: {"set_sha256": "b0cdbae0…", "enabled": ["RF1-ITEM-4.02", "RF2-ITEM-1.05", "RF2-ITEM-2.06"]}`. Without it, all stay SHADOW.
- Class 2 block start, expiry after 5 sessions and reset are policy state. For entry gating while only a Class 2 block remains, read `review_complete_excluding_timed_blocks` (fresh at consumption, like `review_complete`). An 8-K/A never restarts a running block.
- A resolved latch drops the directive (A8). The policy's existing `EVIDENCE_LATCH_RESOLVED` unblocking applies.
- `larp.strategy.assessments.consume` accepts only `AssessmentResult.v1`. The evidence producer emits v2, and the integrated path uses EvidenceContext.v1 instead. Brief I5 lists `consume` as a validator; please confirm it is not on the live path, or extend it.
- Policy tests should use the real records and the fixture file `tests/intelligence/fixtures/red_flag_fixtures.v1.json`.

## 2026-10-12 PR #15 remediation — prospective criteria (IDEA-043)

Before executing changed code: SQLite-backed assessor/bake-off reads must work across the assessor worker boundary with serialized transactions; nested provider objects must be closed while accepting real tool arguments and verified claims; exact request/reply bytes survive overflow/deep-JSON errors. Cross-references cannot start/end an item section; supported same-paragraph and relied-on wording work; amended event freshness uses the source's original report date or refuses unknown provenance. Torn poll tails preserve bytes and subsequent records/cadence. Terms capture uses the supplied SEC contact; review jobs without payload refuse; logged cadence governs gap reports; HTTP transport failures are reported separately from schema-invalid model replies. Regression fixtures use synthetic data and no credentials. Full suite and focused tests required; real providers, T01 and 24-hour live ingestion remain NOT RUN.

Schema source checked 2026-10-12: https://platform.claude.com/docs/en/build-with-claude/structured-outputs (raw schemas; additionalProperties false on objects).
