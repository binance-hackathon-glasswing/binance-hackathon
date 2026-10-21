# #120 — owners' review of the DC-01 quote-cost summary (RV120-01, 2026-10-21)

Status: **prepared in Keegan's session; Keith independently reproduces the distributions and supports the 17 bp
MSFTB spread (PR226 review5602037122). His two interpretation corrections are applied below as RV120-RV01.
Exact selected-profile/owner acceptance remains separate.**
Nothing here pins a profile, changes a config, approves a cap or starts trading.

- Input: the DC-01 capture. That is four daily JSONL files (Oct 16–19 UTC) with manifest `b17002b0…ffc01`, the same
  bytes as Keith's ZIP-01 archive on the `capture` branch. Its committed summary is `QuoteCostSummary.v1`
  `407a08e7…6ecd` (DC-01-R1 reproduces it byte for byte).
- Analysis: [`analyse.py`](evidence/rv120-quote-review-20261021/analyse.py) runs offline on the raw files with the
  repository's session calendar. Output: [`distributions.json`](evidence/rv120-quote-review-20261021/distributions.json).

## 1. Coverage — PASS

| | Value |
|---|---|
| Window | 2026-10-16 18:19:09Z to 2026-10-19 23:57:06Z; 4 UTC days, both weekend days (Oct 17–18) |
| Samples | 1,924 bStock samples and 385 BNB quotes; 2 recorded failures (Oct 18 authentication round, Oct 19 MSFTB sell quote) |
| Per token and regime | 42–43 US-session and 342 off-session per token (minimum is 10); MSFTB has 384 in total |
| `openState` | `true` on every sample in both regimes (no `false` or missing) |
| Gas estimates | all 3,848 are FALLBACK, so the capture holds no usable gas; see §5 |

## 2. Quote size against the per-trade caps — PASS

Every sample quotes **40 USDT**. That is the final profile's full 20 % position of 200 USDT; its per-trade cap is
40.2 USDT. The rehearsal position is 20 USDT (cap 20.1 USDT). LD02d's size sweep (IDEA-070, 10/20/40/100 USDT,
all five tokens) showed no size dependence in quoted round-trip cost, and impact at 40 USDT is about 0 bp. So the
40 USDT figures apply to the 20 USDT rehearsal size as well.

## 3. What is behind each summary value

The summary keeps, per token, the **worse** of the US-session and off-session values (the tokens trade 24/7).
Round trip is `(pay − sell proceeds) / pay`; the spread is that minus the two quoted impacts.

| Token | Summary spread bp | US median / p90 round trip | Off-session median / p90 round trip | Impact median | Drift p90 (15 s requote), US / off |
|---|---:|---|---|---:|---|
| GOOGLB | 3 | 0.68 / 1.65 | **2.91** / 5.07 | ≈0 → 1 bp floor | 3.9 / 1.1 |
| MSFTB | **17** | 6.99 / 32.7 | **16.99** / 27.8 | ≈0 → 1 | 7.1 / 0.9 |
| NVDAB | 4 | 1.11 / 2.73 | **3.63** / 7.05 | ≈0 → 1 | 5.1 / 2.7 |
| SKHYB | 2 | 1.13 / 1.83 | **1.88** / 3.86 | ≈0 → 1 | 7.9 / 6.3 |
| TSLAB | 5 | 0.68 / 2.28 | **4.20** / 7.07 | ≈0 → 1 | 5.6 / 2.2 |

- **MSFTB's 17 bp is correct and current: it is its off-session spread.** In US hours its median is 7.0 bp,
  which matches LD02d's 6.7 bp, measured at 18:45 UTC (US session). That earlier reading is therefore **not** a
  reason to lower MSFTB's spread. The LD09-G1 suggestion to "refresh MSFTB to about 7 bp" is withdrawn. MSFTB also
  has the fattest tails: US p90 is 32.7 bp and the maximum is 50.3 bp.
- Every off-session spread is wider than its US-session one, so the worse-of rule picks the off-session value for
  all five tokens.
- Impact is negligible at this size. The 1 bp floor and `impact_bps = min(50, 2 × median) = 2` are conservative.

## 4. The 50 bp entry-cost cap — PASS at the sizing price; gas-sensitive at small sizes

Entry cost uses the profile formula `spread + min(50, 2 × impact) + fee + pair gas / size`, with pair gas
1,000,057 × 5/4 (LD09-B):

| Gas price | Size | GOOGLB | MSFTB | NVDAB | SKHYB | TSLAB |
|---|---:|---:|---:|---:|---:|---:|
| 0.064 gwei (sizing) | 18.64 | 36.0 | **50.0** | 37.0 | 35.0 | 38.0 |
| 0.064 gwei | 20 | 33.9 | 47.9 | 34.9 | 32.9 | 35.9 |
| 0.064 gwei | 40 | 19.4 | 33.4 | 20.4 | 18.4 | 21.4 |
| 0.16 gwei (cap) | 20 | 77.2 | 91.2 | 78.2 | 76.2 | 79.2 |
| 0.16 gwei | 40 | 41.1 | 55.1 | 42.1 | 40.1 | 43.1 |

- **Gas dominates at rehearsal size.** One approve+swap pair costs about 0.058 USDT at 0.064 gwei, which is
  29 bp of a 20 USDT trade. The minimum trade (18.64 USDT) is exactly where MSFTB reaches 50 bp; this is by
  construction.
- At 20 USDT, MSFTB sits at 47.9 bp. Any gas above about 0.07 gwei, or an off-session tail, takes it over the cap,
  so **expect most rehearsal-size MSFTB entries to be refused by the cost gate.** At the final 40 USDT size every
  token passes at the sizing price.
- If gas rises toward the 0.16 gwei cap, the gate refuses 20 USDT entries. That is the intended safe outcome
  (LD09-B); the reserve still covers exits at that price.
- Exits aren't under the 50 bp entry cap. They are covered by the reserve, which is sized at the cap price.

## 5. Slippage, fee and gas

- **Slippage 8 bp** follows the worst token/regime's rounded p90 of **two-sided absolute** 15 s requote drift.
  That statistic includes favourable moves that increase the quoted BUY output. For an adverse comparison,
  count only `(initial BUY output - later BUY output) / initial BUY output > 8 bp`, using exact integer arithmetic.

  | Token | US absolute | US adverse | Off-session absolute | Off-session adverse |
  |---|---|---|---|---|
  | GOOGLB | 0/43 | 0/43 | 0/342 | 0/342 |
  | MSFTB | 4/42 (9.5%) | **1/42 (2.4%)** | 4/342 (1.2%) | 1/342 (0.3%) |
  | NVDAB | 1/43 (2.3%) | 0/43 | 1/342 (0.3%) | 1/342 (0.3%) |
  | SKHYB | 4/43 (9.3%) | **2/43 (4.7%)** | 23/342 (6.7%) | **10/342 (2.9%)** |
  | TSLAB | 2/43 (4.7%) | 2/43 (4.7%) | 3/342 (0.9%) | 2/342 (0.6%) |

  These are counterfactual quote-output comparisons, including the adverse subset; they are neither executed
  reverts nor a measured transaction revert frequency. [Directional counts and input hashes](evidence/rv120-quote-review-20261021/directional-drift.json)
  reproduce Keith's correction. The original absolute-drift distributions remain unchanged.
  - LD02d observed a `Min return not reached` simulation refusal. Mandatory exact-calldata prepare-time gas
    estimation (KG-DEC-01-C1) can refuse that payload before signing/broadcast; no transaction gas is spent then.
    A successful simulation does not guarantee the later execution or its economics.
  - **Minimum-output and recipient enforcement remain accepted, unverified router assumptions** in the selected
    API-trusted/untrusted mode (`larp/execution_live/untrusted_router.py`). An abnormal fill remains possible.
    Canonical settlement detects supported abnormal movements after execution, records raw deltas/actual gas and
    sustains signing quarantine (LD05-Q01); it cannot prevent or reverse that fill or prove a maximum loss bound.
  - **Keep the selected 8 bp setting**; measure actual simulation refusals, on-chain outcomes and revert frequency
    separately at LD19/LD20. Neither directional quote count changes that policy or establishes future frequency.
- **Fee (#119):** the quoted round trip comes from actual quoted amounts, so any route fee netted into those
  amounts is already inside the spread. `fee_bps = 0` is valid **only if** fees are netted (UNVERIFIED);
  `tradeFee` is network-fee metadata. The capture can't settle this. The first agent quote-versus-receipt
  comparison (LD19/LD20, Isaac) does.
- **Gas:** the capture's FALLBACK estimates are not used. The LD09-B budgets come from the LD02b–LD02d simulations
  (max swap 944,814 gas) and are already in the candidates.

## 6. Recommendations for the owners (proposals, not pinned)

1. **Accept DC-01 as the profile's quote-cost input,** with MSFTB at 17 bp, `impact_bps` 2, slippage 8 bp, quote age
   30 s, fee 0 subject to #119, and gas from LD09-B. Coverage and every value are explained above.
2. **Rehearsal profile: the measured EQUAL_WEIGHT fallback** (the LD09-B candidates), unless frozen S1 weights
   exist before the window opens. S1's `freeze-weights` needs token price series; this quote capture doesn't
   contain them (IDEA-075/076, Keith).
3. **New rehearsal window (DEV-24).** The current one (buy Oct 21–22) has passed. Proposed:
   - `trade_after` 2026-10-23T00:00Z;
   - `new_risk_end` 2026-10-25T00:00Z (two entry days including Saturday Oct 24);
   - `flatten_start` 2026-10-26T00:00Z;
   - `signing_end` 2026-10-26T14:45Z (unchanged).

   This keeps the rehearsal finished before the final-wallet transition (Oct 27–29). If the first signed round
   (LD19) can't start by Oct 23, shift `trade_after` and `new_risk_end` and keep the end date. The window is the
   `WINDOWS` constant in `larp/strategy/profiles.py`, so changing it means rebuilding the candidates (Keith).
4. **Seeding N** (whole-run approve+swap pairs, including exits and failures; seed = N × G × 5/4 + reserve at
   0.16 gwei):
   - **Rehearsal: N ≈ 15** (4 entries, 4 exits, about 2 top-ups or re-entries, ×1.5 for reverts and retries). That
     is ≈ 0.0046 BNB. The dev wallet holds about 0.0027 BNB, so it needs an F-120 dev top-up first.
   - **Final: N ≈ 30** (5 entries, about 4 top-ups, about 2 red-flag exits, 5 flatten exits, about 2 re-entries,
     ×1.5). That is ≈ 0.0083 BNB, about 6 USDT. Add about 5 pairs if LD06 cleanup is enabled.

   These are planning estimates for Keith to set; each step's gas is capped by the signer limits (CAP-02).
5. **Watch at LD19/LD20:** the actual entry cost, the MSFTB refusal rate, the `Min return not reached` revert rate,
   and fee netting (#119).

Not covered by this review: S1 weights and parameters; actual fills; the final-run calendar; holdings coverage for
#44 (Isaac, LD10).

RV120-RV01 sources: [Keith's P1](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/226#discussion_r4338622249),
[P2](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/226#discussion_r4338622255) and
[review](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/226#pullrequestreview-5602037122).
The original proposals and gas/seeding numbers above retain RV120-01's dated context; the selected deterministic
profile, corrected signed-child envelope and conservative0.007296BNB target are recorded in
[LD10-Q01-R1](evidence/rehearsal-qualified-inputs-20261021/README.md). No current profile or funding amount changes here.
