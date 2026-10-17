You are the agent for **Gate A: the hosted shadow run**. You prepare the work behind the checklist's "Gate A setup", "Side note: interim profile", "Oct 20: profile day" and Oct 21 Gate A lines in [`docs/build/PRE_TRADING_CHECKLIST.md`](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/133). You work for the owner each of those lines names, and each review goes to the reviewer its line names; take both from the checklist, not from this brief. Your job is to get LARP running on the AWS dev hosts in shadow mode. That means real read-only market data, real evidence, real decisions and real ai-seeds round logs from a manifested build, with every order ending `NOT_SUBMITTED` and nothing signed. You also need to collect the evidence for the Gate A review item by item in IDEA-042. Gate A is the critical path: Gate B and the signed rehearsal (Oct 21) both need a running host, and the Oct17 interim-profile shadow run is already reported live; Oct20 replaces its profile/configs (checklist status wins).

Read `docs/build/remaining-work/README.md` first; its rules apply here, especially rule 2 (owners come from the checklist; AWS/host operations go to the checklist's AWS owner, with its explicit Isaac key-placement exception). Then read these, on `origin/codex/system-testing-20261012`:
- `docs/build/GATE_A.md`, `docs/build/DEPLOYMENT_DAY.md`, `docs/build/AWS_RUNBOOK.md`, `docs/build/runbook.md`
- IDEA-051, IDEA-058 (all, including "Remaining work and ownership" and design option 6), IDEA-063 (including the real capture run), IDEA-066, IDEA-062 and IDEA-046/047
- GAP-69..72 and "IDEA-049-D PR99-RV1" in `docs/INCOMPLETE_WORK.md`
- issues #92, #97, #118, #119, #120 and #127

Put new records in IDEA-065..069 (IDEA-066 is already used, by #129); extend IDEA-058/063/066 where the work already lives there.

## Deliver, in this order

1. **Quote-cost capture (#118, GAP-69). Running; don't touch it.** The real capture has run on Keith's server since 2026-10-16 18:19 UTC and is set to stop at 2026-10-20 00:00 UTC (#132, IDEA-063). That gives the 3 UTC days including a weekend that IDEA-063's summary needs.
   - Don't restart, stop or move it, and don't start a second capture.
   - It only calls read-only endpoints (quote, approve-build and gas-estimate), never `quote-and-swap` broadcast, signing or an ai-seeds upload. It uses the Binance Web3 API key, never the wallet key or `AI_SEEDS_SECRET`.
   - Raw artifacts stay outside Git; record their hashes in IDEA-063 when the capture's owner sends them.

2. **Interim and final summary and profile (#119, #120).**
   - **Optional interim profile** (checklist "Side note"): prepare the exact `cost_summary summarize --min-days 2` and `profiles` commands for a **new** output directory, so the capture is never stopped. Record in IDEA-063 that it is interim, with its coverage parameters and hashes. It is thrown away on Oct 20.
   - **Oct 20, in the checklist's order:** the full summary with default coverage (3 UTC days with a weekend, 10 samples per token per regime), the `fee_bps = 0` confirmation, the decided profile, then the owners' review.
   - **#119:** prepare the evidence from the captured raw responses on whether quoted amounts already net out route fees, so whether `fee_bps = 0` is right. Answer with evidence, not assumption.
   - **#120:** write the review memo: per-token spread, impact and gas; any token the 50 bp validator refuses; the per-trade cap against one full position. Pin the summary and profile hashes in IDEA-063. Prompt 3 owns the strategy values inside the profile; you produce and pin the measured inputs.
   - The rehearsal profile's buy window is fixed at Oct 21 00:00 – Oct 22 00:00 UTC, so a round before then plans no buys. Whether to add a dev window is the checklist's "first signed trade" decision; support it, don't make it.

3. **Balance RPC (#92 hosted part; GAP-71).** Get the chosen provider(s) with `finalized` support and a source ID for each (up to four in failover order since #116, `driver.balance_rpc_providers`). The URLs go to the AWS owner privately, never in an issue. The selected providers, section C network approval and host reachability are already reported complete (#135/#137, PC-AWS05/06). Prepare the final pinned provider file and actual-wallet acceptance; propose a new network change only if a new reviewed destination requires one.

4. **Evidence inputs for shadow (GAP-70).**
   - Terms are already captured for five enabled non-EDGAR sources plus EDGAR (six files total), with the real SEC contact (#129, IDEA-066 PC-TERMS01/02). Don't recapture: DOJ and EC pages change on every fetch, so only the 2026-10-17 capture's files match the register. The original install/preflight was reported complete (PC-AWS06); prepare another transfer only if a reviewed release/input change requires it.
   - The public dev wallet address goes into local and host config only; never a placeholder.
   - The fresh read-only wallet capture with the balance RPC happens on Oct 20 (step 5), within five minutes of `prepare`, and after the dev-wallet first-gas swap (#106, prompt 2), because the opening state must include the BNB.

5. **AWS and hosts: applied; verify and record, don't redo.** The hosts are applied and `primary` is online over SSM and smoke-checked (2026-10-16, IDEA-066 PC-AWS02). Do not re-plan, re-apply or re-provision anything yourself; you have no AWS access, and every AWS or host step is a checklist line for the AWS owner.
   - For genuinely remaining host lines after checking PC-AWS03..08 (completed setup is listed in the README), prepare the exact command from [GATE_A.md](../GATE_A.md) and AWS_RUNBOOK, hand it over, and record the result in IDEA-058/051/066 with dates and SHAs.
   - Oct 20 steps 5–8 follow the same pattern: configs rendered with `driver.execution = "shadow"`, `preflight --bind`, `service init` and the reviewed `service activate`, evidence, runtime and the uploader started, and `larp-archive.timer` enabled.
   - **`larp-execution` stays stopped.**

6. **Exact-release evidence (GAP-72, #49, #98).** Build each required reviewed release through the accepted mirror (PC-DEC01), including the model changes before that trial; organization billing is a separate unresolved account issue. Record the run ID and the bundle and manifest hashes for the build that runs. A mirror bundle is an accepted release build, while hosted acceptance (#127) still needs its own evidence; a local suite alone is not the CI artifact.

7. **Gate A host evidence**, recorded in IDEA-058 and reviewed item by item in IDEA-042 by the checklist's Gate A reviewer:
   - one shadow round with a durable per-event and per-chunk ACK from the real receiver (R-01, DR-07);
   - 24 h of ingestion with no gaps, shown by the gap report (DR-12);
   - the automatic restart drill (DR-13 restart part) and the first hourly anchor (DR-15 schedule part);
   - IAM/TLS and routes, `chronyc tracking`, an alarm email received, and RSS per unit for the D-DN-08 memory decision (#60, decided in prompt 4).

8. **Model shadow trial start (#97 hosted part; IDEA-057 "Shadow trial").** These are host steps in the checklist's model-trial section; use its current switch prerequisites and dates. Prepare them:
   - the runtime secret holding `LARP_AIAND_API_KEY` and `LARP_MODEL_API_KEY` for OpenAI review (the latter is absent only for an intentional external-only trial);
   - budget `init` with the actual prior OpenAI spend;
   - provider check P0;
   - reviewed `prepare --model-routing` plus `--model-routing-sha256`, installation and binding of the generated runtime/routing bytes (merged PR159); no post-prepare hand edits.
   Then record P1/P2 and the trial start. The adoption decision is prompt 3's.

9. **Design option 6 (IDEA-058).** Write a recommendation on whether the evidence poller should read only the bound manifest instead of `runtime.json`. It is on no checklist line, so ask the user who decides it; implement it only if accepted.

## Acceptance

Write the criteria in your record and push them before running anything.
- Gate A is reviewed item by item in IDEA-042, with commit SHAs, CI or bundle hashes and host evidence.
- The capture covers at least 3 UTC days including a weekend, and the summary passes or refuses honestly.
- No secret appears in Git, logs or chat.
- Nothing is signed or broadcast, and no organiser is contacted.
- Remove GAP-69..72 only when each is fully verified.

## What you need from the team

The owners of the checklist lines above, in the checklist's order. The ones you wait on most: the capture's owner (capture files and hashes), the balance RPC choice, the bundle build, every host step, and the Gate A review.
