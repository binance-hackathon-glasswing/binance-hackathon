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

## PC-AWS01 — deployment access check, 2026-10-17 SGT

- User requested an AWS deployment attempt or executable deployment instructions. Checked the current Isaac checkout without displaying credential values or reading wallet keys. No AWS CLI/Terraform/Session Manager plugin was found on PATH or at documented/common locations; no home AWS config/credentials, project `.aws`, process AWS variable names or `.env` AWS variable names exist. Both ignored Terraform connection/input files, the prepared package and measured rehearsal profile are absent here. The runbook explicitly locates the existing profile/files on Yao Zhu's Mac. No AWS connection or cloud operation was attempted; live resource state cannot be inferred from this check.
- GitHub read-only status: PR129 remains open/unmerged; #98/#118/#92 remain open. Integration head is still `eda2ed2`; latest listed org runs failed. Actual receiver, hosted RPC and applied-stack state are not verified by these issue states.
- Updated AWS_RUNBOOK with the local access findings and an executable login/refreshing-credentials/init/plan sequence for the configured Mac. It uses the existing private state backend; it creates no new stack and performs no apply. Host flags/AMI, exact CI bundle, real profile/RPC/terms, migrations and unsigned activation retain the recorded owners. Applying a saved plan follows AWS_RUNBOOK's explicit Yao Zhu spend approval; that prerequisite was not inferred from Isaac's request.
- Validation: documentation only; shell flow reviewed against the existing runbook and pinned Terraform/provider configuration. Commands were not executed here because the required tooling/access/files are absent. No application code changed; the previous 81-pass/6-skip local acceptance remains the code evidence, not a deployment result.
- Correction (2026-10-17): the runbook's apply line ran outside the plan block's subshell, whose EXIT trap deletes the temporary `larp-tf` config, so `AWS_CONFIG_FILE`/`AWS_PROFILE` were unset at apply time (reproduced in a shell). AWS_RUNBOOK now gives a separate apply subshell that rebuilds the same refreshing-credential setup. Documentation only; not executed against AWS.

## PC-AWS02 — Gate A host apply, 2026-10-16 UTC

- Yao Zhu ran the AWS_RUNBOOK sequence on the configured Mac from `codex/gate-a-package-check-20261016` (`c0fb5ae`; `deploy/aws` identical to `main`), with spend approval given by applying. `aws login` + `get-caller-identity` confirmed the team account. Private `development.tfvars` set `ami_id = "ami-0587b5bb1bc9eab99"` (latest AL2023 x86_64 SSM parameter in ap-southeast-2), `enable_hosts`, `enable_external_https` and `enable_development_ssm` to true; a backup of the previous file is outside the repo.
- Reviewed plan: 17 add (2 instances, internet gateway, public-route-table default route, primary HTTPS egress rule, primary SSM attachment, 6 host + 5 service alarms), 1 change (primary policy drops the `evidence` secret grant), 1 destroy (`larp-dev/evidence`, 30-day recovery). No database, bucket, KMS or replacement change. Signer: private subnet, no public IP, no SSM; the internet route is on the public route table only.
- First apply stopped on `AttachRolePolicy` with a local DNS failure (`lookup iam.amazonaws.com: no such host`; request never sent). State was saved; both instances were running. After DNS recovered, a fresh plan showed only the SSM attachment (1 add, 0 change, 0 destroy); applied: `Apply complete! Resources: 1 added, 0 changed, 0 destroyed`. Outputs list `primary` `i-0d565fb57b216a427` (later replaced, below), `signer` `i-0f8fe5d5fe5ccba36`, `signing_enabled = false`, and service secrets `runtime`/`uploader` only.
- SSM: `primary` did not register. The console log showed the agent failing at 17:05:10 (first boot, before the attach at 17:08:33) and again at 17:12:21, 5 s into the boot from a 17:12:02 reboot, both with only the Default Host Management error (`instance management role is not configured`). The role had `AmazonSSMManagedInstanceCore`, no permissions boundary and only the Terraform inline policy. `simulate-principal-policy` first returned `explicitDeny` / `AllowedByOrganizations: false`; with `aws:RequestedRegion=ap-southeast-2` context it returned allowed and organisation-allowed for the three SSM actions (the other host actions were implicit denies only because the simulation used `*` resources). CloudTrail after 17:10 showed no SSM call from the instance role, only `RegisterManagedInstance OK` from the instance at 17:05:11. Conclusion (inferred, agent log not readable): the first-boot agent saved a Default Host Management registration and kept using it.
- Fix: termination protection was disabled on the old `primary` by CLI, then a reviewed plan with `-replace='aws_instance.host["primary"]'` (1 add, 3 primary alarm dimension updates, 1 destroy; signer untouched; protection restored) was applied. New `primary` `i-040fc5fea8b700e9a` showed SSM `Online`, Amazon Linux, within minutes. Default Host Management was not enabled (account-wide; would cover signer). AWS_RUNBOOK records the attach-order lesson.
- Read-only smoke check on new `primary` over SSM Session Manager (Yao Zhu, 2026-10-16): role file `primary`; Amazon Linux 2023.12.20261014 x86_64; 20G root, 9% used; chrony on 169.254.169.123, `Leap status : Normal`, offset ≈ 0.3 µs; IMDSv1 request `401`; `sts get-caller-identity` = `assumed-role/larp-dev-primary/i-040fc5fea8b700e9a`; HTTPS to `api.binance.com/api/v3/ping` `200`; HTTP port 80 blocked (`000`); TCP 5432 to the RDS endpoint reachable; `larp-dev/runtime` readable by the role and holds a value (length only printed: 186). Nothing installed or changed. This is a host network/identity check only, not the IDEA-047 first-host service tests (those need the bundle, migrations and configs).
- Not yet observed: alarm state/emails. No bundle, provisioning, migration, config, manifest binding or activation was done; runbook steps 5–8 keep their blockers (#98/#49 bundle, signer-access decision, #118–120 profile, #92 RPC). This is infrastructure only, not Gate A evidence.

## PC-TERMS01 — source terms capture, 2026-10-17 UTC

- Ran `python -m larp.sources.live terms --write-register` (Python 3.14 from Anaconda; the macOS system Python 3.9 cannot import the package) on Yao Zhu's Mac with `LARP_ARTIFACT_ROOT=~/larp-artifacts` (outside Git) and a real SEC contact User-Agent. All six rows `CAPTURED` at 2026-10-17T03:3xZ: `doj-press` `47ca65aa…`, `ec-press` `3b899042…`, `fr-bis`/`fr-public-inspection` `ff681707…`, `sec-press`/`sec-edgar` `8ae50328…` (final URL `https://www.sec.gov/about/privacy-information`, 90417 bytes, title "SEC.gov | Privacy Information"). The register now records these hashes with `terms_checked` 2026-10-17; each retained file re-hashes to its register value.
- `python -m larp.sources.live preflight --config-mode shadow`: `{"ok": true, "refusals": []}`.
- Earlier SEC attempts returned HTTP 403 (SEC's "Request Rate Threshold Exceeded" page, which it also serves to undeclared automated tools) because the exported contact was still a copied template (name placeholder, no real email domain). `sec_user_agent` accepted it: its placeholder list catches only `<`, `>`, `example.com`, `contact email` and `you@`. No local process was polling SEC. DOJ and EC pages return different bytes on each fetch, so the host must receive the files from this capture, not a later one.
- Tests: `tests/sources/test_live.py` had two tests that assumed the committed EDGAR terms hash was null. They now derive the expected refusals from the committed register, or pass an explicit absent EDGAR entry, so they hold in either state. Local run (Anaconda Python 3.14, no project env on this Mac): `tests/sources` 85 passed; intelligence, routes and Gate A check 361 passed / 1 skipped; Gate A/execution-loop/halt 51 passed / 10 skipped (PostgreSQL-only). `tests/runtime/test_final_review_d.py` was not collected (`eth_account` missing locally). Org CI remains billing-blocked (#98).
- Remaining (GAP-70): copy the six retained files to `/var/lib/larp-evidence/artifacts/<prefix>/<hash>` on `primary` after provisioning, with evidence-user ownership, then rerun source preflight on the host. Use a bundle built from the commit carrying this register change.

## PC-TERMS02 — stricter SEC contact check, 2026-10-17 UTC

- User-requested follow-up to PC-TERMS01. Pass criteria, written before running: a copied template contact (`your.real@email`-style text, "Your Name" and similar, RFC 2606 example domains), an address with no dotted letter ending and an email with no name are each refused with a message naming the failed rule and never the value; every contact already used by tests and fixtures (`.invalid`, `.test`, `university.edu.sg`) and a real name-plus-address contact are still accepted.
- `larp/intelligence/config.py` `sec_user_agent` now requires one whitespace-delimited address whose domain ends in a dot plus two or more letters, at least one other word (the name), and none of the extended placeholder list. It is used by live preflight, the terms capture, the EDGAR poller, the bake-off and Gate A `prepare --sec-contact`. `EdgarHttpSource`'s own minimal `@` check is unchanged; live paths pass it the value `sec_user_agent` returned.
- Result: PASS. `tests/intelligence/test_edgar.py` gains template-refusal and acceptance tests (3 passed, 20 subtests). Full local suite (Anaconda Python 3.14): 1339 passed, 400 skipped, 3 failed, 1 collection error. The 3 failures (`test_service_configs` ×2, `test_archive` ×1) and the `test_final_review_d.py` collection error fail identically without this change and come from packages missing locally (`psycopg`, `boto3`, `eth_account`). Org CI remains billing-blocked (#98).

## PC-AWS04 — alarm descriptions, 2026-10-17 UTC

- Yao Zhu asked for it after the PC-AWS03 test email showed an empty Description: an alarm firing during the run gave no hint of what it means or what to do.
- Change: `deploy/aws/monitoring.tf` gives all 14 alarms an `alarm_description`: what fired, what the system does on its own, where to look (runbook section), and that nobody acts on the agent during the scored run (F-114). New Terraform test `every_alarm_explains_itself` requires a non-empty description of at most 1024 characters naming F-114 on every alarm.
- Pass criteria, written before the apply: (1) `terraform validate` and `terraform test` pass, and the new test fails when one description is removed; (2) the saved plan changes only `alarm_description` on existing alarms, in place: 0 to add, 0 to destroy, no other attribute; (3) after the apply, `describe-alarms` shows a non-empty description on all 14 alarms.
- Local result for (1): validate OK; `terraform test` 16 passed, 0 failed; with the database-storage description removed, 15 passed, 1 failed (`every_alarm_explains_itself`); restored.
- Result for (2): saved plan from pushed `1b2feb8` (PR #141): "0 to add, 14 to change, 0 to destroy"; a JSON check of the plan found no changed attribute other than `alarm_description`. Applied: "Apply complete! Resources: 0 added, 14 changed, 0 destroyed."
- Result for (3): `describe-alarms` shows descriptions of 249–367 characters on all 14 alarms. **PASS.** The next alarm email carries its description.

## PC-RPC01 — Gate A prepare takes the ordered provider file, 2026-10-17 UTC (prospective)

- Problem: Isaac selected two development balance providers (#135, BNB Chain primary, NodeReal backup), and the runtime accepts up to four in order (#116), but `tools/deploy/prepare_shadow.py` takes one `--balance-rpc-url`, so `prepare` writes only the primary into `runtime.json`. Yao Zhu asked for `prepare` to read the private provider file (`deploy/activation/balance-rpc/selected-providers.json`, the format `qualify_balance_rpc.py` uses).
- Change: `prepare_shadow.py capture|prepare --balance-rpc-config FILE`; `gate_a.prepare(..., balance_rpc_providers=[...])`. The single-URL flags keep working.
- Pass criteria, written before any code:
  - P1: with a provider list, `prepare` writes exactly that list, in order, to `driver.balance_rpc_providers` in `runtime.json`, and the report does not name `BALANCE_RPC`.
  - P2: naming the list together with `--balance-rpc-url`/`--balance-rpc-source-id` is refused; a list that the runtime's own `balance_providers` would refuse (empty, more than four, non-HTTPS, duplicate or empty source ID, extra keys) is refused by `prepare`.
  - P3: the chain capture must come from one of the listed providers' source IDs; another source is refused.
  - P4: a rendered config that still uses the legacy single-URL form refuses more than one provider, and keeps writing one provider as the legacy pair.
  - P5: the CLI reads the file for `capture` (the chain read uses the first provider's URL and source ID) and for `prepare`; it refuses the file combined with the single-URL flags, a symlink, or a file inside the repository that Git does not ignore; no refusal prints a URL.
  - P6: every existing Gate A test (GA01–GA14, `gate_a_check`) and the runtime service tests still pass unchanged.
- Results (2026-10-17): P1–P6 **PASS**. New `ProviderFile` tests in `tests/runtime/test_gate_a.py` (6 tests, 10 subtests) cover P1–P5; a mutation that writes only the first provider fails P1. Existing Gate A tests (GA01–GA14) and `test_gate_a_check.py`: 42 passed, 1 skipped, unchanged. Full local suite (Anaconda Python 3.14): 1353 passed, 400 skipped; the only failures are the three already present without this change (`psycopg`/`boto3` missing locally) and the `test_final_review_d.py` collection error (`eth_account`). `prepare` imports `larp.runtime.service.balance_providers`, which needs neither package. Org CI remains billing-blocked (#98). GATE_A.md and RPC_QUALIFICATION.md now show `--balance-rpc-config`.


## PC-REL01 / PC-GAP01 — Keegan LLM handoff decisions (2026-10-18)

User-delegated assistant decision for Keegan's workstream. Relevant published
host/mirror inputs were read from PR133 commit9b363e6 (PC-CI02, PC-KEY01,
PC-BUD01 and PC-AWS10); no PR133/126 merge is performed by this handoff.

**PC-REL01 complete:** accept CI bundle build7a0ea1433b3a029e9e2dc97817bac98a7e09c0ce
for the unsigned dev/shadow model trial. Exact bundle SHA256 is
ff951451bc80b518620f895b2b0a871df188ce2cb2d3e36e04a58754c7f5de06;
manifest bb17b7ffc28eeb2e14594a80895827bed5327b8408f519692870dcdeffdca70a;
CA d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b.
Retained published evidence: `docs/build/evidence/model-trial-mirror-20261018.json`
(byte-identical to9b363e6, SHA256
30b893ff60399bc819c361744910011504c8da9d78a8a4a829e8d55a48dc7c58).
It records run39091699018/artifact12122169313 and192 verified manifest hashes.
The old PENDING_KEEGAN field is historical; current acceptance is TR-AC1 in
`model-trial-decision-20261018.json`. Private-mirror APIs return404 here;
acceptance relies on the published verification plus our independent source
validation, not a claim of newly downloaded bundle bytes. Install-time exact
hash/manifest checks remain Yao's existing responsibility.

**TR-AC1 complete for Keegan:** unchanged original M1–M9/K1–K4 bars confirmed,
with frozen sampling seed/method before drawing. Keith's personal independent
bar review and exact prior-spend input remain unverified; acceptance of the
release/Keegan bars does not invent those inputs or permit guessed ledger init.
The approximate US$48 balance is not used as an exact billing figure.

**PC-GAP01 decision complete:** accept the documented historical pagination
backlog for source:doj-press and source:fr-bis as explained gaps only for the
fixed Oct17 11:00Z–Oct18 11:00Z report and unsigned trial, after Yao checks the
raw polling cadence/errors/rejections. Preserve the original report, generate a
second using the two exact incident entries, and retain both report hashes plus
the incident hash. A PASS with explanations is not full-source GateA acceptance;
runtime coverage stays INCOMPLETE. Actual outages, corrupt lines, other targets
and archive health are outside the exception. No wildcard or future-window
waiver is granted. At publication the report's end is still future; no actual
report/host success is claimed. Yao owns bounded-history/window coverage work;
Keegan reviews its evidence and release before signed/final source acceptance.

Authoritative instructions, limits and remaining owners:
[MODEL_TRIAL_HANDOFF_20261018.md](../build/MODEL_TRIAL_HANDOFF_20261018.md).
P0/P1/P2, actual11:00 report, archive-delivery evidence, provider/rights and
fresh shadow activation/start remain open. No AWS/host/inference/signing action.

Prospective verification, before running local checks: retained release evidence
matches its source bytes and all acceptance hashes; the two incident entries
have exact targets and the24h window; JSON parses; existing report tests retain
truncation/failure counts, reject corrupt/unrelated-target gaps, and preserve a
short-window INCONCLUSIVE. No application or runtime/config changes are made.

PC-REL01/PC-GAP01 verification at pushed6493a3c: existing source live/report
suite **24 passed, 18 subtests, 0 skips**, 0.19s, Python3.12.14. Separate local
synthetic checks using the exact incident JSON verify rawFAIL/explainedPASS,
zero complete polls and unchanged failed-poll counts, corrupt/unrelated-target
failures, future-window refusal and short-window INCONCLUSIVE. Published mirror
evidence bytes match9b363e6 and the decision hashes exactly; all new JSON parses,
relative handoff links resolve, ledger IDs are unique and whitespace checks pass.
Only documentation differs from accepted7a0ea14; no new runtime/bundle is needed.
Raw verification logs stay outside Git under
`/workspace/larp-cloud/llm-trial-handoff-20261018/`. These are synthetic/local
checks, not the future host report or independently downloaded release bytes.

## PC-REL02 — concurrent protocol and budget reconciliation (2026-10-18)

During PC-REL01 publication, PR166 supplied TRB-01A–E review corrections and
PR133 advanced to2bac3a5 with PC-BUD02/03. Reviewed those published deltas.
TR-AC2 now confirms TRB-01 at6f377dd, superseding our first unchanged-original
bar confirmation where inconsistent. The dated handoff/decision JSON identify
one current protocol, including ordered verdicts,90% recall/positive and route
minima, end-charge forecast, strict spending stops and72 unsigned hours.

PC-BUD03's owner confirmation supplies prior spend2,000,000 micro-USD from the
original50/exact48 balance, retaining10 reserve/40 operating and38 headroom;
the temporary5-reserve proposal was withdrawn. This supersedes our earlier
"exact input still pending" wording. Actual P1 initialization/snapshot and real
provider/funding checks are still unverified here. The same7a0ea14 release and
fixed-window PC-GAP01 explanation remain accepted; these docs require no new
bundle, host change or paid request. Keith's proposal task is supplied; labels,
matching rubric, reporting and remaining rights/funding tasks stay open.
