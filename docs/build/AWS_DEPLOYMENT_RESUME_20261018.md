# AWS deployment resume — PC-HO01 / aws-deployment-resume

**LATEST HANDOFF:** [AWS_DEPLOYMENT_RESUME_20261018_LATE.md](AWS_DEPLOYMENT_RESUME_20261018_LATE.md) supersedes older release/cap/report snapshots below. PR174 repairs and original86b1476 release are delivered; local supplied uncompressed tar still needs verification. Read the late handoff first.

Snapshot: 2026-10-18 ~07:46 UTC (15:46 SGT). Refresh GitHub and host state on
resume; this is not a new host inspection. User is **Yao Zhu**. This record
supersedes the older conversational `aws-deployment-resume` handoff and stale
v2-only instructions for the next trial. Do not repeat completed protocol/key/
migration work or ask for already granted approval.

## PC-GAP02 update — fixed report located and verified after19:00SGT

Report collection is done: ignored gap-report-20261018T110022718213Z contains
raw24h report and718,138-byte exact original log snapshot. All31 hashes verify;
raw report independently reproduces from original bb46234 code. Verdict FAIL:
DOJ96 RESPONSE_TOO_LARGE errors exclude PC-GAP01; BIS historical-only checks
pass. Combined explained report correctly withheld. Do not ask Yao to rerun or
resupply already local files. See IDEA066 PC-GAP02 and sanitized
build/evidence/gap-report-review-20261018.json for full hashes/results.
Yao source repair/private sharing and Keegan independent review remain open;
PC-CAP01/account/provider/installation/start remain pending. No new host action.

## Continuation update — PC-REL08, Oct18 10:36–10:39 UTC

This update supersedes the older pending-release/PC-AWS06-review statements
below. Keegan delivered d8aa7d5 including167/165/KMP-P2/services/DEV-19;169/170
merged, integratione7479b2. Original local bundle now independently verified
(195 exact-source files/234 checksums) in ignored releases/mirror-39111854179;
receipt/hashes in IDEA066 PC-REL08 and evidence/local-v3-receipt-20261018.json.
Keegan's existing primary migration/TLS review is complete with recorded limits.
Local private CI API404; original verification remains Keegan's retained evidence.
PR133/126 stay OPEN; no installation, provider call or activation performed.

Host read-only check: old bb46234 deterministic dev-shadow, healthy,62 audit
chunks ACK,10:00 anchor and00:00 daily backup ACK; historical PERMANENT incident
preserved; no model-budget file. **PC-SRC01 blocker:** DOJ94 RESPONSE_TOO_LARGE
failures since Oct17 19:00Z, cursor page97; PC-GAP01 cannot explain them. Source
repair/disposition and final report/review remain required. **PC-CAP01 blocker:**
account pacing does not implement $8 trial/$2.50 UTC-day admission caps; establish
guaranteed in-flight enforcement before paid jobs. Yao reconfirms OpenAI US$48,
AIand140+, with AIand units and actual billing/usage still to reconcile.

Ignored run-sheet C is now v3-specific. Ignored collect-gap-report-20261018.py
refuses before11Z/19SGT, then retains read-only raw report/exact poll-log prefix
and hashes; withholds explained report on failed exception checks. Actual report
NOT_RUN at this update. Yao owns source/accounts/caps/host actions, Keegan review
and release support, Keith usage/labels. No host mutations/new spend scheduled.

## Read first and branch distinction

Follow AGENTS.md: docs/skill/SKILL.md, docs/LEDGER.md table, then relevant files.
Read this record, docs/build/PRE_TRADING_CHECKLIST.md and IDEA-066 PC-REL01..05,
PC-DEC04 and PC-HO01; IDEA-057 OP-01/KMP records as needed. The detailed current
protocol is docs/build/V3_BUDGET_PROPOSAL_20261018.md and its linked rubric.

- PR133 branch: `claude/pre-trading-checklist-20261017`, **keep OPEN**. It holds
  the live dated checklist, approved protocol and handoff. PR126 also stays open.
- Code/release target: `codex/system-testing-20261012`, last inspected at
  `4312cd17f212df9f370a2c802bb17ff85d3d0250` (PR167 merge).
- PR168 merged into **PR133's branch** at622c522, not integration. Reading this
  documentation checkout is not proof its local application tree includes #167.
  Do code/release preparation from the appropriate exact integration/release
  checkout, not accidentally from the checklist branch. Use ordinary merges.
- Teammates may be active. Latest checklist changes at946edfc are Isaac's signed
  prerequisite criteria/transport correction, not completed provider qualification.
  Do not overwrite concurrent work. No agents were spawned by this chat.

## Authorization and operating constraints

Yao owns AWS/host/provisioning/configuration/activation, over SSM with base64
scripts. Read-only checks may run directly. No Terraform apply or new spend
without Yao's OK. Terraform is not installed on his Mac. AWS profile `larp`,
region `ap-southeast-2`; primary instance `i-040fc5fea8b700e9a`. User runs
`aws login --profile larp` when needed. Session was working earlier; check expiry.

**Latest mirror authorization (PC-DEC04):** Keegan and his release agent may push
directly to `Cookiemunchrr/larp-ci-mirror` and dispatch CI. Do not hand routine
mirror push/dispatch back to Yao. Ask/report only a concrete access blocker.
This supersedes the original request that this chat only supplied mirror commands.
Mirror CI builds are accepted release builds (PC-DEC01); org billing is separate.

No private RPC URLs, database hosts, secrets/keys, .env or private labels in chat,
issues or Git. Do not fetch secret values for verification. The only approved
exception to Yao's host ownership is Isaac placing a wallet key inside the signer
session Yao supplies. No signing/key placement until its gates pass. No force
push, rebase or pushed-history rewrite. Write pass criteria in ledger first;
commit and push decision/trading/logging code/tests before executing them.
No model/provider calls or host mutations occurred during this feature work.

## Completed and decisions that must not be reopened

- PR155 reviewed/fixed/integrated at2f10b9d; PR157 atad9a8b9. #156 closed;
  fee-netting #119 and measured profile review #120 remain open.
- #158 stage prompts mergedce9115e, #163 Object Lock fix2b4f397,
  #161 signer handoff7cd7892 and #164 signed/deferred LLM capabilitya2af2df.
  These do not establish actual hosted or signed acceptance.
- **PR167** requested/built as a separate review PR, now MERGED4312cd1:
  `AIandRouting.v3`, OpenAI primary, paced access to full remaining allocation,
  Kimi K3 high then GLM-5.3 high fallback through AIand, same original evidence/
  verifier, independent review/disagreement abstention, durable conservative
  reservations/unknown usage/latches and explicit preserving migration. Original
  v1/v2 defaults are unchanged. Audit wrapper now selects actual stage config.
- OP-01 local full suite at application/test6bcbef0 + docs-only merge75282ec:
  1580 tests and2622 subtests PASS,426 skips (PostgreSQL/Linux/systemd/external).
  No Docker daemon on Mac; no new accepted Linux/mirror release containing167.
  Tests used `/private/tmp/larp-pr-review-20261018-venv/bin/python`, with matching
  `PYTHON` and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. Full log
  `/private/tmp/larp-openai-pacing-full-permitted.log`. Initial five loopback
  permission failures passed in permitted rerun. No golden regeneration.
- **PR168** MERGED622c522 into checklist: Keith delivered source/composed-prompt
  review, v3 budget/window/stops/forecast proposal, frozen blind rubric and actual
  v3 route mapping, public model/provider terms register, sanitized interim quotes
  and #27/profile/window/DETERMINISTIC-limiter proposals. Independent verification:
  29 quote-file hashes/lengths,1021 records,26 raw artifacts,9 source hashes and3
  composed prompts match. Private terms archive/current collector health not
  independently rechecked by this chat.
- **Yao reviewed/merged168 and explicitly confirmed this counts as approval**
  of the unsigned v3 protocol/rubric/route mapping (PC-REL05). Do NOT ask Keegan
  to approve it again. Approval is Yao's, not invented personal Keegan sign-off.
- Exact reported OpenAI balance US$48 from original US$50: prior2,000,000
  microUSD. AIand140+ owner-reported, units/real affordability still unqualified.
  User briefly tried5 reserve, returned10, then approved new v3 **zero permanent
  reserve** with full-credit pacing. Old v2 $40 operating/$10 reserve is history
  for v2 observations, not the intended new v3 policy.
- Approved v3 example horizon Oct18 11:00UTC to Nov13 00:00UTC exclusive,
  24h release periods,26 periods, first1,846,153 microUSD of the remaining48M.
  Carry unused allowances; temporary pacing can recover without permanent latch.
  Actual credit/allocation/accounting safety failures retain durable fallback.
  No guarantee every job uses OpenAI all window or spends the final cent.
- Protocol includes trial $8 total/$2.50 per UTC-day stop boundaries, in-flight/
  unknown reservations, forecast margin,72 observed unsigned hours and coverage/
  independent quality minima. See approved document for exact enforcement/verdict.
  Actual spend, affordability, draw/labels, qualification/adoption are not measured
  by approval. Signed hours do not count toward unsigned72h; short = inconclusive
  unless a kill/safety defect establishes NOT_SUPPORTED.
- **Both model keys are stored already** in `larp-dev/runtime`; AWSCURRENT
  metadata verified version`d227ba39-c9c9-40c5-a32f-1aa9bb3dfc3e`, changed
  Oct18 05:08UTC. Script replaces whole JSON. Do not rerun merely because a new
  thread starts. No secret values read. Service loads once on startup; secret
  storage alone did not restart services or erase collected data.
- **Yao already completed primary migration/roles/TLS**, PC-AWS06 Oct17:
  migrations001–013/roles applied, all four primary IAM/TLS checks pass, six terms
  artifacts installed/preflight OK, routes13/13 and chrony OK. Keegan's independent
  review remains unrecorded. Do not tell Yao he still needs to do that work.

## Host and old artifact state — last verified, not current guarantees

- Last inspected installed build`bb46234f1b997dae968e2c3f3668d73627857376`,
  run`larp-dev-shadow-20261017`, dev/shadow/deterministic. Runtime/evidence/uploader
  active, execution inactive, archive timer active. No v3 deployment/trial start.
- Oct18 02:46UTC read-only SSM health: daily00:00 backupACK, latest02:00anchorACK,
  all44 audit chunksACK, no HALT/quarantine/delivery breach. Historical incident
  backup remains PERMANENT but superseded. Fix163 still needs installed-release
  incident-backup validation. Strict read-only checks must not use an operations
  command that publishes CloudWatch metrics; earlier check used read-only SQL.
- Old accepted unsigned-v2 bundle source7a0ea1433b3a029e9e2dc97817bac98a7e09c0ce,
  mirror39091699018 / artifact12122169313 (all4 jobs green):
  bundleSHA ff951451bc80b518620f895b2b0a871df188ce2cb2d3e36e04a58754c7f5de06;
  external/embedded manifestSHA bb17b7ffc28eeb2e14594a80895827bed5327b8408f519692870dcdeffdca70a;
  CASHA d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b.
  Verified all192 files, sidecar/build/repository identity and CA. Local bytes:
  ignored`deploy/activation/releases/mirror-39091699018/`. It lacks167.
- GitHub prerelease`model-trial-7a0ea14` is a documentation/download-helper ZIP;
  no uploaded original host binary. Do not deploy that ZIP or relabel old CI bytes.
- Org Actions no-step failures have verified payment/spending-limit annotations
  (e.g.39101498071). That is not a product test failure or restored billing.

## Next work, in order / parallel

1. **Keegan release work:** user prepared the full prompt below; at handoff there
   is no confirmed start/new release. Refresh status rather than assume finished.
   Fix **KMP-P2**: reservation just before pacing end can dispatch at/after end;
   actual reviewed code lacks the second pacing-boundary dispatch check. Needs
   reviewed regression/fix before the strict cutoff v3 release. Arrange actual
   trial sublimit enforcement, update services/DEV-19 to the selected route,
   disposition165, freeze exact source/config/prompt identities, directly push/
   dispatch mirror, hand over original binary/sidecar/manifest/CA/runID. Protocol
   approval is already done. Reading docs can occur from133; release code from
   actual reviewed integration/release branch. Subsequent host steps remain Yao's.
2. **Yao after Oct18 11:00UTC /19:00SGT:** generate the fixed24h gap report
   Oct17 11:00Z→Oct18 11:00Z, raw first, retain hash/logs. Inspect DOJ/BIS normal
   polls/cadence/parse/rejection/truncation evidence before applying PC-GAP01's
   two historical-backfill explanations; save raw and explained reports/hashes.
   Runtime source coverage remains INCOMPLETE; archive incident stays separate.
   Keegan's disposition exists already; it is not full signed/source acceptance.
   Local commands/output locations: ignored`deploy/activation/oct18-run-sheet.md`.
3. **Yao after accepted new binary/fix and report review:** P0 authenticated
   provider/identity/effort/account/terms/funding checks; reconcile actual current
   prior spend/charges; v3 budget initialize WITH `--routing-file`, or explicit
   preserving migration if a ledger exists (no reset of charges/latches). Update
   old run sheet C first: it still has legacy v2 file/$10 initializer. Prepare
   from exact released source with the reviewed v3 routing bytes/hash, fresh
   capture within5min and valid measured interim profile, install/bind, fresh
   version init/activate, route/receiver/first-assessment checks; record P0–P2,
   protocol/build/config/prompt/start/cutoff and budget identities. Provider
   requests/activation/spend remain explicit host actions with Yao.
4. **Parallel evaluation:** Keith measured usage/funding forecast, approved blind
   selection/rubric with immutable population/labels, final quote capture/profile/
   cap review. Interim1021-row snapshot has9<10 US-session samples/token; default
   summary correctly refuses. Collector resumedOct18 06:54:40UTC throughOct20
   00:00UTC after40103 timestamp freshness; do not claim continuous capture. All
   observed swap gas uses FALLBACK. Old interim summary/hash export still needed.
   EXP007 waits on Keegan's O2; later freeze/labels/sign-offs stay open.
5. **Signed gates in parallel, not blockers to unsigned binary packaging:** Isaac
   source139 still DRAFTbd8a34b; router/source/quote check, fee119/profile120,
   #27 finite lifetime (Keith proposal supplied, Keegan decision/code), #44 caps/
   gas/holdings, native tracing30/BNB, signed model network/rights, signer host/
   temporary SSM/approved key session and crash/recovery proof. #165 OPEN at
   8f2d364 (merged current base into branch, not product completion). SP-01 in
   SIGNED_PREREQUISITES_20261018.md is criteria/transport correction only; results
   not yet appended. B4 exposure producer, trend/session inputs/B5, S1 freeze,
   drills/final-wallet/final acceptance remain with checklist owners.

## Last Keegan prompt agreed with Yao

Prepare the next unsigned LLM trial release from latest integration including167.
Update services/DEV-19 for OpenAI-primary/high-effort AIand fallback. Use already
approved168 protocol from133; no repeat approval. Resolve KMP-P2. Review165 and
choose release scope; it needn't delay unsigned trial. Push/dispatch mirror directly
under Yao authorization, ask only if real access block; after CI hand off original
bundle/checksum/manifest/CA/runID. Review existing Yao PC-AWS06 evidence now and
actual24h report after Yao produces it; report needn't delay binary build. Keep133
open, update only verified completions, preserve criteria/commit/push/history rules.
AWS/host deployment stays Yao's. This chat did not message or start another task.

## Repository/handoff audit

Session changes are committed/pushed on133; verify exact current HEAD remotely
on resume. Main was equal to origin/main atfb95114; no session commits unpushed
at audit. Pre-existing untracked `Claude outputs/` is untouched: strict clean-tree
handoff is therefore NOT satisfied, despite the saved handoff. Do not delete or
commit that folder. Other pre-existing worktrees belong to other work; leave them.
No new worktree or managed thread was created in this chat. Private run sheets,
artifacts and outputs stay ignored/local; they are intentionally not in Git.
