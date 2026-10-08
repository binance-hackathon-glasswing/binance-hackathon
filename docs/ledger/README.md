# Ledger — rules and templates

How to keep `../LEDGER.md` (the index) and the entry files in this folder.

## Layout
- `../LEDGER.md` holds **one row per entry**: ID, title, status, a one-line result, last updated date and the file link. Agents and humans read the index first.
- `ledger/<ID>.md` holds the full record: pre-registration, data, results and corrections. Open it only when the task names that ID or touches its topic.
- To add an entry: create `ledger/<next ID>.md` from a template below, then add its row to the index in the same commit.
- When an entry closes, put the verdict in the index row's Result column, e.g. `inconclusive (n=7)` or `supported, CI [0.4, 1.9] bp`. Nobody needs to reopen the file unless they are revisiting it.

## Rules
1. **Append-only.** Never edit a past entry's criteria or results. To correct something, add a dated line under that entry: `- 2026-10-14 correction (initials): …`.
2. **Pre-register before you run.** An experiment needs its hypothesis, metric, data and periods, and its pass criterion written in its entry file, and committed, *before* any result exists. The commit timestamp is the proof.
3. **Three result states:** `supported`, `not supported`, `inconclusive`. A small sample is inconclusive, not a failure.
4. **Results from simulated quotes are not realised fills.** Say which one each result is.
5. **Never tune on P&L from the dev phase or the scored run.** Changes during the dev phase must be justified by non-P&L evidence: schema errors, latency, calibration drift, incidents. No changes at all once the dev phase is over (organiser answer F-117). (`skill/larp/plan.md` G-46, T-15; `skill/SKILL.md` F-117)
6. **If a result changes live behaviour,** it ships only through a committed, manifested version event. Record the version ID in the entry. (`skill/SKILL.md` G-03, G-11; official rule F-60)
7. **No secrets, keys or private training/label data in this file** (official rule F-61). Link to data snapshots by name or hash.
8. Cross-reference skill IDs (H-, D-, G-, Q-) where relevant, and update the skill file if an entry settles one of them.

## Status values
- **Ideas:** `open` → `promoted` (became an experiment) / `dropped` (give a reason) / `adopted` (added directly to the design with a version event).
- **Experiments:** `draft` (criteria not yet frozen) → `pre-registered` → `running` → `supported` / `not supported` / `inconclusive` / `abandoned`.

## Templates

```markdown
### IDEA-000 — short title
- Date / author: YYYY-MM-DD / initials
- Status: open
- What: one or two sentences
- Why it might help: mechanism, not hope
- Cost / risk: build time, failure surface, compliance concerns
- Links: H-/D-/G-/Q- IDs, issues, PRs
```

```markdown
### EXP-000 — short title
- Date / owner: YYYY-MM-DD / initials
- Status: draft
- From: IDEA-xxx or skill ID (e.g. H-02)
- Hypothesis: one falsifiable sentence
- Variants compared: baseline vs treatment, stating exactly what differs
- Data & periods: sources; train / calibration / threshold-selection / final-evaluation windows; snapshot hash
- Metric: primary metric, and how uncertainty is reported (e.g. bootstrap CI)
- Pass criterion: supported if …; not supported if …; inconclusive if …
- Code / config: commit SHA, config hash
- Result: (fill only after running) state + numbers + simulated or realised
- Decision: what changes, if anything; version ID if behaviour changed
- Notes / corrections:
```
