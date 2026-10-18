# Gate B remaining work — 2026-10-17

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
At this inspection, only PR126 and PR133 are open and PR139 remains draft.

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

## Remaining dependencies, in order

Use the owners on the corresponding **Gate B setup** and **Oct 20/21** lines of
[PR133's pre-trading checklist](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/133),
and [PR126's Gate B brief](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/126).
Neither proposal approval nor host acceptance is inferred from merging code.

| Work | Current evidence and next concrete action |
|---|---|
| Router source/ABI and all four guarantees (#33/#138, GAP-29) | PR139 found an unverified router, unusable explorer ABI and no Sourcify match. Its finalized selector lookup identifies candidate facet `0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603`; that is not verified source, dispatch/upgrade proof or an allowed spender. Obtain complete attributable router/facet/helper source and ABI, bind to deployed code, and perform the independent source review. Keep signing blocked if unavailable. |
| Recorded-real route qualification | After source review, run the existing `larp.execution_live.router check` against Keith's retained quote artifacts. Require both stock directions, exact wallet/economic binding and the mutation checks. No actual capture files are present in this cloud checkout. |
| Signing lifetime (#27) | PR144's Option A is a conditional recommendation; 60 seconds is illustrative. Keith reviews; Keegan decides the model, finite lifetime and margins, records C-OPEN-003, and implements the adopted contract. Do not extend the 15-second admission window or remove the encoded-deadline comparison. The kit's approximate 30-second quote lifetime is not measured encoded expiry. |
| Independent signer caps (#44) | PR148 proposes development/final USDT inputs 35/70 and fee 0.0002 BNB. These remain unapproved for installation. Run the current-input review below, review full holdings and adjustment/splitting scenarios, then record the exact policy/profile/metadata evidence and approved hash. Use the router as spender, never the facet. |
| New release bundle | GB-RW2 mirror [run39030800352](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39030800352) passed all four jobs on reviewed integration `0672fb8`, including PR130/144/148/149/153/131. Artifact `12099524179` exists; this session's network policy blocks downloading it. Sidecar/manifest verification and the two file hashes remain required before the AWS-owner handoff; see the [build record](evidence/gate-b-mirror-build-20261017.json). Any later adopted source change requires a newer reviewed release. |
| Signer provisioning | The access choice and Terraform review are complete (IDEA-080 / PR149). After numeric-policy approval, the checklist's AWS owner applies temporary development SSM endpoints, provisions/binds the approved configs, and records SA4/SA9. Isaac places the key on the signer host only; the AWS owner records teardown SA5. This cloud machine has no usable AWS profile or private backend/input files; injected AWS config files contain zero profiles and boto3 resolves ProfileNotFound. |
| First gas, floor and native tracing (#30/#106, GAP-49) | PR151 completes the historical 2-USDT funding-note slice, including source-attributed BNB credit. The planned remaining dev funding and fresh opening capture are still outstanding. Qualify transaction-bound native tracing on the actual execution provider, then review measured floor/top-up amounts. Balance-provider selection alone does not qualify tracing. |
| First signed round and host drills (DR-02..06/19) | After Gate A and every prerequisite above, the agent produces the minimum-size dev approve/swap and ACKed round. Record chain reconciliation, success/revert reservation release, host crashes at each durable boundary and a recorded shadow-day replay. Existing synthetic/real-local-PostgreSQL tests are engineering evidence only. |
| Timing and rehearsal | The current rehearsal buy window begins Oct 21 00:00 UTC (08:00 SGT). An earlier dev window requires its recorded decision/version event. Keep the conditional rehearsal-shape decision in IDEA-049-D D-DN-02; record an applicable shortfall when the gate is missed, rather than recording a future shortfall now. |

S1 B6's per-leg attempt and actual execution-session/window enforcement remains
an explicit later S1 delivery item (IDEA-076), distinct from its existing
planning-session broadcast counter. It is not established by the W04 prepare
probe budget, nor by this cap review. Proposed S1 values remain unadopted.

## Current-input signer-cap review

`python -m larp.execution_live.caps_review` provides the previously manual numeric
comparisons for #44. It reads only explicitly selected, hash-pinned local files,
using the real profile, execution-config and signing-policy validators. It checks:

- The profile's complete largest target position plus reserve, per-trade cash
  cap and gas-top-up input, converting micro-USDT to raw 18-decimal USDT exactly.
- Every current stock holding in its own metadata-checked raw token units,
  without assuming that sell splitting exists.
- The configured worst-case gas envelope and measured/quoted transaction fees
  against the signer's independent fee ceiling.
- Successful, fresh wallet/chain/router-bound quote artifacts, including all five
  BUY/SELL pairs and native top-up, input quantities and execution gas limits.

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

## Identifier and execution audit

| Contract | Implemented evidence | Remaining qualification |
|---|---|---|
| Approve/swap identity (GAP-30) | `Intent.key` binds run/chain/wallet/economic intent; round/decision/version/reservation IDs are retained. Each step has its own attempt, payload and transaction hash. PostgreSQL primary keys pin attempt signatures and observation IDs; its wallet barrier spans runs. Integration maps only swap hashes to round orders. | Definition/uniqueness specification is complete; real signed-pair/ACK acceptance remains DR-02, not an undefined-identifier task. |
| Nonce, timeout, reorg (GAP-31) | Signed attempts persist exact nonce and bytes. Pending/unknown outcomes retain the barrier across the 120-second timeout, probe exhaustion, restart and reorg; a definitely rejected broadcast needs positive nonce/timeout checks before NOT_SUBMITTED. Same-nonce replacement is disabled. | Actual provider qualification and hosted recovery remain. Timeout/absence/deadline alone never proves a dropped transaction. |
| Reservations and accounting (GAP-32) | Real planner I3 output and finalized I4 facts exercise actual accounting and PostgreSQL. Success/revert/NOT_SUBMITTED release appropriate resources once; approval releases only its gas. Broadcast never settles balances. | Hosted signed success/revert/crash/replay evidence remains DR-04/05. |
| Kit adapter (GAP-47) | Live adapter, isolated signer, canonical receipts, Web3 market gates and exact raw-unit mapping are implemented and tested through fake external boundaries. | Real source/route, current metadata, qualified provider and host/signed acceptance remain; local fixtures do not authorize activation. |

Exact commands, tested commits and outcome counts are recorded in IDEA-039 GB-RW1.
No complete Gate B or real trade acceptance is claimed here.

## Mirror artifact handoff still pending

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
