# Pre-trading checklist (2026-10-17)

This is a snapshot of what stands between today and the scored run (Oct 29 – Nov 12 UTC), by gate and date. It was checked against `codex/system-testing-20261012` at `1ab47ae` (#129 merged), the open PRs and the open issues on 2026-10-17. Times are UTC. The live backlog stays [INCOMPLETE_WORK.md](../INCOMPLETE_WORK.md); per-person dates are in #126's `WHO_DOES_WHAT.md`. Tick items here as they finish, and remove the matching backlog line only when its whole item is done.

## Done

- [x] AWS hosts applied; `primary` online over SSM and smoke-checked (2026-10-16, IDEA-066 PC-AWS02).
- [x] Terms captured for all six enabled sources and EDGAR; shadow source preflight passes; stricter SEC contact check (IDEA-066 PC-TERMS01/02, #129).
- [x] Real quote-cost capture running on Keith's server since 2026-10-16 18:19 UTC, set to run until 2026-10-20 00:00 UTC (#132, IDEA-063).

## Interim profile so Gate A doesn't wait: Keith + Isaac (team decision 2026-10-17)

The profile design and its formulas already exist (`config/strategy/LIVE.md`, `build_live_profiles`). Only the cost numbers it is computed from are still being measured. Gate A `prepare` refuses a profile without a real measured `QuoteCostSummary.v1` (`validate_live`), so it can't use a made-up one. Instead, summarise the capture as it stands and build an interim profile. Gate A is unsigned, so these values decide only shadow HOLD/BUY decisions.

- [ ] Keith, on the capture server: summarise the files so far into a new directory, without stopping the capture: `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <interim>/summary.json --min-days 2`. As of 2026-10-17 04:00 UTC the capture covers Fri Oct 16 (about 10 US-session rounds) and Sat Oct 17 (weekend). If a token has fewer than 10 US-session samples, the tool names it. Then use `--min-samples` at the lowest count it reports, never below 5.
- [ ] Keith: build the profiles from it: `python -m larp.strategy.profiles --summary <interim>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <interim>/profiles`. Use `rehearsal-live.json` for Gate A `prepare`.
- [ ] Isaac + Keith: a quick look at the interim summary and profile (spread, impact, gas, minimum trade size). Record in IDEA-063 that it is interim: coverage parameters, capture hash, profile hash.

## After the capture ends (Oct 20 00:00 UTC): Isaac + Keith (GAP-69)

- [ ] Full summary with the default coverage (3 UTC days including a weekend, 10 samples per token per regime); confirm quoted amounts net route fees (#119).
- [ ] Owners' review and the final LIVE rehearsal profile (#120). The profile hash is pinned in the runtime config, so swapping it means rerunning `prepare`, rebinding the manifest and a fresh `service init`/`activate`. Do it before Gate B's first signed trade.

## Gate A: can start now

- [ ] Merge #132 (capture record) and #124 (CI record, closes #91). Both are docs only.
- [ ] Isaac: choose the BSC balance RPC with `finalized` support, give its source ID, open network access to it (#92, GAP-71).
- [ ] Isaac + Keegan: approve the network destination list (#32).
- [ ] Keegan, with whoever pays for GitHub: a host bundle built from the commit with the terms register (`1ab47ae` or later). Org Actions is billing-blocked (#98); a mirror run is engineering evidence only (#127).
- [ ] Yao Zhu: confirm the alarm email subscriptions (AWS SNS). No alarm email has arrived yet.
- [ ] Yao Zhu + Keegan: provision `primary` with the bundle; migrations 012/013 and roles; per-role IAM/TLS checks (AWS_RUNBOOK steps 5–6).
- [ ] Yao Zhu: copy the six retained terms files from the 2026-10-17 capture to `/var/lib/larp-evidence/artifacts/<prefix>/<hash>` on `primary`, then rerun source preflight there. DOJ and EC pages change on every fetch, so only that capture's files match the register.
- [ ] Fresh wallet capture with the balance RPC, after Isaac's dev-wallet first-gas swap so the balances include the BNB.
- [ ] Gate A `prepare` with the interim rehearsal profile; install configs; bind the manifest; `service init` and reviewed `activate`; start the evidence, runtime and uploader services.
- [ ] Host evidence: real receiver ACK, 24 h ingestion, restart drill, hourly anchor, route checks, time sync, an alarm reaching a person. Keegan then reviews Gate A in IDEA-042.

## Gate B: target Oct 20

- [ ] Isaac: review and merge #130 (swap decoder); capture unsigned route bytes for all five tokens and USDT → BNB; `router check` PASS (#33, GAP-29).
- [ ] Isaac + Keegan + Keith: decide how long a signing request stays valid (#27; #130 records a new finding on it).
- [ ] Isaac + Keith: per-token signer caps, fee cap and allowed spenders (#44). Keegan installs `/etc/larp/signer.json`.
- [ ] Keegan + Isaac: decide how the signer host is reached; place the key file there (DR-03).
- [ ] Isaac: record the 2 USDT dev-wallet trial swap in DEPLOYMENT_DAY.md §5 and swap about 2 USDT more (#106).
- [ ] Isaac + Keith: BNB floor and top-up size, BNB tracking on a real provider (#30); balance-reconciliation decisions D1–D6 (#90, #36).
- [ ] Isaac + Keegan: one approve plus one swap on the dev wallet from committed code, and crash tests at each step (DR-02..05); then the Gate B review.

## Decisions due Oct 19

- [ ] Yao Zhu + Keegan: rehearsal shape (D-DN-02). If Gate B slips past Oct 20, record the shortfall as a deviation (GAP-04).
- [ ] Yao Zhu + Keith: HALT behaviour for mandatory sells and exits during a price-jump hold (IDEA-055 POLICY-HOLD).
- [ ] Keith: keep or move the Nov 11 15:00 UTC flatten (#107).
- [ ] Settle open choice O2 so EXP-007's pass criteria are final (#123).

## Oct 22 cut line

- [ ] Review and merge the S1 plan (#123) and its code (#131); freeze the weights; confirm every S1 value.
- [ ] Model decision: AIand routing, the current provider, or deterministic (DR-11, #97). The shadow trial starts only once Gate A is running.
- [ ] Yao Zhu: set the 11 live evidence settings in `intelligence.v1.json`, each with a reason.
- [ ] Keith: #39 (SKHYB red flags), #55, #56, #37, #38.
- [ ] Yao Zhu + Keegan: operations decisions D-DN-01/04/06/07/08/11; review and merge #125 (automatic CLOCK HALT clear, D-DN-10).

## Oct 26–29

- [ ] Every deviations-register row FINAL, including DEV-18 (standby); activation pack; Gate C review (DR-18, DR-22, GAP-62).
- [ ] Final wallet's new `AI_SEEDS_SECRET` by Oct 26; rehearse the wallet switch (GAP-52, DR-17).
- [ ] Isaac: first-gas swap on the final wallet (about 6 USDT) before Oct 29 00:00 UTC (#106).
- [ ] Send the organiser questions Q-39 (scoring, BNB in equity), Q-04, Q-06, Q-08, Q-14, Q-33 and Q-35 (GAP-42).

## Housekeeping

- [ ] #128 did not close automatically, because #129 merged into the integration branch, not `main`. Close it by hand or at promotion.
- [ ] #123 and #126 target `main`, not the integration branch. Retarget them before merging.
- [ ] Branch cleanup (2026-10-17): 61 remote branches whose commits were all in the integration branch or `main` were deleted. These seven hold commits found nowhere else and have no open PR; their owners decide whether to keep, reopen or delete them:

  | Branch | Last commit by | Earlier PR |
  |---|---|---|
  | `claude/gate-a-inputs` | Claude session | #89 (closed) |
  | `claude/issue31-day-roll-tests` | Claude session | #82 (closed) |
  | `claude/issue59-systemd-runtime-dirs` | Claude session | #83 (closed) |
  | `claude/local-ci-20261015` | Cookiemunchrr | none |
  | `docs/idea-052-timesfm-20261015` | Cookiemunchrr | none |
  | `codex/pr-review-system-20261012` | wtvlol | none |
  | `codex/thin-path` | Keegan | #10 (closed) |
