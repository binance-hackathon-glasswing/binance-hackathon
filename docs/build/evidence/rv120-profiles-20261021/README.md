# RV120-02 — recommended rehearsal-window candidates (2026-10-21)

Built from pushed implementation `839658d`, on canonical `81e08d2`. Keegan delegated
recommended choices and the mechanical step-1 work. Keith/Isaac owner confirmation
on #120 remains outstanding; this packet does not pin deployment inputs.

| File | File SHA-256 | StrategyProfile.v1 |
|---|---|---|
| rehearsal-live.json | d76b640866250a2963618d093eadc8fb0b48e26cfca8f98151d693d3e392740f | df58529756c715282c567e39b013163cd1428d347c5d5bef196a273b152f5d6e |
| final-live.json | 0497a820821524cbcbd5234c937aa211b8b94da9409b6b8e787f49b33cde5f40 | 07e8e8c90b06440993052a0ce67ce6f24b103edac4dc7b168ba457a75267a542 |

| Gate | UTC | Singapore |
|---|---|---|
| trade_after | October 23 00:00 | October 23 08:00 |
| new_risk_end | October 25 00:00 | October 25 08:00 |
| flatten_start | October 26 00:00 | October 26 08:00 |
| signing_end | October 26 14:45 | October 26 22:45 |

Offline P1/P2 PASS: repeat construction is byte-identical and both profiles validate.
Rehearsal changes only these dates and their RV120-02 provenance; final is byte-identical
to LD09-B. Historical DC-01/LD04-P/LD09-B artifacts are retained.

Inputs stay DC-01, EQUAL_WEIGHT, initial gas only, execution authority 660 s / margin
30 s, action budget 200011400000000 wei, sizing budget 80004560000000 wei, four-action
exit reserve 800045600000000 wei, minimum 18.637420 USDT, MSFTB spread 17 bp, impact
2 bp, slippage 8 bp and quote age 30 s. Fee 0 remains conditional on #119.

Recommended seeding planning counts are N=15 rehearsal and N=30 final, approximately
0.0046/0.0083 BNB. No funding action is included.

Before adoption: Keith/Isaac #120 confirmation; Isaac #119 fee netting and LD10 actual
signed-child/holdings/cleanup envelope coverage; later LD15 qualification and host gates.
In particular the nominal LD09-B pair budget does not cover independently rounded
child gas limits (minimum 200011520000000 wei at 0.16 gwei). These are rebuilt candidates,
not an accepted signed-action envelope. S1/final calendar acceptance remains separate.

Reproduce offline from the repository root, choosing a fresh output directory:

```sh
python -m larp.strategy.profiles \
  --summary docs/build/evidence/quotes-complete-20261020/quote-cost-summary.json \
  --predicates config/intelligence/red_flags.v1.json --output-dir docs/build/evidence/rv120-profiles-20261021 --initial-gas-only \
  --execution-authority-seconds 660 --submission-margin-seconds 30 \
  --authority-decision "IDEA-049-C LD04-V01 (Keegan, 2026-10-20)" \
  --authority-evidence docs/build/evidence/ld02-execution-packet-20261020.json \
  --gas-action-budget-units 200011400000000 --gas-sizing-budget-units 80004560000000 \
  --gas-budget-decision "IDEA-061 LD09-B (Keegan, 2026-10-21)" \
  --gas-budget-evidence docs/build/evidence/ld02d-size-sell-20261021.json
```

Full decision, prospective criteria and verification: [IDEA-063 RV120-02](../../../ledger/IDEA-063.md).
