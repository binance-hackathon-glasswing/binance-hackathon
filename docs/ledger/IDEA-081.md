# IDEA-081 — Stage prompts for the routed LLM assessor (routine and review)

- Date / author: 2026-10-17 UTC / Yao Zhu, implemented with Claude.
- Status: repository prompt review PASS; hosted trial and provider quality remain open. Signed/service capability is separately implemented in merged PR164.
- From: [IDEA-056](IDEA-056.md) (routing proposal, MR-06) and [IDEA-057](IDEA-057.md) (AIand implementation, shadow trial). This prompt change affects the routed assessor; deterministic behavior is unchanged. Signed/service capability is a separate change in PR164.
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

- **The deployed Gate A run was reported deterministic, not freshly inspected here.** Merged PR159 / IDEA-057 SG-8 now prepares and locally qualifies `aiand_routed` with explicit `--model-routing` and `--model-routing-sha256` inputs; no manual edit of prepared runtime bytes is needed. Existing deployments do not switch automatically. Yao Zhu's PC-DEC02 schedules the host switch after the Oct 18 gap report with a new reviewed release, keys, actual prior spend, provider checks and a fresh bind/init/activation. Merged PR164 separately adds opt-in signed/service routing and explicit preparation, requiring a real adoption reference and the existing gates; actual adoption and hosted rehearsal acceptance remain open. Keith supplies the exact budget figures; the approximate $49 balance is not a ledger initialization value.
- The v2 routing file needs a release built after this change; the host's `bb46234` only accepts the v1 file.

## Merge with PR #159 (IDEA-057 SG-8), 2026-10-17 — prospective

PR #159 added `validate_routing_spec`, shared by Gate A `prepare`, `gate_a_check` and runtime startup, and it accepted only `AIandRouting.v1` with exact field sets, so the v2 file from this change would have been refused by `prepare`. The integration branch was merged into this branch (no rebase) and the validator extended. Criterion written before the new tests ran (the existing routing, stage-prompt and SG-8 preparation suites were run once after the merge, 49 passed, to check the merge itself):

| ID | Criterion |
|---|---|
| SP8 | `validate_routing_spec` accepts the v2 example and the v1 example; it refuses, before any model, budget or network construction: a v2 file missing `openai_prompt` or any entry's `prompt`, a v1 file carrying `prompt`/`openai_prompt`, and a v2 prompt whose file or hash does not match. Its failure text never echoes the supplied name (SG8b). The SG-8 preparation tests pass with the v2 example. |

**Result (local, macOS, Anaconda Python 3.14): SP8 PASS.** `test_stage_prompts.py` now 10 tests (19 subtests incl. 6 SP8 cases); with `test_aiand_routing.py` and SG-8's `test_model_routing_preparation.py` (which prepares a package from the v2 example): 50 passed, 74 subtests. Full suite vs a clean worktree of the new base `a428bab`: 1446 vs 1436 passed, the same 10 failures and 4 collection errors on both (environment, as before), so no new failure. Linux/3.12 mirror CI still to run.

## SP9 — all-PR review (2026-10-17 SGT, prospective)

User requests review and fixes for every open PR. The shared validator currently
checks only prompt bytes/hash; a hash-matching invalid UTF-8 file passes it and
fails later at `stage_config.decode`, contrary to SG8b/SP8. A symlink can also
resolve outside the release prompt directory, and prompt reads are unbounded.

Pass criteria before changed code executes: shared validation and construction
must reject invalid UTF-8, empty/oversized addenda, symlinks and non-local names
(including backslash/`..`/NUL), with fixed non-reflecting errors before budget,
provider or network construction. Limit each addendum to 16 KiB and preserve the
existing exact-byte hash and composition for valid v1/v2 files. Add regression
cases, push before execution, run the routing/preparation suite, and run the full
Linux/PostgreSQL14 suite. Correct stale v1-only preparation claims and the example
hash in the runbook; leave actual host state, adoption and model quality unclaimed.

SP9 result: regression-only `c5e56bc` reproduced all seven bad-input cases
(7 subtest failures; one test body passed). Fix pushed at `60ca47f` before rerun:
stage-prompt/routing/preparation/local-qualification suite **62 passed,
109 subtests**, 4.77s, no skips, Linux/Python3.12.14. The runbook's existing v2
example hash was already correct and is retained; stale manual-edit-only claims
were corrected. Combined full-suite evidence follows in IDEA-049 ALLPR-20261017;
no provider, host or prompt-quality acceptance is inferred.

SP9 full regression: combined published review head `7328e0a` includes the exact
#158 code from `6a65b39` plus all seven other reviewed PRs. Linux/Python3.12.14 /
PostgreSQL14.24: **1957 passed, 6 expected skips, 2931 subtests**, 326.89s. The
skips are one external-recording corpus and five opt-in systemd checks; routing,
preparation and PostgreSQL checks ran. Full record: IDEA-049 ALLPR-20261017.
Owner-reported mirror run39045682226 is also green for `6a65b39`; this session
could not independently read the private mirror API (404). Provider quality,
actual account/budget initialization, hosted trial and adoption remain open.
