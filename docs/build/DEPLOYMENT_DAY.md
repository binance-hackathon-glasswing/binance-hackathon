# Deployment day: first hosted run (Gate A)

Prepared 2026-10-15 SGT (Claude for Yao Zhu, [IDEA-051](../ledger/IDEA-051.md)). This is the order of work once the open reviews and final tests pass. The detail behind each step is in [AWS_RUNBOOK.md](AWS_RUNBOOK.md) and [runbook.md](runbook.md); this page says what is ready, what each person brings, and what still blocks.

**2026-10-16 update:** [GATE_A.md](GATE_A.md) is the current assembly procedure
for inputs 2–6 below. IDEA-050's driver/init/activate and #25's issuer fix are
already on main (PR81); IDEA-054 supplies the calendar. IDEA-058 builds on
`codex/system-testing-20261012`, which adds #84's balance check (IDEA-055) and
is not yet promoted to main, so deploy from that branch plus IDEA-058, or from
main after the promotion. IDEA-058 adds strictly
unsigned shadow settings and derives the issuer map/initial state from captured
real responses. The user owns input 1's summary/profile tool; Yao Zhu sets the
public wallet address and SEC contact locally. Missing terms bytes/captures and
host checks remain required. The original descriptions below retain their dated
context; no hosted run or Gate A pass is established by this update.

## What this deployment can and cannot do

- **It can run in shadow** (`execution: "shadow"`): real market data, real decisions, and real round logs uploaded to ai-seeds from the dev wallet. Every planned order ends `NOT_SUBMITTED`. This is **Gate A** in [DEPLOYMENT_BUILD.md](DEPLOYMENT_BUILD.md), which was planned for Oct 14.
- **It cannot trade.** The Executor accepts only fake capability bundles, and the signer refuses every swap until the verified swap decoder exists (Isaac, GAP-29; #33). `larp-execution` exits 2 `NOT_INTEGRATED` at that gate. Signed trades on the dev wallet are **Gate B** (planned Oct 19–20), and the signed rehearsal starts Oct 21 (GAP-04, D-DN-02).
- **Shadow rounds are real logs.** Every run with the dev wallet's ai-seeds credentials uploads logs the auditors see. Only committed, manifested code may run with them, and test rounds are marked (never-do #13, F-103).

## Status at 2026-10-14 16:50 UTC

| Item | State | Who |
|---|---|---|
| Core AWS stack (VPC, RDS `larp-dev`, buckets, KMS, alarms, secret metadata) | **Applied**, and in sync with `0820b0d`. The credit budget `larp-dev-credit` was added 2026-10-14 ~17:10 UTC; `terraform plan` now shows no changes | — |
| Alarm email subscription | Moved off the Apple relay address (which dropped AWS mail) to Yao Zhu's own inbox on 2026-10-14. **Pending confirmation**: click the link in AWS's email. Budget alerts go to the same inbox | Yao Zhu |
| Service secrets `larp-dev/runtime`, `larp-dev/uploader` | **Stored** 2026-10-14 ~17:20 UTC by Yao Zhu with `put_service_secrets.sh` (dev wallet; checked by version metadata only). The final wallet's values replace them at the switch (runbook §5) | — |
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

`larp.runtime.service` refuses to start a `dev` run without each of these (`larp/runtime/service.py`). None of them is a deployment step: each needs an owner's work, review and a pushed commit before it can be used. The owners shown are suggestions from the build allocation.

### 1. LIVE strategy profile (Isaac with Keith)
- **What it is:** the frozen `StrategyProfile.v1` the planner trades by: minimum trade size, slippage and impact caps, quote age, gas floor and top-up size, and the rehearsal and final windows. Most values are computed from measured costs by `build_live_profiles(summary, registry)` (`larp/strategy/profiles.py`; the algebra is in `config/strategy/LIVE.md`). The allocation thresholds are already fixed by IDEA-035/037: 20/80, 25/90, 75%.
- **Why the run refuses:** `service.py` rejects a dev or live run whose profile isn't `mode: "LIVE"`.
- **What's missing:** the input `QuoteCostSummary.v1`. For **each of the five tokens** it needs `samples`, `median_impact_bps`, `spread_bps`, `fee_bps`, `approve_gas_bnb_units`, `swap_gas_bnb_units`, `slippage_bps` and `quote_ttl_seconds`. It also needs `bnb_price_units`, `bnb_decimals`, `observed_at`, `origin: "RECORDED_WEB3"` and a `capture_hash` of the raw responses. These must be measured from real Web3 Open API quotes, never invented. **No tool produces this summary yet:** `tools/probe_quote.py` measures buy/sell round trips but not gas or this shape. The validator also refuses any token whose spread + 2×impact + fee leaves no room under 50 bp.
- **Registry:** the red-flag set `config/intelligence/red_flags.v1.json` (`RedFlagPredicateSet.v1`, 4 predicates) is already in the repo; its hash goes into the profile.
- **Timing:** the rehearsal profile's window opens **Oct 21 00:00 UTC** (new risk until Oct 22, flatten from Oct 23, signing ends Oct 26 14:45 UTC); final is Oct 29 → Nov 11. **A shadow run before Oct 21 can test the hosts and logs, but it plans no buys**, because the planner holds new risk outside the window. Seeing real decisions earlier needs a team decision on a dev-shadow window: a new profile, recorded as a version event.
- **Done when:** the summary and both profiles are committed or hash-pinned (captures can stay out of Git if private), `schema.profile` accepts them, and their hashes go into `runtime.json` and `execution.json`.

### 2. Session calendar (Keith)
- **What it is:** a `USRegularSessions.v1` document: `calendar_id`, `content_hash`, and `sessions` as consecutive `{session_index, open_at, close_at}` in UTC (regular 09:30–16:00 ET sessions, with half days marked as such). The runtime uses it for "which session is it and how many are left", and the strategy uses it to build daily closes.
- **Why the run refuses:** a decision time **outside the calendar** is refused (`SessionCalendar` in `larp/runtime/driver.py`), so it must cover the whole run, from the first shadow day through the end of the final.
- **Done when:** the file is committed with its SHA-256 in `runtime.json` (`driver.session_calendar_sha256`) and built from an official exchange holiday source cited in its provenance.

### 3. Issuers map (Yao Zhu with Isaac and Keegan; blocked by #25)
- **What it is:** `driver.issuers` in `runtime.json`, which maps each issuer ID in `config/intelligence/issuers.v1.json` (e.g. `SEC-CIK-0001045810`) to `{"token": "NVDAB", "underlying_id": …}`. It is currently `{}`, and an empty map is refused.
- **What's blocking it (#25, P1):** the market side calls a stock by its ticker (`NVDA`), while evidence uses the SEC CIK. The evidence check requires them to be equal, so real filings for a token are rejected as `WRONG_ISSUER`, including Class 1 red flags. The code must carry issuer ID and ticker separately before the map can be filled correctly. Separately, `issuers.v1.json` marks every token-to-share mapping as UNVERIFIED (the kit gives no ratio or share class).
- **Done when:** #25 is fixed and tested with real NVDA/CIK identities, and the five entries are filled.

### 4. Evidence service live settings (Yao Zhu)
- **What it is:** `config/intelligence/intelligence.v1.json` has **11 parameters whose `live` value is null**: `initial_backfill_ms`, `max_clock_skew_ms`, `max_source_staleness_ms`, `result_ttl_ms`, `reassess_delay_ms`, `retry_delay_ms`, `job_validity_ms`, `job_max_attempts`, `max_review_attempts`, `max_review_backoff_ms` and `statement_retention_ms`. Each has a `development` value to start from: 30 days of backfill, 5 min clock skew, 2 h staleness, 1 h result TTL, 6 h reassess, 10 min retry, 24 h job validity, 3 attempts, 3 reviews, 48 h backoff and 90 days retention. Live values need a decision and a provenance note.
- **Source terms:** each **enabled** source needs a dated capture of its terms of use (`rights.terms_evidence_sha256` in `config/sources/sources.v1.json`). Five are enabled and none has one: `sec-press`, `fr-bis`, `fr-public-inspection`, `doj-press` and `ec-press`. The EDGAR entry needs one too (GAP-23).
- **Why the run refuses:** `larp-evidence` exits 4 and isn't restarted. The runtime then also refuses, because the evidence store it reads doesn't exist.
- **Also needed:** a real contact for `LARP_SEC_USER_AGENT` in `/etc/larp/evidence.env` (SEC fair access).

### 5. Initial state file (team, from a balance read)
- **What it is:** a `PortfolioState.v1` with the dev wallet's actual starting balances (USDT, BNB, any tokens) and run ID, pinned by SHA-256 in `runtime.json`. `service init` builds the run from it and refuses an unpinned file.
- **First gas (answered 2026-10-16, SKILL.md F-120).** The organisers send USDT only, and say to buy the first BNB in MetaMask, paying that swap's gas in USDT. Gate B reports `FIRST_BNB_REQUIRED` until the wallet holds BNB. Steps, done by the wallet holder in MetaMask: **Isaac** for both wallets (assigned by Yao Zhu, 2026-10-16; Yao Zhu has no MetaMask access):
  1. Before the wallet's first agent trade (dev wallet: before Gate B; final wallet: after funding and before the scored run starts on Oct 29 00:00 UTC, never during it, F-114), open the wallet in MetaMask on BNB Smart Chain.
  2. Swap USDT for BNB, choosing USDT as the network-fee token. **Size (decided by Yao Zhu, 2026-10-16): enough for the whole run's gas, so the agent's top-ups are a backup only: about 4 USDT in total for the dev wallet, about 6 USDT for the final wallet.** Basis: one approve + swap cost about 0.000022–0.000046 BNB in the organisers' tests (F-93), about $0.02–0.035, so about 150 trades cost about $3–5; these sizes give 170–300 trades of headroom, inside IDEA-055 D6's 5 % bound. One or more swaps are allowed per wallet, all before its first agent trade (SKILL.md F-120). No BNB is swapped back to USDT at the end (G-13); leftover BNB is accepted.
  3. Write each swap's tx hash, USDT paid, BNB received and UTC time into the funding notes below. It is not a trade and not an agent round, so it gets no ai-seeds log (confirmed by Yao Zhu, 2026-10-16). [Inference: the daily fill check (F-100) covers bStock fills, not this swap.]
  4. Take the initial balance read after the last manual swap, so the `PortfolioState.v1` above includes the BNB.

  **Funding notes (deployment record).**

  | Wallet | Date (UTC) | Tx hash | USDT paid | BNB received | Note |
  |---|---|---|---|---|---|
  | dev | 2026-10-16, `[TO FILL: Isaac]` time | `[TO FILL: Isaac]` | 2 | `[TO FILL: Isaac]` | Trial swap in MetaMask (reported 2026-10-16). Isaac fills in the details and swaps about 2 USDT more before Gate B, to about 4 USDT in total. |
  | final | — | — | — | — | Isaac, after funding and before Oct 29 00:00 UTC, about 6 USDT in total. |
  Later top-ups are the agent's own logged USDT → BNB rounds (G-13). Still open: whether BNB counts in equity (Q-39).

### 6. Driver values (team decision)
`driver.cadence_ms` (how often a cadence round runs) and `driver.day_roll_window_ms` (how long after UTC midnight the daily risk anchor may roll). They are null in the example and recorded as open in IDEA-050.

Also `driver.balance_rpc_url` and `driver.balance_rpc_source_id`: the manifested BSC RPC for the chain-balance check ([IDEA-055](../ledger/IDEA-055.md), #36). They are account-specific, null in the example, and required for a `dev` or `live` start. The interval and maximum age are set in the example (10 and 30 minutes). `driver.price_jump_check_bps` (3000 in the example, required with them) is the price-jump guard's threshold: a held symbol whose mark moves at least 30 % between rounds is not traded, and the loss stops wait, until a balance check confirms the chain (IDEA-055 PR 4).

## Order of work

1. **Reviews in.** Merge the open PRs (B #65, D follow-up #69, WR leftovers #71 and any others) and wait for green CI on the final head of `codex/system-testing-20261012`. Note that head's SHA: it is the build.
2. **Secrets (Yao Zhu, in your own terminal). Done 2026-10-14 for the dev wallet; rerun only to change a value:**
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
4. **Bundle.** Download the CI artifact `larp-bundle-x86_64` from the final head's `host-bundle` job. Check that `sha256sum` of the bundle and of its `.release.json` manifest match the job summary, record the run ID and both hashes, and upload the bundle and its `.sha256` to `s3://<artifact bucket>/releases/`. The bundle carries the same manifest as `release-manifest.json`.
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
   - Copy the files to `/etc/larp` as root-owned files, then bind CI's manifest (#62 item 3): `python -m larp.runtime.preflight --bind /opt/larp/current/release-manifest.json --root /opt/larp/current --output /etc/larp/release.json --registration-evidence <file> --runtime-config /etc/larp/runtime.json --service-config NAME=/etc/larp/NAME.json`. It only verifies the installed release against CI's manifest and adds the registration evidence and config hashes; nothing is rebuilt on the host.
8. **Run.**
   - Start with `service init` (quarantined), then `service activate --reviewer … --review-ref …`. That's the team's reviewed step.
   - Then start `larp-evidence`, `larp-runtime` and `larp-uploader`, and enable `larp-archive.timer`.
   - Don't start `larp-execution`: it would only exit 2 at the capability gate.
9. **Gate A evidence.**
   - One shadow round logged and ACKed by the real receiver (R-01).
   - Hosted routes from `primary` to Web3, RPC, SEC and ai-seeds (#32, R-07): `python -m larp.runtime.routes --role primary …` on `primary`, and `--role signer` on the signer once its access route exists; commands and the approved list are in [architecture-deployment.md](architecture-deployment.md) "Approved network destinations" (IDEA-062). Keep both `RouteCheck.v1` reports.
   - `chronyc tracking` (R-08).
   - An alarm email received.
   - Record each in IDEA-051 and review Gate A in IDEA-042 before leaving it running.

## After Gate A

- **Gate B:** Isaac lifts the capability gates. Choose the signer access route (Terraform change, IDEA entry, review). Place the key file. Prove signing on the dev wallet with a small trade, then review Gate B.
- **Decisions due:** D-DN-02 (rehearsal shape, Oct 19); D-DN-01/03 before activation. See IDEA-049-D §5.
