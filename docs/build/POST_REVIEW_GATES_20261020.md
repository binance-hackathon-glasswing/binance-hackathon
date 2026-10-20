# Remaining gates after PR199, PR200 and PR201

OG-01, 2026-10-20. Started from canonical `dd30540`; current review base is
`697ff3a` (includes PR202). This is the
follow-up to the merged gas-scope decision, finite execution authority and
delivery-age guard. The live backlog remains [INCOMPLETE_WORK.md](../INCOMPLETE_WORK.md).

| Gate | Repository state | Required next result and owner | Completion evidence |
|---|---|---|---|
| Initial-gas-only scope (LD08) | LD07/DEV-21 decides initial gas only. LD08-OG01 supplies profiles/scope/caps/gates; IG01 adds sourced action budgets, full-book reserve/minimum-cost checks and durable low-gas incident/metric/alarm. Legacy top-up inputs remain historical capabilities. | Keith reviews accounting, Keegan scope/gates; Isaac accepts measured selected-profile/full-exit/action/cleanup values. Operator installs and tests the exact release and alarm delivery. | Source4044c82 full Linux/PG2241 tests/3686 subtests and Terraform19/19 PASS; [acceptance matrix](INITIAL_GAS_ONLY.md). Numeric and host prerequisites below remain separate. |
| Gas, seeding and signer caps (LD09/LD10, #44/#119/#120) | Quote capture and candidate construction are complete. All 3,848 retained swap-gas estimates were FALLBACK, and one exceeds the draft fee cap. | Operator supplies fresh requested-size/full-exit quotes, complete holdings/decimals, fee inclusion and attributable non-fallback approve/swap gas bounds. Isaac proposes exact dev/final gas/reserve/caps; Keith reviews, then Isaac records the accepted hashes. | Full five-name S1 exit reserve at the selected gas-price cap; whole-run trade count and reviewed margin plus exit reserve; pinned profile/policy/raw inputs and signed owner decisions. Historical 35/70-USDT or 0.0002-BNB candidates remain unapproved. |
| Authority values (LD02/LD04, #27) | Option A and final-submission margin checks are merged in PR200. With L/m absent, prior refusals remain. | Operator supplies actual route deadlines and quote/approval/finality/re-quote/estimate/signer/release timings. Keegan chooses finite L and m; Isaac/Keith review economic/session implications. | Per-value provenance for `execution_authority_seconds` and `submission_margin_seconds`; prove `now+m < route_deadline <= A`, and the full sequence fits before signing/session/new-risk bounds. The recorded roughly 500-second route lifetime is an input, not a chosen L; 60 seconds remains illustrative. |
| Delivery/resource values (LD12/LD14) | PR201 implements the optional `delivery_age_halt_seconds` guard and durable rollback refusal. No B is configured. Existing watchdog/memory mechanisms remain. | Operator measures dispatch-to-positive-ACK tails, complete cycle and worker-drain/finality delays, stalled-call behavior, RSS, disk and restart growth. Isaac decides B/watchdog/memory values; Keegan reviews that bounded stages fit. | Named measurement packet and exact config hashes; boundary/partial-ACK/clock/restart tests with chosen values and actual alarm delivery. The historical 2h/600s examples are not adopted values. |
| Exact release (LD15) | Combined code at `2b60387` passed local native ARM64 Linux/PostgreSQL tests: 2194 tests, 3656 subtests, 8 explicit skips. These are test results, not a release artifact. | Keegan qualifies the final selected source/config bytes through the repository's approved build route; operator verifies transferred bundle/manifest/config hashes. | Original exact-source bundle and release manifest; applicable Linux, separate real-systemd, Docker and Terraform checks; signed run/wallet/DB/CA/router-policy bindings and reviewer acceptance. Old `c5be269` receipts do not transfer to changed code. |
| Host/recovery and first signed round | No-standby and restored-run quarantine decisions are recorded in LD13. Historical unsigned host receipts remain historical. | Approved operator with Yao/Isaac supplies isolation/IAM/TLS/time/routes/key-loader/session checks and actual crash/reconciliation/ACK/restore/anchor/final-wallet evidence. Keegan accepts each applicable gate. | Exact release/run/config identities and UTC results for the accepted host/session; agent-generated approve/swap and positive ACK after prerequisites, preserved UNKNOWN/reservations, quarantine on restore, and actual rehearsal record. |
| Organisation CI availability (#98) | Actions jobs did not start because of account payment/spending limits. | Account owner resolves billing or release owner uses the already approved mirror route and retains original artifacts/provenance. | Executed checks and matching source/artifact identities. This PR does not change billing, spend limits, repository permissions or cloud state. |

## Input packet and sequence

Keep raw/private artifacts outside Git. Record public hashes, UTC timestamps,
environment/run/wallet/build identities, source/method, requested amounts and
units, remaining uncertainties, and the named supplier/reviewer decision.
If LD06 allowance recovery is selected, include its bounded zero-approval steps
in the action/whole-run/full-exit gas and timing evidence; five stock pairs
alone do not cover additional cleanup. PR202 is merged; its actual policy/gas/
timing/host acceptance remains separate and is retained alongside initial-only
gas acceptance in assembly reports.
Use the existing [cap reviewer and assembly procedure](GATE_B_REMAINING.md#current-input-signer-cap-review),
[signer preparation](SIGNER_INSTALLATION_PREPARATION.md) and
[rehearsal gates](REHEARSAL_GATES_20261019.md); no second acceptance system is created.

1. Review the completed initial-only repository controls and supply the operator's
   measurements/current inputs. Timing/resource collection and attributable
   pre-signing gas evidence can precede the first signed trade.
2. Record the exact numeric/profile/policy decisions, selected router-policy
   review and applicable provider/fee checks. Numeric coverage does not approve installation.
3. Qualify and verify the exact final release and host configuration, then
   obtain the separately approved signer session/key-placement acceptance.
4. Only then collect the agent's signed approve/swap/ACK and recovery/rehearsal
   evidence. Do not require the first signed receipt as a prerequisite for
   approving its pre-signing safeguards; use attributable pre-signing evidence,
   never guessed FALLBACK values (DEPLOYMENT_BUILD IQ01 / PC-ORDER01).

Nothing here selects a numeric value, enables signing, closes #27/#44/#30,
finalizes a DRAFT deviation, or claims host or scored-run readiness.

Repository verification at `6ba5dc8`: local native ARM64 Linux/PostgreSQL14.24
suite **2228 passed / 8 explicit skips / 3681 subtests**; dependency checks,
deviation rendering and offline demo PASS. The eight skips include the five
separately opt-in real-systemd cases. These results do not qualify a release
artifact or any host gate above. Full evidence: IDEA-061 LD08-OG01.
