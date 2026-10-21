# LD10-P02 — review of merged rehearsal coverage

**BLOCKED_EXECUTION_CASH_CAP.** PR231 and canonical RC2 supply the previously
missing recorded inputs, but the independent review finds one execution-limit
mismatch. PR230's updated review and checker fix are ready for independent review;
full LD10 owner/deployment acceptance is not complete.

Criteria75a453c/R1 tests6671132 and86e8b74 were pushed before verification.
Normal merge32691c4 incorporates canonical6ec07ba. Original P01, Q01 and RC2
evidence stays unchanged; no historical PASS is rewritten as a new test result.

## What passed

- Selected deterministic rehearsal profile reproduces byte for byte, file
  SHA-256 `41332056bf18e9f07a35f0d4446e2fb02a3d7ebbddabd25b054e03203c3a0a7a`,
  document `eb61ca8646a42cfb59816888576555d10e8aef3502d973ae06e00daacc6670a4`.
- Production LIVE validation, real effective SHADOW authority and CAP-02 policy
  loading/hash/scope pass. Cleanup remains disabled and no hosted model is adopted.
- All50 published numeric rows agree with the policy/profile/recorded holdings
  and quantities. The operator recorded MATCH, nonce2/2, zero allowances and no
  inflight state at14:10:31UTC. This is a dated observation, not current state.
- The new15 execution-cash comparisons pass for14 quotes; the remaining one is
  the NVDAB max-position SELL below.
- Two-child budget0.000384BNB, four-exit reserve0.001536BNB and sizing budget
 80,004,608,000,000wei reproduce. Reported N15-plus-four-exits planning target
  0.007296BNB and additional0.004601501130637114BNB are arithmetically consistent.
  They do not prove a maximum action count or authorize funding.

The public report verifies the committed operator projections and reported
arithmetic. The private original packet/projections are hash-identified but
not available for independent local replay; no original observations are
fabricated and no fresh-clock caps run is claimed. Fee netting remains subject
to the actual LD19/20 receipt comparison.

## P02-R1 — signer coverage omitted the existing execution cash cap

| Recorded Q01 max-position NVDAB SELL | Raw18-decimal USDT | USDT |
|---|---:|---:|
| Quoted proceeds |20,106,983,099,120,719,276|20.106983099120719276|
| Profile execution cash cap |20,100,000,000,000,000,000|20.10|
| Excess |6,983,099,120,719,276|0.006983099120719276|

Its stock input fits the signer's independent raw token ceiling, which is why
the old numeric review could report COVERED. Production `LiveVenue.quote`
already refuses this result as `fresh quote exceeds execution cash cap`.
The planner likewise requests a smaller quote instead of admitting an
over-cap child. That is a safe refusal, not an executed loss or an attempt to
spend above the cap.

The missing check is now added to `larp.execution_live.caps_review`: compare
BUY USDT input and SELL quoted USDT output with the profile cash cap, matching
the existing execution behavior. This does not loosen any trade/signing limit.
Assembler uses that real numeric review, so an incompatible quote cannot yield
a signer.json candidate.

The max-position sample is derived from a hypothetical maximum BUY. The recorded
actual stock holdings are zero. It does **not** describe a currently trapped
wallet position. It does show that the supplied full-size sample is insufficient
to accept a one-action exit plan for that size. Do not silently replace it with
a smaller partial-position quote, assume the residual is executable dust, or
claim four one-action exits are fully qualified.

## Remaining work and owners

1. Keith/Keegan supply a reviewed exit-sizing/requote/splitting disposition that
   preserves existing limits and covers the entire position, including any
   residual/dust and all actual child transactions, gas and authority timing.
   Recompute reserve/count assumptions if more economic actions are required.
2. Approved operator captures the applicable fresh complete holdings and original
   request-bound quotes for that plan; Isaac reruns the real coverage review and
   records acceptance only if all required checks pass.
3. LD16 binds the intended actual release/run/wallet/DB/RPC/CA/configuration and
   reservations. The recorded numeric build/run is not that installed identity.
   LD17 host/session, funding disposition, LD18 key and LD19/20 actual fees/ACK
   remain separate. Final S1/final-wallet coverage is outside this review.

## Verification

- RED at86e8b74: four over-cap BUY/SELL subcases incorrectly reported COVERED;
  exact-cap cases passed. Real LiveVenue refusal of the retained SELL numbers
  reproduced using explicitly synthetic wire shape/ports.
- Fixe8cd3b6; final executable/test sourcef816e28: **87 tests/103 subtests PASS,
  zero skips**, macOS arm64/Python3.12.14. Includes independent policy boundaries,
  caps, assembly, profile authority, split-budget and initial-only consumers.
- New assembler regression proves over-cap cash quotes cannot generate a
  configuration. No full-suite, new CI or signed-host acceptance is claimed.
- [Machine review](review.json) records exact input hashes,15 cash comparisons
  and false acceptance/readiness/signing flags. The original50-row result and
  original RC2 CI/artifact bytes remain historical evidence for their commits.
- Repeat output is byte-identical; selected input hashes match canonical and
  original P01 JSON bytes are unchanged. New local links/whitespace pass. Report
  SHA-256 `9f535602ff0d8543c6d8ad15c35052d0842c19418abe5be5128873197b6a27f0`.

Reproduce the public arithmetic/compatibility review without private inputs:

```sh
PYTHONPATH=. python3 docs/build/evidence/ld10-owner-review-20261021/verify.py
```

No AWS/SSM/DB, new network request, key, funding, trade, deployment or signer
assembly operation was performed. Existing synthetic assembly tests do not
constitute an actual signer candidate or installation approval.
