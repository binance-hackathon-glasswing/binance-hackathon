# Quote fee review — 2026-10-17 (IDEA-063 FN-01/FN-02)

Owner: Isaac. Issue #156 covers this offline evidence/reporting correction. **#119 remains open:** fee netting is not conclusively established. #120 still requires Isaac's and Keith's summary/profile review.

## Sources and interpretation

Checked the verbatim participant-kit `bstocks-trading-guide.md` §3: `toTokenAmount` is described as the expected received amount. The kit does not define `tradeFee`.

Checked the primary [Binance Trading API documentation](https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/trading-api), **Quote and Build Swap Transaction (Flash API)** response fields, on 2026-10-17:

- `tradeFee` is an estimated network fee expressed in USD, rather than a documented token trading-fee rate.
- `feeAmount` and `feeToken` describe the optional custom fee; null indicates that option is not enabled. `actualSwapAmount` distinguishes its input/output deduction behavior.
- Input/output amounts and minimum received are documented separately. These descriptions do not explicitly prove that all possible route fees are already included in the final wallet credit.

These are dated external vendor definitions, not new organiser rules. They explain the fields, but do not independently verify the historical backend or deployed contracts. **Do not convert `tradeFee` to additional `fee_bps`: gas is already budgeted separately.** Nor does null custom-fee metadata prove that liquidity-pool or vendor fees are zero.

## Bounded saved-quote inspection

Preregistered at `f27965d`, before inspection. No new quote, RPC, credential read or transaction. Among 3,713 JSON filenames in the two allowed local artifact directories, inspected the 1,000 most recently modified files: 977 response envelopes, 9 unsuccessful request envelopes and 14 observation manifests. This is a bounded convenience sample, not an exhaustive or representative capture.

Found **391 successful quote responses** in `data/execution-live`, received between **2026-10-15T02:42:34.929Z and 2026-10-16T14:08:05.669Z**. These predate Keith's separate capture that started at 18:19 UTC on Oct 16; that server's ongoing capture has not been inspected here.

All 391 bind response chain 56, both returned token addresses and requested amount to the saved request; token decimals are 18, vendor is LiquidMesh, API code is 0 and outcome is `ok`. All 195 USDT-input quotes pay exactly 40 USDT. All 391 have nonzero `tradeFee`, ranging from **0.00920343 to 0.01684481**; `feeAmount`, `feeToken` and `actualSwapAmount` are explicitly null. None of their requests includes the custom-fee parameters. Missing and null were distinguished; no fee rate or deduction side was inferred from these numbers.

| Stock | USDT → stock quotes | Stock → USDT quotes |
|---|---:|---:|
| NVDAB | 39 | 39 |
| GOOGLB | 39 | 40 |
| SKHYB | 39 | 39 |
| TSLAB | 39 | 39 |
| MSFTB | 39 | 39 |

Routes span nine DEX names, including RFQ-labelled segments; this inspection does not qualify any route for signing. SHA-256 of the sorted unique 391 artifact hashes, each followed by a newline: `6a18ae83e5411dbd7ded4f0166ae7b29def58f75380c21836f6ca5d4240a0763`. The raw artifacts stay outside Git; each example below names its content-addressed artifact filename.

## Exact examples, both directions

Each example pays `40000000000000000000` raw USDT (40 USDT), then requests a sell of exactly the quoted stock receipt. All amounts below are raw 18-decimal token units. The last column is the change between sequential quotes in basis points, excluding separately budgeted gas; it is not a fill or a guaranteed spread. Negative changes can reflect timing and route differences.

| Stock | Stock received / sell input | Sell USDT output | Buy `tradeFee` | Sell `tradeFee` | Quoted round trip bp |
|---|---:|---:|---:|---:|---:|
| NVDAB | 184481497191447797 | 39997114139165497140 | 0.01482991 | 0.01178512 | 0.721465 |
| GOOGLB | 116090908580283920 | 40005085058123869380 | 0.01095592 | 0.01196587 | -1.271265 |
| SKHYB | 288695989804678089 | 39998653131827465969 | 0.01275895 | 0.0128163 | 0.336717 |
| TSLAB | 108393601740909501 | 40006024097289980544 | 0.01291888 | 0.01314108 | -1.506024 |
| MSFTB | 74441934142728760 | 39979079474276400767 | 0.01291463 | 0.01291463 | 5.230131 |

Example provenance (SHA-256 = filename stem under `data/execution-live`):

- **NVDAB**: buy `2026-10-16T14:07:44.980Z`, `55ec747b9817059a79fef8f2ceec30f8f791dcbd23646485bdabbca950114f59`; sell `2026-10-16T14:07:45.380Z`, `a7774af2546d7a0c4e363e97108afdaa9ec27f76967470bd7e68347aeb92d596`.
- **GOOGLB**: buy `2026-10-16T14:07:49.972Z`, `b3034bc9c524736a64d1a5b1ede3a8c39ad021cd1feca349ce60bdcc01c594ca`; sell `2026-10-16T14:07:50.673Z`, `271fd4842ad3ca910c097ddcbf1c683da5910b2675d99c21200edd132ae1bca2`.
- **SKHYB**: buy `2026-10-16T14:07:54.965Z`, `c1cd038aee9a84bd6b9f63f1211d066223f1250b9d0a08da4f4b63427ad38c22`; sell `2026-10-16T14:07:55.315Z`, `426911fc3006c77c09451c9036de94d6ad362ffc677882f577deb7326a15d022`.
- **TSLAB**: buy `2026-10-16T14:07:59.984Z`, `5d6ba349e65e1ac062f6f1fa5f0ce6855fe9982316bf9600a11a28afe16f3a63`; sell `2026-10-16T14:08:00.330Z`, `70bb4775fb70d95fa91255b1d49c3bca228badd43d757dff45f1ab5da646dc4a`.
- **MSFTB**: buy `2026-10-16T14:08:04.970Z`, `12a2528431406f2d2df4e93c96d99d0f182678b012a9373bae893add3e6370cc`; sell `2026-10-16T14:08:05.304Z`, `65f0aee6db047177b30fc556597e8cee19650bca0c4385ce49b39e42c87c0922`.

## Completed correction and remaining work

The historical design table in IDEA-063 stated that fees were netted as a fact; that was unsupported. FN-02 corrects the report to state the assumption and `UNVERIFIED` status, labels the legacy buy-only `trade_fees` field, and retains the four raw fee fields separately for buy, sell and requote legs in future SAMPLE records. Existing captures remain usable: their raw response artifacts already contain the missing leg details. Keith does not need to interrupt the ongoing capture for this change.

The numeric cost formula has not been changed. This correction does not add a new profile validation gate; the existing #119/#120 owner acceptance remains required before pinning a LIVE profile. Synthetic tests cannot establish actual route economics.

Remaining under **#119 (Isaac, with Keith's review)**: obtain explicit, attributable vendor/source evidence about route-fee inclusion for the applicable route, or compare the exact quote bound to an agent transaction against all wallet token debits/credits, distinguishing gas, slippage and price movement. Keep the quote artifact hash, transaction hash, token amounts/decimals, receipt transfers and UTC times together. Extend coverage if routes or fee configurations differ. Reuse the first planned agent development swap when available; this review does not request an extra manual trade. The earlier MetaMask USDT → BNB funding transaction used a different route and does not satisfy this check.

If a charge outside the quoted economics is demonstrated, preregister and measure the additional cost before changing `_costs`; do not guess a rate. **Keith owns completion of capture #118. Isaac and Keith own the measured-summary/profile review #120.**

## Verification

Criteria pushed at `f27965d` / `96c4017`; regression tests pushed at `585512c` and reproduced the missing evidence/report metadata. Fix pushed at `61cb527` before execution. Marketdata and strategy checks: **235 passed, 1 skipped, 131 subtests passed** (Python 3.12.14, 18.34 s). The skipped recorded-market test requires an opt-in external artifact root. Tests exercise distinct nonzero fees on all legs, absent/null/zero preservation, backwards compatibility and unchanged numeric costs. These synthetic checks are not a real quote/fill comparison. No full-suite, host or signing qualification is claimed.
