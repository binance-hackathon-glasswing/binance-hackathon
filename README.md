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
- `WALLET_PRIVATE_KEY` (or `WALLET_MNEMONIC`, path `m/44'/60'/0'/0/0`): signs transactions locally; its address must equal `AI_SEEDS_ADDRESS`. Only on the one machine that runs the agent.

Then run `python binance_test.py` to check API access from your network (exit code 0 only if the API returns `code == 0`;
optional `BINANCE_RECV_WINDOW`, e.g. `15000`, sends `X-OC-RECV-WINDOW`).

The ai-seeds logging SDK 0.3.0 is not on PyPI: its wheel is vendored in `vendor/ai-seeds-sdk-0.3.0/` (sha256 in its README; the kit's own `SHA256SUMS` is stale) and installed from `requirements.lock`; `manual_push.sh` (for batch files the SDK did not push) is vendored next to it. The whole participant kit is captured in the repo (`docs/official/kit/` verbatim, `docs/skill/reference/participant-kit.md` in detail), so you never need the original kit folder. Demo and example runs upload real logs under the registered wallet, even in quote-only mode, so don't run them with the team's `AI_SEEDS_*` values outside committed code.

### Docs
Challenge rules, our plan (LARP), guardrails and the submitted proposal are in [`docs/`](docs/README.md). Start with `docs/skill/SKILL.md`.

W08's read-only execution capability collector, usage and W04 handoff are in
[`docs/engineering/W08.md`](docs/engineering/W08.md); preregistration and measured blockers are in
[`docs/ledger/EXP-005.md`](docs/ledger/EXP-005.md). No transaction is signed or broadcast by this collector.
