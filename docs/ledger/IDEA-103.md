# IDEA-103 — FS1 integration: every open fix, parallel settings confirmed, FINAL install tooling (F0p, Q1, M3)

- Date / author: 2026-10-25/26 / Claude Code, asked by the user: "Fully fix the FS1 completely. Make sure it
  incorporates all the PRs that were made today, and yesterday, and ensure it can trade in parallel". Clarified in
  chat: one integration PR for the open PRs. On "parallel", the user asked how it works and whether it is safe; the
  answer is the design below (parallel assessments, serial wallet). Owners: Keegan (runtime/review), Isaac (signer,
  caps), Yao (install), Keith (strategy values unchanged).
- Status: **open — pre-registered (criteria FI1–FI7 committed before any test or code of this entry).**
- Related: IDEA-093 (FS1), IDEA-096/098 (allowance recovery), IDEA-097 (S4, run 5; PR290 S4-F1), IDEA-099 (reason
  summary, PR287), IDEA-100 (database, PR288/PR292), IDEA-101 (parallel verification, PR289), IDEA-102 (mandatory
  sells, PR291), ARCH-01 (PR281), F-125, GAP-74.

## What "trade in parallel" means in FS1 (read from the code at canonical `be31b37a`)

- **Assessments run in parallel:** up to `assessment_workers` = 5 background threads, one assessor instance per
  thread and one pending job per company (`larp/runtime/deferred_models.py`). Results are committed one per tick on
  the main thread. Models never size, sign or place orders.
- **Wallet trades are serial by design:**
  - the planner plans nothing while a reservation is in flight (`WALLET_PENDING`), and plans one intent per round;
  - `continuation_rounds` = 4 lets up to four more trades follow in the same 15-minute slot, each after the previous
    one settles (`RoundDriver.continuation`);
  - the swap preflight refuses any swap while another token has a router allowance (IDEA-096).
- **Truly concurrent swaps are not built.** They would need the allowance rule removed, several nonces at once and a
  signer policy change. This entry does not change that.

## Open PRs brought in (integration branch `claude/fs1-integration-20261026`)

| PR | What | State when merged here |
|---|---|---|
| 290 | S4-F1: an expired, never-claimed command gives its attempt back | merged into canonical as `be31b37a` during this work |
| 291 | IDEA-102: mandatory sells spaced one per cadence slot, not capped per session | open, head `61a1dba1` (implementation present; its MC-RV01 results not yet recorded by its author) |
| 292 | IDEA-100 DB1/DB2/DB5 (with PR288's spec) | open, head `c586fd64` |
| 281 | ARCH-01 trigger (docs) | open, head `d433c82a` |

Every PR merged on 2026-10-24/25 (#267–#287, #289) is already in canonical.

## Pre-registered pass criteria (written before any test or code of this entry)

| # | Pass when |
|---|---|
| FI1 | The branch contains canonical and the four heads above. Conflicts are docs only and keep both sides' lines. All four FS1 profiles rebuild byte for byte (`fs1-final.json` `19176e6c…`, `fs1-final-recovery.json` `b8ba06e2…`, `fs1-rehearsal.json` `54802665…`, `fs1-rehearsal-recovery.json` `17ab891d…`). |
| FI2 | Parallel settings: FS1's signed live preparation writes `assessment_workers` 5 and `continuation_rounds` 4 (PL-9), and the FS1 M4 script refuses a package without them. Wallet execution is unchanged (serial). |
| FI3 | FINAL caps review: `review_rehearsal_caps.py --environment FINAL` uses CAP-02's `final` signing policy (hash checked), an execution config with `mode` `live`, and caps-review inputs with `environment` FINAL. It refuses a REHEARSAL profile under FINAL and a FINAL profile under the REHEARSAL default. The default (REHEARSAL) path is unchanged: every existing test passes as it is. |
| FI4 | Fresh final wallet: `ld10_readonly_packet.py --target-wallet 0x…` produces a probe that reads holdings, nonce, allowances and quotes for that wallet, not the installed run's, and marks the holdings `FRESH_TARGET` (no ledger). Without the flag the probe bytes are unchanged (the S4 probe `379c476b…` still rebuilds). The FINAL review with `--fresh-wallet` builds the starting book from the chain only, and refuses: any stock unit above 0 (dust included), a pending nonce, an open router allowance, a packet target other than the bindings' wallet, or a non-FRESH_TARGET packet. |
| FI5 | Q1: `quote_check.py --profile-set FS1 --wallet 0x…` verifies a quote with the FS1 recovery profile `b8ba06e2…` (20 bp) for that wallet. The defaults (run-3 profile, dev wallet) are unchanged. |
| FI6 | F0p: `docs/build/ops/final-fs1/` gets the install scripts, adapted from the run-5 sheet: M1 bundle, D1, M3, M4, P4, checks and `ssm_run.py`. They pin `fs1-final-recovery.json` `b8ba06e2…`, `live`, `aiand_routed`, the routing pair `9b86c732…`, recovery on, FINAL, database `larp_final` and run `larp-final-fs1`. They take the final wallet, the model-adoption reference and the A1 approval reference from required environment variables, and refuse when one is missing. A sheet test checks pins, parsing, and that no run-4/5 identifier remains. |
| FI7 | Full suite: no new failures against canonical in the same environment; exact counts reported. Terraform: `deploy/aws` 21/21, `deploy/bootstrap` 1/1. |

Result states: `supported` if FI1–FI7 pass; `not supported` if FI1–FI5 fail after the work.
Not claimed by any criterion: a host run of the scripts, a real final-wallet capture, or owner approval (A1).

## Results

(none yet)
