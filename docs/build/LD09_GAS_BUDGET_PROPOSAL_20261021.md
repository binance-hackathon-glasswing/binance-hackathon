# LD09/LD10 — measured gas budget proposal (2026-10-21)

**Decision 2026-10-21 (Keegan): option B**, implemented as IDEA-061 LD09-B with candidates in
[`ld09b-gas-budget-profiles-20261021`](evidence/ld09b-gas-budget-profiles-20261021/README.md). The expected price is
0.064 gwei, pending Keith's #120 review. The rest of this document is the proposal as written.

Status: **PROPOSAL for Keith (LD09, #120), Isaac (LD10, #44) and Keegan (LD07 policy).** Nothing here changes a
profile, cap or config. It replaces the FALLBACK-based DC-01 action budget with figures computed from simulated gas,
and shows a coupling that blocks the rehearsal profile at the draft cap gas price.

**Revision 2 (same day, after IDEA-070 LD02d):** the first version used a maximum swap gas of 748,525 from BUY
simulations at one size. LD02d added SELL simulations and four sizes and found a BUY at 944,814 and a SELL at
930,548. Every table below uses the new maximum. The first version's figures remain in git history (`11890cb`).

## Inputs

| Input | Value | Source |
|---|---|---|
| Approve gas (max) | 55,243 (bStocks); USDT 46,588 | LD02b/LD02b-F1/LD02c simulations, IDEA-070 |
| Swap gas (max, BUY or SELL) | **944,814** (TSLAB BUY, 20 USDT); SELL max 930,548 (SKHYB, 10/20 USDT) | LD02d, 40 simulation attempts (39 successful), 10–100 USDT |
| Earlier swap observations | 423k–749k (LD02b/F1/LD02c BUY, minimum size) | IDEA-070 |
| MSFTB | routed per quote: RFQ refused at the first scheduled probe in LD02c (actual probe age not recorded); AMM-like (about 515k) in LD02d | LD02c, LD02d |
| Draft signer ceilings | `max_gas` 1,200,000; `max_gas_price` 160,000,000 wei (0.16 gwei) | SP-CAPS, #44 draft |
| Observed gas price | 0.05 gwei now; 0.053–0.062 gwei in the interim capture | LD02 packets, SP-CAPS |
| BNB price | 722.150988 USDT | DC-01 summary |

Pair gas = 55,243 + 944,814 = **1,000,057**. Swap gas varied across the sampled routes and sizes (TSLAB BUY ranged from
423k to 945k). This small sequential sample does not isolate the effects of size, route or time. So the budget has to cover the worst observed route, not a typical one. With 25 %
headroom the per-pair budget at gas price p is `G = ceil(1,000,057 × 5/4 × p)`.

**Cap margin (for Isaac, LD10):** 944,814 × 1.25 = 1,181,018, which is 1.6 % under `max_gas` 1,200,000. A route about
2 % heavier than the worst one seen would need either a higher cap or less headroom. The signer would refuse it, not
underfund it.

## What the profile formulas give

`validate_live` uses one value, `gas_action_budget_units`, both for the exit reserve (≥ 4G, S1 5G) and for the
minimum trade (the trade must cover G's USDT value inside the 50 bp cost budget). Computed with the profile's own
formula and the DC-01 spreads:

| Budget price | G (wei) | G in USDT | Min trade (all / without MSFTB) | Reserve 4G (EW) | Reserve 5G (S1) |
|---|---:|---:|---:|---:|---:|
| 0.05 gwei | 62,503,562,500,000 | 0.045 | 14.57 / 10.50 | 2.50e14 | 3.13e14 |
| 0.064 gwei | 80,004,560,000,000 | 0.058 | 18.64 / 13.44 | 3.20e14 | 4.00e14 |
| 0.08 gwei | 100,005,700,000,000 | 0.072 | 23.30 / 16.80 | 4.00e14 | 5.00e14 |
| 0.10 gwei | 125,007,125,000,000 | 0.090 | 29.13 / 21.00 | 5.00e14 | 6.25e14 |
| 0.12 gwei | 150,008,550,000,000 | 0.108 | 34.95 / 25.20 | 6.00e14 | 7.50e14 |
| **0.16 gwei (cap)** | **200,011,400,000,000** | **0.144** | **46.60 / 33.60** | **8.00e14** | **1.00e15** |

Current DC-01 profile: G = 76,177,634,176,000 wei (fallback-based), minimum 19.44 USDT.

**The blocking interaction:** LD07 criterion 2 asks for the reserve at the cap gas price. At 0.16 gwei the minimum
trade becomes 46.60 USDT (33.60 without MSFTB). That is above the rehearsal position (20 USDT: 100 USDT capital at
20 %) and also above the final profile's 40-USDT positions. `build_live_profiles` would refuse both ("Measured minimum
cannot fit a full position"). MSFTB's 17 bp DC-01 spread drives the worst case. LD02d measured MSFTB's round trip at
about 6.7 bp, so Keith may want to refresh that spread input.

## Options

- **A. One price, lower:** to fit the 20-USDT rehearsal with MSFTB, the budget price must be at most about 0.064 gwei
  (18.64 USDT). That is only 1.0–1.3× the observed price, so the reserve covers little price rise. Without MSFTB,
  0.08 gwei fits (16.80). The signer cap stays 0.16 gwei either way. No code change.
- **B. Decouple (recommended):** keep the exit reserve at the cap price (4G/5G at 0.16 gwei = 8.00e14 / 1.00e15 wei),
  and base the minimum-trade economics on a separate, sourced "expected" pair cost (for example 0.064–0.08 gwei). The
  reserve then covers the declared action-count/gas-price assumptions; it does not guarantee execution or full
  exit coverage. Actual child actions, cleanup, retries and unseen heavier routes still require review. Trade
  sizing uses an expected cost assumption rather than the reserve cap. This needs a small
  reviewed change in `validate_live`/`build_live_profiles` (a second sourced profile value) before the cut line.
- **C. Refresh or exclude MSFTB:** a refreshed MSFTB spread (LD02d suggests about 7 bp round trip, versus 17 bp in
  DC-01) or excluding MSFTB lowers the worst-case minimum to 33.60 USDT at the cap. That remains too large for the 20-USDT rehearsal position, while it is below the 40-USDT final EW position.
  Exclusion would require a separate universe/weight decision: PF-01 currently selects all five names. It is not
  adopted here.

## Seeding (LD07 criterion 3), at the cap price with margin 5/4

`seed = ceil(N × G × 5/4) + R`, G and R at 0.16 gwei (EW reserve R = 8.00e14 wei):

| Planned pairs N | Seed (wei) | BNB | ≈ USDT |
|---:|---:|---:|---:|
| 20 | 5,800,330,600,000,000 | 0.00580 | 4.19 |
| 40 | 10,800,615,600,000,000 | 0.01080 | 7.80 |
| 60 | 15,800,900,600,000,000 | 0.01580 | 11.41 |
| 100 | 25,801,470,600,000,000 | 0.02580 | 18.63 |

N (whole-run approve+swap pairs, including exits and expected failures) is Keith's strategy input. The development
wallet's recorded approximately 0.0027 BNB covers about 13 gross nominal pairs at the cap price, or 43 at
0.05 gwei, before retaining the separate exit reserve or adding cleanup/retry costs. Those are not spendable-action
counts or a seeding approval. Four/five nominal pairs do not prove exit-child coverage under appreciated holdings
and per-action caps; Keith/Isaac must enumerate the complete selected action set.

## Still not covered

- Simulated gas is not receipt gas. The first signed round (LD19/LD20) gives the first receipts to compare against.
- Reverts: a swap that reverts on chain still spends gas up to the revert. LD02c's RFQ routes were refused at the first scheduled probe (actual zero-age usability is unmeasured),
  and LD02d's MSFTB 40-USDT BUY reverted on its minimum return. A pre-sign simulation of the exact calldata (not
  implemented) can detect some failures at the checked state; later state changes, timing and routing still permit
  on-chain reverts and gas costs.
- LD06 cleanup approvals (zero allowance) cost about one approve each; add them to N if cleanup is enabled.
- Five symbols × four sizes is still a small sample of routes. A heavier route than 944,814 may exist.

## Review clarification — LD02cd-RV01

This is a proposal using observed simulated gas, not an approved numeric policy.
Its 25% headroom is proposed here; PF-01's earlier 20% direction does not itself
approve these new budgets or signer caps. PR216 separately records Keegan's
option-B implementation; Keith #120 and Isaac #44 acceptance still remain.
Historical LD02c packets store nominal delay labels, not actual probe ages; do
not infer a zero-second RFQ lifetime. Future collectors now record actual ages.
Original packet bytes and the Q2 FAIL/Q2b amended PASS remain unchanged.

## CAP-02 scope and exact-action rounding

CAP-02 approves finite signer input/fee ceilings, not these deployment action
budgets. The recorded formula rounds a fractional total fee; independently
rounding gas limits gives ceil(55,243*1.25)+ceil(944,814*1.25)=1,250,072gas,
which costs200,011,520,000,000wei at0.16gwei (120,000,000wei above the recorded
pair budget). The exact selected signed child limits, any cleanup/retries and
number of exit children must be summed before deployment acceptance. Two
transactions each at max_gas1,200,000 cost384,000,000,000,000wei at the cap,
also above this proposed pair budget. The builder accepts a sourced larger
action budget; these historical candidates are retained unchanged.
