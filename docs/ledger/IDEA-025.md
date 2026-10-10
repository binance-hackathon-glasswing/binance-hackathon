# IDEA-025 — Evidence-agent build record (Yao Zhu)

- Date / author: 2026-10-10 SGT / Yao Zhu (SYZ) requested; implemented by Claude (Claude Code) on branch `codex/evidence-agent`, started from the kickoff commit `e10eae2` on `origin/codex/engine-foundation`.
- Status: open — implementation and prospective criteria committed; **results NOT RUN at the criteria commit** (appended in §9 after the pushed code is run). Not an adopted strategy, model choice or live authorization. Optional model experiments (trained evidence model, fusion) are **not approved and not validated**.
- What: point-in-time EDGAR ingestion, a verified extraction/severity baseline, a bounded evidence agent behind `assess(AssessmentRequest.v1) -> AssessmentResult.v1`, provider-neutral model adapters, a result gate, a feature export and a labelled synthetic evaluation pack.
- Why: PARALLEL_BUILD.md prompt 01; IDEA-013 R3/R5/R6 (GAP-63), IDEA-014 §1.3 (novelty, no invented consensus), IDEA-015 A.1/A.2 (assessment-only schema, durable filing queue), IDEA-021 ENG-02/08/11 and R07/R12, G-50 (budget), G-51 (falsifiers), G-53 (claim verification), GAP-24/26/28.
- Cost / risk: offline code and synthetic data only. No credential read, no network call made, no model provider called, no ai-seeds log, no wallet or signer code. Main risk: synthetic fixtures are written by the same author as the code, so passing them is weak evidence about real filings (§5.4).
- Links: PARALLEL_BUILD.md; IDEA-007 §1/§3/§7, IDEA-008 §1/§4/§5, IDEA-013, IDEA-014, IDEA-015, IDEA-021, IDEA-023, IDEA-024; G-04/05/06/50/51/53; GAP-24, GAP-26, GAP-28, GAP-57, GAP-63.

## 1. Scope, ownership and ports

Files (owner paths only): `larp/intelligence/`, `tests/intelligence/`, `config/intelligence/`, `tools/edgar_fetch.py`, plus this record, its LEDGER row and the progress appendix of `docs/build/01-evidence-agent.prompt.txt`. No change to `larp/contracts.py`, `pytest.ini`, dependencies, the lock file, `docs/official/kit/` or `vendor/`. No new dependency: the package is standard library plus `larp.contracts`.

Ports, all through canonical `Document` values:

| Port | Here | Owner of the real implementation |
|---|---|---|
| `assess(request: Document) -> Document` | `EvidenceAssessor.assess` (`agent.py`); structurally matches `Assessor` in Keegan's `larp/ports.py` (not imported: unmerged branch) | Yao Zhu |
| `commit(batch: Document) -> Document` | ingestion commits `IngestionBatch.v1` (records + jobs + cursor in one batch); the gate's state and review jobs commit as `EvidenceStateBatch.v1` | Keegan: store adapter mapping both batches into CommitBatch/jobs |
| `read_cursor`, `records`, artifact `put/get` | read side of the same store; content-addressed artifact sink for raw and saved text bytes | Keegan (`LARP_ARTIFACT_ROOT`) |
| `FilingSource` | `EdgarHttpSource` (opt-in, read-only) and `FakeFilingSource` | Yao Zhu |
| `EvidenceModel.step(ModelRequest.v1) -> ModelResponse.v1` | rule baseline, scripted fake, hosted (OpenAI-compatible codec), local checkpoint | Yao Zhu; provider choice is GAP-57 |

`AssessmentRequest.v1` / `AssessmentResult.v1` carry every field in Keegan's `docs/build/runtime-contracts.md` vocabulary (checked against `origin/codex/runtime-audit-platform` @ `955cfc2`); additions are additive (`context`, `source_health`, `assessment_key`, `status`, `reasons`, `findings`, `event_findings`, `freshness`, `proposed_thesis`, `instrument_scope`, `budget_used`, `cost`). Jobs use the runtime job fields (`lane`, `due_ms`, `valid_until_ms`, `max_attempts`, `missed`, `calendar_id`, `tzdata_version`, `payload`). `tests/intelligence/test_agent.py` re-implements that branch's request/result validator checks to test compatibility without importing it.

The fakes (`fakes.py`) are owner-local and explicitly temporary; each sets `synthetic = True` and `require_real` refuses them.

## 2. Design decisions

**Ingestion (`ingest.py`, `edgar.py`, `text.py`).** Per-issuer durable cursor: floor, watermark, known accessions with content hash and revision, pending retries, dead letters, health. One poll commits records, assessment jobs and the new cursor in one batch, so the cursor never advances past non-durable work (IDEA-013 R3). Deduplication is by accession. Everything at or after the floor is considered, so a filing first listed after a later one is ingested and flagged `late_delivery`. An outage commits only a health change; catch-up ingests each missed filing once. Every record keeps `original_ms` (`acceptanceDateTime`, parsed with its stated offset; raw string kept because IDEA-004 T1's EDT/EST check is open), `retrieved_ms` and `available_ms` = our first retrieval (never backdated), the listing hash, and per document raw SHA-256, saved-text SHA-256, byte length, decoder and lossiness. A recheck that finds changed bytes writes revision n+1 linked to the superseded hash; earlier records are never rewritten. Backfill takes an explicit window and leaves the live watermark alone. Forms map by filer class: 8-K/10-Q/10-K (+/A) for domestic filers, 6-K/20-F (+/A) for foreign private issuers; a periodic/current form of the other class is reported as `unexpected_forms`, other forms (e.g. Form 4) are ignored. The submissions response must match the registered CIK and entity name.

**Issuer mapping (`issuers.py`, `config/intelligence/issuers.v1.json`).** Issuer, security and token are separate identities. SK hynix has `XKRX:000660` (KRW common) and `XNAS:SKHY` (US listing; type and depositary ratio UNVERIFIED, no conversion); Alphabet has two share classes; every token→underlying link is UNVERIFIED (F-95 gives only a derived per-share `referencePrice`). Per-share facts get a security scope only when unambiguous; comparisons across currencies, instruments or fiscal/calendar period bases are INCOMPARABLE.

**Text (`text.py`; fixes IDEA-013 R5/R6).** Table cells are joined with " | ", rows with newlines; spacer cells are dropped and a lone `$`, `(`, `)` or `%` is merged into its number. Script/style and the hidden inline-XBRL header are dropped; other hidden text is kept as untrusted data. The saved form is NFC, `\n`-only UTF-8, and `text_sha256` is the SHA-256 of exactly those bytes. Latin-1/ASCII labels decode as windows-1252 (WHATWG); undeclared invalid UTF-8 falls back to windows-1252 with lossiness recorded. `tools/edgar_fetch.py` now uses this extractor and `write_bytes` of the same bytes it hashes; reports are written as explicit UTF-8.

**Verified extraction/severity baseline (`facts.py`, `verify.py`).** Deterministic extraction of revenue, net income, operating income, gross margin and diluted EPS from sentences and tables, with exact spans, period spans, scale spans, exact Fraction values, power-of-ten scale and written precision; 8-K item codes from metadata; keyword events (restatement/non-reliance, cybersecurity incident, delisting, impairment with a negation guard, CEO/CFO departure). A claim is accepted only if its span is the exact substring at its offsets, names the metric/event, states every number (period years and dates excluded), states scale and currency, and its period parses from the cited period span. CONSENSUS/estimate kinds are always rejected. Agreement is rounding-aware: two statements agree within half a unit of the coarser one's last written digit, so "$35.1 billion" agrees with "35,082" (millions). Severity is a mechanical map from item codes, keyword events and comparisons in config; it is not a validated model.

**Bounded agent (`agent.py`, `tools.py`).** Validates identity, cutoff, context hash, declared budget (≤ 6 tool calls, ≤ 60 s; config can tighten, never loosen G-50) and tool allowlist before any model call. Three read-only tools over the point-in-time index (records available at the cutoff, latest revision): `fetch_document` (exhibit by accession and name), `prior_context` (facts for one metric from earlier filings and verified context), `compare_facts` (all comparable pairs for one metric). Tools take identifiers, never URLs, so filing text cannot redirect them; any other name is TOOL_NOT_ALLOWED and still consumes budget. The harness computes gaps (unread exhibit, unchecked prior, uncompared metric); the model chooses the next tool or finishes. Unsupported claims, conflicting reported values (including against prior filings), invalid or trade-bearing model output → ABSTAIN; model timeout/error or exhausted time → UNAVAILABLE. ABSTAIN/UNAVAILABLE never propose a thesis update. Missing prior guidance is recorded as `PRIOR_MISSING:…` and never filled in. Confidence is an uncalibrated ordinal label (`calibrated: false`), never a probability. The public rationale (≤ 3 sentences) is generated from verified structured fields only, never from model text. Falsifiers are evaluated as FIRED / NOT_FIRED / UNKNOWN / NOT_APPLICABLE; any UNKNOWN keeps the thesis UNKNOWN rather than INTACT. Review requests are evidence-lane jobs with no trade command. `model_io` keeps every model request/response and tool call (F-49 (c), G-06), including untrusted output that was rejected.

**Gate (`gate.py`).** Pure reducer per issuer: rejects stale context (a result computed for a thesis that has since moved), wrong profile, expired, out-of-order, duplicate or wrong-issuer results. `evidence_gate` is CLEAR only after a fresh, complete, conflict-free ASSESSED result with no adverse finding; ADVERSE while any accepted adverse finding or fired falsifier is unresolved; UNKNOWN otherwise. Timeouts and abstentions never produce CLEAR and never remove findings, so a timeout cannot re-enable new exposure (IDEA-021 R07). Verified filer/keyword events count even when the model abstains. How findings are resolved and what the gate means for orders is Keith's policy; this module emits no actions.

**Models (`models.py`).** All adapters return `ModelResponse.v1` with status, raw-response hash, usage, cost and basis, and latency on the injected clock. The hosted adapter requires an allowlisted HTTPS endpoint, a pinned revision (not "latest"), the pinned prompt hash and a credential from the runtime secret store; the credential never enters a document or repr. It is **NOT VERIFIED against any live provider**. The local adapter refuses weights whose SHA-256 differs from the pinned checkpoint. The rule baseline's identity hash covers the code that makes its choices.

**Training (`training.py`) — NOT RUN.** No rights-cleared labels, committed experiment record, base checkpoint (id, revision, SHA-256, licence), dataset manifest or compute budget exists; GAP-57 (model track) is undecided. `check_training_manifest` returns NOT_RUN with the missing items and rejects Claude-generated or synthetic-pack labels and a Claude teacher (Anthropic AUP; IDEA-007 §1). No model was trained or fabricated.

**Features (`features.py`).** `FeatureRow.v1` per result for Keith's optional fusion research: as-of and availability times, status, impact ordinal, severity, claim/conflict/novelty/falsifier counts, finding and missingness codes, staleness, confidence label (uncalibrated) and the gate value. No trade or size field. Rule-baseline rows have no fitted parameters; hosted/local model rows inherit knowledge-cutoff risk (I-67) and must be used out-of-fold.

## 3. Backlog items addressed (Keegan removes lines in the integrating change)

- GAP-63: R3 (durable ingestion and deduplication), R5 (table boundaries), R6 (portable saved-byte hashes) implemented with tests; R4 (assessment-only schema) implemented as the evidence-only result plus the gate, with no action field. R1/R2/R7/R8 belong to others and are untouched.
- GAP-26 (claim-verification quality): unsupported-claim acceptance, citation correctness and numerical interpretation are measured on the synthetic pack with frozen thresholds; real-data thresholds remain open.
- GAP-24 (point-in-time contract): live ingestion part implemented (`original_ms`/`retrieved_ms`/`available_ms`, hashes, revisions); historical-availability reconstruction for replay remains open.
- GAP-28 (scheduling/memory contracts): evidence job requests, review requests and thesis-context versioning implemented on this side; durable scheduling, priority service guarantees and queue limits are Keegan's.

## 4. Prospective acceptance criteria (deterministic tests; written before any run)

Pass only if every test below passes, the 13 foundation tests still pass, and `git diff --check` is clean. These are engineering checks, not a market experiment.

| Acceptance item (prompt 01) | Test(s) |
|---|---|
| duplicate and late filing delivery | `test_ingest`: duplicate delivery, replayed/tampered batch, lost acknowledgement then re-poll, late delivery flagged and not backdated |
| outage then catch-up | `test_ingest.test_outage_then_catch_up` |
| HTML tables | `test_text` table tests; `test_edgar_tool`; `test_facts_verify` table extraction and last-cell rule |
| UTF-8 hashes | `test_text.PortableHashTests`; `test_edgar_tool.test_recorded_hash_equals_hash_of_saved_file_bytes`; artifact hashes in `test_ingest` |
| contradictory filings | `test_facts_verify` cross-filing conflict; `test_agent` justified abstention |
| missing prior guidance | `test_agent.test_missing_prior_guidance_stays_missing_and_no_consensus_is_invented` |
| stale contexts | `test_agent` stale-context requests; `test_gate` late result for an obsolete context |
| tool errors | `test_agent` missing/corrupted artifact, reader exception, disallowed tools, tool budget |
| prompt injection | `test_agent.InjectionAndAuthorityTests` |
| model timeout | `test_agent` timeout/error/invalid output; `test_gate` timeout never stays CLEAR |
| tool selection + thesis revision trace | `test_agent.test_autonomous_tool_selection_and_thesis_revision` (+ golden trace, §8) |
| justified abstention trace | `test_agent.test_justified_abstention_on_contradiction_with_prior_filing` (+ golden trace) |
| no policy/signer commands reachable | `test_boundaries` (imports, references, tool registry, fakes refused); recursive forbidden-key checks on results, jobs and feature rows |
| jobs/state through ports | `test_ingest` job vocabulary; `test_gate.test_state_and_review_jobs_persist_through_the_store_port` |
| issuer mapping (8-K/10-Q/10-K, 6-K/20-F; KRX/US listing/token distinct) | `test_edgar.IssuerMappingTests`; foreign-issuer ingestion and agent tests |

Commands: `python -m unittest discover -s tests -v` on Python 3.12, and `python -m pytest -q -p no:cacheprovider` where pytest is installed. Result states: PASS / FAIL with output; nothing is re-labelled after the run.

## 5. Synthetic evaluation — pre-registration (not an EXP; no EXP ID allocated, PARALLEL_BUILD.md)

1. **Question.** On a labelled synthetic pack, does the bounded agent (≤ 6 tool calls) find comparisons, contradictions and falsifiers that the simple verified-extraction baseline (0 tool calls) misses, without accepting unsupported claims?
2. **Pack.** `larp/intelligence/scenarios.py` (SHA-256 `18851b7e74cef61ca552e8dbe87c13c3168b1ea5d0ef9ff1d80b3d9022e92da9` at this commit): 10 synthetic filings of two fictional issuers and 17 labelled cases (13 run by both variants, 4 adversarial model cases run by the agent: trade field, fabricated claim, consensus claim, timeout). Claude-authored and evaluation-only; never training data.
3. **Thresholds** (`config/intelligence/eval_thresholds.v1.json`, SHA-256 `3a1c9d8ac93f63c71f9e8af2b9fb09d91451098b63df9d3f4b68d0ecd2db9106`, frozen before any run). Agent: span accuracy ≥ 19/20, numerical correctness = 1, unsupported-claim acceptance = 0, relevant-event recall ≥ 9/10, abstention recall = 1, false abstention ≤ 1/10, stale-result rejection = 1, max tool calls ≤ 6, max elapsed ≤ 60 000 ms (fake clock). Baseline: numerical correctness = 1, 0 tool calls. Comparison (comparison accuracy = share of labelled novelty, finding, falsifier, thesis-status and status expectations met): SUPPORTED_ON_SYNTHETIC_PACK if agent − baseline ≥ 1/4 with ≥ 20 expectations and zero unsupported acceptance; NOT_SUPPORTED if the gain is smaller; INCONCLUSIVE with fewer expectations.
4. **Limits.** Synthetic, small and written alongside the code: a pass shows the harness behaves as specified on these inputs, not that it generalizes to real filings, beats a hosted LLM, or improves trading. Simulated latencies are on a fake clock; wall-clock times are measured but not thresholded. No held-out real-data evaluation is run: real filing rights are clear (EDGAR, IDEA-001 §15) but labelled real cases, a frozen real-data protocol and a post-cutoff slice do not exist yet (GAP-21/26).
5. **Fallback.** If a check fails, the failure is recorded here with the output; a code defect may be fixed by a new commit and the evaluation re-run, with both runs reported. Thresholds are not edited.

## 6. Model and data provenance

- Real data: none used. The EDGAR adapter and the research tool were not run in this work; the registry's CIKs/forms come from the 2026-10-08 run recorded in IDEA-001 §15 / IDEA-009 C.2.
- Synthetic data: `scenarios.py` (fictional issuers, CIKs 9900001/9900002 are placeholders, fictitious figures, each document marked as a fixture).
- Models: rule baseline (deterministic code, no weights, no prompt use, zero provider cost); scripted fakes in tests; hosted and local adapters exercised only with fake transports and a synthetic weights file. No provider, checkpoint, teacher or output-use rights are assumed.
- Prompt: `config/intelligence/prompts/assessor.v1.txt`, SHA-256 pinned in `intelligence.v1.json`.

## 7. Inputs needed only for real integration (not requested now)

- `LARP_SEC_USER_AGENT`: a real name/contact for the SEC User-Agent (Yao Zhu); the adapter refuses placeholders.
- Model provider, exact model/snapshot revision, endpoint host, price-list source, permitted output and training use, inference budget; then `LARP_MODEL_PROVIDER`, `LARP_MODEL_ID`, and `LARP_MODEL_API_KEY` (hosted) or `LARP_MODEL_PATH` (local), supplied through the runtime secret store (GAP-57/D-03). The wallet key and `AI_SEEDS_SECRET` are never needed here.
- Live values for every `parameters.*.live` entry in `config/intelligence/intelligence.v1.json` (initial backfill, clock skew, source staleness, result TTL, reassessment/retry delays, job validity/attempts); live startup fails until set with provenance.
- Team review of the severity map and default falsifiers before any live use (they are mechanical, not validated); for training: rights-cleared labels, a committed experiment record, base checkpoint and compute (`training.py` list).
- Keegan: store adapter for `IngestionBatch.v1` / `EvidenceStateBatch.v1`, artifact root, scheduler consumption of evidence/review jobs. Keith: policy use of `evidence_gate`/`unresolved_adverse` and finding resolution (re-entry after an adverse finding remains open, IDEA-012 §9).

## 8. Example documents

`python -m larp.intelligence.demo --out tests/intelligence/golden` writes two traces: `trace-tool-selection-thesis-revision.json` (successful assessment) and `trace-justified-abstention.json` (rejected/abstained). They are committed with the results and checked byte-for-byte by a regression test added in the same results commit.

## 9. Results

NOT RUN at the criteria commit. Appended below after the pushed code is run.

### 9.1 2026-10-10 runs (Python 3.12.1, macOS; standard-library unittest)

Environment: the project's locked `binance-hackathon` conda environment does not exist on this machine, so tests ran with an unrelated local conda environment's Python 3.12.1 (standard library only; this package needs nothing else) and pytest 9.0.3 from the base Anaconda Python 3.14.6 with plugin autoload disabled. This is not evidence for the locked environment (Keegan's W09/GAP-45 remains open).

1. **Criteria commit `6442698`, first run: FAIL** — 118 tests, 7 failures, 6 errors. Causes: (a) `<tr>` emitted a newline at both start and end, so table rows were separated by blank lines and never formed a table block — no table fact was extracted, which also broke the tool-sequence test (gross-margin facts exist only in the table) and the evaluation (agent span accuracy 7/19; baseline had no numeric observations); (b) the scripted fake overshot its timeout by 1 ms (agent `max_elapsed_ms` 60 001 > 60 000); (c) two tests expected byte-identical replays (same ingestion batch; same assessment key) to be rejected, while the store and gate correctly return IDEMPOTENT/DUPLICATE; (d) one test matched the word "probability" in the explanatory text "not a probability" instead of checking for probability fields.
2. **Fix commit `2a0abc3`.** Code fix for (a); the fake now times out at exactly the remaining budget, like a transport timeout set to it (b); tests corrected for (c)/(d) — the competing poll and the late result now differ from the accepted ones; the probability check inspects keys. **Process slip:** these fixes were run once locally before they were committed and pushed; the evidence of record below comes only from runs of pushed commits. From pushed `2a0abc3`: 118 tests OK; pytest 118 passed; evaluation PASS on every frozen check.
3. **Review of the `2a0abc3` evaluation report** (all checks passed; nothing in the thresholds covers this): a filing with injected instructions reached evidence gate CLEAR, and the 0-tool baseline reached CLEAR on the 10-Q without checking earlier filings. **Fix commit `b1f7016`**: the gate stays UNKNOWN for `UNTRUSTED_INSTRUCTIONS_IN_EVIDENCE` and for any numerical fact whose prior was not checked; new test `test_untrusted_instructions_or_unchecked_priors_cannot_be_clear`. No threshold or label was changed.
4. **Evidence of record, pushed `b1f7016`:** `python -m unittest discover -s tests` → **119 tests OK** (including all 13 foundation tests in `tests/test_contracts.py`); `python -m pytest -q -p no:cacheprovider` → **119 passed, 489 subtests passed**; `binance_test.py` not collected. `python -m larp.intelligence.evaluation` → **acceptance PASS** (report `tests/intelligence/evidence/eval-report-b1f7016.json`, pack digest `42789e45…7fd69`, thresholds SHA-256 `3a1c9d8a…db9106` = the frozen file):

| Metric (threshold) | Agent (≤ 6 tools) | Baseline (0 tools) |
|---|---|---|
| Supporting-span accuracy (≥ 19/20) | 19/19 | 4/19 |
| Numerical correctness (= 1) | 19/19 claims checked | 4/4 |
| Unsupported-claim acceptance (= 0) | 0/3 planted (trade field, fabricated span, consensus claim) | not run (no adversarial cases) |
| Relevant-event recall (≥ 9/10) | 7/7 | 7/7 |
| Abstention recall (= 1) / false abstention (≤ 1/10) | 6/6 / 0/11 | 1/2 (misses the contradiction) / 0/11 |
| Stale-result rejection (= 1) | 4/4 probes (duplicate, obsolete context, expired, wrong profile) | not run |
| Max tool calls (≤ 6) / max elapsed, fake clock (≤ 60 000 ms) | 4 / 60 000 (the timeout case) | 0 / 0 |
| Comparison accuracy (gain ≥ 1/4, ≥ 20 expectations) | 40/40 | 25/36 |

Comparison verdict: **SUPPORTED_ON_SYNTHETIC_PACK** (gain 11/36 ≈ 0.31). Meaning: on these 17 synthetic cases the tool loop found the guidance cut, the beat versus prior guidance, the cross-filing contradiction and the falsifier states that the single-pass baseline could not see, at no unsupported-claim cost. It is not evidence about real filings, hosted-model behaviour or returns (§5.4).

5. **Measured costs:** rule baseline — zero provider cost, no tokens; wall-clock per `assess()` call on the development Mac 0.09 ms min, 0.98 ms median, 8.3 ms max over 30 runs (fake-clock model latencies are simulated, not measured). No hosted or local model call was made, so no token cost or provider latency exists to report.
6. **Example documents:** `tests/intelligence/golden/trace-tool-selection-thesis-revision.json` (SHA-256 `c8cca285…8e10`: 4 tool calls — fetch exhibit, prior revenue, prior gross margin [NO_PRIOR], compare revenue; findings GUIDANCE_LOWERED and REPORTED_ABOVE_PRIOR_GUIDANCE; thesis v3 INTACT → v4 BROKEN; gate ADVERSE; state and review job committed through the store port; baseline on the same input: thesis UNKNOWN, no comparison finding) and `trace-justified-abstention.json` (SHA-256 `6069e72c…4603`: 3 tool calls; 8-K/A revenue contradicts the original 8-K found through prior context → ABSTAIN CONFLICTING_EVIDENCE, no thesis update, CONFLICT_RESOLUTION review job). `tests/intelligence/test_golden.py` (added with these files) checks both byte for byte.
7. **Outcome:** §4 engineering criteria PASS at `b1f7016`; §5 synthetic evaluation PASS and SUPPORTED_ON_SYNTHETIC_PACK. Still NOT RUN: trained evidence model, any live EDGAR/model run, real-data held-out evaluation, integration with Keegan's store/scheduler and Keith's policy. Nothing here adopts a model, a severity map or a trading use.
8. **Verification of the results commit `947af5f`** (pushed before running): unittest **120 tests OK**, pytest **120 passed, 491 subtests passed** — the 119 above plus `test_golden.py`, which regenerated both traces byte for byte. `git diff --check` clean.

- 2026-10-10 correction (SYZ, drafted by Claude): **model training is out of scope**, not a gated future step. The engine design is based on IDEA-021/022, and IDEA-021 §8.1 places model training outside the build ("Policy selection, comparative policy experiments, model training and new-source licensing are outside this estimate"; §8.5 defers it first). `larp/intelligence/training.py` and its tests are removed. The §2 "Training — NOT RUN" paragraph, the §7 training inputs and the "Add a small trained evidence model" path of prompt item 4 no longer apply. `LocalCheckpointModel` stays only as an adapter for running an already-existing local model with a pinned weight hash; none is selected. The synthetic pack remains evaluation-only and must never be used as training data. The golden traces are regenerated because the rule baseline's identity hash covers `models.py`.

### 9.2 PR #4 review (Keegan, 2026-10-10, at `33c2f40`) — fixes and prospective criteria

Review: 11 inline findings (7 P1, 4 P2) plus the process note on §9.1. The §9.1 process-slip disclosure stays as written. These fixes follow the rule: they are committed and pushed before any of the changed code runs, and §2 is not rewritten. Where a fix changes a design statement in §2, the change is listed here.

| # | Finding | Change | Deterministic test(s) |
|---|---|---|---|
| R1 (P2) | Malformed nested claim fields crash `assess()` | `verify.claim_schema_error`: full nested schema (field set, text fields, scale ints, `source` object, span shapes, `range`), checked before any field is used. `_verify_claims` also turns any remaining exception into a rejected claim. | `test_facts_verify.test_malformed_nested_fields_are_rejected_before_use`; `test_agent.ClaimBindingTests.test_malformed_nested_claims_abstain_instead_of_crashing` (ABSTAIN, no thesis, reassessment request) |
| R2 (P1) | A span from a prior filing can be credited to the current record | With records, `verify_claim` requires the claimed record to hold the cited document and takes all provenance (record, accession, document name, times) from it. A claim with no record is attributed to the record holding its document. A verified claim must still come from an assessed filing. Period/scale spans must be in the same document: on the same line for prose; for a table cell, its own column header and the table's scale line, located as the extractor locates them (`facts.table_cell`). | `test_facts_verify` provenance, period/scale binding; `test_agent.test_a_prior_filing_span_cannot_be_passed_off_as_current_evidence` |
| R3 (P1) | Negated events verified by keyword alone | The verifier applies the extractor's negation guard to the source text before each match (`facts.negated`): `EVENT_NEGATED` | `test_facts_verify.test_negated_events_are_not_verified`; `test_agent.test_a_negated_event_claim_abstains_and_creates_no_adverse_finding` (no adverse finding in the result or gate) |
| R4 (P1) | Per-share rows scaled by "(In millions, except per share data)" | `facts.table_scale`: per-share rows keep scale 0 under an "except … per share" exception and give no fact in a scaled table without one. The verifier checks table claims against the same rule; prose per-share claims must have scale 0. | `test_facts_verify.PerShareScaleTests` (mixed revenue/EPS table, equivalent prose, no conflict, wrong scale rejected) |
| R5 (P1) | Updates classified against superseded guidance | `tools.guidance_basis`: only the latest guidance issued before the assessed filing (latest revision at the cutoff) is the basis. Every pair is still compared and kept with `applicable`/`not_applicable` for audit. Disagreeing guidance issued at that latest time gives no basis (`PRIOR_GUIDANCE_CONFLICT:…` missingness, CONFLICT_RESOLUTION review, gate not CLEAR). | `test_agent.GuidanceBasisTests` (36.0 → 32.0 → 34.0: RAISED only, falsifier NOT_FIRED, thesis INTACT; contemporaneous conflict) |
| R6 (P1) | Local inference not bounded while running | `LocalCheckpointModel` runs inference in a spawn worker process, terminated at the deadline (late replies cannot be read; next step starts a fresh worker). `assess()` runs the whole assessment (reads, tools, model) in a worker thread abandoned at the request deadline with an UNAVAILABLE `ASSESSMENT_DEADLINE_EXCEEDED` result. The abandoned worker makes no further model or tool call. | `test_models.test_a_blocked_local_inference_is_stopped_at_the_deadline`; `test_agent.DeadlineTests` (blocked store read) |
| R7 (P1) | Feature availability dated from the cutoff | Results carry `started_ms`/`completed_ms`; `FeatureRow.available_ms` = `completed_ms` and `as_of_ms` = cutoff. | `test_gate.test_feature_availability_is_completion_time_not_cutoff` (cutoff < start < completion) |
| R8 (P2) | Hosted revision never sent | The request's `model` is the pinned `revision` (the provider's immutable snapshot ID; aliases containing "latest" or "default" are refused). A reply naming another model → ERROR `SERVED_MODEL_MISMATCH`. | `test_models.test_the_pinned_revision_selects_the_snapshot_and_a_different_served_model_is_rejected` |
| R9 (P2) | Hosted response bytes discarded | The hosted adapter requires an artifact sink. It stores the exact request payload (no credential) and every reply's bytes, malformed or rejected included, before parsing. `ModelResponse.v1` gains `raw_response_artifact`, `request_payload_sha256`/`_artifact` and `served_model`. | `test_models.test_request_and_reply_bytes_are_recoverable_and_exclude_the_credential` |
| R10 (P2) | Backfill ignores `filings.files` | `EdgarHttpSource.list_filings(cik, window)` fetches the historical submissions files whose date range may intersect the window (each range widened by a day per side; names validated before use as a URL; at most 20 requests). Per-file status and hash are recorded; any unread file makes the outcome `PARTIAL_HISTORY`. | `test_edgar` history merge/window tests; `test_ingest.test_backfill_reads_historical_submissions_files` (fake HTTP; filing only in a history file; 503 → PARTIAL_HISTORY, then OK) |
| R11 (P2) | Pinned hashes fail on a Windows CRLF checkout | `.gitattributes` in `config/intelligence/`, `larp/intelligence/` and `tests/intelligence/` (`*.py`, `*.json`, `*.txt` → `text eol=lf`). These are owner directories, so the shared root file is untouched pending Keegan. Integrity checks unchanged. | `git check-attr` and a fresh clone with `core.autocrlf=true` (below) |

**Prospective criteria (written before any run of the changed code):**

1. `python -m unittest discover -s tests` and `python -m pytest -q -p no:cacheprovider`: every test passes, including the 13 foundation tests and every test named above.
   - Exception: `test_golden` is expected to fail on the first run. The rule baseline's identity hash covers `facts.py`, `verify.py` and `models.py`, and results and responses gain fields, so the committed traces must be regenerated.
   - The regenerated traces may differ only in identity hashes, the new fields (`started_ms`, `completed_ms`, `applicable`, response artifact fields, feature `available_ms`) and digests derived from them.
   - Statuses, tool sequences, findings, falsifier states and thesis transitions must be unchanged. Any other difference is a FAIL to investigate.
2. `python -m larp.intelligence.evaluation`: **PASS on every frozen threshold, unchanged**. The pack (`scenarios.FILINGS`/`EVAL_CASES`) is not modified; the new fixtures live in the tests only. The SUPPORTED_ON_SYNTHETIC_PACK verdict must hold.
3. Windows-style checkout: a fresh clone of the pushed fix commit with `git -c core.autocrlf=true clone` must pass the whole suite. The same procedure on `33c2f40` is run as the control and is expected to fail as the review describes. This is run on macOS: `core.autocrlf=true` converts on checkout on any platform. It is not a Windows run.
4. `git diff --check` clean.

**Results (runs of pushed commits only; Python 3.12.1 unittest and pytest 9.0.3 on Python 3.14.6, as in §9.1, so not the locked environment, W09/GAP-45):**

1. **Fix commit `35c60b4`, first run:**
   - Every test passed except the expected `test_golden` pair: unittest 139 tests, 2 failures; pytest 2 failed, 139 passed.
   - 21 new tests: 7 in `test_facts_verify`, 4 in `test_models`, 6 in `test_agent`, 2 in `test_edgar`, 1 in `test_ingest`, 1 in `test_gate`.
   - Traces regenerated from `35c60b4` and compared leaf by leaf with the committed ones. The only differences: the rule baseline's code-identity hash (`checkpoint_sha256` `f7b6eb4e…` → `b324be5b…`) and the ids/digests derived from it (`model_hash`, `assessment_key`, `result_id`, finding/job/batch ids, the `compare_facts` result hash), plus the new fields (`applicable`, all `true` in both traces; `started_ms`/`completed_ms`; `raw_response_artifact`, `request_payload_sha256`/`_artifact`, `served_model`). Statuses, tool sequences, findings, falsifier states and thesis transitions are unchanged. Criterion 1 is met.
2. **Evaluation at `35c60b4`: PASS** (`tests/intelligence/evidence/eval-report-35c60b4.json`, SHA-256 `5a43ee4c…5762`). Pack digest `42789e45…` and thresholds SHA-256 `3a1c9d8a…` are the same as at `b1f7016`. Every metric and every per-case status, reason, tool count, elapsed time and gate value is identical to `eval-report-b1f7016.json`. Verdict: SUPPORTED_ON_SYNTHETIC_PACK (agent 40/40 vs baseline 25/36). Criterion 2 is met.
3. **Results commit `5ba3e88`** (regenerated traces and the report): unittest **139 tests OK**; pytest **139 passed, 514 subtests passed**. Trace SHA-256: `trace-tool-selection-thesis-revision.json` `230e28f6…a1ad`, `trace-justified-abstention.json` `1e708004…bdb1`.
4. **CRLF checkout** (fresh `git clone --no-checkout --config core.autocrlf=true`, then checkout; macOS):
   - Control `33c2f40`: the prompt and `facts.py` are checked out with CRLF. unittest gives 1 failure and 53 errors; pytest gives **53 failed, 61 passed, 4 errors**, the same as the review's Windows numbers.
   - Fix `5ba3e88`: owner-directory files stay LF, while `tests/test_contracts.py` (outside them) is CRLF. unittest OK, pytest **139 passed, 514 subtests passed**. Criterion 3 is met.
   - Still not run on Windows itself.
5. `git diff --check 33c2f40..5ba3e88` clean (criterion 4). No change to `larp/contracts.py`, `pytest.ini`, dependency files, `tests/test_contracts.py`, `docs/official/` or `vendor/`.
6. **Outcome: all four §9.2 criteria PASS.**
   - Still open: the root `.gitattributes` (or an equivalent shared rule) is Keegan's to adopt at integration. Already-cloned Windows checkouts need a fresh checkout to pick up the attributes.
   - A blocked store read leaves its abandoned thread waiting until the read returns. It is a daemon thread, makes no further calls, and its result is discarded.
   - The hosted adapter is still not verified against a live provider. Whether a given provider echoes the snapshot ID in `model` is unverified.
