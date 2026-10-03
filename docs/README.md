# Docs — Binance Agentic AI Challenge (LARP)

Reference material for "Beyond the Benchmark: The Binance Agentic AI Challenge". Code lives at the repo root; this folder is documentation only.

## Start here
- **`skill/SKILL.md`** — the core reference, written for both humans and LLMs: the official facts, a "never do" list, hard guardrails (G-01..G-18), open questions, a post-onboarding checklist and a file index. Its reading rules (§0) explain the labels: F = official fact, T = team draft, E = graded external evidence, I = inference, G = guardrail tagged RULE / RULE-DERIVED / POLICY / PRACTICE, and so on. A POLICY is a team choice, not a Binance rule.
- **`official/source_page.md`** — verbatim capture of the official DoraHacks page. It is ground truth until the onboarding documents arrive (Oct 5–10).

## Layout
| Path | What it is |
|---|---|
| `skill/SKILL.md` | Core skill file (v0.5.1, revised 2026-09-30) |
| `skill/reference/environment.md` | External evidence (E items): bStocks, Web3 API, gas, reasoning-trace access, calendar, Laya model card |
| `skill/reference/inferences.md` | General inferences about scoring, compliance/audit and the instruments (I items) |
| `skill/reference/literature.md` | Research references (L items) |
| `skill/larp/plan.md` | Our plan: v1.0 adopted-scope table, team facts, operating plan, decisions (D-02..D-08), concept, harness additions (G-50..G-54), architecture, hypotheses (H-01..H-03), policy guardrails G-20..G-47 |
| `skill/larp/strategy-opinions.md` | Contest-strategy opinions (S items). Not evidence; keep out of official text |
| `skill/archive/proposal-phase.md` | Guidance used to write the Sep 30 proposal |
| `skill/archive/SKILL_v0.3.md` | Pre-restructure version, kept for history |
| `proposal/proposal_answers.md` | Proposal answers as drafted on Sep 30. Replace with the exact submitted text if it was edited before submission |
| `proposal/LARP_System_Architecture.pdf` | Architecture PDF uploaded with the proposal |
| `reviews/` | The two external reviews of the skill file and proposal that informed v0.5 |

## Rules worth remembering
- Never commit secrets, keys, `.env` files or private training/label data (official rule).
- After the repo is registered at onboarding, the challenge branch must keep its history: no force-pushes, no rewrites. Binance's audit account gets read-only access.
- Every piece of code affecting decisions, trades or logging must be pushed to this repo before it runs.
