You are the agent for **Gate C: rehearsal, final activation and operations**. You work for Keegan; Yao Zhu reviews. Your job is to make the build that trades from Oct 29:
- rehearsed;
- able to recover and halt on its own;
- declared honestly in its manifest and deviations register;
- switched to the final wallet;
- handed over as a complete activation pack by **Oct 26**.

During the run there are no deploys (F-117) and no manual restarts (F-124); a human HALT is treated as not allowed (F-114). Anything the run might need has to exist as automatic, tested code before the freeze.

Read `docs/build/remaining-work/README.md` first; its rules apply here. Then read these, on `origin/codex/system-testing-20261012`:
- `docs/build/DEPLOYMENT_BUILD.md` (Gate C and DR-13..22), `docs/build/runbook.md` and `docs/build/AWS_RUNBOOK.md`
- IDEA-042, IDEA-049-D (all, especially §5: D-DN-01..11, and the R-01..R-14 risks), IDEA-036, IDEA-046, IDEA-047 and IDEA-009 §F
- `config/release/deviations.v1.json` and `config/release/services.v1.json`
- these GAP items in `docs/INCOMPLETE_WORK.md`: GAP-04, GAP-05, GAP-33..42, GAP-45, GAP-46, GAP-48, GAP-52, GAP-62 and GAP-65
- issues #49, #60 and #106
- the in-flight branch `claude/d-dn-10-clock-clear`

Put new records in IDEA-080..084; extend IDEA-042 and IDEA-049-D where the work already lives there.

AWS is reported fully resolved (team, 2026-10-16). Where an item below touches AWS, verify what exists and record its evidence. Don't re-plan or re-apply.

## Deliver

1. **Rehearsal shape (D-DN-02, GAP-04). Decide by Oct 19.**
   - Put the choice to Yao Zhu and Keegan:
     - (a) keep the declared signed rehearsal, Oct 21–26, covering Oct 24–25;
     - (b) shadow rehearsal plus a shorter signed window, recorded as a deviation.
   - Base it on prompt 2's Gate B forecast. If Gate B slips past Oct 20, record the shortfall as a deviation that same day.
   - Then run the rehearsal on the hosted dev environment with a daily rehearsal log in IDEA-042: incidents, fixes, cycle length (D-DN-06) and any crash loop (D-DN-07). **DR-21** is satisfied when that log is complete.

2. **Cut line (GAP-05), on Oct 22.** Classify every component as removable or as mandatory (safety, logging, verification, recovery). Anything not working at the cut is either removed, or the activation is blocked, and each choice is recorded as a deviation. Coordinate with prompts 2 and 3 on their items.

3. **Operations decisions.** For each one, write a memo with a recommendation, get the owner's dated answer, then build and test it.
   - **D-DN-01:** standby, or record DEV-18 as a deviation.
   - **D-DN-04:** a delivery-bound HALT on the oldest unacknowledged log.
   - **D-DN-06:** the watchdog timeout.
   - **D-DN-07:** crash loop to HALT after N restarts.
   - **D-DN-08 (#60):** memory limits on a `t3.small` against the RSS prompt 1 measures.
   - **D-DN-10:** automatic CLOCK HALT clear. Finish or review `claude/d-dn-10-clock-clear` rather than starting over.
   - **D-DN-11:** what a restore during the run means, given that F-114 forbids manual activation.
   - Coordinate D-DN-09 (HALT semantics) with prompt 3, which owns it.

4. **Drills on the host, with evidence in IDEA-042.**
   - **DR-13:** an automatic HALT drill.
   - **DR-15:** IDEA-036 criteria 1–6. That means hourly anchors to write-once storage, retention at least to Dec 31 2026, verification against anchored heads and a restore from anchors. Update IDEA-036's status, which still says "not started".
   - **DR-16:** a restore drill into an empty database, and an alarm test that reaches a person.

5. **Release, manifest and deviations (DR-18, GAP-62, D-DN-03).**
   - Collect every deviation from the submitted proposal: IDEA-009 §F, IDEA-035 §4/§5, IDEA-037, PR #123/S1, the build records IDEA-039..041/055/057/058, and each cut and decision above. For each row record the declared text, the v1.0 behaviour, the reason with evidence IDs, the date and the version.
   - Make every row FINAL by Oct 26. `activate_run` refuses a `live` run with an OPEN or DRAFT row.
   - Complete the services list (F-61).
   - **#49:** make the release-integrity step (IDEA-047 R6) something an operator can actually follow.
   - With prompt 1: an exact-release CI bundle for the frozen commit. GitHub billing is settled by the team.

6. **Final wallet (DR-17, GAP-52, #106 final part).** Who owns the final wallet is settled by the team (2026-10-16); don't chase it. Record each step with its date:
   - The fresh final wallet is generated and registered (F-14).
   - Find out whether it gets a new `AI_SEEDS_SECRET` (Q-35; F-122 confirms only the final wallet is scored). Get the answer through the team; agents never contact organisers.
   - The final wallet's BNB is seeded by MetaMask, about 6 USDT, before **Oct 29 00:00 UTC** and before its first agent trade.
   - The opening balance capture comes after that seeding.
   - Rehearse the switch on the dev host with a throwaway config: a new address and secret, a separate `.ai-seeds/` directory and nonce records, and refusal on any address mismatch.

7. **Activation pack (DR-22, GAP-37), by Oct 26.**
   - The frozen commit and its manifest.
   - The final-wallet config with an empty secret slot.
   - The runbook: start, automatic restart, HALT, restore, switch, end of run.
   - The on-call rota, which the team has settled: just include it.
   - Each owner signs off their DR items in IDEA-042.
   - Then the Gate C review, and the integration → `main` promotion PR. The go-ahead process is settled by the team. Keep `main` in step: today it lags the integration branch and has two PR85 record commits integration lacks, so reconcile them as an ordinary merge.

8. **Accountability and audit readiness.**
   - **GAP-46, GAP-48:** verify the round-log contract and test-log hygiene on the real receiver.
   - **GAP-33:** safe mode during repository outages against the version gate.
   - **GAP-34:** the audit journal's durability.
   - **GAP-36:** measurable security and recovery criteria with attached drill evidence.
   - **GAP-35:** close it with the DR-15 evidence.
   - **GAP-65:** close or narrow it against IDEA-043/044/049.
   - Prepare for the winner audit (F-17, Nov 16–20): version history, manifests and complete local logs kept and retrievable.
   - Remove each GAP line only when it is verified.

9. **Documentation and backlog (GAP-38..42, GAP-45).**
   - Update the Adopted, Implemented and Tested status from evidence.
   - Fix stale paths and provenance.
   - Bring the I-65 onboarding gate register and the organiser-question list up to date with F-113..F-124.
   - Narrow GAP-41 and GAP-45 to what is really left.
   - Prepare the thread handoff at the end, following AGENTS.md.

## Acceptance

Write the criteria in your record and push them before running anything.
- Gate C is reviewed in IDEA-042 with every DR-13..22 item evidenced (SHA, drill date or log).
- The deviations register has no OPEN or DRAFT row.
- The final-wallet switch has been rehearsed.
- No secret appears in Git, logs or chat.
- Nothing is promoted to `main` except through the team's settled go-ahead.

## What you need from the team

- Yao Zhu and Keegan: the D-DN answers, the rehearsal shape and the Gate C sign-off.
- The team: the Q-35 answer, plus confirmation of the settled final-wallet, rota and `main` go-ahead arrangements so you can record them.
- Prompts 1–3: their evidence and deviations.
