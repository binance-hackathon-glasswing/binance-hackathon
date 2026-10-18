# IDEA-057 — AIand implementation of external-first evidence routing

- Date / author: 2026-10-15 SGT / Keith, implemented with Codex at the user's request to do both the AIand-specific design and implementation.
- Status: open for review (shadow implementation; AR1–AR8 synthetic/local acceptance passed 2026-10-16; no real-provider inference or live adoption).
- From: [IDEA-056](IDEA-056.md), PR #85 into `main`. Implementation PR #86 was merged into its proposal branch; PR85-M1 below records final promotion review including PR #111.
- Review: [implementation PR #86](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/86) and [budget cleanups PR #111](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/111), incorporated in PR #85. Local acceptance only; repository promotion and live adoption are separate decisions.
- Scope: AIand adapter; opt-in external-first shadow assessor; durable $40 OpenAI admission plus $10 full-run reserve; complete external review after credit refusal; provenance and runtime secret loading. External funding is supplied by the user; K3/GLM prices are outside this comparison.
- Out of scope: real-provider inference, private labels, independent real-document evaluation, source/model rights approval, scored/live activation, trading-policy adoption and AWS changes. These retain IDEA-056 MR-01–06 and GAP-23/24/57/62/67 owners.

## AIand-specific evidence, checked before implementation

**[PRIMARY]** Read the documentation at [docs.aiand.com](https://docs.aiand.com/), including [chat](https://docs.aiand.com/api/chat-completions/), [catalog](https://docs.aiand.com/models/catalog/), [reasoning](https://docs.aiand.com/capabilities/reasoning/), [headers](https://docs.aiand.com/reference/response-headers/) and [errors](https://docs.aiand.com/errors/). Also fetched the public, unauthenticated `GET https://api.aiand.com/v1/models` on 2026-10-15 with TLS verification using the system CA store. No credentials or inference request were used.

The public catalog returned `moonshotai/kimi-k3` and `zai-org/glm-5.3`, each with `low`, `high`, `max`, a 1,048,576-token context and a 131,072-token output bound. Both are served by AIand, not a direct call to the original lab. Org-scoped account access, deployment revision, paid-request behavior and accuracy are unverified. The example pins the observed capability fields; it does not use AIand's dynamic `auto` selector.

The adapter uses fixed `https://api.aiand.com/v1/chat/completions`, bearer auth, JSON mode, explicit `reasoning_effort` and `max_completion_tokens`. It requires the body model plus `X-Model` to match case-insensitively and `X-Reasoning-Effort` to match exactly. The two reasoning text fields are duplicates; retain one in the trace and the complete original reply artifact. Unknown usage is never treated as a zero OpenAI charge. AIand credit errors are not OpenAI-credit errors.

Also checked current [OpenAI error codes](https://developers.openai.com/api/docs/guides/error-codes): `credit_balance_exhausted` and named organization/project spend/usage limits are distinct from transient rate limiting. The implementation recognizes those codes and legacy insufficient-quota errors without latching on every 429.

## Prospective component pass criteria (before any changed code runs)

| ID | Required evidence |
|---|---|
| AR1 | Synthetic AIand transport confirms exact endpoint/auth/model/effort/token cap/JSON body; original nonsecret bytes and response metadata retained; no key in repr, result or artifacts. |
| AR2 | Wrong/substituted model, missing/rounded effort, refusal, truncation, invalid JSON/usage and conflicting reasoning aliases fail closed. Arbitrary endpoint, `auto`, unsupported effort and malformed capability snapshot refuse construction. |
| AR3 | Explicit private budget initialization with prior usage; runtime cannot recreate a missing file. Cross-worker reservations are atomic; unknown/crashed usage stays charged; account mismatch refuses; operating-limit/exhaustion state persists across restart and wallet/run changes. |
| AR4 | Routine GLM-low precedes stronger review. $40 admission or explicit OpenAI insufficient quota dispatches difficult work to external high; a generic 429 does not latch credit exhaustion. Missing OpenAI key supports external-only operation with stable declared identity. |
| AR5 | All stages share the original deadline and at most six tools / ten model steps (six tools plus at most four stage finishes). Required review failure/disagreement cannot produce an accepted clean thesis; no unbounded retries or new minute for fallback. |
| AR6 | The real assessor/verifier, runtime result validator, evidence reducer and round trace accept identity-bound composite results. All actual stage models, raw artifacts and rejected/abandoned stages remain traceable; scheduler review-job identity is preserved. |
| AR7 | Runtime construction is opt-in via a pinned routing file, fixed shared budget directory and optional model secrets from Secrets Manager. Defaults remain deterministic. Experimental routing refuses service execution/scored live mode; it has shadow authority only. |
| AR8 | Relevant intelligence/runtime regressions pass; run the broader local suite and report platform/environment skips accurately. Static AST/JSON/links/diff checks pass. No inference, wallet signing or AWS calls in validation. |

These are engineering criteria, not IDEA-056's independent-label non-inferiority experiment. T01/real accuracy, omission rates, hosted network/permissions and provider access remain NOT RUN. No component pass can authorize live deployment.

## Design choices

- External routine: GLM-5.3 low; difficult external primary: Kimi K3 high; secondary: GLM-5.3 high. These are explicit **example experiment settings**, not selected production models. Sol medium is optional and receives the same original filing/context through its own verifier.
- The routine stage receives at most half the time and three tool calls, reserving time/retrieval for review. Later stages receive only remaining time/tools. A seeded clean-case audit supplements independent item/event/coverage/conflict triggers; model confidence alone is not a router.
- Composite identity binds the routing spec, component identities, account and reserve policy. Job IDs stay unchanged; per-stage model-request namespaces distinguish paid calls. Full intermediate result artifacts preserve verifier outcomes without duplicating their entire text into each final trace.
- OpenAI reservations happen before POST, using a conservative UTF-8 input bound and configured output cap at standard short-context prices. Inputs beyond the short-context bound go external. Failed/unknown calls retain their maximum reservation. A provider credit refusal latches external-only; rate limits merely try the declared external review path for that assessment.
- The SQLite budget is explicitly initialized, not auto-created by the runtime, in one shared primary-host directory independent of wallet/run. Do not run duplicate model workers on other hosts with copied ledgers. Unrelated account/console usage is outside this allocated budget and must be deducted at initialization. Backups/host migration must carry and reconcile this ledger; no automatic multi-host budget failover is claimed.
- Because independent evaluation and declaration are not complete, `aiand_routed` is implemented only for shadow execution and refuses scored `live` mode. Real activation requires a later reviewed change, not a configuration bypass.

## Files and usage

Implementation: `larp/intelligence/aiand.py`, `model_budget.py`, `routing.py`, shared provider metadata/error capture, per-stage trace identity and runtime construction/optional credentials. Example: `config/intelligence/aiand-routing.example.json`. Runbook: [AIAND_MODEL_ROUTING.md](../build/AIAND_MODEL_ROUTING.md).

## Validation record

- Before execution: static AST parsing of changed Python and JSON parsing of the example passed; no project module was imported. Synthetic regression cases prepared in `tests/intelligence/test_aiand_routing.py` plus runtime composition/secret tests. Execution results are recorded below: AR1–AR8 local acceptance (2026-10-16), the PR #86 review fix, PR85-R1/R2 and the #93 cleanups.

## Remaining work and owners

Yao Zhu + independent annotator/Keith: real evidence labels, omission-aware mixed/external-only quality and deadline/cost measurement. Keegan + Yao Zhu: hosted Secrets Manager, private ledger/artifact permissions, single-primary backup/recovery and service/deviation declaration. Team: endpoint rights, org access, exact production revisions, model adoption and freeze. None is established by documentation or synthetic tests.

### AR1–AR8 local acceptance — 2026-10-16 SGT

Tested pushed code: `36a3166dedf8ba693827c316f90e69e3b0e91dba`. Local Docker Desktop runner: native ARM64 Ubuntu 22.04.5, Python 3.12.15, PostgreSQL 14.24, systemd 249 and bubblewrap 0.6.1. The suite ran as the unprivileged `ci` user in a disposable systemd container with a disposable PostgreSQL database. The final documentation-only commit does not change tested code.

- Full suite: **1551 passed, 1 skipped, 2208 subtests passed** in 187.08 seconds, with `LARP_TEST_SYSTEMD=1`, disposable `LARP_TEST_DATABASE_URL`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and `python -m pytest -q -p no:cacheprovider`. The single skip requires the optional external recorded-market dataset; no test failed or xfailed.
- AR1–AR7 synthetic engineering checks pass: exact wire/metadata and credential exclusion, strict model/effort refusal, private durable/concurrent admission, credit versus transient-rate errors, external difficult-case primary/secondary, missing-key operation, deadline abandonment, bounded fallback configuration, consequence/event/falsifier disagreement, real consumer/gate/trace and pinned shadow-only runtime construction.
- `pip check` passes. The real offline runtime demo passes with synthetic ports: audit pending 0, jobs pending 0, open rounds 0 and not quarantined. No live sender, signer or provider is constructed.
- `deploy/Dockerfile` builds for `linux/amd64`; its default inspection command passes under `--network none --read-only --cap-drop ALL`. This is an image/packaging smoke, not hosted inference.
- Changed Python AST, JSON, local Markdown links and `git diff --check` pass. The full suite includes tracked-credential scanning. Terraform and host-bundle infrastructure checks were not repeated because those inputs are unchanged.
- Initial focused failures were code-identity-derived golden hashes. Both golden traces and the dependent strategy producer fixture were re-captured; verified assessment outcomes remained unchanged. Review also fixed missing failed/in-flight model provenance, limited fallback stages to the documented bound, compared full verified consequences and reported unknown hosted failure cost honestly.
- Initial full-run harness failures used the wrong disposable database name and omitted git metadata. A real disposable checkout and the correct database resolved those setup failures. Initial network-disabled image builds lacked the dependency install cache; the successful build downloaded only pinned public packages. A demo invocation missing its required disposable DSN was corrected. These failed attempts are retained separately from the final passing results.
- Hosted Actions are deliberately skipped (`[skip ci]`) at the user's request because the quota is exhausted. No workflow is changed. Native ARM64 local evidence is not a hosted x86_64 CI result.

Artifacts are outside the repo at `/private/tmp/larp-aiand-validation/results/`: `summary.json`, `full.log`, `full.xml`, `environment.json`, `docker-build-final.log`, `docker-smoke.log`, `offline-demo.json` and `pip-check.log`. Final report hashes:

- `full.log`: `15140ded5f63d53abd8c099ab6aa6e7ca08a11dbcb50bed7890403834e20715c`
- `full.xml`: `2cf92e8de428fbf4bcb2b5fea90db8cbf2382f8c4cb8a584dc49801bed261f04`
- `docker-smoke.log`: `51ca497439d15fde454e755a69b96ee3f4d565da83cdf6d764e4e94b7b7f4365`
- `offline-demo.json`: `a9fee7ddbb681c0fbb649a6de628ce6d35b955508db8f77f9f45b89925909510`

AR1–AR8 pass only for the stated synthetic/local scope. Real AIand/OpenAI inference, account entitlements, independent labels/omission rates, actual latency/usage, model/source rights, hosted secret/ledger recovery and live/scored adoption remain NOT RUN and retain the owners above. No whole GAP closes.

### PR #86 review fix — 2026-10-15

Review found that a missing, locked or corrupt budget ledger raised out of the routed assessment after the routine AIand stage had run, because the `external_only` check and the trace snapshot read the ledger without a guard. The coordinator then recorded `ASSESSMENT_UNAVAILABLE` and no external review ran. This contradicted the runbook, which says storage failure blocks only OpenAI dispatch. `RoutedAssessor` now treats an unreadable ledger as external-only (`MODEL_BUDGET_UNAVAILABLE`) for that assessment, and still never recreates the file. New AR4 regression: `test_ar4_unavailable_budget_storage_blocks_openai_but_not_external_review`. The local re-validation is recorded in the PR #86 review.

### PR85-R1/R2 — admission deadlines and paid-response retention (2026-10-16 SGT)

Keegan's PR #85 review at `232447c` reproduced two P2 defects: budget admission
could outlast the original assessment deadline and still dispatch OpenAI; a
post-response settlement failure discarded paid-response provenance from the trace.

Prospective pass criteria, recorded before running changed code:

- **PR85-R1:** advance wall or monotonic time during admission. Dispatch receives
  only the remaining allowance; admission at or beyond expiry dispatches no POST.
  Unused reservations remain conservatively charged. Existing shared-deadline and
  external-fallback tests continue to pass.
- **PR85-R2:** inject settlement and credit-switch storage failures after a provider
  reply. Keep exact request/reply artifact references, usage, cost, reasoning and
  provider outcome in the composite trace; report accounting unavailable, use the
  external review route, and block later OpenAI dispatch in the same process even
  if the ledger is readable again. Failed settlement keeps its full reservation.
- Run the focused routing/provider/runtime regressions with synthetic transports
  only after committing and pushing the code. Report runtime/platform limitations
  and any broader checks separately; no paid model calls or deployment.

Implementation: count serialization/admission time using both the model clock and
monotonic time before dispatch. Catch post-response accounting errors, preserve
the provider outcome and artifacts, and latch local budget unavailability until
process restart/reconciliation. Existing durable reservations protect restart
accounting. Results pending execution of the pushed change. No adoption or whole
backlog item is completed by these fixes.

#### PR85-R1/R2 verification — 2026-10-16 SGT

Tested committed/pushed code: `8d12ae0b7f77f169b0de2aaee5e4a9564fdb1af2`.
Local Ubuntu 22.04 WSL, x86_64, Python 3.12.15. Synthetic transports only;
no model inference, wallet, AWS service calls or deployment.

- Intelligence discovery: `python3.12 -m unittest discover -s tests/intelligence -t . -q`:
  **330 passed, 1 skipped** (331 cases, 43.556 seconds), including all 28 routing
  tests and the six wall/monotonic admission-delay subcases in the new deadline test.
- Runtime credentials/driver: `python3.12 -m unittest tests.runtime.test_credentials tests.runtime.test_driver -q`:
  **16 passed, 6 skipped** (22 cases, 2.336 seconds); PostgreSQL-dependent driver
  cases remain unrun without a disposable database.
- PR85-R1/R2 pass for the stated synthetic scope: expired admissions make no POST,
  live admissions receive the reduced allowance, settlement failure retains paid
  artifacts/usage/cost/reasoning, failed credit-switch writes preserve the provider
  refusal, external reviews run, and later OpenAI calls stay blocked locally.
- Changed Python AST and `git diff --check` pass. No data-source/config/authority,
  production profile, dependency lock or workflow change is required.

Initial environment attempts are separate: WSL's system Python 3.10 passed the
focused 65 tests with 6 skips after adding pinned `botocore==1.43.111` to a
temporary dependency directory. Broader discovery on 3.10 had three failures and
two errors caused by unsupported trailing-Z ISO-date parsing and missing dotenv.
The final passing runs used temporary Python 3.12.15 plus pinned
`python-dotenv==1.2.4`. Windows Python 3.14 also passed the standalone deadline test.
Hosted CI remains quota-blocked/skipped; no full repository or hosted/live
acceptance is claimed. MR-01–06 and the existing adoption backlog retain their
owners and remain open. The documentation update after this test changes no code.

### PR85-M1 — final main-promotion review (2026-10-16 SGT)

User authorized pushing and merging PR #85 if complete and sound. Reviewed current
PR #85 `3b4d1e6`, its discussion/review, and the already-pushed PR #111
`71c4994e7b5d56ffcab49ab4616dbdc76f7b308b`; fast-forwarded the isolated review
branch to include all three PR #111 commits without rewriting history. No new
blocking routing defect found. I93-1..4 fixes close initialization connections,
record one durable switch, enforce the private parent directory and correct the
stale validation line. AR1–AR8 and PR85-R1/R2 remain the acceptance criteria.

- **PASS:** full suite at `71c4994`, native ARM64 Ubuntu 22.04 / Python 3.12.15 /
  disposable PostgreSQL 14.24, as unprivileged `ci`, real systemd 249 and bubblewrap
  0.6.1: **1558 passed, 1 skipped, 2215 subtests passed** in 164.80 seconds.
  Command: `python -m pytest -q -ra -p no:cacheprovider`, with
  `LARP_TEST_SYSTEMD=1`, a disposable `LARP_TEST_DATABASE_URL` and plugin autoload
  disabled. Only the opt-in external recorded-market dataset was skipped.
- `pip check` and `git diff --check` pass. No source, dependency, authority or
  trading-policy change beyond the already-pushed PR #111 fixes was needed.
- Initial full run: 1556 passed / 1 skipped / 2 failures, caused by the runner's
  read-only source mount blocking a synthetic activation directory and its
  `noexec` `/tmp` blocking a synthetic AWS stub. Corrected only the disposable
  mounts; all eight affected tests then passed, followed by the full passing run
  above. No real AWS call or credential was involved.
- Final log: `/private/tmp/pr85-acceptance/final.log`, SHA-256
  `f4b2cae7a54bcbc6f1cbe452cd9346c6ea086a16f3a597581f471157091bb85c`.
  The source mount was read-only except an ephemeral ignored activation directory;
  containers had no external network or production credentials.
- Hosted Actions are **not green**: GitHub's annotation on PR #111 confirms jobs
  never started because recent account payments failed or spending limits must
  increase. The account owner retains that blocker; local checks do not claim
  hosted CI, inference or deployment acceptance.

Integration disposition: PR #85's updated description explicitly keeps `main`
as its target and separates deploy integration into PR #114. PR #114 records
that AIand retains IDEA-057; Keegan owns renumbering #88's QuoteCostSummary record
before combining it with the deployment branch. No #88 or #114 merge is authorized
or performed by this review. PR #114 also carries the hosted writable-model-artifact
and network wiring fixes; those remain separate from this main promotion.
2026-10-17 note (this section reached `codex/system-testing-20261012` with PR #123's
merge): both have since happened there. See "Deploy-branch integration" and
"RR2 index reconciliation" below (#88's record is IDEA-063).

Remaining owners: Keegan + Yao Zhu for hosted artifacts, secrets, ledger recovery
and release declarations; Yao Zhu + independent annotator/Keith for real-provider
and omission/quality evaluation; team for trial thresholds and adoption. Existing
IDEA-056 MR-01..06 and GAP items remain open. `aiand_routed` continues to refuse
service execution and scored live mode. This review grants no live authority.

### Issue #93 cleanups — prospective criteria (2026-10-16 SGT)

Non-blocking findings from the PR #86 review ([#93](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/93)). Written and pushed before the changed code runs. Tests in `tests/intelligence/test_aiand_routing.py` (`BudgetAdmission`); each new test must fail on the unfixed code and pass after the fix.

| ID | Required evidence |
|---|---|
| I93-1 | `ModelBudget.initialize` closes its SQLite connection: a test that wraps `sqlite3.connect` sees `close()` called on every connection `initialize` opens, and the file can be renamed/removed and re-initialized afterwards. |
| I93-2 | One `switches` row per real switch. After an over-bound settle through `BudgetedOpenAI.step` (usage above the reservation), the ledger holds exactly one row, `OPENAI_USAGE_EXCEEDED_BOUND`. Calling `external_only` again, or an `admit` refused at the limit while already external-only, adds no row. A first switch still records its reason. |
| I93-3 | Directory privacy matches the runbook. `ModelBudget(...)` (and therefore `initialize`, which reopens the file) refuses a ledger whose parent directory has any `0o077` mode bit (group-readable `0o750` is refused) or is not owned by the current user. A `0o700` parent owned by the current user still opens. Ownership is tested by substituting the expected owner id, since tests cannot chown. |
| I93-4 | The stale "Execution results are pending…" line in the Validation record above is updated to point at the recorded results. |

No AR1–AR8 or PR85-R1/R2 test may regress; the full local suite (Python 3.12, PostgreSQL 14) is run after the fix and reported with exact counts.

#### Issue #93 results — 2026-10-16 SGT

Order: criteria `657fd03` → fix and tests `c075849`. The three new tests were run against the unfixed code first and failed for the expected reasons (I93-1: one of two connections left open; I93-2: two `OPENAI_USAGE_EXCEEDED_BOUND` rows; I93-3: a `0o750` parent was accepted).

| ID | Result | Evidence (`tests/intelligence/test_aiand_routing.py`, `BudgetAdmission`) |
|---|---|---|
| I93-1 | PASS | `test_i93_1_initialize_closes_every_connection_it_opens` |
| I93-2 | PASS | `test_i93_2_one_switch_row_per_real_switch` |
| I93-3 | PASS | `test_i93_3_parent_directory_must_be_private_and_owned` (also: `initialize` refuses before creating the file) |
| I93-4 | PASS | Validation record line updated |

Full local suite at `c075849` (Linux x86_64 container, Python 3.12.3 venv from `deploy/requirements-test.lock`, disposable PostgreSQL 14.24 in Docker, `python -m pytest -q -p no:cacheprovider`): **1551 passed, 8 skipped, 2210 subtests passed**. Base `3b4d1e6` in the same environment: 1548 passed, 8 skipped (+3 tests, no new failure). Skips are environmental: 1 opt-in external market artifacts, 1 "root ignores the directory mode" (the container runs as root), 3 disposable-systemd runner not enabled, 3 bubblewrap not installed. Hosted CI not used (org Actions minutes exhausted). The runbook now says to run `init` as the runtime user, since the ledger refuses a parent directory it does not own.

## Deploy-branch integration for the Gate A shadow trial — prospective criteria (2026-10-16 SGT)

Branch `claude/aiand-shadow-gate-a` from `codex/system-testing-20261012`, with the routing branch (plus the #93 fixes) merged in. Written and pushed before the changed code runs. Each new test must fail before its change and pass after it.

| ID | Required evidence |
|---|---|
| SG-1 | **Writable model artifacts on a read-only evidence store.** On the host the runtime opens the evidence root read-only (`ProtectSystem=strict`, no writable evidence mount, IDEA-047 R15). Measured 2026-10-16 on a real read-only bind mount at the merge head: the routed assessor raised `OSError: [Errno 30] Read-only file system`, so every round would be `ASSESSMENT_UNAVAILABLE`. Required: for `aiand_routed`, `build_driver` gives the router, its model adapters and the tool-result writes a private store at `<market_artifact_root>/model` (inside the unit's `StateDirectory`), while evidence bytes are still read from the shared evidence store. Test: with the evidence store refusing every write, a routed assessment completes, records no `ARTIFACT_WRITE_ERROR`, and every artifact it names (request/reply, stage result, tool result) is readable from the model store and not written to the evidence store. The deterministic path's wiring is unchanged (its own tool-result writes have the same read-only problem; reported separately, not changed here). |
| SG-2 | **Route checker.** `routes.plan('primary', …)` with a runtime config whose `driver.assessor` is `aiand_routed` adds `api.aiand.com:443` and `api.openai.com:443` for `larp-runtime`, equal to the hosts of `larp.intelligence.aiand.ENDPOINT` and `larp.intelligence.providers.OPENAI_ENDPOINT`. A `deterministic` runtime adds neither; `api.anthropic.com` never appears; the signer plan is unchanged. R8 covers both hosts in the approved table. |
| SG-3 | **Example config.** `config/runtime/runtime.aiand-shadow.example.json` differs from `runtime.example.json` only in `driver.execution: shadow`, `driver.assessor: aiand_routed`, `model_routing_file`, `model_routing_sha256`, `model_budget_root` (and drops `expiry_grace_ms`, which only service execution reads). Filled with synthetic values, `build_driver` accepts it in `mode: dev` with shadow execution and builds the routed assessor; it refuses it with `execution: service` and with `mode: live`. `model_budget_root` and `market_artifact_root` lie inside `/var/lib/larp-runtime/`. |
| SG-4 | **Secrets tooling.** `tools/deploy/put_service_secrets.sh` prompts `LARP_AIAND_API_KEY` and `LARP_MODEL_API_KEY` hidden, after the Binance keys; an empty answer omits that key. Values reach `aws` on stdin only, never in argv or output. The runtime loader accepts both (existing `test_credentials`). |
| SG-5 | **Documentation.** The approved-destination table lists both hosts as shadow-only approved (with the MR-06 decision); `api.anthropic.com` stays unapproved. `docs/build/AIAND_MODEL_ROUTING.md` gives tonight's host steps in order, with the prior OpenAI spend as a flagged placeholder. |
| SG-6 | **No regression.** Full local suite (Python 3.12, PostgreSQL 14) on this branch against the deploy-branch base: no new failure; counts and skips reported. Golden fixtures are regenerated only if the merge breaks them. |

### Deploy-branch integration results — 2026-10-16 SGT

Order: merge `bc14e23` → criteria `3539161` → red tests `5b54182` (all 8 new/changed tests failed: missing `OverlayArtifacts`, missing example, route hosts, secrets prompts) → build `548a2c3` → docs `e57fdf5`, merge of the #93 results `07f2917`.

- **Merge.** `larp/runtime/service.py` merged without conflict: `build_driver` keeps the IDEA-055 balance check (`RuntimeHealth`, `balance_settings`, `DecimalsCache`) and adds the shadow-only `aiand_routed` branch. Only `docs/LEDGER.md` conflicted (rows ordered IDEA-055, 056, 057, 061, 062). The merge also brought main's three docs-only commits (`305f3de`, `0a7d87a`, `e410e49`). **No golden fixture was regenerated**: the goldens, strategy fixtures and route tests passed unchanged after the merge.

| ID | Result | Evidence |
|---|---|---|
| SG-1 | PASS | `test_aiand_routing.py::Routing::test_sg1_read_only_evidence_store_keeps_model_artifacts_private`, `test_driver.py::Composition::test_sg1_routed_model_artifacts_go_to_a_private_runtime_store`. Also measured on a real read-only bind mount: before, `OSError: [Errno 30]`; after, `ASSESSED`, stages routine + openai-review, no tool errors, 21 private artifacts, evidence store unchanged. |
| SG-2 | PASS | `test_routes.py::Plans::test_sg2_aiand_shadow_runtime_adds_the_model_hosts`, extended `test_r8_…` |
| SG-3 | PASS | `test_driver.py::Composition::test_sg3_shadow_example_builds_in_dev_shadow_and_refuses_service_or_live` (placeholders filled: `intelligence_mode` with `development`, since `live` values are still unset and Gate A's mode comes from PR #87) |
| SG-4 | PASS | `test_deploy_presetup.py::PutServiceSecrets::test_sg4_…` (two tests); the existing secrets tests pass with the two new prompts left empty |
| SG-5 | PASS | `architecture-deployment.md` table and note; runbook "Host steps for the Gate A shadow trial" |
| SG-6 | PASS | see below |

**Mutations** (each applied, run, restored; 4/4 caught): model store set back to the evidence store (SG-1 driver test fails); `OverlayArtifacts.put` writes the shared store (SG-1 routing test fails); route checker ignores `aiand_routed` (SG-2 and R8 fail); `LARP_MODEL_API_KEY` never stored (SG-4 fails).

**Full suite** (Linux x86_64 container as root, Python 3.12.3 venv from `deploy/requirements-test.lock`, disposable PostgreSQL 14.24, `python -m pytest -q -p no:cacheprovider`): base `1388f80` **1578 passed, 10 skipped, 2194 subtests**; build `548a2c3` **1617 passed, 10 skipped, 2284 subtests**, no failure. All 10 skips are environmental: 1 opt-in external market artifacts, 1 root ignores directory modes, 5 disposable systemd runner, 3 bubblewrap. Hosted CI not used (org Actions minutes exhausted).

**Finding outside this change (not fixed here).** The deterministic path has the same read-only problem in a milder form: on the real read-only mount, every deterministic tool call was recorded `TOOL_ERROR:…:ARTIFACT_WRITE_ERROR` (fetch_document, prior_context, compare_facts), so Gate A's deterministic runtime would assess without its tools. Owner: section D / Keegan (runtime wiring). `OverlayArtifacts` is the likely fix.

### SG-7: deterministic tool results on the read-only evidence mount (pre-registered 2026-10-16, before the fix)

Claude Code session for Keegan (section B), after the PR #114 review. This fixes the "finding outside this change" above, because it breaks Gate A's deterministic runtime (IDEA-058) on the host.

| ID | Pass criterion |
|---|---|
| SG-7a | `build_driver` with `"assessor": "deterministic"` gives its `EvidenceAssessor` a `PortEvidenceReader` over `OverlayArtifacts`: shared = the evidence store (`<evidence_root>/artifacts`, read), private = `<market_artifact_root>/model` (write), the same private store the routed path uses. Nothing else in the deterministic wiring changes (same model, config and registry). |
| SG-7b | With a shared store whose `put` raises `OSError(30)` (read-only), a deterministic assessment over the synthetic world makes tool calls, none ends `ARTIFACT_WRITE_ERROR`, every tool result artifact is readable from the private store, and the shared store is unchanged. The same assessment over the read-only store alone does end with `ARTIFACT_WRITE_ERROR` (the failure reproduces). |
| SG-7c | No golden fixture is regenerated. Mutation caught: the deterministic reader set back to the shared store fails SG-7a. Full suite: no new failure against the merged base. |

### SG-7 results (2026-10-16)

Order: base merge `00df1b9` (`codex/system-testing-20261012` at `e84083c`; `docs/LEDGER.md` conflict resolved by keeping the base's IDEA-049-D and IDEA-055 rows and this branch's IDEA-056/057 rows) → criteria `2139445` → fix `8cb340a`.

| ID | Result | Evidence |
|---|---|---|
| SG-7a | PASS | `test_driver.py::Composition::test_sg1_routed_model_artifacts_go_to_a_private_runtime_store` (its last block, which asserted the deterministic reader was unchanged, now asserts the overlay) |
| SG-7b | PASS | `test_aiand_routing.py::…::test_sg7_deterministic_tool_results_on_a_read_only_evidence_store`: over the read-only store alone every tool call ends `ARTIFACT_WRITE_ERROR`; with the overlay none does, every result is in the private store, the shared store is unchanged |
| SG-7c | PASS | No golden regenerated. Mutation (deterministic reader back on the shared store) caught. Full suite, Python 3.12.3 venv from `deploy/requirements-test.lock`, local PostgreSQL **16.15** (not 14.24): base `e84083c` 1590 passed, 10 skipped, 2201 subtests; this branch at `8cb340a` **1630 passed, 10 skipped, 2291 subtests, 0 failed**. The same 10 environmental skips. |

SG-3 compatibility with PR #87 (2026-10-16): #87's GA03 guard lets a hosted `dev` run use only the explicit `shadow` evidence settings, so SG3 fills `intelligence_mode` with `shadow` when #87's `intelligence.shadow.v1.json` is present and `development` otherwise. Checked on a scratch merge of #87, #114, #115 and #116.

The "finding outside this change" above is fixed by SG-7. Not yet measured on a real read-only bind mount (SG-1 was); that is part of the host steps.

## Shadow trial on the Gate A deploy (2026-10-16 → ≤ 2026-10-21) — pre-registered

**Pre-registered 2026-10-16 SGT, before the trial starts.** Decision context: IDEA-056 MR-06 (2026-10-16). The trial runs the `aiand_routed` assessor with `execution: shadow` on the Gate A `primary` host with real AIand and OpenAI APIs, for 3–5 days, ending no later than 2026-10-21 so the team can decide by Oct 22. It is shadow only: no order is signed or broadcast; its rounds are test rounds (`mode: dev`). Bars marked **⚠ PROPOSED — team to confirm before the trial starts** are not frozen until the team confirms them in a commit before the first routed assessment; if the trial starts first, the bars apply as written here and any later change is reported as a deviation.

**Current owner decision (2026-10-18): TR-AC1 confirms the unchanged M1–M9/K1–K4
bars for the unsigned trial.** The PROPOSED labels below preserve the original
October16 registration; the current decision, frozen sampling seed/method and
remaining Keith/Yao prerequisites are in
[MODEL_TRIAL_HANDOFF_20261018.md](../build/MODEL_TRIAL_HANDOFF_20261018.md).
No earlier trial start, Keith personal review or collective adoption is inferred.

### Preconditions (before the first routed assessment)

- **P0 Provider check (open; Yao Zhu, on the host).** The AIand account's org-scoped catalog lists `moonshotai/kimi-k3` and `zai-org/glm-5.3`, each with the pinned efforts (`low` for GLM routine; `high` for the K3 primary and GLM secondary reviewers), and the first real routed assessment's recorded reply headers `x-model` and `x-reasoning-effort` match the requested model and effort for every stage that ran. Record the date, the catalog response hash and the first assessment's ID in this entry. A mismatch is a kill (K4). Not run yet.
- **P1 Budget ledger** initialized on the host with all prior OpenAI spend (Yao Zhu supplies the number; see the runbook). Record the `status` snapshot (charged, available) at the start.
- **P2 Pinned routing file** and its SHA-256 recorded here (the reviewed copy of `config/intelligence/aiand-routing.example.json`), plus the build ID.

### Data and method

Data sources, all read-only after the trial: the PostgreSQL journal (round records with their assessment results: `status`, `budget_used.elapsed_ms`, `routing` stages and reasons, `routing.budget`, `cost`, `model_io`), the model artifact store `<market_artifact_root>/model` (exact request/reply bytes and per-stage results), and the budget ledger (`charges`, `switches`). Unit of analysis: an **assessment job** — one assessment the coordinator requested; a round recorded `ASSESSMENT_UNAVAILABLE` counts as a job that did not complete.

| ID | Measure | Definition | Bar / use |
|---|---|---|---|
| M1 | Availability | Jobs that return a validated result with status `ASSESSED` or `ABSTAIN` and `elapsed_ms ≤ deadline_ms` (60 000), ÷ all jobs. `UNAVAILABLE`, `ASSESSMENT_UNAVAILABLE` and over-deadline count as failures; `REJECTED_REQUEST` is excluded and counted separately. | ⚠ PROPOSED: ≥ 95 % over the trial. |
| M2 | Latency | p50 / p95 / max of `budget_used.elapsed_ms` over completed jobs, against the 60 s deadline; per routing path (routine only / OpenAI review / external review). | ⚠ PROPOSED: p95 ≤ 45 s; p50 ≤ 20 s; any job over 60 s is a defect to report. |
| M3 | OpenAI charge | Ledger `charged_micro_usd` at the end minus at the start (reserved, unknown and settled), in total and per assessment (÷ all jobs, and ÷ jobs with an OpenAI stage), against the $40 admission. Include reservations still `RESERVED`/`UNKNOWN`. | ⚠ PROPOSED: trial total ≤ $8 (20 % of the admission); projected spend (start charge + trial daily rate × days left to Nov 12) ≤ $40. |
| M4 | AIand cost | Per-stage AIand token usage (input/output) per model and effort, and any provider-reported cost. External prices stay excluded from pass bars (user decision, IDEA-056). | Report only. |
| M5 | Verifier pass rate per stage | `bakeoff.metrics` claim-verification pass rate and schema-valid rate, computed separately for `routine`, `openai-review`, `external-review-0` and `external-review-1` from the stage result artifacts. | ⚠ PROPOSED: routine ≥ 0.80 and each review stage ≥ 0.90 claim-verification pass rate; schema-valid ≥ 0.95 per stage. |
| M6 | Escalation rate | Share of jobs with any routing review reason, broken down by reason (`ROUTINE_NOT_ASSESSED`, `INDEPENDENT_ITEM_CANDIDATE`, `EVENT_INTERPRETATION`, `INCOMPLETE_OR_CONFLICTING_EVIDENCE`, `SEEDED_CLEAN_CASE_AUDIT`), and by which reviewer ran. | Report; ⚠ PROPOSED alert (not a kill) if > 60 %, because the IDEA-056 §6 budget table assumes ≤ 50 %. |
| M7 | External-only switches | Ledger `switches` rows with reasons and times, plus per-assessment `MODEL_BUDGET_UNAVAILABLE` routing states. | Report every one; see K1/K3. |
| M8 | Disagreement with the deterministic baseline | After the trial, replay each job's identical request and saved evidence offline through `EvidenceAssessor` + `RuleBaselineModel` (no network), then `bakeoff.metrics(routed, baseline)` finding-type agreement plus a per-job diff of findings, event findings and status. | Report; disagreement is not error — M9 decides which side is right. |
| M9 | Accuracy and omission vs independent labels | Keith labels a stratified sample of the trial's filings **blind** to both outputs: the material findings and adverse events each filing supports. Sample: every filing if ≤ 40, else 40 drawn with a frozen seed recorded here before drawing, stratified by issuer × routing path × status. Measures: finding precision and recall, **omission rate** (labelled adverse events absent from accepted findings; `ABSTAIN` reported separately, not as a hit), for routed and baseline. Labels stay outside the repo (hash recorded here; never-do #7). | ⚠ PROPOSED: routed adverse-event omission rate ≤ baseline's, and zero unsupported Class 1/2 findings. With ≤ 40 filings this is triage only; it cannot establish IDEA-056 §7 non-inferiority. |

### Kill criteria (stop early; the operator acts, no code change)

- **K1 Spend.** OpenAI trial charge reaches $8, any single UTC day exceeds $2.50, or the ledger switches external-only for `OPENAI_OPERATING_LIMIT` before Oct 21: stop OpenAI use (remove `LARP_MODEL_API_KEY` from the runtime secret and restart); the trial may continue external-only and is reported as such.
- **K2 Availability.** M1 below 80 % over any rolling 24 h with ≥ 20 jobs: revert the runtime to `"assessor": "deterministic"` (re-pin the runtime config) and end the trial.
- **K3 Accounting.** Any `MODEL_BUDGET_UNAVAILABLE` state, an `OPENAI_USAGE_EXCEEDED_BOUND` switch, or a ledger/provider reconciliation difference: stop OpenAI use as K1 and reconcile before any restart.
- **K4 Identity or safety.** Provider check P0 fails, any served model/effort mismatch is accepted, any credential appears in a log or artifact, or any routed result reaches signing: revert to deterministic immediately and report as an incident.

### Outcome rules

- **Supports adoption (for the Oct 22 decision):** P0–P2 done, no kill fired, every frozen bar met.
- **Not supported:** a kill fired, or M1, M3 or M9 misses its bar.
- **Inconclusive:** fewer than 3 trial days, fewer than 20 completed jobs, or Keith's labels not ready by Oct 21.

Whatever the outcome, live/service use needs a later reviewed code change; this trial cannot enable it. Results and every deviation from this plan are appended below with dates.


### RR2 index reconciliation (2026-10-16)

PR88 is merged and its QuoteCostSummary record is IDEA-063. IDEA-057 continues to identify AIand routing. Remove the stale open-PR renumbering task from the current index/backlog. PR87 assembly is also merged into the testing branch; actual hosted Gate A and the shadow trial still require their recorded owners and evidence.

### #91: CI checks that could not run locally (recorded 2026-10-16)

All six items in #91 are green on mirror CI (`Keegan4/keegan4-larp-ci-mirror`, the repository's own `runtime.yml`).

- **The stack's branch head:** run [38874992380](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/38874992380) on `codex/idea-056-model-routing` at `3b4d1e6`, before #85 merged into `main`. All four jobs pass:
  - `infrastructure`: Terraform fmt, init, validate and test for `deploy/aws` and `deploy/bootstrap`;
  - `host-bundle`: the x86_64 build and `tools/test_host_bundle.sh` provisioning in Amazon Linux 2023;
  - `runtime`: `LARP_TEST_SYSTEMD=1` systemd conditions (3 passed); the full suite on exactly Python 3.12.15 with PostgreSQL 14.24 (**1552 passed, 4 skipped, 2210 subtests, 0 failed**); and `test_live_start.py:83`, which runs because the runner is non-root.
  - It was one hosted x86_64 (ubuntu-22.04) run of the whole workflow.
- **The integration head, which also carries #111's code (c075849, reached via #114):** run [38910102399](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/38910102399) on `codex/system-testing-20261012` at `e4f3d59`. All four jobs pass: full suite **1755 passed, 6 skipped, 2556 subtests, 0 failed**, plus real systemd 5 passed, on Python 3.12.15 and PostgreSQL 14.24.

The 1552-passed run predates #111. The second run covers that code on the integration branch. Org-repo Actions remain blocked (#98).

## SG-8 — prepare the documented LLM split (2026-10-17, prospective)

The user requests ChatGPT for main/difficult questions and the Chinese models for
lighter questions, following the docs. Base integration `0672fb8` already implements
GLM-5.3 low → conditional OpenAI `gpt-6.1-sol` medium review, with Kimi K3 high
then GLM high fallback. The missing integration is Gate A preparation: it always
emits deterministic configuration, and local package qualification rejects routing.
Branch `codex/llm-routing-preparation-20261017` adds explicit opt-in assembly rather
than asking the host owner to edit already prepared runtime bytes manually.

Pass criteria before implementation or changed-code execution:

- **SG8a:** prepare accepts a separately reviewed routing file and its expected
  SHA256 together; bounds and validates the public spec without secrets, budget
  access or inference. Copy exact bytes as `model-routing.json`; runtime and report
  pin those bytes, select `aiand_routed`, and use the documented single shared
  budget directory. Default preparation remains deterministic.
- **SG8b:** preparation and runtime share pure routing validation: exact supported
  model IDs, supported catalog/effort/context/output, one/two fallback reviewers,
  OpenAI effort, frozen audit settings and budget account. Reject malformed or
  altered specs before model, budget, network or output construction; fixed
  failure text never echoes supplied content. No arbitrary provider endpoint.
- **SG8c:** local qualification accepts routed dev-shadow packages only with the
  routing bytes and matching pins, refuses missing/extra/tampered files and
  service/live scope, and performs no credential, budget or provider lookup. It
  continues to distinguish local file validation from host/trial acceptance.
- **SG8d:** exercise the prepared runtime through real composition and the existing
  routed assessor using synthetic provider boundaries: routine GLM, required
  OpenAI review, budget/credit-driven Kimi/GLM fallback, common deadline/tool
  ceiling and full provenance. Retain existing service/live refusals and budget
  reserve. Run focused deployment/intelligence tests and full Linux/PostgreSQL14
  regressions after commit/push; record exact results and skips.
- **SG8e:** update the host runbook with opt-in preparation, original-evidence
  reviewer roles, secret names, actual prior spend and outstanding P0/P1/P2/trial
  requirements. No AWS/host activation, paid calls, labels or policy adoption is
  claimed. No parent model-selection or Gate A/B GAP closes.

### SG-8 results (2026-10-17)

- Criteria committed/pushed at `411dd52`; implementation/tests at `e652603` before
  execution. The first focused run was **127 passed, 1 failed, 7 skipped,
  198 subtests**, 5.74s. The new test incorrectly omitted the retained OpenAI
  budget-refusal stage from its expected trace; no POST occurred. Corrected and
  pushed at `08f2a0a` before rerun. The initial command omitted the disposable DSN,
  so the seven PostgreSQL tests were skipped, not passed.
- **SG8a–e PASS for offline engineering scope**, at pushed
  `08f2a0a1391dc6356859639e0097b636260d959f`: focused routing/preparation/qualification/
  driver/routes/secrets suite **135 passed, 198 subtests**, 14.71s, no skips, with
  disposable PostgreSQL14.24. Seven new tests cover exact-byte copy/pins, unchanged
  deterministic defaults, 16 invalid-spec mutations before construction, missing/
  altered/oversized inputs, actual CLI package production, complete local CI/terms
  package qualification and resealed inner-pin/path/scope mutations. Actual
  prepared runtime composition reads an ingested NVIDIA filing through the
  read-only evidence reader; synthetic transports demonstrate GLM-low → Sol
  review, original filing text at each tier, durable $40 budget refusal with no
  OpenAI POST, Kimi-high fallback and then GLM-high fallback. Original six-tool/
  ten-step/deadline limits and $10 reserve remain enforced by existing regressions.
- **Full suite PASS** at the same code: Linux x86_64, Python3.12.14,
  PostgreSQL14.24, bubblewrap through the supported namespace execution route:
  **1929 passed, 6 skipped, 2858 subtests**, 385.38s, exit0. Command:
  `env -u AWS_PROFILE PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PIP_CACHE_DIR=/workspace/.cache/pip LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/larp_test .venv-runtime/bin/python -m pytest -q -ra -p no:cacheprovider`.
  Skips: one optional external recorded-market dataset and five opt-in systemd
  cases; this host has no systemd PID1. No xfails. The AWS_PROFILE override is
  scoped to offline tests; no deployment authentication is changed. No golden
  trace was regenerated. Static Python AST and `git diff --check` pass.
- Logs outside Git at `/workspace/larp-cloud`: initial
  `llm-routing-focused.log` SHA256
  `dbc465ffe91d75d4785c0f2ee1d9b3c26b8fd456c2a04f9a2b6c3a0dc01b8970`;
  corrected `llm-routing-focused-corrected.log`
  `9b894daae0ae150fb43a8df5b1cf86fe1deeb24bcbfb47f0971fca6ecbb46966`;
  `llm-routing-full.log`
  `9ed94b5f53b6d120477c04f90d6564c2834612f85f9590f24bb9f7e1e229ed41`.
- [PR159](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/159)
  targets integration. Org Actions [39037596385](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/39037596385)
  ran no runtime steps; its annotation reports the existing account-payment/
  spending-limit refusal. No hosted CI pass is claimed for this change.
- Remaining: Yao Zhu installs reviewed prepared files before manifest binding,
  supplies runtime `LARP_AIAND_API_KEY` and `LARP_MODEL_API_KEY` for the requested
  OpenAI review tier (omit the latter only for an intentional external-only
  trial), initializes the single private ledger from actual prior spend, and
  records P0/P1/P2 and trial results. Keith supplies independent labels; team
  owns rights, production declaration/adoption and cut-line decisions. Runtime
  service/live refusal remains. No paid call, AWS/host mutation, activation,
  receiver upload, wallet signing or trading occurred. #97 and the parent GAPs
  stay open; synthetic calls do not establish real-provider access or quality.

### SG-8 review fix (2026-10-17, PR159 review)

- **Finding:** a routing file with a decimal value anywhere (e.g. a catalog
  `price_per_mtok: 0.5`) passed `prepare_shadow` and `gate_a_check`, but the
  runtime refuses it at startup: `build_routed_assessor` hashes the spec with
  `Document.from_dict`, which allows no floats. Preparation could report a package
  the service will not start.
- **Pass criterion:** `validate_routing_spec` refuses
  any spec `Document.from_dict` refuses, so preparation, local qualification and
  runtime construction all refuse it; the existing SG-8 tests still pass.
- **Fix:** `validate_routing_spec` now also builds the Document and maps its
  refusal to `IntelligenceError`. New mutation case in
  `test_shared_spec_validation_refuses_invalid_models_before_any_budget_or_model`.
- **Result: PASS.** New case fails without the fix (1 subtest failed) and passes
  with it. macOS arm64, Python 3.12.14 (no PostgreSQL/systemd): focused routing,
  Gate A and intelligence tests 394 passed, 2 skipped, 1178 subtests; full suite
  1514 passed, 421 skipped (database/systemd/optional cases), 2530 subtests.
  Linux/PostgreSQL for this commit: mirror CI result is recorded on PR159.

## SLM-01 — signed routed assessments (#162; 2026-10-17, prospective)

Isaac requests implementation of PR133's highest-priority task on a separate branch/PR, from integration `a428bab` (PR159). Keith reviews the resulting PR. This is code capability, not the host/model adoption decision, network approval, provider/rights qualification or B4 exposure producer. Read the kit logging input/cot/output requirements and F-102/Q-16: preserve returned provider summaries and complete stage records, without inventing reasoning.

Pass criteria written before new implementation/tests execute:

- **SLM1 — explicit scope:** signed routed service execution and live mode require an explicit adoption/reference setting and hash-pinned routing; unsigned defaults stay unchanged. Keep live intelligence/profile/balance/release/signer capability checks. No actual network, model, wallet or AWS access during config preparation/qualification.
- **SLM2 — independence:** assessment work runs off the runtime's safety/execution thread, with at most one in-flight model request chain and no unbounded queue/retry dispatch. A controlled blocked provider must not prevent further settlement, guard/HALT evaluation or mandatory risk-planning cycles. Background work must never sign or mutate trading state. Test with an event-controlled fake, not flaky timing thresholds.
- **SLM3 — completion authority:** a completed result is consumed once, at current decision time against its original immutable request through assessment_result and ContextBuilder/accept. Wrong run/profile/context, expired/future/malformed responses and failed model chains grant no evidence/trade authority. A restart cannot silently rebind an old request to a new context/build/run.
- **SLM4 — outages:** missing/pending/failed/timed-out assessments preserve the last accepted limiter cut and cannot expire it or raise exposure. Exercise the real S1 policy/planner with an accepted cut and model failure across sessions. Do not fabricate B4 inputs or an exposure-model call; those remain separate.
- **SLM5 — honest audit:** durable local assessment request/stage/model I/O/result records precede consumption; complete, rejected, late and interrupted results retain all completed stage calls and provider reasoning in the ai-seeds round log. Preserve original requests/responses and source result provenance; do not make invalid results usable by relabelling their identity. Log interrupted/in-flight status truthfully. A crash/restart regression must retain completed-stage I/O.
- **SLM6 — persistence and recovery:** background worker uses only read-only evidence and private model/budget/artifact stores; persisted OpenAI accounting remains unchanged across fallback/restart. Journal model outcomes before marking work finished. Duplicate jobs, pending commands and recovery retain normal execution fencing; no worker thread blocks process shutdown or accumulates after a hang.
- **SLM7 — preparation:** an explicit signed rehearsal/live option writes service execution, matching run mode/profile environment, live intelligence settings, reviewed adoption ref and original routing bytes/hash. Local qualification validates that scope and refuses resealed mismatches. Default dev-shadow remains byte-compatible in behavior. Fresh captures, zero stock holdings on initialization and all host checks remain enforced/unqualified as appropriate.
- **SLM8 — integration:** meaningful regressions show failed behavior on the old implementation (or mark controls), pass after the fix and compose the real coordinator/context/planner/audit path with fake model/market/chain boundaries and disposable PostgreSQL. Run existing model/routing/runtime tests and full suite once the implementation stabilizes. No paid provider call, real transaction, golden regeneration or live activation. Record exact tested commits and skipped/hosted limits.

Implementation approach to validate: bounded background assessment, immutable request identity, append-only per-assessment private trace and explicit main-thread completion; concurrent safety rounds use no new assessment. Reuse existing evidence acceptance and output logging, retaining audit-only traces even for discarded results. Parameters/thresholds and final model adoption are not decided here.

### SLM-01 implementation and verification — 2026-10-18 SGT

- **SLM1/SLM7:** explicit `model_adoption_ref`, hash-pinned routing and validated REHEARSAL/dev or FINAL/live profiles enable service-mode capability. Default preparation stays unsigned deterministic dev-shadow. `prepare --execution service --runtime-mode dev|live --model-adoption-ref <actual decision>` sets live evidence scope and retains unqualified host/Gate B checks; qualification checks matching signed identities without constructing providers or reading credentials/budget. Actual live evidence settings remain a startup prerequisite, not replaced by shadow values. No adoption decision is recorded by this code.
- **SLM2/SLM6:** one daemon background assessor chain, no executor queue or concurrent replacement on a hang. Safety ticks keep settlement, HALT supervision and deterministic mandatory planning on the main thread. The worker reads evidence and writes only private model/artifact/budget data, never the trading projection. Original requests and model replies/stage results are appended and fsynced before use; ACK is after the committed round. Existing execution waiting/claim fencing remains in place. Safety planning/HOLD rounds now run at service cadence and are logged: hosted log/DB capacity remains a real rehearsal/#60 check.
- **SLM3/SLM5:** main-thread completion passes the original request and result through the existing timestamp/context/run/profile and evidence acceptance checks. Invalid/late results cannot authorize evidence, but their original I/O and available provider reasoning remain audit-only input. Hash-chained per-run/build/profile journals retain complete unconsumed results or interrupted calls across restart; malformed/torn/tampered traces fail closed. Every completed routed stage retains its model/tool trace, and per-call records precede verification. Worker exceptions record only the class, not possibly credential-bearing exception text.
- **SLM4:** only a fresh ASSESSED result that this round's evidence gate ACCEPTs counts as assessment availability. Pending/missing/failed/duplicate/rejected results cannot advance S1's healthy-session cut-expiry clock. The regression caught an initial implementation that counted cached empty exposure input as healthy; fixed at `0182b32`. This does not implement B4's exposure producer or the MODEL-mode exposure call; until those land, the exposure-input dependency stays open.
- **RED:** `eb1598b`, 7 failures reproduce missing deferred lane and explicit preparation API. The final-profile fixture was corrected to use the real FINAL builder (not an unsupported `profile=` prepare argument). Additional PostgreSQL regressions at `1c2ac88`: 10 passed, 1 failed (limiter healthy-session counter) before its fix; the first sandboxed database attempt was denied local TCP access, then rerun with the required sandbox permission. That access failure is not a product defect.
- **GREEN (synthetic external ports, disposable PostgreSQL 14.24):** `8bbeff9` selected service/S1/new-model tests: **94 passed, 0 skipped, 38 subtests**, 66.09 s. `dfec9ce` new regression file: **14 passed, 0 skipped, 3 subtests**, 4.28 s. Tests cover controlled blocked providers, actual mandatory SELL command creation and CLOCK HALT while blocked, unchanged settlement entry, valid evidence acceptance, expired-result I/O/summary in the production logger, real GLM/OpenAI stage serialization, restart of interrupted traces, frozen limiter cuts across sessions, and signed/live driver composition with explicit review.
- **Full suite at pushed application/test head `3933e20`:** macOS (Darwin), Python 3.12.14, PostgreSQL 14.24 in the disposable Docker container, `LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55439/larp_test PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /private/tmp/larp-pr20-venv/bin/python -m pytest -q -p no:cacheprovider tests`: **1940 passed, 9 skipped, 2862 subtests passed**, 409.26 s, exit 0. No xfails or golden regeneration. Local logs `/private/tmp/larp-signed-llm-{red,integration-red,integration-green,latest,full}.log`. The earlier focused model/routing/preparation checks at `a43ea77` passed 97 tests / 1 skip / 155 subtests. Full hosted/systemd/bubblewrap/real-provider acceptance is not inferred from local tests.

All application/tests/criteria were pushed before execution. No real provider call or model charge, production wallet-key access, real chain signing/broadcast, host/AWS change, ai-seeds upload or service activation occurred; existing suite signing fixtures use ephemeral test keys only. #162 covers implementation only; #97 retains actual provider/rights/network/trial/adoption and hosted acceptance, and B4 remains separately owned. The existing incomplete-work line is narrowed, not removed. Keith reviews the implementation PR before a release; Yao owns actual configuration, budget/provider/source checks, activation and rehearsal evidence.

SLM-01 delivery: [PR #164](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/164), branch `codex/isaac-11-signed-llm-20261017`, open/mergeable into the integration branch with `Closes #162`. Parent #97 updated with implementation review status and retained external/adoption/B4 gates. GitHub Actions run `39049999354` at documentation head `ee040e6`, runtime check `117446464640`, ran no test steps: its annotation explicitly says recent account payments failed or the spending limit must be increased (#98). This is not a CI test failure or hosted acceptance. A new accepted mirror release is still needed after review/merge. The disposable test PostgreSQL container was stopped/removed; all work is committed/pushed and no deployment or key action was performed. When merging into the non-default integration branch, close completed child #162 explicitly if GitHub does not close it; keep parent #97 open for the remaining gates.

### PR164-R1 — retain ownership of timed-out provider workers (2026-10-18, prospective)

Review found that `EvidenceAssessor.assess` can return UNAVAILABLE while its inner provider thread is still alive. The deferred queue currently treats that return as completion, allowing overlapping reviewer/replacement calls and ACK before late provider audit writes. This violates SLM2/SLM5/SLM6 even though the blocked-assessor stub tests pass.

Pass criteria, before running the new regressions: (1) a real routed assessor with an event-blocked synthetic HTTP transport keeps its deferred slot after the inner hard deadline; no reviewer or replacement call starts until the original call exits; (2) ACK is refused while that worker is alive; (3) a late reply and its reasoning are journaled before the final UNAVAILABLE result and ACK, survive in audit-only I/O, and cannot reopen an acknowledged assessment on restart; (4) synchronous assessor deadlines remain unchanged; (5) run the focused regressions red/green, then the local CI runtime suite with PostgreSQL, real Linux systemd/bubblewrap, demo, Docker smoke, host-bundle and Terraform checks where available. No provider credentials, paid calls, live wallet or cloud deployment. Keep #97 adoption and hosted/provider gates open. Record results and exact commits below.

PR164-R1 implementation: `6a57d1d` adds an explicit `RoutedAssessor.assess_deferred` path. Only that background path asks the real `EvidenceAssessor` to wait for its abandoned worker after cancelling further model/tool work. It returns UNAVAILABLE even if the late reply would otherwise have been usable; complete late I/O/reasoning precedes RESULT and ACK. The router's existing shared wall-clock budget prevents a late review dispatch. The normal synchronous `assess` path retains its hard timeout. No policy parameter, budget, provider, profile or adoption decision changes.

- RED at pushed criteria/test commit `bd96bee`: both new real-router/provider regressions fail (lane freed while transport alive; ACK accepted prematurely), 2 failed in 0.73 s.
- GREEN at pushed application/test commit `6a57d1d`: those regressions pass, 2 passed in 2.48 s. The original focused runtime/routing/S1 suite had 124 passed / 100 subtests before remediation; full acceptance below covers it after remediation.
- Local CI environment: native ARM64 Ubuntu 22.04 container, checksum-pinned CPython 3.12.15 and exact `deploy/requirements-test.lock`, `pip check` PASS, non-root test user, disposable PostgreSQL 14.24, real systemd and bubblewrap. Runtime network is isolated to the disposable database; all model/venue/execution boundaries are synthetic. The initial full run's failures were synthetic executable stubs refused by the runner's `/tmp` noexec mount (not product failures). After remounting that disposable tmpfs executable, the affected two test groups pass: 14 tests / 10 subtests in 7.62 s. The full corrected-run result is recorded below.
- Real systemd acceptance: 5 passed / 5 subtests, 0 skipped, 11.67 s. Offline demo PASS: no pending audits/jobs/open rounds; verified journal, not quarantined. Docker build and `--network none --read-only --cap-drop ALL` smoke PASS.
- Host bundle at `6a57d1d`: native aarch64 build/provision/CI-manifest binding PASS for both primary and signer, repeated provisioning and privilege/isolation checks included, with provisioning networking disabled. Bundle SHA256 `0eba572fa743a413d2fd2cb550b70f1243aba4bbf58409f2f37bbfcb06acf77d`; release manifest SHA256 `cf5fc847b6c4aee720a4a1e3e9adec80d4d4580519a2e178e0b964ac04cd0bdf`. These are local review artifacts, not a deployed/activated release or an x86_64 hosted-CI artifact.
- Terraform 1.13.5 matching CI's Linux amd64 binary/checksum: both modules fmt/init/validate PASS; `deploy/aws` 19 tests and `deploy/bootstrap` 1 test PASS, with mock providers and no cloud credentials. The initial ARM64-only attempt refused its downloaded provider against the unchanged lock; acceptance uses CI's amd64 platform without modifying any lock.
- Final corrected full CI runtime run at `6a57d1d`: **1945 passed, 6 skipped, 2862 subtests passed**, 247.09 s, exit 0. The six skips are the five opt-in systemd tests (all five PASS in the explicit job above) and one opt-in external-data case. No xfails or golden regeneration. Raw runtime/demo evidence retained outside Git at `/private/tmp/larp-pr164-results/`; synthetic credentials/throwaway test keys only.

PR164-R1 final review: no remaining implementation blockers found on the tested application head. The user requested fixing the finding, adding PR comments, running CI locally and merging after completion. The verification-only documentation commit changes no executable source or tests. PR #164's target remains `codex/system-testing-20261012`; merge receipt/head are authoritative in its GitHub metadata. Hosted Actions at fixed head `6a57d1d` (run `39051309773`, runtime check `117450296047`) again ran no steps: the annotation confirms the same account-payment/spending-limit refusal (#98). This local acceptance does not approve activation or settle #97's provider/rights/network/trial/adoption/hosted/B4 gates. Keep #97 and the narrowed incomplete-work item open; #162's implementation scope is complete once merged.

## TR-AC1 — release and trial-bar confirmation (2026-10-18)

The user delegates completion of Keegan's LLM application tasks: accept release
7a0ea14, confirm trial bars and dispose of DOJ/BIS gaps. The assistant records
Keegan-workstream decisions, without attributing Keith/team personal approval.
Accepted release, fixed hashes, unchanged M1–M9/K1–K4, frozen blind-label seed
and deterministic selection method are in the dated handoff and machine-readable
`ModelTrialOwnerDecision.v1`. Effective at publication before the first routed
assessment; an earlier start must remain an explicit deviation. An early Oct20
outcome with fewer than3 trial days is inconclusive under the original rule.

Release acceptance relies on PC-CI02's published artifact verification at PR133
commit9b363e6 plus independent application-tree/full-suite evidence; this session
received404 from private-mirror APIs and did not independently download/hash
bundle bytes. No provider call, budget initialization, host operation, signing
or model-adoption approval occurred. Keith's independent bar review, exact prior
OpenAI spend, rights/funding and labels remain his tasks. Yao retains actual
P0–P2, report, prepare/bind/activation and first-assessment evidence.

PC-GAP01 allows two fixed-window historical-backfill explanations for the
unsigned trial, preserving raw reports/logs and INCOMPLETE runtime coverage.
It does not satisfy signed/final source completeness, waive actual poll errors,
or explain other targets/archives. The prospective11:00UTC report was not read.
See IDEA-066 PC-GAP01 and the handoff for the exact window and checks.

## OP-01 — OpenAI preferred with paced full credit (2026-10-18, prospective)

Yao Zhu requests a separate PR for human review implementing PC-ROUTE01
(PR133). This authorizes development, not merge, deployment, model calls or
spend. Existing v1/v2 configurations and their US$10 reserve stay unchanged.
The new opt-in v3 policy prefers GPT-6.1 Sol medium, with Kimi K3 high then
GLM-5.3 high on the qualified AIand endpoint as fallback. Model quality is
unproved; effort/cost is not evidence of accuracy.

Pass criteria recorded before changed code/tests run:

- **OP1:** strict public v3 configuration pins a UTC start/end, period, total
  allocation and prior-spend baseline. Example values are review candidates,
  not adopted dates: US$50 total, US$2 already spent, US$48 remaining, no fixed
  reserve. Preparation validates/hashes this without credentials or network.
- **OP2:** cumulative equal-period allowances use integer micro-USD, carry unused
  allowance forward and release all remaining allocation by the final period.
  Every POST reserves its bounded cost atomically. Temporary pacing/window/
  oversized-request refusal grants no OpenAI call and does not latch exhaustion;
  a later period or smaller request can use remaining credit. Full allocation
  exhaustion and provider credit exhaustion persist external-only across restarts.
- **OP3:** durable policy/account/limits binding prevents accidental legacy or
  mismatched-policy access. Explicit initialization never overwrites a ledger;
  explicit development migration preserves every charge, unknown/reserved amount
  and existing safety latch. Unknown usage keeps its bound; underestimation and
  storage failure block further OpenAI dispatch. Clock rollback fails closed
  until wall time catches up; no automatic budget or policy reset.
- **OP4:** real routed assessments try OpenAI first with a shared deadline/tool
  budget. Missing key, pacing, errors, invalid claims and exhaustion fall back
  to high-effort AIand using original evidence. Required independent review
  uses AIand; disagreement abstains, failed required review grants no authority.
  Provider rate limits do not imply permanent credit exhaustion. Existing
  verification, evidence acceptance and deferred-worker safety ownership stay.
- **OP5:** identity and audit expose the frozen policy, current allowance,
  remaining allocation, stage order, refusals, model I/O and known/unknown cost;
  keys never enter them. Synthetic tests exercise multi-period/restart/concurrent
  admission, migration and malformed policy, real verifier/fallback/deferred
  composition and offline preparation. Existing routing/prompt/runtime suites
  and full available local suite must pass, with skips and host limits reported.

Finite credit cannot guarantee every assessment stays on OpenAI or consumes the
last cent: conservative multi-call reservations, unknown usage and external
account spending reduce availability. No credit-balance query or paid provider
call is required. New policy adoption needs a fresh trial evaluation and an
accepted mirror release; existing v2 trial evidence is not v3 qualification.
