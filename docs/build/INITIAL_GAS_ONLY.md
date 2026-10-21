# Initial-only gas implementation and acceptance — LD08-IG01

2026-10-20. Based on canonical `697ff3a`, with PR203 `a959fe2` incorporated by
normal merge. Application/test source `4044c82` implements the repository part
of LD08. Measurements and owner/host acceptance below remain open; no wallet,
provider, funding, key, installation or AWS apply occurs here.

| LD07 requirement | Repository result | Remaining acceptance / owner |
|---|---|---|
| No top-ups | Explicit initial-only profiles omit top-up fields; planner, mapping and independent signer reject native top-ups; stock-only caps/assembly/Gate B retain other gates. | Keegan reviews integrated scope; exact installed profile/config/policy must select it. |
| Full-exit reserve | A sourced positive `gas_action_budget_units` covers at least the largest summary approve+swap pair. Reserve covers four action budgets, or five for S1. Without `gas_sizing_budget_units`, the action budget also sets minimum-trade gas cost feasibility. With it (LD09-B, decided 2026-10-21), the reserve and the low-gas monitor keep the cap-price action budget, and the minimum trade uses the sourced expected-price sizing budget, which must lie between the summary pair and the action budget. | Keith/operator supplies attributable non-fallback gas at the accepted gas-price cap, including selected cleanup; Isaac accepts exact budget/reserve/profile hashes under #44. |
| Whole-run seeding | Candidate construction keeps seeding/measurement gates open. | Keith/operator supplies dev/final planned action counts and margin; Isaac reviews computed seeding and funding notes. No numeric amount is adopted here. |
| Low-gas behavior | Buys preserve the reserve; affordable reductions/exits continue. `InitialGasCheck` journals transition incidents and persistent gas health. Archive health publishes `GasPairUnaffordable`; Terraform defines `runtime-low-gas`, with missing data breaching and existing notification destinations. | Operator verifies actual deployment, metric/alarm notification delivery and selected-profile execution behavior. |
| Caps and gates | Initial-only stock coverage removes native top-up requirements while retaining ordinary canonical/gas/receipt, lifetime, release and host gates. Reports keep readiness/signing false. | Isaac exact #44 acceptance; Keith accounting and Keegan policy/gates review. #30 native top-ups remain unqualified. |
| Final-wallet first gas | Same measured sizing method as development, separately bound to the final wallet. | LD23 account owner/operator/Isaac handoff; actual final funding notes and post-funding holdings. |

## Gas state and execution boundary

The monitor runs after the driver's balance-reconciliation step and before new
work. It uses the journaled settled ledger less recorded chain deficits, checks
the BNB scale against the pinned profile and changes no financial state. It
defers while a command awaits claim, a reservation/open round exists, or an
execution remains pending. This avoids changing a command's journal version
during I3 hand-off or treating gas held by uncertainty as free resources.

- Below the full-exit reserve: `BELOW_EXIT_RESERVE`.
- Below the action budget: `PAIR_UNAFFORDABLE`, with the dedicated alarm signal.
- Equality with the budget funds that budget; equality with the reserve is `OK`.

Transitions commit `INCIDENT` and `projection.gas_health` atomically. Repeated
ticks/restarts do not duplicate them. A recovered `OK` records `LOW_GAS_CLEARED`;
a backward clock cannot clear a warning. No global HALT or automatic funding is
added. The planner and execution service retain independent per-action gas
checks, so a warning never grants permission or promises an exit will execute.
The stored state describes the last transition, not a continuous balance feed.
The check runs at most once a minute and after every balance reconciliation; a
ledger it cannot read is `SKIPPED` and never stops the round or exits.
Historical top-up profiles do not install this monitor and publish zero for its
signal: their driver journals one `LOW_GAS_CLEARED` (`NOT_MONITORED`) if an
earlier initial-only profile left the alarm raised. The caps review and Gate B
DR-06 refuse a starting native balance below the full-exit reserve, since no
top-up can restore it. No selected production profile or readiness flag is changed.

## Measured packet still needed

Use the existing LD09/LD10 and `GateBCapsInputs.v1` handoff; do not substitute
FALLBACK quote gas or example caps. Supply private raw artifacts and public
hashes/provenance for approve/swap limits, gas-price cap, selected zero-approval
cleanup steps, requested-size/full-exit quotes and fresh complete holdings.

Let `G` be the accepted upper action gas budget, including all selected supporting
steps; reserve `R` must cover the largest allowed book. For each environment,
review the planned non-terminal action count `N` and rational margin `a/b` before
computing whole-run seeding as `ceil(N * G * a / b) + R`. Count planned failures
and retries, and do not omit cleanup. This is a calculation recipe, not adopted
values or a funding instruction. Record inputs, hashes, formulas and the named
review before any final candidate/release is accepted.

## Verification

At pushed source `4044c82a3b843d2781f4ac96e29bebf63d7497ac`, Linux Python3.12.15
and disposable PostgreSQL14.24: **2241 passed, 8 skipped, 3686 subtests**, 133.91s.
Skips: two external/private fixtures, five opt-in real-systemd checks, one root
directory-permission case. That permission case passes separately at UID1000
(six startup tests pass; three PostgreSQL cases skipped there were covered by
the full run). Real-systemd and external-fixture cases remain unrun here.

Terraform1.13.5 / locked AWS provider6.61.0: format, validate and **19 mocked
plan tests PASS**, including dedicated alarm/missing-data checks. No apply.
Dependency locks, deviation rendering, offline PostgreSQL/bubblewrap demo
(six journal batches/two audit chunks) and full-suite packaging/manifest tests
PASS. No original qualified signed bundle or actual host proof is claimed.
[Machine receipt](evidence/ld08-initial-gas-20261020.json).
