# PC-FIX01 — DOJ, source coverage and unsigned trial caps

Yao requests code fixes for Keegan's PR review and a subsequent new release.
Base: integration e7479b2. PR133 stays open. No AWS mutation, paid provider
inference, activation or release publication here.

## Prospective acceptance (before executing new code/tests)

- SRC1: reproduce an oversized DOJ history continuation while current listing
  polls succeed. Preserve durable cursors/artifacts and original failure logs;
  recover with bounded retrieval without skipping items or enlarging global
  response limits. Preserve error identity when recovery cannot succeed.
- SRC2: current-listing checks and bounded history work have separate explicit
  coverage evidence. Forward-window coverage needs a complete current-head scan
  anchored to earlier durable records. Missing anchors, item rejection, transport
  failures, corrupt logs and cadence gaps still fail. Historical completeness
  stays separately visible. Restart and moving-listing regressions are required.
- SRC3: legacy poll logs remain readable; reports retain original failure and
  truncation counts and cannot turn the old24h FAIL into PASS by reinterpretation.
  No log rewrites or blanket incident exemptions. Oversized individual items and
  poisoned pagination URLs remain bounded failures.
- CAP1: opt-in immutable unsigned-trial identity/window/US$8 total/US$2.50 UTC
  day limits are hash-pinned in routing and durable ledger state. Each OpenAI
  POST reserves its conservative maximum atomically against account/pacing/trial/
  dispatch-day headroom, counting concurrent workers, retries and UNKNOWN.
  Exact-cap admission refuses to keep spending strictly below support limits.
- CAP2: transport boundary rechecks UTC day/window and refunds only known-unsent
  work. Settlement retains dispatch-day attribution; unknown/sent failures keep
  full charges. Rollover never resets trial total; rollback cannot restore credit.
  Prior safety latches remain and cap stop disposition is explicit in audit/status.
- CAP3: explicit setup/migration preserves all charges/latches; missing, stale,
  mismatched or corrupt accounting refuses startup/dispatch. Legacy v1/v2 behavior
  remains covered. Signed adoption stays separate.
- OPS1: provide matching host preparation/report/status/export instructions and
  remaining account/P0/start/labels/affordability checks. Code alone cannot supply
  72 observed hours or independent labels; no paid calls without Yao's action.
- TEST1: push each executable revision before running it; record focused red then
  green regressions and an appropriate combined suite with honest skips and log
  hashes. No golden regeneration or weakened checks. Keegan reviews/builds later.

Results will be appended with exact pushed SHAs.
