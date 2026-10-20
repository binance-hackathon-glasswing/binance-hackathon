# LD04-P: LIVE profile candidates with #27 finite authority

The DC-01 candidates (`../quotes-complete-20261020/`), rebuilt from the same committed inputs, plus Keegan's
LD04-V01 values: `execution_authority_seconds` = **660** and `submission_margin_seconds` = **30**. Every other
value and its provenance are unchanged (IDEA-049-C LD04-P, Q1–Q2). **Keith reviews these for #120. They are
evidence candidates only:** no runtime config, manifest pin or readiness flag changes.

| File | File SHA-256 | StrategyProfile.v1 |
|---|---|---|
| `rehearsal-live.json` | `bb27cbf8176ccff934973007559f608c02af47629f8d4060da156b9e19b0eb5b` | `24858d247ea036edaad73d4a28595afd7ad9e882ff1753652646d4b74be510fa` |
| `final-live.json` | `054ca468f1b43fa9469ee6816e347a8531166efc036675034d30fb741eee0bc7` | `ac764577ff3ec2d853fde48685007ccbc7cc54e1e2eb791869d390d3581d50d2` |

Provenance for both new keys: `decision_id` "IDEA-049-C LD04-V01 (Keegan, 2026-10-20)", and `data_hash`
`ad43b634…c4ced4`, the SHA-256 of the committed LD02 packet
[`ld02-execution-packet-20261020.json`](../ld02-execution-packet-20261020.json).

Reproduce from the repository root (no network):

```sh
python -m larp.strategy.profiles \
  --summary docs/build/evidence/quotes-complete-20261020/quote-cost-summary.json \
  --predicates config/intelligence/red_flags.v1.json --output-dir NEW_DIR \
  --execution-authority-seconds 660 --submission-margin-seconds 30 \
  --authority-decision "IDEA-049-C LD04-V01 (Keegan, 2026-10-20)" \
  --authority-evidence docs/build/evidence/ld02-execution-packet-20261020.json
```

These keep everything the DC-01 candidates still lack: the #120 profile review, the #119 fee-inclusion
evidence, LD09's measured approve/swap gas, LD08's initial-gas-only alignment (the candidates still carry the
top-up fields), the #44 caps and the S1 choice. Re-check L and m against measured signer and approve timings
in the signed rehearsal.
