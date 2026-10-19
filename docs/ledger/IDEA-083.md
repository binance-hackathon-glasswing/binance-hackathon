# IDEA-083 — Assessment time budget: per-stage shares, parallel reviewers, longer deadline

- Date / author: 2026-10-19 SGT / Yao Zhu (decision), with Claude (write-up). **Implementer: Keegan** (Yao asks him
  directly). Reviewers: Keith (model protocol/affordability), Isaac (runtime timing).
- Status: **proposed, approved in direction by Yao 2026-10-19; not implemented.** The pass criteria below are written
  before any code exists; the implementer adds red tests against them first.
- Scope: unsigned and signed routed assessments (`aiand_routed`, OpenAI-preferred routing). **Model effort stays as
  is** (OpenAI medium, AIand reviewers high). Yao: lower reviewer effort only if latency is still a problem after
  this change.

## Problem (observed, IDEA-066 PC-DEPLOY02)

The first fixed hosted job on `ea25b52` (round `cadence:1991492#1`, 2026-10-18 17:15 UTC) used all three models in
sequence and ran out of time:

| Stage | Model / effort | Step latencies | Result |
|---|---|---|---|
| openai-primary | `gpt-6.1-sol` / medium | 3.6 s, 14.1 s | ASSESSED (charges settled 6,190 + 13,792 µUSD) |
| external-review-0 | `moonshotai/kimi-k3` / high | 4.1 s, **33.8 s** (3,280 output tokens) | ABSTAIN (`UNSUPPORTED_CLAIM`) |
| external-review-1 | `zai-org/glm-5.3` / high | 3.4 s, then in flight at the deadline | UNAVAILABLE |
| **combined** | | **60,019 ms** | **UNAVAILABLE, `ASSESSMENT_DEADLINE_EXCEEDED`** |

How the deployed code spends the time (`larp/intelligence/routing.py:265-333` at `ea25b52`):

- The whole assessment is capped at **60 s**. The cap is enforced in four places: `max_deadline_ms: 60000` in
  `config/intelligence/intelligence.v1.json` and `intelligence.shadow.v1.json`; `larp/intelligence/config.py:60`;
  `larp/runtime/schema.py:37`; and `routing.py:274`, where a larger request deadline falls back to the routine path.
  `larp/intelligence/agent.py:176` also checks a step's deadline against the config.
- OpenAI gets at most half (30 s). A review runs when OpenAI is not ASSESSED, or on red-flag, event, incomplete or
  conflicting evidence, or the seeded 10 % audit (`_review_reasons`).
- Reviewers run **one after another with no per-stage allowance**: Kimi may use all remaining time, and GLM only gets
  what is left (and only runs if Kimi is not ASSESSED). A slow first reviewer starves the second.
- A timed-out OpenAI call keeps its **conservative maximum** UNKNOWN charge (about 84,764 µUSD) and its answer is lost,
  while a completed call settles at its real cost. Timeouts therefore waste money and trial headroom.
- On a large filing all three can time out: OpenAI 30 s, Kimi the remaining ~30 s, GLM ~0 s →
  `ROUTING_DEADLINE_EXHAUSTED`. UNAVAILABLE fails safe (no new risk), but the decision is lost.

## Decision (Yao, 2026-10-19)

Adopt the recommendation: raise the per-decision budget to **about 120–180 s**, give **each stage its own share**,
and run the **two reviewers in parallel**. Do not lower model effort now.

Timing context (why this does not make decisions too slow): rounds run on a 15-minute cadence or on a new filing;
an assessment stays valid for about 1 hour (`expiry_ms` − `completed_ms` ≈ 3,600 s on the 17:15 job); a round that
wants to trade re-quotes in a follow-up quote round. The hard ceiling is the runtime watchdog
`cycle_timeout_seconds` = **600 s** (a longer cycle restarts the process), and the runtime runs one round at a time,
so a burst of filings queues behind slow assessments.

## Required behaviour (implementer may tune the numbers with a recorded reason)

| ID | Requirement |
|---|---|
| B1 | Per-decision assessment budget **180 s maximum** (proposed default 180,000 ms; anything from 120,000 ms is acceptable with a recorded reason). One constant/config value drives all five places listed above; no hidden 60,000 ms remains on the routed path. |
| B2 | **OpenAI primary share ≤ 60 s** (the original per-decision figure) and never more than one third of the budget. |
| B3 | **Reviewers run in parallel**: when a review is triggered, external-review-0 and external-review-1 start together and each gets its **own allowance** (proposed: the remaining budget, capped at 90 s each), so neither can starve the other. |
| B4 | Combination keeps today's conservative semantics and is deterministic regardless of which reply arrives first: reviewer-0's ASSESSED result takes precedence, else reviewer-1's ASSESSED, else the most informative non-ASSESSED result (ABSTAIN before UNAVAILABLE); if the primary and the selected reviewer are both ASSESSED with different `_signature`s → ABSTAIN `ROUTING_FINDING_DISAGREEMENT` as today. Document any change and its reason. |
| B5 | No change to: model IDs, efforts, prompts, the routing file `a5fca50a…` (so the existing ledger's pacing/trial policies still match), review triggers, the 10 % audit seed, tool limits (≤ 6 calls, ≤ 3 per primary), or fail-safe UNAVAILABLE handling. Effort reduction is explicitly out of scope. |
| B6 | Accounting unchanged and safe under concurrency: every OpenAI POST still reserves its maximum atomically; every AIand POST passes the trial/accounting guard at its own transport boundary; two concurrent reviewer POSTs cannot bypass the trial day/total limits or the accounting quarantine. |
| B7 | Every stage's request, reply, reasoning summary, usage, latency and in-flight status is recorded in the round log and model artifacts exactly as today, for both parallel reviewers, including a reviewer still in flight at the deadline. |
| B8 | Worst case fits the watchdog with margin: budget + market/quote/balance work stays **≤ 300 s** per cycle (half of `cycle_timeout_seconds`). |
| B9 | Train/serve parity (plan.md "Declared values" table, row "Evidence loop budget (G-50)"): the historical/research evidence pass uses the same budget values, or the difference is recorded. |
| B10 | Declared deviation: add **DEV-22** to `config/release/deviations.v1.json` and plan.md §6.5, and update G-50's text in plan.md. The submitted proposal says "The loop is capped at 6 calls and 60 s per decision" (`docs/proposal/proposal_answers.md:12`); G-50 is a POLICY, so this is allowed but must be declared (F-61, GAP-62). The release register hash changes as a result. |

Proposed DEV-22 row (implementer adjusts the numbers to what is built):

> **Area:** Evidence loop time budget. **Declared:** "The loop is capped at 6 calls and 60 s per decision."
> **v1 behaviour:** Still ≤ 6 tool calls. The routed assessment has a 180 s per-decision budget: the primary
> evidence loop keeps ≤ 60 s, and the two independent reviewers run in parallel with their own shares.
> **Reason:** Hosted high-effort reviewers take tens of seconds per step; with a shared 60 s budget the first hosted
> job ended UNAVAILABLE although the primary assessed (IDEA-066 PC-DEPLOY02). **Evidence:** IDEA-083, IDEA-066.
> **Status:** DRAFT until the Oct 26 freeze.

## Prospective pass criteria

| ID | Criterion |
|---|---|
| AB1 | Red first, pushed before the fix: a fake-clock routed job with primary 18 s, reviewer-0 needing 34 s and ABSTAINing, and reviewer-1 needing 10 s and ASSESSing ends **UNAVAILABLE** on the base and **ASSESSED (reviewer-1)** after the change, inside the new budget. |
| AB2 | A reviewer that never answers cannot starve the other: reviewer-0 stalls past its allowance, reviewer-1 still gets its full allowance and its result is used. |
| AB3 | Both reviewers are dispatched before either finishes (parallel), and the combined result is identical for every completion order (B4). |
| AB4 | Primary capped at its share: a primary that would run 70 s is cut at ≤ 60 s, then reviewers still run with their own allowances. |
| AB5 | Concurrency accounting: two parallel AIand POSTs near the trial UTC-day/total limit, and with the accounting quarantine set, are each refused or admitted exactly as the sequential rules require; OpenAI reservations/settlements/UNKNOWN unchanged. |
| AB6 | Config/schema/agent/routing accept the new maximum and refuse anything above it; existing 60 s requests and configs still validate; no 60,000 ms literal remains on the routed path. |
| AB7 | Round log and artifacts contain both reviewers' I/O and in-flight records (B7); existing round-log/receiver contract tests pass unchanged. |
| AB8 | Watchdog: a cycle with every stage at its limit completes in ≤ 300 s against `cycle_timeout_seconds` 600 (B8). |
| AB9 | DEV-22 present in the register, plan.md §6.5 and G-50; release-register tests updated only for the new row. |
| AB10 | Full suite in a `requirements.lock` venv: no new failures against the base; Linux/PostgreSQL/systemd parts on the mirror (preferred) or a recorded local substitute. No golden regenerated without review. |

## Deployment notes

- Needs a new release. Because `runs` allows one run per wallet (IDEA-066 PC-DEPLOY01-B1), a new build on the dev
  wallet needs another trial database (`larp_trialN`) unless reviewed version-switch support lands first. Combine
  with the Oct 20 profile swap if possible, so there is one redeploy. Procedure and scripts:
  `docs/build/ops/llm-trial-20261018/` on PR133's branch.
- Must land before the Oct 26 freeze / Oct 27–29 final activation; no changes during the scored run (F-114, F-117).
- Changing the build mid-trial splits the unsigned trial's measurements; Keith records the boundary.
- After deployment, check the first triggered review on the host: both reviewers dispatched together, stage
  latencies, combined status, settled charges and receiver `STORED`.

## Open questions for the implementer/reviewers (not decided here)

- Should a reviewer timeout override an ASSESSED primary (today the reviewer's result always replaces it)?
- Should a late provider reply after the deadline be recorded and its real cost settled instead of keeping the
  conservative maximum?
- Expected AIand cost increase: parallel review calls both reviewers on every triggered job, where today GLM runs
  only when Kimi is not ASSESSED (Keith: affordability).
