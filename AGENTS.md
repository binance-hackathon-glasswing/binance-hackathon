# Agent instructions

This repo builds LARP, our agent for the Binance Agentic AI Challenge.

## Read in this order
1. `docs/skill/SKILL.md`: official facts, the never-do list, hard guardrails and open questions. Follow its reading rules (§0).
2. `docs/LEDGER.md`: the index of ideas and experiments. Read the table only.
3. Only if the task names an ID or touches its topic: the file that `docs/skill/SKILL.md`'s file index points to, or `docs/ledger/<ID>.md`.

Do not load every doc by default.

## Hard rules (summary; SKILL.md §0.3 governs)
- Never commit secrets, keys, `.env` files or private training/label data.
- Never force-push, rebase, amend pushed commits or otherwise rewrite history on the challenge branch. GitHub branch protection is not available on our plan (checked 2026-10-03), so nothing technical stops a force-push; this rule is the only guard. Never use `git push --force` / `--force-with-lease`, `git reset` on pushed commits, or history-rewriting tools on `main`. Fix mistakes with a new commit (`git revert`).
- Code affecting decisions, trades or logging must be committed and pushed before it runs.
- Log new ideas and experiments in the ledger. Write pass criteria before running anything.

## Thread handoff
Tell the user when a session is ready to hand off to a new one. Do this when they ask, after a big piece of progress, or when the context window is nearing its limit and key details could be lost to compression.

"Ready" means a strict check passes that everything from the session is kept outside the conversation:
1. **Git:** every change is committed and pushed. `git status` is clean and `main` matches `origin/main`. List any unpushed commits.
2. **Docs:** every decision, finding and new fact is written into the right file with an ID: `docs/skill/SKILL.md` or `docs/skill/larp/plan.md` items, or a `docs/LEDGER.md` row plus its `docs/ledger/<ID>.md` entry.
3. **No loose ends:** no unflagged placeholders in files touched this session, no stale copies or temp files in the repo, and no secrets or `.env` committed.
4. **Open items:** listed explicitly — what each is, who owns it, and where it is recorded.

If any check fails, say what is still pending instead of declaring the session ready.
