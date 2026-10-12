# System testing — IDEA-043

The working branch is `codex/system-testing-20261012`. The original PRs were reviewed, fixed and merged into their declared targets; foundation PR11 then promoted the reviewed build to main. PR17 fixes the critical-clear / timed-block collision reproduced during system testing. This branch preserves testing tools and evidence separately from main.

`tools/system_test.py` requires a clean branch whose exact head has been pushed. It runs real coordinator, PostgreSQL execution-store/service, receipt settlement, reservation release, audit ACK, restart/recovery, restore, replay and release-manifest checks with synthetic external transports. Child tests receive no production credentials and may connect only to local fixtures. Raw output stays outside Git; the committed report records counts, tested commit and output hashes.

Use Python 3.12 with `deploy/requirements-test.lock`. Set `LARP_TEST_DATABASE_URL` to a disposable local database whose name starts with `larp_test`, and `LARP_SYSTEM_TEST_DISPOSABLE=1`. The session's database is available at `postgresql://postgres@127.0.0.1:55432/larp_test` in container `larp-system-postgres-20261012`. `deploy/compose.test.yml` defines the same pinned disposable database for another session.

```sh
LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/larp_test \
LARP_SYSTEM_TEST_DISPOSABLE=1 \
python tools/system_test.py --output-dir /private/tmp/larp-system-next
```

The offline demo requires Linux bubblewrap. On macOS, add `--linux-ci-run 38234572440` for this verified runtime tree; the runner verifies the successful demo/job and checks that its tested runtime/config/deployment/migration/workflow/dependency tree equals the current tree. It never reports the demo as locally executed or bypasses the sandbox. `--system-only` runs the focused system checks; omit it for the full suite too.

Results are in [IDEA-043](../ledger/IDEA-043.md) and the adjacent committed `evidence/system-test-20261012*.json` reports. Local Linux-isolation skips and the absent external recorded-market artifact remain explicit. The registered-wallet, real-source/model/economic, hosting and signed-rehearsal gates remain open with owners in [INCOMPLETE_WORK](../INCOMPLETE_WORK.md).

## Verified result (2026-10-12)

- Final system branch at 52d3519: **78 passed, 31 subtests, no skips**, with Linux-isolated demo evidence verified against CI 38234572440.
- Complete final Linux suite: **919 passed, 1 skipped, 1109 subtests**; demo, Docker and both Terraform jobs PASS. The single skip is the external recorded-market artifact check.
- Prior complete local baseline at b49e255: **915 passed, 4 skipped, 1109 subtests**; four skips = three Linux-only sandbox cases and the external recorded-market artifact.
- All original PRs and dependency/follow-up PR16/17 are merged; no open PR remains. Main is 5e945e1. The system-testing branch remains separate and is the active workspace branch.

Raw final logs are retained outside Git at `/private/tmp/larp-system-results-20261012-final/`; hashes and exact tested commits are in the JSON report. Reports copied here contain synthetic test metadata only.
