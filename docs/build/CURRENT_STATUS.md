# Current shared build and remaining work

PR296-RV01 (2026-10-26 SGT, review follow-up; publication authorized by the user): FS1/S5 direct startup now enforces routed
assessment outside the scoped historical rehearsal; run-7 and FINAL startup initialize/activate before signer
and execution, then start runtime only after execution is healthy. The standalone
`tools/deploy/prepare_fs1.py` prepares fresh FINAL wallet/database/history/routing inputs and independently
assembles FINAL caps/signers, without any prior S5 run or signer. Final-wallet nonce/ai-seeds directories are
separate. Existing profiles/routing are unchanged. S5's withdrawn USDT top-up instructions are removed; its
cash/history blockers remain. [Comparison, findings and validation](../ledger/IDEA-104.md#pr296-rv01--review-and-independent-fs1-preparation-2026-10-26-criteria-before-execution) /
[standalone FS1 run sheet](ops/final-fs1/README.md). Final pinned Python3.12.15/PG14.24: **2962 passed, 8 skipped, 4069 subtests, zero failures** ([receipt](evidence/pr296-review-20261026.json)). Publication targets PR296 only; no merge, install or live qualification.

IDEA-104 S5 R3 (2026-10-26 SGT; R2 merged as PR294 `81ee30a1`, R3 not merged or installed): S5 is FS1 FINAL at
rehearsal size on the dev wallet, to Tue Oct 27 12:00 SGT, with FS1's AIand/ChatGPT routing `9b86c732…`, model
authority and token history; profile `f371b18d…`, probe `90344caa…`. Blocked: it buys nothing at the dev wallet's
81.37 USDT (gas excluded), and no real token-history file exists (TH-01). [Record](../ledger/IDEA-104.md) /
[run sheet](ops/rehearsal-install-s5-20261026/README.md). FS1 profiles unchanged.

PR295 / IDEA-103 PR295-RV01 (2026-10-26 SGT): FS1 history producer, bounded pagination/cache,
qualified timestamp/adjustment input and production preparation/startup wiring reviewed. Fixed exact JSON/close
price precision and inconsistent OHLC acceptance. Source `ba6f0d94`: **112 focused tests/20 subtests PASS**;
deferred full rerun complete: pinned Python3.12.15/PG14.24 **2901 tests/4060 subtests PASS**, 8 skips/3 nested
sandbox exclusions. GitHub CI startup billing-blocked. [Receipt](evidence/pr295-review-20261026.json).
[Record](../ledger/IDEA-103.md) / [input and transfer contract](FS1_TOKEN_HISTORY.md).
Actual provider/semantics qualification and exact release/host acceptance remain with TH-01's owners; no deployment.

PR291 / IDEA-102 MC-RV03 (2026-10-26 SGT): mandatory S1 SELL legs now retry without a session ceiling,
with one new attempt per leg per UTC15-minute slot. Quote children may reuse their parent's open slot; refunds
retain spacing. Discretionary caps and all gas/window/health/signer/preflight checks remain. New runtime rounds
record a replay discriminator; historical/new journals replay exactly. Source7e31de34: pinned Linux/Python3.12.15/
PostgreSQL14.24 **2858 tests /4055 subtests PASS,11 platform/fixture skips**; focused51/32/zero skips.
CAP-01 implementation/review is complete. [Receipt](evidence/pr290-pr291-review-20261026.json).
GitHub CI remains billing-blocked; exact FS1 release/owner/host acceptance remains separate. No deployment.

PR290 / S4-F1-RV01 (2026-10-26 SGT): unclaimed command expiry refunds only the latest leg attempt in the same
session. Refund-tagged facts after any recorded broadcast are refused; claimed commands and ordinary aborts do
not refund. Source313c5758: pinned Linux/Python3.12.15/PostgreSQL14.24 **2847 tests /4055 subtests PASS,11 skips**;
focused71/45/zero skips. Exact replay passes. No deployment; record: IDEA-097 S4-F1-RV01.

CL-01 (2026-10-26 SGT): repository maintenance removed 137 merged origin branches and 23 unused local
branches, preserving exact pre-deletion heads in [the audit record](evidence/repo-cleanup-20261026.json).
Main, canonical, open PR heads/PR133, the original checkout branch, unique histories and checked-out local
branches are retained. All eight open issues retain unmet acceptance; [issue dispositions and parallel
verification](../ledger/IDEA-101.md) distinguish completed implementation from remaining owner/host evidence.
PR278 PL is present: five parallel company-assessment slots, serial wallet trades and settlement-gated
cadence continuations; focused current-canonical verification passed 85 tests/54 subtests with PostgreSQL14.24.
Full-suite plus corrected-environment reruns cover2840 unique passing tests, zero unresolved failures;11
environment/fixture cases remain unrun. [Receipt](evidence/parallel-verification-20261026.json).
No deployment, real model call, wallet action or live-concurrency qualification is part of this maintenance.

PR287-RV01 / IDEA-099 (2026-10-26 SGT): reviewed concise round/order reason summaries. Corrected BUY USDT
units, planned-versus-submitted wording, latched risk/discretionary reasons, pending quote/reduction holds and
fallback consistency. Orders unchanged. Pinned Python3.12.15/PG14.24: **2840 tests / 4055 subtests PASS**,
8 skips/3 nested-sandbox exclusions; CI startup billing-blocked. PR285 documentation integrated, preserving
both ledger entries; 41 post-integration checks pass with application/test bytes unchanged. Keegan/Isaac wording
acceptance, FS1 release build and Yao's actual FINAL activation-log check remain open; no installation.
[Review](../ledger/IDEA-099.md#pr287-rv01-results-and-merge-decision-2026-10-26-sgt) /
[receipt](evidence/pr287-review-20261026.json).

PR278-RV03 (2026-10-25): **PR278 (FS1, IDEA-093/098) merged into canonical at the user's request.** Before the merge
canonical `7fc9f601` (PR286) was merged in; all four FS1 profiles rebuild byte for byte (FINAL recovery `b8ba06e2…`
to install, cleanup-off `19176e6c…` for comparison, FS1-R `17ab891d…` / `54802665…`); full suite 2819 passed,
11 environment-only skips, 4033 subtests, 0 failed on Python 3.12 + PostgreSQL 16 (not the pinned 14.24); GitHub CI
billing-blocked. Merging is not approval: every FS1 owner gate below (values, profile/signer/caps approval, F0p
scripts, Q1/M3, model adoption, budget, GAP-73..75, install) remains open. [Record](../ledger/IDEA-093.md#pr278-rv03--merge-into-canonical-2026-10-25).

PR283-RV01 / IDEA-098 (2026-10-25): FS1 recovery profile integration reviewed for merge into PR278's branch.
Fixed stale cleanup-off install/probe references and completed RC4 synthetic numeric coverage. Pinned Linux
Python3.12.15/PG14.24: 2818 tests/4029 subtests PASS, 8 explicit skips/3 nested-sandbox deselections; CI billing-blocked.
Recovery FINAL `b8ba06e2…`, FS1-R `17ab891d…`, S4 `58b31806…` unchanged. Fresh FINAL Q1/M3/scripts, exact
signer/profile approval, real gas/BNB/timing and AL9 remain owner gates. PR278 was later merged (PR278-RV03 above).
[Review](../ledger/IDEA-098.md#pr283-rv01-results-and-merge-decision) / [receipt](evidence/pr283-review-20261025.json).

IDEA-097 S4 (2026-10-25): run 5 carries run 4's book over and flattens with PR282's allowance recovery. The profile is `58b31806` (flatten already begun, signing to Tue 12:00Z, exit reserve 0.01536 BNB). Implemented with the run-5 sheet and supported offline: Linux 3.12.15 + PG 14.24 at `04c8997b`, 2722 passed and 0 failed. Approval, BNB top-up and install remain. [Entry](../ledger/IDEA-097.md).

PR278-RV01 (2026-10-25; superseded by the PR278-RV03 merge above): Repairs cover healthy PF02 recovery,
authorized-minimum entry cost, pending cost-gated small reductions and gas-excluded stock allocation after
PR279/F-125's 30 USDT gas instruction. FINAL profile `19176e6c…`, REHEARSAL `54802665…`.
Combined source `d7741f91` includes current integration `5b5f0c89` and PL: full suite2766 tests/4027 subtests PASS;
5 systemd and2 non-root/origin checks separately PASS (only2 external/private fixtures remain unrun).
Real PostgreSQL all-five construction/restart/exact replay and offline demo pass. [Review](../research/fs1-review-20261025.md) /
[receipt](evidence/pr278-review-20261025.json) / [owners](../ledger/IDEA-093.md#pr278-rv01-results--source-review-complete-keep-pr278-open-2026-10-25-sgt).
Predictive edge is NOT_ESTABLISHED. Missing live trend series, material fixed-price BNB risk valuation (GAP-73),
registered final-wallet self-check/handover (GAP-74), funding check (GAP-75), exact profile/model/caps/release and
FS1 install-script acceptance remain. No merge, deployment or wallet action is implied; earlier receipts below
remain evidence only for their recorded source/configuration.

IDEA-096 / PR282 (2026-10-25): F2/F3/F4 allowance recovery, bounded durable abort cleanup and monitoring merged to
canonical after review PR282-RV01 (three passive-monitor/verifier fixes); defaults remain disabled. Local pinned
Python3.12.15/PG14.24: 2707 tests/4018 subtests PASS, 8 explicit skips/3 nested-sandbox cases deselected. GitHub CI
cannot start (billing). Exact candidate gas/caps/signer, Gate A/host acceptance and AL9 remain open in FLAT-01; no
install or running-profile change. [Entry](../ledger/IDEA-096.md) /
[validation](evidence/pr282-allowance-recovery-validation-20261025.json) / [review](evidence/pr282-rv01-review-20261025.json).

PR277-RV01 (2026-10-24): S3 dev-rehearsal scheduled flatten reviewed with a repair bounding pre-cut BUY command
and independent execution/signer/broadcast authority at the schedule; first flat/DONE re-entry remains allowed.
2659 tests/4004 subtests PASS, 8 explicit skips, 3 unchanged nested-sandbox cases deselected on pinned Linux/Python3.12.15/PG14.24;
all16 S3 cases pass, including real coordinator/restart/settlement/exact replay. GitHub Actions is billing-blocked.
[Review/owners](../ledger/IDEA-092.md#pr277-rv01-results--pass-for-source-merge-2026-10-24-sgt) /
[receipt](evidence/pr277-review-20261024.json). Candidate2fb32b8e unchanged; no profile/signer/host/install acceptance.
H1/H2, full-cycle gas/exit/shared attempt coverage, working sandbox/systemd/release and live S3-L1 remain open.
Active run4/RC7 remains unchanged.

PR276-RV01 (2026-10-24): IDEA-091 strategy research reviewed and corrected against canonical `59c878c0`.
Verified code gaps are scoped; policy/rules and primary-source checks are separated from unverified leads.
Unsupported profit/rank forecasts and unreproduced simulation tables are withdrawn. No strategy, parameter, gas,
runtime or release change is adopted. [Review](../ledger/IDEA-091.md#pr276-rv01-results--pass-for-documentation-merge-2026-10-24-sgt) /
[report](../research/strategy-alternatives-20261024/report.md) /
[receipt](evidence/pr276-review-20261024.json). PF-IMPL01, PF-04 and later dev-run acceptance retain their owners/gates.

PR274-RV01 (2026-10-24): S2-F2..F6 source fixes independently reviewed with three repairs: preserve original model
assessment audits during replay, bound complete SSM decision exports, and retain actual quote-follow-up IDs in the
dashboard. Full pinned Python3.12/PostgreSQL14.24 validation:2643 tests/4004 subtests PASS,10 expected skips; final
dashboard/contract follow-up42 tests/44 subtests PASS. GitHub jobs never started due to billing/spending limits.
[Review and remaining owners](../ledger/IDEA-090.md#pr274-rv01-results--pass-for-source-merge-2026-10-24-sgt) /
[receipt](evidence/pr274-review-20261024.json). Later dev-run F7/post-approve swaps, strategy/profile/config,
final release/host/signing acceptance and PAGES01 remain. Active run4 stays on RC7; original install/trade reports
from PR272 are retained in IDEA-089 as dated evidence, not independently rerun by this review.

IDEA-089 S2 (2026-10-24): the weekend trade test for run 4 is implemented and tested offline (PR270): `KIT_OPEN_STATE` hours for both planner and execution/signer admission, the S2-1 scope in five places, the runtime router-policy pair (with PR268's quote verifier, merged at `398255f`), S2 profile `eb55d76a…` and the RC7 run sheet `build/ops/rehearsal-install-rc7-20261024/`. RC7 build, the Q1 live quote check, Isaac's approval and the install (Yao) remain. Run 3 (RC6 `9dc5edab`) stays a no-trade soak until R1p. See [IDEA-089](../ledger/IDEA-089.md).

PR262-RV01 (2026-10-23 SGT): IDEA-086 fixes the hosted entry blocker with a basis verifier and ratio-scaled token
marks. Independent review repairs also check price-response chain/platform and exclude rejected basis inputs from
usable valuation. Offline planner BUY/failure coverage and full local2507 tests/3929 subtests PASS (10 expected skips) are supplied.
GitHub Actions run39914039956 was unable to start jobs because of account billing/spending limits; no CI pass is claimed. See [IDEA-086](../ledger/IDEA-086.md#9-pr262-rv01--independent-merge-review-isaaccodex-2026-10-23-sgt).
Final policy adoption (Keith/Isaac), RC6 and run-3 S1/profile/gas/caps/config/host acceptance (SJ-11) remain open.
No release was installed or wallet/model operation performed by this review.

SJ-03 (2026-10-22 SGT): Isaac's additional dev gas seed is successful/finalized,
with2USDT net debit. [Receipt/current public snapshot](evidence/dev-gas-funding-20261022.json)
confirms96USDT and0.005325625054330011BNB, covering the selected0.003072BNB signer
exit floor. User dev-seeding step is complete; no further swap requested for
that minimum. Remaining: operator actual hosted post-funding reconciliation/
private current packet, exact input acceptance and intended signed run/config
bindings, then offline signer assembly/local release check. No full92/92,
installed config, native trace or final-wallet acceptance is inferred.
Superseded (2026-10-23): the remaining steps were done in SJ-04 (capture and assembly), SJ-05
(signer `check`) and SJ-06 (install); see the signer-candidate note above.

Latest qualification (2026-10-21, AB-REL-RC2): PR231 is merged at canonical
`b22207e`; all four mirror jobs PASS (2416 tests/3808 subtests, real-systemd5/5,
Docker/demo/both-role host bundle). Original artifact12352993133 is hash-verified.
[Receipt](evidence/ab-rel-rc2-20261021.json) / [remaining LD16/17 bindings](LD15_SIGNED_RELEASE_CHECKLIST.md).
This is a CI-qualified development rehearsal candidate; actual owner/configuration
and host acceptance remain open. Earlier records below retain their dated scope.

Signer candidate (2026-10-22, IDEA-049-C SJ-04/SJ-05): key-free `signer.json`
`f632bbcb…` for run `larp-dev-rehearsal-20261022` / DB `larp_rehearsal1` / build
RC3a `fa1b6c9` is owner-approved (SJ-04-OA01). `larp.signer.service check` passes
against the original RC3a artifact `12365166625` after a local bind, and the dev
wallet has no leftover allowance (all four transactions accounted for, 18 pairs
read 0). [Evidence](evidence/sj05-signer-check-allowances-20261022/result.json).
Remaining: pre-install recapture with the same hashes, then LD17 installation
(host bind and `check`), LD18 key placement and LD19 first round. All readiness
flags stay false.

**Systems check SC-01 (2026-10-22, `d03bbb1`): the paragraph above is superseded for
installation.** Every local check passes, matching mirror RC4: 2470 passed / 7 skipped /
3882 subtests; systemd 5/5; demo, Docker, Terraform 19/19 + 1/1; both host-bundle roles.
RC3a cannot start the LV-01 signed run, so `f632bbcb…` can no longer be installed. RC4
(PR246) and the build-only `signer.json` `cd0b38b8…` (PR244) replace it. Both SC-01 findings
are resolved: Isaac confirmed the build-only extension (SJ-06-A2, PR251) and PR244 merged
(`4198b5f`, which also adds `prepare_rehearsal_db.py`, F2). RC4 was installed in SJ-06.
[Report](SYSTEMS_CHECK_20261022.md). Local evidence only.

Keith's PR226 inline review for #120 independently reproduces the DC-01 distributions
and supports the17bp MSFTB spread. RV120-RV01 addresses both findings: separate
two-sided drift from adverse BUY-output moves and actual reverts; remove the
unsupported fill-safety guarantee. [Corrected review](QUOTE_COST_REVIEW_120_20261021.md).
His COMMENTED review does not explicitly adopt the current exact profile/gas/model/
configuration. The selected profile, gas target and qualified runtime artifact are unchanged.

LD10-P02 independent owner review (PR230): the selected profile/policy/scope
hashes and 50 original numeric rows are consistent, but the recorded maximum
NVDAB SELL returns 20.106983 USDT above execution's 20.10 USDT cash cap. The updated
coverage reviewer now catches this existing runtime refusal on BUY and SELL;
assembly also refuses the incompatible input. [Finding and next owners](evidence/ld10-owner-review-20261021/README.md).
The original canonical RC2 qualification is unchanged and does not qualify the
new PR230 coverage-check source or grant installation approval.

LD10-P03 resolves the exit design under the unchanged limits. Before it, the
planner could leave a tiny cap-ratio residual, and `MarketPort` refused over-cap or
high-impact mandatory exit quotes as if they were discretionary, so a complete
exit could stall. Now mandatory SELLs use balanced children with 1% headroom, the
port validates with the request's mandatory flag, the coverage reviewer requires
covered child quotes, and the rehearsal reserve covers four positions × two
children (0.003072BNB; N=15 target 0.008832BNB, about 0.006138BNB additional at the
dated balance). [Exit split packet](evidence/rehearsal-exit-split-20261021/README.md) /
[IDEA-049-C LD10-P03](../ledger/IDEA-049-C.md). LD10-P04: the fresh read-only
packet has 22/22 request-bound quotes; the review covers 91/92 checks, and only the
pre-registered `INITIAL_BNB_EXIT_RESERVE` funding gap remains
([record](evidence/rehearsal-exit-split-20261021/ld10-p04-coverage.json)). AB-REL-RC3:
canonical `5bee006` passes all four mirror jobs (2452 passed, 7 skipped, systemd 5/5);
original artifact 12363800624 verified ([receipt](evidence/ab-rel-rc3-20261021.json)).
Installable candidate is `fa1b6c9` (RC3a): same runtime files, mirror run
39640064251 all four jobs PASS, artifact 12365166625 verified
([receipt](evidence/ab-rel-rc3a-20261021.json)); LD16 rechecks must bind it.
**RC4 (2026-10-22): `d03bbb1` (LV-01) supersedes it for the signed dev rehearsal.** Mirror run 39766825984
passes all four jobs (2470 passed/7 skipped), and original artifact 12419733594 (bundle `270fe81f…`) is verified
([receipt](evidence/ab-rel-rc4-20261022.json)). Install that artifact, not SJ-06-A1's local bundle.
**Installed and running on the dev wallet (2026-10-22 14:23Z, IDEA-049-C SJ-06):** run `larp-dev-rehearsal-20261022`,
DB `larp_rehearsal1`, `signer.json` `cd0b38b8…`. Runtime, execution and signer were all started, signer access was torn
down (IDEA-080 SA5) and the S3 packages were deleted. The first buy is allowed from 2026-10-23T00:00Z; J8 (the first
logged approve/swap/ACK) is open.
Remaining: funding, Isaac acceptance, LD16 bindings, LD17 installation.

PR204 repair candidate: [PC-AUDIT01-IMPL01](PR204_REPAIRS_20261020.md) implements
dispatch snapshots, rejected usage/per-stage caps, a separately pinned reviewer
prompt and request-budget reporting on a new branch from canonical697ff3a.
The full audit/shutdown history is retained. This is an unmerged repository repair
candidate, not an installed build or a new model-quality/affordability acceptance.
Private corpus reporting, independent review/labels and exact-host
acceptance remain with the owners in the live backlog. The retired trial stays stopped.

Canonical integration branch: **`codex/system-testing-20261012`**.
All new implementation branches and PRs start from this branch. PR133 is an
open noticeboard for links/status/owners only. Its branch is not a build base.
The one live backlog is [INCOMPLETE_WORK.md](../INCOMPLETE_WORK.md).
The post-PR199/200/201 closure sequence and evidence owners are in
[OG-01](POST_REVIEW_GATES_20261020.md).

CONS-01 combines all six retained PR heads through [PR195](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/195).
Validated runtime source `bd4dbee`: Linux/Python3.12.15/PostgreSQL14.24 **2162 tests
PASS /3628 subtests**, separate real-systemd **5/5**, Docker build/offline smoke
and runtime demo PASS. Two external-fixture tests remain unrun (the full suite
skipped those plus the five systemd tests tested separately).
[Consolidation evidence](CONSOLIDATION_20261019.md) / [machine receipt](evidence/consolidation-20261019.json).
PR195 merged at `dfabdea` on2026-10-19; all six original PRs are MERGED.
At that promotion PR133 was the only open PR and remains noticeboard-only. Org CI executed zero
steps because of account billing/spending limits. No host/deployment/readiness is inferred.

## Documentation consolidation — 2026-10-21 SGT

CONS-02 retains PR196/208/209/213 in canonical documentation and retires their
separate review queues. [Retention/evidence](CONSOLIDATION_20261021.md),
[current LD ordering](LIVE_DEPLOYMENT_PLAN_20261020.md),
[delegated policy](../ledger/IDEA-084.md) and
[signed release procedure](LD15_SIGNED_RELEASE_CHECKLIST.md).
PR203 is superseded by PR207, whose history contains its exact head.
No implementation PR remains open at RV01 closeout; PR133 stays noticeboard-only.
PR206/212/217/218/219 and PR217 repair follow-up221 are merged, alongside
PR207/210/211/215/216. Their checks apply only
to their recorded sources; no combined release or hosted acceptance is implied.

## Repository scope retained

- Existing unsigned runtime, model routing, durable audit/accounting, S1 input
  wiring and close jobs, signer configuration assembly, balance-health and
  rehearsal-evidence tools previously collected on PR133.
- PR139 source-acquisition evidence and PR172 historical funding handoff as
  records, with actual source/funding tasks remaining in the backlog.
- PR191 source-link regressions and original interim provenance; PR192 C05
  review decisions; PR193 exact signer input inventory and handoff.
- PR194's **opt-in untrusted-router mode**. This is implemented capability, not
  approved live policy, verified contract behavior or signer activation.

## Router choice and signer status

There are two mutually exclusive supported configuration paths:

| Path | Inputs / limits |
|---|---|
| Source-verified router | Complete verified source/ABI/deployment binding, independent source review and pinned RouterEvidence.v1 plus recorded-route checks. Source is still unavailable in the retained packet. |
| Untrusted router (B02-U / DEV-23) | Isaac selected the trust direction in B09-TRUST01 (PR196); PR205 supplies named-reviewed policy hash `05759e90…`; actual measured #44 acceptance and current policy/configuration binding remain. Fresh layout/replay/preflight checks are required. Recipient and actual contract enforcement remain unverified. This mode does not support native-BNB gas top-ups. LD06 adds disabled-by-default bounded allowance cleanup; actual policy/gas/timing/host acceptance remains. Abnormal-fill accounting still blocks unresolved outcomes. |

The consolidation did not select a mode; B09-TRUST01 subsequently selected the
API-trusted direction. Verified source is required only for the source-verified
path. Existing checked-in configs do not install an untrusted policy. Never label untrusted code source-verified,
substitute a review name for actual acceptance, or turn readiness flags true.
The old signer.json remains a historical source-path draft with unset bindings
and pending caps. A selected untrusted configuration uses its own policy-file/hash
pair instead of router-evidence fields; both cannot be set together.

LD01 aligns assembly/proposal/Gate B reports and current handoffs with both
paths, retaining policy/hash/review and false readiness flags. At `22039ba`,
focused Linux/Python3.12.15/PostgreSQL14.24 verification passed **167 tests /
555 subtests / zero skips**. This is reporting/tooling acceptance, not a full
suite, signed release or host qualification. See [IDEA-070 LD01](../ledger/IDEA-070.md#ld01--mode-aware-readiness-and-handoffs-2026-10-20-prospective).

LD06 adds [bounded allowance recovery](ALLOWANCE_RECOVERY.md) before the next
valid stock intent, independently gated by execution and signer opt-ins. At most
one zero-only approval per eligible token is allowed under the parent's original
authority, gas budget and wallet barrier. Supporting receipt gas is journaled and
replayed without creating a swap order. No configuration enables the feature;
PR202 records Keegan review; actual policy/reserve/timing/host acceptance remain.
Final LD06 source913b400: full Linux/Python3.12/PostgreSQL14 **2190 passed /3660
subtests /eight explained skips**; root-sensitive permission case exercised
separately. Five real-systemd and two external-fixture cases remain unrun.
[Verification receipt](evidence/ld06-allowance-recovery-20261020.json).
LD06 delivery: [PR202](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/202).
Canonical PR199 now records initial-gas-only scope; LD08 and measured cleanup/exit
reserves remain open. Its declaration is retained in the normal canonical merge,
with five register checks/three subtests PASS and unchanged execution/test code.

LD08-IG01 incorporates PR203 and completes the repository low-gas controls:
sourced action budget, full-book exit reserve/minimum-trade checks, quiet-boundary
durable incidents, archive health metric and a dedicated Terraform alarm. Source
`4044c82`: Linux/Python3.12/PostgreSQL14 **2241 passed /3686 subtests**, eight
explained skips; root-sensitive permission case passes separately. Terraform
**19/19**, dependency checks, deviation rendering and offline demo PASS.
[Acceptance matrix](INITIAL_GAS_ONLY.md) / [receipt](evidence/ld08-initial-gas-20261020.json).
No numeric policy, installed alarm, exact signed release or host is accepted by
these offline results.


PR211 merged at `0c1c77a` after LD02b-RV02 review and two P2 repairs: full
private-value filtering before error formatting and exact simulated allowance
overrides. Combined with canonical PR207:125 local tests/449 subtests/zero
skips using disposable PostgreSQL14.24. [Review receipt](evidence/pr211-review-20261021.json).
Archived fresh-calldata/gas packets remain unchanged; provider-reported RFQ
expiry does not establish the inner validity interval. Real gas/caps/provider/
preflight/release/host acceptance remains open; hosted CI is billing-blocked.

PR210 merged at `88c5544` after LD04-P-RV01 repaired missing authority checks
in public LIVE validation. Both-absent legacy output and initial-only+authority
candidate hashes are unchanged. Full local macOS/Python3.12/PostgreSQL14.24:
2283 tests/3730 subtests PASS,10 explained external/platform skips.
[Review receipt](evidence/pr210-review-20261021.json). This is not signed release,
measured gas/S1/profile adoption, Linux/systemd or host qualification.

PR215 merged at `c854c82` after LD02cd-RV01 repaired four P2 collector issues:
pre-format privacy filtering, exact proven-slot/value overrides, actual RFQ
probe-age reporting and response amount binding. Pushed source `21b8e88`:
41 offline tests/62 subtests/zero skips on macOS arm64/Python3.12.14; no repaired-
source full-suite claim. [Review receipt](evidence/pr215-review-20261021.json).
Archived packets are unchanged: Q2 FAIL/Q2b amended PASS; historical actual
RFQ ages remain unmeasured. LD02d contributes 39 successful gas values plus one
refusal from 40 attempts, with max BUY944,814/SELL930,548. These do not establish
size independence, profit, numeric caps or full exit coverage. Gas-budget
proposal and RG2 crash design remain proposals. Actions39556642979 executed
zero steps due account billing/spending limits. PR217's operator/measurement
record is now retained with the RV01 correction below; it does not qualify signer/host timing.

PR216 merged at `657efd3` after LD09-B-RV01 review. The optional sizing budget
reduces minimum-trade cost assumptions while the action/exit budget remains
separate; added tests exercise S1 monitoring and the actual planner reserve
barrier. Source `3e73086`: full local macOS/Python3.12.14/PostgreSQL14.24
**2323 passed /3748 subtests /10 explained external/platform skips**; focused
70 tests/44 subtests/zero skips. [Receipt](evidence/pr216-review-20261021.json).
Actions39558766897 ran zero steps due account billing/spending limits.

**CAP-02: #44 numeric ceilings are APPROVED under Isaac's explicit delegation.**
[Exact policies/hashes](evidence/signer-numeric-ceilings-20261021.json): USDT35
development/70 final, retained finite raw stock caps, pinned router-only spender,
no native-BNB input, cleanup disabled, fee ceiling0.0002BNB. Real policy boundaries
and archived20/40USDT quantities/profile/fee envelope checks pass. No further
permission round is needed for these exact ceiling choices. Current complete
holdings and the actual selected S1/fallback profile, request-bound quotes,
signed child-gas/cleanup/full-exit/seeding and environment configuration coverage
remain unverified. The old pair formula is below separately rounded child gas
limits, so its candidate action/reserve values are not approved execution
envelopes. Historical drafts/examples remain unchanged; nothing is installed.

PR217 originally merged at3b83114 during Isaac's review. RV01 fixes landed in
PR221 at23a98b3: exact retired-run/dev-shadow/inactive-state guards, failed-read
refusal, privacy filtering before/after JSON encoding and error flags, per-event
grouping, and corrected attempt-clock/anchor semantics. Original evidence files
are unchanged; [reviewed summary](evidence/ld12-ops-measure-20261021/README.md)
withdraws the20.4s hard ACK bound. Actual send/ACK timestamps were not captured;
5.387s is a log-to-latest-attempt-clock gap. Source09d5938:40 tests/10 subtests/
zero skips, including real PostgreSQL collector SELECT/write-refusal and
delivery-age integration. [Receipt](evidence/pr217-review-20261021.json).
CI39576593343 ran zero steps due billing limits; no full-suite/host claim.

Keegan's team owns operator LD12/17/19/21/23. Host writes and signer sessions
still need Keegan's separately recorded authorization. Per-unit RSS, actual ACK
timing, signed execution/finality/drain/stall/recovery and Isaac's exact LD14
values remain open. Concurrent PR206 model repairs and PR212 drill harnesses
are merged with private/real quality, affordability, actual drills and host
acceptance still open. PR219 records RG2 and read-side/pre-sign simulation
directions; their acceptance is not created by this collector review.

## What still blocks installation / live acceptance

**PF-01 (2026-10-21 SGT):** Isaac delegated profit-focused policy choices in
[IDEA084](../ledger/IDEA-084.md). S1/95%, five-name/SKHYB scope, drawdown recovery,
terminal windows, valuation/cost/model/provider/recovery directions are decided
for implementation. Measured weights/gas/#44/budgets/ops values, affected code
and tests, exact declaration/release and actual host/signing acceptance remain.
This policy record does not change runtime readiness or qualify missing inputs.

| Owner | Next accepted result |
|---|---|
| Isaac + Keith + approved operator | CAP-02 numeric signer policy hashes are approved. Verify their deployment coverage against the actual selected measured profile, fresh complete holdings and exact initial-only whole-run/exit signed-child gas; B09/PF-01 scope is decided. PR207 (LD08-IG01) adds low-gas incidents/metric/alarm; measured values and actual alarm acceptance remain. PR205 reviewed the router policy; fresh replay/preflight and actual configuration/host acceptance remain. Historical fallback estimates do not qualify caps. |
| Keegan + operator | #27 Option A is implemented by PR200 and L=660s/m=30s selected in the retained LD04-V01 record. PR210 authority provenance/builder is merged and initial-only+L/m candidates regenerate exactly. Keith #120 actual profile/weights/calendar/gas review and adopted-source/actual-host timing checks remain. |
| Approved provider/operator + Isaac | Qualify the PF-01 execution read-side provider direction and current reconciliation/funding disposition. Initial-gas-only scope is selected (PR199); PR207 controls are merged; independent Keith/Keegan review remains. Native top-ups are outside the selected scope and are not declared qualified. Balance-provider MATCH is not execution/finality qualification. |
| Keegan + approved team operator | Exact qualified signed release and run/wallet/DB/CA/selected-router-policy bindings, isolation/time/IAM/TLS/routes and approved session. Isaac places the key only in that session. |
| Operator + reviewers | Real logged agent approve/swap, canonical reconciliation/ACK, resource/clock/delivery measurements, restart/restore/HALT/anchor/final-wallet drills and actual rehearsal evidence. |
| Keith + account owners + Keegan | PF-01 fixes policy direction; actual S1 weights/data/parameters and code qualification, model trial/rights/usage/accounting evidence, source coverage and final declarations remain. PR206 repairs are merged; private/real-input acceptance remains. PR201 delivery-age implementation is merged; C05 numeric settings require measurements. |

The full details/acceptance IDs remain in the backlog and topical records.
Older checklist/handoff documents are dated evidence; this page and the latest
backlog resolve current status. No old CI/artifact/host result qualifies changed
code or a new release. Org Actions availability is separate from local tests and
the approved mirror route. A source merge is not an installed release.


## KG-DEC-01-RV01 — Isaac's pre-sign simulation review (2026-10-21)

PR223/224 corrected the implementation status: `Executor.prepare` already
requires a positive exact-calldata Web3 gas-limit estimate before a swap attempt
exists. Isaac accepts that gate and the stored KG-DEC-01-H host-refusal receipt
within their scope. Canonical6746ef0, independent local PostgreSQL regressions:
**62 tests /47 subtests /zero skips**; packet SHA-256 reproduced. No application,
configuration or test change is introduced by this review; the duplicate PS-01
prototype was reverted and pushed without merging. LD08/10 gas work was also
stopped cleanly pending Keith's selected-profile/full-exit/fee/N packet.

The API's generic refusal does not establish a particular EVM revert cause.
Prepare-time estimation does not guarantee later execution or prevent expiry.
First funded positive swap estimate/transaction/receipt/ACK remain LD19/20;
config/release/host and exact gas/caps acceptance remain open. No live call,
host operation, key action or activation occurred. Full record:
[IDEA-070 KG-DEC-01-RV01](../ledger/IDEA-070.md#kg-dec-01-rv01-results--pass-within-recorded-scope)
and [verification receipt](evidence/kgdec01-isaac-review-20261021.json).

## GC01 / RP01 — gas candidates and fresh local router checks (2026-10-21)

[GC01](evidence/gc01-bounded-profiles-20261021/README.md) supplies reproducible
conservative initial-only EQUAL_WEIGHT candidates: 0.000384 BNB per two-child
action, 0.001536 BNB for four exits. Expected-cost sizing remains separate.
Cleanup stays disabled; the eight-child calculation is a non-adopted scenario.
Keith's selected profile/whole-run counts/fee acceptance and actual holdings,
execution-budget/reservation, funding disposition and host/alarm coverage remain.
No runtime pin, deployment or funding amount is adopted.

[RP01](evidence/rp01-router-readonly-20261021/README.md) passes fresh local
production replay/tamper checks on ten 20 USDT BUY/hypothetical-output SELL quotes
and production code/facet/dispatch/allowance preflight through both selected
RPC providers. 2026-10-21 14:25–14:27 UTC; worst quote-to-preflight completion
6.711 s, policy05759e90… unchanged. This closes Isaac's local replay slice;
actual selected profile/full holdings and production host/release binding,
runtime per-attempt preflight and signed-round/finality/gas/fee/ACK acceptance
remain open. The signer stays offline from RPC. Neither report enables signing.

Final pushed source ffe91d9: macOS/Python3.12.14 focused suite 68 tests/280 subtests
PASS, three disposable-PostgreSQL skips; no full-suite/CI or signed-host claim.

GC01/RP01 are independent dated technical evidence. The selected deterministic
profile and completed coverage/qualification below take precedence for this rehearsal;
GC01 candidates and its illustrative count margin are not adopted.

PR232-RV01 independent review:130 tests/334 subtests/zero skips PASS on Linux/
Python3.12.14/PostgreSQL14.24 at9221277. Frozen candidates/public bindings reproduce;
all205 runtime release files match the original qualified b22207e manifest.
Actual CLI/report refusal/staleness/tamper cases are covered. No fresh live call or
private-original re-verification is claimed. [Receipt](evidence/pr232-review-20261021.json).


## 2026-10-21 scoped rehearsal qualification (LD05-Q01 / LD10-Q01 / LD11-RH01)

Keegan selected the deterministic EQUAL_WEIGHT fallback with model evidence SHADOW;
no hosted-model calls/adoption. [Exact inputs/technical coverage](evidence/rehearsal-qualified-inputs-20261021/README.md):
profile41332056…, documenteb61ca86…, CAP-02 policy3241abd3…, router05759e90… .
Fresh primary read-only holdings at14:10Z MATCH (98USDT,0.002694498869362886BNB, stocks0,
nonce2/2, allowances0, no inflight state). 15/15 request-bound quotes/decode/tamper checks;
50/50 numeric caps checks COVERED. Owner review/final configuration binding remain.
The complete two-child action budget is384000000000000wei and four-exit reserve
1536000000000000wei. N=15 seed target0.007296BNB replaces the old approximate target;
additional0.004601501130637114BNB is a separate funding-owner action.
LD05 abnormal raw-outcome/gas accounting and durable signing quarantine are merged in
PR231 at canonical `b22207e050ea50338d48cf7129378caf480ef290`;
canonical CI and original-artifact verification PASS in AB-REL-RC2 (candidate only).
No host write, signer-host/key access, wallet operation or paid model call occurred.


2026-10-21 AB-REL-RC2 latest: Keegan explicitly approved the repository merge despite
the pending branch CI conclusion, resolving the automatic-review block for this merge.
PR231 is merged at `b22207e`; canonical mirror run39617977531 is completed/success
on all four jobs:2416 passed,7 explained skips,3808 subtests; real-systemd5/5,
demo/Docker and both-role host-bundle qualification PASS.
[Receipt](evidence/ab-rel-rc2-20261021.json): branch commands passed2416 tests plus
systemd/Docker; original branch artifact12352148043 ZIP/bundle/manifest and244 checksums
verified. Branch runtime metadata remains in_progress; it is not a finalized PASS.
Canonical original artifact12352993133 is verified: ZIP307d4c4b…8657,
bundleecc589a5…ba2a, manifest427a8cc6…f8b0;244 file checksums and205 manifested
source/config files match. LD15 has a CI-qualified canonical rehearsal candidate.
Actual signed-release/configuration/owner binding and installation acceptance remain
at LD16/17; registration/runtime/operations manifest bindings are still null.
Selected inputs are the three `-deterministic` files; older candidates are historical.
