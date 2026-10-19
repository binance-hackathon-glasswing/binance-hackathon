IDEA-063 - Interim quote-cost summary (2026-10-17)

INTERIM ONLY. This is a summary of quoted costs, not realised fills.
Not approved for pinning, deployment or trading. No profiles were built.

Source: integration commit eda2ed2ab1ab4b72f220eb6b92e882737d950825.
The existing merged summarizer ran offline on a snapshot of complete JSONL
records. The live capture was left running unchanged as PID 91310.
The snapshot and original captures remain on Keith's Linux server.
No keys, wallet address, .env, raw responses or capture records are included
in this download package.

Coverage: 2026-10-16 and 2026-10-17 UTC, including Saturday.
430 bStock samples: 86 per token (9 US_SESSION, 77 OFF_SESSION).
86 BNB price quotes. Zero FAILURE records.
All 860 buy/sell swap-gas estimates used the expected fallback.

Approved interim parameters: --min-days 2 --min-samples 9.
Weekend coverage remains required. The first attempt at min-samples 10
refused because every token had only 9 US_SESSION samples.
The full Tuesday summary still needs the original default 3 UTC days and
10 samples in each regime for every token. Do not weaken those defaults.

Files:
- quote-cost-summary.json: QuoteCostSummary.v1 cost measurements.
- quote-cost-summary.report.json: coverage, per-regime details, assumptions.
- run-metadata.json: source/snapshot attribution, parameters and hashes.
- SHA256SUMS: file checksums for transfer verification.

Review points: fee_bps=0 assumes quoted amounts already net fees; Isaac
must confirm this. Gas values use fallback estimates. Interim coverage is
smaller than the full capture. Summary and eventual profiles need the
owners' review before pinning (#118/#119/#120, GAP-69).
