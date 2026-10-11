# IDEA-036 — Build hourly write-once anchoring of the audit journal

- Date / author: 2026-10-11 / SYZ (team decision, IDEA-035 §4; drafted with Claude)
- Status: open (decided to build; not started)
- What: once an hour, write the current head of the runtime audit journal (run, sequence, head hash, UTC slot) to write-once storage outside the runtime database, and keep the acknowledgement. This keeps the proposal's declared "anchored hourly" commitment (GAP-35), so no deviation is needed.
- Why it might help: the organisers' ai-seeds store anchors the official round logs (F-101), but our complete local logs (F-47) live in our own PostgreSQL. An independent hourly anchor shows that the journal was not rewritten after the fact: a restored or edited journal no longer matches its anchored heads (`verify(..., anchored_head=...)`). It supports never-do #9 (no backfilled or rewritten logs) and the winner audit (F-17).
- Cost / risk:
  - The code side exists. `larp.runtime.maintenance` schedules durable hourly anchors (Anchor.v2, immutable UTC slots, 3600 s) and `anchor(...)` hands an immutable head record to a write-once receiver (IDEA-028; `docs/build/runtime-operations.md` "Backup, anchoring and retention").
  - Missing: the receiver destination, the worker schedule in deployment, retention, alerts, and a verification drill.
  - S3 Object Lock COMPLIANCE retention cannot be shortened later, so choose it deliberately (B9). The recommendation is a separate versioned bucket with Object Lock and a restricted writer role (`docs/build/runtime-infrastructure.md`).
  - Missed hours are never backfilled; the next current-time anchor exposes the gap.
- Links: GAP-35, G-07, F-47, F-62, F-101; IDEA-028; IDEA-035 §4 and §7 item 12; B9 (deployment inputs); architecture-deployment.md steps 3–7.

## Acceptance criteria (written before building)

Owner: Keegan (destination and deployment), reviewer SYZ. Due with the infrastructure steps, before the rehearsal signs anything.

1. **Destination:** a write-once receiver outside the runtime database and outside Git. Recommended: an S3 bucket with Object Lock. Its retention is chosen and recorded first: through at least the end of the audit and technical-review period, i.e. at least Dec 31, 2026 (IDEA-035 §9).
2. **Cadence:** in a run of at least 24 hours in the dev environment, every UTC hour slot has exactly one anchor record, or a logged incident naming the missed slot. No slot is written twice, and no past slot is written late.
3. **Verification:** `verify(run_id, anchored_head=...)` passes against the anchored heads. A test that alters one journal event after it was anchored makes verification fail.
4. **Immutability:** an attempt to overwrite or delete an anchor record under the runtime's writer role is refused by the storage, and the refusal is recorded.
5. **Restore drill:** after a backup restore into an empty database, verification against the anchors succeeds for the restored run, and a restore older than the latest anchor is rejected as stale.
6. **No secrets:** anchor records contain hashes and identifiers only, never keys, credentials or private model/evidence text.

Result: (fill after the drill) pass/fail per criterion, environment, commit SHA.
