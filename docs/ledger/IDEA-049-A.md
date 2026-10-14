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
