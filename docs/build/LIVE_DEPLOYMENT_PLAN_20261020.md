# API-trusted router: live deployment plan — LIVE-PLAN01

Updated 2026-10-20 SGT. Build base/target: `codex/system-testing-20261012`.
PR133 is the noticeboard, not a build branch. B09-TRUST01 and this plan are
submitted in PR196; until merged, canonical does not contain these updates.
The [live backlog](../INCOMPLETE_WORK.md) remains authoritative for outstanding
GAP items. This plan orders that work; it does not create another implementation
branch or certify a deployment. Historical results retain their exact identities.

## Accepted direction and boundaries

Isaac accepts that the contract returned by the Binance API performs the
requested action (IDEA-070 B09-TRUST01). Use the existing B02-U implementation:
its code/release label remains **UNTRUSTED**, since recipient and actual
minimum-output/deadline enforcement have not been independently established.
Verified router/facet source is no longer an entry requirement for this path.
Do not ask a source supplier to unblock it or fabricate RouterEvidence.v1.
Source acquisition #138/#139 is historical/optional for the alternate verified
path, not completed source verification. Close or retitle an issue only with a
recorded scope disposition; retain original evidence.

Retain pinned addresses/code/facet/calldata, exact approvals, independent
signer caps, fee/amount checks, fresh quotes, nonce barriers, persisted signing,
canonical reconciliation and full audit delivery. A future changed API router
still fails existing pins until reviewed. API trust is not an automatic bypass
of configured limits, a proof of contract behavior, or a guaranteed loss bound.
Detection after a bad fill cannot reverse it.

No AWS changes, paid calls, funding, wallet operations, activation or key
placement are authorized by this planning update. Yao/approved operator owns
host work; Isaac places the key only in Yao's separately approved signer session.

## What is already implemented, and what must change

| Area | Current implementation | Required adjustment / evidence |
|---|---|---|
| Decoder and startup | `UntrustedRouterDecoder`, execution factory, signer loader and SA-01 assembler accept a pinned untrusted policy. Signer decoding is offline; primary performs live preflight. | Supply a real observed/reviewed policy; select its file/hash in both service configs. Remove the alternate `router_evidence_file`/`router_evidence_sha256` pair. Retain mutual exclusion, offline signer isolation and live preflight. No new generic trust flag or decoder rewrite is needed. |
| Readiness and handoff | Runtime supports both modes, but some reports/runbooks remain source-only. | Make `larp/signer/assembly.py:REMAINING_GATES` mode-aware; reconcile `tools/deploy/propose_signer_caps.py` source-only reporting, Gate B DR-02 wording and DR-02/03 documentation. Align signer preparation, rehearsal entry and current tracker links; correct unconditional loss-bound wording in module/deviation descriptions without declaring DEV-23 FINAL. Preserve missing-policy/review refusals and source-mode checks. These are pending changes, not changes made by this plan. |
| Authority lifetime #27 | Fresh admission and parent expiry conflict with longer encoded route deadlines; initial/post-approval quotes can be refused. | Decide and implement finite original execution authority across planner/persistence/executor/signer/replay. Keep admission fresh; re-quote/restart cannot extend authority. Under API trust, deadline enforcement is an assumption, not a source proof or proof a possibly sent transaction cannot execute. Timeout alone never frees uncertainty. |
| Abnormal fills | Final receipt checks refuse unexpected input/output; an unsettleable fill withholds signing. | Define/test accurate abnormal-outcome accounting, immutable incident records and a supported quarantine/recovery disposition. Never book a bad fill as a normal fill, invent received assets or auto-clear unresolved loss. Safe sustained quarantine is a valid documented result; autonomous continuation requires its own reviewed implementation. |
| Leftover allowances | A reverted swap may retain its approval. Preflight refuses other-token allowances; an approval of the same pay token can overwrite that token's allowance. | Qualify supported recovery after approve-without-swap/revert/expiry, including cross-token/final-exit liveness. If an explicit revoke is selected, review permitted call scope and implement bounded authorization/audit; current exact-approval checks cannot simply be bypassed. |
| BNB gas | Existing native settlement/proof tools exist, but this decoder rejects native-BNB routes. | Decide between implementing qualified native top-ups in this mode or an explicitly reviewed initial-gas-only scope. The latter needs measured whole-run/exit reserve, safe low-gas behavior, declaration changes and code/gate alignment; it is not adopted by this plan. |
| Caps/profile/gas scope | `caps_review.py` requires all five BUY/SELL pairs **and BNB:BUY**, native token scope and top-up coverage; Gate B DR-06 also expects a logged top-up. | Reflect the adopted gas scope consistently in planner/profile validation, mapping, caps review/assembly, signer policy, Gate B and tests. Setting `native_trace=false` alone does not resolve these requirements. Ordinary canonical receipt/gas/balance checks remain required even if native top-ups are omitted. |

Code anchors: [decoder](../../larp/execution_live/untrusted_router.py),
[factory](../../larp/execution_live/main.py), [config pairs](../../larp/execution_live/config.py),
[signer policy](../../larp/signer/policy.py), [assembler](../../larp/signer/assembly.py),
[caps review](../../larp/execution_live/caps_review.py),
[settlement](../../larp/execution_live/settlement.py),
[execution/recovery](../../larp/execution.py).

## Ordered checklist for agents

All LD items below are **OPEN**, not claims that earlier component work is
missing. One accountable owner is named per item; reviewers/operators are explicit
handoffs. These are existing workstream allocations, not new access grants or
assumed acceptance by an unavailable operator. Use one focused PR per independent
code point, based on canonical; avoid duplicate implementations. Record exact
commit/artifact/config hashes, scope, result and reviewer in the topical ledger
and PR133. Remove a whole backlog item only when its complete acceptance passes.

### Repository work that can start now

- [ ] **LD01 — Isaac: align readiness/reporting with the selected path.** Implement the mode-aware reporting/runbook adjustments above; review #138/#160 scope against this decision without marking source verified. Done when both router modes retain their proper refusals, reports name the applicable missing inputs, and documentation links/tests pass. No real RPC/source packet is needed to begin. Maps GAP-29/47, DR-02/03/18.
- [ ] **LD04 — Keegan: resolve and implement #27 finite authority.** Start from SL-01 and Keith's conditional Option A review; use LD02 timings/encoded-deadline observations for numeric acceptance. Persist original admission/authority bounds and economic identity; test approve/requote/expiry/restart/unknown-send and entry-versus-exit windows. State API-trust assumptions explicitly. Do not use 60s as an approved value or require a new signed trade before qualifying the authority needed for that trade. Maps DR-04/14.
- [ ] **LD05 — Keith: complete abnormal-fill accounting/disposition.** Add reviewed facts/incidents for an anomalous finalized outcome while preserving exact ledger truth and quarantine. Test zero/short output, unexpected debit, gas, restart and replay; document whether continuation is supported or intentionally blocked. Keegan reviews integration. Maps GAP-65/68, DR-05.
- [ ] **LD06 — Isaac: qualify leftover-allowance recovery.** Supply a reviewed state machine and regression tests for approval success followed by no swap, swap revert and expired authority; prove other-token/final-exit behavior. Any revoke path needs explicitly reviewed scope and signer rules. No production wallet allowance operation is part of this task. Maps GAP-29/47, DR-02/04.
- [ ] **LD07 — Keegan: decide gas scope with Keith and Isaac.** Choose qualified native top-ups or explicitly reviewed initial-gas-only operation; record limitations/deviations and exact acceptance requirements. Do not claim that trusting the router enables its unsupported native layout. Maps #30/#56, DR-06/14/18.
- [ ] **LD13 — Keegan: finish operations implementation.** Complete D-DN-04 delivery-age enforcement and the adopted supervision/resource/recovery behavior; preserve C05-RV01 decisions already delivered. Numeric/host acceptance depends on LD12/LD14. Maps #60, GAP-02/62/70, DR-07/13/15/16.

### Inputs, measurements and dependent repository work

- [ ] **LD02 — Yao/approved operator: supply current execution inputs.** Retain fresh sanitized host/build/run/wallet/DB identity, reconciled complete holdings/reservations/nonce state, funding/no-further-funding disposition, metadata and queue/RPC/clock timing. Through approved private access supply an execution RPC with canonical/finalized support and the original observed router/facet/code/allowance policy draft plus fresh request-bound quotes. #92's recorded balance-health success is retained; it is not native tracing or current signed-release proof. No credentials/private endpoints in GitHub. Maps old A02/B04/B06-pre, #92/#106.
- [ ] **LD03 — Keegan: review actual policy bytes.** After LD02, independently review the observed chain/address/code/facet/calldata/allowance bindings, record the named review and exact policy hash, and review the fresh decoder replay/preflight result supplied with Isaac's execution checks. Review binding correctness, not unavailable source guarantees. Maps B01–B03 replacement, GAP-29.
- [ ] **LD08 — Isaac: implement and qualify the adopted gas scope.** After LD07, align all affected components listed above. With native top-ups, add/qualify native route decoding and real transaction-bound trace evidence before enabling; an approved trace-capable provider and suitable canonical transaction remain required. For initial-only scope, prove reserve/exits/automatic low-gas handling and update scope-dependent gates without claiming #30's top-up acceptance. Normal finalized receipts/gas accounting always remain required. Keith reviews accounting and Keegan reviews policy/gates.
- [ ] **LD09 — Keith: supply measured profile/quote/fee packet.** Retain actual coverage/gaps, all supported BUY/SELL sizes and full-position exits, approve/swap gas and route-fee evidence for #119/#120. Propose exact S1/rehearsal profile/window/weights or the already conditionally permitted measured fallback. Historical 40-USDT captures and fallback gas are not final measurements. Include native coverage only as required by LD07/LD08. Maps DR-01/08/09/14, GAP-50/64.
- [ ] **LD10 — Isaac: accept exact #44 caps and execution limits.** After LD02/03/08/09, verify fresh full holdings, input coverage, route economics, per-token caps, gas price/limit and aggregate approve-plus-swap budget. Finish #119 fee inclusion review with Keith; actual receipt confirmation follows LD20. Record approved exact policy/profile/input hashes and residual exceptions. No cap is approved by relabeling EXAMPLE_PENDING_TEAM_DECISION. Maps B08/B09, DR-01–06.
- [ ] **LD11 — Keith: finish strategy/evidence/model qualification packet.** Freeze selected S1 inputs, measured parameters/session bars/weights and terminal schedule; verify issuer/official-event coverage, SKHYB disposition, limiter/trend/close-job behavior and #55/#56. Report actual unsigned trial population, labels, omissions, cost/latency/rights and inconclusive results; signed hours cannot replace missing unsigned hours or reset the cutoff. Keegan records the scoped adoption decision at LD22; full model adoption is not inferred from code or account authentication. Maps #25/#37–39/#55/#56/#97, DR-08–12/14.
- [ ] **LD12 — Yao/approved operator: deliver current host/source/account/ops evidence.** Export/backup the preserved shared model ledger and reconcile every UNKNOWN charge/reservation/latch with the owners; verify current provider rights/units/expiry/usage and hosted model stage/ACK results. Retain post-fix source polling/gap/terms evidence and memory/queue/delivery/watchdog/clock/backup/anchor measurements. Keep historical FAILs and old host successes distinct. Account-owner identities are already resolved; request missing artifacts/access, not repeated identity decisions. Maps A02/A03/C01, #127/#32/#60/#97.
- [ ] **LD14 — Isaac: accept measured operations values.** After LD12 and Keegan/Keith analysis, decide exact delivery-age/watchdog/memory/recovery values within C05; require LD13 review/tests and later host proof. Review slice already delivered is not repeated. Maps C05, GAP-02/62/70.

### Signed development installation and first functional round

- [ ] **LD15 — Keegan: qualify the exact integrated signed candidate.** Integrate/review LD01/03–10/13/14 and the selected LD11 scope. Bind source, dependencies, prompts, model/source policy, selected profile, gas scope and service configs; run required Linux/PostgreSQL/systemd/sandbox/bundle checks and retain original artifacts. Use the accepted mirror route if needed; org billing remains unresolved, not a reason to invent CI PASS. Old unsigned c5be269 and CONS-01 tests do not qualify changed signed bytes. Maps C06, DR-18/20.
- [ ] **LD16 — Isaac: assemble and check private signer.json.** After LD10/15 plus actual run/build/DB/CA/router bindings, use the existing GateBCapsInputs.v1/SA-01 flow with mode-appropriate gates. Pin the same reviewed untrusted policy file/hash in execution and signer configs, without the source-evidence pair. Run exact release/config checks; preserve key-free candidate/report/hash privately. Distinguish numeric assembly from installation approval. Maps #160, C06/C07, DR-03.
- [ ] **LD17 — Yao/approved operator: qualify installation and approve the signer session.** After LD15/16, verify exact service users, isolation, routes, IAM/TLS/CA, clock, credential mechanism, alarms and preserved DB/run/ledger bindings. Install only the accepted candidate under separate operator authorization; signer keeps no internet RPC dependency. Provide Isaac the approved session and teardown procedure. Maps C07, DR-03/12/16.
- [ ] **LD18 — Isaac: place key only in the approved session.** After LD17, use the existing protected credential/key loader and verify wallet identity, file ownership/mode and exact release/config binding without exposing key material. Yao owns access/provisioning/teardown. signer.json itself contains no private key. Maps C08, DR-03.
- [ ] **LD19 — Yao/approved operator: run the first bounded agent round.** After LD04/08/10/15–18 and applicable Gate A review, allow the registered agent to select/approve/requote/sign/broadcast a minimum-size permitted action in the adopted dev window. Retain every decision/attempt/nonce/hash/receipt, actual token/native gas accounting and receiver STORED ACK, including abort/failure records. No human-selected/manual trade. Do not require the first-trade proof as a prerequisite to this same first round. Maps DR-02–07.
- [ ] **LD20 — Isaac: review first-round execution and fees.** After LD19, independently match canonical approval/swap, actual wallet movements, fees/gas, reservations and logged round/ACK to exact decision/release/config. Validate #119 assumptions against actual results; Keith reviews accounting and Keegan reviews Gate B. A transaction hash or process healthy=true is not acceptance. Maps DR-01–06, B03/C08.

### Rehearsal and final activation

- [ ] **LD21 — Yao/approved operator: execute signed-host drills.** After LD20, use the existing RG-01/RG-02 packet with pinned host fault procedures: crashes at each boundary, UNKNOWN reconciliation, automatic same-build restart/HALT/clear, low-gas/allowance/abnormal-outcome behavior, alarms, immutable anchors, empty-target restore/quarantine and throwaway wallet switch. Export real shadow/signed-day replay inputs; retain daily actual signed rehearsal intervals and incidents. Mark missing coverage BLOCKED/NOT_RUN. Maps C09, DR-04/05/13–17/19/21.
- [ ] **LD22 — Keegan: review operational, model and rehearsal acceptance.** After LD11/20/21, replay actual days, obtain Keith's strategy/model reports and applicable DR signoffs, review measured recovery behavior, and record final adoption/services/deviations (including DEV-23, gas scope and any shorter rehearsal). Existing signed-window/Oct21 conditional rehearsal decisions still apply unless explicitly changed. Do not invent 72 unsigned hours, five signed days or weekend coverage. Maps C04/C10, GAP-04/62, DR-08–21.
- [ ] **LD23 — Isaac: complete final-wallet/credential handoff.** With account owner/Yao, confirm the fresh final wallet registration and applicable logging secret privately; arrange only eligible pre-first-trade gas funding under the existing organizer exception, record transactions and capture balances afterward. Do not assume dev credentials/funds transfer, authorize additional funding from an old report, or put keys in config/GitHub. Yao installs secrets/credentials only in separately approved operations. Maps C11, #106, GAP-52, DR-17.
- [ ] **LD24 — Keegan: assemble final activation acceptance.** After LD22/23, collect Isaac DR-01–06, Keith DR-08–11/14, Yao DR-12/16 and Keegan's remaining reviews; finalize all release registers/services/deviations and bind final wallet/run/config to the exact frozen release. Verify final schedule and automatic terminal behavior, source/account/clock/resource/delivery readiness and complete DR-22 pack before activation. Carry remaining organizer clarifications through the existing C12 reconciliation/owners (Q-04/06/08/14/35/39); do not reopen settled questions. Final environment changes and activation remain the approved operator's separate actions. Maps C12, DR-18/22.

**Start now:** LD01/04/05/06/07/13 repository lanes and LD09/11 analysis with
available data; LD02/12 measurements require the approved operator. LD08 follows
the gas decision. LD03/10/14/15/16 become completable when their named packets
arrive. Source export is absent from this critical path. For any missing input,
record supplier, exact artifact, blocked consumer and alternative/scope decision;
do not assign an impossible task to its consumer.

## Evidence and rules checked

Reviewed local current code and tests; canonical `928b8a8` plus PR196 trust
record `7fbd73e`; PR133 body/comments and open GitHub issues on 2026-10-20 SGT.
No fresh AWS/provider/chain/model call or runtime test was made for this plan.
PR133's Oct19 10:44–10:56 UTC read-only host report is retained owner evidence,
not today's observation: #92 process balance-health success, partial host snapshot,
two UNKNOWN charges and missing native-trace configuration.

Read verbatim [official rules passage](../official/source_page.md#rules--restrictions),
[kit trading guide](../official/kit/bstocks-trading-guide.md),
[core F/K/Q and guardrails](../skill/SKILL.md) including F-114/117/119–124 and
answered Q-40, and the existing lifetime/operations/rehearsal packets. API-trust
adoption is team policy, not an organizer requirement. Automatic same-build
restart is allowed; manual intervention/build changes are not the planned
scored-run recovery mechanism. Keep existing first-gas restrictions and audit
requirements. Unknown scoring/window/credential questions retain their recorded
owners; do not reopen settled identity/network/protocol decisions.
