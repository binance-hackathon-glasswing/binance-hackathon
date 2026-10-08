# IDEA-008 — News semantic model + time-series signal model → trained decision model

- Date / author: 2026-10-08 / user proposal, documented by Codex
- Status: open — user-proposed, not adopted; no training, backtest or live results
- What: use one model for semantic analysis of historical news articles with timestamps, a second model for historical price/volume analysis and trading signals, and a third decision model trained on their aligned outputs plus portfolio/risk context.
- Why it might help [HYPOTHESIS]: news captures company/sector events while price/volume captures market response and regime; a trained fusion model could learn when the inputs agree, conflict or warrant abstention. More models do not establish an edge; this must beat the relevant baseline after costs.
- Cost / risk: additional corpus/rights work, two upstream training pipelines and one fusion pipeline, latency and audit surface. Main risks are historical-news hindsight, in-sample upstream signals contaminating fusion training, sparse aligned events, correlated sources, and share-to-token transfer. Build effort and compute budgets have not been estimated.
- Links: IDEA-001 §§11–14; IDEA-002; IDEA-007; EXP-001; D-03/D-06/D-07/D-08/D-09/D-10; I-37/I-67; F-20/F-49/F-61/F-63/F-71; G-03/G-05/G-10/G-12/G-42; GAP-06/07/21/22/23/24/25/56/57/58/59/60

## 1. Proposed data flow and model contracts

```text
Licensed historical article text + demonstrated availability timestamp
  → Model A: semantic/news analysis → structured event features/news signal
Historical price/volume windows available at the same decision time
  → Model B: time-series analysis → calibrated quantitative trading signal
Both aligned outputs + position/cost/risk context
  → Model C: trained decision model → probabilities/action preference/abstention
  → deterministic selection and risk gates → eligible trade intent or HOLD
```

Both upstream outputs reach Model C. Passing only Model B's signal would discard the proposed semantic input. A/B supply evidence or signals; they do not execute orders. Models, schemas and action mapping remain to be chosen.

| Model | Inputs at decision time `t` | Proposed outputs | Training data / targets |
|---|---|---|---|
| A — semantic/news | Exact eligible article version; company/sector identity; original publication/availability timestamps; prior context available by `t` | Entity relevance, event type, reported facts/numbers, signed impact or sentiment, uncertainty, source references; `as_of`, version and missingness. Novelty requires prior context | Wikinews/EFF original licensed text; conditional FTC/DOJ text; GDELT metadata as supporting features. Human/rule-labelled event/relevance/severity targets; teacher-generated targets only after teacher/output rights are cleared. Future returns must not appear in the prompt or extractive labels |
| B — time-series | OHLCV/returns/volatility windows ending by `t`, with missingness, session/currency/instrument and corporate-action treatment | Forecast probabilities or expected-return/risk estimate, confidence and a trading-signal score; `as_of`, horizon, checkpoint and quality flags | Kit token candles first; conditional Kaggle share series for longer history. Labels are matured future outcomes with frozen horizon, costs and return convention; adjusted prices and preprocessing require point-in-time review |
| C — decision/fusion | A features/news signal + B signal, both available by `t`; positions, cash, costs, market state and risk context | Calibrated directional/outcome probabilities and selection score, mapped by a frozen policy to long/hold/exit or abstain. REDUCE only if D-06 defines it | Chronological out-of-fold A/B predictions joined to subsequently matured outcomes; use a frozen target definition, not a model's own recommendation as supposed ground truth |

The submitted five-US-session horizon is a candidate to reconcile with D-06, not a newly frozen training parameter. Define whether labels refer to underlying shares or actual tokens; do not mix them silently. Sector-level news must be tagged as sector exposure, not invented company-specific events. Unknown/missing upstream inputs need explicit masks and a predeclared fallback rather than forced signals.

## 2. Scope and relationship to existing work

- The requested research targets are NVDAB, GOOGLB, SKHYB, TSLAB and MSFTB; a free candidate source need only cover some of them. Underlying-share proxies NVDA, GOOGL, TSLA and MSFT are not the traded bStocks. GOOG and GOOGL are different share classes; Korean SK Hynix `000660` and the US SKHY ADR need separately verified mapping, currency, ratio and availability.
- IDEA-001 §11's kit-first decision still governs acquisition. The external-source research below does not itself reopen collection, approve Kaggle rights or replace the adopted stack. GAP-56/57/60 cover team decisions and declaration implications.
- IDEA-007 proposes severity/veto training instead of a return-predicting decision model. This fusion idea is an alternative for discussion; no claim that both have been adopted. Existing baseline/default choices (D-07/D-08), deterministic risk limits and eligible-instrument rules remain in force.

## 3. Free training sources and rights status

Research record: source cards, licence policies and selected relevant article pages were checked in this conversation on 2026-10-08. This establishes the reported published terms and example relevance, not completeness of downloaded corpora, upstream clearance or prediction quality. The consolidated source register is [IDEA-001 §14](IDEA-001.md#14-free-training-source-register-and-three-model-follow-up-2026-10-08-codex).

### 3.1 Price/volume time series

| Source | Coverage / proposed use | Terms / status |
|---|---|---|
| [Kit Web3 candles and kit-named sources](IDEA-001.md#11-data-source-priority-kit-sources-first-2026-10-07-syz-drafted-with-claude) | Actual bStock token OHLCV for all five; Web3 since launch; Ondo history for four US names back to June 2025. Train exploratory token signals and measure transfer/costs with forward snapshots | Existing kit-first source position (F-95/F-104; IDEA-001 §13). Short history and correlated market period limit validation; independent share history is absent. api.binance.com through the kit-named market-data skill; data.binance.vision excluded |
| [Larxel S&P 500 stocks, Kaggle](https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks) | Daily underlying OHLCV/adjusted close; NVDA, GOOGL, TSLA, MSFT. Observed overall range 2010-01-04–2024-12-20; exact per-stock ranges unverified. Version 1023, last update 2024-12-23 SGT, despite the daily-update title | Published CC0 1.0; description cites FRED and yfinance. **Candidate only: upstream rights unresolved.** CC0 cannot waive rights the uploader does not hold. Review per-column provenance, avoid restricted FRED features, inspect missingness and adjustments |
| [Sinan tech stocks, Kaggle](https://www.kaggle.com/datasets/sinankr/tech-stocks-dataset) | Daily 2010–2024 prices/features; NVDA, TSLA, MSFT and GOOG. GOOG must not be labelled GOOGL; SKHY coverage not established | Published CC0 1.0; Yahoo Finance API provenance. **Candidate only: upstream rights unresolved.** Inspect derived/macro features and forward-fill/interpolation before accepting any column |

No Kaggle source here is a cleared replacement for the licensed-price requirement. Price-level, return-label, split/dividend and token/share basis checks are still required. [CC0 legal code](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en) permits reuse within the affirmer's rights and preserves third-party rights; downloading for free is not proof of a complete rights chain.

### 3.2 Archived text: starter articles and licence basis

These are starter examples of company/market mentions, not a sufficiently sized training corpus. Month-only dates below are browsing identifiers, not valid precise training timestamps. Preserve authors, original URL, licence/version and excluded third-party passages. Training and commercial signal use are interpretations of the licences' reuse/adaptation permissions; no separate explicit AI grant is claimed.

| Original text source and article | Publication identifier / relevance | Rights and conditions |
|---|---|---|
| Wikinews — [Google buys DoubleClick for $3.1 billion](https://en.wikinews.org/wiki/Google_buys_DoubleClick_for_%243.1_billion) | 2007-04-13; Google advertising/acquisition, also Microsoft context | Article notice CC BY 2.5; original Wikinews prose may be reused/adapted commercially with attribution. Third-party quotations/media are not automatically covered |
| Wikinews — [EU fines Microsoft $1.35 billion for non-compliance with antitrust decision](https://en.wikinews.org/wiki/EU_fines_Microsoft_%241.35_billion_for_non-compliance_with_antitrust_decision) | 2008-02-27; Microsoft software/antitrust | Article notice CC BY 2.5; same attribution and third-party exclusions |
| Wikinews — [Elon Musk emails tell Tesla employees return to office, or “assume you have resigned”](https://en.wikinews.org/wiki/Elon_Musk_emails_tell_Tesla_employees_return_to_office%2C_or_%22assume_you_have_resigned%22) | 2022-06-03; Tesla workforce/operations | Article notice CC BY 2.5; exclude or separately clear substantial quoted emails/publisher passages; original article licence alone is not a blanket licence to quoted material |
| EFF — [Google’s FLoC Is a Terrible Idea](https://www.eff.org/deeplinks/2021/03/googles-floc-terrible-idea) | March 2021; Google advertising/privacy | EFF original material CC BY 4.0 unless otherwise noted; attribution, licence link and change notices; separately clear or exclude non-original text/media |
| EFF — [With Windows 10, Microsoft Blatantly Disregards User Choice and Privacy: A Deep Dive](https://www.eff.org/deeplinks/2016/08/windows-10-microsoft-blatantly-disregards-user-choice-and-privacy-deep-dive) | August 2016; Microsoft software/privacy | Same EFF original-material CC BY 4.0 policy; editorial viewpoint/source type must be retained as features |
| FTC — [Statement regarding termination of NVIDIA’s attempted acquisition of Arm](https://www.ftc.gov/news-events/news/press-releases/2022/02/statement-regarding-termination-nvidia-corps-attempted-acquisition-arm-ltd) | 2022-02-14; Nvidia, semiconductors/M&A | Original US-government text has a US-public-domain basis; **conditional: international reuse for Singapore not established**; third-party attachments/media/marks excluded |
| FTC — [Inquiry into generative-AI investments and partnerships](https://www.ftc.gov/news-events/news/press-releases/2024/01/ftc-launches-inquiry-generative-ai-investments-partnerships) | January 2024; Alphabet/Google, Microsoft, AI/cloud | Same conditional FTC position; verify original publication time and exact retained text |
| DOJ — [Department of Justice prevails in landmark antitrust case against Google](https://www.justice.gov/opa/pr/department-justice-prevails-landmark-antitrust-case-against-google) | 2025-04-17; Google advertising/competition; current page updated 2026-04-14 | Public-domain basis unless otherwise indicated; **international scope unresolved**; preserve the original historical version rather than treating a later revision as available in April 2025 |

Primary licence policies: [Wikinews copyright](https://en.wikinews.org/wiki/Wikinews:Copyright), [EFF copyright](https://www.eff.org/copyright), [FTC website policy](https://www.ftc.gov/policy-notices/website-policy), [DOJ legal policies](https://www.justice.gov/legalpolicies). Wikinews policy: CC BY 2.5 from 2005-09-25 through 2024-12-15, CC BY 4.0 from 2024-12-16; earlier material public domain. Check article-specific notices. [CC BY 2.5](https://creativecommons.org/licenses/by/2.5/) and [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) allow commercial sharing/adaptation within licensed rights; [CC's AI guidance](https://creativecommons.org/faq/#artificial-intelligence-and-cc-licenses) explains how the existing permissions apply. Keep attribution/licence/change records for source material and any permitted redistribution; do not assume model-weight or audit-sharing obligations have been fully reviewed.

Wikinews archives to extend the examples: [Google](https://en.wikinews.org/wiki/Category:Google), [Microsoft](https://en.wikinews.org/wiki/Category:Microsoft), [Tesla Motors](https://en.wikinews.org/wiki/Category:Tesla_Motors). [EFF Deeplinks archive](https://www.eff.org/deeplinks) adds market/sector analysis. No adequately sized, cleared SK Hynix full-text corpus was verified; coverage can start with a subset of eligible names.

### 3.3 GDELT metadata and decision-model training rows

- [GDELT data archive](https://www.gdeltproject.org/data.html) and [terms](https://www.gdeltproject.org/about.html): free academic/commercial/government dataset use. Use organisation mentions, themes, tone and source URLs from its datasets, retaining attribution/link. GDELT-derived metadata can support A/C or article discovery; it is not a licence for full publisher text at those URLs. Exact company coverage is pending a corpus audit.
- Treat GDELT processing timestamps separately from original publication time; deduplicate syndication and common-release derivatives rather than counting them as independent confirmation (GAP-25).
- Model C's dataset is generated from cleared A/B inputs and chronological out-of-fold outputs plus matured labels. It is not a third downloaded dataset; the original source licences and checkpoint/provider output terms still apply. Store private training rows outside Git; commit only permitted manifests/schema and snapshot references/hashes (F-61).

## 4. Training, timestamp alignment and leakage safeguards

1. **Freeze sources first.** Record exact dataset versions/files, licence/policy versions and provenance; training, commercial/contest use, team access, retained snapshots, attribution and F-49 audit sharing must be covered. CC0 card verification and unresolved upstream rights are separate statuses. No training starts with unapproved inputs.
2. **Reconstruct actual historical availability.** Keep event time, original publication time/timezone/precision, revision time, actual retrieval time and demonstrated historical `available_at`. Hash each retained text version and record the source URL. A present-day fetch must remain a present-day fetch; it does not establish past availability. Define a conservative rule for date-only/uncertain records or exclude them. Resolve historical replay versus the live G-05 filter through GAP-24, without silently changing the live rule.
3. **Use only information available by `t`.** Article version and input candle windows must be complete and available before inference; use completed bars, not their later closes. Price preprocessing/adjustment factors, macro vintages and corporate actions need point-in-time review. Label return windows begin after the stated decision/processing latency; future prices enter only as matured labels.
4. **Generate chronological out-of-fold upstream signals.** In each rolling-origin fold, fit A/B and their preprocessors/calibrators only on earlier permitted data; generate their outputs on the later fold. Train C on these outputs, never on in-sample A/B predictions from rows used to fit those models. Prevent C's earlier training rows from receiving upstream models trained on later information. Keep independent calibration/threshold selection and a final block untouched until the design is frozen.
5. **Purge overlapping outcomes.** Apply a horizon-aware purge/embargo at chronological boundaries across all names and linked events. Group syndicated/duplicate events so copies do not cross splits. Do not random-split the event/price panel.
6. **Check pretrained-model hindsight independently.** Walk-forward fine-tuning does not erase a base model's knowledge of old events. Record A/B/C checkpoint cutoffs/provenance; use extractive fields for contaminated historical periods, run identity/hindsight probes, and require a defensible post-cutoff or forward evaluation slice (I-37/I-67). Unknown cutoffs or insufficient samples remain an unresolved gate.
7. **Retain audit evidence.** Log all three models' inputs/outputs, `as_of`, source/checkpoint hashes, horizon, confidence, missingness and policy/risk decisions. Source text retention and organiser disclosure must be licence-compatible; credentials remain excluded. No generated signal becomes an order without the deterministic freshness, cost, allowlist, position and risk checks.

## 5. Evaluation proposed before promotion to an experiment

- Compare the frozen relevant baseline with news-only, time-series-only and fused A+B→C variants on the same eligible population, decision times, risk limits and costs. Ablations must hold other policy choices fixed; changing architecture and policy together prevents attributing the effect to fusion.
- Report paired after-cost policy outcomes, drawdown, turnover, coverage/abstention, probability calibration and uncertainty under temporally dependent samples. Evaluate Model A's relevance/event extraction on human gold labels and Model B's calibration separately from final policy performance. Simulated outcomes must be labelled simulated, not realised fills.
- Numerical improvement, drawdown, calibration, minimum-sample and latency thresholds are **not yet pre-registered**. GAP-60 requires an EXP entry with exact chronological windows, snapshots/hashes, metrics, pass/kill/inconclusive criteria and code/config references, committed before any run. Insufficient evidence is inconclusive, not proof of edge.
- Only promote/adopt after rights, temporal integrity, instrument transfer and held-out performance/operational gates pass. Adoption must reconcile declarations/manifest/versioning; this note changes no live behaviour.

## 6. Remaining decisions and work

- GAP-58: source-rights chain, free access, exact stock coverage, attribution, retention and audit compatibility. Suggested leads: Markets/Data/Risk + Platform/Audit.
- GAP-59: source corpus/price quality and timestamp/version contract, overlapping dates and usable sample counts; token-versus-share mapping (GAP-22) and historical-replay semantics (GAP-24). Suggested leads: Markets/Data/Risk + Agent/Model.
- GAP-60: architecture adoption versus IDEA-007/current plan, checkpoint/provider licences and cutoffs, schemas/targets/costs, compute budget, out-of-fold pipeline and committed experimental criteria. Suggested leads: Agent/Model + Markets/Data/Risk + Platform/Audit. Named owners remain to be assigned (GAP-37).
- Completion evidence for this documentation task: IDEA-008 created, IDEA-001 §14 appended without rewriting prior research, ledger index updated and backlog narrowed/extended. No existing research criteria/results changed; no dataset acquisition, training, backtest, trade or adoption is claimed.
