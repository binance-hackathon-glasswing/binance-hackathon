# IDEA-097 — S4: REHEARSAL-only flatten test that carries over run 4's holdings

- Date / author: 2026-10-25 (~10:40Z) / Yao's request in a Claude Code session (record and implementation: Claude
  Code). Approvals: Isaac (profile hash, `signer.json`), Keegan (carry-over accounting, runtime review). Host steps:
  Yao.
- Status: **open — pre-registered. Criteria S4-1..S4-9 and S4-L1 below were committed before any S4 code or test.**
- Related: IDEA-089 (S2, run 4), IDEA-092 H1/H2 (install needs a stock-flat wallet), IDEA-096 (the leftover-allowance
  block on run 4's flatten), IDEA-090 S2-F6 (post-approve requote; on canonical, not in run 4's RC7), IDEA-093 (FS1,
  delayed; the scored run starts Oct 29), SKILL.md §0.3 #1 (no manual trading).

## Request (in chat, 2026-10-25)

> "we can always delay the FS1 since official trading begins 29 oct, so we have time to implement the new rehearsal
> profile, make this s4 strictly for rehearsal, do the carry over match what s2 does ignore s3 … then lets see if we
> can retire this run and load the new profile in to continue the process note this profile is meant strictly to test
> the flattening process so set the flatten to a time very close to now so when we load the new profile in it
> immediately can begin selling"

**Reading (assistant; the requester can change it).**
- S4 is S2's profile with three changes: a carry-over, a window whose flatten has already begun, and its own
  `policy_id`. It is for the dev wallet only and is never installed for the final run.
- Run 5 starts from run 4's exact on-chain holdings and run 4's recorded cost basis, instead of refusing them.
- Run 5's first round is already inside the terminal flatten. It sells; it never buys.
- S3's `scheduled_flatten_at` is not used.

## Design

1. **Profile S4** (`larp-s4-rehearsal-v1`), built by `tools/deploy/build_rehearsal_candidate.py --carry-over`:
   - the S2 block unchanged (`KIT_OPEN_STATE`, 5 attempts per leg), S2's sizes, caps, gas, slippage and SHADOW scope;
   - window: `trade_after` 2026-10-25T10:00Z, `new_risk_end` = `flatten_start` 2026-10-25T10:30Z (already passed, so
     no BUY is possible and every round of run 5 is a terminal-flatten round), `signing_end` 2026-10-26T12:00Z
     (Mon 20:00 SGT; about a day of rounds for 4 names × 2 balanced children);
   - a new key `holdings_carry_over: "RUN_EXPORT"`, which declares that the run must start from a reviewed export of
     the previous run's book.
   - Scope: `holdings_carry_over` is accepted only in a REHEARSAL with S2's `KIT_OPEN_STATE` block and without
     `scheduled_flatten_at`. Profiles without the key are unchanged byte for byte.
2. **Carry-over file** `HoldingsCarryOver.v1`, exported read-only from run 4's database after run 4 is retired:
   - source `run_id`, `wallet_id`, the run's `version`, a SHA-256 of its portfolio projection, `reservations` (must be
     empty), and per stock `units`, `decimals`, `cost_basis_units`.
3. **`gate_a.initial_state`** with a carry-over profile:
   - requires the file;
   - refuses it unless its wallet matches, its source run differs from the new run, and it has no reservations;
   - refuses unless every stock's `units` equals the captured raw chain balance exactly, including zero and dust;
   - refuses any `cost_basis_units` that is not a non-negative integer, and any positive balance with zero cost.
   It then sets positions to those units and cost bases. Opening equity is cash + BNB value + Σ `cost_basis_units`
   (holdings are carried at cost, so run 5's P&L is measured against what run 4 paid). The day anchor and peak
   start at that value.
   - Without the profile key the file is refused, and the stock-flat rule is unchanged.
   - `gate_a.prepare` writes the file into the package as `holdings-carry-over.json` and pins its hash in the
     report. `gate_a_check` rebuilds the same initial state from it.
4. **IDEA-096 F1 for this run (sell the token that already has an allowance first).**
   - `MarketPort` attaches `router_allowance_units` to each stock's market row. It reads them through the quote
     verifier's own pinned decoder at one block; if the read fails, the field is omitted.
   - Among mandatory sells, the planner puts names whose router allowance is non-zero first. That name's own
     approve replaces the leftover allowance and its swap uses it up, which unblocks the other names.
   - Records without the field replay unchanged.
   - S4 never buys, so USDT, the one case F1 cannot repair, cannot pick up a leftover allowance. F2/F3/F4 stay open
     in IDEA-096.

## Known limits (recorded before testing)

- **Retiring run 4 ends its flatten window early.** Run 4 still holds GOOGLB, NVDAB, SKHYB and TSLAB, and the SKHYB
  router allowance is still open. Run 5 inherits both.
- **The post-approve requote abort (S2-F6) still applies.** The canonical build includes PR274's narrower
  requote; run 4's RC7 did not. A second adverse move can still abort a swap safely. Each name has 5 mandatory
  attempts in the session.
- **The carry-over is an accounting decision.** Cost basis comes from run 4's own ledger, not from a new
  calculation. Keegan reviews it; Isaac approves the profile hash and `signer.json`.
- **Not for the final.** FS1 starts from a fresh, stock-flat final wallet.

## Pre-registered pass criteria (written before code or tests)

| # | Pass when | Evidence |
|---|---|---|
| S4-1 | The S4 profile rebuilds byte for byte. It differs from S2's only in the window, `policy_id`, `holdings_carry_over` and their provenance, and passes `validate_live` | profile test |
| S4-2 | `holdings_carry_over` is refused in a FINAL profile, without `KIT_OPEN_STATE` hours, together with `scheduled_flatten_at`, or with any other value | profile test |
| S4-3 | `initial_state` with S4 and a matching export gives positions equal to the chain units and the export's cost bases, opening equity = cash + BNB value + Σ cost, and `check_initial_state` passes | gate_a test |
| S4-4 | `initial_state` refuses: S4 without an export; an export under a non-carry-over profile; units differing from chain by one unit; another wallet; the same run ID; reservations present; a negative or non-integer cost; a positive balance with zero cost | gate_a tests |
| S4-5 | A signed dev `gate_a.prepare` with S4 and the export packages `holdings-carry-over.json`, pins its hash, and `gate_a_check` passes on the package; without the profile key, the stock-flat refusal is unchanged | gate_a / gate_a_check test |
| S4-6 | With run 4's carried book and `now` after `flatten_start`, the first planned round has an EXIT target for every held name, at least one mandatory `TERMINAL_FLATTEN` SELL quote request or intent, and no BUY | planner test |
| S4-7 | **Red on base.** On canonical, with a non-zero SKHYB `router_allowance_units` and NVDAB worth more, the first mandatory request is NVDAB. After the fix it is SKHYB. With no allowance field, the order equals canonical's | planner test |
| S4-8 | `MarketPort` attaches `router_allowance_units` per stock from the verifier's single-block read, and omits them if the read fails, without failing the observation | market port test |
| S4-9 | The full pinned suite passes with no new failures against canonical | full suite |
| S4-L1 (live, team) | Run 5 installs from the export. Its first round sells SKHYB, the name with the allowance, then the other names; every position reaches dust before `signing_end`; balance check `MATCH`; all router allowances end at 0 | trading-status, chain monitor, BscScan |

## Results

(none yet)
