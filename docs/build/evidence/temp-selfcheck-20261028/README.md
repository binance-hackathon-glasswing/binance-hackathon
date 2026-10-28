# IDEA-110 TA-01 — temporary pipeline release

[Published assets](https://github.com/binance-hackathon-glasswing/binance-hackathon/releases/tag/temp-selfcheck-e261bcfc) / [PR324](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/324).

Build `e261bcfc7a339a5e28388b843798b4197a9993a6` includes the preparation-fence repairs and the scoped temporary activation repair. It is based on canonical2aa95617. The generated profile is [strategy-profile.json](strategy-profile.json); the [machine receipt](release-receipt.json) records hashes and checks.

One0.90USDT SKHYB BUY then a mandatory full SELL; no discretionary strategy BUY. Buy04:00–06:00Z Oct28 (12:00–14:00SGT); signing ends08:00Z. Prepare/activate/install before06:00Z. Profile file SHA256 `b2e85827c65d99b709c0d958c2b1bf734e62cc271bba35ac536284dcba1b4187`.

For the already-created quarantined run, install/bind this new build and service configs, then use the [P4](../../ops/final-selfcheck-temp/host/p4-init-activate-start.sh) third argument `existing-quarantined`; no init/reset. Continue S2/P5/P6 in the [run sheet](../../ops/final-selfcheck-temp/README.md). Fresh quotes/caps, registration/version event and host checks remain operator work. No deployment performed here.

Full pinned Linux:3165 passed/4172subtests/11skips/0failed,290.42s. Three skipped bubblewrap cases pass separately in the sandbox-enabled pinned-Python image, giving3168 distinct passes and8 checks unrun (5 real-systemd,2 optional external fixtures,1 root-sensitive permissions). Focused macOS/Python3.12.14/PostgreSQL14.24:79 passed/17subtests. Actual offline AmazonLinux2023 provisioning twice per primary/signer role and bound manifest verification PASS. All217 release source files and256 archive checksums verified. Offline sandboxed demo PASS after correcting its missing test-image bubblewrap prerequisite; the first full-suite attempt was stopped to replace slow host-network database routing with a direct container connection. No product change was needed for those environment corrections. Hosted CI40623823267 ran zero steps due payments/spending limits.

The build uses the standard bundle builder with its dependency-fetch hooks: Python/wheels/CA reused from checksum-verified published archive a4511e4a…; all Python/dependency lockfiles were compared byte for byte and unchanged. Builder Python checksum and wheel-pin validation, followed by all archive/manifest checks, pass. Application files are newly archived from pushed e261bcfc, not reused from the prior release.

The nine FS1 DRAFT rows remain in the release register. The exact temporary activation journals their IDs and scope; FS1's scored activation still requires finalized declarations/services. GAP-62 remains open. Actual pipeline completion requires BUY/SELL tx hashes in logs, receiver ACKs, DONE and a flat/allowance-free wallet.
