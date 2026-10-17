# Remaining work before trading: four AI-agent tasks (IDEA-064)

Prepared 2026-10-16 (Claude Code session); aligned 2026-10-17 with the pre-trading checklist. This folder splits everything still left between today and the scored run into four task prompts, one per AI agent session. **Owners come from [`docs/build/PRE_TRADING_CHECKLIST.md`](../PRE_TRADING_CHECKLIST.md)** (PR #133; on branch `claude/pre-trading-checklist-20261017` until it merges). It gives every line exactly one owner, and every step that touches AWS, the hosts or their Terraform belongs to the AWS account owner it names, and to no one else. **People: read the checklist for your own tasks and dates.** [WHO_DOES_WHAT.md](WHO_DOES_WHAT.md) only says why the split moved there. The agent does the repository work; the checklist's owner does anything that needs credentials, money, a wallet, AWS or the hosts, or a team decision.

| # | Prompt | Checklist sections it serves | Gate it drives | Hard date (UTC, F-121) |
|---|---|---|---|---|
| 1 | [1-gate-a-hosted-shadow.prompt.md](1-gate-a-hosted-shadow.prompt.md) | "Gate A setup", "Side note: interim profile", "Oct 20: profile day", Oct 21 Gate A lines | **A**: hosted shadow run | capture runs until **Oct 20 00:00**; profile day **Oct 20**; Gate A review after 24 h of ingestion (Oct 21) |
| 2 | [2-gate-b-execution-signing.prompt.md](2-gate-b-execution-signing.prompt.md) | "Gate B setup", Oct 20 steps 9–10, Oct 21 Gate B lines | **B**: first signed trades on the dev wallet | Gate B review **Oct 20** (or Oct 21 inside the rehearsal buy window); signed rehearsal from **Oct 21** |
| 3 | [3-strategy-model-evidence.prompt.md](3-strategy-model-evidence.prompt.md) | strategy and model lines of "Decisions due Oct 19", "Oct 22 cut line", "Oct 24: S1 build" | B/C inputs: the trading plan, profiles, model and evidence settings | parameter freeze and model decision **Oct 22** |
| 4 | [4-rehearsal-activation-operations.prompt.md](4-rehearsal-activation-operations.prompt.md) | rehearsal-shape decision, "Oct 21–26: rehearsal drills", operations lines of "Oct 22 cut line", "Oct 26–29", "Housekeeping" | **C**: rehearsal, final wallet, activation pack | rehearsal shape **Oct 19**; freeze **Oct 26**; final wallet seeded before **Oct 29 00:00** |

The gates and DR items are defined in [DEPLOYMENT_BUILD.md](../DEPLOYMENT_BUILD.md). Organiser dates (F-13..F-17, all UTC per F-121): development ends Oct 26, final activation Oct 27–29, scored run Oct 29 – Nov 12, provisional ranking Nov 13, winner audit Nov 16–20. Once the run starts there are no deploys (F-117) and no manual restarts (F-124), so everything that must happen during the run has to be automatic, tested code by Oct 26.

## State on 2026-10-17 (verify before acting)

The checklist's "Done" list is the current record of finished work; this is a short summary.

- **Main lags the integration branch.** Day-to-day work lands on `codex/system-testing-20261012`. `main` has only the PR85 promotion records (0595074) that integration lacks; #123 and this PR carry them. Read the current state from the integration branch, not from `main`.
- **AWS hosts are applied** and `primary` is online over SSM and smoke-checked (2026-10-16, IDEA-066 PC-AWS02). The remaining host steps (alarm emails, network access to the balance RPC, bundle upload and provisioning, migrations, terms files on the host, route check, then the Oct 20 service start) are checklist lines. Agents prepare commands and record evidence; they never act on AWS themselves.
- **The real quote capture is running** on Keith's server since 2026-10-16 18:19 UTC, until 2026-10-20 00:00 UTC (#132, IDEA-063). The profile, and so Gate A `prepare` and the services, wait for it (checklist "Plan").
- **Terms are captured** for all six enabled sources and EDGAR (#129, IDEA-066 PC-TERMS01/02). Only installing that capture's files on `primary` is left.
- **Signing:** the swap decoder and router-evidence check are written (#130, IDEA-070, open for review). Still open: the router evidence itself, the signing-lifetime decision (#27, which #130 found blocks every real swap), the signer policy values (#44), the signer host access and the key.
- **The trading plan is IDEA-075** (#123, renumbered from IDEA-058 and retargeted to the integration branch). The S1 code is written (#131, IDEA-076, open for review). Its §12 values are proposals until the Oct 22 freeze.
- **Settled by the team (2026-10-16), outside these briefs:** final-wallet ownership, the on-call rota and the go-ahead to promote to `main`. Agents record these and do not chase them. Restoring GitHub Actions minutes is a checklist line (#98).
- **Open PRs at alignment:** #123 (trading plan), #125 (automatic CLOCK HALT clear, D-DN-10), #126 (this folder), #130 (decoder), #131 (S1 code), #133 (the checklist). The checklist's branch-cleanup table lists older branches with no open PR (for example `claude/gate-a-inputs`); their owners decide whether to keep them.

## Rules for all four agents

1. **Read first:** AGENTS.md, `docs/skill/SKILL.md` §0 (reading rules and the never-do list) and §1.10 (organiser answers F-113..F-124, as they stand on the integration branch), the LEDGER table, [DEPLOYMENT_BUILD.md](../DEPLOYMENT_BUILD.md), [PRE_TRADING_CHECKLIST.md](../PRE_TRADING_CHECKLIST.md), `docs/INCOMPLETE_WORK.md`, then your prompt's reading list. Load other files only when an item needs them (SKILL.md §0.2 reading budget).
2. **Owners come from the checklist.** Before you hand anything to a person, look up the checklist line for it and use the owner named there. Don't restate owners in your records; cite the checklist line. Every AWS, host or Terraform step goes to the checklist's AWS owner, and nothing else does. If a brief and the checklist disagree, the checklist wins; tell the user so the brief can be fixed. If an item is on no checklist line, ask the user who owns it rather than guessing.
3. **Base and branches:** start each change on a new branch from the current `origin/codex/system-testing-20261012`. Open one PR per coherent change into that branch, with merge commits and no squashing. Never push to `main`, never self-merge, never force-push or rewrite pushed history (never-do #6). Promoting integration to `main` needs the team's authorization (prompt 4).
4. **Before starting any item,** list the open PRs and the recently pushed branches, then read the item's ledger record. If another session already has the item, review or extend its work rather than duplicating it.
5. **Pre-register:** write the pass criteria in your ledger record and push them before you run anything. Commit and push any code that affects decisions, trades or logging before it runs (AGENTS.md). Report every result as PASS, FAIL, NOT RUN or INCONCLUSIVE, with the commit SHA. Synthetic results are not market evidence.
6. **Humans only:** credentials, private keys, `AI_SEEDS_*` runs, anything on AWS or the hosts, MetaMask swaps, organiser messages and team decisions. For each, prepare the exact command or decision memo (options, recommendation, evidence), hand it to the checklist line's owner, and record their answer with its date. Never ask anyone to paste a secret into a chat, a commit or a document. Every run with the dev wallet's ai-seeds credentials uploads logs the auditors see, so only committed, manifested code may run with them (never-do #13).
7. **Ledger IDs:** IDs have collided before (three different IDEA-058s on 2026-10-16). Use only your reserved block: prompt 1 IDEA-065..069, prompt 2 IDEA-070..074, prompt 3 IDEA-075..079 and EXP-008..009, prompt 4 IDEA-080..084. Already used (2026-10-17): IDEA-066 (Gate A inventory, #129), IDEA-070 (swap decoder, #130), IDEA-075 (trading plan, #123) and IDEA-076 (S1 build, #131). Before taking one, grep every remote branch's `docs/LEDGER.md` for it. Extend an existing record (IDEA-039/040/041/042/055/057/058/063/070/075/076 …) where the work already has one.
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
