# IDEA-043 — Open PR remediation and isolated system testing

- Date / owner: 2026-10-12 / Keith with Codex.
- Status: open; prospective criteria, tests NOT RUN.
- Authorization: user requests review and fixes for all open PRs, merges into their declared target branches, then a separate system-testing branch and an initial system test run. This authorizes ordinary pushes and merge commits, including foundation into main. It does not activate wallets, provision infrastructure, contact organisers, or use production credentials.
- Scope at discovery: PR #9 (integration tests), #13 (runtime), #14 (execution), #15 (evidence) target `codex/engine-foundation`; #11 promotes that branch to `main`. Existing strategy branch is an integration dependency; its existing unpushed work must be preserved.

## Prospective engineering acceptance

1. Review current PR descriptions, comments, inline findings, diffs and target history. Resolve reproduced defects through producer contracts, retaining fail-closed live safety gates.
2. PR #9: current golden request/result equals the pinned producer fixture, reaches canonical evidence-to-policy adapters, and the supported coordinator path commits an intent. Replace obsolete expected-failure wiring with a meaningful current adapter regression.
3. PR #14: fractional SELL proceeds settle conservatively with exact chain units/dust retained; malformed signer credentials never appear in exceptions; pending/failed RPC probes remain bounded and truthful; malformed commands fail closed; final observations respect captured authority. Execution can recover authorized/signed-but-unbroadcast attempts after safe authority changes without duplicate signing/broadcast. Add targeted regression evidence.
4. PR #15: SQLite-backed worker assessments complete safely; provider schemas accept valid tools/claims and close nested objects; raw provider bytes survive parsing failure; item headings differ from cross-references, stale amendments cannot create current directives; torn poll tails remain visible and subsequent records/cadence survive restart. Cover other reproducible review findings with focused regressions.
5. PR #13: verify prior runtime fixes and cross-component contracts, settlement/reservation release, stable round logs/ACKs, same-version restart, HALT behavior and replay. Fix interface mismatches using actual consumer validators. Preserve production readiness backlog.
6. All changed decision/trade/logging code and criteria committed and pushed before execution. Use synthetic fixtures and no live credentials. Report missing PostgreSQL/Linux/recorded-response coverage explicitly; Linux CI must pass required jobs before merging.
7. Merge reviewed child heads by ordinary merge commits into their declared target, then validate combined foundation and merge PR #11 into main. No squash/rebase/history rewrite. Recheck exact heads and CI before merging.
8. Create `codex/system-testing-20261012` from the integrated main commit; commit/push a reproducible system-test entry point and prospective cases before running it. Initial system tests cover real component contracts, synthetic day, final accounting/reservation release, durable restart/replay, audit identity/ACK behavior and execution failure/recovery; use disposable storage only.
9. Record tested commits, counts, CI links, failures and remaining owners here and in owner records as appropriate. Update only genuinely completed backlog work; readiness gates, real market/economic validation, credentials, host rehearsals and team decisions remain separate.

## Results and remaining work

NOT RUN. Initial checkout is clean main at origin/main. Five open PRs; #13/#14 are drafts. All merges and tests remain pending. Local pre-existing strategy worktree has one unpushed commit and is preserved.
