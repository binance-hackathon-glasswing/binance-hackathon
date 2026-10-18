# IDEA-039 — Isaac: live market and execution integration

## GB-RW3 — PR155 review: returned quote binding (2026-10-17 SGT, prospective)

All-PR review found that the offline numeric checker binds request parameters but
does not compare returned `routerResult` token addresses/decimals or input amount.
Its synthetic fixtures omitted those real response fields. This can report
numeric COVERED for a mismatched response, despite GB-CAP2's stated units/binding
criterion; owner approval still remains blocked.

Before changed code runs: extend fixtures to the actual response shape; compare
returned pay/receive token addresses and metadata scales against the requested
pair and configured stock units (USDT/BNB18), and require the exact returned input
amount, positive received/minimum quantities and minimum <= quoted receipt.
Check GET method and any supplied transaction sender/chain metadata; missing
optional transaction sender/chain metadata is not invented. Mutations of each
binding must yield numeric BLOCKED/missing pair, with unchanged owner/signing
refusals. Push regression and fix before execution; run focused caps/proposal/
Gate B checks and the combined review regression. No source or quote-execution
qualification is inferred from these numeric comparisons.

GB-RW3 review status: regression commit `2c594db` was pushed before execution;
all 12 response/method mutations reproduced false numeric coverage. Fix `617abb0`
is committed locally, but GitHub authentication subsequently returned HTTP401
and Git push lost authentication. Changed-code tests have not run because the
push-before-execution rule applies. Push the repair, then run the caps/proposal/
Gate B regressions and combined review suite; do not call this repair verified yet.

GB-RW3 update: authentication recovered and `a8101a9` (including fix `617abb0`)
was pushed before changed-code execution. Focused cap/proposal/Gate B regression
**33 passed, 105 subtests**, 0.88s, no skips (Linux/Python3.12.14). All 12 returned
response/method mutations now block numeric coverage; non18 metadata and omitted
optional transaction fields remain supported. The earlier blocked status above
is historical. Combined review verification follows in IDEA-049 ALLPR-20261017.

## GB-RW1 — remaining Gate B reconciliation (2026-10-17, prospective)

User requests all remaining Gate B work after inspecting all PRs and the remaining-work briefs. Base: integration `0672fb8`, rather than lagging main `fb95114`. All 85 advertised PR heads were fetched through native Git and compared with both branches. Seven heads are outside integration: historical closed #10/#82/#83/#89, remaining-work brief #126, checklist #133 and incomplete source acquisition #139. Their documents were read as references; no PR is merged or represented as independently approved here. Initial GitHub API/discussion requests were blocked by cloud egress; `api.github.com` was added to the environment draft, preserving the package-manager preset. API access later recovered and was verified directly; publication of that draft is not claimed.

The independent repository work is the missing #44 current-input qualification, plus reconciling GAP-30/31/32/47 with the actual execution/storage/replay implementation. Existing caps, lifetime proposals, decoder and signer-access code are reused. Router source/ABI, recorded quote files, current measured profile/holdings, numeric approvals, account/host access and real rehearsal evidence are external prerequisites. No team decision is inferred from a proposal or a synthetic PASS. B6's actual-session/attempt enforcement remains separate from the existing planning-session swap counter; it is not silently called complete.

Pass criteria, before implementation or test execution:

1. **GB-CAP1:** an offline, read-only cap review loads hash-pinned profile, policy, execution configuration and starting portfolio. It uses the existing LIVE-profile, signing-policy and execution-config validators. It checks one complete largest target position plus reserve, per-trade and gas-top-up USDT inputs in raw token units, every current token holding without assuming sell splitting, all configured tokens/spenders, and configured worst-case `max_gas * max_gas_price` against the signer fee ceiling. Use integer/rational arithmetic; reject boolean/negative/malformed quantities, wrong identities, units, environments and altered hashes.
2. **GB-CAP2:** review existing recorded successful quote artifacts as additional raw input/fee observations, with chain, wallet, spender, exact supported pair, execution mode, token decimals, positive quantities and capture time checked. Missing five-name BUY/SELL or top-up coverage, stale/future captures, missing evidence and an example policy remain explicit blockers. A numeric-coverage result never grants approval or signing authority, generates an installable policy, calls a provider, reads credentials or starts a service.
3. **GB-CAP3:** CLI inputs are size-bounded and pinned; output is a new private file, never overwrites, and failure output does not echo supplied content or secrets. Tests cover cap equality/+1, non-18 token scales, full-holding sale limits, gas envelope, environment/wallet/build binding, missing/stale/malformed evidence and byte changes. Push code/tests before running them.
4. **GB-AUDIT:** verify relevant existing real-PostgreSQL identifier, crash/fencing, settlement/reservation, nonce/reorg and replay tests on this branch. Update stale remaining-work text only as far as those results demonstrate; keep source, owner, host and signed acceptance distinct. Run the full Linux/PostgreSQL14 suite with required namespace execution after focused checks pass.

This record authorizes only offline repository qualification; the named human/account/wallet steps remain with the pre-trading checklist. Results are recorded below.

GB-RW1 report finding (prospective): the no-input `gate_b report` correctly exits 2 with overall BLOCKED, but prints `blockers: []` while all 19 DR checks are blocked in the retained artifact. **GB-REPORT4:** expose the sorted blocked-check IDs and OWNER_REVIEW_REQUIRED acceptance in the CLI summary, preserving probe behavior and exit codes. The cap checker must also refuse an output inside the checkout and profile/ledger native-scale disagreement. Push these changes before execution.

### GB-RW1 results and remaining qualification

- Criteria pushed at `2bff036`; implementation/tests pushed at `6f3b668` before execution. First focused result: 6 passed, 1 failed, 27 subtests; the failure was a missing refusal-type import in the test, corrected/pushed at `73d5826` before rerun. No assertion was disabled.
- **GB-AUDIT PASS** at `73d5826`: execution/cap/native/settlement/PostgreSQL crash/replay subset **117 passed, 165 subtests**, 19.18 s. Includes real database process death and immutable registry/observation recovery, actual I3/I4/accounting, reservation release on fill/revert/NOT_SUBMITTED, retained uncertainty after timeout/reorg, and recorded-port replay.
- **GB-CAP1..3 / GB-REPORT4 PASS** at pushed `768d333`: cap/proposal/Gate B report subset **32 passed, 93 subtests**, 0.56 s. The new cap review has 10 tests, covering S1 largest frozen-position input, all raw stock holdings, fee equality/+1, non18 stock metadata, missing/stale/wrong-wallet/chain/pair quote evidence, source-byte changes, output privacy/non-overwrite, scope, native-scale mismatch and fixed failure output. `numeric_status: COVERED` never changes BLOCKED/ready_to_install=false/signing_enabled=false or supplies owner approval.
- Full initial run at `768d333`: **1932 passed, 1 failed, 6 skipped, 2856 subtests**, 312.74 s. The one failure was the pre-existing stubbed archive SDK test inheriting a platform AWS_PROFILE selection without a backing profile (ProfileNotFound); it was an environment issue. `env -u AWS_PROFILE` for that offline test process made all four archive tests pass. No runtime or test source was changed for it.
- **Full corrected run PASS**, same pushed code `768d333`, Linux x86_64 / Python3.12.14 / disposable PostgreSQL14.24 / required bubblewrap namespaces through elevated execution: **1933 passed, 6 skipped, 2856 subtests**, 339.97 s, exit0. Command: `env -u AWS_PROFILE PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PIP_CACHE_DIR=/workspace/.cache/pip LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/larp_test .venv-runtime/bin/python -m pytest -q -ra -p no:cacheprovider`. Skips: one opt-in real-market artifact test and five disposable-systemd cases (systemd is not PID1 here). No xfailed cases. Saved environment startup instructions now include the test-only profile override; real deployment authentication is unchanged.
- Logs retained outside Git under `/workspace/larp-cloud`: `gate-b-focused.log` SHA256 `0ff06575145f1baf2540135c00a68ada73540c6a22c8d93ccab666569ffd8485`; `gate-b-qualification.log` `6d12be72d9f0578ef2c0be90093a71eec7a27cc30dbc3d7087a848c495b5becb`; initial `gate-b-full.log` `14a7788dacbc5aa495961d1d5446c4cb2078ede8b25447e8b26122955135feba`; corrected `gate-b-full-corrected.log` `e6974f5827fc022f186069d79f040c08e9b51f737e6cb8a2e93cea1017e197bb`.
- **GAP-30 definition/uniqueness COMPLETE**: the economic key, command/intent, decision/round/version/reservation, per-step attempt/payload/transaction and stable observation/round-log identities are implemented and exercised by the tests above. The exact mapping is in [GATE_B_REMAINING.md](../build/GATE_B_REMAINING.md). Remove its obsolete undefined-identifiers checklist item; real signed-pair and receiver acceptance remain DR-02 and other Gate B items. GAP-31/32/47 are narrowed to actual provider, source and hosted/signed qualification, not closed wholesale.
- Actual no-input report at this code emits all 19 blocked DR IDs, OWNER_REVIEW_REQUIRED and signing_enabled=false, exit2; retained artifact SHA256 `6ef7cb8c507303c1cac99ea022cc67360f4feb131137eb1d3f90fa5beb77433e`. This is an inventory, not missing evidence being marked passed. Current-wallet cap review, real source/recorded routes, native tracing, signed rounds, hosted drills and release CI are **NOT RUN** in this machine.
- All available PR heads and outstanding handoffs are recorded in [GATE_B_REMAINING.md](../build/GATE_B_REMAINING.md). After API connectivity recovered, all 85 PR descriptions and submitted-review events were fetched; every API head matched the Git inventory. Live issue discussions #27/#30/#32/#33/#36/#44/#92/#106/#127/#138/#142/#146/#150 were inspected. No later #27/#44 approval was found: available records still require the owner decisions. The current-input/artifact question remains unanswered. A technical #27 profile review is prepared in SIGNING_LIFETIME_PROPOSAL.md without attributing owner sign-off or changing the lifetime. No AWS/host/key/funding action, provider call, ai-seeds upload or real transaction was performed. Native Git read/push and GitHub API read work. The saved api.github.com network addition remains draft configuration; publication is not claimed.

### GB-RW2 — current integration mirror bundle (prospective)

The pre-trading checklist's Gate B mirror-bundle line is actionable with the existing authenticated Keegan4 mirror (repository permissions verified, no credential values read). Build reviewed integration `0672fb8d51056702c1d9e05450b422072bcb3138` on a new mirror branch `codex/gate-b-release-20261017`; preserve existing branches and use no force push. It contains PR130/144/148/149/153/131, and the registered-source manifest logic is already integrated. Criteria: dispatch the existing Runtime acceptance workflow once, require all runtime/infrastructure/host-bundle jobs to pass on that exact SHA, download the host-bundle artifact, verify the bundle sidecar checksum and the CI-built external/embedded manifest bytes, and retain run ID, artifact identity and both hashes. No AWS/upload/provisioning, settings/permissions edits, source promotion or signing. A later adopted source change requires a new build; this is not Gate B acceptance. Push this record before dispatch. Record blocked/failed CI distinctly rather than treating a queued workflow as success.

### GB-RW2 result — CI passed, artifact verification blocked

Criteria were pushed at `e38afb0` before creating the new mirror branch and
dispatching workflow385777152 once. [Run39030800352](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39030800352)
completed SUCCESS at 2026-10-17T12:05:47Z on the exact reviewed integration
`0672fb8d51056702c1d9e05450b422072bcb3138`. All four jobs passed: Terraform
aws/bootstrap, runtime (Python3.12.15/PostgreSQL14.24, systemd, demo, Docker),
and host-bundle (both Amazon Linux roles). This does not test unmerged PR155.

Artifact12099524179, `larp-bundle-x86_64`, 98,397,459 bytes, is retained until
2027-01-15; GitHub reports archive digest
`sha256:0a2b764f848239d529f68fd60f40cf64134ee0a547b8e86909153b12a95fd782`.
That is not a locally verified bundle or manifest hash. Two authenticated
downloads were refused by the cloud egress policy at GitHub's artifact-storage
hostname. The environment draft now preserves existing rules and adds
`productionresultssa9.blob.core.windows.net`; revision4 saving is confirmed,
but review/save and publication are required and application is not claimed.
Sidecar checksum, external/embedded manifest byte comparison, and retaining
both file hashes remain BLOCKED. The complete GB-RW2 pass criteria are not met.
Public metadata is retained in
[gate-b-mirror-build-20261017.json](../build/evidence/gate-b-mirror-build-20261017.json).
No artifact was uploaded to AWS, no host was provisioned and nobody was messaged.

### GB-RW1 publication / AWS access clarification

[PR155](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/155)
targets integration with the cap checker, blocked-check CLI summary and remaining-work audit.
Its organization Actions run [39030940212](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/39030940212)
ran no steps; the runtime annotation retains the account-payment/spending-limit refusal.
The passing local results above remain the verification of this code; the separate
GB-RW2 mirror release is reviewed integration, not this unmerged PR.

The user asked whether this session can access their AWS account. A metadata-only
recheck found zero profiles in both injected AWS config files, no environment,
web-identity or container credential binding, and boto3 ProfileNotFound. No account
lookup was attempted from an email address; email alone grants no AWS access.
AWS/host work remains with the checklist's authenticated AWS owner, Yao Zhu.

## GB-20261015 — Gate B implementation (prospective)

User requests a new Gate B PR into `codex/system-testing-20261012`, and confirms using the existing build documents. Base target `0820b0dd87219cb6b96f2ede34051129fab9f49c`; carry unmerged PR70 prerequisite tree `9a14d6e4fc30387feb82be7923d479f71deb1f46` without merging either PR into the target. Branch `codex/gate-b-20261015`, worktree `/private/tmp/larp-gate-b-20261015`. Existing C baseline: 1303 passed, 7 skipped, 1 known D legacy-export expected failure, 1615 subtests (IDEA-049-C C-RESULT-007); this is recorded prior evidence, not a new run.

Scope: build Gate B's repository-side execution evidence and native-gas settlement, following DEPLOYMENT_BUILD DR01–06/08–10/13–14/16/19 plus Gate A prerequisites; existing prompts 06/09 and W04/W08. User explicitly accepts keeping real signing, broadcasts and AWS activation gated. No registered wallet key or AI_SEEDS_SECRET, ai-seeds upload, personal funding, cloud change or organiser contact. Stay in C's code/tests/config and this existing record; shared-doc edits are requested from Keegan. No new experiment ID or frozen interface is invented.

Pass criteria before new tests or code runs:

1. **GB-NATIVE:** a transaction-specific Geth `prestateTracer` diff, explicitly enabled only for a qualified read-only provider, is bracketed by matching canonical/finalized receipt proofs. Wallet identity, nonce, original payload, receipt gas and trace pre/post balances must bind. Native received = transaction-local wallet balance delta + actual gas paid; whole-block balances cannot substitute. Success uses exact USDT debit/minimum output and the real I4/accounting validators, leaves stock slots untouched, and applies once. Missing/malformed trace, wrong hash/wallet, reorg, insufficient output, wrong exact input or unsupported units refuse. Reverts and approvals remain gas-only. Preserve raw-chain amounts in evidence and explicit durable BNB accounting scale; no guessed scale or rounding that changes a balance. Prefer native 18-decimal ledger for Gate B, otherwise reject amounts that cannot be represented exactly. No router/Executor capability is enabled by this proof.
2. **GB-CHAIN:** committed read-only CLI captures chain56, canonical/finalized block identity, wallet balance at that block, latest/pending nonce and router bytecode hash. Recheck block identity; wrong chain, reorg, malformed/absent evidence or native balance zero does not become READY. Fixed method allowlist has no submission/key/ai-seeds path. No registered keys or API secrets are read. Optional real measurements use the user-provided public address only, after commit/push, with UTC times, provider and external artifact hashes recorded. Public RPC availability/terms are checked against primary BNB docs; no production service is silently enabled.
3. **GB-REPORT:** an offline Gate B report evaluates hash-pinned external evidence and actual existing profile/initial-state validators, records every required DR and prior Gate A dependency, and refuses missing/stale/mismatched wallet/build/chain evidence. It distinguishes implemented capabilities, read-only observations and required host/signed rehearsal acceptance. A synthetic fixture cannot mark real Gate B accepted. Current unavailable router/first-gas/host and three-day/weekend evidence remains explicit. The command cannot start services, read keys, sign, broadcast, call ai-seeds or operate AWS.
4. Add requirement tests, commit/push before running, then commit/push repairs before retest. Real PostgreSQL for durable observation/replay tests; fakes only at external boundaries. Run focused, full Python3.12/PostgreSQL14.24 and exact-branch Linux CI; record skips/known D expected failure without treating it as fixed. Open one new Gate B PR targeting the integration branch; preserve PR70 provenance and dependency.

Primary-source investigation: [LiquidMesh Quote API](https://docs.liquidmesh.io/docs/quote-api) describes generated router calldata but supplies no attributable ABI for the observed chain56 router on that page. BscScan and Sourcify retrievals for `0xB44446b0c8E56988c34f7Ff73Ae904982b5FdDA5` were inaccessible via browsing; no verified ABI obtained and no guessed selector is used. [Geth built-in tracers](https://geth.ethereum.org/docs/developers/evm-tracing/built-in-tracers#prestatetracer) documents per-transaction pre/post state differences and omitted unchanged post fields; this is trusted-provider execution evidence, not a cryptographic state proof or proof of BSC provider support. Production qualification remains pending.

GB-NATIVE red at pushed `80055bf`: 8 failures (including three missing-method subcases), 4 passed, 8 subtests; SHA-256 `bc95e2a69f0ef261472f33d240393470c39526f4968bc6c1240e19d605d6729f`. Implementation `2315b59`: native, settlement, RPC and real accounting consumer subset **50 passed / 19 subtests**, 0.51s; log `/private/tmp/larp-gate-b-20261015-native-green.log`, SHA-256 `d1919ff6ab5d155863726c01cbe645d211ddfa815c6e597435bfdd3cffb28f24`. Additional real-PG plan-scale/durable event proof published at `b03f4cc`, red before integration: **1 failed**, missing PlanValuation.bnb_decimals, SHA-256 `3a0c0911347b35e4d0f3d0f350418eabd947826b33722de850485d58b015a6c9`. Production composition now supplies the durable plan's scale as well as its valuation. These are existing I4 accounting units/fields; no consumer validator or policy is changed. Native tracing remains default-off and does not bypass the Executor/decoder.

GB-NATIVE persisted-scale green at pushed `921e108`: **57 passed / 27 subtests**, 0.78s, `/private/tmp/larp-gate-b-20261015-native-pg-green.log`, SHA-256 `9600e12ae344d34cbde31a47f532702b1a701748829d2454a86012a844eefd9c`. Includes real PostgreSQL observation persistence/replay and the composition boundary; no real signatures or chain transactions.

GB-CHAIN/REPORT tests published at `095f48a` were red (10 failed, 1 passed including missing-module subcases), SHA-256 `a8d6128d3aa3d9117bd80bd21ff68afd4144fbfeccd0249d7368197d3b12041c`. Implementation `6500619`: **8 passed / 7 subtests**, 0.09s, SHA-256 `28e8d53bc155f571707873c77e4181bce38963ba3e2351c96edcad8391648ff4`. Additional adversarial tests published at `9760510`: **2 failed, 20 passed / 20 subtests**, 0.37s, SHA-256 `687c751d54d22f78f8b5f025724df47119efc41a97d139ba84d8f82f7ccbb17c`: non-string native proof source and malformed direct trace hash were accepted at their respective boundaries. Repairs enforce both before subsequent tests. Exact USDT underpayment, correct/mismatched public chain snapshots and actual initial-projection/ledger checks are also covered. Report input validation is deliberately partial evidence, not whole-DR acceptance; no ready flag can enable execution.

GB-20261015 verification at pushed `86f3ec66b7b98b3fb7bd2b5f6662167e550d0de9`:

- Full Python 3.12.14 / disposable PostgreSQL 14.24: **1323 passed, 7 skipped, 1 xfailed, 1637 subtests**, 156.55s. +20 passing tests/+22 subtests versus the recorded PR70 baseline. External log `/private/tmp/larp-gate-b-20261015-full.log`, SHA-256 `c287f6da4dc3cf3d8d51670ef9164498c0d36906161215c0f80e8e9987a73da7`. Includes the repaired source/hash negative cases and actual PostgreSQL native replay. Existing environment/external-artifact skips and D legacy-export expected failure remain; suite success does not close that P0.
- Exact `tools/system_test.py:SYSTEM_CASES` through pytest with its own `GUARD` installed as external `sitecustomize.py`, sanitized environment and disposable local DB: **112 passed / 70 subtests**, 31.54s; `/private/tmp/larp-gate-b-20261015-system/system.log`, SHA-256 `5594fbac4c684315249f744fbed98a8c12e7c2fadd8edd87a05e2c19294976cd`. This is the system case list, not a SystemTestReport/runner PASS: the runner does not allow this feature branch name. No integration-prefix alias or D-owned runner change was made. Linux demo/systemd/host-bundle evidence on this new tree remains pending.
- [PR74](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/74), base `codex/system-testing-20261012`, head `codex/gate-b-20261015`. [Exact-head dispatch 38701248657](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38701248657) and PR run 38701244815 could not start jobs. GitHub annotation: “The job was not started because recent account payments have failed or your spending limit needs to be increased.” No steps executed; no exact-checkout/Linux acceptance is claimed. Account owner resolves billing/spending limit, then Keegan reruns the workflow and reviews the final integrated build. No billing/account setting was changed here.
- Real read-only probe from `86f3ec6`, **2026-10-15T07:48:55.676Z** observation start, command `python -m larp.execution_live.gate_b probe-chain --rpc-url https://bsc-dataseed.bnbchain.org --source-id bnb-public-mainnet --wallet 0x62B8ed6C1b3BCAe61d9bFA5551Dfd77B6E7BD479 --router 0xB44446b0c8E56988c34f7Ff73Ae904982b5FdDA5 --artifact-root /private/tmp/larp-gate-b-20261015-chain`. This endpoint is listed in the [official BNB endpoint documentation](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/); it is not automatically approved for production. Chain56 canonical finalized block **127749367**, hash `0x35f65c8b526bda15007e387ac57b3eb6d8704c6d48c0088bac0567d52ab575e7`; native balance **0 wei**, latest/pending nonce **0/0**, router bytecode **180 bytes**, SHA-256 `678b647bfc7b65b4036969469d160aa275ee2b9bef20c30e124ae1c2519648f1`. Result artifact `533133fc95a951b124858fab485ea8e2425e9526c942d3a4eaa3fb7c2375f101` plus nine structured RPC artifacts retained outside Git. Exit 2, `FIRST_BNB_REQUIRED`, `signing_enabled=false`. Probe stdout log SHA-256 `fd25d763413700e09efb8fecbfb0cac2a6f9b7a39d6c2b7171c84b288b770225`. This resolves the earlier API `NO_NATIVE_ENTRY` ambiguity only at this measured block; it is not a current funding attestation for a later signing time. No native trace, ABI/proxy qualification or full-portfolio balance reconciliation occurred.
- Public offline inventory command `python -m larp.execution_live.gate_b report --artifact-root /private/tmp/larp-gate-b-20261015-report` produced artifact `67030a9a409677a32f0ed6fcfac1d3d0b0454b3aadd4cad121aed4f54b87c04f`, status BLOCKED, exit2. It inventories all 19 required DR items, no credentials read.
- Existing finite API-only weekend collector PID58913 remains running and untouched. At 07:49 UTC, six cycle artifacts were present; latest completion `2026-10-15T07:37:29.129Z`, ten pairs, artifact `2c08f9066d8188d08dfaa2650d9817e43beb4ad813b8f2f8f0a237cc65b00984`. Actual gaps, multi-day/weekend coverage and the cost-summary bridge remain unaccepted; Isaac verifies the retained corpus after the scheduled Oct18 SGT end, rather than inferring coverage from process uptime.

Upstream advanced during verification: A/B review PRs #68/#65 landed at target `ba4ff9068ff70abe9e920d3c3aa5677949845a14`; PR70 advanced to `7d4d8438129df9c521ddb098ff2f2931984961ae` (equivalent Base64 private-response reflections). Merge both normally into this PR, preserve their provenance, push before rerunning the full/system suites. The prior counts above apply to the earlier tested tree, not this new integrated result.

**Final integrated repository verification** at pushed `9b06237978489bcd22c3769027ec71eb96c7dcc5` (contains target `ba4ff90` and PR70 `7d4d843`): full suite **1394 passed, 7 skipped, 1 xfailed, 1762 subtests**, 172.57s; `/private/tmp/larp-gate-b-20261015-final/full.log`, SHA-256 `45173ffb7735f9eec88c35ca20d652a0bc39603c41a1ea69817a7fcc756ec6a4`. System case list with repository network guard: **112 passed / 70 subtests**, 32.73s; `/private/tmp/larp-gate-b-20261015-final/system.log`, SHA-256 `9336e6611a37441643b7835a05e199a366f763fe477f667a2ba42be15d39c373`. The +71 passing tests/+125 subtests since the earlier Gate B run are the refreshed upstream A/B/C integration, not additional Gate B tests. `pip check` and `git diff --check` pass. Seven existing environment/external-artifact skips and D's known legacy-export expected failure remain. Latest integrated [PR CI 38701886377](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38701886377) also ran no steps, with the same account billing/spending-limit annotation; no remote acceptance is claimed. Subsequent completion commit is documentation only. Original IDE workspace now tracks the latest `codex/system-testing-20261012`; Gate B implementation remains on its separate clean PR worktree, without changing or merging the target. Remove only this task's disposable `larp-gate-b-postgres-20261015` container after verification; preserve the separate finite read-only collector. **Repository-side implementation delivered for review; Gate B signing acceptance remains BLOCKED.**

**PR74 review follow-up (2026-10-15, Yao via Claude):** (1) Keegan's blocking thread r4280736991: `7d4d843` alone lets a prefixed `signed_<base64>` echo reach stored `Web3Observation.v1` artifacts. Fixed by an ordinary merge of PR70 head `150bf9d` (contains `d868e64`). (2) Target advanced to `5c1c9c8` (IDEA-054 / PR73); merged normally, and the LEDGER row conflict was resolved by keeping both rows plus PR70's newer IDEA-049-C row. (3) Keegan's optional thread r4280738368: the native fill now refuses `payload.value != 0`, because `received = Δbalance + gas` holds only when no BNB is sent. New test `test_gb_native_fill_refuses_bnb_sent_with_swap` was red without the guard and green with it. Full suite on the merged tree (local Python 3.12.3 / PostgreSQL 16, not the CI pins): **1402 passed, 7 skipped, 1 xfailed, 1768 subtests**. The org repo's hosted CI is still blocked by Actions billing, so the same head was run in Yao's mirror instead: [larp-ci-mirror run 38710241514](https://github.com/Cookiemunchrr/larp-ci-mirror/actions/runs/38710241514) (pull_request into the identical base `5c1c9c8`) on `524e263` is **green on all four jobs**: Terraform aws/bootstrap; runtime pytest on Python 3.12.15 / PostgreSQL 14.24 plus real systemd, the offline demo and the Docker build/run; and the x86_64 host bundle. This is mirror evidence, not org-repo CI.

**PR74 merged (2026-10-15, Yao via Claude):** the target moved to `21ee21c` (PRs #69, #70) and then to `2f155fb` (PRs #71, #72). Both were merged into this branch with normal merge commits, `3c2b0ce` and `aa16d3f`. Two conflicts:
- The `docs/LEDGER.md` rows: the target's newer rows were kept. This branch's only ledger change, the IDEA-054 row, was already in the target.
- The `larp/execution_live/chain.py` imports: both `hashlib` and #71's `http.client` were kept.

PR74 was merged as `e5db681`. The integrated tree was checked locally before the merge (IDEA-049 WR-L "Merged"). CI on mirror, commit `e5db681`, [run 38745005867](https://github.com/Cookiemunchrr/larp-ci-mirror/actions/runs/38745005867): all four jobs PASS (runtime: 1422 passed, 4 skipped, 1 xfailed, 2059 subtests, plus real-systemd 3 passed/5 subtests, demo and Docker smoke test; host bundle; Terraform `deploy/aws` and `deploy/bootstrap`). The Gate B acceptance blockers above are unchanged: signing, broadcasts and AWS activation stay gated.

Remaining owner actions / shared-document edits requested from Keegan (no whole GAP completed):

- **Isaac + Keegan, DR02/03/06, GAP29/31/49:** preserve decoder/signing gates; qualify actual router/proxy/nested ABI/deadlines and real provider tracing, reconcile fresh nonce/full balances, solve first BNB through the agreed team process, then conduct the reviewed logged dev approve/swap/top-up. Native settlement is now implemented/tested; production tracing support and signed acceptance are not. Update EXP-005 verdict to record the canonical zero-BNB/nonce/finalized/code snapshot above without promoting swap/signing capability. Narrow the native-settlement backlog to remaining provider/driver/real acceptance, retaining all unresolved dependencies.
- **Isaac + Keith, DR01/08/09:** verify actual collector coverage, produce real sourced QuoteCostSummary inputs (gas/fees/TTL cannot be inferred from sequential quotes), freeze/review the rehearsal profile and use exact 18-decimal native accounting; include actual token-session evidence. Record decisions on live inputs and lifetimes with B/D before activation.
- **Keegan + account owner, DR04/05/07/13/15/16/18/19/20:** restore Actions availability, rerun exact head and merged-branch CI, review PR70/74, integrate through normal merges (2026-10-15: PR70 and PR74 merged, merged-branch CI ran on the mirror; see above), complete durable ACK/host/recovery/restore/manifest/replay acceptance and D's legacy signed-state export P0. Record cloud activation separately; none is authorized by this report.
- **Keegan shared index/backlog:** update IDEA-039's existing row to “Gate B repository native settlement and read-only evidence tools; PR74; engineering verified locally, live/CI acceptance blocked”; append these findings to the relevant GAP29/31/49/65/67 and IDEA-042 DR items with the same owners. Keep incomplete items, including whole first-gas/top-up readiness. No fully completed checklist item was found for removal in this scope. (2026-10-15: the IDEA-039 row is updated to show PR74 merged.)

- Owner Isaac; reviewer Keegan. Prompt `docs/build/06-execution-live.prompt.txt` and IDEA-038 govern scope.
- Baseline: foundation `bd3f69a`, merged into `codex/deploy-execution` by `4d1fde2`. PR12 is merged. Earlier implementation commits were reverted; they provide reusable source, not current acceptance evidence.
- Status: implementation in progress. No live signing, broadcast or official round logging is enabled by this record.

## Preregistered acceptance

Commit and push this record and code before execution. Record PASS / FAIL / NOT RUN / INCONCLUSIVE and commit SHA for each run.

1. Existing foundation, W04 and W08 suites remain passing; network-free component fixtures exercise malformed quantities, credential conflicts, immutable artifacts and exact API signing.
2. I1/I2: recorded real responses, hashed outside Git, pass the actual consumer `market_view`; executable quote evidence must pass `_quote_at_cap`. Missing router decode, expiry, fee or exact gas proof exposes measurements only. Never invent these fields or backdate observations. USDT planner units (6 decimals) map exactly to BSC units (18 decimals).
3. Quote collection: five names, about 40 USDT, hourly or faster; retain availability, impact, round-trip quoted cost, latency, errors and exact simulation failures. Stop on auth/compliance/rate-limit failures. Summary by Oct 19; three days including a weekend remains a time-dependent requirement.
4. Signer: isolated-host configuration, one secret source, matching wallet; immutable signed-byte registry and current fencing/authorization before release. Mutation and restart tests prove exact transaction bytes and hash/sender binding with ephemeral test keys only.
5. Nonce/finality: chain 56, latest/pending counts, transaction/receipt identity, canonical blocks and verified finalized head. Missing or inconsistent evidence keeps the barrier. Replacement disabled.
6. I3/I4: consume commands via `PostgresStore.command`; enforce identity, expiry and exact input/receive scales. Broadcast facts never reach accounting. Final receipt facts contain actual transfer/gas evidence and pass `advance_accounting`; repeated observations are idempotent.
7. Production execution and signer-registry storage require Keegan's fenced atomic PostgreSQL boundary. Crash tests before sign, after sign, after broadcast and after receipt must pass in CI before live activation; SQLite is not production evidence.
8. Check BNB read-only first. A missing/zero balance blocks transactions. USDT→native BNB is allowed only for explicit GAS_TOP_UP intents; final-wallet run identity, nonce and audit directories stay separate.
9. One minimum-size approve/swap with durable decision and official round logs is NOT RUN until router/chain, first gas, production storage, manifest and audit gates pass.

## I3 mapping and integration requests

`command_id = payload.intent_id`; command/payload `decision_id` and `expires_ms` must agree. External run, wallet and registered version come from the trusted store/run configuration. Reservation identity is the intent ID. BUY pays USDT and converts planner `pay_units × 10^12`; SELL pays token units unchanged and converts USDT minimum receive `× 10^12`. `receive_decimals` must match the consumer convention. Router and gas caps are current risk-authorized inputs, never API defaults. Explicit GAS_TOP_UP buys native BNB only.

Keegan owns shared docs/locks/index/backlog/migrations: retain the existing IDEA-039 index reservation; record requested PostgreSQL execution CAS/event storage, restricted immutable signer registry and fenced release/settlement integration. Coordinate I1/I2/I7 with Keith; no owner agreement is assumed from local fixtures. EXP-005 verdict updates are requested through the shared-document owner; no capability is promoted by synthetic tests.

## Open dependencies

- Isaac: verified router ABI/implementation, nested RFQ expiry/economics and decoder; EXP-005 currently inconclusive.
- Team/Keegan: permitted RPC endpoint and manifest entry, signer host runtime secrets, first BNB, production storage/release/audit gates.
- Keith: session-builder I2 validator, live profile/impact/gas values, gas-top-up accounting contract.
- Isaac: start quote measurements and record summaries and coverage; an initial cycle cannot satisfy multi-day acceptance.

## 2026-10-12 SGT implementation and evidence

Implementation `fc0b3ef` was pushed before all runs. [Draft PR14](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/14) targets `codex/engine-foundation`; no merge to main or live activation.

- PASS: targeted 98 tests, including foundation/W04/W08, actual market/planner validators on synthetic proof fixtures and real recorded Binance responses, receipt facts through actual accounting, and real EVM cryptography using ephemeral test keys.
- PASS: full local pytest in a temporary environment using the CI lock: 534 tests, 764 subtests; 90 skips because disposable PostgreSQL and Linux isolation are unavailable locally. Earlier full runs in base/Conda Python failed due missing numpy/AWS test dependencies; no code defect was inferred from those environment failures.
- PASS: [CI on fc0b3ef](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38156124100), all three checks. PostgreSQL-backed run: 621 tests, 780 subtests, 3 skips (external recorded responses and signer dependency). The four new PostgreSQL tests cover pre-sign/post-sign restart, post-broadcast/post-receipt restart, wallet barrier/stale CAS, and registry restart/identity. These are restart simulations over real PostgreSQL and fake venue/signatures; they do not establish power-loss, multi-host or actual chain recovery.
- INCONCLUSIVE: balance artifact `2b75d769b93396aeb8a091dadf65d35d793259f87dfbf7d28af51ee8d5abe683` in ignored `data/execution-live/`: no native BNB entry returned. Per the captured kit zero balances are omitted. No canonical chain balance was collected; first gas remains unresolved and transactions are blocked.
- PASS for read-only collection, not readiness: 40-USDT cycle `ef42ceccbf9963d45f71169adaa871aab1103062e880052e3b5bc368aaa47749`, 2026-10-11 16:33:30.512–16:33:47.993 UTC. All five token/underlying states open; every exact swap gas simulation unavailable. Raw response bytes are retained in private hash-addressed artifacts unless credentials are reflected, in which case only redacted parsed data and the response hash are stored.

| Name | Sequential quoted round-trip bp | Buy impact bp | Sell impact bp |
|---|---:|---:|---:|
| NVDAB | 2.0609 | 0.1763 | 0 |
| GOOGLB | 8.1549 | 0.0408 | 0.0408 |
| SKHYB | -3.3239 | 0.1697 | 0 |
| TSLAB | 7.7633 | 0.0579 | 0.0507 |
| MSFTB | 22.8609 | 0 | 0 |

One pair per name is not a median, spread estimate or opportunity/profit signal: the prices can move between the two calls. Gas is separate and unavailable; these numbers do not satisfy B4's total-cost criterion.

Router search for the exact observed address did not produce a verified ABI. Official [BNB RPC documentation](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/bsc-api-list/) and [BNB node RPC reference](https://github.com/bnb-chain/bsc/blob/master/rpc/json-rpc-api.md) describe finality methods; provider availability and this wallet's nonce/finality evidence remain NOT RUN pending service configuration. Same-nonce replacement stays disabled.

## Integration handoff details and remaining acceptance

- PostgreSQL extension: `larp/execution_live/store.py:SCHEMA` proposes `execution_records` (restricted state/CAS), `execution_journal` (public events/hash chain) and `execution_signatures` (restricted immutable attempt bytes). Atomic commits lock W02's run and compare epoch/state version. The wallet barrier is across economic intents; production startup does not install tables. Keegan must adopt migrations, role grants, backup/restore coverage and atomic command/reservation/observation/outbox wiring. Local tests cannot count as agreement from Keegan.
- Signer requires current authorization and checks fencing before returning persisted bytes. Keegan must add eth-account and its pinned transitives to the deployment/CI signer dependency set; existing full-project requirements already pin eth-account. Local signer tests pass, CI presently skips them.
- I4 broadcasts are stable audit-only events. `ReceiptFacts` uses a durable W04 finalization timestamp and a persisted attempt-specific BNB valuation; the runtime must persist/publicize identical bytes on retry before advancing. Settlement reads actual ERC20 Transfer logs and receipt gas, rejects quantities unrepresentable in the accounting money scale, and includes all USDT transfers in net cash without double-booking an assumed quote fee.
- Native BNB top-up intent validation exists, but actual native receipt/balance-delta settlement and Keith's gas accounting are still needed. No gas conversion is run while first BNB is unresolved.
- I2 supplies raw candle rows and UTC reported timestamps with hashes. Open/close semantics remain explicitly unverified; Keith must establish those semantics in the real session-builder validator. Null open/close values are flagged unresolved fields, not assumed data.
- Live Executor bundles remain rejected until route/expiry and production release gates are evidenced. Development approve/swap acceptance remains NOT RUN. No real wallet transaction signing, broadcasts, official ai-seeds logs, paid services or organiser messages occurred.
- Logger long-running operation and multi-day/weekend summary remain pending; subsequent dated results below record them. The default balance/one-cycle CLI does not start a background logger.

### Follow-up preregistration: actual process death

Additional PostgreSQL acceptance: child processes exit immediately before signing, after restricted signer-registry persistence but before W04 persistence, after a possible fake broadcast but before response persistence, and after receipt reading but before final-state persistence. Restart must recover the same signature/attempt, retain possible-send state, never retransmit, and finalize only from subsequent positive evidence. Both approve and swap paths are covered. The child only uses the disposable CI database and unbroadcastable fake signatures. This strengthens restart evidence; it is not a power-loss or chain test. Commit/push before running.

### Collector operation / follow-up verification

The read-only hourly collector was launched locally on pushed `cbf4440`, PID 96699. First cycle 2026-10-11 16:42:05.187–16:42:24.708 UTC, artifact `2883aca5c9ad96e099bd8a7d81de84f4a9428a9ea731f3552b2b5a1e5ebbb343`. All five names returned 300 raw hourly candles. Its private PID/log files are ignored under `data/execution-live/`; it has no signer or ai-seeds client. This laptop must stay awake and connected for coverage; Keegan must move/supervise collection on the deployment host for reliable multi-day evidence. Multi-day/weekend acceptance remains open.

Local `cbf4440` full pytest: PASS, 538 tests, 767 subtests, 90 skips; raw recorded-response validation and ephemeral cryptographic tests enabled. CI/result hashes for the latest revision are recorded after completion.

`cbf4440` CI: [PASS](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38156516334), 624 tests, 780 subtests, 4 skips (3 signer tests due to missing CI dependency plus external recorded responses). All three checks pass.

Additional receipt retry criterion: because finalized head advances between reads, preserve the first successful final observation and its proof in an immutable PostgreSQL `execution_observations` row. A retry must return those exact stored bytes before any new chain/valuation I/O. Changed bytes under the same event ID are rejected. This extension also needs Keegan's migration/role/outbox integration. A synthetic callback test and real PostgreSQL immutability test are preregistered before execution.

### Final verification for this implementation stage

- `ff945f6` local: PASS, 539 tests, 767 subtests, 93 skips (including the seven PostgreSQL tests, unavailable locally). External recorded-response and ephemeral signer tests are enabled and passing.
- [`ff945f6` CI](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38156901734): PASS, 628 tests, 780 subtests, 4 skips, all three checks green. Both approve and swap process-death fixtures reached their intended exit codes and recovered from PostgreSQL state without re-signing or rebroadcasting. Final observations retain their first proof across restart and reject changed payloads.
- Scope check: only Isaac's exclusive paths plus IDEA-039 changed. Shared docs, migrations, dependency locks, official kit and vendor copies untouched. This remains a draft implementation milestone, not deployment or live-trading acceptance.

| Prompt deliverable | Implemented / verified | Remaining owner / dependency |
|---|---|---|
| 1 · I1/I2 market | Web3 read transport; real metadata/status/price responses; exact unit conversion; actual consumer validation; raw candles and hashes | Isaac: verified route/expiry/fee/gas proof for executable quotes. Keith: candle open/close semantics and actual session-builder validation. |
| 2 · Logger | Running hourly locally; two successful 40-USDT cycles for five names; automatic summaries; 300 hourly candles/name | Isaac: multi-day/weekend coverage and Oct 19 summary. Keegan: reliable host supervision. |
| 3 · Venue | Quote/unsigned approve/exact gas request adapters, verified-decoder boundary, matching vendor/router checks | Isaac: attributable router decoder. Keegan/Isaac: gated real broadcast/release and integrated W04 live activation. |
| 4 · Signer/chain | Exact legacy EVM signature verification, one secret source, isolated-host/address checks, durable fenced PostgreSQL registry; synthetic canonical nonce/finality tests | Team: RPC configuration and signer host. Isaac: real provider/nonce/finality evidence. Keegan: signer role/secret provisioning and CI/deployment dependency lock. |
| 5 · Execution service | Store.command mapping; W04 CAS/journal/registry adapter; replayable broadcast/final facts; actual accounting validator; PostgreSQL process-death tests | Keegan: adopt schema/migration/roles/restore coverage; atomically wire commands, reservations, ordered reducer, final observations and official audit outbox. Isaac/Keegan: integration review and live gates. |
| 6 · Gas | Balance API checked; explicit USDT→native BNB validation | Team: first BNB absent/unproved. Keith/Isaac: top-up planner, native receipt/balance accounting and reserve floor. |
| 7 · Wallet transition | Separate wallet/run audit paths and wallet-wide nonce namespace; mismatch rejection tests | Keegan/Isaac: wire configuration through actual host release and rehearse the final-wallet switch. |

Second cycle summary at 16:42:24.708 UTC: two pairs/name; all observed token/underlying states open. Sequential round-trip median bp (range): NVDAB 0.4467 (-1.1675–2.0609), GOOGLB 2.3439 (-3.4672–8.1549), SKHYB -2.2610 (-3.3239–-1.1981), TSLAB 8.1148 (7.7633–8.4662), MSFTB 19.9120 (16.9631–22.8609). Negative pairs are retained as measurement evidence, not treated as arbitrage. Two samples cannot establish stable spreads, B4 values or profitability; exact gas remains unavailable.

No live transaction, official log or production deployment was run. The next live-capability work is RPC/provider evidence plus router ABI/expiry resolution; the next integration work is Keegan's shared storage/release/audit wiring. The RPC configuration question remains unanswered in this session. No permission to choose a paid service or send organiser messages is assumed.

## PR14 Keegan review corrections — preregistered 2026-10-12

B1/B2/B3 and S1–S5 accepted. Pass criteria: fractional SELL proceeds settle conservatively with exact raw cash/dust retained; all credential parsing exceptions are sanitized; journal commits do not invalidate execution authority; takeover recovers existing bytes through the service without blind re-signing or broadcast. Unbroadcast aborts require atomic execution CAS/no-possible-send evidence and registry/release revocation, never receipt absence. Current projection CAS and fresh risk/nonce/market checks remain independent of stable execution fencing.

Execution authority uses ownership epoch as the initial dedicated authority version: takeover changes it; quarantine/HALT blocks release through the store. Explicit authority revocation must take over or quarantine. Do not reuse journal version as execution authority. Keegan can replace the epoch-derived version with a dedicated column without changing the semantic contract. Production live bundles remain disabled pending his release integration.

Additional criteria: pending/missing receipts are not identity mismatches; dependency failures have sanitized persisted reasons and durable backoff; exhausted fast probes transition to slower periodic reconciliation while retaining the wallet barrier; prepare budgets are per step; I3 enforces an explicit USDT cap; stale receipt producers cannot borrow current ownership; tests cover service publication crashes, takeover, SELL and real ephemeral signing against PostgreSQL. Consumer contracts from current strategy branch govern receipt/provenance/candle fields and BNB scaling. Unknown cost/timestamp semantics remain explicit and blocked, never filled with invented values. Test changes and code are committed/pushed before any run. Shared migrations/locks/backlog remain Keegan's; any required integration edits are recorded here.

### 2026-10-12 I4 cross-owner remediation criteria (IDEA-043)

Actual runtime validator on PR13 must accept produced broadcast and final facts: lowercase approve/swap step, durable observation timestamp, no settlement field on audit-only broadcasts, flat canonical block hash, explicit round_terminal boolean. Round completion is a supplied consumer attestation, never guessed from one intent. ABORTED with no possible swap produces NOT_SUBMITTED so reservations can release, retaining prior approval gas facts. Tests call the actual runtime validator once integrated; isolated component skips that unavailable consumer explicitly. These are interface fixes only; no live release permission. Commit/push before executing changes.

### PR14 review correction results (2026-10-12)

Review fixes and acceptance tests are pushed through `980529a`. Concurrent I4 edits (`c5508be`, IDEA-043) were retained by a normal merge; no force push or history rewriting. `SCHEMA` remains unchanged, so PR13 migration 008 does not require a DDL update for these fixes.

- B1: SELL proceeds round down to six-decimal cash; `actual_cash_chain_units` and `cash_dust_chain_units` retain exact receipt amounts. BUY exact-input checks remain strict. SELL passes both the old and actual new accounting consumers, with committed round identity.
- B2: all credential-parser exceptions are sanitized with suppressed exception context; mnemonic ValidationError regression asserts no phrase/marker in the rendered traceback.
- B3: `Gates.execution_version` separates release authority from projection `state_version`. PostgreSQL release authority is epoch-derived; projection commits still CAS `runs.version`. The service pins its own epoch/version and cannot adopt a newer controller's lease. It calls registry recovery and reauthorization before first submission after takeover. Atomic ABORTED state is the tombstone: registry issuance/lookup and `check_broadcast` reject revoked attempts. A durable possible-send record cannot be aborted/re-authorized. Signed bytes are retained, never deleted as cancellation evidence.
- S1/S2: normal pending/absent evidence is distinguished from mismatches; RPC outages persist sanitized reasons and backoff without exhausting the successful-chain-probe budget. Live venues continue slower reconciliation after the fast budget, retaining the wallet barrier. Prepare budgets reset only at final approve success; the service aborts genuinely unissued work at exhaustion. W04's direct exhaustion API still raises Blocked. Unknown market/nonce facts block signing while permitting receipt reconciliation.
- S3/S4: I3 requires an independent per-trade cap, cash/pay binding and explicit gas scale conversion. Fresh quote caps are checked again. LiveGuards obtains API market status and chain nonce; authorization facts default false. Receipt producers retain their captured lease rather than borrowing current ownership; cached facts are fenced too.
- S5/interfaces: added service takeover, registry-before-state crash, publication-loss replay, immutable NOT_SUBMITTED replay, SELL, and real ephemeral EVM signing against PostgreSQL. Runtime facts use the actual lowercase step/timestamps/round-terminal/receipt contracts. Unknown candle semantics stay raw; `session_candles` emits the actual consumer shape only with explicit OPEN semantics and evidence hash. Independent quote limits replace self-derived limits. Markets carry WEB3_OPEN_API origin and paired-quote cost provenance; unavailable costs remain null/blocked, never default zero. Negative sampled net costs receive no cost credit and the signed measurement remains recorded. Logger summaries include quote latency and effective quoted spread (sequential, fees/movement included).

Verification:
- Local PR14 `980529a`: PASS, 565 tests, 773 subtests, 100 skips (PostgreSQL/Linux and not-yet-integrated consumers unavailable locally; real recorded responses and ephemeral signer tests enabled).
- [PR14 CI on 980529a](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38228852535): PASS, 760 tests, 1068 subtests, 8 skips; all three checks green.
- Isolated validation branch `codex/pr14-review-validation` at `156fd9b`, combining runtime `6d33280`, strategy `ab3adc1` and PR14: actual adapter-consumer subset PASS locally, 57 tests + 19 subtests, 13 skips (PostgreSQL and external recordings unavailable in that worktree).
- [Isolated PostgreSQL/signer CI](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38228856478): 797 passed, 827 subtests, 1 skipped; one failure remains in Keith's already-reviewed `tests/strategy/test_live_profiles.py::test_live_cost_cap_still_blocks_without_double_counting_impact` (IDEA-042 §4.4). All execution, real PostgreSQL signer, runtime-observation and candle-consumer tests passed. Full cross-owner integration is therefore NOT PASS; this unrelated fixture is Keith's remaining item. Earlier integration failure on redacted/corrupt execution records was corrected to a sanitized Conflict; the actual backup/restore consumer now passes.
- The separate Actions dispatch initially could not complete automatic approval review (429 retry limit). Retrying through the same approval path succeeded; no approval check was bypassed.

Collector restarted on pushed `980529a`, local PID 1921. First updated cycle `0be55946e0ff7e928fb2ade110c790f53d365d30f7fb57e81d67d7e29466b51a`, 2026-10-12 09:19:25.259–09:19:51.606 UTC, all five pairs collected. Quote latencies 126–173 ms; effective quoted spread bp: NVDAB -1.5004, GOOGLB 5.3674, SKHYB -2.2570, TSLAB -1.5346, MSFTB 12.5828. These are sequential samples with price-movement noise, not profitable arbitrage evidence. Artifacts remain private and ignored.

Remaining integration requests: Keegan wires LiveGuards/epoch-derived execution authority and `check_broadcast` at the actual release boundary, uses pinned ownership in publication, and adopts NOT_SUBMITTED reservation release. HALT/revocation must quarantine or advance execution authority; ordinary journal commits must not. A future dedicated authority column may replace epoch derivation under the same interface. Keith supplies calibrated independent quote limits, actual gas/BNB scales and verified candle semantics. Confirmed first BNB, RPC/provider/router capability proof and live activation/rehearsal remain pending; no registered-wallet signatures, transactions or official logs were run by these fixes. Update the reserved IDEA-039 ledger row/backlog through Keegan; no whole shared backlog item is closed here.

## GB-CHAIN-20261016 — Gate B chain-probe gaps GB-1/GB-2 (pre-registered 2026-10-16)

These gaps came out of reviewing Gate B against Gate A's GA11 check (IDEA-058, PR #87). The user asked for the fix; Gate B is Isaac's code, so this section is for his review. The branch is `claude/gate-b-chain-gaps` from `codex/system-testing-20261012` at `7a8a246`. Nothing is signed or broadcast, and there is no AWS action.

- **GB-1, a transaction mined but not finalized.** `probe_chain` compares only the `latest` and `pending` nonces. If a wallet transaction is mined but not yet finalized, the finalized BNB still equals the old opening balance, so DR-03 and DR-06 pass. Then the transaction finalizes and changes the balances.
- **GB-2, only BNB cross-checked.** DR-06 compares only the starting BNB against the chain. USDT cash and the five bStock positions in the pinned initial state are not checked.

**Pass criteria.**
- **GB1a:** `probe_chain` also reads the wallet nonce at the finalized height and records it as `finalized_nonce`. When it differs from `latest_nonce`, the blockers include `UNFINALIZED_TRANSACTION_REQUIRES_RECONCILIATION`.
- **GB1b:** the report's DR-03 stays BLOCKED for chain evidence with a missing, non-integer or mismatched `finalized_nonce`.
- **GB2a:** `probe_chain` reads `decimals()` and `balanceOf(wallet)` for USDT and the five pinned bStocks at the finalized height. These go through `chain.Rpc`'s existing `eth_call` allowlist, between the two block-identity checks, and are recorded as `tokens`.
- **GB2b:** DR-06 stays BLOCKED unless all of these hold:
  - `cash_units` equals the chain USDT floored to micro-USDT (`units // 10**(decimals-6)`, decimals ≥ 6). This is Gate A's convention.
  - Every bStock position equals its chain units. A position must be zero when the chain balance is zero. A non-zero position needs matching decimals and units. A token with no position counts as zero, and a position not in the pinned set refuses.
- **GB-tests:** the existing Gate B tests keep passing with the fixture extended, and no `send` or `sign` method is called. A mutation of each new check is caught. The full suite shows no new failures against the base (`7a8a246`: 1546 passed, 7 skipped).

### GB-CHAIN-20261016 results (2026-10-16)

- **Order of commits:** criteria in `ade0d8c`, red tests in `a4a3096` (4 failing tests, 4 failing subtests), fix in `d4ab8be`. Two test corrections followed, after mutations survived:
  - `e7aed94`: DR-03's status is always BLOCKED pending owner acceptance, so GB1b now asserts the refusal detail.
  - `f1df6d5`: adds a `3.0` finalized-nonce case, so the integer-type check is exercised.
- **GB1a/b: PASS.**
  - `finalized_nonce` is recorded.
  - A finalized nonce behind latest adds `UNFINALIZED_TRANSACTION_REQUIRES_RECONCILIATION`.
  - DR-03 refuses a missing, mismatched or non-integer `finalized_nonce`.
- **GB2a/b: PASS.**
  - `tokens` holds USDT and all five bStocks at the finalized height, read through the existing `eth_call` allowlist.
  - DR-06 refuses all of these: a USDT difference of one micro-USDT; a bStock on chain with no ledger position; a ledger position above the chain balance; an unknown position symbol.
  - DR-06 accepts matching zero and non-zero holdings.
- **Mutations:** 7, each caught after the corrections above:
  - blocker;
  - DR-03 nonce comparison;
  - DR-06 cross-check;
  - cash comparison;
  - position comparison;
  - unknown-position check;
  - integer-type check.
- **Full suite** (PostgreSQL 16.15, Python 3.12.3): base `7a8a246` 1546 passed, 7 skipped. This branch: **1550 passed, 7 skipped, 2155 subtests, 0 failed** (+4).
- **Docs:** `config/execution/README.md` lists the new blocker and the DR-06 cross-check.
- **Compatibility:** chain evidence captured before this change has no `finalized_nonce` or `tokens`, so it now keeps DR-03 and DR-06 blocked. Re-run `probe-chain` before Gate B review.
- **Not done:** this is a repository change only. It has not run against a real BSC node, it needs Isaac's review, and mirror CI has not run.
- When this merges, remove the GB-1/GB-2 line that PR #87 adds to `docs/INCOMPLETE_WORK.md`.

## FG-01 — Isaac checklist task8: verify historical dev gas funding (2026-10-17, prospective)

Isaac supplies transaction ID/hash `0x24683de219c18cc78a2d7aeb37c94e733a6a383b1c3a58d3a403f95df7da5c55` for the earlier2USDT USDT→BNB funding action. This is input, not a verified swap. Separate branch `codex/isaac-08-dev-gas-record-20261017` from integration92fd2ad; signer key task7 remains dependent on approved caps/access. Parent106 keeps the remaining dev funding, post-final-swap capture and final-wallet steps.

Criteria before public transaction lookup / analysis:
- **FG1:** use only bounded public, read-only HTTPS RPC (BNB public primary, NodeReal fallback on lack of a read capability), at most16 method calls,20s HTTP timeout, no retries/redirect/auth bypass/keys/env/AWS/signing/broadcast/official-log action. Allowed methods: chainId, transaction/receipt, numeric/finalized block, and optional debug_traceTransaction with prestateTracer diffMode, code/storage disabled. Preserve exact responses and UTC timing/hashes outside Git at `/private/tmp/larp-isaac-dev-gas-20261017`. This does not activate a provider or qualify production native_trace.
- **FG2:** bind chain56, requested transaction hash, successful receipt, block number/hash, block timestamp and canonical identity below a finalized head; recheck identity after optional trace. Compare the involved wallet with previously user-supplied dev wallet0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479. A missing/reverted/approval-only or wrong-wallet transaction is not confirmed gas funding.
- **FG3:** derive actual USDT transfers involving that wallet from receipt logs with pinned USDT contract/Transfer signature and18decimals; separate gross outgoing/incoming/net debit and any fee classification only when attributable. Do not assume the stated2USDT is the total charged or the tx sender pays the user's fee. Verify transaction-local native credit using trace if available; do not infer BNB received from a whole-block balance delta or WBNB event alone. Missing/unsupported evidence stays INCONCLUSIVE; record independently proved fields without guessing the rest.
- **FG4:** publish only public normalized funding facts / evidence hashes in DEPLOYMENT_DAY§5 and this ledger, with source, exact units, uncertainty and finality scope. Do not treat this historical manual funding record as an agent trade/round or emit an ai-seeds log. Remove the existing placeholder row only if its fields are genuinely verified; preserve remaining dev/final/post-funding work in the live backlog. Separate PR closes only the verified historical-record slice, parent106 stays open. No application code/test or live service is run by the manual research.

### FG-01 retrieval status / FG1a protocol clarification (2026-10-17, prospective)

At pushed40e0aed, BNB public chain/transaction/receipt/finalized-head reads succeed. A mixed batch containing debug_traceTransaction is rejected in its entirety as unsupported-in-batch, including the numeric-block read. NodeReal fallback independently agrees on chain/hash/sender/success/canonical inclusion and block time2026-10-16T08:27:44Z; its standalone prestate trace returns missing trie node. Native credit is not inferred from events or block balances. Twelve RPC method calls consumed including the failed batch.

**FG1a:** allow exactly one standalone trace request to the primary, because its prior response rejects the batch protocol, not a successful trace or identical standalone request. This is a new request shape, no transient retry loop or access bypass; keep the original16-method cap and20s timeout. Recheck receipt/block after this optional request. If it also cannot supply native credit, record the fields independently verified and explicitly request further amount evidence rather than call the historical record complete. An explorer transaction page may be inspected as a separate public source.

### FG-01 partially verified historical record (2026-10-17)

Criteria40e0aed and FG1a clarificiationeaf7282 were pushed before their reads. Exactly15 RPC method calls in6 HTTPS requests, within the16-call/20s cap, no transient retry/redirect/authentication bypass. BNB public and NodeReal independently return chain56, the supplied hash, the expected dev wallet sender0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479, successful receipt and the same canonical block below their finalized heads. The receipt and numeric block were rechecked after trace attempts with unchanged identities.

**FG2 verified:** transaction0x24683de219c18cc78a2d7aeb37c94e733a6a383b1c3a58d3a403f95df7da5c55, block0x7a04e65, hash0x1983bbd3490a3bb69f7220d02c7bb218876b73caee5f1ed660d7dbbdad807b01, **2026-10-16T08:27:44Z** (16:27:44SGT), status1, nonce1, tx native value0. User attribution: MetaMask dev trial funding; this record does not prove every prior wallet activity or a current balance.

**FG3 partially verified:** pinned USDT Transfer events in both receipts and the rechecked receipt show exactly2000000000000000000raw units leaving the wallet and0 returning = **2USDT net debit** at18decimals. Do not double-count downstream transfers or classify an unproven separate USDT fee. Receipt gas188294 ×effective price60000000wei =11297640000000wei =0.00001129764BNB; this protocol gas product does not establish what the MetaMask UI charged in USDT.

**Native BNB credit INCONCLUSIVE:** primary mixed batch rejects the trace method; backup standalone trace and primary standalone trace each return missing trie node. The trace amount is not substituted by a pool/WBNB event or whole-block balance difference. BscScan transaction page is inaccessible to the browsing tool. Isaac was asked to relay the exact wallet-directed native amount from BscScan Internal Transactions, or the exact MetaMask received amount with its source. Until evidence arrives, preserve a flagged pending native-credit field and do not close the historical verification slice. No actual native_trace runtime capability is qualified or enabled by these failed traces.

Normalized public evidence `docs/build/evidence/dev-gas-funding-20261016.json`, SHA256 **6ef24da0c9147f73b49caced1e1e2a981213f1705f42ab6274f58b9e2c81a141**; raw requests/responses/headers retained outside Git at `/private/tmp/larp-isaac-dev-gas-20261017`, with exact byte hashes/times in the report. Geth prestate diff semantics checked against its [primary documentation](https://geth.ethereum.org/docs/developers/evm-tracing/built-in-tracers#prestatetracer); JSON-RPC receipt/block fields checked against [Ethereum JSON-RPC documentation](https://ethereum.org/developers/docs/apis/json-rpc/). This is trusted-provider public observation, not a cryptographic proof.

DEPLOYMENT_DAY§5 replaces only the now-known time/hash/debit placeholders and retains explicit native-credit uncertainty. GAP49 is narrowed to remaining amount evidence/dev funding/post-last-swap capture/final wallet, with source evidence here before narrowing. Validation: independent source identity/receipt/Transfer arithmetic checks and JSON/diff checks; no application tests/runtime, private key/env, AI-seeds, new swap/signing/broadcast or AWS action. Parent106 remains open; issue150's full-record criteria remain incomplete, and its PR must stay draft without a closing claim until the missing amount is evidenced.


### FG-01 U1 — attributed explorer amount completes the historical funding note (2026-10-17)

Isaac relayed the BscScan Internal Transactions entry for the same transaction: **0.002684720969362886 BNB** (2684720969362886 wei), from `0xc590175e458b83680867afd273527ff58f74c02b` to `0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479`. The recipient matches the RPC-verified sender/dev wallet; the intermediary also appears in the USDT transfer path. Source: public explorer text copied by Isaac on 2026-10-17, not an independently retrieved RPC trace. The displayed USD estimate is unused. This is gross incoming BNB, not net/current balance or proof of the MetaMask fee-token economics.

FG2 and the USDT portion of FG3 retain their prior RPC evidence. The native portion of FG3 remains RPC-INCONCLUSIVE because the trace errors above are unchanged; the exact amount is now separately evidenced by the attributed explorer entry. No missing evidence is inferred from a pool event or whole-block delta. The historical funding-note deliverable under FG4 is complete with this explicit source grade; this does not convert FG3 into a trace-verification pass or qualify runtime native_trace.

The normalized report now has status `FUNDING_RECORD_COMPLETE_WITH_ATTRIBUTED_EXPLORER_CREDIT`, `native_credit_rpc_verified: false`, and SHA256 **dd27d380f878f5d7e540e6dacc3893d9986f7acbd1bb3e8987de8a49659ddfe9**. The earlier partial-report hash remains above as historical evidence. A source-attributed transcript is preserved outside Git at `/private/tmp/larp-isaac-dev-gas-20261017/isaac-explorer-native-transfer.json`, with its byte hash in the report. DEPLOYMENT_DAY §5 now records all four historical fields. GAP49 retains remaining planned dev funding, Yao's fresh opening capture after the last manual funding swap, final-wallet funding and separate #30 native-trace/floor qualification; no entire live backlog item is fully complete for removal.

PR #151 carries `Closes #150` for the historical-record slice only; because its target is the integration branch, verify issue closure when it is merged rather than assume GitHub closes a non-default-branch merge. Parent #106 remains open. No new transaction, application test/runtime, signing/key, AWS or official-log action was performed.

Validation for U1: evidence JSON parses; exact BNB/wei and receipt gas arithmetic, recipient identity and every retained raw artifact SHA256 match; `git diff --check` passes. Documentation/evidence-only change, so no application tests were added or run.

FG-01 U1 publication: pushed `321980a`; [PR #151](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/151) is OPEN and ready for review with `Closes #150`, targeting integration. Child #150 now states the completed attributed-record scope and remains open pending merge; parent #106 now distinguishes the recorded trial from remaining Isaac funding and Yao opening capture. GitHub reports no automatic closing-issue linkage for this non-default target; verify closure at merge. Actions run [39016527481](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/39016527481), head `321980a`, runtime annotation: job did not start because recent account payments failed or spending limit needs increasing (existing #98). No CI pass or hosted acceptance claimed. Remaining source/decoder, signing-lifetime, caps approval, signer access/key placement and funding/host gates stay with their previously recorded owners.

GB-RW3 combined regression: published review head `7328e0a` includes this PR's
repaired code from `4c19ee8` and all seven other open PRs. Linux/Python3.12.14 /
PostgreSQL14.24: **1957 passed, 6 expected skips, 2931 subtests**, 326.89s, no
failures or xfails. Skips: one external recorded corpus and five opt-in systemd
checks. Full per-PR dispositions and exact heads: IDEA-049 ALLPR-20261017 on
PR158. This confirms offline engineering behavior only; current external input
files, #27/#44 decisions, source/route proof and hosted signed acceptance remain
with their existing owners. This result commit changes documentation only.

## GB-RV155 — integration refresh and merge review (2026-10-18, prospective)

Yao Zhu requests review, repair where needed and merge of PR155/157 into the
integration branch; PR133 stays open. Review PR155 at fbd86ba against integration
a2af2df, incorporating the base by ordinary merge. Preserve GB-CAP1..3,
GB-REPORT4 and GB-RW3 acceptance: exact request/returned economics and raw units,
full-position/holding/top-up and fee bounds, private exclusive output, blocked
owner acceptance and no signing authority. Re-run caps/proposal/Gate B report
checks on the refreshed pushed head; require no failures/skips in that subset.
Run the execution suite to check consumer compatibility; explicitly retain any
macOS/PostgreSQL/Linux-only skips and do not claim a new Linux release build.
Inspect the diff and existing review discussions before merge. No new runtime
policy, live profile acceptance, owner sign-off or host deployment is implied.

### GB-RV155 result — 2026-10-18

Refreshed/pushed head `387160a` includes integration `a2af2df` by ordinary merge.
No further code defect found after reading the full cap checker, its validators,
report consumer, fixtures, prior corrections and empty GitHub review discussions.
Focused caps/proposal/report: **33 passed, 105 subtests, no skips**, 1.29s.
Execution suite: **170 passed, 52 skipped, 694 subtests**, 2.20s on macOS arm64 /
Python3.12. Skips require disposable PostgreSQL or Linux isolation; this is not a
new Linux/host/release qualification. Prior GB-RW3 combined Linux evidence remains
historical. `git diff --check` passes. Existing organization Actions jobs at
run39047166150 have zero steps (the known billing block), not failed assertions.
No runtime code or cap values changed in this refresh; #27/#44 approval,
real-source/route evidence and all host/signing acceptance remain outstanding.
