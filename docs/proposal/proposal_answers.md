# LARP — Proposal answers (copy into the form)

Answers prepared for the Sep 30, 2026 submission (team names added).

---

## Your Proposal

LARP (Liquidity-Aware Regime Planner) is a selective trading agent for bStocks. It turns verified, point-in-time catalysts into long / hold / exit decisions, and it abstains when the evidence or its confidence is not good enough. The distinctive idea sits at the harness layer: evidence verification is part of the decision process, not a preprocessing step.

How the agent works. A catalyst might be a filing, an issuer release, or a scheduled macro or earnings event. For each held position, and for each candidate with a fresh catalyst, the agent runs a bounded research loop:
- It decides what evidence it still needs and retrieves timestamped sources through a small tool set: filing sections, issuer releases, and a second independent source. The loop is capped at 6 calls and 60 s per decision.
- It returns a structured assessment: catalyst type, direction, strength, novelty, durability, source agreement and risks.
- A separate verification step checks every material claim against the cited source text. Unsupported claims are dropped. If the core claim fails, the agent takes no new risk.
- Only verified claims update a thesis memory for each position. The thesis records the catalyst, the expected horizon and explicit falsifiers, and the falsifiers are re-checked every cycle. When a falsifier fires, the agent proposes an exit.

Model layer. The verified state feeds a self-hosted calibrated decision model. It is a bidirectional encoder with a typed decision head, which we fine-tune on our own point-in-time labels and calibrate on validation data. It outputs P(UP), P(FLAT) and P(DOWN) over the next 5 US trading sessions. A selection rule abstains unless confidence and margin clear thresholds fit on validation data. Abstention is a selection decision, not a fourth outcome class.

Control. Three deterministic layers decide whether any trade is allowed:
- a policy that maps the model's output to LONG, HOLD or EXIT,
- a rule-based regime governor that sets the exposure budget from realised volatility and drawdown,
- a risk governor that enforces limits and costs.

The LLM never signs, sizes or sets limits. Every trade is written as a decision record before signing and is tied to one registered version.

What we will test, not claim:
1. Whether verified evidence beats a no-evidence baseline at matched coverage, after costs. The evidence-assisted model trades only if it passes on held-out data. Otherwise the agent runs a pre-registered default and records that in its version manifest.
2. Whether off-hours bStocks quotes lag verified news. bStocks trade 24/7 while the underlying markets and news flow keep different hours, and this motivates the market-state-aware execution controls. Unless the test supports it, off-hours logic is used only as an execution guard.

We make no return promise. Hold/cash is a valid, logged decision.

---

## Data / tools used

Market and execution data:
- **Binance Web3 Open API:** executable quotes, routes, transaction building and simulation. Live quotes are the basis for every execution and cost check.
- **Organiser-published sources:** the published valuation source and the wallet state are authoritative.
- **BNB Smart Chain records:** used to reconcile every transaction and balance change.
- **Historical underlying prices:** licensed historical daily prices of the underlying US shares, for training labels. The vendor will be declared at onboarding.
- **Token-versus-share check:** bStocks quote history since the June 2026 launch, to measure how far the token has diverged from its share.

Information sources:
- **SEC EDGAR:** 8-K, 10-Q and 10-K filings, time-stamped by their acceptance time.
- **Issuer investor-relations releases and RSS feeds.**
- **GDELT news events:** the second independent source.
- **FRED/ALFRED macro data:** vintage data, so each value is as it was known at the time.
- **Official release calendars:** BLS, BEA and the Federal Reserve.

Models:
- **Hosted reasoning LLM for the evidence step:** full requests and responses are logged, and reasoning summaries are requested so the reasoning is readable.
- **Self-hosted calibrated decision model:** a fine-tuned encoder.
- **Small self-hosted finance sentiment/relevance model:** used for triage.

Agent tools (bounded loop):
- `fetch_filing_section`
- `fetch_issuer_release`
- `search_second_source`
- a point-in-time feature lookup

Deterministic services:
- Web3 API quote/build/simulate
- a signer with a contract allow-list
- a version gate
- a reconciler
- a write-once audit uploader

Stack: Python, PostgreSQL, and write-once object storage.

Rules we follow:
- Every item is stamped with event time, retrieval time, source URI and SHA-256.
- We keep a licence register for every source and model.
- No Binance-internal, non-public, other teams' or unlicensed data.
- No scraping of sources we have no rights to.

---

## Position & risk management

Actions:
- The agent takes only LONG, HOLD and EXIT actions, long-only spot.
- There is no leverage, shorting or derivatives, and leveraged-ETF tokens are excluded.

Sizing:
- Position size = 1% of equity ÷ (2 × expected 5-session volatility). The volatility estimate is trailing 60-session daily volatility × √5.
- The size is then cut for liquidity and capped:
  - ≤ 20% of equity per name,
  - ≤ 4 open positions,
  - ≤ 80% gross exposure, so at least 20% stays in cash.
- Example: a name with 2.5% daily volatility gets a position of about 9% of equity.

Entry requires all of the following:
- P(UP) and the margin P(UP) − P(DOWN) clear thresholds fit on validation data.
- The estimated entry cost from the live quote is ≤ 50 bp one-way. This covers spread, price impact, fees and gas.
- Estimated round-trip cost = the live entry cost plus an explicit allowance for the cost of exiting later.
- The thresholds are set so that, on validation data, the selected cases returned more than round-trip cost + 50 bp.
- The order is ≤ 10% of the quoted depth.
- The order aborts if quoted slippage exceeds its cap.

Exits:
- There are three exit triggers:
  - a confident DOWN signal on a held name,
  - a fired thesis falsifier,
  - a risk-limit trigger.
- Entry-cost thresholds never block a risk-reducing exit. Exits have their own slippage cap.

Drawdown control (equity measured on executable quotes):
- **Daily loss ≥ 3%:** no new positions for the rest of the UTC day.
- **Drawdown ≥ 8% from peak:** no new positions; exits continue. This is a new-risk halt, not a liquidation.
- **Drawdown ≥ 12%:** gross exposure is automatically reduced to ≤ 40%, using fresh quotes.
- **Stress regimes:** the regime governor lowers the exposure budget in high-volatility or stress regimes and can veto entries.
- **Scheduled macro and earnings events:** positions are handled by a pre-registered rule per event class (hold, reduce or flatten).

Failure modes:
- A data, model, tool or schema failure means HOLD, no new risk, and an incident record. A timeout never becomes a trade.
- A stale quote is re-quoted or the order is aborted.
- A reconciliation mismatch puts the agent into degraded mode until it is resolved.
- A gas-reserve floor keeps enough gas for exits.

Governance:
- All limits and thresholds are versioned configuration. They are hashed into the version manifest and enforced in code.
- A limit changes only through a logged version event with a stated reason, and limits are never loosened in response to a drawdown.
- Humans can halt the agent but never trade.

---

## How would you prevent future leakage and overfitting?

Point-in-time data:
- Every input carries its event time and our retrieval time.
- A filter at decision time rejects anything stamped later than the decision.
- Filings are dated by their EDGAR acceptance time, and macro data uses vintages (ALFRED).
- The server clock is checked, and trading stops if it drifts.

Validation discipline:
- Anchored walk-forward splits, with purge/embargo gaps at least as long as the 5-session label horizon.
- Training, calibration, threshold selection and final evaluation use separate time periods, and the final test period is used once.
- Thresholds and temperature scaling are fit on validation periods only.
- The strategy is fixed before the live window. Nothing is tuned on development-phase or scored-run P&L.
- Changes during the run are made only on non-P&L evidence (schema errors, latency, calibration drift), each through a logged version event.

LLM memorisation (walk-forward alone does not fix this):
- A hosted LLM may already know how a historical catalyst played out. We evaluate the evidence step on events after the model's training cutoff.
- In historical tests we anonymise the ticker, company and date in the prompt, then check whether the model can still name the firm. Anonymisation can fail for mega-caps.
- We report pre-cutoff and post-cutoff results separately.
- We also check the decision model's pre-training cutoff.

Keeping overfitting small and visible:
- The model layer is small: one calibrated model and a few thresholds.
- Hypotheses are pre-registered with three outcomes: supported, not supported or inconclusive.
- The evidence-assisted model is compared with a no-evidence baseline at matched coverage.
- We report calibration for the cases that actually trade, with bootstrap confidence intervals, not only overall accuracy.

Token-versus-share risk: training labels come from the underlying shares, so we measure how far the tokens diverge from their shares, both off-hours and around corporate actions, using bStocks history since June 2026.

---

## Reproducibility plan — how can your run be rerun and verified?

Versions:
- Every build has a manifest hash covering:
  - the commit and dependency lockfile,
  - prompts and tool schemas,
  - configs, risk parameters and thresholds,
  - model checkpoint hashes or API snapshot IDs.
- Every component checks its hash against the active registered version before it runs:
  - the agent, signer, uploader, tools and reconciler at start-up,
  - the agent again before every order.
- The challenge branch is protected: no force-pushes and no rewrites.

Decision records, written before signing:
- **Inputs:** hashes and pointers to the inputs, with source and retrieval times.
- **Evidence step:** every tool call and result, and the full model requests and responses, including reasoning summaries.
- **Checks:** claim-verification results, the probability vector, and the outcome of each selection, policy and risk check.
- **Order:** a short reason summary, the intended order and the quote ID.
- **Appended after execution:** the transaction or order hash, fill, fees and gas, or an abort status.
- HOLD and abstain decisions are logged too, so inactivity is traceable.

Logs:
- The journal is append-only, sequence-numbered and hash-chained.
- It is uploaded daily, and after any incident, to write-once storage with the chain head, and anchored hourly.
- The hash chain shows tampering after anchoring. Completeness is shown separately:
  - by reconciling every on-chain transaction, execution record, decision record and version event, including non-trade balance changes,
  - by gaps in sequence numbers and heartbeats.

Rerun:
- The deterministic layers (verification rules, selection, policy, risk and execution planning) re-run on the recorded model outputs and must reproduce the same decisions.
- The point-in-time store lets the whole pipeline be re-run on the original inputs.
- Self-hosted model weights are archived with hashes. For hosted models, the complete request/response records stand in for weights.
- The evidence step's reasoning is captured in readable form. The decision model's output is its probability vector plus the policy trace.

Recovery:
- A payload is signed at most once per decision.
- Recovery uses observable identifiers: nonce, quote ID, order hash and transaction hash.
- An ambiguous execution stays unresolved and blocks conflicting orders until the chain settles it.

Onboarding gates:
- **Eligibility:** identity and access.
- **Operating prerequisites:** e.g. the eligible instruments list. Affected live actions stay disabled until each is resolved.
- **Engineering unknowns:** each gets a documented fallback recorded in the manifest.

---

## Team capability + intended scope

Team (4):
- Yao Zhu — **Agent/Model lead:** evidence loop, verification, decision model and calibration. 
- Isaac — **Markets/Data/Risk lead:** point-in-time data, labels, risk and regime governors, hypothesis tests. 
- Keith — **Execution/Security lead:** Web3 API adapter, signer allow-list, recovery and reconciliation. 
- Keegan — **Platform/Audit lead:** versioning, manifests, logging, uploads, monitoring. 

What we deliver (v1.0):
- a bounded evidence loop (≤ 3 tool types) with claim verification,
- thesis memory with falsifiers,
- an event-calendar planner,
- a calibrated decision model with a selection rule,
- rule-based regime and risk governors,
- a restricted signer,
- version gating, audit logging, reconciliation and recovery.

Anything not working by Oct 22 is cut, not delayed. The deployment is one primary runtime plus a fenced cold standby.

Plan:
- **Sep 30 – Oct 4:** typed interfaces, mock adapters, risk engine, hash-chained trace log, CI, and the post-cutoff evaluation set.
- **Oct 5 – 10:** onboarding — identity, dev wallet, Developer Portal, repository, declarations; read the official rules and close open questions.
- **Oct 12 – 18:**
  - real Web3 API adapter,
  - a minimum-size buy and sell generated by versioned code,
  - reconciliation, heartbeat and trace uploads,
  - week-one checkpoint.
- **Oct 19 – 26:**
  - full pipeline for 5+ days including a weekend, at minimum size,
  - recovery drills, soak and fault injection,
  - cost model and hypothesis readouts,
  - cut line Oct 22,
  - self-check evidence.
- **Oct 27 – 29:** fresh final wallet, frozen v1.0 manifest, registered safe-mode build, integrity check.
- **Oct 29 – Nov 12:** scored run with daily uploads and reconciliation. Improvements are versioned releases, at most one a day, each run in shadow first.
- **Nov 13 – 20:** audit bundle — version history, manifests, complete logs, model I/O and thinking output.
