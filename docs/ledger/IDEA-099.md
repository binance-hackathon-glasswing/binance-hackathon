# IDEA-099 — Concise reason summary in every decision record (F-34, G-04, F-125 self-check)

- Date / author: 2026-10-25 / Claude Code, asked by the user ("yes, add the reason summary please") after a check of
  the F-125 self-check list ("Decision record generated with reason summary"). Owners for acceptance: Keegan
  (runtime/audit), Isaac (round-log contents); host check on the next run: Yao.
- Status: **open — pre-registered (criteria RS1–RS7 below committed before any test or code).**
- Related: F-34, F-99..F-101, F-125 (6), G-04, GAP-46, IDEA-042 (round log), IDEA-093 (FS1).

## Problem (read from the code at canonical `f52107f0`)

F-34: "Every scored trade must be traceable. It must map to one registered Agent version and one unique decision
record with a concise reason summary." F-125's self-check repeats "Decision record generated with reason summary".
G-04 asks for a reason summary of at most three sentences, generated from the structured fields actually used.

The round log (`Coordinator.audit_record`, the ai-seeds log) carries `version_id`, `decision_ids`, the plan with each
intent's `reasons` codes (for example `TERMINAL_FLATTEN`, `S1_LEVEL_CHANGE`, `CLASS_1_EXIT`), `mandatory`, the
planner's clamps and rejections, and the `cot`. Nothing states in plain words why each order was placed, or why a
round placed none. `grep -rn reason_summary larp` finds nothing.

## Design (proposed)

- New module `larp/audit/reasons.py`. A pure function builds one sentence per planned order from the round record's
  structured fields only: side, amount, symbol, whether it is mandatory, the intent's `reasons` codes, the policy
  target for that symbol (kind, reason, weight) when present, and a per-trade-cap split from the planner's clamps.
  Each known code maps to a fixed phrase; an unknown code is shown as the code itself, so the summary never fails.
  No model text, prices, or values that are not in the record.
- A round with no order gets one summary sentence naming why: the round's errors (for example `HALTED:…`,
  `VERSION_NOT_REGISTERED`), else up to three planner rejection reasons, else "no target change".
- In the uploaded log's `output`: `reason_summary` (the round's summary) and `decision_summaries` (one entry per
  order, in the order of `orders`: `decision_id`, `symbol`, `side`, `amount`, `summary`). `orders` itself is unchanged
  (kit schema). The audit-fallback log also gets a `reason_summary`.
- The planner plans at most one order per round today, so the round summary is that order's sentence; the code does
  not rely on that.

## Pre-registered pass criteria (written before any test or code)

Base for "red on base": canonical `f52107f0`. Tests in `tests/audit/test_reason_summary.py` and the existing
coordinator/replay tests.

| # | Pass when |
|---|---|
| RS1 | A round that plans one order produces a log whose `output.reason_summary` is a non-empty string of at most three sentences and 400 characters, and whose `output.decision_summaries` has exactly one entry per `orders` entry, in the same order, with matching `symbol`, `side`, `amount` and the intent's `decision_id`. Red on base. |
| RS2 | The sentence names the side, amount and symbol, says mandatory or discretionary, and gives a fixed phrase for each `reasons` code: at least `TERMINAL_FLATTEN`, `SCHEDULED_FLATTEN`, `CLASS_1_EXIT`, `ACTIVATION_SELF_CHECK`, `POSITION_CAP`, `GROSS_OR_REGIME_CAP`, `DEEP_DRAWDOWN`, `POSITION_COUNT_CAP`, `S1_LEVEL_CHANGE`, `S1_TOP_UP`, `ACTIVATION_SELF_CHECK_BUY` and a gas top-up. A per-trade-cap split is stated. An unknown code appears verbatim and does not raise. |
| RS3 | A hold-only round (no order) has `reason_summary` naming its errors, or else up to three distinct planner rejection reasons, or else that no target changed; `decision_summaries` is empty. An audit-fallback log has a `reason_summary`. |
| RS4 | The summary is a pure function of the stored round record: the same record gives the same bytes, and the existing replay tests reproduce the journal heads. |
| RS5 | `orders` bytes and `check_orders` / protocol validation are unchanged; the summary contains no secret (it is built only from the listed fields, and goes through the same `redact` as the rest of `output`). |
| RS6 | Every other test passes. Tests that pin exact round-log bytes or hashes are updated only for the two new `output` keys, and each such update is listed in the results. |
| RS7 | Full suite: no new failures against `f52107f0` in the same environment; exact counts reported. |

Result states: `supported` if RS1–RS7 pass; `not supported` if RS1–RS5 fail after the fix.

## Results

(none yet)
