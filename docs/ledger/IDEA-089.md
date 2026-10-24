# IDEA-089 — S2: weekend full-sequence trade test on the dev wallet (run 4), then back to S1 on Monday

- Date / author: 2026-10-23 (17:5xZ; Saturday Oct 24 morning in Singapore) / Yao Zhu (decision), Claude Code (record)
- Status: **decided, not implemented.** This entry is the decision and its pre-registered pass criteria only. No code,
  profile, config or host change is made here; Yao's team implements it.
- Related: IDEA-049-C SJ-11 (run 3 on S1) and SJ-11-QV01 (no quote verifier), IDEA-076 / IDEA-084 PF-01 (S1),
  RV120-02 (REHEARSAL window), SKILL.md F-95, F-119, never-do #12 and #13.

## Decision (Yao, in chat, 2026-10-23)

"we are changing the rules to allow us to run a full sequence tomorrow morning, make that S2 dont make code changes
just open a pr with this decision ill ask my friends to implement it so we can run the full sequence tomorrow as a test
thats what the most important for us that our agent can actually trade, then on monday we swap back to S1 or some other
version so our final contest has the best strategy with a system that has been through error checking over the weekend
where we actually have time to go through all the errors and details"

## Why

Run 3 (RC6 `9dc5edab`, S1) is installed and healthy but has never placed an order. Two things stop it:
1. **No executable quote on the service path** (SJ-11-QV01): `service.py` wires no quote verifier, so every quote is
   `CAPABILITY_PROOF_REQUIRED`. The fix is being built separately (IDEA-088, PR268).
2. **S1 enters only in the NYSE regular session.** Its execution bounds (`larp/strategy/execution_bounds.py`
   `interval`) allow discretionary buys from `open_delay_seconds` (1800) after the XNYS open to `close_buffer_seconds`
   (900) before the close. Run 3's REHEARSAL window also ends new risk at 2026-10-25 00:00Z. The next session (Mon
   Oct 26, 13:30Z) is after it.

So even with the verifier, no part of the system after "plan" (signing, approve, swap, receipts, STORED ACK,
accounting, exit) can be exercised before Monday night in Singapore. Yao's priority is to prove the agent can actually
trade end to end this weekend, while there is time to work through every error, and to keep the final strategy
choice separate.

## What the rules allow (checked, SKILL.md §0.2)

- **F-119 (organiser clarification):** "Orders can be placed 24/7." Weekend orders are allowed.
- **F-95 (kit):** when `openState` is false in `rwa/tokens` or `rwa/underlying-market`, "don't place orders". S2
  keeps this guard unchanged. Weekend `openState` has never been measured (GAP-44 / Q-32 still open). If the API
  reports it false on Saturday, S2 does not trade, and that result is recorded; there is no bypass.
- **Never-do #12:** every broadcast swap's `tx_hash` reaches an ai-seeds round log. S2 keeps run 3's uploader and logs
  every round, with the dev wallet's ai-seeds credentials.
- **Never-do #13** concerns the registered (final) wallet. S2 uses only the dev wallet and committed, manifested code.

## S2: what it is

S2 is a **REHEARSAL-only test profile for the dev wallet**, not a contest strategy. It makes no profit claim and is never
installed for the final run. Requirements for the implementers:

| # | Requirement |
|---|---|
| S2-1 | **Scope:** `environment` REHEARSAL, `mode` dev, dev wallet `0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479` only. Deterministic, model and falsifier authority SHADOW, no hosted models (the SJ-11-C1 scope). FINAL profiles, FINAL code paths and S1's FINAL bounds are unchanged; a FINAL or non-dev profile carrying S2's relaxations must be refused (by `validate_live` and `gate_a`). |
| S2-2 | **Trading hours:** discretionary entries and exits are allowed whenever the kit's `openState` is true for both the token and its underlying market. The NYSE-session execution bounds (open delay, close buffer, XNYS session window) do not apply to S2. The planner's `MARKET_CLOSED_OR_UNKNOWN` check (`token_open` and `underlying_open`) stays as it is (F-95). |
| S2-3 | **Trades:** S1's five-name book at the run-3 sizes: target 19/100 per name (level 95%, weights 1/5), about 19 USDT per buy, BUY legs one at a time as S1 does now, then a scheduled flatten on Sunday that sells every position. Trend guard and limiter may stay at their start states (UP / NORMAL); they need NYSE sessions and are not what this test checks. If gas or time is short, the implementers may cut to fewer names, recorded with the reason before install. |
| S2-4 | **Window (Yao, 2026-10-23: "extend the whole duration for the weekend ie 0900 to sunday night"):** `trade_after` 2026-10-24 01:00Z (Sat 09:00 SGT); `new_risk_end` 2026-10-25 08:00Z (Sun 16:00 SGT); `flatten_start` 2026-10-25 09:00Z (Sun 17:00 SGT); `signing_end` 2026-10-25 15:00Z (Sun 23:00 SGT); flat before `signing_end`. The run can be installed at any time inside the buy period, so the team does not need to be up at 09:00; a run installed after `new_risk_end` makes no entry. The window ends well before Monday's NYSE session (13:30Z), when the next run swaps back. S1's book is built once and then held, so a second full cycle inside the weekend needs a new profile hash (and a new run). |
| S2-5 | **Unchanged:** CAP-02 policy `3241abd3…`, UNTRUSTED router policy `05759e90…`, L = 660 s / m = 30 s, initial gas only, per-trade cap, minimum trade, entry-cost cap, slippage limit, basis check (IDEA-086), signer caps and refusals, HALT, quarantine, nonce barrier, uploader and archive. |
| S2-6 | **Prerequisite:** SJ-11-QV01's quote verifier merged, and its live read-only quote check returns `VERIFIED_EXECUTABLE` for every S2 name at the S2 size shortly before install. A dropped quote must journal its reason. |
| S2-7 | **Run:** a new build (RC7) containing QV01 and S2, a new run (proposed `larp-dev-rehearsal-20261024-s2`) and database `larp_rehearsal4`, a fresh M3 coverage review against S2's sizes, and Isaac's approval of the S2 profile hash and the new `signer.json` before P4. Run 3 is retired by R1p/R1s as usual. The RC6 sheet is copied to a new RC7 folder; only identities, pins and the profile change. |
| S2-8 | **Both sides of the hours rule.** `execution_bounds.interval` is used twice: by the planner (`reserve`) and again by the execution service's admission check (`permitted`, via `execution_live/main.py` `_execution_permitted`). S2's hours relaxation must apply in that one function (or both callers), or execution refuses every S2 intent after the planner accepts it. A test must show a planner-accepted S2 BUY admitted by `permitted` at a weekend time. |
| S2-9 | **Attempt budget over a weekend.** S1 counts attempts per leg per NYSE session, and the whole weekend sits in one session (Friday's, `next_open` Monday 13:30Z). With `max_attempts_per_leg_session` 3, each name gets 3 BUY quote rounds for the entire window. S2 sets it to 5, the validator's maximum, and records how many were used. |
| S2-10 | **Runtime config for PR268.** PR268's verifier is enabled only when the runtime driver block carries `untrusted_router_policy_file` / `untrusted_router_policy_sha256` (LD03 `05759e90…`) with the balance RPC providers. M4 (or `prepare_shadow`) must write that pair into run 4's `runtime.json`, and the policy file must be readable by the runtime user. Without it the runtime behaves exactly like run 3: no executable quote. |
| S2-11 | **Gas decision in PR268.** PR268 prices the entry-cost cap on expected gas and keeps the full reservation elsewhere (QV6). Isaac and Keith decide it before merge. If it is reverted, 19 USDT entries are refused with `ENTRY_COST_CAP`, and S2 cannot buy. |
| S2-12 | **Before install, also check the exit side:** run the PR268 quote check with `--side SELL` (hypothetical amount) for each name, and confirm the runtime is up across 00:00Z Sunday so the UTC day roll anchors Sunday's risk day (without it, Sunday buys are refused as `NEW_RISK_HALTED`). |

Implementation pointers (not decisions): S1's NYSE bounds are in `larp/strategy/execution_bounds.py` (`interval`,
`reserve`) and the windows in `larp/strategy/profiles.py`; the deterministic SHADOW rehearsal admission is in
`validate_live` and `gate_a.scoped_rehearsal` (SJ-11-RH01); the rehearsal builder and caps review pin the profile
(`build_rehearsal_candidate.py`, `review_rehearsal_caps --profile`, the M3 probe hash). Equal weight's
one-discretionary-swap-per-session rule (`DISCRETIONARY_CADENCE`) would allow only one buy over a weekend, which is
why S2-3 keeps S1's per-leg budget.

## Pre-registered pass criteria (written before anything runs)

| # | Pass when | Evidence |
|---|---|---|
| P1 | The live quote check returns `VERIFIED_EXECUTABLE` for each S2 name at the S2 size, at install time | quote-check output |
| P2 | At least one BUY completes end to end: intent, signing request, signature, approve receipt, swap receipt, STORED ACK, round log with the `tx_hash` | `checks/trading-status.sh`, chain monitor, BscScan |
| P3 | After the entries, the balance check is MATCH: ledger equals chain for USDT, BNB and every stock | `BALANCE_CHECKED` event |
| P4 | The flatten from Sun 09:00Z sells every position to dust before `signing_end` (Sun 15:00Z), and the final balance check is MATCH | events, chain |
| P5 | No HALT, no quarantine, 0 unit restarts, archive healthy; any signer refusal or dropped quote has a recorded reason | status checks |
| P6 | Gas per approve and swap, fill against quote, time from intent to receipt and round-trip PnL are recorded | chain monitor, ledger |

**Fail or partial result:** any other outcome is a finding, not a reason to bypass a guard. Stop new orders with
`systemctl disable --now larp-execution` on primary if anything looks wrong, record it in this entry, and fix it over
the weekend. If `openState` is false all weekend, S2 records that measurement (GAP-44) and the end-to-end test moves to
the Monday session.

## After the test (Monday)

Yao chooses the strategy for the next run and the final: S1 or another version (EXP-008 questions the trend guard).
That run starts from the weekend's fixes, with its own profile hash, build and approval. S2 is never used for the
final run.

## Owners

- Implementation: Yao's team (named in the PR). Review: Keegan.
- Profile and `signer.json` approval: Isaac (A1).
- Host, AWS and Terraform commands: Yao. No assistant key, signing, wallet or host action.

## Pre-install observation: live quote check on Saturday (Yao, 2026-10-24 03:39Z)

`tools/deploy/quote_check.py` (IDEA-088 A1, PR268 head `13bea958`), read-only, BUY 19 USDT per name, run-3 S1 profile
`6bcf1dfb…`, policy `05759e90…`, public BNB Chain RPC; output kept in the git-ignored
`deploy/activation/quote-check-20261024T0339Z.txt`.

| Name | Status | `quote_at_cap` | `token_open` / `underlying_open` | Impact bps | Deadline after quote |
|---|---|---|---|---|---|
| NVDAB | `VERIFIED_EXECUTABLE`, exit 0 | accepted | true / true | 1 | 499 s |
| GOOGLB | `VERIFIED_EXECUTABLE`, exit 0 | accepted | true / true | 1 | 500 s |
| SKHYB | `VERIFIED_EXECUTABLE`, exit 0 | accepted | true / true | 1 | 499 s |
| TSLAB | `VERIFIED_EXECUTABLE`, exit 0 | accepted | true / true | 1 | 500 s |
| MSFTB | `VERIFIED_EXECUTABLE`, exit 0 | accepted | true / true | 0 | 499 s |

Every quote: pay token USDT, receive token equal to the pinned contract in `larp.marketdata.port.TOKENS` (assistant
check), amount 19e18, `native_value` 0, recipient `UNVERIFIED_UNTRUSTED_LAYOUT` (expected for the UNTRUSTED layout),
slippage 8 bps, fee units 0, gas reserved 384000000000000 wei (`EXECUTION_FEE_AUTHORITY`), expected gas
80004608000000 wei.

**What it shows:** on Saturday 03:39Z, with the US market closed, the kit API reports `openState` true for every token
and underlying market, and the venue returns executable quotes that pass the planner's own check. So F-95 does not
stop S2 this weekend, and S2-6's quote condition holds now; it is re-run shortly before install. One weekend sample, not
the 7-day GAP-44 measurement.
