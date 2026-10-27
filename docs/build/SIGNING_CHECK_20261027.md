# SIGN-CHECK01 — signing on the shared integration build

Checked 2026-10-27. Canonical branch is `codex/system-testing-20261012`, fetched head
`305bccfa05d2b9db61c4284648b15d8d3d14ecc9`. PR133 is the noticeboard, not the build branch.
PR317 remains OPEN at `8e20a208`; its FENCE01 and FENCE01-RV01 repairs are not in canonical.

The signing components pass the scoped verification. The overall path to signing is still affected by the
known preparation race, so this is not an end-to-end reliability or current-live-host acceptance.

## Verification

On Linux/Python3.12.15/PostgreSQL14.24, with only disposable test accounts and synthetic ports:

```text
python -m pytest tests/signer tests/execution tests/runtime/test_round_driver_service.py tests/runtime/test_halt_split.py -q -rs -p no:cacheprovider
528 passed, 1294 subtests passed, zero skipped/failed in 39.09 seconds
```

This covers exact legacy transaction bytes/hash/chain/nonce/sender verification; RemoteSigner requests and
SignerService responses through PostgreSQL; immutable signature recovery across retries/crashes; signer-local
input/fee/spender limits; key-file permission/refusal handling; registered build/manifest/wallet identity;
current HALT/epoch checks, expiry/nonce refusals; and possible-send/crash recovery. Tests use ephemeral EVM
accounts and fixture transactions. No registered wallet key, .env, private config or live signing table was read.

The signer independently checks the run and its own pinned policy. Live market/chain observations reach the
offline signer through execution-supplied gates; these tests do not make those observations independent signer
RPC checks. No production signature or broadcast was requested.

## Remaining defect before signing

A separate synthetic PostgreSQL characterization on the same canonical application bytes reproduced:

1. With no concurrent runtime write, the intent reaches PREPARED in one probe.
2. With one harmless journal commit during each gas-estimation call, all three preparations fail their stale
   CAS. The durable intent has three consumed probes, zero prepared attempts and zero signatures/broadcasts;
   the fourth prepare refuses with `prepare probe budget exhausted`.

Both characterization assertions pass (2 tests, 0.350 seconds). The second test confirms the existing defect;
it is not a successful signing test. This is the FENCE01 issue fixed in PR317, plus its reviewed late-expiry
cleanup correction. Do not relax the final CAS or reset historical attempts to work around it.

## Existing hosted evidence and next action

IDEA-104 S5-COST03 records one finalized approval and BUY swap on release `3ae83098`, after planner writes
were paused; it also records five earlier intents exhausting preparation probes. That is recorded historical
hosted evidence, not a fresh observation of the current services or a release acceptance for `305bccfa`.

Release owner: merge reviewed PR317 and qualify a release containing it, including applicable systemd/bundle
checks. Approved operator: reconcile current state, preserve holdings/cost basis/budgets/counters, bind both
hosts to the registered release, and verify request → durable signature → canonical receipt → audit ACK under
ordinary runtime activity. Current installed build/unit health and this post-fix live acceptance remain unverified
by this audit. No host, key, config, policy, transaction or deployment change was performed.

[Criteria and results](../ledger/IDEA-104.md#sign-check01--canonical-signing-audit-criteria-2026-10-27-before-tests).
