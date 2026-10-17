# Pre-trading checklist (2026-10-17)

This is a snapshot of what stands between today and the scored run (Oct 29 – Nov 12 UTC), split into what the team does this weekend without the strategy profile and what runs on Oct 20 once the profile exists. It was checked against `codex/system-testing-20261012` at `1ab47ae` (#129 merged), every open PR (#123–#126, #130–#132), the PRs merged on Oct 15–17 and the open issues on 2026-10-17, so nothing below repeats finished work. Times are UTC (SGT = UTC+8). The live backlog stays [INCOMPLETE_WORK.md](../INCOMPLETE_WORK.md). Tick items here as they finish, and remove the matching backlog line only when its whole item is done.

**Every line has exactly one owner.** Work that needs more than one person is split into small pieces, usually one person proposes or does it and another reviews or decides. A piece that depends on another names it ("after …").

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

- [ ] **Yao Zhu:** merge #132 (capture record) and #124 (CI record, closes #91). Both are docs only.
- [ ] **Isaac:** choose the balance RPC provider(s) with `finalized` support and a source ID for each. Since #116 up to four can be listed in failover order (`driver.balance_rpc_providers`). Send the hosts to Keegan (#92, GAP-71).
- [ ] **Keegan:** after Isaac's choice, open network access from `primary` to those RPC hosts and add them to the destination table (#92, #32).
- [ ] **Isaac:** approve the network destination table for section C; Keegan already approved section B (#113). The table is in `architecture-deployment.md` "Approved network destinations" (#32).
- [ ] **Keegan:** ask the GitHub org owner to restore Actions minutes (#98).
- [ ] **Keegan:** after that, build the host bundle from the commit with the terms register (`1ab47ae` or later); record the run ID and the bundle and manifest hashes (#49). A mirror run is engineering evidence only (#127).
- [ ] **Yao Zhu:** confirm the alarm email subscriptions (AWS SNS), send a test alarm and confirm it arrives. No alarm email has arrived yet.
- [ ] **Yao Zhu:** after the bundle exists, provision `primary` with it over SSM (`provision.sh primary <bundle> --expect-sha256 <CI hash>`; AWS_RUNBOOK step 5).
- [ ] **Keegan:** after provisioning, run migrations 012/013 and `roles.sql` through an SSM port-forward (AWS_RUNBOOK step 6, PR99-RV1).
- [ ] **Isaac:** after the migrations, check IAM token login and TLS for each database role on the real RDS instance (IDEA-044 V10/V11).
- [ ] **Yao Zhu:** copy the six retained terms files from the 2026-10-17 capture to `/var/lib/larp-evidence/artifacts/<prefix>/<hash>` on `primary`, then rerun source preflight there. DOJ and EC pages change on every fetch, so only that capture's files match the register.
- [ ] **Keegan:** on `primary`, run the route check (`python -m larp.runtime.routes --role primary`) and record `chronyc tracking`; keep both reports (R-07, R-08).

### Gate B setup

- [ ] **Isaac:** fill in `RouterEvidence.v1` from the router's verified source on BscScan, following `docs/build/GATE_B.md` in #130 (#33, GAP-29).
- [ ] **Keegan:** review Isaac's router evidence, then review and merge #130. If #131 merged first, keep both `docs/LEDGER.md` rows.
- [ ] **Keith:** give Isaac the quote files the capture has recorded so far (no credentials or `.env`), for the router check.
- [ ] **Isaac:** after #130 merges, run `python -m larp.execution_live.router check` on those files until it reports PASS. No separate route capture is needed.
- [ ] **Isaac:** write the two options for how long a signing request stays valid, with a recommendation: (a) a bounded signing lifetime, or (b) a router deadline no later than the proposal's expiry. #130 found this blocks every real swap: intents live 15 s, a quote's encoded deadline is about 30 s (#27).
- [ ] **Keith:** check what each #27 option does to the profile's quote age and proposal lifetime, and comment on #27.
- [ ] **Keegan:** decide #27 from Isaac's options and Keith's comment, record it as C-OPEN-003 in IDEA-049-C, and open the code change.
- [ ] **Isaac:** propose the per-token input caps, the fee cap and `allowed_spenders` (the router's `tx.to` from the router evidence) for `signer.json` (#44).
- [ ] **Keith:** check Isaac's caps against the profile's per-trade cap (it must allow one full position) and approve or comment on #44.
- [ ] **Keegan:** after #44 is approved, install the decided `/etc/larp/signer.json` on the signer host.
- [ ] **Keegan:** choose how the signer host is reached for provisioning (AWS_RUNBOOK step 5), make the reviewed Terraform change and record it.
- [ ] **Isaac:** after that, place the key file on the signer host only (`/etc/larp/signer/wallet.key`, root, `0600`) (DR-03).
- [ ] **Isaac:** record the 2 USDT dev-wallet trial swap in DEPLOYMENT_DAY.md §5 and swap about 2 USDT more in MetaMask (#106).
- [ ] **Keith:** propose the BNB floor and top-up size (G-28) from the measured gas (#30).
- [ ] **Isaac:** show BNB tracking (`native_trace`) works on a real provider (#30).

### Decisions due Oct 19

- [ ] **Keegan:** propose the rehearsal shape (D-DN-02), including what happens if Gate A only passes on Oct 21.
- [ ] **Yao Zhu:** decide the rehearsal shape from Keegan's proposal and record it. If Gate B slips past Oct 20, Keegan records the shortfall as a deviation (GAP-04).
- [ ] **Keith:** write up the two options for the first signed trade. The rehearsal profile's buy window is fixed in code at Oct 21 00:00 – Oct 22 00:00 UTC (`WINDOWS` in `larp/strategy/profiles.py`), so a round on Oct 20 plans no buys. Option 1: trade on Oct 21 inside that window. Option 2: add a dev window before Oct 20 (code change, recorded as a version event).
- [ ] **Yao Zhu:** pick one of Keith's two options.
- [ ] **Keith:** recommend which profile to build on Oct 20: `EQUAL_WEIGHT` (in the code today) or S1 `TREND_GUARDED_VOL` (needs #131 merged; its values stay proposals until Oct 22).
- [ ] **Yao Zhu:** decide the Oct 20 profile from Keith's recommendation.
- [ ] **Keith:** propose what mandatory exits do during a price-jump hold (IDEA-055 POLICY-HOLD). HALT for mandatory sells is already built (#117).
- [ ] **Yao Zhu:** decide POLICY-HOLD from Keith's proposal.
- [ ] **Keith:** review the model shadow trial's proposed bars and comment on #97 (IDEA-057).
- [ ] **Yao Zhu:** confirm the trial bars after Keith's review.
- [ ] **Keith:** keep or move the Nov 11 15:00 UTC flatten, and record it in IDEA-035 C4 (#107).
- [ ] **Keith:** run EXP-007 on token session bars (S1 plan B1, #123) and record the result.
- [ ] **Yao Zhu:** after EXP-007, settle open choice O2 (what ships if EXP-007 is inconclusive), so its pass criteria are final.

## Side note: interim profile for an early dry run (optional)

Keith is trying this. If it works, the services can start over the weekend, so first-run problems (configs, receiver ACKs, ingestion) show up before Oct 20. It is thrown away on Oct 20 and replaced by the final profile. Gate A is unsigned, so the interim values only change shadow HOLD/BUY decisions.

- [ ] **Keith:** on the capture server, summarise the files so far into a **new** directory, without stopping the capture: `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <interim>/summary.json --min-days 2`. If a token has fewer than 10 US-session samples the tool names it; rerun with `--min-samples` at the lowest count it reports, never below 5.
- [ ] **Keith:** build the profiles: `python -m larp.strategy.profiles --summary <interim>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <interim>/profiles`. `rehearsal-live.json` is the one for Gate A `prepare`.
- [ ] **Isaac:** a quick look at spread, impact, gas and minimum trade size in Keith's interim summary and profile.
- [ ] **Keith:** record in IDEA-063 that it is interim, with the coverage parameters, capture hash and profile hash.
- [ ] **Yao Zhu:** if the weekend Gate A setup is done, run the Oct 20 steps 5–9 early with this profile. On Oct 20 the final profile means rerunning `prepare`, rebinding the manifest and a fresh `service init`/`activate`, because the profile hash is pinned in the runtime config.

## Oct 20: profile day, in this order

The capture ends at Oct 20 00:00 UTC (08:00 SGT).

1. [ ] **Keith:** full summary with the default coverage (3 UTC days including a weekend, 10 samples per token per regime): `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <dir>/summary.json`.
2. [ ] **Isaac:** confirm the quoted amounts already net out route fees, so `fee_bps = 0` holds (#119).
3. [ ] **Keith:** build the decided profile: `python -m larp.strategy.profiles --summary <dir>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <dir>/profiles`.
4. [ ] **Isaac:** owners' review of the summary and `rehearsal-live.json` (#120); record both hashes in IDEA-063.
5. [ ] **Yao Zhu:** fresh read-only wallet capture with the balance RPC (`prepare_shadow.py capture`), within five minutes of step 6.
6. [ ] **Yao Zhu:** Gate A `prepare` with `rehearsal-live.json`; install the configs (`runtime.json` mode 0644); bind them to CI's manifest (`preflight --bind`).
7. [ ] **Keegan:** `service init`, then the reviewed `service activate`; start the evidence, runtime and uploader services; enable the archive timer.
8. [ ] **Keegan:** confirm the first shadow round is ACKed by the real ai-seeds receiver (R-01). This starts the 24 h ingestion clock.
9. [ ] **Isaac:** restart drill: kill a service and check it comes back on the same build with an incident logged (DR-13).
10. [ ] **Keegan:** check the first hourly anchor is written and verified (DR-15).
11. [ ] **Isaac:** only if a dev window was chosen: one approve plus one swap on the dev wallet from committed code, with a logged round (DR-02, DR-03).
12. [ ] **Keegan:** after step 11, crash tests at each execution step (DR-04, DR-05) and the Gate B review in IDEA-042.

## Oct 21

- [ ] **Yao Zhu:** after 24 h of ingestion, produce the gap report (`python -m larp.sources.live report --from … --to …`).
- [ ] **Keegan:** review Gate A item by item in IDEA-042, using the gap report.
- [ ] **Isaac:** if not done on Oct 20: one approve plus one swap on the dev wallet inside the rehearsal buy window (Oct 21 00:00 – Oct 22 00:00 UTC).
- [ ] **Keegan:** after Isaac's trade, crash tests at each execution step and the Gate B review in IDEA-042.
- [ ] **Keegan:** start the signed rehearsal (5+ days including the Oct 24–25 weekend) and keep the daily rehearsal log (DR-21). A late start is recorded as a deviation (GAP-04).
- [ ] **Yao Zhu:** model trial host steps: AIand secret, budget `init` with the actual prior OpenAI spend, provider check P0, then start the shadow trial (#97, IDEA-057).
- [ ] **Keith:** blind independent labels for the trial sample (M9, IDEA-057).

## Oct 21–26: rehearsal drills

- [ ] **Keegan:** automatic HALT drill and hourly-anchoring criteria 1–6 (DR-13, DR-15).
- [ ] **Isaac:** restore the database into an empty instance and check it (DR-16).
- [ ] **Yao Zhu:** replay a shadow day and check it reproduces the journal head (DR-19).
- [ ] **Keegan:** rehearse the final-wallet switch with a throwaway config (DR-17).

## Oct 22 cut line

- [ ] **Keegan:** renumber #123's ledger entry (IDEA-058 is already the Gate A entry) and retarget #123 to the integration branch.
- [ ] **Yao Zhu:** after that, review and merge the S1 plan (#123).
- [ ] **Keith:** review and merge the S1 code (#131). If #130 merged first, keep both `docs/LEDGER.md` rows.
- [ ] **Keith:** freeze the S1 weights from token session bars up to the Oct 21 close (`python -m larp.strategy.s1 freeze-weights`).
- [ ] **Keith:** propose final values for every S1 parameter (§12) and open choices O1 and O3–O6.
- [ ] **Yao Zhu:** confirm Keith's S1 values and choices.
- [ ] **Keith:** summarise the model trial results so far for the model decision (DR-11).
- [ ] **Yao Zhu:** decide the model: AIand routing, the current provider, or deterministic (DR-11, #97).
- [ ] **Yao Zhu:** set the 11 live evidence settings in `intelligence.v1.json`, each with a reason.
- [ ] **Keith:** SKHYB red flags: build it or record a deviation (#39).
- [ ] **Keith:** decide #55 (stale marks) and #56 (flatten on the BNB held at the cut-off).
- [ ] **Keith:** run the pre-registered after-cost comparison and staggered evaluation (#37, #38).
- [ ] **Keegan:** propose the operations decisions D-DN-01, 04, 06, 07, 08 and 11 (IDEA-049-D §5).
- [ ] **Yao Zhu:** decide those operations items from Keegan's proposals.
- [ ] **Isaac:** review and merge #125 (automatic CLOCK HALT clear, D-DN-10).

## Oct 24: S1 build (plan §15 in #123)

- [ ] **Yao Zhu:** LLM exposure limiter (B4). Its input isn't wired yet, so the limiter stays NORMAL until this lands (#131).
- [ ] **Keith:** trend-guard input from token session bars (DR-08). Until it's wired, the trend guard stays UP (#131).
- [ ] **Keegan:** session-close job and round-log fields (B5).
- [ ] **Isaac:** per-leg attempt limit and execution-window checks (B6).
- [ ] **Keegan:** run the T4 dev-wallet test (B8, Oct 24–26).
- [ ] **Keith:** check the T4 results against what S1 should have done.

## Oct 26–29

- [ ] **Keegan:** deviations-register rows for exceeding the proposal's 80% / 20% / four-name limits (B7).
- [ ] **Keegan:** every deviations-register row FINAL, including DEV-18 (standby), and the services list (DR-18, GAP-62).
- [ ] **Keegan:** activation pack and the Gate C review (DR-22).
- [ ] **Keith:** sign off DR-08, DR-09, DR-10 and DR-14 in IDEA-042.
- [ ] **Isaac:** sign off DR-01 to DR-06 in IDEA-042.
- [ ] **Yao Zhu:** sign off DR-11 and DR-12 in IDEA-042.
- [ ] **Keegan:** sign off the remaining DR items (DR-07, DR-13, DR-15 to DR-22) in IDEA-042.
- [ ] **Yao Zhu:** get the final wallet's new `AI_SEEDS_SECRET` by Oct 26 (GAP-52).
- [ ] **Isaac:** first-gas swap on the final wallet (about 6 USDT) before Oct 29 00:00 UTC (#106).
- [ ] **Yao Zhu:** send the organiser questions Q-39 (scoring, BNB in equity), Q-04, Q-06, Q-08, Q-14, Q-33 and Q-35 (GAP-42).

## Housekeeping

- [ ] **Yao Zhu:** close #128 by hand; it didn't close automatically because #129 merged into the integration branch, not `main`.
- [ ] **Yao Zhu:** close #90: D1–D6 are recorded (#110) and built (#115, #116). #36 then waits only on #92.
- [ ] **Keegan:** retarget #126 to the integration branch before it merges.
- [ ] Branch cleanup (2026-10-17): 61 remote branches whose commits were all in the integration branch or `main` were deleted. These seven hold commits found nowhere else and have no open PR; each owner decides whether to keep, reopen or delete them:

  | Branch | Last commit by | Earlier PR | Decides |
  |---|---|---|---|
  | `claude/gate-a-inputs` | Claude session | #89 (closed) | Yao Zhu |
  | `claude/issue31-day-roll-tests` | Claude session | #82 (closed) | Yao Zhu |
  | `claude/issue59-systemd-runtime-dirs` | Claude session | #83 (closed) | Yao Zhu |
  | `claude/local-ci-20261015` | Cookiemunchrr | none | Yao Zhu |
  | `docs/idea-052-timesfm-20261015` | Cookiemunchrr | none | Yao Zhu |
  | `codex/pr-review-system-20261012` | wtvlol | none | wtvlol |
  | `codex/thin-path` | Keegan | #10 (closed) | Keegan |
