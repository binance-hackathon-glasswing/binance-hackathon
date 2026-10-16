# Remaining work before trading: four AI-agent tasks (IDEA-064)

Prepared 2026-10-16 (Claude Code session). This folder splits everything still left between today and the scored run into four task prompts, one per AI agent session. Each prompt names the human owner it works for. The agent does the repository work; the person does anything that needs credentials, money, a wallet, an AWS spend or a team decision.

| # | Prompt | Works for (reviewer) | Gate it drives | Hard date (UTC, F-121) |
|---|---|---|---|---|
| 1 | [1-gate-a-hosted-shadow.prompt.md](1-gate-a-hosted-shadow.prompt.md) | Yao Zhu + Keegan (Isaac) | **A**: hosted shadow run | capture starts before **Oct 17 00:00**; Gate A as soon as the inputs exist |
| 2 | [2-gate-b-execution-signing.prompt.md](2-gate-b-execution-signing.prompt.md) | Isaac (Keegan) | **B**: first signed trades on the dev wallet | Gate B review **Oct 20**; signed rehearsal from **Oct 21** |
| 3 | [3-strategy-model-evidence.prompt.md](3-strategy-model-evidence.prompt.md) | Keith + Yao Zhu (Isaac) | B/C inputs: the trading plan, profiles, model and evidence settings | parameter freeze and model decision **Oct 22** |
| 4 | [4-rehearsal-activation-operations.prompt.md](4-rehearsal-activation-operations.prompt.md) | Keegan (Yao Zhu) | **C**: rehearsal, final wallet, activation pack | rehearsal shape **Oct 19**; freeze **Oct 26**; final wallet seeded before **Oct 29 00:00** |

The gates and DR items are defined in [DEPLOYMENT_BUILD.md](../DEPLOYMENT_BUILD.md). Organiser dates (F-13..F-17, all UTC per F-121): development ends Oct 26, final activation Oct 27–29, scored run Oct 29 – Nov 12, provisional ranking Nov 13, winner audit Nov 16–20. Once the run starts there are no deploys (F-117) and no manual restarts (F-124), so everything that must happen during the run has to be automatic, tested code by Oct 26.

## State at writing (verify before acting)

- **Main lags the integration branch.** Day-to-day work lands on `codex/system-testing-20261012`. `main` has only the PR85 promotion records that integration lacks. Read the current state from the integration branch, not from `main`.
- **AWS is reported fully resolved** (team, 2026-10-16, after the repository records were last updated; they still say the hosts are off). Agents verify it and record the evidence; they do not re-plan or re-apply anything.
- **Gate A has not been reviewed.** The integration branch has the Gate A tooling (`larp/runtime/gate_a.py`, [GATE_A.md](../GATE_A.md), IDEA-058), the session calendar (IDEA-054), the quote-cost producer (`tools/run_quote_capture.sh`, IDEA-063), gas top-up rounds (IDEA-061), route checks (IDEA-062) and chain-balance reconciliation (IDEA-055). What is missing is the real data, a reviewed hosted shadow run and the decisions: GAP-69..72 in [INCOMPLETE_WORK.md](../../INCOMPLETE_WORK.md).
- **Signing is still blocked** by the swap decoder (GAP-29, #33) and the example signer policy values (#44).
- **The trading plan is decided but not built.** PR #123 records the team's choice of S1 at 95% with a trend guard and an LLM limiter. Its §12 values are only proposals until the Oct 22 freeze. Nothing in it is implemented.
- **Branches in flight when this was written:** `claude/d-dn-10-clock-clear` (automatic CLOCK HALT clear, D-DN-10), `claude/sweet-tesla-dx49h0` (PR #123), `claude/record-91` (PR #124), `claude/gate-a-inputs` (an older Gate A input-tools branch; check whether IDEA-058 on integration supersedes it before reusing anything).

## Rules for all four agents

1. **Read first:** AGENTS.md, `docs/skill/SKILL.md` §0 (reading rules and the never-do list) and §1.10 (organiser answers F-113..F-124, as they stand on the integration branch), the LEDGER table, [DEPLOYMENT_BUILD.md](../DEPLOYMENT_BUILD.md), `docs/INCOMPLETE_WORK.md`, then your prompt's reading list. Load other files only when an item needs them (SKILL.md §0.2 reading budget).
2. **Base and branches:** start each change on a new branch from the current `origin/codex/system-testing-20261012`. Open one PR per coherent change into that branch, with merge commits and no squashing. Never push to `main`, never self-merge, never force-push or rewrite pushed history (never-do #6). Promoting integration to `main` needs the team's authorization (prompt 4).
3. **Before starting any item,** list the open PRs and the recently pushed branches, then read the owner's ledger record. If another session already has the item, review or extend its work rather than duplicating it.
4. **Pre-register:** write the pass criteria in your ledger record and push them before you run anything. Commit and push any code that affects decisions, trades or logging before it runs (AGENTS.md). Report every result as PASS, FAIL, NOT RUN or INCONCLUSIVE, with the commit SHA. Synthetic results are not market evidence.
5. **Humans only:** credentials, private keys, `AI_SEEDS_*` runs, AWS spend and applies, MetaMask swaps, organiser messages and team decisions. For each, prepare the exact command or decision memo (options, recommendation, evidence), hand it to the named person, and record their answer with its date. Never ask anyone to paste a secret into a chat, a commit or a document. Every run with the dev wallet's ai-seeds credentials uploads logs the auditors see, so only committed, manifested code may run with them (never-do #13).
6. **Ledger IDs:** IDs have already collided (three different IDEA-058s exist). Use only your reserved block: prompt 1 IDEA-065..069, prompt 2 IDEA-070..074, prompt 3 IDEA-075..079 and EXP-008..009, prompt 4 IDEA-080..084. Before taking one, grep every remote branch's `docs/LEDGER.md` for it. Extend an existing record (IDEA-039/040/041/042/055/057/058/063 …) where the work already has one.
7. **Shared files** (`docs/LEDGER.md`, `docs/INCOMPLETE_WORK.md`, `docs/skill/SKILL.md`): edit only your own rows and items. On a merge conflict keep both sides. Remove an INCOMPLETE_WORK item only when it is fully done and verified, and preserve the evidence first (AGENTS.md checklist rule).
8. **When you stop:** say which items are PASS, which are blocked, and who each blocker is waiting on. Follow the AGENTS.md thread-handoff check.

## Coverage

Every open item at writing is assigned to exactly one prompt:

- **Prompt 1:** GAP-69..72, #118–#120, #92 (hosted part), #98, IDEA-049-D PR99-RV1, D-DN-08 measurement (#60), and the IDEA-057 shadow-trial start (#97, hosted part).
- **Prompt 2:** GAP-29..32, GAP-47, GAP-49, WR-C (#44), #27, #30, #32/#33, #36/#90, and DR-02..06, DR-19 (shadow-day replay).
- **Prompt 3:**
  - Plan and model: PR #123 / EXP-007, D-DN-09 (#34/#52), the IDEA-055 POLICY-HOLD, #37–#39, #55, #56, #107, the IDEA-057 adoption decision.
  - DR items: DR-08..11, DR-14.
  - GAPs: GAP-02, GAP-06..28, GAP-43, GAP-44, GAP-50, GAP-51, GAP-53..57, GAP-63, GAP-64, GAP-66, GAP-67, plus the 11 null live evidence settings.
- **Prompt 4:**
  - Decisions: GAP-04, GAP-05, D-DN-01..04, D-DN-06, D-DN-07, D-DN-10, D-DN-11.
  - DR items: DR-13, DR-15..18, DR-21, DR-22.
  - GAPs: GAP-33..40, GAP-41, GAP-42, GAP-45, GAP-46, GAP-48, GAP-52, GAP-62, GAP-65.
  - Issues: #49, #60 (decision), #106 (final wallet).
  - Also the promotion to `main`, and the audit and end-of-run readiness work.
