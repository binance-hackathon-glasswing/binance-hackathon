# Evidence, source and integration contracts (IDEA-031)

Applies to branch `codex/evidence-hardening`. Record: [IDEA-031](../ledger/IDEA-031.md). This document describes the schemas the code enforces; the code is authoritative where they differ. Nothing here adopts a trading policy: every new evidence influence defaults to SHADOW.

## Records and their producers

| Schema | Producer | Consumer | Key fields |
|---|---|---|---|
| Fact (`statement` field) | `intelligence/facts.py` extractor; `verify.py` for model claims | agent, gate | Numeric: signed exact value or range, unit, scale, period, kind REPORTED/GUIDANCE. Event: plain code = issuer's current occurrence; `STATEMENT:<event>` = any other statement, with `statement` (EventSemantics.v2) |
| EventSemantics.v2 | `intelligence/semantics.py` `classify_event` (shared by extractor and verifier) | facts, verifier, lifecycle | `assertion` OCCURRED / ANNOUNCED_FUTURE / ATTRIBUTED_REPORT / FORECAST / CONDITIONAL_RISK / NEGATED / MENTION_ONLY; `actor` ISSUER / THIRD_PARTY / UNSPECIFIED; `attribution`; `temporal` CURRENT / HISTORICAL / FUTURE / UNKNOWN; `effective` ISO date; `cues` |
| SourceStatement.v1 | `semantics.classify_source_statement` | SourceDocument.v1 | `statement_type` REGULATORY_ACTION / DEVELOPMENT_CLAIM / OTHER_STATEMENT; `actions` (PROPOSED_RULE ≠ FINAL_RULE; COMPLAINT_OR_CHARGE = allegation, not finding); `certainty`; `issuer_relations` only for issuers named in the same source, effect UNKNOWN |
| AssessmentResult.v2 | `intelligence/agent.py` | gate, runtime schema check | v1 fields plus `event_statements` (statement_id, novelty, match, semantics, fingerprint), `retained_facts` (audit only when not ASSESSED), `coverage` (bounds, truncation, prior history checked), `evidence_used[].revision/supersedes/quality`, `findings[].sources` |
| IssuerEvidenceState.v2 | `intelligence/gate.py` `accept` (pure reducer) | `consume` → EvidenceContext | `statements` registry (lifecycle), `unresolved_adverse` latches with `resolution_rule`, `resolved_adverse`, `records_seen`, `assessed_until_ms`, `last_rejection`, `lifecycle` policy |
| EvidenceView.v1 | `gate.consume(state, now)` | integration | As-of status (CLEAR ages to STALE), adverse latches, statements by status, due reviews |
| EvidenceContext.v1 | `integration/contract.py` `build_evidence_context` | `strategy/policy.py` via `accept_for_strategy` | run, issuer, underlying, token, profile hash, state_version, as_of/cutoff/assessed_until ms, status, quality, review_complete, falsifier_findings, statements pending/exhausted, due reviews, `context_hash` (domain `larp.evidence-context.v1`) |
| RuntimePlan.v1 (PlanResult.v1 shape) | `integration/runtime.py` `RuntimePlanner` around `risk/planner.py` | `runtime/coordinator.py`, PostgresStore | intents + `decision_id`, `amount` (exact decimal string), `expires_ms`; reservation deltas as `{intent_id, asset, units}`; `jobs` (evidence lane); `risk_state` |
| SourceDocument.v1 | `sources/ingest.py` | shadow statements, clustering, future evaluation | source/publisher/original publisher, item id, canonical URL, version, supersedes, status ACTIVE/WITHDRAWN, content/raw/text hashes, licence + register hash, exclusions, published {raw, ms, precision, replay bound}, event_times, retrieved/first_seen/available ms, untrusted_instructions, statement, `authority: SHADOW_ONLY` |
| SourceCursor.v1 | `sources/ingest.py` | `sources/store.py` (SQLite) | seen item versions, rejected items, in-progress page URL, ETag/Last-Modified, watermark, per-source health |

## Semantic rules (summary)

PR #7 review corrections ([IDEA-032](../ledger/IDEA-032.md)): BUY audit `amount` is exact USDT pay amount using the planner's money scale, while SELL `amount` is token quantity using token decimals. AssessmentResult.v2 must carry nonnegative integer clocks with `cutoff_ms ≤ started_ms ≤ completed_ms ≤ consumption time`; runtime additionally requires the exact request cutoff. Source page budgets apply per poll: unprocessed continuations persist across restart, incomplete coverage stays visible, and abandoning a failed continuation forces a full rescan without conditional validators.

- Findings come only from OCCURRED ∧ actor ISSUER ∧ temporal CURRENT, re-verified from source text before use, even when the model abstains. Everything else non-negated is a statement and is never a finding.
- Actor: trigger complement ("at one of our suppliers"), passive by-agent, object of a verb trigger, then the mention nearest before the predicate; issuer words inside prepositional phrases are not subjects; named companies (corporate suffix or capitalised possessive) are third parties.
- Scope: negation, modality and years are read in the conjunct holding the trigger, excluding non-restrictive relative clauses and leading concessive clauses. Quoted speech is read with its speaker.
- Frames that assert no occurrence: headings and tables of contents, generic present-tense policy text, scenario/simulation/counterfactual wording.
- Numbers: sign from the governing (nearest preceding) metric mention; only the first amount after it; change amounts and analyst estimates are not levels; ranges (between / range of / X–Y / X to Y) are never points; kind from the statement's own wording.

## Lifecycle and authority

- Statement identity: event, assertion, actor, temporal, effective date, anchors (amounts with scale, dates, years, quarter ordinals, officer titles, third-party roles) and content words with modal verbs normalised. Relations: EXACT, SEMANTIC_SAME, SUBSTANTIVE_CHANGE, UNCERTAIN_MATCH (exposed, never merged).
- Novelty: PRIOR_NOT_CHECKED, HISTORY_UNAVAILABLE, FIRST_SEEN, REPEATED, CHANGED, UNCERTAIN_MATCH, ALREADY_SEEN (accepted before, including a reread of the same filing).
- Review: PENDING_REVIEW → ACKNOWLEDGED after a complete reassessment with history checked; incomplete reassessments back off exponentially to REVIEW_EXHAUSTED. Corrections and withdrawals mark statements CORRECTED/WITHDRAWN and resolve adverse latches only under SOURCE_CORRECTED_OR_WITHDRAWN.
- Authority (strategy profile): `falsifier_authority` NONE / SHADOW (default) / DISCRETIONARY_EXIT / MANDATORY_REDUCTION; `statement_authority` SHADOW (default) / ENTRY_BLOCK. No adoption record makes any non-SHADOW value live.

## Free sources

| source_id | Enabled | Rights basis | Notes |
|---|---|---|---|
| sec-press | yes (needs `LARP_SEC_USER_AGENT`) | SEC public dissemination (`https://www.sec.gov/privacy`) | not probed: no contact User-Agent configured |
| fr-bis | yes | NARA Federal Register reproduction permission | date-only publication; effective/comment dates kept |
| fr-public-inspection | yes | same | `filed_at` second precision |
| doj-press | yes | DOJ legal policies (copy/distribute unless otherwise indicated) | `date` kept at DAY precision; attachment/image fields not retrieved |
| ec-press | yes | CC BY 4.0 unless otherwise indicated | attribution includes licence and normalisation note |
| ftc-press | no | FTC website policy | RSS 404 on 2026-10-10 (rechecked by probe) |
| fed-bls-calendar, eff-articles | no | agency policies / CC BY 4.0 | optional, not delivery dependencies |
| gdelt | no | project data only | discovery metadata only; never body retrieval, corroboration or veto |
| wikinews | no | per revision | archive-only since May 2026 |
| opendart, issuer-newsrooms | no | not established | disabled with reasons |

Retrieval is https-only to allowlisted host/path prefixes, follows redirects only within the allowlist, caps bytes, retries with exponential backoff, sends conditional requests, and commits each page durably. Artifacts (permitted raw item JSON and saved text) live outside the repository.

## Commands

- Semantics, lifecycle and evidence: `python -m pytest tests/intelligence tests/redteam`
- Integration (needs disposable PostgreSQL for the store tests): `LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/larp_test python -m pytest tests/integration/test_evidence_pipeline.py` (`docker compose -f deploy/compose.test.yml up -d`)
- Sources: `python -m pytest tests/sources`; read-only connectivity probe: `python tools/probe_free_sources.py --out <outside repo>`
- Fixture demonstration: `python -m larp.intelligence.evaluation` (synthetic pack) and `python -m larp.integration.demo`
- Real-document evaluation (NOT RUN without an external, independently labelled manifest): `python -m larp.intelligence.realeval --manifest <outside repo>`
