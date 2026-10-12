# LARP runbook (draft) — start, restart, HALT, restore, version, final-wallet switch

Draft for the activation pack (DR-22; [IDEA-042](../ledger/IDEA-042.md) T2). Each step names the code that does it and the test that shows it. Steps marked **host** still need their drill on the provisioned environment (Gates A–C in [DEPLOYMENT_BUILD.md](DEPLOYMENT_BUILD.md)).

**During the scored run nobody acts on the agent** (F-114, F-117, never-do #1). Restart, HALT, clearing and quarantine below are all automatic. People only watch alarms, record what they see, and act before activation or after the run.

## 1. Start (before anything trades)

1. **Release check:** `python -m larp.runtime.preflight --manifest /etc/larp/release.json --root /opt/larp/current`. It refuses a file not in the manifest, a changed services list or deviations register, and missing registration evidence (`larp/runtime/preflight.py`; tests `tests/runtime/test_operations.py`, `tests/runtime/test_release_register.py`).
2. **Version event:** `Coordinator.register_version(manifest, now)` commits `VERSION_REGISTERED`. A coordinator with `require_version=True` commits no execution command before it (`tests/runtime/test_release_register.py`).
3. **Live-start checks:** in `dev`/`live` mode, `larp.runtime.service run` refuses to open a session when:
   - a port is a fake;
   - a runtime secret is missing;
   - a wallet key is on the runtime host;
   - the addresses disagree;
   - a record directory belongs to another wallet.

   It exits 1 with the reason and never a secret value (`larp/runtime/live.py`; `tests/runtime/test_live_start.py`).
4. **Process session:** one durable session per process (`larp/runtime/supervision.py` `Sessions`).

The round driver arrives with integration (item 10). Until then `service run` exits 2 (not integrated) and systemd does not restart it.

## 2. Automatic restart (C5) — **host** drill at Gate A

- Unit: `deploy/systemd/larp-runtime.service`: `Restart=always`, `RestartSec=10`, no start limit, preflight before every start, `KillMode=control-group`.
- A crash leaves the session open, so the next start commits one `INCIDENT` (RESTART) journal event naming the crashed session. The restart runs the same build: another build is refused.
- Exit codes 2 (not integrated) and 3 (quarantined) are not restarted, because restarting cures neither.
- Tests: `tests/runtime/test_supervision.py` (H1, H2).
- **Host drill:** `systemctl kill -s SIGKILL larp-runtime`. Expect the unit back within about 10 s and one RESTART incident in the journal.

## 3. HALT and its automatic clearing — **host** drill at Gate B

| Trigger | Effect | Clears |
|---|---|---|
| Decision clock behind the last committed decision | HALT `CLOCK` | Never during the run (latched) |
| A round log past its upload deadline (next UTC midnight + 2 h) | HALT `DELIVERY_DEADLINE` | Automatically, once nothing is overdue |
| N consecutive failed rounds (planner, plan, commit, policy, context, audit content) | HALT `REPEATED_FAILURES` | Automatically, after the configured number of successful rounds |
| Journal fails verification | Run **quarantined** (every write and signature fenced) | Not during the run |

While halted:
- every round still runs and is logged (`HALTED:<reasons>`, no orders);
- no command is committed;
- `store.command()` refuses every signature, mandatory exits included.

Every HALT and clear is a journal event. Tests: `tests/runtime/test_supervision.py` (H3–H6).

**Host drill:** set the guard's clock input behind the last decision on the rehearsal build. Expect `HALT:CLOCK`, rounds still logged, and the signer receiving nothing.

## 4. Restore — **host** drill at Gate B

1. `python -m larp.runtime.operations restore --config /etc/larp/operations.json --receipt <pinned backup receipt> --target-dsn-file <empty database DSN>` restores into an empty, migrated database. It verifies the backup checksum and every run's journal, and leaves every run **quarantined** with a new epoch.
2. Verify against the hourly anchors read back from the Object Lock archive: `larp.runtime.maintenance.verify_anchors(store, run_id, anchors)`.
   - A restore behind the latest anchor is refused as stale.
   - A rewritten journal is refused.
3. A quarantined run accepts no session, round or signature until a reviewed takeover before the run. During the scored run a quarantine stays: it means the agent has stopped trading.

Backups include the journal, outboxes, process sessions and the execution store. Tests: `tests/runtime/test_maintenance.py`, `tests/runtime/test_anchors_roles.py` (A1–A3).

## 5. Final-wallet switch (Oct 27–29; GAP-52, C7) — **host** rehearsal at Gate C

1. **By Oct 26:** confirm the final wallet's new `AI_SEEDS_SECRET` (C7) and place the final secrets in the runtime secret store only.
2. **Old run:** after the development run's last round, it must have no open round, reservation or pending command, and hold no token.
3. **Switch:** `larp.runtime.live.switch_wallet(...)` opens a fresh run for the final wallet with its own `.ai-seeds/` and nonce directories, marked for that wallet. The new run starts quarantined. The switch record (old run, final head, new run) goes into the activation pack.
4. **New run:** register the version for the final build (step 1.2) and start. The live-start checks refuse any address mismatch.

Tests: `tests/runtime/test_live_start.py` (W1–W4, including a throwaway-configuration rehearsal).

## 6. Owed by the team

- **On-call rota (GAP-37):** names, hours (SGT), backup cover, and what each person watches (alarms, daily delivery, anchors). Due Oct 20.
- **Alarm recipients and AWS inputs (B9):** due Oct 14.
- **This runbook's host drills:** results go into IDEA-042, with each owner's sign-off at Gate C.
