# Binance Agentic AI Challenge — Proposal-phase material

> Live for today's submission (Sep 30); archive after the proposal is sent.
> Contains §10 proposal guidance, T-20, D-01 and I-57, whose only use is writing the Sep 30 proposal.
> IDs are stable; see `SKILL.md` for the reading contract and label meanings. Date: 2026-09-30.
> **Priority 1 (v0.5, due today):** the Framing block and table changes below, and the larp/plan.md §8 diagram (decision model → selection gate; rule-defined regime governor; memory written only after verification; recovery by observable identifiers), must be reflected in the PDF diagram and text before submission.

## Team fact (from §2.2)
- T-20 Off-hours framing still in the drafts: proposal.md — "The core insight is that tokenized equities operate continuously while their underlying companies, primary markets, and information sources move on different clocks"; answers — "LARP's information edge is timing-aware synthesis". 'Different clocks' is acceptable motivation for supporting control 3; presenting it as the core insight or an information edge conflicts with §6.1 (I-55) and H-01. Rewrite before submission (§10).

## Inference (from §4.4)
- **I-57 Reviewers see what the form asks for** (T-02, T-04): leakage/overfitting and reproducibility have their own sections, so the proposal must answer them well; this does not show extra judging weight beyond the five criteria (F-40). The form's questions also suggest a post-run technical review may exist (Q-28) and that a KYC-verified Binance account is expected (Q-26). LARP's answers there are strong (T-15, T-16) but must add the LLM-memorisation point (I-37). Confidence: Med. Proposal use: Y.

## Decision (from §6.4)
- D-01 **Risk posture (before submission, Sep 30).** LARP's draft is conservative (T-14; with I-61's example sizes ≈36% typical gross). Options: keep it (strong on Risk awareness; low upside in rising markets) or widen caps. Either way: state the risk-budget definition (I-61) and drawdown behaviour (I-62). Contest-strategy arguments for more variance are in Appendix A and must not drive proposal wording.

## 10. PROPOSAL GUIDANCE (map to the form's sections, T-02)

Rules for the text: one central capability (I-55); hypotheses, not claims (I-56); no tournament talk (Appendix A); no SECONDARY/DEV-REPORT statistics; no numbers you will not enforce; brand names only where needed to explain capture of model I/O.

**Framing** (guidance from external review A; wording free): the agent is the protagonist. It plans its evidence needs within the bounded loop (G-50), retrieves timestamped evidence, verifies claims (G-53), maintains a falsifiable thesis per held position (G-51) and produces a structured evidence state. A calibrated model turns that state into UP/FLAT/DOWN probabilities; a selection rule may abstain (I-63). Deterministic policy, risk, version and execution layers decide whether any trade is permitted. The LLM never signs, sizes or sets limits.

**Originality statement** (suggested wording, adapted from review A §5; the thesis is placed after verification to match §8): "LARP is a selective trading agent that treats evidence verification as part of the decision process. It plans its research, retrieves timestamped evidence, verifies each material claim, maintains a falsifiable thesis built from verified claims, and passes only verified state into a calibrated decision model that may abstain."

| Form section | Say | Avoid |
|---|---|---|
| Your Proposal | "LARP turns verified, timestamped catalysts into probability-scored, abstaining long/hold/exit decisions; whether off-hours quotes lag verified news is a hypothesis we test and use only as an execution guard unless it passes." Supporting controls in one line each. If clocks are mentioned: "different trading/information clocks motivate market-state-aware controls; whether they support profitable decisions after costs is a hypothesis we test." Also: "the evidence-assisted model trades only if it beats a pre-registered baseline on held-out data; otherwise the agent runs a pre-registered default and records that in its manifest" (H-02, D-07, D-08). | Three co-equal innovations; "core insight … different clocks" as the core idea; "information edge"; "we exploit off-hours mispricing" (T-20). |
| Architecture (PDF) | §8 diagram (v0.5) incl. tool loop, memory (read → loop; write only after verification), planner, claim verification, calibrated decision model → selection gate, rule-defined regime governor. | A pipeline with no agentic loop; ABSTAIN drawn as a model output class. |
| Model approach (in Your Proposal / Architecture) | Describe it generically as a self-hosted calibrated decision model. The base checkpoint is near chance zero-shot (E-51), so the model-layer claim is the team's own fine-tune + calibration on point-in-time labels (I-38, I-51). | Naming Laya or Jev; implying the base checkpoint forecasts out of the box. |
| Data / tools used | Sources with licences; point-in-time stamping; organiser data authoritative. | Grey-area scraping. |
| Position & risk | T-14 values; entry-cost limit + explicit exit-cost assumption (G-25); drawdown new-risk halt / entry halt, not "kill switch" (unless automatic de-risking is defined, G-22); the risk-budget definition (I-61), drawdown behaviour (I-62), "values are versioned configuration enforced in code" (I-35). | Kelly; "kill switch" if it only halts new risk; limits you won't enforce. |
| Leakage / overfitting | T-15 plus LLM memorisation controls (I-37: post-cutoff evaluation, anonymisation). | Claiming walk-forward alone solves LLM leakage. |
| Reproducibility | T-16; hash chain = tamper-evidence after anchoring, completeness via reconciliation and sequence numbers (I-30); thinking-output plan (I-29); target definition (I-63); three kinds of onboarding gate — eligibility, operating prerequisites, engineering dependencies (I-65). | "Proves completeness"; "organizer-approved model". |
| Team capability + scope | Named owners, concrete evidence; corrected timeline (§9). | Dates that don't match the official timeline. |
