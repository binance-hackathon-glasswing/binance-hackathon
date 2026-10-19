# IDEA-055 — Minimal chain-balance reconciliation: detect a mismatch and stop new risk (#36)

- Date / owner: 2026-10-15 SGT / design drafted with Claude Code at the user's request. Owners to agree before anything is built: Isaac (C, balance observation), Keegan (B, comparison and planner effect), Yao Zhu (D, scheduling, journal, health gate), as named in the #36 status of 2026-10-15.
- Status: built (minimal version, B1–B10 PASS); owner decisions recorded 2026-10-16 (D2 and D4 changed to "chain wins", D5 extended; see "Owner decisions"); self-healing reconciliation built in PR 4 (S1–S17 PASS locally, 1600 passed / 10 skipped); RPC failover built in PR 5 (F1–F9 PASS locally, 1612 passed / 10 skipped); provider URLs wait on #92
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

### Results (2026-10-16, PR 4)

Criteria at `c78a0b3`; red tests at `dd226c2`; build at `1530625`; three tests added after the mutation run at `09dc882`. Synthetic chain and marks, disposable PostgreSQL **16.15** (PostgreSQL 14 could not be installed: Ubuntu 24.04 ships only 16, and the PGDG repository is blocked by this session's network proxy), Python 3.12.3 venv from `deploy/requirements-test.lock`, Linux container. No credentials, network, signing or upload. Org CI was not used (Actions minutes exhausted).

- **Red first:** at `dd226c2`, 22 test functions failed for the predicted reasons. The confirming check is not run a minute later, so `balance_check` is missing from the summary. There is no `adjust_ledger`. An unsolicited token is counted as a surplus. The reverse split raised the peak to 220 USDT, and the forward split latched the daily stop. The day roll did not wait. The setting is missing, and the old B4 still saw no adoption.
- **Test corrections before the counted run:**
  1. S12's planner test compares the latches and the peak only, because the planner adds `cap_trims` to every risk state.
  2. The mutation run (below) showed three mutations were not caught, so three tests were added at `09dc882`:
     - a one-name book for S12, where the min-mark valuation visibly changes the buy size;
     - a flatten under a hold for S11, where the held symbol's sale waits while another name sells;
     - S15 cut at the tampered event, because later batches carry full projections and failed replay for another reason.
  No assertion was weakened.
- **Mutations**, each reverted, all caught (failures in the two IDEA-055 test files):

  | Mutation | Failures |
  |---|---|
  | Adopt after one read | 13 |
  | Ignore a commit between the checks | 2 |
  | Adopt an unsolicited token | 2 |
  | Change the cost basis on adjustment | 3 |
  | Plan orders for a held symbol under a hold | 1 |
  | Run `update_risk` under a hold | 2 |
  | Value a held jumped symbol at the current mark | 1 |
  | Never expire a hold | 1 |
  | Keep `balances_ok` false after an adopted deficit | 2 |
  | Skip the replay check of `BALANCE_ADJUSTED` | 1 |

- **Full suite** (`python -m pytest -q -p no:cacheprovider`):
  - base `1388f80` (with the PR 3 docs): 1578 passed, 10 skipped, 2194 subtests;
  - this branch at `09dc882`: **1600 passed, 10 skipped, 2209 subtests**. That is +22 tests (the new file) and +15 subtests (S2, S16 and B9's extra key); no new failure or skip.
  - The 10 skips are environmental and the same on both: opt-in recorded artifacts (1), root ignores directory mode (1), the disposable systemd runner not enabled (5), Linux bubblewrap not available (3).

| ID | Result | Evidence |
|---|---|---|
| S1 | PASS | `Pure::test_s1_*`, `Adoption::test_s1_*` |
| S2 | PASS | `Pure::test_s2_*` |
| S3 | PASS | `Adoption::test_s3_*` |
| S4 | PASS | `Adoption::test_s4_*` (not due at +59 s, adopted at +60 s) |
| S5 | PASS | `Adoption::test_s5_*`; the "nothing read while reservations exist" part is the existing `Stale::test_b6_nothing_is_read_or_journaled_while_something_is_in_flight`, unchanged and passing |
| S6 | PASS | `Adoption::test_s6_*` |
| S7 | PASS | `Adoption::test_s7_*` |
| S8 | PASS | `Adoption::test_s8_*` |
| S9 | PASS | `Adoption::test_s9_*` |
| S10 | PASS | `Adoption::test_s10_*` |
| S11 | PASS | `PriceJump::test_s11_*`, `ReverseSplitPlanner::test_s11_the_flatten_waits_for_a_held_symbol_only` |
| S12 | PASS | `ReverseSplitPlanner::test_s12_*` (two books), `PriceJump::test_s12_*` |
| S13 | PASS | `PriceJump::test_s13_*` |
| S14 | PASS | `PriceJump::test_s14_*` |
| S15 | PASS | `PriceJump::test_s15_*` |
| S16 | PASS | `Settings::test_s16_*` (three tests) |
| S17 | PASS | full suite and mutations above |

**Existing tests changed:**
- `Surplus::test_b4_*` was renamed `..._adopted_at_the_confirming_check`. It now expects adoption, because old D2 asserted the ledger never changes.
- `Deficit::test_b5_*` gets a comment only; its first-check assertions are the D1 window.
- `Settings.BLOCK` (used by B9 and `Composition`) gains `price_jump_check_bps`, now required.

**Still open:** Isaac and Keegan's review. The unconfirmed-deficit pause (Design §3, "Gate") is flagged for Yao Zhu. PR 5 adds the RPC failover.

## Balance RPC failover (PR 5, 2026-10-16)

Builds D5's "made more robust" part. An ordered list of balance RPC providers; a check fails only when every provider fails. Built by a Claude Code session at Yao Zhu's request; Isaac (C, RPC choice #92) and Keegan review. Stacked on PR 4. Pass criteria are committed before any test or code.

### Design

1. **Setting.** `driver.balance_rpc_providers` is an ordered list of `{url, source_id}`: the primary first, then backups, at most four. Each URL must be HTTPS with a host and no credentials in the authority (the `Rpc` rule). Source IDs must be non-empty and unique.
   - The legacy pair `balance_rpc_url` + `balance_rpc_source_id` is still accepted as a one-provider list. A config naming both forms is refused.
   - In `dev`/`live`, a missing or empty list, or any provider with a null URL or source ID, refuses the start (exit 4), as before.
   - `runtime.example.json` names two providers with null URL and source ID. The primary and the backup both come from Isaac's RPC choice (#92); the backup URL stays null until then.
2. **Failover (`BalanceProviders` in `larp/execution_live/balances.py`).** For each check, the providers are tried in order with a whole `read_balances`. Reads never mix providers within one observation, because the block identity re-check is per provider. A provider that raises `DependencyUnavailable` or `Blocked` is skipped for that check, and the next one is tried. The observation carries the `source_id` of the provider that served it, and so does every RPC artifact.
   - The check fails only when every provider failed: `RPC_UNAVAILABLE` if every failure was unavailability, otherwise `OBSERVATION_INVALID`. Retry after 60 s and the 30-minute maximum age are unchanged.
   - Each new check starts again at the primary.
   - One `DecimalsCache` is shared across providers: a contract's decimals are a constant, so two agreeing reads may come from different providers.
   - The two reads that confirm an adoption may come from different providers. The PR 4 rules (same chain units, ledger units and `settled_block`, nothing committed between) are unchanged.
3. **`build_driver`.** One `Rpc` per provider, with artifacts under `<market_artifact_root>/chain` as today. The `BalanceProviders` reader replaces the single `Rpc`, inside the existing balance block only.
4. **Approved destinations and manifest (G-03, IDEA-062).**
   - The route checker (`larp/runtime/routes.py`) plans one destination per provider, and the legacy pair still works. Any unset provider URL is an UNSET row, which fails the check. A bad URL in any provider is refused before any probe.
   - The approved table in `docs/build/architecture-deployment.md` names `driver.balance_rpc_providers`.
   - `config/release/services.v1.json` (the manifest's third-party services, F-61) declares `bsc-rpc` as `PENDING_DECISION` with candidates and a fallback until #92. The configured URLs are bound to the manifest through `runtime_config_sha256`.
   - `tools/deploy/render_host_configs.py` lists unset values inside lists too, so a null provider URL is reported.

### Pass criteria (recorded before any test is written)

Synthetic RPC providers, disposable PostgreSQL; no credentials, network, signing or upload. Tests first and red, then the build.

| ID | Check |
|---|---|
| F1 | Settings: the list form with one or two providers is accepted in order. The legacy pair is accepted as one provider. Both forms together are refused. In `dev`/`live`, a missing or empty list, a null URL or source ID, a non-HTTPS URL, a duplicate source ID or more than four providers is refused. `offline` with none is `None`. |
| F2 | Failover: with the primary unavailable (and, separately, returning a rejected answer), the same check reads from the backup. The observation names the backup's `source_id`. The next check tries the primary first again. |
| F3 | A check fails only when every provider fails. With the primary down and the backup up, checks are comparable and `balances_ok` stays true. With both down, the check is `SKIPPED: RPC_UNAVAILABLE`, retried 60 s later, and new spending stops only after the maximum age. |
| F4 | An adoption can be confirmed across providers: the first read from the primary, the confirming read from the backup (primary down) → `ADJUSTED`. |
| F5 | `build_driver` with two providers wires a reader whose providers are in the configured order, with their source IDs. A single legacy provider still builds. A `dev` start with no provider is refused. |
| F6 | Route checker: both provider hosts are planned. An unset URL in either provider fails the check as UNSET. A bad URL in any provider is refused before any probe. The legacy single form is still planned. The approved table names `driver.balance_rpc_providers`. |
| F7 | `config/release/services.v1.json` declares `bsc-rpc` and still passes `validate_services`. |
| F8 | The example names two providers with null URL and source ID. `unset()` reports `driver.balance_rpc_providers[0].url` and `[1].url`. |
| F9 | Full suite: the PR 4 count plus only these tests and the updated ones, with no new failure or skip. Mutations, each reverted, must each be caught: no failover (primary only); failover on unavailability only (not on a rejected answer); the legacy form refused; both forms accepted; the route checker planning only the first provider; `unset()` not recursing into lists. |

**Existing tests this changes:**
- `Settings::test_b9_the_example_names_every_balance_setting`: the example now uses the list form instead of the legacy keys.
- `tests/runtime/test_routes.py`: its `configs()` fixture fills the provider list. R3 (bad URL, unset URL) uses `providers[0]`, R8 checks the new field name, and the account-specific hosts include the backup.

### Results (2026-10-16, PR 5)

Criteria at `2d08f45`; red tests at `0e1fe07`; build at `8ed2f08`; register test update at the next commit. Same environment as PR 4: PostgreSQL 16.15, not 14 (see PR 4). Python 3.12.3 from `deploy/requirements-test.lock`. No credentials, network, signing or upload. Org CI was not used.

- **Red first:** at `0e1fe07`, the new and updated tests failed for the predicted reasons. There is no `BalanceProviders`. Settings know only the legacy pair (both forms are accepted, a list-only config is "missing"). The route checker plans only `balance_rpc_url`. `bsc-rpc` is not declared, and the example has no list.
- **Updates found by the build run:**
  - `test_routes` R1's expected destinations add the fixture's backup host.
  - `test_release_register::test_r1_services_list` pins the pending services and now lists `bsc-rpc` next to `assessor-model`. This may conflict with the model-routing session if it edits the same list.
  - No assertion was weakened.
- **Mutations**, each reverted, all caught (failing tests and subtests in the four affected files):

  | Mutation | Failures |
  |---|---|
  | No failover (primary only) | 4 |
  | Failover on unavailability only (not on a rejected answer) | 1 |
  | The legacy form refused | 4 |
  | Both forms accepted | 2 |
  | The route checker planning only the first provider | 3 |
  | `unset()` not recursing into lists | 1 |

- **Full suite** at the register update: **1612 passed, 10 skipped, 2231 subtests**. The PR 4 head had 1600 / 10 / 2209, so this is +12 tests and +22 subtests (F1's refusal cases and F2's two failure kinds). There is no new failure or skip; the 10 skips are the same environmental ones.

| ID | Result | Evidence |
|---|---|---|
| F1 | PASS | `Settings::test_f1_*` (10 refusals × 2 modes) |
| F2 | PASS | `Failover::test_f2_*` (unavailable and rejected primary) |
| F3 | PASS | `Failover::test_f3_*`, `FailoverDriver::test_f3_*` |
| F4 | PASS | `FailoverDriver::test_f4_*` (first read from the primary, confirmation from the backup; the two observation hashes differ) |
| F5 | PASS | `Composition::test_f5_*`, plus the unchanged B9 refusals |
| F6 | PASS | `Routes::test_f6_*`, updated `test_routes` R1/R3/R4/R8 |
| F7 | PASS | `Declared::test_f7_*`, `test_release_register` R1 |
| F8 | PASS | `Declared::test_f8_*` |
| F9 | PASS | full suite and mutations above |

**Existing tests changed:**
- B9's example check uses the list form.
- In `test_routes`, `configs()` fills two providers. R1 expects the backup host, R3 uses `providers[0]`, R4 also checks that the backup URL's secret path is never reported, and R8 checks the new field name.
- `test_release_register` R1 lists `bsc-rpc` as pending.

**Still open:** Isaac's RPC choice for both providers (#92), which then sets `bsc-rpc` to ACTIVE; the first hosted check from `primary`; review by Isaac and Keegan.

## PR 4 review fixes (2026-10-16, Claude Code session for Keegan, section B)

From the section B review of PR #115 and wtvlol's ALLPR-R1. Criteria recorded before any change is tested.

**Correction to the review.** One suggested option for R2 below, rolling the day at the lower of the two marks, is not adopted. A lower anchor makes the daily stop *looser*, not tighter, because a later loss is measured against a smaller base. The review comment claimed the opposite.

| ID | Pass criterion |
|---|---|
| R1 (ALLPR-R1) | A mismatch is adopted only by a read made at least `retry_ms` after the first read and at a **strictly newer** finalized block. A comparable check that comes earlier (for example the immediate check that a price jump triggers) neither adopts nor replaces the first read as the candidate, unless the store version or `settled_block` changed. A read of the same block `retry_ms` later does not adopt (a stuck node cannot confirm itself). Both event orders are covered: a hold journaled before the first read, and a first read in the same millisecond as the hold. |
| R2 | A day roll that `PRICE_JUMP_HOLD` defers inside its window is not lost when the window closes. `DayRoll` remembers the deferred UTC day in memory and rolls on the first cycle after the hold clears or expires, even past `window_ms`. A day not deferred inside its window still returns `OUTSIDE_WINDOW`. A restart loses the memory, the same as any outage across the window today. |
| R3 | A hold is cleared by a MATCH only when that check is at least `retry_ms` after `jump_ms`. While any hold is active, the next check is scheduled `retry_ms` later, not after the 10-minute interval. The immediate check after a jump still runs and can start an adoption, but a MATCH there leaves the hold in place. A MATCH `retry_ms` after the jump clears it. |
| R4 | `config/runtime/runtime.aiand-shadow.example.json` (from #114, merged into this branch) gains `price_jump_check_bps: 3000`, so #114's SG3 passes with PR 4. Merge order: #114, then #115, then #116. |
| R5 | The existing S1–S16 tests pass. The synthetic chain advances one block per read. S6's `confirm_block` becomes `first_block + 1`, S11/S12 confirm a minute after the immediate check as before, and S14 keeps its in-window case. Mutations caught: no elapsed-time check, same block allowed, early check replaces the candidate, no day-roll deferral, MATCH clears a hold at once, hold not rescheduled at `retry_ms`. Full suite: no new failure against the branch before these fixes. |

Not changed here (not breaking; reply on the thread): the hold also defers `TERMINAL_FLATTEN` and Class 1 exits (a question for the author and Yao Zhu).

### PR 4 review fixes: results (2026-10-16)

Order: merge of #114 `a6fba10` (stack order #114 → #115 → #116; `docs/LEDGER.md` conflict resolved by keeping both rows) → criteria `eea637a` → fix `6b25525` → second #114 merge (SG3 / #87 compatibility).

| ID | Result | Evidence |
|---|---|---|
| R1 | PASS | `ReviewFixes.test_r1_a_hold_before_the_first_read_cannot_shorten_the_confirmation` (wtvlol's order: the early check returns SURPLUS_ONLY, the adoption comes `retry_ms` after the *first* read, and `first_block` is that read's block), `test_r1_a_first_read_in_the_same_millisecond_as_the_hold`, `test_r1_a_stuck_node_cannot_confirm_its_own_read` |
| R2 | PASS | `ReviewFixes.test_r2_a_hold_across_the_end_of_the_window_defers_the_roll` (5-minute window: held at +1 and +10 min, a fresh `DayRoll` says OUTSIDE_WINDOW at +10, the deferred one rolls at +12 min once the hold is cleared); S14 unchanged |
| R3 | PASS | `ReviewFixes.test_r3_a_match_just_after_the_jump_keeps_the_hold_a_later_one_clears_it` (the immediate MATCH keeps the hold, the next check is `retry_ms` later, its MATCH clears the hold, the next round latches the daily stop on the genuine drop) |
| R4 | PASS | `runtime.aiand-shadow.example.json` has `price_jump_check_bps: 3000`; #114's SG3 passes on this branch |
| R5 | PASS | S1–S16 and B1–B10 pass. Test changes: both synthetic-chain harnesses advance one block per read; S6 asserts `confirm_block == first_block + 1` (it asserted equal blocks); no other assertion changed. Mutations, each reverted, all caught: no elapsed-time check (2 failures), same block allowed (1), early check replaces the candidate (2), no day-roll deferral (1), MATCH clears a hold at once (1), hold not rescheduled at `retry_ms` (1). Full suite, Python 3.12.3 venv from `deploy/requirements-test.lock`, local PostgreSQL **16.15** (not 14.24): the branch before these fixes, `1b21416`, 1612 passed, 10 skipped, 2216 subtests; this branch at `6b25525` (with #114) **1657 passed, 10 skipped, 2306 subtests, 0 failed**. The same 10 environmental skips. |

**Still open:** the hold also defers `TERMINAL_FLATTEN` and Class 1 exits (question to the author and Yao Zhu, not changed). A PostgreSQL 14.24 run. Isaac's section C review.

### PR 5 with #114 and the PR 4 review fixes (2026-10-16)

This branch merges PR 4 (#115) at `bc51c4a`, which now carries #114. Combined, three of #114's tests and F4 needed updating: `5b4adf9` (merge `b3f9ea1`).
- #114's AIand shadow example lists `balance_rpc_providers` like `runtime.example.json`, so SG3 passes.
- #114's SG2/R8 route tests and SG3 fill the providers list instead of the legacy pair. The list wins in the route checker, so the legacy fill had left a null host.
- F4's backup serves a newer finalized block, because R1 needs a strictly newer block to confirm.

Gate A (#87) side: `prepare()` now writes the balance RPC in whichever form the rendered example uses (IDEA-058 GA14). A scratch merge of #87 into this branch passes `test_gate_a.py`, GA06 included.

Full suite, Python 3.12.3 venv from `deploy/requirements-test.lock`, local PostgreSQL **16.15** (not 14.24), 10 environmental skips each:
- this branch at `21ba652`: **1669 passed, 10 skipped, 2328 subtests, 0 failed** (PR 4 at `6b25525`: 1657 passed);
- scratch merge of this branch with #87 at `c9b7613` (all four of #114, #115, #116, #87): **1701 passed, 10 skipped, 2381 subtests, 0 failed**.

Org GitHub Actions jobs on these heads stop after about 3 s with no step output, consistent with the billing block (#98). A PostgreSQL 14.24 mirror run is still owed.


## PR115-C — independent execution/accounting review (2026-10-16, Isaac / Codex)

Review starts at `bc51c4a`, including section B's R1–R5 fixes and the inherited
AIand shadow merge. Review and fixes are isolated from the IDE checkout. No
wallet credentials, provider calls, signing, uploads or deployment are used.

Prospective criteria, recorded before running review tests:

| ID | Pass criterion |
|---|---|
| PR115-C01 | Two agreeing balance reads must be consecutive comparable reads for each asset. An intervening early MATCH or different mismatch invalidates that asset's candidate; a later return to the original units cannot confirm it. An identical early read preserves the original candidate and its elapsed-time bound. Another asset's contradictory read must not invalidate an unchanged asset's candidate. |
| PR115-C02 | A price jump first visible in the midnight market fetch must defer the daily anchor before it is committed, even when no hold was already in the projection. Forward and reverse splits must not anchor using old units and the new mark; ordinary and guard-disabled day rolls remain unchanged. The subsequent round journals the hold through the existing context path. |
| PR115-C03 | Baseline and regression tests use disposable local PostgreSQL, with exact version recorded; targeted balance/adoption/day-roll/replay/HALT tests and the full available suite run after their code is committed and pushed. Existing R1–R5 guarantees remain covered. This establishes offline engineering behavior only. |

Review also checks ordinary cadence versus candidate invalidation, observation
and replay provenance, and the known terminal-sale hold question. New findings
and results will be appended here; no whole readiness GAP is closed by review.

PR115-C01/C02 red at `324de5f`, PostgreSQL 14.24: 5 new regressions failed
for the predicted safety defects, 67 focused tests passed. At pushed `e9a337e`,
all 72 tests and 46 subtests pass. Logs: `/private/tmp/larp-pr115-red.log` and
`/private/tmp/larp-pr115-green.log` (local, outside Git).

**PR115-C04, additional prospective criterion:** a continuous sequence of
hold-only rounds must not starve balance confirmation. Preserve the owner's
two-read/no-wallet-activity contract (D1–D5), but refine the implementation's
stronger "no commit whatsoever" condition: allow journal-proven rounds with
no intents, commands or reservations, and unchanged portfolio/execution state.
Any intervening reservation (even acquired and released between reads), command,
execution observation, balance adjustment, epoch change or unrecognised event
invalidates the candidate. Read only the bounded journal suffix since the
candidate, not the entire historical journal. Retain S5's negative assertion
using actual transient reservations instead of an unrelated hold-only round.
Regression: with one hold round per minute, two stable chain reads a minute
apart adopt the mismatch; real transient resource activity still requires a
new pair of reads. This is an engineering correction to the design's overly
broad commit proxy, not a change to the owner safety or trading policy.

PR115-C04 reproduced at `99c2d0b`: the continuous hold-cadence regression failed,
while the transient-reservation safety control passed. The first focused run
after `ebd8a97` passed 87 tests / 46 subtests, with one existing fixture failing:
S9 still waited for an unnecessary third check after a blocked gas round. Its
assertion is advanced to require adoption at the first eligible confirming
check, retaining the blocked-before / top-up-enabled-after assertions. S5 now
uses actual transient reservations; the safety assertion is retained. Additional
checks require commands and unknown events to invalidate confirmation, validate
bounded journal reads, and replay the continuous-cadence adoption exactly.

**PR115-C05, prospective concurrency criterion:** if another writer commits
resource activity after this check's own commit but before its subsequent load,
that activity must not be treated as this check's own commits. The next read
must reject the old candidate. Reproduce by injecting a reservation and its
release in that exact gap; update the candidate's version only when the reload
contains exactly the one expected commit. Full candidate safety still rests on
the journal suffix, and ordinary single-writer behavior is unchanged.
The same barrier must apply when the concurrent activity happens during the
confirming check's own journal writes: no adjustment may commit using the
previously computed confirmation. Refuse that adoption, pause new spending and
obtain a fresh pair of reads; retain all intervening journal events.

## RR2 — second all-open-PR review, prospective criteria (2026-10-16)

- RR2-R1: a contradictory comparable read, including an early MATCH, invalidates that asset's first mismatch. Only unchanged candidate assets retain their first timestamp. Test MATCH/reverted mismatch and changed mismatch, while retaining the elapsed-time and newer-block checks.
- RR2-R2: a day roll deferred inside its window survives process restart both while the hold remains and after it clears. Persist a journaled deferred-day fact, replay it exactly, clear it only on successful roll, and retain OUTSIDE_WINDOW when no deferral exists. Add restart/replay regressions.
- RR2-R3: a primary below the already-settled block cannot suppress a healthy backup. Use the current ledger floor on each whole-provider read; all-behind stays refused. Bind the floor in build_driver and test fresh/lagging/all-behind providers. No new freshness policy or provider choice.


### RR2 observed results and publication status

RR2 current pushed head 5c1407d: focused balance/failover/routes/register/HALT/driver modules 111 passed / 107 subtests on Linux/Python3.12/PostgreSQL14.24. Inherits RR2-R1/R2 above. Lagging-primary reproduction returns BLOCK_BEHIND_LEDGER with zero backup calls despite a healthy backup. RR2-R3 uses only the existing settled-block floor; provider choice and hosted checks retain their owners. All RR2 fixes remain unexecuted pending approved push. All runs used synthetic inputs, no production credentials and no external network.

RR2 current pushed head bc51c4a: focused balance/HALT/driver modules 77 passed / 67 subtests on Linux/Python3.12/PostgreSQL14.24. Reproductions: 2010 mismatch at t0, MATCH at t1s, 2010 at t60s wrongly adopts; reconstructing DayRoll after an in-window deferral returns OUTSIDE_WINDOW after the hold clears. Original ALLPR-R1 elapsed/newer-block checks are fixed. RR2-R1/R2 fixes and new regressions remain unexecuted pending approved push. All runs used synthetic inputs, no production credentials and no external network.


### RR2 integrated acceptance criteria (before full execution)

The combined PR116 head includes merged Gate A PR87, PR108 migrations012/013, PR115 RR2-R1/R2 and PR116 RR2-R3. Require the full synthetic/offline suite to have no failures or unexpected xfails on Python3.12.15/PostgreSQL14.24 with real systemd and bubblewrap enabled. Account for every skip. Run a disposable local namespace/systemd container without external networking or production credentials. The opt-in external recorded-market dataset may remain skipped; no hosted, provider-quality, AWS, wallet or live acceptance follows. Confirm clean source and published commit before running.

## PR115-C03 — verification and finding disposition (2026-10-16)

This dated result supersedes the earlier RR2 "unexecuted pending approved push"
status. Both reviewers' records and fixes are retained with merge commits.

| Finding | Outcome |
|---|---|
| PR115-C01 / RR2-R1 | Fixed: an early MATCH or contradictory mismatch invalidates that asset's candidate; other unchanged assets retain their first timestamp. Three independent regressions reproduced the original defect before the fix. |
| PR115-C02 | Fixed: a jump first visible in the midnight fetch defers the anchor before it can use old units and a split-adjusted mark. Both split directions are covered. The combined fix journals the deferral using RR2-R2's restart-safe path. |
| PR115-C04 | Fixed: ordinary hold-only cadence no longer invalidates every confirmation indefinitely. The bounded journal suffix proves no wallet activity occurred; transient reservations, commands and unknown events still invalidate the candidate. Exact cadence/adoption replay passes. S5 now injects real transient reservations and retains its negative assertion. S9 requires the earlier valid confirmation, preserving its gas-block/resume assertions. |
| PR115-C05 | Fixed: concurrent commits in the first-read reload cannot be blessed as this check's own commits. A race during confirmation logging aborts adoption, pauses spending and requires a fresh pair. Both gaps were reproduced before their fixes. |
| RR2-R2 | Preserved: deferred day roll survives restart, including a restart after the hold clears; replay recognises DAY_ROLL_DEFERRED. The imported regression needed its existing replay helpers bound to SecondReview; no assertion was removed. |

**Environment:** macOS ARM64, Python 3.12.14, pytest 9.1.1; disposable Docker
`postgres:14.24-bookworm` (PostgreSQL 14.24, image digest
`sha256:5a05f61a534e50e679d27fb45953afec7821f2ffc2aa6c738b94515ca0891ac2`),
bound only to localhost port 55435. No production credentials, provider calls,
signing, uploads or AWS operations. `pip check` and `git diff --check` pass.

- At `a2b54c1`, focused reconciliation/day-roll/HALT/storage: **92 passed,
  50 subtests**, zero failures. After the final concurrency fix `472cede`, the
  independent regressions: **13 passed, 4 subtests**, zero failures.
- At combined `fd5dd6b` (includes concurrent `522cd53`, prior to Gate A's merge):
  full suite **1698 passed, 9 skipped, 2324 subtests**, zero failures,
  244.77 s. Skips: five opt-in real-systemd tests, three Linux bubblewrap tests,
  one opt-in external market artifact. Raw log `/private/tmp/larp-pr115-full.log`,
  SHA-256 `eb89cb27600c18781164b45fade1aff4308d775ce69505112270a18673ac05f0`.
- One initial confirming-race invocation began before the push confirmation was
  read; its result is not used as evidence. It was repeated after explicit push
  confirmation in `/private/tmp/larp-pr115-adoption-race-red-confirmed.log` and
  reproduced the same predicted failure.
- Concurrent `959a627` adds the now-merged Gate A input assembly. It is preserved
  in the review branch and is included in the final verification below.

**Final combined verification at pushed PR head `7062923`:** full suite
**1730 passed, 9 skipped, 2377 subtests**, zero failures, 252.69 s. Same macOS /
Python 3.12.14 / PostgreSQL 14.24 environment and the same nine platform/opt-in
skips described above. Includes Gate A assembly, both reviewers' RR2 fixes,
all thirteen independent PR115-C regressions, exact replay and the storage
journal bounds. Command:
`LARP_TEST_DATABASE_URL=<disposable localhost database> python -m pytest -q -p no:cacheprovider`.
Raw log `/private/tmp/larp-pr115-full-with-gate-a.log`, SHA-256
`dd7a51b1ebd3b0103631eaaf3a3b87adf8bea19b1d2e624b22d6e529100ec739`.
The subsequent record/index/backlog commit changes documentation only.

**PR115-C06, final shared-base qualification:** after that run, concurrent
`8956d7d` preserves integration PR #108's archive-security migrations 012/013
and their regressions. They change no reconciliation code, but affect database
startup. Preserve them with a merge; run the full available suite on PostgreSQL
14.24 again before recording the final combined result. The `7062923` result
above remains evidence for that exact tree only.

**Still open:** the existing mandatory-sale/price-jump-hold policy question
(Yao Zhu + Keith); PR #116's failover composition review (Keith/Keegan); Linux
systemd/bubblewrap qualification and actual hosted/signing/provider readiness
with the existing owners. No policy choice, live authority, whole GAP closure
or PR merge is implied by this offline review.

### RR2 concurrent-review integration acceptance (before execution)

Preserve PR115-C01/C02/C04 concurrency fences and first-observed midnight jump protection alongside RR2-R1/R2/R3, migrations012/013 and merged Gate A. Require independent PR115 adversarial cases plus balance adoption/failover/day-roll, storage, HALT and driver regressions to pass, followed by the full previously specified Linux systemd/bubblewrap/PostgreSQL14 suite. Earlier integrated result at527376c (1744 passed, 1 opt-in external-data skip, 2557 subtests) predates the concurrent fixes and does not validate this updated source. No hosted/live claims follow.

### RR2-R4 — midnight hold must not depend on a later assessment round (prospective)

The midnight jump check currently journals only the deferred-day flag. Without a subsequent assessment round, its new hold/mark is never persisted; repeated DayRoll calls rediscover the same jump and cannot age out or observe BalanceCheck clearing it. Require the first midnight-discovered hold and marks to be journaled with the deferral, survive restart/replay, clear through comparable balances without an intervening assessment, and expire at the original hold deadline without being renewed by repeated day-roll calls. Also persist a later newly discovered hold on an already-deferred day with a unique event ID. Synthetic PostgreSQL regressions must fail before the repair and pass after. No owner policy change.

RR2-R4 original published source9774011: both no-round regressions fail on PostgreSQL14.24 (missing persisted NVDAB hold; still PRICE_JUMP_HOLD at +31min). Repair journals detected marks/holds together with the deferred day, uses a version-qualified event ID for a later new hold on the same deferred day, and retains the original expiry. Before this repair, combined990e912 passed1757 tests /1 opt-in external-data skip /2561 subtests with real Linux systemd/bubblewrap; that run does not close RR2-R4. Verification of the repair follows publication.

RR2-R4 first focused repair run: 90 passed /2 failures /253 subtests. All three new no-round regressions passed; the two existing split-anchor tests expected an extra immediate check after the next round. Persisting the hold correctly moves that check before the round. Update the fixture to expose split units before that actual pre-round check, assert its SURPLUS/DEFICIT result, and retain the full retry interval before adoption. No scheduling safeguard is relaxed. Repeat focused/full validation after publishing this fixture correction.


### RR2-R4 final regression acceptance (2026-10-16)

Published combined source af9ffbf (PR115 fixes at9f561f9/481ae58 plus PR116 failover and merged PR87/108) passes92 focused tests /253 subtests, then the full ARM64 Linux/Python3.12.15/PostgreSQL14.24 suite: **1760 passed, 1 skipped, 2561 subtests** in221.45s. Real systemd and bubblewrap enabled; sole skip is opt-in external recorded market artifacts. Both new no-round regressions were red at9774011, and persisted-hold expiry/reconciliation/second-jump cases now pass with replay. Source clean, pip check passes. Logs/hashes: /private/tmp/larp-rereview-0jHjyg/results-v4/summary.json; full log SHA256 c6451ff3aa2c8fd8b50e286182ee2027e3e19903fbc27bba2f0ef9dd4c539bb7. No remaining implementation finding in this review. Peer merge481ae58 has exactly the same content as9f561f9. Hosted Actions run38908993829 ataf9ffbf never starts because of account billing/spending limits; exact-release bundles and hosted/policy/provider/rehearsal gates remain open. No real credentials, cloud actions, real-wallet signing or network broadcast. PR115/116 merge under the user approval; target is codex/system-testing-20261012, main unchanged. Detailed current index/backlog reconciliation follows with PR116.


### RR2 final combined verification and disposition (2026-10-16)

Published source `af9ffbfccf1f682669ada56fa5fb90db2896a6c1` includes PR87 Gate A, PR108 archive migrations 012/013, PR115 concurrent-review fences and RR2-R1/R2/R4, and PR116 settled-block failover RR2-R3. Focused adoption/independent/failover/roles/driver suite: **92 passed /253 subtests**. Full offline suite: **1760 passed, 1 external-data skip, 2561 subtests**, no failures or xfails, Python3.12.15 /ARM64 Linux /PostgreSQL14.24; real systemd and bubblewrap enabled. The sole skip is tests/marketdata/test_recorded.py:29, opt-in external recorded artifacts. Dependencies pass pip check. Both no-assessment-round regressions failed on published 9774011 before the repair; all three new persistence/expiry/second-hold tests now pass, including exact replay. No implementation findings remain from this review.

RR2-R1 invalidates contradictory per-asset candidates; R2 persists deferred days across restart/replay; R3 tries a backup when the primary cannot meet the current settled-block floor; R4 journals midnight-discovered marks/holds without requiring a later assessment and permits a distinct later hold on the same deferred day. PR115-C concurrency checks reject intervening wallet activity while allowing journal-proven neutral cadence rounds. All concurrent commits were preserved with ordinary merges; no history was rewritten.

Earlier full source 527376c: 1744 passed /1 skip /2557 subtests. Its first attempt had nine executable-permission failures caused by the runner's /tmp noexec mount; remounting that disposable tmpfs exec made affected modules and the entire unchanged-source rerun pass. Source 990e912 then passed 1757 /1 skip /2561 subtests before RR2-R4 was identified. Final acceptance is the source above. Logs, JUnit and hashes are retained outside Git in `/private/tmp/larp-rereview-0jHjyg/results-v4/`; full log SHA256 `c6451ff3aa2c8fd8b50e286182ee2027e3e19903fbc27bba2f0ef9dd4c539bb7`, JUnit SHA256 `f30deb7509ba17304455bda521d8a7608893de8fc94419466d9d2949324c67ac`.

Hosted Actions run 38908993829 at af9ffbf ran no steps: GitHub reports failed payments/spending limit (#98, account owner). Local tests do not replace exact-release host-bundle/Terraform CI or hosted acceptance. No external network, real credentials/provider calls, cloud provisioning, official uploads, real-wallet signing or network broadcast occurred. Yao Zhu + Keith retain the mandatory-exit/price-jump-hold policy question; Isaac retains provider selection/first hosted read (#92); existing owner gates cover measured inputs, terms, host routes/receiver/recovery, shadow trial/adoption and wallet rehearsal. No whole GAP closes. PRs target codex/system-testing-20261012; main is unchanged.


### PR115-C06 — independent final acceptance (Isaac / Codex, 2026-10-16)

- Shared-migration baseline `14daab3`: **1735 passed, 9 skipped, 2531 subtests**,
  zero failures, 248.72 s on the same disposable PostgreSQL 14.24 environment.
  Log `/private/tmp/larp-pr115-full-shared-migrations.log`, SHA-256
  `544828a0451ab5e4edbab84dcfdc2d8f52c6d2e5092553ec63f0486337ca4eb5`.
- RR2-R4 independently reproduced at published review `06e20ec`: both no-round
  tests fail for the documented reasons. Preserved peer fixes `4a62e9d` and
  `9f561f9` with merge `481ae58`; all **16 independent regressions / 4 subtests**
  pass, including expiry, balance clearing, restart/replay and another jump on
  an already deferred day. The original hold deadline is never renewed.
- **Complete suite at pushed `481ae58`: 1738 passed, 9 skipped, 2531 subtests**,
  zero failures, 254.05 s. Same macOS ARM64 / Python 3.12.14 / PostgreSQL 14.24
  environment; the same five opt-in systemd, three Linux bubblewrap and one
  external-artifact skips. Raw log `/private/tmp/larp-pr115-full-complete.log`,
  SHA-256 `645e3eefde181bebca005a085da0ffb6f49bf5454674b31a088f3f6b862e99fc`.
- Preserved peer acceptance commit `5d1f408`; it changes documentation only.
  The final record/index/backlog update also changes documentation only.
  `pip check` and `git diff --check` pass. The disposable database is removed
  after verification. No remaining implementation finding from this review;
  the owner policy, exact-release/host/provider/rehearsal gates above remain.

### PR122-R1 — reconcile the documentation follow-up with completed integration (2026-10-16)

Review began at27f1913 against testing-branch e4f3d59. Pass criteria: preserve both reviewers' dated evidence, leave executable/test/configuration files unchanged, retain the current owner/hosted backlog and do not restore completed integration tasks.

The proposed index/backlog still named PR115/116 merge disposition as pending, although both are merged (19da67f/e4f3d59). Resolve the conflicts using the current index/backlog; retain PR115-C06 as additional evidence and preserve the existing combined Linux acceptance. The only remaining reconciliation owner question is IDEA-055 POLICY-HOLD; all existing provider, hosted, exact-release CI/bundle and rehearsal gates remain explicit.

### RPC-Q01 — Isaac checklist task 1: balance-provider qualification (2026-10-17, prospective)

User authorizes implementing Isaac's PR133 tasks in order, each on its own branch/PR, with decisions called out. First task is #92/GAP-71 provider choice; base `47c8e6c`, branch `codex/isaac-01-balance-rpc-20261017`. PR133 head `9c37c08` assigns the AWS network/config/first-host work to Yao Zhu; do not mark those done from this Mac. Selection/adoption belongs to Isaac. Later checklist items stay separate.

Scope: a small diagnostic wrapping the real `Rpc` and `gate_a.chain_capture` consumers, a point-in-time no-key public-provider comparison and a private operator handoff. No credentials, registered wallet, signing, transaction submission, official round logging, AWS operation, paid account or runtime-default change. Probe the public zero address; it cannot establish the registered wallet's balances. URL/endpoint config and raw artifacts remain outside tracked files. Published results name providers/source IDs, hashes and capability verdicts, never URLs or private values. Local success does not establish hosted reachability, uptime or native tracing (#30).

Primary sources checked before choosing candidates (2026-10-17): [BNB Chain RPC documentation](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/) lists its public mainnet RPC and a 10K/5min limit, with `eth_getLogs` disabled; that method is not needed by this balance reader. [PublicNode BSC page](https://bsc.publicnode.com/) supplies its free mainnet endpoint; [its terms](https://www.publicnode.com/terms) permit intended RPC access, with a revocable service. These are provider-published statements, not a measured availability guarantee. Candidate source IDs: `BSC_BNBCHAIN_PUBLIC`, `BSC_PUBLICNODE_PUBLIC`. No provider is adopted until Isaac decides.

Pass criteria, frozen before any probe or covered-code execution:

- **RQ1:** read a local private ordered provider config using the runtime's real provider validator (1–4 providers), validate public source IDs, and refuse malformed/duplicate IDs, non-HTTPS/credentialed/redirecting endpoints and unsafe output locations. No endpoint, wallet, response or exception value appears in stdout.
- **RQ2:** for each candidate, the real chain capture must successfully check chain 56, a `finalized` block and its numeric-block canonical hash, native balance, decimals/balanceOf on USDT plus all five bStocks at that same numeric block, and latest/pending/numeric-block nonces. Preserve exact observations outside Git. No fallback to latest, guessed scales or mixed-provider results.
- **RQ3:** output a bounded per-source PASS/UNAVAILABLE/REFUSED report, count and hash its observations, and make clear that hosted checks, signed operation, native tracing and provider adoption are NOT_RUN. No failed candidate is silently removed from the report or called qualified.
- **RQ4:** unit tests use the actual consumers with a synthetic HTTP transport and cover wrong chain, missing finalized support, inconsistent canonical hash, invalid token word/scale, unavailable provider, malformed config, non-overwrite, private output constraints and value-safe failures. Run only after commit/push; preserve precise SHA/environment/results.
- **RQ5:** run one complete capture per public candidate, at most four candidates, sequentially; maximum 20-second timeout per existing RPC call and no retries, bypass or authentication workaround. Stop on refusal, report it, and distinguish local engineering evidence from first-host acceptance. Save a private provider/handoff file without activating it, and present the concrete choice to Isaac. Keep #92/GAP-71 open for adoption and Yao Zhu's host checks.

#### RPC-Q01 V1 / environment correction (2026-10-17)

- Pushed source `afd305d`: 55 focused tests passed, 3 existing PostgreSQL-dependent skips (58 total) on macOS/Python3.13. Command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.execution.test_balance_rpc_qualification tests.execution.test_chain_rpc tests.runtime.test_gate_a tests.runtime.test_balance_failover -q`. All six new tests passed; two existing SQLite ResourceWarnings were emitted by fixture cleanup, without test failures. No application behavior or runtime defaults changed.
- First local public-provider probe at `afd305d`, 2026-10-17 05:01:32 UTC: both candidates UNAVAILABLE before any retained successful RPC observation. Report `/private/tmp/larp-isaac-rpc-20261017/probe-01/report.json`; no provider is qualified by this result. Private candidate URLs/IDs are in ignored `deploy/activation/balance-rpc/providers.json` (0600).
- Read-only environment diagnosis: Python's default CA file/directory do not exist; `/etc/ssl/cert.pem` does. Certificate-verified curl HTTPS diagnostics reach BNB (GET 404) and PublicNode (GET 301); these are not RPC capability verdicts, and no redirect was followed. The missing Python trust store is a likely local cause, not evidence that provider capabilities failed.
- **RQ6 (before rerun):** rerun the unchanged probe once per candidate with `SSL_CERT_FILE=/etc/ssl/cert.pem` and a new external output directory. This selects the existing system trust anchors, preserves certificate and hostname verification, adds no trust anchor, follows no redirect, retries no individual request and bypasses no provider refusal. Record exact commit/flags/results; a provider refusal still fails that candidate.

#### RPC-Q01 V2 / backup candidate (2026-10-17, before next probe)

- At pushed `12c6e3d`, using the existing macOS CA file, the BNB Chain public candidate PASSes all 19 calls (5,927 ms; chain-capture SHA256 `6cf176ef5fb440fd39a7205fc6961c97abdc2356abdc46d254dad4032d5da406`). PublicNode remains UNAVAILABLE with zero successful observations (75 ms); the current transport deliberately hides error detail, so its HTTP/error cause is not established. No redirect is followed, no user-agent/authentication workaround is tried and this failure is not called a capability PASS. Report: `/private/tmp/larp-isaac-rpc-20261017/probe-02/report.json`. Only local zero-address capability is established, not hosted wallet, availability, tracing or adoption.
- **RQ7 (prospective):** qualify one additional candidate, NodeReal's public mainnet endpoint listed in the same BNB Chain official RPC documentation, public source ID `BSC_NODEREAL_PUBLIC`. A separate one-provider private config and new output directory preserve both earlier candidates' results. This is candidate 3 (within RQ5's four-candidate ceiling), not a retry or bypass of PublicNode's unavailable endpoint. No account/key is created. A PASS permits recommending it as a separate backup candidate, subject to Isaac's choice and host verification; a failure stays a failure.
- **RQ8 (prospective):** add transport diagnostics recording only numeric HTTP status or a fixed transport/TLS reason, before the existing production Rpc sanitizes its exception. Never reflect a URL, header, body, certificate text or exception message. Synthetic regressions must demonstrate that a 302/401/403/429 is visible without following, retrying or hiding it; arbitrary marker text stays absent. Run tests and the third probe only after pushing the changed code. No additional probe of either earlier provider is authorized by this criterion.

#### RPC-Q01 V3 / recommendation ready (2026-10-17)

- Pushed `333bed6`: focused suite **56 passed, 3 skipped** (59 total), same macOS/Python3.13 command as V1. All seven task tests PASS, including numeric HTTP diagnostics and one-attempt refusal behavior. PostgreSQL-only skips and existing SQLite fixture ResourceWarnings remain; no full Linux/PostgreSQL/host pass is claimed. `git diff --check` passes.
- Third public candidate, NodeReal, PASSes all 19 production-consumer reads at `333bed6`, 2026-10-17 05:14:53 UTC (6,042 ms; chain capture SHA256 `017f1578783bd60b83c68c423231e35367ebc19921b412bf421af0bcffd2a045`). Command: `SSL_CERT_FILE=/etc/ssl/cert.pem PYTHONDONTWRITEBYTECODE=1 python3 tools/deploy/qualify_balance_rpc.py --config deploy/activation/balance-rpc/nodereal-candidate.json --out /private/tmp/larp-isaac-rpc-20261017/probe-03`. No source-ID/URL default is activated. The report records native tracing/hosted qualification as NOT_RUN, no adoption, no signing/upload.
- Recommendation **pending Isaac's decision**: BNB Chain public primary, NodeReal public backup for development balance reads. Both are listed in the BNB Chain official RPC documentation and both passed this local snapshot. PublicNode is excluded because it did not pass. The small elapsed-time difference is not an availability/ranking claim; separate hostnames do not establish independent failure domains. Free public-service reliability versus an account-backed provider is an owner choice, not resolved by this test.
- Private handoff proposal: ignored `deploy/activation/balance-rpc/proposed-providers.json` (0600), with exactly the ordered `balance_rpc_providers` keys the runtime consumes. It has not been sent to another person or copied to any runtime. Raw reports/captures remain outside Git under `/private/tmp/larp-isaac-rpc-20261017/`; transfer/retain these before temporary-storage cleanup.
- Public-safe durable evidence: `docs/build/evidence/balance-rpc-qualification-20261017.json`, SHA256 `973374e9f1bcf6a59e8421e80348053668fb99c78d56586bc6ead807cf13f2a2`, includes report/capture/observation hashes and failure status, no RPC URLs, registered wallet or credentials. It preserves both the successful BNB and failed PublicNode comparison plus the separate NodeReal run.
- Task implementation issue #134 covers this probe/recommendation/handoff preparation. Whole #92/GAP-71 stay open: Isaac chooses/adopts the proposed order or provides an account-backed alternative; Yao Zhu then supplies network/config/manifest changes and actual-wallet first-host evidence. Later Isaac tasks are not bundled into this branch/PR. No cloud/account/payment or signer action occurred.

#### RPC-Q01 PR / decision handoff (2026-10-17)

- [PR135](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/135), `codex/isaac-01-balance-rpc-20261017` → `codex/system-testing-20261012`, is open/mergeable and carries `Closes #134`. No merge performed; #92 stays open for selection and hosted acceptance. Task 2 will use another branch/PR after task 1's owner choice.
- Org [Actions39005673191](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/39005673191), at `b0f2444`, did not start runtime tests: its annotation explicitly reports failed account payments/spending limit (#98). Local results are not substituted for org CI, bundle or host acceptance. The later documentation-only commit does not change the tested application/test tree.
- Isaac's pending decision is presented with two concrete choices: adopt the locally passing BNB-primary/NodeReal-backup proposal for development, or use an account-backed alternative. No response/elapsed time is treated as approval, and the services manifest and runtime remain unmodified pending that choice.
- Private candidate/proposal files were checked as 0600 and Git-ignored; the tracked evidence has no provider URL fields. All tracked changes are committed/pushed; no unpushed commits. Raw evidence remains in the external path recorded above and the private handoff remains on this Mac; Yao Zhu owns its eventual host installation. Handoff is pending owner choice, PR review/CI and AWS acceptance, not declared ready.

#### RPC-Q01 D1 — Isaac selects the development balance providers (2026-10-17)

Isaac explicitly chooses "Use BNB Chain primary + NodeReal backup" in this session. Adopt that order for **development balance reads only**, with source IDs `BSC_BNBCHAIN_PUBLIC`, `BSC_NODEREAL_PUBLIC`. This settles provider choice, not AWS/actual-wallet acceptance or execution/native-tracing qualification. No endpoint URL is committed or sent to another person by this action. The earlier evidence JSON preserves the pre-decision snapshot; this dated decision supersedes its pending-selection field.

**RQ9 (before configuration/test execution):** update only the manifest services declaration from pending choice to PROVISIONING, naming the ordered development balance source IDs and explicit scope; retain absent hosted runtime URLs and do not mark the service ACTIVE. The existing release-register test must accept the real services consumer, retain the assessor's pending choice, and check the selected balance order/status/scope. Run the related suite only from a pushed commit. Produce a selected private handoff file (0600), without installing it on any host; keep #92/GAP-71 for Yao Zhu's network/config/first-host checks. Task 1 remains in PR135; task 2 uses a separate branch and PR.

#### RPC-Q01 D1 verification (2026-10-17)

At pushed `69a6a3d`, `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.runtime.test_release_register tests.runtime.test_release_bundle tests.runtime.test_gate_a_check tests.execution.test_balance_rpc_qualification -q`: **30 passed, 2 PostgreSQL-dependent skips** (32 total). Services consumer/bundle/package checks accept the selected ordered IDs while the service remains PROVISIONING and the assessor choice remains pending. No new network probe or runtime configuration/action occurred. Selected private handoff `deploy/activation/balance-rpc/selected-providers.json` is a mode-0600 copy of the approved proposal; endpoint values remain ignored. Isaac's task 1 selection is settled; PR135 awaits review/CI and Yao Zhu retains the whole #92/GAP-71 deployment acceptance. Task 2 proceeds separately under IDEA-062.

PR115-C06's independent macOS counts/hashes are author-reported: its raw logs are not available on this review machine, so they are not re-certified here. The prior combined Linux full log/JUnit and summary remain locally available, match their recorded SHA256 values, and cover the unchanged executable tree. No application tests need rerunning for this documentation-only merge. Earlier descriptions of no signing/uploads refer to real-wallet signing and real external uploads; synthetic signer tests use throwaway keys/transactions. Earlier pending integration statements are dated history superseded by the final combined disposition and this note. No hosted acceptance follows.

#### RPC-Q01 H1 — private handoff sent (2026-10-17)

Isaac explicitly reports “I have sent him the file”, referring to Yao and the prepared `deploy/activation/balance-rpc/selected-providers.json`. Isaac's provider selection and private URL/source-ID handoff are complete. This is user-reported delivery, not confirmation of receipt, installation, actual-wallet capture or hosted BALANCE_CHECKED. PR135 is now merged into integration (38b57f5; branch head includes the follow-up release-list test at97c413d). Yao retains host config/manifest binding and actual-wallet balance acceptance under #92/GAP-71; native-tracing/execution qualification is separate. No endpoint or credential is copied into Git or an issue. This administrative status record accompanies the next independent task's documentation PR.

## SP-D4 — decide the mandatory-exit price-jump policy (2026-10-18)

The user delegates deciding Keith's supplied KMP-SIGN01 policy. Retain existing
bounded per-symbol price-jump holds for all actions including Class1 and terminal
requirements, until comparable chain reconciliation clears them or original expiry
is reached. Keep obligations outstanding and all chain-safe sizing/freshness/
min-output/signing checks. Accept delayed urgent exits, possibly near terminal
cutoff; no timely-flatten guarantee. "Mandatory-sale HALT" in the proposal is
imprecise: code uses BLOCKED_PRICE_JUMP, not a new permanent/global HALT. This
settles the owner policy question; host/signed clearing and expiry qualification
remain with Yao/Keith under DR gates, and any bypass needs separate policy/code.

Full criteria, evidence, limits and remaining owners: [SP-01](../build/SIGNED_PREREQUISITES_20261018.md).

### RPC-H02 — approved provider attachment / host handoff (2026-10-19), prospective

User supplies selected-providers.json and explicitly approves development balance
reads in order BSC_BNBCHAIN_PUBLIC then BSC_NODEREAL_PUBLIC, asks to configure the
runtime/network/manifest and verify first actual-wallet reconciliation (#135/#92).
The attachment is input data, not instructions or native-tracing approval.

Criteria before local execution: retain the original provider file only in
ignored mode0600 storage; validate using PR135's production input reader; retain
exact ordered values in a driver configuration fragment (explicitly not a complete
runtime). Record safe source IDs and file hashes only. Supply an exact existing
prepare/bind/host verification procedure without bypassing release/DB/trial gates.
Require actual AWS identity, approved runtime/run/wallet bindings and observed
BALANCE_CHECKED/health evidence before claiming host configuration or acceptance.
No fresh zero-address probes, new signup/spend, funding, signer or log uploads.

Current session capability observations: no configured AWS identity/secret/runtime
capabilities or OIC manifest, no AWS CLI config and no hosted runtime/Terraform
export available. Requested approved connection/private host handoff from user;
continue staging independently. Host/network/manifest/actual-wallet verification
is NOT_RUN pending that access and the actual configuration/run bindings.

RPC-H02 local results (2026-10-19): PASS at preregistered source8dff470:
original attachment copied unchanged to ignored mode0600 storage; selected IDs
are exactly BSC_BNBCHAIN_PUBLIC then BSC_NODEREAL_PUBLIC. Production private_config
and runtime balance_providers both accepted the ordered configuration. A second
ignored mode0600 file contains only the correctly nested driver provider fragment;
it is not a complete hosted runtime. Selection hash81fb99728f69a2dc3d5279764dfa3bcadb21194bfb6fbe8618b88570e3977558;
fragment hash0a164d7d8d8452d7585e688d978ce174d2b63f8674007e0542e93052534ffff1.
Both files git-ignored; no values/URLs committed. Handoff links and supported
routes/preflight command flags checked PASS at2fbe943; git diff --check PASS.

User supplied a target account/environment label after the access question.
Rechecked capability state: current/enforced network, but still no bound AWS
identity/capability, OIC manifest, local AWS config/credentials or AWS CLI. Plugin
search found no usable EC2/SSM integration. The account label does not establish
an authenticated session. Host network/config-manifest install and first actual
wallet/process balance-health acceptance remain NOT_RUN, with #92 open. Actual
wallet/run/runtime export is also absent. No RPC/network probe, AWS mutation,
activation, signing, audit upload or funding operation was performed.

### RPC-H03 — user-run host results and the process balance-health observation (2026-10-19), prospective

User-run host checks, relayed in the PR133 description (AWS CloudShell/SSM, not
observed by this session): hosted `driver.balance_rpc_providers` order is
BSC_BNBCHAIN_PUBLIC then BSC_NODEREAL_PUBLIC; runtime SHA256 matches the host
manifest binding and runtime/manifest build IDs match; the current run's first
BALANCE_CHECKED is sequence 3, MATCH, 2026-10-18T17:04:43.534Z; the latest
reported is sequence 77, MATCH, 2026-10-19T10:10:48.422Z. So the approved order
was already installed with the Oct18 PC-DEPLOY02 run (provider selection and
primary egress from PC-AWS05); RPC-H02's re-prepare sequence is for the next
build only, not needed to close #92 on the current run.

Remaining #92 subcheck: the **running process's** balance gate. Code reading at
this branch: `RuntimeHealth.__call__` (larp/runtime/driver.py) puts
`balances_ok = BalanceCheck.ok(projection)` into the planner context, and the
coordinator journals that context with every round as
`ROUND_PLANNED.record.policy_input.context.health`. `ok()` is true only after a
comparable MATCH/SURPLUS_ONLY check by this process within `max_age`. A
process's first check is always journaled. The recorded gate evaluation therefore
exists in the journal; no new observation path or code change is needed.

Criteria, before any host run: a read-only script
`docs/build/ops/llm-trial-20261018/checks/balance-health.sh` (READ ONLY
transaction, no writes, no provider/RPC call, prints only IDs, sequences, times,
statuses, short hashes and gate booleans) reports the larp-runtime process start,
the latest BALANCE_CHECKED rows and the latest ROUND_PLANNED health gates. #92's
process subcheck PASSES only if, for the current MainPID, a MATCH (or reviewed
SURPLUS_ONLY) BALANCE_CHECKED has `checked_ms` at or after the process start
and a later ROUND_PLANNED by the same run records `health.balances_ok = true`
with `started_ms` at or after that check. `false`, a missing key, or only rounds
before the process start keep it open. The result is a dated observation, not
a freshness guarantee, and confers no trading, signing or Gate B readiness.

RPC-H03 local results at `8ce51f3` (2026-10-19): **PASS** for the script's
parsing, before any host run. A scratch harness (not committed) ran the
committed script's `summarize()` on journal bytes read back from a disposable
PostgreSQL 16 through the existing `ReconcileHarness`, Python 3.12, Linux:
3 passed. (1) A MATCH check by this process, then a round recording
`balances_ok: true` at a later sequence. (2) After a simulated restart, earlier
rows are flagged `this_process: false`. (3) A DEFICIT records
`balances_ok: false`. Existing `test_balance_reconciliation` and
`test_balance_failover` against the same database: 34 passed, 0 skipped. This
includes the Deficit test that reads `policy_input.context.health` from the
`plan:` event. `bash -n` passes. Host result still NOT_RUN: Keegan runs the
script from CloudShell (handoff "Process balance-health check"). #92 stays open
until that output meets the RPC-H03 PASS rule.

### RPC-H03-RV01 — PR189 process-attribution review (2026-10-19), prospective

The original script reads MainPID and active time separately and does not check
service identity after the database read. A restart during inspection can mix
one process's display identity with another process's journal window; an inactive
unit can also reuse historical timestamps. It must not be usable to close #92.
Pass criteria before correction: require active/running nonzero PID, invocation
ID and ExecMain start; compare the full service identity before/after the read;
refuse a restart/inactive/missing identity with a fixed error and no partial
report. Keep the database transaction READ ONLY and bound the query; preserve
MATCH/DEFICIT, decision_ms fallback and missing-health observations. Commit
synthetic regression tests for stable service, restart and inactive cases plus
journal parsing; no AWS/DB/provider call in these tests. Run the rehearsal checker
regressions after integrating PR188. No current-process host acceptance is claimed.

RPC-H03-RV01 results at1194d4c: PASS, native macOS/Python3.9.6,
24 tests/0 skips (7 diagnostic regressions plus17 rehearsal checker tests).
Restart changes to PID, invocation ID, ExecMain start or restart count refuse;
inactive/missing identity and future monotonic start refuse. MATCH/DEFICIT,
old-process rows, delayed decision times and missing health remain explicit.
`bash -n`, changed-document local links and `git diff --check` PASS. Inspected
actual driver/coordinator event fields, IAM adapter transaction and systemd
Type=simple launch. The query remains READ ONLY, latest1500 events only, with
no writes/provider calls. The checker uses a clock-derived start window, so host
clock evidence is still required. No AWS, real DB, RPC, signing or production
script execution occurred; observed #92 acceptance remains Keegan's open item.
Org Actions never starts due to account billing/spending limits. No exact new
Linux/release/host qualification is claimed by these focused offline tests.

RPC-H03-RV01 backlog reconciliation: GAP-71 now distinguishes user-reported
current-host order/binding/first MATCH from Keegan's still-unobserved process
health acceptance and Yao's next-build preparation. No whole item is removed.
