# IDEA-001 — Event-driven news ingestion with local sentiment screening

- Date / author: 2026-10-04 / Keith (idea); Codex (research and assessment)
- Status: open — reasonable engineering hypothesis; trading benefit unvalidated
- What: Monitor an approved set of news sources and run a small local model when a new article is detected. The original suggestion is a model below 100B parameters for fast sentiment analysis and immediate trading; the proposed first evaluation is event-driven screening feeding LARP's existing verified evidence and decision pipeline.
- Why it might help: Reduce time spent discovering and screening relevant catalysts, avoid hosted-call overhead for easy classification, and reserve more expensive evidence processing for material or ambiguous events. These are hypotheses, not measured benefits.
- Cost / risk: Source access and retention rights, publication delays, article parsing, duplicate events, entity attribution, inference hardware and burst queues; sentiment can be correct while the trade loses after costs.
- Links: D-03, D-06, D-07/D-08; T-12; I-37/I-38/I-50/I-63; G-03–G-06, G-25/G-26, G-36, G-42, G-50–G-54; H-02 / [EXP-001](EXP-001.md); [incomplete work](../INCOMPLETE_WORK.md) GAP-21 and GAP-23–GAP-28.

## Assessment and relationship to the existing plan

**INFERENCE — reasonable to investigate, not sufficient to authorize immediate sentiment-driven trades.** Small models are credible for sentiment classification (R1/R2 below). Whether faster classification improves executable returns remains a separate hypothesis. A news article can describe higher profits while reporting results below expectations; a positive article may also repeat an event already reflected in quotes. Sentiment probabilities are not calibrated probabilities of a future price increase.

T-12 and the reference architecture already include local FinBERT sentiment/relevance screening. The additions here are explicit event-driven ingestion, measured latency budgets, and comparison of a local model with the hosted evidence step. G-36 already allows event triggers; this need not mean frequent trading.

This idea relates to §6.4, especially D-03's evidence-model choice. It does not settle D-03/Q-16: a sentiment classifier produces no reasoning trace, and local hosting alone does not establish that winner-deliverable requirements are met. A generated explanation must not be represented as a faithful internal reasoning trace. It also does not settle D-06's target or replace the calibrated decision model. Prompt collection, source verification, novelty, thesis memory and falsifiers remain separate requirements.

## Research evidence

Sources checked 2026-10-04. R-identifiers below are local to IDEA-001, not new global E/L IDs. No model, crawler or trading experiment was run.

| ID / grade | Source and scope checked | Finding and limitation |
|---|---|---|
| R1 — PRIMARY | [FinBERT paper](https://arxiv.org/html/1908.10063), methods and task description; [Prosus model card](https://huggingface.co/ProsusAI/finbert), model description | Financial sentiment can use a BERT encoder and classification head; the card exposes positive/negative/neutral scores. The paper describes BERT-base at 110M parameters. Sentence sentiment results do not establish full-article event understanding, local latency or profitable trading. |
| R2 — PRIMARY, research paper | [Reasoning or Overthinking (2025)](https://arxiv.org/html/2506.04574v1), methods, results and limitations | Direct classification outperformed explicit reasoning prompts in this Financial PhraseBank study. General LLMs handled some ambiguous or compositional examples better than the smaller out-of-domain classifier. FinBERT-Prosus had training overlap with the evaluation data, so its headline score is not a clean generalization comparison. This is sentiment evidence, not a trading test. |
| R3 — PRIMARY, research paper | [Lopez-Lira and Tang](https://arxiv.org/abs/2304.07619), abstract only; related to existing L-22 | Reports headline-based return predictability, stronger for smaller stocks and negative news, and argues that complex interpretation needs capable models. Does not establish a low-latency advantage in LARP's long-only bStocks universe or our achievable after-cost returns. |
| R4 — PRIMARY, publisher claim | [Qwen3-4B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507), overview and license metadata | A concrete 4B local generative candidate, with Apache-2.0 metadata and non-thinking output. Candidate for structured extraction, not a demonstrated financial sentiment winner. Pin and verify the exact artifacts and rights before use. |
| R5 — PRIMARY | [SEC webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions), filing availability and scripted access; [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), update schedule | The FAQ describes document availability often 1–3 minutes after acceptance, without a guarantee; the API page describes typically sub-second submissions-API processing as filings are disseminated. These measure different stages. Neither guarantees acceptance-to-agent latency. Measure it; follow source access limits. |

## Proposed design, not adopted

1. Prefer permitted publisher APIs, RSS/Atom, issuer releases and EDGAR interfaces where available. Use HTML crawling only for sources whose access and content-use terms permit the planned use. The source list, access method, polling policy and rights must be registered; public readability alone does not establish retention or redistribution rights under F-71.
2. Save publication time, first-seen/fetch time, source URL, content hash and revision identity. Deduplicate syndicated copies and cluster updates to the same catalyst. Preserve the version actually available at each decision; later corrections must not rewrite history.
3. Resolve each affected company to eligible instruments, then run a warm local classifier over relevant passages. Define chunking and aggregation for full articles rather than silently truncating or averaging unrelated companies. Neutral, duplicate or irrelevant news can avoid an expensive call, but held-position falsifier checks must not be starved by this filter.
4. For relevant events, produce a bounded structured assessment with company, event type, sentiment, source spans, novelty and missing/uncertain fields. Any local generative replacement must also pass LARP's tool-use and verification tests. Unsupported figures or missing expectations remain unknown; the model must not invent them.
5. Feed verified evidence into the calibrated decision model, selection policy, fresh-quote cost checks, deterministic risk controls, write-ahead logging and signer. For ambiguous evidence, escalate within G-50's budget or abstain. No raw sentiment-to-signer path is proposed.

**INFERENCE — model sizing:** Start with the existing FinBERT baseline and one roughly 4B–8B instruction model for extraction/context, rather than treating every model below 100B as small. R4 is one concrete candidate, not a claim about the best current model. Benchmark on the intended hardware before choosing. A larger model may improve interpretation but worsen resource use; a local model is not automatically faster than a hosted one.

**ESTIMATE — weight memory only:** For a dense 70B model, 16-bit weights occupy about 140 GB; ideal 4-bit packing is about 35 GB. Arithmetic: parameter count × bits / 8, decimal GB. Runtime buffers, quantization metadata and KV cache add memory. No inference-speed claim follows from these estimates. Hardware, VRAM/unified memory, input lengths and burst rate are not yet supplied.

**INFERENCE — measure the whole path:** End-to-end delay includes source publication/dissemination, detection/polling, download/parse, queueing, inference, verification, quote/build, signing and settlement. Record p50/p95/p99 for the stages; separately report published-to-first-seen and first-seen-to-action. Keep models loaded. Source delays may dominate the inference saving (R5), and shortening inference does not show that a tradable price gap remains.

## Validation to pre-register before running

This is an idea record, not a frozen experiment. Create an EXP entry with an owner, dataset hashes, dates, model revisions, hardware/config, numeric thresholds and pass/not-supported/inconclusive rules before any benchmark. Commit and push decision/logging-affecting code before execution under G-03/F-61.

- **Separate the changes.** Compare ingestion methods with the same model, then compare the existing FinBERT-plus-evidence path with a local evidence replacement using identical events and downstream controls. A sentiment-only trading policy, if investigated offline, is a separate strategy ablation; its outcome must not be inferred from a latency win.
- **Quality:** Use an unseen, licensed corpus representative of eligible issuers; group syndicated articles by event across splits and address model cutoffs under I-37. Measure entity attribution, sentiment macro-F1, material-event recall, numerical extraction, supported-claim precision, abstention coverage and schema failures. Include multi-company stories, rumors, corrections, negation, earnings surprises and stale reposts. Model confidence must be calibrated, not trusted because it is high.
- **Latency and reliability:** Test real article lengths, warm/cold starts and realistic bursts on target hardware; count dropped events, duplicates, queue growth and stale assessments. Freeze a p95 latency budget and quality non-inferiority margin before comparing models. Do not claim a speedup without measured end-to-end improvement.
- **Economic value:** Separately test whether the faster path preserves or improves after-cost outcomes at matched coverage with unchanged risk/sizing rules. Use executable quotes available only after the measured detection and processing delay; include exit costs, failed/missing quotes, gas and slippage. Fix the horizon and clustered uncertainty method before evaluation. Positive sentiment accuracy does not pass this gate. Do not tune on development/scored-run P&L (G-46); quote simulation is not realized execution.
- **Promotion gate:** Adopt screening only if its latency gain meets the frozen budget while quality/recall remain within the frozen bounds. Replace the evidence LLM only if the full structured-evidence, verification, audit and operational requirements also pass. Require the independently pre-registered economic gate for a trading-policy change. Insufficient samples remain inconclusive, retaining the existing declared design/default rather than enabling an untested shortcut.

## Open dependencies and disposition

- Hardware and operating budget; exact sources and their rights; model/checkpoint selection; entity/event dataset and post-cutoff coverage; detection and execution latency measurements; target horizon (D-06); thinking-output acceptance (D-03/Q-16).
- Suggested functional owners, not assignments: Agent/Model lead for classifier/extraction benchmarks; Markets/Data/Risk lead for source selection and labels; Execution/Security lead for quote timing; Platform/Audit lead for ingestion durability and latency traces.
- Decision: retain as an **open potential idea**. No active design, model declaration, risk limit or experiment criterion is changed. No incomplete-work item is closed by this research alone.
- Notes / corrections: none.
