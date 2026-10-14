# IDEA-049 phase-2 prior-issue inventory (2026-10-14)

Read only after freezing the independent catalogue. These findings are review
inputs to validate, not requirement or decision sources. Snapshot: GitHub tracker
[#22](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/22),
baseline `b4dc6bb194edcb455a3bdd3f049e1620dde23475`; all eighteen children were
OPEN when inspected. Refresh the tracker, linked issues and relevant evidence at
phase 2 and again at integration; do not treat this snapshot as a closure report.

"Primary" assigns review/remediation coordination within IDEA-049, not GitHub
assignees or authority to edit another section's exclusive paths. Cross-section
fixes follow protocol §3. Each consumer supplies its boundary acceptance; D alone
reconciles the full tracker at integration. P1 maps to at least protocol P1 (P0
where §3 applies); each P2 requires reclassification and a fix or written team
acceptance. See protocol §2.1 and §4.

| Finding / issue | Tracker priority | Primary | Cross-section acceptance |
|---|---|---|---|
| R01 [#23](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/23): signed bytes in backups | P1 | D | C: signing/execution record secrecy |
| R02 [#24](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/24): market data beyond round cutoff | P1 | C | D: round cutoff and context |
| R03 [#25](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/25): real issuer IDs/tickers rejected | P1 | A | C: market identifier producer; D: context |
| R04 [#26](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/26): stranded unconsumed command | P1 | D | C: command consumer/version/fencing |
| R05 [#27](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/27): proposal/encoded swap deadline | P1 | C | B: intent expiry; D: execution mapping |
| R06 [#28](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/28): pending broadcast absent from outbox | P1 | D | C: broadcast facts before final receipt |
| R07 [#29](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/29): unrecoverable audit outage | P1 | D | B: spending gate and mandatory risk precedence |
| R08 [#30](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/30): gas replenishment path | P1 | C | B: gas intent/accounting; D: mapping/settlement/audit |
| R09 [#31](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/31): UTC daily-anchor transition | P1 | B | D: trusted journaled boundary/restart hook |
| R10 [#32](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/32): deployment routes vs adapters | P1 | D | A/C: actual SEC/model/venue/chain endpoint needs |
| R11 [#33](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/33): blocked deployable application | P1 | D | C: integrated driver/execution capability |
| R12 [#34](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/34): HALT suppresses mandatory planning | P1 | B | D: operational HALT/coordinator gates |
| R13 [#35](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/35): process-hang supervision | P2 | D | A/C: blocked calls and safe cancellation |
| R14 [#36](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/36): chain-balance reconciliation | P1 | B | C: trusted chain facts; D: durable reconciliation |
| R15 [#37](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/37): economic edge unproved | P2 | B | Team: policy/validation decision |
| R16 [#38](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/38): portfolio/cost conventions | P2 | B | C: quote/fill/gas observations |
| R17 [#39](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/39): SKHYB red-flag coverage | P2 | A | B: policy action/coverage decision |
| R18 [#40](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/40): fixed adapter slippage | P1 | C | B: frozen-profile/minimum-output constraint |

## Publication gap and numbering collision

Tracker #22 calls the trading review "IDEA-046 / GAP-68". That conflicts with
the committed hosting record `docs/ledger/IDEA-046.md` (B1–B4), which remains a
phase-1 decision source. The trading review's original record and GAP-68 text
are absent from the PR #21 tree. Do not overwrite hosting, invent the missing
record or claim the original diagnostics were run here.

Keith owns publication of the original review under an unused ID coordinated
through the ledger index, with its exact baseline/proofs/results and limitations.
D owns reconciliation of the index/backlog and old issue cross-references at
integration. Target: before phase-2 pre-registration (README Day 3); missing
original evidence remains an explicit input gap and prevents full completion.
The published issues themselves now supply R09–R18 and their P2 descriptions, so
sections can inspect those after their catalogues are frozen.
