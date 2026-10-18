# PC-REL09 / PC-HOST02 / PC-PROV02 / PC-PREP02 — deployment continuation

Observed Oct18 2026, 13:50–13:56 UTC (21:50–21:56 SGT). Supplements
[PC-HO02](AWS_DEPLOYMENT_RESUME_20261018_LATE.md). PR133 remains OPEN on
`claude/pre-trading-checklist-20261017`, targeting `codex/system-testing-20261012`.
Host actions remain Yao's. No host configuration/service mutation, paid inference,
ledger setup, wallet transaction or Terraform apply occurred.

## Verified release; installation still pending

The supplied 101,519,360-byte `.tar` is **exactly the decompressed byte stream** of
Keegan's original 98,383,598-byte `.tar.gz`. A browser/client decompression is
consistent with this, but the client responsible is not established. This is
not corruption and no local recompression/rebuild was performed.

Downloaded all six original published assets, original CI artifact ZIP and
runtime job log through authenticated GitHub access. ZIP digest
`419bf1c56e4dd0f08c9d4e262abdda78654c2e9e483f3595c8c755b0f25a9b77`
verifies; its gzip, sidecar and manifest equal the published bytes.

| Item | Independent result |
|---|---|
| Source | `86b14761324faeb8f57df5c0d86ff00320b4361c`, present on fetched integration |
| Supplied uncompressed tar SHA256 | `7632df2ca4b678cd36a4aed7a4a7c8c7045feef72dbb643571b3b8bee2224665` |
| Original gzip SHA256 | `277fd2b6e4b26e0725b38c1f4f2bcb35cab7e25fe3857639683b283e7b684343` |
| Embedded/external manifest | Equal; SHA256 `0053cbc9c7eb68c3ec82dfc519f01979a5e3a0171fee784d43d12b76c7dfff2f` |
| Source files | All196 hashes/bytes equal Git and the committed release-file selector |
| All bundle checksums |235/235; every regular file covered except SHA256SUMS itself; no unsafe/link/duplicate members |
| Provisioner | Both copies equal exact Git `deploy/host/provision.sh`; the extra release-tree copy is checksummed outside the196-file manifest selector |
| BUNDLE.env | Equal published bytes and all recorded identity fields; bundled Python archive hash verifies |
| Actual packaged CA | `d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b` |
| Capped routing | `a5fca50a6f3e166b48299a0d29e686aa6dbfd2428f4bb011839acc684b222d8d` |
| CI39126353379 | Exact86b1476, all4 jobs success; downloaded log confirms2064 passed/6 skipped/2992 subtests; actual systemd5/5 separately. No new suite rerun |

Fetched integration is still1306bbb, with no application/config/deploy/test/lock
or pyproject differences from86b1476. Main and origin/main are bothfb95114f.
[Machine-readable verification](evidence/pr174-independent-verification-20261018.json).
The original Keegan release record is preserved unchanged.

Local originals and inspected inert extraction are in ignored
`deploy/activation/pr174-verification-20261018/{original,verified-bundle}`.
A new clean exact-source managed checkout is at
`/Users/songyaozhu/.codex/worktrees/larp-release-86b1476/binance-hackathon`, branch
`codex/release-86b1476-prep`, tracking the remote frozen86b1476 release branch.
Do not prepare with PR133's application tree. No other worktree was changed.

## Fresh host and provider observations

PC-HOST02, SSM `8d35489e-d121-4f8a-97bd-8312bf8df5ff`,13:50:34–35UTC:
oldbb46234, dev/shadow/deterministic, no routing hash or model-budget ledger.
Runtime/evidence/uploader active, execution inactive, archive timer active.
Operational healthy=true/reasons=[];71 audit chunks ACK,27 anchors ACK/latest
13:00UTC, daily00:00 backup ACK. Historical backup remains PERMANENT.
DOJ SOURCE_UNAVAILABLE/RESPONSE_TOO_LARGE; BIS OK/truncated; five EDGAR latest
checks OK, EC/public-inspection OK, SEC press NOT_MODIFIED;0 corrupt poll lines.
SQL explicitly READ ONLY. Healthy operations do not establish source coverage.

PC-PROV02, SSM `70102d52-0233-4c51-b1d0-25508cf731ea`,13:53:34UTC:
both existing secret fields present, no replacement. OpenAI authenticated
GET `/v1/models` returns200 and includes `gpt-6.1-sol`. AIand authenticated
GET `/v1/models` returns401. No inference POST, account-setting change or ledger
command was run. Ledger still absent at this second observation.

**AIand authentication is a new active blocker**, not a verified empty balance.
Bearer authentication matches both the exact adapter and
[AIand authentication documentation](https://docs.aiand.com/authentication/).
The [models endpoint](https://docs.aiand.com/api/models/) distinguishes anonymous
USD catalogue evidence from authenticated organization-currency evidence.
Do not replace the stored secret without diagnosing account/key status. Yao
checks that the existing key is enabled and belongs to the funded organization;
confirm currency, conversion, expiry, available funds and other consumers.
OpenAI model-list success establishes neither served medium effort nor actual
credit/usage. Reconcile current account usage before budget setup.
[OpenAI's models API](https://developers.openai.com/api/reference/resources/models/methods/list)
is a listing check; actual response identity/effort remains a first-job check.

## Fresh local preparation and checker blocker

PC-PREP02 captured the actual wallet read-only at13:56:15.500UTC and prepared
within5min from exact86b1476. Uses selected private RPCs, real approved interim
LIVE rehearsal profile SHAd951207f432879eda6b349ae334104e47803f809eb5e94aef422c2e31cab4542,
explicit dev/shadow execution and the capped trial hash above. No missing inputs.
Package integrity/JSON, unsigned identities, pinned inputs, service configs and
retained source terms all PASS. Host/provider/trial checks remain NOT_RUN.

**CI_RELEASE_BYTES FAIL; local_ready=false.** Exact-source
`larp/runtime/gate_a_check.py:149–159` requires build_origin equal the registered
repository (or its `.git` URL), rejecting the honestly declared Keegan4 mirror.
Production `preflight.bind_manifest` verifies the same original bytes successfully
in memory, without writing a manifest. This isolates the checker predicate;
it does not turn the failed local qualification into PASS.

Keegan owns reconciliation of the registered-only checker with the accepted
mirror provenance, including negative cases for unauthorized/mismatched origins.
A code repair requires review and a new original exact-source CI release, unless
an explicit reviewed acceptance disposition establishes the approved verification
path for these unchanged bytes. Do not edit manifest/build_origin, remove the
check, relabel the CI asset or claim this package is locally qualified.

The ignored package location is recorded in
`deploy/activation/pr174-verification-20261018/local-prepared-path.txt` and remains
in the exact-source checkout. The initial helper attempt retained a quote around
the existing SEC contact and correctly refused preparation; correcting only the
local helper's environment parsing produced the successful fresh assembly above.
The failed attempts and qualification output remain privately retained.

[Sanitized host/provider/preparation evidence](evidence/deployment-continuation-20261018.json).
A current wallet capture is needed again when deployment resumes; do not reuse
this snapshot as fresh installation evidence.

## Owner sequence after blockers resolve

These are **future Yao actions**, not executed steps. Resolve AIand/P0, actual
funding/usage and PC-PREP02 acceptance first. PR168 protocol is already approved;
no repeat protocol approval or request for keys is needed. Use the
[frozen86b1476 DOJ/cap runbook](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/86b14761324faeb8f57df5c0d86ff00320b4361c/docs/build/DOJ_TRIAL_CAP_FIXES_20261018.md).
If a replacement release is needed, verify its original CI assets/source and
update the build/manifest hashes before preparing;86b1476 remains historical.

1. **Accounts/P0.** Check existing funded organization/key status; authenticated
   AIand catalogue must expose Kimi K3/GLM5.3 at high effort. No low routine effort
   is required for v3. Record account settings/rights applicability privately,
   external consumers, current OpenAI usage and AIand units/expiry/funding.
   Keep unsigned account checks distinct from signed/scored policy compatibility.
2. **Preserve/quiesce.** Yao stops/drains all provider workers and services affected
   by the release switch; confirm none remain. Preserve previous configs, bound
   manifest/version, stores, outboxes and archives. Reinspect ledger existence
   with read-only SQLite, never `status`/`export` as a claimed read-only command.
   Existing ledger: consistent SQLite backup API copy; inspect/reconcile every
   charge, reservation, UNKNOWN, switch/latch and pacing/trial policy. No reset,
   deletion, table edits or reinitialization. Keep uploader/archive retention
   and pending delivery evidence through the stopped-service interval.
3. **Original bundle.** Yao uploads original gzip/sidecar to the existing artifact
   bucket and provisions primary with the verified provisioner and
   `--expect-sha256 277fd2b6e4b26e0725b38c1f4f2bcb35cab7e25fe3857639683b283e7b684343`.
   This switches installed code; it is a host mutation and is not performed here.
   No new resources/Terraform apply. Preserve previous release and stores.
4. **Fresh preparation.** From the exact accepted source, capture with the same
   selected private RPC file and prepare within5min. Use a new run/output directory,
   real approved interim profile, SEC contact and exact trial routing options:

   ```sh
   --model-routing config/intelligence/aiand-routing.openai-trial.example.json \
   --model-routing-sha256 a5fca50a6f3e166b48299a0d29e686aa6dbfd2428f4bb011839acc684b222d8d \
   --execution shadow --runtime-mode dev
   ```

   The local helper `deploy/activation/pr174-verification-20261018/prepare-local.py`
   contains concrete local paths and sanitized capture/prepare/check commands;
   review it before use. It targets86b1476 and intentionally preserves failed
   qualification. A repaired release requires updated verified inputs. Qualify
   the actual frozen package; do not hand-edit runtime drivers. After Oct20,
   replace interim profile only with Keith/Isaac's reviewed measured profile.
5. **Install pinned routing, then preserving setup.** Install prepared configs
   at their pinned paths, runtime.json readable by evidence (0644), routing
   root-owned0644, evidence.env public settings; verify routing SHA again.
   Keep inference stopped. If and only if no ledger exists and current
   reconciliation confirms exactly2,000,000 prior-spend microUSD with the matching
   routing baseline, Yao may run:

   ```sh
   cd /opt/larp/current
   sudo -u larp-runtime .venv/bin/python -m larp.intelligence.model_budget init \
     --path /var/lib/larp-runtime/model-budget/openai-budget.sqlite \
     --account larp-openai-2026 --initial-spent-micro-usd 2000000 \
     --routing-file /etc/larp/model-routing.json
   ```

   Parent directory must be private0700/larp-runtime. Existing unused v1/v2 ledger:
   explicit `enable-pacing` with matching routing; unused paced v3: `enable-trial`.
   Matching trial: no init/migration. Existing non-initial charges whose dispatch
   days cannot be reconstructed must retain the migration refusal and receive
   reviewed reconciliation. If prior account usage has changed, do not guess a
   new baseline or silently add headroom. Preserve every existing amount/latch.
   No permanent$10 reserve. Trial reserves strictly below$8 total/$2.50 UTC day;
   account/pacing limits, concurrency, retries and UNKNOWN all still apply.
6. **Bind/new version.** Preserve old `/etc/larp/release.json` before exclusive
   binding. Registration evidence must name the exact new build and actual
   registration evidence, not pretend a new organizer registration occurred.
   Bind CI identity with operations/runtime/uploader config hashes:

   ```sh
   cd /opt/larp/current
   .venv/bin/python -m larp.runtime.preflight \
     --bind /opt/larp/current/release-manifest.json --root /opt/larp/current \
     --output /etc/larp/release.json \
     --registration-evidence /etc/larp/registration-evidence.json \
     --config /etc/larp/operations.json --runtime-config /etc/larp/runtime.json \
     --service-config uploader=/etc/larp/uploader.json
   ```

   Run exact-release preflight/check, role route check and time-sync checks.
   `service init` creates a fresh quarantined run; `activate` requires the actual
   named reviewer and review reference. Keegan's remaining Gate A review must not
   be fabricated from protocol approval. Then Yao starts unsigned evidence,
   runtime/uploader and archive timer, leaving execution/signer off:

   ```sh
   sudo -u larp-runtime .venv/bin/python -m larp.runtime.service init \
     --config /etc/larp/runtime.json --manifest /etc/larp/release.json --root /opt/larp/current
   # LARP_RUN_REVIEWER and LARP_RUN_REVIEW_REF are required owner inputs from actual review.
   sudo -u larp-runtime .venv/bin/python -m larp.runtime.service activate \
     --config /etc/larp/runtime.json --manifest /etc/larp/release.json --root /opt/larp/current \
     --reviewer "${LARP_RUN_REVIEWER:?actual reviewer required}" \
     --review-ref "${LARP_RUN_REVIEW_REF:?actual review reference required}"
   ```

7. **First actual job/P1/P2.** With Yao's paid-call OK, capture first assessment
   ID, request/start/cutoff and actual build/profile/protocol/routing/composed-prompt
   hashes. Verify ordered stages, served identity/effort, raw request/response
   artifact hashes, provider summaries and all stage/tool/retry I/O in the round.
   Join OpenAI dispatch-day reservations/settlements/UNKNOWN to provider usage;
   reconcile AIand charges separately. Keep first round/ACK identities and actual
   receiver `STORED` evidence. A pending chunk or empty spool is insufficient.
   Qualify only observed successful paths/stages. Do not issue bare paid probes.
   Owner `status`/`export --routing-file ...` can advance clock watermark; retain
   private exports and consistent backups with hashes.
8. **Sources/coverage/trial.** Observe post-fix polls/head proofs across restart;
   retain actual DOJ errors and history state. Collect a NEW elapsed-window
   `report --coverage-scope current` with its historical report/poll bytes/hashes.
   Original fixed24h report remains FAIL; short windows remain INCONCLUSIVE.
   Preserve historical PERMANENT backup; verify a new incident backup ACK
   separately. Keith receives immutable usage/job/source exports for approved
   M1/M2/M3/M5/M9 and affordability/blind labels. Actual start is first qualified
   job, not Oct18 11Z. Allowed end stays Oct22 00Z; never slide it to buy hours or
   credit. Missing72 unsigned hours/routes/labels stays explicit. Signed adoption
   and preserving trial-ledger transition require separate reviewed handling.

## Remaining owners

Yao: provider401/funding/usage, preserving setup and installation, first-job/I/O/
charge/receiver ACK, source/restart/new-window and benign-link trust regression.
Keegan: checker acceptance/repair, GateA/B and operations/release decisions,
B4 exposure_evidence producer and DEV20 event-calendar planner disposition.
Keith: measured final profile/parameters, usage forecasts, immutable actual trial
population/blind labels/report. Isaac: real router/source/ABI/replay/native
provider, signer/cap/funding evidence. Signed-host approve+swap/ACK/crash/restore
and final activation stay separate. The small AI-labelled deterministic diagnostic
qualifies neither T01 nor v3 M9; the withdrawn4/10 rating is not reinstated.
