# REL-AUD01 — published release and outstanding declarations

2026-10-28 SGT. User requested investigation of the purported preparation-fix revert,
review of the nine DRAFT declarations, and a new release only if no important issue remains.
Audit source: canonical `2aa95617bf9217455d88446f44c7cdbd8276f88b`.
This is a read-only release/code audit with documentation follow-up, not a new trading experiment.

## The published release includes the fix

Latest published release at inspection: [temp-selfcheck-2aa95617](https://github.com/binance-hackathon-glasswing/binance-hackathon/releases/tag/temp-selfcheck-2aa95617),
published 2026-10-27T18:08:38Z (Oct 28 02:08:38 SGT). This is the temporary self-check release, not an FS1 release.

- PR317 merged at `c1e23729` on 2026-10-27T16:47:49Z, including stacked PR319 (`7484274a`).
  Both are ancestors of `2aa95617`.
- Keith created revert commit `69d3e3147f54464cf70d4aeff7a6ad25d876f7e5` fourteen seconds later,
  on `revert-317-codex/fence-investigation-20261027`. That commit is **not** an ancestor of canonical.
  GitHub's commit-to-PR lookup and exact-head PR listing returned no associated PR.
  Its message supplies no reason beyond the revert title. Why it was created is undocumented;
  there is no evidence that a failing test or safety finding caused it. Do not invent a rationale.
- Downloaded the actual release archive and manifest. Their SHA-256 values match the published metadata:
  archive `a4511e4aa314e92e3f2d5e5f9bf447b934523f78f70ff651c254bdf4a242cbf3`;
  manifest `213ab1b259377c0cb5b8c67835855267f73ed84fe1a7d5d6c14c253dd605d999`.
- Read the archive directly without installing it. `larp/execution.py`,
  `larp/execution_live/{guards,main,store}.py` and both release declaration files match
  the downloaded manifest and canonical source byte for byte. Thus the shipped bytes contain FENCE01/FENCE02.

COST03's original cause was a stale journal version after preparation network I/O. Ordinary planner writes
invalidated the final compare-and-swap, consuming bounded probes without a prepared attempt. Pausing planning
removed that interference. FENCE01 refreshes authorization/time after I/O; FENCE02 retries only current guards,
pure validation and the fenced save, within bounded limits. It does not repeat venue work or disable fencing.
Persistent races and changed authority still refuse. Source details and historical full Linux/PostgreSQL receipts:
[FENCE01](PREPARE_FENCE_REPAIR_20261027.md), [PR319](PR319_REVIEW_20261027.md), IDEA-104 S5-COST03.

This proves release contents, not installation or successful live operation. The release itself reports pinned
Linux and hosted qualification outstanding. Receipt-reconciliation stale-version follow-up remains separate.

## Nine DRAFT rows are substantive

The published manifest reports 25 deviations, 9 DRAFT, zero OPEN. Declarations SHA-256:
`5c38324017313746e08b1ee7c76b721888418a936559c50a7f2ecf02d429b707`.
`activate_run` refuses a `live` run with any DRAFT row before lifting quarantine/registering a build.
Both standalone FS1 and temporary self-check preparation use `runtime_mode='live'`.
The empty-register activation guard is our implementation; the official source requires truthful declarations,
not this exact internal DRAFT/FINAL mechanism. Checked SKILL.md F-60/61/66, G-11, Q-22/Q-33 and the
verbatim Rules & Restrictions section in `docs/official/source_page.md`.

| Row | Important discrepancy / remaining disposition | Owner |
|---|---|---|
| DEV-01 Model layer | Correctly says no trained decision model, but still treats S1 profile/qualification as pending. Describe the selected FS1 family and exact provenance rather than an obsolete conditional baseline. | Keith profile; Keegan declaration |
| DEV-02 Entry rule | Describes old 75% equal-weight top-up policy. Selected FS1 is TREND_GUARDED_VOL, KIT_OPEN_STATE with trend/limiter/cost/review gates and a separate activation self-check. | Keith; Keegan |
| DEV-03 Sizing | Says four names at 20% / 80% gross, and calls the later family volatility-weighted. Selected FS1 pins five names at 1/5 each and high/mid/low gross 95%/60%/30%. Actual pinned weights must be stated. | Keith; Keegan |
| DEV-04 Cash floor | Old 80% ceiling and 25% name/90% gross trims do not describe selected FS1: high gross 95%, weight cap 30%, hard name weight 35%, top-up band 5%. Distinguish targets, admission limits and hard triggers. | Keith; Keegan |
| DEV-07 Exits | Old red-flag-only summary omits current S1 trend, limiter, drawdown/recovery and stale-data behavior. Verify actual predicate authority and terminal dates; never infer old Class-2 behavior applies to current discretionary falsifiers. | Keith; Keegan |
| DEV-19 Assessor | Describes retired unsigned AIandRouting.v3 trial, whereas standalone FINAL preparation pins AIandRouting.v4 (`9b86c732…`) and requires an adoption reference. Services list repeats the obsolete unsigned-only scope. Confirm current provider/account/rights and signed/scored adoption evidence. | Keith/Keegan model adoption; account owner evidence |
| DEV-22 Budgets | Describes earlier assessor timing/selection contract, still pending adoption. Reconcile actual v4 per-stage caps, prompts, decision budgets, tool partitioning and worker cleanup before declaring FINAL. | Keith/Keegan |
| DEV-23 Router | Material safety declaration: unverified router enforcement remains unproven. Row says no installed configuration enables cleanup; current standalone FS1 builder explicitly enables allowance recovery and requires it in FINAL service validation. Rewrite for the actual selected cleanup/abort path, source patches, gas and signer policy; retain the untrusted-router limitation and actual acceptance evidence. | Isaac policy; Keith abnormal fills; Keegan declaration |
| DEV-24 Rehearsal | Shorter-window decision exists, but actual signed start/end, successful rounds, interruptions and limits need a dated receipt. COST03 records one successful BUY; this is not evidence of a five-day complete-pipeline rehearsal. | Keegan; operator evidence |

Selected FS1 inputs inspected: `tools/deploy/prepare_fs1.py`, its pinned
`docs/build/evidence/fs1-final-20261025/fs1-final-recovery.json` (`b8ba06e2…`) and
`config/intelligence/aiand-routing.fs1.json` (`9b86c732…`). The temporary profile has its own size/cost/window
overrides; do not present them as FS1's scored policy. Services list also has dated RPC/hosting provisioning
scope that needs comparison with actual accepted deployment evidence before final declaration.

DEV-23's residual risk matters independently of wording: local quote/calldata checks and exact approvals cannot
prove that the unverified on-chain router honors recipient/minimum-output/deadline or recover a bad fill.
The existing declared acceptance is not a new guarantee.

## Result and validation

Do not build a replacement under the user's conditional instruction: important declaration issues remain.
Changing only statuses, editing a downloaded manifest or relabeling the run as dev would not reconcile declarations.
Keegan owns the final complete-row/services review with the named contributors. After truthful final declarations
and their evidence are committed, build/qualify new exact bytes and a new build_id; operator deploys later.
Existing activation guard and application/config bytes are unchanged by this audit.

Local Python3.12.14 standard-library unittest: 10 PASS (5 guard acquisition/race classification tests and
5 release-register/preflight consistency tests). `tools/render_deviations.py --check` PASS.
No disposable PostgreSQL was configured for this audit, so database race/live-activation regressions were not
rerun; historical full results retain their original commits. No host/service/key/wallet action, signing,
provider/model call or deployment occurred. Reported quarantined/service-off state was supplied by the user
and was not independently rechecked on hosts.
