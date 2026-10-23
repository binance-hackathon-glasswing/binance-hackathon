# IDEA-086 — Token basis check: let the hosted agent enter positions (consistency rule, not independent share verification)

- Date / author: 2026-10-23 / Yao Zhu (request), Claude Code (analysis and draft). **Reviewers: Keith (strategy and
  market data), Isaac (risk and signing).**
- Status: **implemented for the dev rehearsal; independent PR262 review PASS with repairs (PR262-RV01 below).**
  Final policy adoption, release and run-3 acceptance remain open. The original pass criteria below predate code.
- Links: IDEA-049-C SJ-10 first trading-status; `docs/INCOMPLETE_WORK.md` SJ-10-BASIS01, GAP-22, DR-09/DR-12;
  IDEA-018 §2.2; IDEA-035 item 5; IDEA-037; `larp/strategy/policy.py:154`; `larp/marketdata/port.py:66-125`;
  `larp/runtime/service.py:288`; evidence [basis-sample-20261023/sample.json](../build/evidence/basis-sample-20261023/sample.json).

## 1. Problem

The hosted agent cannot open a position:
- `StrategyPolicy` keeps every name at its current quantity with reason `MISSING_MARKET_OR_BASIS` unless its market view
  has `basis_verified: true`. This is checked before any baseline, `EQUAL_WEIGHT` included (IDEA-037: "`basis_verified`
  [is] still required").
- `MarketPort` sets `basis_verified` only when it is given a `basis_verifier`.
- `service.py` builds `MarketPort(client, wallet, quote_limits=profile)` without one, so every observation is
  `basis_verified: false`.

Seen live in run 2 on 2026-10-23: all 10 targets in 2 cadence rounds were `MISSING_MARKET_OR_BASIS`, with 0 orders. The
LLM trial (Oct 18–20) shows the same: 350 of 350 targets.

**What "basis" was meant to mean** (plan.md, GAP-22): a token-versus-share check, meaning the token tracks its
underlying share. GAP-22 stays open because **the kit's sources give no independent share price** (2026-10-07). This
proposal does not close GAP-22. It defines what *can* be verified now, and asks the reviewers whether that is enough to
let entries through: for the dev rehearsal only, or also for the final.

## 2. What the real data shows (2026-10-23, read-only GETs; `sample.json`)

**`market/rwa/tokens`** (one row per token):
- `tokenSymbol`, `tokenContractAddress`, `binanceChainId`, `platformId` (`bstock`), `assetType`;
- `underlyingTicker`: NVDA, GOOGL, SKHY, TSLA, MSFT;
- `underlyingName`;
- **`tokenToShareRatio`**: NVDAB 1.000778, GOOGLB 1.000478, MSFTB 1.001314, SKHYB 1, TSLAB 1. This is the dividend
  multiplier, never below 1;
- `tokenPrice`, `referencePrice`, `statusInfo.openState`.

**`market/rwa/underlying-market`:**
- the same `tokenContractAddress`, `platformId` and `assetType`, plus `statusInfo`;
- `marketData`: 52-week high/low, volume, market cap, P/E, dividend. It has **no current share price**.

**`market/rwa/price`:** `tokenPrice`, `referencePrice`, `tokenPriceUpdatedAt`.

**Identities:**
- In `rwa/tokens`, `tokenPrice` = `referencePrice` × `tokenToShareRatio` to the last digit, on all five names. This
  re-confirms IDEA-018 §2.2: the two are one reference mark, so comparing them is not an independent check.
- `rwa/price` `tokenPrice` equals `rwa/tokens` `referencePrice`: the **per-share** value. `rwa/price` `tokenPrice` ×
  ratio equals the `rwa/tokens` `tokenPrice` exactly.

**Executable market against the marks** (5 names, a buy and a sell quote of about 20 USDT each, about 05:2xZ, market
open). The quoted mid is within **−2.5 to +8.5 bp** of the ratio-scaled mark (`rwa/tokens` `tokenPrice`) on all five.
Against the per-share `rwa/price` `tokenPrice` it is +1.4 to **+21.7 bp** (MSFTB, because of its 1.0013 ratio). The
measured half-spreads are about 1 bp or below; quotes were taken in sequence, so small moves appear. The run-2 M3
capture at 04:35Z agrees: for example, the NVDAB buy implies 213.99 and the sell 213.98.

**Side finding F2 (valuation scale).** `MarketPort` sets `price_units` from `rwa/price` `tokenPrice`, which is per
share. A token is worth `tokenToShareRatio` shares, so the agent values tokens low by the ratio: about 13 bp for MSFTB,
8 bp for NVDAB, 0 for SKHYB and TSLAB. It is small, but it touches sizing, marks and PnL. Proposed: value with the
ratio-scaled mark (§3 BV5). This is a separate decision from the basis rule.

## 3. Proposed rule: `basis_verified` is true only when every check passes

Each check uses only that observation's three responses, plus one value the process keeps: the last ratio accepted per
token.

| ID | Check | Why | Tolerance (proposed) |
|---|---|---|---|
| BV1 | Identity: `tokens` row and `underlying-market` row name the same `tokenContractAddress`, `platformId == 'bstock'`, the same `assetType`, chain 56; `tokenSymbol` equals the registry symbol. | The three responses describe the same instrument | exact |
| BV2 | Expected underlying: `underlyingTicker` equals the pinned `underlying_id` for that token in `config/intelligence/issuers.v1.json` (today `null`; set it to NVDA, GOOGL, TSLA, MSFT, SKHY as part of this change, closing DR-09/DR-12 for these five). | A token re-pointed to another share must not pass | exact |
| BV3 | Ratio sane: `tokenToShareRatio` is a decimal string with 1 ≤ ratio ≤ 1.05. Per token in the process, it never decreases and rises at most 1% from the last accepted value. | Dividend multipliers only ratchet up slowly; a jump means a corporate action or a bad feed | [1, 1.05]; no decrease; at most +1% per step |
| BV4 | Mark integrity: `tokens.tokenPrice` = `referencePrice` × ratio within 1 bp, and `rwa/price.tokenPrice` × ratio within 25 bp of `tokens.tokenPrice` (the calls are seconds apart). | Detects a malformed, stale or mis-scaled feed. It does **not** prove the share price. | 1 bp; 25 bp |
| BV5 | (with F2) The valued price is `rwa/price.tokenPrice` × ratio, the per-token mark. | Values what the wallet actually holds | — |

What the rule deliberately does **not** do:
- **Independent share price:** none exists in our sources (GAP-22). The recorded deviation is "basis = identity,
  ratio and mark consistency; no independent share-price check".
- **Executable agreement:** this is already enforced downstream:
  - the planner rejects a buy whose quote costs more than 50 bp over the mark, including fee and gas
    (`ENTRY_COST_CAP`, `larp/risk/planner.py:461`);
  - the executor re-quotes with `min_out` at profile slippage (0.08% in the run-2 quotes).

  The sample shows quotes within about 9 bp of the mark, so a quote on every market observation would only add load.
- **Open state:** `token_open` and `underlying_open` already gate entries separately, so they are not repeated here.

When a check fails, `basis_verified` is false and the reason is kept (for example `BV3_RATIO_DECREASED`), so rounds
and the ai-seeds log show why a name was held.

### 3.1 What an entry still has to pass after the basis check

Clearing basis does not by itself guarantee a trade; the run-2 plan only ever reached the first gate. The rehearsal
profile `e95d5842…` has `mode: LIVE` and `assessment_required: false`. So, for `EQUAL_WEIGHT`, an unheld name also
needs:
- the entry window open;
- `measured_roundtrip_bps` as an integer from `MarketPort`'s cost measurement (`policy.py`; `cost_status` is
  `UNAVAILABLE` when that measurement fails);
- gross below 75%.

The planner then applies `COST_RESERVE_INSUFFICIENT`, `ENTRY_COST_CAP` (50 bp), and in LIVE mode
`impact_median_bps[symbol]` with `impact_bps ≤ min(50, 2 × median)`. If the cost measurement or the impact medians
are missing on the host, the next blocker would be one of these, not basis. P3 below runs the full path offline so it
shows up before a run-3 install.

## 4. Wiring (smallest change)

1. **New module `larp/marketdata/basis.py`:** `BasisVerifier(issuers)`, a small stateful object holding the last
   accepted ratio per token. `check(symbol, token_row, underlying, price_row) -> (bool, reasons)`.
2. **`MarketPort.observation`:** call `basis_verifier.check(symbol, row, underlying, price_row)` in place of today's
   two-argument call. Add `basis_checks` (a list of reason codes) to the observation. With BV5, set `price_units` from
   `price_row` × ratio. The existing consumer validator and the `does_not_invent_basis` test stay true when no verifier
   is given.
3. **`service.py` `build_driver`:** `MarketPort(client, wallet, quote_limits=profile,
   basis_verifier=BasisVerifier(issuer_map))`, for `dev` and `live`. `offline` and the fixtures stay as they are.
4. **`config/intelligence/issuers.v1.json`:** pin `underlying_id` for the five tokens. This changes the configuration
   hash and so the release manifest, so it needs a new build.
5. **Release path:** new build (RC6), then a new run (run 3) on a fresh database with a reassembled `signer.json`
   (only `build_id`, `run_id` and `database_name` may differ). This is the same run sheet as SJ-10.

## 5. Pass criteria (offline; written before any code)

- **P1 unit, each check:** for each of BV1–BV4, a passing case and every failing case gives `basis_verified: false`
  with its reason code. Failing cases:
  - another contract, platform or chain;
  - a ticker other than the pinned one;
  - ratio below 1 or above 1.05;
  - a decreasing ratio, or a step above +1%;
  - `tokenPrice` off from referencePrice × ratio by more than 1 bp;
  - the price endpoint off from the mark by more than 25 bp;
  - a missing or non-decimal field.
- **P2 recorded data:** the five real 2026-10-23 rows in `sample.json` all give `basis_verified: true` with an empty
  reason list. The same rows with the ratio reduced by 0.0001 on the next observation give `BV3_RATIO_DECREASED`.
- **P3 policy and planner end-to-end** (offline driver, EQUAL_WEIGHT rehearsal profile `e95d5842…`, stock-flat 96
  USDT, window open, the sample's marks and quotes):
  - with the verifier, the cadence round produces entry candidates and at least one BUY action that passes the planner
    (no `MISSING_MARKET_OR_BASIS`);
  - any remaining rejection (`ENTRY_COST_CAP`, impact, cost unavailable) is listed by reason;
  - without the verifier, today's behaviour is unchanged.
- **P4 valuation (if BV5 is accepted):** `price_units` equals the ratio-scaled mark; for MSFTB on the sample,
  `price_units` / per-share = 1.001314 ± 1e-6. Existing accounting, cap and coverage tests stay green.
- **P5 no regression:** the full local suite with PostgreSQL 14.24 shows no new failure or skip against base.
- **Host (run 3):** within the first 2 cadence rounds after P5 with the window open, at least one `TARGET_WEIGHT`
  target and an approve and/or swap intent reach the signer, then J7 (receipts, accounting, STORED ACK).

## 6. Decisions requested from the reviewers

1. **Keith:** is BV1–BV4 an acceptable meaning of `basis_verified` for the **dev rehearsal** (yes/no)? And for the
   **final** (yes/no), given GAP-22 has no independent share source? If no for the final, what source or check would be?
2. **Keith:** accept BV5 (value tokens at the ratio-scaled mark)? It changes marks, sizing and PnL by up to about 13 bp.
3. **Isaac:** the tolerances (ratio band [1, 1.05], +1% step, 1 bp and 25 bp). Is there anything in the signing caps
   (CAP-02 `max_input_units`) that a 13 bp valuation change would push past? The run-2 coverage review sized at the
   per-share mark.
4. **Both:** pin `underlying_id` = NVDA, GOOGL, TSLA, MSFT, SKHY in the issuer registry (DR-09/DR-12). Is "SKHY" the
   intended underlying identity for SKHYB? It is what the API reports, and plan.md treats SK hynix's Korean line and ADR
   separately for labels.

Once approved, the build follows §4 and §5 test-first, and installs through the SJ-10 run sheet as run 3.

## 7. Decision for the dev rehearsal (Yao, in chat, 2026-10-23 ~06:00Z)

"yes all bv should go in now start". Yao decides, **for the dev rehearsal only**, that BV1–BV4 define
`basis_verified`, and that BV5 (value at the ratio-scaled mark) goes in too. The tolerances are as proposed, and the
`underlying_id` pins are NVDA, GOOGL, TSLA, MSFT and SKHY. Keith's and Isaac's §6 review still decides the final.
Anything they change goes into a later build. The build follows §4 test-first against P1–P5, then a new build (RC6) and
run 3 through the SJ-10 run sheet.

## 8. Results (offline, 2026-10-23; branch `claude/basis-verifier-20261023`, code commit `d151e210`)

Local Mac, Python 3.12 with `deploy/requirements-test.lock`, disposable PostgreSQL 14.24. No host, AWS or wallet
action; the recorded sample is the only live data.

- **P1 PASS:** every BV1–BV4 failing case gives `basis_verified: false` with its reason code, and passing cases pass.
  Cases: contract, platform, chain and asset type; pinned ticker or missing pin; ratio outside [1, 1.05], missing or
  non-decimal; ratio decreased or stepped above +1% (a refused observation never moves the ratchet); mark off by more
  than 1 bp; price endpoint off by more than 25 bp; missing or zero prices. Bad pins refuse construction.
- **P2 PASS:** the five real 2026-10-23 rows give `basis_verified: true` with no reasons, both directly and through
  `MarketPort`, and `market_view` keeps all five. The pins equal the observed tickers (NVDA, GOOGL, SKHY, TSLA, MSFT).
  A changed ticker on one name fails only that name (`BV2_UNDERLYING`).
- **P3 PASS:** with the verifier, the EQUAL_WEIGHT policy plans `TARGET_WEIGHT` 1/5 entries and no
  `MISSING_MARKET_OR_BASIS`. Without it, every name is `KEEP_QUANTITY` / `MISSING_MARKET_OR_BASIS`, as in run 2. This
  composes the real port's verdicts with the policy fixture. A planner run with the S1 profile and the host's cost
  measurement is left to run 3 (SJ-11).
- **P4 PASS:** `price_units` = per-share `rwa/price` × `tokenToShareRatio`; MSFTB 1.0013139648. With no verifier, the
  valuation and the `NO_VERIFIER` reason are unchanged.
- **Wiring:** a driver test shows `build_driver` gives the hosted `MarketPort` a `BasisVerifier` with the run's pins,
  for shadow and service. With the `service.py` change reverted it fails (2 failed).
- **P5 PASS:** full suite **2502 passed, 10 skipped, 3921 subtests, 0 failed**. The 10 skips are identical to the
  base run's: bubblewrap 3, systemd runner 5, external market artifact 1, private fixture 1. The base for this branch is
  canonical `8eb16e5`; I did not run it separately here. The earlier base `f56bcf6` gave 2468/10, and canonical added
  PR256 and others since.

Original author verdict: **P1–P5 supported (offline).** PR262-RV01 below qualifies P3 as policy-only in this
original run; it adds the missing planner check. Still open: an RC6 build and the host check in run 3
(SJ-11).


## 9. PR262-RV01 — independent merge review (Isaac/Codex, 2026-10-23 SGT)

Review base: canonical `8eb16e5`; PR head `a525430`. Initial focused macOS/Python3.12.14 run:
477 passed /9 PostgreSQL-dependent skips /225 subtests. No host, wallet or model-provider call.

Findings and pass criteria, recorded before repair validation:
- **R1 (BV1):** the price response's chain/platform are unchecked. Mutating or removing either must refuse BV1.
- **R2 (BV3/BV4 valuation):** refused ratios/marks still produce `quality=VALID` rows, so the risk planner can value
  holdings with a rejected ratio or fall back to a per-share mark. With a verifier, any failed basis check must keep
  its diagnostic reason but make that row unusable for valuation. Existing partial-valuation handling must block new
  risk and defer loss stops for unvalued holdings. No-verifier fixtures keep their historical behavior.
- **R3 (P3 evidence):** the original P3 copies only verdict booleans into a synthetic policy fixture; it does not
  satisfy §5's planner criterion. Feed real port rows and the pinned EQUAL_WEIGHT rehearsal profile through policy
  and planner, with explicitly stubbed costs/request-bound quotes. Require a BUY, no basis/cost/impact/reserve
  rejection; no-verifier produces no BUY; excessive fees still fail the pinned cost-reserve gate before entry-cost evaluation. This remains offline
  evidence, and does not qualify S1 or actual route/gas/source/host acceptance.
- **R4 (records):** update the stale proposal status and SJ-10-BASIS01 backlog to distinguish repository repairs
  from final policy/release/run-3 acceptance. GAP-22 remains open. Review does not adopt a final share/listing identity.

Validation planned: focused regressions, then full suite on disposable PostgreSQL14.24; report actual environment,
skips and failures. Final policy adoption still needs Keith/Isaac's §6 review; run-3 S1/profile/cap/host gates remain
with their existing owners in IDEA-049-C SJ-11. The in-process ratio ratchet intentionally resets on restart (§3).


PR262-RV01 repair details:
- Price-row chain and platform are now required and checked; the underlying endpoint still inherits chain56 from
  its chain-bound request when its response omits the chain (as in the recorded API sample).
- Any failed verifier result gives `quality=INVALID`, preserving basis reason codes for diagnostics. Usable-market
  filtering now excludes it from policy/planner/accounting marks. With a held invalid symbol, policy is unavailable;
  the coordinator catches that and runs the risk planner without a policy proposal. The existing lower-bound path
  defers loss stops and blocks new risk. No-verifier fixtures retain `quality=VALID` and `basis_verified=false`.
- P3 now uses actual ratio-scaled MarketPort rows, all five tokens, the pinned EQUAL_WEIGHT rehearsal profile and
  stock-flat96USDT/0.005325625054330011BNB. Cost values and exact-size quotes are **offline stubs**, using recorded
  implied quote prices with synthetic timestamps; they do not prove real time availability, route validity, gas or
  execution. A BUY reaches the planner; an added20bp fee is refused by `COST_RESERVE_INSUFFICIENT`.
- CAP-02 ceilings are unchanged. Ratio-scaled marks reduce target BUY token quantities at fixed equity, while they
  can raise the notional of existing holdings and change split/rounding boundaries. The planner and execution/signing
  caps still enforce their finite limits; this review grants no blanket numeric coverage for S1 or existing holdings.
  Re-capture exact request sizes/full exits and review the resulting profile/config hashes before run3 (SJ-11).
- The observed ticker pins, including `SKHY`, identify Binance's API strings. They do not certify a listing, share
  class, depositary ratio, independent share price, or a transferable training label. The issuer registry's existing
  UNVERIFIED security mapping is preserved. Tolerances are accepted only within Yao's dev-rehearsal decision here;
  final adoption remains Keith/Isaac's §6 decision.


PR262-RV01 validation and verdict: **PASS for the repository merge**, at pushed `a609b92b` (macOS/arm64,
Python3.12.14, all44 applicable pinned package versions match, pip check PASS). A single full suite against a fresh
isolated PostgreSQL14.24 instance passes **2507 tests /3929 subtests /10 expected skips /0 failures /0 errors** in
304.93s. Skips: systemd5, Linux bubblewrap3, optional private source fixture1, external market artifacts1. Focused
basis/port/planner coverage:19 tests /45 subtests PASS. [Verification receipt](../build/evidence/pr262-review-20261023.json)
records source/log/JUnit hashes. Earlier overlapping full runs shared one disposable database and had connection
failures; they are discarded, as are intermediate fee-fixture assertions. No application repair was needed after
R1/R2; final planner fixtures identify the actual earlier cost-reserve gate correctly.

GitHub Actions [run39914039956](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/39914039956)
could not start runtime, host-bundle or bootstrap jobs: each annotation says recent account payments failed or the
spending limit must increase. AWS matrix job cancelled. This is **not CI PASS** and supplies no Linux/systemd/bundle
or release qualification. The account owner retains Actions/billing restoration; the release coordinator retains
RC6 and run3 acceptance. This review accepts the source merge using the recorded full local validation; all §6 and
SJ-11 gates remain as stated above. Final result-record changes alter documentation/evidence only.
