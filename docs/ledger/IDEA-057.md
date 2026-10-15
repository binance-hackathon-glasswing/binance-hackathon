# IDEA-057 — AIand implementation of external-first evidence routing

- Date / author: 2026-10-15 SGT / Keith, implemented with Codex at the user's request to do both the AIand-specific design and implementation.
- Status: open (implementation and synthetic regressions prepared; execution pending the required pushed-commit gate; no live adoption).
- From: [IDEA-056](IDEA-056.md), draft PR #85. This branch is stacked on `codex/idea-056-model-routing` at `ab2e155`, not merged into main.
- Scope: AIand adapter; opt-in external-first shadow assessor; durable $40 OpenAI admission plus $10 full-run reserve; complete external review after credit refusal; provenance and runtime secret loading. External funding is supplied by the user; K3/GLM prices are outside this comparison.
- Out of scope: real-provider inference, private labels, independent real-document evaluation, source/model rights approval, scored/live activation, trading-policy adoption and AWS changes. These retain IDEA-056 MR-01–06 and GAP-23/24/57/62/67 owners.

## AIand-specific evidence, checked before implementation

**[PRIMARY]** Read the documentation at [docs.aiand.com](https://docs.aiand.com/), including [chat](https://docs.aiand.com/api/chat-completions/), [catalog](https://docs.aiand.com/models/catalog/), [reasoning](https://docs.aiand.com/capabilities/reasoning/), [headers](https://docs.aiand.com/reference/response-headers/) and [errors](https://docs.aiand.com/errors/). Also fetched the public, unauthenticated `GET https://api.aiand.com/v1/models` on 2026-10-15 with TLS verification using the system CA store. No credentials or inference request were used.

The public catalog returned `moonshotai/kimi-k3` and `zai-org/glm-5.3`, each with `low`, `high`, `max`, a 1,048,576-token context and a 131,072-token output bound. Both are served by AIand, not a direct call to the original lab. Org-scoped account access, deployment revision, paid-request behavior and accuracy are unverified. The example pins the observed capability fields; it does not use AIand's dynamic `auto` selector.

The adapter uses fixed `https://api.aiand.com/v1/chat/completions`, bearer auth, JSON mode, explicit `reasoning_effort` and `max_completion_tokens`. It requires the body model plus `X-Model` to match case-insensitively and `X-Reasoning-Effort` to match exactly. The two reasoning text fields are duplicates; retain one in the trace and the complete original reply artifact. Unknown usage is never treated as a zero OpenAI charge. AIand credit errors are not OpenAI-credit errors.

Also checked current [OpenAI error codes](https://developers.openai.com/api/docs/guides/error-codes): `credit_balance_exhausted` and named organization/project spend/usage limits are distinct from transient rate limiting. The implementation recognizes those codes and legacy insufficient-quota errors without latching on every 429.

## Prospective component pass criteria (before any changed code runs)

| ID | Required evidence |
|---|---|
| AR1 | Synthetic AIand transport confirms exact endpoint/auth/model/effort/token cap/JSON body; original nonsecret bytes and response metadata retained; no key in repr, result or artifacts. |
| AR2 | Wrong/substituted model, missing/rounded effort, refusal, truncation, invalid JSON/usage and conflicting reasoning aliases fail closed. Arbitrary endpoint, `auto`, unsupported effort and malformed capability snapshot refuse construction. |
| AR3 | Explicit private budget initialization with prior usage; runtime cannot recreate a missing file. Cross-worker reservations are atomic; unknown/crashed usage stays charged; account mismatch refuses; operating-limit/exhaustion state persists across restart and wallet/run changes. |
| AR4 | Routine GLM-low precedes stronger review. $40 admission or explicit OpenAI insufficient quota dispatches difficult work to external high; a generic 429 does not latch credit exhaustion. Missing OpenAI key supports external-only operation with stable declared identity. |
| AR5 | All stages share the original deadline and at most six tools / ten model steps (six tools plus at most four stage finishes). Required review failure/disagreement cannot produce an accepted clean thesis; no unbounded retries or new minute for fallback. |
| AR6 | The real assessor/verifier, runtime result validator, evidence reducer and round trace accept identity-bound composite results. All actual stage models, raw artifacts and rejected/abandoned stages remain traceable; scheduler review-job identity is preserved. |
| AR7 | Runtime construction is opt-in via a pinned routing file, fixed shared budget directory and optional model secrets from Secrets Manager. Defaults remain deterministic. Experimental routing refuses service execution/scored live mode; it has shadow authority only. |
| AR8 | Relevant intelligence/runtime regressions pass; run the broader local suite and report platform/environment skips accurately. Static AST/JSON/links/diff checks pass. No inference, wallet signing or AWS calls in validation. |

These are engineering criteria, not IDEA-056's independent-label non-inferiority experiment. T01/real accuracy, omission rates, hosted network/permissions and provider access remain NOT RUN. No component pass can authorize live deployment.

## Design choices

- External routine: GLM-5.3 low; difficult external primary: Kimi K3 high; secondary: GLM-5.3 high. These are explicit **example experiment settings**, not selected production models. Sol medium is optional and receives the same original filing/context through its own verifier.
- The routine stage receives at most half the time and three tool calls, reserving time/retrieval for review. Later stages receive only remaining time/tools. A seeded clean-case audit supplements independent item/event/coverage/conflict triggers; model confidence alone is not a router.
- Composite identity binds the routing spec, component identities, account and reserve policy. Job IDs stay unchanged; per-stage model-request namespaces distinguish paid calls. Full intermediate result artifacts preserve verifier outcomes without duplicating their entire text into each final trace.
- OpenAI reservations happen before POST, using a conservative UTF-8 input bound and configured output cap at standard short-context prices. Inputs beyond the short-context bound go external. Failed/unknown calls retain their maximum reservation. A provider credit refusal latches external-only; rate limits merely try the declared external review path for that assessment.
- The SQLite budget is explicitly initialized, not auto-created by the runtime, in one shared primary-host directory independent of wallet/run. Do not run duplicate model workers on other hosts with copied ledgers. Unrelated account/console usage is outside this allocated budget and must be deducted at initialization. Backups/host migration must carry and reconcile this ledger; no automatic multi-host budget failover is claimed.
- Because independent evaluation and declaration are not complete, `aiand_routed` is implemented only for shadow execution and refuses scored `live` mode. Real activation requires a later reviewed change, not a configuration bypass.

## Files and usage

Implementation: `larp/intelligence/aiand.py`, `model_budget.py`, `routing.py`, shared provider metadata/error capture, per-stage trace identity and runtime construction/optional credentials. Example: `config/intelligence/aiand-routing.example.json`. Runbook: [AIAND_MODEL_ROUTING.md](../build/AIAND_MODEL_ROUTING.md).

## Validation record

- Before execution: static AST parsing of changed Python and JSON parsing of the example passed; no project module was imported. Synthetic regression cases prepared in `tests/intelligence/test_aiand_routing.py` plus runtime composition/secret tests. Execution results are pending the repository's committed-and-pushed requirement.

## Remaining work and owners

Yao Zhu + independent annotator/Keith: real evidence labels, omission-aware mixed/external-only quality and deadline/cost measurement. Keegan + Yao Zhu: hosted Secrets Manager, private ledger/artifact permissions, single-primary backup/recovery and service/deviation declaration. Team: endpoint rights, org access, exact production revisions, model adoption and freeze. None is established by documentation or synthetic tests.
