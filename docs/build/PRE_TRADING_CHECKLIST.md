# Pre-trading checklist (2026-10-17)

This is a snapshot of what stands between today and the scored run (Oct 29 – Nov 12 UTC), split into what the team does this weekend without the strategy profile and what runs on Oct 20 once the profile exists. It was checked against `codex/system-testing-20261012` at `1ab47ae` (#129 merged), every open PR (#123–#126, #130–#132), the PRs merged on Oct 15–17 and the open issues on 2026-10-17, so nothing below repeats finished work. Times are UTC (SGT = UTC+8). The live backlog stays [INCOMPLETE_WORK.md](../INCOMPLETE_WORK.md). Tick items here as they finish, and remove the matching backlog line only when its whole item is done.

**Every line has exactly one owner.** Work that needs more than one person is split into small pieces, usually one person proposes or does it and another reviews or decides. A piece that depends on another names it ("after …").

**Who does what (2026-10-17):** Yao Zhu owns the AWS account and the hosts, so every step that touches AWS, the hosts or their Terraform is Yao Zhu's, and nothing else is: no other team member has AWS access (IDEA-066 PC-AWS01). Decisions, reviews, merges, code and write-ups sit with Isaac, Keith and Keegan.

## Done

- [x] AWS hosts applied; `primary` online over SSM and smoke-checked (2026-10-16, IDEA-066 PC-AWS02).
- [x] Terms captured for all six enabled sources and EDGAR; shadow source preflight passes; stricter SEC contact check (IDEA-066 PC-TERMS01/02, #129).
- [x] Real quote-cost capture running on Keith's server since 2026-10-16 18:19 UTC, set to run until 2026-10-20 00:00 UTC (#132, IDEA-063).
- [x] Route checker built (#102); network destination table approved by Keegan for section B (#113).
- [x] Balance RPC failover: up to four providers in order (#116). Chain-balance decisions D1–D6 decided by Yao Zhu (#110) and built (#115, #116).
- [x] HALT split by reason, so mandatory sells continue under pausing HALTs (D-DN-09, #117).
- [x] Gas top-up round end to end (#103); first-gas MetaMask exception confirmed by the team (#105 closed).
- [x] Every CloudWatch alarm email now says what fired and what to do (#141, IDEA-066 PC-AWS04).
- [x] Swap decoder code and the router-evidence check written (#130, open for review). S1 strategy code written (#131, open for review).

## Plan (team decision 2026-10-17)

Finish every Gate A and Gate B step that doesn't need the strategy profile this weekend, then on **Oct 20** build the profile from the finished quote capture and run everything that needs it, in order. Three things need the profile: `prepare` builds the runtime config from it, the evidence service refuses to start without that runtime config, and the planner takes its minimum trade size and slippage limits from it. Gate A `prepare` accepts only a profile built from a real measured `QuoteCostSummary.v1` (`validate_live`), so it can't be faked to start early.

**Risk:** every service runs for the first time on Oct 20, and the 24 h ingestion run means Gate A can't pass before Oct 21, the day the signed rehearsal is meant to start. The side note below lowers that risk.

## This weekend (Oct 17–19): no profile needed

### Gate A setup

- [x] **Keegan:** merge #132 (capture record) and #124 (CI record, closes #91). Both are docs only. Done: both merged 2026-10-17.
- [x] **Isaac:** choose the balance RPC provider(s) with `finalized` support and a source ID for each. Since #116 up to four can be listed in failover order (`driver.balance_rpc_providers`). Send the URLs and IDs to Yao Zhu privately, not in an issue (#92, GAP-71). Done 2026-10-17: BNB Chain public primary, NodeReal public backup, for development balance reads (#135, IDEA-055 RPC-Q01 D1).
- [x] **Isaac:** approve the network destination table for section C; Keegan already approved section B (#113). The table is in `architecture-deployment.md` "Approved network destinations" (#32). Done 2026-10-17 (#137, IDEA-062 NC-01).
- [ ] **Keegan:** ask the GitHub org owner to restore Actions minutes (#98).
- [ ] **Keegan:** after that, build the host bundle from the commit with the terms register (`1ab47ae` or later); record the run ID and the bundle and manifest hashes, and send them to Yao Zhu (#49). A mirror run is engineering evidence only (#127).
- [x] **Yao Zhu:** confirm the alarm email subscriptions (AWS SNS), send a test alarm and confirm it arrives. Done 2026-10-17: the topic had no subscription; a one-resource Terraform apply added it, Yao Zhu confirmed it, and a test ALARM on `larp-dev-database-storage` reached Yao Zhu by email (IDEA-066 PC-AWS03).
- [x] **Yao Zhu:** after Isaac's RPC choice, open network access from `primary` to those RPC hosts (Terraform, reviewed plan). Done 2026-10-17: no change needed, since `primary` already allows outbound HTTPS; both provider hosts answered from `primary` (IDEA-066 PC-AWS05). The private URLs still come from Isaac for the Oct 20 `prepare`.
- [ ] **Yao Zhu:** after the bundle exists, upload it and provision `primary` over SSM (`provision.sh primary <bundle> --expect-sha256 <CI hash>`; AWS_RUNBOOK step 5).
- [ ] **Yao Zhu:** after provisioning, run migrations 012/013 and `roles.sql` through an SSM port-forward, then check IAM token login and TLS for each database role (AWS_RUNBOOK step 6, PR99-RV1, IDEA-044 V10/V11).
- [ ] **Yao Zhu:** copy the six retained terms files from the 2026-10-17 capture to `/var/lib/larp-evidence/artifacts/<prefix>/<hash>` on `primary`, then rerun source preflight there. DOJ and EC pages change on every fetch, so only that capture's files match the register.
- [ ] **Yao Zhu:** on `primary`, run the route check (`python -m larp.runtime.routes --role primary`) and record `chronyc tracking`; send both reports to Keegan (R-07, R-08).

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
- [x] **Keegan:** choose how the signer host is reached for key placement (options in AWS_RUNBOOK step 5) and record the choice in a short IDEA entry. Done 2026-10-17: option (b), temporary SSM interface endpoints in the signer subnet, criteria SA1–SA7 (IDEA-080, #140).
- [ ] **Yao Zhu:** after #44's approval, build the IDEA-080 Terraform change (temporary SSM endpoints, off by default, with SA1–SA3 tests; Keegan reviews the plan), apply it, provision the signer, install the decided `/etc/larp/signer.json`, run the signer route check (SA4) and give Isaac a session for the key. After the key is placed, tear the endpoints down and record SA5.
- [ ] **Isaac:** after that, place the key file on the signer host only (`/etc/larp/signer/wallet.key`, root, `0600`) (DR-03).
- [ ] **Isaac:** record the 2 USDT dev-wallet trial swap in DEPLOYMENT_DAY.md §5 and swap about 2 USDT more in MetaMask (#106).
- [ ] **Keith:** propose the BNB floor and top-up size (G-28) from the measured gas (#30).
- [ ] **Isaac:** show BNB tracking (`native_trace`) works on a real provider, and accept or change Keith's floor and top-up size (#30).

### Decisions due Oct 19

- [x] **Keegan:** decide and record the rehearsal shape (D-DN-02), including what happens if Gate A only passes on Oct 21. If Gate B slips past Oct 20, record the shortfall as a deviation (GAP-04). Done 2026-10-17 (IDEA-049-D D-DN-02, #140).
- [ ] **Keith:** write up the two options for the first signed trade. The rehearsal profile's buy window is fixed in code at Oct 21 00:00 – Oct 22 00:00 UTC (`WINDOWS` in `larp/strategy/profiles.py`), so a round on Oct 20 plans no buys. Option 1: trade on Oct 21 inside that window. Option 2: add a dev window before Oct 20 (code change, recorded as a version event).
- [ ] **Isaac:** pick one of Keith's two options and tell Yao Zhu.
- [ ] **Keith:** decide which profile to build on Oct 20: `EQUAL_WEIGHT` (in the code today) or S1 `TREND_GUARDED_VOL` (needs #131 merged; its values stay proposals until Oct 22).
- [ ] **Keith:** propose what mandatory exits do during a price-jump hold (IDEA-055 POLICY-HOLD). HALT for mandatory sells is already built (#117).
- [ ] **Isaac:** decide POLICY-HOLD from Keith's proposal.
- [ ] **Keith:** review the model shadow trial's proposed bars and comment on #97 (IDEA-057).
- [ ] **Keegan:** confirm the trial bars after Keith's review.
- [ ] **Keith:** keep or move the Nov 11 15:00 UTC flatten, and record it in IDEA-035 C4 (#107).
- [ ] **Keith:** run EXP-007 on token session bars (S1 plan B1, #123) and record the result.
- [ ] **Keegan:** after EXP-007, settle open choice O2 (what ships if EXP-007 is inconclusive), so its pass criteria are final.

## Side note: interim profile for an early dry run (optional)

Keith is trying this. If it works, the services can start over the weekend, so first-run problems (configs, receiver ACKs, ingestion) show up before Oct 20. It is thrown away on Oct 20 and replaced by the final profile. Gate A is unsigned, so the interim values only change shadow HOLD/BUY decisions.

- [ ] **Keith:** on the capture server, summarise the files so far into a **new** directory, without stopping the capture: `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <interim>/summary.json --min-days 2`. If a token has fewer than 10 US-session samples the tool names it; rerun with `--min-samples` at the lowest count it reports, never below 5.
- [ ] **Keith:** build the profiles: `python -m larp.strategy.profiles --summary <interim>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <interim>/profiles`, and send `rehearsal-live.json` to Yao Zhu.
- [ ] **Isaac:** a quick look at spread, impact, gas and minimum trade size in Keith's interim summary and profile.
- [ ] **Keith:** record in IDEA-063 that it is interim, with the coverage parameters, capture hash and profile hash.
- [ ] **Yao Zhu:** if the weekend Gate A setup is done, run the Oct 20 steps 5–8 early with this profile. On Oct 20 the final profile means rerunning `prepare`, rebinding the manifest and a fresh `service init`/`activate`, because the profile hash is pinned in the runtime config.

## Oct 20: profile day, in this order

The capture ends at Oct 20 00:00 UTC (08:00 SGT).

1. [ ] **Keith:** full summary with the default coverage (3 UTC days including a weekend, 10 samples per token per regime): `python -m larp.marketdata.cost_summary summarize --captures <capture dir> --output <dir>/summary.json`.
2. [ ] **Isaac:** confirm the quoted amounts already net out route fees, so `fee_bps = 0` holds (#119).
3. [ ] **Keith:** build the decided profile: `python -m larp.strategy.profiles --summary <dir>/summary.json --predicates config/intelligence/red_flags.v1.json --output-dir <dir>/profiles`.
4. [ ] **Isaac:** owners' review of the summary and `rehearsal-live.json` (#120); record both hashes in IDEA-063 and send the profile to Yao Zhu.
5. [ ] **Yao Zhu:** fresh read-only wallet capture with the balance RPC (`prepare_shadow.py capture --balance-rpc-config deploy/activation/balance-rpc/selected-providers.json`), then Gate A `prepare` within five minutes with the same `--balance-rpc-config`, so both RPCs go into `runtime.json` (#145); install the configs (`runtime.json` mode 0644); bind them to CI's manifest (`preflight --bind`).
6. [ ] **Yao Zhu:** `service init`, then `service activate` with Keegan named as reviewer; start the evidence, runtime and uploader services; enable the archive timer.
7. [ ] **Yao Zhu:** confirm the first shadow round is ACKed by the real ai-seeds receiver (R-01), which starts the 24 h ingestion clock, and send the round ID to Keegan.
8. [ ] **Yao Zhu:** restart drill (kill a service, check it returns on the same build with an incident logged) and check the first hourly anchor (DR-13, DR-15).
9. [ ] **Isaac:** only if a dev window was chosen: watch the runtime's first approve plus swap on the dev wallet and check it on chain against the logged round (DR-02, DR-03).
10. [ ] **Keegan:** after step 9, Gate B review in IDEA-042. The host-side crash tests (DR-04, DR-05) are step 3 of the Oct 21 list.

## Oct 21

- [ ] **Yao Zhu:** after 24 h of ingestion, produce the gap report on `primary` (`python -m larp.sources.live report --from … --to …`) and send it to Keegan.
- [ ] **Keegan:** review Gate A item by item in IDEA-042, using the gap report and Yao Zhu's host reports.
- [ ] **Yao Zhu:** crash tests at each execution step on the host (DR-04, DR-05), then switch the runtime to signed rehearsal mode.
- [ ] **Isaac:** if not done on Oct 20: check the runtime's first approve plus swap on chain inside the rehearsal buy window (Oct 21 00:00 – Oct 22 00:00 UTC).
- [ ] **Keegan:** after Isaac's check, the Gate B review in IDEA-042 (if not done on Oct 20).
- [ ] **Keegan:** keep the daily rehearsal log (5+ days including the Oct 24–25 weekend, DR-21) from the round logs and alarms. A late start is recorded as a deviation (GAP-04).
- [ ] **Yao Zhu:** model trial host steps: AIand secret, budget `init` with the actual prior OpenAI spend, provider check P0, then start the shadow trial (#97, IDEA-057).
- [ ] **Keith:** blind independent labels for the trial sample (M9, IDEA-057).

## Oct 21–26: rehearsal drills

- [ ] **Yao Zhu:** on the hosts: automatic HALT drill, hourly-anchoring criteria 1–6, a restore into an empty database, and the final-wallet switch with a throwaway config (DR-13, DR-15, DR-16, DR-17).
- [ ] **Keegan:** replay a shadow day from the exported journal and check it reproduces the head (DR-19).

## Oct 22 cut line

- [x] **Keegan:** renumber #123's ledger entry (IDEA-058 is already the Gate A entry) and retarget #123 to the integration branch. Done: #123 is now IDEA-075 and targets the integration branch.
- [ ] **Isaac:** after that, review and merge the S1 plan (#123).
- [ ] **Keith:** review and merge the S1 code (#131). If #130 merged first, keep both `docs/LEDGER.md` rows.
- [ ] **Keith:** freeze the S1 weights from token session bars up to the Oct 21 close (`python -m larp.strategy.s1 freeze-weights`).
- [ ] **Keith:** propose final values for every S1 parameter (§12) and open choices O1 and O3–O6.
- [ ] **Keegan:** confirm Keith's S1 values and choices.
- [ ] **Keith:** summarise the model trial results so far for the model decision (DR-11).
- [ ] **Keegan:** decide the model from Keith's summary: AIand routing, the current provider, or deterministic (DR-11, #97).
- [ ] **Keith:** set the 11 live evidence settings in `intelligence.v1.json`, each with a reason.
- [ ] **Keith:** SKHYB red flags: build it or record a deviation (#39).
- [ ] **Keith:** decide #55 (stale marks) and #56 (flatten on the BNB held at the cut-off).
- [ ] **Keith:** run the pre-registered after-cost comparison and staggered evaluation (#37, #38).
- [ ] **Keegan:** propose the operations decisions D-DN-01, 04, 06, 07, 08 and 11 (IDEA-049-D §5).
- [ ] **Isaac:** decide those operations items from Keegan's proposals.
- [ ] **Isaac:** review and merge #125 (automatic CLOCK HALT clear, D-DN-10).

## Oct 24: S1 build (plan §15 in #123)

- [ ] **Keegan:** LLM exposure limiter (B4). Its input isn't wired yet, so the limiter stays NORMAL until this lands (#131).
- [ ] **Keith:** trend-guard input from token session bars (DR-08). Until it's wired, the trend guard stays UP (#131).
- [ ] **Keegan:** session-close job and round-log fields (B5).
- [ ] **Isaac:** per-leg attempt limit and execution-window checks (B6).
- [ ] **Keegan:** write up the T4 dev-wallet run from the rehearsal round logs (B8, Oct 24–26).
- [ ] **Keith:** check the T4 results against what S1 should have done.

## Oct 26–29

- [ ] **Keegan:** deviations-register rows for exceeding the proposal's 80% / 20% / four-name limits (B7).
- [ ] **Keegan:** every deviations-register row FINAL, including DEV-18 (standby), and the services list (DR-18, GAP-62).
- [ ] **Keegan:** activation pack and the Gate C review (DR-22).
- [ ] **Keith:** sign off DR-08, DR-09, DR-10, DR-11 and DR-14 in IDEA-042.
- [ ] **Isaac:** sign off DR-01 to DR-06 in IDEA-042.
- [ ] **Yao Zhu:** sign off DR-12 and DR-16 (live sources, hosting) in IDEA-042.
- [ ] **Keegan:** sign off the remaining DR items (DR-07, DR-13, DR-15, DR-17 to DR-22) in IDEA-042.
- [ ] **Isaac:** get the final wallet's new `AI_SEEDS_SECRET` by Oct 26 and hand it to Yao Zhu for the host secret, never in chat or an issue (GAP-52).
- [ ] **Yao Zhu:** put the final wallet's secret into AWS Secrets Manager (`put_service_secrets.sh`).
- [ ] **Isaac:** first-gas swap on the final wallet (about 6 USDT) before Oct 29 00:00 UTC (#106).
- [ ] **Keegan:** send the organiser questions Q-39 (scoring, BNB in equity), Q-04, Q-06, Q-08, Q-14, Q-33 and Q-35 (GAP-42).

## Housekeeping

- [ ] **Keegan:** close #128 by hand; it didn't close automatically because #129 merged into the integration branch, not `main`.
- [ ] **Keegan:** close #90: D1–D6 are recorded (#110) and built (#115, #116). #36 then waits only on #92.
- [x] **Keegan:** retarget #126 to the integration branch before it merges. Done.
- [ ] Branch cleanup (2026-10-17): 61 remote branches whose commits were all in the integration branch or `main` were deleted. These seven hold commits found nowhere else and have no open PR; each owner decides whether to keep, reopen or delete them:

  | Branch | Last commit by | Earlier PR | Decides |
  |---|---|---|---|
  | `claude/gate-a-inputs` | Claude session | #89 (closed) | Keegan |
  | `claude/issue31-day-roll-tests` | Claude session | #82 (closed) | Keegan |
  | `claude/issue59-systemd-runtime-dirs` | Claude session | #83 (closed) | Keegan |
  | `claude/local-ci-20261015` | Cookiemunchrr | none | Keegan |
  | `docs/idea-052-timesfm-20261015` | Cookiemunchrr | none | Keegan |
  | `codex/pr-review-system-20261012` | wtvlol | none | wtvlol |
  | `codex/thin-path` | Keegan | #10 (closed) | Keegan |
