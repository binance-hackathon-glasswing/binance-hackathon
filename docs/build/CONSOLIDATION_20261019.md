# CONS-01 — canonical integration consolidation (2026-10-19)

User decision: `codex/system-testing-20261012` is the latest shared build and
the base for every new implementation PR. PR133 remains open solely as a
noticeboard. This is repository consolidation, not policy activation, signer
installation, a new qualified release or an AWS operation.

## Inventory and intended disposition

Canonical starting commit: `eb430b8815029f87a285ab42fea9fa10ed88e94d`.
Previously reviewed work accumulated on PR133 through `e169fa1`; that history
is included without merging PR133's new noticeboard-only head `31182ce`.

| PR | Frozen head | Retained work / disposition after validation |
|---|---|---|
| #139 | `757e4f89653510486c9010644a41d617894f6bdc` | Preserve original source-acquisition reports and honest blockers as documentation; retire the separate draft integration lane. Source-based router qualification remains an optional uncompleted path, not verified source. |
| #172 | `d1682ea0c2d7cbfc64231ed87713fc6f5be1d932` | Preserve historical funding preflight and current reconciliation/funding handoff; retire the separate draft lane. No additional funding or fresh holdings is inferred. |
| #191 | `90ef371c54f892bfb5c626bb1640067cc53e68b7` | Integrate source-link regression tests and recovered original summary/provenance; keep interim/fallback-gas limits and real qualification gaps explicit. |
| #192 | `75e5d7f707f8f87c17364b1dcfd2cadbba02a8a1` | Integrate delegated C05 review decisions and evidence; numeric delivery/watchdog/memory settings, code and host qualification remain open. |
| #193 | `89ba2896ba2272071ce983a8058d33da744fa6ac` | Integrate signer input inventory and owner handoff; keep the original incomplete draft and installation/signing flags false. |
| #194 | `f32d59563b53f2abc7f9983f5c3b03d262cd12d5` | Integrate opt-in untrusted-router capability and tests. No default activation or Isaac #44/B09 risk adoption. Live policy, replay/preflight, lifetime, allowance recovery, abnormal-fill accounting and native gas top-up gaps remain open. |
| #133 | preserved open | Noticeboard only; canonical implementation/backlog lives on system-testing. New implementation PRs must target that branch. |

All useful source history is kept through ordinary merge commits. Conflicting
summaries use the newest supported state; both ledger workstreams and original
evidence bytes remain. No force push, rebase, pushed-commit amendment, branch
deletion or secret/environment-file migration is part of this work.

## Prospective acceptance criteria

1. Review each PR's unique delta and keep pending decisions/qualification
   separate from delivered implementation. No experimental router policy is
   installed or adopted by merging its code.
2. Preserve every frozen retained PR head in canonical ancestry, every original
   source/funding/provenance evidence byte, and all unresolved backlog IDs from
   e169fa1 unless a fully verified closure is recorded.
3. Push combined code/criteria to the registered repository before executing it.
   Run the full pinned Python3.12/PostgreSQL14 suite on Linux; run focused
   router/signer/integration/rehearsal/source-trust checks when needed for a
   change/failure. Validate the generated register and provenance reproduction.
   Record platform/private-fixture skips and CI unavailability truthfully.
4. Review configuration defaults: no real untrusted policy, example caps still
   refuse, no signer key/config installation or capability enablement. Confirm
   no `.env`, secrets, official-kit/vendor changes, conflict markers or accidental
   backlog/index truncation. Verify new documentation links.
5. Promote the validated combined head to system-testing with normal history,
   finalize all original PR dispositions, and retain PR133 open with only
   noticeboard changes relative to canonical. Update README/AGENTS and current
   status so agents have one implementation base and one live backlog.

## Remaining runtime inputs and owners

- **Isaac + Keith:** exact measured #44 policy/profile/holdings/gas/fee approval;
  explicit B09 adoption if the untrusted-router path is selected.
- **Keegan + operator:** #27 finite authorization model/implementation/timing;
  independent policy/release review and original signed-build qualification.
- **Approved operator:** real untrusted policy observation/code/facet pins,
  fresh route replay and preflight; approved native tracing, current wallet
  reconciliation and funding/no-funding disposition, host bindings/isolation,
  session, resource measurements and actual rehearsal/recovery/ACK evidence.
- **Keith/account owners:** final strategy inputs/experiments/model trial,
  provider rights/usage/funding reconciliation and any accounting corrections.
- **Source supplier + reviewer:** complete source/ABI/deployment binding if the
  source-verified router path is pursued. The alternate mode does not claim
  source verification or prove minimum-output/recipient/deadline enforcement.

Validation and final promotion/disposition results: IDEA-066 CONS-01.


## Combined validation and promotion record

Runtime/config/test/tool source: `bd4dbeef652819a15ceb195588fc987b25b40f30`,
pushed to the registered repository before execution. Later changes only record
results/status; verify their runtime/config/test/tool trees remain identical.

- Linux/Python3.12.15/PostgreSQL14.24: **2162 passed,7 skipped,3628 subtests**,
  154.04s. Five skips are the separately exercised systemd cases; the other two
  require external source/market-response fixtures and remain unrun.
- Separate disposable real-systemd: **5 tests/5 subtests PASS**,9.57s.
- Production Docker build and network-disabled/read-only/no-capabilities smoke
  PASS; offline runtime demo emits valid JSON. No host release bundle was built
  or published by this consolidation. Terraform source is byte-identical to the
  starting integration branch and was not reapplied or re-tested here.
- Renderer and original interim provenance reproduction PASS. All six frozen
  PR heads retained, all62 open GAP IDs and79 ledger index IDs preserved,
  all15 original per-PR evidence files byte-identical, new local links valid,
  and no .env/official-kit/vendor or Terraform changes.
- Initial environment run:2157 pass/5 fail/7 skips. Three failures were caused
  by a read-only synthetic activation directory and two by the container's
  inability to mount isolated /proc. Corrected disposable runner permissions
  and a tmpfs activation directory; no application/sandbox weakening. Complete
  corrected suite and real-systemd results above supersede that environment run.
- Org CI39271681737 runtime job118125327031 atbd4dbee ran zero steps; its
  annotation explicitly reports failed account payments/spending limit. This
  is not an executed suite failure or a remote-CI PASS. Local verification is
  recorded separately; exact future release/host qualification remains open.

[Machine receipt](evidence/consolidation-20261019.json) records inputs/scope.
[PR195](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/195)
is the reviewed promotion vehicle. Its merge establishes the canonical build;
all six original lanes are then merged/closed as absorbed work. PR133 stays
OPEN with only its noticeboard file differing from canonical. Branches/worktrees
are retained as historical references; new work must use the canonical branch.
