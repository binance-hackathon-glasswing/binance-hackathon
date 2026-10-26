# Signing lifetime: Isaac's proposal for #27

**SL-01, 2026-10-17. Option A adopted by Keegan on 2026-10-20 and implemented (IDEA-049-C C-OPEN-003 / LD04); L and the margin are still undecided and wait for measured host timings.** Isaac's checklist task5 / #142.
Keith reviews the profile/quote implications; Keegan decides C-OPEN-003 and
owns the implementation PR. Baseline: integration `352446b`. No lifetime,
profile, runtime, signer or validation setting is changed by this document.

## The current mismatch and what is actually known

The current flow couples three different clocks:

| Clock | Current behavior / evidence |
|---|---|
| Proposal admission | `larp/strategy/policy.py` stamps the proposal from the snapshot time; LIVE `profiles.py` sets `proposal_seconds = min(15, quote_age_seconds)`. `contracts.validate_proposal` refuses an expired proposal. |
| Parent execution authority | `risk/planner.py` bounds `quote_expiry` by the initial quote expiry and `signing_end`. `integration/runtime.py:RuntimePlanner.plan` also caps discretionary intents at proposal expiry. `execution_live/service.py` maps `expires_ms` into `Intent.valid_until` in whole seconds. |
| Each swap's chain deadline | `execution.validate_payload` requires `now < decoded.deadline <= intent.valid_until`. `Executor.prepare` validates the quote even before creating the approve; after final approval it gets another quote. The remote signer repeats payload validation. |

Thus a synthetic decision at t=0 with a proposal expiring at t=15 and a
decoded route deadline t=30 is refused **before approval**, not merely when
the swap is signed. Re-quoting after approval can create a later deadline
that is also outside the original intent. Mandatory intents avoid the
discretionary proposal clamp, but retain the initial-quote/signing-end bound;
their later re-quotes need consideration too.

**Evidence limit:** ~30s is the kit's stated approximate quote lifetime, not a
verified deadline for the real router. `docs/official/kit/web3-open-api.md`
Trading flow step3 supplies that description. `marketdata/cost_summary.py`
uses a 30s default and labels its origin `KIT_STATED`; it does not measure
encoded expiry. EXP-005 explicitly leaves encoded expiry unverified. Router
source task3/#138 and the recorded-route check still have to establish actual
deadline semantics. The synthetic 15s/30s conflict is established; a claim
about every real route's encoded deadline would go beyond this evidence.

The old guard-spacing problem #53 is fixed by PR79. IDEA-049-C WR-C records
9 Web3 requests /2.10s forced spacing, or 11 /2.45s with a simulated 10s
approval wait, plus unpaced RPC work. Those tests use a fake transport and
virtual clock: spacing is **not** end-to-end host, queue, HTTP, RPC, signer,
confirmation or finality latency. Their synthetic quote deadline is made to
fit the fixture intent; they do not resolve #27's independent deadline bound.

## Option A: admit a fresh proposal into a finite signing authorization

Keep the short proposal admission window and existing quote/data freshness
limits. Give an admitted economic decision a separately bounded, immutable
execution authorization. This deliberately changes the present policy that
a discretionary intent never outlives its proposal; it needs an explicit
team decision and reviewed implementation.

Proposed contract (all absolute timestamps, with explicit units):

- `t0` is the original decision snapshot timestamp, durably bound to that
  decision. It is not reset at command claim, signing request, re-quote or
  restart. Admission must occur before the original proposal expiry `P` and
  while the required market/quote/evidence facts are fresh.
- Choose a finite reviewed lifetime `L`; set `A = min(t0 + L, signing_end,
  applicable execution-window end)`. Scope any discretionary buy/new-risk
  cutoff to that action; do not accidentally prevent mandatory exits at an
  entry-window boundary. Mandatory and gas actions also need bounded authority
  and their applicable window checks; they get no unlimited lifetime.
- Persist `P`, `t0`, `A`, the chosen policy/version identity and economic
  limits. Proposal admission and execution authority need distinct fields;
  merely increasing `proposal_seconds` would also allow stale admission.
- Preserve the initial quote's expiry on that **payload**. It is not authority
  to reuse expired calldata. For each initial/post-approval quote, independently
  establish `now < route_deadline <= A`, a fresh observation and enough remaining
  time for the reviewed submission/clock margin. Different nested deadlines
  must satisfy the source-qualified decoder contract too.
- Keep exact tokens/amount/recipient, minimum output, cost/slippage, independent
  signer caps, funds/gas reservations, nonce/finality, audit, market-open,
  HALT, epoch/build and health checks. A re-quote cannot increase economic
  authority, refresh `A`, reset attempt budgets or bypass a current refusal.

**Illustrative candidate only:** `L=60s` shows the distinction clearly; it is
not a measured safe setting or an approved deployment value. With t0=0,
P=15 and A=60, an initial route with deadline30 fits. If approval finalizes
at t=10 and a new verified route expires at t=40, `10 < 40 <= 60` fits too.
A new deadline65 fails even at t=35; a restart at t=35 still has A=60.
Any earlier applicable window end shortens A and can make this attempt fail.

For a 60s candidate, a hypothetical budget of at most20s to the post-approval
quote, at most30s remaining encoded route lifetime and10s allowance illustrates
the arithmetic. **None of those bounds is qualified here.** Actual source/TTL
and host timings may rule this candidate out. A measured percentile is not an
inclusion guarantee; attempts outside the frozen limit must be refused rather
than silently getting more time. `L` and the submission/clock margins require
Keegan's recorded decision after Keith's review and actual measurements.

Benefit: permits the required approve → finality → re-quote sequence without
depending on an unproven caller-controlled router deadline. Cost: changes the
parent-authorization model across planner, command persistence, executor,
signer and restart/replay; it permits a fresh admitted decision to execute
after its short proposal-admission window, within the frozen economic bounds.

## Option B: retain the parent expiry and qualify a shorter router deadline

Keep current proposal/parent lifetime semantics. Obtain each exact returned
swap with a verified encoded deadline no later than that original parent
expiry. For discretionary actions the parent is currently at most P and the
initial quote expiry; mandatory/gas actions retain their own existing bounds.

Required capability evidence:

- An attributable, supported API/router mechanism accepts the intended absolute
  deadline and enforces it through the relevant route/helpers. No current
  repository request demonstrates this capability: `LiveVenue.quote` sends
  amount, tokens, wallet, vendor and slippage, without a deadline parameter.
  This is not a claim that every provider API lacks such a feature.
- The returned bytes must decode to that deadline with the required economic
  and source guarantees. Do **not** patch arbitrary returned calldata or an
  RFQ signature to pretend the capability exists.
- Both the initial quote and every post-approval re-quote respect the **same
  absolute parent expiry**. Requesting `now+15s` again would move the boundary.
- The whole approve/finality/re-quote/estimate/signer/release path must fit with
  a reviewed submission/clock margin. If insufficient time remains, refuse and
  reconcile any approval already sent; do not repeatedly approve to chase TTL.

Illustration: t0=0 and P=A=15. If approval finalizes at t=10, the new route must
expire at or before15, leaving at most5s. A deadline40 still fails. Even a
deadline15 is unusable when less than the required processing/clock margin
remains. #53's spacing result does not prove this real path fits in15s.

Benefit: preserves the existing short parent-authorization policy. Cost: needs
an unqualified router/API capability and a tight real end-to-end latency bound;
the new deadline must still work with any nested signed/RFQ route. It is not
currently implementable just by changing a local number.

## Recommendation and owner decisions

**Recommend Option A's separate, finite authorization model**, conditional on
source-qualified deadlines and timing evidence. Keep the existing failures
until Keegan adopts and implements the model. Treat60s as a discussion/test
candidate, not a final value. Do not increase proposal or quote age to hide
the mismatch and do not remove the encoded deadline comparison.

Keith's requested review: whether the admitted action's economic limits stay
valid for the proposed lifetime, how this affects quote/proposal provenance
and measured profiles (including S1), and applicable entry/exit/gas windows.
Keegan decides A versus B, `L`, clock/submission margins and per-kind scope;
records C-OPEN-003 with the final invariants; then opens the code change. Isaac
supplies router/deadline evidence and execution acceptance with the relevant
owners. Yao owns host timing/configuration evidence and deployment after review.

## Required implementation and qualification acceptance

These are prospective requirements for the later code/qualification PR,
**not tests run or results claimed by this documentation change**.

| Case | Required result |
|---|---|
| Late proposal admission | Refuse a proposal at/after P even if a hypothetical A would still be in the future. |
| Normal sequence | Exercise15s proposal,30s decoded-deadline fixtures and nonzero approval delay under the chosen model, through planner, stored command, executor and remote signer. |
| Parent/deadline bounds | Refuse deadline>A or now>=deadline/A at initial quote, re-quote, signing and release; check absolute seconds/ms boundaries without rounding authority upward. |
| Freshness vs authority | A fresh signing window does not make stale data, an old quote or failed cost/slippage/risk checks acceptable. |
| Restart, queue and re-quote | Persist the original t0/A and economic identity; restart/claim/retry cannot extend authority or reset probe budgets. Reject changed timestamps/limits on an existing identity. |
| Slow finalized approval | Do not sign a swap without time left. An ERC20 approve itself has no encoded expiry: expiry cannot undo a released approval or justify forgetting its nonce/allowance consequences. |
| Possible submission | Continue reconciliation and retain reservations/wallet barrier until current positive terminal rules permit release. A route deadline, local expiry or timeout alone does not prove non-submission or release uncertainty. |
| Current refusals | Preserve signed-byte binding, independent signer policy, build/epoch/HALT/nonce checks and disabled same-nonce replacement. |
| Action/window coverage | Discretionary entry/exit, mandatory reduction and gas paths all obey their chosen parent bounds and applicable windows, including crossing cutoffs. |
| Real qualification | Hash recorded decoded deadlines/route variants and host queue, guard, estimate, signer, confirmation/finality and release timings. Decline if the selected cap/margins do not fit; record refusals as well as successes. |

No real signing/trading experiment is authorized by this proposal. Source
evidence, measured profiles, signer setup, first gas and the other Gate B
prerequisites remain independent. Parent #27 stays open after this writing
slice is complete. Existing router task3 and route replay task4 stay separate.

## GB-RW1 technical review for the profile owner (2026-10-17)

This is a repository review prepared for the checklist's Keith review of #27,
not Keith's sign-off, Keegan's decision, or approval of a lifetime value.
The adopted code remains unchanged.

| Profile implication | Option A | Option B |
|---|---|---|
| Quote age and proposal admission | Preserve the existing short ages and admission expiry. A separate finite authority must not make an expired proposal admissible. | Preserve the existing ages and parent expiry. Every route must fit inside that same absolute parent bound. |
| Economic limits | Persist the admitted exact pay amount, minimum output, cost/slippage bounds and original policy/build identity. Current guards, reservations and independent signer caps still apply at each step. | Same limits; requesting a shorter deadline must not change amounts, recipient or signed/RFQ economics. |
| Re-quote and restart | Keep the original decision time and absolute authority end. A re-quote can refresh its own payload, never the parent authority or attempt budget. | Keep the original absolute parent expiry. A fresh now-plus-duration deadline would improperly extend it. |
| S1 and action windows | Bound new-risk authority by the applicable entry/execution window; preserve separate rules for reductions and gas. The planning-session counter does not establish B6's actual-session checks. | The same action/window restrictions apply in addition to the shorter parent bound. |
| Approval delay | Measure the complete approve/finality/re-quote/sign/release path before choosing the duration and margin. A late approval does not grant a new window. | The whole path must fit the short parent window; no current API evidence demonstrates a caller-controlled encoded deadline. |

Option A remains the technically supported direction to investigate, conditional
on the recorded decision and source/timing evidence. It does not require changing
`proposal_seconds` or `quote_age_seconds`. Option B is not established by editing
calldata or adding an undocumented API parameter. Neither option is qualified by
the synthetic request-spacing measurements in WR-C.

Before implementation, the owner decision must specify the duration and
clock/submission margins, each action's applicable window, the original durable
decision timestamp and the persisted admission/authority fields, with producer
and consumer agreement for any I3 change. Source-qualified route deadlines and
actual host queue, RPC, approval/finality, signer and release timings must show
that the limits can be met. An approval has no encoded expiry: delayed/possible
submission continues reconciliation and retains the appropriate reservations
and wallet barrier. The numeric lifetime and the necessary owner decisions
remain outstanding in the available repository records.
