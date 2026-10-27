# S5-NEXT01 — next small-wallet rehearsal candidate

User-selected SGT window: start when qualified (earliest Oct27 16:00), buy cutoff Oct27 22:00,
flatten Oct27 23:00, signing end Oct28 00:00. Existing S5-SMALL01 development wallet and limits apply.

- Profile file SHA256: `1dbb52b12b6b8e379a1b3996d427b2ab83b520f98ec6275d29f536600f327e4c`
- StrategyProfile.v1 hash: `b4719c230f41a28883d268fac77fe44bdcad23fb36355dbaec4af23a3536e7af`
- Minimum trade: 3.192045 USDT; S5 entry-cost cap: 200bp; slippage: 20bp.
- Generate from `tools.deploy.build_rehearsal_candidate.build(2, s1_raw=<fs1-final-20261025/fs1-block.json bytes>,
  s1_decision='IDEA-104 S5-NEXT01 (Keegan, 2026-10-27)', fs1_rehearsal=True, allowance_recovery=True, s5=True)`.
  Override only the four UTC window fields to 08:00 / 14:00 / 15:00 / 16:00 on Oct27 and their provenance,
  naming IDEA-104 S5-NEXT01 and the selected SGT times; validate with `validate_live`, serialize using
  `Document.from_dict(profile).payload + b'\n'`. Historical run8 and FINAL profile files are preserved.

This is a candidate, not an installed run. New run ID, database, exact release, fresh numeric/caps packet,
signer configuration and host acceptance have not been assembled. The run8 install scripts bind run7/run8
identities and must not be rerun unchanged for this candidate.

Primary preflight found the run8 USDT allowance still open and all executions terminal. Nine reservation rows
need reconciliation (a count alone does not establish active units). Clear the old allowance only through a
registered, independently authorized agent intent; never edit journal state or sign a manual transaction.
Preserve the existing provider usage ledger and run8 audit history.

The retry correction permits another fresh quote after a temporary provider failure inside the original probe
and authority bounds. It does not establish that the provider's RFQ will be usable on the next live request.
See IDEA-104 S5-NEXT01 for criteria, owner acceptance and retained SSM evidence.

Validation of the NEXT01-R1 implementation: Python 3.12.14, PostgreSQL 14.24-bookworm
(image digest `sha256:eba39627b02201a04e851363546d34547cc82550a8d7f68c6e9ff6c8b2c6ff33`),
`tests/execution tests/signer tests/strategy/test_s5_monday_flatten.py`: **503 passed,
1279 subtests passed, zero skips**. New regression tests failed before the retry change and passed afterward.
This is targeted validation, not full release/systemd/host acceptance. Both EC2 hosts report x86_64.

Signer read-only check: EC2 running, SSM ConnectionLost (last ping Oct27 04:59:46 UTC).
IAM GetInstanceProfile returns AccessDenied for the current session. T1 requires an authorized operator's
reviewed Terraform plan/apply to restore temporary signer provisioning; the new run has not started.
