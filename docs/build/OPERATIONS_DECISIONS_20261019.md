# Operations decision packet — PC-OPS01 / A06

Prepared for Isaac's C05 review, 2026-10-19, from committed repository evidence.
**Proposals only: no policy, register, unit or runtime setting is changed.**
This completes the operations-proposal portion of A06; O2 and DEV20's final
owner disposition remain separate. Isaac can review the policy/risk choices
below now; measurements are required before accepting numeric settings or
claiming host readiness. This packet is not Isaac's approval.

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
