# Scoped rehearsal inputs — LD05-Q01 / LD10-Q01 / LD11-RH01

Keegan requested steps 2–4 and selected the deterministic fallback rehearsal. This
packet carries technical coverage, not installation or signer-session approval.

- Profile: `rehearsal-live.json`, file SHA-256 `bad7f160bd55c0d40736ee434e7c253ff9d85d7706ac85addfe738659e7a9934`,
  StrategyProfile.v1 `43f956afe7a832e06146bdcdd8e3e725b7b6032541bec5aaab578cd5bb530258`.
- CAP-02 development policy: `3241abd36dfeb216ffe3bb06a3ce800f42e8206ccc261240da6f059b0dd5ea61`.
- Reviewed router policy: `05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5`.
- `rehearsal-scope.json` records required runtime settings and excludes hosted-model routing.
- `coverage-decision.json` records current holdings, nonce, zero allowances, all 15
  quotes (minimum/max BUY and max-position SELL for each name), 50 covered numeric
  checks, exact hashes and residual gates. Request-bound projections preserve exact
  numeric fields and original response/record hashes; duplicate raw response bodies,
  calldata and unrelated metadata are omitted from this private numeric projection.
  Calldata was independently decoded/tamper-tested in memory: 15/15 PASS.

The primary-host read-only packet at 2026-10-21 13:51 UTC reconciled 98 USDT,
0.002694498869362886 BNB and zero holdings of all five bStocks. Latest/pending nonce
2/2, no reservations or pending executions, all router allowances zero. Token scales
are 18. Host build `ea25b52` remains the old shadow deployment, not this release.
The private exact numeric review at 13:52 UTC reported COVERED, no missing pairs,
50/50 checks covered. Its OWNER_REVIEW_REQUIRED remains explicitly visible; technical
review under Keegan's delegation is distinct from Isaac's personal deployment signoff.

Gas: 1,200,000 per-child gas × 0.16 gwei, two children per action = 384,000,000,000,000
wei. Four exits reserve 1,536,000,000,000,000 wei; cleanup disabled. Expected-price
minimum sizing stays decoupled at 80,004,608,000,000 wei (0.064 gwei with corrected
rounding), keeping the minimum 18.637420 USDT feasible. The reserve/action change
covers both configured child maxima, replacing the earlier nominal pair budget.
For N=15 whole-run pairs plus reserve, conservative seed target is **0.007296 BNB**;
additional funding against this snapshot is **0.004601501130637114 BNB**. No funding
was performed. Fresh post-funding balances remain required.

LD11 scope: EQUAL_WEIGHT, deterministic assessor, model evidence SHADOW, no hosted
model calls or discretionary model exits; deterministic red-flag and risk controls
remain. This is a development rehearsal decision, not scored-model adoption.
LD05: ABNORMAL finalized receipts retain exact raw signed token deltas and actual
gas, immutable journal incident and sustained signing quarantine. Assets remain
explicitly unreconciled; no normal fill or realized P&L is invented. Economic views
refuse unresolved outcomes. Missing finality/malformed proof and unsupported native
outcomes still refuse; no automatic resume/repair is added.

Reproduce profile offline (fresh path):

```sh
python -m tools.deploy.build_rehearsal_candidate --output /tmp/rehearsal-profile-check.json
```

`ld10_readonly_packet.py` generates the in-memory-only primary collector;
`review_rehearsal_caps.py` creates private pinned numeric inputs and report, never
signer.json. Keep private packets/review files outside Git; public hashes above bind them.
Pre-install checks must use fresh state and the final release/run/DB/RPC/CA identity.

Remaining: Keith/Isaac exact #120 confirmation/personal deployment coverage acceptance,
#119 actual receipt fee check at LD19/20; LD16 private config bindings and owner check;
LD17 approved install/session; LD18 key; funding; LD19 bounded round. PS-01 optional
extra RPC eth_call is deferred; existing mandatory exact-calldata prepare gas simulation
remains selected. LD24 final S1/model/deviation/final-wallet choices remain separate.
