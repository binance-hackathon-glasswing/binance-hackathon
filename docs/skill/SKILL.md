---
name: binance-agentic-ai-challenge
description: Core skill file for "Beyond the Benchmark: The Binance Agentic AI Challenge" (DoraHacks, Sep–Nov 2026) — official facts, hard guardrails, the never-do list and ranked open questions. Load it for any rule-compliance, design, risk, logging/versioning or planning question on this challenge, then load the reference/larp file the file index points to when you need E/I/L/T/H/P/D/S detail.
version: 0.5.4 (recommendations for D-03/D-07/D-08/D-09/Q-30, marked not decided; I-67)
revised: 2026-10-04 (SGT, UTC+8)
source_verification:
  - official DoraHacks page re-checked 2026-09-30 (body text, timeline image, banner) — unchanged since the 2026-09-27 capture
  - Laya model card (Hugging Face) checked 2026-09-30 — card text only (E-51)
  - other E/L items — as dated in their entries
  - Google application form — never captured (T-01..T-03 are team transcriptions)
primary_source: https://dorahacks.io/hackathon/binance/detail (verbatim capture in source_page.md)
reference_files:
  - reference/environment.md — E items (graded external evidence)
  - reference/inferences.md — challenge-general I items
  - reference/literature.md — L items
  - larp/plan.md — T, D, H, P items, LARP-specific I items, G-20..G-54, architecture, operating plan
  - larp/strategy-opinions.md — S items (keep out of the proposal)
  - ../LEDGER.md — index of ideas and experiments (IDEA-, EXP-); full records in ../ledger/<ID>.md
  - retired (git history, commit 2985af5): archive/proposal-phase.md (§10 proposal guidance, T-20, D-01, I-57) and archive/SKILL_v0.3.md
team_sources: larp/proposal.md, larp/application_answers.md, larp/deployment.md, larp/team_and_delivery.md (team drafts, not official; not stored in this Project)
---

# Binance Agentic AI Challenge — Skill File (core)

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
| `S-xx` STRATEGY OPINION | Contest-strategy views (tournament incentives etc.). Kept in Appendix A (now `larp/strategy-opinions.md`). | **Not evidence of proposal quality. Keep out of the proposal.** Revisit before final activation. |
| `L-xx` LITERATURE | Research evidence with citation and grade. | Justifies P/G items. |

**Status** (design commitments only; see the "v1.0 adopted scope" table in larp/plan.md): Proposed / Adopted / Implemented / Tested / Superseded. Status is separate from confidence: an Adopted design can rest on a Low-confidence inference.

### 0.2 Precedence and reviewer rules
- Precedence when items conflict: official onboarding rules > F > G[RULE] > E[PRIMARY] > G[RULE-DERIVED] > I > T > P/D/G[POLICY/PRACTICE] > H > S; L supports P/G and does not override F.
- **Official vs internal:** the official text requires very little about *how* to trade. Almost every numeric limit, cadence rule and sizing method in this file is a team POLICY. If anyone (human or LLM) cites a POLICY as "the rules say", correct it.
- E and L items carry source, access date and what was checked (existence / abstract / full text / docs / experiment); keep team-transcribed form fields (T) distinct from organiser text (F).
- **Reading budget:** load this file and `../LEDGER.md` (index only). Open a reference/larp file or `../ledger/<ID>.md` only when the task names those IDs or touches their topic. When an item is settled (Q answered, D decided, I superseded, experiment closed), collapse it to one line in the file that indexes it and move or drop the reasoning; git history keeps the full text.
- Reviewers: cite IDs. If you disagree with an inference, name the F/E item you read differently. If you add a claim, give it a label and a source.
- Nothing here is permission to evade a rule. Where a rule is ambiguous, the conservative reading applies until organisers answer.
- **Timezones:** the official page gives dates without timezones. Team is in Singapore (SGT = UTC+8). US Eastern is UTC−4 until Sun Nov 1, 2026, then UTC−5.

### 0.3 Never do
Each line summarises the cited items; the items govern.
1. Never trade manually. Humans never sign, approve or submit wallet transactions and never choose trades. Human actions on the agent are limited to HALT, restart/resume after reconciliation, and deploying a registered version through a version event — each logged as an incident or version event [RULE-DERIVED pending Q-09]; no operator flatten unless Q-09 confirms. (F-48, F-60, F-64, G-08)
2. Never let a trade or transaction exist without a mapping to one registered version and one unique write-ahead decision record — failed txs included. (F-34, F-48, F-60, F-66, G-04)
3. Never add own or external funds, withdraw, transfer wallet-to-wallet, bridge, or make unrelated swaps or arbitrary contract calls. (F-25, F-64, G-01, G-13)
4. Never use leverage, shorting, derivatives, or leveraged/inverse ETF tokens (unless explicitly eligible and confirmed). (F-64, G-02)
5. Never let anything trade unless its version is committed, pushed to the registered repo, manifested and logged in a version event, with a hash equal to the active manifest. (F-60, F-61, G-03, G-12)
6. Never force-push, rebase or rewrite the challenge branch; fix mistakes with a new commit. GitHub does not enforce this on our plan (no branch protection, checked 2026-10-03), so the rule itself is the guard. (F-61, G-40)
7. Never put secrets, keys or credentials in the repo or in logs, or private training/label data in the repo [RULE: F-61]. (F-61, F-62, G-06, G-41)
8. Never use future, non-public, Binance-internal, other teams' private or unlicensed data. (F-63, F-71, G-05, G-10, G-42)
9. Never backfill or rewrite logs; upload daily to write-once storage and buffer locally during outages. (F-62, G-07)
10. Never use a VPN or relay to get around geo-restrictions or IP checks. (F-70, F-71, G-17)
11. Never call a POLICY a rule: only items tagged [RULE: F-xx] are required by the official text. (§0.1, §0.2; tags in §7)

### 0.4 Current phase (as of 2026-10-03)
- The proposal was submitted by Sep 30 (F-10), and the team was selected as a finalist on Oct 2 (F-11) [team statement]. What was submitted is in `../proposal/` (answers + architecture PDF); proposal-phase guidance is retired to git history.
- Onboarding is Oct 5–10 (F-12), when the Participant Guide, Web3 Open API documentation, Audit Log Specification, scoring rules and incident policy arrive (F-18); then run the re-verification checklist at the end of this file.
- **Priority by deadline:** before Oct 12 = team actions: define the decision target/horizon and the rest of D-06; implement G-18; classify onboarding gates (I-65); by Oct 19 define baseline V0 (D-07) and the inconclusive default (D-08). After onboarding = the re-verification checklist at the end of this file.
- After that: development Oct 12–26 (F-13); final activation Oct 27–29 (F-14); scored run Oct 29 – Nov 12 (F-15); provisional ranking Nov 13 (F-16); winner audit Nov 16–20 (F-17). Team plan: `larp/plan.md` §9.

---

## 1. FACTS — official page (F)

### 1.1 Identity and logistics
- F-01 Name: "Beyond the Benchmark: The Binance Agentic AI Challenge". Hosted by Binance on DoraHacks. Format: Online / Virtual. "Binance sets the rules and verifies the record."
- F-02 Prize: "6,000 USD in prize assets across the top 3 teams, plus Binance Seeds Program internship and full-time employment opportunities". The split among the three is not stated.
- F-03 Team size 1–4 people; "you may join only 1 team".
- F-04 Finalists: "<25 teams selected from open applications" (Overview and Stage 1). The timeline image says "25 teams selected". (Minor inconsistency.)
- F-05 Duration: "4 weeks of active work (2-week build + 2-week scored run); ~7 weeks end-to-end including onboarding and audit".
- F-06 Tags: AI Agent, Live Trading, Trading Strategies, Real World Assets, Onchain Finance. Listed tech: OpenAI, Anthropic, Llama, LangChain, Python, Binance.
- F-07 DoraHacks sidebar: "Submission 2026/09/07 00:00", "Deadline 2026/11/13 22:59". No timezone shown. DoraHacks renders these in the viewer's local time. The site's API (`/api/v1/hub/hackathons/binance`; platform API, see E-52) gives timeline_start 1788710400 = Sep 7 00:00 UTC+8 (Sep 6 16:00 UTC) and timeline_end 1794581940 = Nov 13 22:59 UTC+8 (Nov 13 14:59 UTC). The organiser set times on UTC+8 boundaries. (What this deadline governs is an inference: I-60.)
- F-08 Framing: "The question we're asking: can a team build, operate and improve an autonomous Agentic AI system that runs end-to-end in a real-time environment — and produce a decision trail that proves how it got there?" Also: "The best system wins."

### 1.2 Timeline (timeline image on the page; year 2026)
- F-09 Banner image: "Applications: Sept 9 - 30, 2026" and "Oct 12 - Nov 12, 2026".

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
- F-42 Stage 2: "Every eligible team starts from the same opening value, so scores compare directly." "Calculated from your registered wallet's on-chain state and bStocks execution records, using the published valuation source." (The Judging & Scoring section opens: "Two separate evaluations. Proposals are judged by people. The ranking is not.")
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

### 1.8 Page state
- F-80 Snapshots of the DoraHacks page. **2026-09-27:** 75 hackers registered; announcements empty; Q&A: one post (asking for a "password"), no replies; no organiser answers. **2026-09-30:** 86 registered; announcements still empty; the Q&A "password" post now has 1 reply from another participant ("hacker_18") saying ideas go through the Google form; still no organiser answers. (Platform-API details: E-52.)

---

## 7. GUARDRAILS (G)

Tags: **[RULE: F-xx]** required by official text · **[RULE-DERIVED]** our conservative implementation of a rule whose exact reading is open · **[POLICY]** team choice · **[PRACTICE]** engineering hygiene. MUST = enforced in code and tested; SHOULD = default.

### 7.1 Hard constraints (MUST)
- G-01 **Signer allow-list** [RULE-DERIVED: F-64]. Allowed: `to` ∈ `ALLOWED_CONTRACTS` (router/settlement contracts from the Web3 API or organiser allowlist) with selector / EIP-712 type in `ALLOWED_SELECTORS`; or, for ERC-20 `approve` only, `to` ∈ {eligible bStock and quote-asset token contracts} with spender ∈ `ALLOWED_CONTRACTS` and amount ≤ the order amount. Reject everything else. No transfers, bridging, withdrawals, deposits, lending, LP, or permit signatures outside the API flow. Test: signing any other call fails. (LARP: T-18 signer service.)
- G-02 **Long-only spot** [RULE: F-64]. Quantity ≥ 0; no leverage, shorting, derivatives. Leveraged/inverse ETF tokens excluded unless explicitly eligible and confirmed [RULE-DERIVED, I-41].
- G-03 **Version gate** [RULE-DERIVED: F-60, F-61]. Before each order: hash of (commit SHA, lockfile, prompts, tool schemas, configs, risk params, thresholds, model checkpoint hashes/snapshot IDs) equals the manifest of the active version event; working tree clean; commit present on the registered remote. Any failure → no order. Every deployable (agent, signer, uploader, tool/feature services, reconciler) refuses to start unless its commit is on the registered remote and in the active manifest; the manifest also declares third-party services (F-61).
- G-04 **Decision record per order, write-ahead** [RULE: F-34 — one unique record with a concise reason per scored trade] [POLICY: per-order granularity, write-ahead, field list, ≤3-sentence summary]. Minimum fields: `decision_id`, `version_id`, `ts_decision_utc_ms`, input hashes + pointers with `source_ts` and `fetched_ts`, model call IDs, evidence assessment, probability vector, policy result, risk-check results, reason summary (≤3 sentences, generated from the structured fields actually used), intended order, quote ID, route (swap/RFQ), market state (open/extended/closed). Appended after execution: tx hash(es), order hash, fill qty/price, fees, gas, or failure/abort status. Failed txs are mapped too.
- G-05 **Point-in-time filter** [RULE-DERIVED: F-20, F-63]. Reject inputs with `source_ts` or `fetched_ts` later than decision time, or from sources not in the register. NTP offset checked every [5] min; if |offset| > [500 ms], no new orders.
- G-06 **Full model I/O capture** [RULE-DERIVED: F-49, F-62]. Log every raw request/response, including reasoning summaries, `reasoning_content`, encrypted signatures / `encrypted_content`, tool calls and results; credentials redacted. For Anthropic models set `display` explicitly (E-30). Never log keys, seeds, API secrets [RULE: F-62].
- G-07 **Honest logging** [RULE: F-62 — daily upload to write-once storage, upload after any material incident, no end-of-event backfilling, buffer locally during outages and upload within the published grace window] [PRACTICE: append-only journal, monotonic sequence numbers, hash chain, chain head in each upload]. Anchoring the chain head more often than daily (e.g., hourly) is [POLICY] (I-30).
- G-08 **No human trading or wallet interaction** [RULE: F-60 no manual trading; F-48 no manual intervention] Humans never sign, approve or submit wallet transactions and never choose trades. Human actions on the agent are limited to `HALT` (a versioned code path, logged as a decision and an incident), restart/resume after reconciliation, and deploying a registered version through a version event — each logged as an incident or version event [RULE-DERIVED pending Q-09]. An operator-triggered "flatten" is not used unless organisers confirm it is not manual intervention (Q-09).
- G-09 **Key and environment separation** [PRACTICE supporting F-12, F-14]. Dev and final keys on separate hosts/accounts; final key generated at final activation; config refuses to start if wallet address ≠ expected for the environment.
- G-10 **Clean information** [RULE: F-63]. No Binance-internal, non-public, other teams' private, or unlicensed data. [POLICY] no copying other finalists' on-chain trades; no human-authored market views in agent context during the scored run.
- G-11 **Enforce what is declared** [RULE-DERIVED: F-48, F-66]. Every limit in the current proposal/manifest is enforced by the risk governor. Changes go through a version event [RULE: F-60]; a logged reason for each change [POLICY]; limits are not loosened in response to a drawdown [POLICY]. Swapping a principal model/data service declared at onboarding (F-12) = version event + re-declaration request before it trades [RULE-DERIVED, Q-22].
- G-12 **Pinning** [RULE-DERIVED: F-61]. Model snapshot IDs, checkpoint hashes and dependency lockfiles pinned; changing any requires a version event.
- G-13 **Token hygiene** [RULE-DERIVED: F-64, F-48]. Never send, approve or swap tokens outside {eligible bStocks, quote asset}; swaps into the gas asset only if Q-08 is answered yes. Log unsolicited inbound tokens and balance-only changes (I-28); never interact with them.
- G-14 **Safe-mode build** [PRACTICE supporting F-61]. Register a hold/exit-only build before Oct 29 for when a normal deploy is impossible (I-33).
- G-15 **No manipulation** [POLICY + applicable market-abuse law; supports F-48 "no material misrepresentation". Note F-72 is an eligibility clause about people with past sanctions, not a conduct rule]. No order placed in order to move a price; [POLICY] in the final [H] h, no order larger than [p]% of visible depth.
- G-16 **Open orders at version switch** [PRACTICE]. Cancel open/resting orders at every switch, or record which version owns them.
- G-17 **Jurisdiction** [RULE: F-70 legal compliance; F-71 identity verification] [RULE-DERIVED: Web3 API terms, E-14 "IP checks"]. Operate only as permitted; never use VPNs/relays to bypass geo-restrictions.
- G-18 **Fencing, at-most-once signing and reconciliation** [PRACTICE; MUST for any deployment, single instance with restarts included; the fencing part is MUST if any standby exists; I-64]. (a) Persist the authorized payload, payload hash, execution identifiers and signing state durably before a signed payload leaves the signer. (b) The signer signs at most once per `decision_id` (unique constraint). (c) Leadership epochs are issued and persisted durably and enforced at handover; the signer rejects epochs below the highest persisted. (d) Reconcile outstanding signed authorizations before creating any replacement economic action. (e) Recovery uses venue-observable identifiers (wallet nonce, quote ID, RFQ order hash, tx hash, API order status), never the decision ID alone. (f) Distinguish quote expiry, signed-order validity (EIP-712 deadline/expiry) and settlement; per execution path (self-submitted swap / RFQ) define when rebroadcast, replacement or cancellation is allowed. (g) An ambiguous intent stays UNRESOLVED (absence from one query ≠ non-submission) and blocks conflicting new actions on that token but never blocks exits of confirmed holdings (confirmed holdings = on-chain balance minus quantity already in UNRESOLVED sell intents); UNRESOLVED resolves when the signed order's deadline has passed and nonce/order-hash status is checked. (h) No nonce-replacement cancellation (a same-nonce self-transfer is a wallet transfer/arbitrary call under F-64, and G-01 rejects it) unless organisers confirm. (i) Self-submitted swaps must carry a router `deadline` in calldata — verify the API-built tx has one; UNRESOLVED clears when that deadline has passed and the nonce is consumed (check receipt) or the tx is dropped. Test: under connection loss, process crash and leadership handover, no duplicate economic execution occurs; every intent reaches a reconciled terminal state or remains explicitly UNRESOLVED with conflicting actions blocked (zero fills can be correct). Say "at-most-once signing per decision + reconciliation", not "exactly-once".

Guardrails G-20..G-47 (mostly POLICY; G-40–G-42 RULE; G-43–G-44 RULE-DERIVED) and harness additions G-50..G-54 — in `larp/plan.md`.

---

## 11. OPEN QUESTIONS (ranked)

Working assumption in brackets; **UNRESOLVED** = no safe assumption, design must work either way.
1. Q-26 Is a KYC-verified Binance (exchange) account required, and can Singapore-based participants obtain/use one for this challenge? (T-03) [UNRESOLVED]
2. Q-12 Can Singapore-based participants use the Web3 API/Developer Portal and trade bStocks, and host in Singapore? (E-14, E-15) [UNRESOLVED; never bypass]
3. Q-03 Opening asset(s); is BNB for gas provided; does BNB count in equity? [UNRESOLVED]
4. Q-08 May the agent swap into BNB for gas? [Assume no until confirmed.]
5. Q-04 What is the valuation source and valuation instant? [UNRESOLVED]
6. Q-06 Exact start/end timestamps of the scored run. [UNRESOLVED — the stated dates span 15 calendar days vs "14 days" (I-08).]
7. Q-16 What satisfies the "thinking output" deliverable: vendor summaries? decision-model probabilities plus structured assessments? raw CoT only? [UNRESOLVED]
8. Q-07 Is an ERC-20 `approve` to the API-returned router allowed? [Assume yes, capped to order size.]
9. Q-10 Mapping granularity: one decision → several orders? one order → several txs (partial fills, RFQ settlement, failed txs)? [Map everything, both directions.]
10. Q-09 Does a human HALT/restart count as manual intervention? May an operator trigger an agent-coded flatten? [HALT, restart after reconciliation and version deploys OK if logged; no flatten.]
11. Q-17 Minimum-activity requirement; are zero/low-activity teams ranked? [UNRESOLVED]
12. Q-19 Eligible instrument list; leveraged ETF tokens; frozen during the run; valuation if an instrument becomes ineligible? [Exclude leveraged tokens.]
13. Q-20 Treatment of dividend Multiplier, splits, unsolicited tokens and the funding transfer for equity and "unexplained transfers". [Log all; never touch unsolicited tokens.]
14. Q-29 What off-hours liquidity (spreads/depth, RFQ availability) will the challenge path expose? (H-01)
15. Q-27 Is the "Laya" checkpoint (or any self-hosted model) acceptable, and what licence evidence is needed? (I-38, E-51)
16. Q-30 (internal, for the team) Laya: licence (publisher-stated Apache-2.0; confirm file-level licence at the pinned revision), training-data cutoff, redistribution rights under F-49c. [UNRESOLVED; decide by the onboarding declaration (D-03): if still unanswered, either don't run Laya or declare exactly the model that will run; never run an undeclared principal model (F-12, F-66).] Checked 2026-10-04 (HF API, card metadata only): Laya was published 2026-09-18, its training data is not stated (so its cutoff could run to Sep 2026 and overlap our clean evaluation window, I-67), it has 0 downloads, and there is no LICENSE file (the apache-2.0 tag is metadata only). Its backbone, `answerdotai/ModernBERT-large`, is apache-2.0 (also metadata only), was published 2024-12-11 (cutoff ≤ Dec 2024) and describes its pre-training data. **⚠ RECOMMENDED — NOT DECIDED (team to discuss):** declare ModernBERT-large + our own typed decision head as the base. The proposal's "bidirectional encoder with a typed decision head" still holds, and the proposal never names Laya (I-38). Laya becomes an offline challenger: it enters only if it beats ModernBERT on the calibration block and its provenance is cleared, then via re-declaration (Q-22).
17. Q-11 Equity sampling frequency for the max-drawdown tie-break.
18. Q-13 Do prompt/config-only changes require a full version event? [Yes.]
19. Q-14 Grace window for delayed trace uploads. [UNRESOLVED]
20. Q-21 Are weekly diagnostics published during the run?
21. Q-22 Can declared principal model/data services change mid-run via a version event? [Re-declare.]
22. Q-23 Does "invalidate affected trades" reverse their equity effect?
23. Q-15 Does dev-phase funding equal the scored-run opening value?
24. Q-28 What is the late-Nov/early-Dec "virtual technical review" (T-03), and is it part of the audit?
25. Q-01 Proposal deadline time/timezone on Sep 30. [Sep 30 is the last application day. Submit before 23:59 SGT on Sep 30. The organiser's DoraHacks times use UTC+8, which weakly suggests (inference, not confirmed) the proposal deadline is also UTC+8.]
26. Q-02 Prize split; what "prize assets" are.
27. Q-18 Is a DoraHacks BUIDL submission required by "2026/11/13 22:59"? Time zone resolved: 22:59 UTC+8 = 14:59 UTC (F-07). [Whether any BUIDL submission is required remains open (I-60).]
28. Q-24 Sharing/confidentiality terms for winner deliverables.
29. Q-25 Does "non-public information about … the instruments involved" exclude employees of issuers of eligible bStocks?

---

## Post-onboarding re-verification checklist (run when the official documents arrive, Oct 5–10)
Official onboarding documents take precedence over everything here (§0.2). Record the document and section for each change.
- [ ] Re-verify every F-item (F-01..F-80) against the Participant Guide, scoring rules, Audit Log Specification and incident policy; mark superseded items and cite the replacement.
- [ ] Answer or close each Q-item in §11, re-rank the rest; move official answers into F-items with their source. Priority:
  - [ ] Q-03 / Q-08 — opening asset, gas (BNB) provision, swap into gas → I-03, I-26, G-13, G-28.
  - [ ] Q-04 — valuation source and instant → I-01, I-07, D-04, G-24.
  - [ ] Q-06 — exact scored-window start/end → I-08, I-09, G-24, D-04.
  - [ ] Q-16 — accepted "thinking output" format → I-29, E-33, G-06, T-17, D-03.
  - [ ] Q-19 — eligible instruments, leveraged tokens → I-41, G-02, I-61.
  - [ ] Q-14 — upload grace window → G-07, G-44.
  - [ ] Q-07 / Q-09 / Q-10 — approvals, HALT vs manual intervention, mapping granularity → G-01, G-08, I-21, I-24, G-04.
  - [ ] Q-12 / Q-26 — jurisdiction and KYC → I-70, G-17.
  - [ ] Q-18 — any DoraHacks BUIDL requirement → I-60.
- [ ] Downgrade or delete any I-item the documents settle — at least I-01, I-03, I-07, I-08, I-26, I-60 (reference/inferences.md) and any LARP inference in larp/plan.md that depends on them.
- [ ] Fill `[bracket]` placeholders: G-05, G-15, G-21, G-22, G-24..G-29, G-34, G-37, G-44, G-46, G-50, H-01, H-03, I-63, I-66, D-07, D-08, §6.1 and the §9-derived operating plan (larp/plan.md).
- [ ] Re-tag every [RULE-DERIVED] guardrail as [RULE: F-xx] or [POLICY] against the official text: G-01, G-02 (leveraged tokens), G-03, G-05, G-06, G-08, G-11, G-12, G-13, G-17, G-43, G-44.
- [ ] Re-check T-03 / T-04 (team-transcribed form fields and their implications) against the form or the onboarding material.
- [ ] Update `revised` and `source_verification`, bump `version`, add a change-log entry.

---

## File index
| IDs | File | Section |
|---|---|---|
| `F-01`–`F-80` | SKILL.md | §1 |
| `G-01`–`G-18` | SKILL.md | §7.1 |
| `Q-01`–`Q-30` | SKILL.md | §11 |
| `E-01`–`E-52` | reference/environment.md | §3 (E-51: §3.6 Models; E-52: §3.5) |
| `I-01`–`I-09` (I-02 moved to S-01), `I-20`–`I-36`, `I-39`–`I-42`, `I-54`, `I-60`, `I-70` | reference/inferences.md | §4 |
| `L-01`–`L-54` (incl. `L-31b`) | reference/literature.md | §12 |
| `T-01`–`T-19` | larp/plan.md | §2 |
| operating plan | larp/plan.md | §9 |
| `D-02`–`D-09` | larp/plan.md | §6.4 |
| v1.0 adopted scope (status table) | larp/plan.md | top |
| declared values from the submitted proposal (uncalibrated) | larp/plan.md | top, after the scope table |
| concept, `G-50`–`G-54`, `P-01`–`P-17` | larp/plan.md | §6.1–§6.3 |
| reference architecture | larp/plan.md | §8 |
| `I-37`, `I-38`, `I-50`–`I-53`, `I-55`, `I-56`, `I-58`, `I-59`, `I-61`–`I-67` | larp/plan.md | §4 |
| `H-01`–`H-03` | larp/plan.md | §5 |
| `G-20`–`G-47` | larp/plan.md | §7.2–§7.4 |
| `S-01`–`S-07` | larp/strategy-opinions.md | Appendix A |
| ideas and experiments (`IDEA-`, `EXP-`) | ../LEDGER.md (index) → ../ledger/<ID>.md | — |
| `T-20`, `I-57`, `D-01`, proposal guidance (§10), v0.3 as it was | retired with the proposal on Sep 30 | git history: commit 2985af5, `docs/skill/archive/` |
Moved sections keep their v0.3 numbers, so cross-references such as "§6.1" or "§9" still resolve via this table.

---

## APPENDIX B — Known gaps and change log
- Not captured independently: the Google Form (fields taken from T-01..T-03); official onboarding documents (issued Oct 5–10); Web3 API rate limits; gas sponsorship; eligible instrument list; nof1 primary data.
- v0.1 (2026-09-27): primary source only. v0.2 (2026-09-27): red-team fact fixes; environment research; principles, guardrails, architecture, plan, open questions, literature.
- v0.3 (2026-09-29): external reviewer feedback — one central capability (I-55); off-hours pricing as hypothesis H-01; RULE/RULE-DERIVED/POLICY/PRACTICE tags; evidence re-graded; bounded volatility-scaled sizing (G-29, P-07); I-30/I-29/Q-06 corrections; tournament material to Appendix A; LARP team facts, inferences, harness additions G-50..G-54, H-01..H-03. Adversarial pass: I-63..I-66, G-18, T-20, D-06, E-33; tag fixes on G-04, G-07, G-08, G-11, G-15, G-17; arithmetic and timing corrections. Full v0.3 log: archive/SKILL_v0.3.md.
- v0.4 (2026-09-30): **Page re-verified** (body text, timeline image and banner unchanged). **Fixes:** F-07 (DoraHacks times are UTC+8; API timestamps); F-80 / §1.8 (second snapshot: 86 registered, participant reply on Q&A, BUIDL form disabled, 0 BUIDLs/teams/tracks/bounties); I-60 and E-50 (deadline Nov 13 14:59 UTC conflicts with Eventbrite; looks like a platform default; Confidence Low); Q-18 (time zone resolved; BUIDL requirement open); Q-01 (submit before 23:59 SGT Sep 30); §9 row Sep 29–30; G-18 moved after G-17; F-09 moved to the start of §1.2; §11 list renumbered (Q-30 no longer "15b"); source_page.md re-verification note. **Restructure:** core SKILL.md (reading contract, never-do list, current phase, F, G-01..G-18, Q, re-verification checklist, file index) plus reference/environment.md, reference/inferences.md, reference/literature.md, larp/plan.md, larp/strategy-opinions.md, archive/proposal-phase.md, archive/SKILL_v0.3.md. No IDs changed; item wording unchanged except the fixes above.
- v0.5 (2026-09-30): external reviews A (proposal brief) and B (technical review of v0.3) red-teamed and applied. **Laya corrected via the model card** (new E-51): non-autoregressive, never generates text, Apache-2.0; base checkpoint near chance zero-shot and over-confident; the 0.766 figure belongs to `laya-typed-decisions`. **Accepted:** §8 diagram (decision model → selection gate; rule-defined regime governor; memory written only after verification; recovery by observable identifiers); §6.1 canonical flow and planning-claim caveat; archive §10 framing, originality wording, Say/Avoid changes, model row, priority-1 header. **Partial:** I-65 (three gate kinds rather than B's two); status field (legend + adopted-scope table only); verification metadata (frontmatter + §0.2 rule); "different clocks" (motivation OK, edge claim not). **Rewritten:** G-18, G-25, G-41, G-42, G-47, G-51, G-53, I-04, I-20, I-29, I-38, I-50, I-57, I-64, I-65, I-66, H-01, H-02, H-03, D-05, D-06, P-05, T-04, E-33, Q-27, Q-30; notes only on T-12, T-14, T-18, T-20, §9. **New:** E-51, D-07, Status legend (§0.1), `revised`/`source_verification` frontmatter, priority by deadline (§0.4), v1.0 adopted scope table (larp/plan.md). **Not applied:** per-claim verification table (bloat); three-part template for every G item (only G-41, G-42); heavy resampling machinery for H-01; review A's "exactly-once signing" (replaced by at-most-once signing + reconciliation, G-18); review A's "archive the submitted version" (already in §9).
- v0.5.1 (2026-09-30): final red-team fixes. **High:** §9 dev-wallet txs only from versioned test-mode code via decision records; G-03 start-up gate for every deployable + third-party services in the manifest; G-01 approve logic (token contract `to`, spender allow-listed); G-18 (h) no nonce-replacement cancellation, (i) router `deadline` check, "confirmed holdings" defined. **Medium:** never-do #1 / G-08 / Q-09 human actions (HALT, restart after reconciliation, version deploys); G-23 rule-based event policy; D-06 proposal sub-items moved to priority 1 (§0.4); D-07 split into D-07 (baseline V0) and new D-08 (inconclusive default), H-02 and §10 updated; §7.1 footer tags; G-41 / never-do #7 private training/label data; F-80 API details moved to new E-52, F-07 and I-60 cite it; G-53 held names still reach the decision model; Q-30 declaration rule; team_sources note. **Low:** F-42 intro quote; I-62/D-06 drafts-differ wording; D-01 ≈36%; G-50 ≤ [6] calls / ≤3 tool types; E-33 ↔ I-29 aligned; "classifier" → "decision model" (G-31, G-50, D-03, I-37, I-50, I-51, I-63 title, H-02, Q-16); §8 diagram (regime governor → risk governor, HOLD record paths, risk-limit exit bypass); I-65 / §10 three gate kinds; proposal-phase header; §0.4 team actions; file index notes (I-02 → S-01, SKILL_v0.3 location); §0.2 precedence; checklist placeholders.
- v0.5.2 (2026-10-03): finalist status recorded (§0.4); archive retired (proposal-phase.md, SKILL_v0.3.md → git history, commit 2985af5); ledger split into an index (`../LEDGER.md`) plus per-entry files; reading-budget rule added (§0.2); file index updated.
- v0.5.3 (2026-10-03): never-do #6 and G-40 record that GitHub branch protection is unavailable on our plan, so the no-rewrite rule is procedural; larp/plan.md gains a "Declared values" table (proposal numbers are declared defaults, not calibrated; which ones shape training) and a D-06 update; IDEA-001 (training-set plan and source access check) added to the ledger.
- v0.5.4 (2026-10-04): **recommendations only, marked ⚠ RECOMMENDED — NOT DECIDED** (team to test/discuss) on D-03 (evidence LLM), D-07 (V0 baseline), D-08 (inconclusive ladder), new D-09 (price vendor) and Q-30 (ModernBERT-large as base, Laya as challenger); new I-67 (memorisation contaminates training inputs); IDEA-001: ALFRED only if macro values are model features.
- Next update: after finalists (Oct 2) and after onboarding documents (Oct 5–10) — run the checklist above.
