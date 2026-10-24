# S3 REHEARSAL profile (IDEA-092, 2026-10-24)

The candidate `StrategyProfile.v1` for S3: S2 (IDEA-089) plus a scheduled sell-all at **12:00 SGT on Sun Oct 25
(2026-10-25T04:00:00Z)**. After the sell-all, S2 runs as usual from a fresh book.

This is a **candidate for review**. It is not approved, not built into a release, not installed and not bound to a
`signer.json`. Like S2, it is a dev REHEARSAL profile only and is never installed for the final run.

| File | SHA-256 |
|---|---|
| `../s2-rehearsal-profile-20261024/s2-block.json` (the profile's `s1` block, S2's unchanged) | `35e20c38e23657da6723e31b18f323e5f5ede778de938d73c72ff1a2c1408d03` |
| `rehearsal-s3-deterministic.json` (file bytes; the `PROFILE_SHA` to pin) | `2fb32b8e9ba342192ad57b61059654409ffbe3fad04e900c1887053a263f1526` |
| `StrategyProfile.v1` digest of the same profile | `127ce7968c19c8bc27ffa12c92341d2ce33a5aa71d7243c1952a32eb30157eb9` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile rehearsal-s3-deterministic.json`; the `PROBE_SHA` to pin) | `142e1b06eb59b985f7680cbf96a0f7ae9a58ad3089b8bcd812e99c3bcce8085e` |

## Against S2's profile `eb55d76a…`

S3 differs from S2's profile only in these keys:
- `scheduled_flatten_at` `2026-10-25T04:00:00Z`;
- `policy_id` `larp-s3-rehearsal-v1`;
- the provenance of those two keys.

Everything else is S2's: the S1 block (`KIT_OPEN_STATE`, 5 attempts per leg), the window, sizes, caps, gas, the quote
summary and the SHADOW scope.

What the agent does with it:
- **Before the time:** S2.
- **From the time until the book is flat:** every held name is a mandatory SELL (`SCHEDULED_FLATTEN`, mandatory lane).
  No BUY is planned (`SCHEDULED_FLATTEN_PENDING`).
- **Then:** the round records `scheduled_flatten: DONE` in the risk state, and S2 buys again. S1's "never re-enter a name
  held before" block is lifted only after DONE.
- **Unchanged:** the terminal flatten from Sun 09:00Z and `signing_end` Sun 15:00Z.

## Before install (not done)

- **The wallet must be stock-flat at install.** `gate_a.initial_state` refuses existing holdings. Run 4 (S2) holds
  stocks until its own flatten from Sun 09:00Z, after this profile's noon. Installing S3 this weekend therefore needs
  run 4 retired flat first, or S3 rebuilt with a later `--scheduled-flatten-at` and window. That is the team's call
  (Yao; Isaac approves the hash and `signer.json`).
- The usual RC sheet steps: release build, Q1 quote check, D1 database, M3 coverage, Isaac's approval, install.

## Reproduce

```bash
python -m tools.deploy.build_rehearsal_candidate --exit-children 2 \
  --s1-config docs/build/evidence/s2-rehearsal-profile-20261024/s2-block.json \
  --s1-decision "IDEA-089 S2-2/S2-9 (Yao, 2026-10-23): run-3 block (IDEA-084 PF-01 values; weights 1/5, SJ-09-PC01 C5; start UP, legs 3, expiry 3, Keith 2026-10-23) with hours KIT_OPEN_STATE and 5 attempts per leg" \
  --scheduled-flatten-at \
  --output /tmp/s3-profile-check.json
```

Bare `--scheduled-flatten-at` uses `2026-10-25T04:00:00Z`; pass a value for another time. The command prints the digest
above, and the output must be byte-identical to `rehearsal-s3-deterministic.json`.

Checked offline in `tests/strategy/test_s3_scheduled_flatten.py` (IDEA-092 S3-1..S3-7).


## PR277-RV01 source review (2026-10-24)

The candidate bytes/hashes above are unchanged. The reviewed source bounds pre-schedule BUY command and independent
execution/signer/broadcast authority at the cutoff. The first flat/DONE plan permits re-entry; pending reservations
still prevent DONE, and already submitted transactions still reconcile. All16 S3 strategy/profile/PostgreSQL cases
pass. See [review receipt](../pr277-review-20261024.json) and
[IDEA-092 review](../../../ledger/IDEA-092.md#pr277-rv01-results--pass-for-source-merge-2026-10-24-sgt).

The scheduled time starts sequential mandatory exit planning; it does not promise all fills in one round.
Unexecutable holdings keep BUYs blocked. Noon and terminal sells share SAFETY attempts; DONE resets no BUY, leg or
SAFETY budget. An install after the schedule on a flat wallet can skip actual scheduled sales by immediately reaching
DONE. The full cycle's fresh gas/exit/attempt coverage and H1/H2/install approvals remain required. No carry-over,
manual sale, funding or deployment is authorized by the source merge. Active run4/RC7 is unchanged.
