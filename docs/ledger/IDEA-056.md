# IDEA-056 — Experimental model routing with funded external models and OpenAI credit fallback

- Date / author: 2026-10-15 SGT / Keith's proposal, documented with Codex.
- Status: **open — proposal only; not adopted, implemented or run.** Documentation and review only: no adapter, model call, routing configuration, service declaration, wallet action or deployment in this change.
- What: assess routine company-disclosure evidence with a funded external model such as Kimi K3 or GLM-5.3; selectively escalate difficult cases to a stronger OpenAI model; automatically route all LLM assessment traffic to external models if OpenAI credits become unavailable.
- Why it might help: reserve OpenAI inference for ambiguous evidence while retaining independent verification and a complete external route for credit exhaustion. This is a hypothesis about assessment quality, availability and resource use, not a profit claim.
- User constraints: **Kimi K3 and GLM-5.3 are funded separately and treated as the low-cost tier. Their prices are outside this comparison.** Preserve a **$10 OpenAI reserve across development, activation and the scored run**, from $50 of OpenAI credits. No implementation in this PR.
- Links: [IDEA-041](IDEA-041.md) B8/bake-off; [IDEA-049-A](IDEA-049-A.md) A-DEC-001/002 and real evaluation; [IDEA-050](IDEA-050.md) driver; GAP-23/24/57/62/67; D-03, G-03/G-06/G-50 and SKILL.md F-117.

## 1. Present implementation and scope

Reviewed base: `main` at `e410e49966d2d609185513cacfa0b986bf10ec99` (PR #81 promotion).

- `config/intelligence/prompts/assessor.v2.txt`: the model assesses one issuer's evidence, chooses bounded tools and returns source-backed claims. It has no trading authority.
- `larp/intelligence/agent.py`: verifies claims, computes findings/thesis state and enforces the assessment deadline/tool ceiling.
- `larp/intelligence/providers.py`: existing hosted adapters target OpenAI and Anthropic. An OpenAI-compatible external API is not an implemented adapter.
- `larp/runtime/service.py:build_driver`: still composes `RuleBaselineModel` and refuses a hosted assessor as not integrated.
- `larp/intelligence/bakeoff.py`: engineering comparison; baseline agreement is not independently measured accuracy. `realeval.py` is a separate real-label gate.

This is a proposal for a future, separately authorized experiment. It does not implement DR-11, select a live model, grant evidence authority or close a deployment GAP.

## 2. Candidate roles, including external models

"Low-cost" describes the user-funded routine tier, not model size, public prices or a claim that every endpoint supports no-thinking mode.

| Role | Candidate | Proposed setting and remaining check |
|---|---|---|
| Routine external assessment | **Kimi K3** (the user's `kimik3`) | Verify exact endpoint/model identity and supported lower-effort mode. Its launch article described max effort at launch; that does not establish current low-effort API support. Evaluate a supported setting under the same total deadline. |
| Routine external assessment | **GLM-5.3** | Candidate at low effort, subject to checking the selected endpoint's current schema/parameter behavior. Do not silently substitute GLM-5.3-Flash. |
| Stronger escalation | **GPT-6.1 Sol** | Start with medium; a frozen rule may request high for conflicting/complex evidence. Record the exact served model, effort and prompt. |
| External-only operation | Kimi K3 and/or GLM-5.3 | Handle **both routine and difficult assessments**, using a declared stronger supported effort or approved external alternative for the latter. Evaluate this route directly. |
| Optional comparator | GPT-6 Luna low / GPT-5.4 mini low | Experimental arms only, not default replacements for the funded external tier. |

No candidate is selected or invoked here. An external model fills a role only after that configuration passes evaluation. Additional providers need a reviewed candidate record; arbitrary endpoint switching is not proposed.

## 3. Which judgments use which tier

| Task | Routine external tier | Escalate when |
|---|---|---|
| Extract stated revenue, income, margin or EPS, unit and period | Explicit values with exact source quotes | Tables/footnotes, unclear scale, ranges versus levels, multiple periods or scope changes |
| Classify reported results versus guidance | Clear actual/forecast wording | Mixed clauses or conditional guidance |
| Classify an event statement | Explicit occurrence, risk, forecast or announcement | Complex negation, disputed allegations, indirect wording or contradiction |
| Identify actor and timing | Explicit issuer/third party and date | Subsidiary/supplier attribution, pronouns, discovery versus incident versus disclosure date |
| Select an allowed evidence tool | Close an explicit exhibit/prior-context/comparison gap | Several plausible comparison points or conflicting documents |
| Produce structured claims and source quotations | Routine JSON/exact spans | Verifier failure, unsupported claim or materially incomplete coverage |
| Reconcile amendments and prior filings | Simple reference retrieval | Correction/withdrawal, superseded guidance, accounting-basis differences or conflict |
| Potential Class 1/2 evidence | Preserve and extract the candidate | Always obtain stronger review before any proposed action-bearing use; independent verification and configured authority still apply |

A short sentence can be difficult: "we do not believe the previously disclosed incident materially affected operations" combines occurrence, negation, materiality and prior context.

Arithmetic, exact source-offset verification, timestamps, deduplication, configured impact/severity, session expiry, sizing, risk and execution remain deterministic. Stronger models receive no extra trading authority.

## 4. Proposed routing and omission checks

1. Code prepares point-in-time evidence, issuer identity and existing context. Filing instructions remain untrusted content.
2. The selected external routine model extracts claims and closes allowed gaps.
3. Independent checks route hard cases using metadata, existing event predicates, conflicts, coverage, verifier outcomes and explicit ambiguity. Self-reported model confidence is not the sole router.
4. The stronger reviewer reads the relevant **original source evidence**, not only the routine summary. Both outputs pass the same verifier and are retained. Unresolved disagreement yields ABSTAIN/UNKNOWN, not majority-vote truth.
5. Strongly review a preselected sample of apparently clean results too. Proposed initial DEV setting: 10%, stratified by issuer/form/event type, with a frozen seed/policy. Final-evaluation labels cover every document, including un-escalated negatives.
6. Accepted evidence follows the existing state/policy-authority path. An escalation must not erase the earlier failure from the record.

**Omission is the main risk:** valid claims can coexist with a missed adverse sentence. Schema validity and verifier acceptance do not prove completeness. Independent triggers also have blind spots; measure their recall and the clean-case audit results.

All stages share the existing **60-second assessment deadline and six-tool-call ceiling**, with bounded model requests/retries. Escalation does not receive a new deadline or tool allowance. These combined limits need future implementation and testing.

## 5. Shared OpenAI budget and complete external fallback

**User-requested behavior:** when OpenAI credits are exhausted, route **all LLM assessment traffic to external models**. This includes difficult cases normally reviewed by Sol, audits and reassessment/review jobs. The switch is automatic and declared before activation.

With an initial $50 allocation, use a **$40 cumulative OpenAI operating limit and $10 reserve for the whole development/activation/scored window**:

- Switch to external-only mode before admitting a request whose bounded cost would consume the reserve or exceed the remaining operating budget.
- An explicit provider insufficient-credit/quota refusal also triggers external-only mode, even when local accounting shows balance. Actual credit exhaustion uses the same route.
- Generic 429/timeouts/5xx are not proof of exhausted credits. Classify the provider error and use a separately frozen bounded availability/retry policy. Do not retry an explicit credit refusal indefinitely.
- External-only means the external routine route handles simple work and the registered **external difficult route** handles hard work. No OpenAI retry, background review or bake-off bypasses the common budget gate.
- Persist usage/reservations across workers, restarts, wallet changes and run IDs. The later 200 USDT final-wallet deposit does not replenish API credits or reset this allowance. Reserve worst-case costs for concurrent/in-flight, timed-out and unmetered requests; reconcile provider billing.
- Freeze an external primary/secondary order before activation. If all approved external routes fail, return UNAVAILABLE/UNKNOWN and preserve existing autonomous risk behavior. Do not relax verification, clear failed evidence, invent claims or force an execution.
- Journal switch reason, budget state, queued/in-flight work and the actual provider/model used. Already dispatched requests can still be billed; delayed billing cannot be assumed cancellable.
- Latch external-only mode for the run after confirmed credit exhaustion. No return based merely on a stale balance check. Any development-only replenishment policy needs separate specification before use; this idea requests no in-run manual model selection.

External inference is separately funded by the user. Its price is deliberately outside this comparison, but quality, availability, records and rights still apply. This documentation spends or transfers no funds.

## 6. Full-window illustration, not a measured usage forecast

Conservative planning coverage: **32 calendar dates, Oct 12 through Nov 12 inclusive**, covering development, activation and scored operation without double-counting overlapping phase dates. The official scored duration remains 14 days; this estimate does not resolve exact scored timestamps. Five issuers assessed every six hours gives `32 * 5 * 4 = 640` assessments. This is a scenario, **not the actual runtime cadence**: that setting is unset and the scheduler rotates issuers per slot. Future counts must include its filing and review jobs.

Assume **20,000 input + 4,000 output tokens per complete Sol review**, across its requests, including reasoning output. Standard $2/$10 per million input/output tokens gives `$0.08` per review ([Sol documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol), checked 2026-10-15). No caching/Batch discounts, fast modes or regional surcharges assumed.

| Share additionally reviewed by Sol | Sol reviews | Estimated OpenAI usage | Headroom below $40 | Full-window reserve |
|---|---:|---:|---:|---:|
| 10% | 64 | $5.12 | $34.88 | $10.00 |
| 25% | 160 | $12.80 | $27.20 | $10.00 |
| 50% | 320 | $25.60 | $14.40 | $10.00 |
| 100% | 640 | $51.20 | Exceeds limit by $11.20 | Requires external routing to preserve reserve |

Percentages are sensitivity assumptions, not measured rates, and include mandatory escalations plus sampled clean-case reviews. Setup, development evaluations, retries, new filings, initial backfill, extra audits and abandoned calls consume the **same $40 pool** and are excluded from these rows. At 25% review and **16,000 output tokens** per Sol review, the same inputs cost `$0.20` each, or **$32.00**, before extra work. Larger inputs increase that further. The admission/fallback policy, not the estimate, preserves the proposed reserve.

## 7. Prospective experiment and decision criteria

**No experiment is run or pre-registered by this idea.** Before any paid/API run, a separate EXP entry must freeze labels, snapshots, candidates, router, statistical method, sample sizes, code/config hashes, spend ceiling and pass criteria in a committed/pushed change. The following is a proposed protocol for review, not permission to run it.

**Hypothesis:** external-first assessment plus bounded stronger review lowers OpenAI usage while retaining required evidence quality and the common deadline; external-only operation remains usable when credits run out.

**Arms:** deterministic baseline; each external candidate alone; Sol-only; each external-first/Sol mix; **external-only fallback including difficult-case review without Sol**. Optional OpenAI routine comparators stay separate. Report all attempted calls and arms, not only successful results.

**Data:** identical rights-cleared filing snapshots and point-in-time issuer context: 8-K/6-K, exhibits, amendments, numerical comparisons, negation, future/conditional/historical events, third parties, no-event documents, long/truncated inputs and Class 1/2 cases. Independent annotators freeze labels before predictions. Keep related filing revisions together, separate DEV/router-selection from HELD_OUT and report issuer/form/event strata. A 15–25 filing bake-off can triage engineering but cannot establish non-inferiority. Sol and the rule baseline are not ground truth.

**Proposed criteria to freeze in the EXP:**

| Dimension | Required result |
|---|---|
| Omission-sensitive quality | For both mixed-minus-Sol and external-only-minus-Sol adverse-event recall, lower one-sided 95% confidence bound >= -2 percentage points, overall and preregistered critical strata. Report absolute recall and existing T01 criteria; matching a poor baseline cannot pass. |
| False action-bearing evidence | Upper one-sided 95% bound for mixed-minus-Sol false-positive rate <= +1 percentage point; zero new unsupported Class 1/2 directives in frozen safety cases. External-only must meet the same requirements. |
| Extraction | Exact value/period/unit accuracy, supported-claim precision, completeness/recall, abstentions and stale/wrong-issuer errors. Existing independent T01 thresholds remain required; schema validity does not replace them. |
| Availability | Count refusals/timeouts/abstentions in end-to-end success and recall. Terminate within the common deadline/call limits; report p50/p95/max and failure rates. |
| Credit fallback | Simulate $40 admission, explicit credit refusal, reservations racing across workers, unmetered calls, queued/restarted work and OpenAI outage. After switching, new requests use only approved external routes; hard work gets its declared review or abstains. |
| Audit/authority | Complete per-stage provider/effort/prompt/input/output/tool/cost/route trace. Same verifier and consumer contracts; no additional trade authority or false CLEAR after failed evidence. |
| Resources | Lower measured OpenAI usage than Sol-only; full-window workload/stress projection fits the shared $40 limit plus $10 reserve, including evaluation/all attempted calls. External price excluded. |

Use a paired, filing-family-aware confidence method and justify sample size/power before HELD_OUT predictions. These margins are proposed limits, not evidence-backed current performance. If sample size, labels, rights, endpoints or capability are insufficient: **inconclusive**, no adoption. A clear quality/authority/deadline/budget failure: **not supported** for that configuration. Passing supports tested assessment/routing scope only, not profitability/live readiness. Never tune on development/scored P&L.

## 8. Later integration requirements

- **Provider contracts:** exact endpoint allowlist/auth, schema/tool codec, context/tokenizer, served revision, supported effort, finish/refusal/quota semantics, reasoning/summary extraction, deadline and usage accounting. API compatibility alone is insufficient.
- **Composite identity/replay:** today the assessor has one `model.identity`. A composite must bind routine/strong/external-difficult models, prompts, effort/router policy and budget/fallback settings into the manifested identity/assessment key. Journal the realized route and outputs; do not re-call providers to reconstruct history.
- **Budget persistence:** atomic cross-phase admission/reservations, not $40 per worker/job/wallet. External fallback cannot start an extra unrestricted model loop.
- **External-only quality:** directly evaluate its hard-case mode, omissions, disagreements, refusals and outages; unavailable OpenAI cannot be its final judge.
- **Rights/records:** Yao Zhu/team verify inference, source submission, complete I/O retention and audit-sharing terms for each selected endpoint. Submit no secrets, wallet material or private labels. Funding does not settle these checks; no provider terms are approved here.
- **Release declaration:** Keegan/team reconcile adoption with `config/release/services.v1.json` (currently OpenAI/Anthropic candidates), the deviation register and existing release gates. This PR changes none of these. Declare all routes and automatic switching before final activation; no human/remote-config model change during the scored run.

## 9. Sources checked and limits

Checked 2026-10-15: repository `docs/official/source_page.md` (records, services, rights/versioning), verbatim kit `logging.md`, `PROTOCOL.md`, SDK README (multi-call round records), SKILL.md F-49/F-60/F-61/F-62/F-102/F-117, G-03/G-06/G-50, Q-16/Q-30 and participant-kit.md K15. **Q-16 is answered in practice:** provider summaries/available reasoning plus full I/O/harness records; do not reopen it. The recorded organiser answer F-117 supplies the freeze constraint. No new organiser question or live challenge-page refresh is claimed.

**[PRIMARY] vendor sources**, checked for existence/docs only; no inference endpoint or accuracy test:

- [OpenAI model selection](https://developers.openai.com/api/docs/guides/model-selection); [Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini): guidance and candidate interfaces/OpenAI prices. Account access not checked.
- [Kimi K3 API quickstart](https://platform.kimi.ai/docs/guide/kimi-k3-quickstart), [announcement](https://www.kimi.com/en/blog/kimi-k3): naming and interface/effort checks. Launch mode is not proof of current low-effort endpoint support.
- [GLM-5.3 announcement](https://z.ai/blog/glm-5.3), [Z.ai API platform](https://z.ai/model-api): candidate existence and documented controls. The announcement's search-indexed text was readable but its direct page body returned no text; selected endpoint behavior remains unverified.

External prices deliberately excluded following the user's funding clarification. No claim establishes candidate-specific rights, accuracy, throughput or live eligibility for this workload.

## 10. Open decisions and current result

| ID | Remaining decision/work | Proposed owner | When |
|---|---|---|---|
| MR-01 | External routine/difficult primary/secondary models, endpoints, efforts and rights evidence | Yao Zhu + team | Before EXP freeze/API use |
| MR-02 | Independent labels, power/sample feasibility, T01 alignment, locked router and clean-case audits | Yao Zhu + independent annotator; Keith reviews | Before EXP; existing B8 Oct 19 recommendation / Oct 22 selection remain |
| MR-03 | Shared budget reservations, credit-error classification, automatic all-external switch and outage behavior | Keegan + Yao Zhu; Keith confirms budget | Before future implementation approval |
| MR-04 | Freeze paid evaluation allocation inside $40; external funding already supplied by user | Keith + team | Before any paid run |
| MR-05 | Composite identity/logs/replay, service/deviation declaration and runtime wiring | Keegan + Yao Zhu | After evidence, before final activation |
| MR-06 | Approve/reject implementation and adoption after mixed **and external-only** evaluation | Team | Before Oct 22/final activation; otherwise retain as research |

**Current result:** documentation and arithmetic review only. No model calls; routing/budget/fallback not implemented; real-data evaluation NOT RUN; no live model/policy selected; no deployment gate closed. The proposal PR requests review, not execution of this experiment.
