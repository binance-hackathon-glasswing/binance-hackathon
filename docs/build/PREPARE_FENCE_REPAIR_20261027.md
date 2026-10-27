# FENCE01 — preparation refreshes current authorization before committing

FENCE02 update (PR319-RV01): bounded retries now tolerate transient races across refresh/pure validation/PREPARED,
and re-fence non-authorizing records including guard-acquisition races. Refusal/clean-cleanup records retain actual
completion time and never grant expired cleanup. The FENCE01 descriptions/results below are historical to their
named source; current combined-stack review and remaining gates are in [PR319 review](PR319_REVIEW_20261027.md).

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

PR317 independent review **FENCE01-RV01** is complete at runtime/test source `1e90c26f` (not deployed).
The review fixed one remaining failure-path defect: completion time was assigned after final validation, so
an expiry refusal could decide cleanup using the original cycle time and reset its probe counter. The executor
now retains each valid completion-time observation before validation and persists that time on refusal.
Expired authority/margin ends the approved intent without granting cleanup; an expired route with remaining
parent authority still permits only the existing bounded zero-only cleanup. Confirmed approvals are preserved.

New regressions reproduced all four post-approval expiry/margin cases on the original PR head, plus stale
timestamps for a route-deadline refusal and an unapproved intent. The final Linux fence/cleanup/worker check
passes **37 tests / 44 subtests**, including actual bubblewrap isolation.

Pinned Linux/Python3.12.15/PostgreSQL14.24 full run: **3094 passed, 4136 subtests, 9 skipped**, with five
environment failures (three checks lacked the worktree's Git metadata; two bubblewrap checks could not mount
`/proc` in the default container). All five pass with Git metadata mounted and the required namespace/proc
permissions. Two initially skipped origin/non-root permission checks also pass in the corrected environment.
Combined coverage is **3101 distinct tests passed**, zero unresolved failures, **7 remaining skips**: five real
systemd tests, one optional recorded-market fixture and one optional private source fixture. This is a full run
plus targeted reruns, not a single all-green full-suite invocation. Offline demo, all four dependency lockfiles,
pip and diff checks pass. [Review receipt](evidence/fence01-review-20261027.json).

The earlier author validation below applies to `d7318f71`, before this review repair:

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
