# Agent instructions

This repo builds LARP, our agent for the Binance Agentic AI Challenge.

## Read in this order
1. `docs/skill/SKILL.md`: official facts, the never-do list, hard guardrails and open questions. Follow its reading rules (§0).
2. `docs/LEDGER.md`: the index of ideas and experiments. Read the table only.
3. Only if the task names an ID or touches its topic: the file that `docs/skill/SKILL.md`'s file index points to, or `docs/ledger/<ID>.md`.

Do not load every doc by default.

## Incomplete-work checklist
- When planning or completing work, check `docs/INCOMPLETE_WORK.md` for relevant outstanding items.
- Once a checklist item is fully completed and verified, remove its entire line item from `docs/INCOMPLETE_WORK.md` in the same change. Do not leave checked-off items behind.
- Keep partially completed or blocked items in the checklist; update their wording to describe the remaining work. Preserve completion evidence in the relevant plan, test results, or ledger entry before removing an item. The checklist is a live backlog, not the append-only experiment ledger.

## Hard rules (summary; SKILL.md §0.3 governs)
- Never commit secrets, keys, `.env` files or private training/label data.
- Never force-push or rewrite history on the challenge branch.
- Code affecting decisions, trades or logging must be committed and pushed before it runs.
- Log new ideas and experiments in the ledger. Write pass criteria before running anything.
