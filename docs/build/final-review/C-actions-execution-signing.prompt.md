# Final review C: actions (execution, signing, wallet, chain)

**Assigned to: Isaac** (random draw, 2026-10-14).

You are one of four reviewers running LARP's final pre-deployment review (IDEA-049). LARP is our agent for the Binance Agentic AI Challenge. Your section is **everything that turns an approved intent into an on-chain transaction, and the wallet itself**:
- the Web3 Open API venue (quote, approve, re-quote, gas estimate, broadcast, receipt);
- request signing (HMAC);
- the signer service and key file;
- the signer allow-list;
- nonces, finality and reconciliation;
- gas (BNB) and the first BNB;
- funding;
- the final-wallet switch;
- the execution store and service;
- settlement facts handed to accounting.

**Before anything else, read `docs/build/final-review/00-common-protocol.md` in full. It is part of this prompt.** Then read `AGENTS.md`, and `docs/skill/SKILL.md` §0 (reading contract, never-do list). Follow the protocol's phases exactly:
1. Independent requirements catalogue.
2. Trace and tests.
3. Fix loop.
4. Repeat until a full pass finds nothing new.

Branch `review/final-c-<yyyymmdd>`. Record: `docs/ledger/IDEA-049-C.md`. Catalogue: `docs/build/final-review/C-catalogue.md`.

**No signing or broadcasting of anything real, and no use of any registered wallet key or secret** (protocol §0.6). All chain and venue behaviour is tested against fakes built from the kit's documented shapes. Read-only quote calls are allowed through committed probe tools with an existing Web3 API key, recorded per protocol §0.6.

## Scope inventory (every item must appear in your coverage table)

Where an item is split between sections, you own only the aspect named here.

- **Official page:**
  - F-14 (register a fresh final wallet: the wallet aspect);
  - F-20 ("executes eligible bStocks trades on BNB Smart Chain through Binance Web3 Open APIs");
  - F-22 (your wallets and keys);
  - F-25 (no own capital);
  - F-64 (prohibited in both phases: adding funds, withdrawals, wallet-to-wallet transfers, bridging, unrelated swaps or arbitrary contract calls, manual trading);
  - F-65;
  - F-66 (credential misuse).
- **Kit:**
  - F-91: contract addresses, decimals from the API, native BNB representations;
  - F-92 (credentials and wallet, one agent per wallet);
  - F-93 (gas only in BNB; the USDT → BNB swap that itself needs gas);
  - F-94 (mainnet only, amounts, `code == 0`, HMAC signing, legacy transactions, chain 56);
  - F-95: the market data endpoints and their failure behaviour;
  - F-96 (execution flow: `vendor=LiquidMesh`, slippage, approve the exact amount, spender = re-quote `tx.to`, re-quote after the approve, ~30 s RFQ expiry, the gas limit from `pre-transaction/gas-limit` × 1.2);
  - F-97 (confirmation, nonce derivation, no cancel, revert costs gas, 120 s, rate limits);
  - F-98;
  - F-103 (keys only in env or secret manager; live switch with a per-trade cap; quote-only mode);
  - F-104 (trading channel: Web3 Open API with local signing only; not the custodial wallet, not Binance spot);
  - F-105 (pre-launch checklist, execution aspects);
  - F-107, F-108 (error codes);
  - F-111 (demo behaviours that must not be copied: the trading aspects);
  - F-116 (deposit);
  - K3–K9, K16 in `docs/skill/reference/participant-kit.md`, each checked against the verbatim Guide pages, `web3-open-api.md` and `bstocks-trading-guide.md`.
- **Never-do lines (SKILL.md §0.3):**
  - #1 (humans never sign, approve or submit wallet transactions);
  - #2 (no transaction without a version and a write-ahead decision record, failed ones included: the execution aspect);
  - #3 (no funds added or withdrawn, no transfers, bridges, unrelated swaps or arbitrary calls; never the custodial wallet or spot trading);
  - #4 (token aspect);
  - #7 (keys never in the repo or logs);
  - #12 (an approve is never logged as an order: the execution side).
- **Guardrails:** G-01 (signer allow-list), G-08, G-09 (key and environment separation), G-13 (token hygiene), G-16, G-18 (fencing, at-most-once signing, reconciliation), G-28 (gas floor: the execution side), G-43 (reconciliation: the chain side).
- **Declared proposal** (`docs/proposal/proposal_answers.md`): every sentence about execution, signing, keys, the signer and reconciliation, and the execution parts of "Reproducibility plan".
- **Decided items:**
  - IDEA-035 C1 (automatic USDT → BNB conversion), C7 (final-wallet secret reminder), and the decided execution items in §10.1;
  - IDEA-046 B1/B2 (separate signer host, root-only key file, no internet route);
  - IDEA-047 scope and design as adopted (signing requests through the database; swaps refused until a verified decoder exists);
  - plan.md D-items on execution as decided.
- **Readiness and acceptance:** DR-02 (live venue adapter), DR-03 (isolated signer; refuses unless the key address = `AI_SEEDS_ADDRESS`; nonce and finality evidence that does not rely on the kit's history), DR-04 (execution service and crash recovery at each step), DR-05 (settlement facts: the execution side), DR-06 (first BNB and top-ups: the execution side), DR-17 (final-wallet switch: the wallet side); AT items about execution, nonce, finality and the signer (`docs/ledger/IDEA-021.md`).
- **Backlog items to resolve or re-state:** GAP-29 (verified swap decoder), 30, 31, 32 (execution reservations), 41, 47, 49, 52.

## Exclusive paths (you may edit)

- Code: `larp/execution.py`, `larp/execution_live/`, `larp/signer/`, `larp/marketdata/`.
- Migrations: `migrations/008_execution_store.sql`, `migrations/009_signing_requests.sql`. Only add new migrations; never edit an applied one. Coordinate numbering with D.
- Tests: `tests/test_w04_execution.py`, `tests/test_w08_capabilities.py`, `tests/execution/`, `tests/execution_fixtures.py`, `tests/signer/`, `tests/marketdata/`.
- Tools: `tools/probe_quote.py`, `tools/w08_capabilities.py`, `tools/probe_candles.py`, `tools/probe_http.py`.
- Config: `config/execution/`, `config/hosts/signer.example.json`, `config/hosts/execution.example.json`.
- Records: your catalogue and record.

## Use-case prompts (in addition to protocol §1.5)

Make sure your use cases include at least:
- zero BNB at the first transaction;
- the approve confirmed but the re-quote expired;
- a re-quote with a different `tx.to`, amount or token;
- a gas estimate failing before the approve;
- a broadcast that times out but was mined;
- a broadcast rejected for its nonce;
- a dropped transaction;
- a reorg of a confirmed transaction;
- a swap that reverts (`DeadlinePassed`) and still costs gas;
- two intents racing for the same nonce;
- a crash after signing and before broadcast, and after broadcast and before recording;
- a stale owner epoch after takeover;
- the signer down while a mandatory exit is due;
- a malformed or hostile signing request from a compromised `primary`;
- a key file with wrong permissions, symlinked or swapped;
- the wrong wallet's key;
- HTTP 200 with `code != 0`;
- 429 and 5xx from the API;
- decimals that differ from 18;
- dust;
- the final-wallet switch with an old transaction still pending;
- funds arriving or leaving outside the agent (unsolicited assets).

## After your catalogue is frozen (not before)

Only then compare with these areas, which earlier work left open or flagged. They are hints for phase 2, not requirements:
- **Swap decoder:** no verified router decoder exists, so the signer refuses every swap (GAP-29). Decide what the requirements demand before swaps may be signed, and specify the decoder's tests.
- **First BNB:** how the first BNB is paid is still open (Q-03, GAP-49).
- **Execution service:** it stops `NOT_INTEGRATED` until the round driver lands (Keegan's IDEA-048 branch). Check that the contract between the round driver and `RemoteSigner` and `ExecutionService` matches your requirements.
- **Signer trust boundary:** on two hosts `larp_execution` can write `execution_records`. The signer independently enforces only the payload (IDEA-047 notes); check that this meets G-01 and G-18 as written.
- **Signer version binding:** the signer does not check the run's registered version.
- **Signer access:** there is no way yet to reach the signer host to provision it (`docs/build/AWS_RUNBOOK.md` step 5). This is a requirement gap for D, but you own what the signer needs at provisioning.

## Done means

Protocol §4, plus:
- every transaction shape the system can produce is covered by a test showing the allow-list admits exactly the permitted shapes and refuses the rest;
- no execution path signs twice for one attempt across crashes and restarts, shown on real PostgreSQL;
- every failed or uncertain transaction ends in a recorded, reconciled state without human action.
