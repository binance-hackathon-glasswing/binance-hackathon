# PRIMARY SOURCE — verbatim capture, 2026-09-27 (SGT)
# URL: https://dorahacks.io/hackathon/binance/detail  (+ timeline image, banner image, announcements, Q&A)

## Re-verified 2026-09-30 (SGT)
Live page re-checked on 2026-09-30: body text, timeline image (cdn …/1a07afc96584f5eca5194cb41679b9e1.png) and banner (…/1a07ae147b0cf9ca030be524dc5b4d46.png) unchanged since the 2026-09-27 capture below. Hackers registered: 86. Announcements: still empty. Q&A: the "password" post now has 1 reply from another participant ("hacker_18") saying ideas go through the Google form; still no organiser answers. DoraHacks API (`/api/v1/hub/hackathons/binance`): timeline_start 1788710400 = Sep 7 00:00 UTC+8 (Sep 6 16:00 UTC); timeline_end 1794581940 = Nov 13 22:59 UTC+8 (Nov 13 14:59 UTC); the page renders these in the viewer's local time. The verbatim capture below is unchanged.

## Sidebar metadata
PRIZE POOL: 6,000 USD
EVENT TIMELINE: Submission 2026/09/07 00:00 · Deadline 2026/11/13 22:59 · Virtual  ("47 days left for submission" on 2026-09-27)
HACKATHON TAGS: AI Agent · Live Trading · Trading Strategies · Real World Assets · Onchain Finance
PLATFORM TECHNOLOGY: OpenAI · Anthropic · Llama · LangChain · Python · Binance
Hackers registered: 75 (as of 2026-09-27)
Announcements: "The list is empty" (as of 2026-09-27)
Q&A: one unanswered question asking for a "password" (2026-09-25). No organiser answers.
Proposal form: https://forms.gle/UmDXgdwPPwknYZur9 (requires Google sign-in; contents not captured)

## Banner image text
"BEYOND THE BENCHMARK — THE BINANCE AGENTIC AI CHALLENGE. PRIZE POOL USD 6000. PRIZE POOL Binance Seeds Program internship and full-time employment opportunities. Applications: Sept 9 - 30, 2026. Oct 12 - Nov 12, 2026"

## Page body (verbatim)

Beyond the Benchmark: The Binance Agentic AI Challenge

Benchmarks are static. Reality isn't. Build an LLM-powered Agentic AI system that gathers information, reasons, decides, manages its own risk, and operates reliably — then find out how it holds up over a 14-day run in a real-time environment. Fully audited. Fully traceable. The best system wins.

### Overview

Applications: Sep 9-30 — Submit your proposal through this form

Format: Online

Duration: 4 weeks of active work (2-week build + 2-week scored run); ~7 weeks end-to-end including onboarding and audit

Finalists: <25 teams selected from open applications

Team size: 1-4 people; you may join only 1 team

Prize pool - 6,000 USD in prize assets across the top 3 teams, plus Binance Seeds Program internship and full-time employment opportunities

The question we're asking: can a team build, operate and improve an autonomous Agentic AI system that runs end-to-end in a real-time environment — and produce a decision trail that proves how it got there?

You never compete with your own capital. Participants are never required, asked or permitted to use personal funds to enter, continue or complete this challenge. This is a technical research and developer challenge.

### The Challenge

Build an autonomous Agentic AI system and prove it can operate in the real world.

Most agents are evaluated on saved data, in conditions that forgive them. This one is evaluated while it runs — against real-time conditions, latency and costs, with no ability to rewind.

Your system acquires information, reasons, decides, manages its own risk, and executes eligible bStocks trades on BNB Smart Chain through Binance Web3 Open APIs — using only information available to it at each decision point.

You build it, host it and operate it. Binance sets the rules and verifies the record.

You own: your wallets and keys, Developer Portal credentials, data acquisition, models, agent harness, strategy, risk logic, hosting, monitoring, logging and recovery.
Binance owns: the competition rules, eligible instruments, the scored window, the audit standard, the scoring method, and the final results.

Binance does not run your code or hold your wallet keys. The repository is not public; a designated Binance audit account receives read-only access for integrity review.

### What makes a strong entry

It must be genuinely agentic. Innovate at the model layer — domain post-training, fine-tuning, preference optimization, Agentic RL, distillation, tool-use adaptation — and at the harness layer — context engineering, tools, Skills, memory, planning, verification, guardrails, observability, recovery. Rules and classical ML may support the system, but larger spend and higher call volume earn nothing on their own.

Your information pipeline is your edge. Any public or legally authorized market, news, social, on-chain or derived data, including commercial APIs and your own services, provided you hold the rights. You cover your data, model and hosting costs.

Reliability matters in practice. Failures and recovery affect your system's ability to trade and appear as audit evidence and diagnostics — not as a separate score.

Every scored trade must be traceable. It must map to one registered Agent version and one unique decision record with a concise reason summary.

Competition rules are common to everyone. Teams may use different public or legally authorized data, models, tools and infrastructure. The scored window, eligible instruments, opening value, valuation method, scoring formula and audit standard are the same for all teams. Full technical parameters are issued at onboarding.

### Timeline & Submission  (table is an IMAGE on the page; transcribed)

| Phase | Dates | What happens | What you submit |
|---|---|---|---|
| Apply | Sep 9 – 30 | Open applications | A concise proposal covering: agent concept, high-level architecture, intended model approach, agent harness and tools, data-acquisition approach, basic risk design, team capability and roles, delivery plan. Submit through this form. |
| Finalists announced | Oct 2 | 25 teams selected | — |
| Onboarding | Oct 5 – 10 | Wallet, Developer Portal and repository setup; technical briefing | Registered development wallet address; private repository with audit access; declaration of your principal data and model services; required team information |
| 2 week Development phase (unscored) | Oct 12 – 26 | Build and operate in your own environment, integrate logging, test small-value trades, test recovery | A week-one checkpoint commit and progress note; end-to-end self-check evidence |
| Final activation | Oct 27 – 29 | Register a fresh final wallet; clear the pre-final integrity check | New final wallet address; the commit and version manifest for your starting build |
| 2 week Scored run | Oct 29 – Nov 12 | 14 days of live operation. Keep improving — every version must be committed and logged before it trades | Daily structured decision-trace uploads; a version event for each new build deployed |
| Provisional ranking | Nov 13 | Standings published; scored activity stops | — |
| Winner audit & awards | Nov 16 – 20 | Code, version, wallet and decision-trace review | Version history, commits, manifests and complete local logs (top-ranked teams only) |

No public real-time leaderboard. The full 14-day window determines the ranking.

Finalists receive a Participant Guide, Web3 Open API documentation, the Audit Log Specification, scoring rules and incident policy at onboarding. You don't need any of it to apply.

### Judging & Scoring

Two separate evaluations. Proposals are judged by people. The ranking is not.

Stage 1 — Finalist selection (proposals during application stage)
Binance selects <25 finalist teams, evaluating proposals on:
- Feasibility — buildable and operable end-to-end within the timeline
- Agentic depth — real reasoning, tools, memory, planning, verification — not a thin LLM wrapper
- Risk awareness — limits, failure modes, guardrails, recovery
- Originality — a distinctive idea at the model or harness layer
- Ability to deliver — right skills, clear roles, credible milestones
Not considered: proposal length, design polish, brand names in your stack, or budget.

Stage 2 — Scored Run (14 days, mechanical)
- Every eligible team starts from the same opening value, so scores compare directly
- Calculated from your registered wallet's on-chain state and bStocks execution records, using the published valuation source
- Proposed FinalScore (%) = (Final Wallet Equity - Opening Wallet Equity) / Opening Wallet Equity x 100. The final rules will confirm the valuation method and treatment of transfers before onboarding.
- Real costs are reflected. Trading fees and gas reduce what remains in the wallet, and therefore reduce your final figure
- Tie-break: lower maximum drawdown — the largest percentage fall from a previous equity peak to a later low during the run. Still tied → shared rank
- The full 14 days count. No best-week selection, no dropped days, no live leaderboard

Stage 3 — Winner audit (pass/fail)
Top-ranked teams are provisional winners until the audit clears. Binance reviews commits, version history, manifests, submitted traces and complete local logs, then reconciles sampled decisions against your registered wallet's transactions and bStocks execution records.
We're checking for: every scored trade mapped to a registered version and a unique decision record; no unmapped trades; no unexplained transfers; no version gaps; no manual intervention; no prohibited data; no material misrepresentation.
The audit adds no points. It confirms your result, or removes it. Awards are announced only after it passes.

Winner Deliverables — beyond the audit
The audit requirements above verify authenticity. Winning teams are required to go one step further and submit additional deliverables:
- Chain-of-thought (thinking) output — the reasoning your agent produced for its decisions
- Full original prompts and tool definitions — system prompts and tool/Skills definitions exactly as deployed
- Models, plus complete model inputs and outputs — your model artifacts with complete input/output records (for third-party API models, complete request and response records in place of weights)
Exact scope, format and sharing terms are confirmed in the official rules before onboarding.

Not scored
Presentation and demo polish · model or infrastructure spend · call volume · number of trades · development-phase performance.
Weekly return, drawdown, fees, gas, turnover, version changes, heartbeat gaps, failures and recovery events may be published as diagnostics — no points, no separate rankings.
Final scoring, valuation method, treatment of transfers and tie-breakers are confirmed in the official rules before onboarding, and remain fixed for the duration of the scored run.

### Rules & Restrictions
Autonomous operation. Every scored trade must come from your registered Agentic AI system — no manual trading. Each trade maps to one agent version and one unique decision record. New versions must be committed, manifested and logged in a version event before they trade.

Repository integrity. All code affecting decisions, trades or logging must be pushed to your registered repo before it runs — including code on your own remote services. The challenge branch preserves history: no force-pushes, no rewrites. Never commit secrets, keys or private training data. Third-party services are declared in your manifest, not exposed as source.

Honest logging. Daily trace uploads to write-once storage, plus one after any material incident. No end-of-event backfilling. Buffer locally during outages and upload within the published grace window. Credentials never appear in logs. Raw chain-of-thought isn't required in your daily traces — but winning teams are required to provide their thinking output as a deliverable (see Winner Deliverables), so make sure your logging captures it.

Clean information. No Binance-internal data, material non-public information, or future information. No other team's private data, and no source you aren't authorized to use.

Dedicated wallets — prohibited in both phases:
- Adding your own funds or any external capital
- Withdrawals, wallet-to-wallet transfers, bridging
- Unrelated swaps or arbitrary contract calls
- Manual trading
- Leverage, shorting, derivatives

These keep conditions equal and ensure no participant increases personal financial exposure to stay in the challenge. If development funds run out, there's no replacement — but you can keep building, and your final wallet still starts from the same opening value as everyone else's.

Consequences. Manual trading, unmapped trades, fabricated or incomplete decision records, prohibited data, false declarations, credential misuse and material audit gaps lead to ineligibility or disqualification. Binance may suspend a team or invalidate affected trades for security, integrity or eligibility reasons — this implies no custody or control of your wallet.

### Eligibility
Eligibility is open to all legally-compliant participants. You must have full civil capacity under your own local laws — this is a technical research challenge.
Open to: undergraduate and post-graduate students, working professionals, and academic or research teams — applying in their own personal capacity.
You must also:
- Hold the rights to every data source, model, API and third-party component in your system
- Complete identity verification during onboarding — teams that cannot complete it forfeit their place
Not eligible:
- Companies and other legal entities — participation is individual only
- Anyone sanctioned or penalized for financial, fraud or market-misconduct violations
- Anyone with access to non-public information about this challenge, its scoring, or the instruments involved
- Internal Binance employees
Binance may verify eligibility at any stage and may withdraw a team that does not qualify.

This is a technical research and developer challenge. It is not trading education, investment advice, or a promise of any outcome. Instruments, environment rules, data rules and participant eligibility are subject to final event requirements. Full operating parameters are provided to finalists during onboarding.
