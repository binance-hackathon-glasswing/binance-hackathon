# Development signer handoff — SH-01 / #160

**ASSEMBLY DRAFT — NOT READY TO INSTALL.** This folder is a concrete handoff for Yao Zhu, not deployment by Isaac. `signer.json` is a `SignerService.v1` document populated with the known public development wallet and exact CP-01 development policy. It contains no private key, API credential, RPC URL or password. Do not substitute the final-wallet policy.

Isaac asked the assistant to take over the technical review. The review is attributed to Isaac's delegated assistant, not Keith personally. Software/policy checks and nominal sizing can be completed here. The actual selected profile, current full holdings and signed execution gas envelope are not in this checkout; they have not been reviewed. These are data dependencies, not a requirement for Isaac to deploy anything.

## What is populated

- Wallet: `0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479` (development only).
- Proposed USDT input cap: 35 USDT = `35000000000000000000` raw units.
- Proposed fee ceiling: 0.0002 BNB = `200000000000000` wei per transaction, checked as `gas * gasPrice`.
- Exact five stock-input caps and router-only spender from the merged CP-01 proposal, unchanged. Native BNB is receive-only.
- Key delivery: `key_credential: wallet.key`, matching the existing systemd `LoadCredential` unit. There is no key value in this file.
- Dedicated signer DB role, Sydney region, standard CA/key paths, poll interval and clock skew from the existing example.

The example `cap_basis` is intentionally retained: neither the user delegating this review nor a successful boundary test establishes missing profile/holding/gas evidence. A dev-mode service may accept this label after other fields are filled, so do not treat the label as an installation lock.

## Explicit unset fields — Yao's assembly inputs

These six fields are intentionally null, never inferred from the existing unsigned shadow run:

| Field | Required value |
|---|---|
| `run_id` | The intended signed development run ID, shared with execution and initial state |
| `build_id` | The full commit of the selected CI release, shared with execution and the registered manifest |
| `database_host` | Actual RDS endpoint |
| `database_ca_sha256` | SHA-256 of the exact CA bytes installed at `/etc/larp/rds-ca.pem` |
| `router_evidence_file` | Signer's local path to the source-reviewed `RouterEvidence.v1` |
| `router_evidence_sha256` | SHA-256 of those exact evidence bytes |

The existing unsigned shadow run ID/build must not be silently reused. The router-evidence pair is optional for generic signer startup, but is required for a usable swap decoder; without it every swap stays refused. No verified router evidence is available here, and #27's signing-lifetime qualification remains separate.

## Numeric technical review

At the repository builder's 100-USDT rehearsal capital:

| Profile envelope | Largest input including 0.10-USDT reserve | Candidate cap | Nominal result |
|---|---:|---:|---|
| EQUAL_WEIGHT, 20% name | 20.10 USDT | 35 USDT | Covered |
| Proposed S1, 95% gross × 30% maximum name | 28.60 USDT | 35 USDT | Covered |

These are exact formula checks against `larp/strategy/profiles.py`, not a review of the unavailable deployed profile. The actual profile's `per_trade_cap_units` and `gas_top_up_cash_units` must each be no more than 35000000 micro-USDT. Every full stock holding and intended stock-input quote must fit its raw token cap; the cash cap alone does not prove that.

For fees, require all three comparisons: configured `max_gas * max_gas_price <= 200000000000000`; measured approve/swap fees fit separately; and each actual quote plus the gas-estimate/fallback limit used for signing fits. As an illustration only, 1116000 gas fits the ceiling only at gas prices no higher than 179211469 wei (about 0.179211469 gwei). No execution gas-price limit is selected by this illustration.

The token quantities are based on half of historical October 10 marks. That is not a guaranteed price floor, and splits, accumulation or a price decline can block a full sale. The current 40-USDT cost-capture size is measurement only: it exceeds this proposed development cash cap and must not be treated as an approved development trade size. Caps are per transaction, not cumulative loss or spend limits.

## Finish the handoff without Isaac deploying

1. Yao/Keith provide the selected development profile (and measured summary), fresh initial/current wallet state, intended execution configuration and relevant successful quote/gas evidence. Keep private RPC credentials out of chat and Git; the review can use local files. PR #155 supplies the hash-pinned numeric-review tool and remains a separate dependency, not part of this handoff.
2. Complete the missing profile/full-holding/top-up/fee comparisons above; record the reviewed file hashes and any value changes under #44. The assistant can do this review once the files exist locally. Do not write that Keith approved it unless he actually did.
3. Record Isaac's decision for the exact policy bytes; replace `EXAMPLE_PENDING_TEAM_DECISION` with its real decision reference only after that acceptance. Record the resulting policy SHA-256 (changing `cap_basis` changes it).
4. Yao fills the six host/run/evidence fields and checks the public CA file locally. Record the final complete `signer.json` SHA-256 and bind its exact bytes into the selected release manifest. The draft's hash is not the installed config hash.
5. Yao performs provisioning/route/config checks, then Isaac places the key in the separate approved session. No key is passed with this handoff. Activation remains gated by source evidence, #27 and the other Gate B checks.

**Message Isaac can pass with this folder:**

> This is the development signer assembly draft and delegated technical review, not an installation approval. The proposed caps and wallet are populated. Please supply the selected profile/wallet/execution inputs for the remaining numeric check and fill the listed host/run fields; keep signing off until #44 and the separate Gate B prerequisites are satisfied. No private key belongs in this JSON.

## Verification

Results and exact hashes are recorded below after checking the committed/pushed file. Missing-data checks remain NOT_RUN; the handoff will not be relabelled complete by synthetic tests.
