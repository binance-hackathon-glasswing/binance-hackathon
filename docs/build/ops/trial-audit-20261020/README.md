# PC-AUDIT01 read-only reproduction

Run from the repository root with Python3.12, against canonical697ff3a application
bytes. The audit checks its intelligence sources against the current canonical
remote-tracking ref; retain/fetch the exact audit baseline when reproducing later.
The private PC-STOP01 `final-data/` directory and its sibling `final.tar.gz` are
required. Use a private output directory; the scripts set its mode to0700.

```bash
export LARP_AUDIT_DATA_DIR="$PWD/deploy/activation/trial-stop-20261020/final-data"
export LARP_AUDIT_OUTPUT_DIR="$PWD/deploy/activation/trial-stop-20261020/audit/reproduction"
python3.12 docs/build/ops/trial-audit-20261020/witnesses.py
```

`witnesses.py` first runs `audit_capture.py`: manifest/backup/journal/outbox/
artifact/cutoff checks, read-only SQLite evidence, deterministic rule-baseline
replay, per-stage metrics and accounting. It then replays actual failed reviewer
outputs through the current verifier, directly checks incomplete raw replies
against the current codec, and reproduces the mutable-input and stale-deadline
reporting defects. The120s reporting witness is synthetic, not measured provider
performance. Raw HTTP inputs are authoritative for recorded-response replay;
normalized inputs are compared, never repaired or treated as original wire data.

Outputs include private `per-job.json`, `baseline-results.json`,
`input-mismatches.json`, `private-witness-cases.json`, plus aggregate `summary.json`
and `witnesses.json`. They contain no independent labels. Every provider response
used by a replay comes from the export; no model transport is called. `artifacts.put`
is an in-memory sink for derived tool results, leaving source/model originals intact.

Retain all original hashes and logs. These scripts intentionally assert the four
observed defects on the audited source; a repaired build needs updated regression
acceptance, rather than interpreting a disappearing witness as an audit failure.
