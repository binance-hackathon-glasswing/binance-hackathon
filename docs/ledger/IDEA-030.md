# IDEA-030 — Independent review of hypothetical events, licensed news and trading fitness

- Date / author: 2026-10-10 SGT / Yao Zhu request, Codex with independent literature, source-rights and evidence-code reviewers.
- Status: review complete; user-authorized documentation publication on main; zero-paid-licensing follow-up and implementation prompt prepared. No implementation, source activation, paid subscription, training or trading performed by this record.
- Scope: current evidence code `544df90460d55c01a443452f2b02997f96e621f7`; strategy/risk/research `45e4b10f4f77b9faf0279801bbffed299b728731`; runtime/audit/storage `0234a14243057f6d53797dcd585fdcbfbbcedcf1`; main/IDEA-029 `16379df9cc2286fae9d962109066253fbda4f126`; shared kickoff `e10eae22acc8e95e5831770cf15e32ad97d6edb9`.
- The attached evidence-agent build prompt is historical context, not an instruction to rebuild. Existing untracked `Claude outputs/` is not edited, run or committed.
- Related: IDEA-025 §9.5, IDEA-026/028 (on their respective branches), IDEA-029 (on main), H-02/H-04, GAP-23/24/44/50/51/56/57/64/65.

## V01 — Prospective review verification, before execution

Purpose: test the review's static counterexamples, not profitability or trading readiness. Only public/synthetic in-memory inputs and already-pushed source are allowed. No source file changes, external API/model calls, credentials, signing, broadcast, ai-seeds upload, market-data collection, training or portfolio simulation.

1. Re-run the existing evidence and foundation offline unit suite under the available Python interpreter. Report exact interpreter, command, count and failures. Passing confirms only the existing suite's assertions.
2. Read-only semantic probes against the existing evidence functions, with full constructed input and observed output recorded outside private data: (a) an impairment heading, (b) a competitor's cybersecurity incident, (c) a CEO rumor, (d) a confirmed announced future CEO departure, (e) a numeric claim whose sign or REPORTED/GUIDANCE kind is changed while its source span stays fixed, (f) repeated assessment of the same newly seen hypothetical statement, (g) expired assessment after a previously CLEAR gate.
3. For each probe, write the expected correct semantic behavior before running it. A review finding is confirmed only if actual source output demonstrates the claimed failure; otherwise retract or narrow it. Distinguish extraction, verification, assessment, gate and live policy effects. Do not infer live trading behavior from a disconnected component.
4. Cross-branch integration review stays static: compare actual producer/consumer fields and control flow. Report absent adapters as integration work, not as proof of a live crash. No synthetic merged runtime is built here.
5. Literature and source licensing use primary documents; log what was checked and distinguish advertised capability from acquired rights. The live challenge page will be rechecked, with failures stated explicitly.

Results: NOT RUN at this criteria commit. Findings, source register, economic evaluation recommendations and verification outcomes will be appended after independent review.

## R00 — Verdict and scope of confidence

**Recommendation, not an adopted trading policy:** retain attributed statements about uncertain events; broaden source selection to rights-cleared news; keep economic authority separate from evidence extraction. The architecture is a useful foundation for an auditable agent, but neither its integration nor a profitable news/hypothetical-event policy is established. Calling it a very good profit-maximising design would exceed the evidence.

Three independent reviewers covered (1) primary literature and economics, (2) evidence semantics/code, and (3) news products/contracts. The lead reviewed shared contracts, strategy/risk/accounting/research, runtime/audit/storage, source tools and deployment interfaces, reconciled disagreements, and checked primary product/research sources again. A second reviewer independently cross-checked the branch integration findings. V01 added concrete synthetic counterexamples to the static review.

This is a repository-wide architecture review with detailed source review of the authored runtime modules, evidence modules and economic modules, plus test/fixture and operational-script inspection. It is not an exhaustive security audit of third-party dependencies or cloud infrastructure. Vendored SDK and verbatim kit remain unchanged. No private captures, keys or `.env` were read. Existing untracked `Claude outputs/` was excluded, preserved and not executed. No execution-recovery implementation branch was present among fetched origin refs; Isaac's unpublished/local work cannot be assessed here. Main does not contain the owner branches; absence from main is not absence of work.

### R01 — Rechecked competition objective and constraints

Checked `docs/official/source_page.md`, verbatim kit `bstocks-trading-guide.md`, `logging.md` and protocol material, SKILL F-20/32/42–52/60–64/71/90–117, G-05/10/11, Q-16/24/32–40, and participant-kit K2/K6/K11/K14/K15/K18. The live DoraHacks page was retried on 2026-10-10 and returned HTTP 405; no fresh full official rules were obtained.

- F-32 permits public or legally authorized news and commercial APIs, provided the team holds the rights. F-63/71 prohibit unauthorized data. Kit-first/EDGAR-only scope and G-10's human-authored-market-view restriction are **team policy**, not a competition ban on licensed journalism or analyst material. No human trading/in-run intervention remains separate and binding under the working rules.
- F-49 requires complete model I/O for the winner audit. Product/API access, publisher rights, hosted-model processing, retention and private auditor disclosure are distinct permissions. A hash does not replace raw inputs required for an audit. Q-24 leaves exact sharing terms open; design for complete evidence and settle actual licence terms.
- The public page proposes net final wallet equity, with drawdown as a tie-break and an integrity audit. The relayed organiser F-115 instead discusses completed-trade PnL, drawdown, logs and repository together, and rejects no-trading participation. Q-39 is genuinely unresolved. Do not claim either pure return or a particular weighted score is confirmed. Report terminal equity and realised PnL/drawdown; do not manufacture trade quotas or churn to satisfy an unspecified activity threshold.
- Five eligible tokens, long-only, no leverage/shorts; 14-day scored run; final funding 200 USDT is F-107's relayed team fact. These constraints severely limit transfer from diversified long-short equity papers. Higher volatility can raise some tournament-tail outcomes while lowering expected profit: the two objectives are not interchangeable, and rivals' strategies are unknown.
- F-114/117 require the frozen final build; added sources, fallback rules, correction handling and recovery must be declared and implemented before activation. Existing no-change and audit requirements are not optional performance costs.

### R02 — What is already good, and what is not yet connected

Keep the immutable documents; source/content hashes; event/revision timestamps; late-context rejection; bounded read-only tools; explicit abstention; separation from signer authority; independent risk evaluation; confirmed-fill accounting; durable atomic journal/reservations/outboxes; retry identity and quarantined recovery. These reduce preventable losses and disqualification risk. They do not create a trading edge by themselves.

| Component at reviewed SHA | Established scope | Material remaining boundary |
|---|---|---|
| Evidence `544df90` | EDGAR ingestion, deterministic extraction/comparison, bounded assessor, verifier, evidence state, synthetic evaluation | Real-text semantic error rates, live model/provider validation, general news, market-impact policy |
| Strategy `45e4b10` | Offline candidate policy, declared sizing, independent risk/planning, accounting and research scaffolding | Explicitly rejects live profile; source/market adapters and policy adoption absent |
| Runtime `0234a14` | Transactional persistence, coordinator, isolation/scheduling, audit protocol, archive/recovery, fixture replay | Uses injected owner ports/fixture semantics; live capability creation deliberately rejects; actual integration/rehearsal absent |
| Execution | No corresponding remote owner branch found | Signer, RFQ decoding, nonce/finality/gas and live command consumer cannot be certified from these branches |

**P1 integration gap:** identical schema names do not imply compatible records. Evidence returns `instrument_scope.token`, `cutoff_ms/completed_ms/expiry_ms`, `status`, `falsifiers`; strategy expects `symbol`, ISO `available_at/cutoff/expires_at`, `quality=VERIFIED`, `review_complete` and differently shaped `falsifier_findings`. Their context hashes use different domains and different objects. Raw evidence is silently ignored by strategy. Runtime supplies `projection/reservations/request/assessment`; strategy needs `profile/portfolio/markets/series/session_index/assessments`. Strategy intents lack runtime's `amount/decision_id/expires_ms`; its plan lacks `jobs`; its reservation requests differ from store `asset/units` deltas. Risk-state and reassessment-job persistence also require deliberate translation.

These are acknowledged owner-local integration proposals, not evidence that an already-running production deployment has crashed. Required proof is an actual producer-to-consumer fixture, not a fake that duplicates each owner's expected output. References: evidence `agent.py:407`, strategy `policy.py:17,29`, `schema.py:48`, `planner.py:19,241`, runtime `coordinator.py:77,91,111,133`, `postgres.py:207` at the SHAs above.

## R03–R08 — Hypothetical-event assumptions and verified semantic failures

### R03 — Retain information, distinguish what is asserted

A useful information object needs separate source/report, proposition, actor, certainty/conditionality, publication time, effective/event time, affected issuer and supported transmission mechanism. These are proposed semantics, not a request to build a new subsystem now.

| Example | What can be established now | What cannot be inferred automatically |
|---|---|---|
| Company announces today that its CEO will leave next month | A confirmed announcement with a future effective date | That the departure is already complete, or necessarily bad for price |
| A wire reports unnamed sources saying a CEO may leave | The report, attribution and uncertainty | A confirmed departure or multiple independent confirmations from syndicated copies |
| China-based competitor may develop a better chip | A report/claim and any sourced technical evidence | Commercial yields, scale, customer substitution, timing, or a uniform negative effect on NVIDIA and SK hynix |
| Annual disclosure says cyber incidents could harm operations | A conditional risk statement | A new cyber incident or an increase in its probability |
| The agent imagines a possible competitor breakthrough | A scenario for stress testing | New external evidence or a tradable news event |

The China-chip example requires evaluating technical credibility, production scale, customer adoption, export restrictions and the relevant product market. Compute competition could hurt an incumbent, while demand for complementary memory could rise or fall. Those are alternative mechanisms to investigate, not predictions. A source can establish that a claim exists without establishing its truth. Licensed sources are not infallible.

Conceptually, a price can change when information changes scenario probabilities or payoffs before the event occurs. That supports retaining uncertain reports. Trading benefit additionally requires remaining mispricing at an executable price after receipt and assessment. The agent's confidence score is not a calibrated event probability, nor is sentiment a return forecast.

### R04 — P1: keyword support is being mistaken for event entailment

V01 confirmed these outputs of the existing extractor/verifier:

| Constructed input | Observed accepted claim | Required distinction |
|---|---|---|
| `Impairment of goodwill` | `IMPAIRMENT`, scope `ISSUER` | A heading alone asserts no occurrence |
| `Our competitor reported a cybersecurity incident.` | `CYBERSECURITY_INCIDENT`, scope `ISSUER` | Third-party event is not the filing issuer's incident |
| `The CEO is rumored to resign.` | `OFFICER_DEPARTURE` | Rumor is not confirmation |
| `The CEO announced plans to resign effective November 30.` | `HYPOTHETICAL:OFFICER_DEPARTURE` | Confirmed announcement and future occurrence are separate dimensions |

`facts.py:49–63,398` recognizes keywords and modal/negation cues; `verify.py:151–163` repeats that logic. It does not establish subject, occurrence predicate or event time. `agent.py:508–520` can turn affirmed keywords into configured findings regardless of novelty; adverse findings survive abstention and are latched by `gate.py:63`. The first two examples matter especially for false adverse findings. CEO departure currently has UNKNOWN impact, so the CEO probe is **not** proof of an automatic exit. Historical-event repetition is an additional static concern, not a measured frequency.

Simply expanding the modal-word list will not solve attribution, effective dates, headings or semantic scope. Prioritise these before broadening inputs. A model omitting a false deterministic finding does not automatically veto it.

### R05 — P1: verifier accepts numeric sign and kind mutations

On `Revenue for the third quarter of fiscal 2027 was $35.1 billion.`, the unchanged REPORTED claim passed; both a claim changed to **−35.1** and a claim changed to **GUIDANCE** also passed. `verify.py:179` accepts either sign; `:118–120` checks kind membership without establishing reported-versus-forecast meaning. These are confirmed verifier defects, not claims of executed trades. A downstream same-kind conflict may abstain on a sign flip; it does not make the verifier sound, and relabeling kind can evade that conflict partition and pollute a later guidance comparison.

Required invariant: a source span must support the signed number, metric, period, units, kind and attribution together. Span existence/string matching alone is insufficient.

### R06 — P1 design/integration risk: novelty and review have no complete lifecycle

The current `statement_key` normalizes case, spacing and edge punctuation (`facts.py:89–93`). It is textual equality, not semantic novelty or market surprise. `could` to `may` can become NEW; absent prior history can become NEW after a successful lookup with no matches. The default 30-day backfill need not contain the previous quarterly/annual caution. An EDGAR filing can repeat an earlier public release unknown to the index.

V01 reassessed the same synthetic filing after six hours with updated context. All six hypothetical statements remained NEW, gate UNKNOWN, with another `REVIEW_NEW_HYPOTHETICAL_EVENT`. Prior comparison excludes the current accession. No reviewed/acknowledged object closes that loop. Conversely, an unrelated later clean result can clear UNKNOWN because unresolved hypothetical issues are not persisted like adverse findings.

Crucial distinction: no adverse severity does **not** guarantee no effect on trading. NEW hypotheticals force the evidence gate off CLEAR (`gate.py:104`). Connecting CLEAR to entry permission would implement an entry veto. The current strategy does not yet consume that gate, so this is an integration risk, not observed live suppression. Separate evidence novelty/coverage, review state and portfolio permission; specify correction, resolution, expiry and retry limits before wiring them together.

### R07 — P1 integration requirement: CLEAR is not a durable freshness guarantee

V01 accepted a CLEAR result, then submitted an expired subsequent result. It correctly returned `REJECT_EXPIRED`, but the stored state remained CLEAR, unchanged, with no stored expiry. `gate.py:51–60,86–92` checks incoming validity, not aging of an already accepted state. Consumers must check evidence as-of age, coverage age and assessment completion independently. Preserve adverse latches according to their explicit resolution policy; do not clear them just because an assessment expires.

### R08 — Coverage and evaluation are narrower than the intended capability

The implemented event vocabulary contains five adverse-event families: restatement, cyber incident, delisting, impairment and officer departure; numerical extraction covers five financial metrics. Same-issuer EDGAR tools do not represent a competitor breakthrough, geopolitical causal chain or general good-news opportunity. A news adapter cannot safely pretend a competitor story is the affected issuer's filing.

The synthetic 40/40 versus 25/36 comparison uses the same deterministic rule model with six tools versus zero (`evaluation.py:48–54`). It demonstrates retrieval/comparison value on designed fixtures, not incremental LLM value. Numeric scoring ignores extra output keys absent from expected labels (`:115–117`); event scoring measures recall rather than precision (`:124–126`); three planted unsupported claims do not estimate real-world failure rates. The evaluation pack itself has no hypothetical cases; the added unit cases are separate. Compare a full-information deterministic baseline with the LLM on identical accessible evidence.

Also test realistic filing size: one prior-context call may read many documents; a six-call limit does not bound bytes/tokens/work. More than 64 claims and document-selection truncation can reduce coverage or cause abstention. These are static scalability concerns, not measured production failure rates.

## R09 — Literature supports informativeness more strongly than tradable profit

The prior A1/A2 labels in IDEA-025 §9.5 need narrowing. Risk-disclosure studies associate text with risk perceptions/volatility; they do not establish causal signed returns or an executable exit advantage. Dyer et al. document increasing boilerplate, not that most statements in this implementation's hypothetical class are boilerplate. Exact textual changes, actual news and information surprise differ. L-64's secondary impairment study should not carry a causal/trading conclusion.

Lopez-Lira/Tang explicitly separate initial-reaction recognition from subsequent returns. Their high headline hit rate concerns a nontradable initial reaction; subsequent drift is strongest among smaller stocks and negative news. In their value-weighted overnight example, assumed costs turn positive gross performance negative. This is evidence for useful interpretation, not a directly transferable long-only five-name token strategy. It also does not prove that all news trading is futile. [Full manuscript, methods and cost tables checked](https://arxiv.org/html/2304.07619v6).

| Review source ID | Primary source and reading depth | What it supports / limit |
|---|---|---|
| L030-01 | [Cohen, Malloy & Nguyen, Lazy Prices](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12885), publisher abstract | Comparing filing language; slow effects and long-short construction do not validate a five-day lexical veto |
| L030-02 | [Kravet & Muslu](https://www.bauer.uh.edu/vmuslu/docs/Abstract%20Kravet%20Muslu%20%282013%20RAST%29.pdf), author abstract | Risk-perception associations; prior boilerplate paraphrase was too broad, including its firm-versus-industry comparison |
| L030-03 | [Campbell et al.](https://doi.org/10.2139/ssrn.1694279), author abstract | Risk disclosure is informative; residual mispricing is a separate claim |
| L030-04 | [Dyer, Lang & Stice-Lawrence](https://scholarsarchive.byu.edu/facpub/8429/), author abstract and [publisher introduction/conclusions](https://www.sciencedirect.com/science/article/pii/S0165410117300484) | Boilerplate/stickiness trends; no prevalence estimate for our extracted class |
| L030-05 | [Baginski, Hassell & Kimbrough](https://onlinelibrary.wiley.com/doi/full/10.1111/j.1475-679X.2004.00127.x), publisher abstract | Forecast explanations relate to price reactions; L-65 upgraded from search-only to primary abstract, not full-text verification |
| L030-06 | [Lopez-Lira & Tang v6](https://arxiv.org/html/2304.07619v6), full methods/results and cost tables | Interpretation versus delayed profitability, size/cost and short-side limitations |
| L030-07 | [Tetlock, All the News That's Fit to Reprint](https://business.columbia.edu/sites/default/files-efs/pubfiles/3099/Tetlock%20Fit%20to%20Reprint%2010%2010.pdf), author manuscript sections | Stale news can move prices then partly reverse; repeated does not mean inert |
| L030-08 | [Chou, Tian & Yin, Takeover Rumors](https://www.sciencedirect.com/science/article/pii/S1057521915000885), publisher abstract/introduction | Rumors may contain information in a specialized sample; no transfer to all chip/CEO stories |
| L030-09 | [Martineau, Rest in Peace PEAD](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607), author abstract | Challenges generic large-cap earnings drift; not proof that every event strategy fails |
| L030-10 | [Glasserman & Lin](https://arxiv.org/abs/2309.17322), author abstract | LLM return tests can suffer company-knowledge/look-ahead contamination; anonymisation is only a diagnostic |

H-04 currently combines higher volatility **or** lower returns and multiple horizons. Split risk prediction from directional returns and policy utility; preselect one primary endpoint/horizon. A volatility result does not license selling, and a 60-session result does not establish two-week trading profit. Both insufficient sample and a confidence interval spanning no benefit should remain inconclusive, with a fixed fallback.

## R10 — IDEA-029 corrections and licensed-source options

IDEA-029 is at main `16379df`, not in this evidence-based branch. Preserve its historical research record; this section is a dated correction, not a silent rewrite.

1. Its “from the rules, not preferences” introduction incorrectly covers G-10's policy row. Kit-first and excluding licensed commentary are revisable team choices.
2. Its conclusion that nothing licensed adds news absent from EDGAR is unsupported. Several terms pages were unavailable in that research. **Not cleared for LARP** differs from **no usable licensed product exists**.
3. Treat each provider's definition of personal/commercial use separately. Prize participation alone is not a universal legal definition. Alpha Vantage's actual §2(i) refers to use beyond private individual analysis; the prior paraphrase omitted that distinction. Team use/audit still need appropriate rights. [Current terms PDF checked](https://www.alphavantage.co/terms_of_service/).
4. EDGAR acceptance is not necessarily first disclosure. Many 8-K items generally have a four-business-day filing deadline, with exceptions; that does not measure actual delay, but defeats assuming zero delay. Cross-company/regulatory news may never appear promptly in the affected issuer's filing. [SEC Form 8-K instructions](https://www.sec.gov/divisions/corpfin/forms/8-k.htm).

The user's present instruction opens licensed external sources for evaluation. It does not purchase a licence or automatically admit a source into the production manifest.

| Candidate | Useful fit, as an assessment | Verified product capability | Clearance still needed |
|---|---|---|---|
| N030-01 Benzinga direct enterprise, preferably original news | First practical licensing candidate for US issuers and competitor coverage | Explicit financial AI datasets, runtime/history, inference/training uses advertised; REST/streaming. [Provider guide](https://www.benzinga.com/apis/guidebook/) | Team/contest, hosted processor, raw retention and Binance audit, publisher entitlements, historical versions, SK hynix coverage and quote |
| N030-02 LSEG Machine Readable News / Reuters | Strongest documented global-semiconductor/geo-policy candidate | Reuters stories/headlines, streaming and point-in-time archive. [MRN](https://www.lseg.com/en/data-analytics/financial-news-service/machine-readable-news); [version/correction model](https://developers.lseg.com/en/article-catalog/article/machine-readable-news-mrn-n2_ubms-comparison-and-migration-guide) | Cost/onboarding time, exact content package and AI/retention/audit rights; language availability does not prove target-name coverage |
| N030-03 RavenPack EDGE News Analytics | Alternative if licensed structured events reduce engineering burden | Entity/relevance/novelty/event analytics. [Product](https://www.ravenpack.com/products/edge/data/news-analytics) | Features versus underlying text rights, feature-version history, audit/export, price and Korean coverage |

Massive advertises Benzinga News at **$99/month individual**, while business access requires a sales quote; that is not a cleared four-person LARP price. Publication and last-update fields are exposed, but these alone do not prove access to every prior article version. [Pricing](https://massive.com/partners/benzinga), [business distinction](https://massive.com/knowledge-base/article/which-plan-do-i-need-to-show-massive-data-in-my-app), [news fields](https://massive.com/docs/rest/partners/benzinga/news). No suitable team price was verified.

| Other option | Contract finding from primary terms, checked 2026-10-10 | LARP consequence |
|---|---|---|
| Bigdata.com | Single-inference grounding with restrictions on retaining underlying content, redistribution, evaluation/training; §4.2. [Terms](https://bigdata.com/terms-and-conditions) | Standard terms conflict with this complete-input/audit design; bespoke agreement needed. Do not apply these terms automatically to RavenPack EDGE |
| NewsAPI.ai / Event Registry | Rendered terms, updated 7 Oct 2026, permit paid internal AI and retention, but leave publisher-content rights to customer and restrict raw sharing. [Terms](https://newsapi.ai/terms) | An API subscription is not complete publisher/auditor clearance |
| Finnhub | Personal-use, sharing/derived-result and termination-deletion restrictions. [Terms](https://finnhub.io/terms-of-service) | Existing caution remains justified; written suitable agreement needed |
| NewsAPI.org | Developer plan not production; third-party copyrighted content remains restricted. [Terms](https://newsapi.org/terms) | Paid API access alone does not settle full-text audit rights |
| GDELT | Its own data can be reused; linked publishers retain rights. [Project terms](https://gdeltproject.org/about.html) | Discovery/metadata candidate, not a way to acquire article rights or independent corroboration |
| Dow Jones/Factiva | Official retrieval-to-LLM demonstration exists. [Official repository](https://github.com/dowjones/factiva-retrievalapi-demo) | Additional licensing route, not investigated enough for price/timing/adoption |

Choose at most one commercial feed for the first comparison. Existing official SEC/regulatory/macro sources can supplement it within their own verified terms; being governmental, free, licensed or well-known does not by itself establish marginal trading value.

For a concrete licence, record named users/team, Singapore location, automated competition use, exact publishers and fields, runtime inference separately from evaluation/training, named hosted-model processors and retention, immutable raw input/output storage, private Binance disclosure, post-subscription audit retention, derivatives/attribution, correction/version history. If an offered contract lacks required rights, obtain an amendment or reject it. No vendor was contacted or purchase made.

## R11 — What has to change conceptually before news can help

Preserve news as source/versioned evidence rather than forcing it into `FilingSource.list_filings(cik)/fetch_filing(accession)`. Distinguish publisher from distributor, original actor from affected eligible issuer, statement from verified occurrence, first report from later revision, and semantic novelty from missing history. Cluster syndication/reports of one underlying event. Store corrections/withdrawals without rewriting earlier inputs. A copied release in EDGAR is not a second independent corroboration.

Require three separate outputs: **what the source establishes**, **possible economic implications and unknowns**, and **the policy's justified action under prices/costs/constraints**. The evidence component need not itself set prices or target weights. A blanket “negative news means exit” omits whether the position is held, what was priced in, the re-entry rule, transaction costs and what happens if the report is denied. Likewise an adverse event can be true yet already over-discounted.

A live prediction about a future event uses information available now; that is distinct from prohibited future-information leakage. Historical testing must never use later confirmation to select which rumors were initially included, nor today's revised article as though it had arrived at its original publication time.

## R12 — Economic and operational blockers beyond the news question

1. **No demonstrated entry advantage.** Strategy currently offers unvalidated declared-exposure and price-momentum candidates, with evidence SHADOW by default. More severe event interpretation does not supply an expected-return model. Sizing/risk controls constrain an edge; they do not establish one.
2. **Required inputs cannot yet be supplied by the current pipeline.** Declared sizing requests 61 closed consecutive sessions of underlying-share history, with currency/calendar/corporate-action/basis metadata (`strategy/features.py:19–57`). Token candles are not automatically those inputs. Obtain a suitable licensed price history/adapter or formally change the declared approach; do not fake basis validation or silently substitute short history. Independent share-price access remains GAP-56.
3. **The inherited depth requirement blocks RFQ entries.** `risk/planner.py:221–224` rejects absent `quoted_depth_units`; kit quotes expose no depth (GAP-51). This is an explicit safe placeholder, not an accidental permission to remove the rule. Adopt a measurable replacement, document it, and test actual adapter behavior before concluding the policy will trade.
4. **Falsifier exits and mandatory risk need explicit precedence.** BOUNDED_FALSIFIER creates policy EXIT targets that can hit discretionary cadence/minimum/cost gates unless translated into reduction constraints. Terminal flattening is already independently mandatory in the planner, including without a policy; the reviewers specifically verified that correction. Decide which evidence events are true constraints versus optional economic exits, rather than assuming all EXIT labels bypass filters.
5. **Costs and opportunity cost dominate marginal stories.** The kit's historical gas illustration is about $0.02–0.035 per approve-plus-swap leg. Two such legs on a $20 position are approximately 20–35 bp before spread/impact; on $40, 10–17.5 bp. These are arithmetic illustrations from historical kit values, not live quotes or a calibrated break-even estimate. Measure size-specific executable round trips, failure gas and re-entry costs. Report off-wallet model/feed expense separately from wallet scoring PnL.
6. **Freeze/rehearsal remains material.** Unit tests and fake execution do not establish five-plus-day full-pipeline rehearsal, market-open availability, nonce recovery or audit delivery under real operating conditions. Runtime current live rejection is appropriate. No market/model/wallet probe was run in this review.
7. **P2: the economic evaluator accepts criteria its verdict does not implement.** Strategy-branch `research/evaluation.py:16–21` requires text fields for `paired_metric`, `kill_rule` and `inconclusive_rule`, but `:75–78,92–97` hardcodes after-service-cost incremental returns and a positive lower-bound/positive absolute-mean test. A registered material-improvement margin or different metric can therefore be accepted yet ignored. This is a static finding, not a failed real experiment: the module declares synthetic-only use and always sets `promotion_authorized=False`. Before real use, either reject unsupported structured criteria or calculate exactly the registered rule. Keep wallet scoring economics separate from off-wallet project expenses.
8. **Sample validity is not established by a cluster count.** The same evaluator checks nonoverlapping window boundaries and counts aligned outcomes; it does not bind outcome decision/label times to the registered windows or enforce recorded purge/embargo values. Two admissible clusters are not inherently a coding error, but their statistical independence is not proved by those checks. Validate actual outcome provenance and the registered dependence/sample design before interpreting confidence intervals. These are static limitations, not measured financial results.

## T01–T05 — Recommended prospective evaluation, NOT RUN

These are study designs, not adopted parameters or completed EXP results. Coordinate a concrete EXP with dates, licensed dataset/version hashes, exact baseline/policy, thresholds, primary endpoint, sample requirement and fallback before collecting outcomes or training.

**T01 Semantic correctness.** Freeze an adversarial safety set including V01, then independently annotate a rights-cleared real corpus stratified by filings/news, good/bad/neutral, rumor/forecast/announcement/occurrence, entity/time, corrections and multiple numbers. Require no unsupported promotion to actionable fact on the safety set. Separately report precision, recall, abstention, coverage, label disagreement and confidence intervals on real documents. Do not accept high recall while ignoring false exits. Safety-set perfection is not a zero-error population claim.

**T02 Coverage and usable latency.** Forward-capture EDGAR plus one licensed feed for all five names and supported competitor/regulatory relations. Measure unique material-event coverage, first public/version time, actual receipt, completed assessment and first executable quote. Include source outages, delayed stories and missed events. Kill a source that cannot satisfy rights/audit/version requirements; assess acquisition value separately from alpha. Do not treat publication lead time as executable lead time.

**T03 Separate ablations.** Freeze one executable no-news baseline. Compare baseline versus EDGAR evidence, then adding licensed news, then adding uncertain-event features; confirmed future announcements remain their own class. Separately compare full-information deterministic extraction with the LLM on identical inputs. Use the same risk limits, starting cash, feasible position sizes and execution engine. Freeze explicit entry/hold/exit/re-entry/correction policies; avoid a large post-hoc menu of variants.

**T04 Score complete portfolios.** Primary: paired incremental net wallet terminal equity from actual post-assessment executable prices, including approve/swap gas, spread, slippage, failed attempts and opportunity costs. Also report realised PnL, drawdown, turnover, time invested, missed upside and external service costs. A matched-exposure diagnostic helps distinguish information benefit from simply holding less risk; it must not replace full policy PnL. Stress costs/latency, include no-event periods, retain incomplete/late outcomes and censor labels at the competition end. Broader large-cap samples can inform development but must not silently substitute for the five-name target population.

**T05 Statistical/decision discipline.** Chronological training/calibration/selection/holdout; point-in-time versions and model provenance; purged overlapping labels; issuer/event/day clusters rather than headline count; out-of-fold upstream predictions for any fusion. Predefine a minimum meaningful improvement and uncertainty hurdle. Supported requires the chosen net-policy criterion and operational/risk limits; an adverse upper bound rejects; insufficient independent cases or an interval spanning the hurdle is inconclusive. Use a predeclared fallback on inconclusive evidence. Freeze one primary horizon; 20-/60-day studies are secondary and cannot validate two-week profit. Include delayed-news, duplicated/syndicated-news, absent-history and price-recap/placebo tests. No development-wallet/scored-run PnL tuning.

Priority order: (1) fix semantic invariants and real component contracts; (2) establish a feasible baseline and executable costs/required prices; (3) clear one news licence and capture correct versions; (4) run the smallest informative ablations; (5) rehearse the frozen integrated system. This preserves the useful architecture while directing effort toward trading value rather than adding components without evidence.

## V02 — Verification outcomes, limitations and owners

- V01 criteria recorded locally in commit `703a10a` before execution. All runtime source used was unchanged and already pushed at `544df90`.
- Lead rerun: `/opt/homebrew/bin/python3.12 -m unittest discover -s tests -v`, Python **3.12.14**, **150 tests passed**, 2.966 seconds, including the 13 foundation tests. No new test/source file was added.
- Independent in-memory probes, same interpreter/source: R04/R05 table outputs confirmed; six-hour hypothetical reassessment remained NEW/UNKNOWN; expired input left prior CLEAR unchanged. Expected behavior and exact inputs were written before probing; [the retained probe record](IDEA-030-probes.md) contains expectations and observed outputs. These deterministic synthetic cases establish paths, not real-data prevalence, integrated execution effects or profitability.
- The branches' reported 48 strategy tests and 108 runtime tests/65 subtests are historical build evidence, **not rerun here**. No Linux/PostgreSQL/cloud/live execution acceptance is claimed. Static branch comparisons establish missing adapters, not a synthetic merged-system result.
- Source research checked current primary documents as linked; some academic sources were abstracts only, explicitly marked. Advertised capabilities are not acquired legal rights. Actual provider lead times, team prices, Korean event recall, feed latency and incremental returns remain unmeasured.
- No implementation or live policy changed. No licensed corpus acquisition, model training, paid service, source polling, real audit upload, wallet transaction, vendor message or organiser message occurred.

| Open work | Suggested owner under IDEA-024 allocation | Record |
|---|---|---|
| Semantic verification, event taxonomy, novelty/review/freshness lifecycle; real-data eval | Yao Zhu; Keith reviews economic implications | GAP-67, R03–R08, T01 |
| Canonical evidence→policy→planner→store adapters, actual producer tests, durable risk/jobs, release closure | Keegan with all component owners | GAP-65, R02/R12 |
| Executable baseline, evidence authority/default, objective, evaluator criteria/provenance and economic registration | Keith + Yao Zhu; team adopts | GAP-64/67, H-02/H-04, R12.7–8, T03–T05 |
| Source contract/provenance, correct price history, source/version capture | Team chooses licensee; Yao Zhu evidence, Keith research, Keegan audit rights | GAP-23/24/56, R10–R11 |
| Market availability, exact-size costs, depth-rule replacement, actual execution/recovery | Isaac + Keith; Keegan integrates | GAP-44/50/51/65, R12 |
| Scoring/valuation/time-window questions already recorded | Team organiser liaison | GAP-42/Q-39; do not re-ask settled items |

### V03 — Initial repository delivery status (historical; superseded by V04)

Review branch: `codex/review-hypotheticals-news`, based on the existing evidence branch; no automatic merge into main. Automatic approval review rejected the attempted push of the review documents to the configured GitHub origin, citing potentially sensitive findings, an unverified destination and lack of explicit payload/destination authorization. Local commits are permitted. The GitHub connector's read-only repository check returned 404, so it did not resolve destination verification. No alternate upload route was used. Remote publication remains pending user approval.

Strict handoff is not ready: review commits are local-only; the user's pre-existing untracked `Claude outputs/` remains; owner branches/integration and main synchronization must be handled separately. This review does not remove any fully incomplete implementation/research backlog item.

### V04 — User-authorized main publication and free-source follow-up

The user explicitly authorized pushing the review to main under IDEA-030 (or another free ID) and requested zero paid licensing plus an implementation prompt. A fresh fetch confirmed IDEA-030 remained free. Main was fast-forwarded to `16379df`; this publication transfers the report, synthetic probe evidence and applicable corrections as documentation only, preserving main's IDEA-023 and IDEA-029. It does not merge any owner runtime code. Original review commits `703a10a` and `9f28065` remain in the local review branch as historical provenance; their findings are carried into this main publication. The earlier automatic push restriction is resolved by the user's explicit authorization.

New fact from the follow-up fetch: `origin/branch-isaac` now exists, initially seen at `dee2f78` and advanced to `0343661` at the publication check, including `larp/execution.py`. The initial R00/R02 statement about no fetched execution branch was accurate at that earlier snapshot and must not be used as a current absence claim. This follow-up did not review or certify the new execution implementation. The implementation prompt requires inspecting all current owner branches before changes.

**N030-F / zero-cost source decision:** the user will not pay for news licensing. [The free-source review](IDEA-030-free-sources.md) replaces R10's paid shortlist for this implementation: official SEC news, Federal Register/BIS, DOJ and EC original material are the first candidates; FTC retrieval needs repair/verification; Fed/BLS calendar context and EFF are optional. GDELT is discovery metadata only; Wikinews is archive-only after May 2026. Free original announcements do not provide comprehensive rumor/competitor coverage. Rights-qualified access does not establish trading benefit. No paid source or data acquisition is authorized.

**P030-01 / implementation handoff artifact:** [05-evidence-hardening-free-sources.prompt.txt](../build/05-evidence-hardening-free-sources.prompt.txt) instructs the next implementation session to reuse existing components, correct semantics/lifecycle/contracts/evaluation, implement a minimal free source basket, preregister and push before executing affected code, and leave unvalidated new trading authority disabled. The present session prepares the prompt and documentation only; it does not execute that prompt or close GAP-67.

Validation of this publication is document/link/diff checking only. The 150-test result remains tied to the original evidence SHA, not to main or any future integration. The pre-existing untracked `Claude outputs/` remains untouched; do not declare the strict clean-worktree handoff check satisfied. Remote success is reported only after the push and fetched-head comparison complete.

The implementation prompt received an independent semantic red-team pass before publication. Corrections applied: require an actual policy-adoption record instead of assuming one; prevent partial fact retention from upgrading ABSTAIN or expanding authority; require an independently labeled held-out real-document evaluation and mark it NOT RUN if its inputs are unavailable. No review criterion was treated as an already passing implementation test.

- 2026-10-10 note (Keegan, integration): "main's IDEA-023" above is renumbered [IDEA-032](IDEA-032.md) on the integration branch; the foundation's IDEA-023 keeps its ID.
