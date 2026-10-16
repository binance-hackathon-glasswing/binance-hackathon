# IDEA-066 — Gate A inventory and offline package qualification

- Date / owner: 2026-10-16 SGT / Isaac with Codex; runtime/deployment review: Keegan.
- Baseline: `eda2ed2`, fetched from `codex/system-testing-20261012`; PR87 and the Gate A assembly are already merged.
- Issues: [#127](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/127) tracks hosted qualification; [#128](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/128) covers the offline package check. Existing #32/#49/#92/#98/#118–120 keep their own acceptance criteria.
- Scope: inspect assembled inputs before deployment, using existing consumer validators and local files only. This grants no runtime/signing authority and cannot establish Gate A PASS. No AWS operation, real capture, upload or wallet action is part of this change.
- Sources checked: SKILL.md §0/F/K/Q (including F-119–124 and settled answers), the verbatim `official/source_page.md`, kit `logging.md` and `PROTOCOL.md`; DEPLOYMENT_BUILD DR-01/07/11/12/13/15/16/18/20, GATE_A, IDEA-058 and GAP-69–72. Gate A is a team gate; version integrity, trace mapping and source authorization come from F-60–63/F-99–103. Official rules and unresolved scoring questions are not invented here.
- Findings: configuration assembly exists; a consolidated read-only check of the transferred package, CI release bytes and retained terms is missing. Hosted evidence is still unrecorded. The quote-cost tool is already merged (#88), but real captures/output review remain #118–120; GAP-69's older tool-build wording needs narrowing.

## Prospective acceptance (before implementation execution)

- **PC01:** read only an existing prepared directory. Check exact expected file names, refuse symlinks/missing/changed files and validate every preparation hash. No package files are rewritten.
- **PC02:** require dev/shadow/deterministic/shadow-intelligence scope, approved cadence/day-roll settings, matching run/build/wallet and pinned state/profile/calendar/issuer inputs. Recompute the initial state through the existing producer/consumer checks; malformed identities, altered holdings and inconsistent pins refuse.
- **PC03:** validate runtime, uploader and operations with their actual configuration validators, substituting only an explicitly supplied local copy of the pinned RDS CA path. No database, credential or remote service is accessed. Missing CA/RPC settings cannot PASS.
- **PC04:** check an explicit CI manifest against its release tree and prepared build, preserving existing manifest/register/file validation; refuse mirror origin or an already host-bound manifest. Missing CI inputs stay NOT_RUN. This is byte consistency, not proof of a remote CI run; #49/#98 remain separately open.
- **PC05:** parse only the generated public evidence environment format, and use existing source/terms preflight with an explicit external artifact root. Missing contact/hash/artifact bytes block local readiness; no terms are fetched or fabricated. First BNB is a Gate B dependency and does not block this unsigned check.
- **PC06:** machine-readable output uses fixed reason codes, no raw exceptions/endpoints/contact/account/wallet/credential values. Always `signing_enabled: false`, `gate_a_passed: false`, and every host check NOT_RUN. Exit 0 means only local checks pass; 4 means blocked/refused.
- **PC07:** regressions cover valid assembly, each refusal boundary, unavailable prerequisites, mutation detection and no remote/write side effects. Commit and push covered code before execution; record exact SHA, environment, results and limits. Run the feasible related suite; do not describe macOS/local synthetic checks as Linux/host acceptance.

## Outstanding work and handoff

#127 retains the hosted checks with Yao Zhu/Keegan/Isaac/Keith as listed in the issue. GAP-69–72 stay open. Deployment spend follows AWS_RUNBOOK's named approval, and org Actions billing (#98) plus exact downloadable bundle (#49) remain with the account owner/Keegan. The implementation PR closes #128 only. No merge to main, activation, organiser message or infrastructure change is authorized by this record.

## PC-V01 — first local run, 2026-10-16 SGT

At pushed `1ea851c`, Python 3.13/macOS unittest: 10 passed, 1 failed. The terms-artifact test selected the first filesystem artifact, which may belong to a disabled source; preflight correctly does not require disabled-source terms. Correct the fixture to target EDGAR's required terms hash, preserving the production validator. An earlier invocation yielded before completion and its final output was unavailable; the recorded complete run is the one above. No host, provider or economic evidence was produced.

## PC-V02 — local acceptance, 2026-10-16 SGT

- Tested commit: pushed `61f935c`; Python 3.13. System interpreter, not the pinned Linux host/test profile; no PostgreSQL configured. No dependencies installed or cloud changes made.
- Command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.runtime.test_gate_a_check tests.runtime.test_gate_a tests.runtime.test_deploy_presetup tests.runtime.test_live_start tests.runtime.test_manifest_prompts tests.runtime.test_release_bundle tests.runtime.test_release_register tests.sources.test_release_mode tests.sources.test_final_a_requirements -v`.
- Result: **81 passed, 6 skipped, 0 failed** (87 tests, 10.446 s). All 11 new package tests pass. The six PostgreSQL-only skips cover the existing full Gate A composition, wallet switch/start checks and version-event tests. They are not host acceptance; the entire Linux/PostgreSQL suite was not run locally.
- PC01–06 PASS on synthetic fixtures: byte changes/missing/extra/symlink files; re-sealed build/run/wallet/scope/database/pin/state/issuer/RPC changes; the real service validators with a wrong role/CA; matching CI manifest and changed-build/mirror/bound/tampered release refusals; required retained terms bytes; generated environment parsed without shell execution; zero-BNB unsigned operation; fixed output/exit codes and value-safe failures. A passing local check always keeps every host check NOT_RUN and grants no authority.
- PC07 side effects: a complete passing check runs with network/subprocess/DB/capture paths trapped and leaves every fixture file byte-identical. Fixture manifests are generated by the real bundle producer and checked by production manifest binding; source terms are explicitly synthetic bytes in a disposable tree. No real receiver/provider or rights evidence is claimed. `git diff --check` passes.
- Remaining: registered-repo CI/bundle acceptance (#49/#98) and all real deployment evidence (#127, GAP-69–72). The PR carries `Closes #128`; #127 stays open. A PR into the integration branch does not automatically close its issue on GitHub until the change reaches the default branch; the closing relationship is recorded for that promotion.

## PC-CI01 — PR and org CI, 2026-10-16 SGT

- [PR #129](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/129) targets `codex/system-testing-20261012`, contains `Closes #128`, and is mergeable. No merge performed.
- At documentation head `d52ba7b` (same tested code as `61f935c`), [Actions run 38925891632](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38925891632) could not start any of its four jobs. The runtime check annotation explicitly says: "The job was not started because recent account payments have failed or your spending limit needs to be increased." Logs are unavailable because the jobs did not start. This is the existing #98 account-owner blocker; no green CI or release bundle is claimed.
- All session changes are committed and pushed on `codex/gate-a-package-check-20261016`, with no unpushed commits. Handoff remains pending PR review, CI (#98), deployment qualification (#127), and eventual integration/promotion; this work does not establish that main matches origin/main or that Gate A passed.
