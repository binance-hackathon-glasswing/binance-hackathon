# IDEA-042 — Deployment build record: runtime, hosting and integration (Keegan)

- Date / author: 2026-10-11 / Keegan (drafted with Claude)
- Status: open (item 1 in progress; items 2–10 not started)
- What: Keegan's part of the deployment build, prompt [09-runtime-deployment](../build/09-runtime-deployment.prompt.txt) under the common brief [DEPLOYMENT_BUILD.md](../build/DEPLOYMENT_BUILD.md) ([IDEA-038](IDEA-038.md)): reconciled baseline, settlement and execution wiring, official ai-seeds logging, live replay, restart/HALT, hourly anchoring, hosting, release/manifest/deviations, final-wallet switch, integration and the DR checklist evidence.
- Branch: `codex/deploy-runtime`, cut from `codex/deployment-prompts` (`e4ebff6`, the commit that adds the brief; PR #12 still open), with `origin/codex/engine-foundation` (`e8658ba`) merged in by an ordinary merge (`b583059`). Reviewer: Isaac.
- Decisions that govern: [IDEA-035](IDEA-035.md) and [IDEA-037](IDEA-037.md); where main's `a21d034` differs, those govern (IDEA-035 A11).
- Rules: criteria below are committed and pushed before anything they cover runs. Results are PASS, FAIL, NOT RUN or INCONCLUSIVE with the commit SHA. Synthetic results are engineering evidence, not market evidence. No secret, organiser message, signing, wallet use or merge to `main` is part of this record unless a later dated entry says so with the team's authorization.

## 0. Baseline before changes

- 2026-10-11, `e4ebff6` (brief commit, before the base merge), local Python 3.13.16 with disposable PostgreSQL 16, fresh venv from `deploy/requirements-test.lock` (`pip check` clean): **592 passed, 3 skipped, 770 subtests passed**. The 3 skips are the Linux bubblewrap isolation tests (the local sandbox has no bubblewrap). CI runs Python 3.12.15 with PostgreSQL 14.24.
- Found while merging: the base merge of main (`e8658ba`) kept main's `a21d034` plan.md and SKILL.md lines but dropped its GAP-51 sentence ("2026-10-10 team decision: replace the declared depth cap with a price-impact limit …"). Restored in item 1 below; no other `a21d034` line is missing (checked by counting `Decided 2026-10-10` in plan.md, the F-116 receipt note in SKILL.md and the `2026-10-10 team decision` notes in INCOMPLETE_WORK.md against `a21d034`).

## 1. Item 1 — reconciled baseline (due Oct 13)

### 1.1 Prospective criteria (written 2026-10-11, before running anything they cover)

- **B1 · main synced and annotated (A11).** `codex/deploy-runtime` contains `a21d034` through ordinary merges only (no rebase, no force-push). plan.md D-03, D-05, D-11 and D-12, SKILL.md Q-03, and the GAP-51 and GAP-57 lines carry a dated annotation from IDEA-035/037 where they differ from `a21d034`; GAP-51's lost `a21d034` sentence is restored. Check: `git merge-base --is-ancestor a21d034 HEAD`; the annotations are present; `git diff --check` clean.
- **B2 · PR #9 (`codex/integration-tests`).** The base is merged in by a merge commit. C1 passes. C3 is rewritten to exercise the current evidence-to-strategy path on the current golden output and passes. C2 is kept unchanged as the drift check: it is expected to **fail** until Keith re-captures `tests/strategy/fixtures/assessment-producer.json` (prompt 07 item 8), so PR #9 must not merge before that. C4's `expectedFailure` is re-checked against the current code and either kept with a stated reason or replaced by a passing test of the current coordinator path.
- **B3 · PR #10 closed and its parts ported.** PR #10 is closed with a note naming what superseded it (PR #7's `ContextBuilder`/`RuntimePlanner`) and what was ported. Its execution bridge and settlement reducer are ported to `larp/integration/settlement.py` for the projection layout `ledger_from` uses (`portfolio` + `balances` in the projection, reservations in the store), with interface I4's two boundaries:
  1. `BROADCAST_ATTEMPTED` changes only execution state and the round record (the order's `tx_hash`, one `swap_mappings` row per swap); balances, `portfolio` and store reservations are byte-identical before and after.
  2. Only `APPROVAL`, `FILL` and `REVERT` with `settlement: FINAL` change balances and gas, through Keith's `advance_accounting`; `projection.balances` stays equal to the ledger so `ledger_from` accepts the next round.
  3. A terminal `FILL` or `REVERT` releases every remaining store reservation of its intent: USDT, BNB and `INCOMING:<token>` (A9). An `APPROVAL` releases the BNB it spent.
  4. Terminal-round attestation is emitted only when the last intent of a round reaches a terminal final fact.
- **B4 · ports published (I3, I4, I7, I5 interface).** `larp/ports.py` defines one validator per document: `EXECUTION_REQUEST` command payload (I3, including the gas top-up kind of I7), `ExecutionObservation.v1` for both boundaries (I4), and the round-log builder protocol (I5). The producer test calls the validator on real output: `RuntimePlanner` output for I3; the settlement reducer refuses any observation the I4 validator rejects.
- **B5 · regressions on PostgreSQL** (`tests/integration/test_settlement.py`):
  1. SELL (MANDATORY_REDUCTION round from the evidence pipeline harness): broadcast leaves balances and reservations unchanged and maps the hash; a final FILL updates balances by the accounting result, leaves **no reservation row** for the intent, and the round closes with the `tx_hash` in its audit event.
  2. BUY (a planned intent through `RuntimePlanner`): a final FILL and, separately, a final REVERT each leave no USDT, BNB or `INCOMING:` row; REVERT changes only gas.
  3. Replaying the same observation (same event ID, same bytes) is a no-op with the same receipt; the same event ID with changed bytes is refused.
  4. An observation for an intent the round did not plan, a provisional (`settlement` not `FINAL`) fill, and a fill with another wallet's ID are refused and change nothing.
- **B6 · nothing else breaks.** Full suite locally (PostgreSQL) and in Linux CI: every test that passed at the baseline still passes; new tests pass; the only failure allowed on PR #9 is C2 as stated in B2.

### 1.2 Results

NOT RUN at the time of writing (criteria commit).
