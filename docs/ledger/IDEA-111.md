# IDEA-111 — Stale cycle time makes `clock_trusted` refuse the swap after every approve

- Date / author: 2026-10-28 SGT / Claude Code at Keith's request (read-only host analysis, then this fix)
- Status: open (criteria registered before code; not merged, not installed)
- What: the TEMP-SC run (IDEA-110) on the final wallet approved SKHYB three times and never swapped. Each
  swap preparation failed `clock_trusted`, and with `allowance_recovery` on that one refusal cancels the intent
  and revokes the approval. Fix: `RunAuthorization.facts` compares the run's `last_decision_ms` with a clock
  reading taken after it loads the projection, not with the time the executor cycle started.
- Why it matters: FS1 runs the same code with `allowance_recovery: true` in all three services
  (`docs/build/ops/final-fs1/README.md` A1/M4). Every FS1 trade, BUY or SELL, approves first, so every trade
  can hit this. Each failure costs an approve and a revoke in gas and one of the leg's session attempts; a
  mandatory SELL or the terminal flatten can be left unsold.
- Links: IDEA-050 (where the check came from, `8fc135c6`), IDEA-096 (abort on any refusal after approval,
  `348946de`), IDEA-098 (FS1 recovery), IDEA-104 S5-OBS03, IDEA-110, F-125.

## Evidence (2026-10-28, read-only: SSM, CloudWatch, artifacts, one read-only DB connection, public RPC)

Run `larp-final-selfcheck-temp`, release `e261bcfc` (its execution code is byte-identical to canonical
`2aa95617`).

| Intent key | Approve (status 1) | Swap step | Zero revoke (status 1) |
|---|---|---|---|
| `3a33afd9…` | `0x88b7647a…` 04:00:52Z | `PREPARE_BLOCKED` "current execution prerequisite failed" | `0x1dffbfc4…` 04:01:51Z |
| `e3b7dc20…` | `0x5df4725a…` 04:03:47Z | same | `0x8932ef29…` 04:04:47Z |
| `80c58917…` | `0x35a8bb02…` 04:05:56Z | same | `0xe7ba034c…` 04:07:08Z |

- No quote request followed any approve, so the refusal came from the first `gates.check()` in `prepare()`,
  before any network I/O. The market was open throughout (`openState: True`, `TRADING`).
- Replaying the deployed `RunAuthorization.facts` against the run's own event rows: `audit_durable`,
  `reservation_valid`, `version_valid`, `risk_valid` and `health_valid` (assumed; not replayable) are True at
  every event between each approve and its revoke. Only `clock_trusted` is False, and only after the runtime
  commits a round mid-cycle.
- Mechanism: `ExecutionLoop.once` passes `now_ms // 1000` taken at the start of the cycle to every step
  (`loop.py:324`). The cycle that prepares the swap first fetches the approve receipt and commits its
  settlement observation (3–4 s). The runtime plans a new round right after that observation (every case), so
  `last_decision_ms` passes `now*1000 + 1000`:

  | Intent | latest possible cycle `now` | `last_decision_ms` at the check |
  |---|---|---|
  | `3a33afd9…` | 1793160060 | 1793160062036 |
  | `e3b7dc20…` | 1793160235 | 1793160236880 |
  | `80c58917…` | 1793160363 | 1793160365959 |

- The revoke is approve(router, 0) on-chain (OBS03-B1); the router allowance read 0 afterwards.

## Design (registered before code)

- `RunAuthorization` takes an optional `clock_s` (the executor's own clock). When set, `facts()` reads it once,
  **after** `store.load()`, and `clock_trusted` requires:
  - no `CLOCK` halt (unchanged);
  - an integer reading not before the caller's `now_s` (a backward reading is a regression, refused);
  - `reading * 1000 >= last_decision_ms - 1000` (unchanged tolerance).
  Without `clock_s` the behaviour is byte-for-byte the current one.
- Only `clock_trusted` uses the reading. `expires_at`, `permitted()` windows, reservations and every other fact
  keep the caller's `now_s`.
- `build_execution` passes the same `clock_s` it gives the executor and signer.
- Unchanged on purpose: IDEA-096's abort after a refusal following approval. A real clock regression still
  refuses and still cleans up.

## Pass criteria (offline; registered before code)

- **CT-1 (red before the fix).** A stub-store reproduction of the 04:01 case (`now_s` 1793160060,
  `last_decision_ms` 1793160062036, every other fact True): with a clock reading of 1793160063 taken after the
  load, `clock_trusted` is True and the other facts are identical to the no-clock result. Without `clock_s` it
  stays False. On the unfixed code the with-clock case fails.
- **CT-2.** Still refused, with a clock: a reading earlier than `last_decision_ms - 1000`; a reading earlier
  than `now_s`; a non-integer or boolean reading; a `CLOCK` halt with an otherwise good reading.
- **CT-3.** The clock is read after the projection load and at most once per `facts()` call.
- **CT-4.** `build_execution` wires the executor's own `clock_s` into the guards' `RunAuthorization`.
- **CT-5.** Regression: the execution, execution_live-composition, runtime and signer suites pass unchanged;
  the full suite has no new failures. PostgreSQL suites run only where a disposable database is configured;
  the receipt says which ran.

Not covered offline: the live race (needs a release and host run), and whether the runtime's round is caused
by the executor's observation commit (seen in all three cases, not traced through the runtime code).
