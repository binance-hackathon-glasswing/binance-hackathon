# Run-3 S1 REHEARSAL profile (IDEA-049-C SJ-11-RH01-P1, 2026-10-23)

The candidate `StrategyProfile.v1` for signed dev rehearsal run 3, which trades S1 `TREND_GUARDED_VOL` instead of the
equal-weight fallback (IDEA-049-C SJ-11). It is a **candidate for review**. It is not approved, installed or bound to a
`signer.json`. Isaac's approval of this hash and of the reassembled `signer.json` is still required (SJ-11).

| File | SHA-256 |
|---|---|
| `s1-block.json` (the profile's `s1` block) | `0ee110d4f048bec156c6ce16a8d125cf1e94fedcb14fb68aa2044b32fd687e7d` |
| `rehearsal-s1-deterministic.json` (file bytes; the `selected_profile_sha256` / `PROFILE_SHA` to pin) | `6bcf1dfbd7f0c29893dd62bf67d9bcf7a04299b1d24a29d7310b6d769f8c1526` |
| `StrategyProfile.v1` digest of the same profile | `b2c81e99a570ba85566291403afdcf4e15dffdd20b6178592688fd107f71f421` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile rehearsal-s1-deterministic.json`; the `PROBE_SHA` to pin) | `75547c8e7d3d02e977e9859665f713580f64cc935f41641a3c129edc68fd9b99` |

The probe differs from the reviewed equal-weight probe `692787e4…` only in its `SELECTED_PROFILE_B64` line, so
reviewing it reduces to reviewing the profile bytes (`tests/strategy/test_s1_run3_profile.py`).

## Values and where they come from

- **IDEA-084 PF-01** (Isaac's delegation, 2026-10-21): levels 95/60/30%; trend over five sessions, ±1%, evaluated at
  session close + 15 min; weight cap 0.30; hard name line 35%; replenish below target − 5 pp; discretionary legs from
  open + 30 min to close − 15 min, at most 3 attempts per name, leg and session; deterministic limiter.
- **Keith, in chat, 2026-10-23:** use PF-01's values; `trend_start_state` UP (IDEA-076 S03); `max_legs_per_symbol_session`
  3; `llm_expiry_sessions` 3 (IDEA-075 §12).
- **Rehearsal deviation:** weights are 1/5 each, not PF-01's inverse-volatility weights. At about 100 USDT the measured
  minimum trade (18.637420 USDT) needs every weight ≥ 0.1962 (SJ-09-PC01 C5).
- **Scope (SJ-11-RH01, Yao's confirmation pending):** REHEARSAL, run mode `dev`, `evidence_mode` and
  `falsifier_authority` SHADOW, no model routing.
- **Gas, authority and costs** are the RC4/RC5 rehearsal inputs (`tools/deploy/build_rehearsal_candidate.py`): action
  budget 384,000,000,000,000 wei, sizing budget 80,004,608,000,000 wei, L = 660 s, m = 30 s, the 2026-10-20 quote
  summary. Exit reserve: 5 positions × 2 children × action = 3,840,000,000,000,000 wei.
- **Window:** RV120-02's REHEARSAL window, unchanged. New risk only until **2026-10-25 00:00Z**, flatten from Oct 26
  00:00Z, signing until Oct 26 14:45Z.

## Reproduce

```bash
python -m tools.deploy.build_rehearsal_candidate --exit-children 2 \
  --s1-config docs/build/evidence/s1-rehearsal-profile-20261023/s1-block.json \
  --s1-decision "IDEA-084 PF-01 (Isaac delegation, 2026-10-21) values; weights 1/5 (SJ-09-PC01 C5); start UP, legs 3, expiry 3 (Keith, chat, 2026-10-23); IDEA-049-C SJ-11-RH01-P1" \
  --output /tmp/s1-profile-check.json
```

It prints the `StrategyProfile.v1` digest above. The output must be byte-identical to `rehearsal-s1-deterministic.json`.

## Checked offline (`tests/strategy/test_s1_run3_profile.py`)

- The block's values match the mapping above, and the profile rebuilds byte for byte and passes `validate_live`.
- A signed dev `gate_a.prepare` with no routing prepares it with the deterministic assessor. `gate_a_check`'s scope and
  input checks accept the result, and a dev/service runtime builds from it with no network.
- On a synthetic flat-wallet packet with run 2's balances (96 USDT, 5,325,625,054,330,011 wei),
  `review_rehearsal_caps --profile` covers `FULL_BOOK_EXIT_RESERVE` and `INITIAL_BNB_EXIT_RESERVE`. The planner's
  gas floor admits the first buy (BNB − action ≥ reserve). The packet has no quotes, so the only blockers are quote
  coverage and owner review. Real coverage needs a fresh M3 capture.

**At this size (SJ-09-PC01 C6, accepted):** the trend guard's and limiter's cuts are smaller than one minimum trade,
so run 3 exercises S1's entries, levels, sessions and the flatten, but not a trend-guard trim.
