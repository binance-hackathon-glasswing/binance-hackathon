# Issue closure checklist (2026-10-16)

This is a snapshot of what must happen before each open GitHub issue can be closed, split among the four section owners. Each item has one lead, who may involve the others named. It was checked against `codex/system-testing-20261012` at `793b382` (#84, #99, #100 and #101 merged), the ledger files and every issue comment. The live copy to tick off is the description of the PR that added this file. Closing an issue still follows its own acceptance criteria.

## Keith (section A: strategy, evidence and research)
- [ ] **Start the quote captures before Sat 17 Oct 00:00 UTC** (#88's `tools/run_quote_capture.sh`). They feed the LIVE profile that Gate A and #33 need.
- [ ] Review and merge PR #88 (cost summary).
- [ ] #25: confirm A-T15. The code is merged and the proof passes → close #25.
- [ ] #107: keep or move the Nov 11 15:00 UTC flatten; record it in IDEA-035 C4 → close #107.
- [ ] #39: decide A-DEC-005 with Yao Zhu. Recommended: block new SKHYB buys.
- [ ] #55: write a decision row in IDEA-037. Recommended: last good mark minus a haircut.
- [ ] #56: decide how the full flatten finishes on the BNB held at the cut-off. Recommended: size the reserve for split sells.
- [ ] #37: decide B-DEC-03, then run a pre-registered after-cost comparison.
- [ ] #38: lead B-DEC-02, -03 and -06 with the team, then run the staggered four-session evaluation. Isaac supplies the cost measurements.

## Keegan (section B: decisions, risk and CI)
- [ ] #52 and #34: record D-DN-09, which HALT reasons only pause new spending → close #52, unblock #34.
- [ ] #104: push the merged head to the mirror CI (PostgreSQL 14.24) and record it in IDEA-049-D → close #104.
- [ ] #91: run the six AIand checks on the mirror.
- [ ] Push #87, #102 and #103 to the mirror too, since none of today's PRs has run there.
- [ ] #98: get org Actions minutes restored, then run `runtime.yml` on the branch head.
- [ ] #49: download the org-run CI artifact by hand and match its hash (after #98).
- [ ] #32: approve the destination table in `architecture-deployment.md` with Isaac; run the route checker on the hosts at Gate A.
- [ ] #60: measure memory use during the Gate A run, then choose a bigger host or tighter limits. Yao Zhu approves any spend.
- [ ] #36: close with a comment handing the rest to #90, #92 and #94, or wait for them.
- [ ] #42 (tracker): close once #44, #49, #52, #55, #56 and #60 are closed.

## Isaac (section C: execution, signing and chain)
- [ ] Review and merge PR #103 (gas top-up fix).
- [ ] #27: decide C-OPEN-003 with Keegan and Keith before Oct 22: (a) a bounded signing lifetime, or (b) a router deadline no later than the proposal's expiry.
- [ ] #44: choose the signer cap values with Keith, and set them in `signer.json`. This blocks Gate B.
- [ ] #92: choose a BSC RPC with `finalized` support, open network access to it, fill in the config, and run the first hosted check.
- [ ] #30: prove native BNB tracking on a real provider, and decide G-28 (BNB floor and top-up size) with Keith.
- [ ] #33: build the swap decoder (GAP-29) and lift the fake-only executor gate.
- [ ] #38: measure all-in cost, including gas, at real order sizes for Keith's B-DEC decisions.

## Yao Zhu (section D: operations, hosting and wallets)
- [ ] Review and merge PR #87 (Gate A assembly), PR #102 (route checker) and PR #108 (follow-up to #99).
- [ ] Run the terms capture `python -m larp.sources.live terms --write-register` with a real SEC user agent (needed for #33).
- [ ] #105: collect the team's confirmation of the first-gas swap exception → close #105.
- [ ] #106: do the first-gas swaps, or assign the wallet holder: dev wallet now, final wallet before Oct 29 00:00 UTC. Record each transaction hash, amount and time.
- [ ] #90: lead the review of IDEA-055 decisions D1–D6 with Isaac and Keegan; record confirm or overrule.
- [ ] #94: track Q-20; once answered, design the dividend and split adjustments.
- [ ] #95 and #97: lead the model-routing decision and its gates (provider access, evaluation, hosted ledger and secrets, release declaration).
- [ ] #93: apply the model-budget cleanups on #85's branch, with wtvlol.
- [ ] #22 (tracker): close once #25, #27, #30, #32, #33, #34, #36, #37, #38 and #39 are closed.

## Waiting on the organisers
- [ ] Q-39: does BNB held count in equity? Needed for #30. Still open in SKILL.md.
