# Handoff 2026-10-08 — direction review (TEMPORARY)

- Author: SYZ, drafted with Claude (one Cowork thread, 2026-10-08).
- Status: **temporary working note.** Nothing here is decided. Move each surviving item into its proper home (SKILL.md F/Q, plan.md D/G, a ledger entry, INCOMPLETE_WORK) and then delete this file.
- Why it exists: the thread answered strategy questions quickly and made several rough assumptions. SYZ asked for every detail to be written down so a new thread can investigate the direction properly.

## Labels used here
- **[VERIFIED: source]** checked in this thread against the verbatim page capture (`docs/official/source_page.md`), the kit (`docs/official/kit/`, Guide re-read 2026-10-08), or a repo file.
- **[TEAM STATEMENT]** SYZ said it in this thread; not in any organiser document.
- **[REPO ESTIMATE: file]** a number or claim taken from a repo file without re-checking its sources.
- **[CLAUDE OPINION]** a judgement from this thread. Treat as a hypothesis.
- **[ASSUMPTION — UNCHECKED]** something the thread assumed and never verified.

## 1. Repo state left by this thread
- **Uncommitted edits (F-117)** in `docs/skill/SKILL.md` (v0.7.4), `docs/skill/larp/plan.md` (G-46 rewritten, §9 scored-run row), `docs/skill/reference/inferences.md` (I-33, I-35), `docs/ledger/README.md` (rule 5), `docs/INCOMPLETE_WORK.md` (GAP-42). SYZ has not yet said whether to commit and push.
- The Project mirror copies of SKILL.md, plan.md, inferences.md and INCOMPLETE_WORK.md are behind the repo.
- This file is new and uncommitted (`docs/handoff/`).

## 2. New facts and statements from this thread
1. **F-117 (recorded as an organiser answer, paraphrase).** [TEAM STATEMENT, relayed as organiser answer] "we can keep improving in the development period, but must halt once this period is over". Read as: code changes stop; the build registered at final activation runs unchanged through the scored run. Conflicts with the page's scored-run text "Keep improving — every version must be committed and logged before it trades" (F-15). [ASSUMPTION — UNCHECKED] that "halt" means changes, not trading; that the freeze point is final activation (Oct 27–29), not Oct 26.
2. **No declaration has been requested.** [TEAM STATEMENT, not yet in SKILL.md] The organisers' only form was the Google Form for the wallet; the team was added to a Telegram chat; no declaration of principal data/model services, repo registration or audit-account form has been requested. The page lists "declaration of your principal data and model services" as an onboarding submission (F-12), but the organisers have not operationalised it (Q-33 still open). Consequence: **Oct 10 is not a deadline.** The repo still frames decisions as "due before the Oct 10 declarations" (INCOMPLETE_WORK heading, GAP-53/56/57; plan.md D-03, D-09, D-10) — re-date to the real deadlines (model freeze Oct 18 if kept; code freeze at final activation Oct 27–29). Safe default: keep a services list (every model and data source) in each version manifest, since the page says "Third-party services are declared in your manifest" and "false declarations" disqualify (F-66).
3. **The kit's reference agent lets the LLM decide.** [VERIFIED: participant-kit.md K16; Guide p.13] `strategy_agent.py` runs an Anthropic tool loop (`AGENT_MODEL "claude-sonnet-5"`) with a `place_order` tool; code enforces amount caps and the arming switch. The log's `orders` field is what "the code finally decided to place this round (after risk checks …; not necessarily what the model output)" (F-99). The Node.js/Java demos are rule-only, no model call, and fill `cot` with the rule statement (F-106a).

## 3. What the challenge asks for (re-read 2026-10-08)
[VERIFIED: source_page.md unless noted]
- Core question: "can a team build, operate and improve an autonomous Agentic AI system that runs end-to-end in a real-time environment — and produce a decision trail that proves how it got there?" Called a "technical research and developer challenge" three times; "not trading education".
- "Build an LLM-powered Agentic AI system that gathers information, reasons, decides, manages its own risk, and operates reliably". "It must be genuinely agentic" (model layer: post-training, fine-tuning, preference optimisation, Agentic RL, distillation, tool-use adaptation; harness layer: context engineering, tools, Skills, memory, planning, verification, guardrails, observability, recovery). "Rules and classical ML may support the system, but larger spend and higher call volume earn nothing on their own." Stage 1 listed "not a thin LLM wrapper".
- Stage 1 (proposal, human-judged): done; team is a finalist.
- Stage 2 (scored run): page = proposed FinalScore % equity change, tie-break max drawdown, "Not scored: … number of trades". Organiser chat F-115 = "completed trades' PnL, drawdown, logs, and code repo all together", and not trading "is definitely not what this competition is about". **The formal scoring rules were never issued** (kit has none, K18). Q-39 open: weights; whether open positions count or only completed round trips; BNB in equity.
- Stage 3: pass/fail audit (mapping of every fill to a version and decision record, no manual intervention, no prohibited data, no misrepresentation). Winner deliverables: thinking output, prompts and tools as deployed, model artefacts plus complete inputs/outputs.
- Constraints: five names (NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB), long-only, no leverage; ~200 USDT final wallet, USDT only, gas from the wallet (F-107, team statement); no human action during the run (F-114) and no changes after development (F-117); mainnet only.
- Live re-check of the DoraHacks page failed (HTTP 405 to automated fetches); the capture is from 2026-09-27/30.

## 4. Cost and gas
- [VERIFIED: Guide p.5, F-93] one approve + swap = 0.000022–0.000046 BNB ≈ $0.02–0.035 at BNB ≈ $756 (organiser test, ~Oct 1). Consistent with 450k–930k gas × 0.05 gwei (E-17).
- [REPO ESTIMATE: plan.md "Funding implications"] gas ≈ 11–20 bp per leg on an 18 USDT trade; 5–9 bp at 40 USDT.
- [REPO ESTIMATE: IDEA-004] full round trip ≈ 100 bp at 18 USDT incl. 22–39 bp gas. **Spread and impact were never measured** for bStocks; quote logging starts Oct 12. Note: quotes "are free and don't check balances" (Guide p.7), so quote-only cost probes need only a Web3 API key, not funds — check whether this can start before Oct 12 and whether plain API calls (no ai-seeds `log()`) leave any audit trace.
- [ASSUMPTION — UNCHECKED] today's BNB price and gas price (both lookups blocked from the cloud and from SYZ's machine).
- [CLAUDE OPINION] frequency table: 5 / 14 / 40 round trips ≈ 0.45% / 1.3% / 3.6% of equity at 100 bp per 18 USDT round trip; suggested 5–15 rule-driven round trips; fewer, larger trades. Rests entirely on the unmeasured 100 bp figure and on Q-39.

## 5. Claims the thread made that need proper investigation
Each is a rough assumption or opinion, not a finding.
1. [REPO ESTIMATE: IDEA-004 §1] "score ≈ exposure × market path; a news/skill overlay is worth ≈ 0.09% of equity" (4 trades × 18 USDT × 25 bp). Depends on declared sizing, trade count and assumed edge.
2. [REPO ESTIMATE: IDEA-004, IDEA-007] "no model trained on kit data can show an edge" (MDE and stock-days arguments). Depends on assumed effect sizes and on the kit-only data decision; IDEA-008 (Keith) argues for a trained model and was not considered in this thread.
3. [REPO ESTIMATE: IDEA-004 §2, literature not re-read] PEAD gone in large caps; LLM news signals decay and concentrate in small caps; "LLMs reading price history over-extrapolate" (AEA 2026 paper). Not re-verified.
4. [CLAUDE OPINION] layer ranking given: (1) execution + recovery + logging, (2) deterministic exposure/risk policy (IDEA-004 C1 base book), (3) thin LLM evidence loop, (4) model-layer training. Later corrected: the proposal's distinctive harness (bounded research loop, claim verification, thesis memory with falsifiers) should not be minimal — it is what got the team selected and what "logs and code repo" (F-115) would see.
5. [CLAUDE OPINION] C1 base book = the proposal's "pre-registered default". [ASSUMPTION — UNCHECKED] the proposal never defined the default (D-08 open); IDEA-004 asserts the link.
6. [CLAUDE OPINION] the LLM should choose from a fixed menu (LONG / HOLD / EXIT per name) on verified evidence, with code doing sizing and limits and able to veto. Not compared against alternatives. Conflicts with the proposal ("schema forbids trade actions"; T-12) unless recorded as a change.
7. [CLAUDE OPINION, withdrawn] "`trading-signal`, `crypto-market-rank`, `query-address-info`, `query-token-audit` are of little use." Judged from one-line descriptions only; never probed (K6b probed only the Web3 API, `query-token-info`, `binance-tokenized-securities-info`, `binance`). Unknowns: coverage of the five bStock contracts; timestamped history vs live snapshots only.
8. [CLAUDE OPINION] the harness needs runtime text for the evidence loop and the kit gives none (K6b: price and activity data only); suggested EDGAR for runtime only (public, acceptance timestamps, rights clear per IDEA-007 §1; four US names; SK Hynix via DART or nothing). Not compared with issuer IR pages, GDELT, or a hosted LLM's own web-search tool (rights and point-in-time issues unchecked). The kit-first decision (IDEA-001 §11) covers training/validation data only.
9. [CLAUDE OPINION] distillation: only text-describing tasks are distillable (event type/severity/veto, claim verification, extraction); return or direction cannot be; Claude can never be a teacher (Anthropic AUP, IDEA-007 §1 [VERIFIED in repo]); a 2-week small model is unlikely to beat a hosted frontier model at tool use (IDEA-007 C4). Score value of a distilled classifier ≈ 0 — but whether repo/log quality is scored is unknown (Q-39).
10. [CLAUDE OPINION] under F-117 every fallback must ship in v1.0 (DST Nov 1, gas top-up, API errors/429, upload spool, stuck tx, end-of-run policy, autonomous restart pending Q-40); external dependencies (hosted LLM snapshot) are a bigger risk when nothing can be patched.
11. [CLAUDE OPINION] "dedicated trading agent" in the quant sense = statistical models + risk rules, which LARP's decision model + governors already are; the binding constraint is rights-clear price history (D-09 on hold), not model choice.

## 6. Proposal vs current thinking (from this thread's comparison)
Same: risk/regime governors, version gate, write-before-sign, reconciliation, recovery, HOLD on failure, Oct 12–18 adapter / Oct 19–26 soak, cut line Oct 22, fallback "Otherwise the agent runs a pre-registered default and records that in its version manifest". Different: (a) decision model may not pass its own test → re-target or fall back (must run H-02 and record the result); (b) data sources (licensed prices, EDGAR, GDELT, FRED/ALFRED declared; now kit-first, FRED dropped for licence reasons); (c) character ("selective, abstains often" vs regular exposure with LLM veto/exit); (d) in-run releases (now banned by F-117); (e) execution details already corrected by the kit (I-68).

## 7. Questions the direction review must answer
A. Scoring: what each reading of Q-39 rewards, and a design that is robust to both.
B. The LLM's role in the decision (evidence reader only / chooses from a menu / full decision with code caps / rules with LLM veto) — judged against the page wording, the kit's reference agent and log format, audit and freeze constraints, cost, reliability, and the proposal.
C. Runtime data: probe the four unprobed Skills; choose a text source for the evidence loop; rights for each.
D. Exposure level and trading frequency; what can be measured before Oct 26 (quote costs, `openState` hours).
E. Whether any model-layer work (IDEA-007 Track A, IDEA-008, none) is worth the person-days.
F. How each deviation from the proposal is recorded (version manifest reasons, H-02 result, D-08 default).
G. What four people can build and soak between Oct 12 and Oct 26.
