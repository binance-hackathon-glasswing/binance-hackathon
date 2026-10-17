# Pre-trading checklist (2026-10-17)

This is a snapshot of what stands between today and the scored run (Oct 29 – Nov 12 UTC), split into what the team does this weekend without the strategy profile and what runs on Oct 20 once the profile exists. It was checked against `codex/system-testing-20261012` at `1ab47ae` (#129 merged), every open PR (#123–#126, #130–#132), the PRs merged on Oct 15–17 and the open issues on 2026-10-17, so nothing below repeats finished work. Refreshed 2026-10-17 08:20 UTC against `bb46234` (#123 and #125 merged) and the open PRs #126, #130, #131, #139, #143, #144, #148, #149 and #151. Audited 2026-10-17 for the LLM path and against every open issue (IDEA-066 PC-AUD01). Times are UTC (SGT = UTC+8). The live backlog stays [INCOMPLETE_WORK.md](../INCOMPLETE_WORK.md). Tick items here as they finish, and remove the matching backlog line only when its whole item is done.

Review refresh: integration `a428bab` includes #130/#131/#143/#144/#148/#149/#151
and #159. Open review scope is #126/#133/#139/#155/#157/#158/#161, plus #163 opened during review. Completed
repository deliveries below are distinct from pending evidence, decisions and
host checks. Host results are prior owner reports, not fresh checks by this review.

**Every line has exactly one owner.** Work that needs more than one person is split into small pieces, usually one person proposes or does it and another reviews or decides. A piece that depends on another names it ("after …").

**Who does what (2026-10-17):** Yao Zhu owns AWS access, host operations and Terraform (IDEA-066 PC-AWS01). The one explicit exception is Isaac placing the wallet key in the separately approved signer-host session supplied by Yao Zhu; Yao still owns session access, provisioning and teardown. Decisions, reviews, merges, code and write-ups sit with Isaac, Keith and Keegan.

## Done

- [x] AWS hosts applied; `primary` online over SSM and smoke-checked (2026-10-16, IDEA-066 PC-AWS02).
- [x] Terms captured for five enabled non-EDGAR sources plus EDGAR (six retained files total); shadow source preflight passes; stricter SEC contact check (IDEA-066 PC-TERMS01/02, #129).
- [x] Real quote-cost capture running on Keith's server since 2026-10-16 18:19 UTC, set to run until 2026-10-20 00:00 UTC (#132, IDEA-063).
- [x] Route checker built (#102); network destination table approved by Keegan for section B (#113).
- [x] Balance RPC failover: up to four providers in order (#116). Chain-balance decisions D1–D6 decided by Yao Zhu (#110) and built (#115, #116).
- [x] HALT split by reason, so mandatory sells continue under pausing HALTs (D-DN-09, #117).
- [x] Gas top-up round end to end (#103); first-gas MetaMask exception confirmed by the team (#105 closed).
- [x] Every CloudWatch alarm email now says what fired and what to do (#141, IDEA-066 PC-AWS04).
- [x] Swap decoder/router-check code (#130) and S1 strategy code (#131) are merged. Actual source/route qualification and S1 parameter/input adoption remain below.

## Plan (team decision 2026-10-17)

Finish every Gate A and Gate B step that doesn't need the strategy profile this weekend, then on **Oct 20** build the profile from the finished quote capture and run everything that needs it, in order. Three things need the profile: `prepare` builds the runtime config from it, the evidence service refuses to start without that runtime config, and the planner takes its minimum trade size and slippage limits from it. Gate A `prepare` accepts only a profile built from a real measured `QuoteCostSummary.v1` (`validate_live`), so it can't be faked to start early.

**Risk:** the interim shadow services already started on Oct 17 (PC-AWS07). Gate A still needs its actual 24 h gap report and review; the Oct 20 final profile needs fresh preparation/binding/activation. Early shadow success does not qualify those later configs or signed Gate B operation. The later PC-AWS09 host report found archive delivery blocked after the restart drill; #163 and its hosted recheck remain necessary. This review does not mark the run healthy.

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
- [ ] **Keegan:** review Yao Zhu's PC-AWS06 migration/role output for PR99-RV1; host execution is already reported complete, independent review is not implied.
- [x] **Yao Zhu:** copy the six retained terms files from the 2026-10-17 capture to `/var/lib/larp-evidence/artifacts/<prefix>/<hash>` on `primary`, then rerun source preflight there. DOJ and EC pages change on every fetch, so only that capture's files match the register. Done 2026-10-17: installed, host preflight `ok` (IDEA-066 PC-AWS06).
- [x] **Yao Zhu:** on `primary`, run the route check (`python -m larp.runtime.routes --role primary`) and record `chronyc tracking`. Also confirm that `/etc/chrony.conf` has `rtcsync` and that `kernel_clock_synchronized()` prints `True` there (command in DEPLOYMENT_DAY step 9); without that signal a `CLOCK` HALT never clears (D-DN-10, #125). Send the reports to Keegan (R-07, R-08). Done 2026-10-17: 13/13 PASS, chrony normal (IDEA-066 PC-AWS06).

### Gate B setup

- [ ] **Isaac:** fill in `RouterEvidence.v1` from the router's verified source on BscScan, following `docs/build/GATE_B.md` in #130 (#33, GAP-29). **Blocked (2026-10-17, draft #139):** the router's code is unverified on BscScan, Read Facets gives no usable ABI and Sourcify has no match, so there is no verified source yet. #139 holds the acquisition report and the handoff in `ROUTER_SOURCE_REVIEW.md`; it is not to be merged until the evidence is complete.
- [ ] **Keegan:** build a new mirror bundle from the current integration head (it must include #130, #144, #148, #153 and, after they merge, #158 and #163) and send its hashes to Yao Zhu, for reprovisioning `primary` (the model trial below needs it first) and provisioning the signer at Gate B.
- [ ] **Keegan:** independently review Isaac's complete verified router evidence (#138/#139) when supplied. Decoder PR #130 is already merged and its repository review is recorded in IDEA-070; that does not approve missing real source evidence.
- [ ] **Keith:** give Isaac the quote files the capture has recorded so far (no credentials or `.env`), for the router check.
- [ ] **Isaac:** using merged #130, after the source-evidence review, run `python -m larp.execution_live.router check` on those files until it reports PASS. No separate route capture is needed.
- [x] **Isaac:** write the two options for how long a signing request stays valid, with a recommendation: (a) a bounded signing lifetime, or (b) a router deadline no later than the proposal's expiry. The encoded-deadline versus 15 s admission contract is unresolved (#27); about 30 s is the kit-stated quote lifetime, not a measured encoded deadline. Done 2026-10-17 in merged #144: `SIGNING_LIFETIME_PROPOSAL.md` and IDEA-049-C SL-01 recommend option A conditionally (60 s only an illustrative value) and note that the 30 s is the kit's stated quote lifetime, not a measured deadline.
- [ ] **Keith:** check what each #27 option in #144 does to the profile's quote age and proposal lifetime, and comment on #27.
- [ ] **Keegan:** decide #27 from Isaac's options and Keith's comment, record it as C-OPEN-003 in IDEA-049-C, and open the code change.
- [x] **Isaac:** propose the per-token input caps, the fee cap and `allowed_spenders` (the router's `tx.to` from the router evidence) for `signer.json` (#44). Done 2026-10-17 in merged #148: USDT input 35 (development) / 70 (final), fee cap 0.0002 BNB per transaction, token caps at 50% of the Oct 10 reference marks, spender the router `0xb444…fdda5`. Not installable until approved (`ready_to_install: false`).
- [x] **Isaac:** hand over a development `signer.json` draft and a technical cap review (#160, PR #161; received by Yao Zhu 2026-10-17, IDEA-066 PC-SIG01). Draft SHA-256 `339c4202…1442`; its `signing_policy` is byte-identical to the merged CP-01 development candidate (policy SHA-256 `254f5c31…2033`). Nominal check passed: the largest input is 20.10 USDT (EQUAL_WEIGHT) or 28.60 USDT (proposed S1) against the 35 USDT cap, at 100 USDT capital. The review was done by Isaac's delegated assistant, not by Keith. `ready_to_install: false`.
- [ ] **Keegan:** review and merge #161 (the handoff record).
- [ ] **Keith:** after the Oct 20 profile, finish the cap checks the handoff could not run, and record the file hashes on #44: the profile's `per_trade_cap_units` and `gas_top_up_cash_units` are each ≤ 35 000 000 micro-USDT; every full stock holding in the fresh wallet capture fits its token cap; measured approve and swap fees each fit 0.0002 BNB. PR #155's numeric-review tool can do this. Do not count the 40 USDT quote-capture size as a trade size: it is above the 35 USDT cap.
- [ ] **Isaac:** set the execution gas limits so `max_gas × max_gas_price ≤ 200 000 000 000 000` wei (0.0002 BNB); otherwise the signer refuses the transaction. Example: at 1 116 000 gas the price must stay ≤ 0.179 gwei.
- [ ] **Isaac:** after Keith's checks, decide the exact policy on #44 and replace `cap_basis: EXAMPLE_PENDING_TEAM_DECISION` with the decision reference. That changes the policy hash; record the new one. A `dev` signer would start with the example label, so this decision is the real lock, not the code.
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

**The LLM stays in for the signed rehearsal (decided by Yao Zhu, 2026-10-17, IDEA-066 PC-DEC03).** The proposal declares a hosted reasoning LLM for the evidence step, and the team keeps it. Today the code allows the LLM assessor only in unsigned shadow execution (`larp/runtime/service.py`), so the Oct 21–26 rehearsal needs a reviewed code change and an early model decision on Oct 20, both below. If either is missing on Oct 21, the rehearsal starts on `deterministic` and switches once both are in (a version event, recorded as a deviation). The full decision on Oct 22 confirms it with at least 3 trial days.

- [ ] **Keegan:** review and merge #158 (IDEA-081, per-stage prompts for GLM-5.3, Kimi K3 and Sol), then include it in the new mirror bundle above.
- [ ] **Keith:** read the exact remaining OpenAI balance on the billing page and send Yao Zhu the prior spend in micro-USD for budget `init` (US$1 = 1 000 000; about $1 spent if $49 is left of $50). The ledger keeps its $40 operating limit and $10 reserve, so OpenAI may use about $39 more (IDEA-056 MR-04, IDEA-057 P1).
- [ ] **Keith:** send Yao Zhu the OpenAI API key for that account and the funded AIand API key, privately: never in chat, an issue or Git.
- [ ] **Keith:** confirm or change the trial's ⚠ PROPOSED bars (IDEA-057 "Shadow trial") before the switch; after the switch they apply as written. Comment on #97.
- [ ] **Yao Zhu:** after the gap report, the new bundle and Keith's keys and number: runtime secret with `LARP_AIAND_API_KEY` and `LARP_MODEL_API_KEY` (`put_service_secrets.sh --only runtime`), provider check P0, budget `init`, reprovision `primary`, re-run Gate A `prepare` with `--model-routing <reviewed routing file> --model-routing-sha256 <its hash>` (PR #159, IDEA-057 SG-8: it writes `aiand_routed` and pins the file, no hand edits), install, re-bind, fresh `service init`/`activate` (a version event), route check, check the first routed assessment (`docs/build/AIAND_MODEL_ROUTING.md` "Host steps"). Record P0–P2 and the start time in IDEA-057.
- [ ] **Yao Zhu:** daily until the switch to signed rehearsal: budget `status` snapshot and ledger backup, kill criteria K1–K4 (runbook step 8).
- [ ] **Yao Zhu:** on Oct 20, pass the same `--model-routing` options to `prepare`; without them it writes `deterministic`.
- [ ] **Yao Zhu:** at the switch to signed rehearsal (Oct 21): keep `aiand_routed` if Keegan's Oct 20 decision is yes and the bundle with the code change below is installed; otherwise set `deterministic` (the current code refuses `aiand_routed` with signing). Note in IDEA-057 when the unsigned trial ended and which assessor the rehearsal started on.

**LLM in the signed rehearsal: early decision and code change**

- [ ] **Isaac:** write the code change that lets `aiand_routed` run with signing (`execution: service`, and `mode: live` for the scored run). Write its pass criteria in a ledger entry first. Minimum criteria: (1) a model call can never delay or block a mandatory sell, an execution step or a HALT; (2) a model failure, timeout or budget switch leaves the last accepted limiter level in place and never raises exposure (IDEA-075 §4.2); (3) the routed result reaches the limiter only through the existing verification and acceptance path; (4) every stage's model I/O and reasoning reaches the ai-seeds round log (F-102). Open the PR by Oct 19.
- [ ] **Keith:** review that PR (he designed the routing) and merge it by Oct 20.
- [ ] **Keegan:** after it merges, build the mirror bundle for Gate B with it (the bundle line under "Gate B setup") and send the hashes to Yao Zhu.
- [ ] **Keith:** on Oct 20 (morning UTC), an interim trial summary from about 2 days of data: availability (M1), latency (M2), OpenAI spend and projection to Nov 12 (M3), verifier pass rate per stage (M5), escalation rate (M6), and any kill criterion that fired. Deciding on fewer than 3 trial days breaks IDEA-057's "inconclusive" rule: record that as a deviation in IDEA-057.
- [ ] **Keegan:** on Oct 20, decide from Keith's summary whether the rehearsal runs with the LLM assessor (early DR-11), and tell Yao Zhu before the Oct 20 re-activation. A no means `deterministic` for the rehearsal and a DEV-19 row (hosted LLM not shipped).
- [ ] **Keegan:** add the AIand and OpenAI endpoints to the services list (`config/release/services.v1.json`) and update DEV-19's row to "AIand routing (GLM-5.3, Kimi K3) with optional GPT-6.1 Sol review" (GAP-62), in the same bundle if possible.

**LLM: everything else between now and the scored run (audit 2026-10-17, IDEA-066 PC-AUD01)**

These were missing from every list; each one is needed for the LLM to be in the activated build and working (A-REQ-079). Owners rebalanced 2026-10-17 (Yao Zhu): model and routing work to Keith, who proposed the routing; tooling, network, operations and review to Isaac; Keegan keeps the strategy wiring, release declaration and model decision.

*How the LLM's findings reach trading.* Two paths: accepted assessment findings feed the evidence gate (Class 1 exits and entry blocks), and, with the S1 profile only, the exposure limiter. The limiter's input is not produced anywhere today. In `MODEL` mode it also needs an LLM call that returns `{level, evidence_ids, reason, falsifier}`, and that call does not exist; with no assessment, every session is rejected as `NO_ASSESSMENT`, so the limiter never cuts and a cut never expires.

- [ ] **Keith:** propose the S1 `limiter_mode` for the rehearsal and final profiles: `DETERMINISTIC` (code maps the LLM-verified evidence classes to levels; no extra LLM call) or `MODEL` (needs the exposure call below). Recommended: `DETERMINISTIC` unless the call is built and tested by Oct 21. Only matters if the Oct 20 profile is S1.
- [ ] **Isaac:** decide `limiter_mode` from Keith's proposal by Oct 20 (IDEA-075 O6, DEV-19).
- [ ] **Keegan:** B4 producer: build `exposure_evidence` (verified items with `class`, `symbols`, `session_index`) from the evidence store into the runtime context, for both modes (IDEA-075 B4 lists Yao Zhu; this checklist puts code with Keegan). Bring it forward from Oct 24 if possible; see the B4 line under Oct 24.
- [ ] **Keith:** only if `MODEL` is chosen: the exposure-level LLM call (once per session and on each new verified filing), with its own pinned Markdown prompt like #158's, through the same routing and OpenAI budget, its I/O in the round log. Criteria in a ledger entry first.
- [ ] **Isaac:** activation tooling: PR #159 (SG-8, merged 2026-10-17) added the reviewed `--model-routing` option to Gate A `prepare` and `gate_a_check`, for unsigned dev-shadow only. Extend preparation and qualification to signed rehearsal (`execution: service`) and the live config, together with the guard-lifting change above.
- [ ] **Isaac:** re-approve the network table rows for `api.aiand.com` and `api.openai.com` for signed and live use (today "Shadow only", `architecture-deployment.md` "Approved network destinations").
- [ ] **Keith:** capture the AIand and OpenAI terms (date and SHA-256) and record in the licence register what they allow for sending public filings, retention and audit sharing (GAP-23, IDEA-056 §8, IDEA-049-A rights row). Keegan reviews.
- [ ] **Keith:** check the AIand balance covers the run: AIand token usage from the trial (IDEA-057 M4) projected to Nov 12, with a margin. An empty AIand account leaves every assessment UNAVAILABLE.
- [ ] **Keith:** record the scored-run model behaviour: after activation only automatic switches act (budget latch to external-only, provider fallback, UNAVAILABLE keeps the last level). The trial's operator kill actions K1–K4 (remove a key, restart, revert) are not allowed during the scored run (F-114, F-124). Write it into IDEA-057.
- [ ] **Keith:** freeze the routing file and both stage prompts with the Oct 22 parameters; any later prompt edit is a new release before activation, never after.
- [ ] **Keith:** in the Oct 22 trial summary, record the disposition of the real-evaluation blocker (T01 / independent labels / post-cutoff check, IDEA-049-A): what ran (the trial's M9 sample) and what is declared as not run.
- [ ] **Yao Zhu:** during the trial, record memory use on `primary` (`systemctl show -p MemoryCurrent` for each unit, `free -m`) once a day. Units may use up to 3 GiB on a 2 GiB `t3.small` (#60). **Baseline 2026-10-17 15:27 UTC (before the trial):** 1401 of 1909 MiB available; runtime 65, evidence 57, uploader 53 MiB (IDEA-066 PC-AWS09).
- [ ] **Isaac:** decide #60 from Yao Zhu's numbers: keep `t3.small`, lower the unit limits, or resize (a resize costs money and needs Yao Zhu's OK and a Terraform apply).
- [ ] **Isaac:** on the first signed rehearsal rounds, with the on-chain check, confirm the ai-seeds round logs carry every routed stage's model I/O and reasoning, and record cost and latency per round (DR-11).

### Decisions due Oct 19

- [x] **Keegan:** decide and record the rehearsal shape (D-DN-02), including what happens if Gate A only passes on Oct 21. If Gate B slips past Oct 20, record the shortfall as a deviation (GAP-04). Done 2026-10-17 (IDEA-049-D D-DN-02, #140).
- [ ] **Keith:** write up the two options for the first signed trade. The rehearsal profile's buy window is fixed in code at Oct 21 00:00 – Oct 22 00:00 UTC (`WINDOWS` in `larp/strategy/profiles.py`), so a round on Oct 20 plans no buys. Option 1: trade on Oct 21 inside that window. Option 2: add a dev window before Oct 20 (code change, recorded as a version event).
- [ ] **Isaac:** pick one of Keith's two options and tell Yao Zhu.
- [ ] **Keith:** decide which profile to build on Oct 20: `EQUAL_WEIGHT` (in the code today) or S1 `TREND_GUARDED_VOL` (code #131 is merged; its values stay proposals until the recorded freeze).
- [ ] **Keith:** propose what mandatory exits do during a price-jump hold (IDEA-055 POLICY-HOLD). HALT for mandatory sells is already built (#117).
- [ ] **Isaac:** decide POLICY-HOLD from Keith's proposal.
- [ ] **Keegan:** confirm the trial bars after Keith's review (moved before the switch on Oct 18; see "Model trial" above).
- [ ] **Keith:** keep or move the Nov 11 15:00 UTC flatten, and record it in IDEA-035 C4 (#107).
- [ ] **Keegan:** settle open choice O2 (what ships if EXP-007 is inconclusive) **before** EXP-007 runs, since it is part of the pre-registered decision rule (IDEA-075 §16, EXP-007 status).
- [ ] **Keith:** after O2, run EXP-007 on token session bars up to the Oct 16 close (IDEA-075 B1) and record the result by Oct 19.

## Side note: interim profile for an early dry run (optional)

The interim profile is already running in the owner-reported Oct 17 shadow run (PC-AWS07). It is replaced on Oct 20 by the final profile; its mandatory coverage/hash record remains below. Gate A is unsigned, so the interim values only change shadow HOLD/BUY decisions.

- [x] **Keith:** on the capture server, summarise the files so far into a **new** directory, without stopping the capture: `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <interim>/summary.json --min-days 2`. If a token has fewer than 10 US-session samples the tool names it; rerun with `--min-samples` at the lowest count it reports, never below 5. Done 2026-10-17 (`--min-days 2 --min-samples 9`).
- [x] **Keith:** build the profiles: `python -m larp.strategy.profiles --summary <interim>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <interim>/profiles`, and send `rehearsal-live.json` to Yao Zhu. Done 2026-10-17 by Yao Zhu from Keith's summary (`d951207f…`).
- [x] **Isaac:** a quick look at spread, impact, gas and minimum trade size in Keith's interim summary and profile. Done: Keith and Isaac approved it for the shadow run (2026-10-17).
- [ ] **Keith:** record in IDEA-063 that it is interim, with the coverage parameters, capture hash and profile hash.
- [x] **Yao Zhu:** if the weekend Gate A setup is done, run the Oct 20 steps 5–8 early with this profile. On Oct 20 the final profile means rerunning `prepare`, rebinding the manifest and a fresh `service init`/`activate`, because the profile hash is pinned in the runtime config. Done 2026-10-17: shadow run live, first round ACKed by the receiver (IDEA-066 PC-AWS07).

## Oct 20: profile day, in this order

The capture ends at Oct 20 00:00 UTC (08:00 SGT).

1. [ ] **Keith:** full summary with the default coverage (3 UTC days including a weekend, 10 samples per token per regime): `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <dir>/summary.json`.
2. [ ] **Isaac:** confirm the quoted amounts already net out route fees, so `fee_bps = 0` holds (#119). Isaac's #157 (fee estimate semantics, #156) is open: **Keith** reviews it before this step.
3. [ ] **Keith:** build the decided profile (its `per_trade_cap_units` and `gas_top_up_cash_units` must each be ≤ 35 USDT, the signer's development cap): `python -m larp.strategy.profiles --summary <dir>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <dir>/profiles`.
4. [ ] **Isaac:** owners' review of the summary and `rehearsal-live.json` (#120); record both hashes in IDEA-063 and send the profile to Yao Zhu.
5. [ ] **Yao Zhu:** fresh read-only wallet capture with the balance RPC (`prepare_shadow.py capture --balance-rpc-config deploy/activation/balance-rpc/selected-providers.json`), then Gate A `prepare` within five minutes with the same `--balance-rpc-config`, so both RPCs go into `runtime.json` (#145); install the configs (`runtime.json` mode 0644); bind them to CI's manifest (`preflight --bind`).
6. [ ] **Yao Zhu:** `service init`, then `service activate` with Keegan named as reviewer; start the evidence, runtime and uploader services; enable the archive timer.
7. [ ] **Yao Zhu:** confirm the first shadow round is ACKed by the real ai-seeds receiver (R-01), which starts the 24 h ingestion clock, and send the round ID to Keegan.
8. [x] **Yao Zhu:** restart drill (kill a service, check it returns on the same build with an incident logged) and check the first hourly anchor (DR-13, DR-15). Done early 2026-10-17 on the shadow run: back in 10.3 s with one RESTART incident; the 11:00 anchor verifies against the journal, COMPLIANCE-locked (IDEA-066 PC-AWS08). Repeat after the Oct 20 re-activation only if Keegan asks.
9. [ ] **Isaac:** only if a dev window was chosen: watch the runtime's first approve plus swap on the dev wallet and check it on chain against the logged round (DR-02, DR-03).
10. [ ] **Keegan:** only if the dev-window trade in step 9 occurred, perform the Gate B review in IDEA-042; otherwise use the Oct 21 Gate B review after its first signed trade. The host-side crash tests (DR-04, DR-05) are step 3 of the Oct 21 list.

## Oct 21

- [ ] **Keegan:** review and merge the incident-backup fix #163 (IDEA-082: S3 keeps Object Lock dates to whole seconds, so every incident backup is marked PERMANENT and blocks archive health; IDEA-066 PC-AWS09), and include it in the Gate B bundle.
- [ ] **Yao Zhu:** after Oct 18 00:00 UTC, check `operations health` is healthy again (the daily backup should supersede the failed incident backup); if not, record it in IDEA-066.
- [ ] **Keegan:** decide how `doj-press` and `fr-bis` pass the gap report (IDEA-066 PC-AWS10): their unbounded history walk marks every poll truncated, so DOJ can never show a complete 24 h. Either bound the history in code (owner to name) or accept them as explained gaps in the report.
- [ ] **Yao Zhu:** after 24 h of ingestion, produce the gap report on `primary` (`python -m larp.sources.live report --from … --to …`) and send it to Keegan. **Rehearsed 2026-10-17 on 4.7 h (IDEA-066 PC-AWS10):** the command works; expect `doj-press` and `fr-bis` to fail until Keegan's decision above. Exact command and output location in `deploy/activation/oct18-run-sheet.md`.
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
- [ ] **Keith:** summarise the full trial results (at least 3 days, including the first rehearsal days) for the final model decision (DR-11).
- [ ] **Keegan:** confirm or reverse the Oct 20 model decision from Keith's summary: AIand routing or deterministic (DR-11, #97). A reversal is a version event before final activation.
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
- [ ] **Isaac:** per-leg attempt limit and execution-window checks (B6).
- [ ] **Keegan:** write up the T4 dev-wallet run from the rehearsal round logs (B8, Oct 24–26).
- [ ] **Keith:** check the T4 results against what S1 should have done.

## Oct 26–29

- [ ] **Keegan:** deviations-register rows for exceeding the proposal's 80% / 20% / four-name limits (B7).
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
