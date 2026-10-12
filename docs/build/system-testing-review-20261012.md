# IDEA-044 — Claude continuation checkpoint

The user requested a comprehensive review of the entire system-testing codebase, proceeding through components, integration and system tests, with prospective expectations, fixes, independent review and red-team cases. They explicitly authorized subagents and a PR. They then requested a usage-limit stop and this handoff. Continue the same work; do not restart the review or merge into main.

## Branch and authority

- Repository: `/Users/songyaozhu/binance-hackathon`, remote `https://github.com/binance-hackathon-glasswing/binance-hackathon.git`.
- Work branch: `codex/system-testing-review-20261012`, based on `213a782`.
- Published implementation commit: `5dc42de6d330c8e26a1e6f719b3c27da55d2f516`. Draft PR: [#18](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/18).
- **PR base: `codex/system-testing-20261012`**, explicitly corrected by the user. Discover the existing draft PR with `gh pr list --head codex/system-testing-review-20261012`; update that PR rather than creating a duplicate. No merge is authorized.
- Read `AGENTS.md`, then `docs/skill/SKILL.md` under its reading rules, the LEDGER table, this file, `docs/ledger/IDEA-044.md`, and relevant `docs/INCOMPLETE_WORK.md` entries.
- Code affecting decisions/trades/logging **must be committed and pushed before execution, including offline tests**. This was followed: no modified repo Python/tests/demos/probes ran before this checkpoint. Every subsequent code fix must also be published before testing it. Never force-push/rebase/amend pushed history.
- Existing untracked **`Claude outputs/` belongs to the user**. Do not inspect, delete, stage or commit it. Do not use `git add .`. Secrets, dotenv and private data remain excluded. Official-kit/vendor copies are immutable.
- No live venue/model/source calls, wallet signing, registered ai-seeds logs, cloud provisioning or money movements are authorized by these synthetic checks.

## Completed work

All first-party `larp` modules, migration/deployment/CI definitions and ancillary scripts were reviewed by the parent plus three component reviewers. Selected tests were reviewed by boundary. Independent cross-review already checked evidence/source, runtime/storage/release, cadence/replay and deployment roles. The ledger records C01–C13 prospective acceptance and R01–R26 findings/disposition; detailed reviewer notes are preserved in its appendix.

Implemented fixes cover expired unsigned attempts, RPC/market/signer failures, credential echoes and probe redirects, independent adverse filing support, incomplete source coverage/retry recovery, artifact integrity/durability, provider responses, numeric evidence verification, spending health/cost ordering, research chronology/horizons/candles/statistics, IAM archive verification, genesis integrity, manifest/config binding including durable registered hash, discretionary broadcast cadence, IAM/SQL roles and retention floor. No adopted policy values or live capability gates were changed.

**Implementation is NOT VALIDATED.** `git diff --check` passed. Pinned environment installation and initial `pip check` passed; PostgreSQL container startup passed. Repository test counts are unknown. First CI may fail on deliberately stale golden traces; other failures are not expected/waived. Do not claim the old IDEA-043 919-test baseline validates these fixes.

## Resume in this order

1. Inspect `git status`, branch/head/remote and the draft PR/CI. All checkpoint changes were intended to be committed/pushed. Verify that before running. Main and user material were not changed by this review.
2. Finish the local test environment install using `deploy/requirements-test.lock` (the last signed-probe tests added existing project-pinned requests/dotenv dependencies after the initial install). Use Python 3.12; do not change dependency versions to hide failures.
3. Use a **clean temporary checkout of the pushed review branch** for testing. The user directory makes the shared checkout dirty, and `tools/system_test.py` intentionally refuses dirty trees. A local clone of committed files with origin set to the GitHub URL is sufficient after verified publication; alternatively clone the exact remote branch. Keep raw test artifacts outside the repo.
4. Run focused component regressions with no inherited credentials. Cover `tests/strategy tests/risk tests/research`; `tests/intelligence tests/sources tests/redteam/test_semantics_redteam.py`; `tests/execution tests/marketdata tests/signer tests/test_w04_execution.py tests/test_w08_capabilities.py tests/test_probe_boundaries.py`. Use pytest so parametrized cases and all subtests run. The test database is required for the PostgreSQL tests; a skip is not a pass.
5. Regenerate the synthetic intelligence goldens using **published** code: `python -m larp.intelligence.demo --out tests/intelligence/golden`. Review every semantic difference. Expected baseline identity/hash changes come from `facts.py`, `verify.py`, and `models.py`; independent filing findings may affect derived identifiers. Unexpected status, thesis, tool-use, falsifier or gate differences must be understood before acceptance. Re-capture `tests/strategy/fixtures/assessment-producer.json` request/result exactly from its `source_trace`, with `producer_commit` equal to the published producer HEAD. Preserve the other fixture metadata. Commit/push the reviewed outputs before final tests. `python -m larp.integration.demo --out <outside-repo-file>` provides an additional synthetic trace if useful.
6. Run integration/storage/runtime/audit tests, especially new `tests/integration/test_cadence.py`, `tests/runtime/test_review_boundaries.py` and real-role `tests/runtime/test_anchors_roles.py`. New cases exercise actual PostgreSQL, archive preparation, replacement same-build manifests, cross-session broadcasts, restart and exact replay. Fix test or code failures based on evidence; commit/push before rerunning affected code.
7. Run the complete suite with the disposable DB, then the enhanced `tools/system_test.py`. On macOS, bubblewrap is unavailable: `--linux-ci-run <successful-run-id>` must reference a successful GitHub runtime job with the same runtime tree. This tool verifies the run rather than accepting an assertion. PR CI runs full Linux pytest, the namespace-isolated runtime demo, Docker build/network-disabled smoke and Terraform fmt/init/validate/tests for both `deploy/aws` and `deploy/bootstrap`. Inspect all jobs and actual skip reasons.
8. Perform final independent review/red-team of the tested diff and callers; resolve findings and rerun affected checks. Update IDEA-044 with exact commits, commands/counts, CI links, failures fixed and remaining limits. Update the PR body from checkpoint state to final behavior/validation; mark ready only after checks pass. Keep broad live-production backlog items open. No merge requested.

## Local resources at checkpoint

- Python venv: `/private/tmp/larp-review-venv` (created from `/opt/homebrew/bin/python3.12`). Install final lock additions before running new probe tests.
- Disposable PostgreSQL: compose project `larp-review-20261012`, service `postgres`, container `larp-review-20261012-postgres-1` from `deploy/compose.test.yml`, loopback port 55432. DSN: `postgresql://postgres@127.0.0.1:55432/larp_test` (local fixture only). Start/check with `docker compose -f deploy/compose.test.yml -p larp-review-20261012 up -d --wait postgres`. Clean up this project when done; do not touch unrelated containers.
- Set `LARP_TEST_DATABASE_URL` to that local DSN and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. For system runner also set `LARP_SYSTEM_TEST_DISPOSABLE=1` and an outside-repo output directory. Its child environment scrubs credentials and installs a local-network-only socket guard. Use equivalent secret-free environment for focused tests; never load `.env`.
- `.github/workflows/runtime.yml` runs on every PR and supports workflow_dispatch. Push alone to this review branch does not trigger it without a PR.
- Original reviewer scratch reports in `/tmp/larp-{execution,intelligence,strategy}-review.md` are optional copies; durable notes are in the ledger. No new dependency on these temp files.

## Remaining capability limits and formal handoff check

`larp.runtime.service.build_driver` deliberately raises `NotIntegrated`; live Executor/router/native-BNB-finality and hosted recovery/signing/source/model/economic/calendar evidence remain unqualified. Existing owners: Keegan + Isaac (runtime/execution/host), Keith + Isaac (market/cost/first BNB), Yao Zhu + independent annotator (real documents/rights/model), team (hosting/rota/final freeze). Original-data research reruns under GAP-66 remain pending. Synthetic fixes do not establish live readiness.

This is a **published implementation checkpoint**, not a completed/verified session. Functional validation, generated fixtures, final review and PR readiness remain open. The shared worktree also retains user-owned untracked material, so the strict AGENTS clean-worktree handoff check is not satisfied. List any actual unpushed commits if publication failed; do not call it fully ready while these conditions remain.

Verified at publication: no unpushed review-branch commits and no unstaged tracked changes; only `Claude outputs/` is untracked. Local `main` is `a21d03432c1436dc676ff5fb4afefbf223dfa520`; cached `origin/main` is `5e945e148314b395a09ffe3e8a1461467b617114`, so the strict main-equality check also fails. Both refs were left untouched; this PR's target is the separate testing branch. Do not rewrite or synchronize main as a side effect of resuming this review.
