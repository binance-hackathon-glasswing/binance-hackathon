# Pre-trading checklist (2026-10-17)

This is a snapshot of what stands between today and the scored run (Oct 29 – Nov 12 UTC), split into what the team does this weekend without the strategy profile and what runs on Oct 20 once the profile exists. It was checked against `codex/system-testing-20261012` at `1ab47ae` (#129 merged), every open PR (#123–#126, #130–#132), the PRs merged on Oct 15–17 and the open issues on 2026-10-17, so nothing below repeats finished work. Times are UTC. The live backlog stays [INCOMPLETE_WORK.md](../INCOMPLETE_WORK.md); per-person dates are in #126's `WHO_DOES_WHAT.md`. Tick items here as they finish, and remove the matching backlog line only when its whole item is done.

## Done

- [x] AWS hosts applied; `primary` online over SSM and smoke-checked (2026-10-16, IDEA-066 PC-AWS02).
- [x] Terms captured for all six enabled sources and EDGAR; shadow source preflight passes; stricter SEC contact check (IDEA-066 PC-TERMS01/02, #129).
- [x] Real quote-cost capture running on Keith's server since 2026-10-16 18:19 UTC, set to run until 2026-10-20 00:00 UTC (#132, IDEA-063).
- [x] Route checker built (#102); network destination table approved by Keegan for section B (#113).
- [x] Balance RPC failover: up to four providers in order (#116). Chain-balance decisions D1–D6 decided by Yao Zhu (#110) and built (#115, #116).
- [x] HALT split by reason, so mandatory sells continue under pausing HALTs (D-DN-09, #117).
- [x] Gas top-up round end to end (#103); first-gas MetaMask exception confirmed by the team (#105 closed).
- [x] Swap decoder code and the router-evidence check written (#130, open for review). S1 strategy code written (#131, open for review).

## Plan (team decision 2026-10-17)

Finish every Gate A and Gate B step that doesn't need the strategy profile this weekend, then on **Oct 20** build the profile from the finished quote capture and run everything that needs it, in order. Three things need the profile: `prepare` builds the runtime config from it, the evidence service refuses to start without that runtime config, and the planner takes its minimum trade size and slippage limits from it. Gate A `prepare` accepts only a profile built from a real measured `QuoteCostSummary.v1` (`validate_live`), so it can't be faked to start early.

**Risk:** every service runs for the first time on Oct 20, and the 24 h ingestion run means Gate A can't pass before Oct 21, the day the signed rehearsal is meant to start. The side note below lowers that risk.

## This weekend (Oct 17–19): no profile needed

### Gate A setup

- [ ] Merge #132 (capture record) and #124 (CI record, closes #91). Both are docs only.
- [ ] Isaac: choose the balance RPC provider(s) with `finalized` support, each with a source ID. Since #116 up to four can be listed in failover order (`driver.balance_rpc_providers`). Open network access to them (#92, GAP-71).
- [ ] Isaac: approve the network destination table for section C. Keegan already approved it for section B (#113); the table is in `architecture-deployment.md` "Approved network destinations" (#32).
- [ ] Keegan, with whoever pays for GitHub: a host bundle built from the commit with the terms register (`1ab47ae` or later). Org Actions is billing-blocked (#98); a mirror run is engineering evidence only (#127).
- [ ] Yao Zhu: confirm the alarm email subscriptions (AWS SNS), then send a test alarm and confirm it reaches a person. No alarm email has arrived yet.
- [ ] Yao Zhu + Keegan: provision `primary` with the bundle; migrations 012/013 and roles; per-role IAM/TLS checks (AWS_RUNBOOK steps 5–6).
- [ ] Yao Zhu: copy the six retained terms files from the 2026-10-17 capture to `/var/lib/larp-evidence/artifacts/<prefix>/<hash>` on `primary`, then rerun source preflight there. DOJ and EC pages change on every fetch, so only that capture's files match the register.
- [ ] Keegan + Isaac: on `primary`, run the route check (`python -m larp.runtime.routes --role primary`) and record `chronyc tracking`; keep both reports.

### Gate B setup

- [ ] Isaac, reviewed with Keegan: fill in `RouterEvidence.v1` from the router's verified source on BscScan, following `docs/build/GATE_B.md` in #130; merge #130; run `python -m larp.execution_live.router check` on the quote files Keith's capture has already recorded. No separate route capture is needed (#33, GAP-29).
- [ ] Isaac + Keegan + Keith: decide how long a signing request stays valid (#27). #130 found this blocks every real swap even with the decoder: intents live 15 s but a quote's encoded deadline is about 30 s.
- [ ] Isaac + Keith: per-token signer caps, fee cap and allowed spenders (#44). Keegan installs `/etc/larp/signer.json`.
- [ ] Keegan + Isaac: decide how the signer host is reached; place the key file there (DR-03).
- [ ] Isaac: record the 2 USDT dev-wallet trial swap in DEPLOYMENT_DAY.md §5 and swap about 2 USDT more (#106).
- [ ] Isaac + Keith: BNB floor and top-up size, and BNB tracking on a real provider (#30).

### Decisions due Oct 19

- [ ] Yao Zhu + Keegan: rehearsal shape (D-DN-02), including what happens if Gate A only passes on Oct 21. If Gate B slips past Oct 20, record the shortfall as a deviation (GAP-04).
- [ ] Yao Zhu + team: when the first signed trade happens. The rehearsal profile's buy window is fixed in code at Oct 21 00:00 – Oct 22 00:00 UTC (`WINDOWS` in `larp/strategy/profiles.py`), so a round on Oct 20 plans no buys. Either do the Gate B trade on Oct 21 inside that window, or add a dev window before Oct 20 (code change, recorded as a version event).
- [ ] Keith + Yao Zhu: which profile to build on Oct 20: `EQUAL_WEIGHT` (in the code today) or S1 `TREND_GUARDED_VOL` (needs #131 merged; its values stay proposals until Oct 22).
- [ ] Yao Zhu + Keith: exits during a price-jump hold (IDEA-055 POLICY-HOLD). HALT for mandatory sells is already decided and built (#117).
- [ ] Keith + Yao Zhu: confirm the model shadow trial's proposed bars before the trial starts (#97, IDEA-057).
- [ ] Keith: keep or move the Nov 11 15:00 UTC flatten (#107).
- [ ] Keith: run EXP-007 on token session bars (S1 plan B1) and settle open choice O2, so its pass criteria are final (#123).

## Side note: interim profile for an early dry run (Keith, optional)

Keith is trying this. If it works, the services can start over the weekend, so first-run problems (configs, receiver ACKs, ingestion) show up before Oct 20. It is thrown away on Oct 20 and replaced by the final profile from step 2 below. Gate A is unsigned, so the interim values only change shadow HOLD/BUY decisions.

- [ ] On the capture server, summarise the files so far into a **new** directory, without stopping the capture: `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <interim>/summary.json --min-days 2`. The capture covers Fri Oct 16 (about 10 US-session rounds) and the weekend. If a token has fewer than 10 US-session samples the tool names it; rerun with `--min-samples` at the lowest count it reports, never below 5.
- [ ] Build the profiles: `python -m larp.strategy.profiles --summary <interim>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <interim>/profiles`. `rehearsal-live.json` is the one for Gate A `prepare`.
- [ ] Isaac + Keith: a quick look at spread, impact, gas and minimum trade size; record in IDEA-063 that it is interim, with the coverage parameters, capture hash and profile hash.
- [ ] If the weekend Gate A setup is done, run Oct 20 steps 3–7 early with this profile. On Oct 20, swapping in the final profile means rerunning `prepare`, rebinding the manifest and a fresh `service init`/`activate`, because the profile hash is pinned in the runtime config.

## Oct 20: profile day, in this order

The capture ends at Oct 20 00:00 UTC (08:00 SGT).

1. [ ] Keith: full summary with the default coverage (3 UTC days including a weekend, 10 samples per token per regime): `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <dir>/summary.json`. Isaac: confirm quoted amounts net route fees (#119).
2. [ ] Keith: build the profiles: `python -m larp.strategy.profiles --summary <dir>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <dir>/profiles`. Isaac + Keith: owners' review of the summary and `rehearsal-live.json` (#120); record both hashes in IDEA-063.
3. [ ] Fresh read-only wallet capture with the balance RPC (`prepare_shadow.py capture`), within five minutes of step 4.
4. [ ] Gate A `prepare` with `rehearsal-live.json`; install the configs (`runtime.json` mode 0644); bind them to CI's manifest (`preflight --bind`).
5. [ ] `service init`, then the reviewed `service activate`; start the evidence, runtime and uploader services; enable the archive timer.
6. [ ] First shadow round ACKed by the real ai-seeds receiver (R-01). This starts the 24 h ingestion clock.
7. [ ] Restart drill and first hourly anchor.
8. [ ] Gate B proof, only if a dev window was added (see the Oct 19 decision): one approve plus one swap on the dev wallet from committed code with a logged round, and crash tests at each step (DR-02..05). Then the Gate B review.

## Oct 21

- [ ] After 24 h of ingestion with a clean gap report: Keegan reviews Gate A item by item in IDEA-042.
- [ ] If not done on Oct 20: the Gate B proof inside the rehearsal buy window (Oct 21 00:00 – Oct 22 00:00 UTC), then the Gate B review.
- [ ] Signed rehearsal starts (5+ days including the Oct 24–25 weekend); any late start is recorded as a deviation (GAP-04). Keegan keeps the daily rehearsal log (DR-21).
- [ ] Yao Zhu: model trial host steps: AIand secret, budget `init` with the actual prior OpenAI spend, provider check P0, then start the shadow trial (#97, IDEA-057).
- [ ] Keith: blind independent labels for the trial sample (M9, IDEA-057).

## Oct 21–26: rehearsal drills (Keegan, with Isaac)

- [ ] Automatic HALT drill, hourly anchoring criteria 1–6, restore into an empty database, and replay of a shadow day (DR-13, DR-15, DR-16, DR-19).
- [ ] Rehearse the final-wallet switch with a throwaway config (DR-17).

## Oct 22 cut line

- [ ] Review and merge the S1 plan (#123) and its code (#131). #123 must be renumbered first: IDEA-058 is already the Gate A entry. Freeze the weights from token session bars up to the Oct 21 close; confirm every S1 value (§12) and open choices O1–O6.
- [ ] Model decision: AIand routing, the current provider, or deterministic (DR-11, #97). The shadow trial starts only once Gate A is running.
- [ ] Yao Zhu: set the 11 live evidence settings in `intelligence.v1.json`, each with a reason.
- [ ] Keith: #39 (SKHYB red flags), #55, #56, #37, #38.
- [ ] Yao Zhu + Keegan: operations decisions D-DN-01/04/06/07/08/11; review and merge #125 (automatic CLOCK HALT clear, D-DN-10).

## Oct 24: S1 build (plan §15 in #123)

- [ ] Yao Zhu: LLM exposure limiter (B4). Its input isn't wired yet, so the limiter stays NORMAL until this lands (#131).
- [ ] Keith: trend-guard input from token session bars (DR-08). Until it's wired, the trend guard stays UP (#131).
- [ ] Keegan: session-close job and round-log fields (B5); deviations-register rows for exceeding the proposal's 80% / 20% / four-name limits (B7, by Oct 26).
- [ ] Isaac: per-leg attempt limit and execution-window checks (B6).
- [ ] All: the T4 dev-wallet run (B8, Oct 24–26).

## Oct 26–29

- [ ] Every deviations-register row FINAL, including DEV-18 (standby); activation pack; each owner signs off their DR items in IDEA-042; Gate C review (DR-18, DR-22, GAP-62).
- [ ] Final wallet's new `AI_SEEDS_SECRET` by Oct 26; rehearse the wallet switch (GAP-52, DR-17).
- [ ] Isaac: first-gas swap on the final wallet (about 6 USDT) before Oct 29 00:00 UTC (#106).
- [ ] Send the organiser questions Q-39 (scoring, BNB in equity), Q-04, Q-06, Q-08, Q-14, Q-33 and Q-35 (GAP-42).

## Housekeeping

- [ ] #128 did not close automatically, because #129 merged into the integration branch, not `main`. Close it by hand or at promotion.
- [ ] #123 and #126 target `main`, not the integration branch. Retarget them before merging.
- [ ] Close #90: D1–D6 are recorded (#110) and built (#115, #116). #36 then waits only on #92.
- [ ] #130 and #131 both add a `docs/LEDGER.md` row; whichever merges second keeps both rows.
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
