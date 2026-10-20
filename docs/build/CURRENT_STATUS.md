# Current shared build and remaining work

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
| Untrusted router (B02-U / DEV-23) | Isaac selected the trust direction in B09-TRUST01 (PR196); actual measured #44 acceptance and named-reviewed live code/facet/allowance policy/hash remain. Fresh layout/replay/preflight checks are required. Recipient and actual contract enforcement remain unverified. This mode does not support native-BNB gas top-ups. LD06 adds disabled-by-default bounded allowance cleanup; actual policy/gas/timing/host acceptance remains. Abnormal-fill accounting still blocks unresolved outcomes. |

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
independent review and actual policy/reserve/timing/host acceptance remain.
Final LD06 source913b400: full Linux/Python3.12/PostgreSQL14 **2190 passed /3660
subtests /eight explained skips**; root-sensitive permission case exercised
separately. Five real-systemd and two external-fixture cases remain unrun.
[Verification receipt](evidence/ld06-allowance-recovery-20261020.json).
LD06 delivery: [PR202](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/202).
Canonical PR199 now records initial-gas-only scope; LD08 and measured cleanup/exit
reserves remain open. Its declaration is retained in the normal canonical merge,
with five register checks/three subtests PASS and unchanged execution/test code.

## What still blocks installation / live acceptance

| Owner | Next accepted result |
|---|---|
| Isaac + Keith + approved operator | Exact measured initial-only profile, fresh complete holdings, stock quote/fee/gas coverage, full-exit reserve/whole-run seeding and #44 policy hashes; reviewed selected-router policy. LD08-OG01 adds explicit initial-only candidates and stock-only cap/assembly controls for review; low-gas incident/alarm and measured acceptance remain open. Historical fallback estimates do not qualify caps. |
| Keegan + operator | PR200 implements and reviews #27 Option A, including final-release margins. Operator supplies actual timings; Keegan chooses L/m with Isaac/Keith review and per-value provenance. Without L/m, old short-authority refusals remain. |
| Approved provider/operator + Isaac | Qualified canonical/native tracing or a separately reviewed supported scope; current reconciliation and funding/no-further-funding disposition. Balance-provider MATCH is not native settlement qualification. |
| Keegan + Yao/approved operator | Exact qualified signed release and run/wallet/DB/CA/selected-router-policy bindings, isolation/time/IAM/TLS/routes and approved session. Isaac places the key only in that session. |
| Operator + reviewers | Real logged agent approve/swap, canonical reconciliation/ACK, resource/clock/delivery measurements, restart/restore/HALT/anchor/final-wallet drills and actual rehearsal evidence. |
| Keith + account owners + Keegan | Final S1 inputs/experiments/parameters, model trial/rights/usage/accounting decisions, missing source/evidence coverage and final declarations. C05 numeric settings remain open; PR201 implements the delivery-age guard, disabled until B is decided. |

The full details/acceptance IDs remain in the backlog and topical records.
Older checklist/handoff documents are dated evidence; this page and the latest
backlog resolve current status. No old CI/artifact/host result qualifies changed
code or a new release. Org Actions availability is separate from local tests and
the approved mirror route. A source merge is not an installed release.
