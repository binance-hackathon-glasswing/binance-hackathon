# IDEA-049-A — Final review A: inputs, evidence, data sources and model

- Date: 2026-10-15 SGT.
- Reviewer: Keith, working for GitHub user `wtvlol`.
- Branch: `review/final-a-20261015`.
- Base: `c1b6dafd62f8df7ea894a5177138da2726452696` (latest fetched integration head at setup).
- Worktree: `/private/tmp/larp-final-a-20261015`; main checkout remains clean on `codex/system-testing-20261012` at that fetched head.
- Catalogue: [A-catalogue.md](../build/final-review/A-catalogue.md).
- Status: **phase 1 prepared; catalogue push gate pending. Review NOT COMPLETE; deployment blocked.** No implementation, tests or live parameter values changed. The previous `review/final-a-20261014` worktree at `5bb1143` was discovered through Git metadata and left untouched; its review contents were not read as requirements.

## Integration prerequisites (checked live before catalogue work)

Read-only GitHub commands: `gh pr view 20 --json state,baseRefName,mergedAt,mergeCommit`, the same for #21, `gh pr list --state merged --base codex/system-testing-20261012 --json number,title,mergeCommit,mergedAt,headRefName --limit 30`, and `gh pr view 66 --json body,mergeCommit,baseRefName,state`.

| Input | Verified disposition |
|---|---|
| PR #20 | MERGED into `codex/system-testing-20261012`, `2026-10-14T11:27:54Z`, merge `faf9adc37e49daafbc2490a77b9871462c7c066e`. |
| PR #21 | MERGED into that target, `2026-10-14T11:41:42Z`, merge `c829fae038a0589085d13552b1123802babbde4c`. The runner path's latest Git commit at the tested base is `7498d1785ebc7f9dae1a484899c6101b14d82bdb` (`fix: address PR21 final review protocol comments`); runner implementation inspection waits for phase 2. |
| Driver PR #66 | MERGED into that target, `2026-10-14T15:09:51Z`, merge/base `c1b6dafd62f8df7ea894a5177138da2726452696`. Head `claude/round-driver-20261014`; PR body says the original IDEA-048 branch history is merged. Accepted scope includes runtime service/shadow modes and execution-service/signer/settlement/round-close integration with synthetic external ports. This review has NOT RUN those tests. |
| Driver production boundary | PR #66 explicitly retains fake-only Executor capabilities, unverified router/quote decoder and native-top-up receipt refusal. It reports live execution exiting `NOT_INTEGRATED / EXECUTOR_CAPABILITY_GATE`; shadow remains the rehearsal mode until those gates close. Integrated driver coverage is not production signing readiness. C/D must test the final merged execution path. |

No missing-driver exclusion is needed to start this A catalogue because #66 is integrated. Its still-blocked production capabilities remain C/D-owned inputs, not an overall completion waiver.

## Phase 1 evidence and independence

Read the common protocol and A prompt in full, then checked them again on the fetched tree. Read AGENTS.md, core SKILL.md's reading contract/never-do list and relevant F/Q/G source summaries; ledger index table; relevant backlog lines; verbatim official page; submitted proposal; participant Guide pp.2–3 and 13–18; protocol/logging/Web3 copies; K2/K15/K18; explicitly permitted decision sections in plan/IDEA-035/037/046/047/041; DR checklist; AT matrix. The IDEA-041 stale-bound check was limited to §2.1, which explicitly describes seven days as awaiting team confirmation. R15's later implementation decision narrows R3's original WAL arrangement; it was read only as an exact decision source, not as current test evidence.

No application implementation, tests, prior issue inventory, tracker/child issue bodies or old review records were inspected to derive requirements. Fetch/merge diff filenames, Git metadata and #66's required integration disposition do not supply requirement authority. Environment lockfiles are the protocol §0.4 setup exception; they were used without application imports. Summary findings are not inferred from historical results.

Catalogue: **78 requirement rows; 99 use-case rows (80 group/axis families plus 19 explicit scenarios); 12 assumptions; 9 conflicts**. Scope closure maps the named A F/K/never-do/G/decision/backlog inventory, all DR-01–22 and AT01–20, every nonempty proposal line and remaining shared source inventory. Scenario families must be expanded into meaningful concrete boundaries during tracing/testing; this count is not passed-test coverage.

The in-scope F/K summaries agree with the checked verbatim text. No summary correction was established. Complete original I/O remains local, credentials are excluded, and encrypted reasoning is excluded from official output. Q-16 summaries are answered in practice; do not present them as an unanswered daily-trace format question.

## Environment and baseline

| Item | Current evidence |
|---|---|
| Python | Disposable `/private/tmp/larp-final-a-test-env`, Python **3.12.14**, created from the available 3.12 interpreter. Installed `deploy/requirements-test.lock` and its included runtime/AWS/signer locks. `pip check`: **No broken requirements found**. No AWS client/login was invoked. |
| Document extraction | Disposable `/private/tmp/larp-final-a-doc-env` with pypdf, used only to read the original Guide. Guide SHA-256 `8b14a371c67f4d2105b62dde33d0b02f7be1ab914ed6a255fc3f0bf9fc586f86`, 18 pages. Extraction in `/private/tmp/larp-final-a-guide.txt`, outside Git. |
| Docker | Client/server **29.8.2**. Disposable PostgreSQL **14.24 not started yet**; local image listing did not establish an available tagged pinned version. |
| Terraform | Not required for A-only paths; not invoked. |
| Artifacts | `/private/tmp/larp-final-a-artifacts`, outside Git. Catalogue authoring helper remains outside the worktree. No real-source artifacts fetched. |
| Unchanged full-suite baseline | **NOT RUN**. Required only after the independent catalogue is frozen and pushed, before any phase-2 code/test changes. Record exact passed/skipped/subtests and tested SHA when run; historical PR counts are not this review's baseline. |
| System test / Linux CI | **NOT RUN** for this branch. No pass claim or CI run ID. |

### Prospective baseline criteria (before execution)

After catalogue freeze is committed and pushed, run the unchanged full suite against the application tree at the recorded base using Python 3.12 and a disposable local PostgreSQL 14.24 database. Record the exact command, branch HEAD, base, database image/version, output artifact hash, passed/skipped/subtests and every environmental skip or failure. Baseline failures must not retroactively shape frozen requirements. Do not alter code/tests before recording that baseline. All new defect/test hypotheses require a later committed and pushed pre-registration before they run.

Catalogue freeze commit is identified by the required message: `docs: freeze A requirements catalogue before code review (IDEA-049)`. Its concrete SHA and remote confirmation must be recorded in a dated amendment after the push. Until then, **phase 2 is not authorized by the protocol gate**.

## Findings, fixes and retests

**NOT STARTED.** No application defect has been established by a test or implementation proof in this review. No fix/retest SHA. Assumptions/conflicts are not fabricated failing test results.

## DECISION-NEEDED

| ID | Decision / alternatives | Recommendation and owner / deadline |
|---|---|---|
| A-DEC-001 | Exact assessor provider/model and API budget versus explicitly declared deterministic assessor. | Preserve the B8 choice for team + Yao Zhu; bake-off evidence by Oct 19, final choice Oct 22. No provider credentials requested. No model or budget chosen by this review. |
| A-DEC-002 | Each live intelligence cadence/freshness/clock/retry/TTL/backfill/job parameter. | A enumerates actual fields and gives per-value derivations only after freeze, then team approves by Oct 22. Null/default code values are not decisions. |
| A-DEC-003 | Adopt or change the seven-day red-flag age bound. | Team + A derive from decision cadence, five-session lifecycle, persistent adverse evidence and 14-day run by Oct 22; IDEA-041 calls it an engineering value. No new decided value committed. |
| A-DEC-004 | Qualitative agentic sufficiency and declared model/source/calendar deviations. | Team + A/D explicitly accept the final assessor/harness and release deviations before Oct 26. Deterministic fallback alone is not demonstrated agentic compliance. |

## Deployment risks / pending validation

| ID | Risk | Owner | Validation step | Deadline | Blocks deployment? |
|---|---|---|---|---|---|
| A-RISK-001 | Source/model rights and dated terms have not been verified by this review. | A + team | Per-contact register/terms hash and contest/retention/audit rights check; disabled-source refusals. | Before Gate A / adopted source use | Yes |
| A-RISK-002 | SEC/issuer identity, SKHYB coverage, revisions and real-text accuracy not proved. | A; B for policy acceptance; Yao Zhu + independent annotator for real labels | Trace after freeze; rights-cleared coverage and independent T01/bake-off evidence. | Before live evidence authority; Oct 22 cut | Yes |
| A-RISK-003 | Live values, stale bound and model selection are pending decisions. | Team + A | A-DEC-001–004, derived proposals and final pinned manifests. | Oct 22; release Oct 26 | Yes |
| A-RISK-004 | Concurrent evidence reader/writer and 14-day storage/audit retention not tested on this base. | A offline; D + hosts owners for deployment | Real store/restart/growth tests; two-user systemd permissions/hot-journal/legacy migration and capacity drill. | Before Gate A and rehearsal | Yes |
| A-RISK-005 | Catalogue unpushed; full-suite baseline, trace, prior-issue reconciliation, fix loop, system tests and CI pending. | Keith/A | Freeze/push, then phases 2–4 exactly. | Before review completion | Yes |
| A-RISK-006 | Driver merged but actual execution capability gates remain closed. | Isaac + Keegan; C/D review | Final merged executor/decoder/native gas receipt checks and later hosted/rehearsal gates. | Before signed rehearsal / activation | Yes |

These are explicit pending review inputs, not confirmed application failures. No partially completed backlog item is removed.

## For other sections

- **B:** accept A's exact issuer identity and red-flag contract evidence; verify Class 1 sale, Class 2 five-session expiry without forced sale, Class 3 SHADOW, corrected-source re-entry and SKHYB missing-coverage behavior. A will reconcile #25/#39 after freeze; no prior issue disposition invented yet.
- **C:** own actual token/session identity and market data contracts, wallet/chain execution and native-resource constraints. Kit-named Ondo data does not establish bStock identity. #66 live capability restrictions remain.
- **D:** own shared manifest/deviation/services, full trace/export/delivery deadlines and host storage permissions/repair. Supply SEC/model endpoint needs after A phase-2 contact enumeration. Recheck #20/#21/#66 and actual final merged execution path; no AWS/signing action is authorized here.
- **Team + Yao Zhu:** final model/budget, live parameter decisions, stale bound, rights-cleared independent real-document labels and deadline ownership remain explicit.

## Requested shared edits (D applies at integration)

These requests record the current partial status; revise them with verified results at final integration. They do not ask D to mark any backlog item done.

- **docs/LEDGER.md:** add `| IDEA-049-A | Final review A: inputs, evidence, sources and model | phase 1 prepared; catalogue push gate pending | 78 independent requirements, 99 use-case rows, 12 assumptions and 9 conflicts; full-suite baseline/trace/fixes/system/CI NOT RUN; deployment blocked | 2026-10-15 | [ledger/IDEA-049-A.md](ledger/IDEA-049-A.md) |`.
- **docs/INCOMPLETE_WORK.md:** append to the IDEA-049 final-review item: `Section A (Keith for wtvlol, 2026-10-15; IDEA-049-A): independent catalogue prepared at base c1b6daf; freeze push, unchanged PostgreSQL baseline and phases 2–4 remain pending. A owns source/model rights, actual issuer evidence identity, real-text evaluation input reconciliation and complete sampled model-I/O proof. Team owns assessor/budget/live-value/stale-bound decisions by Oct 22; D owns shared final integration. Deployment remains blocked; no whole GAP-23/24/25/26/27/28/56/57/67 closed.`
- **docs/skill/SKILL.md:** no correction requested in phase 1; summary text was checked and no in-scope discrepancy established.
- **README.md:** if displaying review status, use `Final review A is partial: independent requirements prepared; baseline, trace, fix loop, system tests and CI are NOT RUN (IDEA-049-A). This does not establish deployment or activation readiness.`
- **docs/build/AWS_RUNBOOK.md / runbook.md:** retain existing Gate A/B/C restrictions. Add `A review gates: dated rights captures, adopted intelligence values and assessor/budget, verified source coverage and real-text evaluation disposition, complete sampled evidence/model audit trail, and hosted read-only evidence restart/capacity checks. Owners and deadlines: IDEA-049-A deployment risks. Catalogue or synthetic tests alone do not satisfy hosted/rehearsal gates.`

## Completion and handoff

Review is not complete and this session is not ready for a strict handoff: freeze push and every subsequent phase remain pending. No implementation/trading/logging code ran; no registered secret, ai-seeds log call, AWS action, organiser contact or live signing/broadcast occurred. Application full suite/system tests/CI are NOT RUN. Any local unpushed commit must be listed with its SHA in the user-facing status. Shared-doc edits are requests for D, not completed integration work.


## 2026-10-15 phase-2 amendment 1: baseline and prospective defect tests

Supersedes the initial push/environment status: catalogue freeze `990408d086952d2a891f96a153ec6b4615e8829a` was pushed unchanged to `origin/review/final-a-20261015` after wtvlol authorized this and subsequent protocol-required pushes. Draft PR #68 targets the integration branch. Its reviewed application base remains `c1b6daf`.

Unchanged baseline at `990408d`: **1229 passed, 7 skipped, 1561 subtests passed**, 222.15 s, Python 3.12.14. Disposable PostgreSQL 14.24-bookworm, pinned digest `5a05f61a534e50e679d27fb45953afec7821f2ffc2aa6c738b94515ca0891ac2`, container `larp-final-a-postgres-20261015`, loopback port 55435, disposable database `larp_test_final_a`. Command: `env -i PATH=/private/tmp/larp-final-a-test-env/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55435/larp_test_final_a /private/tmp/larp-final-a-test-env/bin/python -m pytest -q -p no:cacheprovider`. Output `/private/tmp/larp-final-a-artifacts/baseline.log`, SHA-256 `6673e0b7a03ebb14035b92d460b5e820c17fbd999e2b1d86f9cffc7c8474dfcf`. Seven skips are Linux isolation, explicit systemd-runner opt-in and external recorded-market input; exact skip reasons will be recorded from the final `-rs` run. No new code/test existed at baseline execution.

GitHub account verified with `gh api user`: `wtvlol`. Refreshed all issue bodies and tracker #22/#42 comments to external artifacts. #25 and #39 remain OPEN. #24/#26/#40 are CLOSED but require C/D current-tree disposition, not inferred proof. New A inputs: #47/#48/#58; #57 is B-owned with A acceptance; #61 and #64's sidecar/network concerns need D/C co-owners. Other #23–40/#43–64 remain explicitly owned by B/C/D for integration. Shared tracker text still calls the original review IDEA-046, which is the hosting-ID collision; D must reconcile original evidence/publication rather than relabel hosting.

### Prospective pass criteria — commit and push before new tests

| Proof | Owning frozen requirement | Suspected defect / pass criterion | Mapping |
|---|---|---|---|
| A-T01 | A-REQ-020,043 | Real canonical registry and real MarketPort with fake HTTP producer: NVDA ticker and SEC-CIK-0001045810 are distinct, accepted through real context/consumer including Class 1; wrong issuer and wrong ticker reject; never certify token/share conversion. | #25, at least P1 |
| A-T02 | A-REQ-028,043,048 | Both clause orders of current non-reliance (restated before/after should no longer be relied upon) produce the same Class 1 evidence; negated, conditional, third-party and historical versions produce no directive. Full ingest/assessor/verifier/gate/contract uses real SQLite and artifacts. | #47, P1 |
| A-T03 | A-REQ-017,028–030,047 | Fresh declared but unverified Class 1/2 item persists across unrelated clean result and writer restart; only verified resolution or complete source correction/withdrawal resolves its exact accession, with reason retained. Stale/backfill/out-of-scope records never acquire actionable authority. | #48, P1 |
| A-T04 | A-REQ-001,014,016,018 | Permanent rights exclusion recorded without fetching restricted bodies or making permitted-source coverage incomplete; changed excluded content reevaluated by hash and register; malformed timestamps/parse errors still impair coverage. | #58 part 1, P1 if DR-12 cannot ever recover |
| A-T05 | A-REQ-016–018 | Every multi-page poll checks page 1 before continuing its saved history tail without losing durable progress or falsely claiming completeness. New head item appears on the next poll; original pagination/crash/rejection tests retain their acceptance. | #58 part 2, P1 dependency recovery |
| A-T06 | A-REQ-039 | All hosted adapters reject credential-bearing request bytes before artifact capture/network; arbitrary transport exception `.code` text is sanitized and cannot echo a credential into the returned error. Existing byte-for-byte safe request/response capture remains. | New suspected secret paths; P0 if reproduced |
| A-T07 | A-REQ-052–062,064–066 | Sampled multistep hosted decision retrieves original prompts, tool definitions, every model request/reply and tool result from real file artifacts/SQLite after close/reopen. Reasoning order preserved; encrypted blocks stay local, never official output. Reader sees 14 days of writer restarts and cannot mutate committed data. | Independent audit/restart proof |
| A-T08 | A-REQ-049,077; A-ASM-003 | Actual SKHYB registry and foreign forms stay scoped; no domestic Item 4.02 directive is synthesized from 6-K, and SHADOW facts are not promoted. Scope decision remains team-owned. | #39: P2 decision needing written team acceptance; not a parser permission |

No fixture or mutation has yet been executed for these new criteria. Runtime review-job ticker-to-issuer mapping is outside A's exclusive code paths (`larp/integration/runtime.py`); A will supply a failing test and D-owned fix request, without silently editing it. Live parameter values, stale bound and SKHYB policy remain unchanged. Source rights captures, provider bake-off and independent T01 corpus evaluation remain NOT RUN without authorized inputs/decisions.


### Amendment 2: first prospective run and fixture correction

Pushed tests `7bdecf4` ran with no implementation change. Initial report: 20 failed / 4 passed (subtest failures included), `/private/tmp/larp-final-a-artifacts/proofs-red.log`. Source policy-exclusion/pagination failures and both credential-path failures are direct proofs. Evidence tests instead hit a test-harness profile mismatch: `World.request` hardcodes the scenario profile, while this new fixture intentionally uses its own profile. They are not application findings yet. Correct the test helper to call the real `build_request` with the fixture profile/run/cursor; all original acceptance assertions remain intact. Push this correction before rerunning; no implementation fix yet.


### Amendment 3: corrected red proofs and audit fixture strengthening

At `d48a3cf`, independent regressions reported **13 failed / 7 passed / 4 subtests passed** (failure count includes subtest failures). Confirmed #25 identity rejection, #47 clause-order miss, #48 loss of pending uncertainty, #58 rights/pagination failures, request credential capture and unsanitized exception-code reflection. Real store fourteen-day restart and foreign-filer non-authority tests passed. The audit fixture had no tool gap and therefore only one model call: switch it to synthetic guidance text requiring prior-context retrieval so it tests a genuine multistep audit, without changing assertions. Strengthen the correction test with an unreadable intermediate revision before a complete reread. These remain pre-registered A-T03/A-T07 boundaries; push fixture changes before the rerun.


### Amendment 4: findings before first fix / additional source-budget criterion

The `c84ab55` audit fixture reaches a real two-call loop and fails because the retained tool call contains only `result_sha256`, not the returned content. Corrected proof artifact SHA-256 `5512d2170a0c6717f64ab3ff0c213a9bddf6f1ea44ed52f0113c6a5eeea8e577`. Findings are now application proofs, not the earlier fixture profile mismatch.

| Finding | Severity | Proof before fix | Planned correction |
|---|---|---|---|
| A-FND-001 | P1 | #25 / A-T01 `WRONG_ISSUER` for canonical NVIDIA CIK + actual NVDA market ticker | Separate issuer/security namespaces and bind through registry; keep synthetic legacy contract compatibility. D still owns runtime review-job ID mapping. |
| A-FND-002 | P1 | #47 / A-T02 reversed restatement clause has no Class 1 finding | Extend only the non-reliance compound phrase; retain external negation/condition/actor checks. |
| A-FND-003 | P1 | #48 / A-T03 unrelated clean result becomes CLEAR after writer restart | Persist accession/predicate uncertainty separately from verified adverse latches; resolve only verification or a complete newer source correction/withdrawal, with provenance. |
| A-FND-004 | P1 | #58 part 1 / A-T04 permanent legal exclusion keeps permitted-source coverage incomplete | Hash/register-bind policy exclusion; preserve genuine processing/parse incompleteness and audit exclusion counts. |
| A-FND-005 | P1 | #58 part 2 / A-T05 new head ignored while saved history continues | Reserve one head page within existing budget, preserve history after known-head overlap, otherwise restart history from changed head; deduplicate through durable store. |
| A-FND-006 | P0 | A-T06: key in request reaches artifact sink/transport; OSError.code reflects key into response | Refuse unsafe request payload before capture/network; normalize transport errors without arbitrary exception text. |
| A-FND-007 | P1 | A-T07: multistep audit cannot retrieve a full tool result from its hash-only call record | Capture the bounded original tool result with the call before constructing a reduced model view. |

Additional pre-registered A-T05b: live paginated source with a page budget of one must refuse startup, since one request cannot serve both a fresh head and an archive continuation. This is a derived engineering capability constraint, not a new trading policy or changed live parameter value. Add its failing test before implementing the preflight guard. Offline one-page legacy recovery fixtures remain supported; the shipped paginated sources already allow three pages. Current first-fix code has no guard yet.

First correction is to be committed/pushed before any execution. Golden fixtures will necessarily change because complete tool-result capture, optional pending state and model-code identity change audit bytes. Regenerate only from pushed code, preserve all former decisions/source facts and separately review structural/hash changes; do not remove any test or weaken its acceptance.


### Amendment 5: first retest, preserved safety assertions and new terms proof

First fix `32c79a0`: focused A tests **5 failed / 372 passed / 1026 subtests passed**; full suite **6 failed / 1240 passed / 7 skipped / 1569 subtests passed**. Seven skip reasons: three Linux bubblewrap tests, three explicit disposable-systemd tests and one external recorded-market artifact test. System runner attempted on this clean pushed head, exit 2 before tests: Linux bubblewrap unavailable; no equivalent green Linux CI tree yet. Not a system-test pass.

All new defect tests except the deliberately red live-page-budget guard passed. Remaining failures are two golden snapshots (model identity/complete tool audit changed), the existing injection assertion (raw untrusted text entered the call summary) and existing pagination fixtures whose HTTP maps expect history-only requests. Fix full tool capture by retaining the complete original tool result as a content-addressed external artifact and placing only its pointer in summaries. The audit test continues to retrieve exact original bytes and verify the original domain-separated result hash; it no longer prescribes embedding raw text in the call summary. Existing injection assertions remain unchanged. The source-local fixture gains the newly required head response; every existing record/version/conditional assertion remains. The red-team fixture path is outside A ownership: requested a test-only user scope exception, pending an answer; otherwise D must update it.

Additional A-T11 pre-registration (A-REQ-014): source terms hashes are currently checked only for presence. A live source must refuse startup when its declared capture bytes are missing or tampered, and pass structurally with matching synthetic capture bytes in the actual external artifact root. This proves capture integrity only, never legal/source clearance. Test committed before its guard fix. Source/model actual rights and dated captures remain owner validation inputs.


### Amendment 6: prospective remaining catalogue probes and terms fix

A-T11 failed at pushed `5047c6e`: a fictitious non-null terms hash with no bytes did not refuse startup. A-FND-008 (P1, A-REQ-014) fixes the guard to read the actual external hash-addressed capture and reject missing/corrupt/oversized or unsafe paths. Existing ready-state fixtures now retain matching synthetic bytes instead of fabricating their presence; all acceptance assertions remain. This is structural integrity, not legal approval.

Golden refresh was run only from pushed `5047c6e`. Independent comparison against base `c1b6daf` confirms original result status, reasons, full claims, findings, falsifiers, proposed thesis, impact, severity, missingness and confidence, baseline comparisons and gate disposition are unchanged in both traces. Only model/code identity, hashes and complete tool-result artifact pointers change. Refreshed files must be pushed before tests use them.

Pre-register before execution:
- **A-T12 / A-REQ-010:** a filing whose acceptance timestamp is one second after the cutoff, but within ingestion's configured clock tolerance, cannot be evidence/model input at that cutoff. It becomes usable only after the timestamp passes. Ingestion tolerance is not permission to use future-stamped inputs.
- **A-T13 / A-REQ-045, #47's second symptom:** current issuer determination that a material impairment charge is required is Class 2 even if recording the already-determined charge uses future tense. Bare hypothetical/forecast/negated/third-party text remains nonactionable. No rule authorizes every “will record” sentence.
- **A-T14 / A-REQ-027:** every declared assessment dimension exists with explicitly unknown durability, uncalibrated ordinal strength and single-issuer source agreement; no return forecast or additional trade authority.
- **A-T15 / A-REQ-020/022, #25 cross-owner path:** explicitly run `PYTHONPATH=. python tests/intelligence/proofs/issue25_runtime_review.py`; a real policy review produced from actual NVDA market metadata must schedule canonical SEC issuer identity. The mapper implementation belongs to D (`larp/integration/runtime.py`) and must not be edited by A without an explicit exception/written owner OK. A failing explicit proof remains P1 even if default discovery is green.

No implementation change for A-T12–15 yet. New tests/proof are pushed before they run. User scope answer for the existing red-team pagination fixture is still pending; no outside-exclusive test path changed.

### Amendment 7: second-round proofs and identity-loader fault criterion

At pushed `63109ad09f723b9a04b3cdd0f89a0ffa12c3c2c2`, focused **2 failed / 377 passed / 1028 subtests passed**, full **5 failed / 1243 passed / 7 skipped / 1571 subtests passed**, 195.22 s. A-T12 proves future acceptance can enter decision inputs within clock tolerance: **A-FND-009, P0**, because RULE-PAGE F-20 forbids unavailable inputs. A-T14 proves missing declared assessment dimensions: **A-FND-010, P1**. A-T13's current impairment determination already passes on this base; #47's second symptom is not reproduced for this exact narrow current-determination text. Broader “will record” is not automatically current fact.

Linux CI `38606727414` is FAILED (runtime); host-bundle and infrastructure jobs passed. Logs: `focused-round2.log`, `full-round2.log` in the external artifact directory. The remaining full-suite failures are the two new requirements, old red-team history-only HTTP map, and copied strategy producer golden. A prepared test-only diff for the last two paths is `/private/tmp/larp-final-a-artifacts/requested-test-exception.patch`; explicit user scope exception requested because both are outside A paths. No outside application code changed.

A-T15 first run failed during fixture setup because actual MarketPort contains SKHYB but the research snapshot universe has four tokens. Filter boundary rows to that fixture universe, preserving actual identity/metadata and real policy/mapper; push before rerunning. That setup error is not evidence of #25's runtime symptom.

Additional prospective A-T16 / A-REQ-020: when the canonical identity registry cannot load, even equal supplied issuer/security strings cannot authorize a record. Inject only a registry-read failure into the real contract after real ingest/assessment; expect WRONG_ISSUER. Suspected first-fix fallback accepts self-matching IDs after loader failure. This criterion/test is committed and pushed before execution and before any fix.

### Amendment 8: strict point-in-time and explicit descriptive dimensions

Pushed `101e770`: A-T16 fails (contract accepts equal IDs after registry-read failure), **A-FND-011 P1**. Additional proofs: 3 failed / 1 passed. Runtime proof still hits fixture unit mismatch before mapping; correct synthetic ledger scaling to real token decimals, retaining held quantity and cost basis. No D mapper fix is made.

A-FND-009 correction excludes original_ms after cutoff in both the real evidence index and retained known-fact context. Ingestion may tolerate source clocks for storage but that grants no early decision authority. A-FND-010 adds all declared dimensions to regular, abandoned and rejected results: verified catalyst identifiers, existing impact, explicitly uncalibrated severity, novelty, UNKNOWN durability, honest one-origin SEC agreement and missingness/conflict risks. It introduces no return prediction, trading permission or live parameter change. A-FND-011 separates registry loading from unknown synthetic-token compatibility: loader failure always rejects identity.

Push these corrections before execution. Subsequent golden refresh must preserve all former decision semantics and copy complete new metadata without inventing calibration or independent sources.

### Amendment 9: narrow regressions green; runtime scheduler proof remains red

At pushed fix `3557947`, all four additional A requirement tests pass. A-T15 now reaches the actual D mapper and prints required issuer `SEC-CIK-0001045810`, actual job issuer `NVDA`, then fails its requirement assertion. **A-FND-012 P1 / #25 residual**, owned by D: `RuntimePlanner._jobs` must carry canonical issuer identity separately from quoted security identity; recommended ContextBuilder token→issuer mapping, with compatibility for synthetic fixtures. Due before activation / final IDEA-049 integration; do not close #25 based on A's contract fix alone. Explicit proof remains outside default discovery deliberately, and therefore a green default suite will not mean this blocker is fixed.

Golden regeneration from pushed `3557947` adds descriptive assessment fields and dependent result/state/tool IDs. Independent comparison with `63109ad` preserves status, reasons, claims, findings, proposed thesis, impact, severity, missingness, confidence, novelty and falsifiers. No live values or policies changed. Raw log `golden-refresh-final.log` is outside Git.

### Amendment 10: partial-HTTP proofs and prospective public terms capture

Focused A retest at `83a741b`: **380 passed / 1028 subtests passed** (10.26 s). An initial sandbox-only attempt could not bind two synthetic localhost HTTP servers; it is environmental failure, not an application finding. Repeated with authorized loopback capability, all tests passed unchanged.

Pre-register **A-T17 / A-REQ-017**: a truncated HTTP response in the real EDGAR adapter must return UNAVAILABLE with only a sanitized exception class; a later valid response recovers. **A-T18 / A-REQ-014**: a partial terms response must produce a failed capture without retaining the partial body and continue to other sources. Inject only external HTTP failures into real adapters/stores. Suspected `http.client.IncompleteRead` escapes handlers that catch only OSError. Push tests before executing; no fix yet.

Prospective read-only terms command from the clean pushed review head: `env -i PATH=<test-venv>:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin LARP_ARTIFACT_ROOT=/private/tmp/larp-final-a-artifacts/terms python -m larp.sources.live terms`. No `--write-register`, no ambient credentials, no issuer-body fetch. Criteria: report every enabled source/EDGAR, date, status, final URL, original-byte hash, and inspect successful originals against the configured rights/exclusions. Missing SEC contact must refuse SEC calls; no contact is invented or requested. Network failures remain failures. A captured page alone is not accepted legal clearance, and no raw terms bytes enter Git. Any metadata update requires successful capture and checked primary text.

### Amendment 11: partial-HTTP findings

A-T17/A-T18 each fail at pushed `27c11f0` with uncaught `http.client.IncompleteRead`: two failed tests, `http-partial-red.log`. **A-FND-013 P1** (#64 evidence-side residual): EDGAR's real HTTP path cannot autonomously report/recover a partial response. **A-FND-014 P2**: offline terms-capture command aborts remaining captures after a partial response. Both corrections catch HTTPException alongside OSError and retain only the exception class, never the partial body. Free-source ingestion already catches HTTPException; no duplicate fix to its existing retry path.

The preregistered public terms capture ran from `27c11f0` without credentials or SEC contact; results in `terms-capture.json`, originals outside Git. This is not issuer ingestion or a model call. All statuses/hashes and checked primary text will be recorded in the final terms disposition below; failures remain explicit.

### Amendment 12: complete trace and prospective remaining offline gaps

Catalogue now has an explicit 78-row Trace amendment, with AST-checked exact existing test names, honest cross-owner CONTRADICTED/MISSING rows and named NOT-OFFLINE gates. It is not a claim that phase 4 passed.

Pre-register **A-T19 / A-REQ-007**: real durable SEC evidence record preserves the exact external source URI through writer close/reopen. **A-T20 / A-REQ-038**: real ingest/assessor/verifier/gate/policy/planner/coordinator using PostgreSQL records a hosted transport failure once, sanitized, with attempt and autonomous retry disposition, no new commands, and idempotent round retry. Existing fake-assessor incident test is WEAK. The synthetic world helper accepts a real artifact sink as well as a real store so the tested path uses durable real storage throughout; defaults stay unchanged. **A-T21 / A-REQ-078**: run the explicit `tests/intelligence/proofs/calendar_declaration.py` release proof: an absent declared planner cannot be waived by an OPEN/DRAFT deviation. D/team/B own implementation or reasoned final approval; no A-owned application fix can decide it.

Push before executing these tests/proofs. If A-T19/A-T20 pass initially, they strengthen coverage without an invented defect. A-T21 intentionally remains blocking if the release declaration has no approved disposition; a green default suite cannot satisfy it.

### Amendment 13: new proof setup corrections

A-T20 collection at `6a4b6ff` used an incorrect adapter class name; correct to the existing `AnthropicMessagesModel`. A-T21 assumed a tuple where `load_register` returns a mapping; use its actual deviations key. Neither setup failure proves an application defect. Retain every requirement assertion and push these corrections before rerunning.

### Amendment 14: live-parameter derivations — DECISION-NEEDED, not adopted values

All eleven `parameters.*.live` fields remain null. No PnL optimization, measured-provider claim or live value is made. Team + A approve/reject by **Oct 22**, D pins the accepted values before **Oct 26**. Each candidate below is a bounded engineering proposal requiring a final cadence, source/model budget and host drill. Zero skew is permitted by the current nonnegative config schema.

Cadence inputs checked in code/register: SEC polls every **Psec=300,000 ms** by the runner default, longest enabled official feed interval **Pfree=900,000 ms**. These are existing engineering settings, not newly adopted decisions. RuntimeWork schedules **one issuer per global slot**; with N=5 and candidate **C=300,000 ms**, normal per-issuer refresh is **N×C=1,500,000 ms (25 min)**, not five minutes. Filing jobs preempt cadence, so overload can increase that latency. Fourteen days have 4,032 global cadence slots at C; an assessor can make up to seven model steps per six-tool decision, so the cadence-only worst bound is 28,224 calls, before filing/retry jobs. This is an upper bound, not an estimate of paid use; team budget and actual latency measurement must cover it. C is D-owned, currently unset and must be approved with this table. If the measured work cannot meet the accepted freshness bound, keep affected new buys blocked; do not silently extend TTL or source-age limits.

| Live parameter | Candidate / formula for team approval | Requirement-based derivation and failure boundary |
|---|---|---|
| initial_backfill_ms | 2,592,000,000 (30 days), conditional on a cold-start scope check | Cover at least the 14-day run length plus a full adopted five-session review horizon in the frozen session calendar; 30 days is a bounded preactivation sweep, not proof that older permanent non-reliance is harmless. A/D must verify existing unresolved flags before release; backfill never becomes fresh trade authority. |
| max_clock_skew_ms | 0 | The declaration excludes source timestamps after the decision. Storage jitter tolerance is optional, not a requirement; choose zero for ingestion until measured clock/source offset justifies another storage-only allowance. A-FND-009 enforces the strict decision cutoff regardless. D separately owns NTP/backward-clock checks: this field does not measure local drift. |
| max_source_staleness_ms | 1,800,000 (30 min), conditional on cadence/health drill | S>=N×C plus one SEC poll (25+5 min) permits a complete five-issuer rotation. Also S=2×Pfree permits at most one missed longest feed interval. This conservative operational budget is not calibrated safety; for SEC it tolerates six missing polls, which team must explicitly accept or choose tighter source-specific health checks. Require measured priority-job latency and D propagation of current source health. |
| result_ttl_ms | min(S, N×C+Psec)=1,800,000 (30 min) under the proposed cadence | Context must expire by the accepted source-age bound yet cover one issuer rotation plus one retrieval interval. A tighter accepted S requires faster C or a D change to reassess all relevant names; stale results block dependency-invalid entry. B's context max-age must be no looser than this accepted TTL. |
| reassess_delay_ms | 300,000 (one candidate global slot) | A missing comparison/conflict/new statement should receive its first review within one source poll/slot, rather than development's six hours. For statement reviews, three attempts at exponential delays consume B+2B+4B=35 min with B=5 min, before queue delay; D's deadline/priority drill must bound that extra delay below five sessions and run end. |
| retry_delay_ms | 600,000 (2×Psec) | Allow one missed SEC cycle plus the next successful poll before retrying a model/source-dependent assessment; failures remain UNKNOWN. Provider unavailable for a day cannot trigger undeclared substitution or manual recovery; eventual exhaustion must stay visible. |
| job_validity_ms | 86,400,000 (24 h), clipped by terminal/scored-run boundaries in D scheduling | The prompt explicitly includes day-long dependency loss and daily poller restart. One day of durable catch-up budget supports that case without granting stale result authority. An old expired job must not reopen ended trading; deadlines and expiry preserve failure/audit state. |
| job_max_attempts | 3, subject to measured per-job scheduling | Finite retries are needed to protect recovery/upload lanes. Three attempts separated by the proposed retry cadence span at least 20 min plus bounded execution/queue time within a 24 h job. A job's attempt count is distinct from statement review attempts; failing dependencies remain nonactionable after exhaustion. |
| max_review_attempts | 3 | Three complete opportunities within the derived 35 min review schedule bound the lifecycle and cost; attempts must belong to the exact review scope. Exhaustion retains uncertainty, never automatically clears it. D must fix review routing and original pending-support retrieval first. |
| max_review_backoff_ms | 1,800,000 (same accepted freshness budget) | Cap review spacing at the accepted operational freshness bound, rather than a 48 h development cap. The proposed first three delays are below this cap; if attempt count/base changes, recompute total horizon against the frozen five-session/end-of-run deadlines. |
| statement_retention_ms | 2,764,800,000 (32 days), plus longer original-audit retention | Oct 27 earliest final activation to Nov 20 end of winner audit is 24 calendar days; add a full five-session review horizon measured in the frozen calendar. Candidate 32 days is sufficient only if that horizon is <=8 calendar days; otherwise increase by that measured excess. Semantic statement expiry cannot delete original model/source/round records or unresolved adverse proof. D archive retention remains the separately adopted date (at least Dec 31), with host capacity validated for 14-day growth. |

Additional decisions: **A-DEC-005 / #39 SKHYB** — recommended keep new buys blocked until qualified foreign-filer coverage is proven. Alternatives: explicit written acceptance of the 6-K/no-domestic-items protection limit, or qualify rights-cleared separate foreign predicates. No team approval or universe change is inferred from an unanswered question. A-DEC-003 seven-day RF age remains unadopted engineering value; team must decide how original non-reliance remains protected beyond that age, and how amendments are dated. **A-DEC-006 / DEV-20** — implement an adopted announced-event planner or approve a reasoned release deviation. Its explicit proof currently fails OPEN/DRAFT, **A-FND-015 P1**, team/D/B before release. Existing hosted adapter implementations do not satisfy driver integration: `build_driver` deliberately rejects non-rule assessor selection; team/D must choose the deterministic release or integrate and validate the selected provider before Oct 22/26.

### Amendment 15: contact and rights inventory / actual public calls

Command exactly: `env -i PATH=/private/tmp/larp-final-a-test-env/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin LARP_ARTIFACT_ROOT=/private/tmp/larp-final-a-artifacts/terms /private/tmp/larp-final-a-test-env/bin/python -m larp.sources.live terms` at pushed `27c11f0`. Exit 1 because SEC/EDGAR had no configured contact; neither SEC endpoint was fetched. No issuer body or provider call occurred. JSON: `/private/tmp/larp-final-a-artifacts/terms-capture.json`; originals under `terms/artifacts/<sha[:2]>/<sha>`. Successful byte hashes were independently recomputed before checking their text.

| Contact / component | Register / rights basis checked in this review | Original-byte evidence / disposition |
|---|---|---|
| www.justice.gov API and legalpolicies | sources.v1.json doj-press; original DOJ legal policy permits government information copying/distribution; source citation appreciated; other-owner material and seals need permission. Config exclusions retained. | 2026-10-14T17:42:31Z, 68,701 bytes, SHA-256 `dd99df630bfd52d5ba46a8e258198ed20d32518eb042d5163d15c37127982770`. Capture date/hash updated only; no bodies ingested. |
| ec.europa.eu Press Corner + commission.europa.eu terms | ec-press; original EU-owned website content CC BY 4.0 requires credit/indicated changes; third-party works and industrial property excluded. Config attribution/exclusions match this limited scope. | 2026-10-14T17:42:32Z, 154,050 bytes, `aad5e6685135d18198212a23ecb287f4aaf752e761585d453fb2c6f23cad452a`. Metadata updated. Per-item rights checks still required. |
| federalregister.gov BIS API; archives.gov rights page | fr-bis; original NARA page says Federal Register documents may be reproduced without restriction. Does not erase incorporated third-party exclusions. | 2026-10-14T17:42:33Z, 48,393 bytes, `594e3106c86f3dc77b405c52340bd921cd17009ab100eaf5de69ccc5387f4aff`. Metadata updated. |
| federalregister.gov public-inspection API | fr-public-inspection; same captured NARA page describes public inspection, but its unrestricted-reproduction statement explicitly concerns published Federal Register documents. | Same original hash/time. Capture metadata is valid; **rights basis for prepublication content remains PARTIAL** until A/team checks applicable metadata/document rights before Gate A. Do not interpret capture as unrestricted third-party permission. |
| sec.gov press/privacy; data.sec.gov submissions and www.sec.gov Archives | sec-press + separate edgar block; claimed SEC public-dissemination basis is not verified by a current original in this run. | USER_AGENT_NOT_CONFIGURED at 17:42:33Z; no network request; both hashes remain null. A/team provide genuine contact and rights capture outside this review's no-secret constraints, before Gate A. |
| api.anthropic.com/v1/messages; api.openai.com/v1/responses; legacy api.openai.com chat-completions | Providers are allowlisted adapters; config/release/services.v1.json says assessor-model PENDING_DECISION. **No model/API licence register entry proving selected provider retention/audit rights.** | Team/Yao Zhu choose provider/snapshot/budget, review original terms, retention/disclosure/price basis and pin model manifest; no actual calls or spending here. Legacy codec remains not live-provider verified. |
| LocalCheckpointModel / arbitrary allowlisted custom model endpoint | Capability can run a hash-pinned local file; no checkpoint selected and no weight/training-data licence exists in this review. | Keep disabled; A/team must register exact checkpoint/component licence, source rights and endpoint before adoption. Hash alone is not a licence. |
| Web3 Open API, BNB-chain RPC / explorer, ai-seeds receiver | Services draft covers Web3/receiver as participant-kit channels; chain RPC provider and actual endpoint terms need C/D enumeration. | A-REQ-077 kit scope checked, not independent bStock identity. C owns exact contacted-market/chain endpoint rights and response hashes; D owns receiver/service declarations. No keys/log calls/signing here. |
| AWS / CloudWatch / S3 / PostgreSQL hosting | Draft services list, hosting B1–B4; D owns actual account/service terms and infrastructure manifests. | No AWS action; before hosted Gate A. PostgreSQL14.24 disposable test image is test evidence only. |
| Python locked libraries, Docker/PostgreSQL image, vendored ai-seeds SDK | Pinned dependency inventories exist, but dependency/component licences and SDK audit redistribution rights have not all been checked. Participant kit specifies use, not a general third-party licence. | A/D supply SBOM/licence inventory with exact versions/terms and final release scope before Oct 26. Never modify vendor or kit originals. |
| Disabled ftc/fed-bls/eff/gdelt/wikinews/opendart/issuer-newsrooms | Existing source rows enumerate their current basis/NOT_ESTABLISHED state, with allow/enabled refusals. | Not contacted. Enabling one needs its own reviewed rights/capture and approved declaration change, especially OpenDART/newsroom protection for SKHYB. |

Captured originals must be transferred/verified in the final host artifact root before startup; committing their hashes does not transfer bytes. SEC/model/component rights still block overall source-readiness. No all-sources-clear or unrestricted legal conclusion is made.

### Amendment 16: assumptions amended after code inspection

Frozen assumption rows remain historical; current dispositions:
- A-ASM-001 PARTIAL: four actual rights captures checked above; SEC, selected models, component licences and exact prepublication scope remain blocking, A/team/C/D, Gate A/Oct 22–26.
- A-ASM-002 PARTIAL: real-component deterministic timestamp/pagination/error fixtures pass, including strict future source cutoff; live completeness/timezone fidelity requires rights-cleared actual SEC samples and 24 h run, A, Gate A.
- A-ASM-003 UNVALIDATED: actual registry's foreign-form scope tested, no domestic-items authority invented, but SKHYB protection/rights still decision-needed, A+B/team, Oct 22.
- A-ASM-004 UNVALIDATED: seven-day value not adopted; A-DEC-003, team/A, Oct 22, blocks affected live predicates.
- A-ASM-005 UNVALIDATED: synthetic provider summaries/timeouts/audit retrieval pass; real model latency/cost/rights/cutoff/budget not measured, Yao Zhu/team, Oct 19 evidence/Oct 22 choice.
- A-ASM-006 PARTIAL: fourteen writer restarts/read-only accesses prove preserved committed records, **not 14-day worst-case capacity**. D/host owners must measure ingestion/IO volume, disk headroom, bounded registries and archive retention with selected model, before rehearsal.
- A-ASM-007 PARTIAL: local DELETE-mode/writable writer/read-only reader, old WAL refusal/migration/corruption and concurrent access pass. Two-user group mounts, hot-journal recovery and host process restart remain D acceptance, Gate A.
- A-ASM-008 PARTIAL: repeated/syndicated synthetic releases count once and descriptive SEC source agreement stays one; independently labelled actual syndication tests remain A/annotator input before any corroboration-based authority.
- A-ASM-009 PARTIAL: Guide scope is checked and no conversion is synthesized; C/B actual bStock identity/candle coverage remains blocking before affected trading.
- A-ASM-010 UNVALIDATED: all eleven live fields still null. Derivations are proposals above, not adoption; team/A/D Oct 22/26.
- A-ASM-011 PARTIAL: Q16 readable daily summaries answered in practice, not reopened. D/team final-wallet/audit package checks remain; no organiser contact here.
- A-ASM-012 UNVALIDATED: exact selected snapshot/API/licence and cutoff unknown; choose and verify original provider documents, Yao Zhu/team/A Oct 22.

New code assumptions:
| ID | Assumption / code reliance | Review disposition / validation | Risk owner, step, deadline, blocking |
|---|---|---|---|
| A-ASM-013 | Ingestion's 300,000 ms development clock allowance implies availability. | CONTRADICTED before A-FND-009; dependency removed by strict original+retrieval decision cutoff and A-T12 passing. This allowance is no longer early-authority evidence. | Live skew remains A-DEC-002; team/A/D adopt storage-only value and clock guard, Oct 22; yes. |
| A-ASM-014 | Market ticker equals SEC issuer ID; registry-read failure validates equal supplied strings. | CONTRADICTED; A contract dependence removed by canonical registry binding and fail-closed loading, passing A-T01/A-T16. D scheduler still relies on ticker identity, explicit A-T15 remains red. | D fix mapping and original-ref review integration, before final review/activation; yes (#25). |
| A-ASM-015 | Development bounds/limits fit actual fourteen-day data and provider token budget. | UNVALIDATED: max documents6, result chars20,000, claims64, known accessions5,000, known facts200, fetch attempts3, document chars4,000,000, facts400, statements/document200, prior records40, comparisons4,000, model-input chars400,000, statement registry400. Synthetic truncation is visible; no real-load calibration. | A/Yao Zhu + D measure selected-model costs/token limits, maximum ingestion and durable growth, before Gate A/rehearsal; yes. |
| A-ASM-016 | Semantic matching Jaccard 0.8 same / 0.5 uncertain protects real issuer statements. | PARTIAL: thresholds inspected in lifecycle.py, synthetic actor/anchor/paraphrase tests pass. Real independent T01 remains NOT RUN. | A + independent annotator validate false positives/negatives against frozen corpus, Oct 19/22; yes. |
| A-ASM-017 | One cadence slot refreshes all five issuers. | CONTRADICTED; proposals now explicitly use N×C and queue delay. Code still intentionally rotates one issuer; no reliance on all-name refresh is permitted. | D/team adopt C jointly with TTL/source budget and priority overload test, Oct 22; yes. |
| A-ASM-018 | Terms hash presence establishes original capture and all content rights. | CONTRADICTED: integrity dependence removed by A-T11 guard; actual originals now partially captured. Hash cannot replace per-contact/per-item rights checking. | A/team current SEC/provider/component/public-inspection rights steps above, Gate A; yes. |

### Amendment 17: final audit boundary criterion

A-T19/A-T20 pass initially at `621f687`: **7 passed**, including real SQLite source-URI retention and real PostgreSQL provider-failure trail/retry/idempotency. A-T21 reaches the actual validated OPEN/DRAFT DEV-20 and fails its assertion; this confirms A-FND-015's unmet declaration, not an import/setup error. A-REQ-038 is now component COVERED; D still owns hosted incident delivery.

Prospective **A-T22 / A-REQ-060–061 / A-UC-100**: a hosted assessment completes one real allowlisted tool, then the next external model call hangs past the 200 ms test deadline. The result must be UNAVAILABLE while retaining the completed tool call and full original result pointer/hash for audit. No late model reply may revive it. Real store/artifacts are used; only model HTTP is blocked with an event. Suspected abandoned-worker result currently drops all tool calls. Commit and push test before run and before any fix.

### Amendment 18: audit abandonment finding and fix

A-T22 fails at pushed `edcba22`: the result correctly reports UNAVAILABLE with two started model calls, but zero retained tools after one tool completed. **A-FND-016 P1**: hard abandonment drops declared tool call/result audit records. Correction shares the completed-call list with the deadline snapshot and copies those calls into the abandoned result. They are audit-only; evidence/claims remain empty, no late output revives authority. Tool count is the number of completed retained calls; any call still executing is not claimed complete. Normal successful traces are unchanged.

The committed-register refusal test now handles real partial capture metadata: captured hashes with no bytes in its synthetic empty root must return ARTIFACT_UNAVAILABLE; uncaptured SEC hashes return EVIDENCE_MISSING. A second all-null fixture preserves every original missing-capture assertion. No refusal is weakened or source declared cleared.

### Amendment 19: completed audit assertions and stable fixture cleanup

At `bb2834f`, the A-T22 audit retention assertions pass, but its released late worker races TemporaryDirectory cleanup. Join that real worker after releasing the external HTTP block before deleting test artifacts; no application assertion changes. Three A source readiness fixture failures assumed the old all-null committed register or obsolete mixed-refusal ordering. Make the single-missing fixture explicitly null, check unchanged failed-capture source's entire original rights record, and preserve the exact all-null refusal test. Actual hash-bearing metadata still requires bytes in the configured root; no guard is bypassed.

Full/focused results from this round are retained externally; application fixes will be retested after pushing these fixture corrections. Outside-A red-team/strategy fixture permission remains unanswered; no outside path has been edited.


### Amendment 20: final local/CI evidence and artifact index

Tested review head **`10612f08d47e5c1c479de43d79193df351804035`**, original application base **`c1b6dafd62f8df7ea894a5177138da2726452696`**. Final focused intelligence/sources: **385 passed, 1029 subtests passed**, 11.43 s. Final complete local suite: **3 failed, 1251 passed, 7 skipped, 1572 subtests passed**, 192.68 s. Relative to unchanged baseline (1229 passed/7 skipped/1561 subtests), 25 additional tests are collected: 22 more passes and 3 existing consumer fixture failures. No test is weakened/skipped/deleted to achieve a green report.

Three failures: `tests/integration/test_cross_component.py::AssessmentBoundary::test_c2_strategy_fixture_matches_current_evidence_output`, `tests/strategy/test_live_profiles.py::test_c2_fixture_matches_current_golden_trace_without_reconstruction` (both depend on one copied producer fixture), and `tests/redteam/test_integration_redteam.py::SourceProbes::test_d11_control_crash_between_pages_resumes_without_duplicates_and_versions_not_backdated` (obsolete history-only request map). The prepared two-file test-only diff is indexed below; explicit user scope exception or D written OK remains required. Neither outside path changed. Original crash/version/injection/decision assertions are preserved by the proposed diff.

Seven local skips: external recorded-market artifact `tests/marketdata/test_recorded.py:29`; three explicit disposable-systemd opt-in cases (`test_systemd_conditions.py:81,97,107`); three Linux bubblewrap cases (`test_worker_release.py:46,57,62`). The guarded system runner at this head exits **2 before tests**: Linux bubblewrap unavailable, no successful equivalent runtime CI. It was invoked directly on the clean pushed final-A branch with the disposable DSN and `LARP_SYSTEM_TEST_DISPOSABLE=1`; no alias/bypass.

Linux run [38612604846](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38612604846), head `10612f0`: **FAILED runtime**, **3 failed, 1278 passed, 4 skipped, 1 xfailed, 1604 subtests**, 254.16 s. The same three fixture failures occur. Host-bundle and both Terraform jobs PASS. CI pull-request checkout additionally includes D target changes; counts differ from local review tree and are not presented as the same baseline. Its xfail is an explicit D/C signed-bytes-backup blocker, not a passing proof. No deployment/bootstrap/host/workflow/lock edits by A; no local Terraform/host reruns were required by A scope. CI jobs are observed evidence, not AWS deployment.

Integration advanced during this review: final fetch sees **`0820b0dd87219cb6b96f2ede34051129fab9f49c`** (merged D PR #67). Primary checkout is now detached at that exact requested latest origin target, clean; A worktree remains its isolated review branch. D must integrate/requalify A against the final combined tree; original c1b6daf baseline is preserved. No main/reset/rebase/force-push/GitHub merge was performed.

| External artifact under `/private/tmp/larp-final-a-artifacts/` | SHA-256 |
|---|---|
| `baseline.log` | `6673e0b7a03ebb14035b92d460b5e820c17fbd999e2b1d86f9cffc7c8474dfcf` |
| `proofs-red-final.log` | `5512d2170a0c6717f64ab3ff0c213a9bddf6f1ea44ed52f0113c6a5eeea8e577` |
| `additional-red.log` | `43c205683b2108d1fab579ea42ffd3fd677fa9c45e6c289b137bc91318e75753` |
| `additional-green.log` | `44091516c6f7d278c9900d796163d45f95d1ad1819370ffeeaf887bc704f2e38` |
| `http-partial-red.log` | `62a9828274134b0b2c561a7d58aabb8b86ed18ceda45b48e1711934589f3c1b3` |
| `http-partial-green.log` | `bef02fe18c206353337187db84524e59e29564442c4adac0853e97ff7383203b` |
| `durable-proofs.log` | `e74116d41a6385ec4ff8d74607bc5b52f8c0fd51645f80c30b3b354dd068cb81` |
| `deadline-audit-red.log` | `ee5ad7d8557eec287430192206fffe4e5acca4db464f3db7eb8754174e1460e9` |
| `focused-round5.log` | `be21d2e4a22695e6d3bf733c597a7754020cb54acb4d21b309631e4d89dacf01` |
| `full-final.log` | `fe520d4e765ed8b9321ce4dbcaf2cd8670ad8bc734cf968d910e336f577f525b` |
| `system-final.log` | `60f5be8df99107432ceca4be791c1aea4e4337c2c63085fd051417c303308683` |
| `linux-ci-38612604846.log` | `a82f1a7ca8bec49c54042c27faba8ed207c33b957a8595f4d8c909ebb5e578d1` |
| `terms-capture.json` | `88fdbf8ed20aab3cd296f18cc219df3a6427c77ef9e51f9a9dadf4dad8682f02` |
| `requested-test-exception.patch` | `5afc02da7eaffb2590646bd2bb1ab7cdc25773d80ec28e202008af794a1b7f83` |
| `issue25-runtime-proof.log` | `7c2774f9a9b96a3311a96d602b2516368d3b4cc44f47ca34c3cc8abb7fc0e8dc` |
| `calendar-proof.log` | `d522a0d5240e8e0a69c4a7a4065018bd38d7360a1d5635fe628f3d818eede2cb` |

### Amendment 21: current finding disposition / prior-input reconciliation

All retests below mean final focused/full evidence in amendment 20, with three unrelated but blocking fixture failures explicitly retained. They never mean full/system/CI PASS. Fourteen A component defects are corrected; two P1 findings remain owned outside A's implementation authority.

| Finding | Severity | Pre-fix proof commit | Application fix | Current disposition |
|---|---|---|---|---|
| A-FND-001 canonical issuer/ticker rejection | P1 | d48a3cf | 32c79a0 | A component fixed; #25 overall remains open via FND-012. |
| A-FND-002 reversed nonreliance | P1 | d48a3cf | 32c79a0 | Both orders and negative controls pass; #47 subsidiary unspecified phrasings are not certified. |
| A-FND-003 forgotten unverified flag | P1 | d48a3cf | 32c79a0 | Persistent accession-specific uncertainty/correction passes; D must route exact original-support reviews. |
| A-FND-004 permanent policy exclusion | P1 (tracker #58 P2 promoted: readiness cannot autonomously recover) | 7bdecf4 | 32c79a0 | Permitted coverage can complete; restricted bytes not retained, changed item/register reevaluated. |
| A-FND-005 archive hides new head | P1 | 7bdecf4 | 32c79a0; 5047c6e | Fresh head within budget; single-page live pagination refused. External recovery fixture update pending. |
| A-FND-006 request/exception credential leakage | P0 | 7bdecf4/d48a3cf | 32c79a0 | Both modern providers and legacy codec refuse reflected requests before persistence/send; normalized transport errors pass. |
| A-FND-007 full tool results unavailable | P1 | c84ab55 | 32c79a0; 5047c6e | Complete private artifacts plus safe trace pointers; original injection assertion retained. |
| A-FND-008 nonexistent/corrupt terms capture | P1 | 5047c6e | 63109ad | Real byte-integrity refusal passes; source rights remain partially validated. |
| A-FND-009 future accepted timestamp used | P0 | 63109ad | 3557947 | Strict original/retrieval cutoff; after-stamp input usable, before-stamp excluded. |
| A-FND-010 missing assessment dimensions | P1 | 63109ad | 3557947 | All dimensions explicit; uncalibrated/UNKNOWNs honest, no new trade authority. |
| A-FND-011 registry failure accepts equal IDs | P1 | 101e770 | 3557947 | Failed identity authority rejects; synthetic compatibility does not mask load failure. |
| A-FND-012 scheduled review ticker namespace | P1 | 3557947 explicit proof | NONE (D-owned) | OPEN, #25, A-REQ-020/022. Real policy/mapper proof prints NVDA instead of canonical SEC issuer. |
| A-FND-013 EDGAR partial HTTP escapes | P1 | 27c11f0 | 34e5bfe | Real adapter reports sanitized UNAVAILABLE and next successful response recovers. |
| A-FND-014 terms partial HTTP aborts basket | P2 | 27c11f0 | 34e5bfe | Failed capture recorded; partial body omitted; other sources continue. No written P2 acceptance needed because fixed. |
| A-FND-015 unfulfilled calendar declaration | P1 | 621f687 explicit proof | NONE (team/D/B) | OPEN, A-REQ-078. DEV-20 OPEN/DRAFT cannot waive binding declaration. |
| A-FND-016 abandoned completed-tool audit lost | P1 | edcba22 | bb2834f | Deadline snapshot preserves completed call/result, audit-only; stable late-worker cleanup at 10612f0. |

Issue reconciliation: #25→A-REQ-020/022, component fix plus still-red D scheduling proof; #39→A-REQ-043–049/077, no domestic directives for foreign forms, P2 DECISION-NEEDED (A-DEC-005), no team acceptance inferred; #47→A-REQ-028/043–045/048, reversed nonreliance reproduced/fixed and exact current impairment determination passes on original base. Bare future/conditional Item2.06 wording remains nonactionable under the decided “current determination” predicate; unspecified Item1.05 phrasings need concrete independently labelled evidence before claiming general parser coverage. #48→A-REQ-017/028–030/047, persistence/restart/correction proof passes; original support review integration remains D's acceptance. #58→A-REQ-014/016–018, both symptoms reproduced/fixed and promoted P1 because DR-12 could never recover. #57 Class1 planner propagation belongs to B with A verified identity/latched record acceptance. #61 IAM belongs to D: PR67 records D-FND-018 fix; read its final merged record, do not conflate that with this branch's old host configuration. #64 source HTTP retries already caught HTTPException; EDGAR/terms residuals now fixed; shared live sidecars use R15 DELETE mode and local real restart tests pass. C owns chain/Web3 partial HTTP, B owns mandatory-sale ordering, D owns archive retries. #23–24/#26–38/#40 and #43–46/#49–56/#59–60/#62–63 remain assigned to B/C/D under prior-issues.md/current trackers; their current-tree integration evidence is not supplied by A.

Original tracker22 evidence recovery: `/private/tmp/larp-codebase-review-20261014.py` exists, SHA-256 `e8a2ae47c54eb35c92cb51a4d9bb15006275c9b4523c4186565fc48be05468dd`; corresponding results JSON SHA-256 `c13b40b92725c6342a14a9a5b50b93c7e914885905773b5f074061e1ce9c37e6`. This review read them but did not rerun them. RV09 records NVDA/SEC-CIK-0001045810 WRONG_ISSUER and the old driver-not-integrated state. They contain no embedded exact baseline or full-suite counts; tracker22's baseline is a separate published reference, not authenticated execution provenance in these files. **Publication input gap remains:** Keith supplies a complete original record under an unused ledger ID with verified baseline/results/limits; D integrates the new row/backlog/cross-references, before overall IDEA-049 acceptance. Do not overwrite IDEA-046 hosting or claim these old results on today's tree. Exclusive A record scope prevents silently creating unrelated ledger entries in this PR.

### Amendment 22: current deployment blockers / other-section requests

The initial phase-1 risk/status text above is historical. Superseding current blockers:

| Open item | Owner | Exact next verification / decision | Deadline | Blocks deployment |
|---|---|---|---|---|
| Two outside-A fixture updates (three failures) | wtvlol scope exception OR D written OK/application | Apply prepared patch, retain every existing acceptance, push, full suite + Linux CI + guarded system runner; no test-only green substituted for system evidence. | Before A offline exit | yes |
| #25 scheduled canonical issuer | D, C producer acceptance, A consumer acceptance | Run issue25_runtime_review.py red proof; carry canonical token→issuer mapping through ContextBuilder/RuntimePlanner; preserve synthetic compatibility and exact job identity; cross-component real test. | Final integration / before activation | yes, P1 |
| Original pending RF accession review | D + A | RuntimeWork._review must select explicit pending support refs, not unrelated latest filing; prove complete correction/verification after restart with real evidence store and scheduler. No default timer may clear uncertainty. | Final integration / before activation | yes |
| Calendar / DEV-20 and declared source/model deviations | Team + D/B/A | Implement adopted planner or approve reasoned deviation; calendar_declaration.py must reach valid FINAL disposition; approve other draft deviations/agentic sufficiency. | Oct 22 decisions / Oct 26 release | yes, P1 declaration |
| Chosen model, budget and driver integration | Team + Yao Zhu + D | Adopt deterministic release or integrate exact selected hosted adapter, rights/cutoff/latency/cost/budget and pinned fallback; DR-11, A-DEC-001/004. | Oct 19 evidence / Oct 22 choice | yes |
| Eleven live values, runtime C, stale seven-day bound | Team + A + D/B | Decide amendment14 proposals with measured queue/model costs, five-session calendar and fourteen-day capacity; keep live nulls until accepted. | Oct 22 | yes |
| #39 foreign-filer/SKHYB protection | A + B/team | Decide A-DEC-005; recommended block new buys until qualified rights-cleared coverage. Current fixture proves no fake domestic authority, not adequate foreign coverage. | Oct 22 / before affected live use | yes until decision; P2 requires written acceptance or fix |
| Remaining source/model/component rights, originals transfer | A/team + C/D | Amendment15 inventory: genuine SEC contact/capture, prepublication scope, selected model/API/component licences, exact RPC/market endpoints; originals in final external artifact store, all hashes reverified. | Before Gate A / Oct 22–26 | yes |
| Real T01/post-cutoff/anonymization/bake-off | Yao Zhu + independent annotators + team | Rights-cleared external frozen independent labels, exact model cutoff, distinct pre/post cohorts and anonymized historical prompts, actual source/syndication samples; report pass/fail/inconclusive. NOT RUN here. | Oct 19 evidence / Oct 22 disposition | yes; no synthetic accuracy/profitability claim |
| 24 h live coverage and hosted shared-store capacity/recovery | A + D/host owners | Exact rights-cleared cadence/gap report; two-user DELETE mode/read-only mount/hot-journal restart, group artefact retrieval and actual fourteen-day capacity/archive retention. | Gate A / before rehearsal | yes |
| Original tracker22 publication + final combined review | Keith + D, B/C boundary owners | Complete original unused-ID record, current issue reconciliation, final integrate/retest against target 0820b0d and later sections; complete final adversarial source pass after blockers resolved. | Before overall IDEA-049 acceptance | yes |

A's latest source reread: official source_page top-to-bottom; declared proposal top-to-bottom; Guide pp.2–3/13–18 directly, relevant F/K/Q and decided-class/read-only-store supersessions checked. It added A-UC-100 and the deadline audit proof/fix, no new authoritative requirement ID. **Phase4 is not complete:** final full adversarial closure must be repeated on the final merged tree after these blockers, and currently full/system/runtime CI are not green. No generic organiser question replaces already-settled Q16/class/host rules. No SKILL summary correction established.

### Amendment 23: exact superseding shared edits (D applies)

These replace the earlier phase-1 requested text. D alone applies the shared files; no whole backlog item is completed by A's component tests.

**docs/LEDGER.md — append this exact index row:**

`| IDEA-049-A | Final review A: inputs, evidence, sources and model | partial review; deployment blocked; PR #68 | 78 independently frozen requirements, 100 use cases; baseline 1229/7/1561; final A 385 tests/1029 subtests PASS; full 1251 passed/3 failed/7 skipped/1572 subtests, Linux runtime FAIL; 14 component fixes, cross-owner/decision/rights/host gates remain | 2026-10-15 | [ledger/IDEA-049-A.md](ledger/IDEA-049-A.md) |`

**docs/INCOMPLETE_WORK.md — replace the stale section-A status within the IDEA-049 final-review item, retaining unresolved whole GAPs, with:**

`Section A (Keith for wtvlol, PR #68, IDEA-049-A): independent catalogue frozen/pushed at 990408d before code review; 78 requirements and 100 use cases. Tested head10612f0/basec1b6daf: A 385 tests/1029 subtests pass; full1251 passed,3 failed,7 skipped,1572 subtests; Linux38612604846 runtime FAIL (same three outside-A fixture dependencies), system runner refused unavailable equivalent green Linux tree. wtvlol/D must authorize/apply the two prepared test-only fixture updates, then rerun full/CI/system before A offline exit. D owns #25 canonical scheduled review mapping and original pending-RF support review, final combined-tree requalification (target advanced0820b0d), and shared integration. Team/D/B resolve declared calendar DEV-20 and final draft deviations; team/A decide all eleven intelligence live values plus cadence, seven-day age bound and #39 SKHYB scope by Oct22. Yao Zhu/team/independent annotator own model choice/budget/rights and real T01/post-cutoff/anonymized bake-off evidence (NOT RUN); A/team complete SEC/model/component/prepublication rights/originals transfer and 24h live coverage, D/host owners two-user restart/capacity/recovery before GateA/rehearsal. Keith publishes tracker22 original under unused ID with exact provenance; D reconciles it without overwriting hostingIDEA046. Fourteen A component defects fixed; P1/shared/input gates remain. No whole GAP-23/24/25/26/27/28/56/57/67 is closed.`

**docs/skill/SKILL.md:** no summary correction requested. If adding the review status index, exact text: `IDEA-049 A: partial offline component review (PR #68; docs/ledger/IDEA-049-A.md). Synthetic/component passes do not establish real source rights, source/model accuracy, hosted integration, deployment or activation readiness. Team decisions and D combined-tree verification remain blocked as recorded there.`

**README.md — replace stale A-not-run status with:**

`Final review A is partial (PR #68, IDEA-049-A): independent catalogue and 14 component fixes are pushed; A-focused tests pass, but three outside-A fixture failures keep the full suite and Linux runtime CI red. System-test equivalent-green-tree guard is unsatisfied. Model/live-value/rights/calendar/SKHYB and hosted/real-evaluation gates remain open. Deployment is blocked.`

**docs/build/AWS_RUNBOOK.md and runbook.md — add this exact A gate block to the existing GateA/B/C checklist, without changing their restrictions:**

`A gates (IDEA-049-A, PR#68): (1) resolve/approve two fixture scope updates, canonical #25 review routing and original pending-support review; final combined full/CI/system pass with recorded counts. (2) adopt every intelligence live parameter jointly with per-issuer N×cadence, source freshness, model budget/queue delay, five-session horizon and fourteen-day capacity; no default or null is a team decision. (3) select/pin assessor and approved fallback; verify actual provider/cutoff/rights/budget or explicitly declare deterministic release; resolve calendar and draft declaration deviations. (4) genuine SEC contact, dated rights captures for every adopted source/model/API/component, prepublication/third-party exclusions and exact endpoint declarations; transfer original capture bytes to final external artifact root and reverify hashes. (5) A rights-cleared 24-hour live source gap report and independently labelled T01/post-cutoff/anonymized provider evidence, with explicit inconclusive/fallback disposition. (6) D/host owners two-user evidence writer restart while read-only reader stays open, DELETE/no-WAL-sidecar permission/recovery drill, group-readable original audit artifacts and measured fourteen-day capacity with post-run archive retention. Team/A/Yao Zhu decisions dueOct22; D final releaseOct26; host/source/rehearsal checks before their gates. Synthetic runs, raw hash metadata or a copied source terms page alone cannot satisfy these acceptances. No registered-key/ai-seeds/AWS/signing action is authorized by the review itself.`

### Amendment 24: session status / strict handoff

**Partial review; deployment blocked.** All A-authorized code/tests/catalogue/record changes are committed and pushed to the isolated review branch; no unpushed application commit remains. User explicitly authorized protocol-required branch pushes. No outside-A application edit, main history rewrite, registered wallet key, AI_SEEDS_SECRET, ai-seeds log call, AWS action, organiser contact or live signing/broadcast occurred. Public rights reads used only the pushed repo command and original bytes stayed outside Git. Main primary checkout is clean at latest fetched target0820b0d; A worktree is separate. PR #68 remains draft; no merge/approval claim.

This is **not a strict ready-to-handoff declaration**: D shared edits and original-review publication are still requests, target integration/main equality is not asserted, and open inputs/decisions/P1 and suite/system/runtime CI block completion. Owners, exact next steps and deadlines are in amendment22. The two scope exceptions require user approval or D written OK before dependent fixture changes; the reviewed diff is concrete and outside Git. After those and other owner resolutions, repeat the guarded verification and final complete source pass; do not mark IDEA-049 or any whole GAP complete merely because A component tests pass.

### Amendment 25: started-but-incomplete tool criterion

The nominal final evidence in amendment20 is retained as round5 evidence, not an exit claim. A second boundary under the same frozen requirement remains suspect: `_call_tool` appends its record only after return. Pre-register **A-T23 / A-REQ-060 / A-UC-101**: pause only the external filesystem open for a prior document, then delegate to the real original read. Real tool, SQLite evidence and FileArtifacts remain unchanged; only an OS-read fault and synthetic model HTTP are injected. At the hard deadline, retain the started prior_context call/args as IN_FLIGHT_AT_DEADLINE, with no completed result hash/pointer and no claims/authority. Joining the released worker must not mutate the already returned result. Commit/push test before run/fix. If reproduced, record another P1 audit finding and repeat focused/full/CI/system checks; do not accept the earlier nominal final counts as completed review.
