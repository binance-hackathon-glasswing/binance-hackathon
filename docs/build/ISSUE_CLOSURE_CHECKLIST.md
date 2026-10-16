# Issue closure checklist (2026-10-16)

This is a snapshot of what must happen before each open GitHub issue can be closed. It was checked against `codex/system-testing-20261012` at `793b382` (#84, #99, #100 and #101 merged), the ledger files and every issue comment. The live copy to tick off is the description of the PR that added this file. Closing an issue still follows its own acceptance criteria.

## Quickest wins
- [ ] Keith confirms A-T15 → close #25
- [ ] Keegan records D-DN-09 → close #52, unblock #34
- [ ] Team confirms the first-gas swap exception → close #105
- [ ] Keith keeps or moves the Nov 11 15:00 UTC flatten (IDEA-035 C4) → close #107
- [ ] Push the merged head to the mirror CI and record it in IDEA-049-D → close #104

## Sign-off or one decision
- [ ] #25: Keith confirms A-T15. The code is merged and the proof passes.
- [ ] #90: Isaac, Keegan and Yao Zhu confirm or overrule decisions D1–D6 in IDEA-055.
- [ ] #105: Team confirms items 1–3: the MetaMask swap exception and how it is recorded.
- [ ] #107: Keith records the flatten time in IDEA-035 C4.
- [ ] #52: Keegan records D-DN-09. Criteria 2 and 3 are already merged (PR #66).

## Decision, then small code
- [ ] #34: Keegan records D-DN-09.
  - [ ] Code: run required reductions under pausing HALTs, or record them only.
- [ ] #27: Isaac, Keegan and Keith decide C-OPEN-003 before Oct 22: (a) a bounded signing lifetime, or (b) a router deadline no later than the proposal's expiry.
  - [ ] Code: the expiry change and the approve→swap test.
- [ ] #39: Yao Zhu and Keith decide A-DEC-005. Recommended: block new SKHYB buys.
  - [ ] Code: an SKHYB entry block.
- [ ] #55: Keith writes a decision row in IDEA-037. Recommended: last good mark minus a haircut.
  - [ ] Code: a test with one stale name and one name near its cap.
- [ ] #56: Keith decides how the full flatten finishes on the BNB held at the cut-off. Recommended: size the reserve for split sells.
  - [ ] Code: a full four-name flatten test.
- [ ] #44: Isaac and Keith choose the signer cap values. This blocks Gate B.
  - [ ] Set the values in `signer.json`.

## Decision plus research or measurement
- [ ] #37: Keith and Yao Zhu decide B-DEC-03.
  - [ ] Run a pre-registered after-cost comparison.
- [ ] #38: Team decides B-DEC-02, -03 and -06.
  - [ ] Section C measures all-in cost, including gas, at real order sizes.
  - [ ] Run a staggered four-session evaluation.
- [ ] #60: Keegan measures memory use during the Gate A run.
  - [ ] Choose a bigger host (about +$19/month, Yao Zhu approves the spend) or tighter limits.
- [ ] #94: Q-20 is answered.
  - [ ] Design the dividend and split adjustments.
- [ ] #95: Team decides whether the routing stack lands on `main`.
  - [ ] #85's description is fixed.
  - [ ] #91 passes.

## CI and verification
- [ ] #104: Mirror CI runs on the merged head (PostgreSQL 14.24) and is recorded in IDEA-049-D.
- [ ] #91: The six AIand checks run, on the mirror.
- [ ] #98: Org Actions minutes are restored, then `runtime.yml` runs on the branch head.
- [ ] #49: Someone downloads the org-run CI artifact by hand and matches its hash. Depends on #98.

## Hosted or real-world actions
- [ ] #106: First-gas swaps.
  - [ ] Dev wallet now.
  - [ ] Final wallet before Oct 29 00:00 UTC.
  - [ ] Each transaction hash, amount and time recorded.
- [ ] #92: The BSC RPC is ready.
  - [ ] A provider with `finalized` support is chosen.
  - [ ] Network access to it is opened.
  - [ ] The config is filled in.
  - [ ] The first hosted check is run.
- [ ] #32: Network routes are proven.
  - [ ] PR #102 is merged.
  - [ ] The destination table is approved.
  - [ ] The route checker is run on the hosts at Gate A.
- [ ] #30: Gas top-ups work end to end.
  - [ ] PR #103 is merged.
  - [ ] First-gas swaps are done (#106).
  - [ ] Native BNB tracking is proven on a real provider.
  - [ ] G-28 (BNB floor and top-up size) is decided.
  - [ ] The organisers answer Q-39 (does BNB count in equity).
- [ ] #33: The application is unblocked.
  - [ ] Section C's swap decoder is done and the fake-only executor gate is lifted.
  - [ ] A measured LIVE profile exists (#88 merged, then the quote captures).
  - [ ] Source terms hashes are recorded.
  - [ ] The hosted rehearsal is done.
- [ ] #97: Model-routing adoption gates.
  - [ ] Provider access.
  - [ ] An independent evaluation.
  - [ ] Hosted ledger and secrets.
  - [ ] A release declaration.
- [ ] #36: Closes when #90, #92 and #94 close, or close it now with a comment handing the rest to them.

## Other people's code and trackers
- [ ] #93: The model-budget cleanups are applied on #85's branch.
- [ ] #22: Closes when #25, #27, #30, #32, #33, #34, #36, #37, #38 and #39 close.
- [ ] #42: Closes when #44, #49, #52, #55, #56 and #60 close.
