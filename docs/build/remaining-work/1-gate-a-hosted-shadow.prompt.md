You are the agent for **Gate A: the hosted shadow run**. You work for Yao Zhu and Keegan; Isaac reviews. Your job is to get LARP running on the AWS dev hosts in shadow mode. That means real read-only market data, real evidence, real decisions and real ai-seeds round logs from a manifested build, with every order ending `NOT_SUBMITTED` and nothing signed. You also need to collect the evidence that lets Keegan review Gate A item by item in IDEA-042. Gate A was due Oct 14–16 and is now the critical path: Gate B (Oct 20) and the signed rehearsal (Oct 21) both need a running host.

Read `docs/build/remaining-work/README.md` first; its rules apply here. Then read these, on `origin/codex/system-testing-20261012`:
- `docs/build/GATE_A.md`, `docs/build/DEPLOYMENT_DAY.md`, `docs/build/AWS_RUNBOOK.md`, `docs/build/runbook.md`
- IDEA-051, IDEA-058 (all, including "Remaining work and ownership" and design option 6), IDEA-063, IDEA-062 and IDEA-046/047
- GAP-69..72 and "IDEA-049-D PR99-RV1" in `docs/INCOMPLETE_WORK.md`
- issues #92, #97, #118, #119 and #120

Put new records in IDEA-065..069; extend IDEA-058/063 where the work already lives there.

## Deliver, in this order

1. **Quote-cost capture (#118, P0; GAP-69). Do this now.** The capture must start before **Sat Oct 17 00:00 UTC**, so that by Mon Oct 19 it covers 3 UTC days including the weekend. That is what IDEA-063's summary refuses to work without.
   - Isaac runs it (DR-01 owner). Check that Isaac has a pushed build of `tools/run_quote_capture.sh` and the IDEA-063 producer.
   - Prepare the exact command with the IDEA-063 defaults (`--min-samples 10`, `--min-days 3`, `--require-weekend`). Confirm it only calls read-only endpoints: quote, approve-build and gas-estimate, never `quote-and-swap` broadcast, signing or an ai-seeds upload.
   - The capture uses the Binance Web3 API key, never the wallet key or `AI_SEEDS_SECRET`. Isaac runs it on their own machine or on `primary`.
   - Raw artifacts stay outside Git; record their hashes.
   - If the start slips, record the new coverage date and what it delays.

2. **Summary review and the LIVE rehearsal profile (#119, #120).**
   - **#119:** settle from the captured raw responses whether quoted amounts are already net of route fees, so whether `fee_bps = 0` is right. Answer with evidence, not assumption.
   - **#120:** run `summarize`, then `build_live_profiles`. Write the owners' review memo: per-token spread, impact and gas; any token the 50 bp validator refuses; the per-trade cap against one 20% position. Get Keith's and Isaac's sign-off.
   - Pin the summary and profile hashes. Prompt 3 owns the strategy values inside the profile; you produce and pin the measured inputs.
   - **Decision for the team:** the rehearsal profile's window opens Oct 21 00:00 UTC, so a shadow run before then plans no buys. Put the choice to Yao Zhu: accept that, or register a short dev-shadow window profile as a version event so real decisions can be seen sooner.

3. **Balance RPC (#92 hosted part; GAP-71, Isaac).** Get Isaac's choice of a BSC RPC with `finalized` support and its source ID, and add it to the approved destination list (IDEA-062). After the hosts start, run the first hosted read and the route check from both host roles.

4. **Evidence inputs for shadow (GAP-70, Yao Zhu).**
   - The public dev wallet address and a real SEC contact for `LARP_SEC_USER_AGENT` go into local and host config only; never a placeholder.
   - Run `python -m larp.sources.live terms --write-register` from pushed code to capture the missing terms of use. Keep the artifacts outside Git, install them on the host and record their hashes.
   - Take a fresh read-only wallet capture with the balance RPC. Do this **after** the MetaMask first-gas swap (#106, prompt 2), because the opening state must include the BNB.

5. **AWS: reported fully resolved (team, 2026-10-16). Verify and record it; don't redo it.** Do not re-plan, re-apply or re-provision anything.
   - Ask Yao Zhu or Keegan where the evidence of the AWS work is: the applied plan, the hosts, the provisioned bundle hash, the migrations (including additive 012/013, IDEA-049-D PR99-RV1), the alarm subscription and the SSM access.
   - If any of it isn't written down yet, record it in IDEA-058/051 with dates and SHAs.
   - Only items the AWS work didn't cover are still yours. Check each against [GATE_A.md](../GATE_A.md):
     - configs rendered with `driver.execution = "shadow"`;
     - `preflight --bind`;
     - `service init` and the reviewed `service activate`;
     - evidence, runtime and the uploader started, and `larp-archive.timer` enabled.
   - **`larp-execution` stays stopped.**
   - If a step turns out to be undone, hand the exact command to Yao Zhu rather than running it yourself.

6. **Exact-release evidence (GAP-72).** GitHub billing and Actions minutes are settled by the team (2026-10-16), so don't chase them. With Keegan, pin the CI-built bundle and its manifest hashes for the build that runs. A local suite is never a substitute for it.

7. **Gate A host evidence**, recorded in IDEA-058 and reviewed by Keegan in IDEA-042:
   - one shadow round with a durable per-event and per-chunk ACK from the real receiver (DR-07);
   - 24 h of ingestion with no gaps (DR-12);
   - the automatic restart drill (DR-13 restart part) and the hourly anchor running (DR-15 schedule part);
   - IAM/TLS and routes from both roles, `chronyc tracking`, an alarm email received, and RSS per unit for the D-DN-08 memory decision (#60, decided in prompt 4).

8. **Model shadow trial start (#97 hosted part; IDEA-057 "Shadow trial").** Once Gate A is up, help Yao Zhu with the host steps:
   - the runtime secret holding `LARP_AIAND_API_KEY`;
   - budget `init` with the real prior OpenAI spend;
   - provider check P0;
   - pinning the routing file and runtime config.
   Then record P1/P2 and the trial start. The adoption decision is prompt 3's.

9. **Design option 6 (IDEA-058).** Bring Keegan a recommendation on whether the evidence poller should read only the bound manifest instead of `runtime.json`. Implement it only if Keegan accepts.

## Acceptance

Write the criteria in your record and push them before running anything.
- Gate A is reviewed item by item in IDEA-042, with commit SHAs, CI or bundle hashes and host evidence.
- The capture covers at least 3 UTC days including a weekend, and the summary passes or refuses honestly.
- No secret appears in Git, logs or chat.
- Nothing is signed or broadcast, and no organiser is contacted.
- Remove GAP-69..72 only when each is fully verified.

## What you need from the team

- Isaac runs the capture (DR-01 owner), with Web3 API credentials on their own machine.
- Isaac: the RPC choice.
- Yao Zhu: where the AWS evidence is recorded, the SEC contact and the AIand key.
- Keegan: Gate A review.
