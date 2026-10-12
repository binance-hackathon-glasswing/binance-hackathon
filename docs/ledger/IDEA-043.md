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

### Review progress 2026-10-12 (engineering evidence)

- PR15: concurrent author remediation preserved through ordinary merges; local full suite at 18ef02d: 695 passed, 3 Linux-only skips, 1052 subtests. Linux CI run 38226602692 all jobs PASS; merged to engine-foundation at 434229a. R01-R16/V01-V10 evidence in IDEA-041.
- Strategy dependency PR16: preserved c38eb98, added mandatory-sale precedence, overlapping timed latches, published directive consumption, confirmation margin, explicit fake-accounting mode and current producer fixture. At dba139f: focused 144 passed, 2 integration-dependent skips, 17 subtests; full 757 passed, 5 skips, 1052 subtests. CI 38227946185 all PASS; merged into foundation at 2136b58.
- PR9: C1-C4 4 passed against disposable PostgreSQL after replacing expectedFailure and binding fixture clock/run/wallet. CI initially failed on refreshed v2 fixture with old target compatibility consumer; synchronizing the reviewed strategy target preserves the actual v2 validator. Deep provider output also receives an explicit 64-level bound instead of relying on interpreter recursion limits.
- PR14: author B1/B2/B3 and S1-S5 fixes preserved; independently found I4 producer/runtime shape mismatches and added actual-consumer regressions. Focused component suite before final author follow-up: 125 passed, 3 consumer/recorded-response skips, 58 subtests. Latest author head 980529a adds immutable NOT_SUBMITTED facts and safe recovery authority.
- Combined PR13 diagnostics at 8f7830e: 907 passed, 4 skips, 1105 subtests, 3 failures (deep output recursion dependence, obsolete purpose test assertion, controlled refusal on malformed restored execution state). Fixed without relaxing validators. At c78e2a9, combined integration/receipt/restore/provider focus: 150 passed, 96 subtests, no skips. Earlier context tests exposed minimal offline fixture mode handling, now fixed while actual runtime mode remains authoritative.
- Outstanding: final combined system regressions/full suite/Linux CI; PR9/14/13 merges; foundation PR11 review/merge; separate system-testing branch and initial run. Production activation gates stay open.

### Final integration verification before PR13/PR11 promotion

- PR9 merged after CI 38230505451 PASS; PR14 merged after CI 38229704347 PASS (latest 173b35c differs from the verified code only in its result docs).
- At c4aec12: complete PostgreSQL suite **913 passed, 4 skipped, 1109 subtests** (108.22 s). Skips are three Linux bubblewrap checks and the external recorded-market artifact test. Actual service/receipt/reservation/audit/replay test and published RF1 independent-risk test PASS.
- Follow-up at 411ced9: focused safety/profile/manifest/operations tests **17 passed, 2 PostgreSQL-dependent skips, 3 subtests**. Prompts and Dockerfile are manifested; tampering either refuses release. Asymmetric gas regression ensures another token's larger budget cannot preempt an affordable mandatory sale. Full Linux CI on final head is required before merging.
- Kit/vendor copies unchanged; no secrets, environment files or private captures added. Final docs update leaves broad production/real-data backlog items open with explicit owners.
