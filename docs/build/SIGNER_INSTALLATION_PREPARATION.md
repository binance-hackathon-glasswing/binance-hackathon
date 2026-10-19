# Signer installation preparation — SA-01 (2026-10-19)

**CONS-01:** use the canonical `codex/system-testing-20261012` build and
[current status](CURRENT_STATUS.md). PR194 adds an optional untrusted-router
policy path; selecting it requires actual B09/#44 adoption and qualification.
Its `untrusted_router_policy_file`/`_sha256` replace the source-path evidence
fields. Both paths cannot be configured together. The old six-null-field draft
and SA-02 inventory remain historical; no final candidate is generated here.
The source-only requests below apply when pursuing the verified-source path.

The merged signer guards and IDEA083 model implementation do not make the
historical signer.json draft installable. Its six unset bindings and pending
policy remain unchanged. This procedure completes offline configuration assembly
when the missing real inputs arrive. It performs no installation or key access.

## SA-02 current handoff — 2026-10-19

**NOT READY TO INSTALL.** Current repository inventory:
[signer input-readiness record](evidence/signer-input-readiness-20261019.json).
This is a missing-input inventory, not a candidate, source guarantee, provider
qualification or fresh host observation. The original
[signer.json](signer-handoff-20261017/signer.json) and
[Oct17 review](signer-handoff-20261017/review.json) remain historical and unchanged.
C05's available review slice is submitted separately in
[PR192](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/192);
its acceptance does not supply the missing signer bindings or approve caps.

The draft's six null bindings are `build_id`, `run_id`, `database_host`,
`database_ca_sha256`, `router_evidence_file`, `router_evidence_sha256`.
Its policy still says `EXAMPLE_PENDING_TEAM_DECISION`. Filling those values from
an old unsigned run or relabeling that policy is not valid assembly/approval.
The recent #92 balance-health work is distinct from native tracing/signing.

### Exact inputs to return privately, in dependency order

The existing [GateBCapsInputs.v1 contract](GATE_B_REMAINING.md#current-input-signer-cap-review)
is authoritative; do not create a second input format. Return approved local
paths and SHA256 pins, not keys, credentials, raw DSNs or private endpoints in
GitHub/chat. No account purchase or external message is authorized by this packet.

| Supplier / next actor | Required artifact and acceptance boundary | Why still required |
|---|---|---|
| Account owner/source supplier → Keegan → Isaac (B01–B03) | Complete #139 router/facet/helper source + ABI/imports/compiler/settings, chain56 deployment/dispatch bindings and original export hashes; Keegan independently reviews economic/deadline guarantees; Isaac builds pinned RouterEvidence.v1 and passes recorded real BUY/SELL/native route replay and #119 fee-netting review | No source export/review is supplied here. Do not fabricate ABI, guess selectors or enable the decoder using synthetic source |
| Keith + Yao/approved operator → Isaac (B06-pre/B07/B06-post/B08/B09) | Actual selected LIVE profile, fresh full PortfolioState.v1 after funding/no-additional-funding disposition, original successful quotes for all five BUY/SELL pairs plus USDT→BNB, actual scales/approve+swap gas/fee/full-position/top-up coverage. Supply the exact signing_policy object for Isaac's #44 approval and hashes | Historical balances, 40-USDT capture sizes, nominal headroom and FALLBACK gas do not establish current coverage. Funding occurs only if reconciliation shows remaining eligible need; this handoff performs none |
| Keegan + operator timings (B10) | Dated adopted #27 authority/deadline model, finite bounds/margins and per-action windows; reviewed implementation and expiry/requote/restart/uncertain-send evidence, based on source guarantees and measured queue/signing/finality timing | Conditional OptionA review exists;60s is illustrative. Do not enlarge quote freshness or reset authority to make old transactions pass |
| Approved provider owner → Isaac → Yao/operator (B04/B05) | Approved trace-capable private RPC config path plus suitable canonical successful native-credit transaction; sanitized local proof and provider/input hashes, then same-provider host qualification | Public balance providers and the #92 MATCH report do not qualify prestateTracer/diffMode/native settlement. Credentials remain private |
| Keegan + Yao/approved operator (C06/C07) | Exact reviewed signed release/build/manifest; intended signed run/wallet/environment/database; hosted execution.json with actual IAM database/region/CA fields; real CA/evidence available at configured paths and matching hashes; release/config binding plus isolation/time/IAM/TLS/routes and session plan | Do not copy current unsigned ea25b52 run/database IDs or assume published unsignedc5be269 qualifies later signed changes. No AWS or key operation is performed by this document |

Return one `GateBCapsInputs.v1` manifest outside the checkout containing its four
pinned files (`profile`, `signing_policy`, `execution_config`, `initial_state`),
original `quote_artifacts`, exact matching run/build/wallet/environment and a
reviewed freshness budget. The intended execution.json also pins the real router
evidence and public CA at locally available configured paths. Keep packet and
candidate hashes; separate accepted owner decisions from measured facts.

### After the required packet is accepted

1. Isaac rechecks #44 numeric coverage and records exact policy/input hashes;
   source/replay, native proof and #27 acceptance remain required separately.
2. Run the existing SA-01 assembly command below using current approved inputs.
   Do not use `--now` to make an old packet appear fresh. Preserve the emitted
   signer.json and signer-assembly-report.json together; a successful numeric
   assembly still reports installation/signing/GateB false.
3. Keegan/Yao bind the exact signer config bytes to the qualified signed release.
   In that release environment run the production local check:

   ```sh
   python -m larp.signer.service check \
     --config /absolute/private/new-signer-candidate/signer.json \
     --manifest /absolute/private/qualified-signed-release.json \
     --root /absolute/private/exact-signed-release
   ```

   These are documented required input paths, not files produced in this audit.
   A local check validates release/config/evidence; it does not qualify the host
   or supply a private key. Rebind/recheck after any path or content edit.
4. Handoff only the exact key-free candidate/config hash, assembly report,
   matching manifest/release identity and independent approvals to Yao/approved
   operator through the agreed private transfer. Yao qualifies/provisions the
   host and supplies the separately approved session. Isaac's key placement
   stays in that session; no key is ever embedded in signer.json or this packet.
5. Agent-generated first-round/approve+swap/receiver-ACK and host recovery/drill
   evidence complete the applicable later gates. Installation approval,
   enabling signing and GateB acceptance remain distinct recorded actions.

No final signer candidate is generated by SA-02: the required real inputs are
absent from this workspace. Completing C05 or this handoff must not flip an
assembly report's false flags or describe the old draft as installable.

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
