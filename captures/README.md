# Completed quote capture — IDEA-063 ZIP-01

At Keith's explicit request on 2026-10-21, the complete Downloads ZIP is
retained on the dedicated `capture` branch of the private
`binance-hackathon-glasswing/binance-hackathon` repository.

`LARP-capture-complete-20261020T031658Z.zip` is the original ZIP, unchanged:

- Size: 49,009,956 bytes.
- SHA-256: `2dcb92c67c4e041019aeba759518e1aeb699182a59e4cb5016db2937be6f4755`.
- Contents: four daily capture files, 14,258 API-response artifacts,
  operational logs/notes, export metadata and the original payload manifest.
  The ZIP also retains the macOS metadata from the supplied file.
- Measurements: 1,924 bStock samples and 385 BNB quotes, across Oct 16–19 UTC.
  The export preserves two failures and the approximately 4 h 25 min gap.
- Quote requests and operational notes contain the public development-wallet
  address. Credentials, `.env` files, wallet keys and private labels are excluded.

Verification before commit: ZIP CRC passed; all 14,268 payload checksums and
14,257 retained decoded HTTP-response-body hashes passed. Raw ZIP members,
parsed JSON/JSONL values and decoded response bodies were scanned against the
locally stored Web3 key pair and credential patterns/fields, with no findings.
The non-secret receipt is `archive-verification.json`.

To check the ZIP from this directory:

```bash
shasum -a 256 -c SHA256SUMS
```

This is archival delivery of quoted-cost measurements. It does not approve
fee netting, measured swap gas, selected strategy profiles, signer caps,
deployment or trading. DC-01 and its remaining owner reviews are recorded in
[`docs/ledger/IDEA-063.md`](../docs/ledger/IDEA-063.md).
