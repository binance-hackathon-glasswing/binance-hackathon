# Gate A: prepare and qualify the unsigned runtime (IDEA-058)

Use `codex/system-testing-20261012` (with #84/IDEA-055) plus the reviewed IDEA-058
change, or `main` once that integration branch is promoted. IDEA-050 already
supplies the round driver and `service init` / `activate`; IDEA-054 supplies the
calendar.
Gate A is hosted shadow operation, with real data and official test-round logs.
The preparation tool below never enables execution, signs, activates a run, reads
AWS secrets, provisions resources or uploads logs.

## Inputs and responsibility

| Input | Owner / source |
|---|---|
| Reviewed `REHEARSAL` `StrategyProfile.v1`, mode `LIVE` | User's concurrent cost-summary/profile tool; measured `QuoteCostSummary.v1`, never fixture values |
| Current metadata and dev-wallet balances | Keegan/Isaac; capture command below (no signing) |
| Public wallet address and SEC contact name/email | Team/Yao Zhu, local deployment input |
| Terraform outputs and bundle CA hash | Yao Zhu's AWS environment; no values in Git |
| Exact pushed CI bundle commit | Keegan; bundle and CI manifest must refer to that same commit |
| Terms bytes | Yao Zhu; retained outside Git, copied to the host's content-addressed artifact store |
| Balance RPC: HTTPS URL with `finalized` support and its source ID (IDEA-055) | Isaac (#92); pass both to `capture` and `prepare`, or neither |

User decision, 2026-10-16: for unsigned development use explicit `shadow`
evidence parameters equal to the existing bounded defaults, a 900,000 ms cadence
and a 300,000 ms UTC day-roll window. `live` parameters remain unset. The runtime
refuses `shadow` parameters in service execution or final/live mode. The evidence
unit selects shadow through `LARP_EVIDENCE_CONFIG_MODE=shadow` and verifies the
matching `runtime.json` against the release manifest before starting ingestion.
The default evidence mode stays `live` unless explicitly selected. The environment
file may select only `live` or `shadow`, and `development` is refused on a release
host (IDEA-058 GA13a).

## Assemble inputs before spending

Run these commands from the clean, pushed checkout on the AWS-connected machine.
Keep the profile and outputs in ignored `deploy/activation/` storage. Retain raw
captures outside the repo. Use a new output directory for each frozen build.

```sh
# Read-only: reads just Web3 API credentials; no wallet key or ai-seeds secret needed.
# Supply the public address locally with --wallet or AI_SEEDS_ADDRESS.
python tools/deploy/prepare_shadow.py capture \
  --env-file .env --wallet "$AI_SEEDS_ADDRESS" \
  --artifact-root "$LARP_CAPTURE_ROOT/web3" \
  --balance-rpc-config deploy/activation/balance-rpc/selected-providers.json \
  --output "$LARP_CAPTURE_ROOT/gate-a-inputs.json"

terraform -chdir=deploy/aws output -json > deploy/activation/tf-output.json

# Capture within five minutes of preparation. $LARP_BUILD_ID is the CI bundle SHA.
python tools/deploy/prepare_shadow.py prepare \
  --terraform-output deploy/activation/tf-output.json \
  --profile deploy/activation/profile/rehearsal-live.json \
  --capture "$LARP_CAPTURE_ROOT/gate-a-inputs.json" \
  --run-id larp-dev-shadow-20261016 --build-id "$LARP_BUILD_ID" \
  --rds-ca-sha256 "$LARP_RDS_CA_SHA256" \
  --sec-contact "$LARP_SEC_USER_AGENT" \
  --balance-rpc-config deploy/activation/balance-rpc/selected-providers.json \
  --out deploy/activation/gate-a-prepared
```

The run ID is an operator-selected identifier; change the dated example if
preparing on another date. Create `deploy/activation/` before redirecting the
Terraform output if it does not exist. Set all shell variables explicitly in the
local terminal; none is a request to put a secret in chat.

For the documented GLM routine / ChatGPT difficult-review shadow trial, preparation
also accepts `--model-routing <reviewed public JSON>` and
`--model-routing-sha256 <reviewed SHA256>` together. These are flagged input
placeholders; use actual reviewed values. The complete command, model roles,
credential names and shared-budget steps are in
[AIAND_MODEL_ROUTING.md](AIAND_MODEL_ROUTING.md#prepare-the-routed-configuration-without-manual-runtime-edits-sg-8).
The generated package includes pinned `model-routing.json`; install it with the
other files before manifest binding. Model/provider/ledger checks stay `NOT_RUN`.

The tool validates all five contract/chain/token identities and binds their
observed market tickers to the SEC issuer IDs. It grants no share-class, ratio or
basis verification. It preserves exact BNB wei and floors USDT to ledger
micro-units, retaining raw balances in the capture. A stock holding is refused:
initializing existing positions needs reviewed cost-basis/history, not a guessed
zero basis. The Web3 balance snapshot has no block identity. With
`--balance-rpc-url`, the capture also reads the finalized chain balances and
nonces through the manifested RPC (IDEA-058 GA11). Capture and preparation both
refuse while a wallet transaction is pending or not finalized, and when the
finalized balances differ from the Web3 snapshot. If either happens, wait and
capture again. Preparation with `--balance-rpc-url` refuses a capture made without
it, or with a different `--balance-rpc-source-id` (GA12). Without the RPC, the
report lists `BALANCE_RPC` and `CHAIN_BALANCE_CAPTURE`.

`--balance-rpc-config` names the private, git-ignored provider file
(`{"balance_rpc_providers": [{"url": …, "source_id": …}, …]}`, primary first,
up to four; the format `tools/deploy/qualify_balance_rpc.py` reads). `capture`
reads the chain through the first provider; `prepare` writes the whole list, in
order, to `driver.balance_rpc_providers`, so the runtime fails over to the backup
(IDEA-055 PR 5). The single `--balance-rpc-url` + `--balance-rpc-source-id` pair
still works for one provider; naming both forms is refused. A capture made
through any listed provider is accepted (IDEA-066 PC-RPC01, GA15). The URLs can
carry API keys: keep the file outside Git and never paste it into a chat or issue.

Outputs are `runtime.json`, `uploader.json`, `operations.json`, the profile,
calendar, initial state, pinned capture and a preparation report. `evidence.env`
is emitted only with a valid supplied SEC contact. No execution/signer config is
emitted. The preparation report explicitly distinguishes assembled inputs,
missing source/contact prerequisites and NOT RUN host checks; it never passes a
gate. Archive settings are bounded development values: 82-day retention, daily
backups, three delivery attempts per task with 60-second retry, 64 MiB per archive.
Record any measured capacity shortfall before changing them.

Before copying anything to the host:

1. Run `python -m larp.sources.live terms --write-register` from pushed code with
   the real SEC User-Agent and an absolute `LARP_ARTIFACT_ROOT` outside Git.
   This retains exact terms bytes and updates successful capture hashes. Commit
   and push the register change, then use a bundle from that updated commit.
2. Transfer the retained terms artifacts to `/var/lib/larp-evidence/artifacts/`
   under their original hashes and evidence-user/group permissions. Existing
   non-SEC hashes also require the original bytes; hashes alone cannot start the
   service. A denied/failed terms fetch remains a blocker.
3. Review the preparation report. Install files into the paths named by the
   runtime config (`/etc/larp/` by default), root-owned; `evidence.env` contains
   public settings only. Preparation writes every file as `0600`, but both
   `larp-runtime` and `larp-evidence` read `runtime.json`, so set its mode on
   install, e.g. `install -m 0644 -o root -g root runtime.json /etc/larp/runtime.json`
   (it holds secret IDs and endpoints, no secret values). Copying with `cp -p`,
   `scp -p` or `install` without `-m` keeps `0600`, and the evidence unit then
   exits 4 with "Cannot read the shadow runtime configuration". Bind those exact bytes to CI's release manifest using
   `preflight --bind` (AWS_RUNBOOK step 7); bind `operations.json` with `--config`
   as well as the runtime and service configs.

## Hosted qualification (Yao Zhu + Keegan; not performed by preparation)

Before transfer, inspect the frozen package using the downloaded CI bundle's
unbound manifest, release directory and CA, plus the retained terms store:

```sh
python -m larp.runtime.gate_a_check \
  --prepared deploy/activation/gate-a-prepared \
  --ci-manifest "$LARP_BUNDLE_ROOT/release-manifest.json" \
  --release-root "$LARP_BUNDLE_ROOT/release" \
  --rds-ca "$LARP_BUNDLE_ROOT/rds-ca.pem" \
  --artifact-root "$LARP_CAPTURE_ROOT/terms"
```

This read-only command checks the exact package hashes, run/build/wallet
agreement, unsigned settings, profile/calendar/state pins, real service
configuration validators, CI release bytes and retained terms artifacts. It
parses the generated public `evidence.env` without running it. The supplied
artifact root must contain `artifacts/<hash-prefix>/<hash>` as produced by the
terms capture; the host still needs its own installed copy and source preflight.
Only the CA path is mapped to its local bundle copy for configuration validation.
No secrets, network/DB/AWS calls, writes, activation or uploads occur.

Exit **0** and `local_ready: true` mean those local checks passed. Exit **4**
means a failed check or missing prerequisite (`NOT_RUN`). `gate_a_passed` and
`remote_ci_verified` always remain false, and all host checks remain `NOT_RUN`.
Obtain the exact artifact and check its hash against the registered-repo CI
summary separately (#49/#98); local bytes alone cannot establish CI provenance.
Run this command from the checked build's environment; it does not verify the
installed dependency versions or host file permissions. It neither refreshes
the captured wallet balances nor qualifies a real RPC provider. First BNB is
Gate B work and does not prevent this unsigned check. Keep the frozen directory
unchanged; save any stdout report outside it.

The remaining Gate A work and owners are tracked in
[#127](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/127);
this checker is [IDEA-066](../ledger/IDEA-066.md), issue
[#128](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/128).

Follow [AWS_RUNBOOK.md](AWS_RUNBOOK.md) for the concrete reviewed spend/apply,
primary-host provisioning, database migrations and least-privilege IAM/TLS checks.
Signer access and key provisioning are Gate B work; neither blocks an unsigned
primary-host run. The existing stack may start both hosts: review the saved plan
and costs before applying. Do not deploy from the Windows working copy; use the
verified Linux CI release bundle, with its hash and manifest.

1. Run source preflight with `--config-mode shadow`, the real SEC User-Agent and
   the populated external artifact store. Start the evidence service first so
   `evidence.sqlite` exists. Its shadow scope check needs the bound runtime config.
2. Run `service init`, then the reviewed `service activate` with reviewer and
   review reference, using the bound config/manifest (runbook §1.6).
3. Start runtime and uploader, then enable the archive timer. Leave execution
   and signer units stopped. Before Oct 21 the unchanged rehearsal profile can
   HOLD; a logged HOLD is valid shadow evidence, not a trading failure.
4. Record the real receiver's durable per-event/chunk ACK; ingestion over 24 h;
   restart drill; hourly anchoring; role/TLS checks; allowed network routes;
   `chronyc tracking`; an alarm reaching its owner. Record commit, input hashes,
   timestamps and artifacts in IDEA-058/IDEA-042 before claiming Gate A PASS.

See [DEPLOYMENT_BUILD.md](DEPLOYMENT_BUILD.md) for DR-01/07/11/12/13/15/16/18/20.
Gate B remains separate: router/decoder and provider capability proof, signer
version binding/provisioning, first BNB and automatic gas top-up, real approve and
swap, measured profiles/candles, crash/HALT/restore drills and shadow-day replay.
