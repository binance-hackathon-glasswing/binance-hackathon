# Current shared build and remaining work

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
Active code reviews: PR206 and draft PR212. PR207, PR210 and PR211 are merged. Their checks apply only
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

## What still blocks installation / live acceptance

**PF-01 (2026-10-21 SGT):** Isaac delegated profit-focused policy choices in
[IDEA084](../ledger/IDEA-084.md). S1/95%, five-name/SKHYB scope, drawdown recovery,
terminal windows, valuation/cost/model/provider/recovery directions are decided
for implementation. Measured weights/gas/#44/budgets/ops values, affected code
and tests, exact declaration/release and actual host/signing acceptance remain.
This policy record does not change runtime readiness or qualify missing inputs.

| Owner | Next accepted result |
|---|---|
| Isaac + Keith + approved operator | Exact measured profile, fresh complete holdings, selected initial-only whole-run/exit gas coverage and #44 policy hashes; B09/PF-01 scope is decided. PR207 (LD08-IG01) adds low-gas incidents/metric/alarm; measured values and actual alarm acceptance remain. PR205 reviewed the router policy; fresh replay/preflight and actual configuration/host acceptance remain. Historical fallback estimates do not qualify caps. |
| Keegan + operator | #27 Option A is implemented by PR200 and L=660s/m=30s selected in the retained LD04-V01 record. PR210 authority provenance/builder is merged and initial-only+L/m candidates regenerate exactly. Keith #120 actual profile/weights/calendar/gas review and adopted-source/actual-host timing checks remain. |
| Approved provider/operator + Isaac | Qualify the PF-01 execution read-side provider direction and current reconciliation/funding disposition. Initial-gas-only scope is selected (PR199); PR207 controls are merged; independent Keith/Keegan review remains. Native top-ups are outside the selected scope and are not declared qualified. Balance-provider MATCH is not execution/finality qualification. |
| Keegan + Yao/approved operator | Exact qualified signed release and run/wallet/DB/CA/selected-router-policy bindings, isolation/time/IAM/TLS/routes and approved session. Isaac places the key only in that session. |
| Operator + reviewers | Real logged agent approve/swap, canonical reconciliation/ACK, resource/clock/delivery measurements, restart/restore/HALT/anchor/final-wallet drills and actual rehearsal evidence. |
| Keith + account owners + Keegan | PF-01 fixes policy direction; actual S1 weights/data/parameters and code qualification, model trial/rights/usage/accounting evidence, source coverage and final declarations remain. PR206 repairs are under review. PR201 delivery-age implementation is merged; C05 numeric settings require measurements. |

The full details/acceptance IDs remain in the backlog and topical records.
Older checklist/handoff documents are dated evidence; this page and the latest
backlog resolve current status. No old CI/artifact/host result qualifies changed
code or a new release. Org Actions availability is separate from local tests and
the approved mirror route. A source merge is not an installed release.
