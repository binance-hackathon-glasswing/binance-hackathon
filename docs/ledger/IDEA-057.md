# IDEA-057 — AIand implementation of external-first evidence routing

- Date / author: 2026-10-15 SGT / Keith, implemented with Codex at the user's request to do both the AIand-specific design and implementation.
- Status: open for review (shadow implementation; AR1–AR8 synthetic/local acceptance passed 2026-10-16; no real-provider inference or live adoption).
- From: [IDEA-056](IDEA-056.md), draft PR #85. This branch is stacked on `codex/idea-056-model-routing` at `ab2e155`, not merged into main.
- Review: [implementation PR #86](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/86), stacked on proposal PR #85. Local acceptance only; merge and live adoption are separate decisions.
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

- Before execution: static AST parsing of changed Python and JSON parsing of the example passed; no project module was imported. Synthetic regression cases prepared in `tests/intelligence/test_aiand_routing.py` plus runtime composition/secret tests. Execution results are pending the repository's committed-and-pushed requirement.

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

### Issue #93 cleanups — prospective criteria (2026-10-16 SGT)

Non-blocking findings from the PR #86 review ([#93](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/93)). Written and pushed before the changed code runs. Tests in `tests/intelligence/test_aiand_routing.py` (`BudgetAdmission`); each new test must fail on the unfixed code and pass after the fix.

| ID | Required evidence |
|---|---|
| I93-1 | `ModelBudget.initialize` closes its SQLite connection: a test that wraps `sqlite3.connect` sees `close()` called on every connection `initialize` opens, and the file can be renamed/removed and re-initialized afterwards. |
| I93-2 | One `switches` row per real switch. After an over-bound settle through `BudgetedOpenAI.step` (usage above the reservation), the ledger holds exactly one row, `OPENAI_USAGE_EXCEEDED_BOUND`. Calling `external_only` again, or an `admit` refused at the limit while already external-only, adds no row. A first switch still records its reason. |
| I93-3 | Directory privacy matches the runbook. `ModelBudget(...)` (and therefore `initialize`, which reopens the file) refuses a ledger whose parent directory has any `0o077` mode bit (group-readable `0o750` is refused) or is not owned by the current user. A `0o700` parent owned by the current user still opens. Ownership is tested by substituting the expected owner id, since tests cannot chown. |
| I93-4 | The stale "Execution results are pending…" line in the Validation record above is updated to point at the recorded results. |

No AR1–AR8 or PR85-R1/R2 test may regress; the full local suite (Python 3.12, PostgreSQL 14) is run after the fix and reported with exact counts.
