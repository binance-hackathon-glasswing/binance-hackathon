LARP completed quote-cost capture - IDEA-063 / #118

This package contains the original daily measurement JSONL files, the raw
API response artifacts retained by the capture, and operational logs/notes.
Only allowlisted capture files were copied. Repository files, .env files,
wallet keys and credential files are excluded. Public wallet addresses may
appear in quote requests and operational notes.

The original capture has stopped. Last record:
2026-10-19 23:57:06.600 UTC (2026-10-20 07:57:06.600 SGT).
There are 1,924 bStock samples and 385 BNB price quotes across four UTC
dates (Oct 16-19), including the weekend. Each token has 42-43 US_SESSION
samples and 342 OFF_SESSION samples, meeting the default coverage minima.

Two failures were recorded: an authentication error on Oct 18 at
02:41:22.837 UTC, and one MSFTB sell-quote API error on Oct 19 at
14:24:49.757 UTC. The largest gap between successful BNB quote records is
Oct 18 02:31:22.826-06:56:06.986 UTC (about 4 h 25 min); capture resumed.

SHA256SUMS verifies every payload file in this package. On your Mac:
  cd <this extracted folder>
  shasum -a 256 -c SHA256SUMS

EXPORT-METADATA.json records counts, failures, timestamps and source commit.
This is a raw-data export. No final summary or strategy profiles were
generated during this export. Run the final summary with the original
default coverage requirements, then obtain the owners' review before
pinning or deploying summary/profile outputs. Costs are quotes, not fills.
