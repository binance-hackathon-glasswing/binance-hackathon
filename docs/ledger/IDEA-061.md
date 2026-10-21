# IDEA-061 — Gas top-up round end to end, and no top-up the service cannot settle (#30 slice)

- Date / owner: 2026-10-16 SGT / built with Claude Code at the team's request. Review: Isaac (C, execution and native settlement), Keith (B, gas accounting), Yao Zhu (D, round logging).
- Status: built (T1–T8 PASS on disposable PostgreSQL 16; full local suite PASS; owners' review open; #30 stays open)
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

## Results (2026-10-16, Linux, venv `/opt/larp-venv`, disposable PostgreSQL 16)

- Branch `claude/issue-30-gas-replenishment` from base `7a8a246` (`codex/system-testing-20261012`). Criteria committed at `d7a7f0a` before the T7–T8 tests and the fix.
- **Red** at `f68d319` (tests only): `tests/integration/test_gas_top_up_round.py` **9 failed, 1 passed**. T7 failed on both subtests with "Blocked not raised": `map_command` mapped a `GAS_TOP_UP` command with native settlement absent or false. That is the defect. T8 failed on `ImportError` (no `execution_mapping`). T2–T6 failed on `TypeError` (no `native_settlement` argument yet). T1 passed.
- **Fix** at `7c55448`: `larp/execution_live/service.py` (`map_command` refusal), `larp/execution_live/main.py` (`execution_mapping`, used by `build_execution`), `config/execution/README.md` (one paragraph). Two existing tests that map a top-up now pass `native_settlement=True`: `tests/risk/test_b_regressions.py` (scale check) and `tests/execution/test_review_fixes.py` (which also asserts the refusal without it).
- **Green:** T1–T8 **8 passed, 10 subtests**; with the two edited test files and `test_live_boundaries.py`: 64 passed, 16 subtests.
- **Mutation:** disabling the `map_command` refusal makes T7 (both subtests) and `test_gas_accounting_units_convert_to_native_chain_units` fail (3 failed); binding `native_settlement=True` whatever the config makes T8 fail (`native_trace` absent and false). Both files restored from the commit afterwards.
- **Full suite** `python -m pytest -q -p no:cacheprovider`: branch **1554 passed, 7 skipped, 2157 subtests passed, 0 failed** (315 s). Base `7a8a246`, same environment, run from an exported copy outside any repository: 1544 passed, 2 failed, 7 skipped, 2147 subtests passed (356 s). Both base failures need a repository checkout (`test_deploy_presetup ...ignored_directory`, `test_final_review_d ...no_credentials_are_tracked`) and pass on the branch. 1546 + 8 new tests = 1554; subtests +10.
- Not covered: `build_execution` is not exercised past the Executor capability gate, so the test checks `execution_mapping`, not that `build_execution` calls it (it does, by reading). No provider, signing, broadcast or real chain data.

## Still open for #30 (not in this entry)

- Dev-wallet first-gas swap by a team member (F-120, `DEPLOYMENT_DAY.md` §5).
- Native tracing qualified on a real provider (DR02/03, IDEA-039). Until then `native_trace` stays false and every top-up command is refused.
- Top-up size and BNB floor (G-28); whether BNB counts in equity (Q-39).
- #56 (no top-up after `new_risk_end`) is handled separately.

## LD07 — gas scope decision for v1 (Keegan, 2026-10-20)

**Decision: initial-gas-only operation for v1.** The agent plans no gas top-up
rounds. The only BNB source is the F-120 first-gas swap (MetaMask, gas paid in
USDT), which must happen before each wallet's first agent trade. Native top-ups
are not adopted.

Why, from the current record:
- **Native top-ups can't be qualified in time.** The untrusted-router decoder
  (IDEA-070 B02-U) rejects native-BNB routes. A native route decoder, an
  approved trace-capable provider and real transaction-bound native proof
  (#30; checklist B04/B05) don't exist yet.
- **First gas is already sized for the whole run** (SKILL.md F-120 sizing
  POLICY, 2026-10-16). Top-ups were only ever a backup.
- **The planner already protects the exit reserve:** buys that would cut into
  `exit_gas_reserve_units` are refused, and any unaffordable action is refused
  (`INSUFFICIENT_GAS`).

**What this gives up:** after a wallet's first agent trade, no human may add
BNB (F-114, F-120). If gas runs out, the agent can no longer trade at all,
including exits and the final flatten. The reserve and the seeding size are
therefore safety values, not cost estimates.

**Acceptance requirements for LD08 (Isaac implements; Keith reviews
accounting, Keegan reviews policy and gates):**
1. **No top-ups:** the planner plans no `GAS_TOP_UP` intent in v1, and the
   mapping and signer refuse one: native BNB is not an allowed receive token.
   Tests prove both.
2. **Exit reserve:** `exit_gas_reserve_units` covers a full exit of the
   largest permitted book (S1: five approve+swap pairs) at the measured gas
   limit and the cap gas price, from LD09's real approve/swap gas, not the
   fallback estimates.
3. **Seeding size:** dev and final first-gas amounts are computed from LD09's
   measured per-trade gas × the planned whole-run trade count × a reviewed
   margin, plus the exit reserve. They're recorded in the funding notes before
   the swap.
4. **Low-gas behaviour, tested:** below the reserve, no new buys while
   reductions and exits continue. When even one pair is unaffordable, a
   journaled incident and an alarm fire. No human top-up is ever expected.
5. **Gates:** caps (#44), Gate B and the signer assembly stop requiring top-up
   coverage for v1. #30's native top-up acceptance stays open and unclaimed.
   DEV-21 declares the scope.
6. **Final wallet:** its first gas follows the same sizing before Oct 29
   00:00 UTC (LD23).

Not decided here: the numeric reserve, seeding amounts and alarm threshold.
They follow LD09's measurements, with Isaac's #44 acceptance (LD10).

### LD07-RV01 — PR 199 review (2026-10-20)

Reviewed `2723b5e` against integration `06a93f9`: no blocking defect in this
decision/register slice. `render_deviations --check` and whitespace checks PASS;
Linux Python 3.12.15 with disposable PostgreSQL 14.24: release-register and
final-review-D tests **39 passed, 34 subtests**. GitHub Actions did not start
because of account billing/spending limits; this is local evidence only.
LD08 implementation, measured LD09 gas/reserve/seeding values and #44/host
acceptance remain open. This review does not enable signing or top-ups.

## LD08-OG01 — initial-only repository controls (2026-10-20, prospective)

Follow-up requested after PR199–201. Base `dd30540`; gate closure sequence and
owners: [OG-01](../build/POST_REVIEW_GATES_20261020.md). This slice introduces
explicit initial-only candidate profiles while retaining historical top-up
fixtures. No numeric reserve/seeding/cap/L/m/B or installation is adopted.

Pass criteria before running added code:
- An explicit initial-only profile neither plans nor requests a native top-up,
  including with low/zero BNB. Affordable mandatory exits still proceed below
  the reserve; new buys cannot consume it.
- Mapping refuses a top-up under that profile even if native tracing is on.
  The independent signer policy excludes native BNB and refuses top-up approve
  and swap requests before signing.
- Initial-only LIVE profile validation does not require top-up sizing fields;
  existing exit-reserve and per-value-provenance checks remain mandatory.
- Cap coverage requires all stock BUY/SELL pairs and full holdings/fees but no
  native quote or top-up input. Supplying a native quote or a native-enabled
  policy for initial-only scope refuses. Assembly retains false readiness and
  explicit reserve/seeding/route/host acceptance gates.
- Legacy profile/top-up and current cap/assembly tests remain valid. Run focused
  regressions and the full disposable Linux/PostgreSQL suite on pushed code.

LD08 low-gas incident/alarm and actual selected-profile/full-exit host acceptance,
LD09 measurements and #44 decisions remain open unless separately evidenced.

LD08-OG01 implementation at `048e414`: opt-in `initial_gas_only: true`
candidates have no top-up sizing fields and retain the existing exit reserve.
The planner emits no native quote/intent; execution mapping binds the pinned
profile's scope and refuses native top-ups even with tracing enabled. Candidate
signer policies exclude native BNB. Cap review/assembly require stock-only
coverage, reject native-enabled policy/quote inputs and retain false readiness.
Gate B reports measured whole-run seeding/reserve/low-gas acceptance as missing.
Historical profile/top-up behavior remains available for historical inputs.

Focused native ARM64 Linux/Python3.12.15/disposable PostgreSQL14.24 checks:
**108 passed, 129 subtests**, zero skips. New checks cover zero/low gas,
affordable mandatory exits, S1/four-name reserves, contradictory/malformed or
unsourced scope, native mapping and independent policy refusal, exact cap
boundaries, assembly and both funded/missing initial-only Gate B reporting.
No current measurement, numeric adoption, low-gas incident/alarm or hosted
acceptance is claimed. Full-suite results follow after the pushed-code run.

First full run at `84e6d57`: **2204 passed, 8 skipped, 3656 subtests**, 234.69 s;
dependency checks, deviations rendering and offline demo PASS. While it ran,
PR202 merged as canonical `697ff3a`. Merge `993d6b4` retains both initial-only
coverage and LD06 allowance-recovery opt-in/mismatch checks and acceptance
gates; backlog/Gate B conflicts retain both scopes. Before rerunning, add a
combined initial-only/untrusted/allowance-recovery assembly case proving both
gas/host gates remain and a config/policy opt-in mismatch refuses. Any selected
cleanup steps need their own measured reserve/seeding/timing coverage.

Final combined verification at `6ba5dc8`, including canonical `697ff3a`:
native ARM64 Linux / Python3.12.15 / disposable PostgreSQL14.24, **2228 passed,
8 skipped, 3681 subtests**, 236.91 s. The 8 skips are two external/private
fixtures, one root-only directory-mode check and five separately opt-in real
systemd checks. Combined initial-only/allowance configuration selection:
21 tests / 3 subtests PASS. `pip check`, deviation rendering, offline runtime
demo and whitespace checks PASS; 20 local documentation link targets resolve.
These are local tests, not hosted CI, an original release artifact or actual
host/signing acceptance. No gate requiring measurements or a named decision
is closed. Low-gas incident/alarm work and selected-profile qualification stay
in the live backlog; legacy top-up capability is not adopted for v1.

Delivery: [PR203](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/203),
branch `codex/post-review-gates-20261020` into canonical integration. Opened for
review at the user's request; no merge, numeric owner acceptance, installation
or cloud/wallet operation is requested or claimed.

## LD08-IG01 — complete initial-only low-gas controls (Isaac, 2026-10-20; prospective)

User requests LD08 completion. Branch from canonical `697ff3a`, incorporating
PR203 `a959fe2` by normal merge; PR203's branch is not edited. Scope is repository
implementation and offline qualification. No host/provider/key/funding action.

Pass criteria, before new regressions or implementation run:

- IG1: initial-only profiles require a positive, sourced `gas_action_budget_units`,
  at least the summary's worst approve+swap pair and no larger than the full exit
  reserve. Candidate generation derives the pair budget; additional selected
  cleanup requires measured coverage in that budget/reserve (LD09/LD10).
- IG2: after reconciliation and before planning, compare spendable settled BNB
  against the action budget and exit reserve. Equality funds an action; below the
  budget records `PAIR_UNAFFORDABLE`; below only the reserve records
  `BELOW_EXIT_RESERVE`. Existing buy refusal and affordable reductions/exits stay.
- IG3: journal a transition incident plus durable gas-health state atomically,
  without changing balances, reservations, authority, quarantine or HALT. Repeated
  ticks and restart do not duplicate incidents. Recovery is a new recorded fact;
  backward clocks cannot clear a warning. Journal replay reproduces exact bytes.
- IG4: do not commit a gas incident over an unclaimed command or any in-flight
  execution/reservation/open round. Observe at the next quiet driver boundary;
  prove command version/nonce barriers remain intact.
- IG5: archive-role service health exposes the durable unaffordable-action signal;
  publish a dedicated CloudWatch metric and define a missing-data-breaching alarm
  through the existing authorized destinations. Exercise publisher failure and
  recovery with synthetic clients; Terraform tests require no AWS apply.
- IG6: production driver construction wires the monitor from the pinned profile;
  historical top-up profiles keep their existing behavior and metrics default
  healthy when this scope is absent. No native route or new spending is enabled.
- IG7: pushed regressions run red before repair, then focused Linux/PostgreSQL
  and complete suite plus applicable Terraform/bundle/replay checks pass. Record
  exact source/results/skips; do not rewrite existing measurements or goldens.
- IG8: narrow the live backlog to measured gas/cleanup/full-exit reserve, dev/final
  whole-run seeding, exact #44 decisions and actual alarm/host acceptance. Keith
  reviews accounting and Keegan policy/gates; candidate formulas and offline
  tests do not constitute their approval or complete those external gates.

Red evidence: `37a8ad8` had four missing-feature failures and eight fixture
uniqueness failures (the harness already owns wallet `wallet`). Isolated the
new fixture's wallet at pushed `4d8a8e8`; all **12 tests fail** on the missing
budget/monitor/driver support, Linux Python3.12/PostgreSQL14.24, 0.56s. No
application repair was present in either run.

IG1 full-book refinement before the next run: a larger selected action budget
(e.g. measured cleanup) must also increase the full-exit reserve to cover four
actions, or five for S1. A pair-only reserve cannot silently cover a larger
declared action. Add this refusal to the pushed profile regression before repair.

At `90e825a` the new full-book assertion fails (`ContractError not raised`).
Repair also applies the larger action budget to the existing minimum-trade
cost bound; otherwise cleanup could be omitted from that same economic check.

### LD08-IG01 results — source `4044c82` (2026-10-20 UTC)

IG1–IG6 repository behavior is implemented and verified. Initial-only profiles
carry a positive sourced action budget; full-book reserve and minimum-trade
cost checks include the whole budget, including reviewed cleanup when selected.
The monitor runs after balance reconciliation at a quiet driver boundary,
records atomic `LOW_GAS`/`LOW_GAS_CLEARED` incidents plus durable gas health,
does not duplicate them after restart, and refuses a backward-clock clear.
It preserves financial state/HALT/authority and defers for reservations, open
rounds and pending execution. Planner/executor gas checks remain independent;
affordable mandatory exits are still exercised by the initial-only regressions.
The archive health path and CloudWatch publisher expose `GasPairUnaffordable`;
the existing Terraform notification destinations receive the configured alarm.
Actual installation/notification delivery is not claimed.

IG7 PASS: pushed application/test source
`4044c82a3b843d2781f4ac96e29bebf63d7497ac`, Linux Python3.12.15/disposable
PostgreSQL14.24, **2241 passed, 8 skipped, 3686 subtests**, 133.91s. Full log
`/private/tmp/larp-ld08-full.log`, SHA-256
`8b23977b4e4427742f57e27eae7a8e2a8be2b18e41d24eb1606ebe6b8addcfea`.
Eight skips: two external/private fixtures, five opt-in actual-systemd cases
(unrun here), and the root directory-permission case. Separately UID1000:
six startup tests PASS, including that permission case; three PostgreSQL cases
skipped in that separate command are covered by the full run.

Terraform1.13.5/locked AWS6.61.0: fmt/validate and **19 mocked plan tests PASS**,
including low-gas metric/threshold and missing-data behavior. No apply. Log
`/private/tmp/larp-ld08-terraform.log`, SHA-256
`00cf8b85d2b553be5be9dab454aacf5613b6067f4db0922d4f87de5a8332d9e5`.
Dependency checks, deviation rendering, full-suite bundle/manifest regressions
and offline PostgreSQL/bubblewrap demo (six batches/two audit chunks) PASS.
This does not qualify an original signed release artifact or actual host.

IG8: the live backlog is narrowed, not removed: Keith/operator supplies measured
gas/cleanup/current quotes/full holdings; Isaac accepts exact action/reserve/
whole-run dev/final seeding/#44 hashes after Keith/Keegan review; Keegan/operator
qualifies the exact release and actual alarm/host/selected-profile exits.
[Acceptance matrix](../build/INITIAL_GAS_ONLY.md) and
[machine receipt](../build/evidence/ld08-initial-gas-20261020.json) preserve
criteria, evidence and owners. No secrets, live RPC, funding, key, signing or
deployment action was performed. No readiness flag is enabled.

Delivery (2026-10-21 SGT / Oct20 UTC):
[PR207](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/207)
targets canonical and includes PR203 by normal merge. Independent Keith
accounting / Keegan policy-and-gates review remains requested by the ownership
plan; no review or merge is inferred. PR203's author branch is unchanged.
After documentation changes at `256b08f`, focused gas/operations/signer assembly/
mode-readiness checks: **44 passed /23 subtests**, zero skips; **27** local
documentation targets resolve. Application/test/deployment bytes remain exactly
the full-suite source `4044c82`. Canonical remains `697ff3a`; main and origin/main
both `fb95114`. All session work is committed/pushed on the task branch; the
original checkout is untouched. The task's isolated PostgreSQL is removed after
verification. Numeric/measurement/release/host/independent-review items above
remain explicitly open; this is a repository delivery, not installed acceptance.

GitHub run [39454047109](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/39454047109)
at `9786bea` executed **zero steps across all four jobs**. Its annotation says
account payments failed or the spending limit must be increased. This is the
existing account-owner CI availability blocker, not an executed test failure;
local verification above is not presented as hosted CI or release acceptance.

### LD08-IG01-RV01 — PR207 code-review fixes (2026-10-20 UTC)

Review of PR207 head `808b531` found nine items. Eight are fixed in `7f004f7`:
the gas monitor returns `SKIPPED` instead of raising out of the driver tick; top-up
profiles install `RetiredGasCheck`, which journals one `LOW_GAS_CLEARED`
(`NOT_MONITORED`) so a stale `GasPairUnaffordable` cannot stay raised; the check
runs every 60 s and after each balance reconciliation, not every tick; the caps
review (`INITIAL_BNB_EXIT_RESERVE`) and Gate B DR-06 refuse starting BNB below the
full-exit reserve; the action-budget provenance cites IDEA-061 LD07/LD08; top-up
profiles refuse `gas_action_budget_units`; the duplicate reserve comparison is
removed; signer assembly reuses the review's `gas_scope`.

Not applied: journaling a low-gas transition while a reservation, open round or
pending execution exists. That would break the quiet-boundary barrier this PR
keeps on purpose. An alarm during an in-flight attempt needs a signal outside the
journal; the owner decides (Isaac, with Keegan review).

PR133 PF-06 (PR209, open) chooses a full bounded-action reservation with 20%
gas-limit headroom, and approves no number without LD09 measurements. PR207 keeps
`gas_action_budget_units` a sourced input, so that rule is applied when Keith's
measurements and Isaac's acceptance supply the value; no headroom is hard-coded.

Local verification, source `7f004f7`, Linux/Python 3.13.16/PostgreSQL 16.15:
**2243 passed /11 skipped /3686 subtests**, no failures. The unchanged PR head
`808b531` in the same environment: 2238 passed /11 skipped /3686 subtests. The five
new tests account for the difference. Hosted CI still runs zero steps because of
the organisation's Actions billing block (PR133); this is local evidence, not
hosted CI or release acceptance.

## LD09-G1 — measured gas budget proposal (2026-10-21, proposal only)

[LD09_GAS_BUDGET_PROPOSAL_20261021.md](../build/LD09_GAS_BUDGET_PROPOSAL_20261021.md) computes the initial-only gas
values from simulated gas (IDEA-070 LD02b/F1/LD02c): pair gas 803,768 (approve 55,243 + BUY swap 748,525), 25 %
headroom. At the draft cap price (0.16 gwei) G = 160,753,600,000,000 wei and the EW/S1 exit reserves are
6.43e14 / 8.04e14 wei, but the profile's shared use of G for minimum-trade economics raises the minimum trade to
37.45 USDT (27.00 without MSFTB), which refuses the 100-USDT rehearsal profile. Options A (one lower price, about
0.08 gwei), B (decouple reserve price from sizing price; recommended) and C (exclude MSFTB, currently unexecutable)
are laid out with a seeding table. No profile, cap or config changed; Keith, Isaac and Keegan decide.

LD09-G1 revision 2 (2026-10-21, after IDEA-070 LD02d): the maximum swap gas is now 944,814 (TSLAB BUY; SELL max
930,548), so pair gas is 1,000,057. At 0.16 gwei G = 200,011,400,000,000 wei, the reserves are 8.00e14 / 1.00e15 wei,
and the minimum trade is 46.60 USDT (33.60 without MSFTB). That refuses both the rehearsal (20 USDT) and the final
(40 USDT) positions. Option A now needs a budget price of at most about 0.064 gwei. Option B (decouple) stays
recommended. The 1.25× headroom swap limit (1,181,018) is 1.6 % under the draft `max_gas`; this is flagged for
Isaac (LD10).

## LD09-B — decision B adopted and its implementation (2026-10-21; prospective)

**Decision (Keegan, 2026-10-21):** LD09-G1 option B. The exit reserve and the action budget stay at the signer's cap
gas price. Minimum-trade sizing uses a separate, sourced pair budget at an expected gas price. Values from the
LD09-G1 revision 2 inputs (IDEA-070 LD02d maximum, pair gas 1,000,057, 25 % headroom):

- action budget at 0.16 gwei (draft `max_gas_price`): `gas_action_budget_units` = 200,011,400,000,000 wei;
- sizing budget at 0.064 gwei: `gas_sizing_budget_units` = 80,004,560,000,000 wei. 0.064 gwei is the observed
  0.05 gwei rounded above the interim capture's 0.053–0.062 gwei range. It is also the highest price at which the
  20-USDT rehearsal position fits with DC-01's MSFTB spread. Keith can replace it with a measured value for #120.

**Pass criteria, written before the code (B1–B6):**

- B1. `validate_live` accepts an optional `gas_sizing_budget_units` only on initial-only profiles. It must be a
  positive integer with provenance, at least the quote summary's measured pair and at most `gas_action_budget_units`.
  Otherwise the profile is refused.
- B2. With the sizing budget present, minimum-trade feasibility uses it. The exit-reserve check (4×, S1 5×) still
  uses `gas_action_budget_units`, and so do `InitialGasCheck` and the planner's reserve. Without it, behaviour is
  unchanged: the existing tests pass and the committed DC-01 and LD04-P candidates reproduce byte for byte.
- B3. `build_live_profiles(..., gas_budget={action_units, sizing_units, decision_id, data_hash})` is allowed only
  with `initial_gas_only`. It sets both budgets and a reserve of 4× (S1 5×) the action budget, and computes the
  minimum trade from the sizing budget. The CLI flags `--gas-action-budget-units`, `--gas-sizing-budget-units`,
  `--gas-budget-decision` and `--gas-budget-evidence` must be supplied together.
- B4. Candidates rebuilt from the committed DC-01 summary with initial-only scope, L = 660 / m = 30 and the B values
  build and validate for both environments. Expected values: minimum trade about 18.64 USDT, EW reserve
  800,045,600,000,000 wei. Their hashes are recorded, and they are evidence candidates only.
- B5. Tests cover B1–B3: refusals, unchanged behaviour without the key, and the reserve still using the action budget.
- B6. The full suite passes.

### LD09-B results — implementation `f4fde3a` (2026-10-21)

- **B1 PASS.** `validate_live` accepts `gas_sizing_budget_units` only on initial-only profiles, sourced, with
  summary pair ≤ sizing ≤ action. Top-up profiles, out-of-range values, zero and unsourced values are refused.
- **B2 PASS.** The minimum trade uses the sizing budget. The reserve check still uses the action budget
  (4 × action − 1 is refused). Removing the sizing key restores the coupled check, which then refuses the 20-USDT
  rehearsal minimum. The committed DC-01 and LD04-P candidates reproduce byte for byte. `InitialGasCheck` and the
  planner are unchanged: they read the action budget and the reserve.
- **B3 PASS.** `build_live_profiles(gas_budget=...)` and the four CLI flags. They need initial-only scope and must
  all be supplied together; provenance carries the decision and the evidence hash.
- **B4 PASS.** [Candidates](../build/evidence/ld09b-gas-budget-profiles-20261021/README.md): rehearsal
  `54eb6fba…6f2ea4` and final `07e8e8c9…a542` (StrategyProfile.v1). Minimum trade 18,637,420 (18.64 USDT), reserve
  800,045,600,000,000 wei, action 200,011,400,000,000 wei, sizing 80,004,560,000,000 wei. They reproduce byte for
  byte in tests. These are evidence candidates only.
- **B5 PASS.** `tests/strategy/test_gas_budget_b.py`: 11 tests.
- **B6 PASS.** Full suite on Linux, Python 3.12, local PostgreSQL 16: 2304 passed, 11 skipped, 3748 subtests passed.

Still open: Keith's #120 review (the expected price of 0.064 gwei, a refreshed MSFTB spread, the S1 or fallback
profile and calendar), the #119 fee evidence, Isaac's #44 caps (including the 1.6 % `max_gas` margin), seeding N
and selected cleanup gas.

## LD09-B-RV01 — Isaac review of PR216 (2026-10-21; prospective)

User requests review/fixes/merge of PR216 and delegates #44 approval wherever
the evidence supports it. Original head6c04f1b; canonical2cd1551. Normal merge
resolves the backlog conflict by preserving both the B candidates and PR215's
measurement caveats; no historical evidence bytes are changed.

Pass criteria before execution: RV1 inspect validator/builder/CLI and consumers
of action, sizing and reserve values; RV2 verify missing/partial/invalid budgets,
provenance, legacy reproduction and S1 reserve behavior; RV3 exercise actual gas
monitor/planner/caps contracts so the smaller sizing budget cannot lower funded
action/exit requirements; RV4 independently reproduce archived candidates and
check measured gas/raw quote amounts against proposed #44 limits; RV5 run
focused checks and full local suite on pushed source with real disposable
PostgreSQL and mocked external boundaries; RV6 approve only exact reviewed
head, merge and update canonical/PR133; RV7 record a separate exact-policy #44
decision where supported, preserving missing actual selected-profile/current-
holdings/config/release/host facts. Numeric ceiling approval is not a claim
that every future holding can exit in one capped action, installation or
authorization to trade. No live/provider/model/host/key/funding action.

### LD09-B-RV01 verified result

Pushed executable/test source3e73086 passes full macOS arm64/Python3.12.14 /
disposable PostgreSQL14.24: **2323 tests /3748 subtests /10 explained skips**,
zero failures,355.52s. Skips:2 external fixtures,5 systemd,3 Linux bubblewrap.
Focused split-budget/policy/caps/monitor/planner suite:70 tests/44 subtests/
zero skips. Deviation rendering and whitespace pass. No blocking feature-code
defect found; added consumer tests cover S1's five-action reserve/monitor and
the actual planner's funded-reserve barrier. DC01/LD04/LD09-B candidate JSONs
reproduce byte-identically. [Receipt](../build/evidence/pr216-review-20261021.json).

The proposal's action budget remains unapproved for deployment: separately
rounded observed child gas limits plus25% cost200,011,520,000,000wei at0.16gwei,
120,000,000wei above its recorded fractional-pair budget; two max-gas children
cost384,000,000,000,000wei. Caller-supplied budgets support larger values, but
exact selected signed children/cleanup/exit count and whole-run N require real
coverage before adoption. Numeric signer ceilings are approved under CAP-02,
not a claim of actual profile/complete-holdings/gas coverage or installation.

LD09-B-RV01 delivery: PR216 APPROVED/MERGED at657efd3 on
2026-10-21T06:59:09Z, exact reviewed head6367a15. Only docs changed after
tested source3e73086. Actions39558766897 executed zero steps because account
payments/spending limits blocked startup. Canonical status/plan, #44 and PR133
record CAP-02 approved numeric ceilings plus remaining deployment coverage;
local test container stopped. No installed release or signed-host acceptance.

## GE-01 — LD08/LD10 exact configured gas-envelope coverage (2026-10-21; prospective)

Isaac requests completion of the next LD08/LD10 work. Canonical146a751 includes
PR216 sizing split, CAP-02 ceilings and PR222 fault hooks. No implementation PR
is open. Selected actual profile/fresh holdings/quotes/whole-run N are not in
the retained packet; request local paths while completing repository checks.

Pass criteria before execution:
- GE1 compute an integer wei bound for every allowed action: approve+swap,
  plus all six possible zero-approval cleanup steps when explicitly enabled;
  no transaction is assumed to get the observed mean/quoted gas rather than its
  configured maximum. Independently rounded measured limits remain diagnostics.
- GE2 initial-only caps coverage rejects execution parent budgets below this
  envelope, profile action budgets below the configured parent and nominal
  position reserves below the larger action budget. Expected sizing cannot mask
  a deficit. Keep top-up behavior unchanged, exact wei/scales and false readiness.
- GE3 an offline non-overwriting proposal tool emits input hashes, concrete
  recommended action/reserve values and optional explicit N/margin seeding math;
  no private raw fields, host/key/network/signing/funding side effects or invented
  action count. It is a proposal, not a deployment acceptance or selected profile.
- GE4 exact/+1, per-child rounding, disabled/enabled cleanup, S1/four-name,
  action/profile mismatches, scale/type and output privacy/non-overwrite tests;
  exercise existing actual caps-review/assembler boundaries, then appropriate
  broader checks on pushed code. Preserve historical candidate bytes.
- GE5 retain measured results, reduce live checklist to actual remaining inputs,
  commit/push, prepare a reviewable canonical-based PR and update PR133.

Numeric CAP-02 policy approval remains in force, with cleanup disabled. This
change never installs policies, approves current holdings or substitutes a local
scenario for Keith's selected S1/fallback/exit-child counts and whole-run N.

GE-01 STOPPED at Isaac's explicit direction (2026-10-21): the missing actual
selected-profile/full-exit/fee/N work belongs to Keith under LD09/#119/#120.
PR218 only supplies historical DC-01 reproduction, not those current inputs;
#119/#120 remain open without newer acceptance comments. Do not complete another
owner's packet or keep pursuing this dependency-bound task.

The unmerged prototype reproduced action/profile envelope false positives in
the numeric reviewer. Initial subset:26 passed/39 subtests,1 cleanup-fixture
failure (cleanup enabled after the fixture's budget was set). Prototype is NOT
accepted or released. Normal revert commits remove all GE-01 application/test
changes; no canonical/runtime/config/host change occurred and no PR was opened.
Keep the audit trail on codex/ld08-ld10-gas-envelope-20261021 for later review
when real inputs arrive. Isaac's next independent task is IDEA-070 KG-DEC-01
pre-sign swap simulation, based on fresh canonical rather than this worktree.
