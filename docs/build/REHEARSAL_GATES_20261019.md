# Rehearsal gates — RG-01

Status: **PREPARED; all live results NOT_RUN.** This is the C09/C10 operator
packet for [PR133 remaining actions](PR133_REMAINING_ACTIONS_20261019.md).
It makes the existing [DR acceptance requirements](DEPLOYMENT_BUILD.md) usable
as a sequence; it introduces no new trading policy or authority. Account-owner
details are resolved per the user's Oct19 update. Private access delivery and
actual host qualification still require evidence.

Use the [pre-trading checklist](PRE_TRADING_CHECKLIST.md) for accountable owners:
"Oct21–26: rehearsal drills", "Oct21" first-trade/crash checks, daily rehearsal
log, and "Oct26–29" final signoffs. C09 belongs to the approved operator;
Keegan reviews C10; Isaac's key placement remains confined to C07's approved
session. The established team rota/go-ahead and account-owner identities do not
need to be decided again. Preserve separation of operators and reviewers.

## Run order and entry conditions

1. **Prepare now:** fill the public identity/evidence index, select exact source
   and release, register each drill's procedure and pass criteria before running.
   Obtain missing policy decisions; prepare isolated restore/switch targets.
2. **Unsigned work when access exists:** inspect current timing, alarms, retention,
   backup/anchor cadence and complete unsigned exports. Historical successes are
   references; mark current-build results separately.
3. **Signed work after C07/C08:** first agent-generated minimum-size round and
   ACK/on-chain proof, then scheduled fault drills on the approved dev environment.
   No human-selected trade is a drill prerequisite.
4. **Review:** reconcile every attempt, replay the actual day, complete daily
   observations and DR reviews, then assemble final activation evidence.

Before step3, Gate A qualification and applicable Gate B execution prerequisites
must have attributable evidence: source/review/route check; native tracing proof;
adopted #27 bounds; measured #44 caps; approved profile/window; funding eligibility
and fresh reconciled holdings; exact reviewed release; configured/isolated signer
and approved session. Keep first-round evidence separate from the subsequent
Gate B review so this sequence has no circular dependency.

Never reset the shared model ledger, UNKNOWNs, reservations, spend latches or
fixed unsigned cutoff to start a rehearsal. Signed time does not supply the
72 qualified unsigned hours. Freeze run/build/profile/config/DB/calendar identities
before each series. A changed relevant identity requires impact review and new
applicable evidence; an older bundle's PASS cannot qualify newer bytes.

## Gate checklist

Each row starts **NOT_RUN**. Record PASS/FAIL/INCONCLUSIVE only from observed
results; BLOCKED names the missing prerequisite. Attach the record below to each
row. Missing evidence or review blocks acceptance even if the process returned0.

| Gate | DR coverage | Procedure and observations | Pass criteria / block condition |
|---|---|---|---|
| RG1 — release and entry | DR18/DR20; C06–08 | Compare exact source, original bundle, manifest, bound configs, profile, source/caps approvals, run/wallet and database identities. Review required CI/platform/bundle results and first logged agent approve/swap. | Every required binding matches; applicable reviews exist; canonical approve/swap has unique decision/attempt and ACKed round mapping. Missing input or synthetic-only proof blocks signed entry. Final declarations remain RG10. |
| RG2 — crash and reconcile | DR04/DR05/DR13 | Freeze a fault matrix at authorized, signed-durable, send/unknown, receipt/settlement and round/ACK boundaries. Use approved host instrumentation for those boundaries. For runtime restart use runbook §2; inspect journal, commands, attempts, reservations, nonces, receipts and ACKs before/after. | Automatic same-build restart with incident; no duplicate economic execution; UNKNOWN remains fenced until canonical reconciliation; no reservation released merely because of timeout/restart; each broadcast swap remains mapped to its round. Recovery time fits adopted bounds. Missing boundary instrumentation or measured bounds is BLOCKED, not a completed drill. |
| RG3 — autonomous HALT/clear | DR13 | Register a reversible isolated CLOCK/planner/delivery fault procedure against actual configured triggers. Observe HALT/clear journal events and signer/command counts. Follow runbook §3 and adopted operations decisions. | Trigger halts automatically, rounds remain logged with no orders/commands/signatures; clear follows the adopted automatic condition only. Unresolved quarantine does not clear. Record measured latency, clock health and probe counts. Do not alter the production clock or invent a fault-injection flag. |
| RG4 — anchors | DR15; IDEA036 criteria1–6 | Inspect destination/retention first; collect ≥24h hourly slots and incidents; read anchors back, verify journal heads, try overwrite/delete under writer role on a designated drill object, verify a deliberately altered isolated journal and stale restore are refused. | All six IDEA036 criteria evidenced, including storage-enforced refusal, actual retention through Dec31 2026, identifiers/hashes only, and empty-target restore verification. Missed slots have original incidents; never backfill them. An ACK alone is insufficient. |
| RG5 — restore and alert | DR16; DR15 restore | Restore pinned backup receipt into empty migrated isolated DB using runbook §4; verify checksum, journal and anchors. Exercise an approved alarm and obtain recipient acknowledgement without sending secrets. | Consistent restored state; stale/corrupt input refuses; new epoch and quarantine fence writes/signing; no signed bytes exported. Record actual recovery duration/data-loss boundary against adopted targets. Real alert reaches intended person with timestamp. No resume during scored operation is inferred. |
| RG6 — throwaway wallet switch | DR17 | Before switch prove no old open round, execution, reservation or holding; use dedicated dev throwaway config/credential and separate SDK/nonce namespaces per runbook §5. Deliberately mismatch address in isolated check. | Mismatch refuses, identities/records cannot leak across wallets, switch record links old final head to new quarantined run. No final wallet/key is required for this rehearsal. Never create an empty shared cost ledger to switch wallets. Final registration/credentials/funding are separate C11 evidence. |
| RG7 — time boundaries | DR14 | Keith supplies adopted exact profile and boundaries. Retain clock-driven test results for that profile and observe applicable dev-window behavior without moving live time. Verify independent signing/intent/quote bounds. | No new risk outside adopted window; required exits retained when guards block; no reinvestment after cutoff; no stale authority extended to force a fill. Final dated schedule must be approved separately; a dev clock test is not a real final-window observation. |
| RG8 — actual-day replay | DR19 | Export complete immutable original inputs/assessments/state/calendar and journal for a shadow day and signed rehearsal day; use recorded ports and original build/config in isolated DB. Compare original/replayed sequence and head. | Both required days reproduce exact head; live provider/venue writes disabled. Missing inputs, unsupported reducer or divergent head fails; never edit/backfill captured records to obtain equality. See integration replay API/tests; no standalone replay CLI is assumed. |
| RG9 — daily rehearsal | DR21; T4/DR11 inputs | Keegan compiles UTC-day records below from actual round logs, canonical chain results, alarms and usage; Keith reports unsigned/signed evidence separately. | Declared ≥5 signed days including Oct24–25 at minimum size; complete intervals/outages/incidents and model I/O/cost/latency evidence. Apply existing D-DN02 conditional shortfall decision when missed and record deviation/review; a shorter window never becomes five observed days. Strategy/model adoption and T4 need their own reports. |
| RG10 — activation review | DR18/DR20/DR22 | Collect DR01–22 owner reviews, Gate A/B evidence, RG1–9 records, final deviations/services, frozen release/manifest, final-wallet config with empty secret slot, runbook and established rota. | All required owner signoffs, FINAL deviations, service declarations, actual final credential/registration/funding/opening capture and activation approvals exist. Do not infer final-wallet acceptance from throwaway switch. Any missing mandatory item blocks Gate C and activation. |

## Supported host commands and API boundaries

These are for the checklist's approved operator **before scored operation**.
Do not run a destructive drill until its isolated target, injection method,
measurement bounds and rollback/reconciliation procedure are reviewed. Retain
full sanitized output outside Git; retain raw private artifacts only in approved
restricted storage. Never upload credential files, signed bytes or private RPC URLs.

Read-only local config check (does not establish cloud/host readiness):

```sh
python -m larp.runtime.operations check --config /etc/larp/operations.json
```

Observed archive health (uses configured host access and publishes health
metrics to CloudWatch; it is not a purely local/read-only check):

```sh
python -m larp.runtime.operations health --config /etc/larp/operations.json
```

Approved dev runtime crash only; systemd must restart it automatically:

```sh
sudo systemctl kill -s SIGKILL larp-runtime
systemctl show larp-runtime -p ActiveState -p SubState -p NRestarts
```

Do not accept service status as reconciliation evidence. Record actual restart
latency against adopted settings; the historical approximately10s observation is
not a new acceptance bound.

Restore into the pre-created empty migrated drill database only. The following
paths are explicit operator-supplied inputs: pinned receipt and private DSN file.
Check the target is isolated before running; never point it at the active DB.

```sh
python -m larp.runtime.operations restore \
  --config /etc/larp/operations.json \
  --receipt "$LARP_DRILL_BACKUP_RECEIPT" \
  --target-dsn-file "$LARP_DRILL_TARGET_DSN_FILE"
```

Anchor verification uses `larp.runtime.maintenance.verify_anchors`; wallet switch
uses `larp.runtime.live.switch_wallet`; exact recorded-port replay uses
`larp.integration.replay.replay_live`. These are APIs, not supported shell
subcommands. The operator must pin a reviewed, committed invocation harness with
actual sanitized input bindings before running RG4/RG6/RG8. Baselines:
[anchor tests](../../tests/runtime/test_anchors_roles.py),
[wallet tests](../../tests/runtime/test_live_start.py),
[replay tests](../../tests/integration/test_live_replay.py).
Do not run a fixture against real wallet credentials. Boundary fault injection,
HALT stimulation and storage-denial probes likewise require pinned host-specific
procedures; their absence is an explicit execution blocker.

## Evidence record — copy once per gate/attempt

Keep originals append-only in approved evidence storage; put public hashes and
sanitized summaries in [IDEA042](../ledger/IDEA-042.md). No credentials here.
Empty fields below are **intentional unfilled template fields**, not evidence.

```yaml
record_type: RehearsalGateAttempt.v1
gate: null                 # RG1..RG10
attempt_id: null
status: NOT_RUN            # BLOCKED / PASS / FAIL / INCONCLUSIVE after observation
started_at_utc: null
ended_at_utc: null
operator: null
reviewer: null
source_commit: null
bundle_sha256: null
manifest_sha256: null
profile_sha256: null
bound_config_sha256: null
run_id: null
wallet_public_address: null
isolated_target_id: null
procedure_commit_and_ref: null
adopted_limits_and_approval_ref: null
precondition_evidence: []
observations: []            # measured values plus pass/fail per criterion
artifacts: []               # access-controlled locator, SHA256, capture UTC, scope
before_and_after_heads: []
incident_and_reconciliation_refs: []
blockers: []
review_decision_and_date: null
```

A PASS claim requires matching identities, every row criterion, retrievable
hashed artifacts and dated operator/reviewer findings. A reviewer records a
rejection without overwriting the original attempt. Resolved incidents retain
their originals. Re-run relevant gates after fixes; attach superseding evidence.
This template does not compute acceptance or enable signing.

## Daily record — one per actual UTC day

Record date; exact run/build/profile and operating mode per interval; signed
start/end and unsigned intervals separately; minimum-size policy ref; rounds,
approves/swaps/reverts and ACK coverage; unresolved executions/reservations;
source/model availability and full I/O coverage; observed cycle/model/ACK latency;
actual per-provider cost/units, shared reservations/UNKNOWN/headroom; anchors,
backups, alarms and restart counts; incidents/fixes with version events; final
journal head; operator evidence and Keegan review. Mark partial days and missing
observations explicitly. Keep the Oct24/25 weekend records identifiable.

If Gate B misses the existing Oct20 forecast, record the shortfall on that day
under D-DN02/GAP04 and retain the actual signed start. No retroactive rehearsal
credit. This packet leaves C09/C10, GAP04/35/36/37/52/62/65 and Gate C open.


## Local evidence index checker — RG-02

The offline utility creates a **new** JSON index and checks locally exported,
sanitized evidence. It never calls cloud services, RPCs, databases or signing.
Keep the index, identity file and evidence outside Git in approved local storage.
The output path below must not already exist. These variables are explicit
operator-supplied local paths, not credentials or live service destinations.

```sh
python tools/deploy/rehearsal_evidence.py init --out "$LARP_REHEARSAL_INDEX"
python tools/deploy/rehearsal_evidence.py check \
  --packet "$LARP_REHEARSAL_INDEX" \
  --identity "$LARP_REHEARSAL_EXPECTED_IDENTITY" \
  --evidence-root "$LARP_REHEARSAL_SANITIZED_EXPORT"
```

`init` writes ten NOT_RUN records. Fill top-level `identity` and each observed
record's identity with the exact reviewed source commit, bundle/manifest/profile/
bound-config SHA256 values, run ID and lowercase public wallet address. The
separate expected-identity file is a JSON object with those same seven keys,
obtained from the reviewed release/run bindings; do not generate it by copying
an unverified packet. The index is JSON, distinct from the descriptive YAML
attempt template above.

Set a gate to REVIEWED only after operator observation and independent review.
Include UTC start/end (YYYY-MM-DDTHH:MM:SSZ), operator/reviewer, pinned procedure,
approval and review references, OBSERVED_HOST scope and individual criterion
results. All required criterion keys are emitted by `init`; do not remove them.
Every claimed PASS needs actual supporting artifacts; artifact rows have exactly
`file` (a flat local sanitized export filename) and `sha256` (lowercase hex).
No directory traversal, nested artifact paths, symlinks or special files are
accepted. The evidence directory must also have no symlinked ancestors; on
macOS use its canonical `/private/tmp` or `/private/var` path rather than the
`/tmp` or `/var` alias. Input JSON is bounded to1MiB and each artifact to16MiB; split large
sanitized exports into separately hashed files. Private credentials/signed bytes
and unredacted provider configs are never valid evidence exports.

Exit0 means **index structure and local artifact integrity complete**, exit1
means incomplete records, exit2 means refused/malformed inputs. Reports contain
only gate IDs and fixed reason codes, not paths or input contents. Even exit0
always reports `gate_c_accepted=false`, `signing_enabled=false` and
`host_results_verified=false`: file hashes and attributed claims cannot establish
that a drill ran, that a claimed measurement is valid or that a reviewer approved
activation. Keegan still reviews the original artifacts and criteria, including
actual duration/weekend coverage or the explicitly reviewed shortfall. The checker
does not independently compute daily duration or replay/chain correctness.
