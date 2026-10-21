# RG2 — boundary crash injection: design note (2026-10-21)

**Decided 2026-10-21 (Keegan, IDEA-042 RG2-D02):** all three recommendations below are accepted: the F1–F10 matrix
is frozen, the fault-point hook is to be built as specified, and Keegan approves each signer-host F3/F4 run, which
the operator (Keegan's team) carries out. **Built 2026-10-21 (RG2-H01):** `larp/runtime/faults.py`, the five
sites below and the refusals; see "Arming a drill" at the end.

Status: **DESIGN for Keegan's review. No code, config or host change.** RG2 in
[REHEARSAL_GATES_20261019.md](REHEARSAL_GATES_20261019.md) needs a frozen fault matrix at the authorized,
signed-durable, send/unknown, receipt/settlement and round/ACK boundaries, using approved instrumentation. It says
that a drill with missing instrumentation is BLOCKED. The LD21 packet's D1 kills only the runtime process at a random
point. This note proposes the matrix, how each crash is placed, and the pass checks, so that review can happen
before anything is built.

## What already exists (engineering evidence, not RG2)

- `tests/execution/crash_worker.py` and `test_postgres_execution.py` call `os._exit` in a subprocess at BEFORE_SIGN,
  AFTER_SIGN, AFTER_BROADCAST and AFTER_RECEIPT. They run against real PostgreSQL, with a fake venue and the
  in-process `RegistrySigner`.
- `tests/storage/crash_worker.py`: before/after event commit, and after the remote write before the local ACK.
- Those tests cover none of the following:
  - the real two-process path (runtime `RemoteSigner` → `signing_requests` → `SignerService` on another host);
  - a real node or receipt RPC;
  - systemd restart;
  - recovery time.

## Durable state machine (from `larp/execution.py`, `execution_live/service.py`, `execution_live/signing.py`)

```
PREPARED ─authorize→ AUTHORIZED ─RemoteSigner.submit→ signing_requests row ─SignerService._sign→
execution_signatures row (put_if_absent, one per attempt) ─runtime sign()/recover_signature()→ SIGNED_DURABLE
─broadcast(): commit BROADCAST_ATTEMPTED (broadcast_at set) → venue.broadcast → commit PENDING | UNKNOWN | REJECTED
─reconcile(): RECOVERY_PROBE commit → venue.outcome → commit INCLUDED_* | FINAL_* → advance(): settlement fact → observe
```

The crash points that matter are the gaps between a durable write and the next one. Inside each gap, recovery sees
the same persisted state whether or not the external effect happened. So each row below fixes the persisted state
and covers both "effect happened" and "effect didn't happen" where the two can differ.

## Fault matrix (proposed, to be frozen before any run)

| ID | Process | Crash point | Persisted state at restart | Required recovery |
|---|---|---|---|---|
| F1 | runtime | after AUTHORIZED commit, before `submit` | AUTHORIZED, no request | `recover_signature` finds nothing → a new request for the **same** attempt; one signature |
| F2 | runtime | after `submit`, while waiting for signer | AUTHORIZED + request | the signer still answers; `SIGNATURE_RECOVERED` on restart, no second request signed |
| F3 | signer | after reading the request, before `put_if_absent` commits | request pending | the request is served again after the signer restarts; exactly one signature row |
| F4 | signer | after the signature commit, before the next cycle | signature row | the runtime picks it up; the signer doesn't sign it again (`pending()` excludes it) |
| F5 | runtime | signature visible, before the SIGNED_DURABLE commit | AUTHORIZED + signature | `SIGNATURE_RECOVERED`; the bytes equal the registry row |
| F6 | runtime | SIGNED_DURABLE, before the BROADCAST_ATTEMPTED commit | SIGNED_DURABLE, `broadcast_at` null | at most one guarded first broadcast; if authority changed or the intent expired, abort or reauthorize with no send |
| F7a | runtime | BROADCAST_ATTEMPTED committed, **before** the network send | possible send, not sent | no blind resend; reconcile until the timeout → the nonce check shows it unused → the barrier holds until reconciled; reservation retained |
| F7b | runtime | node accepted the bytes, before the PENDING commit | possible send, sent | reconcile finds the tx by hash → FINAL; no resend |
| F8 | runtime | during reconcile, after the receipt is read, before the FINAL commit | RECOVERY_PROBE | the next probe re-reads the same receipt → FINAL once; gas and receipt match the signed limit |
| F9 | runtime | FINAL committed, before the settlement observation is published | FINAL | `advance()` republishes; the consumer dedups by event_id; one FILL/REVERT per attempt |
| F10 | runtime | round logged, before the uploader ACK | journal event, no ACK | covered by the storage crash tests plus D2 (uploader stop); RG2 only re-checks ACK continuity after F1–F9 |

F7a and F7b are the RG2 "send/unknown" boundary. F8 and F9 are "receipt/settlement". F1–F5 are "authorized" and
"signed-durable". Each row runs once for an approve step and once for a SWAP, because a SWAP's `possible_swap_hashes`
must stay mapped to its round.

## How each crash is placed

Two mechanisms, chosen per row:

1. **External kill on a durable marker (F1, F2, F4, F6, F9):** the gap is wide (a signer round trip, a guard
   snapshot, or a loop cycle). The drill uses a read-only watcher that polls the drill database for the marker row
   (for example the AUTHORIZED event, or a `signing_requests` row with no signature). When the row appears, the
   operator's approved command sends `systemctl kill -s SIGKILL` to the unit. No product code is needed. The watcher
   records the marker sequence, so the attempt can show where the kill actually landed. A kill that lands after the
   next marker counts as a different row, not a pass.
2. **In-process fault point (F3, F5, F7a, F7b, F8):** these gaps are microseconds wide, and an external kill can't
   land in them reliably. They need a named hook at the exact line, so this mechanism needs code.

### Proposed fault-point hook (for review; not built)

- A module `larp/runtime/faults.py` with one function, `point(name)`, called at five sites:
  - `SignerService._sign` just before `self.signer.sign`, and just after it returns (F3);
  - `Executor.sign` after `signer.sign` returns, before `_update_attempt` (F5);
  - `Executor.broadcast` after the BROADCAST_ATTEMPTED commit, before `venue.broadcast` (F7a);
  - `Executor.broadcast` after `venue.broadcast` returns, before the phase commit (F7b);
  - `Executor.reconcile` after `venue.outcome` returns, before the phase commit (F8).
- It is armed only when **all** of these hold. Otherwise it is a no-op that reads no file:
  - the environment names the point (`LARP_FAULT_POINT=F7b`);
  - a one-shot token file exists in the unit's runtime directory, and the hook consumes it with an atomic rename, so
    the restarted process doesn't crash again;
  - the run projection's mode isn't the final live run. Preflight and `check_signing_run` refuse to start a
    final-mode run if `LARP_FAULT_POINT` is set.
- When armed, it calls `os.kill(os.getpid(), SIGKILL)`. That gives no Python cleanup and no `finally` blocks, the
  same as an OOM kill.
- The hook ships in the same build as the one under test. RG2 asks for a same-build restart, so a separate
  "fault build" would test a different binary.
- Tests:
  - each point unarmed is a no-op (no file read once the environment variable is absent);
  - the token is consumed exactly once;
  - final mode refuses to start with the variable set;
  - an extended `crash_worker` drives F3/F5/F7a/F7b/F8 through the real `RemoteSigner` and `SignerService` against
    local PostgreSQL before any host use.

Alternative considered: Linux `ptrace` or eBPF breakpoints on the CPython frames. That needs no product code, but it
needs root debugging tools on the hosts, and its placement depends on the interpreter. Not proposed.

## Pass checks (read-only, after each restart)

Run once the unit is active again and the attempt has reached a terminal or a stable fenced state:

1. **No duplicate economic execution:**
   - `execution_signatures`: at most one row per attempt_id;
   - no two attempts in an intent share a nonce, unless one of them is NOT_SUBMITTED;
   - each SWAP tx_hash appears in `possible_swap_hashes` of exactly one intent, and that intent's round.
2. **UNKNOWN stays fenced:** while an attempt is UNKNOWN/PENDING/REJECTED_UNRESOLVED, the wallet barrier blocks new
   prepares, and the reservation rows are unchanged.
3. **No release on restart or timeout alone:** reservations are released only through FINAL, REVERT or
   NOT_SUBMITTED events, never by an ABORT that follows a possible send.
4. **Restart:** systemd restarts the unit (NRestarts +1, new InvocationID), with an incident or HALT entry where the
   runtime records one. The journal verifies.
5. **Recovery time:** the time from the kill to the first post-restart progress event on that intent. It is recorded
   against the LD14 bound once that bound is adopted. Until then the row is "measured, bound pending", not PASS.
6. **Chain agreement:** for F7b/F8/F9, the receipt from the qualified RPC (LD02c PF-01) matches the FINAL attempt's
   block hash and gas used.

## Where it runs and who acts

- **Local first:** the extended crash worker against PostgreSQL, with a fake venue and a fake chain. Every row runs
  there before the host.
- **Signed development hosts only, after LD19/LD20.** It never runs on the final wallet or during the scored run
  (F-114, F-117).
- **Host writes are the operator's**, each with its own approval: setting `LARP_FAULT_POINT` through a systemd
  drop-in, placing the token, and the SIGKILL. F3/F4 act on the **signer host**. These sessions never touch that host,
  so those rows need Keegan's explicit approval and an operator on that host.
- **Chain rows:** F7b/F8/F9 spend real development-wallet gas: one approve or swap each, about 12 transactions for
  the approve and SWAP variants. Count them into the LD09 N (see
  [LD09_GAS_BUDGET_PROPOSAL_20261021.md](LD09_GAS_BUDGET_PROPOSAL_20261021.md)).

## Decisions for Keegan

1. Accept the matrix F1–F10 (or amend it) and freeze it in the RG-01 attempt template.
2. Accept the fault-point hook in the release build, inert by default, with a final-mode refusal. The alternative is
   to run only the external-kill rows and record F3/F5/F7a/F7b/F8 as BLOCKED.
3. Approve, or name someone to approve, the signer-host rows F3/F4.

## Arming a drill (RG2-H01, built 2026-10-21)

Run this only on the signed development hosts, after LD20, with Keegan's approval for each run.

1. Pick one point: `F3`/`F4` (signer host only, and only with Keegan's explicit approval), or `F5`, `F7a`, `F7b` or
   `F8` (`larp-execution` on `primary`).
2. As root, create a token in the unit's runtime directory, for example
   `install -o larp-execution -m 0600 /dev/null /run/larp-execution/drill.token`. The rename that consumes it needs
   the service user to be able to write that directory.
3. Add a systemd drop-in with `Environment=LARP_FAULT_POINT=F7b` and
   `Environment=LARP_FAULT_TOKEN=/run/larp-execution/drill.token`, then run `daemon-reload` and restart the unit.
   Preflight refuses the start if the run is `live`, the point name is unknown or the token path isn't absolute.
4. Let a round reach the point. The process dies by SIGKILL and systemd restarts it. The token is now
   `drill.token.consumed`, so the restarted process runs normally.
5. Apply the six read-only pass checks above. Then remove the drop-in, run `daemon-reload`, and delete the
   consumed token.

Local evidence:
- `tests/execution/test_fault_points.py`: F5, F7a, F7b and F8 each kill a real child process, and a restarted
  executor recovers;
- `tests/signer/test_fault_points.py`: F3/F4 through `SignerService`, plus the refusals at signing and preflight;
- `tests/runtime/test_faults.py`: the hook is inert by default, fires once, and validates its configuration.
