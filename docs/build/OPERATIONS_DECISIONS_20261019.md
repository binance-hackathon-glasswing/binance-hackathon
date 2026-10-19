# Operations decision packet — PC-OPS01 / A06

Prepared for Isaac's C05 review, 2026-10-19, from committed repository evidence.
**Original proposal packet with dated owner dispositions below. No unit or runtime setting changes in this review.**
This completes the operations-proposal portion of A06; O2 and DEV20's final
owner disposition remain separate. Isaac can review the policy/risk choices
below now; measurements are required before accepting numeric settings or
claiming host readiness. The original packet was not approval; C05-RV01 below records Isaac's subsequent delegated review.

Source baseline: [IDEA-049-D §5](../ledger/IDEA-049-D.md),
[current runbook](runbook.md), runtime service/supervision and current systemd
units. Older recommendations are checked against current behavior below.

## Ready for policy review without new credentials

### D-DN-01 — standby / DEV-18

**Recommend:** propose the explicit no-standby deviation: primary plus isolated
signer, automatic same-build restart and existing EC2/RDS recovery mechanisms;
no third host or automated standby promotion. This matches the built topology
and avoids proposing an unimplemented standby as protection.

**Tradeoff Isaac must accept or reject:** primary/availability-zone failure can
stop trading for the rest of the run. Restarts and infrastructure alarms do not
provide a fenced standby or establish an RTO/RPO. Do not attach an estimated
recovery time to the recommendation. A standby alternative needs fencing,
state/nonce authority, cost approval, code and failover qualification.

**After acceptance:** Keegan updates D-05/DEV-18 with the actual decision,
reason and evidence; the register stays DRAFT until its required final review.
Operator still supplies restart/reboot/backup evidence. Isaac may record the
risk choice now without certifying recovery timings. See
[DEV-18](../../config/release/deviations.v1.json) and
[the runtime unit](../../deploy/systemd/larp-runtime.service).

### D-DN-07 — deterministic crash loop

**Recommend:** retain current supervision for the candidate, with explicit
residual crash-loop risk. `Restart=always`, `RestartSec=10`, no start limit;
exit2/3/4 suppress restart for known integration/quarantine/start refusals.
An exit1 defect can therefore keep restarting. A RESTART incident records each
unclean session; backup-rate limits do not prove bounded incident journal,
host logs or storage growth.

**Tradeoff Isaac must accept or reject:** fail-closed repeated restarts can
consume resources and prevent progress indefinitely. The alternative, a new
N-restarts-per-hour HALT, requires a durable cross-process counter, explicit
autonomous clearing semantics and tests. Adding a systemd start limit alone
could leave the agent stopped without the approved autonomous recovery path.

**After acceptance:** Keegan records the policy/risk; operator still supplies
restart/RSS/disk/incident-growth observations. This decision need not wait for
those observations to prepare a risk disposition, but actual qualification does.
References: [service exit handling](../../larp/runtime/service.py),
[supervision tests](../../tests/runtime/test_supervision.py).

### D-DN-11 — restore during the scored run

**Recommend:** retain the implemented quarantine boundary: a restored run stays
quarantined and cannot trade during the scored run. Do not implement automatic
re-activation as a late recovery shortcut. Before the scored run, restore drills
use empty migrated targets, checksum/journal verification and anchor freshness
checks; any re-activation follows the separately reviewed development procedure.

**Tradeoff Isaac must accept or reject:** database loss/quarantine can end
trading for the remainder of the run even when backups are recoverable.
Accepting this risk does not establish backup delivery, recovery time or RPO.
Automatic recovery would need a separately specified registered code path,
strong identity/anchor/fencing/reconciliation checks and release qualification.

**After acceptance:** Keegan records the explicit recovery limitation; operator
still completes backup/restore/anchor drills. References:
[runbook restore](runbook.md#4-restore--host-drill-at-gate-b),
[archive/restore CLI](../../larp/runtime/operations.py),
[anchor tests](../../tests/runtime/test_anchors_roles.py).

## Ready to review requirements; numeric adoption still blocked

| Proposal | Current behavior / recommended direction | Missing input and acceptance work |
|---|---|---|
| D-DN-04, pre-deadline delivery bound | Current runbook/supervision HALT on an overdue upload deadline, not merely on log age. Recommend an additional oldest-unacknowledged-log-age guard, conditional on design approval. The historical2h example is not adopted. | Isaac may approve/reject the guard contract now. Final B needs measured normal dispatch/ACK delays and owner decision. Code must persist oldest pending identity/age across restart, handle future/backward clocks without extending authority, count only positive stored ACKs, preserve hard upload deadlines, and retain reconciliation while all signing is halted. Include multiple chunks/out-of-order ACK, timeout/HTTP200-without-STORED, restart and boundary tests. Do not claim this earlier guard is implemented. |
| D-DN-06, cycle watchdog | Keep the existing watchdog mechanism; separate assessment authority deadlines from actual worker cleanup and whole-cycle duration. Example600s remains a candidate pending measurement. | Approved operator supplies actual whole-cycle, reviewer-drain, source/quote/finality and stalled-call timing; Keegan checks all bounded stages fit the proposed cap with a stated margin. A180s assessment deadline alone does not prove a600s cycle bound. Tests must show hung workers cause same-build restart without extending authority or losing UNKNOWN/reservations. |
| D-DN-08, memory / #60 | Measure before choosing tighter unit limits or a larger instance. Sum of MemoryMax values is not actual RSS and is not proof of safe simultaneous use. No instance change or swap recommendation is adopted. | Operator exports timestamped per-unit MemoryCurrent/MemoryPeak, cgroup events/limits, RSS, host MemAvailable, OOM/restarts and overlap during routed work/evidence ingestion/archive. Keith/Keegan compute simultaneous peak plus documented kernel/cache/headroom. Isaac decides; any resize needs existing cost/apply approval and a measured rerun. |

References for the pending numeric rows:
[supervision](../../larp/runtime/supervision.py),
[watchdog](../../larp/runtime/watchdog.py),
[runtime service](../../larp/runtime/service.py),
[systemd units](../../deploy/systemd/larp-runtime.service).

## DEV20 disposition proposal, kept separate from scheduled safety windows

**Decided 2026-10-19 (Keegan): accepted.** The planner is omitted and declared
as DEV-20 in `config/release/deviations.v1.json` (`decided` 2026-10-19, status
DRAFT until C10). The proposal text below is kept as the reasoning.

Recommend Keegan propose an explicit event-calendar-planner omission deviation
for the next candidate unless a reviewed planner lands. The implemented frozen
session/execution windows and scheduled-event evidence class do not constitute
per-class macro/earnings planning. `SCHEDULED_EVENT` alone cannot cut exposure
in the existing S1 limiter. Do not present an event diary as an implemented
planner or remove mandatory market/terminal/execution-window safety gates.

The alternative needs a trusted event source/calendar snapshot with provenance,
per-class action/freshness/window rules, conflict precedence, replay and audit
fields, implementation and tests. Keegan must decide the proposal and reconcile
DEV-20/declarations; no choice is finalized by this packet. References:
[DEV-20](../../config/release/deviations.v1.json),
[S1 class map](../../larp/strategy/s1.py),
[execution windows](../../larp/strategy/execution_bounds.py).

## Isaac's requested response and following work

For each D-DN-01/07/11: record ACCEPT / REJECT / REQUEST_CHANGE, date, exact
proposal revision and reason. He can complete this review from repository
material now; no source export, RPC account, private key or fresh holdings is
required. For D-DN-04 he can review the guard requirements now while B/code
remain pending. D-DN-06/08 are measurement-blocked for final value selection.

Keegan implements/documents accepted choices and obtains their required review;
operator measures/qualifies real behavior. Do not mark all of C05/A06 complete:
O2, final DEV20 disposition, adopted numeric settings, required code and actual
host acceptance remain open. No unchanged runtime tests were rerun to prepare
this decision packet; linked existing tests are coverage references, not new
results.


## C05-RV01 — Isaac's review and dispositions, 2026-10-19

The user explicitly asks the assistant to do the remaining work on Isaac's
behalf toward signer installation. The following are Isaac's delegated policy
review decisions, not Keegan's independent signoff or a host/release approval.
Reviewed proposal revision: `aa97b8b`, original PC-OPS01 file SHA256
`59037d4554081a66690b07328ee226a6578863ddeb1f6db3972bd7f34cb35517` (bytes before this review).
Keegan's already decided O2 and DEV20 are preserved and are not reopened here.

| Decision | Disposition | Reason and accepted limits | Next owner / acceptance |
|---|---|---|---|
| D-DN-01 — no fenced standby | ACCEPT the proposed no-standby scope for the candidate | Match the built primary + isolated-signer topology; do not promise unbuilt failover. Primary/AZ failure may end trading for the run. No measured RTO/RPO, availability or recovery guarantee is asserted. No third host, promotion path or infrastructure change is authorized. Existing fencing remains mandatory. | Keegan independently reviews and records D-05/DEV-18 scope; DEV18 remains OPEN/DRAFT until that decision. Yao/approved operator supplies exact-host isolation/restart/reboot/backup evidence. |
| D-DN-07 — restart behavior | ACCEPT retaining current supervision for the candidate | Preserve same-version supervisor restart, `Restart=always`, `RestartSec=10`, `StartLimitIntervalSec=0`, with exit2/3/4 restart suppression. Accept the residual exit1 crash-loop/resource-growth risk; repeated incidents are not healthy operation or a bounded-storage guarantee. Do not add an unqualified restart-limit/HALT/clear path. | Keegan records/reviews the policy. Operator measures repeated-error/restart, RSS, disk and incident growth before host acceptance. A failed drill remains failed and requires a reviewed correction, not a waived resource gate. |
| D-DN-11 — restored-run quarantine | ACCEPT keeping restored runs quarantined during scoring | Prefer loss of availability over unqualified reactivation of restored state. Database loss/quarantine may stop trading for the rest of the run. No human or new automatic scored-run reactivation is authorized; no backup-delivery/RPO/recovery-time claim follows. | Keegan records/reviews the limitation; operator performs empty-target checksum/journal/anchor/fencing drills under the development procedure. |
| D-DN-04 — earlier delivery-age guard | ACCEPT the requirements; numeric B and implementation remain pending | Require a durable oldest-pending-log identity/age guard that HALTs all signing, preserves reconciliation and never weakens the hard upload deadline. Only positive stored per-chunk ACKs release pending work. Restart, partial/out-of-order ACKs, empty200/timeouts, clock reversal/future timestamps and exact threshold boundaries must fail closed. Clearing requires the reviewed complete-ACK/clock rule; no restart/refresh may extend authority. No illustrative2h value is adopted. | Keegan supplies reviewed code and lifecycle/clock/ACK tests. Operator supplies normal and tail dispatch/ACK measurements; Isaac decides the exact B with a documented margin after those inputs. This guard is not implemented or qualified by this review. |

D-DN-06 watchdog and D-DN-08 memory remain **MEASUREMENT_BLOCKED**. No600s
watchdog,2h delivery bound, sum-of-MemoryMax capacity claim, instance resize or
swap policy is adopted. Operator provides the timestamped whole-cycle/drain/
finality and concurrent-memory packet described above; Keith/Keegan analyze
coverage/headroom and Isaac then decides the exact settings.

Evidence checked: [runtime unit](../../deploy/systemd/larp-runtime.service),
[`Sessions` and `Guard`](../../larp/runtime/supervision.py),
[service start/activation](../../larp/runtime/service.py),
[restore quarantine](../../larp/storage/backup.py),
[operations restore command](../../larp/runtime/operations.py),
[supervision tests](../../tests/runtime/test_supervision.py),
[anchor/restore tests](../../tests/runtime/test_anchors_roles.py).
Rules checked: verbatim source-page repository/autonomy/logging passages,
kit PROTOCOL and SKILL F-114/F-117/F-124 and answered Q-40. These decisions
retain the same registered-build boundary; they are team policy, not new rules.

**C05 status: review slice delivered; measurements, D-DN-04 code, independent
review and actual qualification remain open.** This does not approve #27/#44,
source/native capability, signed release, host installation or a signer session.
Validation and exact scope are recorded in IDEA-066 C05-RV01.
