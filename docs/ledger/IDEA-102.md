# IDEA-102 — Mandatory sells are not capped per session; spacing and gas guards bound them instead

- Date / author: 2026-10-26 (SGT) / Yao's decision in a Claude Code session ("yes change it"). The record and spec are
  by Claude Code; the implementation is for a teammate (ChatGPT/Codex). Review: Keith (strategy rules), Keegan
  (runtime).
- Status: **open — decided; spec and pass criteria MC1–MC8 pre-registered below. Not implemented.**
- Related: IDEA-076 Q14 (S1 per-leg/session attempt budget), IDEA-089 S2-9 (3 → 5 attempts),
  IDEA-097 S4-F1 (PR290, refund of never-claimed attempts), IDEA-093 FS1 (final profile), IDEA-084 PF-04 (final
  calendar).

## Why (run 5, 2026-10-25)

- Run 5's terminal flatten sold everything except the second half of GOOGLB (0.029482, about 9.5 USDT). At 16:30Z it
  was refused with `LEG_ATTEMPT_LIMIT`: all 5 `SAFETY:SELL:GOOGLB` attempts of session 203 were spent.
  - Three of those commands expired unclaimed; PR290 fixes that case.
  - One aborted at the price check; one sold.
- The cap then kept a mandatory exit open for about 20 hours, until session 204 (Mon 13:30Z).
- **The same rule threatens the final.** FS1's flatten runs from 2026-11-10T19:00Z to 2026-11-11T14:45Z with
  `KIT_OPEN_STATE` hours and 5 attempts per leg. Almost all of it sits in one session (Nov 10 14:30Z → Nov 11
  14:30Z), followed by one 15-minute session.
  - Five price-check aborts on one volatile name would leave it held when scoring ends.
  - An unsold mandatory exit costs more than a few cents of approve gas.
- The cap is still right for discretionary legs: it stops gas and quote churn on trades the strategy only wants.

## Decision (Yao, 2026-10-26)

**Mandatory (`SAFETY`) SELL legs are not limited by `max_attempts_per_leg_session`.** These are the terminal flatten,
the S3 scheduled flatten, loss-ladder/hard-line reductions, red-flag exits and any other `mandatory: true` SELL.

They stay bounded by:
1. **spacing:** at most one new mandatory attempt per leg per cadence slot (15 min). A quote child of the same
   chain (`/quoteN`) may still reuse its parent's slot as today;
2. the existing gas checks: the exit gas reserve, `gas_action_budget_units` per intent, and the signer fee cap;
3. the execution window and `signing_end`;
4. allowance recovery (IDEA-096) and the strict swap preflight, both unchanged.

Discretionary legs keep the per-session cap exactly as today.

## Implementation spec (for the implementer)

- **`larp/strategy/execution_bounds.py`**
  - In `reserve`: when `mandatory` is true, do not refuse on `max_attempts_per_leg_session`. Still increment the
    ordinal, so attempts stay numbered and auditable.
  - Instead, refuse with a new reason `MANDATORY_RETRY_SPACING` when the leg's last reservation is in the same
    cadence slot and is not a reusable parent slot.
  - Store the last reservation time per leg in the budget: `last_ms: {leg: ms}`. Today the budget validator accepts
    only `session`, `counts` and `closed`, so extend it with an optional `last_ms` restricted to the same leg keys.
    A budget without `last_ms` stays valid; no migration.
- **`permitted`** must accept a mandatory authority whose ordinal is above the configured cap. Keep every other check
  (schema, session, leg, interval, `ordinal == count == closed`).
- **Planner (`larp/risk/planner.py`):** no change beyond passing `now_ms` and the cadence length if `reserve` needs
  them.
- **Profile key: none.** The behaviour is the same for every S1 profile. Existing profile hashes do not change.
  Document it in `config/strategy/LIVE.md`.
- **Replay:** a recorded round reproduces its plan from its own recorded budget. Old rounds have no `last_ms`, and
  their recorded plans are unchanged.

## Pass criteria (pre-registered before implementation)

| # | Pass when |
|---|---|
| MC1 | **Red on base:** a 6th mandatory SELL attempt in one session is refused with `LEG_ATTEMPT_LIMIT` on canonical. After the change it is planned (ordinal 6) in the next cadence slot. |
| MC2 | A second mandatory attempt in the **same** cadence slot is refused with `MANDATORY_RETRY_SPACING`, except a `/quoteN` child reusing its parent's slot, which still plans. |
| MC3 | Discretionary BUY and SELL legs still stop at `max_attempts_per_leg_session` with `LEG_ATTEMPT_LIMIT`, unchanged. |
| MC4 | `permitted` admits a mandatory intent with ordinal > cap and refuses the same authority for a discretionary leg. Every existing `execution_bounds` test passes unchanged. |
| MC5 | Gas guards still apply: with BNB below the exit reserve or the per-intent gas budget, the mandatory SELL is refused or held exactly as today; the spacing never bypasses HALT, health or the window. |
| MC6 | Budget validation: a budget without `last_ms` loads; malformed `last_ms` (unknown leg, non-integer, future time) is refused. |
| MC7 | Replay of existing journals and fixtures is byte for byte (full suite); a new journal with ordinal > 5 replays exactly. |
| MC8 | A synthetic flatten in which one name aborts at the price check 8 times in a session still reaches dust within the window, with one attempt per slot, no more. Full pinned suite: no new failures. |

## Not changed

Strategy sizes, slippage, the flatten window, `max_attempts_per_leg_session` (still 5 for discretionary legs), the
signer and execution caps.
