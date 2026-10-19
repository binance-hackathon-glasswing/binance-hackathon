# Signer installation preparation — SA-01 (2026-10-19)

The merged signer guards and IDEA083 model implementation do not make the
historical signer.json draft installable. Its six unset bindings and pending
policy remain unchanged. This procedure completes offline configuration assembly
when the missing real inputs arrive. It performs no installation or key access.

## Assemble without manually transcribing settings

Use the existing [GateBCapsInputs.v1 manifest](GATE_B_REMAINING.md#current-input-signer-cap-review).
It must pin the actual selected LIVE profile, reconciled full holdings, intended
execution.json, exact signing_policy object, and successful fresh quotes for all
five BUY/SELL pairs plus USDT→BNB. Choose the applicable freshness budget; do not
increase it to make old evidence pass. The caps must already carry their real
decision reference, rather than EXAMPLE_PENDING_TEAM_DECISION. That reference is
an operator assertion; the assembly tool cannot authenticate Isaac's approval.

The selected execution.json supplies the signed run/build/wallet/environment,
actual IAM database/region/CA settings, and pinned router evidence paths/hashes.
The CA and evidence must be available locally at those configured paths. Use
the intended signed run and database explicitly; do not reuse the unsigned
trial's identity or assume the old draft's database_name is correct.

```sh
python -m larp.signer.assembly \
  --inputs /absolute/private/caps-inputs.json \
  --out /absolute/private/new-signer-candidate
```

The command re-runs numeric coverage and the production decoder/config checks.
It copies shared identity and evidence bindings, selects the dedicated
larp_signer role, and uses the existing wallet.key systemd credential name.
It copies no execution RPC URL, service secret reference or secret value.
It refuses a local DSN, unfinished policy, changed input/CA/evidence, wrong router,
uncovered amounts/fees, or incomplete/stale quotes. It does not set new gas limits
or signing-lifetime policy. The existing 1s poll and 2s clock-skew defaults are
preserved; those are not a #27 signing-lifetime decision.

Success (exit0) creates a new directory0700 containing files0600:

- signer.json: a complete local configuration candidate, with no wallet key.
- signer-assembly-report.json: exact config/input/CA/router hashes, numeric review,
  and the remaining acceptance gates.

Both existing and symlink output directories refuse. Invalid inputs (exit4)
create no candidate; output-write failures clean up this attempt. Stdout contains
status/hash flags only, without private endpoints, input values or error text.
`--now` exists for reproducible offline checks; normal preparation uses the
current clock. Historical checks never establish present freshness.

Every report keeps ready_to_install=false, signing_enabled=false and
gate_b_accepted=false. Numeric coverage does not prove source provenance, current
reconciliation, actual quote executability or owner approval. The exact final
signer bytes must subsequently be bound to the selected registered release
manifest. Re-check after any edit, including paths or the policy decision label.
Production `larp.signer.service check` remains the local release/config check;
it also does not accept the host or Gate B.

## Real inputs and decisions still required

| Owner | Required next result |
|---|---|
| Router source supplier / Isaac / Keegan | Verified router/facet/helper source with deployment, ABI and compiler binding; independent guarantee review, then replay Keith's recorded routes. PR139/#138 remain blocked; never manufacture source evidence. |
| Keith / current coordinator; Isaac reviews and confirms | Selected measured profile, fresh reconciled full holdings and top-up/approve/swap fee/quote evidence. Complete #44 numeric coverage, then Isaac records the exact approved policy hashes. Historical prices, fallback gas estimates and 40-USDT capture sizes do not complete this review. |
| Keegan, with actual operator/router timings | Adopt #27's authority model, finite limit, margins and per-action windows; implement and verify approval/requote/expiry/restart/uncertain-send behavior. Keith supplied the conditional OptionA review; 60s is illustrative, not an adopted setting. |
| Provider/source owner; Isaac qualifies | Supply an eligible private native-trace provider configuration and attributable route-fee evidence for #30/#119. No credentials in Git/chat; native_trace remains off until qualified. |
| Release owner / current coordinator / approved host operator | Exact signed release and run/DB/CA/evidence bindings, preserving state, host isolation/time/IAM checks and hosted signer/recovery/round/ACK acceptance. Resolve CI billing #98 or provide the approved exact-release substitute. |
| Isaac / Yao's approved signer session | Key placement only in that separately approved session, after the preceding requirements. No key belongs in signer.json or this handoff. |

No AWS changes, wallet funding, signing, broadcasting, provider account setup or
external receiver calls are part of SA-01. PR133 remains the live coordination
tracker. Local synthetic acceptance evidence is in IDEA-049-C SA-01.
