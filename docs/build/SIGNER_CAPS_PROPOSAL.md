# Signer caps: Isaac's proposal for #44

**CP-01, 2026-10-17. Unapproved candidates.** Checklist task6 / #146.
**Isaac confirmed these candidates for Keith's review on 2026-10-17 (CP-01 D1).**
This completes the proposal/tool slice; installation approval and signer readiness
remain outstanding.
Keith reviews the actual profile, current quoted input quantities and holdings;
Isaac confirms the resulting policy. Yao installs/binds only an approved policy.
No host config, runtime limit, default signing policy or key is changed here.

## Proposed limits

| Setting | Development candidate | Final-wallet candidate |
|---|---:|---:|
| USDT input per approve/swap | 35 USDT | 70 USDT |
| Maximum fee per transaction (`gas * gasPrice`) | 0.0002 BNB | 0.0002 BNB |
| Payable tokens | USDT + the five pinned bStocks | Same |
| Native BNB | Receive-only for gas; no BNB-input permission | Same |
| Allowed spender | Only `0xb44446b0c8e56988c34f7ff73ae904982b5fdda5` | Same, subject to final router evidence |

The spender is the **router named by quote `tx.to` and approve
`dexContractAddress`**, not candidate implementation facet
`0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603`. The existing router observation
comes from EXP-005. Verified source/decoder evidence is still outstanding;
proposing this spender does not qualify its code or authorize a swap.

Rationale for USDT limits: current equal-weight profiles permit a full position
plus reserve of20.10/40.20 USDT for100/200 expected equity. Pending S1 code at
PR131 head `4b87036` uses
`ceil(equity * high * max_weight) + ceil(equity/1000)`; at proposed high95%
and maximum weight30%, that is28.60/57.20 USDT. Both fit35/70. This is nominal
coverage of those known examples, not approval of S1 or proof that any future
profile/capital/top-up amount fits. The strategy's smaller limits still apply.

## Per-token raw caps and reference provenance

Candidate stock-input limits use:

`ceil(USDT_input_cap * 10**token_decimals / (reference_price / 2))`

The50% reference-price floor is a **proposed sizing assumption**, not a market
prediction or guaranteed floor. It provides token-quantity headroom for sells
and lower-price entries. At that floor each cap covers35/70 nominal USDT;
at the original reference price it instead permits approximately70/140 USDT
of stock input. The USDT cap does not impose an equivalent value cap on sells.
Keith/Isaac can request tighter candidates, with the corresponding reduction
in quantity headroom.

| Token | Development maximum input, raw18-decimal units | Final maximum input, raw18-decimal units |
|---|---:|---:|
| USDT | 35000000000000000000 | 70000000000000000000 |
| NVDAB | 303543664881272184 | 607087329762544368 |
| GOOGLB | 198599352431777696 | 397198704863555392 |
| SKHYB | 410076157000585824 | 820152314001171647 |
| TSLAB | 182786714017129727 | 365573428034259453 |
| MSFTB | 130728070832380858 | 261456141664761715 |

These are per-request ceilings. Approves must still equal the exact intended
swap input; do not approve the ceiling merely because it is allowed. No
unlimited approval is introduced. Repeated individually valid requests can
exceed these amounts cumulatively: the current signer policy does not enforce
a daily loss, portfolio allocation or cumulative wallet-spend budget by itself.

The reference is the five public `tokenPrice`/decimals rows from retained
W08 `market/rwa/tokens` data at **2026-10-10T11:38:00.565Z**. Prices use the
project's USDT-money mark convention; they are historical marks, not executable
quote or fee-netting proofs. Public normalized rows and exact source-file /
response hashes are in
[signer-caps-reference-20261010.json](evidence/signer-caps-reference-20261010.json).
Raw evidence includes wallet/API context and remains ignored in `data/w08/`;
none of that context is copied into this proposal. Source hashes identify
retained bytes, not independent source or oracle verification.

**Units:** signer input caps are token base units, so35USDT is `35*10**18`.
Portfolio/profile money uses USDT micro-units, so the same35 is `35*10**6`
there. BNB fee units are wei:0.0002BNB = `200000000000000`. This fee ceiling
limits signed worst-case gas allowance per transaction; it is neither a
percentage, route trading fee, round budget nor a measured adequate fee.
Parent gas budgets remain separate and unchanged.

## Reproduce and inspect

The committed
[signer-caps-proposal-20261017.json](evidence/signer-caps-proposal-20261017.json)
is an offline `SignerCapsProposal.v1` wrapper. It is **not** a
`SignerService.v1` configuration and says `ready_to_install: false`.
Both embedded policies retain `EXAMPLE_PENDING_TEAM_DECISION`, which the
existing live-service validator refuses. Dev mode can accept example labels,
so the label alone is not a dev-mode installation barrier: do not copy a
candidate into the running config before approval. No host renderer reads this
proposal automatically.

From a committed/pushed revision, generate into a new file:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/deploy/propose_signer_caps.py \
  --reference docs/build/evidence/signer-caps-reference-20261010.json \
  --output /private/tmp/signer-caps-new-proposal.json
```

The builder has no network/key/service API. It strictly validates public
reference fields, chain/token identities, decimals and provenance, calculates
with exact rationals and rounds upward. The real `SigningPolicy` parser checks
each candidate. Output uses explicit UTF-8/LF bytes on every platform, so
Windows newline conversion cannot change the artifact hash. Output creation
is exclusive, mode0600 on POSIX, and refuses overwrite;
failures print a fixed status rather than arbitrary input values. Generated
public artifacts may be committed through review; private raw inputs may not.

## Approval and remaining checks

Keith must check the actual selected profile and raw quote/holdings quantities,
including all five sell positions and any gas-top-up input, against the exact
caps. The profile's per-trade cash cap alone cannot prove stock sell coverage.
Confirm token decimals/scales against current accepted metadata and compare
worst signed approve/swap gas limits times gas prices with the fee ceiling.
The kit's approximate historical gas costs do not establish that0.0002BNB
is sufficient for the deployed route or future gas prices.

Price drops below the assumed floor, splits/multiplier adjustments, position
accumulation or equity growth can exceed fixed token limits and block a full
sale. No automatic repricing or cap expansion is introduced. Existing
price-jump/balance-adjustment guards and their unresolved policies remain;
this proposal does not resolve them. Before activation, qualify the intended
adjustment scenarios, or revise the candidate limits/leg policy explicitly.
Per-leg splitting is not assumed to exist merely because it is planned in S1 B6.

After Keith's review and Isaac's confirmation, record a dated decision with
the exact chosen policy hash and profile/metadata/holdings evidence. If values
change, regenerate/retest the affected candidates through review. Yao then
uses the decided policy in `/etc/larp/signer.json`, records its actual decision
in `cap_basis`, binds the full config to the release manifest and completes
IDEA-080 provisioning/access checks. The final-wallet candidate requires its
own final-profile/fresh-wallet review; development approval does not approve it.

Router evidence, signing-lifetime #27, key placement, actual-host tests and
Gate B execution remain separate. #44 stays open for these numeric approval /
configuration requirements even after the proposal/tool slice #146 merges.

## Verification

Criteria CP1–CP5 pushed at `ff1fd6f`; tool/tests/reference pushed at `ebe8b74`
before execution. `python3 -m unittest tests.execution.test_signer_caps_proposal -v`
passes **7 tests, no skips** on macOS/Python3.13. Actual policy checks exercise
all six input-token boundaries, approve and swap, at cap and cap+1; fee equality
and fee+1; wrong spender/native input/value; non18-decimal exact rounding;
malformed/private fields; deterministic output, mode and non-overwrite.
The pushed builder generated the committed candidate without network access.
No signer service, wallet/key, signing, transaction, AWS or receiver was used;
no current-profile, Linux/CI or hosted/live qualification is claimed.
