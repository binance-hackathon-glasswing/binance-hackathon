# PC-FIX01 — DOJ, source coverage and unsigned trial caps

Yao requests code fixes for Keegan's PR review and a subsequent new release.
Base: integration e7479b2. PR133 stays open. No AWS mutation, paid provider
inference, activation or release publication here.

## Prospective acceptance (before executing new code/tests)

- SRC1: reproduce an oversized DOJ history continuation while current listing
  polls succeed. Preserve durable cursors/artifacts and original failure logs;
  recover with bounded retrieval without skipping items or enlarging global
  response limits. Preserve error identity when recovery cannot succeed.
- SRC2: current-listing checks and bounded history work have separate explicit
  coverage evidence. Forward-window coverage needs a complete current-head scan
  anchored to earlier durable records. Missing anchors, item rejection, transport
  failures, corrupt logs and cadence gaps still fail. Historical completeness
  stays separately visible. Restart and moving-listing regressions are required.
- SRC3: legacy poll logs remain readable; reports retain original failure and
  truncation counts and cannot turn the old24h FAIL into PASS by reinterpretation.
  No log rewrites or blanket incident exemptions. Oversized individual items and
  poisoned pagination URLs remain bounded failures.
- CAP1: opt-in immutable unsigned-trial identity/window/US$8 total/US$2.50 UTC
  day limits are hash-pinned in routing and durable ledger state. Each OpenAI
  POST reserves its conservative maximum atomically against account/pacing/trial/
  dispatch-day headroom, counting concurrent workers, retries and UNKNOWN.
  Exact-cap admission refuses to keep spending strictly below support limits.
- CAP2: transport boundary rechecks UTC day/window and refunds only known-unsent
  work. Settlement retains dispatch-day attribution; unknown/sent failures keep
  full charges. Rollover never resets trial total; rollback cannot restore credit.
  Prior safety latches remain and cap stop disposition is explicit in audit/status.
- CAP3: explicit setup/migration preserves all charges/latches; missing, stale,
  mismatched or corrupt accounting refuses startup/dispatch. Legacy v1/v2 behavior
  remains covered. Signed adoption stays separate.
- OPS1: provide matching host preparation/report/status/export instructions and
  remaining account/P0/start/labels/affordability checks. Code alone cannot supply
  72 observed hours or independent labels; no paid calls without Yao's action.
- TEST1: push each executable revision before running it; record focused red then
  green regressions and an appropriate combined suite with honest skips and log
  hashes. No golden regeneration or weakened checks. Keegan reviews/builds later.

Results will be appended with exact pushed SHAs.

## Implementation and retained evidence

The public failing DOJ page97 returned20,757,780 bytes (SHA256
`a22e0edf7a0f4d6925bb0720cc167d3ecf3cdad147d1de28f68d1248870fd018`).
One article contains an inline JPEG in its HTML. Selecting body fields still
exceeds8 MB; changing page size changes tied-date result ordering, so it is not
a safe way to preserve every item offset. The official [DOJ API documentation](https://www.justice.gov/developer/api-documentation/api_v1)
was checked for field selection and zero-based pagination; no paid API used.
Raw diagnostic bytes are private local files, never committed or model inputs.

The repair gives only DOJ's allowlisted press-release API a32 MB hard wire
bound, removes complete excluded img tags before the existing4 MB permitted
payload check, and retains original wire hash/size and per-item media exclusions.
Other hosts retain their8 MB read bound and all configured response limits stay
unchanged. Large text, malformed JSON/images, wire overflow and potentially
removed item-rights notices still refuse. No record/page-size/offset is skipped.
Offline replay of the retained actual response preserves all20 ordered article
IDs, removes1 image and produces91,830 bytes in0.22s; normalized SHA256
`abe9fc05e62c9cfb513e56be69bf088f0584de8f33c672a6076900f6ecd5289f`.

Head overlap/checkpoint proofs are durable and logged per poll. An unfinished
scan cannot advance an established checkpoint or become its own proof on
restart. History retry counts survive successful head probes. The default
historical report is unchanged. Explicit `--coverage-scope current` requires
new, valid current-head proof, retains the complete historical report and all
history-incomplete counts, and never upgrades legacy logs without that proof.
It reports CURRENT_LISTING coverage, not completion of the publisher archive.
Existing runtime SourceCoverage remains conservative/INCOMPLETE while history
is pending; no signed/final source acceptance is inferred. Keegan must review
this explicit report scope and the prior failed window before deployment.

The new **opt-in unsigned-only** routing example is
`config/intelligence/aiand-routing.openai-trial.example.json`, SHA256
`a5fca50a6f3e166b48299a0d29e686aa6dbfd2428f4bb011839acc684b222d8d`.
It retains approved v3 primary/review prompts and account pacing, and adds
OpenAITrial.v1 with trial ID, Oct18 11Z–Oct22 00Z window,8,000,000 microUSD total
and2,500,000 per UTC day. Actual observed start is the first qualified job,
not the earlier allowed window start. Freeze/review any changed dates/hash
before setup; never slide an active window to create new credit.

Every routed OpenAI POST reserves its maximum in one SQLite transaction against
account, pacing, total-trial and UTC-day capacity, with equality refused. The
transport boundary atomically moves a waiting reservation to its actual UTC
dispatch day and rechecks capacity. Settlement never moves that day; UNKNOWN
keeps its maximum. Actual cap reach durably stops the trial, and underestimated
usage retains the existing account latch. Preventive admission refusal while
strictly below a cap is reported separately from an actual K1 stop; a smaller
request/later day can still fit. Account pacing refusal remains distinct.

Trial identity is also bound into the stored pacing-policy string: pre-cap
binaries' existing exact-string comparison refuses all new transactions after
migration. Removing trial configuration cannot bypass this fence. All prior
charges/latches remain. Trial expiry, clock rollback, durable stop or missing
accounting also blocks new AIand POSTs at their transport boundary; those paid
calls do not silently extend the original observation window. Preventive OpenAI
headroom refusal can still use the reviewed external route within the window,
subject to independently confirmed AIand funding. All three preparation/package/
runtime entry points refuse trial routing with signed or live scope.

## Yao's host steps after Keegan review and a new accepted release

These are future owner actions; none was executed by this fix. Keep the original
failed Oct17–18 report and private logs. Do not install the older d8aa7d5 binary
and expect these repairs: Keegan must build a new exact-source CI bundle.

1. Reconcile account use (OpenAI owner-reported48 remaining/2 prior; AIand140+
   still needs currency/conversion/expiry/entitlement). Reuse stored secrets;
   do not replace them or print values. Complete provider/terms/identity P0.
   Any paid identity probe must use this same budgeted router; bare inference
   tools/other account consumers are not protected by this runtime's caps.
2. Provision the new original verified bundle using AWS_RUNBOOK step5. Preserve
   all stores/archives and the old version event. Prepare from its exact source
   with fresh wallet capture within5min, the approved real interim profile,
   balance-RPC file, and `--model-routing` pointing to the new trial example
   plus its exact `--model-routing-sha256`. Review report.openai_trial and
   dev/shadow scope. Install/pin the prepared routing before budget setup.
3. Stop inference and verify no provider worker before a migration. Recheck
   ledger existence; at PC-REL08's earlier inspection it did not exist. For a
   new ledger only, after current prior-spend confirmation and private directory
   setup (0700, owned by larp-runtime):

   ```sh
   cd /opt/larp/current
   sudo -u larp-runtime .venv/bin/python -m larp.intelligence.model_budget init \
     --path /var/lib/larp-runtime/model-budget/openai-budget.sqlite \
     --account larp-openai-2026 --initial-spent-micro-usd 2000000 \
     --routing-file /etc/larp/model-routing.json
   ```

   2000000 is an explicit required reconciliation input, not a guessed default.
   Existing unused v1/v2 ledger: `enable-pacing` with matching `--routing-file`
   atomically adds pacing/trial; unused v3 paced ledger: `enable-trial` with the
   same file. An active matching trial ledger only needs `status`. Migration
   refuses any existing non-initial request charges because it cannot invent
   their dispatch days; it leaves rows unchanged. Retain a consistent private
   backup and obtain a reviewed reconciliation if that refusal occurs. Never
   delete/edit/re-init the ledger, remove its trial tables, or clear a latch.
4. Bind the new release/configs, new version init/activate, unsigned services
   only, and route/receiver checks. Record actual first assessment ID/start/
   cutoff/build/profile/routing/prompt hashes. Check first-stage served identity
   and effort, raw I/O, ledger dispatch rows, and first-round receiver ACK.
   Observe at least two normal source polls across restart/current-head checks;
   retain history status and any errors. A short post-repair check is not a
   new24h PASS. Keegan dispositions prior Gate A failure explicitly.
5. Retain full private model journals/artifacts (including failed, interrupted,
   unavailable and retry jobs), original source artifacts and charge exports.
   As larp-runtime, export status and all attribution/unknown rows with:

   ```sh
   cd /opt/larp/current
   sudo -u larp-runtime .venv/bin/python -m larp.intelligence.model_budget export \
     --path /var/lib/larp-runtime/model-budget/openai-budget.sqlite \
     --account larp-openai-2026 --routing-file /etc/larp/model-routing.json
   ```

   Capture/hash output privately. Status/export update the durable clock
   watermark; these are owner operational actions, not strict read-only SQL.
   Back up via SQLite's backup API, never by copying an active SQLite file.
   All probes/retries share this ledger. Review K1–K4, headroom/UNKNOWNs,
   memory and reconciliation throughout; code caps do not supply quality labels.
6. For a report over the new observed window, required owner inputs are
   LARP_LLM_RUN_START_UTC (recorded activation/first-job time) and
   LARP_REPORT_END_UTC (an already elapsed UTC time). Do not fill them with the
   old deterministic window or a future end. Run as larp-evidence over base64 SSM:

   ```sh
   cd /opt/larp/current
   sudo -u larp-evidence env LARP_ARTIFACT_ROOT=/var/lib/larp-evidence \
     .venv/bin/python -m larp.sources.live report \
     --from "${LARP_LLM_RUN_START_UTC:?record actual start first}" \
     --to "${LARP_REPORT_END_UTC:?record elapsed end first}" --coverage-scope current
   ```

   Retain original JSON, its embedded historical report, full poll-log snapshot
   and hashes. Before24 observed hours, verdict stays INCONCLUSIVE; no automatic
   extension or historical-only incident blanket turns it into PASS. Keith uses
   immutable model/job/source exports for the approved blind draw and measured
   M1/M2/M3/M5/M9/forecast report. Missing routes/labels/cost reconciliation remain
   explicit; supported unsigned qualification still needs72 observed hours.

Trial caps are for this unsigned block only. A later signed/scored configuration
needs a separately reviewed preserving transition of the trial-bound ledger;
silently removing openai_trial is deliberately refused. No manual reset is a
supported transition. That later adoption/transition is outside this PR's scope.


## Final verification and delivery

Prospective criteria c6097e0 and red tests ddcfb2f were pushed before execution:
17 failures reproduce the missing media recovery/head evidence/caps, with1
negative control passing. Subsequent pushed regressions reproduce unfinished
checkpoint self-qualification, unintended signed-trial preparation, stale-binary
policy bypass and unvalidated304 coverage; each has a corresponding fix. One
later test-fixture scope typo was corrected without changing application code.

Final application/test revision ae7ccaa: **1,630 passed,436 skipped,2,659 subtests
passed**,39.32s, Python3.12/macOS. Skips are PostgreSQL/Linux/systemd/external
requirements absent from this local environment; this is not Linux/host CI.
Earlier focused source/routing/preparation suite:186 passed/158 subtests; final
full run includes the later stale-binary and304 regressions. No goldens changed.
Full log SHA256: `6cef2a1e3c1197cba58a13bbec179a52cb133761d17985c4d83a065eca2ce45d`.
Machine-readable results: [doj-trial-cap-fixes-20261018.json](evidence/doj-trial-cap-fixes-20261018.json).

Keegan reviews the PR, including the explicit CURRENT_LISTING report scope,
prior failed24h window,32 MB DOJ-only wire handling and preserving trial ledger
binding. He then builds/tests a new original mirror release from the reviewed
integration source. Yao retains P0/funding/rights, actual ledger setup/backup,
source/report disposition, install/bind/activate and first-assessment/ACK checks.
The old failed24h report is never rewritten. No host change, provider inference,
wallet action, new release or PR merge was performed here. PR133 stays open.


## PR174-R1 — independent review and corrections

Review of published1dee43d and actual GitHub comments/reviews found no posted
issue/inline comments or submitted reviews. Direct code review produced three
reproducible findings. Prospective criteria b4abb08 and tests45cda3e/d373dde
were pushed before execution. Red45cda3e: two actual-dispatch regressions fail
and four malformed-proof subcases crash; one control passes.

- R1-CAP: OpenAI settlement failure marked its wrapper budget_unavailable, but
  a successful SQLite reread allowed AIand trial continuation. Fix b141074
  checks that same primary accounting quarantine at every AIand transport
  boundary, including later jobs in the router. Exact paid reply/artifacts and
  conservative reservations remain retained; storage recovery cannot itself
  reconcile uncertain settlement. V1/v2 external fallback is unchanged.
- R1-CLOCK: migration can attach a trial to an unused ledger whose pacing
  watermark is ahead of the new trial watermark. The shared trial guard now
  honors the existing pacing CLOCK_ROLLBACK refusal too. No existing charge,
  watermark or safety latch is cleared.
- R1-SOURCE: non-object head proof crashed current report. It now counts as
  corrupt proof/failed coverage and forces FAIL, even when a single malformed
  proof is within healthy cadence tolerance. Legacy historical report remains
  byte-for-byte unchanged for the same input.

Focused pushed b141074: **152 passed,169 subtests**,4.02s; trial/pacing/legacy
routing/providers/source/current+historical reports/model preparation.
Full Linux/PostgreSQL/all-job CI and original bundle verification follow on a
separately frozen release branch. All4 CI jobs must PASS, including actual
systemd/Terraform/Docker/demo/both-role bundle checks. Publish original tarball,
sidecar and manifest with actual CA/source/run identity; never substitute old
d8aa7d5 or a local rebuild. PR133/126 stay open; merge174 normally after green.

## PC-GAP02-RV1 — disposition of the completed Oct17–18 report

Reviewed PR133 snapshot48fb70d's PC-GAP02 and machine-readable
`gap-report-review-20261018.json`. Retained report SHA092c18e5…dfa5cf5 and
poll snapshot18d6ec9e…bd1168 identify the installed bb46234 fixed24h window.
Its recorded31-file/13-SSM verification and exact old-code reproduction were
performed by the evidence owner; the private raw bytes are not in this cloud
checkout, so this reviewer does not claim another raw-byte reproduction.

Accept the reported **FAIL**,0 corrupt lines. DOJ144 incomplete polls comprise
48 OK/truncated and96 actual RESPONSE_TOO_LARGE failures: historical-only
exception is ineligible. BIS96 successful transports include3 report-complete
and93 historical-incomplete; only BIS meets the scoped backfill-explanation
conditions. Combined explained report was correctly withheld. Other sources'
reported complete counts do not repair DOJ or qualify the whole Gate A.

Disposition: do not apply a full-window DOJ waiver, rewrite logs or turn this
window into PASS. PR174's bounded image repair/current-head scope addresses
future ingestion, not those historical failures. Authorize this code/new-bundle
work for unsigned trial preparation only. Yao must qualify actual post-install
polls/restart/new observed window with retained raw+historical reports; a short
post-fix check remains INCONCLUSIVE. SourceCoverage stays conservative and
signed/final source acceptance remains open. No host action or new coverage
observation was performed by this review.
