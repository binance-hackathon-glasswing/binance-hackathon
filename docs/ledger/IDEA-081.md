# IDEA-081 — Stage prompts for the routed LLM assessor (routine and review)

- Date / author: 2026-10-17 UTC / Yao Zhu, implemented with Claude.
- Status: open — shadow-only code change; pass criteria below written before any changed code ran.
- From: [IDEA-056](IDEA-056.md) (routing proposal, MR-06) and [IDEA-057](IDEA-057.md) (AIand implementation, shadow trial). Changes the routed assessor only; the deterministic assessor, the shadow-only guard in `larp/runtime/service.py` and every trading path are untouched.
- Why: OpenAI credits cannot carry the assessor alone, so the funded AIand models (GLM-5.3 routine, Kimi K3 and GLM-5.3 high reviewers) do most of the work and must do it well. Today every stage gets the same system prompt (`assessor.v2.txt`), so the cheap first pass and the hard-case reviewer get the same instructions, and nothing tells the Chinese models about the harness's exact reply rules (JSON only, no native tool calls, finish before the output limit). IDEA-056 §4 names omission as the main risk; neither stage is told that.

## Change

1. Two Markdown addenda in `config/intelligence/prompts/routing/`:
   - `routine.md` — first pass (GLM-5.3, low effort): exhaustive scan for adverse events, exact quotes only, use the `STATEMENT:` form when unsure, leave hard cases to review, keep the reply short.
   - `review.md` — independent hard-case review (GPT-6.1 Sol, Kimi K3, GLM-5.3 high): re-read the original evidence from scratch (it never sees the first pass, by design, IDEA-056 §4.4), check negation, actor, timing and third-party attribution, spend tools only on listed gaps.
   Both repeat the reply-format rules the AIand adapter enforces. Neither adds authority: the core contract in `assessor.v2.txt` still comes first and wins any conflict.
2. Routing spec `AIandRouting.v2` (v1 keeps working unchanged): every model entry (`routine`, each `external_reviewers[i]`, and `openai_prompt`) names its addendum by file name and SHA-256. The model's system prompt is `assessor.v2.txt` + a blank line + the addendum; that composed text is hash-checked by the adapter, recorded as the stage's `prompt_sha256`/`prompt_hash` and part of its assessment key. Addenda are read only from the release's `config/intelligence/prompts/routing/` (no paths, no traversal); the spec hash, and so the router identity, covers every addendum hash.
3. `config/intelligence/aiand-routing.example.json` moves to v2 with the two addenda pinned.
4. `larp/runtime/preflight.py` `release_files` adds `config/intelligence/prompts/**/*.md`, so the addenda are in the release bundle and its manifest. Found while planning: without it the host would start without the files.

## Prospective pass criteria (frozen before the changed code ran)

| ID | Criterion |
|---|---|
| SP1 | A v2 spec builds without network I/O. Each AIand request's system message, and the OpenAI `instructions`, equal exactly `assessor.v2.txt` (trailing newlines removed) + `"\n\n"` + that stage's addendum. |
| SP2 | Each stage result and model request records the composed prompt's SHA-256 (not the core prompt's); the routine and review hashes differ; the assessment key changes with the addendum. |
| SP3 | Refused before any transport: an addendum hash mismatch, a missing or extra prompt entry, a name with a path separator or `..`, a non-`.md` name, or an unknown schema. |
| SP4 | A v1 spec behaves exactly as before: every stage uses the core prompt and its hash. |
| SP5 | Changing any addendum hash in the spec changes the router `model_hash`. |
| SP6 | Existing routing tests (`tests/intelligence/test_aiand_routing.py`) and the intelligence/runtime suites pass with no new failures against the base `0672fb8`. |
| SP7 | `larp.runtime.preflight.release_files` includes both addenda (the bundle only shipped `config/**/*.json` and `*.txt`), and no other Markdown under `config/`. |

Out of scope and NOT RUN here: real AIand/OpenAI inference, prompt quality (that is the IDEA-057 shadow trial, M5/M9), live adoption.

## Results — 2026-10-17 UTC (local, synthetic)

- New tests `tests/intelligence/test_stage_prompts.py`: **9 passed, 13 subtests** (SP1 ×2, SP2 ×2, SP3 with 11 refusal cases, SP4, SP5 ×2, SP7, plus the example-spec pin). **SP1–SP5, SP7 PASS.**
- **SP6 PASS (local):** full suite on this change vs a clean worktree of the base `0672fb8`, same machine (Anaconda Python 3.14, macOS; not the project's Linux/3.12 environment): change 1438 passed / 10 failed / 407 skipped / 4 collection errors / 2383 subtests; base 1429 / 10 / 407 / 4 / 2368. The failing and erroring tests are identical on both (`test_gate_b_evidence` ×6, `test_service_configs` ×2, `test_execution_loop` ×1, `test_archive` ×1; collection errors from the missing `eth_account` module), so no new failure. `test_aiand_routing.py` (the IDEA-057 AR suite) passes unchanged against the v2 example. Mirror CI on Linux/3.12 is still to run.
- NOT RUN: real AIand/OpenAI inference; whether the addenda improve verifier pass rate or omissions (IDEA-057 M5/M9 measure that once the trial runs with a release that contains this change).

## Open points

- **The live Gate A run cannot carry the trial as prepared.** `larp/runtime/gate_a.py` writes `assessor: deterministic` and `gate_a_check.check_scope` requires it, so the running `larp-dev-shadow-20261017` makes no model calls and needs no LLM keys. Running the IDEA-057 trial means editing `driver` in `/etc/larp/runtime.json` after `prepare` (runbook steps 4–6), re-binding and re-activating: a version event that `gate_a_check` would then refuse. When and on which run to do that is Yao Zhu's decision (see the PR).
- The v2 routing file needs a release built after this change; the host's `bb46234` only accepts the v1 file.
