# Signer installation preparation — SA-01 (2026-10-19)

**LIVE-PLAN01 (2026-10-20 SGT):** [current API-trusted deployment order](LIVE_DEPLOYMENT_PLAN_20261020.md) supersedes the source-export-first prerequisites below for the selected B02-U path. B09-TRUST01 accepts router behavior; measured caps, actual policy, supported gas scope and host/rehearsal acceptance remain open. Proposed in PR196 until merged; historical procedures/results below retain their original scope.

**CONS-01:** use the canonical `codex/system-testing-20261012` build and
[current status](CURRENT_STATUS.md). PR194 adds an optional untrusted-router
policy path. Isaac selected that trust direction in B09-TRUST01 (PR196);
actual named policy/hash review, measured B09/#44 acceptance and qualification remain.
Its `untrusted_router_policy_file`/`_sha256` replace the source-path evidence
fields. Both paths cannot be configured together. The old six-null-field draft
and SA-02 inventory remain historical; no final candidate is generated here.
Source-only requests apply when pursuing the verified-source path. LD01 updates
the current packet below for both modes; the original SA-02 artifacts stay historical.

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
| Operator → Keegan → Isaac (selected untrusted path, LD02/03) | Current observed router/facet/code/allowance policy draft, independent named review/hash, fresh request-bound recorded quotes and matching untrusted replay/live preflight | No actual reviewed policy supplied here. Review bindings without claiming source guarantees. #138 remains incomplete optional source-path work |
| Source supplier → Keegan → Isaac (verified path only) | Complete source/ABI/compiler/deployment binding; independent four-guarantee review, RouterEvidence.v1 and recorded-route replay | Source remains unavailable. Do not manufacture evidence; it is not a prerequisite for the selected untrusted path |
| Keith + Yao/approved operator → Isaac (B06-pre/B07/B06-post/B08/B09) | Actual selected LIVE profile, fresh full PortfolioState.v1 after funding/no-additional-funding disposition, original successful quotes for all five BUY/SELL pairs plus USDT→BNB, actual scales/approve+swap gas/fee/full-position/top-up coverage. Supply the exact signing_policy object for Isaac's #44 approval and hashes | Historical balances, 40-USDT capture sizes, nominal headroom and FALLBACK gas do not establish current coverage. Funding occurs only if reconciliation shows remaining eligible need; this handoff performs none |
| Keegan + operator timings (B10) | Dated adopted #27 authority/deadline model, finite bounds/margins and per-action windows; reviewed implementation and expiry/requote/restart/uncertain-send evidence, with mode-specific contract assumptions and measured queue/signing/finality timing | Conditional OptionA review exists;60s is illustrative. Do not enlarge quote freshness or reset authority. API-trusted deadlines and timeout do not prove an uncertain send cannot execute |
| Keegan/Keith/Isaac gas scope, then provider owner → Isaac/operator (LD07/08) | Qualified native route/trace proof, or explicitly reviewed initial-only scope with measured whole-run/exit reserve and low-gas controls aligned across code/profile/caps/gates | Untrusted native routes currently refuse; existing caps/Gate B require top-ups. No scope omission adopted here; balance MATCH is not native proof. Canonical receipts/gas accounting remain required |
| Keegan + Yao/approved operator (C06/C07) | Exact reviewed signed release/build/manifest; intended signed run/wallet/environment/database; hosted execution.json with actual IAM database/region/CA fields; real CA and selected evidence/policy available at configured paths and matching hashes; release/config binding plus isolation/time/IAM/TLS/routes and session plan | Do not copy current unsigned ea25b52 run/database IDs or assume published unsignedc5be269 qualifies later signed changes. No AWS or key operation is performed by this document |

Return one `GateBCapsInputs.v1` manifest outside the checkout containing its four
pinned files (`profile`, `signing_policy`, `execution_config`, `initial_state`),
original `quote_artifacts`, exact matching run/build/wallet/environment and a
reviewed freshness budget. The intended execution.json also pins the selected router
evidence/policy and public CA at locally available configured paths. Keep packet and
candidate hashes; separate accepted owner decisions from measured facts.

### After the required packet is accepted

1. Isaac rechecks #44 numeric coverage and records exact policy/input hashes;
   mode-appropriate router review/replay/preflight, adopted gas-scope qualification
   and #27 acceptance remain required separately.
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
actual IAM database/region/CA settings, and exactly one complete router pair:
`router_evidence_file` / `router_evidence_sha256` (verified), or
`untrusted_router_policy_file` / `untrusted_router_policy_sha256` (untrusted).
Both cannot be configured together. The CA and selected router file must be
available locally at those configured paths. Use
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
- signer-assembly-report.json: exact config/input/CA/router hashes, `router_mode`,
  numeric review and mode-appropriate remaining gates. Verified mode retains
  source review/replay; untrusted mode retains named policy review/replay/live
  preflight. Both retain owner, lifetime, gas/fee, release/host and signer-session gates.

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
| Operator / Keegan / Isaac | Selected untrusted policy: fresh observed router/facet/code/layout/allowance bindings, named review/hash, replay and live preflight. Verified-path source/review (#138) remains incomplete and optional for the selected path. |
| Keith / current coordinator; Isaac reviews and confirms | Selected measured profile, fresh reconciled full holdings and top-up/approve/swap fee/quote evidence. Complete #44 numeric coverage, then Isaac records the exact approved policy hashes. Historical prices, fallback gas estimates and 40-USDT capture sizes do not complete this review. |
| Keegan, with actual operator/router timings | Adopt #27's authority model, finite limit, margins and per-action windows; implement and verify approval/requote/expiry/restart/uncertain-send behavior. Keith supplied the conditional OptionA review; 60s is illustrative, not an adopted setting. |
| Gas-scope/provider owner; Isaac qualifies | Complete LD07/08 scope decision/code alignment, applicable native proof and #119 fee evidence. Native scope remains unqualified; disabling native_trace alone is insufficient. |
| Release owner / current coordinator / approved host operator | Exact signed release and run/DB/CA/evidence bindings, preserving state, host isolation/time/IAM checks and hosted signer/recovery/round/ACK acceptance. Resolve CI billing #98 or provide the approved exact-release substitute. |
| Isaac / Yao's approved signer session | Key placement only in that separately approved session, after the preceding requirements. No key belongs in signer.json or this handoff. |

No AWS changes, wallet funding, signing, broadcasting, provider account setup or
external receiver calls are part of SA-01. PR133 remains the noticeboard; canonical INCOMPLETE_WORK.md remains the live
backlog. Local synthetic acceptance evidence is in IDEA-049-C SA-01.

## LD01 issue dispositions — 2026-10-20

- **#138:** original source-acquisition/four-guarantee acceptance is incomplete;
  retain the evidence and do not claim it closed. Under B09-TRUST01 it is optional
  source-path work, replaced on the selected path by actual observed policy/hash
  review, fresh replay and live preflight (LD02/03). Parent #33/GAP-29 stays open.
- **#160:** the delegated technical review and historical key-free draft were
  delivered by PR161 (now consolidated), with SA-01/SA-02 assembly tooling/input
  inventory retained. That issue's handoff slice is delivered; the GitHub issue
  was still OPEN when checked in this session. Actual approved assembly remains
  NOT_RUN_MISSING_INPUTS under #44/LD16, with release/host/session/key placement
  separate. No historical draft or review artifact is rewritten or relabeled.

## LD06 allowance-recovery scope

[ALLOWANCE_RECOVERY.md](ALLOWANCE_RECOVERY.md) defines the optional zero-only
supporting approval policy and bounded state machine. Execution configuration
and the root-owned signing_policy must both explicitly set allowance_recovery
true; missing means false, non-booleans refuse, and caps review refuses unequal
settings. Only the selected untrusted-router path supports it. This PR changes
no example, private or installed configuration.

Before enabling, accept measured cleanup gas and token/API behavior, full
parent/exit-reserve coverage, authority timing and real host recovery. Up to six
cleanup approvals are additional to the usual approve/swap; two-transaction gas
estimates do not qualify that envelope. Assembly retains all false readiness
flags and a separate ALLOWANCE_RECOVERY_GAS_AND_HOST_ACCEPTANCE gate. Normal
positive approvals remain exact; zero-only cleanup cannot authorize a swap,
change the parent's expiry or turn its transaction hash into an order.
