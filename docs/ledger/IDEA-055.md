# IDEA-055 — Minimal chain-balance reconciliation: detect a mismatch and stop new risk (#36)

- Date / owner: 2026-10-15 SGT / design drafted with Claude Code at the user's request. Owners to agree before anything is built: Isaac (C, balance observation), Keegan (B, comparison and planner effect), Yao Zhu (D, scheduling, journal, health gate), as named in the #36 status of 2026-10-15.
- Status: open (design only; nothing built; decisions D1–D6 below are open)
- Links: #36 (R14, P1); IDEA-049-B item 007; IDEA-049-C C-OPEN-008; IDEA-049-D D-REQ-039; IDEA-039 / PR #74 (`gate_b probe-chain`); SKILL.md Q-20, F-95, F-114, F-117; inferences.md I-28; plan.md G-43.

## What and why

The ledger (`projection.portfolio`: `cash_units`, `bnb_units`, `positions[*].units`) changes only through the settlement reducer, from this agent's own finalized receipts. Nothing compares it with what the chain holds. If the two drift apart, the planner sizes orders, loss limits and terminal flatness from wrong numbers. Ways it can drift:
- balance changes with no trade: unsolicited transfers, or a dividend multiplier that shows up as a balance change (Q-20 is open; I-28 says to expect such changes);
- a restore from a backup older than the chain;
- an accounting defect (for example #46 before its fix).

Separately, the BNB mark in `equity()` (`larp/strategy/schema.py`) is `ledger.bnb_price_units`, which comes from the `QuoteCostSummary.v1` when the profile is built (`larp/strategy/profiles.py`). So it is fixed for the whole run and carries no timestamp.

No person can fix the ledger during the scored run (F-114, F-117), so the agent must notice on its own and fail safe.

**Scope of "minimal":** detect, journal and stop new risk. Mandatory sales and the flatten keep running. It never writes chain values into the ledger and never invents a fill (#36 remedy). Automatic adoption of supported adjustments (dividend multiplier, splits) is out of scope until Q-20 is answered.

## Design

### 1. Observation (C, Isaac): `ChainBalances.v1`, read-only, bound to a finalized block

- The kit's `balance/token-balances-by-address` (F-95; `WebPort.balances` in `larp/marketdata/port.py`) returns values with no block identity, so a comparison could not tell an old read from a missed receipt. It may be logged as a cross-check, but it is not the source.
- Source: the manifested RPC (`larp/execution_live/chain.py` `Rpc`). Extend `probe_chain`'s pattern (`larp/execution_live/gate_b.py`):
  1. Read the finalized block number and hash.
  2. Read `eth_getBalance(wallet, height)`.
  3. Read `eth_call` of `balanceOf(wallet)` (selector `0x70a08231`) at `height` for exactly the six pinned contracts: USDT plus the five bStocks in `TOKENS`.
  4. Re-check that `height` is still canonical with the same hash.
  5. Read the latest and pending nonce.
- Allowlist change: `eth_call` is added only for that selector, the wallet as the sole argument, and the pinned contract set at a numeric block tag. Any other `eth_call` is refused, like the rest of `METHODS`.
- Output: chain ID, wallet, block number and hash, raw integer balances per asset with each contract's on-chain decimals, nonces, and the artifact hash. It never contains a key or credential. About 10 RPC calls per check.

### 2. Comparison (B, Keegan): a pure function `compare_balances(ledger, observation, settled_block)` → `BalanceCheck.v1`

- **Comparable only when nothing is in flight.** That means no reservations, no non-terminal `execution_records`, latest nonce equal to pending nonce, and an observation block at or after `settled_block`, the highest block of any receipt the ledger has applied. Otherwise the result is `SKIPPED` with a reason (`IN_FLIGHT`, `PENDING_NONCE`, `BLOCK_BEHIND_LEDGER`), not a mismatch.
- **Scale.** Convert the chain's raw units to ledger units with `floor(raw / 10**(chain_decimals - ledger_decimals))`. B must confirm the ledger floors every fill this way. If it does, chain ≥ ledger always holds without drift, so any shortfall is real.
- **Per-asset class:**
  - `MATCH`: equal after flooring.
  - `SURPLUS`: chain > ledger. Recorded only, never adopted (Q-20 working assumption "log all; never touch unsolicited tokens"). Equity is then understated, which is the conservative side.
  - `DEFICIT`: chain < ledger.
- **Result:** `MATCH`, `SURPLUS_ONLY` or `DEFICIT`, with each asset's ledger units, chain units and difference.

### 3. Effect (B and D): one non-global health gate

- `RuntimeHealth` (`larp/runtime/driver.py`) adds `balances_ok`. It is true only when the latest journaled check is `MATCH` or `SURPLUS_ONLY` and is younger than `balance_check_max_age_ms`.
- `new_spending_ok` already requires every gate, so a false `balances_ok` blocks entries (planner BUY) and gas top-ups (`plan_top_up`) with no planner change.
- `balances_ok` is **not** added to the planner's global list (`integrity_ok`, `journal_ok`, `ownership_ok`, `clock_ok`), so mandatory sales, Class 1 exits and the flatten continue. This avoids the #34 problem, where a HALT suppresses mandatory planning. It is deliberately not a HALT reason.
- At startup, `balances_ok` is false until the first comparable check, so a restored or restarted run takes no new risk before it has reconciled.
- It recovers on its own: a later `MATCH` restores new spending, for example after a skipped or stale read. A deficit that persists keeps new spending blocked for the rest of the run (D4).
- **Deficit and sales (D1):** a sale for a symbol in `DEFICIT` is sized to at most the chain units from the latest comparable check. Phantom ledger units therefore never become an order that reverts. After a capped sale settles, the leftover phantom units produce sales of zero, which is no intent.

### 4. Scheduling and journal (D, Yao Zhu)

- The driver runs the check once at service start, before the first round, and then every `balance_check_interval_ms` in a cycle with nothing in flight. It runs in the same place as the day roll: after the hand-off wait, before `work.next`.
- Each result is journaled as `BALANCE_CHECKED`, including `SKIPPED` results: block, classes, differences, observation artifact hash. It becomes a recorded fact for replay (`RECORDED_FACTS` in `larp/runtime/replay.py`, like `DAY_ROLLED`).
- A `DEFICIT`, or the first `SURPLUS` for an asset, also commits an `INCIDENT` (`BALANCE_DEFICIT` / `BALANCE_SURPLUS`), so a non-trade balance change is logged as one (I-28, G-43).
- An unavailable RPC is `SKIPPED: RPC_UNAVAILABLE`. Once the last good check is older than the maximum age, `balances_ok` turns false: new spending stops and sales continue.
- New `runtime.json` keys: `balance_check_interval_ms` and `balance_check_max_age_ms`. Both are required in `dev`/`live`, null in the example until the team sets them, as with `day_roll_window_ms`.

### 5. BNB mark freshness (B)

- Value BNB in risk equity from a BNB observation fetched in the same cycle, with its `observed_at`, held to the profile's quote-age bound. When no fresh BNB mark exists, BNB counts as zero in risk equity. That is a lower bound, like `allow_missing` for unmarked stocks, and BNB is gas only.
- `bnb_price_units` from the profile stays the planning price for gas costs.

## Decisions to agree before building (owners, by the Oct 20 combined review)

| ID | Decision | Recommendation |
|---|---|---|
| D1 | Sales of a symbol in deficit: cap them at the chain units (§3), or block that symbol (`BLOCKED_INPUT: BALANCE_DEFICIT`) | Cap. Blocking leaves real holdings unsold at the flatten. The cap needs one planner input (`sellable_units`), and its block must be at or after `settled_block`. |
| D2 | Surplus: record only, or also stop new risk | Record only. Equity is understated, and a dividend-multiplier surplus would otherwise block trading for the rest of the run. |
| D3 | Deficit tolerance | Zero after flooring, if B confirms the reducer floors fills (§2). Otherwise B states the rounding bound. |
| D4 | A deficit that persists: accept "no new risk for the rest of the run", or adopt the chain value automatically | Accept for the minimal version. Automatic adoption needs Q-20's answer and a rule for which adjustments are supported. |
| D5 | `balance_check_interval_ms` / `balance_check_max_age_ms` | About 10 min / 30 min (about 10 RPC calls per check). |
| D6 | BNB mark: fresh mark or zero (§5), or keep the profile price | Fresh or zero. |

Q-20 (dividend multiplier, splits, unsolicited tokens) is open and the kit is silent on it (K18). It goes in the next batch of organiser questions (GAP-42). The minimal design is safe either way.

## Prospective acceptance (to be run when built; synthetic chain, disposable PostgreSQL)

| ID | Expected outcome |
|---|---|
| R1 | Observation: balances are read at one finalized block whose hash is re-checked; a reorg or hash change between reads refuses the observation; any `eth_call` outside the selector, wallet or contract set is refused; the artifact holds no credential. |
| R2 | Comparison: equal → `MATCH`; chain above → `SURPLUS_ONLY`, ledger unchanged; chain below → `DEFICIT`. Reservations, a non-terminal record, pending ≠ latest nonce, or an observation block before the last applied receipt → `SKIPPED`, never a mismatch. |
| R3 | Startup: until the first comparable check, `new_spending_ok` is false and a BUY is refused (`NEW_RISK_HALTED`); after a `MATCH` it is true. |
| R4 | Unsolicited transfer (surplus): journaled with an incident; entries continue; the ledger and orders are unchanged. |
| R5 | Restore divergence (deficit): a ledger restored with more units than the chain gives `DEFICIT` and an incident; entries and gas top-ups are refused; a mandatory sale of that symbol is sized to the chain units (D1) and settles; the leftover makes no order; Class 1 exits and the flatten of other symbols proceed. |
| R6 | Stale balance: the RPC is down past the maximum age → `balances_ok` false, sales continue; a later `MATCH` restores it. |
| R7 | Stale BNB valuation: with no fresh BNB mark, risk equity counts BNB as zero; with one, BNB is valued at it. |
| R8 | Replay reproduces every `BALANCE_CHECKED` and incident; no fill or ledger change ever comes from a check (mutation: writing chain units into the ledger fails a test). |

## Not in scope

- Automatic adoption of dividend-multiplier or split adjustments (D4, Q-20).
- Non-universe tokens: never touched, only logged if the cross-check endpoint reports them.
- Any transfer, sweep or withdrawal (never-do #3).
