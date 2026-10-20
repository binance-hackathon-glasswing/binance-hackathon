# LD04-P: LIVE profile candidates with #27 finite authority

The DC-01 candidates (`../quotes-complete-20261020/`), rebuilt from the same committed inputs in the **initial-gas-only**
scope (IDEA-061 LD07/LD08, PR207), plus Keegan's LD04-V01 values: `execution_authority_seconds` = **660** and `submission_margin_seconds` = **30**. Every other
value and its provenance are unchanged (IDEA-049-C LD04-P, Q1–Q2). **Keith reviews these for #120. They are
evidence candidates only:** no runtime config, manifest pin or readiness flag changes.

| File | File SHA-256 | StrategyProfile.v1 |
|---|---|---|
| `rehearsal-live.json` | `07130775bbe6ab07a384c5efbde35582ec93c7e22ef50df7c73db921d1e6a729` | `58cb1be94247aa043230e7118733afd15e85715745aad433a521bc8124bbbdd4` |
| `final-live.json` | `3393ce672f0586df1dad535a1e1b8235135217c151e08aea38183a96a35e34fd` | `70cb0d4f563f5a0f051e0e6f39f1802befb4005687ab056abe82ea33c686d862` |

Provenance for both new keys: `decision_id` "IDEA-049-C LD04-V01 (Keegan, 2026-10-20)", and `data_hash`
`ad43b634…c4ced4`, the SHA-256 of the committed LD02 packet
[`ld02-execution-packet-20261020.json`](../ld02-execution-packet-20261020.json).

Reproduce from the repository root (no network):

```sh
python -m larp.strategy.profiles \
  --summary docs/build/evidence/quotes-complete-20261020/quote-cost-summary.json \
  --predicates config/intelligence/red_flags.v1.json --output-dir NEW_DIR --initial-gas-only \
  --execution-authority-seconds 660 --submission-margin-seconds 30 \
  --authority-decision "IDEA-049-C LD04-V01 (Keegan, 2026-10-20)" \
  --authority-evidence docs/build/evidence/ld02-execution-packet-20261020.json
```

Both carry `initial_gas_only`, `gas_action_budget_units` = 76,177,634,176,000 wei and an exit reserve of
304,710,536,704,000 wei, and no top-up fields. They still lack: the #120 profile review, the #119 fee-inclusion
evidence, LD09's measured approve/swap gas (the action budget is still the FALLBACK-based DC-01 pair), the #44 caps
and the S1 choice. Re-check L and m against measured signer and approve timings
in the signed rehearsal.
