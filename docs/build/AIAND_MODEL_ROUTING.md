# Experimental AIand model routing (IDEA-057)

This is an opt-in **shadow-only** implementation of [IDEA-056](../ledger/IDEA-056.md). It has no live/scored activation approval. The default runtime remains deterministic. Kimi K3 and GLM-5.3 are funded through AIand; do not point these routes at the original labs or AIand's `auto` selector.

## Endpoint and identities

The example uses `zai-org/glm-5.3` at low effort, then optional direct OpenAI `gpt-6.1-sol` at medium for review. If OpenAI is absent, limited or unavailable, the difficult route is `moonshotai/kimi-k3` high followed by GLM-5.3 high. All external calls use `https://api.aiand.com/v1/chat/completions`.

This implements the requested ChatGPT/Chinese-model split through API calls:

| Work | Model |
|---|---|
| Routine extraction and straightforward evidence questions | GLM-5.3, low effort, through AIand |
| Main/difficult judgments: material events, conflicting or incomplete evidence, failed verification, and sampled clean-case audits | OpenAI `gpt-6.1-sol`, medium effort, through the direct OpenAI API |
| Difficult review when OpenAI is absent, unavailable or over its shared operating limit | Kimi K3 high, then GLM-5.3 high, through AIand |

The stronger reviewer receives original evidence and uses the same verifier.
Unresolved disagreement abstains. Arithmetic, sizing and execution remain code.

AIand's [catalog](https://docs.aiand.com/models/catalog/) lists models per organization. The public catalog was checked 2026-10-15; authenticated account entitlement and inference are not verified. The example embeds selected public capability metadata. Review/freeze that metadata and the exact settings before an authorized experiment. Body/header model mismatch or an applied effort different from the requested one is an error, not an accepted substitution. See [response headers](https://docs.aiand.com/reference/response-headers/).

## Stage prompts (IDEA-081)

The routing file is `AIandRouting.v2`. Each model gets the core assessor prompt (`config/intelligence/prompts/assessor.v2.txt`) followed by a blank line and its stage's Markdown addendum from `config/intelligence/prompts/routing/`:

| Stage | Model(s) | Addendum |
|---|---|---|
| Routine first pass | GLM-5.3 low | `routine.md`: scan every excerpt for adverse events, prefer `STATEMENT:` when unsure, at most three tools, short JSON reply |
| Review (OpenAI, then external) | GPT-6.1 Sol medium; Kimi K3 high; GLM-5.3 high | `review.md`: independent re-read of the original evidence (it never sees the first pass), settle actor, timing, negation and attribution, tools only for listed gaps |

The routing file pins each addendum by name and SHA-256 (`prompt` on each model entry, `openai_prompt` for Sol). The runtime refuses to start on a missing file, a hash mismatch or a name with a path. Each stage records the composed prompt's hash, so the trace says exactly what each model was sent. The addenda add guidance only; the core prompt comes first and wins any conflict. To change a prompt: edit the `.md`, update its hash in the routing file, and ship it in a new release (the files are release files). A `v1` routing file still works and sends every stage the core prompt only.

## Credentials

Add `LARP_AIAND_API_KEY` to the existing runtime **Secrets Manager JSON**. `LARP_MODEL_API_KEY` is optional for Sol: without it, all model work is external. The service loads these explicitly; it does not inherit keys from an `.env` file. Never put actual keys in this repo, command arguments, routing JSON or logs. Existing signer/audit secrets still refuse loading on the coordinator.

## Shared OpenAI allocation

Use one primary-host ledger for the entire development, activation and scored window, independent of wallets/run IDs. Before the first experiment, explicitly initialize it with **all prior allocated OpenAI spend** deducted. The parent directory must already be private (no group/other mode bits) and owned and writable by the runtime user; the ledger code refuses any other parent directory (#93). Run the command as the runtime user:

```sh
python -m larp.intelligence.model_budget init \
  --path /var/lib/larp-runtime/model-budget/openai-budget.sqlite \
  --account larp-openai-2026 \
  --initial-spent-micro-usd <PRIOR_OPENAI_SPEND_MICRO_USD>
```

`<PRIOR_OPENAI_SPEND_MICRO_USD>` is a placeholder, never a guess: the known prior spend in micro-USD (US$1 = 1 000 000). The exact host steps for the Gate A shadow trial are in "Host steps" below. Initialization refuses to overwrite a ledger. Runtime requires a pre-existing private file and refuses account/limit mismatch or missing/corrupt storage. Check state with the same command using `status` and omitting the initial-spend argument.

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
  "model_budget_root": "/var/lib/larp-runtime/model-budget"
}
```

A complete example is `config/runtime/runtime.aiand-shadow.example.json`: `runtime.example.json` with only these keys changed (and no `expiry_grace_ms`, which only service execution reads). Model request/reply bytes, per-stage results and tool results are written to `<market_artifact_root>/model` (private, inside the unit's state directory), because the runtime opens the evidence root read-only on the host; evidence is still read from the shared store.

This fragment supplements all existing driver fields and the pinned runtime release configuration. The example is not installed or activated automatically. `execution: service` and scored `mode: live` refuse experimental routing. Existing intelligence live values, rights, source, release and host prerequisites still apply.

## Assessment and failure behavior

Every stage uses original saved filing evidence and the real verifier. The routine stage has half the assessment time and at most three tools; review/fallback can use only the remaining common time and six-tool allowance. At most four stages mean at most ten model steps including finishes. Class-item candidates, event interpretation, incomplete/conflicting evidence, verifier failure and seeded clean-case audits request stronger review.

If a required reviewer fails, or accepted findings disagree, the result abstains/is unavailable; it cannot inherit a clean thesis from the routine stage. If AIand's difficult primary fails, only the declared secondary is attempted within the same limits. Full request/reply bytes, whitelisted model/effort headers, actual component identity and intermediate result artifact references survive in the aggregate trace. No credential header is recorded.

The primary capability this PR validates is synthetic component behavior. Provider access, real extraction quality, omission rates, latency, hosted permissions, rights/audit retention terms and production service declaration still need independent evidence before adoption. See [IDEA-057 AR1–AR8](../ledger/IDEA-057.md).

## Prepare the routed configuration without manual runtime edits (SG-8)

The [Gate A preparation command](GATE_A.md#assemble-inputs-before-spending) now
accepts `--model-routing` together with `--model-routing-sha256`. Review the public
example's exact model IDs, efforts, catalog snapshot, audit seed and account before
using it. Set `LARP_MODEL_ROUTING_SHA256` to that reviewed file's SHA256 in the local
terminal. Other variables and inputs below have the same meanings as in Gate A:

```sh
python tools/deploy/prepare_shadow.py prepare \
  --terraform-output deploy/activation/tf-output.json \
  --profile deploy/activation/profile/rehearsal-live.json \
  --capture "$LARP_CAPTURE_ROOT/gate-a-inputs.json" \
  --run-id larp-dev-model-shadow-20261017 --build-id "$LARP_BUILD_ID" \
  --rds-ca-sha256 "$LARP_RDS_CA_SHA256" \
  --sec-contact "$LARP_SEC_USER_AGENT" \
  --balance-rpc-config deploy/activation/balance-rpc/selected-providers.json \
  --model-routing config/intelligence/aiand-routing.example.json \
  --model-routing-sha256 "$LARP_MODEL_ROUTING_SHA256" \
  --out deploy/activation/gate-a-model-prepared
```

Use a fresh capture and new output directory. The command copies exact reviewed
bytes to `model-routing.json`, pins them in `runtime.json` and the preparation
report, selects `aiand_routed`, and keeps dev-shadow settings. A missing or wrong
hash, unsupported model/effort or invalid catalog refuses before any package is
written. Omitting both flags retains deterministic preparation.

The report's `model_routing.checks` remain `NOT_RUN`: preparation cannot prove
credentials, provider identity, budget initialization or trial evaluation.
`gate_a_check` verifies the routed package and pins offline; `local_ready` does
not establish those host/trial requirements. It never opens a budget ledger or
constructs a provider. Install `model-routing.json` root-owned `0644` at
`/etc/larp/model-routing.json` with the other prepared files, before binding the
release manifest. Continue the host steps below for actual credentials, prior
spend, ledger initialization, provider checks and trial evidence. When using
this preparation path, host steps 4–5 are already assembled: install and verify
those exact files rather than editing the prepared runtime afterward.

## Host steps for the Gate A shadow trial (2026-10-16)

Decision: IDEA-056 MR-06 (2026-10-16). Pre-registered measures, bars and kill criteria: [IDEA-057](../ledger/IDEA-057.md) "Shadow trial on the Gate A deploy". Yao Zhu runs these steps on the `primary` host and in Yao Zhu's own terminal; nobody pastes a key into a chat, commit or command line.

**Before starting.** The release on the host must contain this integration (merged into `codex/system-testing-20261012`) and the Gate A assembly (PR #87, not merged as of 2026-10-16). Steps 4–6 change `/etc/larp/runtime.json`, so do them before binding `/etc/larp/release.json` (DEPLOYMENT_DAY step 7). If `release.json` is already bound, binding refuses to replace it: move the old file aside, record that as a version event, and bind again.

1. **Runtime secret (Mac terminal).** `AWS_PROFILE=larp bash tools/deploy/put_service_secrets.sh --name larp-dev --only runtime`. Every run replaces the whole secret value, so re-enter the wallet address and both Binance keys. Then enter `LARP_AIAND_API_KEY` at its hidden prompt, and `LARP_MODEL_API_KEY` (OpenAI) at its own; press Enter at that prompt for an AIand-only trial. Record the printed version ID. Only key names are printed.
2. **Provider check, part 1 (P0, open).** On `primary`, list the account's AIand catalog without putting the key on a command line:
   ```sh
   read -rs AIAND_KEY && printf 'Authorization: Bearer %s\n' "$AIAND_KEY" \
     | curl -sS --fail -H @- https://api.aiand.com/v1/models > /tmp/aiand-models.json; unset AIAND_KEY
   sha256sum /tmp/aiand-models.json
   ```
   Check that `moonshotai/kimi-k3` and `zai-org/glm-5.3` are listed with `reasoning_efforts` containing `low` (GLM routine) and `high` (both reviewers). Record the date and the hash in IDEA-057 P0. If either is missing, do not start the trial.
3. **Private budget directory and ledger.**
   ```sh
   sudo install -d -m 0700 -o larp-runtime -g larp-runtime /var/lib/larp-runtime /var/lib/larp-runtime/model-budget
   cd /opt/larp/current && sudo -u larp-runtime .venv/bin/python -m larp.intelligence.model_budget init \
     --path /var/lib/larp-runtime/model-budget/openai-budget.sqlite --account larp-openai-2026 \
     --initial-spent-micro-usd <PRIOR_OPENAI_SPEND_MICRO_USD>
   ```
   ⚠ **PLACEHOLDER: `<PRIOR_OPENAI_SPEND_MICRO_USD>` must be the actual prior spend against the $50 OpenAI allocation, which Yao Zhu supplies (US$1 = 1 000 000). Never guess it and never use 0 unless the spend really is zero.** The directory must be owned by `larp-runtime` with mode `0700`, and the ledger refuses anything else. Run `init` as `larp-runtime`: run as root, it refuses because the directory is not root's. The printed snapshot is the trial's starting `charged_micro_usd`; record it in IDEA-057 P1.
4. **Pinned routing file.** Install the reviewed routing file root-owned and read-only: `sudo install -m 0644 -o root -g root config/intelligence/aiand-routing.example.json /etc/larp/model-routing.json`. Then run `sha256sum /etc/larp/model-routing.json`; the unchanged v2 example (IDEA-081) is `d6847c2bf96d0085b7e6176fdcff5480c1bc290c691b998bbb651cb9ef501fa7`; it needs a release that contains IDEA-081 (the stage prompt files). On an older release such as `bb46234`, use the v1 example from that release instead (`7d80ae163e4e…`). Record the hash in IDEA-057 P2.
5. **Runtime config.** In the `driver` block of `/etc/larp/runtime.json` (as assembled for Gate A), set exactly:
   `"assessor": "aiand_routed"`, `"execution": "shadow"`, `"model_routing_file": "/etc/larp/model-routing.json"`, `"model_routing_sha256": "<hash from step 4>"`, `"model_budget_root": "/var/lib/larp-runtime/model-budget"`. Keep `"mode": "dev"`. `config/runtime/runtime.aiand-shadow.example.json` shows the shape. Any other combination is refused at start: `execution: service` or `mode: live` with `aiand_routed` gives exit 4.
6. **Bind and check routes.** Bind `/etc/larp/release.json` as in DEPLOYMENT_DAY step 7. Then run the route check (architecture-deployment.md "Approved network destinations"). With `aiand_routed` it also expects `api.aiand.com:443` and `api.openai.com:443` from `larp-runtime`. Keep the `RouteCheck.v1` report.
7. **Start and verify the first routed assessment.** Start `larp-runtime`. On the first assessment, check the following:
   - the journal's round has an assessment with `routing.stages`, not `ASSESSMENT_UNAVAILABLE`;
   - each stage's step responses in that assessment's `model_io` carry `provider_metadata` with `x-model` and `x-reasoning-effort` equal to the requested model and effort (P0 part 2). The exact request/reply bytes are in `/var/lib/larp-runtime/market/model/`, addressed by the `request_payload_artifact` / `raw_response_artifact` hashes. The adapter refuses a mismatch, so an accepted stage already matched;
   - `model_budget status` (below) still matches the ledger.

   Record the first assessment's ID and the trial start time (UTC) in IDEA-057.
8. **Daily, until the trial ends (≤ 2026-10-21).**
   - Snapshot: `cd /opt/larp/current && sudo -u larp-runtime .venv/bin/python -m larp.intelligence.model_budget status --path /var/lib/larp-runtime/model-budget/openai-budget.sqlite --account larp-openai-2026`.
   - Ledger backup (consistent copy while the runtime runs):
     ```sh
     cd /opt/larp/current && sudo -u larp-runtime .venv/bin/python -c 'import sqlite3, sys, time
     src = sqlite3.connect("file:" + sys.argv[1] + "?mode=ro", uri=True)
     dst = sqlite3.connect(sys.argv[2]); src.backup(dst); dst.close(); src.close()' \
       /var/lib/larp-runtime/model-budget/openai-budget.sqlite \
       /var/lib/larp-runtime/model-budget/backup-$(date -u +%Y%m%dT%H%MZ).sqlite
     ```
     Copy the backup off the host to private storage. Never restore a backup over a ledger that has newer charges: the runtime would re-admit spend already used. On a host migration, stop `larp-runtime` first, then carry the live file.
   - Check the kill criteria K1–K4 in IDEA-057. Stopping OpenAI use means re-running step 1 without `LARP_MODEL_API_KEY`, then restarting `larp-runtime`. Reverting means setting `"assessor": "deterministic"`, re-pinning the config and re-binding `release.json` (a version event).
