# Handoff — S5 run 7/8 monitoring and FS1 readiness (2026-10-27, ~06:40 UTC)

Linked from `docs/build/CURRENT_STATUS.md` and the IDEA-104 OBS03-B1, OBS03-B2 and S5-OBS03 run-8 follow-up items in `docs/INCOMPLETE_WORK.md`. S5-OBS03 itself is recorded in [IDEA-104](../ledger/IDEA-104.md#s5-obs03--run-8s-first-buy-aborts-on-rfq-expiry-after-the-approve-the-zero-amount-revoke-is-rejected-2026-10-27-live-observation).

## Readiness check (AGENTS.md "Thread handoff")
| Check | Result |
|---|---|
| 1. Git | PASS once the PR adding this file is pushed. Earlier work is fully merged (PR #304). This file was written against canonical head `codex/system-testing-20261012` = `74de7102`. |
| 2. Docs | PASS (follow-up commit): S5-OBS03 is recorded in `docs/ledger/IDEA-104.md` and the IDEA-104 ledger row; backlog items OBS03-B1, OBS03-B2 and the S5-OBS03 run-8 follow-up are in `docs/INCOMPLETE_WORK.md`. S5-OBS01/02 are recorded (merged in #304). |
| 3. Loose ends | PASS. No temp files in the repo; the diagnostic scripts were in a session scratchpad and are not kept. No secrets committed. |
| 4. Open items | Listed below. |

## Deadlines (UTC)
- **Run 8:** new buys stop 2026-10-27 10:00, flatten from 11:00, signing ends 15:00.
- **IDEA-109 (proposed, not confirmed):** freeze 2026-10-27 12:00; install 2026-10-27 22:00, latest 2026-10-28 02:00 (IDEA-109 "Revised dated plan", which replaces S-01's 2026-10-28 06:00).
- **F-127 (organiser):** code changes end and the project pauses 2026-10-28 10:00. The scored phase restarts 2026-10-29 02:00.

## Run-8 evidence (done: recorded as IDEA-104 S5-OBS03, its ledger row and backlog items)
Evidence gathered (read-only SSM, public BNB Chain RPC):

Run 8 = `larp-dev-rehearsal-20261027-s5-small`, build `bdd515f8` (PR305 S5-SMALL01; includes IDEA-109 #303). Dev wallet `0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479`.

| UTC | Event |
|---|---|
| 05:01 | Run 8 starts. Trend UP (session 204), limiter NORMAL, targets ~15.44 USDT/name (`S1_LEVEL_CHANGE`). |
| 05:03:47 | `aggregator/approve-transaction` ok, `approveAmount` `15441878000000000000`, vendor LiquidMesh. |
| 05:04:12 | Approve confirmed: nonce 38, tx `0x5e67cc065517f252d4cbe97c7b00b0d514e5f65a06edfd2bb19b482597403b74`, USDT `0x55d3…7955` → `approve(0xb44446b0c8e56988c34f7ff73ae904982b5fdda5, 15.441878)`, status 1. |
| 05:04:31, 05:04:39 | `pre-transaction/gas-limit` code 40435: `execution reverted … RFQ_OrderExpired`. No swap sent; record `0e22df21…` ABORTED. |
| 05:04:50, 05:04:58, 05:05:05 | Revoke `approve-transaction` with **`approveAmount: "0"`** rejected: code 40001, "invalid approveAmount, must be a positive integer string". |
| 05:05→ | `DIRTY_ROUTER_ALLOWANCE` (LOW) incident every ~2 min (USDT 15441878000000000000). Records `e639da05…` and `e813dcea…` got approve payloads (05:06–05:12, ok) but were never broadcast; both ABORTED. Last plan: `EXECUTION_BLOCKED` gate `WALLET_PENDING`; reason summaries show `LEG_ATTEMPT_LIMIT (GOOGLB)` and `BUY_RECEIVE_TARGET_REQUOTE (NVDAB)`. |
| 05:12 | Manual `systemctl stop larp-runtime` (`PLANNING_PAUSED`). Execution, evidence and uploader still active. |

State at ~06:35 UTC:
- Flat book; cash 81.3730 USDT; BNB 0.024971.
- 67 rounds / 66 audit events; 96 chunks ACK 200; archive healthy; 0 restarts.
- **On-chain USDT allowance to `0xb444…dda5` = 15.441878 (still open).** Next nonce 39, so only one tx was sent.

Not yet determined (my last read-only query was cancelled). These are open items 9 and 10 below, recorded in S5-OBS03 as open, not as findings:
- Whether a fresh quote was fetched between the approve and the reverted gas estimates.
- Why attempts 2 and 3 were never broadcast. Likely cause, unconfirmed: the dirty allowance plus the attempt limit.

## Open items
| # | Item | Owner (per backlog) | Recorded? |
|---|---|---|---|
| 1 | **Bug: allowance clean-up cannot work.** `larp/execution_live/venue.py:72-73` revokes with `approveAmount='0'`; the live API rejects zero. FS1 recovery profile `b8ba06e2…` (IDEA-098/AL9) relies on it, and the FS1 flatten requires all router allowances to be 0. A fix needs Isaac's signer-policy decision, e.g. another revoke route or accepting a 1-unit allowance. | Isaac (signer policy), Keegan (code) | Yes: IDEA-104 S5-OBS03 + backlog |
| 2 | **Bug: first buy aborts when the RFQ quote expires during the approve.** About 25 s from the approve request (05:03:47) to its confirmation (the quote time is not recorded); the gas estimate reverted `RFQ_OrderExpired` and the leg aborted instead of re-quoting. Similar to run 4's S2-F6. Likely to hit FS1's first entries. | Keegan, Keith | Yes: IDEA-104 S5-OBS03 + backlog |
| 3 | **Run 8 decision:** the runtime is stopped and a 15.44 USDT allowance is open. Restart, clean up, or retire before FS1 install (R1p/R1s). | Yao (run owner) | Yes: `docs/INCOMPLETE_WORK.md` S5-OBS03 run-8 follow-up |
| 4 | **Database (S5-OBS02):** ARCH-01 trigger (b) is met, so slim per-event rows before final activation. `db.t4g.small` is refused on the free-plan account (PR305), so the instance stays `db.t4g.micro`. Read RDS Monitoring 22:30–04:00Z (2026-10-26/27) to name the starved resource. Restart pacing (full journal re-verification per restart). | Keegan (ARCH-01), Yao (RDS) | Yes: `docs/INCOMPLETE_WORK.md` DB-01, ARCH-01, IDEA-109; IDEA-104 S5-OBS02 / S5-SMALL01 |
| 5 | **FS1 release** must be built from a commit containing all fixes, including any for items 1–2. The FS1 profile hash `b8ba06e2…` is unaffected by code-only fixes. | Keegan | Yes: IDEA-093 / IDEA-099 backlog items |
| 6 | Close `claude/fs1-integration-20261026` (superseded by PR296). | Branch owner | PR #304 body only |
| 7 | FS1 sizing margin (information): mid level ≈ 20.4 USDT/name vs the 18.64 minimum; no new entries at the limiter's lowest level (≈ 10.2). | Keith | Yes: IDEA-104 S5-OBS01 |
| 8 | Hosted CI billing-blocked; the host-bundle and systemd tests remain for the exact merged build. | Keegan | Yes: IDEA-109 backlog item |
| 9 | **Unconfirmed: was a fresh quote fetched before the `RFQ_OrderExpired` gas estimates (05:04:31, 05:04:39)?** If not, the executor estimated gas on the stale pre-approve quote, contrary to the kit's approve → confirm → re-quote → gas estimate order (F-105). If yes, the fresh RFQ order expired again and the abort-instead-of-retry is the issue. It decides how bug 2 is fixed. **How to check (read-only):** on the primary, list every API artifact under `market_artifact_root` with `requested_at` 05:03:00–05:13:00Z (all endpoints, not just approve/gas-limit). Print endpoint, outcome, code, and the quote's deadline/expiry and `toTokenAmount`. Then compare with the execution record `0e22df21…` (`attempts`, `prepare_probes`). | Next session; then Keegan | Yes: IDEA-104 S5-OBS03 + backlog |
| 10 | **Unconfirmed: why attempts 2 and 3 (`e639da05…`, `e813dcea…`) were never broadcast.** They received approve payloads 05:06–05:12 (API ok, gas estimate ok) but no signing request (`signing_requests` = 1 total) and ended ABORTED. Candidates: the open USDT allowance (`DIRTY_ROUTER_ALLOWANCE`) blocking a new approve, `WALLET_PENDING`, or `LEG_ATTEMPT_LIMIT`. **How to check (read-only):** on the primary, print each record's `blocked_reason`, `attempts`, `prepare_probes` count and `last_observed_at`. Check its `ABORTED` transition in `execution_records.state` (the earlier query crashed on `len()` of an int field). Grep the execution service's code path that sets ABORTED before signing. | Next session; then Keegan/Isaac | Yes: IDEA-104 S5-OBS03 + backlog |

## How the checks were done (for the next session)
- AWS identity `larp-claude-session` (region `ap-southeast-2`).
  - Allowed: `ec2:DescribeInstances`, `ssm:DescribeInstanceInformation`, `ssm:ListCommands`, `ssm:GetCommandInvocation`, `ssm:SendCommand`.
  - Denied: CloudWatch, RDS, IAM, `ec2:DescribeInstanceStatus`.
- boto3 is not preinstalled in the Claude container: `pip install --target <scratch dir> boto3`.
- Primary `i-040fc5fea8b700e9a` (SSM online). Signer `i-0f8fe5d5fe5ccba36` has SSM removed by design after run-sheet step T2.
- Read-only database pattern:
  - On the primary: `cd /opt/larp/current && runuser -u larp-execution -- .venv/bin/python -`.
  - Subclass `IamPostgresStore` to `SET TRANSACTION READ ONLY`; config `/etc/larp/execution.json`.
  - API artifacts: the JSON files under `market_artifact_root`.
- Exception text is never logged by the services (by design). Use the database, the API artifacts and on-chain reads instead.
- Public RPC `https://bsc-dataseed.binance.org` for tx receipts, allowance (`allowance(owner,spender)` selector `0xdd62ed3e`) and nonce.
