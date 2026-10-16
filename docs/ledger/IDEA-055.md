# IDEA-055 — Minimal chain-balance reconciliation: detect a mismatch and stop new risk (#36)

- Date / owner: 2026-10-15 SGT / design drafted with Claude Code at the user's request. Owners to agree before anything is built: Isaac (C, balance observation), Keegan (B, comparison and planner effect), Yao Zhu (D, scheduling, journal, health gate), as named in the #36 status of 2026-10-15.
- Status: built (minimal version, B1–B10 PASS); owner decisions recorded 2026-10-16 (D2 and D4 changed to "chain wins", D5 extended; see "Owner decisions"); self-healing reconciliation to be built in PR 4 and RPC failover in PR 5
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

## Build (2026-10-15, Claude Code session at the user's request: "build the entire minimal design; make the best decision for each area")

The user asked for the design to be built now instead of waiting for the owners' agreement. The decisions below are made here, with reasons. They stay open to the owners' review: Isaac, Keegan and Yao Zhu can overrule any of them in review before merge. Facts checked in the code before deciding:
- `larp/execution_live/settlement.py` books token units as raw chain units (no scaling), floors USDT credits from 18 to 6 decimals (`cash_raw // 10**12`, dust stays on chain), and refuses any BNB or USDT debit that is not exact in the ledger scale. So the ledger never exceeds the chain without a defect, and USDT rounding dust shows up as a surplus.
- The runtime has no RPC client; `larp-execution` has one (`execution_live/main.py`). The planner's global gates are a fixed list (`larp/risk/planner.py`); `new_spending_ok` is `all(gates)` (`RuntimeHealth`). Replay feeds the recorded health back (`larp/integration/replay.py`), and it rebuilds the projection from journaled events.
- Live gas policy (`larp/strategy/profiles.py`): floor = 6 × the largest approve+swap gas; a top-up receives 2 × the floor. So BNB held is at most about 3 × the floor.

### Decisions

| ID | Decision | Reason |
|---|---|---|
| D1 | Cap. While a deficit is recorded, the planner sees `max(0, ledger − deficit)` for every asset (stocks, USDT, BNB). This is a view in `ContextBuilder`; the journaled ledger is never changed. | Subtracting the recorded deficit, instead of capping at the chain units of the last read, stays correct after a capped sale settles: the ledger then falls by the fill while the deficit stays, so the leftover phantom units are always 0 in the view and produce no order. Equity in the view is lower (conservative). |
| D2 | Surplus is recorded only, with one `BALANCE_SURPLUS` incident per newly surplus asset. It does not block. | USDT dust from floored credits is a normal surplus; equity is understated (conservative); Q-20 says never touch unsolicited tokens. |
| D3 | Deficit tolerance is zero after flooring chain units to the ledger scale. | Settlement books exact or floored units (above), so any shortfall is real. |
| D4 | A persistent deficit keeps new spending blocked for the rest of the run. It clears only when a later comparable check finds no deficit. | No one can fix the ledger during the run (F-114); adopting chain values automatically waits for Q-20. |
| D5 | `balance_check_interval_ms` = 600 000 (10 min), `balance_check_max_age_ms` = 1 800 000 (30 min), retry after 60 s when a check was skipped or failed. Required in `dev`/`live` together with `balance_rpc_url` and `balance_rpc_source_id`; a start without them is refused (exit 4). | About 16 RPC calls per check (finalized block, re-check, native balance, `decimals` and `balanceOf` for six contracts, two nonces). The max age allows two missed checks before new spending stops. |
| D6 | **Changed from the design's recommendation.** Keep the profile's BNB price (its provenance is the pinned `QuoteCostSummary` capture hash and time inside the manifested profile), do not value BNB at zero, and pin the error bound with a test. | Valuing BNB at zero turns every gas top-up into a loss of its USDT cost, about 1–2 % of equity, which feeds the 3 % daily and 8 % run loss latches. With BNB held ≤ floor + one top-up, a 20 % BNB move changes equity by a fraction of a percent. A test fails if a profile ever makes BNB material (> 5 % of expected equity). |

### Components

1. **C, `larp/execution_live/balances.py` `read_balances(rpc, wallet, observed_at)` → `ChainBalances.v1`.** It checks the chain ID, reads the finalized block, then the native balance, `decimals()` and `balanceOf(wallet)` for USDT and the five bStocks at that numeric block, then re-checks the block hash and reads the latest and pending nonce. `Rpc.call` (`chain.py`) allows `eth_call` only as `[{to, data}, <hex block>]` with `to` in the pinned set and `data` exactly `decimals()` or `balanceOf(<address>)`. ABI words are parsed as 32-byte values.
2. **B, `larp/risk/reconcile.py`.** `compare_balances(ledger, observation, settled_block)` → `BalanceCheck.v1` (`MATCH`, `SURPLUS_ONLY`, `DEFICIT` or `SKIPPED` with `PENDING_NONCE` / `BLOCK_BEHIND_LEDGER`). An unknown or mis-scaled asset raises `ContractError`. `spendable_view(ledger, deficits)` gives the planner's view.
3. **B/D, `larp/integration/settlement.py`.** `settle` records `projection.settled_block`, the highest receipt block it has applied.
4. **D, `larp/runtime/driver.py` `BalanceCheck`.** It runs in `RoundDriver.once` after the hand-off wait and before the day roll and round. With reservations, an open round or an execution pending, it reads nothing and writes nothing (in-flight skip, retry in 60 s). Otherwise it reads, compares and journals `BALANCE_CHECKED` (also when the read fails: `SKIPPED: RPC_UNAVAILABLE` or `OBSERVATION_INVALID`), plus an `INCIDENT` for a deficit or a newly surplus asset. `projection.balance_check` keeps the status, the last deficits (a skip keeps them), the surplus assets, `checked_ms` and `ok_ms`. `ok(projection)` is true only for a `MATCH`/`SURPLUS_ONLY` check made by this process and younger than the max age. `BALANCE_CHECKED` is added to `RECORDED_FACTS`.
5. **D, `RuntimeHealth(…, balances=BalanceCheck)`** adds `balances_ok`. Without one (offline fixtures) the gates are unchanged. **`ContextBuilder`** applies `spendable_view` from `projection.balance_check`. **`build_driver`** wires an `Rpc` from the new settings (artifacts under `<market_artifact_root>/chain`), and refuses a `dev`/`live` start without them. **`runtime.example.json`** gets the four keys (URL and source ID null, D5 values).

### Pass criteria (recorded before any test is written)

Synthetic RPC and market, disposable PostgreSQL; no credentials, network, signing or upload. The tests are pushed first and must fail on the unchanged code (missing modules or behaviour); then the build is pushed and they must pass.

| ID | Check |
|---|---|
| B1 | `read_balances`: every read uses the same numeric finalized block; the result names it, its hash, each asset's raw units and decimals, and both nonces. A hash change before the re-check, or a chain ID other than 56, refuses (`Blocked`). `Rpc.call` refuses an `eth_call` with another selector, another contract, a `latest` tag, extra fields or a malformed address, and accepts the two allowed forms. |
| B2 | `compare_balances`: equal → `MATCH`; USDT dust above → `SURPLUS_ONLY`; a stock or BNB below → `DEFICIT` with the exact difference; pending ≠ latest nonce → `SKIPPED: PENDING_NONCE`; block < `settled_block` → `SKIPPED: BLOCK_BEHIND_LEDGER`; a held symbol missing from the observation, or ledger decimals above chain decimals → `ContractError`. `spendable_view` subtracts deficits, never below zero, and leaves the input unchanged. |
| B3 | Driver, startup: before this process's first check, `new_spending_ok` is false; after a `MATCH` it is true; a `MATCH` journaled by an earlier process (restore or restart) does not count. |
| B4 | Surplus: an unsolicited stock surplus is journaled with one `BALANCE_SURPLUS` incident (not repeated on the next check); `balances_ok` stays true; the journaled ledger is unchanged. |
| B5 | Deficit (restore divergence): `DEFICIT` with one `BALANCE_DEFICIT` incident; `new_spending_ok` false; the round's policy input shows the reduced units; a mandatory sale of the deficit symbol is planned for at most the chain units (never the ledger units), while the global gates stay open. After a sale of the chain units, the view of the leftover is 0. |
| B6 | Stale or unavailable: an RPC failure journals `SKIPPED: RPC_UNAVAILABLE`; `balances_ok` stays true until the max age passes, then turns false; a later `MATCH` restores it. With reservations or an open round, nothing is read or journaled. |
| B7 | BNB bound: for the live profile builder, (gas floor + top-up receive) valued at the summary's BNB price is ≤ 5 % of `expected_equity_units`. |
| B8 | Replay of a run with checks, incidents and a deficit reproduces the head; `settled_block` follows applied receipts; no check ever changes the journaled ledger or balances. |
| B9 | Configuration: a `dev` driver without the four settings is refused; with them it builds a `BalanceCheck` wired into `RuntimeHealth`; `runtime.example.json` names all four; `offline` drivers build as before. |
| B10 | Full suite: the base count plus only these tests, no new failure or skip. Mutations, each reverted, must each be caught: drop the in-flight skip; compare without flooring; count an earlier process's check; let `spendable_view` go negative; apply the deficit to the journaled ledger; drop `balances_ok` from `RuntimeHealth`. |

### Results (2026-10-15)

Criteria pushed at `292b1e9`; red tests at `021931c`; test corrections at `c853a36`; build at `3b8a4bc`; runbooks and GAP-14 at `707d0f2`. Synthetic chain and market, disposable PostgreSQL 16.15, Python 3.12.3 venv from `deploy/requirements-test.lock`, Linux container. No credentials, network, signing or upload.

- **Red first:** at `021931c`, 17 of 18 tests failed for the predicted reasons (missing `balances`/`reconcile` modules, `BalanceCheck`, `balance_settings`, `settled_block`, `balance_check` attribute, example keys). B7 passed, as expected: it pins a bound the current profiles already meet.
- **Two test corrections before the counted run** (`c853a36`):
  1. B5 read the round from `round_records`, but a round whose capped sale only requests a quote closes at once and leaves that map. It now reads the round's `ROUND_PLANNED` record.
  2. A build review found that journaling every check would add one full projection copy per interval (about 4,300 per month). `BalanceCheck` now journals a check only when it is the process's first, when its outcome changes, or hourly, and keeps the last good time in memory (the gate trusts only this process's checks anyway). B3 was changed to expect that. No other test was changed.
- **Mutations**, each reverted, each caught:

  | Mutation | Failures |
  |---|---|
  | No in-flight skip | 2 |
  | Compare without flooring | 6 |
  | Count an earlier process's check | 1 |
  | `spendable_view` goes negative | 1 |
  | Deficit written to the journaled ledger | 1 |
  | `balances_ok` dropped from `RuntimeHealth` | 4 |
  | No deficit view in `ContextBuilder` | 1 |
  | `settled_block` not recorded | 1 |
  | `eth_call` unrestricted | 7 |

- **Full suite:** base `b6ab0a9` 1518 passed, 8 skipped, 2123 subtests. This branch at `3b8a4bc`: **1536 passed, 8 skipped, 2143 subtests** (+18 tests, +20 subtests: this change only). The skips are the same eight environmental ones. Mirror CI not run.

| ID | Result | Evidence |
|---|---|---|
| B1 | PASS | `Observation.test_b1_*`, `RpcAllowlist.test_b1_*` (7 refused forms) |
| B2 | PASS | `Comparison.test_b2_*` (MATCH, dust floored, SURPLUS_ONLY, DEFICIT with exact differences, PENDING_NONCE, BLOCK_BEHIND_LEDGER, unknown asset, finer ledger, view) |
| B3 | PASS | `Startup.test_b3_*` (no new spending before this process's check; a restarted process re-checks; one check per interval, journaled on change or hourly) |
| B4 | PASS | `Surplus.test_b4_*` |
| B5 | PASS | `Deficit.test_b5_*` (DEFICIT + incident; view 1500; `new_spending_ok` false; no `EXECUTION_BLOCKED`; the only NVDAB sale is for 1500; ledger unchanged) |
| B6 | PASS | `Stale.test_b6_*` (RPC failure journaled; gate holds until the max age, then closes; retry restores it; nothing read or journaled while in flight) |
| B7 | PASS | `BnbBound.test_b7_*` |
| B8 | PASS | `Replay.test_b8_*` (replay head equal; `settled_block` = highest applied receipt block in the end-to-end signed flow) |
| B9 | PASS | `Settings.test_b9_*`, `Composition.test_b9_*` |
| B10 | PASS | full suite and mutations above |

**Still open**
- Owners' review of D1–D6 (Isaac, Keegan, Yao Zhu); they can overrule any decision before merge.
- Mirror CI.
- On the first hosted run: a manifested BSC RPC that supports the `finalized` tag, and egress to it from the primary host.
- Q-20 for automatic adoption of dividend or split adjustments.

### Mirror CI (2026-10-15)

Org Actions is out of funds, so CI ran in the private mirror `Keegan4/keegan4-larp-ci-mirror`: the workflow is unchanged, on GitHub's own runners, with branches pushed by Keegan. This is mirror evidence, not org-repo CI.
- **This branch at `608b85b`** (merge of `02e2be9` into the build): [run 38772178760](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/38772178760). **All four jobs passed, every step.**
  - runtime: `pip check`, full pytest on Python 3.12.15 / PostgreSQL 14.24, real systemd, offline demo, Docker build and smoke test;
  - host bundle: build plus the provisioning test;
  - Terraform: `deploy/aws` and `deploy/bootstrap` fmt, init, validate and test.
- **Base `02e2be9`**: [run 38772174598](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/38772174598), all four jobs passed.

### #96 follow-up (2026-10-16, Claude Code session at the user's request)

- `read_balances` takes an optional `decimals` cache. `build_driver` passes one per process, so each token's `decimals()` is read and checked once, and later checks make 12 RPC calls instead of 18. An implausible value (> 77) is still refused and never cached. Test: `tests/runtime/test_balance_reconciliation.py::Observation::test_decimals_are_read_once_per_cache`.
- The `build_driver` comment now says the settings are refused "before any port makes a request" (the ports are already constructed by then).
- Disk budget for the chain observations is in `docs/build/architecture-deployment.md` (estimate: 10–15 MiB a day normally, about 2 GiB over the run in the worst case; budget 3 GiB). Measure it at Gate A together with #60.
- 2026-10-16 correction (Claude Code): D5's "about 16 RPC calls per check" was 18 before this change and is 12 after it.
- 2026-10-16 correction (Claude Code, PR #99 review): a decimals value is now reused only after two consecutive reads agree (`DecimalsCache`). One bad but plausible RPC answer could otherwise have been kept for the life of the process, giving a false DEFICIT on every check, and restarts are automatic only (F-124). Checks make 18 calls until two reads agree, then 12. Tests: `Observation::test_decimals_are_reused_once_two_reads_agree` and `test_one_bad_decimals_answer_is_never_kept` (these replace `test_decimals_are_read_once_per_cache`).

## Owner decisions (2026-10-16, Yao Zhu leading the #90 review)

Made by Yao Zhu (section D owner in tracking PR #109, leading the #90 review) on 2026-10-16 and recorded here as given. Isaac (C: balances, `chain.py`) and Keegan (B: `reconcile.py`, settlement) are the named owners of the code these decisions change; they can still comment in the review of PR 4 and PR 5.

**Guiding principle.** The contest goal is maximum profit (F-43). Data and ledger errors should correct themselves so the agent keeps trading. The stops that protect money stay: the 3 % daily and 8 % run loss stops, the end-of-run flatten window and the new-risk end time.

### D1–D6

| ID | Outcome | Decision | Reason | Code |
|---|---|---|---|---|
| D1 | **Confirmed** | Sales of a symbol in deficit are capped (`spendable_view`). This still applies in the short window between detecting a mismatch and adopting it. | Phantom ledger units must never become an order that reverts. | PR 4 (kept for the window) |
| D2 | **Changed: adopt surplus** | A surplus on our own assets (the five eligible bStocks NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB, plus USDT and BNB) is adopted into the ledger. Unsolicited tokens outside that set are never adopted, sold or touched (never-do #4, G-13); they are logged only, as today. | A surplus on our own assets is real value we sell at the end: a dividend Multiplier top-up, a forward split, USDT dust. Leaving it out of the ledger leaves it unsold at the flatten. | PR 4 |
| D3 | **Confirmed** | Zero tolerance after flooring chain units to the ledger scale. | Settlement books exact or floored units, so any difference is real. | — (unchanged) |
| D4 | **Changed: "chain wins", keep trading** | A deficit no longer means "no new risk for the rest of the run". The ledger is re-synced to the chain through an appended, journaled balance-adjustment event, and trading continues. History is never rewritten: the audit needs it (F-47, F-48), and "reverting to a previous state" is not possible because the chain is the truth. An adopted deficit is a real loss and flows into equity, so the existing loss stops are the backstop against a wallet that keeps draining (key compromise, systematic bug). There is no separate deficit stop. | Blocking new risk for the rest of the run on a ledger error forfeits the run's profit (F-43); the loss stops already bound a real drain. | PR 4 |
| D5 | **Confirmed, made more robust** | 10-minute interval, 30-minute maximum age, and a 60 s retry after a failed or skipped check. Add an ordered list of balance RPC providers with failover; a check counts as failed only when every provider fails. New buys pause only when no check succeeded within 30 minutes, and resume automatically on the next good check. Sales and the flatten are never blocked by this. | One RPC outage should not pause buying. | PR 4 (scheduling), PR 5 (failover) |
| D6 | **Confirmed** | BNB is valued at the profile price; the ≤ 5 % of expected equity test stays. | As in the build record: valuing BNB at zero books every top-up as a loss. | — (unchanged) |

**#84 review point (gas top-ups gated by `new_spending_ok`): resolved.** An adopted BNB deficit no longer blocks top-ups after adoption, and the first-gas swap is sized to cover the whole run (SKILL.md F-120 reading), so agent top-ups are a backup only. Code: PR 4.

### Safety limits on adoption (both required)

1. **Two consecutive comparable checks agree.** Both on finalized blocks at or after `settled_block`, both showing the same chain units for that asset, and the ledger for that asset unchanged between them. One bad RPC answer must never become the ledger (the same idea as `DecimalsCache`). After a first mismatch, the confirming check is scheduled after about 60 s, not the full 10 minutes. Code: PR 4.
2. **Nothing in flight for that asset.** No reservation, pending execution or unsettled receipt touching it, during or between the two checks. Code: PR 4.

### Price-jump guard (new)

Splits change the price and the token count at the same moment, but the balance check lags by up to 10–20 minutes. Example: we hold 0.25 TSLAB at $400 and a 2-for-1 split makes it 0.5 at $200. The agent values 0.25 × $200 = $50, thinks it lost 25 % of 200 USDT equity, and the latched loss stops fire. So, when a held symbol's mark moves ≥ 30 % between consecutive rounds (a driver setting, `price_jump_check_bps` = 3000, not a profile field):
- run an immediate balance check;
- send no new orders for that symbol (buys or sales) until a comparable check after the jump completes (MATCH, or an adopted adjustment after the two-check confirmation);
- do not evaluate or latch the daily or run loss stops while any held symbol is in that state.

If the check cannot complete within the 30-minute maximum age, behaviour falls back to normal: the loss stops evaluate on the marks as they are. Reverse splits (the price doubles, so the agent briefly looks richer and could oversize buys) are covered by the same guard. Code: PR 4.

### Accounting for an adjustment

- Units are set to the chain value; the position's total cost is unchanged. A dividend or split lowers the average cost; a deficit raises it. Equity is marked to market as usual.
- An adjustment is not a trade and not a round, so it gets no ai-seeds round log (G-19 covers rounds).
- It is recorded in the journal plus an incident `BALANCE_ADJUSTED` with asset, `ledger_before`, `chain_units`, `delta`, both block numbers and observation hashes, and reason `SURPLUS` or `DEFICIT`. Replay must reproduce it exactly.

Code: PR 4.

### #94 / Q-20 (dividends and splits)

Resolved by D2 and D4: a dividend Multiplier or split change on our assets is adopted through the same adjustment, so #94 does not wait for the organisers. The team position on Q-20 is recorded in SKILL.md (adopt balance-only changes on our own assets; never touch unsolicited tokens). How the organisers count them in equity is still open, so Q-20 stays open for that part only. #94 closes when PR 4 merges.

## Self-healing reconciliation (PR 4, 2026-10-16): chain wins, two safety limits, price-jump guard

Builds the owner decisions above (D2 and D4 changed, D5 scheduling; the #84 top-up point). Built by a Claude Code session at Yao Zhu's request; Isaac (C) and Keegan (B) review. PR 5 adds the RPC failover. Pass criteria are committed before any test or code.

### Design

1. **Eligible assets only (B, `larp/risk/reconcile.py`).** `compare_balances` classifies only USDT, BNB and the five eligible bStocks. Any other token in an observation is listed under `unsolicited`, never in `surplus` or `deficits`, and can never be adopted. `read_balances` reads only the pinned contracts anyway, so this is a second guard.
2. **`adjust_ledger(portfolio, adjustments)` (B), pure.** It sets each adjusted asset's units to the chain units: `cash_units` for USDT, `bnb_units` for BNB, `positions[s].units` for a bStock (a missing eligible position is created with the chain decimals and zero cost). The position's `cost_basis_units` is unchanged, so a dividend or split lowers the average cost and a deficit raises it. It refuses any other asset. The input is not changed.
3. **Adoption (D, `BalanceCheck` in `larp/runtime/driver.py`).**
   - **First mismatch.** A comparable check (MATCH, SURPLUS_ONLY or DEFICIT) that shows an eligible asset off the ledger records a candidate in memory. The candidate holds the chain units, ledger units, block number and hash, observation hash, `settled_block`, and the store version after this check's own commits. Detection is journaled as today: `BALANCE_CHECKED`, plus `BALANCE_DEFICIT` / `BALANCE_SURPLUS` incidents. The confirming check is scheduled `retry_ms` (60 s) later, not after the 10-minute interval.
   - **Confirmation (limit 1).** The next comparable check adopts an asset only when all of these hold:
     - it shows the same chain units;
     - the ledger units for that asset are the same;
     - `settled_block` is the same;
     - its block is at or after the first block (both are at or after `settled_block`, or `compare_balances` would have skipped);
     - **nothing else was committed to the run between the two checks** (the store version is unchanged), so no round, reservation, execution observation or receipt came in between (limit 2).
     Otherwise the newer read replaces the candidate and is confirmed 60 s later. Both checks still read nothing while anything is in flight: reservations, an open round, an execution pending or a pending nonce (existing skip). A candidate is kept in memory only, so a restarted process re-reads twice before it adopts (the same rule as the B3 gate).
   - **Adoption.** One `BALANCE_ADJUSTED` journal event with the adjustments and the new projection: `portfolio` from `adjust_ledger`, `balances` rewritten to agree, and the `balance_check` state without the adopted deficits and surplus assets. Then one `INCIDENT` per asset, of type `BALANCE_ADJUSTED`, carrying asset, `ledger_before`, `chain_units`, `delta`, both block numbers, both observation hashes and reason `SURPLUS` or `DEFICIT`. It is not a trade or a round: no round, intent, audit (ai-seeds) event or fill is created. `BALANCE_ADJUSTED` is a recorded fact on replay. Replay recomputes `adjust_ledger` from the previous projection and the event's adjustments, and refuses the batch (`IntegrityError`) if the journaled portfolio differs.
   - **Gate.** `balances_ok` is true when this process's latest comparable check is younger than the maximum age and leaves no unadopted DEFICIT. Between detecting a deficit and adopting it (about 60 s), new spending stays paused as in the minimal build, and that asset's sales are capped (D1). After adoption, new buys and gas top-ups resume. Sales and the flatten are never blocked by the gate. **Interpretation flagged for Yao Zhu:** D5 says buys pause "only when no check succeeded within 30 minutes". This keeps one more, short pause: the unconfirmed-deficit window. It exists so a single bad read cannot size buys from phantom units before the second read confirms or clears it.
4. **Price-jump guard (D builder and driver, B planner).**
   - **Detection (`ContextBuilder`).** When `price_jump` is configured (`bps` from the new driver setting `price_jump_check_bps`, `hold_ms` = `balance_check_max_age_ms`), each round compares every usable mark with the last mark journaled in `projection.marks`. A symbol held in the journaled ledger whose mark moved by at least `bps` of the previous mark gets a hold in `projection.price_jump`: reference (previous) price, new price, `jump_ms` and `until_ms` = `jump_ms + hold_ms`. The round's context carries `price_jump_hold` = {symbol: reference price} for every hold still active. Both updates are part of the round batch, so replay recomputes them. Without the setting nothing changes, and existing contexts keep their bytes.
   - **Planner.** For each held symbol under an active hold:
     - no order is planned (its sale requirement is `BLOCKED_PRICE_JUMP`, its discretionary target is rejected `PRICE_JUMP_HOLD`), and it does not stop other symbols' discretionary trades;
     - it is valued at min(reference, current) for sizing and caps, so a reverse split cannot oversize buys and a forward split cannot make the book look over-weight;
     - `update_risk` is not run: the daily, run and deep-cut latches, and the peak, stay as they were. The plan reports `loss_stops_deferred`.
   - **Immediate check (driver).** `BalanceCheck.due` is true as soon as a hold exists that is newer than this process's last check attempt.
   - **Clearing (`BalanceCheck`).** A comparable check made after `jump_ms` clears the hold when that asset is MATCH, or when it is adopted after the two-check confirmation.
   - **Fallback.** A hold past `until_ms` is dropped from the context, and the loss stops evaluate on the marks as they are.
   - **Day roll.** `DayRoll` does not roll while a hold is active (`PRICE_JUMP_HOLD`); it rolls on a later cycle within its window.
5. **Settings.**
   - `driver.price_jump_check_bps`: an integer from 1 to 10 000. It is required in `dev`/`live` together with the four balance settings (a start without it is refused, exit 4). `runtime.example.json` sets 3000.
   - `build_driver` passes `price_jump` to the builder in the existing balance block. That is a two-line edit; nothing else in `build_driver` changes.

### Pass criteria (recorded before any test is written)

Synthetic chain and market, disposable PostgreSQL; no credentials, network, signing or upload. The tests are pushed first and must fail on the code without this change; then the build is pushed and they must pass.

| ID | Check |
|---|---|
| S1 | Unsolicited token: an observation with a token outside the seven assets lists it under `unsolicited`; it is never in `surplus` or `deficits` and does not change `status`. End to end, it is never adopted or written to the ledger. |
| S2 | `adjust_ledger`: units set to the chain units for USDT, BNB and a held stock; `cost_basis_units` unchanged; a missing eligible position is created with zero cost; the input is not changed; an asset outside the seven is refused (`ContractError`). |
| S3 | A single bad RPC read is never adopted: a mismatch seen once and then a MATCH adopts nothing. Two mismatching reads with different chain units adopt nothing; the newer read becomes the candidate and is adopted only after it is read again. |
| S4 | After a first mismatch the confirming check runs about 60 s later (`retry_ms`), not after the 10-minute interval. |
| S5 | In flight: a round planned between the first and the confirming check (a commit and a reservation) prevents adoption at that check. Adoption follows only after two agreeing checks with nothing committed between them. While reservations exist, nothing is read. |
| S6 | Dividend Multiplier +0.5 %: NVDAB 2000 → 2010 on chain is adopted at the confirming check. The ledger and `balances` read 2010, the cost basis is unchanged, there is one `BALANCE_ADJUSTED` event and one incident with every field (reason SURPLUS), no audit event or round is added, and `new_spending_ok` stays true. |
| S7 | USDT dust: chain cash 3 units above the ledger is adopted (reason SURPLUS). |
| S8 | Restore from an old backup (deficit): ledger above the chain. The first check pauses new spending and caps the sale (D1). The confirming check adopts the chain units (reason DEFICIT). `new_spending_ok` is true again, and a later round's policy input shows the adopted units and open gates (trading resumes). |
| S9 | BNB deficit: before adoption, a top-up is refused `GAS_TOP_UP_SPENDING_BLOCKED`. After adoption, `new_spending_ok` is true and the same top-up plan is no longer refused for spending (it requests its quote). |
| S10 | Backstop: a large adopted deficit (USDT 10 % of equity) makes the next round latch the run loss stop (`run_halt`). |
| S11 | Forward split 2:1 (driver, PostgreSQL). The NVDAB mark halves in a round: a hold is set; that round plans no NVDAB order; its risk state keeps every latch false and the peak unchanged. The next cycle checks immediately; the confirming check adopts 4000 units and clears the hold. The next round has no loss stop latched. At the flatten, the NVDAB requirement covers all 4000 units and the sale is planned for 4000. |
| S12 | Reverse split 1:2. Planner: with a hold on NVDAB at its reference price, the MSFTB buy is no larger than with no jump, NVDAB gets no order, and no latch or peak changes. Driver: the adopted 1000 units clear the hold, and the next round latches no run stop (the peak was never raised). |
| S13 | Fallback: with no comparable check before `until_ms`, the hold leaves the context and the loss stops evaluate on the marks as they are (the forward-split drop latches the daily stop). |
| S14 | Day roll waits while a hold is active (`PRICE_JUMP_HOLD`) and rolls once it has cleared. |
| S15 | Replay of a run with checks, an adoption, holds and incidents reproduces the journal head exactly. A tampered `BALANCE_ADJUSTED` (portfolio not equal to `adjust_ledger` of the previous one) is refused (`IntegrityError`). |
| S16 | Configuration: `dev`/`live` without `price_jump_check_bps`, or with 0 or more than 10 000, is refused. The example sets 3000. `build_driver` gives the builder `price_jump` with `hold_ms` equal to the maximum age. Offline drivers build as before. |
| S17 | Full suite: the base count plus only these tests and the updated IDEA-055 tests, with no new failure or skip. Each mutation below, reverted after, must be caught: adopt after one read; ignore a commit between the checks; adopt an unsolicited token; change the cost basis on adjustment; plan orders for a held symbol under a hold; run `update_risk` under a hold; value a held jumped symbol at the current mark; never expire a hold; keep `balances_ok` false after an adopted deficit; skip the replay check of `BALANCE_ADJUSTED`. |

**Existing tests this changes (old D2/D4 behaviour):**
- B4 (`Surplus.test_b4_*`) asserted that a surplus is never adopted and the ledger is unchanged after two checks. It becomes "recorded once, adopted at the confirming check": the incident is still not repeated, and `new_spending_ok` stays true.
- B5 (`Deficit.test_b5_*`) keeps its first-check assertions (that is the D1 window), and its name and docstring say so.
- The design's prospective R4/R5 (no adoption; no new risk for the rest of the run) and B10's mutation "deficit written to the journaled ledger" are superseded by S6–S8 and S17.
