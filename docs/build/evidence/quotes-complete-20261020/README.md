# DC-01 — completed Desktop capture: analysis and profile candidates

2026-10-20 / Keith, with Codex. Criteria: IDEA-063 DC-01, committed/pushed
at `4035d93`. Canonical base `928b8a8`; final verifier source `85adb01`.
**#118's capture/summary/profile-construction deliverable is complete.**
LD09's current execution packet, #119 fee inclusion, #120 profile acceptance
and #44 caps remain open. These are quoted costs, not fills or deployment proof.

## Inputs and verification

Private input: Desktop folder `LARP-capture-complete-20261020T031658Z`.
All **14,268 payload checksums** match its SHA256SUMS (manifest SHA
`b17002b02570332b40cbcb68fe072c9afffe4dfda19c0f2c0b6118c07c5ffc01`).
The export declares capture source `eda2ed2ab1ab4b72f220eb6b92e882737d950825`;
this is exported metadata, not a fresh host/source attestation.

[Verifier](verify.py) checks all 14,258 content-addressed API artifacts,
request/response chain/token/amount/vendor bindings for every successful sample,
gas arithmetic and metadata open-state bindings. All 10,390 distinct referenced
artifacts verify (11,929 occurrences). **14,257 raw HTTP response-body hashes**
also verify against their retained base64 bytes. One unreferenced HTTP502
non-JSON response has only its transport hash; its body was not retained and
cannot be independently rehashed. The 3,868 unreferenced artifacts include
failed gas estimates and partial rounds, not extra successful samples.

[Receipt](verification.json) retains daily hashes, exact failures, gaps, endpoint
timings, quantity ranges and the historical cap screen. No original JSONL, raw
API response, operational log, wallet key or credential is committed here.
[Independent YP-01 replay](interim-verification.json) reproduces the original
interim summary and report coverage/symbol details, verifies its original byte
prefixes and confirms final defaults still refuse that earlier snapshot.
Its capture hash `2ec51d514bff738a1b09a5c0be694d69a0e1334dc3bc2990b9c7d57354dde7da`
is distinct from the completed capture below. No historical profile is replaced.

## Completed coverage and cost output

Observed Oct16 18:19:09.205–Oct19 23:57:06.600 UTC: **1,924 stock samples,
385 BNB quotes, two recorded failures**, four UTC dates and both weekend dates.
Unchanged defaults pass: at least three dates, weekend, ten samples/token/regime.
All successful samples report `openState=true`; this is observed availability,
not proof of continuous availability. BNB's largest success gap is **4h24m44.160s**,
Oct18 02:31:22.826–06:56:06.986 UTC; token gaps are separately recorded.
Failures: Oct18 authentication/ROUND and Oct19 MSFTB SELL_QUOTE. No row excluded.

| Token | US / off-session samples | Spread bp | Impact median bp | Slippage bp |
|---|---:|---:|---:|---:|
| NVDAB | 43 / 342 | 4 | 1 | 6 |
| GOOGLB | 43 / 342 | 3 | 1 | 4 |
| SKHYB | 43 / 342 | 2 | 1 | 8 |
| TSLAB | 43 / 342 | 5 | 1 | 6 |
| MSFTB | 42 / 342 | 17 | 1 | 8 |

These are the producer's rounded, worse-of-regime statistics, not guaranteed
spread/impact/slippage bounds. Median impact has the existing 1bp floor. BNB
quote median is 722.150988 USDT/BNB. TTL remains kit-stated 30s, not measured.
All **3,848 swap-gas estimates are FALLBACK**; no successful swap simulation or
actual approve/swap gas is supplied. Additional fee is zero only under the
explicit **UNVERIFIED** quote-netting assumption (#119); `tradeFee` remains
network-fee metadata, not an additional route-fee rate. The old capture has
legacy BUY-only fee metadata; no missing SELL/REQUOTE fields were invented.

## Candidate construction and cap exception

The unchanged builder produces EQUAL_WEIGHT rehearsal/final candidates with
the published predicate set. SP-D2 already supplies the conditional EQUAL_WEIGHT
fallback rule; this construction does not accept an unseen profile or S1 scope.
No selected S1 weights/parameters, actual current holdings or signed execution
scope can be derived from these quote records.

| Value | Rehearsal candidate | Final candidate |
|---|---:|---:|
| Expected equity, USDT | 100 | 200 |
| Minimum trade, USDT | 17.745807 | 17.745807 |
| Per-trade cash cap, USDT | 20.10 | 40.20 |
| Cost reserve, USDT | 0.10 | 0.20 |
| Top-up cash, USDT | 0.663460 | 0.663460 |
| Exit reserve, BNB | 0.000304710536704 | 0.000304710536704 |
| Gas trigger floor, BNB | 0.000457065805056 | 0.000457065805056 |
| Top-up min receive, BNB | 0.000914131610112 | 0.000914131610112 |

The minimum follows the existing 50bp algebra, using fallback p90 gas and the
zero-additional-fee assumption. It fits a nominal 20-USDT rehearsal position,
but neither gas nor quote-size transfer is qualified. Existing windows are
preserved: rehearsal Oct21 00:00/new-risk end Oct22 00:00/flatten Oct23 00:00/
signing end Oct26 14:45 UTC; final Oct29 00:00/Nov9 00:00/Nov10 00:00/
Nov11 14:45 UTC. No window or policy is newly adopted.

Against CP-01's **unapproved** 35/70-USDT input limits, both candidates' cash
and top-up amounts fit their corresponding environments. All historical BUYs
are 40 USDT: all 1,924 exceed the development input limit and none exceed the
final one. Sampled SELL token quantities fit both draft per-token ceilings;
they are sells of the just-quoted buy output, **not current full holdings**.

**One fallback gas product exceeds the draft per-transaction fee cap:** NVDAB
BUY, Oct19 19:20:59.049 UTC, quote artifact
`07f43952ccbb347b7327a45a9decec2949cfa1f32d4a781a1f4a86be310f12b2`.
Quote gas=250,000; fallback limit=1,116,000; gasPrice=181,069,783wei;
product **202,073,877,828,000wei = 0.000202073877828 BNB**, above
200,000,000,000,000wei (0.0002BNB) by about 1.04%. This is an estimated
worst-case signing allowance, not gas spent. All sampled approve products fit;
p90 swap products fit, but those statistics do not erase the exception.
No cap is raised or approved. The aggregate two-transaction budget and native
top-up execution remain separately unqualified.

## Exact hashes

SHA256SUMS contains file-byte hashes. Document-domain hashes are separate:

- Capture hash: `407a08e744aaaaf95e30f006deb56a59b220a2bb2fe1f8b9b21b4fc118986ecd`.
- Summary file: `9d4479e3b02e0aceb2c739e7292b8ca80043972b5c258734c7439a979ef1946a`.
- Report file: `a43bbd26c1e418231d056c2b7e641d58a1640d8817ecff766d56cf1002527ca3`.
- Rehearsal file: `401739f5dfdcbbd38e26a58c66fa76855e5377427234ca60fb0b7a8395d4060f`;
  StrategyProfile.v1: `ed67dfca62750b898aad2f6e932c626bb00a5b72c40f57d827d96af7f1487039`.
- Final file: `7151a55d145d64d17c9cec880442027a947bb05f58c7af11cf1426eab3f61bae`;
  StrategyProfile.v1: `adcf1032beb17569a792db7ee39a9bef37d84d799c3f7f13e487ee0541e24d9d`.

The builder's `LIVE`/`MEASURED_AND_DECIDED` schema labels do not confer review
approval. These files are evidence candidates; runtime/config/manifest pins
and readiness flags are unchanged. Full private captures stay on the Desktop.

## Reproduce and remaining owners

From repository root, with the existing dependencies installed:

```sh
PYTHONPATH=. python docs/build/evidence/quotes-complete-20261020/verify.py \
  --captures /path/to/LARP-capture-complete-20261020T031658Z
PYTHONPATH=. python docs/build/evidence/interim-provenance-20261019/verify.py
```

The first command verifies the full private export and reproduces this summary,
report and both candidate files exactly; neither command calls a network port.
The original `cost_summary summarize` and `strategy.profiles` CLI commands
were also exercised with no override flags and output under a new private temp
directory. Local macOS arm64/Python3.12.14 producer/consumer regression:
**249 passed, 1 skipped, 161 subtests**, 16.96s (`tests/marketdata tests/strategy`,
plugin autoload disabled; supported `PYTHON` points to the same interpreter).
The skip is the opt-in external recorded-market corpus. No full-suite,
Linux/host/release or new hosted CI acceptance is inferred.

Remaining: **Isaac/Keith #120** review exact summary/candidate hashes, size
transfer and the fee-cap exception; **Isaac #119** supply attributable route-fee
semantics or the gated first agent quote/receipt comparison; **operator/Isaac**
supply fresh complete holdings/reservations/nonces, actual requested-size and
full-exit quotes and usable approve/swap gas; **Keegan/Isaac LD07/08** decide and
qualify native top-ups versus an explicit initial-gas-only scope. The proposed
floor only budgets several legs; it is not a measured whole-run gas reserve.
**Keith/Keegan LD11** finalize selected S1/fallback parameters/weights/windows;
**Isaac LD10/#44** independently accepts exact caps/profile/input hashes after
the current packet exists. LD09 remains partial until those measurements are
supplied. No host, provider, paid inference, key, signing or deployment action.
