# IDEA-083 — Assessment time budget and review outcome rule: per-stage shares, parallel reviewers, longer deadline, reviewers never replace an assessed primary

- Date / author: 2026-10-19 SGT / Yao Zhu (decision), with Claude (write-up). **Initial implementer: Keegan**; Isaac takes over implementation at the user's request (AB-IMPL01). Reviewers: Keith (model protocol/affordability; B11 changes how the approved PR168 v3 protocol counts reviewed jobs), Isaac (runtime timing).
- Status: **implemented in PR181; final local acceptance in progress.** Yao approved direction on2026-10-19.
  Pass criteria were preregistered; pushed red witnesses and implementation evidence are recorded in AB-IMPL01.
- Scope: unsigned and signed routed assessments (`aiand_routed`, OpenAI-preferred routing). **Model effort stays as
  is** (OpenAI medium, AIand reviewers high). Yao: lower reviewer effort only if latency is still a problem after
  this change.

## Problem (observed, IDEA-066 PC-DEPLOY02)

The first fixed hosted job on `ea25b52` (round `cadence:1991492#1`, 2026-10-18 17:15 UTC) used all three models in
sequence and ran out of time:

| Stage | Model / effort | Step latencies | Result |
|---|---|---|---|
| openai-primary | `gpt-6.1-sol` / medium | 3.6 s, 14.1 s | ASSESSED (charges settled 6,190 + 13,792 µUSD) |
| external-review-0 | `moonshotai/kimi-k3` / high | 4.1 s, **33.8 s** (3,280 output tokens) | ABSTAIN (`UNSUPPORTED_CLAIM`) |
| external-review-1 | `zai-org/glm-5.3` / high | 3.4 s, then in flight at the deadline | UNAVAILABLE |
| **combined** | | **60,019 ms** | **UNAVAILABLE, `ASSESSMENT_DEADLINE_EXCEEDED`** |

How the deployed code spends the time (`larp/intelligence/routing.py:265-333` at `ea25b52`):

- The whole assessment is capped at **60 s**. The cap is enforced in four places: `max_deadline_ms: 60000` in
  `config/intelligence/intelligence.v1.json` and `intelligence.shadow.v1.json`; `larp/intelligence/config.py:60`;
  `larp/runtime/schema.py:37`; and `routing.py:274`, where a larger request deadline falls back to the routine path.
  `larp/intelligence/agent.py:176` also checks a step's deadline against the config.
- OpenAI gets at most half (30 s). A review runs when OpenAI is not ASSESSED, or on red-flag, event, incomplete or
  conflicting evidence, or the seeded 10 % audit (`_review_reasons`).
- Reviewers run **one after another with no per-stage allowance**: Kimi may use all remaining time, and GLM only gets
  what is left (and only runs if Kimi is not ASSESSED). A slow first reviewer starves the second.
- A timed-out OpenAI call keeps its **conservative maximum** UNKNOWN charge (about 84,764 µUSD) and its answer is lost,
  while a completed call settles at its real cost. Timeouts therefore waste money and trial headroom.
- On a large filing all three can time out: OpenAI 30 s, Kimi the remaining ~30 s, GLM ~0 s →
  `ROUTING_DEADLINE_EXHAUSTED`. UNAVAILABLE fails safe (no new risk), but the decision is lost.

## Decision (Yao, 2026-10-19)

Adopt the recommendation: raise the per-decision budget to **about 120–180 s**, give **each stage its own share**,
and run the **two reviewers in parallel**. Do not lower model effort now. Also (B11): when the primary is ASSESSED,
reviewers can only confirm or block it, never replace it, and a review in which no reviewer finishes leaves the
primary's result standing.

Timing context (why this does not make decisions too slow): rounds run on a 15-minute cadence or on a new filing;
an assessment stays valid for about 1 hour (`expiry_ms` − `completed_ms` ≈ 3,600 s on the 17:15 job); a round that
wants to trade re-quotes in a follow-up quote round. The hard ceiling is the runtime watchdog
`cycle_timeout_seconds` = **600 s** (a longer cycle restarts the process), and the runtime runs one round at a time,
so a burst of filings queues behind slow assessments.

### Observed in the running trial (read-only check, 2026-10-19 01:34 UTC, run `larp-dev-llm-trial-20261018t170339z`)

14 rounds, 13 assessments since 17:04 UTC. Every review was triggered by risk reasons
(`EVENT_INTERPRETATION` + `INCOMPLETE_OR_CONFLICTING_EVIDENCE`, once `PRIMARY_NOT_ASSESSED`), none by the seeded audit;
GLM never finished a review.

| Case | Jobs | Today | Under B11 |
|---|---|---|---|
| No review triggered (OpenAI alone, 3–5 s) | 7 | ASSESSED | unchanged |
| OpenAI ASSESSED, Kimi confirmed | 1 | ASSESSED but Kimi's result replaced OpenAI's | OpenAI's result, CONFIRMED |
| OpenAI ASSESSED, Kimi timed out or errored, GLM no time | 3 | UNAVAILABLE | OpenAI's result, INCOMPLETE |
| OpenAI ASSESSED, Kimi ABSTAIN, GLM no time | 2 | UNAVAILABLE | ABSTAIN, DISSENT |
| OpenAI not ASSESSED, Kimi ASSESSED | 1 | ASSESSED (Kimi) | unchanged, FALLBACK |

Yao's reasoning for "no reviewer finished → primary stands": a timeout is a capacity failure, not information about
the filing; the primary's claims still pass the harness's evidence verification and the downstream risk limits; with
B1–B3 these cases should become rare, and every one is recorded for the trial report. The conservative alternative
(ABSTAIN `REVIEW_INCOMPLETE`) was considered and not chosen.

## Required behaviour (implementer may tune the numbers with a recorded reason)

| ID | Requirement |
|---|---|
| B1 | Per-decision assessment budget **180 s maximum** (proposed default 180,000 ms; anything from 120,000 ms is acceptable with a recorded reason). One constant/config value drives all five places listed above; no hidden 60,000 ms remains on the routed path. |
| B2 | **OpenAI primary share ≤ 60 s** (the original per-decision figure) and never more than one third of the budget. |
| B3 | **Reviewers run in parallel**: when a review is triggered, external-review-0 and external-review-1 start together and each gets its **own allowance** (proposed: the remaining budget, capped at 90 s each), so neither can starve the other. |
| B4 | Combination of the primary and the parallel reviewers follows **B11** exactly and is deterministic regardless of which reply arrives first. The disagreement test is today's `_signature` comparison (findings, event findings, falsifiers). |
| B5 | No change to: model IDs, efforts, prompts, the routing file `a5fca50a…` (so the existing ledger's pacing/trial policies still match), review triggers, the 10 % audit seed, tool limits (≤ 6 calls, ≤ 3 per primary), or fail-safe UNAVAILABLE handling. Effort reduction is explicitly out of scope. |
| B6 | Accounting unchanged and safe under concurrency: every OpenAI POST still reserves its maximum atomically; every AIand POST passes the trial/accounting guard at its own transport boundary; two concurrent reviewer POSTs cannot bypass the trial day/total limits or the accounting quarantine. |
| B7 | Every stage's request, reply, reasoning summary, usage, latency and in-flight status is recorded in the round log and model artifacts exactly as today, for both parallel reviewers, including a reviewer still in flight at the deadline. |
| B8 | Worst case fits the watchdog with margin: budget + market/quote/balance work stays **≤ 300 s** per cycle (half of `cycle_timeout_seconds`). |
| B9 | Train/serve parity (plan.md "Declared values" table, row "Evidence loop budget (G-50)"): the historical/research evidence pass uses the same budget values, or the difference is recorded. |
| B10 | Declared deviation: add **DEV-22** to `config/release/deviations.v1.json` and plan.md §6.5, and update G-50's text in plan.md. The submitted proposal says "The loop is capped at 6 calls and 60 s per decision" (`docs/proposal/proposal_answers.md:12`); G-50 is a POLICY, so this is allowed but must be declared (F-61, GAP-62). The release register hash changes as a result. |
| B11 | **Review outcome rule (decided by Yao 2026-10-19; replaces today's `chosen = reviewed`).** Each finished reviewer is *confirm* (ASSESSED, same `_signature` as the primary), *dissent* (ASSESSED with a different `_signature`, or ABSTAIN) or *no result* (TIMEOUT, ERROR, UNAVAILABLE, in flight at the deadline, or not run). **If the primary is ASSESSED, its result is the final result and is never replaced by a reviewer's content:** ≥1 confirm and no dissent → primary result unchanged, `review_outcome: CONFIRMED`; any dissent → ABSTAIN, reason `ROUTING_REVIEW_DISSENT` (`ROUTING_FINDING_DISAGREEMENT` may be kept for the ASSESSED-different case), `review_outcome: DISSENT`; no reviewer finished → **primary result stands**, `review_outcome: INCOMPLETE`. **If the primary is not ASSESSED** (error, timeout, ABSTAIN, unavailable or not run for budget), reviewers are the fallback as today: the first ASSESSED reviewer in precedence order (reviewer-0, then reviewer-1) becomes the result, `review_outcome: FALLBACK`; two ASSESSED reviewers that disagree → ABSTAIN `ROUTING_FINDING_DISAGREEMENT`; none ASSESSED → UNAVAILABLE `ROUTING_DEADLINE_EXHAUSTED`, `review_outcome: NONE_AVAILABLE`. No review triggered → `review_outcome: NOT_TRIGGERED`. The same rule applies whatever triggered the review (risk reasons or the seeded audit). Record `review_outcome` and each reviewer's verdict (confirm/dissent/no result, with model, status and reasons) in the result's `routing` block and the round log; add any new reason code wherever the result schema checks reason codes. Apply the same rule to the legacy AIand-first branch (`routing.py:335-358`) or record why not. |

Proposed DEV-22 row (implementer adjusts the numbers to what is built):

> **Area:** Evidence loop time budget. **Declared:** "The loop is capped at 6 calls and 60 s per decision."
> **v1 behaviour:** Still ≤ 6 tool calls. The routed assessment has a 180 s per-decision budget: the primary
> evidence loop keeps ≤ 60 s, and the two independent reviewers run in parallel with their own shares.
> **Reason:** Hosted high-effort reviewers take tens of seconds per step; with a shared 60 s budget the first hosted
> job ended UNAVAILABLE although the primary assessed (IDEA-066 PC-DEPLOY02). **Evidence:** IDEA-083, IDEA-066.
> **Status:** DRAFT until the Oct 26 freeze.

## Prospective pass criteria

| ID | Criterion |
|---|---|
| AB1 | Clarified against B11: primary **not ASSESSED** after18s, reviewer-0 needs34s and ABSTAINS, reviewer-1 needs10s and ASSESSES: the180s path returns reviewer-1 / FALLBACK. The historical60s serial path has only8s left for reviewer-1. The originally observed **ASSESSED** primary plus ABSTAIN review is DISSENT under AB13, never reviewer replacement. |
| AB2 | A reviewer that never answers cannot starve the other: reviewer-0 stalls past its allowance, reviewer-1 still gets its full allowance and its result is used. |
| AB3 | Both reviewers are dispatched before either finishes (parallel), and the combined result is identical for every completion order (B4). |
| AB4 | Primary capped at its share: a primary that would run 70 s is cut at ≤ 60 s, then reviewers still run with their own allowances. |
| AB5 | Concurrency accounting: two parallel AIand POSTs near the trial UTC-day/total limit, and with the accounting quarantine set, are each refused or admitted exactly as the sequential rules require; OpenAI reservations/settlements/UNKNOWN unchanged. |
| AB6 | Config/schema/agent/routing accept the new maximum and refuse anything above it; existing 60 s requests and configs still validate; no 60,000 ms literal remains on the routed path. |
| AB7 | Round log and artifacts contain both reviewers' I/O and in-flight records (B7); existing round-log/receiver contract tests pass unchanged. |
| AB8 | Watchdog: a cycle with every stage at its limit completes in ≤ 300 s against `cycle_timeout_seconds` 600 (B8). |
| AB9 | DEV-22 present in the register, plan.md §6.5 and G-50; release-register tests updated only for the new row. |
| AB10 | Full suite in a `requirements.lock` venv: no new failures against the base; Linux/PostgreSQL/systemd parts on the mirror (preferred) or a recorded local substitute. No golden regenerated without review. |
| AB11 | Red first: primary ASSESSED and neither reviewer finishes yields ASSESSED / INCOMPLETE, with the unchanged primary ID/content in its linked selected artifact. Isaac clarified canonical identity in AB-IMPL01: the routed envelope has its own ID. |
| AB12 | Confirming review never overrides the selected primary artifact: its result ID/content remain unchanged; root claims, findings, rationale and confidence equal the primary, review_outcome CONFIRMED. The root has a separate canonical routed ID (Isaac's AB-IMPL01 clarification). |
| AB13 | Dissent blocks: primary ASSESSED with a reviewer that ABSTAINs (e.g. `UNSUPPORTED_CLAIM`) or ASSESSes different findings → ABSTAIN with the dissent reason, for either reviewer and either completion order, even if the other reviewer confirms. |
| AB14 | Fallback unchanged: primary ERROR/TIMEOUT/ABSTAIN/budget-refused → first ASSESSED reviewer by precedence; both ASSESSED and different → ABSTAIN; none → UNAVAILABLE. Matches the observed 86b1476 and seq-19 cases. |
| AB15 | Full matrix: primary {ASSESSED, ABSTAIN, ERROR, TIMEOUT, not run} × reviewer-0 {confirm, dissent-different, dissent-ABSTAIN, timeout, error} × reviewer-1 (same set) × both completion orders gives exactly the B11 table; `review_outcome` and per-reviewer verdicts are in the round log; the result validates against the consumer schema. |

## Deployment notes

- Needs a new release. Because `runs` allows one run per wallet (IDEA-066 PC-DEPLOY01-B1), a new build on the dev
  wallet needs another trial database (`larp_trialN`) unless reviewed version-switch support lands first. Combine
  with the Oct 20 profile swap if possible, so there is one redeploy. Procedure and scripts:
  `docs/build/ops/llm-trial-20261018/` on PR133's branch.
- Must land before the Oct 26 freeze / Oct 27–29 final activation; no changes during the scored run (F-114, F-117).
- Changing the build mid-trial splits the unsigned trial's measurements; Keith records the boundary.
- After deployment, check the first triggered review on the host: both reviewers dispatched together, stage
  latencies, combined status, settled charges and receiver `STORED`.

## Open questions for the implementer/reviewers (not decided here)

- Should a late provider reply after the deadline be recorded and its real cost settled instead of keeping the
  conservative maximum?
- Expected AIand cost increase: parallel review calls both reviewers on every triggered job, where today GLM runs
  only when Kimi is not ASSESSED (Keith: affordability).

## IR179-RV01 — Isaac runtime review: prospective verification (2026-10-19)

Requested scope: Isaac reviews runtime timing/concurrency; Keegan retains
implementation, Keith model-protocol/affordability review and Yao deployment.
Review target PR179 head5557824; application baselineea25b52325656a19b29e8ddb07b94dd792be6e18
is unchanged by that design-only PR. This review does not adopt a new policy,
modify runtime/defaults, sign, access providers or change AWS.

Write these review pass criteria before running any tests:
- Trace all producer/consumer deadline checks, actual deferred worker ownership,
  audit writer, global tool accounting, result identity and main-thread gates.
  Distinguish a demonstrated existing contract from hazards introduced by the
  proposed concurrency; do not claim parallel code has been implemented/tested.
- Run the already-pushed focused routing, provider, trial/pacing accounting,
  signed-model/safety/restart and watchdog tests against this exact source,
  using synthetic external adapters and disposable local PostgreSQL only.
  Record counts/skips/environment; no full-suite/new180s-path/host acceptance.
- Findings name source lines, consequence, required change, owner and a
  prospective acceptance case. In particular address AB1/B11, append-chain
  serialization, deadline versus provider cleanup, six-tool-call accounting,
  deterministic combination/result identity, late usage and watchdog headroom.
- Keep model effort/prompt/routing/account identities and Yao's B11 semantics
  unchanged; do not silently resolve a policy/identity ambiguity on his behalf.
  Retain uncertainty charges, trial stops and all signed safety/recovery gates.
- Deliver the runtime review in its own PR based on179; leave the implementer
  concrete obligations and record the linkage in PR133. No vendor/teammate
  message, production credential, wallet/API call or AWS action is part of it.

### IR179 findings and implementation obligations

**Disposition:** direction is reviewable, but runtime acceptance is withheld.
PR179 has no implementation to approve. The following are concrete integration
requirements against the current source, not claims that a future parallel
implementation has already failed. Keegan owns fixes and new red-first tests;
Isaac owns review of their runtime evidence. Yao's B11 choice and the declared
model efforts remain unchanged.

**IR179-01 / P1 — stage deadlines must not wait for provider cleanup.**
`routing.py:297–298` uses `EvidenceAssessor.assess(wait_for_worker=True)` on the
signed lane; `agent.py:230–235` sets cancellation at the stage timeout and then
joins the actual provider worker without a time bound. Consequently the routing
caller cannot launch the next stage merely because the primary's allowance
expired. Existing OpenAI pacing tests explicitly reproduce a held primary lane
and no reviewer dispatch until it exits. Raising numbers or parallelizing only
the reviewer loop does not fix this coupling. Separate the immutable stage
result deadline from ownership/draining of its real worker. Permit independent
review stages at the primary cutoff within the same bounded owned group, while
keeping all late workers fenced. Never drain a group or a ThreadPoolExecutor
context on the safety thread, release its single-flight fence early, or allow
successive jobs to accumulate orphan workers. If cleanup can exceed the decision
budget, report it separately instead of asserting decision+cleanup was bounded.
Acceptance: a blocked primary outlives its share, both reviewers still start in
time, the combined result is frozen by the original deadline, safety ticks keep
running, and no second assessment group/ACK/retry occurs until owned writes end.

**IR179-02 / P1 — the deferred audit chain currently has one writer.**
`deferred_models.py:78–94` reads the current chain head, computes a successor,
then appends/fsyncs without a lock; its comment explicitly assumes one writer.
`submit:111` supplies that same callback to all stages; `AuditedModel.step`
emits request/response events from each provider worker. Two parallel reviewers
can read the same predecessor and append sibling successors; `_read` then
rejects the chain during ready/restart. This is a source-proven concurrency
hazard, not a newly reproduced failure on the existing serial path. Serialize
the complete head-read/hash/append/fsync transaction or route events through one
owned writer. Preserve durable request-before-dispatch and response-before-final
publication; RESULT/ACK cannot race a late callback. Acceptance: barrier-driven
simultaneous reviewer callbacks, fsync/write failure, two completion orders and
restart yield one valid chain with all stages, or fail closed without ACK.
No provider exception/credential text may leak into failure events.

**IR179-03 / P1 — reserve the six tool calls before concurrent use.**
`routing.py:277–299` computes each stage's allowance from a shared `tools`
counter and updates it only when that stage returns. Naively running the current
closure twice concurrently gives each reviewer the same remainder: after three
primary calls, each can receive three more, exceeding six globally. Specify a
deterministic partition or a properly synchronized shared dispatch budget with
defined allocation semantics; primary stays at most three and total at most
six, including timed-out workers. An output counter after the fact is not an
enforcement boundary. Freeze allocations before dispatch or explain how race
order cannot change the permitted evidence budget. Acceptance: simultaneous
reviewer tool requests at the last token, cancellation and late completion cannot
overspend/reset the global allowance in either finish order.

**IR179-04 / P1 — clarify AB1 and canonical result identity before coding.**
AB1 does not state the primary's status, but recreates the hosted ASSESSED
primary example and expects reviewer-1 to win after reviewer-0 ABSTAINs. Under
Yao's B11/AB13, an ASSESSED primary plus any reviewer ABSTAIN means DISSENT and
ABSTAIN. Make the fallback witness explicitly non-ASSESSED at the primary,
and add a separate observed-case dissent witness; do not override B11 to pass
AB1. AB2 must similarly distinguish fallback, confirmation and dissent.

AB11/AB12 also require the final primary `result_id` to remain identical.
Current `_combine` (`routing.py:360–415`) removes that ID, changes router/model/
assessment-key and I/O metadata, and computes a new result ID. Downstream
`gate.accept:83–89` deduplicates on result_id or assessment_key. This is an
identity contract change, not solved by only avoiding `chosen = reviewed`.
Specify whether primary identity is the root ID or a separately pinned selected
primary inside a canonical routed envelope, with Yao's clarification if AB12
must change. Do not claim the present consumer recomputes/checks this digest:
it does not. Acceptance must test exact unchanged semantic primary fields,
original artifact/ref, final identity/hash conventions, consumer validation,
duplicate acceptance/restart and dissent stripping. Wait for all applicable
reviewer outcomes or their fixed cutoff; first-completion wins is invalid.

**IR179-05 / P1 — propagate absolute budgets through every boundary.**
The two intelligence configs, `config.py:60`, `schema.py:37`, the agent validator
and `routing.py:274` must agree. Today an out-of-range routed deadline falls
back to the routine assessor, so partial updates can silently select a different
route or refuse the request. Driver request production (`driver.py:878`) also
uses the configured maximum. Start from one decision deadline; stage allowance
must be bounded by remaining time and its own cap. At180s, primary is at most60s;
at120s, B2's one-third rule makes it at most40s. Existing60s inputs must still
validate; their shares must follow the recorded contract, not a hidden old
half-budget shortcut. Use monotonic elapsed time for bounds, recheck cancellation/
remaining time immediately before each new model/tool dispatch, and include
preparation/accounting/audit overhead instead of gifting it a fresh relative
HTTP timeout (`providers.py:351–362`). Expired authority must never start a POST.
Acceptance: all config/request/stage boundaries, exact-equality/above-limit,
preparation crossing cutoff, clock rollback and late re-quote remain bounded.
Assessment budget changes do not extend trade/quote/signing windows (#27).

**IR179-06 / P1 — late audit/cost evidence must not revive decision authority.**
Keep current conservative accounting as the default until any late-cost change
is separately reviewed. `providers.py:365–370,393–396` treats a complete late
reply as TIMEOUT while preserving safe raw bytes. `BudgetedOpenAI.step` settles
non-OK usage conservatively; `model_budget.py:383–390` permits settlement only
from RESERVED, so an UNKNOWN charge cannot simply be settled again with the
existing method. Audit/usage capture and policy authority are separate: a late
answer cannot replace a frozen result, change the limiter, refresh request
identity/cutoff/expiry, or clear an uncertainty charge. Any proposed late actual-
usage reconciliation needs an explicit trusted, idempotent same-charge/same-
dispatch-day transition; absent proof, retain the original maximum and latch.
Parallel AIand calls still run the real trial/accounting guard at each POST
boundary. This guard enforces OpenAI-account stop/window/quarantine semantics;
it is not an AIand-dollar reservation or a proof of AIand affordability. Keith
retains that cost review. Test midnight, concurrent admission, UNKNOWN/crash,
settlement failure and a late response while the other reviewer is completing.

**IR179-07 / P1 — retain signed main-thread authority and recovery.**
Signed runtime already uses `DeferredAssessments` (`service.py:343–350`);
`driver.py:1006–1060` consumes ready results on the main thread, then runs safety
planning while the one model lane is busy. Background workers supply evidence,
not orders, reservations or projection changes. `schema.assessment_result` and
`gate.accept` still check original run/job/profile/context/cutoff/expiry before
acceptance. Preserve that architecture; do not move reviewer waits/aggregation
onto the safety lane or accept an expired/stale result merely because B11 says
an ASSESSED primary stands. Retain current build/profile/run identity fences,
no automatic paid replay after restart, complete audit-before-ACK and verified
result-before-limiter mapping. Acceptance: mandatory reduction/terminal/HALT,
execution reconciliation, heartbeat and accepted-cut outage behavior continue
with both reviewers hung; restart replays no paid calls or additional actions.

**IR179-08 / P2 — prove the composite cycle bound, not stage arithmetic.**
60s plus two parallel90s shares is nominally150s, not evidence that a cycle
finishes within300s. Unsigned coordinator assessment is synchronous
(`coordinator.py:149–158`); signed assessment is background work and must not
be charged as a blocking safety wait. `Service.run:77–86` wraps guard+driver+
heartbeat in the watchdog, and `RoundDriver.once:970–979` can perform balance/
market/day-roll work before model handling. Include I/O, audit locks/fsync,
queue/verification/aggregation, provider cleanup and multiple market refreshes
in the relevant timing tests. A600s watchdog exits the process; it neither
cancels a stage nor establishes the300s target. Test both lanes with real-time
blocking adapters and fake-clock boundary cases; a fast fake clock alone cannot
prove worker liveness. Yao retains actual host latency/first-triggered-review/
charge/receiver-ACK evidence after Keegan's exact reviewed release. No watchdog
increase, model-effort reduction, trial-ledger reset or AWS change is needed to
write these tests.

### Required evidence before Isaac's runtime acceptance

| Area | Evidence Keegan supplies after implementation |
|---|---|
| Deadlines / worker ownership | Updated AB1–AB4/AB6 with real blocked workers; explicit result cutoff versus drain state; bounded owned groups and no post-cutoff dispatch |
| Concurrent audit / tools | Serialized hash chain and restart/failure cases; globally enforced six-call budget under simultaneous tool attempts |
| B11 / identity | AB11–AB15 in both completion orders, preserved primary content/selected identity contract, validated canonical output and consumer dedup/recovery |
| Accounting / late I/O | AB5/AB7 including UTC rollover, UNKNOWN/quarantine, safe late audit and accounting behavior without late trade authority |
| Signed safety / watchdog | Both reviewers blocked while mandatory planning/heartbeat/execution continue; AB8 full-cycle evidence at current600s watchdog |
| Scope / release | Existing prompts/efforts/routing hash and caps unchanged; DEV-22/parity updates; full exact-source Linux/PostgreSQL/systemd/release checks under AB9–AB10 |

This completes the static runtime review scope, not implementation acceptance.
The review does not settle Keith's affordability question or Yao's late-cost/
identity choices. Keegan implements the recorded contract and addresses these
findings; Isaac reviews the resulting evidence; Yao deploys/qualifies afterward.

### IR179 current-path verification result

At pushed review commit730c99e (application/config/deploy/tests identical to
integrationea25b52), the focused suite passed **129 tests,120 subtests,0 skips**,
14.32s. Environment: macOS ARM64, Python3.12.14, fresh external venv populated
from `deploy/requirements-test.lock`, disposable PostgreSQL14.24. Command:

```sh
LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55447/larp_test \
  /private/tmp/larp-pr179-review-venv/bin/python -m pytest -q \
  tests/intelligence/test_aiand_routing.py \
  tests/intelligence/test_openai_pacing.py \
  tests/intelligence/test_trial_caps.py \
  tests/intelligence/test_providers.py \
  tests/runtime/test_signed_models.py \
  tests/runtime/test_final_review_d.py::Watchdog -p no:cacheprovider
```

Retained log: `/private/tmp/larp-pr179-runtime-review-tests.log`. The original
old temporary venv had no pytest, so its attempted command ran no tests; a new
pinned venv was created before the actual successful run. No assertions or
source were changed to obtain this result. Existing inner-provider-timeout,
single-lane ownership, main-thread mandatory/HALT safety, model outage limiter,
restart audit, concurrent SQLite reservation, UTC-day/UNKNOWN/quarantine,
transport deadline and watchdog cases pass on the existing serial routed code.

These tests do not implement or accept the new180s budget, simultaneous reviewers,
concurrent deferred audit callbacks, B11 outcome/identity changes, new AB1–AB15,
full composite300s timing or actual host behavior. IR179-02/03 are source-traced
hazards of naively parallelizing the serial design, not reproduced failures of
the current serial routing. No full suite, Linux/systemd, provider/account,
release bundle, deployment or signed-wallet qualification is claimed. The
completed deliverable is Isaac's static runtime review plus current-path checks;
Keegan still supplies corrected design/implementation and new red-first evidence
for runtime acceptance. No production credentials, paid calls, model effort/
prompt changes, new lifetime/caps, official uploads, AWS or wallet action.

IR179 delivery: [PR180](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/180)
is OPEN/non-draft/mergeable against PR179's unchanged5557824 design branch;
Keegan can merge the review before implementing. PR133 records Isaac's design
review as delivered at1ba0414, with future implementation/runtime/host acceptance
still open. No review of nonexistent implementation is claimed. Remote runtime
job117859512110/run39189676522 at6ab83cb ran zero steps; annotation confirms
failed payments/spending-limit (#98). Local129/120 verification is separate
from this CI blocker. The temporary local PostgreSQL container was stopped and
disposed. All review changes are documentation only; no app/config/test files
or model/account state changed.

## AB-IMPL01 — Isaac takes over Keegan implementation (2026-10-19)

User explicitly asks this session to do Keegan's task as well. Implement on a
separate branch containing179+180; no deployment/AWS/provider calls. Record
and push new red tests first. Preserve model efforts/prompts/routing bytes,
transport accounting guards, UNKNOWN charges and signed main-thread authority.
Fix AB1 by making fallback-primary status explicit; the observed ASSESSED
primary plus ABSTAIN reviewer remains DISSENT, per Yao's B11. Keep legacy
AIand-first selection semantics separate and documented; B11 changes the
OpenAI-preferred path for which it was approved, not historical v1/v2 trial data.

Implementation criteria: central180000ms ceiling in configs/validators; primary
min(total/3,60000), each parallel reviewer min(remaining,90000). Independent
cancellable task handles separate cutoff snapshots from actual worker cleanup;
one owned assessment group fences timed-out workers through audit completion,
including unsigned callers. Serialize deferred audit appends. Deterministically
reserve primary tool allowance and partition only safe remaining calls between
reviewers, never exceeding six including late workers. Propagate an absolute
worker deadline to provider dispatch after payload/accounting preparation.
Preserve late cost semantics (TIMEOUT/UNKNOWN, no refund or decision resurrection).
B11 matrix and original primary semantic content are immutable; root versus
selected result identity uses the separate routed envelope and linked unchanged
primary artifact explicitly selected by Isaac below.

Red witnesses in tests/intelligence/test_assessment_budget.py cover config/stage
limits, B11 status matrix, real concurrent reviewer dispatch, review dispatch
after a primary timeout while the actual worker/lane remain owned, and concurrent
hash-chain callbacks. After pushed implementation, run these plus existing
routing/accounting/provider/signed/restart/watchdog checks, then the full pinned
suite with local PostgreSQL. Review any required golden changes explicitly;
never regenerate blindly. Declare DEV-22 and train/serve budget parity. Full
Linux/systemd/original release and hosted acceptance stay separate owner gates.


AB-IMPL01 RED at pushed2ecb3a1: all6 targeted tests failed (3.81s), including
actual concurrent audit hash mismatch, lack of simultaneous reviewer dispatch,
and reviewers starved until a blocked primary exits. Other failures demonstrate
old config ceilings and absent new budget/B11 contract helpers. Log retained at
/private/tmp/larp-idea083-red.log. The live config remains refused while its
independent parameters are unset; numeric ceiling tests use development/shadow
instead of bypassing those existing live gates.

Isaac explicitly selected the recommended identity contract in this session:
separate canonical routed-envelope ID, with unchanged primary ID/content linked
as an original artifact. This clarifies AB11/AB12's wording: semantic primary
fields and selected-stage identity are preserved, not the envelope ID itself.
B11 behavior is unchanged. No optional answer or named teammate endorsement is
inferred. Default late usage remains TIMEOUT/UNKNOWN/conservative, not refunded.

AB-IMPL01 golden review at pushed f3cf851: generated candidates outside Git.
Structured comparison found exactly23 changed leaves in the thesis-revision
trace and17 in the abstention trace: config_sha256 and its dependent assessment,
result, falsifier, review-job, persisted-batch and gate/feature references only.
Claims, findings, source spans, tools, model I/O, rationale, confidence, timestamps,
status, gates and thesis semantics are unchanged. Accepted these reviewed bytes;
no blanket golden regeneration. The deliberately explicit historical60s demo
fixtures remain comparable; the research evaluation entry point now requests
config.max_deadline_ms (180s), matching the runtime request builder. The six-call
cap and provider settings stay unchanged. No research quality/affordability
claim follows from these synthetic acceptance checks.

AB-IMPL01 initial full regression at3872856:2068 passed,9 expected platform/
external skips,3265 subtests,7 failures (274.72s). Failures identify old60s
boundary/reason expectations, serial-review preparation expectations, the copied
strategy producer fixture, and synthetic evaluation still using v2's frozen60s
ceiling and70s timeout script. Preserve v1/v2 threshold files unchanged; freeze
v3 before its first run, copying every quality threshold and changing only the
elapsed ceiling to180000 under B9/DEV-22. The synthetic timeout witness becomes
190s so it still exceeds the declared budget. This is a budget-parity change,
not a relaxation of precision, abstention or quality criteria. Re-capture the
strategy fixture's request/result from the reviewed golden, binding its producer
commit to f3cf851; its semantic fields remain unchanged as above. Update exact
boundary (180001), hard-deadline reason and two-reviewer assertions accordingly.

Additional pushed acceptance at4ad4044:11 assessment tests/257 subtests PASS;
18 runtime tests/5 subtests PASS, including both real reviewer workers blocked
while the PostgreSQL-backed mandatory-reduction planner, CLOCK HALT and
reconciliation continue; restart retains the result without another paid call.
The composite substitute uses actual stage tasks/transports, SQLite accounting,
artifact checks, concurrent audit fsync, PostgreSQL guard/heartbeat and the real
Service watchdog, with 1:100 timing and explicit bounded balance/market/day-roll/
quote delays. Both unsigned synchronous and signed-background cycles complete
inside the scaled300s target with a scaled600s watchdog; no watchdog increase.
This measures the local injected boundary contract, not production I/O maxima
or actual host latency. Host measurement and exact Linux/release acceptance
remain Yao/Keegan gates.

AB-IMPL01 finalization race found in source review: a stage may finish its
verified result before its deadline yet still own its worker during final
context cleanup. Red witness pushed8e2c989 blocks that finalizer after logical
completion: the old Task.result incorrectly returns UNAVAILABLE (1 failed,
0.41s). Completion eligibility must use the saved on-time terminal marker;
actual worker lifetime still fences new groups/audit ACK. Add this regression
and the stalled reviewer-0/successful reviewer-1 fallback witness to final
acceptance. Neither changes timeout accounting or permits late content.
