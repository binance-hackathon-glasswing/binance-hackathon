# SJ-01 — signer.json preparation and input coverage

Scope requested by Isaac, 2026-10-22 SGT: update PR133 with only the work needed
to prepare the development signer configuration; then finish input coverage.
The partner owns installation. Base: canonical `5bee006` (PR235).

**Current after SJ-03 (2026-10-22 SGT):** Isaac's additional2USDT dev seed
is verified. Public finalized balance96USDT/0.005325625054330011BNB covers the
0.003072BNB signer exit floor. **The user's dev gas-seeding step is complete;
no further swap is requested for this minimum.** Remaining task1 is the actual
operator post-funding reconciliation/private current packet and exact input
review; task3 is the intended signed run/DB/CA/config bindings; task4 is offline
assembly/local release check. RC3a/PR238 records qualification of fa1b6c9.
The separate live-challenge wallet remains excluded. Dated pre-funding sections
below preserve original findings and do not re-open the completed user seed.

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

## Initial archive-only results — before concurrent PR236

Pushed audit source `777d80e` verifies capture head `e26c96f` without extraction:
archive SHA-256/CRC PASS, **14,268 payload checksums** and **14,257 decoded
response-body hashes** PASS. There are 1,924 stock samples, 385 BNB-price rows
and two preserved failures. All 14,258 API artifacts are `Web3Observation.v1`.

All **3,855 stock BUY requests are 40 USDT**. Each of the five stocks has zero
matches at the selected 18.637420 USDT minimum or 20.10 USDT cap. The newest
quote is 2026-10-19 23:57:06.475 UTC, already147,778 seconds old at this audit,
versus the real review's300-second limit. There is no current reconciled
portfolio/nonce/allowance/reservation packet or selected-profile full-exit/
child-quote packet. The archive remains valid historical cost evidence; it
cannot close the new PR235 coverage requirement.

[Machine report](evidence/signer-input-coverage-20261022/capture-review.json),
SHA-256 `a865d5a6da03ad043f147c80755bffe03bb126cea77c3182018a5f0c5249bde7`.

Canonical collector/privacy/caps/assembly regressions: **47 tests /141 subtests
PASS, zero skips**, macOS arm64/Python3.12.14; no PostgreSQL/live network/host is
needed or exercised by this selected suite. This is not a full release run.

A ready-to-run **read-only operator capture package** is generated privately at
`/private/tmp/larp-signer-sj01-operator-packet-20261022/`: `capture.sh`, selected
profile, `capture-parameters.json`, README and checksums. The payload compiles;
its generated script SHA-256 is
`692787e49a55c37fec5af9082a0247e202e86f4aaf8e083e939c55c6d59b69b3`.
Only the approved primary operator runs it; no key or signer access is needed.
It is generated reproducibly from pushed canonical code:

```sh
python -m tools.deploy.ld10_readonly_packet \
  --profile docs/build/evidence/rehearsal-exit-split-20261021/rehearsal-deterministic.json \
  --output /private/path/new-capture.sh
```

Use the existing [primary SSM procedure](ops/ld02-20261020/README.md) with this
new payload, preserving its original compressed output/hash/command identity
privately. The capture carries the selected profile and split function in memory;
it does not install the new runtime on primary. It makes no service/config/
ledger change. Re-run the canonical `tools.deploy.review_rehearsal_caps` on the
actual packet immediately at the current clock. An old packet must be recollected,
not replayed under a historical `--now` to claim current coverage.

**Still required, owned by the approved operator:** fresh primary packet,
including the changed exit sizes and current reconciled gas balance. **Then
Isaac:** numeric rerun and exact-input owner acceptance. The old gas snapshot
is not represented as current. No capture, funding, signer assembly or installation
has been performed. Task1/LD10 remains OPEN; tasks2–4 are unchanged.

## Concurrent PR236 — prospective receipt review

PR236 merged at `fa1b6c9` during SJ-01 and supersedes the missing-primary-packet
and new-release prerequisites above. It preserves the existing two-child profile.
Before verification: compare its public LD10-P04 receipt with the selected
profile/CAP-02/router and this independently generated probe hash; check all
published child cash proceeds, counts, reserve and gas-shortfall arithmetic;
read GitHub's RC3 job/artifact metadata; verify runtime/config/test bytes have
not changed after qualified `5bee006`. Public receipt consistency is not replay
of the private input packet; keep full owner/install/signing flags false.
Do not ask the operator to duplicate the pre-funding capture already delivered
by PR236. Remaining state work is a fresh post-funding reconciliation/review.

## SJ-01 review of PR236 — public consistency PASS; reserve remains blocked

The new canonical coverage/profile/scope/approved-policy bindings agree. Its
probe hash exactly matches the independently generated SJ-01 capture payload.
All published child proceeds stay within20.10USDT;22 total quote artifacts
match15 base quotes plus7 distinct child sizes. The recorded full-book reserve
matches4×2×384000000000000wei. NVDAB/MSFTB full-size quotes remain above the
cap only as sizing evidence; no over-cap child is admitted.

[Public receipt review](evidence/signer-input-coverage-20261022/pr236-review.json)
checks the exact profile document, policy/router/probe hashes, published balances,
counts and integer gas arithmetic. It does **not** replay unavailable private
original quotes/requested child amounts, assert new current-clock freshness,
forge personal owner approval or clear `OWNER_REVIEW_REQUIRED`.

PR236's RC3 receipt records all four jobs PASS and verified original artifact
12363800624 for source5bee006. Runtime/config/deploy/tool/test/vendor bytes in
this docs-only branch still exactly match that source. Independent mirror
metadata queries returnedHTTP404 for the current account; the original
artifact/CI were not independently downloaded or rerun by SJ-01. This access
limitation does not relabel PR236's recorded qualification as missing.

**Next operator/funding input:** resolve the reserve shortfall and supply the
actual reconciled post-funding private packet. **Then Isaac:** rerun the real
numeric reviewer within300s at the current clock and record exact input
acceptance. The larger whole-run target remains0.008832BNB (recorded shortfall
0.006137501130637114BNB), separate from the minimal exit-floor blocker. No
funding, live call, host write, key or signer assembly was performed by SJ-01.

## SJ-02 — current pre-funding check and Isaac's exact next action

At **2026-10-22 01:14:47 SGT** (2026-10-21 17:14:47.127UTC), the production
read-only chain reader captured finalized block128976212 on chain56 and
rechecked its hash. BNB is0.002694498869362886, USDT98 (18decimals), all five
stock holdings zero; finalized/latest/pending nonces2/2/2. **21 read-only calls**
within the25-call bound. No credential, .env, wallet key, approval, broadcast,
paid quote, AWS or host access. Existing funding gap remains unchanged.

[Public snapshot](evidence/dev-funding-preflight-20261022.json), SHA-256
`29d534bccc7ff907bb5f74ff79fa1022a9af646c1fb157a06ac81df6844789e1`. Original chain observations remain privately at
`/private/tmp/larp-sj02-funding-preflight-20261022/observations/`.
This is not the actual hosted run's PortfolioState/reconciliation, a wallet
activity lock, proof about unused signing authority, or a funding authorization.

For **only the signer reserve gate**, balance after the seed/fees must cover
**0.003072BNB**. The measured shortfall is **0.000377501130637114BNB**;
it is not an exact swap-output instruction because fees and quote economics
still affect the actual post-transaction balance. The separate whole-run
planning target remains0.008832BNB; neither target is a new permission to spend
or add capital. Do not automatically repeat the stale about2USDT handoff amount.

Isaac's remaining wallet step, following the existing FG02 handoff:

1. Approved operator confirms current eligibility: before this wallet's first
   agent trade and no in-flight work/unused authority. The local nonce/balance
   read alone cannot establish that host precondition.
2. If still needed under the agreed funding disposition, **Isaac himself**
   performs the MetaMask USDT-to-BNB gas seed from this dedicated dev wallet on
   BNB Smart Chain, using the existing organizer-provided USDT and the agreed
   USDT fee-token mechanism. No own/external funds, transfer or key export.
   The assistant does not sign/submit/confirm the swap.
3. Return only the public tx hash and displayed amounts/time. The assistant
   independently verifies canonical receipt, net USDT debit and attributable
   native evidence, and writes the actual funding note. Missing native trace
   evidence stays explicit; a current balance difference is not transaction-local
   proof of BNB received. No new hash has been supplied to SJ02 yet.
4. Operator captures fresh reconciled post-last-seed state/private LD10 inputs;
   assistant reruns current-clock numeric coverage and completes assembly once
   the separately required actual run/DB/CA/config bindings are supplied.

Sources checked: verbatim `official/source_page.md` dedicated-wallet text;
verbatim `official/kit/bstocks-trading-guide.md` gas/wallet text; SKILLF120/G13/Q03;
existing FG02 handoff and approved PR235/236 reserve/profile receipts. No new
organizer question, policy, approval or completed wallet action is asserted.

### SJ-02-U1 — wallet scope confirmed by Isaac

Isaac confirms on2026-10-22SGT that no additional dev-wallet gas swap has been
made since the recorded trial. He has a separate live-challenge wallet and
explicitly says it is **not to be used yet**. Current work is restricted to
the dev wallet; no live-wallet address, key, balance read, funding, registration
or activation is requested or performed. Its future handoff stays outside SJ02.

## SJ-03 result — dev gas seed verified; signer exit floor covered

Isaac completed additional dev seed
`0xab19e680522a72632fd3e0ad296c69b9901643de66d3fa218795bf35c57a168d`.
Production receipt verification confirms chain56, registered dev sender, nonce3,
success and canonical finalized inclusion at **2026-10-21 17:27:41UTC /
2026-10-22 01:27:41SGT**. Transfer logs show exactly2USDT net debit, no USDT
incoming; both dev seeds now total4USDT. Receipt gas is194643×50000000wei =
0.00000973215BNB; this does not independently classify MetaMask fee-token economics.
Displayed native credit0.00264317BNB is attributed rounded MetaMask evidence,
not a transaction-local native RPC trace or a whole-block balance difference.

At17:31:04.217UTC (Oct22 01:31:04.217SGT), the finalized public snapshot is
**96USDT**, **0.005325625054330011BNB**, all five stocks zero, nonces4/4/4.
The **0.003072BNB signer exit reserve is covered** with
0.002253625054330011BNB headroom. **No further swap is requested for this
signer minimum.** The separate whole-rehearsal target is not relabeled fully
funded and is not a request for another user transaction in this preparation.
The separate live-challenge wallet remains untouched.

[New receipt and public snapshot](evidence/dev-gas-funding-20261022.json),
SHA-256`e4d54fb62e641c185808bf48880a80ab5818bd5c845de7fa64e841a70619ea83`.29 successful observations /30 read attempts within the40
budget. A local quantity decoder first rejected a padded ABI allowance value;
the production word decoder corrected that processing. The original29 reads
were reused; one additional token-allowance call was refused by the provider,
not retried. Complete current allowances remain part of the actual operator
packet. None of this is a failed wallet transaction or a full numeric pass.
Raw public observations remain privately under
`/private/tmp/larp-sj03-seed-verification-20261022/observations/`.

**Current remaining work:** operator reconciles the actual hosted post-funding
state and supplies the fresh private LD10 packet/quotes plus actual intended
signed run/release/DB/IAM/CA/profile/router/execution bindings. Assistant reruns
the real current-clock numeric review, records exact input acceptance and
assembles/locally checks the key-free signer.json. Old91/92 rows and old
PortfolioState/quote timestamps are not edited to invent92/92. Source contains
no application/config/policy change, so RC3/RC3a runtime qualification is not
replaced by an unrelated test run. Installation/key/activation stay outside.
