# October 18 model-trial handoff — TR-AC2 / PC-GAP01

User-delegated confirmation for Keegan's workstream, recorded by the assistant.
This records Keegan's release/bar/gap decisions. It does not attribute personal
approval to Keith or a collective decision to the team. PR #133 and PR #126 stay open.

## Release accepted for the unsigned shadow trial

Use the existing CI-produced `larp-7a0ea1433b3a-x86_64.tar.gz`, build
`7a0ea1433b3a029e9e2dc97817bac98a7e09c0ce`, from mirror run
[39091699018](https://github.com/Cookiemunchrr/larp-ci-mirror/actions/runs/39091699018),
artifact 12122169313. Preserve the existing release; these decision documents do
not change its application, prompts or configuration.

| Bytes | Accepted SHA-256 |
|---|---|
| Bundle | `ff951451bc80b518620f895b2b0a871df188ce2cb2d3e36e04a58754c7f5de06` |
| External and embedded manifest | `bb17b7ffc28eeb2e14594a80895827bed5327b8408f519692870dcdeffdca70a` |
| Included RDS CA | `d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b` |

Acceptance relies on the published PC-CI02 verification at PR #133 commit
`9b363e6`: four green jobs, matching sidecar/embedded manifest, all 192 manifest
file hashes, repository identity and CA. The verification record is retained
byte-for-byte in [the mirror evidence](evidence/model-trial-mirror-20261018.json).
Its `PENDING_KEEGAN` field describes that earlier verification time; the current
decision is [TR-AC2](evidence/model-trial-decision-20261018.json).
This session's private-mirror API requests returned404, so it did not download or
independently re-hash the bundle. Independent source validation of the identical
application/config/test tree passed 1973 tests and 2934 subtests, with 6 documented
skips (IDEA-049 MERGE-20261018). No hosted installation is claimed here.

Yao verifies these same exact hashes at installation and retains the existing
version/bind/activation procedure. The archive fix and signed-model capability
are present, but this acceptance is for `mode: dev`, `execution: shadow` only.

## Trial protocol confirmed: TRB-01A–E / TR-AC2

TR-AC2 confirms the corrected protocol proposed in PR166 at `6f377dd`, reviewed
while this handoff was being prepared. It supersedes the initial TR-AC1
confirmation of the October 16 bars where they differ. The exact proposal text
and its SHA-256 are retained in [IDEA-057](../ledger/IDEA-057.md). Publication is
effective before the first job under this protocol; earlier jobs retain their
original protocol and are never relabelled prospectively. No personal Keith or
collective team sign-off is inferred.

| Measure | Frozen bar |
|---|---|
| M1 availability | At least 95% of jobs return validated ASSESSED/ABSTAIN by 60 s; unavailable/late jobs remain failures. |
| M2 latency | p50 at most 20 s; p95 at most 45 s; any job over 60 s is a reported defect. |
| M3 OpenAI | Trial charge strictly below US$8 and each UTC day strictly below US$2.50; reaching either triggers K1. Forecast `C_end + conservative daily rate × remaining days + planned extra evaluation spend ≤ US$40`, through Nov 13 00:00 UTC as a budgeting horizon, retaining the US$10 reserve. Include RESERVED/UNKNOWN charges and reconcile prior reservations. |
| M4/M6/M7/M8 | Report external usage/cost, escalation, switches and baseline disagreements. Escalation over 60% is an alert, not a kill. |
| M5 verification | Routine claim-verification at least 80%; each reviewer at least 90%; schema-valid at least 95% per stage. Require 10 completed jobs per declared path and 10 replies/claims per required stage; under-covered paths are unqualified. |
| M9 independent labels | Adverse-event recall at least 90% and omission no worse than baseline; zero unsupported Class 1/2 findings. Need 10 distinct adverse events across 5 filing families, including both classes. Abstained/unavailable/late detections are misses. |

Keep K1–K4 identity, safety and accounting stop criteria and TRB-01A outcome
order: a demonstrated kill/safety defect is NOT_SUPPORTED even with little data;
otherwise missing evidence is INCONCLUSIVE; with sufficient evidence any M1/M2/
M3/M5/M9 miss is NOT_SUPPORTED; only then can all passing bars support the tested
unsigned scope. Operator spend stops require monitoring/headroom before dispatch,
including in-flight reservations; a daily snapshot cannot enforce the sublimits.
The implemented automatic US$40/US$10 account guard remains unchanged.

PC-BUD03 at PR133 commit `2bac3a5` now records owner confirmation of exactly
US$48 from the original US$50 allocation: use **2,000,000 micro-USD prior spend**
for P1, retaining US$10 reserve and US$38 operating headroom. This supersedes our
earlier pending-input note; it is owner-reported, not an independent billing API
check. No ledger was initialized here. AIand can continue assessments when
OpenAI admission stops; report any failed mixed-route window and its external-only
continuation separately. Funding/availability still require actual provider checks.

Freeze M9 seed `larp-model-trial-20261018-M9-v1` before drawing. Use all
filings if at most 40. Otherwise take 40 unique `(issuer ID, filing artifact hash)`
pairs. For repeated jobs on the same pair use the earliest recorded request
(tie-break by assessment ID) to assign its issuer, ordered routing-stage labels
and final status stratum. Rank strata by SHA-256 of canonical JSON `[seed,
"stratum", issuer, stages, status]`; within each, rank filings by SHA-256 of
`[seed, "filing", issuer, artifact_hash]`. Canonical means UTF-8 JSON, sorted object
keys, compact separators and ASCII escaping. Break hash ties lexically by the
same canonical bytes. Select one from each ranked stratum in round-robin order
until 40 are selected or the population is exhausted. Record any unrepresented
strata. Retain the population/selection manifests and their hashes before blind
labelling; labels and private document sets stay outside Git. No drawing or
labelling occurred here. This freezes selection without inventing the population.

Qualification needs **72 observed unsigned hours**, at least 20 completed unique
jobs, route/stage coverage and independent-label coverage under TRB-01. Planned
maximum cutoff is **2026-10-22T00:00:00Z** (end of Oct 21). Pauses, deterministic
operation, supplemental probes and signed rehearsal never supply unsigned hours.
Close/archive the unsigned window before any separately approved signed window.
An Oct 20 report is interim/provisional if evidence is short; a development-only
rehearsal exception must be a separate recorded decision/deviation, preserving
an inconclusive/failed trial verdict. No scored adoption is granted here.

## DOJ/BIS: explained historical-backfill gaps for this shadow window

PC-GAP01 accepts the PC-AWS10 pagination backlog as an explanation for
`source:doj-press` and `source:fr-bis` in the fixed report window
**2026-10-17T11:00:00Z to 2026-10-18T11:00:00Z**. It permits the unsigned model
trial after the report is reviewed. It does not declare either source complete.
The code checks the listing head while continuing history, but the poll log
does not record `head_checked`; do not claim that flag was observed on the host.

Yao produces and hashes the original report **without** incidents first. Before
applying the two explanations, inspect the original poll log for both targets:

- Polls cover the full window at the existing declared cadence, including edges,
  with no gap over twice cadence (DOJ10 min, BIS15 min). A true polling outage is
  outside this exception.
- Each in-window poll completes normally (OK/NOT_MODIFIED), has a valid completion
  clock and no transport/parse error or permitted-record rejection. Truncation
  must be attributable to the documented pagination backlog, not an unknown error.
- Retain the failed/complete poll counts, truncation flags and all original logs.
  Any corrupt log, other target failure or separate archive-delivery incident
  stays a separate unresolved item; do not explain it with these entries.

If those checks hold, run the same report again with the two exact entries in
[model-trial-gaps-20261018.json](evidence/model-trial-gaps-20261018.json), using
the file copied from this decision commit into Yao's activation pack:

```sh
python -m larp.sources.live report \
  --from 2026-10-17T11:00:00Z --to 2026-10-18T11:00:00Z \
  --incidents /path/to/activation-pack/model-trial-gaps-20261018.json
```

Run through the existing evidence-user environment, with the original
`LARP_ARTIFACT_ROOT`; the activation-pack path above is a required local input.
Retain both reports, the incident file and all three hashes. The CLI may return
PASS with explained gaps. Describe that as **shadow trial accepted with known
incomplete coverage**, not a full-source Gate A PASS. No wildcard explanation,
other time window, log edit, cursor reset, source disablement or relaxed runtime
coverage check is approved. The future 11:00 UTC report was not inspected here.

Runtime `SourceCoverage.v1` remains INCOMPLETE and affected consumers remain
impaired. The exception gives no clean-evidence or signing authority and does
not waive any other model/host prerequisites. Do not reuse these historical
exceptions for later reports. Before signed/final source acceptance, Yao owns a
reviewed bounded-history/window coverage implementation with explicit overlap,
late/amended-item handling, restart and truncation tests; Keegan reviews its
coverage claim and the new release. Scope it separately rather than changing
the accepted 7a0ea14 bundle.

## Remaining handoff inputs

- Keith: matching/adjudication rubric and blind labels, provider terms/funding
  work and the trial report. Review proposal PR166 is supplied and confirmed by
  TR-AC2; exact prior-spend input is owner-confirmed in PC-BUD03. Key receipt is
  owner-reported in PC-KEY01; this session did not read or validate keys.
- Yao: finish and hash the 11:00 UTC report and scoped explanation checks; retain
  archive incident/health evidence; verify/install the accepted release, provider
  catalog/served identities, budget P1, routing/build P2, new prepared/bound shadow
  run and its first assessment. Record actual UTC start and host results.
- Keegan: review actual report/trial outputs when they exist; later adoption,
  B4 and signed/final acceptance remain separate work. Today's three requested
  owner decisions are recorded; no host action or paid inference ran here.
