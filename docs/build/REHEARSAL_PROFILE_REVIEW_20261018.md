# Rehearsal/profile and signing-lifetime review — KMP-SIGN01

Keith proposal, 2026-10-18 UTC. Inputs: #27 and merged PR144's SL-01,
`SIGNING_LIFETIME_PROPOSAL.md`, integration `4312cd1`; IDEA-075/076 and the
Oct18 checklist. No profile, cap, lifetime or mode is adopted or changed here.

Recommend option A's separate immutable finite authority, conditional on actual
router deadline and host latency evidence. Keep quote freshness and proposal
admission at their measured/current bounds: LIVE proposals are at most15s,
further bounded by quote age. Increasing either to hide #27 would admit older
economic decisions and make the measured re-quote-drift profile inapplicable.
SL-01's60s is illustrative, not a qualified setting.

Let t0 be the original decision timestamp, P the short admission expiry and
`A=min(t0+L,signing_end,applicable_action_window_end)`. Admit only before P with
fresh inputs. Persist t0/P/A, build/policy/profile identity and exact economic
limits. Every initial/post-approval quote must be fresh, independently decoded,
and satisfy `now < route_deadline <= A` with a reviewed release/clock margin.
The old quote's expiry governs its payload, not the lifetime of all future
payloads. A re-quote/claim/restart never refreshes A, resets attempts or expands
tokens, amount, slippage, min-output, gas/funds/signing authority.

The entry-window end bounds new-risk buys; it must not accidentally prohibit
mandatory exits at an entry cutoff. Mandatory and gas actions need their own
finite applicable bounds and existing HALT/market/finality checks. Expiring an
intent cannot undo an ERC20 approval: uncertain/released approval still requires
nonce/allowance reconciliation and the wallet barrier, even after A expires.
Do not infer NOT_SUBMITTED or release reservations merely from a timeout.

Option B preserves the existing parent expiry but needs a source-qualified
API/router facility that returns a deadline within that unchanged absolute
expiry. Current quote requests supply no such deadline parameter. Repeating
`now+15s` or patching returned/RFQ calldata would not establish the capability.
The15s/30s synthetic conflict is established;30s remains kit-stated approximate
quote TTL, not measured encoded-router expiry. #53's9/11 requests and2.10/2.45s
spacing are synthetic, not real end-to-end approval/finality bounds.

For either option Isaac supplies route source/TTL evidence and Yao measures
queue, Web3/RPC, approval/finality, re-quote, signer and release clocks. Keegan
chooses finite L/margins/per-kind scope in C-OPEN-003 and owns the implementation.
Exercise late admission, boundary equality, nonzero approval delay, restart and
uncertain-send/reconciliation before qualifying signing. Until then #27 blocks swaps.

## Recommended rehearsal shape

1. First signed trade inside the existing **Oct21 00:00–Oct22 00:00 UTC** buy
   window, after Gate B, #27 and explicit signed-model adoption. This needs no
   earlier-window code change. An earlier development window is an alternative
   requiring a separately reviewed committed/pushed release/version event and
   cannot count as extra unsigned-trial observation time. Isaac decides.
2. Build the final measured **EQUAL_WEIGHT** rehearsal profile on Oct20 as the
   fallback if S1 inputs/weights/parameters, EXP-007 disposition and B4 producer
   are still unqualified. This exercises the implemented four-name20%/80%
   exposure policy; it is not evidence for S1's five-name95% strategy. If all S1
   prerequisites are completed and explicitly frozen/adopted, use that exact
   `TREND_GUARDED_VOL` profile instead and record its hashes. The profile decision
   is conditional, not a reversal of the team's S1 direction.
3. For an adopted S1 profile, recommend **`limiter_mode: DETERMINISTIC`** for
   rehearsal/final: code maps LLM-verified evidence classes into reduce-only
   levels without an additional exposure-model call. This still needs Keegan's
   `exposure_evidence` producer. It does not replace the routed LLM assessor with
   a deterministic assessor. `MODEL` remains unqualified until its separate
   pinned exposure call, audit, shared budget, expiry and acceptance are built
   and tested. Isaac confirms O6/DEV-19 by Oct20. No B4 producer means no claim
   that the rehearsal tests the LLM's exposure-limiting effect.

The current quote handoff uses40 USDT quotes, not a permitted trade size: the
development signer candidate caps input at35 USDT. Final profile/trade/gas and
full-holding cap checks remain after Oct20 data. The interim two-day/nine-sample
profile is for unsigned shadow only and cannot be reused as final acceptance.

POLICY-HOLD is a separate owner decision. Recommendation: retain the implemented
HALT on mandatory-sale price-jump refusal until a reviewed, bounded mandatory-exit
policy is adopted; do not bypass freshness/chain-safe sizing to force a sale.
Isaac decides with Yao/Keith; this proposal does not change the existing behavior.
