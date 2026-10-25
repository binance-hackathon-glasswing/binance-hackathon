# IDEA-098 — FS1 with allowance recovery: the final can always sell after an aborted swap

- Date / author: 2026-10-25 / Claude Code, asked by the user ("add the fixes to the pipeline in a new PR; ensure it can
  run smoothly for 14 days by buying and selling without disruptions"). Owners: Keegan (gas/caps, execution), Isaac
  (signer policy, profile approval), Keith (strategy values unchanged), Yao (install).
- Status: **open — pre-registered (criteria RC1–RC7 below committed before any criterion test was run).**
- Related: IDEA-096 (PR282, allowance recovery, implemented with defaults off), IDEA-093 (PR278, FS1 final candidate,
  cleanup disabled), IDEA-090 S2-F6 (post-approve requote aborts; fix merged), IDEA-089 (run 4), LD06, LD10.

## Problem

Run 4's terminal flatten (2026-10-25) sold nothing:
1. The first SELL's swap aborted after its approval succeeded (S2-F6 class).
2. That left the SKHYB router allowance open (68939879194155372 units at 10:43Z, read on BSC public RPC).
3. The quote verifier refuses every other name's swap while another token has an open allowance (IDEA-096).

Two PRs address this, but neither makes the final safe on its own:
- **PR282** implements the recovery: F2 revoke before the trade, F3 revoke on abort, F4 reason codes. Its defaults are
  off.
- **PR278** builds the FS1 final candidate. It does not contain PR282, and its profile `19176e6c…` reserves gas with
  "cleanup disabled".

As things stand, the final would have run 4's deadlock. One aborted swap after an approval would block every later
trade in another token for the rest of the 14 days. That includes the F-125 activation self-check's SELL, any loss-ladder
reduction and the terminal flatten. The 20 bp slippage makes aborts rarer, but it cannot exclude them.

## Decision (proposed; Isaac and Keegan to accept)

1. Merge PR282 into the PR278 head, on a new branch, with no change to either PR's code apart from item 3.
2. Add FS1 profiles with cleanup on, built by the existing builders with an explicit `allowance_recovery` option:
   - **FINAL** `fs1-final-recovery.json`;
   - **FS1-R REHEARSAL** `fs1-rehearsal-recovery.json`.

   The only changes are PR282's gas formulas at the CAP-02 signed ceilings (1,200,000 gas × 160,000,000 wei):
   - `gas_action_budget_units` = 8 children × 1.92e14 = 1.536e15 wei;
   - `exit_gas_reserve_units` = 5 positions × 2 exit children × that = 0.01536 BNB;
   - their provenance.

   Strategy values, windows, sizes, slippage and the self-check are unchanged. The cleanup-off profiles stay as they
   are for comparison.
3. `tools/deploy/enable_allowance_recovery.candidate` leaves a profile that already carries these values
   byte-for-byte unchanged. Turning on the execution, signer and runtime flags at install therefore cannot change the
   hash Isaac approves.
4. The FS1 install sheet names the recovery profile, its hash and the opt-in steps.

## Pass criteria (pre-registered)

Base for "red on base": PR278 head `19580fe1` merged with PR282 head `5cac4ca4` (`992180e5`), without this entry's
changes. Real PostgreSQL where needed.

| ID | Criterion |
|---|---|
| RC1 | Run 4's sequence through the real coordinator, planner, PostgreSQL execution registry and settlement (PR282's AL2 harness, synthetic chain/venue), five held names:<br>• the first terminal-flatten SELL's approval succeeds, then its swap aborts at the requote ("encoded swap economics mismatch/expired");<br>• **with recovery**, that pay token's allowance is revoked within the same intent, and later rounds sell all five names to dust with at most `max_attempts_per_leg_session` (5) quote rounds per leg. All six allowances end at 0 and no reservation remains;<br>• **without recovery**, the same sequence ends holding stock with the allowance open (run 4 reproduced). |
| RC2 | Both recovery profiles rebuild byte-for-byte from their builders and pass `validate_live`. Each differs from its cleanup-off profile only in `gas_action_budget_units`, `exit_gas_reserve_units` and their provenance, with the values in Decision 2. |
| RC3 | `candidate()` on the pinned FINAL recovery profile returns the same profile bytes and sets `allowance_recovery` true in the execution, signing policy and runtime outputs, with `gas_budget` = 1.536e15. On the cleanup-off FS1 profile it produces the same three gas values as the pinned recovery profile. |
| RC4 | `caps_review` reports `numeric_status` COVERED for the FINAL recovery profile with an execution config at the CAP-02 ceilings and BNB equal to its exit reserve, and BLOCKED with 1 wei less `gas_budget`. |
| RC5 | Signed live Gate A preparation of the FINAL recovery profile with the FS1 routing and `allowance_recovery=True` passes `gate_a_check` (`check_scope`, `check_inputs`), and the runtime driver carries `allowance_recovery: true`. Signed dev preparation of the FS1-R recovery profile passes the same way. |
| RC6 | The FS1 install sheet and the backlog (FLAT-01, IDEA-093) name the recovery profile hash for approval (A1) and the opt-in step (M4); the FS1 final README lists both profiles. |
| RC7 | Full suite: no new failures against the base in the same environment; exact counts reported. |

Result states: `supported` if RC1–RC7 pass; `not supported` if any of RC1–RC5 fails after the change; `inconclusive` if the
environment prevents a run (stated).

## Not covered here

- AL9 (PR282's live check in a dev run), Isaac's approval of the new hash and signer policy, Keegan's gas and timing
  acceptance against the final wallet's actual BNB (GAP-73), and the install itself.
- Run 4: it keeps RC7 and stays stuck until the SKHYB allowance is consumed. No manual wallet action is proposed
  (SKILL.md §0.3 #1).

- 2026-10-25 clarification (Claude Code, before any criterion test was run): RC2's "their provenance" also includes
  `gas_sizing_budget_units`. Its value is unchanged, but PR282's recovery formula rewrites its provenance to say that
  the verifier adds the observed revokes. The shared helper writes all three provenance entries, exactly as
  `candidate()` already does.
