# Experiment & Idea Ledger

One running record of every idea we consider and every experiment we run, kept in the repo so the history stays with the code. Newest entries go at the bottom.

## Rules
1. **Append-only.** Never edit a past entry's criteria or results. To correct something, add a dated line under that entry: `- 2026-10-14 correction (initials): …`.
2. **Pre-register before you run.** An experiment needs its hypothesis, metric, data and periods, and its pass criterion written here, and committed, *before* any result exists. The commit timestamp is the proof.
3. **Three result states:** `supported`, `not supported`, `inconclusive`. A small sample is inconclusive, not a failure.
4. **Results from simulated quotes are not realised fills.** Say which one each result is.
5. **Never tune on P&L from the dev phase or the scored run.** Changes during the run must be justified by non-P&L evidence: schema errors, latency, calibration drift, incidents. (`skill/larp/plan.md` G-46, T-15)
6. **If a result changes live behaviour,** it ships only through a committed, manifested version event. Record the version ID in the entry. (`skill/SKILL.md` G-03, G-11; official rule F-60)
7. **No secrets, keys or private training/label data in this file** (official rule F-61). Link to data snapshots by name or hash.
8. Cross-reference skill IDs (H-, D-, G-, Q-) where relevant, and update the skill file if an entry settles one of them.

## Status values
- **Ideas:** `open` → `promoted` (became an experiment) / `dropped` (give a reason) / `adopted` (added directly to the design with a version event).
- **Experiments:** `draft` (criteria not yet frozen) → `pre-registered` → `running` → `supported` / `not supported` / `inconclusive` / `abandoned`.

## Templates

```markdown
### IDEA-000 — short title
- Date / author: YYYY-MM-DD / initials
- Status: open
- What: one or two sentences
- Why it might help: mechanism, not hope
- Cost / risk: build time, failure surface, compliance concerns
- Links: H-/D-/G-/Q- IDs, issues, PRs
```

```markdown
### EXP-000 — short title
- Date / owner: YYYY-MM-DD / initials
- Status: draft
- From: IDEA-xxx or skill ID (e.g. H-02)
- Hypothesis: one falsifiable sentence
- Variants compared: baseline vs treatment, stating exactly what differs
- Data & periods: sources; train / calibration / threshold-selection / final-evaluation windows; snapshot hash
- Metric: primary metric, and how uncertainty is reported (e.g. bootstrap CI)
- Pass criterion: supported if …; not supported if …; inconclusive if …
- Code / config: commit SHA, config hash
- Result: (fill only after running) state + numbers + simulated or realised
- Decision: what changes, if anything; version ID if behaviour changed
- Notes / corrections:
```

---

## Entries

### EXP-001 — Verified evidence vs no-evidence baseline
- Date / owner: 2026-10-03 / [owner]
- Status: draft (blocked on D-07: baseline definition)
- From: H-02, D-07, D-08
- Hypothesis: at matched coverage, the decision model with verified structured evidence beats the no-evidence decision model in after-cost mean return of the traded cases.
- Variants compared: V0 = no-evidence decision model (inputs, sizing and exits per D-07); V1 = V0 + verified evidence state; V2 = V0 with an evidence-only veto. Each variant is judged against its own criterion.
- Data & periods: events after the evidence LLM's training cutoff (I-37); separate train / calibration / threshold / final windows [dates]; snapshot [hash]
- Metric: after-cost mean return of the selected cases minus V0's at matched coverage; Brier score and reliability of the traded bin, with bootstrap CI
- Pass criterion: supported if the CI lower bound is > 0; not supported if the CI upper bound is ≤ 0; inconclusive otherwise or if n < [N]
- Code / config: —
- Result: —
- Decision: if inconclusive → D-08 default (to be pre-registered)
- Notes / corrections:

### EXP-002 — Do off-hours bStocks quotes lag verified news?
- Date / owner: 2026-10-03 / [owner]
- Status: draft (thresholds in brackets not frozen)
- From: H-01
- Hypothesis: after a verified post-close catalyst, the executable token buy quote at detection plus the sell quote at [US open + 30 min] give a positive after-cost gain.
- Variants compared: catalyst events vs a matched no-catalyst baseline at the same observation times
- Data & periods: Web3 API executable quotes logged read-only from dev week 1 (Oct 12); fixed quote size [q]; missing quotes recorded, not dropped; catalysts deduplicated
- Metric: mean after-cost gain per observation, with a one-sided bootstrap p-value
- Pass criterion: supported if n ≥ [20] and p < [0.05]; not supported if n ≥ [20] and the criterion fails; inconclusive if n < [20] (expected for the dev phase)
- Code / config: —
- Result: — (results are quote-simulated, not realised)
- Decision: v1.0 uses off-hours logic as an execution guard only unless the result is supported
- Notes / corrections:

### EXP-003 — Rule-based regime gating vs a simple volatility cap
- Date / owner: 2026-10-03 / [owner]
- Status: draft
- From: H-03, I-66
- Hypothesis: pre-registered regime rules reduce drawdown in historical stress episodes more than a simple volatility cap does, at an acceptable coverage cost.
- Variants compared: no gating / volatility cap / regime rules
- Data & periods: historical stress episodes [list]; block bootstrap; report the count of independent episodes
- Metric: max drawdown and coverage (share of candidate entries still allowed)
- Pass criterion: supported if the regime rules beat the volatility cap on drawdown with coverage loss ≤ [x]%; not supported if not; inconclusive if fewer than [k] independent episodes
- Code / config: —
- Result: —
- Decision: if not supported → replace the regime governor with the volatility cap (version event)
- Notes / corrections:
