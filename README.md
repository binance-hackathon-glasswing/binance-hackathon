# Binance Agentic AI Hackathon
Agentic AI Hackathon where we build an autonomous AI trading agent that operates under real market conditions.

Members
- Song Yao Zhu [Cookiemunchrr](https://github.com/Cookiemunchrr)
- Isaac Choong [isaaaxe](https://github.com/isaaaxe)
- Keegan Gan [Keegan4](https://github.com/Keegan4)
- Keith Chia [wtvlol](https://github.com/wtvlol)


### Setting up
After cloning the project to your local machine, run `conda env create -f environment.yml`
(then `conda activate binance-hackathon`) to set up Python 3.12 and the pinned packages.

Dependencies: `requirements.in` lists the top-level pins; `requirements.lock` is the full pinned set that
`environment.yml` installs. To change a dependency, edit `requirements.in`, install it into a fresh Python 3.12
env, run `pip check`, then regenerate the lock with `pip freeze | sort -f > requirements.lock` (keep the header
comment). A dependency change in anything that trades or logs is a version event.

Copy `.env.example` to `.env` and fill it in (never committed):
- `BINANCE_API_KEY` / `BINANCE_SECRET_KEY`: the Web3 API key and secret from the Binance Web3 Developer Portal, shared within the team. The participant kit's demos call the same values `BN_WEB3_API_KEY` / `BN_WEB3_API_SECRET`.
- `AI_SEEDS_ADDRESS` / `AI_SEEDS_SECRET`: the registered wallet address and the log-upload signing secret the organisers issue for that wallet. The ai-seeds SDK reads these exact names.

Then run `python binance_test.py` to check API access from your network.

The ai-seeds logging SDK is not on PyPI: it ships in the participant kit (`ai-seeds-sdk-0.3.0`). How it gets pinned in this repo is still open (`docs/INCOMPLETE_WORK.md`, GAP-45). Demo and example runs upload real logs under the registered wallet, even in quote-only mode, so don't run them with the team's `AI_SEEDS_*` values outside committed code.

### Docs
Challenge rules, our plan (LARP), guardrails and the submitted proposal are in [`docs/`](docs/README.md). Start with `docs/skill/SKILL.md`.
