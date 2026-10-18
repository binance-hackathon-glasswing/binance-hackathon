# PC-HO02 — late Oct18 deployment continuation for Yao Zhu

This is the latest handoff. It supersedes pending-release/cap-code/report and
older v2 instructions in AWS_DEPLOYMENT_RESUME_20261018.md and the local run
sheet. Refresh remote and host state; these are dated observations, not live state.

## Immediate task: verify the newly supplied release, then resume owner deployment

Yao says Keegan has supplied the release. Local candidate located:
`/Users/songyaozhu/Downloads/larp-86b14761324f-x86_64.tar`.
Only packaging was inspected in this last handoff step:101,519,360 bytes,
uncompressed ustar, no gzip magic. No final local content/source verification
of this candidate has been performed. It may be a browser-decompressed form of
the original asset; that is not established by its name. Do not compare its
whole-file hash directly with the recorded compressed asset or call the hash
difference corruption. Inspect safely without executing archive contents.

Expected original release, verified by Keegan in PR174-REL01:

| Identity | Expected value |
|---|---|
| Source | `86b14761324faeb8f57df5c0d86ff00320b4361c` |
| Original asset | `larp-86b14761324f-x86_64.tar.gz`,98,383,598 bytes |
| Original gzip SHA256 | `277fd2b6e4b26e0725b38c1f4f2bcb35cab7e25fe3857639683b283e7b684343` |
| Embedded/external manifest SHA256 | `0053cbc9c7eb68c3ec82dfc519f01979a5e3a0171fee784d43d12b76c7dfff2f` |
| Actual packaged RDS CA SHA256 | `d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b` |
| Source files / full checksums |196 /235 |
| CI mirror | Keegan4/Keegan4-larp-ci-mirror, run39126353379, all4 jobs PASS |
| Release | https://github.com/Keegan4/Keegan4-larp-ci-mirror/releases/tag/llm-trial-pr174-86b1476 |

Read `docs/build/evidence/pr174-release-20261018.json`. Original artifact ZIP
id12135774607/digest419bf1c56e4dd0f08c9d4e262abdda78654c2e9e483f3595c8c755b0f25a9b77
was verified by Keegan; publication-only run39126901213 uploaded six original
assets without rebuilding. This chat has not newly downloaded/verified those
remote assets. If private access returns404, preserve that access limitation;
it does not prove the release is missing. Verify the local source/files against
Git, manifest, BUNDLE.env, complete checksums and CA. If the runbook/provisioner
requires the original gzip and sidecar, obtain those originals; do not repackage
and claim newly compressed bytes are the original CI asset.

## Repository state and completed deliveries

- Primary checkout `/Users/songyaozhu/binance-hackathon` is the documentation
  branch `claude/pre-trading-checklist-20261017`; PR133 stays OPEN, base
  `codex/system-testing-20261012`. PR126 also stays open.
- Latest inspected integration:1306bbb (PR175 release-evidence merge). It has
  no differences from86b1476 under larp/, config/, deploy/, tests/,
  requirements.lock or pyproject.toml. Refresh before relying on that statement.
- PR174 is reviewed/fixed/MERGED100d493. Its DOJ repair, durable head proofs,
  explicit report scope, unsigned trial caps and Keegan R1 accounting/clock/
  malformed-proof corrections are in86b1476. PR167/165/KMP-P2/services/DEV19
  are included. No repeat request for Keegan to fix/build those completed items.
- Keegan exact-source Linux/Python3.12.15/PostgreSQL14.24:2064 passed /6 expected
  skips /2992 subtests; actual systemd5/5 separately. All4 CI jobs PASS; Docker,
  offline demo, Terraform and both-role bundle provision checks PASS. These are
  retained release results, not a new rerun by this chat or host acceptance.
- PR168 was merged into PR133's branch, not integration. Yao explicitly approved
  its unsigned v3 protocol/rubric. Do not ask Keegan to approve it again.
- Earlier code/release work PR155/157/158/161/163/164/165/167 is merged. New release
  provenance is PR174-REL01. Older7a0ea14/d8aa7d5 do not contain the new DOJ/caps
  repairs; do not deploy them assuming they do.
- The completed managed fix worktree was clean, had no unpushed commits, and
  was archived through Codex tools. Do not treat its saved1dee43d snapshot as
  the final86b1476 source. Use/reuse a suitable clean exact-release checkout
  for preparation, not the PR133 documentation tree's application files.
- No subagents were spawned. Other pre-existing worktrees were untouched.

## Last fresh host observation:21:29:41SGT /13:29:41UTC

PC-HAR01 read-only base64 SSM d763f48e-aefd-4399-a4cf-43c186282651:

- Still buildbb46234, dev/shadow/deterministic, runtime/evidence/uploader active;
  execution inactive, archive timer active. No routing hash or model-budget file.
- Operational healthy=true/reasons=[];70 audit chunks ACK,27 anchors ACK/latest
  13:00UTC,00:00 daily backup ACK. Historical incident backup remains PERMANENT.
- DOJ latest SOURCE_UNAVAILABLE/RESPONSE_TOO_LARGE; BIS OK/truncated. Five EDGAR
  latest checks OK, EC/public-inspection OK, SEC press NOT_MODIFIED.0 corrupt lines.
- No host/code/config mutation, metric publication, inference or signer action.
  Operational healthy does not mean source coverage passed.

Tracked snapshot: `docs/build/evidence/harness-readiness-audit-20261018.json`.
Private raw result/script retained in Downloads/LARP-harness-audit-20261018.
Recheck current state before setup; never initialize a ledger based only on the
older no-file observation.

## Approved provider/budget direction and exact trial file

OpenAI preferred; no permanent US$10 reserve; pace the reported US$48 remaining
from originalUS$50, with US$2 owner-reported prior spend. AIand140+ reported,
units/funding/actual usage still unqualified. Both keys are already stored in
`larp-dev/runtime`; do not request keys or replace the secret unnecessarily.
Primary migrations/roles/IAM/TLS checks and Keegan's limited independent primary
review are done; signer-host/populated upgrade/new-install qualification are
separate. Do not repeat the original empty-DB work as though it never happened.

**Use the opt-in capped unsigned file, not merely the preferred example:**
`config/intelligence/aiand-routing.openai-trial.example.json`, SHA256
`a5fca50a6f3e166b48299a0d29e686aa6dbfd2428f4bb011839acc684b222d8d`.

- OpenAI gpt-6.1-sol medium primary; high-effort AIand KimiK3/GLM5.3 review/fallback.
- OpenAITrial.v1 strictly-belowUS$8 total /US$2.50 per UTC day, atomic conservative
  maximum reservations including concurrency/retries/UNKNOWN and actual dispatch
  day. Trial ID/window immutable (allowed Oct18 11Z–Oct22 00Z); actual observation
  starts at the first qualified job, not the earlier allowed-window start.
- Preserving setup also fences old workers; accounting quarantine/clock/trial
  stop rules guard AIand dispatch. Account funding/other consumers remain separate.
- Stage/model/raw I/O and charge reconciliation still need real verification.
- A new ledger init may use2,000,000 initial-spend microUSD only after current
  reconciliation confirms it and matching routing baseline. Existing ledger:
  stop/drain providers, consistent backup, inspect/reconcile, then explicit
  preserving enable-pacing/enable-trial as applicable. Migration refuses existing
  non-initial request charges whose dispatch days cannot be reconstructed. Retain
  that refusal; never reset/delete/edit charges, reservations, tables or latches.
- `status`/`export` can advance a durable clock watermark: owner operational
  commands, not strict read-only checks. Use explicit read-only SQL for inspection.
- No moving active policy dates to replenish credit. No automatic signed adoption
  or removal of trial policy. Later signed transition needs separately reviewed
  preserving ledger handling. No bare paid inference probes outside accounting.

## Next sequence (Yao owns AWS/host actions)

1. Read AGENTS.md and its skill/ledger order, then this handoff, live checklist,
   PR174 release evidence and frozen DOJ_TRIAL_CAP_FIXES runbook. Verify the
   local candidate as above and refresh remote/host state without rewriting history.
2. Provider/account/terms/entitlement/effort checks using stored secrets securely;
   reconcile actual balances/usage and prior spend. Prepare reviewable commands
   for Yao; no new paid calls or spend without his OK.
3. Verify original release/source, fresh wallet capture, reviewed real interim
   profile/RPC file and exact capped routing. Prepare in the exact-source clean
   checkout, within5min of wallet capture; verify package/hash/scope. Install/pin
   routing and perform matching preserving ledger setup while inference is stopped.
   Follow the tracked runbook's safe ordering; do not hand-edit runtime drivers.
4. Yao provisions/installs/binds the new release/configs, creates a new version/run
   and activates unsigned services. Preserve all stores, ledger/old versions and
   archives. No Terraform apply/new resources without explicit OK.
5. Verify first actual assessment ID/start/cutoff/build/profile/protocol/prompt/
   routing hashes, served identity/effort, raw I/O, dispatch/charges and receiver
   ACK. Record only observed route-stage qualification; no inference from config.
6. Check post-fix source polls/head proof/restart and trust/coverage behavior;
   collect/hash a NEW actually observed window/report. Current-listing mode is
   explicit and retains historical coverage separately. No short/old-window PASS.
   Supply immutable exports for Keith's actual usage/label/trial report. Keep
   signed rehearsal hours separate from required unsigned observation hours.

AWS profile larp, region ap-southeast-2, base64 SSM scripts. Read-only checks may
run directly. AWS/host mutations remain Yao's; no Terraform apply or new spend
without his OK. Never expose credentials, private RPC URLs or database hosts.
Keegan/release agent is explicitly authorized to push the mirror and dispatch CI
directly; routine mirror work is not routed through Yao unless access is blocked.
No messages to other people/tasks without explicit user authorization.

## Collected report and evaluation: completed, preserve original facts

- Fixed Oct17 11Z–Oct18 11Z report/raw collection is DONE under ignored
  deploy/activation/gap-report-20261018T110022718213Z.31 hashes and original718138
  bytes independently verified; raw FAIL reproduced with originalbb46234 code.
  Report SHA092c18e555d73f34be6b95d3c02b80c470c31073539fce0836dfa22abdfa5cf5;
  snapshot SHA18d6ec9eb70591198befe43a7b765f76a713163060d2c7fff635df1bb4bd1168.
  DOJ96 actual size errors cannot use the historical-backfill exception. BIS
  historical-only checks eligible. No combined explained PASS. Keegan's retained-
  metadata disposition is complete; original failure is never rewritten.
- Four-filing/five-document deterministic diagnostic DONE (PC-LABEL02-R2/R3):
  43 saved requests, four original representatives plus39 repeats. Two AI labels
  and blind AI adjudication validated; gold SHAf4274c0b1c887f0b4c85d4ebe80d2d0bf2b0408a00b4ac69e6e03822ca3933be.
  Broad flags4/4; detailed annotation outputs exceed the temporary rule path's
  representation. No human-gold/T01/v3-M9 qualification. All original private
  labels/answers/results in Downloads/LARP-independent-labels-20261018.
- The conversational4/10 rating was WITHDRAWN as misleading/unvalidated. Harness
  provides evidence/tools, verification, policy/risk/execution/audit; LLM supplies
  semantic assessment. Do not grade the harness as an analyst or assume that
  adding an LLM automatically changes the verifier/schema contracts.

## Still-open owners: all tracked in PR133, not all already underway

- Yao: preserving release/ledger/provider/install/first-job and host qualification;
  PC-LABEL02-INJ01 benign investor-link text triggered instruction-risk coverage
  incompleteness on one filing/21 requests. Review intended behavior with Keegan
  and keep injection protection; retain old outputs.
- Keegan: B4 exposure_evidence producer missing; DEV20 event-calendar planner
  coordination (implement/verify adopted scope or obtain approved reasoned final
  deviation); operations/release declarations and GateA/B review.
- Keith: measured profile/parameters/usage/actual v3 population/blind labels/
  affordability/trial report; source/quote coverage and profile inputs remain live.
- Isaac: real router/ABI/source/replay/native-provider and signer evidence; Yao
  host signed approve+swap/ACK/crash/restore/replay and final activation remain
  separate. No signed gate was enabled by this session.

Read docs/build/HARNESS_READINESS_AUDIT_20261018.md, checklist and INCOMPLETE_WORK
for details. Keep completed items checked and leave partial items open. Do not
silently count old reports, temporary rule labels, signed hours, mirror source
claims or an available binary as passing host/model qualification.

## Session preservation

Tracked session changes are committed/pushed on PR133's documentation branch;
no unpushed session commits. Main matches origin/main as last checked. The only
primary untracked entry is the pre-existing `Claude outputs/`, intentionally
untouched. Private sources/labels and local ignored run-sheet stay outside Git;
this tracked handoff preserves their findings/paths and current instructions.
The completed Codex fix worktree is archived; pre-existing worktrees untouched.
Strict clean-tree handoff criterion has the known pre-existing untracked-folder
exception, so do not claim git status is literally clean.
