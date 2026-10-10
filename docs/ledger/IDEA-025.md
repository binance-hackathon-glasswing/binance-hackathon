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
