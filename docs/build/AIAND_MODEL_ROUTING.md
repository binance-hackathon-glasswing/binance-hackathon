# Experimental AIand model routing (IDEA-057)

This is an opt-in **shadow-only** implementation of [IDEA-056](../ledger/IDEA-056.md). It has no live/scored activation approval. The default runtime remains deterministic. Kimi K3 and GLM-5.3 are funded through AIand; do not point these routes at the original labs or AIand's `auto` selector.

## Endpoint and identities

The example uses `zai-org/glm-5.3` at low effort, then optional direct OpenAI `gpt-6.1-sol` at medium for review. If OpenAI is absent, limited or unavailable, the difficult route is `moonshotai/kimi-k3` high followed by GLM-5.3 high. All external calls use `https://api.aiand.com/v1/chat/completions`.

AIand's [catalog](https://docs.aiand.com/models/catalog/) lists models per organization. The public catalog was checked 2026-10-15; authenticated account entitlement and inference are not verified. The example embeds selected public capability metadata. Review/freeze that metadata and the exact settings before an authorized experiment. Body/header model mismatch or an applied effort different from the requested one is an error, not an accepted substitution. See [response headers](https://docs.aiand.com/reference/response-headers/).

## Credentials

Add `LARP_AIAND_API_KEY` to the existing runtime **Secrets Manager JSON**. `LARP_MODEL_API_KEY` is optional for Sol: without it, all model work is external. The service loads these explicitly; it does not inherit keys from an `.env` file. Never put actual keys in this repo, command arguments, routing JSON or logs. Existing signer/audit secrets still refuse loading on the coordinator.

## Shared OpenAI allocation

Use one primary-host ledger for the entire development, activation and scored window, independent of wallets/run IDs. Before the first experiment, explicitly initialize it with **all prior allocated OpenAI spend** deducted. The parent directory must already be private and writable by the runtime user:

```sh
python -m larp.intelligence.model_budget init \
  --path /var/lib/larp-runtime/openai-budget.sqlite \
  --account larp-openai-2026 \
  --initial-spent-micro-usd 0
```

Zero is an illustration, not a balance check: replace it with known prior spend. This command is future operator setup, not performed by this PR. Initialization refuses to overwrite a ledger. Runtime requires a pre-existing private file and refuses account/limit mismatch or missing/corrupt storage. Check state with the same command using `status` and omitting the initial-spend argument.

The $50 allocation leaves $10 reserved and admits at most $40 of cumulative OpenAI usage/reservations. Per-request bounds cover the configured output allowance plus conservatively bounded input, with no cache discount. Unknown/abandoned usage retains its full charge. At the limit, or explicit OpenAI insufficient-quota refusal, the durable switch sends all new model work externally, including hard reviews. A generic 429 is not credit exhaustion. In-flight calls can still be billed.

This is a single-primary allocated budget, not a global OpenAI balance API. Deduct unrelated usage before starting; do not spend this allocation using unbudgeted bake-off scripts/other keys. Carry/reconcile the ledger on host migration; do not start a second primary from a stale copy. All budget/storage failure blocks OpenAI dispatch. External funding remains separate.

Admission time counts against the model call's existing deadline. If admission
finishes after expiry, no POST is sent and its reservation remains conservatively
charged. A settlement or credit-switch storage failure after a reply preserves the
paid request/reply artifacts, usage, cost, reasoning and original provider outcome;
the assessment falls back externally. Further OpenAI dispatch stays blocked in
that process even if storage becomes readable again. Reconcile ledger reservations
and provider usage before restarting the model worker.

## Opt-in runtime configuration

Copy/review `config/intelligence/aiand-routing.example.json`, then pin its file SHA-256 in the runtime's existing `driver` block:

```json
{
  "assessor": "aiand_routed",
  "execution": "shadow",
  "model_routing_file": "/etc/larp/model-routing.json",
  "model_routing_sha256": "<reviewed-file-sha256>",
  "model_budget_root": "/var/lib/larp-runtime"
}
```

This fragment supplements all existing driver fields and the pinned runtime release configuration. The example is not installed or activated automatically. `execution: service` and scored `mode: live` refuse experimental routing. Existing intelligence live values, rights, source, release and host prerequisites still apply.

## Assessment and failure behavior

Every stage uses original saved filing evidence and the real verifier. The routine stage has half the assessment time and at most three tools; review/fallback can use only the remaining common time and six-tool allowance. At most four stages mean at most ten model steps including finishes. Class-item candidates, event interpretation, incomplete/conflicting evidence, verifier failure and seeded clean-case audits request stronger review.

If a required reviewer fails, or accepted findings disagree, the result abstains/is unavailable; it cannot inherit a clean thesis from the routine stage. If AIand's difficult primary fails, only the declared secondary is attempted within the same limits. Full request/reply bytes, whitelisted model/effort headers, actual component identity and intermediate result artifact references survive in the aggregate trace. No credential header is recorded.

The primary capability this PR validates is synthetic component behavior. Provider access, real extraction quality, omission rates, latency, hosted permissions, rights/audit retention terms and production service declaration still need independent evidence before adoption. See [IDEA-057 AR1–AR8](../ledger/IDEA-057.md).
