# IDEA-064 — Remaining work before trading, as four AI-agent task prompts

- Date / author: 2026-10-16 / Claude Code session, at the user's request
- Status: open (work allocation; not started; owners aligned to PRE_TRADING_CHECKLIST.md on 2026-10-17). Nothing was run, decided or changed in code.
- What: every open item between now and the scored run (Oct 29 – Nov 12 UTC), split into four self-contained prompts for AI agent sessions, each working for named human owners (owners as written 2026-10-16; superseded by the 2026-10-17 alignment below). The files are in [`docs/build/remaining-work/`](../build/remaining-work/README.md):
  1. Gate A, the hosted shadow run (Yao Zhu + Keegan; Isaac reviews). Quote-cost capture before Oct 17 00:00 UTC (#118), the summary and LIVE profile review (#119/#120), the balance RPC (#92), evidence inputs, recording the AWS state, CI bundle evidence (#98), Gate A host evidence and the model shadow-trial start.
  2. Gate B, execution and signing (Isaac; Keegan reviews). Swap decoder (GAP-29, #33, #27), signer policy values (#44), signer host and key, first gas (#106 dev, F-120), reconciliation and routes (#36/#90, #32/#33), state machine GAPs and the dev-wallet approve/swap proof.
  3. Strategy, model and evidence settings (Keith + Yao Zhu; Isaac reviews). Renumber and implement PR #123's S1 plan (with EXP-007), the strategy issues (#37–#39, #55, #56), profiles (DR-08/09), the end of run (#107, DR-14), D-DN-09 and POLICY-HOLD, red flags (DR-10), the model decision (DR-11, #97), the 11 live evidence settings and triage of the strategy and research backlog.
  4. Gate C, rehearsal, activation and operations (Keegan; Yao Zhu reviews). Rehearsal shape (D-DN-02, GAP-04), cut line (GAP-05), D-DN-01/04/06/07/08/10/11, drills (DR-13/15/16), deviations register and manifest (DR-18, GAP-62), the final wallet (DR-17, GAP-52), the activation pack (DR-22), the promotion to `main`, audit readiness and doc and backlog hygiene.
- Why: Gate A was due Oct 14–16 and has not been reviewed, and Gate B (Oct 20), the cut line (Oct 22) and the freeze (Oct 26) are close. Parallel sessions were already colliding on ledger IDs (three different IDEA-058s), so each prompt gets its own ID block: IDEA-065..069, 070..074, 075..079 plus EXP-008..009, and 080..084.
- State it was written from: `origin/codex/system-testing-20261012` at `eda2ed2` and `main` at `fb95114`, the open issues and PRs (#123, #124), and the branches in flight on 2026-10-16. The user reported mid-writing that AWS is fully resolved. The repository records (IDEA-051/058, DEPLOYMENT_DAY.md) had not caught up, so the prompts tell agents to verify and record the AWS state rather than redo it.
- Pass criteria: none. This is an allocation, not an experiment. Each prompt makes its agent pre-register criteria in its own record before running anything.
- Links: DEPLOYMENT_BUILD.md (gates, DR-01..22), IDEA-038 (the earlier four-person allocation), IDEA-042, IDEA-049-D §5, IDEA-058, IDEA-063, GAP-69..72.
- 2026-10-16 update (user): final-wallet ownership, the on-call rota, the go-ahead to promote to `main`, and GitHub billing are settled by the team. The briefs now only record them. Added [`WHO_DOES_WHAT.md`](../build/remaining-work/WHO_DOES_WHAT.md), the per-person split with dates. The quote capture (#118), which had no named owner, is given to Isaac as the DR-01 quote-logger owner in DEPLOYMENT_BUILD.md.
- 2026-10-17 alignment (user decision): the per-person split now lives in [`docs/build/PRE_TRADING_CHECKLIST.md`](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/764eff39ac900dfb9bbc9cc05c5358ab78deae1c/docs/build/PRE_TRADING_CHECKLIST.md) (PR #133, 2026-10-17), so the repository holds one owner list. That checklist gives every line exactly one owner, and every step that touches AWS, the hosts or their Terraform is Yao Zhu's and nothing else is (no one else has AWS access, IDEA-066 PC-AWS01). `WHO_DOES_WHAT.md` is now a short pointer with no owner tables. The README and the four briefs no longer name owners or reviewers; agents take them from the checklist (new README rule 2), and an item on no checklist line goes to the user. Corrections from the 2026-10-16 text: the quote capture runs on Keith's server since 2026-10-16 18:19 UTC until Oct 20 00:00 UTC (#132), not Isaac's machine; no separate route-byte capture is needed (the router check replays the capture files); terms are captured for all sources (#129); D-DN-09 is built (#117) and D1–D6 decided and built (#110, #115, #116); the decoder is written (#130); the trading plan is IDEA-075 (#123, renumbered and retargeted, so brief 3 no longer asks for that); `signer.json`, host drills and the model-trial host steps are host steps, not Keegan's or another person's; Actions-minute restoration is a checklist line (#98) rather than "settled". Reserved IDs already used: IDEA-066 (#129), IDEA-070 (#130), IDEA-075 (#123), IDEA-076 (#131). The coverage map, agent rules and ID blocks are otherwise unchanged. The 2026-10-16 update above, which gave the capture to Isaac, is superseded.


## RV126 — current-integration and brief review (2026-10-17 SGT)

User requests review/fixes for all open PRs. Normally merged current integration
`a428bab` into this branch; resolved the two LEDGER conflicts by retaining the
newer IDEA-057 row and all added integration rows, with IDEA-064 preserved once.
Updated the briefs so they no longer ask agents to repeat provisioning, terms
installation, merged implementations/proposals or historical funding notes.
Mirror releases are accepted under PC-DEC01; organization billing remains broken.

Corrected EXP-007's O2 ordering (freeze the default before running), its Oct16
cutoff versus Oct21 weight cutoff, missing local checklist dependency (PR133
fallback links), final-wallet credential assumption, consumed IDEA-080/081 IDs,
Isaac's key-session exception and stale deterministic-only preparation. Source,
policy, actual host/route/trial evidence and future S1 delivery remain open.
No new team decision, host action or trade is implied. Historical alignment text
above records what was true then; these corrections supersede its stale tasks.

Validation: stdlib-only local Markdown link checks and unique ledger-ID checks
passed; conflict markers are absent and `git diff --check` passes. No application
code was changed beyond the ordinary target merge; changed application code was
not run while GitHub authentication is unavailable. Merge/fixes are committed
locally and need an authenticated push before further project execution.


## RV126-CONT01 — reconcile briefs with PR133 (2026-10-19)

User asks to continue PR133; its recorded outstanding work includes aligning
PR126's older briefs with the current handoff. Merge existing PR126 material,
retaining the tracker’s newer ledger rows. Correct stale coordinator ownership,
interrupted quote coverage, budget init/restarted-window instructions, completed
review/release/assembler/B6 status, funding confirmation and consumed IDs.
No new authority model, numeric bound, adoption, host action or official-rule
interpretation is introduced. Historical evidence above remains historical.

Prospective documentation checks: all brief links resolve locally or retain
explicit PR133 fallback; ledger IDs unique, register rendering valid, no conflict
markers or whitespace errors; diff from9a0b80e contains only documentation and no
manifested runtime/config/build bytes. Combined CI at9a0b80e therefore covers the
unchanged application tree; do not claim its bundle contains these later briefs.


RV126-CONT01 documentation verification **PASS** at e80960e:14 relative links,
75 unique ledger IDs, register rendering and whitespace/conflict checks. Diff
from combined CI source9a0b80e is only nonmanifested documentation. The briefs
are incorporated into PR133; original PR126's integration promotion remains
separate until the parent tracker is promoted. No market experiment, adoption,
host, credential or trading action. Combined application CI39213335253 passes
2109 tests/3340 subtests with6 expected skips and separate systemd5/5.


## RV-126 — independent integration review (2026-10-19)

Criteria before verification: briefs must agree with the current PR133 handoff, retain all operational gates and recorded uncertainty, link to available documents, and add no runtime/configuration/tool changes to integration. Resolve the old ledger conflict without discarding either historical records or newer integration status. Check Markdown links, whitespace and the exact integration diff before merge.

Review fixes: import the reviewed PR133 brief corrections, replace unavailable local tracker links with pinned PR133 source links, and retain the newer integration ledger rows. Owner acceptance, source/native evidence, signing lifetime, measured caps, funding and host qualification remain open. This review completes documentation preparation only.
