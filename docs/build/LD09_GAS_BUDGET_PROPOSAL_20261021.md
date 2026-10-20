# LD09/LD10 — measured gas budget proposal (2026-10-21)

Status: **PROPOSAL for Keith (LD09, #120), Isaac (LD10, #44) and Keegan (LD07 policy).** Nothing here changes a
profile, cap or config. It replaces the FALLBACK-based DC-01 action budget with figures computed from simulated gas,
and shows a coupling that blocks the rehearsal profile at the draft cap gas price.

## Inputs

| Input | Value | Source |
|---|---|---|
| Approve gas (max) | 55,243 (bStocks); USDT 46,588 | LD02b/LD02b-F1/LD02c simulations, IDEA-070 |
| BUY swap gas (max) | 748,525 (SKHYB); GOOGLB ≤ 731,144; NVDAB ≤ 731,150; TSLAB ≤ 731,976 | same, six runs |
| MSFTB swap | not executable (`RFQ_OrderExpired` at 0 s) | LD02c R2, replicated |
| SELL swap gas | **not simulated** (wallet holds no bStocks) | open |
| Draft signer ceilings | `max_gas` 1,200,000; `max_gas_price` 160,000,000 wei (0.16 gwei) | SP-CAPS, #44 draft |
| Observed gas price | 0.05 gwei now; 0.053–0.062 gwei in the interim capture | LD02 packets, SP-CAPS |
| BNB price | 722.150988 USDT | DC-01 summary |

Pair gas = 55,243 + 748,525 = **803,768**. With 25 % headroom on the simulation, the per-pair budget at gas price
p is `G = ceil(803,768 × 5/4 × p)`. All 1.25× headroom swap limits (≤ 935,657) sit under `max_gas` 1,200,000.

## What the profile formulas give

`validate_live` uses one value, `gas_action_budget_units`, both for the exit reserve (≥ 4G, S1 5G) and for the
minimum trade (the trade must cover G's USDT value inside the 50 bp cost budget). Computed with the profile's own
formula and the DC-01 spreads:

| Budget price | G (wei) | G in USDT | Min trade (all / without MSFTB) | Reserve 4G (EW) | Reserve 5G (S1) |
|---|---:|---:|---:|---:|---:|
| 0.05 gwei | 50,235,500,000,000 | 0.036 | 11.70 / 8.44 | 2.01e14 | 2.51e14 |
| 0.064 gwei | 64,301,440,000,000 | 0.046 | 14.98 / 10.80 | 2.57e14 | 3.22e14 |
| 0.08 gwei | 80,376,800,000,000 | 0.058 | 18.72 / 13.50 | 3.22e14 | 4.02e14 |
| 0.10 gwei | 100,471,000,000,000 | 0.073 | 23.41 / 16.87 | 4.02e14 | 5.02e14 |
| 0.12 gwei | 120,565,200,000,000 | 0.087 | 28.09 / 20.25 | 4.82e14 | 6.03e14 |
| **0.16 gwei (cap)** | **160,753,600,000,000** | **0.116** | **37.45 / 27.00** | **6.43e14** | **8.04e14** |

Current DC-01 profile: G = 76,177,634,176,000 wei (fallback-based), minimum 19.44 USDT.

**The blocking interaction:** LD07 criterion 2 asks for the reserve at the cap gas price. At 0.16 gwei the minimum
trade becomes 37.45 USDT (27.00 without MSFTB). A rehearsal position is 20 USDT (100 USDT capital, 20 %), so
`build_live_profiles` refuses the rehearsal profile ("Measured minimum cannot fit a full position"). The final
profile (40 USDT positions) still fits, barely. MSFTB's 17 bp spread is what drives the worst case.

## Options

- **A. One price, lower:** budget everything at about 0.08 gwei (1.3–1.6× the observed price). The rehearsal fits
  (18.72 USDT). The signer cap stays 0.16 gwei, so if prices doubled, the reserve would pay for about half the exits
  it was sized for. No code change.
- **B. Decouple (recommended):** keep the exit reserve at the cap price (4G/5G at 0.16 gwei = 6.43e14 / 8.04e14 wei),
  and base the minimum-trade economics on a separate, sourced "expected" pair cost (for example 0.08 gwei). The exit
  guarantee then holds at the signer's worst case, and trade sizing reflects realistic cost. This needs a small
  reviewed change in `validate_live`/`build_live_profiles` (a second sourced profile value) before the cut line.
- **C. Exclude MSFTB from the universe for now:** it is unexecutable anyway. That lowers the worst-case minimum
  (27.00 USDT at the cap), but alone does not fit the rehearsal at 0.16 gwei. It combines with A or B.

## Seeding (LD07 criterion 3), at the cap price with margin 5/4

`seed = ceil(N × G × 5/4) + R`, G and R at 0.16 gwei (EW reserve R = 6.43e14 wei):

| Planned pairs N | Seed (wei) | BNB | ≈ USDT |
|---:|---:|---:|---:|
| 20 | 4,661,854,400,000,000 | 0.00466 | 3.37 |
| 40 | 8,680,694,400,000,000 | 0.00868 | 6.27 |
| 60 | 12,699,534,400,000,000 | 0.01270 | 9.17 |
| 100 | 20,737,214,400,000,000 | 0.02074 | 14.98 |

N (whole-run approve+swap pairs, including exits and expected failures) is Keith's strategy input. The development
wallet's current 0.0027 BNB covers 16 pairs at the cap price, or 53 at 0.05 gwei.

## Still not covered

- SELL swap gas: estimate once a position exists (first signed round, LD19), or by simulation with a token balance
  override after proving that token's balance slot (not attempted).
- Reverts: a swap that reverts on chain still spends gas up to the revert. RFQ routes revert even at 0 s, so a
  pre-sign simulation of the exact calldata (not implemented) would avoid paying for them.
- LD06 cleanup approvals (zero allowance) cost about one approve each; add them to N if cleanup is enabled.
