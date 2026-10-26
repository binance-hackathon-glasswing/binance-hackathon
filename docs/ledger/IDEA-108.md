# IDEA-108 — Final-run failure analysis and safeguards (activation Oct 27–29, scored run Oct 29 – Nov 12)

- Date / author: 2026-10-26 SGT / drafted with Claude Code at the user's request
- Status: open (analysis complete; every safeguard below is recommended, not decided)
- What: a review of what can still go wrong between now and the end of the winner audit, and what to put in place
  before the build is frozen. Each finding names its evidence, its trigger, what it costs, and a safeguard with a
  suggested owner (owners follow the IDEA-024/IDEA-038 split; the team decides).
- Why it matters: from the scored start no person may change, restart, pause or flatten the agent (F-114, F-117,
  F-124). A failure that needs a person is therefore a failure for the rest of the run. Every safeguard has to be in
  the registered build, or in infrastructure settled before install.
- Cost / risk: the code safeguards (S-03, S-04) are small but touch the frozen candidate and need their own red/green
  tests and owner review before the freeze; the infrastructure ones (S-05..S-07) need no code change but must be done
  before P4, outside any run.
- Links: F-14, F-99..F-101, F-114..F-126; G-03, G-08, G-18, G-19; Q-04, Q-35, Q-39, Q-40; GAP-29, GAP-52, GAP-62,
  GAP-73..GAP-75; IDEA-085, IDEA-093..IDEA-100, IDEA-104; [S5/FS1 readiness](../build/S5_FS1_READINESS_20261026.md);
  [FS1 run sheet](../build/ops/final-fs1/README.md).

## 1. Scope and method

Reviewed on `codex/system-testing-20261012` at `c997df2c` (2026-10-26 19:42 SGT): the FS1 FINAL profile
`fs1-final-recovery.json` (`b8ba06e2…`), the runtime, execution, settlement, audit-delivery and halt code, the systemd
units, the AWS Terraform, the S5/FS1 readiness checklist, the FS1 run sheet, `INCOMPLETE_WORK.md` and the dev-run
incident records (IDEA-085, IDEA-094, IDEA-095, IDEA-096, IDEA-100). Read-only: no host, wallet, database, provider or
AWS account was touched and nothing was run. Findings about code paths come from reading the code, not from tests;
the ones marked *verify* need a measurement before anyone relies on them.

Failures fall into three classes, by who recovers:

| Class | Meaning | Examples in this build |
|---|---|---|
| Self-healing | The agent recovers on its own | systemd `Restart=always`; EC2 auto-recover/auto-reboot alarms; delivery and repeated-failure HALTs that clear themselves |
| Fail-closed, auto-clears | Trading pauses, then resumes when the cause goes | HALT:CLOCK, DELIVERY_DEADLINE, DELIVERY_AGE, REPEATED_FAILURES |
| **Fail-frozen** | Trading stops and nothing in the build can restart it | exit codes 2/3/4; ABNORMAL latch; a permanently refused round log; a missed day roll (frozen for one day) |

The fail-frozen class is where this review spends its effort, because during the run it has no remedy.

## 2. Findings

Likelihood and impact are judgements (H/M/L). Impact assumes no human action is possible.

### Before the freeze and during activation (Oct 26–29)

| ID | Finding | Evidence | Likelihood | Impact |
|---|---|---|---|---|
| FR-01 | **Schedule.** FS1 FINAL is BLOCKED on about ten owner inputs (history binding, exact release, fresh Q1/M3 caps, signer approval, model adoption/budget, host checks). The install must finish before the self-check buy cutoff, **2026-10-28T18:00Z**. F-126 allows changes until Oct 28, which overlaps that cutoff: the last change, the release build and the install can land in the same few hours. | S5_FS1_READINESS (both BLOCKED); run sheet F0..F0d, P4–P6 | H | H: no self-check (F-14 "pre-final integrity check"), or an unverified build goes live |
| FR-02 | **No CI on the exact release.** GitHub Actions did not start (run 40311935172, account spending limit). Recent receipts are local or mirror runs on earlier sources. | S5_FS1_READINESS "GitHub run…executed no jobs"; R-14 open | H | M: the registered bytes may never have passed the pinned suite as a whole |
| FR-03 | **Final wallet's `AI_SEEDS_SECRET`.** Still open in the repo (Q-35, R-02 due Oct 26). The uploader retries a 401 forever (`delivery.py`): a wrong or missing secret leaves every log undelivered, and every fill becomes "fill without log" at the daily check. | F-100, F-101, F-113; `larp/audit/delivery.py:15` (only 400/413/422 are permanent) | M | **Very high**: audit failure → result removed (F-48, F-66) |
| FR-04 | **Self-check outcome.** The SKHYB buy and sell (~32 USDT) is the first real trade on the final wallet. If it exposes a defect, whether a corrected version may still be registered before Oct 29 is open (Q-40; F-125 reading (c)). | IDEA-093 SC; F-125; Q-40 | M | H if a defect appears with no permitted fix |
| FR-05 | **A refused self-check log blocks the whole run's buys.** `deadline_breaches` counts every chunk whose status is not `ACK`, including `PERMANENT` (a 400/413/422 refusal), which never becomes `ACK`. After that log's 02:00 UTC deadline, DELIVERY_DEADLINE is active for good: no new buys or discretionary trades for the rest of the run (mandatory sells still pass). On the self-check log, FS1 would never build its book. | `larp/audit/delivery.py:18-23`; `larp/runtime/supervision.py` (DELIVERY_DEADLINE); `larp/runtime/halts.py` (PAUSING) | L (chunking keeps records under 256 KiB, `protocol.py:90-94`) | H |
| FR-06 | **Database fixes not installed.** IDEA-100 DB1 (alarms), DB2 (query visibility, needs one RDS reboot) and DB5 (archive backoff/cap) are required before activation and are not installed. | INCOMPLETE_WORK DB-01; IDEA-100; run sheet F0d | H unless done | H: the Oct 25 stall recurs without warning |
| FR-07 | **RDS maintenance can reboot the database mid-run.** No `preferred_maintenance_window` or `preferred_backup_window` is set, so AWS picks a weekly 30-minute window. `apply_immediately = false` means any pending modification is applied in that window. Required OS maintenance is also scheduled there. | `deploy/aws/storage.tf:96-130` (no window keys; line 123) | M | M–H: a DB restart is a runtime restart (FR-12) at a time nobody chose |
| FR-08 | **Model inputs.** Adoption ref (F0m), budget reconciliation (F0b) and keys (F0s) are open. AIand credit runway and expiry are unrecorded. Without `LARP_MODEL_API_KEY`, ChatGPT is never used. The official page asks for an LLM-powered agent (A-REQ-079). | Run sheet F0m/F0b/F0s; IDEA-057 | M | M: trading continues (`assessment_required: false`), but the agent may run the whole scored window with no working model |

### During the scored run (Oct 29 – Nov 11), no human action

| ID | Finding | Evidence | Likelihood | Impact |
|---|---|---|---|---|
| FR-10 | **Exit codes 2/3/4 stop a service for good.** Every unit has `RestartPreventExitStatus=2 3 4`. In `larp.runtime.service.main`, any `OSError` raised while building the driver becomes a start refusal (exit 4). `ConnectionError`, `TimeoutError` and socket errors are `OSError` subclasses. Today `build_driver` constructs clients lazily and makes no network call, so the trigger is a file-level fault at restart. The mapping is fragile, though: a future network call there turns a transient blip during an automatic restart into a dead runtime. The other services' exit paths were not traced in this review (*verify*). | `deploy/systemd/larp-runtime.service:29` (and execution 25, signer 27, uploader 22, evidence 27); `larp/runtime/service.py:452,545,567` | L | **Very high**: runtime stopped for the rest of the run, positions held, no flatten |
| FR-11 | **One missed midnight = one day without new risk.** The daily risk anchor is only taken inside `day_roll_window_ms` after 00:00Z (5 min in the Gate A settings). If the runtime is restarting, the market fetch fails, or the database stalls for that whole window, the planner refuses new risk for the entire UTC day. There are 14 midnights. The first that matters is **2026-10-29T00:00Z**, before the first buy at 14:00Z. | `larp/runtime/driver.py:440-475` (line 469 returns `OUTSIDE_WINDOW`); run sheet "must be up across every 00:00Z" | M (over 14 days) | M: the book is built a day late, and re-entries after the 8% stop recovery or a trend flip wait a day |
| FR-12 | **Restart pause grows to ≈17 min by day 14.** Each runtime or execution restart verifies the whole journal once. The runtime does it before its watchdog starts; execution does it at its first intent. That first intent (authority 660 s) is likely to expire. A restart that starts in the ≈20 min before midnight also hits FR-11. | IDEA-095 "Residual 14-day risks"; profile `execution_authority_seconds: 660` | M | M |
| FR-13 | **Permanent freeze on an ABNORMAL fill.** A finalized swap with a different pay amount, output below the authorized minimum, or any extra token movement is recorded as ABNORMAL (`SUSTAINED_QUARANTINE`). Nothing clears it, and `permits()` then refuses every intent, the terminal flatten included. The wallet is held as-is to the end, valued by an unknown method (Q-04). | `larp/execution_live/settlement.py:127-139`; `larp/runtime/halts.py:37`; `larp/integration/settlement.py:198-202` | L (RFQ fills in full or reverts, F-97) | **Very high** |
| FR-14 | **Database capacity.** `db.t4g.micro` (1 GB). Run 5 sits at ≈10 % CPU, which is the burst baseline. Events average 202 KB raw and the largest is 1.56 MB. The Oct 25 stall is the precedent. Unlimited mode now borrows credits rather than throttling, against about US$141 of account credit; the Free plan closes the account if the credit runs out (IDEA-046 B4). | IDEA-100 (stall, billing check) | M | H: a stall → login timeouts → restart loop → FR-11/FR-12 |
| FR-15 | **Primary host has no CPU-credit or memory alarm.** It is a `t3.small` (2 vCPU, 2 GiB) with `standard` credits, so it throttles to a 20 % baseline when credits run out. The units' `MemoryMax` values add up to about 3 GiB (runtime 1 G, four services at 512 M), above physical RAM, so the kernel OOM killer can act before any per-unit cap is reached. The run-4 archive OOM is the precedent. | `deploy/aws/variables.tf:94`; `deploy/aws/hosts.tf:82`; `deploy/aws/monitoring.tf:71` (the only CPU-credit alarm is on RDS); `deploy/systemd/*.service` MemoryMax | M | M–H: slow cycles → watchdog kills → restart pauses |
| FR-16 | **Gas-price ceiling.** The signer refuses any price above 0.16 gwei. Dev runs observed 0.053–0.062 gwei, about 2.6× headroom. A sustained spike blocks every signature, flatten included. Mandatory sells retry every 15 min, so a short spike only delays them. | `config/hosts/execution.example.json:31`; dev-run evidence `gasPrice` 53,000,748–62,282,249 wei | L | H only if sustained through the flatten window |
| FR-17 | **Gas must last the whole run.** `initial_gas_only: true` means the agent never buys BNB. The 30 USDT seed is ≈0.041 BNB at the profile's US$722 price, against a 0.01536 BNB exit reserve and 0.001536 BNB per action. That is ample unless BNB is lost elsewhere (e.g., repeated reverts). BNB is valued at a fixed price, which hides a ≈15 % position from the loss latches (GAP-73). | profile `initial_gas_only`, `exit_gas_reserve_units`, `quote_cost_summary.bnb_price_units` | L | M |
| FR-18 | **Model outages.** In the unsigned trial, 29 of 70 assessments were UNAVAILABLE (25 deadline). Trading does not depend on them, but red-flag exits and the agentic evidence in the logs do. | INCOMPLETE_WORK IDEA-056/057 (PC-STOP01) | H | L–M |
| FR-19 | **Flatten window.** Flattening runs from Nov 10 19:00Z until signing ends Nov 11 14:45Z (≈20 h, about 79 mandatory-retry slots, wallet trades serial). Holdings remain at the end only if FR-10, FR-13 or FR-16 coincide with it, or `openState` stays false for most of it. | profile `flatten_start`, `signing_end`; IDEA-102 | L | M (Q-04 valuation unknown) |
| FR-20 | **Clock.** HALT:CLOCK blocks every signature, exits included, and clears on its own after a synchronised window. A Time Sync fault therefore pauses everything. | `larp/runtime/supervision.py` `_clock_window`; R-08 drift alarm (Gate A) | L | M |

### Market and outcome (not failures; exposure the design accepts)

- **Concentration.** FS1 holds 95 % of capital in five correlated technology names while the trend guard reads UP (60 % / 30 % otherwise). A sector fall of ≈8.5 % stops new buys; ≈12.6 % forces a cut to 40 % gross, selling into the fall. This was decided (IDEA-084). EXP-008 measured S1 at −0.58 pp per 10 sessions against equal weight, −0.33 pp of it from the trend guard; FS1 keeps equal weights and the guard.
- **Event calendar around the start** (*confirm dates*): the FOMC meeting scheduled for Oct 27–28; mega-cap Q3 earnings that usually fall in the last week of October; US midterm elections on Nov 3. US daylight saving ends Nov 1, and the frozen calendar already handles it (Oct 30 opens 13:30Z, Nov 2 opens 14:30Z). The first FS1 buy (Oct 29 14:00Z) can meet wide RFQ spreads after an earnings gap; the 50 bp cost gate refuses expensive entries rather than paying them.

### After the run (Nov 13–20, winner audit)

- **FR-30 Evidence retention.** RDS automated backups keep one day (Free plan), so the S3 archive (Object Lock), the final snapshot and journald collection (R-06) are the only complete copies of the journal and the model inputs/outputs that F-49 asks winners to provide. A teardown before the audit ends would destroy the local logs that F-47 requires.
- **FR-31 Human access looks like intervention.** Read-only checks over SSM during the run are allowed by the run sheet, but nothing records them for the audit.

## 3. Safeguards, by deadline

Suggested owners only; the team assigns. Code changes need red/green tests, review and the normal release path before
the freeze. Rules that bind every row: commit and push before running (F-61); no change after the freeze (F-117).

### Today and before the code freeze (propose **2026-10-27T12:00Z**)

| # | Safeguard | Answers | Suggested owner |
|---|---|---|---|
| S-01 | **Fix the freeze time and a go/no-go timetable now.** Code freeze 2026-10-27T12:00Z; release built and checked by 2026-10-27T18:00Z; install (P4→S2→P5→P6) done by **2026-10-28T06:00Z**, 12 h before the self-check cutoff. Anything not accepted by the freeze ships as the current FS1 or is cut, never patched during the install. | FR-01, FR-04 | Team (Keegan as release owner) |
| S-02 | **Run the pinned full suite on the exact release commit** (lift the GitHub spending limit, or run the pinned Linux/Python 3.12.15/PostgreSQL 14.24 suite locally on that commit) and record the receipt with the release. Check that the bundle rebuild reproduces its hash (R-14). | FR-02 | Keegan; account owner for billing |
| S-03 | **Day roll: allow a late anchor.** When the window passes because of a restart or `MARKET_UNAVAILABLE`, roll on the first cycle with complete marks and journal it as `LATE_ROLL`. The deferred-roll path for price-jump holds already does this; extend it to these causes. The cheaper alternative is a wider window (e.g., 60 min). Trade-off: the daily-loss anchor is taken a little after midnight. | FR-11, FR-12 | Keith (risk semantics) + Keegan (driver) |
| S-04 | **Do not turn transient faults into permanent refusals.** In `service.main`, keep `ContractError`/`ValueError` as refusals, but let `ConnectionError`, `TimeoutError` and other non-deterministic `OSError`s exit 1 (systemd restarts). Trace the same paths in execution, signer, uploader and evidence (*verify*). If the team prefers no code change, record the acceptance and run S-08's restart drill. | FR-10 | Keegan (runtime), Isaac (execution/signer) |
| S-05 | **Decide FR-05 and FR-13 explicitly.** Recommended: keep both fail-closed (an abnormal fill or a refused log is an integrity problem that pausing limits), and make the activation self-check prove they are absent (S-10). Record the decision in GAP-62's deviations if accepted. | FR-05, FR-13 | Keegan + Isaac |

### Infrastructure before install (no code change; outside any run)

| # | Safeguard | Answers | Suggested owner |
|---|---|---|---|
| S-06 | **Database.** Apply IDEA-100 DB1/DB2/DB5 and do the one planned RDS reboot (F0d). Then run `aws rds describe-pending-maintenance-actions` and `describe-db-instances` (`PendingModifiedValues`), and apply anything pending now. The maintenance window is weekly and cannot be moved past the run, so pin `preferred_maintenance_window` to a quiet slot away from 23:30–01:00Z and from the flatten window, and pin `preferred_backup_window` away from midnight too. Consider `db.t4g.small` (2 GB) for the run: roughly US$9 more over 14 days against US$141 of credit, double the memory and CPU baseline; the class change needs its own reboot before P4. | FR-06, FR-07, FR-14 | Yao (Terraform/host), Keegan reviews |
| S-07 | **Primary host.** Add a `CPUCreditBalance` alarm for both hosts, read `free -m` and swap during S5, and either move the primary to `t3.medium` (4 GiB) or set `unlimited` credits for the run. Check `describe-instance-status --include-all-instances` for scheduled EC2 events before install. | FR-15 | Yao |
| S-08 | **Measure the restart.** Before the freeze, time one runtime and one execution restart against a journal grown to day-14 size, on the real host and database classes. If it exceeds about 5 min, S-03 becomes required. Do this on the dev run, not on the final wallet. | FR-10, FR-12 | Keegan |
| S-09 | **Record the money.** W0 on the final wallet: 200 USDT received (GAP-75), the 30 USDT → BNB seed and its BNB amount, zero stock and no in-flight nonce. Confirm the BNB covers the 0.01536 BNB exit reserve plus the action envelope (GAP-73). | FR-17 | Yao + Isaac |

### Activation self-check: hard go/no-go before Oct 29 14:00Z

| # | Check (read-only) | Answers |
|---|---|---|
| S-10 | Both self-check round logs are **ACKed by the real ai-seeds receiver for the final wallet** (spool empty, zero `PERMANENT` rows in `audit_chunks`), each with its swap `tx_hash` and a non-empty `reason_summary`. If a 401 appears, the final-wallet secret is wrong: stop and ask the organisers. | FR-03, FR-05 |
| S-11 | No ABNORMAL outcome and no active HALT reason after the self-check sell; `activation_self_check: DONE`. | FR-13 |
| S-12 | At least one FINAL round log contains a **real model call** (served model, request/response hashes), not only UNAVAILABLE. | FR-08, FR-18 |
| S-13 | A `DAY_ROLLED` event exists for **2026-10-29** before 14:00Z. If not, new buys are blocked that day (FR-11). | FR-11 |

### Questions for the organisers (genuinely open; send today)

- Q-40 (part c): if the self-check exposes a defect, may a corrected version be registered before Oct 29?
- Q-35: is a new `AI_SEEDS_SECRET` issued for the final wallet, and has it been sent?
- Do AWS-initiated events count as manual restarts: an RDS maintenance reboot, or an EC2 auto-recover? (F-124 allows automatic restarts; these are automatic but not the agent's own.)

### During the run (read-only, never acting on the agent)

A short daily check, logged with the UTC time and who looked, so the audit can see that every access was read-only (FR-31):
`DAY_ROLLED` for today; uploader spool empty and zero `PERMANENT` chunks; active HALT reasons; service restart counts;
RDS and host CPU-credit and memory alarms; BNB against the exit reserve; model UNAVAILABLE rate and OpenAI/AIand
budget; account credit. A finding is written down, never acted on (F-114).

### After the run

Keep the stack (`allow_teardown = false`) until the audit closes (Nov 20). Export the journal, model artifacts and
journald (R-06) to the Object Lock archive and confirm the hashes before any teardown (FR-30).

## 4. What this review does not cover

Strategy choice and parameters (decided in IDEA-084/IDEA-093), the correctness of the signer and router decoder
(IDEA-070/IDEA-088 and their reviews), and anything that needs a live measurement (restart time, host memory, real
gas). Those are marked *verify* above.

## Addendum 2026-10-26 (after F-127, the organisers' activation schedule)

The organisers set the activation timetable (F-127): code changes end and the project is **paused at
2026-10-28T10:00Z**; it is **restarted at 2026-10-29T02:00Z**, which starts the scored phase. Three consequences for
the plan above, checked against the code at `c997df2c`:

1. **The pause makes FR-11 certain on day one.** A run's risk day is its opening capture's date
   (`larp/runtime/gate_a.py:249`), and the planner refuses every BUY while today's day is not rolled
   (`larp/risk/planner.py:400`, `NEW_RISK_HALTED`). The roll only happens within `DAY_ROLL_MS = 300_000` (5 min) of
   00:00Z (`gate_a.py:25`; `driver.py:469`). A runtime stopped from Oct 28 10:00Z and restarted Oct 29 02:00Z misses
   the Oct 29 roll, so FS1 makes **no buy during the whole of Oct 29 UTC**. The first buy moves from Oct 29 14:00Z to
   about Oct 30 00:05Z, and the first scored day has no trade. Options, to decide before 2026-10-28T10:00Z:
   - **(A) Recommended:** widen `DAY_ROLL_MS` to cover the restart, e.g. 4 h (`14_400_000`). One constant, used by
     the run assembly and checked by `gate_a_check.py:78`; `DayRoll` already accepts any window shorter than a day.
     Normal days are unchanged (the first cycle after midnight still rolls within seconds); a run that was down at
     midnight rolls at its first cycle with complete marks, up to 4 h late, which also covers FR-12's restart pause.
     Needs updated tests, a new release and re-assembly before the freeze. Owner: Keegan; Keith accepts the
     anchor-timing semantics.
   - (B) S-03's late-roll code: the same effect, more change.
   - (C) Accept a day without new risk and record the reason.
2. **Order of the activation steps.** The F-125 self-check trade needs BNB, so the 30 USDT → BNB swap happens
   **before** the self-check, not at the pause (F-120). The self-check must then be bought, sold and **logged and
   ACKed** before the 10:00Z pause. The Oct 28 logs' upload deadline is 02:00Z Oct 29 (F-101), the same minute as
   the restart. If the uploader is stopped with a full spool, the self-check fills are flagged "fill without log",
   and DELIVERY_DEADLINE pauses buys after the restart until they are delivered.
3. **Revised dated plan (replaces S-01's dates):**

| UTC | Step | Done when |
|---|---|---|
| now → Oct 27 | Confirm 200 USDT (GAP-75); 30 USDT → BNB MetaMask swap on the final wallet (F-120/F-125); ask for the final-wallet secret (Q-35) | W0 recorded |
| 2026-10-27T12:00Z | Internal code freeze, including option A if adopted | release commit pushed |
| 2026-10-27T22:00Z | Install P4 → S2 → P5 → P6 on the final wallet (latest 2026-10-28T02:00Z, to leave 8 h for the self-check) | `P6_DONE` |
| by 2026-10-28T09:30Z | Self-check BUY and SELL done, wallet flat, both logs ACKed by the real receiver, zero PERMANENT chunks, no ABNORMAL or HALT (S-10, S-11, S-12) | J-SC recorded |
| 2026-10-28T10:00Z | Pause: stop runtime, then execution and signer; stop the uploader last, only with an empty spool. Remove dev wallet bindings (F-127; G-09) | all units inactive; spool empty |
| 2026-10-29T02:00Z | Restart in the run sheet's order (signer, execution, runtime after execution is healthy); this is the organiser-instructed start, after which only automatic restarts (F-124) | `DAY_ROLLED` for 2026-10-29 if option A; first scored round logged |
| 2026-10-29T14:00Z | FS1's first buy (PF-04 `trade_after`) | first BUY with `tx_hash` in a round log |

- Note: `trade_after` stays at 14:00Z, so FS1 holds cash for the first 12 scored hours. Moving it to the restart is a
  profile change (new hash and A1 re-approval) and a strategy decision for Keith (PF-04); it is not recommended this
  late.
- Questions still worth sending: is the final-wallet self-check expected before the 10:00Z pause (F-125 says
  "before Oct 29")? May the uploader keep delivering already-written logs during the pause? Is a new `AI_SEEDS_SECRET`
  issued for the final wallet (Q-35)?

## Implementation of fixes 1 and 2 (pass criteria pre-registered 2026-10-26, before any code change)

Requested by the user on 2026-10-26. Base: canonical `c997df2c` (this branch's code is identical). Environment:
Python 3.12.3 and PostgreSQL 16.15 on Linux x86_64 (the pinned 3.12.15/14.24 image cannot run here; IDEA-095 used
the same substitute). Baseline: the full suite on the unchanged tree at `7f9e6353`, recorded before the fixes.

**Fix 1 changed after reading the code.** Option A (widen `DAY_ROLL_MS`) would break IDEA-049-D #31 acceptance 2
(WR-T3b): a run that missed midnight must never re-anchor its daily loss from a post-midnight mark, because that
would forgive the losses since midnight and clear `daily_halt`. The fix keeps that rule and narrows the late roll
to the case where it cannot apply: a run holding **no stock units and no reservations**. Its equity is cash plus BNB
at the ledger's fixed `bnb_price_units` (`larp/strategy/schema.py` `equity`), so no market mark can change the
anchor, and a late roll gives exactly the anchor a midnight roll would have. This covers the F-127 pause (the wallet
is flat after the self-check) and any flat day; a run that holds stock keeps today's behaviour.

| ID | Pass when |
|---|---|
| DR-1 | A flat run (zero stock units, no reservations) whose day was not rolled at midnight rolls on its first cycle with usable market observations, at any time that UTC day (e.g. 02:00Z after the F-127 restart): one `DAY_ROLLED` for that day, `anchor_units` = cash + BNB at the ledger price, the event carries `late_flat: true`, and the planner no longer rejects BUYs as `NEW_RISK_HALTED` for the day reason. |
| DR-2 | A run holding any stock unit, or with any reservation, is unchanged: `OUTSIDE_WINDOW`, no event, risk state unchanged. WR-T1..WR-T6 and every existing day-roll test pass unmodified. |
| DR-3 | An in-window roll's event is byte-for-byte what it was (no `late_flat` key). |
| DR-4 | Price-jump holds still defer; missing observations still return `MARKET_UNAVAILABLE`; a late flat roll never rolls without observations. |
| DR-5 | Replay of a journal containing a late flat roll is exact; still at most one `DAY_ROLLED` per day; `DAY_ROLL_MS` and `gate_a_check` unchanged. |
| EX-1 | Runtime, execution, signer and uploader: a transient `OSError` raised while the service is built or its configuration is loaded (`ConnectionError`, `TimeoutError`, a `requests` connection error, a generic `OSError` such as EIO) ends with exit 1 (systemd restarts it), not exit 4. |
| EX-2 | `ContractError`, `ValueError`, `FileNotFoundError`, `PermissionError`, `IsADirectoryError` and `NotADirectoryError` still exit 4 (a restart cannot cure them). |
| EX-3 | No other exit path changes; `init`/`activate`/`check` commands are unchanged. |
| RG-1 | Full suite after the fixes: no test that passed at the baseline fails or errors; skip set unchanged; the new tests pass. |
| RG-2 | FS1-focused suites (FS1 preparation/recovery/self-check, daily anchor window, round driver service, Gate A, execution boundaries, signer, audit delivery, halts, replay) pass. |
| RG-3 | Second round, aimed at the live run: an end-to-end PostgreSQL scenario of the F-127 schedule (flat after the self-check → stopped before midnight → restarted 02:00Z → day rolled → BUY admitted at `trade_after`), plus a second full-suite run to expose order-dependent or flaky failures. Any failure found is recorded here with its cause, whether or not it is caused by these fixes. |

## Results of fixes 1 and 2 (2026-10-26, Claude Code; criteria above were committed at `ed230df8` before any code)

Code: `b6a6ae9c` (fixes and tests), `3b7a4828` (RG-3 scenario). Environment: Linux x86_64, Python 3.12.3, PostgreSQL
16.15 (not the pinned 3.12.15/14.24 image, which this container cannot run; no Docker, systemd or bubblewrap).
Nothing was deployed and no live port, wallet or provider was touched.

**What changed.**
- F1, `larp/runtime/driver.py` `DayRoll`: `flat(current)` is true when the run holds no stock units and has no
  reservations. A due roll past the window proceeds only for a flat run and journals `late_flat: true`; every other
  path (holding run, deferred price-jump roll, missing observations, marks) is unchanged. `DAY_ROLL_MS` and
  `gate_a_check` are unchanged, so no profile, runtime configuration or Gate A hash changes.
- F2, new `larp/runtime/exits.py` `refuses_start`: runtime (`service.main`, release check and `build_driver`),
  execution (`main`, release check and `build_execution`), signer (`load_config`, `router_decoder`) and uploader
  (`load_config`) keep exit 4 for `ContractError`, `ValueError` and the file errors, and re-raise any other
  `OSError`, which their existing outer handlers turn into exit 1. `init_run` (a manual command) is unchanged.

| ID | Result | Evidence |
|---|---|---|
| DR-1 | PASS | `test_dr1_flat_run_paused_across_midnight_rolls_at_restart` (crash 14 h before midnight, price halved, restart +2 h: one `DAY_ROLLED`, anchor = cash + BNB at the ledger price, `late_flat`), `test_dr1_late_flat_roll_lets_entries_plan` (BUY intents, no `NEW_RISK_HALTED`) |
| DR-2 | PASS | `test_dr2_holding_run_still_refuses_a_late_roll`, `test_dr2_a_reservation_or_a_held_unit_is_not_flat`; WR-T1..WR-T6 unmodified and passing |
| DR-3 | PASS | `test_dr3_in_window_roll_event_is_unchanged` (exact key set) |
| DR-4 | PASS | `test_dr4_late_flat_roll_needs_observations` (`MARKET_UNAVAILABLE`, no event) |
| DR-5 | PASS | exact replay in DR-1 and RG-3; one roll per day asserted; `DAY_ROLL_MS` unchanged |
| EX-1 | PASS | runtime and execution exit-code loops extended (`ConnectionResetError`, `TimeoutError`, `requests` `ConnectionError`, EIO → 1); signer `test_f2_…` at both patch points; uploader `test_f2_…`; `test_startup_exits` |
| EX-2 | PASS | the same tests: `FileNotFoundError`, `PermissionError`, `ContractError` → 4; existing refusal tests (including #59/WR17's `NotADirectoryError`) unchanged |
| EX-3 | PASS | no other exit path changed; full suite unchanged |
| Red check | PASS | on the unfixed tree `7f9e6353`: every DR-1 and transient EX case fails (exit 4 / `OUTSIDE_WINDOW`), every unchanged-behaviour case passes |
| RG-1 | PASS | full suite, base `7f9e6353`: 3005 passed, 11 skipped, 0 failed, 4069 subtests. Fixed `3b7a4828`: **3017 passed, 11 skipped, 0 failed, 4114 subtests**; per-test comparison: the only differences are the 12 new tests (all pass); identical skip set |
| RG-2 | PASS | 21 FS1-critical files (FS1 standalone/recovery/self-check/final, S5 flatten, daily anchor, round driver service, Gate A, supervision, driver, balance adoption, flatten allowance, execution loop, signer, uploader, startup exits): 320 passed, 238 subtests, three consecutive runs, identical |
| RG-3 | PASS | `tests/runtime/test_fs1_pause_restart_pg.py`: FS1 self-check BUY/SELL/DONE → paused flat across midnight → restart +2 h → `late_flat` roll → the first scored plan builds the book (BUY quote request and attempts, no `NEW_RISK_HALTED`); exact replay. Control without the roll: `NEW_RISK_HALTED`. On `7f9e6353` the scenario fails with `OUTSIDE_WINDOW` and the control passes. Second full run with the 400+ test files in **reverse order**: 3017 passed, 11 skipped, 4114 subtests, zero outcome changes against the forward run (no order dependence or flakiness found) |

**Not run here (environment), unchanged by these fixes and identical on the base:** the 11 skipped tests (real
systemd ×5 including `test_r13_*` restart conditions, bubblewrap sandbox ×3, non-root permission ×1, opt-in external
data ×2) and the offline demo `python -m larp.runtime.demo`, whose isolated worker needs bubblewrap (it stops with
`KeyError: 'entry'` on both trees here). Run them in mirror CI or on a host before the release is accepted.

**Other bugs found during the second round:** none in product code. One test-fixture limit was found and handled in
RG-3: the shared synthetic FS1 fixture has a single session, so a scored-time plan after its next open
(2026-10-11T13:30Z) is `EXECUTION_WINDOW_CLOSED`; RG-3 plans at 03:00Z inside that session instead.

**Remaining before the 2026-10-28T10:00Z cutoff:** Keegan reviews and merges; Keith accepts F1's anchor semantics
(a flat run anchors at cash + BNB at the ledger price whenever it rolls); the exact release is rebuilt from the merge
and qualified (pinned image or mirror CI, including the systemd/sandbox cases); Isaac and Yao accept the exact release
for FS1 preparation.
