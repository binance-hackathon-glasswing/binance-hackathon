# Gate B remaining work — 2026-10-17

**CONS-01 current source:** build from `codex/system-testing-20261012`; PR133 is noticeboard only. Use [CURRENT_STATUS.md](CURRENT_STATUS.md) and the [live backlog](../INCOMPLETE_WORK.md). Dated branch/PR status below is historical where superseded. Source-verified and explicitly adopted untrusted-router paths are separate; neither is activated by consolidation.

Record: [IDEA-039 GB-RW1](../ledger/IDEA-039.md). Repository base: integration
`0672fb8`, which includes reviewed PR130 (decoder), PR131 (S1), PR144
(lifetime proposal), PR148 (cap proposal), PR149 (temporary signer access),
PR151 (historical funding note), and PR153 (provider timeout repair).
Main `fb95114` does not include most of that work.

## PR inspection and existing work

All **85 advertised PR heads** were fetched through native Git: 40 are ancestors
of main, 78 are ancestors of the integration base. The complete public inventory
is [gate-b-pr-inventory-20261017.tsv](evidence/gate-b-pr-inventory-20261017.tsv).
After initially blocked API access recovered, all 85 PR descriptions and
submitted-review records were fetched and their heads matched against Git,
with no discrepancies. The inventory distinguishes head subjects from API PR
titles and includes state, merge time and review-event counts. The live Gate B
issue discussions were also read: #27 and #44 still record pending decisions.
At this inspection, only PR126 and PR133 are open and PR139 remains draft. Oct 18 update: #155, #157, #158, #161, #163 and #164 are merged into integration (IDEA-049 MERGE-20261018); #126 and #133 stay open, #139 stays draft, and Isaac's #165 (S1 execution windows, B6) merged817eb71 after EB-RV2 current-integration review/full local acceptance.

Seven heads remain outside integration: historical closed PR10/82/83/89, the
remaining-work brief PR126, the pre-trading checklist PR133, and router-source
acquisition PR139. Their relevant records were read without merging them.
PR133 reports that primary provisioning, database migrations/grants, terms,
SNS email and primary route/time checks have already been completed; those
steps must not be repeated just because older integration documents are stale.
Its accepted mirror-build decision is also recorded separately from actual
release evidence. These are prior owner-reported results, not fresh cloud checks.

The decoder, cap/lifetime proposals, native top-up settlement, immutable signer
registry, database reservations, crash recovery, and temporary signer-access
Terraform already exist. The missing work is their qualification and the
specific decisions/evidence below.

## Current dependencies — after PR199/200/201, 2026-10-20

Use the current LD01–LD24 owners/order on
[PR133](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/133).
B09-TRUST01 / [PR196](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/196)
selects API-trusted behavior; named policy/hash review and #44 numeric acceptance
remain. Earlier inventories and bundle receipts below are historical.
Neither proposal approval nor host acceptance is inferred from merging code.
[OG-01](POST_REVIEW_GATES_20261020.md) gives the current closure sequence and
measurement/decision/release/host owners. LD08-OG01 adds explicit initial-only
candidates for review; legacy top-up inputs remain historical capabilities.

| Work | Current evidence and next concrete action |
|---|---|
| Selected untrusted policy (#33, GAP-29; LD02/03) | Operator supplies current router/facet/code/layout/allowance bindings and fresh quotes; Keegan reviews exact policy/hash; Isaac replays and qualifies live preflight. Source guarantees remain unverified, with no established maximum loss. #138 remains incomplete optional source-path acquisition, not a selected-path prerequisite. |
| Source-verified path only (#138) | Complete attributable source/ABI/compiler/deployment binding, independent four-guarantee review and RouterEvidence.v1 remain unavailable. Do not fabricate them; no source acceptance is claimed. |
| Recorded-real route qualification | Verified mode uses `larp.execution_live.router check` after source review. Selected untrusted mode uses `larp.execution_live.untrusted_router check` with the reviewed policy/hash and fresh request-bound quotes, then live preflight. Historical SP-01 hashes do not establish current freshness. Both retain the logged agent round/ACK acceptance. |
| Signing lifetime (#27) | Option A and the final-release authority/deadline margin checks are merged in PR200 (IDEA-049-C LD04-RV01). Keegan still chooses L/m from operator timings, with Isaac/Keith review and per-value provenance. Recorded routes carry roughly 500-second deadlines; 60s is not an adopted value. Proposal/quote freshness and uncertain-send reconciliation remain unchanged. |
| Independent signer caps (#44) | PR148 proposes development/final USDT inputs 35/70 and fee 0.0002 BNB. These remain unapproved for installation. Run the current-input review below, review full holdings and adjustment/splitting scenarios, then record the exact policy/profile/metadata evidence and approved hash. Use the router as spender, never the facet. |
| New release bundle | GB-RW2 mirror [run39030800352](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39030800352) passed all four jobs on reviewed integration `0672fb8`, including PR130/144/148/149/153/131. Artifact `12099524179` exists; this session's network policy blocks downloading it. Sidecar/manifest verification and the two file hashes remain required before the AWS-owner handoff; see the [build record](evidence/gate-b-mirror-build-20261017.json). Any later adopted source change requires a newer reviewed release. |
| Signer provisioning | The access choice and Terraform review are complete (IDEA-080 / PR149). After numeric-policy approval, the checklist's AWS owner applies temporary development SSM endpoints, provisions/binds the approved configs, and records SA4/SA9. Isaac places the key on the signer host only; the AWS owner records teardown SA5. This cloud machine has no usable AWS profile or private backend/input files; injected AWS config files contain zero profiles and boto3 resolves ProfileNotFound. |
| Gas scope, initial funding and native tracing (#30/#106, GAP-49; LD07/08) | PR199 decides initial gas only. LD08-OG01 introduces explicit initial-only profile/mapping/signer and stock-only cap/assembly controls for review. Complete low-gas incident/alarm, measured reserve/whole-run dev/final seeding and exact #44/host acceptance remain. Legacy top-up mode still needs native qualification; #30 stays open. Current wallet/in-flight and funding/no-further-funding disposition remain mandatory; historical receipts authorize no additional seed. |
| First signed round and host drills (DR-02..06/19) | After Gate A and every prerequisite above, the agent produces the minimum-size dev approve/swap and ACKed round. Record chain reconciliation, success/revert reservation release, host crashes at each durable boundary and a recorded shadow-day replay. Existing synthetic/real-local-PostgreSQL tests are engineering evidence only. |
| Timing and rehearsal | The current rehearsal buy window begins Oct 21 00:00 UTC (08:00 SGT). An earlier dev window requires its recorded decision/version event. Keep the conditional rehearsal-shape decision in IDEA-049-D D-DN-02; record an applicable shortfall when the gate is missed, rather than recording a future shortfall now. |

S1 B6 code is consolidated; actual selected-profile/session/host acceptance stays
open. This cap review does not qualify that behavior. LD06 allowance recovery
and LD05 abnormal-fill disposition also remain open, including cross-token and
final-exit behavior. No sustained-quarantine condition is silently cleared.

## Current-input signer-cap review

`python -m larp.execution_live.caps_review` provides the previously manual numeric
comparisons for #44. It reads only explicitly selected, hash-pinned local files,
using the real profile, execution-config and signing-policy validators. It checks:

- The profile's complete largest target position plus reserve, per-trade cash
  cap (plus gas-top-up input for legacy top-up profiles), converting micro-USDT to raw 18-decimal USDT exactly.
- Every current stock holding in its own metadata-checked raw token units,
  without assuming that sell splitting exists.
- The configured worst-case gas envelope and measured/quoted transaction fees
  against the signer's independent fee ceiling.
- Successful, fresh wallet/chain/router-bound quote artifacts, including all five
  BUY/SELL pairs, input quantities and execution gas limits. Explicit initial-only
  profiles exclude native BNB from the signer policy and reject native quote
  artifacts; legacy top-up profiles still require BNB:BUY coverage.

Returned `routerResult` token addresses, decimals and input amount must match the
request and configured units; quoted output must cover its positive minimum.
Any returned transaction sender/chain metadata must also agree. These metadata
checks do not decode calldata or establish source/route executability.

Prepare a public-input manifest outside the checkout:

```json
{
  "schema": "GateBCapsInputs.v1",
  "wallet": "<lowercase public wallet>",
  "run_id": "<configured run>",
  "build_id": "<full registered commit>",
  "environment": "REHEARSAL",
  "max_age_seconds": 60,
  "files": {
    "profile": {"path": "profile.json", "sha256": "<actual file hash>"},
    "signing_policy": {"path": "policy.json", "sha256": "<actual file hash>"},
    "execution_config": {"path": "execution.json", "sha256": "<actual file hash>"},
    "initial_state": {"path": "initial-state.json", "sha256": "<actual file hash>"}
  },
  "quote_artifacts": [
    {"path": "<original Web3Observation.v1 file>", "sha256": "<actual file hash>"}
  ]
}
```

The 60-second freshness budget above illustrates the format; the reviewer must
supply the applicable budget explicitly. List every selected quote artifact;
the checker reports missing pairs and refuses stale/future or altered inputs.
`policy.json` contains only the `signing_policy` object, not a proposal wrapper or
credentials. The initial portfolio includes all five symbols and exact 18-decimal
BNB; its wallet/run/environment and token scales must match the execution config.
Hosted execution configs also require their pinned public database CA locally
because the real config validator checks it. No service or database is opened.

```sh
.venv-runtime/bin/python -m larp.execution_live.caps_review \
  --inputs /absolute/external/caps-inputs.json \
  --output /absolute/external/new-caps-review.json
```

`numeric_status: COVERED` means only that the supplied local numbers fit. The
overall result stays BLOCKED, `ready_to_install` and `signing_enabled` stay false,
and exit 2 preserves owner review. Example caps add POLICY_APPROVAL_REQUIRED.
Malformed input returns 4. Output is private, exclusive and outside the checkout;
no overwrite, credential lookup, networking, policy installation or signing occurs.
Pins do not prove real-world provenance, fresh portfolio reconciliation, source
guarantees, quote executability or owner approval.

SA-01 adds [offline signer candidate assembly](SIGNER_INSTALLATION_PREPARATION.md)
from the same pinned inputs. It re-runs coverage, loads the actual pinned decoder,
validates the signer configuration and copies exact execution identity/CA/evidence
bindings with the dedicated signer role. It never establishes installation,
source/owner approval, #27, release or host acceptance.

## Identifier and execution audit

| Contract | Implemented evidence | Remaining qualification |
|---|---|---|
| Approve/swap identity (GAP-30) | `Intent.key` binds run/chain/wallet/economic intent; round/decision/version/reservation IDs are retained. Each step has its own attempt, payload and transaction hash. PostgreSQL primary keys pin attempt signatures and observation IDs; its wallet barrier spans runs. Integration maps only swap hashes to round orders. | Definition/uniqueness specification is complete; real signed-pair/ACK acceptance remains DR-02, not an undefined-identifier task. |
| Nonce, timeout, reorg (GAP-31) | Signed attempts persist exact nonce and bytes. Pending/unknown outcomes retain the barrier across the 120-second timeout, probe exhaustion, restart and reorg; a definitely rejected broadcast needs positive nonce/timeout checks before NOT_SUBMITTED. Same-nonce replacement is disabled. | Actual provider qualification and hosted recovery remain. Timeout/absence/deadline alone never proves a dropped transaction. |
| Reservations and accounting (GAP-32) | Real planner I3 output and finalized I4 facts exercise actual accounting and PostgreSQL. Success/revert/NOT_SUBMITTED release appropriate resources once; approval releases only its gas. Broadcast never settles balances. | Hosted signed success/revert/crash/replay evidence remains DR-04/05. |
| Kit adapter (GAP-47) | Live adapter, isolated signer, canonical receipts, Web3 market gates and exact raw-unit mapping are implemented and tested through fake external boundaries. | Mode-appropriate router policy/evidence review/replay, current metadata, qualified provider and host/signed acceptance remain; local fixtures do not authorize activation. |

Exact commands, tested commits and outcome counts are recorded in IDEA-039 GB-RW1.
No complete Gate B or real trade acceptance is claimed here.

## Historical Oct17 mirror artifact handoff

The successful CI release is the reviewed integration baseline, not unmerged
[PR155](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/155).
The artifact ZIP's GitHub-reported digest is not a bundle checksum. Download
`larp-bundle-x86_64` from run39030800352 using authenticated GitHub access, verify
`larp-0672fb8d5105-x86_64.tar.gz.sha256`, compare the external `.release.json`
byte-for-byte with the archive's `release-manifest.json`, and retain the bundle
and manifest SHA256 values. Confirm the full build ID and registered repository
before giving Yao Zhu the release evidence. No AWS upload is performed here.

The cloud draft now includes `productionresultssa9.blob.core.windows.net`, the
artifact storage hostname returned by GitHub, while preserving `api.github.com`
and the package-manager preset. Saving the draft did not apply the rule; the
user must review/save and publish it in environment settings. The two download
attempts were refused, so local artifact verification is explicitly incomplete.
