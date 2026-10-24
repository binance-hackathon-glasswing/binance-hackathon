# Tokenized-stock execution — measured evidence and preserved guards

PR276-RV01, checked 2026-10-24 SGT against source at `59c878c0`. This note adopts no execution or gas change.

## Sources and dated observations

Checked the [verbatim trading guide](../../../official/kit/bstocks-trading-guide.md),
[participant-kit reference](../../../skill/reference/participant-kit.md), [SKILL](../../../skill/SKILL.md) F/K/Q
items and the local execution sources. The guide specifies exact-pay-amount approval, local signing, confirmation
before re-quote, RFQ expiry of about 30 seconds and Web3 API broadcast. Retain the `openState` guard. Standing
allowances or direct/private RPC submission are not compatible drop-in optimizations for this harness; an alternative
architecture would need separate rule, policy and security review. No such alternative is recommended or authorized.

[IDEA-090](../../../ledger/IDEA-090.md) records four BUY executions: one approve-plus-swap completion, two
approval-only aborts and one abort without a prepared signed attempt. Calling them four signed buys confuses
intent, approval and swap. The “encoded swap economics mismatch/expired” message covers output and deadline checks;
without payloads and clocks it does not prove price movement was the unique cause of every abort. These are dated
retained records, not independently queried chain observations in this review.

PR274's repair in [venue.py](../../../../larp/execution_live/venue.py) keeps the original intent's authorized minimum and
allows a bounded narrower-slippage quote after approval; it does not authorize widening minima on retry. Offline
source tests passed in the [PR274 review record](../../../ledger/IDEA-090.md), while later dev-cycle slot/quote,
sell/flatten, profile/config and host qualification remain open in [INCOMPLETE_WORK](../../../INCOMPLETE_WORK.md).

## Costs are not interchangeable

[IDEA-012](../../../ledger/IDEA-012.md)'s 13–56 bp Roll estimates derive from trade prints, not executable quotes.
[IDEA-022](../../../ledger/IDEA-022.md) and GAP-66 retain correction/rerun limits. They cannot serve as current route
costs. The [dated DC-01 review](../../../build/QUOTE_COST_REVIEW_120_20261021.md) reports quote-pair summaries of
2–5 bp for four names and 17 bp for MSFTB under its aggregation convention. These are sampled proxy statistics,
not guaranteed fill spreads or one-way all-in costs. Do not halve them and omit gas, route fees, quote ageing or
adverse movement. Actual quote/fill fee attribution and selected-size/full-exit acceptance remain GAP-50/#119/#120.

One recorded approve-plus-swap used about 0.0000242 BNB. That observation cannot size whole-run spending, repeated
failed approvals, gas spikes or exit reserves. Current gas/BNB prices were not remeasured for this review. BscScan,
chain marketing, press estimates and other venues' tokenization arrangements remain leads unless specifically
verified; their numbers are not this route's executable guarantees or independent MEV measurements.

## Gas, slippage and attempts need a joint case

The [S1 rehearsal candidate](../../../build/evidence/s1-rehearsal-profile-20261023/README.md) reserves
0.000384 BNB per action and 0.00384 BNB for ten exit children, so reserve plus one action is 0.004224 BNB. This is
candidate-specific arithmetic, not a FINAL funding recommendation. The [action-budget formula](../../../../tools/deploy/build_rehearsal_candidate.py)
uses 0.16 gwei, only 3.2 times a quoted 0.05 gwei observation; actual signer binding/acceptance remains separate.
Larger wallet funds do not allow signing above an approved ceiling. The original
“roughly twentyfold spike headroom” conflated spend, gas-limit and gas-price constraints and is withdrawn.

[profiles.py](../../../../larp/strategy/profiles.py) allows fixed slippage up to 50 bp by team policy, and
[execution_bounds.py](../../../../larp/strategy/execution_bounds.py) allows one to five attempts. A validation ceiling
is not a recommendation. Neither the generic aborts nor an assumed volatility model selects 20 bp or five attempts.
Changing them requires actual-size quote age, approval-to-swap latency, adverse movement, fee/gas costs and acceptable
loss bounds, together with retry/exit coverage. PF-06's no automatic widening on retry remains in force.

F-120 already answers first-BNB bootstrap: permitted pre-trading/pre-scored-run MetaMask funding swaps from wallet
USDT, with the funding record and opening snapshot after the last seed. BNB valuation remains Q-39. The roughly
6 USDT FINAL seed is existing team policy; reducing it to 4 USDT has no approved measured reserve case here, and
an unresolved valuation convention is not permission to optimize against an assumed score. Preserve current gates.

Isaac/Keith own any revised cost/gas/cap proposal and exact acceptance; Keith/Keegan own runtime/profile semantics;
Yao operates a later approved dev run. No wallet operation, RPC test, fee measurement or new live run occurred here.

## Provenance and original source leads

The [original research text](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/5d5b5e284fd0e70586ba83767a2d22b0fd726d1e/docs/research/strategy-alternatives-20261024/notes/tokenized_stock_execution.md) is retained immutably.
PR276-RV01 replaces unsupported conclusions and repairs local references. The register preserves the original
external URLs for follow-up; inclusion does not verify availability, quality, rights or any claimed result. Only
sources explicitly assessed above have been rechecked; all other entries remain unverified leads.

- Lead 01: [BNB Chain blog](<https://www.bnbchain.org/en/blog/introducing-bstocks-on-bnb-chain-trade-24-7-with-zero-fees-deploy-across-defi-protocols-with-full-self-custody>)
- Lead 02: [HackerNoon](<https://hackernoon.com/binance-opens-bstocks-collateral-to-every-eligible-user-as-tokenized-stock-volume-tops-$30-billion>)
- Lead 03: [Blockchain.News](<https://blockchain.news/news/binance-bstocks-tokenized-securities-24-7-access>)
- Lead 04: [Eco.com comparison](<https://eco.com/support/en/articles/15254023-best-tokenized-stock-platforms-2026-fees-us-access-and-backing-compared>)
- Lead 05: [Traders Union](<https://tradersunion.com/news/brokers-news/show/2658271-binance-lists-sk-hynix-tokenized/>)
- Lead 06: [Thailand Business News](<https://www.thailand-business-news.com/pr-news/sk-hynix-lists-adrs-on-nasdaq-elevating-global-status-at-the-heart-of-capital-markets>)
- Lead 07: [Finance Magnates](<https://www.financemagnates.com/cryptocurrency/exchange/binance-claims-fastest-1-billion-sprint-in-bstocks-with-6-billion-in-share-conversions/>)
- Lead 08: [crypto.news](<https://crypto.news/bnb-chain-claims-42-6-of-tokenized-stock-market/>)
- Lead 09: [Wisevoter](<https://wisevoter.com/world/2026/10/05/binance-end-fee-free-bstock-conversion>)
- Lead 10: [Phemex News](<https://phemex.com/news/article/binance-to-enable-247-dynamic-updates-for-bstocks-collateral-index-price-100584>)
- Lead 11: [The Defiant](<https://thedefiant.io/converge/tradfi-and-fintech/binance-to-reprice-bstocks-collateral-while-us-stock-markets-are-closed>)
- Lead 12: [Hokanews](<https://www.hokanews.com/2026/10/binance-to-reprice-bstocks-collateral.html>)
- Lead 13: [Native on X](<https://x.com/native_fi/article/2065075659790270758>)
- Lead 14: [BNB Chain market-making landscape](<https://www.bnbchain.org/en/blog/bnb-chain-market-making-landscape-liquidity-venues-how-to-integrate>)
- Lead 15: [TradingView/Chainwire](<https://tr.tradingview.com/news/chainwire%3A2dd28640d094b%3A0-stablestock-and-native-launch-24-7-tokenized-stock-trading-on-bnb-chain>)
- Lead 16: [Kraken xStocks FAQ](<https://support.kraken.com/articles/xstocks-faq>)
- Lead 17: [CoinPaprika](<https://coinpaprika.com/education/tokenized-stocks-price-tracking/>)
- Lead 18: [DeGate playbook](<https://degate.com/playbook/tokenized-stocks-24-7-price-discovery.md>)
- Lead 19: [The Block](<https://www.theblock.co/post/111661/binance-ceases-stock-tokens-trading>)
- Lead 20: [Decrypt](<https://decrypt.co/82495/binance-lets-customers-move-stock-tokens-before-service-shuts-down>)
- Lead 21: [The Block](<https://www.theblock.co/news/markets/2021-01-27-ftx-lists-gme-stock-for-tokenized-spot-futures-trading-92756>)
- Lead 22: [Crypto Briefing](<https://cryptobriefing.com/ftx-adds-silver-stocks-reddit-market-surge/>)
- Lead 23: [Coin Bureau](<https://coinbureau.com/review/mirror-protocol-mir>)
- Lead 24: [Veradiverdict](<https://veradiverdict.beehiiv.com/p/synthetic-assets-blockchain>)
- Lead 25: [CertiK](<https://www.certik.com/blog/mirror-protocol-exploited-due-to-incorrect-oracle-price>)
- Lead 26: [Blockworks Research (0xResearch)](<https://blockworks-research.beehiiv.com/p/when-markets-sleep>)
- Lead 27: [4pillars](<https://research.4pillars.io/en/research/can-hyperliquids-weekend-trading-predict-monday-opens-for-korean-stocks>)
- Lead 28: [Dune](<https://dune.com/blog/hyperliquid-priced-wti-while-futures-were-shut>)
- Lead 29: [AEA 2026 listing](<https://www.aeaweb.org/conference/2026/program/paper/kRz7yE6Q>)
- Lead 30: [Neudata review](<https://www.neudata.co/literature-reviews/trading-in-the-dark-retail-flow-in-the-overnight-session>)
- Lead 31: [Eaton et al. PDF](<https://haslam.utk.edu/wp-content/uploads/2024/11/Eaton-Paper.pdf>)
- Lead 32: [Nasdaq](<https://www.nasdaq.com/articles/looking-all-day-data-24-hour-trading>)
- Lead 33: [BMLL](<https://www.bmlltech.com/news/market-insight/there-is-a-clear-trend-towards-24-7-equity-trading-but-how-much-liquidity-is-available-for-participants-during-overnight-trading>)
- Lead 34: [BlockEden](<https://blockeden.xyz/blog/2025/10/30/xstocks/>)
- Lead 35: [Boston Fed WP 98-6](<https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/wp98_6.pdf>)
- Lead 36: [Spark glossary](<https://www.spark.money/glossary/request-for-quote>)
- Lead 37: [Ethernal blog](<https://tryethernal.com/blog/the-dex-trade-that-was-never-on-a-dex>)
- Lead 38: [0x Help](<https://help.0x.org/articles/3310442497-understanding-0x-rfq-request-for-quote>)
- Lead 39: [Coinbase CDP docs](<https://docs.cdp.coinbase.com/prime/concepts/trading/rfq>)
- Lead 40: [Consensys on Hashflow](<https://consensys.io/blog/hashflow-a-dex-for-bridgeless-cross-chain-swaps-zero-slippage-and-mev-protected-trades>)
- Lead 41: [Spark glossary (sandwich)](<https://www.spark.money/glossary/sandwich-attack>)
- Lead 42: [thetrading.tools](<https://www.thetrading.tools/nvda-options>)
- Lead 43: [Market Rebellion](<https://marketrebellion.com/news/mid-session-iv-report-october-14-2026>)
- Lead 44: [MarketChameleon](<https://marketchameleon.com/Overview/TSLA/OptionChain/>)
- Lead 45: [Decrypt](<https://decrypt.co/294648/bnb-smart-chain-blocks-hits-record-high-sandwich-attacks>)
- Lead 46: [BNB Chain blog](<https://www.bnbchain.org/en/blog/how-the-goodwill-alliance-slashed-sandwich-attacks-by-95>)
- Lead 47: [BNB Chain forum](<https://forum.bnbchain.org/t/call-for-proposal-addressing-malicious-mev-attacks-on-bnb-chain/3167>)
- Lead 48: [BNB Chain blog](<https://www.bnbchain.org/en/blog/protecting-users-from-sandwich-attacks-bnb-chain-introduces-mev-protection-with-several-wallets>)
- Lead 49: [Chainstack](<https://chainstack.com/build-better-with-bnb-smart-chain/>)
- Lead 50: [BscScan Gas Tracker](<https://bscscan.com/gastracker>)
- Lead 51: [Bitget News](<https://www.bitget.com/news/detail/12560604996708>)
- Lead 52: [Bitcoin.com](<https://news.bitcoin.com/bnb-chain-validators-move-to-halve-gas-fees-with-new-proposal/>)
- Lead 53: [ECOIN Wallet blog](<https://ecoinwallet.org/blog/bnb-chain-cuts-gas-fees-to-0-05-gwei-and-speeds-up-blocks-cheaper-than-ever/>)
- Lead 54: [Chainwire](<https://chainwire.org/2026/04/28/bnb-chain-activates-osaka-mendel-hard-fork-faster-finality-predictable-gas-and-enhanced-stability/>)
- Lead 55: [BNB Chain blog](<https://bnbchain.org/en/blog/osaka-mendel-hard-fork-strengthening-bnb-chain-after-sub-second-speed-gains>)
- Lead 56: [Cointelegraph](<https://cointelegraph.com/news/bnb-chain-pasteur-hard-fork-bridge-security>)
- Lead 57: [The Block](<https://www.theblock.co/post/341215/bnb-chain-will-prioritize-memecoin-transactions-as-gas-fees-surge-400>)
- Lead 58: [The Defiant](<https://thedefiant.io/news/defi/binance-smart-chain-congestion-is-slowing-down-pancakeswap>)
- Lead 59: [Univ. of Memphis Digital Commons](<https://digitalcommons.memphis.edu/facpubs/11507/>)
- Lead 60: [Hinich et al., UT Austin](<http://www.la.utexas.edu/hinich/files/Economics/Signal-NYSE.pdf>)
- Lead 61: [HKUST Research Portal](<https://researchportal.hkust.edu.hk/en/publications/market-structure-and-the-intraday-pattern-of-bid-ask-spreads-for->)
- Lead 62: [Univ. of Saskatchewan](<https://harvest.usask.ca/items/185eee73-6ce2-422e-9a11-c6fb47c0e9d0>)
- Lead 63: [Univ. of Southampton ePrints](<https://eprints.soton.ac.uk/37372>)
- Lead 64: [Microsoft News](<https://news.microsoft.com/source/2026/10/07/microsoft-announces-quarterly-earnings-release-date-69/>)
- Lead 65: [Wall Street Horizon](<https://www.wallstreethorizon.com/nvidia-earnings-calendar>)
- Lead 66: [days.to](<https://days.to/nvidia-earnings>)
- Lead 67: [Fidelity](<https://www.fidelity.com/learning-center/smart-money/stock-market-holidays>)
- Lead 68: [Kiplinger](<https://www.kiplinger.com/investing/stock-market-holidays>)
