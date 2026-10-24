# LD03-RP01 — fresh local router replay and preflight

**PASS_LOCAL_READONLY**, production named-reviewed policy
`05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5`.
Criteria91e04cc and probe/test sourcefe91326 were pushed before execution.
No production runtime configuration is changed.

Run: **2026-10-21 14:25:56–14:27:01UTC (22:25:56–22:27:01SGT)** from Isaac's
local macOS arm64/Python3.12.14 environment. Credentials were loaded with the
production read-only parser, which excludes wallet keys and logging secrets.

| Check | Observed result |
|---|---|
| Fresh quote coverage | Five eligible stocks, one20USDT BUY and one SELL each:10/10 |
| SELL quantity | Corresponding hypothetical BUY output, not actual reconciled holdings |
| Canonical decoder replay |10/10 match request tokens/amount/minimum; every built-in tamper mutation refused |
| BNB Chain public preflight |10/10 PASS;101 allowlisted reads; chain56 |
| NodeReal public preflight |10/10 PASS;101 allowlisted reads; chain56 |
| Live preflight observations | Pinned router/facet code hashes, dispatch slot and all six allowances checked at numeric blocks |
| Freshness at preflight end | Worst6.711s, within the candidate30s quote-age limit |
| Web3 calls | One token-metadata GET and10 quote GETs; no approval/gas-estimate/submission calls |

The exact profile is GC01's new bounded rehearsal EQUAL_WEIGHT candidate, file
SHA-256 `c2a6936739a336c1df55e7e3579a6e9b922df4dd085b29f70ff3c1b9ea912f0e`.
This identifies the measured candidate; it does not accept #120 or cover S1/final
sizes/full holdings. Preflight does not prove a route will execute, RFQ lifetime,
recipient/contract enforcement, gas sufficiency, fees or realized fill outcome.

[Sanitized report](review.json) SHA-256
`9eaad5d29797d3057b74e7544a369fd8970b0d3fcaf5d9c76788fffec7b3ff02`.
Original observations remain private at
`/private/tmp/larp-rp01-router-readonly-20261021`:202 RPC observations and11 Web3
observations, all content-addressed files independently hash-verified. Every
reported quote artifact resolves to its original private file. Provider URLs,
wallet and credentials are excluded from the committed summary. Read-only
boundary/privacy tests pass in the final focused68-test suite at `ffe91d9`
(CLI blocked-status follow-up; the real observation source remains `fe91326`);
no full CI claim.

This completes Isaac's **fresh local decoder replay/preflight slice** of priority3
under the named policy. Actual selected-profile/current-holdings/configuration
review, execution RPC/finality qualification, production host/release binding,
runtime preflight before every real step, first registered-agent round/receipt/
accounting/STORED ACK and host drills remain separate. The signer stays offline
from RPC. Signing/readiness/host-binding flags remain false. No AWS, DB, key,
signing, funding, broadcast, paid model or log-upload operation occurred.

To repeat, use committed `tools/deploy/replay_router_readonly.py` with explicit
private environment/provider files, the chosen rehearsal candidate and a new
external output directory. New observations never extend the validity of this
dated receipt, authorize a host session or replace production per-attempt checks.
