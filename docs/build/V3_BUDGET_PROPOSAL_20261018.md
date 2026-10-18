# V3 budget and stop proposal — KMP-BUD01

2026-10-18 UTC. Keith proposal for Keegan's confirmation on #97 / PR #133.
Criteria were pushed at `1536af8` before this analysis. **Not adopted or initialized.**
The confirmed v2 TR-AC2 protocol remains historical and unchanged. A new v3
window needs its own confirmation before its first routed assessment.

## Routing, prompts and window reviewed

Reviewed PR #167 at `f20e941801230c183bd5b849434bffd095a8ceaa`, merged into
integration at `4312cd17f212df9f370a2c802bb17ff85d3d0250`.
[Source hashes](evidence/model-prerequisites-20261018/source-review.json) bind the
config, core/stage prompts, routing, provider, budget and predicate implementations.

V3 tries `gpt-6.1-sol` / medium first, with half the shared assessment deadline
(30 of 60 seconds) and at most three retrieval calls. Event/red-flag/incomplete
cases and the frozen audit sample require independent AIand review. Failed
primary work also falls back to Kimi K3 high, then GLM-5.3 high. A verified
disagreement abstains; required review cannot inherit a clean finding on failure.
All stages share six tools/ten steps and the overall deadline. This is source
behavior, not measured provider availability, latency or accuracy.

The primary and reviewer appendices preserve the core assessor contract, request
original evidence, distinguish actuality/issuer/time/negation and require
verifiable spans. Reviewers are not shown the primary response. The wrapper
prompt lookup was corrected in #167. Hashes include the unchanged routine prompt
although it is not the preferred primary. Keep complete composed prompt and
all stage I/O in audit artifacts. A prompt review does not establish M9 recall.

Local review evidence from the #167 review: focused 67 tests / 70 subtests;
broader 388 passed, 1 external-data skip / 1,126 subtests on Python 3.12.14.
Two initial loopback-permission failures passed on the permitted rerun. Hosted
Actions could not start because of account billing/spending limits (#98).
These are offline results, not hosted or real-provider qualification.

**Outstanding KMP-P2:** a call admitted just before pacing `end_ms` can dispatch
at/after it: the provider wrapper rechecks the assessment deadline, but not the
pacing boundary after reservation. The synthetic review admitted at end−1 ms,
advanced 1 ms, and observed a POST at end and an ASSESSED result with
`OPENAI_PACING_WINDOW_ENDED`. A dispatch-boundary recheck/refund regression is
needed if end means no new OpenAI dispatch. Until fixed, do not represent the
example as enforcing that stricter contract. This finding survived the requested
merge; this documentation PR does not remediate application code.

## Proposed allocation — no permanent reserve

| Field | Proposed v3 value / provenance |
|---|---|
| Total | US$50 = 50,000,000 micro-USD |
| Already spent | Exactly US$2 = 2,000,000 micro-USD, from the owner's report of exactly US$48 remaining (PC-BUD03); not a fresh billing API measurement |
| Reserve | **US$0 permanently withheld** |
| Remaining at that report | US$48; subtract every subsequent charge/reservation/unknown before spending |
| Example start | 2026-10-18 11:00 UTC (`1792321200000`) |
| Example end / budgeting horizon | 2026-11-13 00:00 UTC (`1794528000000`), exclusive; a budgeting horizon, not an organiser-confirmed scored cutoff |
| Release period | 86,400,000 ms; 26 periods, including the final partial period |
| First cumulative release | floor(48,000,000 / 26) = 1,846,153 micro-USD |
| Period k cumulative release | floor(48,000,000 × k / 26), k=1..26, capped at US$48 |

The window is 25 days 13 hours. Its average available charge is about US$1.879/day;
the first equal-period release is US$1.846153. Unused released credit carries
forward, and the last period releases the remainder. The US$48 is eligible to
be used within the window; there is no separate unused US$10. Pacing is a
ceiling, not a goal to spend all credit. Quotes of catalogue prices cannot show
that the intended OpenAI-primary workload fits this ceiling.

Freeze the actual start/end and their hashes before the first v3 job. If the
start changes, recompute the allocation explicitly. Never move a running window
to replenish it. Existing v2 ledgers require the reviewed `enable-pacing`
migration, preserving settled/reserved/unknown charges and latches; do not
delete/reinitialize the ledger or turn a prior spend into new headroom.

## Proposed trial stop limits and verdict

Keegan is asked to confirm the following as a **new v3** protocol, retaining
TR-AC2's M1/M2/M5/M9 coverage and ordered outcomes, frozen sampling and 72
observed unsigned hours / 20 unique completed jobs. Signed hours never count.
The planned unsigned cutoff remains Oct22 00:00 UTC; a later start or earlier
signed rehearsal may make a supported unsigned verdict impossible. Report that
as inconclusive rather than extending or relabelling observations.

| Stop / admission bar | Proposed action |
|---|---|
| New OpenAI trial charges reach US$8, or any UTC day's reach US$2.50 | Stop that experimental window (K1). Reserve conservative maximum in-flight cost before dispatch so it cannot cross the stop while a monitor sleeps. Count all attempts, failures, retries, probes, RESERVED and UNKNOWN, not only accepted results. These temporary experiment limits do not withhold a permanent reserve. |
| OpenAI account would exceed US$50 cumulative, or a request exceeds released pacing allowance | Refuse that OpenAI admission and use the reviewed external fallback. Normal pacing refusal is expected routing behavior; it is not proof of provider failure or affordability. Report primary share and fallback load. |
| Credit/account latch, understated charge/reservation, unexplained billing delta or clock/accounting fault | Stop OpenAI spending; reconcile against provider usage. UNKNOWN remains charged at its conservative reservation until resolved. Do not clear a latch to keep the experiment going. |
| Existing K2–K4 identity/effort, verification/audit or safety condition | Stop the affected experiment and retain its evidence. Do not route around a safety/identity refusal and still count the original path as passing. |
| External account cannot conservatively fund the next request or has unverified billing units | Pause paid evaluation, record unavailable/missing evidence. AIand is not an unlimited fallback. |

A demonstrated kill/safety defect means NOT_SUPPORTED; otherwise missing hours,
routes, labels or reconciled costs mean INCONCLUSIVE; with sufficient evidence
any required M1/M2/M3/M5/M9 miss means NOT_SUPPORTED; only all passing required
bars support the tested unsigned scope. Planned fallback does not waive those
availability/quality bars. Earlier v2 data retain v2 bars and are reported separately.

The US$8/US$2.50 sublimits require host admission/monitoring with in-flight
headroom; #167 implements account/pacing admission, not these experimental
operator sublimits. Yao records the enforcement method before the first job.
If that method cannot enforce the caps, paid v3 testing waits for a reviewed
implementation. This is a proposal, not a claim that a daily report enforces it.

## Measurement and forecast procedure

**Current result: NOT_MEASURED; affordability is unqualified.** No immutable v3
job population, actual usage export or reconciled charge ledger was supplied.
No paid inference was initiated to fill that gap. AIand “140+” is owner-reported;
the account's currency/credit conversion, expiry and current balance still need
confirmation. Public catalogue USD pricing does not verify that balance.

Yao supplies a private, cutoff-bound export containing every request/attempt's
assessment/stage ID, model/effort, prompt/config/build hash, UTC request/completion,
input/cached/reasoning/output usage, rate and currency, reservation and settlement,
failure/retry outcome and provider invoice/usage totals. Include direct calls
outside the router. Hash the export and reconcile every delta; no credentials
or model/label payloads go into Git. Report no-call and stopped periods as well.

For the report at t, use cumulative charge `C(t)` including the US$2 prior spend,
settled charges and conservative unresolved/in-flight amounts. After at least
24 observed hours, define daily rate `r` as the larger of the maximum complete
observed rolling-24h charge and new trial charge over observed hours scaled to
24h (exclude the fixed pre-window US$2 from the rate). Report
wall-clock gaps and pacing censorship; neither paused hours nor missing jobs
prove a lower intended demand. Use a separately recorded workload forecast if
the remaining schedule/source rate is higher than observed. Proposed margin:
25% over that conservative future rate; extra probes/labels/rehearsal calls are
explicit additional spend, not silently omitted.

`F_OpenAI = C(t) + 1.25 × conservative_future_daily_rate × remaining_days + extra_calls_budget`

Require `F_OpenAI ≤ US$50` and measured intended-primary demand compatible with
the period allowance to call the proposed primary share affordable. Equivalently,
at the owner's balance report, future total spending has at most US$48 headroom.
If pacing has suppressed demand, report the observed cost plus the censored
primary requests and cost estimate separately; “we never exceeded pacing” is
not an affordability result. Before 24h, estimates remain provisional.

Forecast AIand separately from actual reconciled charges and fallback/review
mix, with the same 25% margin and planned-extra-call accounting. Require confirmed
balance/unit conversion to exceed its forecast. Report cached-input assumptions,
taxes/FX and all uncertainty explicitly. Public Oct18 rates: OpenAI Sol standard
US$2 input / US$10 output per million; AIand K3 US$3 / US$12.50, GLM-5.3 US$1 /
US$4, with separate cached rates. Full reasoning/tool loops and unsuccessful
attempts can cost more than a single completed reply. These are reference rates,
not measured spending or account entitlements; captured sources are in the
[provider register](MODEL_PROVIDER_RIGHTS_20261018.md).

Keegan confirms window, limits, margin, cutoff meaning and protocol ID on #97
before Yao prepares/initializes the new release. Keith then issues measured
interim/final forecasts from Yao's export. No affordability verdict is granted here.
