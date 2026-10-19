# Current shared build and remaining work

Canonical integration branch: **`codex/system-testing-20261012`**.
All new implementation branches and PRs start from this branch. PR133 is an
open noticeboard for links/status/owners only. Its branch is not a build base.
The one live backlog is [INCOMPLETE_WORK.md](../INCOMPLETE_WORK.md).

CONS-01 combines all six retained PR heads through [PR195](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/195).
Validated runtime source `bd4dbee`: Linux/Python3.12.15/PostgreSQL14.24 **2162 tests
PASS /3628 subtests**, separate real-systemd **5/5**, Docker build/offline smoke
and runtime demo PASS. Two external-fixture tests remain unrun (the full suite
skipped those plus the five systemd tests tested separately).
[Consolidation evidence](CONSOLIDATION_20261019.md) / [machine receipt](evidence/consolidation-20261019.json).
The canonical promotion is effective when PR195 merges; org CI executed zero
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
| Untrusted router (B02-U / DEV-23) | Explicit Isaac B09/#44 adoption and measured caps; named-reviewed live code/facet/allowance policy and hash; fresh layout/replay/preflight checks. Recipient and actual contract enforcement remain unverified. This mode does not support native-BNB gas top-ups; reverted-swap allowances and abnormal-fill accounting can block later work. |

The mode is not selected by this consolidation. Existing checked-in configs
do not install an untrusted policy. Never label untrusted code source-verified,
substitute a review name for actual acceptance, or turn readiness flags true.
The old signer.json remains a historical source-path draft with unset bindings
and pending caps. A selected untrusted configuration uses its own policy-file/hash
pair instead of router-evidence fields; both cannot be set together.

## What still blocks installation / live acceptance

| Owner | Next accepted result |
|---|---|
| Isaac + Keith + approved operator | Exact measured profile, fresh complete holdings, quote/fee/gas/top-up coverage and #44 policy hashes; explicit untrusted-mode risk decision if selected. Historical fallback estimates do not qualify caps. |
| Keegan + operator | #27 finite authority model, duration/margins and implementation/review using source/provider timing assumptions. The encoded long deadline still conflicts with short existing authority. |
| Approved provider/operator + Isaac | Qualified canonical/native tracing or a separately reviewed supported scope; current reconciliation and funding/no-further-funding disposition. Balance-provider MATCH is not native settlement qualification. |
| Keegan + Yao/approved operator | Exact qualified signed release and run/wallet/DB/CA/selected-router-policy bindings, isolation/time/IAM/TLS/routes and approved session. Isaac places the key only in that session. |
| Operator + reviewers | Real logged agent approve/swap, canonical reconciliation/ACK, resource/clock/delivery measurements, restart/restore/HALT/anchor/final-wallet drills and actual rehearsal evidence. |
| Keith + account owners + Keegan | Final S1 inputs/experiments/parameters, model trial/rights/usage/accounting decisions, missing source/evidence coverage and final declarations. C05 numeric settings and delivery-age implementation remain open. |

The full details/acceptance IDs remain in the backlog and topical records.
Older checklist/handoff documents are dated evidence; this page and the latest
backlog resolve current status. No old CI/artifact/host result qualifies changed
code or a new release. Org Actions availability is separate from local tests and
the approved mirror route. A source merge is not an installed release.
