# Approved development balance RPC settings — RPC-H02 / #92

User supplied `selected-providers.json` on Oct19 and explicitly approved:

1. `BSC_BNBCHAIN_PUBLIC` primary.
2. `BSC_NODEREAL_PUBLIC` backup.

Both previously passed19 local qualification reads in merged PR135. These are
**development balance-read** approvals. They do not qualify native tracing,
provider uptime, actual-wallet reconciliation or AWS access.

## Prepared in this session

Private working copy (ignored by Git, mode0600):
`/workspace/rpc92-host/deploy/activation/balance-rpc/selected-providers.json`.
Exact uploaded bytes SHA256:
`81fb99728f69a2dc3d5279764dfa3bcadb21194bfb6fbe8618b88570e3977558`.

A second ignored mode0600 file, `driver-balance-rpc.fragment.json` in that same
directory, contains the ordered `driver.balance_rpc_providers` block.
SHA256: `0a164d7d8d8452d7585e688d978ce174d2b63f8674007e0542e93052534ffff1`.
PR135's `private_config` reader and runtime `balance_providers` both accept it
with the approved order. No provider URL is in this document or Git.

**This is a configuration fragment, not a complete runtime.json.** No hosted
runtime, wallet/run binding, Terraform output or AWS identity is available in
this session. The fragment must never replace a complete hosted runtime file.
Account-owner details are resolved per the user; working host access and evidence
are separate. The user also supplied the target account/environment label, but
a fresh capability check still exposes no bound AWS identity. A name alone
cannot authenticate an AWS/SSM session. No new zero-address probe was run, since that does not establish
the requested actual-wallet result.

## Operator sequence — use the approved access handoff

1. Export/inspect the actual current host/runtime/release identity privately.
   Establish the exact approved dev run, wallet, DB, source commit, original CI
   bundle and profile. Preserve the shared cost ledger, UNKNOWN charges,
   reservations, latches, old DBs and fixed unsigned cutoff. Follow
   [the fresh trial DB procedure](NEXT_TRIAL_DATABASE_20261019.md) if preparing a
   new build/run; do not rewrite the old run's registered config or manifest.
2. Use the existing `capture`/`prepare` commands in [Gate A](GATE_A.md) with
   `--balance-rpc-config` pointing at the attached selected file. Both commands
   take it; preparation writes the exact ordered providers to the runtime driver.
   Supply actual fresh wallet capture, measured profile, Terraform outputs, CA,
   SEC contact and build/run IDs. Do not reconstruct those from examples.
   Preserve existing accepted model-routing pins and balance-check interval,
   maximum-age and price-jump settings. Refuse nonempty legacy
   `balance_rpc_url`/`balance_rpc_source_id` alongside the ordered list.
3. Inspect the approved primary-host network state. Terraform already defines
   HTTPS443 egress for primary under `enable_external_https`; check the applied
   route/DNS/NACL/security-group state before proposing any change. Do not add
   signer internet access or apply Terraform merely because local providers pass.
   On primary, run the route checker below against the candidate configs. It
   derives both destinations from `driver.balance_rpc_providers`, and verifies
   DNS/TCP/TLS rather than making a wallet transaction. Retain the full report in
   restricted storage; publish only safe IDs/statuses/hashes.
4. Stage complete configs as root-owned private files for the qualified run.
   Bind the exact original CI release manifest to these exact config bytes using
   the existing binding command below, with a **new output path**. Preserve all
   applicable installed service-config bindings. Verify the candidate before any
   approved install/activation. Never edit a bound runtime file afterward or
   manufacture a new CI manifest to bless an unqualified bundle.
5. Complete ordinary Gate A preparation/registration/activation on the approved
   dev run. No execution/signing capability is enabled by provider selection.
   Let the runtime perform its own first eligible balance check. Do not manually
   inject a BALANCE_CHECKED event or run a standalone probe with audit credentials.
6. Collect the evidence below and obtain reviewer acceptance before closing #92.
   A failed first check remains recorded; a subsequent successful check gets its
   own timestamp/head. Do not reset the run to manufacture a successful first check.

## Existing host commands

Run from the exact installed release environment on primary. Variables below
are **explicit operator-supplied private paths** for the complete candidate configs,
original CI manifest, registered evidence and new output files. They are not
populated by this handoff. Do not print config contents or secret values.

Unsigned primary route check (add execution config only if applicable):

```sh
.venv/bin/python -m larp.runtime.routes --role primary \
  --config "runtime=$LARP_RUNTIME_CANDIDATE" \
  --config "uploader=$LARP_UPLOADER_CONFIG" \
  --config "operations=$LARP_OPERATIONS_CONFIG" \
  --root "$LARP_RELEASE_ROOT" --output "$LARP_ROUTES_REPORT"
```

New host-bound manifest from the original qualified CI manifest:

```sh
.venv/bin/python -m larp.runtime.preflight \
  --bind "$LARP_ORIGINAL_CI_MANIFEST" --root "$LARP_RELEASE_ROOT" \
  --output "$LARP_BOUND_MANIFEST_CANDIDATE" \
  --registration-evidence "$LARP_REGISTRATION_EVIDENCE" \
  --runtime-config "$LARP_RUNTIME_CANDIDATE" \
  --config "$LARP_OPERATIONS_CONFIG" \
  --service-config "uploader=$LARP_UPLOADER_CONFIG" \
  --service-config "operations=$LARP_OPERATIONS_CONFIG"
```

For any additional service configuration already required on primary, retain its
own `--service-config NAME=PATH` argument. Use the installed qualified source's
preflight checks and Gate A package verification; these commands do not start a
service or install the candidate. Preflight refuses an existing output file.

## Actual-wallet acceptance evidence — still NOT_RUN

Retain a sanitized, UTC-stamped record with:

- Exact host, source/build, run/wallet, DB, profile, runtime and bound-manifest
  hashes; original CI/bundle provenance and registration review.
- Selected provider order and applied egress/DNS/TLS route results from primary.
- The actual runtime's first BALANCE_CHECKED event for this process/run/config,
  its journal sequence/head, observation hash and readback of the original
  ChainBalances.v1 artifact. Confirm chain56, actual wallet, finalized numeric
  block/hash and all pinned BNB/ERC20 balances/scales, with current nonce/in-flight
  reconciliation. Retain which approved provider served the observation.
- Comparison status MATCH, or reviewed SURPLUS_ONLY (for example USDT dust).
  SKIPPED/in-flight, deficit, stale read, provider outage or a zero-address capture
  does not satisfy acceptance. Any non-dust surplus needs reconciliation rather
  than assuming harmless funding.
- Evidence the **running process's** balance-health gate became true following
  that comparable fresh check. `BalanceCheck.ok()` requires process-local ok_ms,
  acceptable comparable_status and age less than configured max_age. An old
  journal MATCH or persisted projection alone cannot prove this after restart.
  Confirm from the corresponding recorded runtime gate evaluation; if the build
  exposes no such evidence, keep that subcheck open and prepare a reviewed
  observation path. Never instantiate a new BalanceCheck to invent process state.

Do not infer trading readiness from balances_ok: all other spending, execution,
strategy/source, signing and Gate B checks remain independently required.

## Current disposition

| Item | Result |
|---|---|
| Approved file received and ordered driver fragment staged | PASS, local only |
| Existing private reader and runtime provider validation | PASS, no network calls |
| Ignored private files and permissions | PASS |
| AWS network state / primary route check | NOT_RUN, no configured AWS identity |
| Complete actual runtime config / host manifest binding | NOT_RUN, actual config/build/run inputs missing |
| First actual-wallet BALANCE_CHECKED and process balance-health | NOT_RUN, needs approved host access and run evidence |
| Native tracing / signing qualification | Separate, no acceptance conferred |
