You are the agent for **Gate B: execution and signing**. You work for Isaac; Keegan reviews. Your job is to make the first real approve and swap on the dev wallet possible and safe. That means every gate in front of signing comes off with evidence, not by loosening checks. The aim is Gate B reviewed by **Oct 20**, so the signed rehearsal can start **Oct 21** and cover the Oct 24–25 weekend.

Read `docs/build/remaining-work/README.md` first; its rules apply here. Then read these, on `origin/codex/system-testing-20261012`:
- IDEA-039 (all, GB-20261015 onward), EXP-005, IDEA-049-C (WR-C), IDEA-055, IDEA-061, IDEA-062 and IDEA-050
- `larp/execution.py` (`Decoder`, `validate_payload`), `larp/execution_live/` (including `gate_b.py`), the signer service (IDEA-047) and `config/hosts/signer.example.json`
- `docs/official/kit/web3-open-api.md` and `participant-kit.md` K8–K12
- GAP-29..32, GAP-47, GAP-49 and the WR-C line in `docs/INCOMPLETE_WORK.md`
- issues #27, #30, #32, #33, #36, #44, #90, #92 and #106

Put new records in IDEA-070..074; extend IDEA-039 where the work already lives there.

## Deliver

1. **Swap decoder (GAP-29, #33). This is the largest blocker; start now.**
   - Pre-register the criteria first (EXP-005 criterion 2 already states the bar). Identify the router that `quote-and-swap` returns as `tx.to` / `dexContractAddress` on chain 56. Get its verified source and ABI from BscScan, including any proxy implementation and nested calls, and record the contract address, implementation address, selector(s) and source hash.
   - Build a production `Decoder` that decodes the unsigned calldata into: input and output tokens, input amount, recipient (must equal our wallet), minimum output, deadline and native `value` (must be 0 for token-to-token). Bind every decoded field to the exact bytes and to the risk-approved intent. Refuse any unknown selector, path, extra call or recipient.
   - Test it against **real unsigned route bytes**. Isaac produces them with the read-only capture (IDEA-063 already calls quote and approve-build) for both directions on all five tokens and a USDT → BNB gas route. Use synthetic mutations for the refusal cases.
   - **#27:** reconcile the proposal expiry with the decoded deadline so a signed swap can never outlive its proposal.
   - Then lift the `NOT_INTEGRATED` capability gate only for the paths that now have evidence.

2. **Signer policy values (WR-C, #44).**
   - Fill `allowed_spenders` from the router evidence in item 1.
   - Prepare a decision memo for Isaac and Keith on the per-token input caps and the fee cap. The per-trade cap must allow at least one full position at the plan's weight: check PR #123's 95% / five-name sizing with prompt 3, and the #56 flatten-splitting issue.
   - Make a `live` signer refuse to start while `cap_basis` is `EXAMPLE_PENDING_TEAM_DECISION`.
   - Keegan writes the decided `/etc/larp/signer.json` on the signer host.

3. **Signer host and key (D-DN-05, DR-03).**
   - AWS is reported fully resolved (2026-10-16). Find out from Keegan or Yao Zhu how the signer host is reached now (AWS_RUNBOOK step 5) and where that is recorded. Write it up only if it isn't recorded yet; don't build a new route.
   - The person places the key file at `/etc/larp/signer/wallet.key` (root, `0600`) on the signer host only, never in Secrets Manager, the repo or a chat.
   - Verify that the signer refuses to start unless the key's address equals `AI_SEEDS_ADDRESS`.
   - Update EXP-005's nonce and finality verdicts with real-node evidence from the #92 RPC. That RPC is chosen and opened in prompt 1; the GB-1/GB-2 fixes are already merged.

4. **First gas (#106, F-120; GAP-49, DR-06).**
   - Write the step-by-step for the human MetaMask USDT → BNB swap on the dev wallet: about 4 USDT, gas paid in USDT, before any agent trade, recorded as a funding note with no ai-seeds log (SKILL.md v0.7.9). Isaac does the swap.
   - Then prompt 1 re-takes the opening balance capture.
   - Close #30: the owners' review of IDEA-061 (top-up rounds that the service can settle) and the two-transaction BNB floor.
   - #56's "no top-up after `new_risk_end`" is a strategy question; agree it with prompt 3.

5. **Reconciliation and routes.**
   - **#36 / #90:** get the IDEA-055 D1–D6 decisions reviewed by the owners and recorded.
   - **#32 / #33:** get the per-unit destination list approved (IDEA-062: Keegan + Isaac), then run the hosted route check from both host roles after Gate A.
   - Keep #33 open until the decoder, the measured profile, the live evidence values and the hosted rehearsal all exist. Comment on #33 with the remaining list.

6. **Execution state machine and identifiers (GAP-30/31/32, GAP-47).** Check what IDEA-039, IDEA-050 and EXP-006 already prove against each GAP's remaining text. Close or narrow each item with evidence. Build only what is still missing: approve + swap identifiers, the 120 s timeout, dropped and replaced states, and reservation release on every path.

7. **Gate B proof on the dev wallet.** Do this from committed, manifested code, with the signer on, at minimum size, after Gate A.
   - **DR-02:** one approve plus one swap, each with its decision record and a logged, ACKed round; a top-up round as well if one is needed.
   - **DR-04:** crash at each execution step on the host (before sign, after sign, after broadcast, after receipt) with no duplicate transaction.
   - **DR-05:** no reservation left after success, revert or replay.
   - **DR-19:** replay a whole shadow day exactly.
   - Run `python -m larp.execution_live.gate_b report` on the real evidence, then have Keegan review Gate B in IDEA-042.
   - **If Oct 20 slips,** tell Keegan the same day, so prompt 4 can record the rehearsal shortfall as a deviation (GAP-04, D-DN-02).

## Acceptance

Write the criteria in your record and push them before running anything.
- The decoder refuses every mutation in its pre-registered set and accepts the real route bytes.
- No swap is signed whose decoded recipient, tokens, amounts, deadline or value differ from the approved intent.
- Every transaction maps to one registered version, one decision record and one ACKed round (never-do #2, #12).
- Approves are never logged as orders.
- No key leaves the signer host.
- Remove GAP or WR lines only when each is fully verified.

## What you need from the team

- Isaac: real unsigned route captures, the MetaMask swap, key placement, cap decisions with Keith, and the RPC choice.
- Keegan: the signer access route review, the `signer.json` install and the Gate B review.
- Prompt 1: a running Gate A host.
- Prompt 3: the plan's position sizes.
