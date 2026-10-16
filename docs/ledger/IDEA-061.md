# IDEA-061 — Gas top-up round end to end, and no top-up the service cannot settle (#30 slice)

- Date / owner: 2026-10-16 SGT / built with Claude Code at the team's request. Review: Isaac (C, execution and native settlement), Keith (B, gas accounting), Yao Zhu (D, round logging).
- Status: open (criteria pre-registered; T7–T8 and the fix not run)
- Links: #30 (R08, P1; acceptance 2); IDEA-039 GB-NATIVE (PR #74, native settlement); PR #41 / #66 (`NativeGasQuotePort`, acceptance 1); IDEA-049-D row "#30 R08" (`test_l3_l4_gas_topup_round`); IDEA-049-C C-OPEN-005; GAP-46 (B11 round-log format), GAP-49 (gas operations). Related, not in scope: #56 (no top-up after `new_risk_end`, triaged separately), #46, #54.

## What and why

Issue #30's status comments (2026-10-15 and 2026-10-16) leave five items open. Three need people or decisions and are **not** touched here: the dev-wallet first-gas swap (F-120 process, `DEPLOYMENT_DAY.md` §5), the top-up size and BNB floor (G-28), and whether BNB counts in equity (Q-39). Provider tracing on a real provider (DR02/03) needs a qualified provider. The fifth, "the top-up audit round shown end to end", is code and test work. This entry covers it.

Reading the path for that item found one defect. The execution service maps every `GAS_TOP_UP` command to a native-BNB intent (`map_command` in `larp/execution_live/service.py`), whatever its configuration. But a top-up fill can only be settled through `ChainEvidence.native_receipt`, which refuses unless the execution config sets `native_trace: true` (default false, `config/execution/README.md`). With the default, once the Executor gate is lifted, the service would sign and broadcast a USDT → BNB swap whose finalized receipt it can never turn into an I4 fact: real USDT leaves the wallet, the reservations are never released, the non-terminal execution holds the wallet barrier, and the round never closes. That is the hazard #30 names ("settlement cannot update balances or release reservations"), still reachable by configuration.

## Change

1. `map_command` refuses a `GAS_TOP_UP` command unless the mapping says native settlement is enabled (`native_settlement=True`). The default is refusal. A refused command is never claimed, so nothing is signed; the runtime expires it like any other refused command (#26) and the round logs no order.
2. `build_execution` sets `native_settlement` from the same `native_trace` flag that enables the trace on the RPC, through a small helper so the binding is testable without lifting the Executor gate.
3. A PostgreSQL end-to-end test of one top-up round (below).

Nothing changes in the planner, the gas policy (`larp/risk/gas.py`), the accounting reducer or the audit protocol.

## Pre-registered pass criteria (written before the fix and before T7–T8 exist)

- **T1** The real planner (`plan`, BNB below the floor, one valid gas quote) through `RuntimePlanner` and the Coordinator on disposable PostgreSQL commits one `GAS_TOP_UP` round: its record has `round_kind: GAS_TOP_UP`, the single intent is BNB/BUY, the store holds USDT = cash + fee, BNB = quoted gas and `INCOMING:BNB` = quoted output, and the order amount is the USDT spent (GAP-46 B11).
- **T2** The committed command, read back from the `commands` table, maps through the real `map_command` (with native settlement enabled) to a `GAS_TOP_UP` intent paying USDT and receiving native BNB, with exact input and minimum output in chain units.
- **T3** The broadcast fact records the swap hash on the BNB order without changing balances. The real `final_observation` on a transaction-bound native trace then passes the real `settle`: USDT falls by the pay amount, BNB changes by output − actual gas, no stock moves, `gas_top_up_cash_units` grows by the pay amount, turnover stays 0, every reservation of the intent is released and `ledger_from` accepts the result. The round closes; its one ai-seeds log has `round_kind: GAS_TOP_UP`, orders `[{BNB, BUY, <USDT spent>, <tx_hash>}]` and a gas top-up `cot`; `swap_owners` binds the hash to the round and decision.
- **T4** Replaying the same final fact is a no-op (same receipt, same journal version).
- **T5** An output below the minimum, or a trace bound to another account, never yields a fact (`Blocked`).
- **T6** A final fact naming an unplanned intent, a stock symbol, or a different cash amount is refused and changes nothing.
- **T7 (defect, expected red before the fix)** `map_command` refuses a `GAS_TOP_UP` command when the mapping does not enable native settlement (absent or false), and still maps BSTOCK buys and sells without it.
- **T8 (defect, expected red before the fix)** The execution mapping built from config carries `native_settlement` equal to `native_trace` (true → true; absent or false → false).
- **Regression** The full suite on the branch shows no new failure against the base `7a8a246` run in the same environment.
- **Mutation** Reverting the `map_command` refusal makes T7 fail; reverting the config binding makes T8 fail.

T1–T6 exercise code that already exists. A first draft of them was run once during triage, on the unchanged base, to find out whether the path worked (6 passed, 3 subtests); that run is why they are evidence, not a reproduction. T7–T8 reproduce the defect and have not been run.

## Results

NOT RUN (except the triage run of T1–T6 noted above).
