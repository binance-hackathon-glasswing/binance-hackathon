# Pre-trading checklist (2026-10-17)

This is a snapshot of what stands between today and the scored run (Oct 29 – Nov 12 UTC), split into what the team does this weekend without the strategy profile and what runs on Oct 20 once the profile exists. It was checked against `codex/system-testing-20261012` at `1ab47ae` (#129 merged), every open PR (#123–#126, #130–#132), the PRs merged on Oct 15–17 and the open issues on 2026-10-17, so nothing below repeats finished work. Refreshed 2026-10-17 08:20 UTC against `bb46234` (#123 and #125 merged) and the open PRs #126, #130, #131, #139, #143, #144, #148, #149 and #151. Audited 2026-10-17 for the LLM path and against every open issue (IDEA-066 PC-AUD01). Times are UTC (SGT = UTC+8). The live backlog stays [INCOMPLETE_WORK.md](../INCOMPLETE_WORK.md). Tick items here as they finish, and remove the matching backlog line only when its whole item is done.

Review refresh: integration `a428bab` includes #130/#131/#143/#144/#148/#149/#151
and #159. Historical open review scope was #126/#133/#139/#155/#157/#158/#161, plus #163 opened during review. Oct 18 refresh: #155/#157 reviewed and merged; #158/#163/#161 now also merged; #164 signed-LLM code merged; #133 remains open. Oct 18 03:30 UTC: status board below checked against integration `63ee226`; #165 newly open. Completed
repository deliveries below are distinct from pending evidence, decisions and
host checks. Host results are prior owner reports, not fresh checks by this review.

Latest checker correction **PC-MIRROR01 / PR177**: Yao approved the code fix; pushed verifier4eb33bb accepts only the exact registered challenge repo/approved Keegan4 mirror and passes all7 checks on the unchanged saved86b1476 package.65 focused tests PASS/3 PostgreSQL skips. **Correction:** PC-DEC01 already accepts the old mirror-only FAIL with production bind PASS; earlier wording that it was a deployment blocker or required a new binary is withdrawn. Original observed FAIL remains historical. PR177 was reviewed/merged on2026-10-19 (MERGE-RV20261019); future exact-release qualification remains separate; existing accepted86b1476 can proceed through fresh owner preparation without a checker-only rebuild. [Evidence](evidence/gate-a-approved-mirror-20261018.json).

Latest provider check Oct18 14:30UTC: **PC-PROV03 resolves AIand401**. Yao updated only the AIand secret field; host verifies all other fields match previous version. Authenticated AIand catalogue200 lists both exact models with high effort and USD currency; OpenAI still200. Balance endpoint403 leaves140+ owner-reported/expiry unverified. No inference/ledger/service action. [Evidence](evidence/aiand-key-verification-20261018.json).

Historical preparation snapshot, Oct18 13:56UTC: [PC-REL09 / PC-HOST02 / PC-PROV02 / PC-PREP02](PR174_DEPLOYMENT_CONTINUATION_20261018.md). Supplied tar and original CI assets independently verified; all196 Git files/235 checksums/manifest/CA/capped hash PASS. Host stillbb46234,71 audit chunks ACK, no ledger, DOJ failing. OpenAI model listing200; AIand authenticated401. Fresh exact-release package assembled with six local checks PASS, but CI_RELEASE_BYTES FAIL because its registered-only origin predicate rejects the verified mirror. Local qualification/host activation remain open; no manifest rewrite, paid call or host change.

Release-status refresh Oct18 (PR174-REL01): new frozen86b1476 includes merged174 and its independent accounting/clock/proof corrections;174 merged100d493 after private CI39126353379 all4 PASS. Full2064/6/2992 plus actual-systemd5/5; original tarball/sidecar/manifest/196 source files/235 bundle checksums/CA verified and uploaded to [new LLM release](https://github.com/Keegan4/Keegan4-larp-ci-mirror/releases/tag/llm-trial-pr174-86b1476). Older d8aa7d5 lacks these repairs. PR133/126 remain open. Yao actual preserving ledger/provider/host/source/start/ACK checks and trial measurements/adoption remain. PC-GAP02-RV1 retains the original fixed-window FAIL.

Historical Yao receipt (PC-REL08, Oct18 10:36Z; superseded above): original d8aa7d5 binary locally
verified (195 source files/234 checksums); host still bb46234 deterministic shadow,
healthy with62 audit chunks ACK and no model ledger. **New blocker PC-SRC01:**
DOJ94 RESPONSE_TOO_LARGE failures since Oct17 19:00Z fall outside PC-GAP01.
Do not explain these as pagination-only gaps. The later fixed-window result is
recorded below in PC-GAP02. **PC-CAP01:** $8 trial/$2.50 UTC-day admission enforcement still needs
reviewed deployment before paid work; PR174 now implements atomic caps (PC-FIX01), while the older binary enforces account pacing only.
Yao reconfirms OpenAI US$48/AIand140+; AIand units/actual funding still unqualified.

Fixed report now complete (PC-GAP02): located the19:00SGT local collector output,
verified31 hashes/718,138 raw bytes and independently reproduced **FAIL**.
DOJ96 RESPONSE_TOO_LARGE errors exclude PC-GAP01; BIS historical-only checks pass.
No combined explained PASS. Collection/hash verification is done; Keegan review,
PR174 review/new exact-source CI/original release are complete (PR174-REL01); DOJ actual post-fix host qualification and PC-CAP01 preserving ledger setup remain open.

Repair delivery PC-FIX01 / PR174-REL01: [PR174](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/174) reviewed, corrected and merged100d493. Accounting quarantine, migrated pacing clock and malformed proof regressions fixed; local/private CI2064/6/2992 and separate actual-systemd5/5 PASS. Original deployment files are attached to [the new86b1476 release](https://github.com/Keegan4/Keegan4-larp-ci-mirror/releases/tag/llm-trial-pr174-86b1476); no host install, paid inference or activation performed. Review and preserving setup/report instructions are in the frozen docs/build/DOJ_TRIAL_CAP_FIXES_20261018.md.

Current harness audit PC-HAR01 (Oct18 21:29SGT): [requirements/readiness matrix](HARNESS_READINESS_AUDIT_20261018.md). Fresh read-only host healthy with70 chunks ACK, but still bb46234 deterministic/shadow with no model ledger and continuing DOJ size failure. New86b1476 release is built/tested, not installed. DEV20 planner and S1 B4 producer remain open; full GateA/B/C acceptance is not inferred.

**Every line has exactly one owner.** Work that needs more than one person is split into small pieces, usually one person proposes or does it and another reviews or decides. A piece that depends on another names it ("after …").

**Who does what (2026-10-17):** Yao Zhu owns AWS access, host operations and Terraform (IDEA-066 PC-AWS01). The one explicit exception is Isaac placing the wallet key in the separately approved signer-host session supplied by Yao Zhu; Yao still owns session access, provisioning and teardown. Decisions, reviews, merges, code and write-ups sit with Isaac, Keith and Keegan.

## Done

- [x] AWS hosts applied; `primary` online over SSM and smoke-checked (2026-10-16, IDEA-066 PC-AWS02).
- [x] Terms captured for five enabled non-EDGAR sources plus EDGAR (six retained files total); shadow source preflight passes; stricter SEC contact check (IDEA-066 PC-TERMS01/02, #129).
- [x] Interim real quotes retained from Oct16 18:19 UTC; actual capture resumed Oct18 06:54:40 UTC through Oct20 00:00 UTC after a timestamp-freshness refusal. Tmux1 was keeping the host awake, not collecting quotes. Two resumed rounds verified; no uninterrupted-coverage claim (IDEA-063 KMP-QUOTE01).
- [x] Route checker built (#102); network destination table approved by Keegan for section B (#113).
- [x] Balance RPC failover: up to four providers in order (#116). Chain-balance decisions D1–D6 decided by Yao Zhu (#110) and built (#115, #116).
- [x] HALT split by reason, so mandatory sells continue under pausing HALTs (D-DN-09, #117).
- [x] Gas top-up round end to end (#103); first-gas MetaMask exception confirmed by the team (#105 closed).
- [x] Every CloudWatch alarm email now says what fired and what to do (#141, IDEA-066 PC-AWS04).
- [x] Swap decoder/router-check code (#130) and S1 strategy code (#131) are merged. Actual source/route qualification and S1 parameter/input adoption remain below.

## Completed in the Oct18 continuation (PC-HO01)

- [x] **Yao Zhu:** complete the requested review/fixes/merges for #155 and #157; merged at `2f10b9d` and `ad9a8b9`. Fee-reporting fix does not close fee-netting #119 or measured-profile #120.
- [x] **Yao Zhu:** deliver the requested OpenAI-primary/paced-credit implementation as separate PR #167, subsequently merged at `4312cd1`. Code capability is complete; KMP-P2 correction and new release/host qualification remain open.
- [x] **Keith:** deliver the v3 source/composed-prompt review and budget/window/stop proposal in merged PR168, plus the interim quote handoff, public terms register and signing/profile/limiter recommendations (KMP-02/KMP-RV168).
- [x] **Yao Zhu:** review/merge PR168 and approve the unsigned v3 protocol, route mapping and blind rubric (PC-REL05). No repeat Keegan protocol approval is pending.
- [x] **Yao Zhu:** store both model keys in the runtime secret; AWSCURRENT version `d227ba39-c9c9-40c5-a32f-1aa9bb3dfc3e` verified by metadata (PC-KEY01). No secret values recorded; provider checks remain open.
- [x] **Keegan:** accept the existing `7a0ea14` CI bundle for its unsigned v2 scope (PC-REL01). This does not satisfy the next v3 release item.
- [x] **Yao Zhu:** authorize Keegan/his release agent to push directly to `Cookiemunchrr/larp-ci-mirror` and dispatch CI (PC-DEC04). AWS/host operations remain with Yao.

Resume record: [AWS_DEPLOYMENT_RESUME_20261018.md](AWS_DEPLOYMENT_RESUME_20261018.md). It supersedes stale v2-only instructions for the next v3 trial; refresh remote/host state before acting.

## Plan (team decision 2026-10-17)

Finish every Gate A and Gate B step that doesn't need the strategy profile this weekend, then on **Oct 20** build the profile from the finished quote capture and run everything that needs it, in order. Three things need the profile: `prepare` builds the runtime config from it, the evidence service refuses to start without that runtime config, and the planner takes its minimum trade size and slippage limits from it. Gate A `prepare` accepts only a profile built from a real measured `QuoteCostSummary.v1` (`validate_live`), so it can't be faked to start early.

## Oct 18 status board (team task list, checked 03:30 UTC / 11:30 SGT)

One row per item on the team's Oct 18 list: its owner, then the evidence found in the repository and issues at integration `63ee226` (plus open PRs #126, #133, #139, #165), or the blocker. "Not recorded" means nothing in the ledger, the issues or this file shows it done; it may have happened privately. Owners tick the matching line further down when done. No keys, private RPC URLs or database hosts go in this file, the issues or the group chat; send those privately.

**Priority: unblock the LLM shadow trial.** The trial switch (last row) needs all four inputs above it.

| Item | Owner | Status, evidence or blocker |
|---|---|---|
| Send Yao Zhu both model keys (AIand, OpenAI) and the exact prior OpenAI spend, privately | Keith | **Received:** both keys stored (PC-KEY01); Yao confirms exact US$48 remaining from the original US$50 allocation: prior spend2,000,000 micro-USD. For v2 only, PC-BUD03 retains US$10 reserve/US$40 cumulative operating ceiling, leaving US$38 headroom. The separate v3 KMP-BUD01 protocol has no permanent reserve and is approved by Yao through PR168 (PC-REL05); host enforcement/setup remains pending. Existing external-only fallback keeps LLM assessments running on AIand; host initialization and provider validity remain separate |
| Review the trial's acceptance bars | Keith | **Proposal supplied:** PR166 TRB-01A–E, merged into this checklist branch at a3fa18a; Keegan-workstream confirmation is TR-AC2. Blind labels/matching rubric and reporting remain Keith's tasks; no personal approval is inferred |
| Confirm release bundle `7a0ea14` | Keegan | **Accepted for unsigned trial:** PC-REL01 / TR-AC2, based on PC-CI02's retained exact CI bundle/manifest/CA verification and independent source validation. Bundle SHA256 ff951451…5de06; manifest bb17b7ff…ca70a. This session could not independently download the private mirror artifact. See MODEL_TRIAL_HANDOFF_20261018.md |
| Confirm the trial bars | Keegan | **Confirmed:** TR-AC2 accepts PR166 TRB-01A–E at6f377dd; unchanged operational thresholds plus corrected verdicts, recall/route coverage, spending boundaries/forecast and 72 unsigned observation hours. Seed/allocation frozen; actual measurements are pending |
| Decide how `doj-press` and `fr-bis` pass the gap report | Keegan | **Decided PC-GAP01:** two exact historical-backfill explanations for Oct17 11:00Z–Oct18 11:00Z and the unsigned trial only, after raw cadence/error/rejection review. Keep raw/explained reports and hashes; runtime coverage stays INCOMPLETE; no full-source Gate A or signed acceptance. Incident JSON and limits in MODEL_TRIAL_HANDOFF_20261018.md |
| 24 h gap report at 11:00 UTC (19:00 SGT); save its hash; send to Keegan | Yao Zhu | **Collection/hash/local verification DONE (PC-GAP02):** raw FAIL, report SHA092c18e5…a5cf5; original718,138-byte snapshot hash verified. DOJ96 response-size errors exclude the blanket gap exception; BIS historical-only checks pass. PR174-R1/PC-GAP02-RV1 retained-metadata review/disposition is complete: preserve FAIL and withheld DOJ explanation; private raw-byte sharing/audit and actual post-install source qualification remain separate. Separate historical archive incident preserved |
| After the report, bundle acceptance and Keith's inputs: install the bundle, start the trial, verify its first assessment | Yao Zhu | **Remaining:** actual fixed-window report/exception checks, P0 provider identity/terms/funding, P1 initialization using confirmed2,000,000 prior spend and in-flight headroom monitoring, P2 prepared/bound shadow config, installation/version event and first assessment. Release/bars/gap disposition are recorded in PC-REL01/TR-AC2/PC-GAP01 |

**In parallel while waiting**

| Item | Owner | Status, evidence or blocker |
|---|---|---|
| Send Isaac the quote artifacts collected so far; keep the capture running | Keith | **Handoff prepared/published:** KMP-QUOTE01 links1,021 records/26 latest raw artifacts, exact hashes/coverage and #118 handoff. Unchanged runner resumed Oct18 06:54:40Z through Oct20 00:00Z; future health/final coverage remain open |
| Record the interim profile's coverage settings and capture/profile hashes in IDEA-063 | Keith | **Partial:** KMP-QUOTE01 records new snapshot hashes and default-summary refusal (9 US-session samples/token), plus the older two-day/nine-sample profile's full reported SHA. Its original capture hash/full summary bytes still need Yao's export; no reconstruction or final-profile acceptance |
| Comment on #27's signing-lifetime options | Keith | **Proposal supplied:** KMP-SIGN01 / #27 comment recommends SL-01 option A conditionally; keep fresh ≤15s admission and measured quote age, persist finite authority across re-quotes/restarts. No unmeasured60s adoption; Keegan decides/implements C-OPEN-003 |
| Oct 19 proposals: first-trade window, profile (`EQUAL_WEIGHT` or S1), POLICY-HOLD | Keith | **Proposal supplied:** KMP-SIGN01 recommends existing Oct21–22 window, measured EQUAL_WEIGHT fallback if S1 prerequisites remain unqualified, S1 DETERMINISTIC limiter with B4 required, and retaining the current bounded per-symbol hold. Isaac decisions now recorded SP-D1..4; original O6 assessor adoption remains separate |
| Capture AIand/OpenAI terms; check current AIand funding | Keith | **Terms captured/review recorded:** KMP-RIGHTS01 register + dated hash manifest; account overrides and signed/scored financial-policy compatibility await Keegan review. Funding remains NOT_MEASURED: AIand140+ units/current balance and actual usage/charges need Yao export; no affordability approval |
| Run EXP-007 after O2 | Keith | **Blocked** on Keegan's O2 below. EXP-007 is still draft; result due Oct 19 |
| Router source/evidence for #139: exact blocker and next action | Isaac | **Blocked, rechecked SP-01 R1:** candidate facet Code403/Cloudflare; Sourcify404/no match. No verified router/facet/helper source/ABI or independent guarantees review. Isaac obtains permitted source export/vendor evidence; no vendor message sent. Router replay NOT_RUN until source/review; #139 stays draft |
| Re-approve the AIand/OpenAI network destinations for signed/live use | Isaac | **Approved application scope SP-NET D2:** user explicitly authorizes the reviewed same-host signed/live scope in its own PR. Provider compatibility/adoption/declaration/host gates remain; no AWS change |
| Execution gas limits within the 0.0002 BNB per-transaction fee cap | Isaac | **Draft ceilings set SP-CAPS:**1,200,000 gas ×160,000,000wei=.000192BNB in execution.example.json. All1,700 captured swap-gas estimates are FALLBACK; actual gas/aggregate budget/final profile/fresh holdings and #44 approval remain open |
| Real-provider `native_trace` qualification (#30) | Isaac | **UNQUALIFIED; NT-Q1 tool delivered:** PublicNode also rejects recent/historical prestateTracer, SubQuery DNS fails. Private account config is unavailable. The separate [qualification procedure](NATIVE_RPC_QUALIFICATION_20261018.md) uses production canonical/native proof and passes42 synthetic tests/56 subtests; actual endpoint/proof and Yao host acceptance remain open. No capability enabled |
| Attributable fee-netting evidence (#119) | Isaac | **UNVERIFIED SP-FEE:**15 current routes retain nonzero network tradeFee/null custom-fee fields; these do not prove wallet-net route fees. Applicable source semantics or exact first planned agent quote/receipt still required; #119/#120 open |
| Decide the first-trade window and POLICY-HOLD | Isaac | **Decided SP-D1..4:** existing Oct21–22 window after gates; conditional measured EQUAL_WEIGHT fallback; DETERMINISTIC S1 limiter with B4 required; retain bounded per-symbol price-jump hold including urgent exits. Original O6 assessor adoption and actual profile/hash approval remain open |
| Review Yao Zhu's migration, database-role and TLS evidence | Keegan | **Reviewed PC-AWS06-RV1 / V3-REL01:** reported empty-DB migrations001–013 and limited primary IAM/TLS checks match unchanged source. Admin verify-ca differs from runtime verify-full; preserve the initial timeout. Signer-host, populated upgrade and new-release installation are separate, unverified checks. See the release record |
| Settle O2 (what ships if EXP-007 is inconclusive) | Keegan | **Not recorded.** IDEA-075 §16 recommends shipping the trend guard as declared. Blocks EXP-007 |
| Update the model services list and DEV-19 | Keegan | **Done V3-REL01:** selected opt-in unsigned OpenAI Sol medium primary with high-effort AIand Kimi K3 then GLM-5.3 review/fallback; PROVISIONING means actual provider/host qualification pending. DEV-19 dated Oct18, final scored adoption remains separate |
| B4 exposure-evidence producer | Keegan | **Not built.** `larp/strategy/policy.py` reads `exposure_evidence`, but no runtime or integration code produces it, so the limiter stays NORMAL |
| Draft the outstanding operations decisions; update #22/#42 and #98's mirror-CI disposition | Keegan | **Not recorded.** D-DN-01, 04, 06, 07, 08, 11 still open (IDEA-049-D §5); #22, #42 and #98 last updated Oct 15 |
| After the trial starts: budget status, ledger backup, memory use | Yao Zhu | **Waits for the trial.** Deterministic memory baselines: PC-AWS09 (Oct 17) and PC-AWS11 (Oct 18) |

SP-01 refresh Oct18: #165 reviewed/merged at817eb71 after combined-head local acceptance (2021 passed /9 skips /2981 subtests). Exact-release Linux/host qualification and real-cost parameter freeze remain; see B6 below.

**Risk:** the interim shadow services already started on Oct 17 (PC-AWS07). Gate A now has its actual 24 h report (PC-GAP02, FAIL); PC-GAP02-RV1 retains FAIL/no DOJ waiver; actual post-fix source qualification remains; the Oct 20 final profile needs fresh preparation/binding/activation. Early shadow success does not qualify those later configs or signed Gate B operation. The later PC-AWS09 host report found archive delivery blocked after the restart drill; #163 and its hosted recheck remain necessary. Oct 18 02:46 UTC read-only recheck is healthy after the daily backup superseded that historical failure (PC-AWS11); #163 still needs release/host qualification.

## Isaac immediate points — separate PRs (2026-10-18)

Isaac authorizes carrying out the listed immediate points, each in its own PR,
and reports no source export, private RPC config or additional funding hash.
No AWS operation, key placement or wallet transaction occurred in this follow-up.

| Point | Owner | Dedicated PR and current result |
|---|---|---|
| Signed/live model-network scope | Isaac | [PR171](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/171), merged into this checklist branch on2026-10-19 (MERGE-RV20261019). Explicit authorization settles the previous review-only blocker; same-host policy/report change is isolated in that PR.40 tests/48 subtests pass, no skips. Provider-policy/adoption/host gates remain; no AWS or client endpoint/config changes |
| Verified router/facet source | Isaac | Existing draft [PR139](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/139), source point only. RE-02: Code403, legacy API301, v2 source API Missing/Invalid API Key; no export/account access. No source/ABI/independent review; route check NOT_RUN. Keegan reviews after complete evidence is obtained |
| Real native-tracing provider | Isaac | [PR173](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/173), tool reviewed/merged into this checklist branch on2026-10-19 (MERGE-RV20261019). NT-Q1 uses production canonical/native receipt proof;42 tests/56 subtests pass. PublicNode tracer unavailable, SubQuery DNS failed; no usable private account. Actual provider qualification/selection NOT_RUN, tracing remains off; Yao host check follows |
| Remaining dev gas funding | Isaac | Draft [PR172](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/172). FG-02 public snapshot:98USDT,0.002694498869362886BNB, nonces2/2/2. No additional hash/action; remaining seed NOT_DONE. Isaac/Yao first confirm no first-agent-trade/in-flight work, Isaac completes MetaMask step, Yao takes actual post-last-seed opening capture |

These points remain separate. PR171/173 are now merged; PR139/172 remain draft. Repository merges do not claim source/provider/wallet/host readiness.

## This weekend (Oct 17–19): no profile needed

### Gate A setup

- [x] **Keegan:** merge #132 (capture record) and #124 (CI record, closes #91). Both are docs only. Done: both merged 2026-10-17.
- [x] **Isaac:** choose the balance RPC provider(s) with `finalized` support and a source ID for each. Since #116 up to four can be listed in failover order (`driver.balance_rpc_providers`). Send the URLs and IDs to Yao Zhu privately, not in an issue (#92, GAP-71). Done 2026-10-17: BNB Chain public primary, NodeReal public backup, for development balance reads (#135, IDEA-055 RPC-Q01 D1).
- [x] **Isaac:** approve the network destination table for section C; Keegan already approved section B (#113). The table is in `architecture-deployment.md` "Approved network destinations" (#32). Done 2026-10-17 (#137, IDEA-062 NC-01).
- [x] **Keegan:** ask the GitHub org owner to restore Actions minutes (#98). No longer needed: mirror-CI builds are the accepted release builds (Yao Zhu, 2026-10-17; IDEA-066 PC-DEC01).
- [x] **Keegan:** after that, build the host bundle from the commit with the terms register (`1ab47ae` or later); record the run ID and the bundle and manifest hashes, and send them to Yao Zhu (#49). Mirror builds are accepted release builds under PC-DEC01; hosted Gate A acceptance (#127) is separate. Progress 2026-10-17: Keegan's mirror-CI bundle `bb46234` received and used for `primary`; the org-CI build is still blocked (#98), and the signer will need a newer bundle that includes #130. Done for Gate A with mirror bundle `bb46234` (accepted, PC-DEC01). A newer mirror bundle for Gate B is listed below.
- [x] **Yao Zhu:** confirm the alarm email subscriptions (AWS SNS), send a test alarm and confirm it arrives. Done 2026-10-17: the topic had no subscription; a one-resource Terraform apply added it, Yao Zhu confirmed it, and a test ALARM on `larp-dev-database-storage` reached Yao Zhu by email (IDEA-066 PC-AWS03).
- [x] **Yao Zhu:** after Isaac's RPC choice, open network access from `primary` to those RPC hosts (Terraform, reviewed plan). Done 2026-10-17: no change needed, since `primary` already allows outbound HTTPS; both provider hosts answered from `primary` (IDEA-066 PC-AWS05). The private URLs still come from Isaac for the Oct 20 `prepare`.
- [x] **Yao Zhu:** after the bundle exists, upload it and provision `primary` over SSM (`provision.sh primary <bundle> --expect-sha256 <CI hash>`; AWS_RUNBOOK step 5). Done 2026-10-17 with the mirror-CI bundle `bb46234` (IDEA-066 PC-AWS06).
- [x] **Yao Zhu:** after provisioning, run migrations 012/013 and `roles.sql` through an SSM port-forward, then check IAM token login and TLS for each database role (AWS_RUNBOOK step 6, PR99-RV1, IDEA-044 V10/V11). Done 2026-10-17: migrations 001–013 and roles applied; all four `primary` roles pass (IDEA-066 PC-AWS06).
- [x] **Yao Zhu:** copy the four distinct retained terms files covering six source entries from the 2026-10-17 capture to `/var/lib/larp-evidence/artifacts/<prefix>/<hash>` on `primary`, then rerun source preflight there. DOJ and EC pages change on every fetch, so only that capture's files match the register. Done 2026-10-17: installed, host preflight `ok` (IDEA-066 PC-AWS06).
- [x] **Yao Zhu:** on `primary`, run the route check (`python -m larp.runtime.routes --role primary`) and record `chronyc tracking`. Also confirm that `/etc/chrony.conf` has `rtcsync` and that `kernel_clock_synchronized()` prints `True` there (command in DEPLOYMENT_DAY step 9); without that signal a `CLOCK` HALT never clears (D-DN-10, #125). Send the reports to Keegan (R-07, R-08). Done 2026-10-17: 13/13 PASS, chrony normal (IDEA-066 PC-AWS06).

### Gate B setup

- [ ] **Isaac:** fill in `RouterEvidence.v1` from the router's verified source on BscScan, following `docs/build/GATE_B.md` in #130 (#33, GAP-29). **Blocked (2026-10-17, draft #139):** the router's code is unverified on BscScan, Read Facets gives no usable ABI and Sourcify has no match, so there is no verified source yet. #139 holds the acquisition report and the handoff in `ROUTER_SOURCE_REVIEW.md`; it is not to be merged until the evidence is complete. SP-01 recheck: candidate Code403 challenge and Sourcify404/no match; source/ABI still unavailable. See [current evidence and next action](SIGNED_PREREQUISITES_20261018.md#evidence-results--sp-01-r1).
- [ ] **Keegan:** independently review Isaac's complete verified router evidence (#138/#139) when supplied. Decoder PR #130 is already merged and its repository review is recorded in IDEA-070; that does not approve missing real source evidence.
- [x] **Keith:** interim quote handoff supplied for Isaac via #118 and [KMP-QUOTE01](evidence/quotes-interim-20261018/README.md): complete JSONL snapshots/26 latest raw artifacts, verified hashes, actual coverage/gaps and fee/gas caveats. Final capture/profile review remains open.
- [ ] **Isaac:** using merged #130, after the source-evidence review, run `python -m larp.execution_live.router check` on those files until it reports PASS. No separate route capture is needed. **NOT_RUN SP-01:** all29 handoff hashes/lengths verify, but source and independent review are absent; do not manufacture evidence to invoke the command.
- [x] **Isaac:** write the two options for how long a signing request stays valid, with a recommendation: (a) a bounded signing lifetime, or (b) a router deadline no later than the proposal's expiry. The encoded-deadline versus 15 s admission contract is unresolved (#27); about 30 s is the kit-stated quote lifetime, not a measured encoded deadline. Done 2026-10-17 in merged #144: `SIGNING_LIFETIME_PROPOSAL.md` and IDEA-049-C SL-01 recommend option A conditionally (60 s only an illustrative value) and note that the 30 s is the kit's stated quote lifetime, not a measured deadline.
- [x] **Keith:** #27 review/proposal supplied in KMP-SIGN01 and its issue comment: separate fresh admission from finite immutable authority, preserve quote age/economic windows, no unmeasured lifetime adoption. Keegan decides/implements.
- [ ] **Keegan:** decide #27 from Isaac's options and Keith's comment, record it as C-OPEN-003 in IDEA-049-C, and open the code change.
- [x] **Isaac:** propose the per-token input caps, the fee cap and `allowed_spenders` (the router's `tx.to` from the router evidence) for `signer.json` (#44). Done 2026-10-17 in merged #148: USDT input 35 (development) / 70 (final), fee cap 0.0002 BNB per transaction, token caps at 50% of the Oct 10 reference marks, spender the router `0xb444…fdda5`. Not installable until approved (`ready_to_install: false`).
- [x] **Isaac:** hand over a development `signer.json` draft and a technical cap review (#160, PR #161; received by Yao Zhu 2026-10-17, IDEA-066 PC-SIG01). Draft SHA-256 `339c4202…1442`; its `signing_policy` is byte-identical to the merged CP-01 development candidate (policy SHA-256 `254f5c31…2033`). Nominal check passed: the largest input is 20.10 USDT (EQUAL_WEIGHT) or 28.60 USDT (proposed S1) against the 35 USDT cap, at 100 USDT capital. The review was done by Isaac's delegated assistant, not by Keith. `ready_to_install: false`.
- [x] **Keegan:** review and merge #161 (the handoff record). Merged 2026-10-18 at `7cd7892`; numeric-policy approval and host installation remain separate.
- [ ] **Keith:** after the Oct 20 profile, finish the cap checks the handoff could not run, and record the file hashes on #44: the profile's `per_trade_cap_units` and `gas_top_up_cash_units` are each ≤ 35 000 000 micro-USDT; every full stock holding in the fresh wallet capture fits its token cap; measured approve and swap fees each fit 0.0002 BNB. PR #155's numeric-review tool can do this. Do not count the 40 USDT quote-capture size as a trade size: it is above the 35 USDT cap.
- [x] **Isaac:** set conservative draft execution ceilings within the candidate fee cap. SP-CAPS: `max_gas=1200000`, `max_gas_price=160000000`wei; product192000000000000wei (<200000000000000). Example only, uninstalled; actual gas, aggregate budget and final profile/full-holding #44 acceptance remain open.
- [ ] **Isaac:** after Keith's checks, decide the exact policy on #44 and replace `cap_basis: EXAMPLE_PENDING_TEAM_DECISION` with the decision reference. That changes the policy hash; record the new one. PR176 is merged into integration (MERGE-RV20261019): both dev/live now refuse the pending-decision label before startup. Replacing a label does not establish numeric approval; the exact #44 decision remains required.
- [x] **Keegan:** choose how the signer host is reached for key placement (options in AWS_RUNBOOK step 5) and record the choice in a short IDEA entry. Done 2026-10-17: option (b), temporary SSM interface endpoints in the signer subnet, criteria SA1–SA7 (IDEA-080, #140).
- [ ] **Keegan:** review Yao Zhu's actual IDEA-080 Terraform plan before apply. #143 and implementation #149 are already merged/reviewed in the repository; the host apply is still pending. Preserve SA3 (both host groups), SA8 signer egress and SA9 primary SSM checks.
- [ ] **Yao Zhu:** on Gate B day, finish `signer.json` from Isaac's draft (copy kept outside Git in `deploy/activation/signer-dev-20261017/`). Order: Keegan's Gate B bundle exists, Isaac's router evidence is merged and his #44 policy decision is in, then the IDEA-080 apply below. The six fields the draft leaves null, and where each comes from: **Progress 2026-10-17:** `database_host` and `database_ca_sha256` pre-filled in `signer.prefilled.json` next to the draft (IDEA-066 PC-PREP01); four fields left.
  - `database_host`: `terraform -chdir=deploy/aws output -raw database_host` (the same RDS `primary` uses). Keep it out of Git and chat.
  - `database_ca_sha256`: `rds_ca_sha256` in the verified Gate B bundle's `BUNDLE.env` (the `.release.json` has code identity, not CA metadata) (`d73890748b5a…` for `bb46234`, PC-AWS06); check it on the signer with `sha256sum /etc/larp/rds-ca.pem`.
  - `build_id`: the full 40-character commit in the Gate B bundle's `.release.json`; the same in `execution.json`, the runtime config and the release manifest.
  - `run_id`: the ID chosen for the signed rehearsal run, the same one passed to `prepare` and `service init` for it and used in `execution.json` and the initial state (e.g. `larp-dev-rehearsal-20261021`). Never `larp-dev-shadow-20261017`.
  - `router_evidence_file`: `/etc/larp/router-evidence.json` on the signer, a copy of Isaac's merged `config/execution/router-evidence.v1.json` (GATE_B.md steps 4 and 8). **Blocked on #139.**
  - `router_evidence_sha256`: `sha256sum /etc/larp/router-evidence.json`; must equal Isaac's recorded hash. `execution.json` gets the same pair.
  Shortcut for the database fields: `python tools/deploy/render_host_configs.py --terraform-output /tmp/tf.json --wallet 0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479 --out deploy/activation/development --rds-ca-sha256 <verified BUNDLE.env rds_ca_sha256>` (DEPLOYMENT_DAY step 7) fills them and lists what is still unset; replace its example `signing_policy` with Isaac's decided one. Then record the final file's SHA-256 (not the draft's `339c4202…`), install it as `/etc/larp/signer.json` and re-bind with `--service-config signer=/etc/larp/signer.json`.
- [ ] **Yao Zhu:** after #44's approval and Keegan's review of #143 and #149, apply the IDEA-080 Terraform change (built 2026-10-17 in #149: temporary SSM endpoints, off by default, `terraform test` 19 passed; planned, not applied), provision the signer, install the decided `/etc/larp/signer.json`, run the signer route check (SA4) and give Isaac a session for the key. After the key is placed, tear the endpoints down and record SA5.
- [ ] **Isaac:** after that, place the key file on the signer host only (`/etc/larp/signer/wallet.key`, root, `0600`) (DR-03).
- [ ] **Isaac:** swap about 2 USDT more in MetaMask and record the fresh opening balance afterwards (#106). The record of the first 2 USDT swap (0.002685 BNB received, 2026-10-16 08:27:44 UTC) is recorded in merged #151; parent #106 retains the remaining funding/capture.
- [ ] **Keith:** propose the BNB floor and top-up size (G-28) from the measured gas (#30).
- [ ] **Isaac:** show BNB tracking (`native_trace`) works on a real provider, and accept or change Keith's floor and top-up size (#30).

### Model trial: before Gate B goes live

Decided by Yao Zhu, 2026-10-17 (IDEA-066 PC-DEC02): switch the live shadow run to the LLM assessor (`aiand_routed`) right after the 24 h gap report (Oct 18, after 11:00 UTC), on a new bundle that includes #158's stage prompts. About $49 of OpenAI credit is left; Keith holds those credits and settles the budget numbers. The deployed run was reported deterministic; it was not inspected in this review. Merged #159 now opts into routing with explicit file/hash inputs; existing deployments do not switch automatically.

**The LLM stays in for the signed rehearsal (decided by Yao Zhu, 2026-10-17, IDEA-066 PC-DEC03).** The proposal declares a hosted reasoning LLM for the evidence step, and the team keeps it. The signed/live capability and preparation change is merged in #164 (IDEA-057 SLM-01/SLM-RV1). The Oct 21–26 rehearsal still needs its mirror bundle installed and an early model decision on Oct 20, below. If either is missing on Oct 21, the rehearsal starts on `deterministic` and switches once both are in (a version event, recorded as a deviation). **Protocol correction proposed Oct 18 (IDEA-057 TRB-01):** unsigned qualification needs 72 observed hours; signed rehearsal is a separate evidence window and cannot complete that duration. The Oct 22 decision reports both windows separately and keeps a short/under-covered unsigned trial inconclusive. Any earlier development-only rehearsal exception needs an explicit decision/deviation; it does not establish trial support or scored-run adoption.

- [x] **Keegan:** review and merge #158 (IDEA-081, per-stage prompts for GLM-5.3, Kimi K3 and Sol). Merged 2026-10-18 at `ce9115e`; mirror bundle from reviewed head `7a0ea14` downloaded and hash-verified locally. Release acceptance/handoff is complete in PC-REL01; actual install/start remains with Yao (IDEA-066 PC-CI02).
- [x] **Keith:** supply the exact OpenAI budget input. Yao confirms exactly US$48 remaining Oct18 from the recorded US$50 allocation, so prior spend is2,000,000 micro-USD. PC-BUD03 retains US$10 reserve, US$40 cumulative operating ceiling and US$38 current headroom; actual P1 initialization remains separate.
- [x] **Keith:** send Yao Zhu the OpenAI API key and AIand API key privately. Yao confirms receipt Oct 18 and stored the runtime secret at 05:08 UTC; AWSCURRENT metadata verified (IDEA-066 PC-KEY01). Provider/funding validity remains a separate check; no key values recorded.
- [ ] **Yao Zhu:** complete host gates for [merged PR #167](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/167), the OpenAI-preferred/full-credit route (merged at `4312cd1`; source/prompt review and unsigned v3 protocol supplied in approved PR168/PC-REL05). Protocol approval is complete; KMP-P2 and PR174 fixes/release verification are complete (PC-REL09). Done 2026-10-18 (IDEA-066 PC-DEPLOY01/02): new capped trial ledger (2,000,000 µUSD owner-confirmed prior spend, no reserve), exact routing `a5fca50a…` installed, run `larp-dev-llm-trial-20261018t170339z` on `ea25b52` live, first OpenAI job served `gpt-6.1-sol`/medium with settled charges and receiver `STORED`. Remaining: AIand units/expiry/funding (balance endpoint 403), reconciliation of the one UNKNOWN 84,764 µUSD charge from the 86b1476 JSON-mode bug (kept, never edited), and the identified unsigned start record for Keith.
- [x] **Keith:** supply the frozen matching/adjudication rubric and unchanged seed/selection procedure, with actual v3 route mapping (PR168 KMP-LABEL01/KMP-RV168; approved PC-REL05).
- [ ] **Keith:** after Yao supplies the immutable job/source export, apply the approved draw, retain population/selection/blind/label hashes, arrange independent annotation and report M9/unqualified paths. Actual drawing/labels remain NOT_RUN.
- [ ] **Yao Zhu:** after the gap report and accepted v3 release/fix, perform P0 provider/account checks, reconcile all actual spend against the reported2,000,000-microUSD prior charge, and use matching v3 budget setup with `--routing-file` (reviewed migration if a ledger already exists; preserve all charges/latches). Reprovision primary, prepare from the exact release source with the reviewed v3 `--model-routing` file/hash, install/re-bind, fresh `service init`/`activate` and route check; verify the first routed assessment/receiver ACK and record P0–P2/start identity. 2026-10-18: all of this done for `ea25b52` (PC-DEPLOY02; first fixed job 17:15 UTC, OpenAI ASSESSED, combined UNAVAILABLE at the 60 s deadline). Remaining: AIand funding/expiry and UNKNOWN-charge reconciliation (next item). No permanent reserve under approved PC-REL05. Local run-sheet section C is updated; its historical v2/$10 tail is superseded. Both model keys are already stored (PC-KEY01); provider validity remains pending.
- [ ] **Yao Zhu:** before the first routed assessment, record Yao-approved PR168/PC-REL05 protocol revision, unsigned UTC start/cutoff and P0–P2. During that window, monitor K1–K4 and spending headroom including in-flight reservations (TRB-01D); daily `status`/ledger backup alone cannot enforce a spend ceiling. Report the unique-job, route/stage and M9 coverage gaps (TRB-01B/C); pre-register any separate unsigned route probes and charge them to the same budget.
- [ ] **Yao Zhu:** on Oct 20, pass the same `--model-routing` options to `prepare`; without them it writes `deterministic`.
- [ ] **Yao Zhu:** before the switch to signed rehearsal (Oct 21), close/archive the unsigned window with its last job, UTC cutoff, budget reconciliation and verdict under TRB-01A. Keep `aiand_routed` only with Keegan's separately recorded rehearsal decision/deviation, installed reviewed bundle and Gate B prerequisites; otherwise use `deterministic`. Record the signed window's new version/adoption reference and opening shared-budget snapshot; never count signed jobs/days toward unsigned qualification (TRB-01E).

**LLM in the signed rehearsal: early decision and code change**

- [x] **Isaac:** write the code change that lets `aiand_routed` run with signing (`execution: service`, and `mode: live` for the scored run). Write its pass criteria in a ledger entry first. Minimum criteria: (1) a model call can never delay or block a mandatory sell, an execution step or a HALT; (2) a model failure, timeout or budget switch leaves the last accepted limiter level in place and never raises exposure (IDEA-075 §4.2); (3) the routed result reaches the limiter only through the existing verification and acceptance path; (4) every stage's model I/O and reasoning reaches the ai-seeds round log (F-102). Done: #164 merged 2026-10-17 17:05 UTC at `a2af2df`; synthetic/Linux verification in IDEA-057 SLM-01/SLM-RV1. Hosted acceptance and adoption remain open.
- [ ] **Keith:** confirm the model-owner review before Oct 20 adoption; #164 is already reviewed and merged at `a2af2df` (IDEA-057 SLM-RV1), so no further merge is required. Personal Keith approval is not inferred from the merge.
- [ ] **Keegan:** after it merges, build the mirror bundle for Gate B with it (the bundle line under "Gate B setup") and send the hashes to Yao Zhu.
- [ ] **Keith:** on Oct 20 (morning UTC), publish an **interim/provisional** report: actual unsigned hours/unique jobs, M1/M2/M3/M5/M6, all kills, route/stage counts and M9 label/positive coverage. Use end charge plus forecast future charge (TRB-01D). Fewer than 72 observed hours or missing coverage means inconclusive unless a kill/safety defect makes it not supported; an interim report cannot establish SUPPORTED.
- [ ] **Keegan:** on Oct 20, separately decide whether a bounded development-only signed rehearsal proceeds (early DR-11), and tell Yao Zhu before re-activation. If unsigned qualification is inconclusive, record missing evidence, scope, owner, fallback and the explicit deviation under TRB-01E; do not call it trial support or scored adoption. A no means `deterministic` for the rehearsal and the corresponding DEV-19 disposition.

**LLM: everything else between now and the scored run (audit 2026-10-17, IDEA-066 PC-AUD01)**

These were missing from every list; each one is needed for the LLM to be in the activated build and working (A-REQ-079). Owners rebalanced 2026-10-17 (Yao Zhu): model and routing work to Keith, who proposed the routing; tooling, network, operations and review to Isaac; Keegan keeps the strategy wiring, release declaration and model decision.

*How the LLM's findings reach trading.* Two paths: accepted assessment findings feed the evidence gate (Class 1 exits and entry blocks), and, with the S1 profile only, the exposure limiter. The limiter's input is not produced anywhere today. In `MODEL` mode it also needs an LLM call that returns `{level, evidence_ids, reason, falsifier}`, and that call does not exist; with no assessment, every session is rejected as `NO_ASSESSMENT`, so the limiter never cuts and a cut never expires.

- [x] **Keith:** propose S1 `limiter_mode`: **DETERMINISTIC** for rehearsal/final, mapping LLM-verified evidence classes without a separate exposure call (KMP-SIGN01). B4 producer still required; MODEL remains unqualified until its call/audit/budget acceptance. Isaac decides; this does not select a deterministic assessor.
- [x] **Isaac:** choose DETERMINISTIC S1 limiter under SP-D3 from Keith's proposal. It maps verified LLM evidence; B4 remains required. Original IDEA075 O6 assessor adoption/DEV-19 remains separate and open.
- [ ] **Keegan:** B4 producer: build `exposure_evidence` (verified items with `class`, `symbols`, `session_index`) from the evidence store into the runtime context, for both modes (IDEA-075 B4 lists Yao Zhu; this checklist puts code with Keegan). Bring it forward from Oct 24 if possible; see the B4 line under Oct 24.
- [ ] **Keith:** only if `MODEL` is chosen: the exposure-level LLM call (once per session and on each new verified filing), with its own pinned Markdown prompt like #158's, through the same routing and OpenAI budget, its I/O in the round log. Criteria in a ledger entry first.
- [x] **Isaac:** activation tooling: signed rehearsal/live preparation and qualification merged with #164 (IDEA-057 SLM-01/SLM-RV1); explicit signed/live acceptance and routing pins are retained. Deploying the new bundle remains Yao Zhu's separate item.
- [x] **Isaac:** SP-NET D2 records explicit user approval and implements the reviewed signed/live application scope for the same AIand/OpenAI primary/runtime HTTPS destinations in its own PR. Earlier review-only refusal is superseded. KMP-RIGHTS01 compatibility, model/release adoption and hosted qualification remain separate; no AWS change.
- [x] **Keith:** public terms capture/register supplied: [KMP-RIGHTS01](MODEL_PROVIDER_RIGHTS_20261018.md), exact model licences, submission/retention/audit scopes and capture hashes. Raw403 versus rendered text distinguished. Keegan review, account-contract applicability/signed financial-policy compatibility and durable private archival remain open; GAP-23 is not closed.
- [ ] **Keith:** check the AIand balance covers the run: AIand token usage from the trial (IDEA-057 M4) projected to Nov 12, with a margin. An empty AIand account leaves every assessment UNAVAILABLE.
- [x] **Keith:** scored-run behavior recorded in IDEA-057 KMP-02: frozen automatic pacing/credit fallback, provider/verification/UNAVAILABLE handling and autonomous safety only. Development operator K1–K4 interventions do not authorize manual key removal/restart/revert after scored activation (F-114/F-117). Actual release selection/adoption remains open.
- [ ] **Keith:** freeze the routing file and both stage prompts with the Oct 22 parameters; any later prompt edit is a new release before activation, never after.
- [ ] **Keith:** in the Oct 22 trial summary, record the disposition of the real-evaluation blocker (T01 / independent labels / post-cutoff check, IDEA-049-A): what ran (the trial's M9 sample) and what is declared as not run.
- [ ] **Yao Zhu:** during the trial, record memory use on `primary` (`systemctl show -p MemoryCurrent` for each unit, `free -m`) once a day. Units may use up to 3 GiB on a 2 GiB `t3.small` (#60). **Baseline 2026-10-17 15:27 UTC (before the trial):** 1401 of 1909 MiB available; runtime 65, evidence 57, uploader 53 MiB (IDEA-066 PC-AWS09).
- [ ] **Isaac:** decide #60 from Yao Zhu's numbers: keep `t3.small`, lower the unit limits, or resize (a resize costs money and needs Yao Zhu's OK and a Terraform apply).
- [ ] **Isaac:** on the first signed rehearsal rounds, with the on-chain check, confirm the ai-seeds round logs carry every routed stage's model I/O and reasoning, and record cost and latency per round (DR-11).

### Decisions due Oct 19

- [x] **Keegan:** decide and record the rehearsal shape (D-DN-02), including what happens if Gate A only passes on Oct 21. If Gate B slips past Oct 20, record the shortfall as a deviation (GAP-04). Done 2026-10-17 (IDEA-049-D D-DN-02, #140).
- [x] **Keith:** first-trade options recorded in KMP-SIGN01. Recommend existing Oct21 00:00–Oct22 00:00 UTC buy window after gates; earlier development window needs a separate reviewed release/version event. Isaac decides.
- [x] **Isaac:** SP-D1 selects the existing Oct21 00:00–Oct22 00:00UTC window, after all gates; recorded here for Yao. No earlier-window release. A missed window needs an explicit reviewed follow-up, never an out-of-window trade.
- [x] **Isaac:** SP-D2 adopts Keith's conditional profile rule: measured EQUAL_WEIGHT on Oct20 if S1 inputs/weights/parameters/EXP007/B4 are unqualified; otherwise explicitly adopted exact S1. Actual built profile/hash and final caps review remain open in Keith/Isaac Oct20 steps.
- [ ] **Keith:** after Isaac's selection, build/hash the final measured Oct20 profile. The proposal and interim shadow profile do not complete this item.
- [x] **Keith:** POLICY-HOLD proposal in KMP-SIGN01: retain the existing hold pending a separately reviewed bounded alternative; preserve chain-safe sizing/freshness. SP-D4 records Isaac's decision and corrects the HALT terminology.
- [x] **Isaac:** SP-D4 retains the existing bounded per-symbol price-jump hold, including Class1/terminal obligations, until comparable chain reconciliation/expiry. Obligations stay outstanding; delayed urgent exits are an accepted risk. This is not a new global HALT; actual hosted clearing/expiry evidence remains Yao/Keith.
- [x] **Keegan:** confirm the trial bars. Done TR-AC2: reviewed and confirmed PR166 TRB-01A–E before the planned first job; sample seed/method frozen. Actual trial/label evidence and later adoption remain open.
- [ ] **Keith:** keep or move the Nov 11 15:00 UTC flatten, and record it in IDEA-035 C4 (#107).
- [ ] **Keegan:** settle open choice O2 (what ships if EXP-007 is inconclusive) **before** EXP-007 runs, since it is part of the pre-registered decision rule (IDEA-075 §16, EXP-007 status).
- [ ] **Keith:** after O2, run EXP-007 on token session bars up to the Oct 16 close (IDEA-075 B1) and record the result by Oct 19.

## Keith prerequisite review — Oct18 (KMP-02)

Delivery verified in IDEA-066 PC-REL04: PR168 merged into this checklist branch at `622c522`; its approved protocol/rubric/register and public manifests are carried on the V3-REL01 release branch; the complete checklist/quote handoff remains here. Keith's pre-release proposals/handoffs are supplied. Yao confirms PR168 review/merge approves the unsigned v3 protocol (PC-REL05); Keegan proceeds with release implementation, retaining KMP-P2 and actual measurement/label/profile gates.

- [x] **Yao Zhu:** prepare/hash retrospective deterministic blind packet (PC-LABEL02): four filings/five documents, all 43 audit requests matched, ten source artifacts verified; private source/answer separation checked. This is separate from v3 M9.
- [x] **Yao Zhu:** return two AI readings for PC-LABEL02 (R1): both original files retained; all31 exact source/hash/quote spans validated. AI provenance and declined/limited independence remain explicit.
- [x] **Yao Zhu:** return the baseline-blind AI adjudication for PC-LABEL02-R2; validate27 final supporting spans, freeze exact gold hash and score four original representatives with39 repeats separate. Broad flag agreement4/4; strict evidenced adverse matching0/1, because metadata-only output lacks source-text support. AI provenance retained; T01/v3 M9/human-ground-truth qualification stay separate.
- [ ] **Yao Zhu:** review PC-LABEL02-INJ01 benign-link instruction detection in the exact new routed configuration with Keegan peer review/regression evidence; preserve the historical incomplete result and injection defenses.
- [x] **Yao Zhu:** verify receipt of the supplied original d8aa7d5 bundle against source/sidecar/manifest/CA (PC-REL08:195 files/234 checksums). Installation is separate.
- [x] **Yao Zhu:** investigate PC-SRC01 DOJ response-size failures and implement bounded repair/current-head evidence (PC-FIX01, PR174; 1,630 local tests passed). Final report/raw retention is complete in PC-GAP02.
- [ ] **Yao Zhu:** after installation, qualify DOJ polls/restart/report on the host. Keegan prior-window disposition is complete (PC-GAP02-RV1: retain FAIL/no DOJ waiver); actual post-fix coverage remains open.
- [x] **Yao Zhu:** independently verify supplied86b1476 tar against original published/CI gzip, manifest, exact Git, all235 checksums/196 source files, BUNDLE.env and CA (PC-REL09). No contents executed before verification.
- [x] **Yao Zhu:** PC-PREP02 provenance reconciled under existing PC-DEC01; approved checker correction pushed and tested in PR177, original unchanged86b1476 package7/7 PASS with separate verifier4eb33bb. No new binary needed for local-verifier correction; historical FAIL retained.
- [ ] **Keegan:** include merged PR177 in the next exact reviewed release and verify its original bundle/manifest binding. Isaac reviewed/merged it on2026-10-19 (MERGE-RV20261019); no checker-only rebuild is needed for already accepted original86b1476.
- [x] **Yao Zhu:** replace the invalid AIand key preserving all other runtime-secret fields; authenticated host catalogue/high-effort checks PASS (PC-PROV03). USD currency confirmed; original401 retained.
- [ ] **Yao Zhu:** complete remaining account-expiry/funding/usage/rights reconciliation; balance endpoint403 leaves140+ owner-reported. Actual served effort/first-reply evidence remains open. No further key replacement is required by the passing catalogue check.
- [ ] **Yao Zhu:** verify actual preserving trial ledger setup and host/provider qualification before paid testing. 2026-10-18 (PC-DEPLOY01/02): ledger created once and preserved across the ea25b52 redeploy (SQLite backup `2a20adc1…`; policies matched routing read-only); OpenAI served identity/effort and AIand Kimi K3/GLM 5.3 high served identities observed in real jobs. Remaining: owner `status`/`export` snapshot with hashes, AIand funding/expiry, and the UNKNOWN-charge reconciliation. Reviewed PR174 is merged and new86b1476 original release is delivered (PR174-REL01), including atomic8M total/2.5M UTC-day maximum/UNKNOWN reservations, accounting quarantine, clock guard and unsigned-only preparation. Explicitly prepare/pin the capped trial example (SHAa5fca50a…22d8d), preserve all charges/latches, and record installed source/config, status/export/P0 and first-job/ACK. No repeat protocol approval; no ledger reset. PR133 stays open.
- [ ] **Keegan (code/release review), Keith (protocol/affordability):** [PR #179](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/179) / IDEA-083, assessment time budget. **Decided by Yao 2026-10-19:** raise to ≤180 s, OpenAI share ≤60 s, reviewers in parallel with their own allowances, effort unchanged (lower it only if latency remains), declare DEV-22. must land before the Oct 26 freeze. Also decided (B11): when OpenAI reaches ASSESSED, reviewers only confirm or block it, never replace it; if no reviewer finishes, OpenAI's result stands (recorded INCOMPLETE); any dissent → ABSTAIN. Criteria AB1–AB15. The first fixed job (IDEA-066 PC-DEPLOY02, cadence:1991492#1) had OpenAI ASSESSED but the combined result UNAVAILABLE (`ASSESSMENT_DEADLINE_EXCEEDED`, 60,019 ms; Kimi K3 step 33.8 s). Reviewed config/code change only; keep the original job records. Isaac has now implemented this at the user's request in [PR181](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/181), stacked on179/180; see PC-IMPL18101. PR179/180/181/182 are now merged; code review/reconciliation is complete. Remaining: exact release qualification (PR183), Keith protocol/affordability and coordinator/operator host timing/charges/ACK; no deployment is implied.
- [x] **Isaac:** runtime design review of PR179 delivered in [PR180](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/180), IDEA-083 IR179-RV01 / PC-RUNTIME17901. Eight source-linked findings cover deadline/worker-drain separation, concurrent audit serialization, the global six-tool-call budget, AB1/B11/result identity, dispatch/late accounting, signed safety/recovery and composite watchdog evidence. Current-path focused129 tests/120 subtests PASS,0 skips (local PostgreSQL14.24); this does not accept the future180s/parallel implementation. Isaac subsequently supplies implementation/evidence in PR181 below; Keith retains protocol/affordability and the next coordinator/operator retains host qualification.
- [x] **Isaac:** implement Keegan's IDEA-083 work, delivered in [PR181](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/181), PC-IMPL18101 / IDEA-083 AB-IMPL01. 180s ceiling; primary ≤60s/one third; parallel reviewers ≤90s each; deterministic B11; separate canonical routed ID linked to unchanged primary ID/content (Isaac approved); owned late workers, serialized audit, global six tools and conservative UNKNOWN charges. Final local pushed runtime c8e8150:2079 passed/9 explicit platform-external skips/3272 subtests; expanded components14/257. Goldens reviewed; DEV-22/research parity recorded. Org CI billing-blocked #98 (zero steps); no Linux/systemd/original release or actual host PASS claimed. Keegan review/release, Keith affordability, coordinator/operator hosted qualification remain open; no AWS, paid calls or keys.
- [ ] **Keegan:** review merged PR178 and the local non-CI `ea25b52` bundle (PC-FIX02/PC-BUILD01; differs from CI 86b1476 only in `providers.py`, manifest and BUNDLE.env), and add reviewed version-switch support: `runs` UNIQUE(wallet_id, chain_id) means every new build or the Oct 20 profile currently needs a new trial database (PC-DEPLOY01-B1).

[Model prerequisites](MODEL_PREREQUISITES_20261018.md) and its linked budget,
blind-label, provider-rights and signing/profile records carry the proposed v3
work. V2 PC-BUD03/TR-AC2's US$40/US$10 policy remains historical; it is **not**
the intended v3 policy. Yao approved KMP-BUD01 through PR168: US$50 cumulative/
US$2 prior/US$48 remaining at the reported balance, zero permanent reserve and
explicit pacing/trial stops (PC-REL05). Repeat protocol approval is not pending. Actual affordability is NOT_MEASURED,
actual M9 drawing/labels NOT_RUN pending Yao's immutable usage/job/source export.
No new keys are requested; stored keys and provider validity are separate checks.

## Side note: interim profile for an early dry run (optional)

The interim profile is already running in the owner-reported Oct 17 shadow run (PC-AWS07). It is replaced on Oct 20 by the final profile; its mandatory coverage/hash record remains below. Gate A is unsigned, so the interim values only change shadow HOLD/BUY decisions.

- [x] **Keith:** on the capture server, summarise the files so far into a **new** directory, without stopping the capture: `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <interim>/summary.json --min-days 2`. If a token has fewer than 10 US-session samples the tool names it; rerun with `--min-samples` at the lowest count it reports, never below 5. Done 2026-10-17 (`--min-days 2 --min-samples 9`).
- [x] **Keith:** build the profiles: `python -m larp.strategy.profiles --summary <interim>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <interim>/profiles`, and send `rehearsal-live.json` to Yao Zhu. Done 2026-10-17 by Yao Zhu from Keith's summary (`d951207f…`).
- [x] **Isaac:** a quick look at spread, impact, gas and minimum trade size in Keith's interim summary and profile. Done: Keith and Isaac approved it for the shadow run (2026-10-17).
- [ ] **Yao Zhu:** supply the original interim capture hash/full summary bytes for KMP-QUOTE01; the later snapshot cannot substitute for that provenance.
- [ ] **Keith:** after Yao's export, verify and record the original interim capture/summary hashes in IDEA-063 alongside the existing two-day/nine-sample settings and reported profile SHA.
- [x] **Yao Zhu:** if the weekend Gate A setup is done, run the Oct 20 steps 5–8 early with this profile. On Oct 20 the final profile means rerunning `prepare`, rebinding the manifest and a fresh `service init`/`activate`, because the profile hash is pinned in the runtime config. Done 2026-10-17: shadow run live, first round ACKed by the receiver (IDEA-066 PC-AWS07).

## Oct 20: profile day, in this order

The capture ends at Oct 20 00:00 UTC (08:00 SGT).

1. [ ] **Keith:** full summary with the default coverage (3 UTC days including a weekend, 10 samples per token per regime): `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <dir>/summary.json`.
2. [ ] **Isaac:** confirm the quoted amounts already net out route fees, so `fee_bps = 0` holds (#119). PR #157's reporting/evidence correction is reviewed and merged 2026-10-18 (IDEA-063 FN-RV157); fee netting remains UNVERIFIED. Keith's profile review remains separate (#120).
3. [ ] **Keith:** build the decided profile (its `per_trade_cap_units` and `gas_top_up_cash_units` must each be ≤ 35 USDT, the signer's development cap): `python -m larp.strategy.profiles --summary <dir>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <dir>/profiles`.
4. [ ] **Isaac:** owners' review of the summary and `rehearsal-live.json` (#120); record both hashes in IDEA-063 and send the profile to Yao Zhu.
5. [ ] **Yao Zhu:** fresh read-only wallet capture with the balance RPC (`prepare_shadow.py capture --balance-rpc-config deploy/activation/balance-rpc/selected-providers.json`), then Gate A `prepare` within five minutes with the same `--balance-rpc-config`, so both RPCs go into `runtime.json` (#145); install the configs (`runtime.json` mode 0644); bind them to CI's manifest (`preflight --bind`).
6. [ ] **Yao Zhu:** `service init`, then `service activate` with Keegan named as reviewer; start the evidence, runtime and uploader services; enable the archive timer.
7. [ ] **Yao Zhu:** confirm the first shadow round is ACKed by the real ai-seeds receiver (R-01), which starts the 24 h ingestion clock, and send the round ID to Keegan.
8. [x] **Yao Zhu:** restart drill (kill a service, check it returns on the same build with an incident logged) and check the first hourly anchor (DR-13, DR-15). Done early 2026-10-17 on the shadow run: back in 10.3 s with one RESTART incident; the 11:00 anchor verifies against the journal, COMPLIANCE-locked (IDEA-066 PC-AWS08). Repeat after the Oct 20 re-activation only if Keegan asks.
9. [ ] **Isaac:** only if a dev window was chosen: watch the runtime's first approve plus swap on the dev wallet and check it on chain against the logged round (DR-02, DR-03).
10. [ ] **Keegan:** only if the dev-window trade in step 9 occurred, perform the Gate B review in IDEA-042; otherwise use the Oct 21 Gate B review after its first signed trade. The host-side crash tests (DR-04, DR-05) are step 3 of the Oct 21 list.

## Oct 21

- [x] **Keegan:** review and merge the incident-backup fix #163 (IDEA-082). Merged 2026-10-18 at `2b4f397`; exact-head mirror39091506616 passes all four jobs. The combined `7a0ea14` bundle includes it; release handoff accepted in PC-REL01; the fixed release's hosted incident-backup ACK remains open (IDEA-066 PC-CI02).
- [x] **Yao Zhu:** after Oct 18 00:00 UTC, check archive health. Done 02:46 UTC over SSM with read-only SQL: healthy, 00:00 daily backup ACK, latest anchor ACK, all 44 audit chunks ACK, no HALT or delivery breach (IDEA-066 PC-AWS11). Historical incident backup remains PERMANENT; #163 still needed.
- [x] **Keegan:** decide DOJ/BIS gap treatment. Done PC-GAP01: fixed-window historical-backfill explanations for the unsigned trial, retaining raw reports, actual error/cadence checks and INCOMPLETE runtime coverage; see MODEL_TRIAL_HANDOFF_20261018.md. No signed/final source acceptance.
- [x] **Yao Zhu:** collect/hash the fixed Oct17 11Z–Oct18 11Z report and raw snapshot. PC-GAP02 verifies all31 hashes and reproduces raw FAIL; DOJ96 RESPONSE_TOO_LARGE errors remain unexplained. No combined explained report was produced.
- [ ] **Yao Zhu:** retain/share the private fixed-window raw evidence for any further byte-level audit. PC-GAP02-RV1 independently reviewed the published metadata and retained FAIL/no DOJ waiver; it does not claim a second private raw-byte reproduction in the cloud. Owner verification and hashes remain in PC-GAP02.
- [ ] **Keegan:** review Gate A item by item in IDEA-042, using the gap report and Yao Zhu's host reports.
- [ ] **Yao Zhu:** crash tests at each execution step on the host (DR-04, DR-05), then switch the runtime to signed rehearsal mode.
- [ ] **Isaac:** if not done on Oct 20: check the runtime's first approve plus swap on chain inside the rehearsal buy window (Oct 21 00:00 – Oct 22 00:00 UTC).
- [ ] **Keegan:** after Isaac's check, the Gate B review in IDEA-042 (if not done on Oct 20).
- [ ] **Keegan:** keep the daily rehearsal log (5+ days including the Oct 24–25 weekend, DR-21) from the round logs and alarms, including model availability, latency, OpenAI spend and AIand usage per day. A late start is recorded as a deviation (GAP-04).
- [ ] **Keith:** blind independent labels for the trial sample (M9, IDEA-057).

## Oct 21–26: rehearsal drills

- [ ] **Yao Zhu:** on the hosts: automatic HALT drill, hourly-anchoring criteria 1–6, a restore into an empty database, and the final-wallet switch with a throwaway config (DR-13, DR-15, DR-16, DR-17).
- [ ] **Keegan:** replay a shadow day from the exported journal and check it reproduces the head (DR-19).

## Oct 22 cut line

- [x] **Keegan:** renumber #123's ledger entry (IDEA-058 is already the Gate A entry) and retarget #123 to the integration branch. Done: #123 is now IDEA-075 and targets the integration branch.
- [x] **Isaac:** after that, review and merge the S1 plan (#123). Done 2026-10-17: reviewed (TRV-01 to TRV-05 addressed) and merged as IDEA-075 and EXP-007.
- [x] **Keith:** S1 code #131 is merged; repository review RV-131 is recorded in IDEA-076. Weights, live inputs and parameter decisions remain separate tasks below.
- [ ] **Keith:** freeze the S1 weights from token session bars up to the Oct 21 close (`python -m larp.strategy.s1 freeze-weights`).
- [ ] **Keith:** propose final values for every S1 parameter (§12) and open choices O1 and O3–O6.
- [ ] **Keegan:** confirm Keith's S1 values and choices.
- [ ] **Keith:** report the unsigned trial verdict in TRB-01A order, with actual hours, all frozen bars, M9 recall/omission/TP/FP/FN and unqualified routes; report supplemental probes and signed-rehearsal results separately. Signed days cannot supply the 72 unsigned hours (DR-11, TRB-01E).
- [ ] **Keegan:** confirm or reverse the Oct 20 rehearsal decision from Keith's separate unsigned/signed reports: AIand routing or deterministic (DR-11, #97). Preserve an inconclusive/failed trial verdict and list remaining adoption gates; any exception is an explicit decision/deviation, not a passing result. A reversal is a version event before final activation.
- [ ] **Keith:** set the 11 live evidence settings in `intelligence.v1.json`, each with a reason.
- [ ] **Keith:** SKHYB red flags: build it or record a deviation (#39).
- [ ] **Keith:** decide #55 (stale marks) and #56 (flatten on the BNB held at the cut-off).
- [ ] **Keith:** run the pre-registered after-cost comparison and staggered evaluation (#37, #38).
- [ ] **Keegan:** propose the operations decisions D-DN-01, 04, 06, 07, 08 and 11 (IDEA-049-D §5).
- [ ] **Isaac:** decide those operations items from Keegan's proposals.
- [x] **Isaac:** review and merge #125 (automatic CLOCK HALT clear, D-DN-10). Done 2026-10-17: reviewed and merged (full suite 1790 passed, 9 skipped, on the merge with the integration branch). The host check is in Yao Zhu's route-check line above.

## Oct 24: S1 build (IDEA-075 §15)

- [ ] **Keegan:** LLM exposure limiter (B4). Its input isn't wired yet, so the limiter stays NORMAL until this lands (#131). With the LLM in the rehearsal (PC-DEC03), land it as early as possible: until then the rehearsal tests the LLM running under signing, but not its effect on exposure.
- [ ] **Keith:** trend-guard input from token session bars (DR-08). Until it's wired, the trend guard stays UP (#131).
- [ ] **Keegan:** session-close job and round-log fields (B5).
- [x] **Isaac:** B6 per-leg attempt/execution-window code reviewed and merged in #165 at817eb71 (EB-RV2:2021 passed /9 platform-or-external skips /2981 subtests). Proposed values still need Isaac/Keith measured-cost/profile freeze; Keegan retains exact-release Linux/mirror evidence, Yao hosted qualification.
- [ ] **Keegan:** write up the T4 dev-wallet run from the rehearsal round logs (B8, Oct 24–26).
- [ ] **Keith:** check the T4 results against what S1 should have done.

## Oct 26–29

- [ ] **Keegan:** deviations-register rows for exceeding the proposal's 80% / 20% / four-name limits (B7).
- [ ] **Keegan:** coordinate the team disposition of the declared event-calendar planner (G-52 / DEV-20): implement and verify the adopted planner, or record an explicitly approved, reasoned final deviation. Current DEV-20 remains OPEN/not built; resolve the decision by the Oct22 cut line and the release disposition before Oct26. See [PC-HAR01](HARNESS_READINESS_AUDIT_20261018.md).
- [ ] **Keegan:** every deviations-register row FINAL, including DEV-18 (standby), and the services list (DR-18, GAP-62).
- [ ] **Keegan:** activation pack and the Gate C review (DR-22). The pack's runtime config names `aiand_routed` with the frozen routing file, unless the Oct 22 decision was deterministic.
- [ ] **Keegan:** team acceptance that the final assessor and harness are the declared agentic system, with the model and source deviations listed (IDEA-049-A A-DEC-004, A-REQ-079), before Oct 26.
- [ ] **Keith:** sign off DR-08, DR-09, DR-10, DR-11 and DR-14 in IDEA-042. DR-11 needs the LLM assessor running with signing in the rehearsal, with complete model I/O in the round logs.
- [ ] **Isaac:** sign off DR-01 to DR-06 in IDEA-042.
- [ ] **Yao Zhu:** sign off DR-12 and DR-16 (live sources, hosting) in IDEA-042.
- [ ] **Keegan:** sign off the remaining DR items (DR-07, DR-13, DR-15, DR-17 to DR-22) in IDEA-042.
- [ ] **Isaac:** confirm the final-wallet credential issuance under Q-35 and obtain the applicable `AI_SEEDS_SECRET` by Oct 26. If a new secret is issued, deliver it to Yao Zhu securely, never in chat or an issue (GAP-52); do not assume the development secret applies.
- [ ] **Yao Zhu:** put the final wallet's secret into AWS Secrets Manager (`put_service_secrets.sh`). The script replaces the whole runtime secret, so re-enter `LARP_AIAND_API_KEY` and `LARP_MODEL_API_KEY` too; without the AIand key the runtime refuses to start. Never re-`init` the model budget ledger for the new wallet: it covers the whole run.
- [ ] **Isaac:** first-gas swap on the final wallet (about 6 USDT) before Oct 29 00:00 UTC (#106).
- [ ] **Keegan:** send the organiser questions Q-39 (scoring, BNB in equity), Q-04, Q-06, Q-08, Q-14, Q-33 and Q-35 (GAP-42).

## Housekeeping

- [ ] **Keith:** confirm A-T15 on #25 (issuer IDs fixed in #78; the proof passes) so it can be closed.
- [ ] **Keegan:** reconcile #98 with accepted mirror builds (PC-DEC01): organization Actions still fails on billing, so do not call billing fixed. Record whether #98 is retained or retired as not planned, and update trackers #22/#42 with actually completed work.
- [x] **Keegan:** close #128 by hand; it didn't close automatically because #129 merged into the integration branch, not `main`. Done: closed 2026-10-17.
- [x] **Keegan:** close #90: D1–D6 are recorded (#110) and built (#115, #116). #36 then waits only on #92. Done: closed 2026-10-17.
- [x] **Keegan:** retarget #126 to the integration branch before it merges. Done.
- [ ] **Keegan:** coordinate branch disposition (2026-10-17): 61 remote branches whose commits were all in the integration branch or `main` were deleted. These seven hold commits found nowhere else and have no open PR; each owner decides whether to keep, reopen or delete them:

  | Branch | Last commit by | Earlier PR | Decides |
  |---|---|---|---|
  | `claude/gate-a-inputs` | Claude session | #89 (closed) | Keegan |
  | `claude/issue31-day-roll-tests` | Claude session | #82 (closed) | Keegan |
  | `claude/issue59-systemd-runtime-dirs` | Claude session | #83 (closed) | Keegan |
  | `claude/local-ci-20261015` | Cookiemunchrr | none | Keegan |
  | `docs/idea-052-timesfm-20261015` | Cookiemunchrr | none | Keegan |
  | `codex/pr-review-system-20261012` | wtvlol | none | Keegan identifies the responsible team member before disposition |
  | `codex/thin-path` | Keegan | #10 (closed) | Keegan |


## V3-REL01 / PC-AWS06-RV1 — release-agent update, Oct18 UTC

[PR169](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/169)
contains the next unsigned release candidate from integration817eb71 (#165 and
#167), KMP-P2 fix6955eaf, OpenAI-primary services/DEV-19 and approved PR168
protocol/rubric/register. No repeat approval. Full pushed61a123a verification:
**2029 passed,6 skipped,2981 subtests**, Linux/Python3.12.14/PostgreSQL14.24;
external corpus1 and actual-systemd5 skipped, Linux bubblewrap ran. No xfails.
Focused85 tests/111 subtests, deviation rendering and offline demo pass.

[Release/evidence record at published0441806](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/996ef0f/docs/build/LLM_V3_RELEASE_20261018.md)
records prospective criteria, corrected red/green tests, PR165 review/inclusion,
PC-AWS06 report review and full log hash. The migration/roles/TLS review is
complete for reported empty-DB primary checks only; signer-host login, populated
upgrade and new-release deployment stay separate. Source migrations/roles/TLS
configuration are unchanged from the reported bb46234 bundle. Preserve the
initial runtime timeout, admin verify-ca versus runtime verify-full distinction,
and four distinct terms files covering six source entries.

The release agent attempted the authorized direct mirror push (exit128, repository
not found) and direct Actions dispatch (HTTP404) to Cookiemunchrr/larp-ci-mirror.
This is an actual access blocker; GitHub connection access was requested, not
repeated release permission. No new mirror run, binary, checksum or manifest has
been produced. The release agent resumes push/dispatch and original-artifact
verification after access restoration. Old7a0ea14/its handoff ZIP is not this
release. Org billing is not fixed and no all-job CI pass is claimed.

Pending: Yao's actual in-flight stop-cap enforcement, P0/P1/P2 and host start;
Keith's real usage forecast and blind labels; Keegan's fixed-window gap review
after Yao supplies it after Oct18 11:00 UTC/19:00 SGT. Pending gap report does not
delay building. No AWS, paid-provider, signer or deployment action performed.
PR133 remains open and unmerged; PR126 is untouched.


## V3-REL02 / PC-REL07 — original unsigned release delivered

[GitHub prerelease](https://github.com/Keegan4/Keegan4-larp-ci-mirror/releases/tag/llm-trial-v3-d8aa7d5),
frozen source `d8aa7d53e5e27543135f8729ff7a7afd4450278a`. User selected their
private Keegan4 mirror; direct push and dispatch completed. Acceptance
[run39111854179](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39111854179)
passes all4 jobs:2029 tests/2981 subtests;6 skips include5 actual-systemd tests
subsequently passed separately (5 tests/5 subtests), plus1 external corpus.
Terraform, Docker/demo and both-role bundle provisioning pass. PR169 merged
ordinarily at95f6a8f. PR133/126 remain open. No repeated protocol approval.

Original CI artifact12129754965 downloaded and independently verified: ZIP
digest, sidecar, external/embedded manifest,195 release files,234 bundle-file
checksums, source/repository/mirror identity and packaged CA. Six actual assets
are uploaded to the prerelease. The publishing-only branch/run39112659498
reverified and uploaded originals with a scoped mirror Actions token after
direct cloud uploads returned401; it did not rebuild the binary or substitute
for acceptance CI. Frozen tag/source stay d8aa7d5; org billing is not fixed.

| Item | SHA-256 |
|---|---|
| Original bundle | `9930f361dce63480ec1966082b2ca0d0e4360ad1512b35a9eca57ef00bd90b89` |
| External/embedded manifest | `8bed25395fa23947f93193f2eb48acfbf1091e8b0ad3aa37ca4cafc899b149e0` |
| Actual packaged RDS CA | `d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b` |

[Machine-readable evidence](evidence/llm-v3-release-20261018.json). Sendable
folder/ZIP are in `/workspace/exports/larp-d8aa7d53e5e2-unsigned-v3` and `.zip`,
including the real deployment binary. AWS/host deployment, provider/funding/
rights checks, in-flight trial-cap enforcement and start remain with Yao.
Keith supplies actual usage/labels; team decides adoption. Keegan's fixed-window
gap-report review is pending until Yao supplies it after19:00 SGT. No paid calls,
AWS changes, host deployment or future coverage pass claimed.


## PR174-REL01 — new original LLM bundle delivered

PR174-R1 fixes and frozen source `86b14761324faeb8f57df5c0d86ff00320b4361c` passed
[private mirror39126353379](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39126353379), all4 jobs PASS. Full Linux/
Python3.12.15/PostgreSQL14.24:2064 passed,6 skipped,2992 subtests,236.95s;
actual systemd5 tests/5 subtests separately PASS. Terraform, offline demo,
restricted Docker and both-role bundle provisioning PASS. Local same-source
Linux2064/6/2992 passed in173.13s. Skips: external corpus1 plus5 systemd cases
exercised separately. No xfails, golden changes or weakened acceptance checks.

PR174 merged normally at `100d49327f4f50e13ff4c16f297b1acccf187496` after green CI and
original-artifact verification. No issue/inline comments or submitted reviews
existed at either inspection; the three direct-review findings and regressions
were corrected before release. Frozen source/tag stay unchanged.

[Published unsigned LLM prerelease](https://github.com/Keegan4/Keegan4-larp-ci-mirror/releases/tag/llm-trial-pr174-86b1476)
has six actual assets: original tarball, original sha256 sidecar, external
manifest, VERIFICATION.json, BUNDLE.env and README. Dedicated publication-only
[run39126901213](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39126901213)
reverified/uploaded originals using the mirror's scoped Actions token. It did
not rebuild the bundle or replace acceptance CI. Tag/source and asset API
sizes/digests verified. Organization billing is not claimed fixed.

| Verified original | SHA-256 |
|---|---|
| `larp-86b14761324f-x86_64.tar.gz` (98,383,598 bytes) | `277fd2b6e4b26e0725b38c1f4f2bcb35cab7e25fe3857639683b283e7b684343` |
| External/embedded manifest | `0053cbc9c7eb68c3ec82dfc519f01979a5e3a0171fee784d43d12b76c7dfff2f` |
| Actual packaged RDS CA | `d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b` |

Original artifact12135774607 ZIP digest verified;196 manifested source files
and235 full-bundle checksums checked. Registered repository stays the challenge
repo; build_origin honestly names the Keegan4 mirror. The packaged trial config
hash is `a5fca50a6f3e166b48299a0d29e686aa6dbfd2428f4bb011839acc684b222d8d`.
Yao must explicitly prepare/pin this capped unsigned trial file; the legacy
preferred file remains separate. No ledger reset, policy removal or automatic
signed adoption is authorized. [Machine-readable evidence](evidence/pr174-release-20261018.json).

PR133/126 stay open. Code/review/CI/new-original-bundle work is complete. Yao
retains private provider/account/funding/rights checks, preserving ledger setup,
host install/bind/activate, actual post-fix polls/restart/new observed window
and first assessment/receiver ACK. Keith retains actual usage/labels; team
retains adoption. PC-GAP02-RV1 review is complete on retained metadata: original
raw FAIL remains; DOJ96 actual errors cannot be waived and no new host coverage
is claimed. These result-only records change no manifested runtime file.


## Signer startup follow-through — PC-SIGNER-READY01 (Oct18)

- [x] **Isaac:** implement and deliver [PR176](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/176), separately from source/provider/network/funding PRs. Both dev/live refuse explicitly pending cap labels; check/run require loadable hash-pinned router evidence for a policy spender before DB/key access. Check reports the evidence hash, local-only scope, signing disabled and no Gate B acceptance. IDEA-070 SR-01:139 tests/219 subtests PASS,0 skips, with local disposable PostgreSQL14.24 and synthetic evidence/keys. Org run39133862711 executed zero steps due confirmed billing/#98; no new signed bundle/host qualification claimed.
- [ ] **Keegan:** include merged PR176 with the adopted #27 implementation in the exact Gate B release and verify original CI bundle/manifest/config bindings. Isaac reviewed/merged PR176 on2026-10-19 (MERGE-RV20261019). PR176 does not choose a lifetime, approve caps or establish real source provenance.
- [ ] **Isaac:** obtain complete verified source/imports/ABI/compiler/settings and deployed-code binding for #139. RE-03 also tried the public Routescan chain56 source API at13:59:09–10UTC: both router/facet requests returned HTTP200/status0 `chain not supported`. This is an access/coverage blocker, not an explorer-verification verdict. No source export/account supplied; use the retained export/vendor-request packet through an approved team contact. No vendor message sent. Keegan's independent source review and the existing router check still wait for that input.

Remaining owner order: source intake **Isaac**, independent review **Keegan**,
real-artifact check **Isaac**; finite authority/margins decision and implementation
#27 **Keegan**, using source TTL plus **Yao** host timing; measured profile/fees/
full-holding checks **Keith**, exact #44 approval **Isaac**; signed release
**Keegan**, provisioning/config/isolation/session/drills **Yao**, key placement
**Isaac only during Yao's approved session**. Native #30/provider and route-fee
#119 evidence remain separate rehearsal gates. PR171/173 were explicitly reviewed and merged into this tracker on2026-10-19; funding PR172 remains draft/open. No AWS, wallet key, transaction,
paid-provider or official receiver operation occurred; signing remains blocked.

## What Isaac can do next — PC-SIGNER-NEXT01 (Oct18)

Current merge status (2026-10-19, MERGE-RV20261019): PR176/177 are merged into integration; PR171/173 are merged into this tracker. PR139/172 remain draft/open; #27/#44 still require their recorded decisions/inputs. The local implementation/proposal/qualification-tool work already
reported above is delivered; no new runtime fix or readiness pass is inferred
from this follow-up. No unchanged tests or failed public probes are repeated.

| Request now | Owner / exact deliverable | Isaac's next action after delivery |
|---|---|---|
| Qualify the reviewed release | Keegan supplies the exact reviewed release including merged176/177; the next coordinator/operator qualifies the host. PR171/173 are merged here. Keep source139/funding172 draft until their missing inputs/actions are complete. | Use the exact reviewed release for real source/native/route and signer qualification; code merge alone closes none of those gates. |
| Obtain real source | Isaac asks the team's confirmed Binance/Web3/LiquidMesh contact for complete verified router/facet/helper source/imports, ABI, compiler/settings and chain56 deployed-code/dispatch binding for router0xb44446b0c8e56988c34f7ff73ae904982b5fdda5, selector0xad43f73d, candidate facet0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603. Existing request packet is in PR139 ROUTER_SOURCE_REVIEW.md. No source/account input or contact is available to this agent. | Hash/inspect the original export; fill real RouterEvidence only for supported guarantees, obtain Keegan's actual independent review, then run the existing checker on Keith's artifacts. Do not sign or guess an ABI while waiting. |
| Resolve signing lifetime | Keegan: record C-OPEN-003/#27's adopted authority model, finite duration/margins and per-action windows; implement persisted original decision/admission/authority bounds across planner, commands, executor, signer and restart. Keith's review is already supplied. Yao supplies real queue/signer/approval-finality timing; Isaac supplies source-qualified route deadlines when available. | Run/inspect approve-confirm-requote, stale/expired/restart/uncertain-send acceptance against the reviewed implementation. Neither60s nor the kit's approximate30s is a measured adopted bound. |
| Supply measured policy inputs | Keith: finish capture/coverage and selected profile when available (planned Oct20), with original summary/report/artifact hashes, raw token scales, per-trade/top-up amounts, actual approve/swap estimates and fee-netting disposition. Yao: fresh reconciled full holdings/opening-state hash and matching execution config, after the last manual funding. | Run caps_review on those exact pinned inputs, assess full sell holdings/gas/top-up coverage, then record the exact #44 policy decision and hashes. Current40USDT captures and fallback gas cannot close it. |
| Arrange native-trace access | Isaac retains provider qualification ownership. Yao/team account owner: help supply an already-approved chain56 endpoint/account supporting exact prestateTracer diffMode with disableCode/disableStorage, canonical finalized reads and recovery-state retention. Keep account credentials in a private0600 external input file; supply its local path only. No signup/spend or service selection is inferred. | Run PR173's bounded qualifier on the known wallet funding transaction (or a supported wallet-native-credit receipt), review the sanitized proof/hashes, then hand accepted provider evidence to Yao for real-host checks. A public block balance is insufficient. |
| Reconcile and finish manual funding | Yao: confirm from actual run/signing/wallet state that the dev wallet has not made its first agent trade and has no in-flight work. Isaac: only after that confirmation, finish the existing MetaMask gas-funding plan if still needed and retain the public hash/amounts/UTC (PR172 handoff). This agent has no wallet UI/session. | Verify the supplied receipt read-only; Yao then takes the post-last-funding opening capture. No keys or seed phrase are sent to the assistant. |
| Prepare actual signed deployment | After the preceding approvals, Keegan supplies the exact reviewed Gate B release/bundle/manifest; Yao completes private run/build/DB/CA/router config pins, isolation/time/IAM checks, provisioning and the approved signer session, followed by hosted drills/round/ACK evidence. | Place the key only in that approved session, then verify the actual signed rounds and logs. No AWS or key-placement action is authorized/performed by this follow-up. |

Source intake, account access and funding UI are the immediate human inputs
Isaac can arrange. Final numeric approval, real route/native qualification and
key placement wait for their stated prerequisites. #119 fee evidence and the
measured floor/top-up remain open with Isaac/Keith; do not conflate a MetaMask
funding receipt with the bStock route's fees. The signer remains disabled.
These are requests for Isaac to forward, not messages already sent to teammates
or a vendor. No new policy, account, deployment or transaction is created.


## Reviewed prerequisite merges — MERGE-RV20261019 (Oct19)

User authorized review/merge. PR177 (exact approved mirror) and PR176 (signer
startup refusals) are merged into integration; PR171 (same-host scope labels)
and PR173 (bounded native-proof CLI) are merged into this tracker. Normal merge
commits only, reviewed head hashes matched. PR133 stays OPEN and now includes
the current integration base; five documentation-only conflicts retain both
source/caps and historical deployment/review evidence. No application conflicts.

Full prospective177+176 tree f6ebda0:2071 passed/9 explicit platform-external
skips/3040 subtests. Scope/native focused tree:67 passed/72 subtests, with an
additional8 PostgreSQL top-up tests/10 subtests. PR177 array/object negative
controls:14 passed/52 subtests, no runtime change. Org CI billing #98 ran zero
steps; no Linux/systemd/original release or host PASS is inferred. Final
combined-tree checks are recorded in IDEA-066 MERGE-RV20261019.

Remaining: exact release/bundle and host qualification; source/route/native
account inputs and measured profile/holding/caps/signing-session decisions.
PR126's older briefs conflict and need alignment with the current handoff;
PR179/180/181/182 are now merged; code reconciliation is complete. Exact-release
qualification is in PR183; protocol/affordability and host acceptance remain.
PR139/172 retain their input blockers.
No AWS changes, key access, model/chain/receiver live call or deployment.

Final combined-tree validation at pushed2202c15:282 tests/434 subtests PASS,
0 skips,30.71s (all four changes together, pinned Python/PostgreSQL). Source
code is unchanged by the following result-only documentation commit. CI remains
billing-blocked, and no AWS or hosted acceptance is inferred.


### Signer file readiness — PC-SIGNER-CHECK02 (Oct19)

The tracked signer-handoff signer.json is **sendable only as a labelled assembly
draft**, not final/ready to install. Its six run/build/DB/CA/router fields are
still null and its policy is explicitly pending decision. Current merged176
validator refuses it before service/key/DB access. Measured #44 inputs/approval,
real source/route evidence and #27 remain open; the coordinator/operator must
finish exact release/config/manifest/host assembly. Corrected handoff README
and IDEA-066 PC-SIGNER-CHECK02 give owners and exact file hash. No key belongs
in the JSON; key placement stays in Yao's approved session.

### Signer preparation after merged branches — PC-SIGNER-ASSEMBLY01 (Oct19)

PR133 now includes integration8c1e6df through normal merge cabc159. Two
documentation-only conflicts retained current source/caps evidence and the merged
IDEA083 acceptance; no application conflict. IDEA083 code review/reconciliation is
complete; PR183 supplies a separately reviewed release candidate/qualification,
not signer installation acceptance. Do not repeat the earlier draft179 blocker.

Isaac delivered the remaining offline assembly work in separate
[PR184](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/184),
stacked here for review: `python -m larp.signer.assembly` re-runs the pinned
numeric review, copies exact signed execution identity/CA/router bindings with
the signer DB role, checks production validators and writes a new key-free
candidate plus exact-hash report. **194 tests/349 subtests/0 skips PASS** with
Python3.12.14/PostgreSQL14.24, including malicious-intent/authority/startup,
signed-model preparation, and output symlink/non-overwrite/cleanup checks.
CI39210809471 runtime ran zero steps: verified failed-payment/spending-limit
annotation (#98), not a test failure or remote PASS. No real candidate assembled.

- [ ] **Source supplier / Isaac / Keegan:** real router/facet/helper evidence and
  independent review, then recorded-route replay; draft139/#138 remain blocked.
- [ ] **Keith/coordinator inputs, Isaac review/decision:** selected measured
  profile, fresh full holdings/top-up/approve/swap/fee quotes, then exact #44
  policy acceptance/hash. Existing historical caps and fallback gas are insufficient.
- [ ] **Keegan plus operator timing:** adopt finite #27 authority/margins/action
  windows, implement and qualify expiry/requote/restart/uncertain-send behavior.
  Keith supplied the conditional OptionA review; no finite lifetime is adopted.
- [ ] **Provider owner / Isaac:** private native-trace provider input and
  attributable route-fee evidence for #30/#119; native_trace stays off.
- [ ] **Coordinator/release owner/approved operator:** exact signed run/build/DB/CA/
  evidence values, registered manifest/config binding and host acceptance. Use
  PR184's preparation procedure after review; do not reuse unsigned identities.

The tracked old signer.json is unchanged, still has six null bindings and pending
caps, and is not ready to install. Candidate assembly success also keeps all
installation/signing/Gate B flags false. Key placement remains restricted to
Yao's approved signer session. No AWS, wallet/key, provider/model/receiver live
action, funding, signing or installation occurred. Details: IDEA-066
PC-SIGNER-ASSEMBLY01 and IDEA-049-C SA-01 in PR184.
