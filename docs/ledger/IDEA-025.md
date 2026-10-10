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

### 9.3 PR #4 R3 re-check (Keegan, 2026-10-10, at `572332f`) — negation scope

Re-check result: R1, R2 and R4–R11 verified fixed. Keegan also ran the full suite (139 tests) on a real Windows `core.autocrlf=true` checkout (Python 3.14, unittest), and it passed; this closes the "not run on Windows itself" caveat in §9.2 result 4. R3 is **partly fixed**. `facts.negated` only looked 40 characters *before* the keyword. Negation after the keyword ("An impairment charge was not required", "a restatement … is not required") and a negated verb governing it ("We did not identify any events … that would indicate an impairment") still verified. The extractor shares the guard, so the rule baseline also turned this boilerplate into verified adverse findings without any model.

**Change.** `facts.negated(text, start, end)` reads the whole clause holding the match, both before and after it. A clause ends at a line end, a sentence end, a semicolon or a contrastive join (", but", ", whereas", ", while", ", although", ", though", ", however", ", yet"). A bare comma or ", and" does not end a clause. The negation cues are: no, not, none, neither, nor, never, without, cannot, n't, "absence of" and unnecessary. "No/not later than" and the event phrase "should no longer be relied upon" do not count as negation. The extractor (`_keyword_events`) and the verifier (`EVENT_NEGATED`) use the same function. The check is deliberately conservative: any negation in the clause rejects the event, so an affirmed event that shares its clause with an unrelated negation is missed rather than accepted. Out of scope and unchanged: hypothetical or risk-factor wording ("could result in an impairment") is still read as an event.

**Prospective criteria (written before any run of the changed code):**

1. New tests pass:
   - `test_facts_verify.NegationScopeTests`. Seven negated sentences, the four from the re-check plus the three it confirmed already rejected, give no event fact from the extractor and `EVENT_NEGATED` for a model claim quoting either the whole sentence or the keyword alone. Four affirmed controls (a plain impairment, an impairment followed by ", but no restructuring charge was required", a CFO resignation "no later than" a date, and the pack's non-reliance sentence) still give the event and verify.
   - `test_agent.ClaimBindingTests.test_a_negated_event_claim_abstains_and_creates_no_adverse_finding`, now over the five boilerplate sentences: ABSTAIN `EVENT_NEGATED`, no event finding, and no adverse entry at the gate.
   - `test_agent.ClaimBindingTests.test_the_baseline_finds_no_event_in_negated_boilerplate`: no IMPAIRMENT or RESTATEMENT claim or finding, F-RESTATEMENT not FIRED, and nothing adverse at the gate.
2. Every other test passes, including the 13 foundation tests. Exception: `test_golden` is expected to fail on the first run, because the rule baseline's identity hash covers `facts.py` and `verify.py`. The regenerated traces may differ only in that hash and the ids and digests derived from it; any other difference is a FAIL.
3. `python -m larp.intelligence.evaluation`: PASS on every frozen threshold, unchanged, with the pack unchanged. Every metric and per-case status and reason must be identical to `eval-report-35c60b4.json`; only the identity-derived fields and wall-clock fields may differ. The pack's three event sentences contain no negation cue, so no event may change.
4. `git diff --check` clean.

**Results (runs of pushed commits only; Python 3.12.1 unittest and pytest 9.0.3 on Python 3.14.6, as in §9.1, so not the locked environment, W09/GAP-45):**

1. **Fix commit `ae7acb7`, first run:** every test passed except the expected `test_golden` pair. unittest: 142 tests, 2 failures. pytest: 2 failed, 142 passed, 528 subtests passed. The three new tests and all their subtests pass (criterion 1).
2. **Traces** regenerated from `ae7acb7` and compared leaf by leaf with the committed ones. The only differences are the rule baseline's code-identity hash (`checkpoint_sha256` `b324be5b…` → `7865f60e…`) and the ids derived from it (`model_hash`, `assessment_key`, `result_id`, finding, job, request and batch ids). No field was added or removed. Statuses, tool sequences, findings, falsifier states, thesis transitions and gate values are unchanged (criterion 2).
3. **Evaluation at `ae7acb7`: PASS** (`tests/intelligence/evidence/eval-report-ae7acb7.json`, SHA-256 `4e42fd4f…b980`). Pack digest `42789e45…` and thresholds SHA-256 `3a1c9d8a…` are unchanged. Compared leaf by leaf with `eval-report-35c60b4.json`, the only differences are `wall_clock_us.median` and `.max`. Every metric, per-case status, reason, tool count, gate value and the SUPPORTED_ON_SYNTHETIC_PACK comparison are identical (criterion 3).
4. Trace SHA-256 after regeneration: `trace-tool-selection-thesis-revision.json` `20b7d9c8…239e`, `trace-justified-abstention.json` `10318b4b…8ac3`.
5. **Results commit `8cabdc3`:**
   - unittest **142 tests OK**; pytest **142 passed, 530 subtests passed**.
   - A fresh `git clone --no-checkout --config core.autocrlf=true` checkout of `8cabdc3` (macOS) passes unittest.
   - `git diff --check 572332f..8cabdc3` is clean (criterion 4).
   - Mutation check: with the old 40-character look-behind guard restored in a scratch worktree, the new tests fail on each of the four re-check sentences, in both the extractor/verifier tests and the agent tests. The three sentences the old guard already rejected still pass.
6. **Outcome: all four §9.3 criteria PASS.** The open limits are the conservative misses described above (an affirmed event sharing its clause with an unrelated negation) and hypothetical or risk-factor wording, which is still read as an event.

### 9.4 Hypothetical event wording (follow-up to §9.3; SYZ, 2026-10-10)

The §9.3 limit: modal, conditional and forward-looking wording ("Goodwill impairment could result if …", "our common stock could be delisted", "We expect to record an impairment charge") was still read as a reported event. The extractor turned such risk-factor and outlook boilerplate into verified adverse findings without any model, and the verifier accepted it from a model claim. This is the same failure class as R3.

**Change.** `facts.negated` becomes `facts.unasserted(text, start, end)`. It reads the same clause as §9.3 and returns `NEGATED`, `HYPOTHETICAL` or None. The hypothetical cues are: may, might, could, would, should, can, if, unless, whether, possible/possibly, potential/potentially, risk(s), likely/unlikely, future, expect(s)/expected, anticipate(s)/anticipated, intend(s), "plan(s) to" and "in the event". Three phrases are not cues: "no/not later than", "should no longer be relied upon", and the month "May" followed by a day or year (case-sensitive). The extractor skips any unasserted match. If every match in a claim is unasserted, the verifier rejects it with `EVENT_NEGATED` when any match is negated, otherwise with `EVENT_HYPOTHETICAL`.

The check stays conservative: one cue anywhere in the clause rejects the event. So "the Audit Committee concluded that the statements would need to be restated" is missed, and so is "the expected impairment was recorded". For non-reliance, the Item 4.02 metadata event (`ITEM:4.02`, F-ITEM-4.02) does not depend on wording and is unaffected. Tests renamed: `test_negated_events_give_no_fact_and_are_not_verified` → `test_negated_or_hypothetical_events_give_no_fact_and_are_not_verified`; the two §9.3 agent tests gain "or_hypothetical" in their names and now cover both boilerplate documents.

**Prospective criteria (written before any run of the changed code):**

1. New and changed tests pass:
   - `test_facts_verify.NegationScopeTests`. The seven §9.3 negated sentences still give `EVENT_NEGATED`. Eight hypothetical sentences, at least one for each keyword event type, give no event fact and `EVENT_HYPOTHETICAL` for a claim quoting either the sentence or the keyword alone. Six affirmed controls give the event and verify: the four from §9.3, "We recorded a goodwill impairment of $12 million; further impairments may follow." (the modal sits in another clause) and "On May 12, 2026, the Chief Financial Officer resigned." (the month).
   - `test_agent.ClaimBindingTests`: a model claim on each sentence of the negated and the hypothetical boilerplate 8-Ks abstains with the matching reason and leaves no adverse finding in the result or at the gate. The baseline finds none of those events, and F-RESTATEMENT is not FIRED.
2. Every other test passes, including the 13 foundation tests. The `test_golden` pair is expected to fail on the first run (the identity hash covers `facts.py` and `verify.py`). The regenerated traces may differ only in that hash and the ids derived from it.
3. `python -m larp.intelligence.evaluation`: PASS on every frozen threshold, with the pack unchanged. Compared leaf by leaf with `eval-report-ae7acb7.json`, only wall-clock fields may differ. None of the pack's three event sentences contains a cue.
4. `git diff --check` clean.

**Results (runs of pushed commits only; same interpreters as §9.3):**

1. **Fix commit `91db50d`, first run: FAIL.** unittest: 142 tests, 5 failures. pytest: 5 failed, 142 passed, 543 subtests passed. Two failures are the expected `test_golden` pair. The other three come from one cause, on "Our Chief Executive Officer may resign at any time." The OFFICER_DEPARTURE pattern matches across "Chief Executive Officer may resign", and `unasserted` read the clause *outside* the match, so a cue inside the match was invisible. The §9.3 negation check had the same gap: "The Chief Financial Officer has not resigned." would have verified. All other new subtests passed.
2. **Fix commit (next):** `unasserted` reads the whole clause, the match included. "Should no longer be relied upon" is already masked as not a cue, so the non-reliance phrase still counts as an event. Criterion 1 gains one negated fixture, "The Chief Financial Officer has not resigned." (OFFICER_DEPARTURE; the negation is inside the match). Criteria 2–4 are unchanged.
3. **Fix commit `511b403`, first run:** every test passed except the expected `test_golden` pair. unittest: 142 tests, 2 failures. pytest: 2 failed, 142 passed, 547 subtests passed (criterion 1).
4. **Traces** regenerated from `511b403` and compared leaf by leaf with the committed ones. The only differences are the rule baseline's code-identity hash (`checkpoint_sha256` `7865f60e…` → `d95e019f…`) and the ids derived from it. No field was added or removed, and statuses, tool sequences, findings, falsifier states, thesis transitions and gate values are unchanged (criterion 2). Trace SHA-256: `trace-tool-selection-thesis-revision.json` `c9fd94a7…31de 635cb669…fca0 ac1ed01e…0658 `, `trace-justified-abstention.json` ``.
5. **Evaluation at `511b403`: PASS** (`tests/intelligence/evidence/eval-report-511b403.json`, SHA-256 ``). Pack digest `42789e45…` and thresholds SHA-256 `3a1c9d8a…` are unchanged. Compared leaf by leaf with `eval-report-ae7acb7.json`, the only differences are `wall_clock_us.median` and `.max` (criterion 3).
6. **Results commit `332288b`:**
   - unittest **142 tests OK**; pytest **142 passed, 549 subtests passed**.
   - A fresh `core.autocrlf=true` clone of `332288b` (macOS) passes unittest.
   - `git diff --check 5e7eb33..332288b` is clean (criterion 4).
   - Mutation checks in a scratch worktree:
     - With the hypothetical cue check removed, the new tests fail on all eight hypothetical sentences in the extractor/verifier tests, and on all six in the agent tests.
     - With the match excluded from the clause again, the tests fail on "has not resigned" and "may resign".
7. **Outcome: all four §9.4 criteria PASS at `511b403`/`332288b`** (after the first-run FAIL at `91db50d`, results 1–2). The remaining limits are the conservative misses described in the Change paragraph. All of this is on synthetic sentences only; precision and recall on real filings remain unmeasured until the real-data evaluation (§7).

### 9.5 Hypothetical events kept as their own signal (SYZ, 2026-10-10)

**Why.** §9.4 dropped hypothetical wording entirely. SYZ's correction: a statement about a possible event carries weight on its own, and markets react before the event happens, so the evidence layer must keep it. It must not treat it as a reported event, though; most such wording is risk-factor boilerplate, and a verified adverse event can force an exit (IDEA-010). SYZ asked for the assumptions behind keeping these statements to be checked before building on them.

**Assumption check (2026-10-10).** Sources are in `docs/skill/reference/literature.md` §12.8 and in the code.

| # | Assumption | Verdict | Evidence |
|---|---|---|---|
| A1 | Statements about possible events carry price-relevant information before the event | **Supported** (broad US samples) | L-61 (more risk text → higher volatility and volume around and after the filing), L-62 (reflected in risk, information asymmetry and value), L-64 (impairments priced 7–12 months before being recorded; secondary). These mostly measure risk perception, not a signed return. |
| A2 | Most such statements are repeated boilerplate; mainly new ones inform | **Supported** | L-63 (boilerplate and stickiness rising, with risk factors a main driver), L-61 (weaker effects for boilerplate-like text), L-60 (changes are what predict) |
| A3 | The market reacts at once | **Partly contradicted** | L-60: changed filing text has **no announcement effect**, and returns accrue over later months. Forecasts move prices at once (L-65, unconfirmed). Timing depends on the statement type. |
| A4 | Our pipeline can tell a new statement from repeated boilerplate | **False before this change** | Event novelty was keyed on (event, accession) (`agent.py` `_novelty`), so a statement in any other filing counted as NEW and every year's boilerplate looked new. Built here. |
| A5 | Statements can come from anywhere and the pipeline sees them | **Not covered** | The evidence agent ingests EDGAR only. Other sources need licensing (outside the build, IDEA-021 §8.1) and the G-05 source register. Not built; open. |
| A6 | The effect holds for our five large-cap names at the 5-session label horizon | **Unverified** | No study covers it. L-32 and L-22 suggest weaker effects for large caps, and L-60's effect is slower than 5 sessions. Recorded as H-04. |

**What the evidence supports building:** keep each statement, compare it with the issuer's earlier filings, flag the new ones, and assign no severity. Weighting is a policy decision (Keith) that waits on H-04.

**Change.**
- `facts._keyword_events` keeps each distinct hypothetical statement as an EVENT fact named `HYPOTHETICAL:<event>`, spanning its clause; negated mentions still give nothing. Reported events are unchanged: one span per type per document.
- `verify.verify_claim` accepts a `HYPOTHETICAL:<event>` claim only when the span has a hypothetical, non-negated mention. Otherwise it returns `EVENT_NEGATED` or `EVENT_NOT_HYPOTHETICAL`. A plain event claim on hypothetical wording still fails `EVENT_HYPOTHETICAL`.
- `tools.prior_context(metric="HYPOTHETICAL")` returns every hypothetical event from earlier filings in one call. The baseline requests it when the current filing has any (`gaps`).
- Novelty: `REPEATED` if the same statement (`facts.statement_key`, the clause case- and whitespace-normalised) appears in an earlier filing, `NEW` if not, `PRIOR_NOT_CHECKED` if the lookup did not run. Exact match is stricter than L-60's similarity measure, so any edit counts as NEW and goes to review.
- Results gain `hypothetical_events` (type, event, novelty, fact id, statement), present whatever the status. These are never findings, never fire a falsifier and never enter `unresolved_adverse`.
- A NEW or unchecked statement adds the review request `REVIEW_NEW_HYPOTHETICAL_EVENT` and the gate reason `NEW_HYPOTHETICAL_EVENT`, which keeps the gate off CLEAR.
- `FeatureRow.v1` gains `n_hypothetical_new`, `n_hypothetical_repeated` and `hypothetical_types_new` for the H-04 test.
- The model prompt is unchanged: event codes come from the harness's facts.

**Prospective criteria (written before any run of the changed code):**

1. New tests pass:
   - `test_facts_verify.NegationScopeTests`: each of the eight hypothetical sentences gives one `HYPOTHETICAL:<event>` fact whose span is the sentence, and a `HYPOTHETICAL:` claim on the sentence or the keyword verifies. On the seven negated sentences such a claim gives `EVENT_NEGATED`; on a plain reported impairment, `EVENT_NOT_HYPOTHETICAL`. "We recorded a goodwill impairment of $12 million; further impairments may follow." gives both IMPAIRMENT and `HYPOTHETICAL:IMPAIRMENT` ("further impairments may follow."). `statement_key` ignores case and spacing but not a changed word. The §9.4 tests still pass.
   - `test_agent.HypotheticalEventTests`:
     - Six new statements with no earlier filing: ASSESSED; `prior_context(HYPOTHETICAL)` called and NO_PRIOR; all six NEW; no finding and nothing adverse at the gate; review `REVIEW_NEW_HYPOTHETICAL_EVENT`; gate UNKNOWN with `NEW_HYPOTHETICAL_EVENT`; feature row 6 new and 0 repeated.
     - The same two statements a month earlier: both REPEATED, no review and no gate reason; feature row 0 and 2.
     - Those two plus one new statement: only the new one is NEW, with no IMPAIRMENT event finding.
     - A model claim `HYPOTHETICAL:DELISTING` verifies, with no DELISTING finding.
2. Every other test passes, including the 13 foundation tests. Exception: the `test_golden` pair is expected to fail on the first run. The regenerated traces may differ only in the identity hash and the ids derived from it, plus the new fields: `hypothetical_events: []`, and in the feature row `n_hypothetical_new: 0`, `n_hypothetical_repeated: 0`, `hypothetical_types_new: []`. The pack has no hypothetical statement, so tool sequences, statuses, findings, falsifiers, theses and gates must be unchanged.
3. `python -m larp.intelligence.evaluation`: PASS on every frozen threshold, with the pack unchanged. Compared leaf by leaf with `eval-report-511b403.json`, only wall-clock fields may differ.
4. `git diff --check` clean.

**Results (runs of pushed commits only; same interpreters as §9.3):**

1. **Feature commit `cfa0966`, first run: FAIL.** unittest: 150 tests, 3 failures. pytest: 3 failed, 149 passed, 564 subtests passed. Two failures are the expected `test_golden` pair. The third is a **test error**, not a code fault: `test_new_hypothetical_statements_are_kept_reviewed_and_never_adverse` expected no findings at all, but the fixture 8-K carries Item 8.01, which the item map gives an UNKNOWN-impact finding (severity 1), as for any 8-K. The hypothetical statements produced no finding, nothing was adverse, and the gate reason was `NEW_HYPOTHETICAL_EVENT` alone. Every other new test passed.
2. **Amendment (before the next run):** criterion 1's "no finding" now reads "no finding other than the fixture's own `ITEM:8.01` (impact UNKNOWN), and nothing adverse at the gate". The test asserts exactly that. No code change.
3. **Test commit `616d43b`, first run:** every test passed except the expected `test_golden` pair. unittest: 150 tests, 2 failures. pytest: 2 failed, 150 passed, 564 subtests passed. The 8 new tests (4 in `test_facts_verify`, 4 in `test_agent.HypotheticalEventTests`) pass (criterion 1).
4. **Traces** regenerated from `616d43b` and compared leaf by leaf with the committed ones. The differences are the identity hash (`checkpoint_sha256` `d95e019f…` → `a7d44a05…`), the ids derived from it, and the new fields: `hypothetical_events: []` in both results, and `n_hypothetical_new: 0`, `n_hypothetical_repeated: 0`, `hypothetical_types_new: []` in both feature rows. Tool sequences, statuses, findings, falsifiers, theses and gates are unchanged (criterion 2). Trace SHA-256: `trace-tool-selection-thesis-revision.json` `214bfa6d…5272`, `trace-justified-abstention.json` `610d7800…c9e7`.
5. **Evaluation at `616d43b`: PASS** (`tests/intelligence/evidence/eval-report-616d43b.json`, SHA-256 `089aca62…3cfb`). Pack digest and thresholds are unchanged. Compared leaf by leaf with `eval-report-511b403.json`, the only differences are `wall_clock_us.median` and `.max` (criterion 3).
