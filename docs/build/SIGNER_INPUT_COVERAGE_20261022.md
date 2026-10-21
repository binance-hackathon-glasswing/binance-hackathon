# SJ-01 — signer.json preparation and input coverage

Scope requested by Isaac, 2026-10-22 SGT: update PR133 with only the work needed
to prepare the development signer configuration; then finish input coverage.
The partner owns installation. Base: canonical `5bee006` (PR235).

## Four deliverables and owners

1. **Isaac / approved primary operator / funding owner:** fresh PR235 input
   coverage and exact input acceptance. Selected profile file `e95d5842…`,
   StrategyProfile `ddb82813…`, CAP-02 development policy `3241abd3…`, router
   policy `05759e90…`; initial gas only, cleanup disabled. Include complete
   reconciled holdings/metadata, nonce, allowances, absence of in-flight work,
   minimum/max BUY, full-size SELL and every required balanced child SELL.
   The assembler checks the 0.003072 BNB exit-reserve floor. The separate
   N=15 whole-rehearsal planning target is 0.008832 BNB. No funding is performed
   or assumed by this task.
2. **Keegan / release owner:** qualify source containing PR235 and retain the
   original artifact/manifest. RC2 `b22207e` predates the exit fix.
3. **Partner / coordinator / operator:** return the intended signed
   run/build/wallet/environment and actual execution IAM database/region/CA,
   profile/router paths and hashes, gas and RPC bindings privately. The
   numeric-review DSN stub and retired unsigned identity are not these inputs.
4. **Isaac / assistant:** assemble from complete pinned `GateBCapsInputs.v1`,
   run the production local signer/release check, and hand off the exact
   key-free signer.json, reports/hashes and matching dependency identities.

Host/session qualification, installation, key placement, activation, first
trades/receipt checks, drills and final S1/model/wallet adoption remain outside
this preparation. Existing false installation/signing/Gate-B flags are retained.

## Prospective task-1 pass criteria

Recorded before verification:

- S1: verify the `capture` branch archive's recorded SHA-256, ZIP CRC and every
  payload checksum; inspect actual quote dates and requested sizes against the
  exact selected PR235 profile. Report historical evidence as historical.
- S2: exercise the existing collector/privacy, numeric child/cap/reserve and
  assembler regressions on canonical source, with zero unexpected failures.
  Synthetic test success does not establish real input coverage.
- S3: real coverage requires a fresh primary read-only packet: unchanged host
  configs and matching wallet/registration, reconciled complete holdings,
  latest/pending nonce equality, zero allowances for this disabled-cleanup scope,
  no reservations/pending executions, all required request-bound quotes and
  child sizes, and the real review at the current clock within 300 seconds.
- S4: retain low-gas, stale/missing packet or refused quote blockers exactly.
  Do not alter balances, dates, caps, policies, reserves or approval flags to
  obtain COVERED. Only a complete actual input pass can close task 1.
- S5: no signer/key access, funding, signing, broadcast, installation, service
  change or ledger write. Keep exact private packets outside Git; publish only
  non-secret source/hash/count/blocker evidence.

## Inputs located before verification

Isaac identifies branch `capture`. Its head is `e26c96f`, containing
`captures/LARP-capture-complete-20261020T031658Z.zip`; its own README calls it
archival quote-cost data from Oct16–19, not profile/caps/deployment approval.
There is no local AWS profile or credential, and computer access to Chrome was
denied. No primary capture was attempted through an unapproved alternative.

Verification script and result will be retained in
`evidence/signer-input-coverage-20261022/`. Missing host evidence remains an
explicit operator input, not an additional signer implementation feature.
