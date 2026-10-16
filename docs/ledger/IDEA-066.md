# IDEA-066 — Gate A inventory and offline package qualification

- Date / owner: 2026-10-16 SGT / Isaac with Codex; runtime/deployment review: Keegan.
- Baseline: `eda2ed2`, fetched from `codex/system-testing-20261012`; PR87 and the Gate A assembly are already merged.
- Issues: [#127](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/127) tracks hosted qualification; [#128](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/128) covers the offline package check. Existing #32/#49/#92/#98/#118–120 keep their own acceptance criteria.
- Scope: inspect assembled inputs before deployment, using existing consumer validators and local files only. This grants no runtime/signing authority and cannot establish Gate A PASS. No AWS operation, real capture, upload or wallet action is part of this change.
- Sources checked: SKILL.md §0/F/K/Q (including F-119–124 and settled answers), the verbatim `official/source_page.md`, kit `logging.md` and `PROTOCOL.md`; DEPLOYMENT_BUILD DR-01/07/11/12/13/15/16/18/20, GATE_A, IDEA-058 and GAP-69–72. Gate A is a team gate; version integrity, trace mapping and source authorization come from F-60–63/F-99–103. Official rules and unresolved scoring questions are not invented here.
- Findings: configuration assembly exists; a consolidated read-only check of the transferred package, CI release bytes and retained terms is missing. Hosted evidence is still unrecorded. The quote-cost tool is already merged (#88), but real captures/output review remain #118–120; GAP-69's older tool-build wording needs narrowing.

## Prospective acceptance (before implementation execution)

- **PC01:** read only an existing prepared directory. Check exact expected file names, refuse symlinks/missing/changed files and validate every preparation hash. No package files are rewritten.
- **PC02:** require dev/shadow/deterministic/shadow-intelligence scope, approved cadence/day-roll settings, matching run/build/wallet and pinned state/profile/calendar/issuer inputs. Recompute the initial state through the existing producer/consumer checks; malformed identities, altered holdings and inconsistent pins refuse.
- **PC03:** validate runtime, uploader and operations with their actual configuration validators, substituting only an explicitly supplied local copy of the pinned RDS CA path. No database, credential or remote service is accessed. Missing CA/RPC settings cannot PASS.
- **PC04:** check an explicit CI manifest against its release tree and prepared build, preserving existing manifest/register/file validation; refuse mirror origin or an already host-bound manifest. Missing CI inputs stay NOT_RUN. This is byte consistency, not proof of a remote CI run; #49/#98 remain separately open.
- **PC05:** parse only the generated public evidence environment format, and use existing source/terms preflight with an explicit external artifact root. Missing contact/hash/artifact bytes block local readiness; no terms are fetched or fabricated. First BNB is a Gate B dependency and does not block this unsigned check.
- **PC06:** machine-readable output uses fixed reason codes, no raw exceptions/endpoints/contact/account/wallet/credential values. Always `signing_enabled: false`, `gate_a_passed: false`, and every host check NOT_RUN. Exit 0 means only local checks pass; 4 means blocked/refused.
- **PC07:** regressions cover valid assembly, each refusal boundary, unavailable prerequisites, mutation detection and no remote/write side effects. Commit and push covered code before execution; record exact SHA, environment, results and limits. Run the feasible related suite; do not describe macOS/local synthetic checks as Linux/host acceptance.

## Outstanding work and handoff

#127 retains the hosted checks with Yao Zhu/Keegan/Isaac/Keith as listed in the issue. GAP-69–72 stay open. Deployment spend follows AWS_RUNBOOK's named approval, and org Actions billing (#98) plus exact downloadable bundle (#49) remain with the account owner/Keegan. The implementation PR closes #128 only. No merge to main, activation, organiser message or infrastructure change is authorized by this record.

## PC-V01 — first local run, 2026-10-16 SGT

At pushed `1ea851c`, Python 3.13/macOS unittest: 10 passed, 1 failed. The terms-artifact test selected the first filesystem artifact, which may belong to a disabled source; preflight correctly does not require disabled-source terms. Correct the fixture to target EDGAR's required terms hash, preserving the production validator. An earlier invocation yielded before completion and its final output was unavailable; the recorded complete run is the one above. No host, provider or economic evidence was produced.
