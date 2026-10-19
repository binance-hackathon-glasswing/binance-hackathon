# Native RPC qualification — NT-Q1 / #30

Immediate point3, isolated in its own PR. **Tool and synthetic proof tests pass;
actual provider/host qualification remains open.** Isaac reports no private RPC
configuration/account available. No account was created, payment accepted or
runtime provider selected/enabled. Balance-provider approval does not qualify
native settlement.

## Public alternatives checked

Five bounded discovery calls at2026-10-18 10:59UTC, below the eight-call cap:

| Candidate | Observed result |
|---|---|
| SubQuery BNB endpoint listed in the [BNB Chain endpoint documentation](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/) | DNS resolution failed (curl6, no HTTP response); this does not establish tracer support |
| [PublicNode BSC endpoint](https://bsc.publicnode.com/) | Chain56 and finalized block returned; both recent and historical exact prestateTracer requests return -32601 method does not exist/is not available |

Report: [native-rpc-candidate-search-20261018.json](evidence/native-rpc-candidate-search-20261018.json),
SHA256 `13bb1b38a77526760317d8554f90cf8869676f50b2a6d0b4a5c294bf496b0b46`. Every request, UTC/status/error and response hash is retained; raw bytes stay
at/private/tmp/larp-isaac-now-public-20261018. Earlier SP-NATIVE tests established
that BNB/NodeReal public endpoints also lack recent-transaction tracing. No
new trace-capable endpoint was found; the real qualification CLI was not run
against unsupported candidates merely to create another refusal report.

[QuickNode's chain-specific method documentation](https://www.quicknode.com/docs/bnb-smart-chain/debug_traceTransaction)
lists prestateTracer/diffMode and limited free-trial access. This is a concrete
account candidate to investigate, **not a selected/qualified service, free-plan
promise or spending approval**. The actual account must support our exact
options, canonical finalized reads and sufficient historical state/recovery
retention. [NodeReal's BSC method documentation](https://docs.nodereal.io/reference/debug-tracetransaction)
lists callTracer only: an archive label or the presence of debug_traceTransaction
alone does not establish the required diff capability. No account signup occurred.

## Run the committed proof tool when the missing input exists

`tools/deploy/qualify_native_rpc.py` uses the actual production
Rpc and ChainEvidence.native_receipt. It does not accept a user-supplied trace
as proof or infer native credit from a block/current balance. The tool:

- allows1–4 explicitly supplied providers and at most16 read-only calls each,
  with production20s timeout, no retries/redirects or additional methods;
- requires chain56, success/finalized/canonical receipt identity, matching sender/
  wallet/nonce and exact prestateTracer diff, rechecks the receipt after tracing,
  and requires value0/positive native inflow excluding actual receipt gas;
- writes private immutable observations, a proof hash and a URL-free sanitized
  report; bad chain, revert, foreign wallet, missing trace, reorg, bad nonce,
  malformed/private input or spent read budget cannot pass;
- does not choose/enable a provider, install configs, access keys, sign, submit,
  upload official logs, call models or change AWS.

Inputs must be a private0600 JSON file outside the repository. The following is
an explicit **format example with an unusable reserved endpoint**, not actual
credentials or a ready-to-run configuration:

```json
{
  "schema": "NativeRpcQualificationInputs.v1",
  "providers": [{"source_id": "NATIVE_CANDIDATE", "url": "https://rpc.invalid/account-path"}],
  "wallet": "0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479",
  "tx_hash": "0x24683de219c18cc78a2d7aeb37c94e733a6a383b1c3a58d3a403f95df7da5c55"
}
```

Use the owner-approved actual endpoint privately, not in CLI arguments, Git,
chat or issue comments. Source IDs are public labels, never API keys. The
historical funding transaction is a native-proof capability test, not an agent
quote/top-up round or the unrelated bStock route-fee evidence in #119. If its
historical state is unavailable, provide a known successful wallet-directed
native-credit transaction whose state is retained; a random recent transfer
cannot qualify our positive native-credit path.

From a clean pushed branch, with normal certificate validation configured:

```sh
python tools/deploy/qualify_native_rpc.py   --inputs /absolute/private/native-inputs.json   --out /absolute/private/new-native-qualification
```

Exit0: all supplied transaction proofs pass; exit2: at least one inconclusive;
exit4: input/start refusal. A pass is **exact transaction evidence only**.
`runtime_enabled`, `providers_selected`, `signing_enabled` remain false;
`hosted_check` and `agent_topup_round` remain NOT_RUN. Copy/review the actual
report, receipt/tracer retention and hashes before an explicit execution-provider
selection; Yao then checks the real host. Floor/top-up sizing and an actual
logged agent top-up remain separate #30 acceptance.

## Verification and remaining owner

At pushedab105c1: **42 tests,56 subtests,0 skips**,3.24s on macOS/Python3.12.14/
disposable PostgreSQL14. Includes the new qualifier, real chain-proof composition,
provider privacy, existing receipt/native settlement, PostgreSQL persistence and
end-to-end synthetic gas-top-up round. No real external adapters in those tests.
No full-suite/CI/host qualification is claimed. Criteria/code were pushed first.

Isaac supplies a permitted trace-capable account/config after checking exact
tracer/finality/retention; the qualifier then collects actual transaction proof.
Yao retains host/runtime acceptance. Keith+Isaac retain measured floor/top-up
values. No account input exists today, so #30 stays open with native_trace off.
