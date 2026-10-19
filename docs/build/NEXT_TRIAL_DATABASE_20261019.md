# Next unsigned build/database procedure — PC-DBPLAN01 / A04

Status: repository procedure selected, 2026-10-19. **Use a fresh trial database
on the existing RDS instance for the next development build/profile change.**
Do not add version-switch support to the critical path. This uses the existing
PC-DEPLOY01/02 procedure; it creates no new RDS instance or infrastructure.
Actual database creation, access and host execution remain the approved
operator's work after accepted handoff. Nothing in this record authorizes an
AWS apply or deployment without the existing approvals.

## Why this procedure

`runs` is unique per wallet/chain and
[`activate_run`](../../larp/runtime/service.py) refuses a different registered
build. Reusing the existing run/database or deleting registration history is
not a version switch. Prior runs in `larp`, `larp_trial` and `larp_trial2` stay
intact. `larp_trial3` is a candidate name only: the operator must prove it does
not exist and reserve a new `larp_trialN` name if it does. An existing apparently
empty database is not automatically safe to reuse.

A new database does **not** create a new model allocation or trial window.
The same budget ledger and every prior charge, reservation, UNKNOWN amount,
switch, stop latch and fixed **2026-10-22 00:00 UTC** cutoff survive.

## Operator inputs before starting

- Accepted coordinator/operator handoff, existing approved AWS profile and
  private Terraform/runtime/provider/profile/terms files.
- Fresh actual host/run/database/build identity; current services and signing
  state. Oct18 observations are historical.
- Exact qualified original release assets/manifest/source commit/CA checksums,
  the selected measured profile hash and owner review reference. The published
  c5be269 candidate is available; using it still requires the actual approved
  inputs and compatibility checks. Later preparation tooling is separately pinned.
- A unique new run ID and database name, old run/build identity, unchanged
  wallet identity and verified existing shared ledger path/policy.

Missing inputs stop this procedure. Do not substitute example profiles or empty
ledger state. This is an unsigned development procedure; it does not authorize a
scored-run build switch or reuse unsigned identities for signing.

## Ordered operator execution and evidence

Use the existing [R1–R9 script templates](ops/llm-trial-20261018/README.md).
Copy them to a new ignored activation directory and review all old hard-coded
values before execution. In particular, R8's old build/run/database/reviewer
reference is historical, and the DB setup script's original-machine/CA paths
must match the selected release. No template is ready to run unchanged.

| Step | Action | Required result before next step |
|---|---|---|
| 1 | Record current identity, latest charges/latches and pending work privately. Pause new runtime rounds (R1), leaving evidence/uploader/archive alive. | No new rounds; existing work reconciled. Execution remains stopped/disabled. Unknown or active signing work must be resolved first. |
| 2 | Drain old audit chunks and outboxes and obtain an hourly anchor ACK after the pause. Use R3's actual drain checks. | No unchunked/unacknowledged audit work; post-stop anchor verified. Preserve historical failures; never mark them ACK to pass. |
| 3 | R3 preserves old configs and makes consistent SQLite backup-API copies of evidence and budget state. Keep the original shared ledger in place. | Private paths/checksums, charge/reservation/UNKNOWN/latch/policy/cutoff comparison retained. Do not copy a live SQLite main file alone or initialize a new ledger. |
| 4 | Prove the selected trial database name is absent; use R2 with the exact clean release checkout/commit. Review migrations and grants against that release. | Zero runs in the new DB, exact migration hashes and role privileges. Historical DBs unchanged. If schema differs from the old DB, explicitly compare with selected source rather than declaring equality to old schema sufficient. |
| 5 | Verify/upload/provision original release (R4/R5); keep execution disabled. Fresh capture/prepare (R6) targets the new DB in every service configuration. | Exact asset and final config/profile/CA hashes; explicit shadow mode; matching new run/DB identities. Never copy old registration/binding into the new run. |
| 6 | R7 installs configs after all package checks; read-only compare existing ledger policy with routing. | Same ledger path/content semantics, no init/migration/reset; all services reference the intended new database. No credentials or route output in GitHub. |
| 7 | R8 binds/checks/registers/activates the new unsigned run with the current reviewer/reference, then starts unsigned services. | Exact build/config registration, preflight, route/time checks and fresh session. Record each result; no output alone establishes Gate A acceptance. |
| 8 | Verify first actual stages, accounting/reservations, round closure, receiver ACK and operating health. Remove approved private-bearing transfer copies (R9) after retention/handoff checks. | Sanitized UTC evidence plus hashes, preserved budget accounting/cutoff, disabled execution. Failures remain explicit. |

The old DB is the immutable record of the retired run. If any step fails, keep
new services stopped, retain all partial records/configs and the ledger, and
report the failure. Do not fall back by activating an older build or unpausing
the previous run without a reviewed development recovery disposition. Never
delete a database/run or reset the ledger to make a retry pass.

## Completion boundary

A04's repository deliverable is this selected procedure and its evidence
requirements. Host preparation, new DB creation, capture/prepare/bind/activation
and stage/ACK verification are **NOT_RUN here**, remain A01/A02/GAP-70 tasks and
must be recorded by the approved operator. Version-switch support remains a
separate optional future change, not a claim made by this plan.
