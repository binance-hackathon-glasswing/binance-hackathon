# LD10-P01 — Isaac's priority-1 coverage review, 2026-10-21

**Offline candidate verification PASS; actual LD10 coverage BLOCKED.** Review
base canonical `f10d9ad`; prospective criteria `e3b82e5`, verification code
`7e371d8`, both pushed before verification. This review stops before the user's
separate priorities 2 (gas/action/exit budgets), 3 (router replay/preflight) and
4 (signer assembly). No profile or signer configuration is adopted or installed.

## Results

Both RV120-02 candidate files reproduce byte for byte using the production
builder, pass production `validate_live`, and retain their published file and
StrategyProfile.v1 hashes. CAP-02 evidence/policy hashes reproduce, and the real
`SigningPolicy` validator accepts the approved policies.

| Check | Rehearsal | Final candidate |
|---|---:|---:|
| Baseline | EQUAL_WEIGHT | EQUAL_WEIGHT |
| Full target plus cash reserve | 20.10 USDT | 40.20 USDT |
| Approved USDT input ceiling | 35 USDT | 70 USDT |
| Cash coverage | PASS | PASS |
| Configured maximum transaction fee | 0.000192 BNB | 0.000192 BNB |
| Independent signer fee ceiling | 0.0002 BNB | 0.0002 BNB |
| Transaction fee ceiling coverage | PASS | PASS |
| Current complete holdings / fresh quotes | NOT_RUN_MISSING_INPUTS | NOT_RUN_MISSING_INPUTS |
| Deployment acceptance | false | false |

The fee comparison uses CAP-02's retained execution ceilings, not an actual new
execution.json. It does not establish a full-action or exit reserve. Fee netting
under #119 remains UNVERIFIED. Neither the historical raw DC-01 export nor a
current private wallet packet is present locally; this verification reproduces
the public derived candidates, not raw capture observations or new measurements.

### Final calendar mismatch — not accepted

The rebuilt final candidate is intentionally byte-identical to historical LD09-B.
Its generator's midnight gates have not been reconciled with selected PF-04:

| Gate | Candidate UTC | Selected PF-04 UTC |
|---|---|---|
| First buy | Oct 29 00:00 | Oct 29 14:00 |
| New risk ends | Nov 9 00:00 | Nov 9 21:00 |
| Flatten starts | Nov 10 00:00 | Nov 10 19:00 |
| Signing ends | Nov 11 14:45 | Nov 11 14:45 |

Keith/Keegan own the already-recorded generator/S1/calendar/DR14 reconciliation.
Retain historical files; regenerate and qualify the selected final profile
before accepting its hash. This is not a new preference question or a defect in
the rehearsal's separately reviewed October23/25/26 window. Qualified S1 remains
preferred; a reproduced EQUAL_WEIGHT candidate does not establish its adoption.

## Packet search and missing inputs

On Isaac's instruction, searched all-state PRs for `GateBCapsInputs`,
`GateBCapsInputs in:comments`, `signer assembly` and `LD10`; checked #44/#120
and the #184/#193/#205/#210/#211/#216/#228/#229 handoffs. The checkout and usual
temporary locations contain no identified current manifest/config/holdings packet.

- [PR184](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/184)
  delivers the assembler and explicitly records real assembly NOT_RUN_MISSING_INPUTS.
- [PR193](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/193)
  inventories missing inputs; it does not supply them.
- [PR205](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/205)
  contains an October20 sanitized operator snapshot with reconciled holdings and
  request-bound quotes. It is historical evidence, not the current signed-run
  execution.json, original fresh quote artifacts or four-file manifest.
- [PR216](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/216)
  approves numeric ceilings only; deployment coverage remains open.
- [PR229](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/229)
  supplies rebuilt candidates, explicitly leaving owner confirmation, holdings,
  fees and signed-action coverage outstanding.

No current usable packet was identified. As Isaac instructed, treat it as missing
for this review; do not reinterpret a historical snapshot as current evidence.

The packet is a manifest that hashes four private local files plus original quote
artifacts. The existing [GateBCapsInputs.v1 contract](../../GATE_B_REMAINING.md#current-input-signer-cap-review)
remains authoritative; this review adds no replacement format.

| Next owner | Exact result needed |
|---|---|
| Keith + Isaac (#120) | Confirm the selected measured rehearsal profile and exact file/document hashes; record S1 versus permitted fallback scope, calendar and unresolved #119 fee assumptions. For final, reconcile PF-04 first. |
| Keegan's approved operator | Supply current reconciled full `PortfolioState.v1` (all five stocks, cash, exact BNB, metadata, reservations) and nonce/in-flight evidence; original fresh wallet/request-bound BUY/SELL artifacts for every name. No funding or host operation is authorized by this review. |
| Keegan / release operator | Supply intended execution.json and pinned CA/policy paths with actual run/build/wallet/environment/database identity. Do not substitute the retired unsigned run. |
| Isaac after those inputs | Assemble the existing four-file manifest with approved CAP-02 policy bytes and an explicit applicable freshness budget; run the production caps reviewer at the current clock, retain the private report and accept only genuinely covered inputs. |

The separate gas/cleanup/full-exit/seeding, router replay, qualified release and
host/session gates remain. None is closed by this public inventory. #119 actual
receipt confirmation follows LD19/20; it is not a prerequisite to the same first
round being used to collect it, and fee zero is not silently accepted here.

## Reproduce

From the repository root, without installing dependencies or contacting a service:

```sh
PYTHONPATH=. python3 docs/build/evidence/ld10-profile-coverage-20261021/verify.py
```

[Machine-readable result](review.json) retains exact public input/profile/policy
hashes and false readiness/signing/Gate B flags. Executed on macOS arm64,
Python3.13.3. A second run is byte-identical; public input hashes, new local links,
false flags and whitespace checks pass. Report SHA-256:
`3bf41478138a53f9185f3f296759773c63f6b084a40894f92c2d8476bf4b749b`.
This is production-builder/validator verification, not a full test
suite, raw-data replay, CI result, fresh caps review or actual-host acceptance.
