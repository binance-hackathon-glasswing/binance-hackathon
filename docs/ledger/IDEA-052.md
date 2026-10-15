### IDEA-052 — TimesFM forecaster in the decision block: plan, red team and adoption design
- Date / author: 2026-10-15 SGT / Yao Zhu with Claude Code (idea raised by a friend of the team)
- Status: open (recommended, not decided). Deferred until Gate A passes. No code, nothing pre-registered, nothing run.
- What: decide whether Google's TimesFM, a pretrained time-series forecasting model, should feed LARP's decision block. This entry red-teams a straightforward adoption plan, then gives the design to use if the team adopts it.
- Why it might help: it forecasts each name's future price (a point and quantiles) from its own history, with no training on our side. It could restore part of the declared model layer (DEV-01: no decision model ships) and give the policy a volatility or direction input it lacks today.
- Cost / risk: no evidence of a trading edge, and no time to get any before the Oct 22 freeze. Host memory and CPU risk on the t3.small primary. A licence trap in the newest version. A new principal model to declare, log and hand over (F-49 (c)).
- Links: DEV-01, DEV-02, DEV-03, DEV-06, DEV-07, DEV-08; IDEA-012, IDEA-018, IDEA-034, IDEA-035, IDEA-037, IDEA-046, IDEA-051; EXP-003, H-03, I-38, I-66, Q-30; F-30, F-31, F-48, F-49, F-61, F-71, F-96, F-97, F-115, F-117; G-03, G-04, G-05, G-12, G-47; DR-08, DR-19; GAP-69.

**Bottom line.** v1.0 ships without TimesFM, not even in shadow. After Gate A, run a small offline research track (§6.1). The only use admissible for v1.0 is a fail-open, risk-only cap on buy capacity (§6.2), and only if every gate in §6.3 passes by Oct 20. That is unlikely. Entry ranking, forecast exits, forecast sizing and LLM context are rejected for v1.0.

## 1. What TimesFM is (checked 2026-10-15)

| Version | Released | Size | Weights licence | Notes |
|---|---|---|---|---|
| 2.5 | 2025-09-15 | 200M parameters, F32 safetensors (≈ 0.8 GB [ESTIMATE: 200M × 4 bytes]) | Apache-2.0 (Hugging Face tag; LICENSE file not yet read) | Context up to 16k. Optional 30M quantile head gives continuous quantiles to a 1k horizon. Covariates (XReg) added back 2025-10-29. |
| 3.0 | Aug 2026 | ≈ 330M | **TimesFM Non-Commercial License v1.0.** The README says non-commercial, non-production use only; commercial use goes through Google Cloud (BigQuery ML). [README summary; licence text not read] | Point forecast plus quantiles 0.1–0.9; native past and future covariates. |
| 1.0, 2.0 | archived | — | — | — |

- Code is Apache-2.0. The README says "not an officially supported Google product".
- Pretraining data (2.5 and 3.0 model cards): GiftEvalPretrain, Wikipedia pageviews to Nov 2023, Google Trends top queries to end-2022, and synthetic data. None of it is finance-specific. GiftEvalPretrain's contents were not checked. All of it predates the bStocks (Jun–Jul 2026), so the model cannot have memorised our token series.
- It forecasts one series from its own past, plus optional covariates. It knows nothing about filings, earnings dates or news unless they are given as covariates.

## 2. Evidence on stock returns and risk
Grade: [PRIMARY], the papers themselves. Abstracts and summaries only; full texts not read; checked 2026-10-15.
- **Rahimikia, Ni & Wang 2025** (arXiv 2511.18578). Daily excess returns across global markets: "off-the-shelf pre-trained TSFMs perform poorly in zero-shot and fine-tuning settings". Models pre-trained from scratch on financial data do better.
- **Noguer i Alonso & Franklin 2026** (arXiv 2606.27100). Five US large caps, GOOG among them:
  - TimesFM-2.5 and Moirai-2.0 had the best average ranks.
  - Gains over a random walk were "small and sparse". The Diebold–Mariano test was significant only for Chronos on AMZN and Moirai-2.0 on GOOG.
  - Conclusion: useful priors for low-data forecasting, not reliable sources of statistically robust alpha.
- **Goel et al. 2024** (arXiv 2410.11773). Value-at-Risk on the S&P 100 with a 512-day context:
  - Zero-shot use "is not optimal".
  - TimesFM fine-tuned daily on a rolling window has the best coverage ratios, and is on par with GAS on quantile loss.
- **Goel et al. 2025** (arXiv 2505.11163). Realised volatility: zero-shot is a reasonable baseline, and incremental fine-tuning beats HAR, ARFIMA and RGARCH.
- **Fu, Hirano & Imajo 2024** (arXiv 2412.09880). Base TimesFM was poor on raw prices; continual pre-training on a proprietary price dataset improved mock trading. Its weights (`pfnet/timesfm-1.0-200m-fin`) state no licence, and the training data is undisclosed.
- **Ours:**
  - Hourly token moves mostly bounce: autocorrelation −0.08 to −0.34, Roll spread 13–56 bp (IDEA-012, IDEA-018).
  - Break-even is ≈ 20 bp per side (IDEA-035 §10).
  - A discretionary round trip needs ≥ 45–135 bp of edge (IDEA-018).
  - Buy-the-dip is unsupported; momentum mode is off and untested (IDEA-035).

**Reading:** for direction, there is no robust zero-shot evidence. For risk (volatility, VaR), there is some evidence, mostly after fine-tuning.

## 3. Where it could plug in
Today's path:
1. ContextBuilder builds the snapshot: market observation, token session closes (I2/B3), assessments and portfolio.
2. `StrategyPolicy.decide` runs `EQUAL_WEIGHT`: four names at 20%, cheapest round trip first, red-flagged names skipped.
3. `plan` applies the caps, the 25%/90% hard trims, the daily-loss and 8% stops, the 12% deep cut and the flatten window.
4. Execution.

No step uses a price forecast.

| Hook | Use | Today |
|---|---|---|
| H1 Entry choice | Rank names by forecast return instead of cost | `policy.py` ranks by `measured_roundtrip_bps` |
| H2 Exit | Sell a held name on a forecast fall (DEV-07's "confident DOWN signal") | No forecast exit |
| H3 Sizing | Forecast volatility → 1% ÷ (2σ₅) (DEV-03) | `DECLARED_EXPOSURE` exists, unused |
| H4 Exposure cap | Forecast volatility lowers `regime_gross_weight` (buy capacity only) | Static profile value |
| H5 LLM context | Forecasts in the assessor's prompt | Assessor sees EDGAR evidence only |
| H6 Quote sanity | Flag a quote outside the forecast band | Impact and slippage checks |

## 4. Plan v0 (the straightforward version, before the red team)
1. Run TimesFM 3.0 (the latest) on hourly kit candles for all five names every round, with a 5-session horizon.
2. H1: hold the four names with the highest forecast 5-session return after cost; skip names with a negative median.
3. H2: sell a held name when its median forecast is below −X%.
4. H3: size by forecast volatility.
5. H5: show the forecasts to the assessor model.
6. Backtest on token history since June, tune X and the context length, and ship in v1.0 by Oct 26.

## 5. Red team of plan v0
**Severity:**
- **Block**: must not ship as written.
- **High**: needs a design change.
- **Med**: handle in the design.

### 5.1 Rules, audit and rights
- **R1 Block: licence.**
  - The 3.0 weights are non-commercial and non-production. A live run with real funds for a prize is plausibly production use.
  - F-71 requires rights to every model, and F-66 disqualifies unauthorised components.
  - So only 2.5 (Apache-2.0) is usable, with its LICENSE file read and hashed at a pinned revision. This is the Laya lesson (Q-30): a licence tag is metadata only.
  - The pfnet finance fine-tune is out: no stated weight licence and undisclosed training data (I-38).
  - BigQuery ML would add a paid cloud provider, against the zero-paid-budget choice (IDEA-030).
- **R2 Block: freeze.**
  - F-117: the build registered at activation runs unchanged. Profile values are frozen Oct 22 and code Oct 26.
  - Plan v0 tunes X and the context length on dev-phase data, which ledger rule 5 forbids. Nothing can be fixed during the run.
  - Any TimesFM behaviour must also be in the rehearsal build from Oct 21, so the decision is due ≈ Oct 20.
- **R3 High: manifest and F-49 (c).** The model would be a principal service. It needs:
  - a services-list entry (F-61);
  - pinned weight hashes (G-12) and archived weights (G-47);
  - the full input and output of every forecast, kept.

  Plan v0 has none of these.
- **R4 High: deviation honesty.**
  - The proposal declared "a bidirectional encoder with a typed decision head, which we fine-tune on our own point-in-time labels" (DEV-01). A zero-shot forecaster is not that.
  - It needs its own deviation row. Calling it "our calibrated decision model" risks "material misrepresentation" (F-48).
- **R5 Med: round logs.**
  - A forecast that affects a decision is part of that round's `input` (F-99).
  - `cot` states the deterministic rule path (F-106 (a), Q-36), never invented "model reasoning".
  - Hourly series for five names in every round add tens of KB per round [ESTIMATE]. That is within the limits (64 KB chunks, ≤ 8 MB per log) but wasteful.
- **R6 Med: replay.**
  - Same-head replay (DR-19) needs identical bytes, and CPU floating-point results can differ across machines and thread counts.
  - So forecasts must be recorded port outputs: quantised before use, and read back from the record on replay.

### 5.2 Evidence and statistics
- **S1 Block: no evidence of a directional edge.**
  - Rahimikia 2025 and Noguer i Alonso 2026 find no robust zero-shot alpha on large-cap daily returns, and our five names are among the most heavily traded stocks there are.
  - H1/H2 need 45–135 bp per round trip. With 5-session volatility of ≈ 5.6–9% (assuming 2.5–4% daily), that means an information coefficient (IC) of roughly 0.05–0.25 [ESTIMATE].
- **S2 Block: it cannot be validated in time.**
  - By Oct 21 there are ≈ 100 US sessions of token history for NVDAB, TSLAB and MSFTB (since ~June, E-02) and ≈ 70 for GOOGLB and SKHYB (since mid-July) [ESTIMATE].
  - After warm-up, overlapping 5-session horizons and five correlated tech names leave roughly 20–40 independent observations. The standard error of an IC is then ≈ 1/√n ≈ 0.16–0.22, so only an IC above ~0.35 would show.
  - Even 1-session horizons (≈ 100–150 effective observations) need an IC of about 0.2.
  - A plausible zero-shot IC is 0–0.05, so the result is INCONCLUSIVE with near certainty, which grants no authority (IDEA-034).
- **S3 High: hourly data is mostly bounce.**
  - With negative hourly autocorrelation and 13–56 bp Roll spreads (IDEA-012, IDEA-018), an hourly forecaster learns mean reversion that costs more than it earns.
  - Off-hours prices are derived (`tokenPrice` = `referencePrice` × ratio, IDEA-018), and candles exist only for periods with trades (F-95), so the series is irregular.
  - If anything is used, use US-session closes (I2/B3).
- **S4 High: it is a black-box momentum filter.**
  - Univariate forecasts from price levels mostly extrapolate the recent trend.
  - `PRICE_MOMENTUM` is the same class of signal, and it is off and untested by team decision (IDEA-035).
  - Plan v0 adds opacity, not information. The edge is meant to come from the information pipeline (F-32).
- **S5 High: turnover.**
  - H2 exits and H1 re-ranking create the round trips that the equal-weight book avoids by design ("never sell on drift", IDEA-037).
  - Forecasts that flip around zero cause whipsaw, and at 200 USDT, gas alone is about the whole premium (IDEA-018).
  - Ranking by forecast also stops the policy choosing the cheapest names.
- **S6 Med: calendar-blind.**
  - It does not know earnings dates. TSLA, MSFT, GOOGL and SK Hynix usually report in late October, and NVIDIA in mid-to-late November [UNCONFIRMED].
  - Some of those jumps fall just before or inside the run, where its quantile bands are too narrow.
- **S7 Med: quantiles are not calibrated zero-shot** (Goel 2024). Using q10 as a stop or as a volatility input needs a calibration check first.
- **S8 Med: forking paths.** Context length, bar size, horizon, normalisation and thresholds are too many choices for about 30 effective observations.
- **S9 Med: population transfer.** The papers study exchange-traded shares; we trade 24/7 RFQ tokens.

### 5.3 Engineering and operations
- **E1 High: host memory.**
  - The primary host is a t3.small: 2 GiB RAM and standard CPU credits (IDEA-046).
  - 2.5 needs ≈ 0.8 GB of weights plus PyTorch: ≈ 1.1–1.7 GB at peak, since loading can briefly hold two copies [ESTIMATE, unmeasured]. 3.0 needs more.
  - An out-of-memory kill of the runtime during the run cannot be fixed (F-117).
  - A t3.medium costs ≈ +$15–20/month [ESTIMATE; check the official Sydney price]. That fits the $100 credit cap only with Yao Zhu's OK.
- **E2 High: CPU credits and latency.**
  - Inference every round burns burst credits. When they run out, the whole host drops to its baseline speed, which slows the ~30 s RFQ quote path (F-96).
  - The model must run off the critical path.
- **E3 Med: dependencies.**
  - `torch==2.14.1` is already pinned, but no code imports it (a Laya leftover).
  - TimesFM adds its own package, pinned by commit.
  - The host bundle must carry a CPU-only wheel and the weights, outside Git.
- **E4 High: failure semantics.**
  - Plan v0 does not say what happens when a forecast fails.
  - A gate that fails closed blocks all buys, leaving the book mostly in cash, which F-115 penalises.
  - A forecast in the exit path could block safety exits.
- **E5 Med: interfaces and people.**
  - A forecast input is a new interface beside I1–I8, which both owners must agree on.
  - It touches Keith's policy and Keegan's runtime during Gate A/B work, while capacity is already short (IDEA-011 X1).
- **E6 Med: H5 breaks the assessor's role.**
  - The assessor rates verified EDGAR claims only (D-11), with three tools (DEV-08).
  - Price forecasts in its prompt invite calls on direction.

### 5.4 Strategy
- **P1 Med: weak model-layer claim.** "Larger spend and higher call volume earn nothing on their own" (F-31). A zero-shot drop-in, with no post-training, is a weak "model-layer" claim (F-30).
- **P2 Med: H6 adds nothing.** A 5-session band is far wider than any bad quote, and the impact and slippage checks already catch bad quotes. Rejected.

## 6. Revised plan

### 6.1 Recommendation
1. **v1.0 (the scored run) ships without TimesFM, not even in shadow.**
   - Reasons: S1 and S2 (no edge, and no way to validate one); R2 (the decision would be due ≈ Oct 20 while Gate A has slipped); E1 and E2 (host risk, with no fix allowed during the run).
   - Shadow inside the scored build adds host risk and gives nothing an offline replay cannot. The model is zero-shot and its training data ends in 2023. Running it later on the recorded inputs, cut at each decision time, gives the same forecasts a live shadow would have given. Only latency and availability evidence would be missing.
2. **After Gate A passes, run a small offline research track.**
   - Laptop only, recorded captures only, at most 2 person-days, one owner, pre-registered as a new experiment.
   - Primary question: does TimesFM 2.5 forecast the 1- and 5-session volatility of the five tokens better than a simple EWMA?
   - Secondary, descriptive only: directional IC.
   - Expected outcome: INCONCLUSIVE.
3. **The only use admissible for v1.0 is H4, a risk-only exposure cap** (§6.2), and only if every gate in §6.3 passes by Oct 20.
   - A team that wants volatility-aware exposure should start with EWMA: it is transparent and has no model and no host risk.
   - TimesFM replaces EWMA only if it beats it (G3).
4. **Rejected for v1.0:** H1, H2, H3, H5 and H6. After the competition, H1–H3 could be reconsidered with:
   - rights-cleared long histories;
   - fine-tuning or finance pre-training;
   - a walk-forward test with enough independent observations;
   - an after-cost policy comparison whose lower bound is above zero (IDEA-034).

### 6.2 Adoption design (only if adopted: H4, risk-only)
- **Model.**
  - TimesFM 2.5, 200M, PyTorch: `google/timesfm-2.5-200m-pytorch`, pinned by Hugging Face revision.
  - SHA-256 of each weight file and of the LICENSE file. The `timesfm` package pinned by commit. CPU-only PyTorch.
  - Never 3.0, and never a third-party fine-tune.
- **Input.**
  - The US-session close series the policy already receives (`PriceSeries.v1` from I2/B3 `token_sessions`), as log returns over the full available history (~70–100 sessions).
  - No forecast (`INSUFFICIENT_HISTORY` or `GAPPED`) when the history is shorter than N sessions or any of the last N is missing [N frozen in the pre-registration].
  - No hourly bars, no fill-forward, no Ondo splice.
- **Output: `PriceForecast.v1`.** Fields:
  - symbol; cutoff (the session close used); `available_at`;
  - input-series hash; model ID, weight hashes and code commit; context length;
  - horizons 1 and 5 sessions; quantiles 0.1–0.9 of the cumulative log return, quantised to 1e-6; the derived volatility;
  - status: `OK`, `INSUFFICIENT_HISTORY`, `GAPPED`, `FAILED`, `TIMEOUT`, `QUANTILE_CROSSING` or `NON_FINITE`;
  - runtime and peak memory.
- **Timing.**
  - Once per US session, after the 16:00 ET bar is available.
  - Its own systemd unit (`larp-forecast`): `Nice=19`, `MemoryMax` set from the G2 measurement, a hard timeout, one thread.
  - It writes forecasts to the database as recorded observations. Rounds read the latest forecast and never call the model.
- **Consumption (H4 only).**
  - ContextBuilder accepts a forecast only if:
    - `available_at` ≤ the decision cutoff (G-05);
    - it is no older than the feature age (four calendar days, `config/strategy/LIVE.md`);
    - its status is `OK`.
  - Policy: `regime_gross_weight` is 80%, or a lower frozen value L (e.g. 60%) when the book's forecast 5-session volatility is above threshold T [T and L frozen in the profile with provenance].
  - This limits new buys only: a regime weight below 80% never forces sales below the 90% hard line (IDEA-037 §2).
  - It never raises any limit above the declared values, never creates a sale, and never touches exits, the drawdown ladder, red flags or the flatten window.
- **Failure.**
  - A missing, stale or failed forecast leaves the static `regime_gross_weight` (today's behaviour), with reason `FORECAST_UNAVAILABLE` in the decision record.
  - More than k consecutive failures write an incident record but cause no HALT: a forecast is not a safety input.
- **Logs.**
  - Decision record (G-04): the forecast's ID, hash and status, and the value used.
  - ai-seeds `input`: a forecast summary (symbol, quantiles, status, hash). The full model input and output go to the local journal (F-49 (c), G-06).
  - `cot` is a plain rule statement, e.g. "Forecast 5-session volatility 9.1% is above the 8.0% threshold, so new buys are capped at 60% gross" (F-106 (a)).
- **Replay.** Forecasts are recorded port outputs: replay reads the record and never recomputes (DR-19). A separate offline check recomputes them and compares within a tolerance.
- **Manifest and declarations.**
  - `config/release/services.v1.json`: TimesFM 2.5, self-hosted, Apache-2.0, with its revision and hashes.
  - `config/release/deviations.v1.json`: a new row saying the model layer is a pretrained zero-shot forecaster used only to lower buy capacity, not the declared fine-tuned decision model.
  - A licence-register row with the LICENSE capture hash.
  - Weights archived with hashes for the F-49 (c) handover (G-47).
- **Regime governor.** I-66 adopts rule-defined regimes and keeps learned regime models in shadow. H4 is a frozen rule on a forecast input, and G3 is the validation that I-66 asks for. Without G3 it conflicts with I-66. This belongs to the EXP-003 / H-03 regime-gating thread.
- **Ownership** (nominal, following the IDEA-024/038 areas):

  | Part | Owner |
  |---|---|
  | Model and forecast unit | Yao Zhu |
  | Policy hook and profile values | Keith |
  | ContextBuilder, unit, manifest and replay | Keegan |
  | I2 candle supply | Isaac |

  The new interface needs both owners' agreement (DEPLOYMENT_BUILD.md).

### 6.3 Gates (all must pass, in order, by Oct 20 for v1.0)
- **G0 Schedule.** Gate A passed and Gate B on track (signer on by Oct 20). If either slips, the v1.0 track stops and TimesFM stays offline research.
- **G1 Rights.** The LICENSE file at the pinned revision is read, captured and hashed; it is Apache-2.0; the register row is written.
- **G2 Host.** On a t3.small with standard credits and every LARP service running:
  - peak memory ≤ [X] MB;
  - a run for five names takes ≤ 60 s at p95;
  - a 72 h soak has no out-of-memory kill, no crash and no CPU-credit exhaustion;
  - three runs on the same host give bit-identical outputs after quantisation.
- **G3 Forecast quality** (a pre-registered experiment, frozen before running):
  - Walk-forward on recorded session closes; each forecast uses only sessions closed before its origin.
  - Target: realised 1- and 5-session variance. Loss: QLIKE.
  - Baselines: EWMA (λ = 0.94) and trailing 20-session realised variance.
  - Supported if TimesFM's mean QLIKE beats EWMA's at both horizons, with a one-sided block-bootstrap 95% interval excluding zero. Not supported if EWMA is better. Inconclusive otherwise.
  - Inconclusive means not adopted.
- **G4 Effect.**
  - Replay the decided `EQUAL_WEIGHT` policy over the same history with and without H4.
  - Report gross exposure, turnover, costs and maximum drawdown.
  - Adopt only if turnover and cost do not rise and the cap fires on no more than [y]% of sessions [frozen beforehand].
  - No tuning on P&L (ledger rule 5).
- **G5 Integration.**
  - Tests for the forecast unit, the ContextBuilder freshness rules, the fail-open path, logging and replay.
  - Linux CI green.
  - Included in the rehearsal build from Oct 21.

### 6.4 Timeline

| When | Step | Note |
|---|---|---|
| Now until Gate A | Nothing | Gate A comes first |
| Gate A + 1 day | Pre-register G3 and G4; read and hash the 2.5 LICENSE | Docs only; experiment ID from Keegan |
| + 2–3 days | Offline run on recorded captures, on a laptop; record the result | Code committed before it runs (ledger rule 2) |
| Oct 20 | Team decision: adopt H4 (every gate passed) or not | Expected: not adopted |
| Oct 21–26 | If adopted: in the rehearsal build | Otherwise nothing |
| Oct 22 / Oct 26 | Profile freeze / code freeze | F-117 |
| After Nov 12 | Optional forward evaluation on the run's own recorded data | Never during the run on the agent's API key (shared rate limits, F-97) |

## 7. Red team of the revised plan
- **RR1:** G2–G4 cannot realistically all pass within ~5 days while Gate A has slipped. Accepted: the default outcome is "not adopted", and the research track is the real deliverable.
- **RR2:** an inconclusive G3 tempts a "ship it anyway in shadow" compromise. Rejected in §6.1: shadow adds risk and no information that an offline replay lacks.
- **RR3: H4 lowers invested exposure.**
  - F-115 says "if you don't trade at all? That's definitely not what this competition is about", and the team target is 80% invested.
  - A cap that fires often turns the book partly into cash. G4's [y]% ceiling bounds that, and L must stay well above "mostly cash".
- **RR4: EWMA may make TimesFM pointless.** That is what G3 tests. If EWMA is as good, use EWMA or nothing; that is a separate decision under EXP-003, not this entry.
- **RR5: new code in the audited build.** A forecast unit on the primary host is audited code even when it fails open (F-61; F-48 "no version gaps"). It is committed, manifested and hashed like everything else, and the fail-open path is itself tested.
- **RR6: rate limits.** Research forecasts run during the scored run on the dev API key would compete with the agent for rate limits (F-97, HTTP 429). Run them after the run on recorded data, or with a separate key.
- **RR7: replay fidelity.** An offline replay equals a live shadow only if it uses the exact recorded inputs: the same candle capture and the same cutoff. Use the captured I2 documents and their hashes, not a fresh download.

## 8. Decisions for the team
- **T1:** accept "v1.0 without TimesFM" (recommended).
- **T2:** run the offline research track after Gate A? Name an owner and a time box.
- **T3:** if T2 is yes, freeze N, T, L, k, X and y, and get an experiment ID from Keegan before anything runs.

## Sources (checked 2026-10-15)
- TimesFM repository and README: https://github.com/google-research/timesfm
- TimesFM 2.5 model card: https://huggingface.co/google/timesfm-2.5-200m-pytorch
- TimesFM 3.0 model card: https://huggingface.co/google/timesfm-3.0-pytorch
- Rahimikia, Ni & Wang 2025: https://arxiv.org/abs/2511.18578
- Noguer i Alonso & Franklin 2026: https://arxiv.org/abs/2606.27100
- Goel et al. 2024 (VaR): https://arxiv.org/abs/2410.11773
- Goel et al. 2025 (realised volatility): https://arxiv.org/abs/2505.11163
- Fu, Hirano & Imajo 2024: https://arxiv.org/abs/2412.09880; weights repository https://github.com/pfnet-research/timesfm_fin
