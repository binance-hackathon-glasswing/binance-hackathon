# Remaining work before trading: four AI-agent tasks (IDEA-064)

Prepared 2026-10-16; refreshed 2026-10-19 against PR133, PR183 release evidence and merged PR184 preparation. These are task briefs; they do not authorize spawning agents or host operations. This folder splits everything still left between today and the scored run into four task prompts, one per AI agent session. **Owners come from [`docs/build/PRE_TRADING_CHECKLIST.md`](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/133)** (PR #133; on branch `claude/pre-trading-checklist-20261017` until it merges). It gives every line exactly one owner, and AWS/host operations belong to the named AWS owner, except the explicitly authorized Isaac key-placement session. **People: read the checklist for your own tasks and dates.** [WHO_DOES_WHAT.md](WHO_DOES_WHAT.md) only says why the split moved there. The agent does the repository work; the checklist's owner does anything that needs credentials, money, a wallet, AWS or the hosts, or a team decision.

| # | Prompt | Checklist sections it serves | Gate it drives | Hard date (UTC, F-121) |
|---|---|---|---|---|
| 1 | [1-gate-a-hosted-shadow.prompt.md](1-gate-a-hosted-shadow.prompt.md) | "Gate A setup", "Side note: interim profile", "Oct 20: profile day", Oct 21 Gate A lines | **A**: hosted shadow run | capture runs until **Oct 20 00:00**; profile day **Oct 20**; Gate A review after 24 h of ingestion (Oct 21) |
| 2 | [2-gate-b-execution-signing.prompt.md](2-gate-b-execution-signing.prompt.md) | "Gate B setup", Oct 20 steps 9–10, Oct 21 Gate B lines | **B**: first signed trades on the dev wallet | Gate B review **Oct 20** (or Oct 21 inside the rehearsal buy window); signed rehearsal from **Oct 21** |
| 3 | [3-strategy-model-evidence.prompt.md](3-strategy-model-evidence.prompt.md) | strategy and model lines of "Decisions due Oct 19", "Oct 22 cut line", "Oct 24: S1 build" | B/C inputs: the trading plan, profiles, model and evidence settings | parameter freeze and model decision **Oct 22** |
| 4 | [4-rehearsal-activation-operations.prompt.md](4-rehearsal-activation-operations.prompt.md) | rehearsal-shape decision, "Oct 21–26: rehearsal drills", operations lines of "Oct 22 cut line", "Oct 26–29", "Housekeeping" | **C**: rehearsal, final wallet, activation pack | rehearsal shape **Oct 19**; freeze **Oct 26**; final wallet seeded before **Oct 29 00:00** |

The gates and DR items are defined in [DEPLOYMENT_BUILD.md](../DEPLOYMENT_BUILD.md). Organiser dates (F-13..F-17, all UTC per F-121): development ends Oct 26, final activation Oct 27–29, scored run Oct 29 – Nov 12, provisional ranking Nov 13, winner audit Nov 16–20. Once the run starts there are no deploys (F-117) and no manual restarts (F-124), so everything that must happen during the run has to be automatic, tested code by Oct 26.

## Current state on 2026-10-19 (verify before acting)

Read the local [pre-trading checklist](../PRE_TRADING_CHECKLIST.md) and
[coordinator handoff](../COORDINATOR_HANDOFF_20261019.md) in this tracker. For a
checkout lacking them, use [PR133](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/133).
Historical paragraphs are dated evidence, not instructions to repeat setup.

- Yao stepped down as coordinator. The next coordinator and approved AWS operator
  need the account/access/private-input handoff; do not assume another team member
  has access. Isaac key placement remains restricted to the approved session.
- Latest recorded host observation is Oct18: ea25b52 unsigned trial in larp_trial2,
  execution disabled, no signer host. It is not a fresh health check. The previous
  source-gap FAIL and UNKNOWN charge remain retained.
- Quote capture was interrupted by timestamp freshness failure and resumed Oct18
  06:54Z through Oct20 00:00Z. Do not claim uninterrupted three-day coverage.
  Keith still supplies final coverage/summary, measured fees/profile and review.
- PR176/177 are merged into integration;171/173 into this tracker;179/180/181/182
  are integrated. PR184's offline signer assembler is reviewed/merged, but actual
  assembly remains NOT_RUN_MISSING_INPUTS and all installation/signing flags false.
- PR183 qualifies the original candidatec5be269: all four mirror jobs, real systemd,
  and independent original-asset/source verification PASS. Use its exact release
  handoff; that frozen candidate predates the offline assembly tool. Host install,
  actual stage timing/charges/receiver ACK and Keith affordability remain open.
- Preserve the shared budget ledger, every charge/reservation/UNKNOWN/latch and
  the fixed unsigned cutoff Oct22 00:00Z. New builds use a separate trial database
  until reviewed version-switch support exists; a new DB never authorizes a new
  empty budget ledger or restarted trial window.
- Signing stays blocked on real router source/review/replay, #27's adopted finite
  bounds/code/timing, native tracing, measured #44 approval, funding reconciliation
  and actual signer provisioning/session/host drills. Draft139/172 remain input-gated.
- S1 core and B6 execution guards are implemented and reviewed (PR131/165).
  B4 input production, actual B5/session/input qualification, parameters, weights,
  evaluation, model adoption and rehearsal evidence remain separately tracked.
- Consumed records include IDEA066/070/075/076/080/081/082/083. Read the current
  ledger before allocating an ID or duplicating an existing implementation.

## Rules for all four agents

1. **Read first:** AGENTS.md, `docs/skill/SKILL.md` §0 (reading rules and the never-do list) and §1.10 (organiser answers F-113..F-124, as they stand on the integration branch), the LEDGER table, [DEPLOYMENT_BUILD.md](../DEPLOYMENT_BUILD.md), [PRE_TRADING_CHECKLIST.md](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/133), `docs/INCOMPLETE_WORK.md`, then your prompt's reading list. Load other files only when an item needs them (SKILL.md §0.2 reading budget).
2. **Owners come from the checklist.** Before you hand anything to a person, look up the checklist line for it and use the owner named there. Don't restate owners in your records; cite the checklist line. AWS/host operations go to the checklist's AWS owner; retain its explicit Isaac key-placement exception. If a brief and the checklist disagree, the checklist wins; tell the user so the brief can be fixed. If an item is on no checklist line, ask the user who owns it rather than guessing.
3. **Base and branches:** start each change on a new branch from the current `origin/codex/system-testing-20261012`. Open one PR per coherent change into that branch, with merge commits and no squashing. Never push to `main`, never self-merge, never force-push or rewrite pushed history (never-do #6). Promoting integration to `main` needs the team's authorization (prompt 4).
4. **Before starting any item,** list the open PRs and the recently pushed branches, then read the item's ledger record. If another session already has the item, review or extend its work rather than duplicating it.
5. **Pre-register:** write the pass criteria in your ledger record and push them before you run anything. Commit and push any code that affects decisions, trades or logging before it runs (AGENTS.md). Report every result as PASS, FAIL, NOT RUN or INCONCLUSIVE, with the commit SHA. Synthetic results are not market evidence.
6. **Humans only:** credentials, private keys, `AI_SEEDS_*` runs, anything on AWS or the hosts, MetaMask swaps, organiser messages and team decisions. For each, prepare the exact command or decision memo (options, recommendation, evidence), hand it to the checklist line's owner, and record their answer with its date. Never ask anyone to paste a secret into a chat, a commit or a document. Every run with the dev wallet's ai-seeds credentials uploads logs the auditors see, so only committed, manifested code may run with them (never-do #13).
7. **Ledger IDs:** IDs have collided before (three different IDEA-058s on 2026-10-16). Use only your reserved block: prompt 1 IDEA-065..069, prompt 2 IDEA-070..074, prompt 3 IDEA-075..079 and EXP-008..009, prompt 4 IDEA-080..084. Already used (2026-10-17): IDEA-066 (Gate A inventory, #129), IDEA-070 (swap decoder, #130), IDEA-075 (trading plan, #123), IDEA-076 (S1 build, #131), IDEA-080 (signer access, #149) IDEA-081 (stage prompts, #158), IDEA-082 (backup date fix) and IDEA-083 (assessment budget). Before taking one, grep every remote branch's `docs/LEDGER.md` for it. Extend an existing record (IDEA-039/040/041/042/055/057/058/063/070/075/076 …) where the work already has one.
8. **Shared files** (`docs/LEDGER.md`, `docs/INCOMPLETE_WORK.md`, `docs/skill/SKILL.md`, the checklist): edit only your own rows and items, and tick a checklist line only when its owner confirms it is done. On a merge conflict keep both sides. Remove an INCOMPLETE_WORK item only when it is fully done and verified, and preserve the evidence first (AGENTS.md checklist rule).
9. **When you stop:** say which items are PASS, which are blocked, and which checklist line each blocker is waiting on. Follow the AGENTS.md thread-handoff check.

## Coverage

Every open item at writing (2026-10-16) is assigned to exactly one prompt. Some have since been done (see the checklist's "Done" list); check before starting.

- **Prompt 1:** GAP-69..72, #118–#120, #92 (hosted part), IDEA-049-D PR99-RV1, D-DN-08 measurement (#60), and the IDEA-057 shadow-trial start (#97, hosted part).
- **Prompt 2:** GAP-29..32, GAP-47, GAP-49, WR-C (#44), #27, #30, #32/#33, #36/#90, and DR-02..06, DR-19 (shadow-day replay).
- **Prompt 3:**
  - Plan and model: PR #123 (IDEA-075) / EXP-007 and PR #131 (IDEA-076), D-DN-09 (#34/#52; built in #117), the IDEA-055 POLICY-HOLD, #37–#39, #55, #56, #107, the IDEA-057 adoption decision.
  - DR items: DR-08..11, DR-14.
  - GAPs: GAP-02, GAP-06..28, GAP-43, GAP-44, GAP-50, GAP-51, GAP-53..57, GAP-63, GAP-64, GAP-66, GAP-67, plus the 11 null live evidence settings.
- **Prompt 4:**
  - Decisions: GAP-04, GAP-05, D-DN-01..04, D-DN-06, D-DN-07, D-DN-10, D-DN-11.
  - DR items: DR-13, DR-15..18, DR-21, DR-22.
  - GAPs: GAP-33..40, GAP-41, GAP-42, GAP-45, GAP-46, GAP-48, GAP-52, GAP-62, GAP-65.
  - Issues: #49, #60 (decision), #106 (final wallet).
  - Also the promotion to `main`, and the audit and end-of-run readiness work.
