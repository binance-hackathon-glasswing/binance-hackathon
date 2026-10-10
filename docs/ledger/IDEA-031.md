# IDEA-031 — Evidence hardening, free-source ingestion and component integration (implements IDEA-030)

- Date / author: 2026-10-10 SGT / Yao Zhu request; Claude (Opus 5.5) implementation session; independent subagent red teams for semantics and integration/evaluation.
- Status: **implemented on `codex/evidence-hardening` (not merged); synthetic acceptance PASS; real-document, LLM-value and economic evaluations NOT RUN; no authority adopted.** Results are in V01–V06, appended only after the code they describe was committed and pushed.
- Branch: `codex/evidence-hardening` (integration branch; not merged to main by this record).
- Implements: [IDEA-030](IDEA-030.md) R02–R12 and T01 path, [free-source register](IDEA-030-free-sources.md), prompt [05-evidence-hardening-free-sources](../build/05-evidence-hardening-free-sources.prompt.txt). Backlog: GAP-67 (primary), GAP-65 (integration), GAP-23/24/25/26/27 (source register, point-in-time contract, dedup, verification quality, untrusted content). Policy items GAP-64/GAP-51/GAP-56 are **not** decided here.
- Hard limits for this record: zero paid data/licensing; no deploy, trade, signing, ai-seeds upload, paid model or return-model training; no unvalidated new trading authority (new news/uncertain-event influence stays SHADOW/disabled). Pre-existing untracked `Claude outputs/` is not run, edited or committed.

## S0 — Starting state (verified 2026-10-10 before editing)

Fetched all remotes. Owner branches and the SHAs integrated by ordinary `--no-ff` merges into `codex/evidence-hardening` (from main `2c64084`):

| Component | Branch | SHA |
|---|---|---|
| Evidence (Yao Zhu) | `origin/codex/evidence-agent` (PR #4) | `544df90` |
| Strategy/risk/research (Keith) | `origin/codex/strategy-risk-research` (PR #5, draft) | `45e4b10` |
| Runtime/audit/storage (Keegan) | `origin/codex/runtime-audit-platform` (PR #3) | `0234a14` |
| Execution W04/W08 (Isaac) | `origin/branch-isaac` (PR #6) | `0343661` |

No branch was rebased, force-pushed or rewritten. Merge conflicts were documentation-only (`LEDGER.md`, `INCOMPLETE_WORK.md`, `literature.md`, `README.md`, `larp/__init__.py` docstring) and were resolved by keeping both sides.

**IDEA-023 reconciliation.** The ID IDEA-023 was used twice: main's `docs/ledger/IDEA-023.md` ("Proposed solutions for evidence exits, economic evidence and engine proof") and the owner branches' "First engine increment: offline policy boundary". Both are kept unchanged. In integrated trees the owner-branch record lives at [`IDEA-023-offline-policy-boundary.md`](IDEA-023-offline-policy-boundary.md) with a reconciliation note; its LEDGER row is labelled "owner-branch record; duplicate ID". References inside PARALLEL_BUILD, prompts 01–04, IDEA-024 and IDEA-025–028 mean the owner-branch file; references in IDEA-029/030 and main's S1–S3 note mean `IDEA-023.md`. IDEA-027 remains reserved for Isaac, so this record takes IDEA-031, the next free ID on every fetched branch.

**Baseline test run (merged tree `d73ec66`, before any code change).** Python 3.12.14 (`/opt/homebrew/bin/python3.12`) in a scratch venv with the pinned `deploy/requirements-*.lock` package versions (installed by version; the Linux hash-locked wheels do not match macOS) plus `numpy==2.5.3`, `pandas==3.0.6`. `python -m pytest -q -p no:cacheprovider --ignore=tests/test_w04_execution.py`: **223 passed, 74 skipped, 571 subtests passed**. Skips: PostgreSQL (`LARP_TEST_DATABASE_URL` unset) and Linux worker isolation. `tests/test_w04_execution.py` fails to import (`ModuleNotFoundError: execution_fixtures`) because the runtime branch made `tests/` a package while Isaac's test imports its fixture as a top-level module. This is an integration defect to fix (AC-I09), not a W04 behaviour failure. Historical counts (150 evidence, 48 strategy, 108 runtime, 31 W04) are not reused as results here.

**Policy-adoption check.** Searched `plan.md` (v1.0 adopted scope, G-51/G-53, IDEA-018 notes), INCOMPLETE_WORK and IDEA-018/019/023 headers. Adopted: G-50 evidence budget, G-53 claim verification, G-51 "thesis memory: falsifiers" exist. **Not adopted:** falsifier EXIT as a live/mandatory trading authority (IDEA-018 R3 is marked "RECOMMENDED — NOT DECIDED"), any evidence entry veto, any baseline (GAP-64), depth-rule replacement (GAP-51), price-history source (GAP-56). Consequently: authority is implemented as a configurable, tested capability whose default is SHADOW; no live profile is enabled.

## S1 — Staged plan

| Stage | Scope | Main files (owner of original code) |
|---|---|---|
| 1 Semantics | Event-statement classification (actor, assertion class, attribution, announcement vs effective time, temporal/historical, heading, negation scope, quotes, mixed clauses) shared by extractor and verifier; signed numeric + REPORTED/GUIDANCE verification; development/capability and regulatory-action statements with separately sourced issuer relations | `larp/intelligence/semantics.py` (new), `facts.py`, `verify.py`, `agent.py` (Yao Zhu) |
| 2 Lifecycle | Statement identity (exact text vs semantic vs uncertain match), first-seen vs missing history, acknowledgment, pending review with bounded retry/backoff/exhaustion, supersession/correction/withdrawal, expiry, adverse-latch resolution rules, consumption-time freshness, work/coverage bounds | `larp/intelligence/lifecycle.py` (new), `gate.py`, `agent.py` |
| 3 Integration | Canonical `EvidenceContext.v1` + versioned adapters; typed rejections; runtime↔strategy context, plan jobs, intent amount/expiry/decision identity, reservation asset deltas, persisted risk/evidence state, reassessment scheduling; configurable falsifier authority (NONE/SHADOW/DISCRETIONARY_EXIT/MANDATORY_REDUCTION); real-component fixture | `larp/integration/` (new), small hooks in `strategy/policy.py` (Keith), `runtime/coordinator.py`, `runtime/schema.py` (Keegan) |
| 4 Free sources | Generic `SourceDocument.v1` record/cursor/ingestor; allowlisted transport; SEC news, Federal Register (BIS + public inspection), DOJ; EC via the same adapter after checks; FTC disabled unless a working permitted path is verified; optional/disabled register entries for Fed/BLS, EFF, GDELT, Wikinews, OpenDART, issuer newsrooms; clustering; rights filter | `larp/sources/` (new) |
| 5 Evaluation | Evidence-eval precision/false positives/statement classes/latency; same-input baseline vs model harness; independently labelled real-document path (NOT RUN without labels); structured economic registration v2 enforced exactly; ablation spec validator | `larp/intelligence/evaluation.py`, `larp/intelligence/realeval.py` (new), `larp/research/evaluation.py` (Keith), `larp/research/ablation.py` (new) |

Order of work: stage 1 → 2 → 3 → 4 → 5, each committed and pushed before its tests run. Existing tests whose expectations encode a confirmed IDEA-030 defect are corrected in the same commit and listed in V-sections with the reason (never silently).

## S2 — Design commitments (what "correct" means for the criteria)

1. **Event statement fields.** Every keyword event fact carries `statement: {event, assertion, actor, actor_text, attribution, temporal, announced_at, effective, event_time_text, cues}`.
   - `assertion` ∈ OCCURRED, ANNOUNCED_FUTURE, ATTRIBUTED_REPORT (rumor, unnamed sources, allegation, third-party report), FORECAST, CONDITIONAL_RISK, NEGATED, MENTION_ONLY (heading/noun phrase with no occurrence predicate).
   - `actor` ∈ ISSUER, THIRD_PARTY, UNSPECIFIED; `temporal` ∈ CURRENT, HISTORICAL, FUTURE, UNKNOWN.
   - Only OCCURRED ∧ ISSUER ∧ ¬HISTORICAL can become an adverse finding (metric = event code). Every other statement is retained as `STATEMENT:<event>` (replaces the overloaded `HYPOTHETICAL:` prefix; legacy context facts are read as `assertion=LEGACY_UNCLASSIFIED`).
   - Classification is structural (occurrence predicate present, subject/possessor of the predicate, attribution frame, scope of negation over the predicate, quotation, dates relative to the document date), not a longer modal list.
2. **Verifier parity.** The verifier recomputes the statement semantics from the cited source text and rejects a claim whose `assertion`, `actor` or `temporal` differs (`EVENT_SEMANTICS_MISMATCH`). A claimed finding-eligible event without an occurrence predicate fails. Numeric claims: the signed value derived from the span (parentheses, leading minus, "loss"/"decline of" frames for income metrics) must equal the claim exactly; `kind` must equal the span's derived kind (forward-looking frame governing the number ⇒ GUIDANCE; otherwise REPORTED); ranges must be claimed as ranges. Valid positive and negative controls still pass.
3. **Partial retention.** When some claims fail, supported facts are retained in an audit field (`retained_facts`) with `coverage` and the result stays ABSTAIN; retention cannot change status, create CLEAR, authorise entry or expand mandatory-exit authority.
4. **Evidence state v2** (`IssuerEvidenceState.v2`): statement registry with stable identity and lifecycle (`PENDING_REVIEW`, `ACKNOWLEDGED`, `REVIEW_EXHAUSTED`, `SUPERSEDED`, `CORRECTED`, `WITHDRAWN`, `EXPIRED`, `RESOLVED`), bounded review schedule (`attempts`, `next_review_ms`, exponential backoff, `max_review_attempts`), adverse latches with explicit `resolution_rule`, `assessed_until_ms`. `consume(state, now)` returns the as-of view: CLEAR only while `now < assessed_until_ms`; otherwise `STALE`. Evidence status is descriptive; portfolio permission is computed separately by the integration layer under a configured authority.
5. **Bounds.** Per-assessment limits on document bytes, facts per document, prior records scanned, statements compared, estimated model input tokens and elapsed time, in addition to tool calls. Any truncation is reported in `coverage` and makes the result incomplete (never CLEAR).
6. **Sources.** Each source has an allowlisted endpoint set, rights basis (licence/permission identifier, terms URL, terms-checked date, attribution, exclusions), enable flag with reason, and per-source limits. Records are `SourceDocument.v1`, never disguised as EDGAR accessions. Date-only timestamps keep `precision=DAY` and are never treated as available before retrieval; historical replay uses a conservative end-of-day bound. Corrections/withdrawals create new versions; earlier versions are never rewritten or backdated. A failed source affects only consumers declaring it.
7. **Evaluation.** No synthetic result can satisfy T01. Real-document evaluation requires an external, rights-cleared, independently labelled manifest frozen before predictions; otherwise its report says NOT_RUN. Economic registration v2 is structured and evaluated exactly as registered; v1 text criteria are rejected for evaluation.

## S3 — Preregistered acceptance criteria (written before implementation; not yet run)

Each AC is an automated offline test unless marked. Pass = the stated observable holds. "Control" = a valid input that must still be accepted. Tests use only synthetic/fixture inputs and fake external sources, model and execution.

### Semantics (stage 1)
- **AC-S01** `Impairment of goodwill` (heading) → no IMPAIRMENT finding; statement `MENTION_ONLY`; a model claim of IMPAIRMENT occurrence on that span is rejected. Control: `We recorded a goodwill impairment charge of $1.2 billion.` → OCCURRED/ISSUER finding.
- **AC-S02** `Our competitor reported a cybersecurity incident.` → actor THIRD_PARTY, no issuer finding, claim of issuer occurrence rejected. Control: `On October 5, 2026, the company identified a cybersecurity incident...` → OCCURRED/ISSUER.
- **AC-S03** `The CEO is rumored to resign.` → ATTRIBUTED_REPORT, no departure finding/occurrence.
- **AC-S04** `The CEO announced plans to resign effective November 30.` and the existing EXSEMI_502 8-K text → ANNOUNCED_FUTURE with `effective` = the stated date (year from document when absent), not OCCURRED and not CONDITIONAL_RISK. Control: `The CFO resigned effective October 1, 2026.` (document dated later) → OCCURRED.
- **AC-S05** Negation scope and mixed clauses: `We recorded an impairment charge and did not record a restructuring charge.` → IMPAIRMENT OCCURRED; `We did not record an impairment charge.` → NEGATED; `No cybersecurity incident has had a material effect` → NEGATED.
- **AC-S06** Quoted/third-party text: `"We expect a cybersecurity incident," said an analyst.` → not issuer OCCURRED. Historical repetition: `In fiscal 2019, we restated our financial statements.` in a 2026 document → temporal HISTORICAL, no current finding.
- **AC-S07** Allegation/regulatory frames: `The SEC filed a complaint alleging that X misstated revenue` → ATTRIBUTED_REPORT (allegation), never OCCURRED for X; `proposed rule` ≠ effective rule (regulatory statement subtype PROPOSED vs FINAL).
- **AC-S08** Numeric sign: on `Revenue for the third quarter of fiscal 2027 was $35.1 billion.` the unchanged REPORTED claim passes; value −35.1 fails; kind GUIDANCE fails. `Net loss for the third quarter of fiscal 2027 was $(1.2) billion` / `net loss of $1.2 billion` → extracted net_income −1.2; claim +1.2 fails; −1.2 passes. Table cell `(1,234)` → −1234 only.
- **AC-S09** Kind: `For the fourth quarter ... the company expects revenue to be $33.0 billion` passes as GUIDANCE and fails as REPORTED; a guidance range claimed as a point at one bound fails; a correctly claimed range passes.
- **AC-S10** Development/capability claim: `A China-based company announced it had developed a chip that it says outperforms ...` → `DEVELOPMENT_CLAIM` statement, attribution to the announcing company, `issuer_relations` empty unless an eligible issuer is named in the same source (then `MENTIONED_IN_SOURCE`, effect `UNKNOWN`); never an adverse finding for NVIDIA/SK hynix.
- **AC-S11** Unsupported deterministic findings do not survive: a fact whose statement re-verification fails is excluded from `findings` and `event_findings` even when the model abstains or times out; supported facts are retained in `retained_facts` with status ABSTAIN and `coverage.complete=false`; the gate's adverse latch is not created from a retained-but-unverified fact; ABSTAIN never yields CLEAR.

### Lifecycle (stage 2)
- **AC-L01** Same-document rereview: assessing the same filing again after acceptance (6 h later, new context) gives novelty `ALREADY_SEEN`/`ACKNOWLEDGED`, no new `REVIEW_NEW_STATEMENT` request after the review attempt completes, and no unbounded loop (review requests ≤ `max_review_attempts`).
- **AC-L02** Paraphrase vs substantive change: `could`→`may` and reordered wording of the same risk statement → `SEMANTIC_SAME`; changing a date, amount, actor or event type → `SUBSTANTIVE_CHANGE`; a gray-zone pair → `UNCERTAIN_MATCH` (exposed, not silently merged).
- **AC-L03** Missing history: prior lookup not performed → `PRIOR_NOT_CHECKED`; lookup performed but history unavailable/failed → `HISTORY_UNAVAILABLE`; lookup completed with no matches → `FIRST_SEEN`. None of these is reported as market-novel.
- **AC-L04** Correction/withdrawal: a superseding revision that removes or changes a fact marks the old statement `SUPERSEDED`/`CORRECTED` without deleting it; an adverse latch whose only supporting record is withdrawn/corrected becomes eligible for resolution by its declared rule; a latch with no satisfied rule persists.
- **AC-L05** Unrelated clean document does not erase an unresolved concern: pending statements and adverse latches persist and keep the gate non-CLEAR.
- **AC-L06** Stale CLEAR: an accepted CLEAR state consumed after `assessed_until_ms` reads `STALE`; an expired incoming result is rejected and leaves the stored state's freshness unchanged (still ages to STALE).
- **AC-L07** Review retries are bounded with exponential backoff and explicit `REVIEW_EXHAUSTED` status; no human action is required to leave the loop; exhausted items remain visible uncertainty and do not by themselves veto entry.
- **AC-L08** Novel statement alone is not an entry veto under default authority (SHADOW): permission output for an otherwise permitted name is unchanged and the statement appears in shadow records.
- **AC-L09** Realistic large filing: a synthetic ~2 MB 10-K-like document with >64 candidate claims and many risk statements completes within limits, reports `coverage` truncation counts (facts/statements/bytes/prior records), is not CLEAR, and bounded comparisons stay under the configured caps.

### Integration (stage 3)
- **AC-I01** `EvidenceContext.v1` is produced from the real evidence state and accepted by the real strategy policy through the versioned adapter; issuer↔token identity, UTC times, quality, falsifier findings and a domain-separated context hash round-trip.
- **AC-I02** Missing, incompatible-version, wrong-issuer, expired or hash-mismatched contexts produce typed rejections visible in the policy state/plan record; none is silently dropped.
- **AC-I03** The real planner output, via the runtime adapter, carries `decision_id`, `amount`, `expires_ms`, `jobs` and asset/units reservation deltas accepted by the real coordinator/store validation; risk state is persisted in the projection.
- **AC-I04** End-to-end fixture: fake EDGAR source → real `Ingestor` → real `EvidenceAssessor` (rule model) → real verifier/gate (state v2, persisted in the real store projection) → real strategy `decide` → real risk `plan` → real `Coordinator` + `PostgresStore` (jobs/commands/audit outbox). Requires disposable PostgreSQL; otherwise the test is reported SKIPPED (not passed) and an in-process variant with the same real modules except the store runs.
- **AC-I05** Restart/duplicates/stale context: rerunning the same round after a simulated restart is idempotent (no duplicate commands/reservations); a duplicate assessment result is DUPLICATE; a result for an obsolete context is rejected; a correction arriving later updates state without rewriting earlier events.
- **AC-I06** Falsifier authority: NONE/SHADOW → no exit target, shadow record only; DISCRETIONARY_EXIT → policy EXIT subject to cadence/minimum/cost gates; MANDATORY_REDUCTION → planner reduction constraint that bypasses discretionary cadence, minimum-trade and cost-reserve gates but still enforces gas/fee affordability, global integrity/journal/ownership/clock gates and signing end. Default config is SHADOW. Not every policy EXIT is mandatory.
- **AC-I07** Terminal flattening remains mandatory with and without a policy proposal (existing behaviour preserved).
- **AC-I08** Entries without verified underlying history, basis or quoted depth are not planned; the plan exposes the capability blockers (`MISSING_MARKET_OR_BASIS`, `INSUFFICIENT_FEATURES`, `DECLARED_DEPTH_INPUT_UNAVAILABLE`) rather than passing with fabricated inputs.
- **AC-I09** `tests/test_w04_execution.py` imports and runs under the integrated tree without changing W04 behaviour.

### Sources (stage 4)
- **AC-D01** Register: SEC news, Federal Register BIS documents, Federal Register public inspection and DOJ enabled; EC enabled only if its connectivity/rights check result is recorded, otherwise disabled with reason; FTC disabled unless a working permitted retrieval path is verified; Fed/BLS, EFF optional; GDELT discovery-only (no body retrieval, no corroboration count, no veto); Wikinews archive-only; OpenDART and issuer newsrooms disabled with reason. Every enabled source has licence/permission id, terms URL, checked date and attribution.
- **AC-D02** Records store source, original publisher, canonical URL, immutable raw text hash/artifact, version, licence/attribution, publication time with precision, event/effective time, retrieval and first-seen time; date-only items keep DAY precision and `available_ms` = retrieval time (never earlier).
- **AC-D03** Outage: a failing source marks only its own health; other sources ingest; coverage reports the failure; consumers not depending on it are unaffected.
- **AC-D04** Pagination restart: a crash between pages resumes from the durable page cursor without duplicating or skipping items; conditional requests (ETag/Last-Modified) avoid re-ingesting unchanged listings.
- **AC-D05** Changed item body → new version linked to the superseded hash; withdrawal → withdrawn version; earlier versions unchanged and not backdated.
- **AC-D06** Rights: images, attachments and items/sections carrying third-party copyright notices are excluded with a recorded reason; non-allowlisted hosts and off-allowlist redirects are refused; oversize bodies are truncated/refused with a recorded reason.
- **AC-D07** Prompt injection inside a source document is stored as data, flagged, and cannot change tools, destinations or authority.
- **AC-D08** Common-origin clustering: an EDGAR exhibit and the same press release from another source form one cluster; independent-confirmation count = 1.
- **AC-D09 (network, one-time, after push)** A read-only unauthenticated connectivity probe of the enabled endpoints records status/shape/timestamps without storing article bodies in Git. Failure is reported, not hidden; it is not an uptime or latency result.

### Evaluation (stage 5)
- **AC-E01** Evidence-eval scoring counts unexpected numeric claims and unexpected/incorrect event statements as false positives; reports precision, recall, abstention, coverage, error types and latency; a test with one extra output lowers precision.
- **AC-E02** The pack includes statement-class cases (rumor, forecast, conditional risk, announcement, occurrence, third-party, heading, historical) with expected assertion labels.
- **AC-E03** Baseline-vs-model comparison runs both variants with identical inputs and tool budgets; with no authorised model the model arm reports NOT_RUN (scripted fakes exercise only the harness and are labelled so).
- **AC-E04** Real-document evaluation path: without an external manifest → NOT_RUN; a synthetic manifest is refused for the gate (`SYNTHETIC_NOT_ADMISSIBLE`); with a well-formed manifest the report gives per-class precision/recall, false positives, abstention, Wilson 95% intervals and held-out separation; labels frozen before predictions and an annotator identity distinct from the implementer are required fields.
- **AC-E05** Economic registration v2: metric, improvement margin, support/kill/inconclusive rules, minimum sample, decision/label windows, purge/embargo and outcome provenance are structured; unsupported values are rejected; a registered margin changes the verdict exactly as specified; outcomes outside their registered decision/label windows or violating purge/embargo are rejected; net wallet return and off-wallet service costs are reported separately; aligned cluster counts alone do not upgrade the verdict; v1 free-text registrations return NOT_RUN.
- **AC-E06** Ablation spec: baseline/EDGAR/free-news/uncertain-event arms share fixed sizing/risk/execution assumptions and one frozen primary horizon; required cost/outcome fields (post-assessment executable price, gas, spread, slippage, failed attempts, re-entry, missed upside, drawdown, turnover, incomplete outcomes) are validated; without a committed EXP record and rights-cleared point-in-time data the study reports NOT_RUN; insufficient cases → INCONCLUSIVE; never promotes live.

### Regression
- **AC-R01** Re-run every existing suite in the integrated tree; report exact commit, interpreter and counts. Any changed expectation is listed with its IDEA-030 justification.

## S4 — Red-team plan

Two independent subagents with disjoint editing ownership, after stages 1–3 are pushed: (A) evidence-semantics red team writing only `tests/redteam/test_semantics_redteam.py`; (B) integration/evaluation red team writing only `tests/redteam/test_integration_redteam.py`. Neither edits implementation files. Their findings and my responses are recorded in V-sections. No messages to other user chats or external parties.

## S5 — Explicitly NOT in scope / will remain NOT RUN

Real-document semantic accuracy (T01) without independent labels; LLM-versus-baseline value without an authorised no-cost model; profitability/ablation studies (T03–T05) without an EXP record and rights-cleared point-in-time data; live/rehearsal acceptance; policy adoption (falsifier authority, baseline, depth replacement, price history). Passing these synthetic tests is not evidence of live readiness or profit.

## V01 — Implementation record (results appended after the code was committed and pushed)

Every code change below was committed and pushed to `origin/codex/evidence-hardening` before the tests that exercise it were run (commit history `cfa60c6..HEAD`; fixes after a failing run are separate commits). Interpreter for all runs: Python 3.12.14 (`/opt/homebrew/bin/python3.12`) in a scratch venv with the pinned `deploy/requirements-*.lock` versions plus `numpy==2.5.3`, `pandas==3.0.6`; disposable PostgreSQL 14 from `deploy/compose.test.yml` on 127.0.0.1:55432 for store tests. Linux bubblewrap worker tests remain skipped on macOS.

### Changed behaviour by stage

1. **Semantics** (`semantics.py`, `facts.py`, `verify.py`): event facts carry EventSemantics.v2; only issuer, current, occurred events are findings; every other non-negated statement is `STATEMENT:<event>` (replaces `HYPOTHETICAL:`; legacy facts are read as unclassified and never become findings). Verifier parity: model claims must match semantics recomputed from text. Numeric verification checks sign (governing metric mention, parentheses, loss forms), first amount, change vs level, analyst estimates, ranges and REPORTED/GUIDANCE kind. Harness event facts are re-verified before any finding (AC-S11). Partial retention: `retained_facts` on non-ASSESSED results, no status change.
2. **Lifecycle** (`lifecycle.py`, `gate.py`, `agent.py`, `tools.py`): statement identity/novelty with bounded comparisons; IssuerEvidenceState.v2 registry with bounded review, correction/withdrawal handling, latch resolution rule, consumption-time freshness (`consume`); work bounds on document chars, facts/statements per document, prior records, comparisons and model input; `coverage` in every result. Facts of a superseded revision of the same accession are no longer treated as current.
3. **Integration** (`integration/contract.py`, `integration/runtime.py`; hooks in `strategy/policy.py`, `strategy/schema.py`, `runtime/coordinator.py`, `runtime/schema.py`): EvidenceContext.v1 with typed rejections; configurable falsifier/statement authority defaulting to SHADOW; strategy unblocks when the evidence latch is resolved by rule; runtime context builder, plan adapter (decision id, exact amount, expiry, asset/units reservations, review jobs), persisted evidence and risk state. Strategy tests now build EvidenceContext.v1 instead of a dict bound to the policy's own `ThesisContext` digest.
4. **Sources** (`larp/sources/`, `config/sources/sources.v1.json`, `tools/probe_free_sources.py`): register with rights bases; allowlisted transport; RSS/FR/FR public inspection/DOJ parsers; rights filter; SQLite cursors with per-page commits; SourceDocument.v1 versions; clustering; coverage per consumer. All records `SHADOW_ONLY`.
5. **Evaluation** (`intelligence/evaluation.py`, `intelligence/realeval.py`, `research/evaluation.py`, `research/ablation.py`, `config/intelligence/eval_thresholds.v2.json`, `real_eval_criteria.v1.json`): see V03.
6. **Integration defect fixed:** W04 tests import their fixtures in the package layout (AC-I09).

### Existing expectations changed, with reasons

| Test / label | Before | After | Reason |
|---|---|---|---|
| `test_facts_verify` "CFO will resign effective no later than Nov 30" | occurred departure | ANNOUNCED_FUTURE statement, effective 2026-11-30 | IDEA-030 R04 confirmed defect |
| Eval pack `officer_departure_502` | expects OFFICER_DEPARTURE event | ITEM:5.02 event + ANNOUNCED_FUTURE statement | same |
| Modal/forecast claim reasons | `EVENT_HYPOTHETICAL` | `EVENT_NOT_OCCURRED:<assertion>` | reason names the assertion class |
| Hypothetical tests (`test_agent.py`) | `hypothetical_events`, `NEW`, `REVIEW_NEW_HYPOTHETICAL_EVENT`, gate `NEW_HYPOTHETICAL_EVENT` | `event_statements`, `FIRST_SEEN`, `REVIEW_NEW_STATEMENT`, `PENDING_STATEMENT_REVIEW` | R06 lifecycle; first-seen ≠ market-novel |
| `test_gate` CLEAR fixture | 5.02 8-K gives CLEAR | clean 8-K | the 5.02 announcement is now a pending statement |
| Strategy assessment helper | `AssessmentResult.v1`-like dict bound to `ThesisContext` digest | EvidenceContext.v1 | R02: no producer emitted that shape |
| Economic registration tests | v1 free-text criteria | v2 structured; v1 → NOT_RUN | R12.7 ignored criteria |
| Golden traces | v1 bytes | regenerated twice; statuses, tools, thesis and gate unchanged | code identity and result schema changed |
| Lifecycle AC-L02 gray-zone example | "...reputation with customers" | "...reputation significantly" | role nouns became anchors after red team f04 |
| Eval pack: `compact_html_table`, `utf8_foreign_issuer_6k` | non-exhaustive labels | marked exhaustive, `events: []` | first v2 run had no exhaustive numeric case so numerical precision had no observations; labels enumerated from the fixture text, not from outputs |

## V02 — Test evidence (final code `12a931a`)

`LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/larp_test python -m pytest -q -p no:cacheprovider` → **478 passed, 3 skipped, 718 subtests passed** (33 s). The 3 skips are Linux bubblewrap worker-isolation tests (`tests/runtime/test_worker_release.py`); they need Linux and were not run. The count includes both red-team probe files. Baseline before any change (merged tree `d73ec66`, no PostgreSQL): 223 passed, 74 skipped, W04 import error. Runtime/storage with PostgreSQL before changes: 92 passed, 3 skipped. Historical owner-branch counts are not reused.

| Acceptance group | Tests | Result at `12a931a` |
|---|---|---|
| AC-S01–S11 semantics | `tests/intelligence/test_semantics.py`, `test_facts_verify.py`, `test_agent.py` | pass |
| AC-L01–L09 lifecycle | `tests/intelligence/test_lifecycle.py`; L08 in `tests/integration/test_evidence_pipeline.py` | pass |
| AC-I01–I08 integration | `tests/integration/test_evidence_pipeline.py` (I04/I05 against PostgreSQL) | pass |
| AC-I09 W04 import | `tests/test_w04_execution.py` + W08 | 48 passed |
| AC-D01–D08 sources | `tests/sources/test_sources.py` | pass |
| AC-D09 connectivity | `tools/probe_free_sources.py` (V05) | run |
| AC-E01–E06 evaluation | `tests/intelligence/test_evaluation.py`, `test_realeval.py`, `tests/research/test_research.py`, `test_ablation.py` | pass |
| AC-R01 regression | full suite above | pass |

## V03 — Evaluation outcomes (synthetic; not real-text accuracy or profit)

- Synthetic evidence pack with frozen `eval_thresholds.v2.json`: acceptance **PASS**. Exhaustive cases have numerical, event and statement precision 1/1, statement recall 1/1 and zero false positives. Coverage was complete in 11/12 assessed runs. Retrieval ablation (rule model, 6 vs 0 tools): gain 11/38, `SUPPORTED_ON_SYNTHETIC_PACK`, labelled RETRIEVAL_ABLATION_NOT_LLM_VALUE. Report: `tests/intelligence/evidence/eval-report-v2-12a931a.json`. These are designed fixtures written by the implementer; they cannot estimate real error rates.
- **LLM vs deterministic: NOT RUN.** No authorised no-additional-cost model is selected (GAP-57); no paid inference. The harness was exercised only with a fake (HARNESS_ONLY).
- **Real-document T01 evaluation: NOT RUN.** No independently labelled, rights-cleared manifest exists. The path and frozen criteria (`real_eval_criteria.v1.json`) are implemented and refuse synthetic or non-independent input.
- **Economic studies (T03–T05): NOT RUN.** No EXP record and no rights-cleared point-in-time data exist. The registration v2 evaluator and the ablation validator are tested on synthetic accounting values only.

## V04 — Independent red teams

**S4-A semantics** (subagent; owned only `tests/redteam/test_semantics_redteam.py`): 50 probes. On first run, 37 failed and all 13 controls passed. The P1 findings were false issuer occurrences from by-agents, objects, possessors, named companies, appositives, quoted third parties, relative clauses, scenarios, tabletop exercises, definitions, tables of contents and prior-year text, plus wrong signed or kind numbers from second metric mentions, change nouns, "As expected", trailing "we expected", analyst estimates and unparsed range forms. P2 findings were missed occurrences from relative-clause or concessive negation, quoted issuer officers, biographical years, past effective dates and "accepted the resignation", together with a proposed-vs-final rule error and identity anchors. Fixes in `7fb7891`, `7b42462`, `b0b118b`. **All 50 probes now pass**, controls unchanged. The red team's judgement-call items were not probed and remain open: fiscal-year offset rules, whether a "Restated …" heading signals a restatement, director-vs-officer scope, delisting-notice wording, direction reversal ("harm"→"help") as a substantive change, non-GAAP counterfactual levels, and whether quoted issuer speech is finding-eligible.

**S4-B integration/evaluation** (subagent; owned only `tests/redteam/test_integration_redteam.py`): 40 probes. On first run, 25 failed and all 15 controls passed.
- **P1:**
  - mandatory reductions built from contexts the strategy rejects (c03);
  - latch resolved by an incomplete reassessment (g01);
  - bootstrap verdict depending on input order (e03);
  - duplicate claims inflating precision (e01).
- **P2 and P3** covered:
  - typed rejection of malformed contexts and results;
  - acknowledgment without a history check;
  - pending-BUY reservations unrecoverable from the store;
  - allowlist path traversal;
  - non-OSError transport failures;
  - one bad timestamp blocking a source;
  - the `-0000` time zone;
  - eviction of the bounded seen-cache;
  - poisoned continuations;
  - Federal Register withdrawal notices;
  - copyright notice forms;
  - unexpected findings in scoring;
  - label-before-decision outcomes;
  - split leakage;
  - ablation registrations not bound to the study;
  - identity normalisation;
  - ledger/balance key sets.

Fixes are in `ecdbcd7` and `12a931a`. Two contract changes follow from them. A pending BUY now writes an `INCOMING:<token>` reservation claim, which the PostgreSQL store excludes from its settled-balance check (a small change to Keegan's `larp/storage/postgres.py`). Economic outcomes must now state the registered detection delay and come from the registered commit.

Of the red team's ambiguous items, these were acted on: unused registered fields, the EXP-record check (now a git-tracked file that names the study), silent page truncation (now reported) and per-issuer error isolation. Still open: the unkeyed context hash (it detects corruption, not forgery; it needs a store-side signature), and intra-record consistency beyond CLEAR versus findings.

Changes to red-team files: three control or incidental assertions were updated with comments because the contract changed deliberately: the r03 deltas, the e06 helper fields and d07's first-poll status. **All 40 probes now pass.**

## V05 — Free-source connectivity (AC-D09, read-only, 2026-10-10 13:20 UTC, code `12a931a`)

| Source | Result |
|---|---|
| fr-bis | HTTP 200 JSON, 20 items, next page present |
| fr-public-inspection | HTTP 200 JSON, 108 items |
| doj-press | HTTP 200 JSON, 20 items. The first probe at 12:55 UTC failed with UNPARSEABLE_TIMESTAMP; this showed that `created`/`changed` are `<time datetime=…>` fragments and `date` is epoch seconds at a fixed hour. The parser was fixed and covered by a regression test |
| ec-press | HTTP 200 RSS, 10 items |
| ftc-press | HTTP 404; the register keeps it disabled |
| sec-press | SKIPPED: no `LARP_SEC_USER_AGENT` contact configured, and none was invented |

No bodies were stored and no artifacts were written to the repository. One request per endpoint is not an uptime, latency or completeness measurement.

## V06 — Remaining blockers and decisions (not closed by this record)

| Item | What remains | Owner (IDEA-024 allocation) | Record |
|---|---|---|---|
| Real-text semantic accuracy (T01) | Independent annotators (not implementers), a rights-cleared corpus outside Git, a labels commit frozen before predictions; then run `realeval` | Yao Zhu + an annotator not involved in implementation | GAP-67, GAP-26 |
| LLM value | Select an authorised no-additional-cost model (or none); run `model_vs_deterministic` | Team (GAP-57) | GAP-57 |
| Evidence authority | Decide whether any falsifier predicate is DISCRETIONARY_EXIT or MANDATORY_REDUCTION; the default stays SHADOW. Statement authority stays SHADOW until its own prospective gate | Team; Keith + Yao Zhu propose | GAP-64, IDEA-018 R3 |
| Entry capability | Rights-cleared underlying price history and basis validation (GAP-56); a depth-rule replacement (GAP-51). Entries are blocked until then, by design | Team / Isaac + Keith | GAP-51, GAP-56 |
| Source activation | SEC contact User-Agent; dated terms captures (`terms_evidence_sha256` is null); a production store and artifact location outside the repo; per-source polling cadence | Keegan (store/archive), Yao Zhu (sources) | GAP-23, GAP-24 |
| Economic studies | An EXP record with registration v2, rights-cleared point-in-time data and cost measurements before any profitability study; inconclusive results keep the default | Keith + Yao Zhu | GAP-64, GAP-67 |
| Execution integration | The runtime still uses a fake execution port; W04 integration with commands/reservations, the `INCOMING:` row in settlement reducers, and Linux isolation tests | Isaac + Keegan | GAP-65 |
| Merge | This branch is not merged to main; merging needs owner review (PRs #3–#6 are still open or draft) | Team | — |

No deployment, trading, signing, ai-seeds upload, paid service, vendor or organiser contact, or model training occurred. The pre-existing untracked `Claude outputs/` directory was not run, edited or committed.

## V07 — PR #7 review follow-up (2026-10-10, Codex / Keith request)

[IDEA-032](IDEA-032.md) records five concrete findings and pushed fixes, including ordinary merges of the 10 newer strategy/risk and execution owner commits. The canonical EvidenceContext.v1 boundary remains the strategy input. BUY audit amounts now record USDT spent, bounded source polling retains continuations and reports incomplete coverage (including failure/exhaustion recovery), and evidence consumption rejects future/mismatched result clocks. Integration/demo fake quotes now carry exact-input fields; the CI test profile includes the existing NumPy pin. On `4c63282`: local PostgreSQL acceptance 503 passed / 3 Linux-only skips / 728 subtests; Linux CI 506 passed / 728 subtests / no skips, with Terraform and Docker checks passing. `9aba1a4` adds the tested continuation-recovery guard (25 source tests/probes passed) and refreshes the demo artifact. Details and final CI evidence are in IDEA-032. Linux isolation is now verified in CI; real execution/settlement integration, rehearsal, independent real-text/economic evaluations and team authority/configuration decisions remain open under V06's named owners. PR #7 remains unmerged.
- 2026-10-11 ID note (PR #7 merge preparation into `codex/engine-foundation`): the merged tree adopts the foundation numbering. The owner-branch record "First engine increment: offline policy boundary" is [IDEA-023](IDEA-023.md) (the `IDEA-023-offline-policy-boundary.md` file above is replaced by it), main's proposed-solutions record is [IDEA-032](IDEA-032.md), and the PR #7 review that V07 above cites as IDEA-032 is [IDEA-033](IDEA-033.md). Both records' content is unchanged; see the note at the top of IDEA-023.
