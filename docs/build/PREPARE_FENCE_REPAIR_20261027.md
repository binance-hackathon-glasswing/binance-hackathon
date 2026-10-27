# FENCE01 — preparation refreshes current authorization before committing

A successful venue preparation can overlap ordinary runtime journal commits. The executor had persisted its work
probe before that I/O, but saved the prepared payload using the old run version. A stale CAS then consumed the probe
without leaving a prepared attempt. Repeated retries could exhaust the bounded preparation budget without signing.

## Change

- LiveGuards performs metadata/nonce I/O before binding the authorization version. It rejects ownership changes and
  a version race while obtaining the authorization facts.
- Executor.prepare retains the original probe reservation and does its quote, approval, gas and router-preflight
  work once. It then refreshes guards/current time, requires the original owner/release authority, and repeats the
  pure payload/sequence/current-prerequisite checks immediately before the existing fenced store commit.
- No new market/RPC operation follows that final refresh. Router preflight is still performed before it; future
  authorize/sign/broadcast phases continue their own checks.
- The live builder supplies the executor's clock explicitly. Preparation checks actual completion time, including
  time spent in the refreshed guards, against expiry and submission margin. Fixture defaults remain deterministic.
- Fencing queries fetch only epoch/version columns, avoiding repeated loads of the growing projection. The actual
  commit still locks the run and checks the expected version, ownership, chain, immutable intent and execution CAS.
- StateVersionConflict distinguishes a stale journal fence. The execution daemon logs blocked-cycle summaries with
  fixed exception classes and public intent IDs; arbitrary exception text is not logged.

## Safety and limits

No schema, profile, signer-policy, gas, slippage, work-budget or attempt-limit change. No automatic historical
counter reset. No key access, signature, broadcast or hosted deployment in this implementation step.

A race after the final refresh remains a refusal, as do revoked risk/reservations/version/health/clock, changed
nonce/owner, invalid payload/sequence and exhausted authority/margin. The fix tolerates benign version advancement
while doing external work; it never silently accepts a stale fence.

## Regression coverage

Synthetic PostgreSQL/fake-venue tests cover benign concurrent journal writes, adverse prerequisite and owner/nonce
changes, races after final refresh, actual expiry/margin and backwards-clock cases. Unit cases cover guard-acquisition
races, explicit native-route authorization, scalar-only fence reads and classification without exception text.
The new tests fail on the previous implementation. No live operational evidence is included in this report.

## Validation

Python3.12.15/PostgreSQL14.24: affected execution, signer, strategy, risk and marketdata suites **1258 passed,
1540 subtests passed,1 opt-in external-artifact skip**. All14 new fence regressions pass (8 subtests).
An earlier focused execution/signer/runtime check passed561 tests/1306 subtests. Composition fixtures were updated
to support scalar transactional fence reads; existing capability-gate assertions remain. pip/compile/diff checks pass.
[Machine-readable receipt](evidence/fence01-repair-20261027.json). No full new release/systemd/bundle or live pass is claimed.

## Rollout

Merge/review the source, qualify a new exact release, bind both hosts to the resulting registered manifest, and use
the reviewed same-run dev upgrade path with fresh holdings/caps/owner acceptance. Preserve the existing portfolio,
cost basis, journals, provider usage and historical attempt records. Do not reuse a bundle built before this fix.
Supported Linux/systemd/bundle and host acceptance remain required before deployment. The code-only PR does not
activate this repair on an already running service.
