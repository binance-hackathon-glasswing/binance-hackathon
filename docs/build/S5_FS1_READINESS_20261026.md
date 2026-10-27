# S5 and FS1 deployment readiness — PR297-RV01

Review date: 2026-10-26 SGT. Canonical input: `d4f7a6e0` (PR296 merged).
Probe repair source: `df01d9cb`; Keith's unchanged public live evidence: `84f0fd47`.

**Deployment readiness: S5 BLOCKED; FS1 FINAL BLOCKED.** Source preparation and
synthetic acceptance pass; the remaining actual inputs/approvals below are not
supplied by a probe PASS or a repository merge. No host or wallet was changed.
FS1 can be prepared independently of S5.

## Verified evidence and source

- Keith's [live capture](evidence/th01-live-20261026/timestamp-evidence.json)
  hashes to `cc8371bd235eb4db284367fbf0267890d3c6a87bafca60ca2573f0b9d64b3fa6`.
  Offline replay with the repaired assessor returns the identical stored PASS
  on GOOGLB, MSFTB, NVDAB, SKHYB and TSLAB. Every successful source observation
  replays from its hash-named raw artifact using the production MarketPort;
  all442 artifacts verify (440 candle responses, two metadata responses).
  No provider request was made during review. Original evidence bytes and TS4
  trade-count calculation are preserved. TH-CONFIG01 now supplies the actual
  config with a descriptive label for existing raw-token/no-local-adjustment
  processing; no further naming decision is needed. Release binding remains.
- Nine regressions fail on original `35aab2dc` and pass with the repair:
  absent/modified raw files, edited candle rows/availability/request identity/
  metadata, poll-start versus response-time confusion, repeated observation
  times and misaligned minute labels. All30 probe tests pass.
- 201 focused history/session/strategy/PostgreSQL replay/S5/FS1 preparation,
  recovery and startup tests pass. Synthetic FINAL caps/signer assembly and
  independent FINAL preparation pass; production history and routed assessor
  requirements remain enforced. S5/FS1 profile, routing and runtime code bytes
  are unchanged by PR297.
- Full pinned-suite results and environment are recorded in
  [the review receipt](evidence/pr297-review-20261026.json). The three worker
  sandbox cases pass separately in the existing bubblewrap-enabled image;
  its offline runtime demo also passes. Systemd/actual hosts are not qualified.
- GitHub run40311935172 executed no jobs because account payments/spending
  limits prevented startup. This is not a CI PASS or a qualified release bundle.

## Shared prerequisites still open

| Input / decision | Owner | Required evidence |
|---|---|---|
| Bind generated `TokenHistoryConfig.v1` | Keegan; Yao transfers | TH-CONFIG01 supplies [token-history.json](evidence/th01-live-20261026/token-history.json), SHA-256 `5e572570bc24fb2ca7b692dccf71f67a37c5fac3d75330e4558634cf45417be9`, generated/reproduced from the committed verified evidence. Use its exact bytes in preparation and accept the resulting release binding. Generation/naming is complete. |
| Exact release and configuration | Keegan; Yao prepares | New canonical build containing PR295/296/297, verified bundle/manifest, explicit run/database/wallet/RPC/CA bindings, reviewed operations and service configs. Historical RC4 or offline test results do not qualify these exact bytes. |
| Current chain/caps/signer | Isaac; Keegan/Yao supply inputs | Fresh reconciled balances, nonce, allowances and request-bound quotes at selected sizes; actual BNB/action/full-exit coverage; accept exact profile/probe/signer/release hashes before installation. |
| Model/account adoption | Team, account owners | Actual FS1 routing adoption reference, reconciled shared OpenAI ledger/prior spend and provider keys/rights. S5 consumes that same account budget. |
| Host acceptance | Yao with operator owners | Transfer the pinned history/routing inputs, Gate A/preflight and both-role checks, then verify current-host five-token history/trend, service startup, reason summaries and delivered logs. |

## S5-specific checklist

- Profile `6dadc1961a54374f51415e2168ff8d4a917b28f90e58c9493a1b9fbd8731e80d`;
  numeric probe `68e49922432f8a8e8081fbaa32b3d8bb3b5614a5ca2982b6ed5ee671262f8e17`.
  Current source supports up to four19-USDT opening lots at the dated81.37USDT
  balance; exact current quotes/cash may still refuse an entry. No top-up step.
- A1 still needs acceptance of these SIZE01 pins and the newly assembled signer.
  Historical R3 acceptance does not adopt the changed sizing profile.
- M3/M4 require fresh flat development-wallet state, the run6 identity/diff
  checks, new run `larp-dev-rehearsal-20261026-s5` / DB `larp_rehearsal7`, and the
  shared history/model inputs above. PR296 is already merged.
- Follow [the S5 sheet](ops/rehearsal-install-s5-20261026/README.md), including
  execution before runtime and the live J checks. New risk ends **Oct27 07:00SGT**,
  flatten starts **08:00SGT**, signing ends **12:00SGT**. A late install must not
  silently move these windows. Record trades, recovery/zero allowances and
  retirement before FINAL; no live S5 acceptance is claimed by this review.

## FS1 FINAL-specific checklist

- Recovery profile `b8ba06e248b48b6406d77c1bda4110001324382e91bb63c71a27ce514731892f`;
  routing `9b86c7327eddca76e0739f6639211f9b609f18c027bc4e61bf83dc804dfcf1f4`.
  [Standalone preparation](ops/final-fs1/README.md#standalone-preparation-pr296-rv01)
  and FINAL P3/P4/P5/P6 source exist and pass offline; no retired S5 signer or
  development ledger is required.
- F0/F0m/F0b: accept strategy/history/model values and adoption, resolve GAP-73's
  fixed-price BNB risk valuation, reconcile account budget and confirm FINAL
  execution RPC/finality qualification (GAP-29).
- F0w/F0k: verify actual final-wallet funding, required gas-seeding record,
  uploader identity and signer key binding. This review did not inspect secrets
  or perform funding/key/host operations.
- Fresh FINAL Q1/M3 artifacts at FS1 sizes are still needed; the run3/dev quote
  checker is supplementary. Obtain current final-wallet quotes and full numeric
  coverage with the final policy/recovery gas before Isaac's exact A1 approval.
- F0d/F0p: required database monitoring/parameters and registered final release,
  database/configuration/host checks remain. Record actual self-check BUY/SELL,
  reason summaries and delivered trace before scored handover (J-SC/GAP-74).
  Complete startup by `2026-10-28T02:00Z` so the self-check is done and ACKed by 09:30Z, before the F-127
  pause at `2026-10-28T10:00Z` (the profile's later `buy_until` 18:00Z is not usable);
  no self-check result is inferred from synthetic tests.

Authoritative remaining work: [TH-01, IDEA-093/104, GAP-29/62/73/74/75 and
account/host gates](../INCOMPLETE_WORK.md). Keep their partially completed items
until actual acceptance evidence exists.
