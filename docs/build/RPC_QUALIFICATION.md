# Isaac task 1: choose the balance RPCs (#92)

This is the first Isaac-owned task in PR133, tracked as IDEA-055 RPC-Q01 and
implementation issue #134. It changes no runtime defaults and grants no signing
authority. Isaac chooses the providers; Yao Zhu owns AWS network access, the
hosted configuration and first-host verification. Whole issue #92 stays open
until those checks are recorded.

The proposed no-key candidates are BNB Chain's public mainnet RPC
(`BSC_BNBCHAIN_PUBLIC`) and PublicNode's BSC RPC (`BSC_PUBLICNODE_PUBLIC`). Copy
their current HTTPS URLs from their own [BNB Chain documentation](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/)
and [PublicNode BSC page](https://bsc.publicnode.com/) into private local input,
not an issue or commit. These are candidates, not an adopted configuration. BNB
Chain documents 10K requests per five minutes and disabled `eth_getLogs`; our
balance reader does not use that method. PublicNode's [terms](https://www.publicnode.com/terms)
describe intended RPC access and a revocable service. Neither a listed endpoint
nor a successful one-time test establishes uptime or host reachability.

## Qualification

From the clean, pushed task branch, create an ignored config such as
`deploy/activation/balance-rpc/providers.json`. The following is a **template**:
replace both `<set privately>` URL values locally before running. The source
IDs may be published; the full URLs stay in the private file.

```json
{
  "balance_rpc_providers": [
    {"url": "<set privately>", "source_id": "BSC_BNBCHAIN_PUBLIC"},
    {"url": "<set privately>", "source_id": "BSC_PUBLICNODE_PUBLIC"}
  ]
}
```

Use an absolute new output directory outside Git; no `.env`, API key, registered
wallet address or private key is needed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/deploy/qualify_balance_rpc.py \
  --config deploy/activation/balance-rpc/providers.json \
  --out "$LARP_CAPTURE_ROOT/balance-rpc-qualification-01"
```

Set `LARP_CAPTURE_ROOT` explicitly to your external capture directory first.
The command refuses dirty/unpushed code, an existing output directory, tracked
provider config, symlinks and non-HTTPS/credentialed/redirecting endpoints. It
accepts the runtime's ordered list of one to four providers, with distinct
public source IDs. One public-zero-address capture per candidate makes 19
read-only requests using the real `Rpc` and Gate A `chain_capture` paths:

- Chain 56; a `finalized` block and the same block re-read by numeric height.
- BNB and all six pinned ERC-20 balances, including their decimals, at that
  numeric block; no guessed decimals or latest-block fallback.
- Wallet nonces at that finalized height, `latest` and `pending`.

There is no retry, signing, broadcast, official log upload or AWS action. The
production transport verifies HTTPS, refuses redirects and bounds each call to
20 seconds. Reports print only source IDs, statuses, elapsed time, observation
hashes/counts and scope flags; raw observations and chain captures are retained
as mode-0600 files outside Git. Elapsed time is one sequential capture, not a
latency benchmark.

Exit 0 means all candidates passed that point-in-time capability test. Exit 1
means at least one candidate was unavailable/refused (including rate-limit or
redirect failures); its failure remains visible even if a backup passed. Exit
4 means the local inputs or committed-code gate refused the run. Do not bypass
a refusal or infer permission from a different provider's success.

## Decision and handoff

After the technical comparison, Isaac chooses the ordered providers or supplies
a preferred account-backed alternative. No paid account is created here. Send
the private config to Yao Zhu through the team's private channel; this tool
does not send a message or activate it. Preserve the report/capture hashes and
record the choice in IDEA-055 RPC-Q01 before updating the release services list.

Yao Zhu then opens only the chosen RPC destinations, fills the existing
`driver.balance_rpc_providers` on the host, binds those config bytes into the
release manifest and runs the host's first balance read. Verify chain/finality
and all pinned assets from `primary`; then record the runtime's first
`BALANCE_CHECKED` verdict against the actual wallet/ledger and the balance-health
gate. Local zero-address probes cannot establish that result. Update #92/GAP-71
only for the work actually evidenced. Native tracing for gas settlement (#30)
is a separate checklist task and remains NOT_RUN here.
