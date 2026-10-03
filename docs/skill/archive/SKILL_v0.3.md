---
name: binance-agentic-ai-challenge
description: Ground truth, graded environment evidence, argued inferences (with counterpoints and examples), the team's LARP concept, and enforceable guardrails — each labelled as official RULE or internal POLICY — for "Beyond the Benchmark: The Binance Agentic AI Challenge" (DoraHacks, Sep–Nov 2026). Load before writing or revising the proposal, choosing models or data, designing the agent/harness, setting risk limits, designing logging/versioning, or answering any rule-compliance question for this challenge.
version: 0.3 (reviewer feedback applied; LARP draft integrated; evidence re-graded; adversarially reviewed)
last_verified: 2026-09-29 (SGT, UTC+8)
primary_source: https://dorahacks.io/hackathon/binance/detail (verbatim capture in source_page.md)
team_sources: larp/proposal.md, larp/application_answers.md, larp/deployment.md, larp/team_and_delivery.md (team drafts, not official)
---

# Binance Agentic AI Challenge — Skill File

## 0. Reading contract (for humans and LLMs)

### 0.1 Labels
Every line carries an ID and a label. Never upgrade a label silently.

| Label | Meaning | How to use it |
|---|---|---|
| `F-xx` FACT | Stated on the official DoraHacks page or its timeline image. Quoted or near-verbatim. | Binding until the official rules issued at onboarding say otherwise. |
| `T-xx` TEAM FACT | What the team's own drafts say (LARP proposal, answer sheet, deployment plan), or what the team transcribed from the application form. | True about *our plan*, not about the rules. Form fields are as transcribed by the team, not independently captured. |
| `E-xx` ENVIRONMENT | External evidence, graded: **[PRIMARY]** issuer/regulator/vendor's own doc, or the paper itself; **[ISSUER-EDU]** issuer's marketing or educational pages (official, not independent); **[SECONDARY]** press/aggregators; **[DEV-REPORT]** third-party developer repos/issues; **[ESTIMATE]** our arithmetic; **[UNCONFIRMED]**. | Plan around PRIMARY. Hedge the rest. **Never copy a SECONDARY/DEV-REPORT statistic into the proposal.** |
| `I-xx` INFERENCE | Reasoned from F/T/E. Each has **Basis**, **Counterpoints**, **Example**, **Confidence** (High / Med / Low), and **Proposal use** (whether it may inform proposal text). | Act on High. Design to survive Med/Low being wrong. |
| `H-xx` HYPOTHESIS | A claim about edge or behaviour that we intend to test, with a test plan and a kill criterion. | Never present as established. |
| `P-xx` PRINCIPLE | Design direction we recommend. Opinion grounded in F/E/I/L. | Default choices; change by explicit team decision. |
| `D-xx` DECISION | A choice the team still has to make. | Resolve by the named date. |
| `G-xx` GUARDRAIL | Behaviour imposed on our agent/team. Each is tagged **[RULE: F-xx]** (directly required by the official text), **[RULE-DERIVED]** (our conservative implementation of a rule whose exact reading is open), **[POLICY]** (a team choice, not required), or **[PRACTICE]** (engineering hygiene). MUST = enforced in code and tested. SHOULD = default; overriding needs a logged reason. `[brackets]` = placeholder. | Implement as written. Never describe a POLICY as a rule. |
| `Q-xx` OPEN QUESTION | Unknown that matters. Ranked. Where a conservative working assumption exists it is stated; where none is safe, the item is an **unresolved dependency** and the design must work either way. | Ask organisers. |
| `S-xx` STRATEGY OPINION | Contest-strategy views (tournament incentives etc.). Kept in Appendix A. | **Not evidence of proposal quality. Keep out of the proposal.** Revisit before final activation. |
| `L-xx` LITERATURE | Research evidence with citation and grade. | Justifies P/G items. |

### 0.2 Precedence and reviewer rules
- Precedence when items conflict: official onboarding rules > F > G[RULE] > E[PRIMARY] > G[RULE-DERIVED] > I > T > P/G[POLICY] > S.
- **Official vs internal:** the official text requires very little about *how* to trade. Almost every numeric limit, cadence rule and sizing method in this file is a team POLICY. If anyone (human or LLM) cites a POLICY as "the rules say", correct it.
- Reviewers: cite IDs. If you disagree with an inference, name the F/E item you read differently. If you add a claim, give it a label and a source.
- Nothing here is permission to evade a rule. Where a rule is ambiguous, the conservative reading applies until organisers answer.
- **Timezones:** the official page gives dates without timezones. Team is in Singapore (SGT = UTC+8). US Eastern is UTC−4 until Sun Nov 1, 2026, then UTC−5.

### 0.3 One-paragraph summary
The team's concept is **LARP (Liquidity-Aware Regime Planner)**: one central capability — turning verified, point-in-time catalysts into probability-scored long/hold/exit decisions (thresholds fit on validation data) that may abstain — supported by a regime-based exposure governor and a deterministic risk governor. Off-hours pricing of 24/7 bStocks is a *hypothesis to test*, not a claimed edge. Stage 1 is judged by people on feasibility, agentic depth, risk awareness, originality and ability to deliver; Stage 2 is mechanical % return; Stage 3 is a pass/fail audit of traceability. The largest proposal weakness is harness depth (the LLM currently has no tools, memory, planning or claim verification); the largest run-time risks are audit mapping (RFQ fills, non-trade balance events, version gaps) and day-0 gas.



---

## 1. FACTS — official page (F)

### 1.1 Identity and logistics
- F-01 Name: "Beyond the Benchmark: The Binance Agentic AI Challenge". Hosted by Binance on DoraHacks. Format: Online / Virtual. "Binance sets the rules and verifies the record."
- F-02 Prize: "6,000 USD in prize assets across the top 3 teams, plus Binance Seeds Program internship and full-time employment opportunities". The split among the three is not stated.
- F-03 Team size 1–4 people; "you may join only 1 team".
- F-04 Finalists: "<25 teams selected from open applications" (Overview and Stage 1). The timeline image says "25 teams selected". (Minor inconsistency.)
- F-05 Duration: "4 weeks of active work (2-week build + 2-week scored run); ~7 weeks end-to-end including onboarding and audit".
- F-06 Tags: AI Agent, Live Trading, Trading Strategies, Real World Assets, Onchain Finance. Listed tech: OpenAI, Anthropic, Llama, LangChain, Python, Binance.
- F-07 DoraHacks sidebar: "Submission 2026/09/07 00:00", "Deadline 2026/11/13 22:59". No timezone shown. (What this deadline governs is an inference: I-60.)
- F-08 Framing: "The question we're asking: can a team build, operate and improve an autonomous Agentic AI system that runs end-to-end in a real-time environment — and produce a decision trail that proves how it got there?" Also: "The best system wins."

### 1.2 Timeline (timeline image on the page; year 2026)
| ID | Phase | Dates | What happens | What you submit |
|---|---|---|---|---|
| F-10 | Apply | Sep 9–30 | Open applications | "A concise proposal covering: agent concept, high-level architecture, intended model approach, agent harness and tools, data-acquisition approach, basic risk design, team capability and roles, delivery plan." Via Google Form https://forms.gle/UmDXgdwPPwknYZur9 (form fields not captured; needs Google sign-in). |
| F-11 | Finalists announced | Oct 2 (Fri) | "25 teams selected" | — |
| F-12 | Onboarding | Oct 5–10 | Wallet, Developer Portal and repository setup; technical briefing | Registered **development** wallet address; private repository with audit access; declaration of principal data and model services; required team information |
| F-13 | Development (unscored) | Oct 12–26 | Build and operate in your own environment, integrate logging, test small-value trades, test recovery | A week-one checkpoint commit and progress note; end-to-end self-check evidence |
| F-14 | Final activation | Oct 27–29 | Register a **fresh final wallet**; clear the pre-final integrity check | New final wallet address; the commit and version manifest for the starting build |
| F-15 | Scored run | Oct 29 – Nov 12 | "14 days of live operation. Keep improving — every version must be committed and logged before it trades" | Daily structured decision-trace uploads; a version event for each new build deployed |
| F-16 | Provisional ranking | Nov 13 | Standings published; scored activity stops | — |
| F-17 | Winner audit & awards | Nov 16–20 | Code, version, wallet and decision-trace review | Version history, commits, manifests and complete local logs (top-ranked teams only) |

- F-18 At onboarding finalists receive: "a Participant Guide, Web3 Open API documentation, the Audit Log Specification, scoring rules and incident policy". "You don't need any of it to apply."
- F-19 "No public real-time leaderboard. The full 14-day window determines the ranking."
- F-09 Banner image: "Applications: Sept 9 - 30, 2026" and "Oct 12 - Nov 12, 2026".

### 1.3 The task
- F-20 The system "acquires information, reasons, decides, manages its own risk, and executes eligible bStocks trades on BNB Smart Chain through Binance Web3 Open APIs — using only information available to it at each decision point."
- F-21 "evaluated while it runs — against real-time conditions, latency and costs, with no ability to rewind."
- F-22 "You build it, host it and operate it." You own: "your wallets and keys, Developer Portal credentials, data acquisition, models, agent harness, strategy, risk logic, hosting, monitoring, logging and recovery."
- F-23 Binance owns: "the competition rules, eligible instruments, the scored window, the audit standard, the scoring method, and the final results."
- F-24 "Binance does not run your code or hold your wallet keys. The repository is not public; a designated Binance audit account receives read-only access for integrity review."
- F-25 "You never compete with your own capital. Participants are never required, asked or permitted to use personal funds to enter, continue or complete this challenge. This is a technical research and developer challenge."

### 1.4 "What makes a strong entry"
- F-30 "It must be genuinely agentic. Innovate at the model layer — domain post-training, fine-tuning, preference optimization, Agentic RL, distillation, tool-use adaptation — and at the harness layer — context engineering, tools, Skills, memory, planning, verification, guardrails, observability, recovery."
- F-31 "Rules and classical ML may support the system, but larger spend and higher call volume earn nothing on their own."
- F-32 "Your information pipeline is your edge. Any public or legally authorized market, news, social, on-chain or derived data, including commercial APIs and your own services, provided you hold the rights. You cover your data, model and hosting costs."
- F-33 "Reliability matters in practice. Failures and recovery affect your system's ability to trade and appear as audit evidence and diagnostics — not as a separate score."
- F-34 "Every scored trade must be traceable. It must map to one registered Agent version and one unique decision record with a concise reason summary."
- F-35 "Competition rules are common to everyone. Teams may use different public or legally authorized data, models, tools and infrastructure. The scored window, eligible instruments, opening value, valuation method, scoring formula and audit standard are the same for all teams. Full technical parameters are issued at onboarding."

### 1.5 Judging and scoring
- F-40 Stage 1, "Proposals are judged by people". Binance selects <25 finalists on:
  - "Feasibility — buildable and operable end-to-end within the timeline"
  - "Agentic depth — real reasoning, tools, memory, planning, verification — not a thin LLM wrapper"
  - "Risk awareness — limits, failure modes, guardrails, recovery"
  - "Originality — a distinctive idea at the model or harness layer"
  - "Ability to deliver — right skills, clear roles, credible milestones"
- F-41 "Not considered: proposal length, design polish, brand names in your stack, or budget."
- F-42 Stage 2: "Proposals are judged by people. The ranking is not." "Every eligible team starts from the same opening value, so scores compare directly." "Calculated from your registered wallet's on-chain state and bStocks execution records, using the published valuation source."
- F-43 (emphasis ours) "**Proposed** FinalScore (%) = (Final Wallet Equity - Opening Wallet Equity) / Opening Wallet Equity x 100. The final rules will confirm the valuation method and treatment of transfers before onboarding."
- F-44 "Real costs are reflected. Trading fees and gas reduce what remains in the wallet, and therefore reduce your final figure."
- F-45 "Tie-break: lower maximum drawdown — the largest percentage fall from a previous equity peak to a later low during the run. Still tied → shared rank."
- F-46 "The full 14 days count. No best-week selection, no dropped days, no live leaderboard."
- F-47 Stage 3 (pass/fail): "Top-ranked teams are provisional winners until the audit clears. Binance reviews commits, version history, manifests, submitted traces and complete local logs, then reconciles sampled decisions against your registered wallet's transactions and bStocks execution records."
- F-48 Audit checks for: "every scored trade mapped to a registered version and a unique decision record; no unmapped trades; no unexplained transfers; no version gaps; no manual intervention; no prohibited data; no material misrepresentation." "The audit adds no points. It confirms your result, or removes it. Awards are announced only after it passes."
- F-49 Winners must also submit: (a) "Chain-of-thought (thinking) output — the reasoning your agent produced for its decisions"; (b) "Full original prompts and tool definitions — system prompts and tool/Skills definitions exactly as deployed"; (c) "Models, plus complete model inputs and outputs — your model artifacts with complete input/output records (for third-party API models, complete request and response records in place of weights)". "Exact scope, format and sharing terms are confirmed in the official rules before onboarding."
- F-50 Not scored: "Presentation and demo polish · model or infrastructure spend · call volume · number of trades · development-phase performance."
- F-51 "Weekly return, drawdown, fees, gas, turnover, version changes, heartbeat gaps, failures and recovery events may be published as diagnostics — no points, no separate rankings." (Publication timing not stated.)
- F-52 "Final scoring, valuation method, treatment of transfers and tie-breakers are confirmed in the official rules before onboarding, and remain fixed for the duration of the scored run." (Instruments and data rules are NOT in this fixed list — see F-73.)

### 1.6 Rules and restrictions
- F-60 "Autonomous operation. Every scored trade must come from your registered Agentic AI system — no manual trading. Each trade maps to one agent version and one unique decision record. New versions must be committed, manifested and logged in a version event before they trade."
- F-61 "Repository integrity. All code affecting decisions, trades or logging must be pushed to your registered repo before it runs — including code on your own remote services. The challenge branch preserves history: no force-pushes, no rewrites. Never commit secrets, keys or private training data. Third-party services are declared in your manifest, not exposed as source."
- F-62 "Honest logging. Daily trace uploads to write-once storage, plus one after any material incident. No end-of-event backfilling. Buffer locally during outages and upload within the published grace window. Credentials never appear in logs. Raw chain-of-thought isn't required in your daily traces — but winning teams are required to provide their thinking output as a deliverable …, so make sure your logging captures it."
- F-63 "Clean information. No Binance-internal data, material non-public information, or future information. No other team's private data, and no source you aren't authorized to use."
- F-64 "Dedicated wallets — prohibited in both phases:" adding your own funds or any external capital; withdrawals, wallet-to-wallet transfers, bridging; unrelated swaps or arbitrary contract calls; manual trading; leverage, shorting, derivatives.
- F-65 Stated purpose: "These keep conditions equal and ensure no participant increases personal financial exposure to stay in the challenge. If development funds run out, there's no replacement — but you can keep building, and your final wallet still starts from the same opening value as everyone else's."
- F-66 "Consequences. Manual trading, unmapped trades, fabricated or incomplete decision records, prohibited data, false declarations, credential misuse and material audit gaps lead to ineligibility or disqualification. Binance may suspend a team or invalidate affected trades for security, integrity or eligibility reasons — this implies no custody or control of your wallet."

### 1.7 Eligibility
- F-70 Open to "all legally-compliant participants" with "full civil capacity under your own local laws": undergraduate and post-graduate students, working professionals, academic or research teams, "applying in their own personal capacity".
- F-71 Must "Hold the rights to every data source, model, API and third-party component in your system" and "Complete identity verification during onboarding — teams that cannot complete it forfeit their place".
- F-72 Not eligible: companies and other legal entities; "Anyone sanctioned or penalized for financial, fraud or market-misconduct violations"; "Anyone with access to non-public information about this challenge, its scoring, or the instruments involved"; "Internal Binance employees". "Binance may verify eligibility at any stage and may withdraw a team that does not qualify."
- F-73 "It is not trading education, investment advice, or a promise of any outcome. Instruments, environment rules, data rules and participant eligibility are subject to final event requirements. Full operating parameters are provided to finalists during onboarding."

### 1.8 Page state on 2026-09-27
- F-80 75 hackers registered on DoraHacks. Announcements: empty. Q&A: one unanswered post (asking for a "password"); no organiser answers.


---

## 2. TEAM FACTS (T) — our drafts, not the rules

### 2.1 Application form fields (as transcribed by the team in `application_answers.md`; not independently captured — the form needs Google sign-in)
- T-01 Registration: email, team name, team size; per member: name, location, role, university/institution, highest degree, major, graduation year, prior experience.
- T-02 Long-answer sections: "Your Proposal"; "System architecture - PDF upload"; "Data / tools used"; "Position & risk management"; "Preventing future leakage and overfitting"; "Reproducibility plan"; "Team capability + intended scope".
- T-03 Consent/logistics questions: may Binance contact you; preferred contact (address / Telegram ID); "Available October 13-November 13?" (differs from the official dev start, Oct 12, F-13; answer for Oct 5 – Nov 20 plus any review); "Available for a late-November or early-December virtual technical review?"; "Eligible, KYC-verified Binance account in your jurisdiction?"; privacy notice.
- T-04 Implications of T-02/T-03 (inference, Med): the form asks separately about leakage/overfitting and reproducibility, so the reviewers weight those beyond the five public criteria (F-40); a post-run technical review may exist (Q-28); a KYC-verified Binance account appears to be expected (Q-26).

### 2.2 LARP draft (proposal.md, application_answers.md, deployment.md, team_and_delivery.md — drafts as of 2026-09-28)
- T-10 Name: "LARP - Liquidity-Aware Regime Planner". Four-person team; roles: Agent/Model lead, Markets/Data/Risk lead, Execution/Security lead, Platform/Audit lead; names and evidence still placeholders.
- T-11 Concept: a "catalyst-aware, regime-adaptive" long/cash agent; "not to trade often"; decisions are long, reduction, exit, or hold; "A calibrated classifier, not a generative LLM, produces the directional forecast, and it may explicitly abstain."
- T-12 Pipeline: (1) connectors with event time, retrieval time, source URI, SHA-256 hash; (2) pinned FinBERT sentiment/relevance + calibrated regime classifier (risk-on / neutral / risk-off / dislocated); (3) a hosted LLM (GPT-6 Sol via OpenAI Responses API, remote storage disabled) receives "only a point-in-time feature snapshot, current positions, and evidence identifiers" (no evidence text in the draft) and returns structured evidence only — catalyst type, signed strength, novelty, durability, source agreement, summary, risks; "Its schema forbids trade actions"; (4) a pinned self-hosted "Laya typed-decision model" returns calibrated UP/FLAT/DOWN/ABSTAIN probabilities ("Jev" is an offline challenger only); (5) deterministic policy maps high-confidence, high-margin UP → candidate buy, strong DOWN on an existing long → exit, else hold; a separate risk governor enforces allowlist, freshness, action semantics, concentration, gross exposure, cash floor, position count, cost/edge threshold, daily loss halt, drawdown kill switch; (6) idempotent Binance adapter keyed by decision ID, reconciliation; (7) hash chain in PostgreSQL, exported to S3 Object Lock; "Failures create incident records and default to HOLD or a controlled reduction." Draft conflicts: step 5 says "drawdown kill switch" while T-14 says only "no new risk"; the proposal allows "controlled reduction" on failure while deployment.md says "Data, model, or verification failure: `HOLD`" (see D-06).
- T-13 Data: SEC EDGAR, issuer IR releases/RSS, GDELT, FRED (vintages), BNB Smart Chain records; organizer-provided prices and wallet state are authoritative. (The page promises only a "published valuation source", F-42; if no organiser price feed is provided, executable Web3 API quotes are the only price, G-30.)
- T-14 Declared risk values (draft): ≤4 open positions; ≤20% of equity per bStock; ≤80% gross, ≥20% cash; "1% equity risk budget per position" reduced for volatility/liquidity; no new risk after a 3% daily loss; no new risk after an 8% peak-to-trough drawdown (exits still allowed); estimated costs ≤50 bp and expected edge ≥ costs + 50 bp. "Every limit and probability threshold is configurable but frozen and hashed before it can govern a scored trade." Ambiguity: "Estimated costs must be at most 50 basis points" does not say one-way or round-trip (G-25).
- T-15 Leakage controls: event + retrieval timestamps; vintage macro data; anchored walk-forward with purge gaps; thresholds chosen on validation periods; strategy chosen before the live window, not by development-period profit. Calibration method (answers): "Classifier temperature and action thresholds are fit on validation periods only."
- T-16 Reproducibility: per-decision trace (evidence hashes, features, LLM assessment, probability vector, model/calibration versions, full hosted request/response, policy result, rationale, prompt version, commit, config hash, risk decision, cost, receipt, incidents), canonicalised and hash-chained; "exact replay" re-runs downstream code on recorded model outputs; daily audit bundle with chain head.
- T-17 Thinking output plan: confirm Binance's required format; if hosted reasoning is insufficient, "the registered scored version will use an organizer-approved open-weight reasoning model". Note: switching implies re-declaring principal services (F-12, Q-22); no official model-approval process is mentioned, so say "declared", not "organizer-approved".
- T-18 Deployment: two ECS/Fargate tasks across AZs, PostgreSQL advisory-lock leader election, RDS, S3 Object Lock (compliance mode), Secrets Manager, CloudWatch alerts; a narrow signer service with no exportable key accepts only allowlisted calls carrying an approved decision ID and risk-decision hash. Live execution gated on five onboarding gates (fixture contract tests; frozen instruments/quote asset/valuation source/transfer rules/fee model; confirmed thinking-output format; manifests; 24-hour accelerated soak + dry run) — see I-65 on gates without fallbacks. Recovery policy quotes: "Ambiguous execution receipt: query by decision ID before retrying" (flawed: decision IDs are not on-chain, see I-64); "Trace sink unavailable: buffer locally, stop new risk if the organizer grace window is at risk"; the second task "remains hot but cannot emit intents".
- T-19 Delivery plan (draft): pre-finalist skeleton (typed contracts, mock adapters, risk engine, hash-chained trace sink, CI); "finalist week 1" = data, features, models, mock execution; "finalist week 2" = Binance adapter, signer boundary, storage, alerts, recovery; then "dry runs, fault injection, configuration freeze". See I-58 for the conflict with the official timeline.
- T-20 Off-hours framing still in the drafts: proposal.md — "The core insight is that tokenized equities operate continuously while their underlying companies, primary markets, and information sources move on different clocks"; answers — "LARP's information edge is timing-aware synthesis". Both conflict with §6.1 and H-01 and should be rewritten before submission (§10).

---

## 3. ENVIRONMENT (E) — graded external evidence (audited 2026-09-29)

Grades: [PRIMARY] [ISSUER-EDU] [SECONDARY] [DEV-REPORT] [ESTIMATE] [UNCONFIRMED] (see §0.1). Statistics that are not [PRIMARY] must not appear in the proposal.

### 3.1 What bStocks are
- E-01 [ISSUER-EDU] "tokenized securities issued by BTech Holdings Limited, a Binance group affiliate"; "standard BEP-20 tokens on BNB Smart Chain"; "backed 1:1 by the corresponding US share held at a regulated custodian"; legally "Certificates representing certain Financial Instruments" under ADGM FSMR, with prospectuses approved by ADGM's FSRA (issuer press release, 2026-06-12). "not offered to US persons"; "available only to eligible users in permitted jurisdictions" — no list of permitted jurisdictions found in the sources checked. — Binance Academy "What are bStocks" (updated 2026-06-29); PR Newswire 2026-06-12.
- E-02 [ISSUER-EDU] Launch ~2026-06-11/12 with CRCLB, MUB, NVDAB, SNDKB, TSLAB (SPCXB pending); 15 tickers "As of 2 July 2026" incl. METAB, MSFTB, PLTRB, QQQB. [SECONDARY] +10 on 2026-07-29 incl. Apple, Amazon (Yahoo Finance; no Binance announcement found). [SECONDARY] CryptoRank (2026-09-29): 76 tokens, ~$405M market cap, including SOXLB ("Semicon Bull 3X ETF").
- E-03 [ISSUER-EDU] "trade 24/7" (BNB Chain blog); "traded around the clock on Binance's spot market" (Academy); minimum "from as little as $5"; self-custody on Binance Wallet/Trust Wallet "powered by Native"; DeFi integrations (Venus, Lista, PancakeSwap, Aster); daily Proof of Collateral.
- E-04 [SECONDARY — no primary located; figures attributed to Binance Research] 47% of first-15-day volume "outside U.S. trading hours" (Chainwire press release 2026-07-01); 62% of July volume "while US markets were dark" and weekend prices capturing a median 92% of the next Monday move (Crypto Briefing 2026-08-26); QQQB "regularly accounts for over 90% of all bStocks activity" (Crypto Briefing) vs ≈82% of tokenized-equity volume in July (CoinDesk Data). **Use only qualitatively: off-hours trading is substantial.**
- E-05 [ISSUER-EDU] No cash dividends: "net dividend value is automatically reinvested… Your bStock balance increases proportionally via the Multiplier adjustment", after US withholding; splits change token quantity; "deposits, withdrawals, and conversions may be temporarily paused" during corporate actions. [SECONDARY] statutory 30% withholding for non-US persons unless reduced by treaty (OneKey blog).
- E-06 [SECONDARY] NVDAB CEX spot volume ~$4.2M vs NVDAUSDT perp ~$418M over Jul 17–22 (both Binance CEX; wublock Substack). The ~285 bp figure in that source is a **perp vs cash-open** gap on SPCX (Aug 10), **not** a bStocks token divergence. [SECONDARY] launch-day per-token 24h volume ~$0.42–2.54M (ourcryptotalk). [UNCONFIRMED] no depeg report found in our search (absence claim).
- E-07 [SECONDARY] BNB Chain offers free bStocks price feeds "powered by APRO Oracle", covering "at least 12 bStocks" (Crypto Briefing 2026-09-17; no official post found).
- E-08 [ISSUER-EDU] The Web3 API is a "single point of aggregation across bStocks, Ondo or xStocks" (BNB Hack blog). The challenge text says **bStocks** only (F-20).

### 3.2 Execution path: Binance Web3 API
- E-10 [PRIMARY] Web3 API launched 2026-06-17 (Binance announcement a9f19002…): "get aggregated swap quotes from multiple vendors, execute token swaps, and broadcast transactions on-chain"; "the API returns unsigned transactions — users sign locally in their own wallets"; "Zero Service Fees and No Positive Slippage Charge (for a limited time)"; MEV "protection cannot be guaranteed in all market conditions". Portal: web3.binance.com/en/dev-portal.
- E-11 [PRIMARY] Python SDK `binance-web3-wallet` v7.0.0 (2026-09-18); base URL `https://web3.binance.com/build`; WebSocket `wss://web3-stream.binance.com/w3w`; RSA or ED25519 signing (one dev repo reports HMAC — confirm at onboarding); official example `quote_and_build_swap_transaction(binance_chain_id="56", …, vendor="LiquidMesh")`. [UNCONFIRMED] no rate-limit table found.
- E-12 [DEV-REPORT] Endpoints seen in hackathon repos: `rwa/tokens`, `aggregator/quote`, `aggregator/approve-transaction`, `pre-transaction/simulate` (others unconfirmed); routes "LiquidMesh SWAP" and "PcsXRfq"; quote validity ~30 s in one repo (another uses its own 60 s cutoff).
- E-13 [DEV-REPORT] "Every bStocks and Ondo quote is LiquidMesh `SWAP`, but the filling venue switches between RFQ makers and AMM-style pools"; `referencePrice` is "token price divided by the token-to-share ratio" (oneticker README). "An RFQ fill is an EIP-712 order that a market maker settles" (ottopus issue #59, 2026-09-24).
- E-14 [PRIMARY] Web3 API prohibited regions: US and territories, Canada, Netherlands, Iran, Cuba, North Korea, Crimea, DNR, LNR, UK, Japan (conditional). **Singapore is not listed.** "IP checks are enforced on both the Developer Portal and the API server side."
- E-15 [DEV-REPORT] "`40304 "compliance restriction"` came back from US, Singapore and Netherlands servers, but not from a French exit" (oneticker README; date not shown).
- E-16 [SECONDARY] Binance.com restricted Singapore users from 2021-10-26 (Forbes 2021-09-28). [ISSUER-EDU] Binance Agent OS hackathon "not available to users in … Singapore" (Binance blog 2026-09-04).
- E-17 [PRIMARY] BSC block time "approximately 0.45 seconds" (Fermi hard fork, 2026-01-14); "0.05 Gwei standard gas price"; typical tx "around $0.005 or less"; gas paid in BNB. [ESTIMATE] a swap of 150k–300k gas × 0.05 gwei = 7.5–15 µBNB ≈ $0.008–0.02 at BNB ≈ $1,000–1,300. **Gas is small relative to spread/slippage**, but a wallet with zero BNB cannot transact.
- E-18 [PRIMARY] The Binance Agentic Wallet ("MPC Keyless"; user-set daily limit and token scope) is a different product from the Web3 API. Binance's Aug 17–Sep 1, 2026 bStocks AI PnL contest scored realised PnL by FIFO and banned wash trades and "activity between wallets controlled by the same entity". Which wallet model this challenge uses is not stated; F-22/F-24 ("your wallets and keys", Binance does not hold keys) suggest self-custody.
- E-19 [SECONDARY] Jeff Li (Binance VP of product): "We really cannot see the reasoning of what the user's action is." (TechCrunch 2026-08-20) — context for why F-49 asks for thinking output.
- E-20 [SECONDARY] Binance Seeds Program (launched ~2025-04-01): Pioneer Talent Program (full-time, ≤5 years' experience) and Accelerator Program (3–6-month projects for students/graduates) (ChainCatcher). No Binance primary found.

### 3.3 Reasoning-trace availability (bears on F-49a)
- E-30 [PRIMARY] Anthropic: "No `display` setting returns the raw chain of thought." `"summarized"` returns a summary produced by a different model; `"omitted"` returns an empty thinking field (full thinking encrypted in `signature`). `"omitted"` is the default on Fable/Mythos 5.x, Opus 5.5, Opus 5, Sonnet 5.5, Sonnet 5, Opus 4.8, Opus 4.7, Mythos Preview; `"summarized"` on Opus/Sonnet 4.6 and earlier.
- E-31 [PRIMARY] OpenAI reasoning models: "reasoning tokens are not visible via the API"; summaries via `reasoning.summary`; `encrypted_content` when not stored. gpt-oss (open weights) emits raw CoT in the `analysis` channel.
- E-32 [PRIMARY] Gemini returns thought summaries ("synthesized versions of the model's raw thoughts"); default depends on API surface. **DeepSeek's hosted API returns CoT in `reasoning_content`.** Qwen3 open weights emit `<think>…</think>` text.
- E-33 [UNCONFIRMED] The model name "GPT-6 Sol" and its behaviour were not checked; assume E-31 applies. With response storage disabled, OpenAI reasoning items come back as `encrypted_content` (E-31), which neither the team nor Binance can read, so they cannot serve as F-49a thinking output; readable text exists only if `reasoning.summary` is requested; a multi-turn tool loop (G-50) must pass the encrypted items back each turn and log them, because complete request/response records (F-49c) then exist only in our logs. Whether the "Laya" checkpoint emits any reasoning text is unknown (T-12).

### 3.4 Calendar (US Eastern unless noted)
| ID | Date (2026) | Event | Grade |
|---|---|---|---|
| E-40 | Wed Oct 14 | CPI (Sep), 08:30 — dev phase | PRIMARY (BLS) |
| E-41 | Oct 27–28 | FOMC; decision Oct 28, the day before the scored run | PRIMARY (Fed) |
| E-42 | ~Oct 28 AMC | MSFT, GOOGL, META earnings | ESTIMATE (unannounced) |
| E-43 | Thu Oct 29 | Q3 GDP advance + Personal Income & Outlays (Sep), 08:30 | PRIMARY (BEA); AAPL/AMZN AMC = ESTIMATE |
| E-44 | Sun Nov 1 | US DST ends; 09:30 ET = 21:30 SGT before, 22:30 SGT after | PRIMARY (15 U.S.C. §260a) + ESTIMATE (conversion) |
| E-45 | Tue Nov 3 | US midterm elections | PRIMARY (2 U.S.C. §7) |
| E-46 | Fri Nov 6 | Jobs report (Oct), 08:30 | PRIMARY (BLS) |
| E-47 | Tue Nov 10 | CPI (Oct), 08:30 | PRIMARY (BLS) |
| E-48 | Wed Nov 11 | Veterans Day: NYSE open; SIFMA recommends full bond-market close | PRIMARY |
| E-49 | ~Nov 17 | NVDA earnings (after the window) | ESTIMATE (unannounced) |

### 3.5 Other public information
- E-50 [SECONDARY] Eventbrite mirror: Sep 10 06:30 UTC → Nov 14 07:00 UTC (= Nov 13, 23:00 US Pacific). [ESTIMATE] No Binance post about this challenge found (absence). [ISSUER-EDU] "BNB Hack: Tokenized Stocks Edition" (Sep 16 – Oct 11, 2026) is a different event.


---

## 4. INFERENCES (I)

Format: **claim** · Basis · Counterpoints · Example · Confidence · Proposal use (Y = may inform proposal text; N = internal only).

### 4.1 Scoring mechanics
- **I-01 The score is total % return; drawdown only breaks ties.**
  Basis: F-43, F-45. Counterpoints: the formula is labelled "Proposed" and the valuation method and treatment of transfers are still to be confirmed (F-43, F-52); Binance may "invalidate affected trades" (F-66) with an undefined equity effect (Q-23); so the final metric could differ in detail. Example: +6% with a 10% drawdown outranks +5% with a 1% drawdown. Confidence: Med-High. Proposal use: N (say nothing about gaming the metric).
- **I-03 Holding the opening asset scores ≈0%.**
  Basis: F-43; gas is tiny (E-17). Counterpoints: (a) the opening asset is unknown (Q-03) — if it includes BNB for gas and BNB counts in equity, a flat book still moves with BNB; (b) if the opening value were delivered as bStocks, "flat" would require selling first; (c) whether a team with few/no trades is ranked is unknown (Q-17). Example: 10,000 USDT held for 14 days → 10,000 USDT less ~$0 gas → 0.00%. Confidence: Med. Proposal use: Y, only as "cash/hold is a valid, logged decision".
- **I-04 Every trade must clear a cost hurdle; costs compound.**
  Basis: F-44, F-50 ("number of trades" not scored). Counterpoints: service fees are waived "for a limited time" (E-10), so explicit fees may be ~0 during the run — but spread, AMM price impact and RFQ maker spread remain and are not waived; failed txs still burn gas. Example: a 0.3% round-trip cost over 30 round trips leaves 0.997³⁰ ≈ 0.914 of equity (≈ −8.6%) before any edge; at T-14's worst reading (50 bp one-way = 100 bp round trip) just 10 round trips leave 0.99¹⁰ ≈ 0.904 (≈ −9.6%). (Numbers are illustrative on the whole book; per-position costs scale with position weight.) Confidence: High. Proposal use: Y (LARP's cost/edge threshold, T-14).
- **I-05 Absolute return will be dominated by market direction; differences between teams come mostly from exposure level and concentration.**
  Basis: F-64 (long-only), F-15 (short window); L-14, L-16. Counterpoints: if the eligible list includes low-beta or non-equity RWAs, dispersion changes; a concentrated book around an earnings event is driven by idiosyncratic moves — single-name earnings gaps can exceed the whole book's beta move [UNSOURCED; measure on our own data] — not beta. Example: if QQQ falls 3% over the window, a book averaging 30% invested in QQQ-like names loses ≈0.9%; one averaging 100% loses ≈3%. Confidence: Med. Proposal use: N.
- **I-06 Without shorts, leverage or derivatives, the risk-reduction levers are cash and rotation to lower-volatility eligible names.**
  Basis: F-64, E-02 (index ETF tokens such as QQQB exist). Counterpoint: whether index tokens are in the eligible list is unknown (Q-19). Confidence: Med-High. Proposal use: Y.
- **I-07 The valuation source and instant can move the final score independently of skill.**
  Basis: F-42 ("published valuation source"), E-03 (24/7 trading), E-13 (`referencePrice` is not an independent fair value). Counterpoints: if valuation uses executable on-chain quotes at a time the US market is open, the effect is small; it is the same for all teams (F-35). Example: a position marked at a stale off-hours quote 1% above the next open would overstate equity by 1% × position weight. Confidence: Med. Proposal use: N (ask Q-04).
- **I-08 Window arithmetic.** Oct 29 (Thu) → Nov 12 (Thu) is 15 calendar days inclusive, 11 US weekdays, two weekends (Oct 31–Nov 1, Nov 7–8); "14 days" therefore implies boundary timestamps that are not published. Final activation (Oct 27–29) overlaps day 1. **Unresolved dependency (Q-06): nothing in the design may depend on the exact start/end instant until it is published.** Confidence: High (arithmetic). Proposal use: N.
- **I-09 The window opens into dense scheduled events.**
  Basis: E-41, E-43, E-45..E-47 (primary); E-42 (estimated). Counterpoints: earnings dates are unannounced; the eligible list may exclude reporting names. Example: day 1 carries GDP/PCE at 08:30 ET (20:30 SGT). The FOMC decision at 14:00 ET Oct 28 is 02:00 SGT Oct 29, so it may fall inside or outside the scored window depending on Q-06. Confidence: Med-High. Proposal use: Y (event-aware risk policy), without listing unconfirmed earnings dates.

### 4.2 Compliance and audit
- **I-20 Traceability must be designed in (write-ahead decision records).**
  Basis: F-34, F-47, F-48. Counterpoint: write-ahead produces records for intents that never execute (crash between record and signature); these need an explicit terminal status ("aborted, not submitted") so they are not mistaken for missing trades. Example: decision `dec-0123` written 10:00:00.100, process dies 10:00:00.200 before signing → on restart, chain query shows no tx → append status `ABORTED_NOT_SUBMITTED`. Confidence: High. Proposal use: Y.
- **I-21 Default to one decision record per order, and map every on-chain effect back to it.**
  Basis: F-34 ("one unique decision record"). Counterpoints: a rebalance may legitimately produce several orders; one order may settle in several txs (partial fills, RFQ settlement). Conservative design records both directions (decision → orders → txs) until Q-10 is answered. Confidence: Med. Proposal use: Y.
- **I-22 "Version" should cover everything that changes decisions: code, prompts, tool schemas, configs, risk parameters, thresholds, model checkpoints/snapshot IDs, dependency lockfile.**
  Basis: F-60, F-61 ("all code affecting decisions"), F-49b ("exactly as deployed"). Counterpoint: the rule text says "code"; prompts and configs may not be "code" in the organiser's reading — but versioning them costs little and removes the risk. Vendor model aliases that update silently are a hidden version change. Confidence: Med-High. Proposal use: Y (LARP already does this, T-14, T-15).
- **I-23 A process may trade only if its content hash equals the manifest of the currently active version event.**
  Basis: F-60, F-61. Counterpoint: rolling back is legitimate if the rollback is itself a version event; "latest manifest" is the wrong check. Confidence: High. Proposal use: Y.
- **I-24 "No manual intervention" (F-48) is broader than "no manual trading" (F-60).**
  Counterpoint: organisers presumably expect restarts and bug fixes; an incident policy is promised at onboarding (F-18). Until then, any human action is logged as an incident and halts are a versioned code path. Confidence: Med. Proposal use: Y (humans can halt, never trade).
- **I-25 Humans never sign from, approve for, or interact with a challenge wallet.**
  Basis: F-60, F-64, F-48. Example of an accidental breach: a teammate opens the wallet in a browser extension that auto-swaps dust for gas → an unmapped tx. Confidence: High. Proposal use: Y.
- **I-26 Token approvals are probably inside the sanctioned flow; a gas top-up swap is uncertain; day-0 gas is a blocking question.**
  Basis: E-12 (`approve-transaction` endpoint, DEV-REPORT), F-64 ("unrelated swaps"), F-25/F-64 (no own funds). Counterpoint: organisers may fund BNB directly or sponsor gas, making the issue moot. Example: final wallet funded with 10,000 USDT and 0 BNB → the first approve/swap fails. Confidence: Med. Proposal use: N (ask Q-03, Q-08).
- **I-27 RFQ fills can settle via a maker-submitted transaction, so our own wallet may not originate the on-chain tx.**
  Basis: E-13 (DEV-REPORT). Consequence: the decision record must store quote ID, order hash and the settlement tx hash, or the trade may look unmapped. Counterpoint: the organiser's "bStocks execution records" (F-42) may already link these. Confidence: Med. Proposal use: N.
- **I-28 Balance changes without trades will happen and must be logged as non-trade events.**
  Basis: E-05 (dividend Multiplier, splits — ISSUER-EDU); the opening-value funding transfer; unsolicited tokens (general public-chain behaviour). Counterpoint: a rebasing Multiplier may change value without any token transfer event; detect via periodic balance snapshots, not only transfer logs. Confidence: High. Proposal use: N.
- **I-29 Winners' "thinking output" needs a deliberate model choice and capture plan.**
  Basis: F-49a, F-62. Evidence: Anthropic, OpenAI and Gemini hosted APIs return summaries or nothing (E-30..E-32); full reasoning text comes from open-weight models run by the team (Qwen3, gpt-oss) **and from DeepSeek's hosted API** (`reasoning_content`, E-32). For LARP, the directional decision is made by a classifier (T-12), which produces probabilities, not reasoning text; whether a probability vector plus the LLM's structured assessment and summaries satisfies "the reasoning your agent produced for its decisions" is unknown (Q-16). Counterpoints: organisers may accept summaries; visible reasoning is not a faithful account of causation anyway (L-53), so structured decision fields remain the audit-grade explanation. In LARP the LLM reasons about *evidence*, not the *decision*; the decision's "thinking" is the classifier vector + policy trace + verified evidence (see E-33 for why hosted reasoning with storage disabled may be unreadable). Confidence: High on the need to decide; Low on what will be accepted. Proposal use: Y (state the capture plan, as T-17 does).
- **I-30 Logs must be real-time, append-only and externally anchored; a hash chain alone proves tamper-evidence, not completeness.**
  Basis: F-62 ("No end-of-event backfilling", write-once storage), F-47 ("complete local logs"). Reasoning: a hash chain lets a verifier detect edits to records *after* the chain head has been published somewhere the team cannot rewrite. It cannot show that events were never recorded, and records created between anchors can be rewritten undetectably until the next anchor. Completeness evidence comes from cross-checks: every on-chain tx reconciled to a record (G-43), monotonic sequence numbers with heartbeat records (gaps show as outages), write-ahead records before signing (I-20), and anchoring frequency. Example: with daily anchoring only, a record written at 01:00 could be altered until the 00:30 next-day upload; hourly anchoring shrinks that window to ≤1 h. Counterpoints: organisers only require daily uploads, so more frequent anchoring is a POLICY; an anchor counts only where the team cannot write an alternative — a team-controlled S3 Object Lock bucket can hold a *second* bundle, so the organiser's write-once store is the credible anchor; never anchor via a transaction from a challenge wallet ("arbitrary contract calls", F-64). Confidence: High. Proposal use: Y (state tamper-evidence + reconciliation, not "proof of completeness").
- **I-31 "Complete local logs" is a retention and capacity requirement.** Full model I/O for ~5 weeks (dev + run) may be large; a full disk means incomplete logs. Confidence: High. Proposal use: N.
- **I-32 Sampling does not lower the bar.** The audit samples decisions to reconcile (F-47), but "every scored trade mapped" is universal and "incomplete decision records" disqualify (F-66). Confidence: High. Proposal use: N.
- **I-33 A hotfix during an outage is constrained by "pushed … before it runs" (F-61).** If the registered remote is unreachable, the compliant options are to stop taking new risk or run a pre-registered safe-mode build. Confidence: High. Proposal use: Y (recovery design).
- **I-34 The dev phase counts for compliance.** Wallet prohibitions apply "in both phases" (F-64); eligibility can be checked "at any stage" (F-72). Confidence: High. Proposal use: N.
- **I-35 Declared risk parameters are not frozen by rule, but behaviour must stay consistent with what is currently declared.**
  Basis: F-60 ("Keep improving — every version must be committed and logged before it trades") permits changes; F-48/F-66 prohibit "material misrepresentation" and "false declarations"; no official text freezes proposal parameters. Reasoning: a limit changed through a logged version event with a stated reason is an improvement; a limit silently exceeded is a misrepresentation risk. Counterpoints: (a) organisers selected finalists partly on the risk design; a change that reverses its character (e.g., from ≥20% cash to all-in on one name) may be judged against the spirit of the selection even if versioned; (b) the principal data/model services declared at onboarding (F-12) are a separate declaration that may need re-declaration if swapped (Q-22). Example: proposal says ≤20% per name; v1.3 raises it to 25% with a logged reason after liquidity data → consistent. v1.0 trades 45% in one name with no version change → misrepresentation risk. Confidence: Med. Proposal use: Y ("values are versioned configuration; limits are enforced in code").
- **I-36 Clock discipline is part of "no future information".** An input whose recorded fetch time is later than the decision time looks like future data even if honest. Confidence: High. Proposal use: N.
- **I-37 Development evaluations that use an LLM on historical events are contaminated by memorisation.**
  Basis: L-20..L-24. For LARP: walk-forward splits and purge gaps protect the classifier from temporal leakage between splits, but **not** the hosted LLM's evidence step (T-12, T-15), which may already know how a historical catalyst played out. Counterpoints: LARP's LLM extracts structured fields and does not forecast direction, which reduces but does not remove the risk (judgements of "durability" or "novelty" can be coloured by known outcomes). Example: asked in validation to rate the durability of a 2025 earnings beat, a model trained on 2025–26 text may "know" the stock rallied. Mitigations: evaluate on events after the model's training cutoff; anonymise ticker/company/date in the evidence prompt (L-21); report both. Further counterpoints: anonymisation leaks identity for mega-caps ("a $4T GPU maker") — test by asking the model to name the firm; post-cutoff windows may contain fewer than ~100 usable catalysts, so report confidence intervals. Confidence: High. Proposal use: Y.
- **I-38 Data and model rights are an eligibility condition (F-71).** Keep a register with licences for every source and model. For LARP: GDELT, SEC EDGAR and FRED have public terms that must still be read; the Laya checkpoint link points to an individual's Hugging Face repository (T-12 source list), so its licence and provenance must be confirmed before it is declared. Unknowns [UNCONFIRMED]: architecture (if generative, T-11's "not a generative LLM" may be false); pre-training data and cutoff (look-ahead in backtests before that cutoff, I-37); licence (F-71); redistribution rights for the F-49c handover; maintenance. If the team only temperature-scales a third-party checkpoint, the model-layer claim (I-51) is thin — state what the team trains (e.g., a head/adapter on its own point-in-time labels). Jev is offline only; leave it out of proposal text. Confidence: High. Proposal use: Y (brief).
- **I-39 The development wallet is a non-refillable test budget, and dev and final wallets are distinct** (F-65, F-12, F-14). Confidence: High. Proposal use: N.

### 4.3 The instrument universe
- **I-40 The documented short-horizon news edges are weakest where this universe sits.**
  Basis: E-02 (mostly US large caps and ETFs), L-22 (predictability "especially for small stocks and negative news"), L-32 (PEAD largely gone in large caps). Counterpoints: an earnings-announcement premium has been documented across markets (L-32); LLM news embeddings show predictability across markets (L-31); the 24/7 structure may create timing effects not covered by that literature (H-01). Implication: use news mainly to avoid or exit; enter only on fresh, specific, verifiable positive information; abstain otherwise. Confidence: Med. Proposal use: Y (as design rationale, not as a claim of edge).
- **I-41 Leveraged-ETF tokens and DeFi deposits are out of bounds unless explicitly allowed.** SOXLB (3x) exists (E-02, SECONDARY); holding it is arguably "leverage" (F-64); depositing bStocks into lending or LP is leverage and/or an "arbitrary contract call". Confidence: Med-High. Proposal use: N.
- **I-42 Latency risk is mostly quote staleness and route switching, not block time.** Blocks ~0.45 s (E-17, PRIMARY); quotes live tens of seconds and routes switch between RFQ and AMM (E-12, E-13, DEV-REPORT). Deliberation must finish before the quote is requested. Confidence: Med. Proposal use: Y.

### 4.4 Stage 1 (proposal) — against the rubric
- **I-50 Agentic depth is judged on "real reasoning, tools, memory, planning, verification" (F-40).** LARP's LLM currently makes a single structured call with no tools, memory, planning or claim verification (T-12); the classifier and rules are not agentic. The harness is strong on guardrails, observability and recovery. Risk: judges read LARP as "an ML pipeline with an LLM feature extractor". Counterpoint: F-31 says rules and classical ML "may support the system", and a conservative, auditable design scores on Risk awareness. As drafted, the LLM receives evidence *identifiers*, not evidence text (T-12), so a retrieval tool (G-50) is a prerequisite, not an enhancement. Remedy (G-50..G-54): add a bounded tool loop, thesis memory, a catalyst planner and claim verification without giving the LLM trade authority. Confidence: Med-High. Proposal use: Y.
- **I-51 Model-layer work must be small, testable and ready early.** Build time is ~2 weeks after ~1 week of onboarding (F-12, F-13). LARP's probability-scored classifier with an abstention rule is a credible model-layer piece if the prediction target, horizon and label definition are stated. A fine-tuned or self-hosted model also triggers the F-49c artefact handover. Confidence: Med-High. Proposal use: Y.
- **I-52 Declare a coherent risk framework with concrete initial values, and say the values are versioned configuration.** See I-35. Counterpoint: vague ranges can read as low risk awareness; concrete numbers read better if they are also enforced in code. Confidence: Med. Proposal use: Y.
- **I-53 Describe capabilities, not vendors; be concise** (F-41). Vendors are still declared at onboarding (F-12); "budget not considered" does not waive Feasibility — an expensive always-on stack must look sustainable for a student team. Confidence: High. Proposal use: Y.
- **I-54 Acceptance odds are unknown.** 75 DoraHacks registrants on Sep 27 (F-80) for ≤25 slots; registration ≠ submission. Confidence: Low. Proposal use: N.
- **I-55 One central capability reads as more buildable than several parallel innovations.**
  Basis: F-40 Feasibility ("buildable and operable end-to-end within the timeline") and Ability to deliver ("credible milestones"). Reasoning: presenting event analysis, exposure timing and off-hours valuation as three separate innovations multiplies what must work in two weeks and dilutes the "distinctive idea". Counterpoint: Originality still needs one distinctive idea; a single capability that is ordinary (generic news sentiment) would score low. Choice for LARP: central capability = **verified catalyst → probability-scored, abstaining decision**; regime classification and off-hours pricing are supporting controls (see §6). Confidence: Med-High. Proposal use: Y.
- **I-56 Claims of edge should be framed as hypotheses with test plans.**
  Basis: F-73 ("not … a promise of any outcome"), base rate of live LLM trading (L-12..L-16 PRIMARY; L-10/L-11 SECONDARY, internal only), unknown costs and liquidity (E-06, E-13). Example wording: "We will test whether verified catalysts support decisions that clear estimated costs; if not, the agent defaults to hold." Counterpoint: too much hedging can read as lack of conviction; state the mechanism concretely and the test plainly. Confidence: High. Proposal use: Y.
- **I-57 Reviewers see what the form asks for** (T-02): leakage/overfitting and reproducibility have their own sections, so they are likely weighed alongside F-40. LARP's answers there are strong (T-15, T-16) but must add the LLM-memorisation point (I-37). Confidence: Med. Proposal use: Y.
- **I-58 LARP's delivery plan conflicts with the official timeline.**
  Basis: F-12..F-15, T-19. The official development phase is Oct 12–26 and already expects "small-value trades", "test recovery", a week-one checkpoint and "end-to-end self-check evidence" (F-13); final activation is Oct 27–29 and overlaps day 1 of scoring (F-14, F-15). LARP places the Binance adapter in "finalist week 2" and dry runs after it; there is no later slot. Remedy: move a minimal real adapter and one small real buy/sell into dev week 1; run the soak and fault injection in dev week 2. Onboarding (Oct 5–10) should appear explicitly. Confidence: High. Proposal use: Y.
- **I-59 LARP's infrastructure is heavy for the timeline.** Two-AZ Fargate with leader election, RDS, Object Lock and a separate signer service (T-18) is defensible for four people but adds failure modes (lock loss, failover double-execution). Counterpoint: it directly supports Reliability and Risk awareness. A credible middle path: one primary task plus a cold standby, with the leader lock retained as a safety interlock. Confidence: Med. Proposal use: Y (show it is scoped).
- **I-60 The DoraHacks "Deadline 2026/11/13 22:59" may require a BUIDL submission.** Eventbrite shows Nov 14 07:00 UTC. Confidence: Low. Proposal use: N (Q-18).
- **I-61 LARP's "1% equity risk budget per position" is undefined until the risk measure and horizon are stated.**
  Basis: T-14. Example with an assumed definition (risk = 2 × σ over a 5-trading-day holding horizon): a name with 2.5% daily volatility has σ₅ ≈ 2.5% × √5 ≈ 5.6%, so 2σ ≈ 11.2% and size ≈ 1% / 11.2% ≈ 8.9% of equity; an index token with 1.2% daily volatility gives 2σ₅ ≈ 5.4% and size ≈ 18.6%. Consequences: at 2.5% daily vol four names ≈ 36% gross; at 1.5% (≈14.9% each) ≈ 60%; names or index tokens at ≤ ~1.1% daily vol hit the 20% per-name cap (1.0% → 22.4% before the cap). Which caps bind depends on the universe (Q-19); the 2.5% figure is an assumption, not a measurement. Also define whether σ uses the underlying's sessions or the token's 24/7 series. Counterpoint: a different definition (1σ, or a stop distance) changes sizes by ~2×. Confidence: High that the definition is needed. Proposal use: Y (define it in one line).
- **I-62 LARP's drawdown rules stop new risk but do not reduce existing risk.**
  Basis: T-14 ("no new risk after… 8% drawdown; reductions and exits remain available"). Example: peak equity 100 = 80 holdings + 20 cash. An 8% drawdown means holdings fell 10% (to 72; now 78% of equity). A further 10% fall costs 7.2 → equity 84.8, a 15.2% total drawdown. At I-61's typical ≈36% gross the same moves give 3.6% and then ≈6.8%, so the 8% halt may never trigger. Gap risk: a 20% position gapping −15% costs 3% of equity in one print, which the daily-loss check sees only afterwards. Counterpoint: forced de-risking crystallises losses and can whipsaw; the choice is a POLICY. Remedy option: an automatic reduction step at a deeper level (G-22). Confidence: High (arithmetic). Proposal use: Y (state which behaviour is intended).

- **I-63 The classifier target must be defined before any calibration claim.**
  Required: (a) horizon h (e.g., next [5] US sessions); (b) price series — bStocks exist only since ~Jun 2026 (E-02), so training labels will mostly come from the *underlying* US shares while live actions are on the token; basis risk (off-hours token moves, Multiplier adjustments E-05) must be checked on the few months of token data; (c) classes, e.g., UP = r_h > +(c + b), DOWN = r_h < −(c + b), FLAT otherwise, with c = round-trip cost and b = buffer; (d) absolute vs index-relative return; (e) **ABSTAIN is not an outcome class** — it has no ground-truth label, so "calibrated P(ABSTAIN)" is undefined; implement abstention as a selection rule (selective classification, arXiv:2110.14914, cited by LARP) and calibrate only the UP/FLAT/DOWN vector; (f) action semantics: FLAT or ABSTAIN on a held name → HOLD (+ falsifier re-check, G-51); DOWN on a non-held name → no action (no shorting). Counterpoint: only the high-P(UP) tail trades, and it rests on few samples — report reliability for that bin with a bootstrap interval, not only overall calibration error. Confidence: High. Proposal use: Y (one line: target, horizon, abstention rule).
- **I-64 A hot standby can double-execute.** PostgreSQL advisory locks are session-scoped: after a network partition the server releases the lock while the old leader may already hold a signed transaction; the new leader's recovery then sees a write-ahead intent with no tx and resubmits. Wallet nonces protect self-submitted txs but not RFQ EIP-712 orders settled by makers (I-27). deployment.md's "query by decision ID before retrying" does not work because decision IDs are not on-chain. Remedy: G-18. Confidence: High. Proposal use: N (implementation).
- **I-65 Onboarding gates need deadlines and fallbacks.** T-18 disables live execution until, among others, "Binance confirms the accepted format for model thinking output" and a fee model is frozen. Organiser answers may be late (F-80: no Q&A answers so far) while the scored run starts regardless. Rule: any gate still pending on Oct 26 falls back to a pre-registered conservative option (thinking format → capture everything per G-06 and trade; fee model → estimate from dev-phase fills), recorded in the version manifest. Counterpoint: some gates (valuation source, eligible list) have no safe fallback; then trade minimally and log why. Confidence: High. Proposal use: Y ("gates with fallbacks").
- **I-66 The regime classifier cannot be validated live and is hard to calibrate at all.** Regimes are latent; rule-defined labels make a classifier redundant, and after-the-fact labels use look-ahead; "dislocated" may have fewer than ~10 historical episodes; the 14-day run will contain 0–1 regime transitions. Policy: define regimes by pre-registered rules on realised volatility, drawdown and [spread] thresholds; validate the *exposure effect* with a block bootstrap over historical stress episodes; report the episode count; do not call the regime model "calibrated". Confidence: High. Proposal use: Y.

### 4.5 Team-specific
- **I-70 Jurisdiction and account eligibility.** The challenge reached the team via a university email (team statement), which suggests students here are expected. Evidence to reconcile: E-14 (Singapore not on the Web3 API prohibited list, PRIMARY); E-15 (a developer saw `40304` from Singapore, DEV-REPORT); E-16 (Binance.com restricts Singapore; another 2026 Binance hackathon excluded Singapore); T-03 (the form asks for an "Eligible, KYC-verified Binance account in your jurisdiction"). Failing identity verification forfeits the place (F-71). Remedy: one question to organisers (Q-12, Q-26); never route around geo-restrictions (G-17). Confidence: Med. Proposal use: N.

---

## 5. HYPOTHESES (H) — to be tested, never claimed

- **H-01 Off-hours pricing.** *Claim:* when the US market is closed, verified information that arrives after the close is not fully reflected in executable bStocks quotes, and the gap can be captured after costs.
  Supporting evidence: off-hours trading is substantial (E-04, SECONDARY); routes switch between RFQ and AMM (E-13, DEV-REPORT). Against: weekend prices reportedly anticipate most of Monday's move (E-04, SECONDARY), which suggests efficiency; off-hours spreads, depth and the valuation source are unknown (Q-04, Q-29); our only 285 bp example was a perp, not a token (E-06).
  Test (read-only quotes, no fair-value model): for each verified post-close catalyst, record the executable token buy quote at detection time t₀ and the executable token sell quote at [US open + 30 min]; the after-cost difference is the observation. Weekend statistics in E-04 are SECONDARY and not used.
  Pass criterion (pre-registered): n ≥ [20] observations and mean after-cost gain > 0 with a one-sided bootstrap p < [0.05]. **Sample reality:** the dev phase has 2 weekends (Oct 17–18, Oct 24–25) and ~9 weeknight closes, and only some will carry a verified catalyst, so n ≈ 0–10. **Therefore v1.0 ships with off-hours logic as an execution guard only** (avoid trading into wide off-hours spreads; mark positions from executable quotes); logging continues during the run for a later decision. Proposal wording: "we will test"; never "we exploit".
- **H-02 Verified catalysts improve decisions over no-news baselines.** *Claim:* the classifier with structured evidence beats a no-evidence classifier at matched coverage, after costs. Test (pre-registered): metric = after-cost mean return of selected cases minus the baseline's at matched coverage, on post-cutoff walk-forward data (I-37); report calibration (Brier/reliability for the traded bin, I-63), coverage and confidence intervals. Pass: CI lower bound > 0. Sample warning: post-cutoff windows for recent models may hold only a few months. If H-02 fails, the evidence step is kept as a **veto** (avoid/exit on verified negative catalysts, I-40) and the proposal/manifest says entries are regime- and cost-gated only.
- **H-03 Regime gating reduces losses in stress periods.** A numerical regime model has no LLM memorisation issue, so a post-cutoff split is not the relevant test. Test: block bootstrap over historical stress episodes (I-66), comparing drawdown and coverage with and without gating. Kill: if gating does not reduce drawdown at acceptable coverage, replace it with a simple volatility cap.


---

## 6. CONCEPT AND DESIGN PRINCIPLES

### 6.1 Scope: one central capability
- **Central capability (LARP):** turn *verified, point-in-time catalysts* into *probability-scored long / hold / exit decisions that may abstain* (target and abstention defined per I-63). "Reduce" exists only if the policy defines it (e.g., P(DOWN) in [θ_r, θ_exit) on a held name → reduce to [50]%); otherwise remove it from all text (D-06). The innovation claim lives here: evidence gathering and verification (harness layer) feeding a probability-scored classifier, calibrated on validation data (I-63), with an abstention rule (model layer).
- **Supporting control 1 — regime governor:** the regime classifier (T-12) sets the exposure budget and can veto entries; it is a risk control, not a second strategy.
- **Supporting control 2 — deterministic risk governor:** limits, costs, freshness, allowlist (T-12, T-14).
- **Supporting control 3 — off-hours handling:** execution guard by default; entry logic only if H-01 passes.
- **Not claimed:** alpha, a fair-value model, or any return expectation (I-56).
- Name note: "Liquidity-Aware Regime Planner" foregrounds the supporting controls (liquidity, regime), not the central capability; the team may keep it, but the first sentence of the proposal must name the central capability.
- Superseded: v0.2's "C1 + C2 + C3 synthesis" (three co-equal innovations) — dropped per I-55.

### 6.2 Harness additions needed for agentic depth (closes I-50)
All four keep the LLM away from trade authority and fit LARP's trace schema.
- **G-50 Bounded tool loop [POLICY].** The evidence LLM may call up to [6] tools per decision within [60] s: fetch filing section, fetch issuer release, search a second independent source, look up the name's historical reaction to similar catalysts (from our point-in-time store), query the feature store. Every tool call and result is logged in the decision record. Exceeding the budget → assessment returned as "insufficient evidence" → classifier input marks low evidence quality.
- **G-51 Thesis memory [POLICY].** Each open position stores a thesis object: catalyst, evidence IDs, expected horizon, falsifier conditions. Each cycle re-checks falsifiers against new evidence; a fired falsifier produces an exit candidate. After exit, a short post-mortem is stored and retrievable (with timestamps, G-35).
- **G-52 Catalyst planner [POLICY].** A calendar-driven planner schedules research ahead of known events (earnings dates once announced, E-41..E-47 macro releases) and decides which names get LLM attention each cycle; logged as a planning record.
- **G-53 Claim verification [POLICY].** A separate step checks that each claim in the evidence assessment cites an evidence ID whose content supports it (string/number match plus a second-model or rule check). Unsupported claims are removed; if the core catalyst claim fails, the classifier is not called and the decision record is HOLD with `hold_reason=EVIDENCE_UNVERIFIED`.
- **G-54 Harness failure modes [PRACTICE].** Tool loop has hard timeouts, retry caps and a max-token budget; loops, schema failures or empty evidence resolve to HOLD with an incident record.
- Counterpoints: each addition adds latency and failure surface (L-52) and competes with I-55/I-58 for build time; keep the graph shallow (G-37); measure each addition's value in dev (H-02) and remove what does not help.
- **Build order and cut line [POLICY]:** G-50 (≤3 tools, retrieval first) and G-53 are required for v1.0; G-51 falsifiers required, post-mortems optional; G-52 may be a static calendar. Anything not green by Oct 22 is cut, not delayed. The proposal describes the v1.0 set only.

### 6.3 Principles (P)
- P-01 **Hold/cash is a legitimate, logged decision** (I-03). It is not free in every scenario (it forgoes gains in rising markets), so it must come from the policy, not from failure.
- P-05 **Every trade pays its costs.** Entry thresholds are set so that, on validation data, selected cases cleared round-trip cost plus a buffer (G-25); live costs come from the actual quote. State one-way vs round-trip explicitly (T-14). Use a no-trade band so small signal changes do not cause trades (L-34).
- P-06 **Reason slowly, execute deterministically.** LLMs and classifiers produce inputs minutes-to-hours ahead; no model on the signing, limit-check, version-gate, logging, reconciliation or recovery path (T-12 already does this).
- P-07 **Sizing is simple and bounded.** Size from a defined volatility-scaled risk budget with hard caps (I-61, G-29). Do not commit to Kelly-style sizing: there is no validated payoff model or sufficient sample to estimate edge per trade.
- P-08 **Every thesis carries its own falsifier** (G-51).
- P-09 **Verification can only say no.** Verifiers veto or shrink; they never add or enlarge. Use external checks (tools, rules), not the same model re-thinking (L-50).
- P-10 **Write before you sign** (I-20).
- P-11 **Nothing trades that isn't registered** (I-23).
- P-12 **Point-in-time or it didn't happen** (I-36, I-37).
- P-13 **Humans may stop, never steer the wallet** (I-24, I-25).
- P-14 **Behaviour matches current declarations;** changes go through versions with reasons (I-35).
- P-15 **Capture the thinking you may be asked for** (I-29).
- P-16 **Harness over model choice.** Choose models for schema reliability, latency, cost and reasoning-trace access (L-12, L-13).
- P-17 **The dev wallet is a test budget** (I-39).
- (P-02, P-03, P-04 moved to Appendix A as strategy opinions.)

### 6.4 Decisions (D)
- D-01 **Risk posture (before submission, Sep 30).** LARP's draft is conservative (T-14; with I-61's example sizes ≈35% typical gross). Options: keep it (strong on Risk awareness; low upside in rising markets) or widen caps. Either way: state the risk-budget definition (I-61) and drawdown behaviour (I-62). Contest-strategy arguments for more variance are in Appendix A and must not drive proposal wording.
- D-02 **Concept scope — resolved:** LARP central capability as in §6.1.
- D-03 **Thinking-output model plan (by onboarding declaration, Oct 5–10):** hosted LLM with summaries + classifier probabilities vs an open-weight or DeepSeek reasoning model at the evidence step (I-29, Q-16).
- D-04 **End-of-window policy (after Q-04/Q-06 are answered).**
- D-05 **Infrastructure scope (before dev week 1):** two-AZ hot standby vs primary + cold standby (I-59); if hot, G-18 fencing is mandatory.
- D-06 **Decision semantics (before Oct 12):** label horizon, thresholds and price series (I-63); whether "reduce" exists (§6.1); failure behaviour — HOLD only, or reduction only on a risk-limit breach with fresh quotes, never on data/model failure (T-12 conflict); daily-loss day boundary (G-22); "kill switch" vs "new-risk halt" wording (T-12).

---

## 7. GUARDRAILS (G)

Tags: **[RULE: F-xx]** required by official text · **[RULE-DERIVED]** our conservative implementation of a rule whose exact reading is open · **[POLICY]** team choice · **[PRACTICE]** engineering hygiene. MUST = enforced in code and tested; SHOULD = default.

### 7.1 Hard constraints (MUST)
- G-01 **Signer allow-list** [RULE-DERIVED: F-64]. Reject any transaction whose `to` is not in `ALLOWED_CONTRACTS` (router/settlement contracts from the Web3 API or organiser allowlist) or whose selector / EIP-712 type is not in `ALLOWED_SELECTORS`. Approvals only to the API-returned router, for at most the order amount. No transfers, bridging, withdrawals, deposits, lending, LP, or permit signatures outside the API flow. Test: signing any other call fails. (LARP: T-18 signer service.)
- G-02 **Long-only spot** [RULE: F-64]. Quantity ≥ 0; no leverage, shorting, derivatives. Leveraged/inverse ETF tokens excluded unless explicitly eligible and confirmed [RULE-DERIVED, I-41].
- G-03 **Version gate** [RULE-DERIVED: F-60, F-61]. Before each order: hash of (commit SHA, lockfile, prompts, tool schemas, configs, risk params, thresholds, model checkpoint hashes/snapshot IDs) equals the manifest of the active version event; working tree clean; commit present on the registered remote. Any failure → no order.
- G-04 **Decision record per order, write-ahead** [RULE: F-34 — one unique record with a concise reason per scored trade] [POLICY: per-order granularity, write-ahead, field list, ≤3-sentence summary]. Minimum fields: `decision_id`, `version_id`, `ts_decision_utc_ms`, input hashes + pointers with `source_ts` and `fetched_ts`, model call IDs, evidence assessment, probability vector, policy result, risk-check results, reason summary (≤3 sentences, generated from the structured fields actually used), intended order, quote ID, route (swap/RFQ), market state (open/extended/closed). Appended after execution: tx hash(es), order hash, fill qty/price, fees, gas, or failure/abort status. Failed txs are mapped too.
- G-05 **Point-in-time filter** [RULE-DERIVED: F-20, F-63]. Reject inputs with `source_ts` or `fetched_ts` later than decision time, or from sources not in the register. NTP offset checked every [5] min; if |offset| > [500 ms], no new orders.
- G-06 **Full model I/O capture** [RULE-DERIVED: F-49, F-62]. Log every raw request/response, including reasoning summaries, `reasoning_content`, encrypted signatures / `encrypted_content`, tool calls and results; credentials redacted. For Anthropic models set `display` explicitly (E-30). Never log keys, seeds, API secrets [RULE: F-62].
- G-07 **Honest logging** [RULE: F-62 — daily upload to write-once storage, upload after any material incident, no end-of-event backfilling, buffer locally during outages and upload within the published grace window] [PRACTICE: append-only journal, monotonic sequence numbers, hash chain, chain head in each upload]. Anchoring the chain head more often than daily (e.g., hourly) is [POLICY] (I-30).
- G-08 **No human trading or wallet interaction** [RULE: F-60 no manual trading; F-48 no manual intervention] [RULE-DERIVED pending Q-09: HALT as the only human action]. Humans can only trigger `HALT` (a versioned code path, logged as a decision and an incident). An operator-triggered "flatten" is not used unless organisers confirm it is not manual intervention (Q-09).
- G-09 **Key and environment separation** [PRACTICE supporting F-12, F-14]. Dev and final keys on separate hosts/accounts; final key generated at final activation; config refuses to start if wallet address ≠ expected for the environment.
- G-10 **Clean information** [RULE: F-63]. No Binance-internal, non-public, other teams' private, or unlicensed data. [POLICY] no copying other finalists' on-chain trades; no human-authored market views in agent context during the scored run.
- G-11 **Enforce what is declared** [RULE-DERIVED: F-48, F-66]. Every limit in the current proposal/manifest is enforced by the risk governor. Changes go through a version event [RULE: F-60]; a logged reason for each change [POLICY]; limits are not loosened in response to a drawdown [POLICY]. Swapping a principal model/data service declared at onboarding (F-12) = version event + re-declaration request before it trades [RULE-DERIVED, Q-22].
- G-12 **Pinning** [RULE-DERIVED: F-61]. Model snapshot IDs, checkpoint hashes and dependency lockfiles pinned; changing any requires a version event.
- G-13 **Token hygiene** [RULE-DERIVED: F-64, F-48]. Never send, approve or swap tokens outside {eligible bStocks, quote asset}; swaps into the gas asset only if Q-08 is answered yes. Log unsolicited inbound tokens and balance-only changes (I-28); never interact with them.
- G-14 **Safe-mode build** [PRACTICE supporting F-61]. Register a hold/exit-only build before Oct 29 for when a normal deploy is impossible (I-33).
- G-15 **No manipulation** [POLICY + applicable market-abuse law; supports F-48 "no material misrepresentation". Note F-72 is an eligibility clause about people with past sanctions, not a conduct rule]. No order placed in order to move a price; [POLICY] in the final [H] h, no order larger than [p]% of visible depth.
- G-18 **Fencing and idempotency** [PRACTICE, MUST if any standby exists; I-64]. Each leader holds a monotonically increasing epoch; the signer rejects requests with an epoch below the highest it has seen; the signer keeps its own unique constraint on `decision_id` and signs at most once per ID. Recovery checks observable keys (wallet nonce, quote ID, RFQ order hash, API order status), never the decision ID alone. Retry only after the quote has expired and the order is confirmed unfilled. Test: kill the DB connection between sign and broadcast → exactly one fill.
- G-16 **Open orders at version switch** [PRACTICE]. Cancel open/resting orders at every switch, or record which version owns them.
- G-17 **Jurisdiction** [RULE: F-70 legal compliance; F-71 identity verification] [RULE-DERIVED: Web3 API terms, E-14 "IP checks"]. Operate only as permitted; never use VPNs/relays to bypass geo-restrictions.

### 7.2 Risk policy (SHOULD) — all [POLICY]; LARP draft values in parentheses (T-14)
- G-20 **Default action is HOLD** when evidence, calibration margin or freshness is insufficient (T-11, T-12).
- G-21 **Caps:** open positions ≤ [4]; per-name ≤ [20]% of equity; gross ≤ [80]%, cash ≥ [20]%; daily one-sided turnover ≤ [T]%; orders/day ≤ [O].
- G-22 **Loss controls:** daily loss ≥ [3]% → no new risk; drawdown ≥ [8]% from peak → no new risk (exits allowed). Optional deeper step (I-62): at ≥ [Y]% drawdown, reduce gross to [g]% automatically. "Daily" boundary = [00:00 UTC]; loss measured against equity at that instant using executable quotes (G-30). Equity sampling frequency: [every N min] (Q-11 is about the official tie-break, not our control). Gap moves can breach limits between samples (I-62).
- G-23 **Event policy:** for each scheduled event and each held name, decide in advance (hold / reduce / flatten) and log it.
- G-24 **End-of-window:** from T_end − [H] h, no new positions; target book at valuation pre-committed once Q-04/Q-06 are answered.
- G-25 **Liquidity/cost:** estimated one-way cost (spread + impact + fees + gas, from the live quote) ≤ [50] bp, so round trip ≤ [100] bp. Entry requires P(UP) ≥ [θ] and P(UP) − P(DOWN) ≥ [m], with θ and m set on validation data so that the historical mean return of selected cases exceeded round-trip cost + [50] bp. This is a *validation-period estimate*, recorded as such in each decision record (`edge_est_source: validation_vX`), not a forecast of live edge. Order ≤ [p]% of quoted depth; abort if quoted slippage > [s_max] bp.
- G-26 **Staleness:** data or model output older than [N] s at quote time → refresh or abort; re-quote if a quote is older than [q] s.
- G-27 **Degraded mode:** API failure, model timeout, schema failure, reconciliation mismatch → no new risk, keep logging, retry with backoff; resume only after reconciliation passes. A timeout means "no trade", never "trade anyway".
- G-28 **Gas floor:** keep ≥ [k] × estimated exit gas × open positions + [buffer] in the gas asset (pending Q-03/Q-08).
- G-29 **Sizing:** size = (risk budget [1]% of equity) / (risk measure), where the risk measure is defined as [e.g., 2 × σ over the expected holding horizon] (I-61), reduced for liquidity; then apply G-21 caps. Replaces v0.2's fractional-Kelly rule.
- G-30 **Market-state awareness:** record US market state and route (swap/RFQ) before each order; off-hours marks use executable quotes, not `referencePrice` (E-13).

### 7.3 Reasoning behaviour (SHOULD) — [POLICY] unless noted
- G-31 Thesis schema: catalyst, evidence IDs with timestamps, falsifier, horizon, classifier probability vector, size rationale (G-51).
- G-32 Verifier: deterministic rule checks + tool-grounded claim checks (G-53); veto/shrink only.
- G-33 Uncertainty about evidence → abstain; uncertainty about direction → handled by calibration and sizing.
- G-34 No hallucinated numbers: models output structured assessments/probabilities only; code computes quantities, rounding, fees and gas; schema failure → retry ≤ [2] → HOLD.
- G-35 Audited memory: every memory write has source and timestamp; memory never carries future information into past-dated contexts in evaluation.
- G-36 Cadence: a few scheduled cycles per day plus event triggers; no minute-level loops.
- G-37 Shallow graph: ≤ [4] model roles; inter-agent messages logged.
- G-38 Each cycle logs HOLD for every held name and every candidate considered, with `hold_reason ∈ {NO_SIGNAL, ABSTAIN, FLAT, RISK_VETO, COST_VETO, EVIDENCE_UNVERIFIED, DEGRADED, HALT}`, in the same hash chain; DEGRADED/HALT holds also create incidents. (F-34 requires records only for trades; HOLD records are [POLICY] and show inactivity is a decision.)
- G-39 Evaluation hygiene: anonymise ticker/company/date in evidence prompts during development evaluation; report pre- vs post-cutoff results separately (I-37).

### 7.4 Team and process (MUST unless noted)
- G-40 Protected challenge branch; no force-push or rebase [RULE: F-61]; signed commits [PRACTICE, SHOULD]; confirm branch protection works on the private-repo plan before Oct 5.
- G-41 Secrets in a secret manager; pre-commit secret scanning [RULE: F-61 "Never commit secrets"].
- G-42 Data/model register with licences, declared at onboarding [RULE: F-71, F-12].
- G-43 Reconciliation hourly [POLICY] and daily full [RULE-DERIVED: F-47, F-48]: on-chain txs ↔ execution records ↔ decision records ↔ version events ↔ non-trade balance events; any mismatch → degraded mode.
- G-44 Incident list (over-report) [RULE-DERIVED: F-62]: outage, restart, failed tx, reconciliation mismatch, missed heartbeat > [N] min, disk > [80]%, NTP breach, human HALT, unexpected inbound token, leader-lock loss.
- G-45 Dev reliability test [PRACTICE]: replay identical inputs k times; measure decision agreement, hallucinated-number rate, schema-error rate; include in the week-one progress note.
- G-46 Release cadence during the run [POLICY — the rules allow improvement at any time via versions, F-60]: v1.0 frozen at activation; planned releases ≤ [1 per day] with ≥ [12] h shadow; P0 fixes any time via the normal gate; no re-fitting to scored-run P&L. Counterpoint: F-08 asks whether a team can "build, operate and improve", so over-freezing can read as not improving — improve on non-P&L evidence (schema errors, latency, calibration drift, incidents) and state the reason in each release.
- G-47 Storage [PRACTICE]: disk alerts, off-box journal backups, retention through at least Nov 20 and any later technical review (Q-28). Self-hosted model weights (classifier, FinBERT, regime model) archived with hashes for the F-49c handover, after confirming redistribution rights (Q-30).

---

## 8. REFERENCE ARCHITECTURE (LARP + harness additions)

```
[Connectors] → point-in-time store (event_ts, retrieved_ts, source_uri, sha256)
   ↓ scheduled / planner (G-52)            ↓ event-triggered
[Local scoring: FinBERT relevance/sentiment; regime classifier]
   ↓
[Evidence LLM + bounded tool loop (G-50)] ←→ [Thesis memory (G-51)]
   ↓ structured assessment (no actions)
[Claim verification (G-53)] — removes unsupported claims
   ↓
[Calibrated classifier: UP / FLAT / DOWN / ABSTAIN]
   ↓
[Deterministic policy] → [Risk governor (G-20..G-30)]
   ↓ approved intent
[Version gate (G-03)] → [Write-ahead decision record (G-04)] → [Signer service (G-01)] → Web3 API
   ↓ tx / order hash / fill
[Hash-chained journal → daily write-once bundle (G-07)]  [Reconciler (G-43)]  [Heartbeat/alerts]  [Recovery]
```
Recovery: replay the journal; find intents with no tx (write-ahead); query the chain before any retry; idempotent by decision ID; resume only after reconciliation passes.

---

## 9. OPERATING PLAN (aligned to the official timeline; fixes I-58)

| Dates (2026) | Work | Exit criteria |
|---|---|---|
| Sep 29 (SGT) | Finalise and submit proposal: scope per §6.1, harness additions §6.2, hypotheses §5, risk-budget definition (I-61), drawdown behaviour (I-62), corrected delivery plan, rewrite T-20 wording. | Submitted; copy archived. |
| Sep 30 – Oct 4 | Skeleton: typed contracts, mock adapters, risk engine, hash-chained trace sink, CI (T-19). Start post-cutoff evaluation set (I-37). | Tests green. |
| Oct 2 | Finalists announced. | — |
| Oct 5–10 | Onboarding: identity verification, dev wallet, Developer Portal, repo with audit access, declarations. Read Audit Log Spec, scoring rules, incident policy; send Q list. | All submissions made. |
| Oct 12–18 (dev wk 1) | Minimal real adapter; one minimum-size real buy and sell on the dev wallet; reconcile; heartbeat and uploader live; start H-01 quote logging. | Week-one checkpoint commit + progress note; zero unmapped items. |
| Oct 19–26 (dev wk 2) | Full pipeline ≥5 days incl. weekend Oct 24–25, signer ON at minimum size for ≥[2] days and shadow otherwise (so the first full-pipeline real trade is not on the scored wallet); gate fallbacks decided by Oct 26 (I-65); recovery drills; soak and fault injection; fit cost model; H-01/H-02 readouts. | End-to-end self-check evidence. |
| Oct 27–29 | Fresh final wallet (key generated then); freeze v1.0; register safe-mode build; pre-commit FOMC/day-1 posture; integrity check. | v1.0 manifest submitted. |
| Oct 29 – Nov 12 | Scored run under G-46; daily uploads and reconciliation; on-call rota. | No version gaps; no unmapped items. |
| Nov 13 | Stop; export logs; final reconciliation. | Audit bundle ready. |
| Nov 16–20 (+ possible technical review, Q-28) | Audit hand-over. | Pass. |

Dev-wallet budget (F-65): ≤ ~30% for plumbing tests, ~20% for the dress rehearsal, rest held back. Test matrix: approve (if allowed), buy, sell, slippage-abort, stale-quote reject, crash-recovery ×2, gas-floor block, allow-list rejection (dry-run), version-gate refusal, uploader outage → catch-up.

---

## 10. PROPOSAL GUIDANCE (map to the form's sections, T-02)

Rules for the text: one central capability (I-55); hypotheses, not claims (I-56); no tournament talk (Appendix A); no SECONDARY/DEV-REPORT statistics; no numbers you will not enforce; brand names only where needed to explain capture of model I/O.

| Form section | Say | Avoid |
|---|---|---|
| Your Proposal | "LARP turns verified, timestamped catalysts into probability-scored, abstaining long/hold/exit decisions; whether off-hours quotes lag verified news is a hypothesis we test and use only as an execution guard unless it passes." Supporting controls in one line each. | Three co-equal innovations; "core insight … different clocks"; "information edge"; "we exploit off-hours mispricing" (T-20). |
| Architecture (PDF) | §8 diagram incl. tool loop, memory, planner, claim verification. | A pipeline with no agentic loop. |
| Data / tools used | Sources with licences; point-in-time stamping; organiser data authoritative. | Grey-area scraping. |
| Position & risk | T-14 values, one-way vs round-trip cost (G-25), the risk-budget definition (I-61), drawdown behaviour (I-62), "values are versioned configuration enforced in code" (I-35). | Kelly; "kill switch" if it only halts new risk; limits you won't enforce. |
| Leakage / overfitting | T-15 plus LLM memorisation controls (I-37: post-cutoff evaluation, anonymisation). | Claiming walk-forward alone solves LLM leakage. |
| Reproducibility | T-16; hash chain = tamper-evidence after anchoring, completeness via reconciliation and sequence numbers (I-30); thinking-output plan (I-29); target definition (I-63); gates with fallbacks (I-65). | "Proves completeness"; "organizer-approved model". |
| Team capability + scope | Named owners, concrete evidence; corrected timeline (§9). | Dates that don't match the official timeline. |

---

## 11. OPEN QUESTIONS (ranked)

Working assumption in brackets; **UNRESOLVED** = no safe assumption, design must work either way.
1. Q-26 Is a KYC-verified Binance (exchange) account required, and can Singapore-based participants obtain/use one for this challenge? (T-03) [UNRESOLVED]
2. Q-12 Can Singapore-based participants use the Web3 API/Developer Portal and trade bStocks, and host in Singapore? (E-14, E-15) [UNRESOLVED; never bypass]
3. Q-03 Opening asset(s); is BNB for gas provided; does BNB count in equity? [UNRESOLVED]
4. Q-08 May the agent swap into BNB for gas? [Assume no until confirmed.]
5. Q-04 What is the valuation source and valuation instant? [UNRESOLVED]
6. Q-06 Exact start/end timestamps of the scored run. [UNRESOLVED — the stated dates span 15 calendar days vs "14 days" (I-08).]
7. Q-16 What satisfies the "thinking output" deliverable: vendor summaries? classifier probabilities plus structured assessments? raw CoT only? [UNRESOLVED]
8. Q-07 Is an ERC-20 `approve` to the API-returned router allowed? [Assume yes, capped to order size.]
9. Q-10 Mapping granularity: one decision → several orders? one order → several txs (partial fills, RFQ settlement, failed txs)? [Map everything, both directions.]
10. Q-09 Does a human HALT/restart count as manual intervention? May an operator trigger an agent-coded flatten? [Halt OK if logged; no flatten.]
11. Q-17 Minimum-activity requirement; are zero/low-activity teams ranked? [UNRESOLVED]
12. Q-19 Eligible instrument list; leveraged ETF tokens; frozen during the run; valuation if an instrument becomes ineligible? [Exclude leveraged tokens.]
13. Q-20 Treatment of dividend Multiplier, splits, unsolicited tokens and the funding transfer for equity and "unexplained transfers". [Log all; never touch unsolicited tokens.]
14. Q-29 What off-hours liquidity (spreads/depth, RFQ availability) will the challenge path expose? (H-01)
15. Q-27 Is the "Laya" checkpoint (or any self-hosted model) acceptable, and what licence evidence is needed? (I-38)
15b. Q-30 (internal, for the team) Laya: licence, training-data cutoff, architecture, redistribution rights under F-49c. [UNRESOLVED; do not declare it at onboarding until answered.]
16. Q-11 Equity sampling frequency for the max-drawdown tie-break.
17. Q-13 Do prompt/config-only changes require a full version event? [Yes.]
18. Q-14 Grace window for delayed trace uploads. [UNRESOLVED]
19. Q-21 Are weekly diagnostics published during the run?
20. Q-22 Can declared principal model/data services change mid-run via a version event? [Re-declare.]
21. Q-23 Does "invalidate affected trades" reverse their equity effect?
22. Q-15 Does dev-phase funding equal the scored-run opening value?
23. Q-28 What is the late-Nov/early-Dec "virtual technical review" (T-03), and is it part of the audit?
24. Q-01 Proposal deadline time/timezone on Sep 30. [Submit by Sep 29 SGT.]
25. Q-02 Prize split; what "prize assets" are.
26. Q-18 Is a DoraHacks BUIDL submission required by "2026/11/13 22:59"; which timezone?
27. Q-24 Sharing/confidentiality terms for winner deliverables.
28. Q-25 Does "non-public information about … the instruments involved" exclude employees of issuers of eligible bStocks?


---

## 12. LITERATURE (L)

Grades as in §0.1. [PRIMARY] here means the paper itself was checked at abstract/HTML level (2026-09-27/29) unless noted.

### 12.1 LLM trading agents (architectures; backtest-only evidence)
- L-01 FinMem (Yu et al., 2023, arXiv:2311.13743) — layered memory. Backtest only. [PRIMARY, existence]
- L-02 FinAgent (Zhang et al., KDD 2024, arXiv:2402.18485) — multimodal, dual-level reflection. Backtest only. [PRIMARY, existence]
- L-03 FinCon (Yu et al., NeurIPS 2024, arXiv:2407.06567) — manager–analyst hierarchy, self-critique as risk control. Backtest only. [PRIMARY, existence]
- L-04 TradingAgents (Xiao et al., 2024, arXiv:2412.20138) — Sharpe 8.21 (AAPL), 6.39 (GOOGL), 5.60 (AMZN) over Jan 1–Mar 29, 2024; the authors note the high Sharpe came from a period with few pullbacks; costs not mentioned. [PRIMARY]
- L-05 Trading-R1 (arXiv:2509.11420) — SFT + RL curriculum; backtest only. [PRIMARY, abstract]
- L-06 Survey (Xia et al., 2026, arXiv:2605.19337) — of a 19-study primary empirical subset, only 2 report extractable time-consistent split protocols and 1 an explicit transaction-cost model; none reaches the top reproducibility tier. [PRIMARY]
- L-07 Li et al. (EMNLP 2023 Industry, arXiv:2305.05862) — GPT-4 "can outperform" domain-pretrained and fine-tuned models "on many tasks"; fine-tuned models still lead on structured prediction. [PRIMARY]
- So what: borrow structure (roles, memory, reflection); do not cite their returns.

### 12.2 Live / forward evaluations
- L-10 nof1 Alpha Arena Season 1 (Oct 18 – Nov 3, 2025; $10k each; crypto perps): final balances $12,231 / $10,489 / $5,799 / $5,445 / $4,208 / $4,126 (Qwen3-Max, DeepSeek-V3.1, Claude Sonnet 4.5, Gemini 2.5 Pro, Grok 4, GPT-5). [SECONDARY: ForkLog; nof1.ai blocked] Behavioural details [UNCONFIRMED].
- L-11 Alpha Arena Season 1.5 (~Nov 19 – Dec 3, 2025; US stock tokens on Hyperliquid; reported tickers incl. TSLA, NVDA, MSFT, AMZN, Nasdaq-100): Grok 4.20 "up 12% on avg" across four modes. [SECONDARY]
- L-12 LiveTradeBench (arXiv:2511.03628) — 21 LLMs, 50 days live; "high LMArena scores do not imply superior trading outcomes"; performance on one market "does not generalize to another". [PRIMARY]
- L-13 Agent Market Arena (arXiv:2510.11695) — "model backbones contribute less to outcome variation" than agent frameworks. [PRIMARY]
- L-14 StockBench (arXiv:2510.02209) — "most models struggle to outperform the simple buy-and-hold baseline"; "all LLM agents underperform the passive baseline during the downturn"; thinking models make fewer arithmetic but more schema errors. [PRIMARY]
- L-15 DeepFund (arXiv:2505.11065) — DeepSeek-V3 and Claude-3.7-Sonnet "incur net trading losses". [PRIMARY]
- L-16 AI-Trader (arXiv:2512.10971) — "risk control capability determines cross-market robustness". KTD-Fin (arXiv:2605.28359, CSI300) — returns "largely explained by passive market and style exposure". [PRIMARY]
- L-17 FinSearchComp (Hu et al., arXiv:2509.13160) — search/finance tools "substantially" improve time-sensitive retrieval. [PRIMARY]
- So what: base rate is losing money or matching beta; harness matters more than backbone; deterministic quantities/schemas are mandatory. These support design choices; they are not claims about LARP's results.

### 12.3 Look-ahead bias and leakage
- L-20 Profit Mirage (arXiv:2510.07920) — backtest gains fade after the model's knowledge window. [PRIMARY]
- L-21 Glasserman & Lin (arXiv:2309.17322) — anonymised headlines outperform; "distraction effect". [PRIMARY]
- L-22 Lopez-Lira & Tang (arXiv:2304.07619) — headline predictability "especially for small stocks and negative news"; "strategy returns decline as LLM adoption rises". [PRIMARY]
- L-23 Lopez-Lira, Tang & Zhu (arXiv:2504.14765) — LLMs memorise past market values. [PRIMARY]
- L-24 Gao, Jiang & Yan, "Detecting Lookahead Bias in LLM Forecasts" (arXiv:2512.23847); Benhenda, Look-Ahead-Bench (arXiv:2601.13770). [PRIMARY]

### 12.4 Short-horizon predictability and costs
- L-30 Tetlock (2007, J. Finance) — media pessimism → temporary pressure then reversal. [PRIMARY, standard]
- L-31 Chan (2003, JFE) — drift after news, reversal after no-news moves, mainly small stocks; Chen, Kelly & Xiu (SSRN 4416687) — LLM news embeddings predict returns across markets. [PRIMARY, not re-checked]
- L-32 Martineau (CFR 2022) — PEAD largely gone in large caps; Barber et al. (2013, JFE) — earnings-announcement premium; Lou, Polk & Skouras (2019, JFE) — overnight vs intraday returns differ. [PRIMARY, not re-checked]
- L-34 Novy-Marx & Velikov (2016, RFS) — high-turnover strategies rarely survive costs; a buy/hold spread is an effective mitigation. [PRIMARY, not re-checked]

### 12.5 Tournament incentives (used only in Appendix A)
- L-40 Brown, Harlow & Starks (1996) — mid-year losers raise risk; Busse (2001) — effect weakens with daily data. [PRIMARY, standard]
- L-41 Gaba, Tsetlin & Winkler (INSEAD WP 2003/27) — with proportion of winners p < 0.5, choose riskier distributions and lower correlation; at p = 0.1 and zero correlation, doubling σ raises P(win) about 2.7×. [PRIMARY]
- L-42 Seel & Strack (2013, JET) — winner-take-all contestants gamble. [PRIMARY, standard]
- L-43 Fang et al., "Winning ways" (SSRN 4856341) — convex prizes favour positive skew; equilibrium bounded. [PRIMARY, existence only]

### 12.6 Risk management
- L-31b Harvey et al. (2018, JPM) — volatility targeting improves equity Sharpe and trims tails; gains fragile out of sample (Cederburg et al., 2020). [PRIMARY, not re-checked]
- L-33 Kaminski & Lo (2014) — stop-losses add value only under momentum/regime-switching; Lo & Remorov (2017) — tight stops lose to costs. [PRIMARY, not re-checked]
- L-35 Grossman & Zhou (1993) — drawdown-constrained exposure ∝ equity − floor. [PRIMARY, standard]
- L-36 MacLean, Thorp & Ziemba (2010) — fractional Kelly and estimation error. [PRIMARY, standard] Not adopted (P-07).

### 12.7 Agent reliability
- L-50 Huang et al. (ICLR 2024, arXiv:2310.01798) — no reliable self-correction without external feedback. [PRIMARY]
- L-51 Self-consistency (Wang et al., ICLR 2023). [PRIMARY, standard]
- L-52 MAST (arXiv:2503.13657) — 14 multi-agent failure modes; τ-bench (arXiv:2406.12045) — pass^8 < 25% in retail. [PRIMARY]
- L-53 Chen et al. (Anthropic, arXiv:2505.05410) — reasoning models reveal hint use often below 20% of the time. [PRIMARY]
- L-54 LoRA; DPO. No live evidence found that fine-tuned/RL traders beat a well-harnessed frontier model. [PRIMARY, standard]

---

## APPENDIX A — STRATEGY OPINIONS (S). Not evidence of proposal quality; keep out of the proposal.

These concern how to *place* in a raw-return contest. They do not bear on the Stage 1 rubric. Revisit before final activation, once the opening asset, valuation and instrument list are known.

- **S-01 (was I-02) The prize structure rewards variance.** Top 3 of ≤25 paid (F-02, F-04), raw return (F-43), no own capital at risk (F-25). Theory (L-41, L-42, L-43): with p ≈ 0.12, bounded, positively skewed, low-correlation risk raises P(top 3). Counterpoints: no live leaderboard (F-19) prevents rank-conditioning; weekly diagnostics may act as a delayed one (F-51, Q-21); Busse (L-40) finds tournament effects weaker in daily data; the Seeds recruitment prize rewards a sound system regardless of rank (E-20); a large variance increase contradicts a conservative declared design (I-35). Example [ESTIMATE, our Monte Carlo]: 25 teams with zero-mean normal returns and pairwise correlation 0, 0.5 or 0.8; one team scales its whole return by 2 (e.g., doubles exposure). Its P(top 3) rises from ≈12% to ≈27%, 29% and 33% respectively. Caveats: assumes zero expected return for everyone and ignores costs; the same scaling doubles the chance of finishing near the bottom; with a negative expected edge after costs the gain shrinks.
- **S-02 (was I-10) Crowding.** Up to 25 agents may trade the same thin pools and names, compounding slippage near events. Counterpoint: size of the effect unknown; spreads may be deep enough for small wallets.
- **S-03 (was I-11) Tie-breaks rarely matter** except among near-flat teams; don't give up expected return merely to protect drawdown. Counterpoint: if many teams stay flat in a falling market, drawdown decides among them (F-45).
- **S-04 (was P-02) Avoid the middle.** A diversified, always-invested book ranks near the pack. Counterpoint: "the middle" is also the most defensible posture for the audit and for recruitment.
- **S-05 (was P-03) Exposure before selection** over 14 days (see I-05).
- **S-06 (was P-04) Be different on purpose** (lower correlation to the field). Counterpoint: "different" without edge is just noise.
- **S-07 Where LARP sits.** LARP's draft (T-14, I-61) behaves like a hold-heavy book: it is likely to rank well if markets fall and poorly if they rise sharply. That is a legitimate choice (D-01); it should be made knowingly, not by accident.

---

## APPENDIX B — Known gaps and change log
- Not captured independently: the Google Form (fields taken from T-01..T-03); official onboarding documents (issued Oct 5–10); Web3 API rate limits; gas sponsorship; eligible instrument list; nof1 primary data.
- v0.1 (2026-09-27): primary source only.
- v0.2 (2026-09-27): red-team fact fixes; environment research; principles, guardrails, architecture, plan, open questions, literature.
- v0.3 (2026-09-29): applied external reviewer feedback — (1) scope reduced to one central capability (§6.1, I-55); (2) off-hours pricing reframed as hypothesis H-01 with a test and kill criterion; (3) guardrails tagged RULE / RULE-DERIVED / POLICY / PRACTICE, and I-35/I-52 rewritten: no rule freezes proposal parameters, consistency with declarations is what matters; (4) evidence re-graded after a source audit (E-04, E-06 285 bp misattribution, E-07 attribution, L-06, L-17, L-24 corrected); (5) Kelly sizing replaced with bounded volatility-scaled sizing (G-29, P-07); (6) I-30 hash-chain claim limited to tamper-evidence after anchoring; I-29 corrected (DeepSeek hosted API returns reasoning); Q-06 left unresolved rather than assumed; (7) tournament material moved to Appendix A. Added team facts from the LARP drafts (T-xx), LARP-specific inferences (I-37, I-38, I-50, I-58, I-59, I-61, I-62), harness additions (G-50..G-54), hypotheses (H-01..H-03), counterpoints and worked examples throughout.
- v0.3 adversarial pass (2026-09-29): added I-63 (target/label definition; ABSTAIN is a selection rule, not a class), I-64 + G-18 (hot-standby double execution, fencing), I-65 (gate fallbacks), I-66 (regime validation), T-20 (off-hours framing left in drafts), D-06; fixed RULE/POLICY tags on G-04, G-07, G-08, G-11, G-15, G-17; replaced G-25 edge wording with validation-period thresholds; operational H-01/H-02/H-03 criteria; corrected I-61/I-62 arithmetic and scope, I-09 FOMC timing (02:00 SGT), E-17 gas range; added storage-disabled reasoning implications (E-33), anchoring limits (I-30), anonymisation limits (I-37), Laya provenance (I-38, Q-30), build cut line (§6.2), signer-on dev run (§9).
- Next update: after finalists (Oct 2) and after onboarding documents (Oct 5–10) — answer Q-items, replace placeholders, re-verify every F-item against the official rules.
