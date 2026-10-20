# PR204 — captured LLM trial audit and complete repair handoff

**PC-AUDIT01-HO01. This PR preserves the verified shutdown and completed audit. The four application repairs below are OPEN; this PR does not implement or deploy them.** Yao will ask an implementer to take them. Suggested owners below identify the existing implementation/quality roles; no message or assignment has been sent to anyone.

Start from the latest canonical `codex/system-testing-20261012`, recheck whether any intervening merge fixes a finding, and preserve this PR's evidence. The audit baseline was canonical **`697ff3a9e4f310aae7980dc61f0fedc376d148a7`**, rechecked remotely when preparing this handoff. Captured runtime: **`ea25b52325656a19b29e8ddb07b94dd792be6e18`**, run `larp-dev-llm-trial-20261018t170339z`, database `larp_trial2`, shadow execution. Resolved legacy LLM timing/review issues are deliberately excluded from the repair queue.

- [Full audit and scope](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/codex/llm-trial-stop-20261020/docs/build/LLM_TRIAL_AUDIT_20261020.md)
- [Aggregate evidence and result/script hashes](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/codex/llm-trial-stop-20261020/docs/build/evidence/llm-trial-audit-20261020.json)
- [Offline reproduction instructions](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/codex/llm-trial-stop-20261020/docs/build/ops/trial-audit-20261020/README.md)
- [Shutdown/export record](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/codex/llm-trial-stop-20261020/docs/build/LLM_TRIAL_STOP_20261020.md)

## What the data actually establishes

70 assessment jobs repeatedly examined **two filing records/two issuers**; four filing records were stored in total. OpenAI primary: 68/70 ASSESSED, 103/103 returned messages schema-valid, 58/58 proposed claims verifier-passing. Accepted combined results: six nonempty ASSESSED, 35 empty ASSESSED and 29 unavailable. All 24 emitted combined claims reverify, but they are repeated `ITEM:2.02`/`ITEM:9.01` tags. SK hynix's 35 results contain no claims and retain UNKNOWN thesis.

The deterministic baseline replayed the same 70 immutable requests/source bytes/cutoffs with 70 ASSESSED results; its finding/claim-metric sets match all 41 captured ASSESSED outputs. No extra economic fact over baseline was established. All 350 stock targets were KEEP_QUANTITY / MISSING_MARKET_OR_BASIS, with zero intents/orders/commands. The historical EQUAL_WEIGHT profile was pre-entry and had unverified basis; this was not the later S1 deployment. These are historical capture measurements, not a current-router live-performance projection, labelled accuracy, positive-event recall or trading alpha. Independent labels/coverage/adoption remain separate.

## R1 / P1 — freeze model input records at dispatch

**Evidence:** 81/174 normalized completed-step inputs differ from the original saved HTTP inputs: OpenAI35, Kimi34, GLM12. Every difference is `input.tool_results`: a later tool append appears in an earlier call's normalized input. Original HTTP artifacts are intact. The current-code real-input deterministic witness reproduces the mismatch on its first of two model steps.

**Root cause and starting locations:** [`_State._view`, agent.py:143](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/697ff3a9e4f310aae7980dc61f0fedc376d148a7/larp/intelligence/agent.py#L143) returns the mutable `self.tool_results` list. [`_assess`, agent.py:306–320](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/697ff3a9e4f310aae7980dc61f0fedc376d148a7/larp/intelligence/agent.py#L306) retains that mutable request dictionary, although the separate `Document` dispatched to the model is frozen.

**Required change:** create one complete immutable/deeply detached dispatch snapshot before publishing it as in-flight or completed I/O; use equivalent content for dispatch, deferred hooks and final trace. Detach nested values, not just the outer dictionary. Preserve input bounds and existing worker ownership/deadline behavior. Suggested implementation owner: Isaac/LLM maintainer; reviewer: Keegan/runtime-audit owner.

Acceptance:

- [ ] R1-T1: a new regression fails on canonical baseline, then passes after repair: step0 input stays byte-equivalent to its dispatch snapshot after one and multiple later tool calls.
- [ ] R1-T2: cover nested tool-result values, model-input truncation, a tool error, a provider error and an in-flight/abandoned assessment. Neither retained earlier requests nor sent bytes may change.
- [ ] R1-T3: verify request equivalence across normal, deferred and parallel-review traces, including MODEL_REQUEST and final result records. Provider calls remain parallel; no lock held through model/network work.
- [ ] R1-T4: validate exact wire content using recorded/synthetic transports; replay must use actual HTTP inputs, not the already-mutated historical normalized fields.
- [ ] R1-T5: retain historical logs/anchors and mismatch provenance. Do not rewrite uploaded records. If a reconstruction/correction manifest is supplied, keep it separate, referencing original event/request IDs and raw payload hashes.

**Priority:** repair R1 before another trial. Hash-chain integrity alone does not establish truthful model-input content.

## R2 / P2 — address reviewer completion exhaustion and retain rejected usage

**Evidence:** all eleven recorded external codec errors are single-choice `finish_reason=length` replies at exactly4,096 completion tokens: Kimi7, GLM4. In nine, reasoning consumes all4,096. Current codec reproduces all11 refusals. The current checked-in trial routing spec is byte-identical to the captured one, including the4,096 shared cap.

Known raw AIand replies contain **336,797 input /71,194 completion tokens**, versus **273,288 /26,138** normalized. The45,056 missing completion tokens are11×4,096. Raw reasoning breakdown totals62,141 tokens. The25 historical external calls without a completed-step record are not zero-cost calls; invoices are still needed.

**Starting locations:** `config/intelligence/aiand-routing.openai-trial.example.json`; `routing.py::validate_routing_spec` / `build_routed_assessor` (shared `max_output_tokens`); `aiand.py::_body` / `_parse_reply` (lines54–86); `providers.py::HostedModel.step`; `models.py::response`; `routing.py::BudgetedOpenAI` (maximum reservations).

**Required change:** Keith + Isaac select an affordable, explicitly recorded per-stage completion strategy: adequate bounded output allocation and/or a compact response/citation contract. Preserve model/effort choices unless separately decided. If stage-specific cap fields are introduced, define schema/backward compatibility and manifest/hash handling; do not silently reinterpret an existing pinned routing file. Preserve validated usage/finish reason for incomplete/rejected responses without treating their content as usable evidence.

Acceptance:

- [ ] R2-T1: all11 old truncated replies remain ERROR/UNAVAILABLE; they must not become valid decisions after the repair. Report `length` separately from multiple choices and transport failures.
- [ ] R2-T2: raw-vs-normalized known usage reconciles for successful, incomplete, malformed-output and provider-error replies with usable usage. Missing/untrustworthy usage remains unknown; no invented invoice or refund.
- [ ] R2-T3: if caps differ by stage, prove that each provider request gets exactly its pinned cap; preserve legacy-spec behavior and refusal of invalid/unbounded settings.
- [ ] R2-T4: any OpenAI cap change updates conservative maximum reservations before dispatch. Recheck concurrent reservations, UNKNOWN retention, UTC-day/total caps, clock quarantine and actual-usage-over-bound behavior. Do not globally raise the shared cap just to help external reviewers.
- [ ] R2-T5: supply the selected settings, output-size/affordability rationale and offline completion/contract checks. Paid qualification is separate and requires an explicit prospective packet/authorization; this handoff grants none.

## R3 / P2 — improve reviewer citation/schema reliability

**Evidence:** 15/35 Kimi proposed claims were rejected: **six SPAN_TEXT_MISMATCH, seven METRIC_NOT_IN_SPAN, two ITEM_NOT_IN_RECORD**. Five stages abstained for unsupported claims and one for MODEL_OUTPUT_SCHEMA. Recorded claim-verification rate20/35=57.14% is a contract statistic, not independent accuracy. All six current-assessor replays, using identical original HTTP inputs and pinned prompts with a180s ceiling, retain the same abstentions. Current adopted review selection correctly yields DISSENT/ABSTAIN with the recorded assessed primary.

**Starting locations:** `config/intelligence/prompts/routing/review.md`; `routing.py::stage_config`; `models.py::parse_output`; `agent.py::_verify_claims` / `_bind_source`; `verify.py::verify_claim`; `tools.py` document/span tool output. Existing predicates, issuer identity and metric allowlists still govern.

**Required change:** Keith + Isaac make exact source/span references and output structure reliable. A compact harness-issued citation handle is a candidate, not an adopted protocol: any handle must bind to an exact point-in-time source/document/span and typed claim. Do not guess offsets, switch source records, expand supported metrics casually, or drop rejected claims to make the overall assessment appear valid. Pin/version any changed prompt or output contract.

Acceptance:

- [ ] R3-T1: the six historical malformed responses remain safely rejected/abstained under their original contract. Replaying the same bad output is not a new valid provider result.
- [ ] R3-T2: add portable synthetic counterparts to the real private counterexamples. Check wrong record/item, wrong document, off-by-one/Unicode/repeated text spans, metric outside the cited span, wrong issuer, future/revised evidence, and malformed/unknown fields.
- [ ] R3-T3: if using handles, only a handle actually supplied in the bounded model input may resolve; reject invented, foreign, stale, truncated-away or ambiguous handles. Retain complete resolved claim provenance.
- [ ] R3-T4: preserve strict verification, the existing dissent policy, authority/tool budgets and no-signing boundary. No permissive fallback accepts unsupported reviewer content.
- [ ] R3-T5: report schema and claim-verification numerators/denominators separately by stage, on the fixed private corpus; preserve the independent-label gate. Prompt/code repair is not evidence of improved real-provider accuracy without a separate measured test.

## R4 / P2 — make reporting budget-aware and expose failure causes

**Evidence:** `bakeoff.py:27` sets `DEADLINE_MS=60000`; line106 uses it for `within_deadline`, versus current `time_budget.py::MAX_ASSESSMENT_MS=180000`. The reporting-only120,000ms witness is incorrectly late under a180,000ms request. The helper also folds the11 token-limit completions into schema-invalid counts while reporting zero provider errors, hiding their cause.

**Required change:** Keith/LLM tooling owner binds metrics to actual immutable request/stage allowances, retaining explicitly selected historical protocol budgets. Do not replace every60s threshold with180s: historical requests and individual stages can have different bounds. Keep the frozen M5 denominator; add cause-specific diagnostics and known rejected-response usage without retrospectively improving a frozen result.

Acceptance:

- [ ] R4-T1:120,000ms is timely under180,000ms and late under60,000ms or90,000ms; mixed-budget batches use each result's actual bound. Cover exact equality, overrun and invalid/missing bounds.
- [ ] R4-T2: preserve explicit historical60s reporting; missing metadata remains unqualified/unknown, not silently valid under the largest configured limit.
- [ ] R4-T3: distinguish request-to-usable-result delay, internal stage elapsed time, late audit-only replies, unavailable jobs and busy/not-started jobs. Never count late/unavailable content as timely accepted evidence.
- [ ] R4-T4: separately report token-limit completions, schema errors, unsupported claims, transport/provider errors and deadline failures, while preserving the frozen schema denominator and historical counts.
- [ ] R4-T5: recover the45,056 known rejected-completion tokens from raw evidence in the report; preserve lower-bound/unknown flags for unresolved calls and prices. Recompute a report with exact request/config/prompt/source/result identities.

## Private data and reproducible evidence

Yao holds the private data. On the collecting Mac:

- Repository root: `/Users/songyaozhu/binance-hackathon`.
- Archive: `deploy/activation/trial-stop-20261020/final.tar.gz`, **31,701,204 bytes**, SHA-256 **`587aeb67bafde94061889eeff55bf57a91811e64864e998e20d20f87dbe398d0`**.
- Extracted inputs: `deploy/activation/trial-stop-20261020/final-data/`.
- Final private audit outputs: `deploy/activation/trial-stop-20261020/audit/final/`, including `per-job.json`, `baseline-results.json`, `input-mismatches.json`, `private-witness-cases.json`, `summary.json`, `witnesses.json`.
- Provider test log: `deploy/activation/trial-stop-20261020/audit/focused-checks-final.log`.

An implementer on another machine needs an approved private transfer from Yao; these paths are not a public downloadable dataset. No credentials, raw source/model I/O, labels, private endpoints or `.env` belong in Git/PR comments. The immutable AWS copy is retained through2027-01-10. Keep original artifacts/logs unchanged.

From the repo root, with private data present:

```bash
export LARP_AUDIT_DATA_DIR="$PWD/deploy/activation/trial-stop-20261020/final-data"
export LARP_AUDIT_OUTPUT_DIR="$PWD/deploy/activation/trial-stop-20261020/audit/reproduction"
python3.12 docs/build/ops/trial-audit-20261020/witnesses.py
```

The reproduction checks intelligence working files against the canonical ref and intentionally proves the defects on the audited source. Run the baseline witness in that exact source state; on a repaired build replace/update the expected defect assertion with regression acceptance. A disappearing defect witness is not grounds to restore the bug. The script uses recorded responses, not live transports.

## Completed checks and implementation delivery

Already verified:14,544 export file hashes/Backup.v1/three SQLite integrity checks;188 journal batch/event/head hashes and terminal projection; exact outboxes/109 ACK chunk bytes;496 referenced artifacts;70 point-in-time/tool/accepted-deadline checks;zero signing/execution/command rows. All103 settled OpenAI costs match recorded usage ($0.880356); three UNKNOWN reservations remain$0.337180 including shared/prior usage. All71 recorded AIand model/high-effort metadata pairs match. No credential-pattern candidate found, within the documented scan limits.

**38 focused existing tests PASS**, Python3.12.14/macOS, synthetic transports; two tests use localhost HTTP. Reproduce the focused set with:

```bash
python3.12 -m unittest \
  tests.intelligence.test_assessment_budget.ReviewOutcomes \
  tests.intelligence.test_stage_prompts \
  tests.intelligence.test_providers \
  tests.intelligence.test_bakeoff
```

- [ ] Implement in reviewable commits/PRs against current canonical, with red-before/green-after evidence for actual code defects; follow repository commit/push-before-execution and no-history-rewrite rules. Scope changes need recorded rationale, not new retrospective pass criteria.
- [ ] Run focused and change-appropriate broader checks. Changes to routed/deferred I/O need relevant concurrency/ownership/audit regressions and applicable Linux/PostgreSQL/systemd/sandbox qualification; the existing38 macOS checks are not a substitute. Run bundle/manifest/hash checks where changed files affect release identity.
- [ ] Publish exact commits, reproduction commands, results/skips, per-finding disposition and any private corpus hashes. Do not blindly regenerate decision goldens; explain every semantic change.
- [ ] Preserve immutable originals and shared accounting: never reset the ledger, erase UNKNOWNs, relax verification to pass, manufacture labels, or reinterpret old trial hours/thresholds.
- [ ] Once each repair is fully verified, remove its entire `PC-AUDIT01-Rn` backlog line and retain completion evidence in the ledger; partially completed items remain narrowed. Update PR133's noticeboard and PR204's repair status.
- [ ] Obtain independent review and new exact-release/host acceptance through the existing owners before any installation. No repair completion, live quality pass, restart, paid inference, wallet operation or deployment is authorized by this handoff.

The trial remains retired: all six trial services/timers were verified inactive/disabled, final sequence188 anchored, original EC2/RDS/configs/databases retained. Independent labels, provider billing/rights, selected profile, model adoption and signed/final-host gates remain with their existing owners. PR133 remains noticeboard-only.
