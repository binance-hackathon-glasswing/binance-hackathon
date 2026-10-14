# Deployment day: first hosted run (Gate A)

Prepared 2026-10-15 SGT (Claude for Yao Zhu, [IDEA-051](../ledger/IDEA-051.md)). This is the order of work once the open reviews and final tests pass. The detail behind each step is in [AWS_RUNBOOK.md](AWS_RUNBOOK.md) and [runbook.md](runbook.md); this page says what is ready, what each person brings, and what still blocks.

## What this deployment can and cannot do

- **It can run in shadow** (`execution: "shadow"`): real market data, real decisions, and real round logs uploaded to ai-seeds from the dev wallet. Every planned order ends `NOT_SUBMITTED`. This is **Gate A** in [DEPLOYMENT_BUILD.md](DEPLOYMENT_BUILD.md), which was planned for Oct 14.
- **It cannot trade.** The Executor accepts only fake capability bundles, and the signer refuses every swap until the verified swap decoder exists (Isaac, GAP-29; #33). `larp-execution` exits 2 `NOT_INTEGRATED` at that gate. Signed trades on the dev wallet are **Gate B** (planned Oct 19–20), and the signed rehearsal starts Oct 21 (GAP-04, D-DN-02).
- **Shadow rounds are real logs.** Every run with the dev wallet's ai-seeds credentials uploads logs the auditors see. Only committed, manifested code may run with them, and test rounds are marked (never-do #13, F-103).

## Status at 2026-10-14 16:50 UTC

| Item | State | Who |
|---|---|---|
| Core AWS stack (VPC, RDS `larp-dev`, buckets, KMS, alarms, secret metadata) | **Applied**, and in sync with `0820b0d`. The credit budget `larp-dev-credit` was added 2026-10-14 ~17:10 UTC; `terraform plan` now shows no changes | — |
| Alarm email subscription | **Pending confirmation**: click the link in AWS's email | Yao Zhu |
| Service secrets `larp-dev/runtime`, `larp-dev/uploader` | **Empty** (0 versions) | Yao Zhu, step 2 |
| Hosts `primary`, `signer` | **Off** (`host_ids = {}`) | needs a spend OK, step 3 |
| Database tables and service roles | **Not migrated** | step 6 |
| Session Manager plugin on the Mac | **Not installed** (needed for SSM shells and the database port-forward) | Yao Zhu |
| Release bundle | CI builds it on every push; take it from the **final** merged head | step 4 |
| Candidate AMI | `ami-0c82c1a90be4dccc1` (AL2023 x86_64, released 2026-10-14); pin it after a look at its release notes | Yao Zhu |
| How to reach `signer` | **Undecided** (AWS_RUNBOOK step 5). Not needed for a shadow run | team |

## What each person brings (never into a chat, a commit or a shared doc)

| Input | Where it goes | How |
|---|---|---|
| Dev wallet **public** address | every host config; both secrets | `render_host_configs.py --wallet`; `put_service_secrets.sh` prompt |
| Binance Web3 API key and secret | `larp-dev/runtime` | `put_service_secrets.sh` (hidden prompt) |
| ai-seeds `AI_SEEDS_SECRET` | `larp-dev/uploader` | `put_service_secrets.sh` (hidden prompt) |
| Wallet private key | the file `/etc/larp/signer/wallet.key` (root, `0600`) **on the signer host only**. Not Secrets Manager, not the Mac's repo | at Gate B, through the signer access route once chosen |
| A real SEC contact for `LARP_SEC_USER_AGENT` | `/etc/larp/evidence.env` on `primary` | by hand; never a placeholder |

## Inputs the shadow run still needs (blocking Gate A)

A `dev` run refuses to start without each of these. None is a deployment step: each needs an owner's work and a pushed commit first.

1. **LIVE strategy profile.** `build_live_profiles` needs a measured `QuoteCostSummary.v1`: per-symbol spread, impact, fee, approve and swap gas, slippage and quote TTL from real Web3 quotes, plus the BNB price. **No tool produces it yet:** `tools/probe_quote.py` measures round trips but not this summary. Owner: Isaac (I1), with Keith (B6 values). See `config/strategy/LIVE.md`.
2. **Session calendar** (`USRegularSessions.v1`) for the run window, with its hash. Owner: Keith.
3. **Issuers map** (issuer ID → token and the market's `underlying_id`), currently `{}`. Real issuer IDs can't yet pass the evidence contract (#25). Owner: Yao Zhu / Keith.
4. **Evidence service live settings:** every `parameters.*.live` in `config/intelligence/intelligence.v1.json` (11 nulls) with provenance, plus the source terms hashes. Until then `larp-evidence` exits 4. Owner: Yao Zhu.
5. **Initial state file** (`PortfolioState.v1`): the dev wallet's attested starting balances, pinned by SHA-256. Whether the wallet holds any BNB for the first gas is still open (Q-03). Owner: team, from a balance read.
6. **Driver values:** `cadence_ms` and `day_roll_window_ms` (team, IDEA-050 "Still open").

## Order of work

1. **Reviews in.** Merge the open PRs (B #65, D follow-up #69, WR leftovers #71 and any others) and wait for green CI on the final head of `codex/system-testing-20261012`. Note that head's SHA: it is the build.
2. **Secrets (Yao Zhu, in your own terminal):**
   ```bash
   aws login --profile larp --region ap-southeast-2
   ```
   ```bash
   AWS_PROFILE=larp bash tools/deploy/put_service_secrets.sh --name larp-dev
   ```
   It shows each secret ID and key name, asks before writing, and prints only the new version ID.
3. **Terraform (spend OK first).** Use the refreshing-credentials setup in AWS_RUNBOOK "Log in and run Terraform".
   - **Done 2026-10-14:** the credit budget is applied (IDEA-051).
   - **Then:** in `development.tfvars` set `ami_id`, `enable_hosts = true`, `enable_external_https = true` and `enable_development_ssm = true`. Plan, review, apply. That's about $23/month more, and it starts both hosts.
4. **Bundle.** Download the CI artifact `larp-bundle-x86_64` from the final head's `host-bundle` job. Check that `sha256sum` matches the job summary, record the run ID and hash, and upload both files to `s3://<artifact bucket>/releases/`.
5. **Provision `primary`** through SSM:
   ```bash
   bash provision.sh primary /root/<bundle> --expect-sha256 <CI hash>
   ```
   Then run the IDEA-047 item 3 host checks for `primary`.
6. **Migrations and roles** (D-DN-05). Run them from the Mac through an SSM port-forward via `primary`, with the RDS admin secret. Never during the scored run.
7. **Configs.** Produce the infrastructure values:
   ```bash
   terraform -chdir=deploy/aws output -json > /tmp/tf.json
   ```
   ```bash
   python tools/deploy/render_host_configs.py --terraform-output /tmp/tf.json --wallet 0x<public> --out deploy/activation/development --rds-ca-sha256 <bundle meta rds_ca_sha256>
   ```
   - The renderer lists what is still unset per file. Fill those from the inputs above.
   - Set `driver.execution` to **`"shadow"`** (the example says `"service"`).
   - Copy the files to `/etc/larp` as root-owned files, then build `/etc/larp/release.json` with `preflight --build-output` (#62 item 3: still built on the host).
8. **Run.**
   - Start with `service init` (quarantined), then `service activate --reviewer … --review-ref …`. That's the team's reviewed step.
   - Then start `larp-evidence`, `larp-runtime` and `larp-uploader`, and enable `larp-archive.timer`.
   - Don't start `larp-execution`: it would only exit 2 at the capability gate.
9. **Gate A evidence.**
   - One shadow round logged and ACKed by the real receiver (R-01).
   - Hosted routes from `primary` to Web3, RPC, SEC and ai-seeds (#32, R-07).
   - `chronyc tracking` (R-08).
   - An alarm email received.
   - Record each in IDEA-051 and review Gate A in IDEA-042 before leaving it running.

## After Gate A

- **Gate B:** Isaac lifts the capability gates. Choose the signer access route (Terraform change, IDEA entry, review). Place the key file. Prove signing on the dev wallet with a small trade, then review Gate B.
- **Decisions due:** D-DN-02 (rehearsal shape, Oct 19); D-DN-01/03 before activation. See IDEA-049-D §5.
