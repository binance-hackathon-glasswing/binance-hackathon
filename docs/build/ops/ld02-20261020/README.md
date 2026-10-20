# LD02 operator execution packet

`execution-packet.sh` is a read-only check for `primary` only (`i-040fc5fea8b700e9a`). Never run it on the
signer. It prints one sanitized JSON packet and the packet's SHA-256 for Keegan's LD03 review and the #27 L/m
choice. Pass criteria are pre-registered in [IDEA-070 LD02](../../../ledger/IDEA-070.md) (P1–P11).

It collects:

- **Identity:** host, run, build and DB; hashes of `runtime.json`, `release.json` and the strategy profile;
  one wallet fingerprint, and whether the wallet and registered version match.
- **Holdings:** a fresh finalized balance read through the approved ordered balance providers, reconciled with
  the production `compare_balances` against the current ledger. Also reservations, commands, rounds and nonces.
- **Quotes:** for each bStock, a BUY at `minimum_trade_units` and at `per_trade_cap_units`, and a SELL at the
  minimum BUY's receive size. Each goes through the runtime's `MarketPort.quote`, with the host's existing Web3
  keys and the profile's slippage.
- **Router draft:** the canonical `untrusted_router.observe()` draft (still `REVIEW_REQUIRED`) and the six
  router allowances at the same block.
- **Timings:** RPC round trips per provider and method, quote round trips, and the latest-to-finalized lag.
  Signer timings are `UNMEASURED`.
- **LD02b:** the canonical `check()` on the fresh quotes under the hash-pinned reviewed policy, and
  `eth_estimateGas` simulations for approve and minimum-size BUY swaps (the swap only after an on-chain proof
  of the USDT allowance slot used in a state override).
- **Funding input** for Isaac against LD07, and the **execution RPC candidates**, which await Keegan's
  confirmation.

## Safety

- **No host writes.** Web3 and RPC artifacts stay in memory. SQL runs `READ ONLY`. The script makes no file, service, config,
  ledger or AWS change, and the command below passes it through `bash -c`. The SSM agent still stores the
  command and its sanitized output under `/var/lib/amazon/ssm/`, as it does for every run.
- **No secrets in the output.** Keys never leave the host. A final scan refuses any output containing `://`,
  a provider URL or hostname, the database host, the wallet address or any runtime secret value. On any failure
  the script prints only `LD02_PACKET_REFUSED` with the exception type, plus one of its own allowlisted codes.
- **Pinned router code.** The host release (`ea25b52`) predates `untrusted_router`, so the script carries that
  module's exact canonical bytes (`697ff3a`, SHA-256
  `9934f5372f406ad9b9b62e85da93421128d68fdf2722af234f358d6140b0923a`). It refuses to run if the bytes differ.
  `tests/runtime/test_ld02_packet_script.py` fails if the repository file changes without the embed being updated.
- **Fresh calls, but nothing claimed as proof.** The run makes about 15 quote requests and about 40 read-only
  RPC calls. The packet is not native-trace, signed-path or #92 evidence, and it enables nothing.

## Run it from AWS CloudShell (ap-southeast-2)

Upload `execution-packet.sh` to CloudShell (**Actions → Upload file**), then run:

```bash
REGION=ap-southeast-2; I=i-040fc5fea8b700e9a
python3 -c 'import base64,json; b=base64.b64encode(open("execution-packet.sh","rb").read()).decode(); print(json.dumps({"commands":["bash -c \"$(echo "+b+" | base64 -d)\""],"executionTimeout":["600"]}))' > ld02-params.json
CID=$(aws ssm send-command --region $REGION --instance-ids $I --document-name AWS-RunShellScript \
  --comment 'LD02 read-only packet' --parameters file://ld02-params.json --query Command.CommandId --output text)
aws ssm wait command-executed --region $REGION --command-id $CID --instance-id $I || true
aws ssm get-command-invocation --region $REGION --command-id $CID --instance-id $I \
  --query '[Status,StandardOutputContent,StandardErrorContent]' --output text
```

Paste the packet line, the `packet_sha256` line, the command ID and the status. SSM returns at most 24,000
characters of output. If the packet looks cut off, say so rather than pasting a partial packet.
