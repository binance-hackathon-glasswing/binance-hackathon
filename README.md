# Binance Agentic AI Hackathon
Agentic AI Hackathon where we build an autonomous AI trading agent that operates under real market conditions.

Members
- Song Yao Zhu [Cookiemunchrr](https://github.com/Cookiemunchrr)
- Isaac Choong [isaaaxe](https://github.com/isaaaxe)
- Keegan Gan [Keegan4](https://github.com/Keegan4)
- Keith Chia [wtvlol](https://github.com/wtvlol)


### Setting up
After cloning the project to your local machine, run `conda env create -f environment.yml` from the repo root
(then `conda activate binance-hackathon`) to set up Python 3.12 and the pinned packages, including the vendored
ai-seeds SDK.

Dependencies: `requirements.in` lists the top-level pins; `requirements.lock` is the full pinned set that
`environment.yml` installs. To change a dependency, edit `requirements.in`, install it into a fresh Python 3.12
env, run `pip check`, then regenerate the lock with `pip freeze | sort -f > requirements.lock` (keep the header
comment). `pip freeze` writes the ai-seeds SDK as an absolute `file://` URL: replace that line with the relative path
`./vendor/ai-seeds-sdk-0.3.0/ai_seeds_sdk-0.3.0-py3-none-any.whl` (relative paths resolve against the directory pip runs
in, so install from the repo root). A dependency change in anything that trades or logs is a version event.

Copy `.env.example` to `.env` and fill it in (never committed):
- `BINANCE_API_KEY` / `BINANCE_SECRET_KEY`: the Web3 API key and secret from the Binance Web3 Developer Portal, shared within the team. The participant kit's demos call the same values `BN_WEB3_API_KEY` / `BN_WEB3_API_SECRET`.
- `AI_SEEDS_ADDRESS` / `AI_SEEDS_SECRET`: the registered wallet address and the log-upload signing secret the organisers issue for that wallet. The ai-seeds SDK reads these exact names. Leave the optional `AI_SEEDS_URL` override unset.
- `WALLET_PRIVATE_KEY` (or `WALLET_MNEMONIC`, path `m/44'/60'/0'/0/0`): signs transactions locally; its address must equal `AI_SEEDS_ADDRESS`. Provision only to the isolated signer, never to the coordinator, evidence workers or uploader.

Then run `python binance_test.py` to check API access from your network (exit code 0 only if the API returns `code == 0`;
optional `BINANCE_RECV_WINDOW`, e.g. `15000`, sends `X-OC-RECV-WINDOW`).

The ai-seeds logging SDK 0.3.0 is not on PyPI: its wheel is vendored in `vendor/ai-seeds-sdk-0.3.0/` (sha256 in its README; the kit's own `SHA256SUMS` is stale) and installed from `requirements.lock`; `manual_push.sh` (for batch files the SDK did not push) is vendored next to it. The whole participant kit is captured in the repo (`docs/official/kit/` verbatim, `docs/skill/reference/participant-kit.md` in detail), so you never need the original kit folder. Demo and example runs upload real logs under the registered wallet, even in quote-only mode, so don't run them with the team's `AI_SEEDS_*` values outside committed code.

### Docs
Challenge rules, our plan (LARP), guardrails and the submitted proposal are in [`docs/`](docs/README.md). Start with `docs/skill/SKILL.md`.

### Offline engine foundation
The `larp` package starts the IDEA-021 policy boundary; it cannot trade. See
[`IDEA-023` (owner-branch record)](docs/ledger/IDEA-023-offline-policy-boundary.md) for its scope, verification and remaining work.
After committing and pushing decision-related changes as required by `AGENTS.md`,
run `python -m unittest tests.test_contracts -v` from the repository root for the
original 13 standard-library tests. The complete runtime suite needs
`deploy/requirements-test.lock`, disposable PostgreSQL and Linux worker isolation;
it needs no `.env` or real credentials. Pytest collects under `tests/`, excluding
credential-dependent standalone probes.

The runtime/audit branch adds real PostgreSQL transactions, durable scheduler and
audit outboxes, isolated workers, backup/restore and a restartable synthetic fixture.
Use the [runtime operations guide](docs/build/runtime-operations.md) for exact setup,
test and demo commands, deployment boundaries and missing settings. Results and the
acceptance matrix are in [IDEA-028](docs/ledger/IDEA-028.md). The default is offline;
this increment cannot activate live trading. The lightweight coordinator image uses
`deploy/requirements-runtime.lock`; the full research lock was also installed and
checked on Linux Python 3.12.15 and Windows Python 3.12.14.

The [architecture deployment guide](docs/build/architecture-deployment.md) lists
every remaining provisioning/integration step and owner. Terraform definitions are
in `deploy/bootstrap/` and `deploy/aws/`; the optional archive host uses
`deploy/requirements-aws.lock` and `deploy/systemd/larp-archive.timer`. These provide
durable S3 backup/hourly anchor delivery, monitoring and release checks. No AWS
resources are provisioned, no destinations are selected, and signing remains blocked.
W08's read-only execution capability collector, usage and W04 handoff are in
[`docs/engineering/W08.md`](docs/engineering/W08.md); preregistration and measured blockers are in
[`docs/ledger/EXP-005.md`](docs/ledger/EXP-005.md). No transaction is signed or broadcast by this collector.
W04's execution component and production integration boundaries are in
[`docs/engineering/W04.md`](docs/engineering/W04.md); offline crash/recovery evidence is in
[`docs/ledger/EXP-006.md`](docs/ledger/EXP-006.md). Its supplied ports are fake only; live execution remains disabled.

### Evidence hardening, free sources and integration (IDEA-031)
Branch `codex/evidence-hardening` integrates the evidence, strategy/risk, runtime and execution owner branches and
implements [IDEA-030](docs/ledger/IDEA-030.md)'s corrections: event semantics and signed numeric verification,
statement lifecycle and consumption-time freshness, EvidenceContext.v1 and runtime adapters with configurable
evidence authority (default SHADOW), a free official-source basket (SEC, Federal Register/BIS, DOJ, EC; FTC
disabled) and corrected evaluation. Contracts and commands: [docs/build/evidence-integration-contracts.md](docs/build/evidence-integration-contracts.md);
record and results: [IDEA-031](docs/ledger/IDEA-031.md). Synthetic tests do not establish live readiness or profit.
