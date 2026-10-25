# IDEA-098 — FS1 allowance recovery within the original execution authority

- Date / author: 2026-10-25 / Claude Code, asked by the user ("add the fixes to the pipeline in a new PR; ensure it can
  run smoothly for 14 days by buying and selling without disruptions"). Owners: Keegan (gas/caps, execution), Isaac
  (signer policy, profile approval), Keith (strategy values unchanged), Yao (install).
- Status: **open — pre-registered (criteria RC1–RC7 below committed before any criterion test was run).**
- 2026-10-25 status (Claude Code): **supported offline with two recorded deviations** (results below); owner approval, M3 and AL9 open.
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

Without recovery, a leftover allowance can block trades in other tokens until it is consumed or cleared.
The no-recovery harness below also shows that a successful retry of the same token can consume it; persistence
for the whole 14 days is not established. This can affect the activation self-check SELL, loss-ladder reductions
and terminal flatten. The slippage setting alone does not exclude quote refusals.

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

## Results (2026-10-25, Claude Code; PostgreSQL 16.15 / Python 3.12.3 on Linux x86_64, not the pinned 14.24 image)

Commits: criteria `2e69a8d7` (+ clarification `92141ca2`), tests `d8663811`, implementation `f0f35a5a`.
On the base merge `992180e5` the test file gives 5 failed and 3 passed:
- RC2–RC6 fail there.
- RC1's arms pass. The recovery itself is PR282's and is already in the base, so RC1 qualifies the merged build rather
  than this change.

| ID | Result | Evidence |
|---|---|---|
| RC1 (recovery) | PASS | First SELL (GOOGLB): approve final, then the requote is refused once. The SELL is aborted and its pay-token allowance revoked in the same intent. Its retry and the other four SELLs complete, and all five reach dust. Six allowances 0, no reservations, maximum leg ordinal 2 (limit 5), 0 allowance blocks. |
| RC1 (no recovery) | **prediction NOT met** | The abort leaves the allowance open, as predicted. But the planner re-plans the aborted name first, its own approve overwrites the allowance and its swap consumes it, so this flatten still ends flat. Run 4 stuck because RC7 planned another name next (NVDAB at 09:30Z) and SKHYB's retries kept aborting. The test now asserts only the open allowance after the abort. |
| RC1x (exploratory, added after the RC1 run) | — | The aborted name's market stays adverse, so every SELL of it is refused after its approve. **Without recovery:** nothing sells; all five legs reach 5 attempts with 60 allowance blocks and the allowance stays open (run 4 reproduced). **With recovery:** the other four reach dust; the adverse name stops at its leg limit (5) with no allowance open. |
| RC2 | PASS | Both recovery profiles rebuild byte-for-byte. Each differs from its cleanup-off profile only in `gas_action_budget_units` 1.536e15 and `exit_gas_reserve_units` 1.536e16, plus the provenance of those two and of `gas_sizing_budget_units` (RC2 clarification). `validate_live` passes. FINAL `b8ba06e2…`, FS1-R `17ab891d…`. |
| RC3 | PASS | `candidate()` on the FINAL recovery profile returns its exact bytes. It sets the three `allowance_recovery` flags, `gas_budget` 1.536e15 and the same profile SHA in the execution and runtime outputs. From the cleanup-off profile it derives the same three gas values. |
| RC4 | **partial** | Recovery gas rows COVERED: `INITIAL_SIGNED_CHILD_GAS_ENVELOPE` and `INITIAL_PROFILE_ACTION_BUDGET` at 1.536e15, `INITIAL_BNB_EXIT_RESERVE` at 1.536e16. Each is BLOCKED one unit short. `numeric_status` stays BLOCKED on two rows that come from the rehearsal-sized synthetic fixture, not from recovery: `FULL_POSITION_USDT` (fixture policy allows 35 USDT per input, below FS1's 38.2 USDT cap) and `QUOTE_EXCEEDS_EXECUTION_GAS_LIMITS` (fixture quotes at 2 gwei, above the 0.16 gwei ceiling). The real M3 review with FS1-size quotes and the final signer policy is required (FLAT-01). |
| RC5 | PASS | Signed live preparation of the FINAL recovery profile (FS1 routing, router-policy pair, `allowance_recovery=True`) and signed dev preparation of FS1-R pass `check_scope` and `check_inputs`. Both carry the runtime flag and the report's `allowance_recovery`. |
| RC6 | PASS | The install sheet pins `b8ba06e2…` with A1 approving it and the signer's `allowance_recovery`, and M4 adds `--allowance-recovery` and the opt-in tool. Both READMEs list the recovery hashes. The backlog (FLAT-01, IDEA-093) is updated. |
| RC7 | PASS | Full suite: branch `f0f35a5a` **2798 passed, 11 skipped, 4029 subtests, 0 failed**; base `992180e5` **2790 passed, 11 skipped, 4029 subtests, 0 failed** (+8 = this file). Related suites (FS1, allowance recovery): 86 passed. |

Result state: **supported with two recorded deviations.** RC1's no-recovery prediction was not met in this harness
(RC1x reproduces run 4 instead). RC4 is partial: its gas rows pass, and its two remaining blockers come from the
fixture scale.

What this means for 14 days: with the recovery profile installed and opted in, an aborted swap after an approval no
longer blocks other names. The SELL is cleaned up in the same intent and retried, within 5 attempts per leg per
session. A name whose market stays adverse stops at its limit and resumes in the next session, while the others keep
trading. Without the opt-in, the final has run 4's failure mode. Open: Isaac's approval of `b8ba06e2…` and the signer
policy, Keegan's gas acceptance against the final wallet's actual BNB (GAP-73) and M3 at FS1 sizes, and AL9 in a dev
run on `17ab891d…`.
- 2026-10-25 update (Claude Code): the branch now includes canonical `9fe5fb07` (`30a993e9`). That brings in PR282 as
  merged, with its PR282-RV01 monitor and verifier fixes, and PR284's S4 carry-over.
  - `build_rehearsal_candidate.py` keeps FS1-R/`allowance_recovery` and S4 `carry_over` as separate options, refused
    together.
  - FS1 FINAL/FS1-R recovery profiles `b8ba06e2…`/`17ab891d…` and S4 `58b31806…` still rebuild byte-for-byte.
  - Full suite at `30a993e9` (PostgreSQL 16.15 / Python 3.12.3): **2817 passed, 11 skipped, 4029 subtests, 0 failed**.
    FS1, S4 and recovery suites: 137 passed.

## PR283-RV01 — independent review (2026-10-25; criteria before execution)

Review head `308e91b340ae8aeae7e7b7549768190553ab5fec` against PR278 base `19580fe1` and canonical
`9fe5fb07`. Preserve the stacked target `claude/final-strategy-20261025`; merging PR283 updates PR278's branch,
not canonical. No deployment or wallet action is part of this review.

Findings to resolve in this PR: the FS1 sheet's F0p/M3 still name cleanup-off `fs1-final.json` and probe `5b642bd3…`
after Pins/A1 moved to the recovery profile; the FS1-R README still labels its cleanup-off probe the install pin.
M3's current `review_rehearsal_caps` helper is dev/REHEARSAL-only and cannot be presented as a completed FINAL
assembly path. M4's opt-in emits a standalone signing-policy source, not a replacement `signer.json`; final assembly
and prepared/release hash checks must bind the final outputs before approval/install. Existing F0p explicitly leaves
FS1-specific scripts to the owners; retain that activation blocker.

Prospective checks:
- RV1: replace stale install pins with recovery-profile/fresh-probe requirements, spell out final signer assembly
  and package/release re-pinning; preserve original expiry, signed ceilings, stock-flat and owner/host gates.
- RV2: extend RC4 with synthetic FINAL-sized signer input caps and CAP-02-compatible quote fees so the whole
  `numeric_status` is COVERED, retaining OWNER_REVIEW_REQUIRED/POLICY_APPROVAL_REQUIRED. One wei less gas/BNB,
  an insufficient USDT signer input cap or over-ceiling quote fee must still block. This supplies offline coverage,
  not fresh real-wallet M3 evidence or approval.
- RV3: both FS1 recovery profiles and canonical S4 still rebuild byte for byte; idempotent candidate output and
  explicit runtime/execution/signer scope pass; coordinated abort/cleanup/flatten and existing guard suites pass.
- RV4: full suite on pinned Linux Python 3.12.15/PostgreSQL 14.24 with dependency pins verified; exact exclusions
  recorded. Confirm the intended head/base immediately before a history-preserving merge to PR278's branch.

Commit/push all changed executable code/tests before running it. GitHub CI/account status, real caps/gas/timing,
exact signer/profile approval, FS1-specific scripts and AL9 remain separately recorded if unavailable.


### PR283-RV01 results and merge decision

At pushed source `b3a333de6f8a82c3b06b7bcd49dc1e7a1440c2f1`: focused suite **49 passed**; full suite
**2818 passed, 0 failed, 8 skipped, 3 deselected, 4029 subtests passed**, 265.50 s. Linux aarch64,
Python 3.12.15 / PostgreSQL 14.24; all 45 applicable dependency pins matched. Source, profiles, commands, artifact
hashes, environment/exclusions and CI annotation are in [the review receipt](../build/evidence/pr283-review-20261025.json).

RV1 fixes stale install references without changing any profile bytes. F0p/M3 now require the recovery profile and
a newly pinned probe; the existing dev-only reviewer is explicitly insufficient for FINAL. M4 distinguishes its
standalone policy output from assembled signer.json and requires final prepared/release pin checks before install.
The two historical cleanup-off probes remain labeled comparison evidence. FINAL-specific scripts/Q1/M3 remain
owner work, not completed by this documentation correction.

RV2 completes the prospective RC4 numeric success case using synthetic FINAL-sized signer caps and quote fees
inside CAP-02. The whole numeric status is COVERED; approval/install/signing remain false. Independent one-wei
short gas/BNB cases, insufficient USDT input cap and over-ceiling quote fees still block. This resolves the earlier
fixture-only RC4 limitation offline; real M3 against the final wallet remains required.

RV3/RV4 pass. FINAL `b8ba06e2…`, FS1-R `17ab891d…` and S4 `58b31806…` are unchanged and rebuild exactly.
The current canonical execution/signer/strict-preflight code is unchanged by this review. No application source or
tests changed after the full passing run; subsequent edits record documentation/evidence only.

Eight skips are the optional private public-source fixture, external recorded artifacts, root directory-mode
semantics and five systemd runner cases. Three nested Sandbox cases were explicitly deselected because this Docker
host cannot supply their namespaces/proc mounts. No host/sandbox/systemd acceptance is claimed. GitHub run
`40197344800` did not start jobs due account billing/spending limits; runtime annotation `121180942791` confirms it.
The merge uses the user's explicit PR283 review/fix/merge request and this pinned local validation; CI PASS is not claimed.

Merge decision: approve source integration into `claude/final-strategy-20261025` (PR278's branch), preserving history;
PR278's own integration merge remains separate. **Keegan:** fresh FINAL gas/caps/BNB/timing evidence.
**Isaac:** exact profile/signer acceptance. **Yao/host owners:** FINAL-specific scripts, Q1/M3/release preparation,
installation and AL9. These remain in FLAT-01/IDEA-093/GAP-73; this merge grants no deployment or wallet authority.

Final documentation/packaging follow-up: **15 tests / 12 subtests PASS** (release register, bundle and RC6 install
references). All tested application/config/test hashes and all three profiles still match the full-suite receipt.
The PR description records PR283-RV01 and the user-authorized stacked merge scope.
