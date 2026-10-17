# Isaac task 3: router source review (#138)

Status 2026-10-17: **waiting for public source/ABI input**, not ready for
deployment. Record: IDEA-070 RE-01. Decoder dependency: PR130 at `e5bd552`.
This task has its own branch, `codex/isaac-03-router-evidence-20261017`.

## Evidence needed from Isaac's browser

1. Open [the router's BscScan Contract tab](https://bscscan.com/address/0xb44446b0c8e56988c34f7ff73ae904982b5fdda5#code).
   Confirm this is BNB Smart Chain, chain56, and the exact router address above.
2. If verified source is displayed, save the complete source (all files/imports,
   or the explorer's source/standard-JSON export) and Contract ABI JSON **outside
   the repository**. Retain the original files without reformatting. Also save
   the page or a plain-text note of its URL, verification status, compiler,
   contract name and UTC retrieval time. These are public artifacts; no wallet
   connection, signing or secret is needed.
3. Inspect the proxy information. If it identifies an implementation, include
   its address, verified source and ABI too. An unknown proxy status is not
   evidence for `implementation: null`. A proxy shell alone is insufficient;
   any facets/delegated implementation handling the selector must be reviewed.
4. Tell Codex the local folder path. Codex can read and hash the files and
   continue the source review. There is no need to paste source or API keys
   into chat.
5. If the source is unverified or your browser is blocked too, report that
   result. Keep task3 open; the team must resolve source availability before
   this evidence path can proceed.

The automated attempt returned a Cloudflare challenge (HTTP403). Sourcify's
documented v2 lookup returned HTTP404 with no match. Neither result determines
BscScan's verification status. Retained response bytes/headers are outside Git
at `/private/tmp/larp-isaac-router-20261017`; the committed acquisition report
contains response-body hashes and outcomes only. **Those hashes must never be
used as source or ABI hashes.** The authenticated Etherscan source API is an
alternative if suitable account access already exists; no API key was read or
used here. Do not create a paid subscription for this handoff.

## Review after the source is available

Isaac's source review must establish each item; all remain unresolved today:

| Requirement | Evidence to record |
|---|---|
| Provenance | Exact source/ABI file SHA256, explorer URL, verification/compiler metadata, retrieval time and implementation/facet identity where applicable |
| Swap signature | Canonical ABI tuple signature whose keccak selector is `0xad43f73d`; derive from source/ABI, not a selector registry |
| Economic field paths | Zero-based tuple paths and leaf types for pay/receive token, amount, minimum output, recipient and deadline |
| Native BNB | Source-defined native sentinels and the treatment of `msg.value` |
| Minimum output | Concrete code proving the minimum is enforced on the recipient's balance, including helper/delegated route behavior |
| Deadline | Concrete code enforcing the encoded deadline |
| Input authority | Concrete code proving the input is pulled only from `msg.sender`, including helper/delegated route behavior |
| Independent review | Keegan's actual review reference; never attribute review before it happens |

If any guarantee is false or unsupported, stop the evidence path and record the
finding for the team. A schema accepting `true` does not establish a guarantee.
No runtime config or signer policy should reference this acquisition report.

When the facts are established, fill the existing `RouterEvidence.v1` template
in [GATE_B.md](GATE_B.md), push it before running the evidence/selector checks,
and obtain Keegan's review. Only then can this task's PR become ready and close
#138. Keep parent #33/GAP-29 open for the remaining acceptance requirements.

Task4 is the separate recorded-route replay over Keith's existing IDEA-063
quote artifacts after Keegan's evidence review and PR130 merge. No new capture
is needed here. Signing lifetime #27, caps #44, gas, signer access, deployment
and the first agent trades remain later tasks.
