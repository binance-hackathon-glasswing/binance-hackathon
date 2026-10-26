# Remaining development gas funding — FG-02 / #106

**Subsequent SJ-03 update (2026-10-22 SGT):** Isaac completed the additional
2USDT dev seed. Its receipt/net debit and finalized public96USDT/
0.005325625054330011BNB balance are verified in
[the new record](evidence/dev-gas-funding-20261022.json). Both dev seeds now
total4USDT net debit. The selected0.003072BNB signer exit floor is covered;
no further swap is requested for that minimum. The still-open handoff is the
operator's actual post-last-seed reconciliation/PortfolioState/private inputs
and final run/config bindings. The historical preflight/status/instructions
below remain dated evidence; do not repeat the completed seed. The separate
live-challenge wallet must not be used in this task.


**CONS-01 archived PR lane:** this evidence/handoff is retained on `codex/system-testing-20261012`; the separate source/funding draft is retired by consolidation. Actual missing inputs remain in the [live backlog](../INCOMPLETE_WORK.md). Use [current status](CURRENT_STATUS.md), including the conditional untrusted-router alternative. Historical observations below are not current readiness or an instruction to fund/sign.

Status: **preflight recorded; remaining wallet action NOT_DONE; hosted opening
capture NOT_RUN**. This is immediate point4 in its own PR. Isaac reports no
additional funding hash. No wallet key/session or MetaMask control is available
to this agent, and no swap was submitted. About4USDT total development funding
and about6USDT final funding are existing team policy, not new sizing decisions.

## Historical public preflight

The 2026-10-18 collection completed at10:59:17.509815UTC. Its anchored block
time was10:59:12UTC (18:59:12SGT); this is historical evidence, not current wallet
state. BNB Chain public RPC returned chain56,
finalized block128350421, hash
0xf99fd175d1d4b7634111e131fc06bcbcd07d573f6058cc0ed6c06bc1dda3fda2.
Numeric block identity and chain were rechecked after the reads.

| Field | Exact observed value |
|---|---|
| Development public wallet | 0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479 |
| Finalized native balance | 2694498869362886wei =0.002694498869362886BNB |
| Finalized USDT balance | 98000000000000000000 raw units =98USDT, decimals18 |
| Finalized / latest / pending nonce | 2 /2 /2 |
| Known historical funding | 0x24683de219c18cc78a2d7aeb37c94e733a6a383b1c3a58d3a403f95df7da5c55; nonce1; successful canonical block127946341; 2026-10-16 08:27:44UTC |

Positive BNB means this particular snapshot is not a zero-BNB balance. It does
not prove current hosted Gate B readiness, the whole planned funding target,
that no agent trade or unreleased signing authority exists, or complete wallet
activity reconciliation. Nonces were separate snapshots, not an atomic lock.
Current BNB is not the gross incoming amount of the historical swap and is not
substituted for transaction-bound native tracing.

Public evidence: [dev-funding-preflight-20261018.json](evidence/dev-funding-preflight-20261018.json),
SHA256 `2784503923b345095e58302becf06220818b3dde869f0749ff33941d3e93a83a`. Exactly14 RPC calls, within FG-02's16-call limit,20s per call,
no retries/redirects or credentials. Original public response bytes remain at
/private/tmp/larp-isaac-now-public-20261018; the report retains every request,
UTC/status, byte length and response hash. This is not PortfolioState.v1 or the approved operator's
post-last-funding opening capture.

## Finish in the wallet, then hand off

1. **Named approved operator, after accepted coordinator handoff:** confirm from actual run/signing/wallet reconciliation that
   the development wallet has not made its first agent trade and has no in-flight
   work. The public snapshot alone does not establish that precondition.
2. **Isaac, in MetaMask:** only after that confirmation and fresh reconciliation
   establishes that additional funding is still needed under the existing
   about4USDT total development plan, complete the required USDT→BNB seed from
   this same wallet. About2USDT was the historical remaining target, not an
   instruction to repeat funding based on this old snapshot. If funding is
   already sufficient, record that reconciliation instead. For any required swap,
   use BNB Smart Chain, selecting USDT for the network fee. Review the wallet's
   actual total USDT debit/fee against the freshly reconciled remaining need;
   the historical about2 target is not an executed amount. No own funds, external deposit, wallet-to-wallet transfer,
   BNB sell-back, key export or agent trade is part of this handoff.
3. **Isaac:** retain the exact transaction hash and receipt UTC, USDT outgoing/
   incoming/net debit, BNB received, and the source for each amount. Keep native
   credit RPC-INCONCLUSIVE if only explorer/MetaMask evidence is available;
   do not replace it with a whole-block/current balance delta. The earlier2USDT
   note remains separate. Supply the new public hash for independent read-only
   receipt verification; never provide private keys or the mnemonic.
4. **Named approved operator, after accepted handoff:** after the last manual
   funding swap, take the fresh canonical
   all-asset/nonce/kit cross-checked opening capture, build the actual run's
   PortfolioState.v1, record/pin its SHA256 and re-prepare/bind as required.
   Existing shadow captures are not automatically the signed run's opening.

The funding action is a deployment funding note, not an agent decision round;
no ai-seeds log is produced for it under the already confirmed F120 team record.
Signed top-ups after the first agent trade use the agent's separately qualified
logged path. Key placement still waits for Yao's approved signer session; no
AWS operation, wallet transaction or official-log upload occurred in FG-02.

Sources checked: verbatim official/source_page.md dedicated-wallet restrictions;
official/kit/bstocks-trading-guide.md gas/wallet text; SKILL.md F120/G13/Q03 and
reference/participant-kit.md K4; confirmed team funding decisions and the existing
DEPLOYMENT_DAY.md §5/#106 note. The manual first-gas exception is already answered;
no new organiser question is proposed. Native tracing/floor, actual caps/profile,
first signed round, final-wallet funding and all hosted acceptance remain open.

## Ownership and completion

| Remaining step | Owner / record |
|---|---|
| Reconcile current holdings/funding need and confirm no first agent trade/in-flight work | Named approved operator after accepted handoff — #106 / GAP49 |
| If still needed, execute confirmed MetaMask seed and supply hash/amounts | Isaac — #106 / GAP49 |
| Independently verify the supplied new hash/amounts | Isaac execution workstream — IDEA039 FG-02 |
| Actual post-last-seed opening capture and binding | Named approved operator after accepted handoff — DEPLOYMENT_DAY §5 / GAP70 |
| Trace-qualified agent top-up and measured floor | Isaac execution workstream; Keith measurement and approved operator host dependencies — #30 |

Parent106 and GAP49 remain open. This PR is a draft preparation/evidence slice,
not a claim that remaining funding or the opening capture is complete.
