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

Copy `.env.example` to `.env` and fill in the Web3 API key and secret (shared within the team, never committed).
Then run `python binance_test.py` to check API access from your network.

### Docs
Challenge rules, our plan (LARP), guardrails and the submitted proposal are in [`docs/`](docs/README.md). Start with `docs/skill/SKILL.md`.
