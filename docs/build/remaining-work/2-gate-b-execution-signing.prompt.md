You are the agent for **Gate B: execution and signing**. You prepare the work behind the checklist's "Gate B setup" section, Oct 20 steps 9–10 and the Oct 21 Gate B lines in [`docs/build/PRE_TRADING_CHECKLIST.md`](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/133). You work for the owner each of those lines names, and each review goes to the reviewer its line names; take both from the checklist, not from this brief. Your job is to make the first real approve and swap on the dev wallet possible and safe. That means every gate in front of signing comes off with evidence, not by loosening checks. The aim is Gate B reviewed on **Oct 20** (or on Oct 21 inside the rehearsal buy window), so the signed rehearsal can start **Oct 21** and cover the Oct 24–25 weekend.

Read `docs/build/remaining-work/README.md` first; its rules apply here, especially rule 2 (owners come from the checklist; AWS/host operations go to the checklist's AWS owner, with its explicit Isaac key-placement exception). Then read these, on `origin/codex/system-testing-20261012`:
- IDEA-039 (all, GB-20261015 onward), EXP-005, IDEA-049-C (WR-C), IDEA-055, IDEA-061, IDEA-062 and IDEA-050
- PR #130 (branch `claude/gate-b-router-decoder`: IDEA-070 and `docs/build/GATE_B.md`)
- `larp/execution.py` (`Decoder`, `validate_payload`), `larp/execution_live/` (including `gate_b.py`), the signer service (IDEA-047) and `config/hosts/signer.example.json`
- `docs/official/kit/web3-open-api.md` and `participant-kit.md` K8–K12
- GAP-29..32, GAP-47, GAP-49 and the WR-C line in `docs/INCOMPLETE_WORK.md`
- issues #27, #30, #32, #33, #36, #44, #92 and #106

Put new records in IDEA-071..074 (IDEA-070 is the decoder record in #130); extend IDEA-039/070 where the work already lives there.

## Deliver

1. **Swap decoder and router evidence (GAP-29, #33).** The decoder and the router-evidence check are merged in #130 (IDEA-070; real source evidence remains incomplete in draft #139). Review and extend that work; don't rebuild it.
   - `RouterEvidence.v1` is filled in from the router's verified source on BscScan, following `GATE_B.md` in #130: contract and implementation addresses, selector(s), source hash, including any proxy and nested calls. Support the checklist line that does this and the independent source-evidence review; decoder code #130 is already merged.
   - The decoder must bind every decoded field (input and output tokens, input amount, recipient equal to our wallet, minimum output, deadline, native `value` 0 for token-to-token) to the exact bytes and the risk-approved intent, and refuse any unknown selector, path, extra call or recipient.
   - Test it against **real route bytes**: using merged #130 after verified source review, `python -m larp.execution_live.router check` runs on the quote files the running capture has recorded (shared without credentials or `.env`) until it reports PASS. No separate route capture is needed. Use synthetic mutations for the refusal cases.
   - **#27, signing lifetime:** The encoded-deadline/admission contract is unresolved; 15 s admission and the kit-stated approximate 30 s quote lifetime are different quantities, not a measured encoded expiry. Merged #144 already proposes the two options: (a) a bounded signing lifetime, or (b) a router deadline no later than the proposal's expiry. The decision is recorded as C-OPEN-003 in IDEA-049-C, then the code change follows.
   - Then lift the `NOT_INTEGRATED` capability gate only for the paths that now have evidence.

2. **Signer policy values (WR-C, #44).**
   - Fill `allowed_spenders` from the router evidence (the router's `tx.to`).
   - Use the unapproved candidates already delivered by #148 and the handoff in #161; finish the numeric check that the per-trade cap allows at least one full position at the plan's weight (IDEA-075's sizing, the profile's per-trade cap, and the #56 flatten-splitting issue, with prompt 3).
   - Verify the existing refusal for a `live` signer while `cap_basis` is `EXAMPLE_PENDING_TEAM_DECISION`.
   - Installing the decided `/etc/larp/signer.json` on the signer host is a host step.

3. **Signer host and key (D-DN-05, DR-03).**
   - How the signer host is reached for key placement is a checklist decision, chosen from the options in AWS_RUNBOOK step 5 and recorded in a short IDEA entry. The choice is already IDEA-080 option (b), with temporary SSM access code in merged #149. Review the actual owner-produced plan; do not restart the choice or rebuild the route.
   - Applying the signer-access Terraform change, installing `signer.json` and opening a session for the key are host steps.
   - The key file goes to `/etc/larp/signer/wallet.key` (root, `0600`) on the signer host only, never in Secrets Manager, the repo or a chat.
   - Verify that the signer refuses to start unless the key's address equals `AI_SEEDS_ADDRESS`.
   - Update EXP-005's nonce and finality verdicts with real-node evidence from the #92 RPC (chosen and opened through prompt 1). The GB-1/GB-2 fixes are already merged.

4. **First gas and gas floor (#106, F-120; GAP-49, DR-06; #30).**
   - The dev-wallet first-gas swap is done by hand in MetaMask: the historical 2-USDT trial note is already delivered by merged #151. Only the remaining planned development funding and fresh capture remain; record each actual funding action as a funding note with no ai-seeds log (SKILL.md v0.7.9). Then prompt 1's wallet capture can include the BNB.
   - **#30:** the gas top-up round is built end to end (#103, IDEA-061). Prepare the BNB floor and top-up size proposal from the measured gas (G-28) and the evidence that BNB tracking (`native_trace`) works on a real provider.
   - #56's "no top-up after `new_risk_end`" is a strategy question; agree it with prompt 3.

5. **Reconciliation and routes.**
   - **#36 / #90:** D1–D6 are decided (#110) and built (#115, #116); closing #90 is a housekeeping line. #36 then waits only on #92.
   - **#32 / #33:** the destination table's section B is approved (#113); section C's approval is a checklist line. The route check on `primary` is a host step; record its report.
   - Keep #33 open until the decoder, the measured profile, the live evidence values and the hosted rehearsal all exist. Comment on #33 with the remaining list.

6. **Execution state machine and identifiers (GAP-30/31/32, GAP-47).** Check what IDEA-039, IDEA-050 and EXP-006 already prove against each GAP's remaining text. Close or narrow each item with evidence. Identifiers, persisted nonce/signatures, timeout uncertainty and reservation release already exist. Verify actual provider/host qualification. A timeout or expired deadline never proves a dropped send; replacement is disabled unless separately specified and qualified. PR155 reconciles the remaining acceptance work.

7. **Gate B proof on the dev wallet.** Do this from committed, manifested code, with the signer on, at minimum size, after Gate A. The rehearsal profile plans no buys before Oct 21 00:00 UTC unless the checklist's "first signed trade" decision adds a dev window.
   - **DR-02:** one approve plus one swap, each with its decision record and a logged, ACKed round, checked on chain against the logged round; a top-up round as well if one is needed.
   - **DR-04:** crash at each execution step on the host (before sign, after sign, after broadcast, after receipt) with no duplicate transaction. This is a host step (checklist Oct 21).
   - **DR-05:** no reservation left after success, revert or replay.
   - **DR-19:** replay a whole shadow day from the exported journal and check it reproduces the head (checklist "Oct 21–26: rehearsal drills").
   - Run `python -m larp.execution_live.gate_b report` on the real evidence for the Gate B review in IDEA-042.
   - **If Gate B slips past Oct 20,** tell the owner of the checklist's rehearsal-shape line the same day, so the shortfall is recorded as a deviation (GAP-04, D-DN-02).

## Acceptance

Write the criteria in your record and push them before running anything.
- The decoder refuses every mutation in its pre-registered set and accepts the real route bytes.
- No swap is signed whose decoded recipient, tokens, amounts, deadline or value differ from the approved intent.
- Every transaction maps to one registered version, one decision record and one ACKed round (never-do #2, #12).
- Approves are never logged as orders.
- No key leaves the signer host.
- Remove GAP or WR lines only when each is fully verified.

## What you need from the team

The owners of the "Gate B setup" lines, in the checklist's order: the router evidence and #130's review, the capture files for the router check, the #27 options and decision, the #44 caps and their check, the signer-access choice, every host step (signer access, `signer.json`, crash tests), the key placement, the MetaMask swap, the #30 floor, and the Gate B review. From prompt 1: a running Gate A host. From prompt 3: the plan's position sizes.
