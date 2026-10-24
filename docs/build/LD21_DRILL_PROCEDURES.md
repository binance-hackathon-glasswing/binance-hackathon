# LD21 drill procedures (RG2–RG6, RG8) — operator packet

Status: **PREPARED; every drill NOT_RUN.** This turns the gates in
[REHEARSAL_GATES_20261019.md](REHEARSAL_GATES_20261019.md) into pinned procedures for the approved operator, run
after LD19/LD20 on the **signed development** environment. It never runs during the scored run (F-114, F-117), and
never against the final wallet. Each drill attempt is recorded with the RG-01 `RehearsalGateAttempt.v1` template;
procedures and pass criteria are fixed here before any run.

Common rules:
- **Freeze identities first.** Before each drill, record the run, build, profile, bound manifest and database
  identity using the read-only LD02 packet (`docs/build/ops/ld02-20261020/execution-packet.sh`). Don't drill while
  a round is open, or while a command or reservation is in flight, unless the drill targets that boundary.
- **Observe with read-only checks only:**
  - `docs/build/ops/llm-trial-20261018/checks/host-health.sh` (units, operational health, ACK/anchor/backup);
  - `balance-health.sh` (process identity and the `balances_ok` gate);
  - the LD02 packet.
- **Who acts:** host writes (stopping or killing units, restores) are the operator's, each under its own approval.
  Reviewers only read.

## D1 — automatic restart (RG2, DR-13; F-124)

1. Record `systemctl show larp-runtime -p MainPID -p InvocationID -p NRestarts -p ActiveEnterTimestamp`.
2. Operator: `sudo systemctl kill -s SIGKILL larp-runtime`.
3. Read the same properties every 2 s until active again. Then run `balance-health.sh`.

**Pass:** systemd restarts it with no human action. NRestarts goes up by exactly 1 and InvocationID changes. The
restart latency is recorded against the adopted LD14 value; the historical ~10 s isn't a bound. The journal verifies
(`host-health.sh` `journal_ok`). No command is duplicated. Rounds after the restart record `balances_ok=false`
until the new process's first comparable balance check, then true (a restarted run reconciles before new risk).
**Fail:** a manual start is needed, a duplicate command or signature appears, or `balances_ok` is true before a
fresh check.

## D2 — autonomous HALT and clear (RG3, DR-13)

Trigger: `DELIVERY_AGE` (LD13), which is reversible and needs no clock manipulation.

1. Note the configured delivery-age limit and the current audit-chunk ACK state (`host-health.sh`).
2. Operator: `sudo systemctl stop larp-uploader`.
3. Wait until the oldest unacknowledged round log is older than the limit. Keep observing rounds.
4. Operator: `sudo systemctl start larp-uploader`.

**Pass:**
- A `HALT` event with reason `DELIVERY_AGE` is journaled.
- Rounds keep running and logging (`HALTED:<reasons>`, no orders), and the signer receives no request.
- After the restart, the backlog is ACKed and a `HALT_CLEARED` event appears with no human clear action.

The CLOCK variant in runbook §3 is optional: it needs the guard's clock input set behind the last decision on
the rehearsal build. **Fail:** orders are planned while halted, the HALT clears before the backlog is ACKed, or
someone has to clear it by hand.

## D3 — anchors (RG4, DR-15; IDEA-036 criteria 1–6)

1. After at least 24 h of hourly slots, operator downloads the run's anchor objects from the archive prefix into a
   private directory.
2. `python tools/deploy/drill_verify_anchors.py --config /etc/larp/operations.json --anchors-dir DIR`
3. On a designated drill object only, attempt an overwrite and a delete with the writer role, and record the
   refusal.

**Pass:** the harness exits 0 (`PASS`) and the journal head matches. `missing_slots` is empty, or each gap has a
recorded incident. The overwrite and delete are refused by object lock.
**Fail:** exit 1 (`FAIL`: a head differs, or the restore is stale), an unexplained gap, or a successful overwrite
or delete.

## D4 — restore and alert (RG5, DR-15/16)

1. Pre-create an **empty, migrated, isolated** drill database. Check that it isn't the active database.
2. `python -m larp.runtime.operations restore --config /etc/larp/operations.json --receipt "$LARP_DRILL_BACKUP_RECEIPT" --target-dsn-file "$LARP_DRILL_TARGET_DSN_FILE"`
3. Run `drill_verify_anchors.py` against the restored target (a config pointing at it) with the same anchors.
4. Exercise one approved alarm, for example the `runtime-low-gas` or `uploader-overdue` test path, and obtain the
   recipient's acknowledgement.

**Pass:** the backup checksum, journal verification and anchors all pass on the target. A restore behind the
latest anchor is reported stale, never adopted. The alarm reaches its recipient, and the acknowledgement is
recorded. The active run is untouched.
**Fail:** any write to the active database, a stale restore accepted, or an unacknowledged alarm.

## D5 — throwaway wallet switch (RG6, DR-17)

Use a **throwaway** wallet address and dedicated directories, never the registered final wallet or its secret.

1. `python tools/deploy/drill_wallet_switch.py preflight --config /etc/larp/runtime.json --new-wallet THROWAWAY --new-ai-seeds-dir DIR1 --new-nonce-dir DIR2`
2. Negative cases, each expected to be refused by the preflight (exit 3):
   - the same wallet as the old run;
   - a shared directory;
   - a directory bound to another wallet;
   - the old run while it has an open round, if one can be observed naturally.
3. On the isolated drill database only: the `switch` step with `--confirm-old-run`, the opening projection and a
   new record file. Then confirm the new run is quarantined and the live-start checks refuse an address mismatch.

**Pass:** the preflight's blockers match exactly what `switch_wallet` refuses. The switch record holds the old
run's verified head. The new directories are bound to the throwaway address. Nothing touches the active run's
database.
**Fail:** the preflight says ready but the switch refuses (or the reverse), or any write reaches the active
database.

## D6 — actual-day replay (RG8, DR-19)

1. Pre-create an **empty, migrated, isolated** drill database (as in D4) and write its DSN to a private file.
2. `python tools/deploy/drill_replay_day.py --config /etc/larp/runtime.json --target-dsn-file FILE`
   (add `--through-sequence N` to replay up to the end of one UTC day).
3. Run it once for a shadow day and once for a signed rehearsal day, each against its own fresh target.

The harness reads the source journal in READ ONLY transactions. It rebuilds the context builder, planner and policy
from the run's pinned configuration exactly as `build_driver` does, with every live port made to raise, and replays
into the target with `replay_live`. It refuses a non-empty target, and a target that is the source database.

**Pass:** exit 0. The replayed head equals the source head at that sequence, and no live port was called.
**Fail:** exit 1 (`LIVE_PORT_CALLED`, a divergence, or a different head), or any write to the source.

## Not covered here (remaining LD21 work)
- **Boundary crash injection for RG2:** crashes at authorized, signed-durable, send/unknown and receipt boundaries
  need signer-side instrumentation that doesn't exist yet. D1 covers the runtime-process crash only. The fault
  matrix F1–F10 and the proposed instrumentation are in `RG2_CRASH_INJECTION_DESIGN_20261021.md` (IDEA-042
  RG2-D01, PR215), accepted 2026-10-21 (RG2-D02); the hook is built (RG2-H01) and the arming steps are in that note. Host runs happen
  after LD20, with approval for each run.
- **RG7 time boundaries and RG9 daily rehearsal records:** these need Keith's adopted profile and the signed days.
