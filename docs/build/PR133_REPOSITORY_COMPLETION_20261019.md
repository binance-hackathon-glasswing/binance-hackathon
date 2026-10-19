# PR133 remaining-work implementation — PC-S1WIRE01 / NT-RV02

The user requested tackling the remaining work and opening a PR. This change
implements the repository work possible with current inputs. It does not claim
all30 actions, policy approvals or actual external acceptance are complete.

## Implemented in this PR

- `ContextBuilder` now produces an audited `S1ExposureInput.v1` for S1. The
  producer applies existing run/profile/issuer/hash/version acceptance and the
  profile's exact versioned predicate authority before creating Class2 facts.
  It uses original event sessions from the frozen calendar, and a stable
  token/predicate/set/original-accession identity. Re-review/state-version changes
  and amendments cannot create a fresh renewal identity for the same event.
- Missing/unverified coverage and unmappable event times cannot count a healthy
  limiter-expiry session. Independently valid adverse facts remain available
  when another issuer is unavailable. The full input, source context hashes,
  calendar and input hash are retained in the existing policy-input audit;
  policy output retains target/trend/limiter decisions and rejections. Provider
  reasoning remains the actual original reasoning, not invented S1 model output.
- `RuntimePlanner` schedules one bounded close-trigger review per configured
  issuer/session from the frozen close plus the profile's existing delay. Job
  identity is stable through later plans/restart and uses the durable scheduler.
  Expired triggers do not pretend to be timely close reviews. The existing
  signed driver still performs safety/reconciliation before dispatching evidence
  work; no provider call is added to that safety thread.
- Recorded-port replay includes the original frozen event calendar. Tests check
  journal-head equality with live ports disabled, durable job identity/claim and
  terminal completion, while existing execution-window tests remain applicable.
- Native RPC qualification now uses receipt `effectiveGasPrice` without eagerly
  requiring legacy transaction `gasPrice`. The existing successful canonical
  receipt/trace/wallet/positive-inflow checks and sanitized output remain intact.

## Exact completion boundary

A07's Class2 producer, audit/expiry support and close-trigger scheduling are
implemented here, pending PR review. **A07 is not wholly complete:** verified
trade-restriction/suspension and scheduled-event producer contracts, real full
issuer/source coverage (including SKHYB), selected profile/parameters and actual
S1/T2/T3 acceptance remain open. The report names its Class2-only scope, lists
unsupported classes and explicitly keeps live-input qualification false. A raw
model label or `verified:true` supplied by a caller is not an alternate production
producer. No extra MODEL exposure call is selected or implemented.

#27 remains a real blocker: the existing lifetime proposals do not supply the
source-qualified deadlines, measured host timing, selected finite duration and
margins needed to adopt the parent-authority change. This PR does not extend
proposal admission, quote freshness or signing authority to conceal that mismatch.
PR187 submits the concrete O2 default RETAIN_DECLARED_TREND_GUARD on an
INCONCLUSIVE EXP007 result (EXP007 PC-O2-20261019). Acceptance and immutable
code/config/data pins must precede a real run; no result or live profile is
adopted. DEV20 and the operations risk choices remain explicit owner decisions; the
existing ready decision packet can be reviewed without new credentials.

## Remaining actions and suppliers

| Work | Supplier / exact next input or deliverable |
|---|---|
| A01/A02, access and current host state | Account owner names accepted operator and transfers approved access/private files; operator supplies fresh build/run/service/ledger/timing reports. No approved private inputs were supplied to this session. |
| A03/A05/C01/C02, accounts and trial evaluation | Account owner supplies funding/expiry/rights/usage reconciliation; operator exports immutable actual populations and preserved accounting; Keith supplies independent labels, M9/coverage, actual cost/latency and unsigned verdict. UNKNOWN charges and fixed cutoff stay intact. |
| A06/C03/C04, strategy/research decisions | Owner accepts the submitted O2 rule before Keith's real EXP007 run and decides DEV20; Keith supplies recorded candles, frozen weights/parameters/profile and evaluations. Selected profile/model/adoption remains separate from available code. |
| B01/B02/B03, router | Confirmed source supplier delivers complete export/ABI/compiler/helper/deployed-code bindings; Keegan independently reviews guarantees; Isaac then runs recorded-real route/fee checks. Draft139 remains the source intake. |
| B04/B05, native tracing | Account owner supplies approved private RPC config and suitable public transaction; Isaac runs the repaired qualifier, then operator qualifies the same provider on the host. No credentials enter GitHub. |
| B06-pre/B07/B06-post, funding | Operator reconciles actual no-first-agent-trade/no-in-flight state and remaining need; Isaac funds only if needed; operator captures fresh complete holdings afterward. Draft172 remains the handoff; historical balances are not current proof. |
| B08/B09, caps | Keith supplies measured profile/full holdings/top-up/fee coverage; Isaac decides exact #44 policies and hashes. No example cap is adopted. |
| B10, signing lifetime | Source review and actual timing, followed by adopted finite model/values, reviewed implementation and expiry/restart/requote/uncertain-send tests.60s remains illustrative. |
| C05, operations | Isaac reviews the delivered D-DN-01/07/11 risk choices and D-DN-04 requirements; operator measurements precede numeric memory/watchdog/delivery acceptance. |
| C06/C07/C08 | After all source/provider/policy/input gates, Keegan supplies a qualified signed release; operator assembles/provisions/isolates and opens the approved session; Isaac places the key, then the agent generates the first logged minimum-size round. This PR is not that release or session. |
| C09/C10/C11/C12 | Actual signed recovery/restore/replay/rehearsal evidence, final wallet/credentials/funding/opening state, declarations/services, all DR signoffs and activation pack. Keep draft deviations and actual failures until legitimately resolved. |

The full action list remains [PC-COORD01](PR133_REMAINING_ACTIONS_20261019.md).
A04's repository database procedure, IQ01 and IQ02 are already complete/reviewed;
they are not reimplemented here. Nothing enables signing, alters provider scope,
initializes a budget ledger, moves the trial cutoff, operates AWS or a wallet,
sends vendor messages, or declares host/rights/trading readiness.

## Verification record

Prospective criteria and exact RED/GREEN/final evidence are in
[IDEA-076 PC-S1WIRE01](../ledger/IDEA-076.md) and
[IDEA-039 NT-RV02](../ledger/IDEA-039.md). New code and tests were pushed before
execution. CI/source and test counts below are recorded only after completion;
old release acceptance is not transferred to new application bytes.

Exact-source approved mirror [39227766192](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39227766192) is all4 PASS at0191633: runtime2119 passed/6 expected skips/3340 subtests; separate real systemd5/5, both Terraform jobs and original host-bundle tests for both roles. [Machine receipt](evidence/pr133-remaining-20261019.json) records scope and log hash. Org CI39228699044 ran zero runtime steps due billing. The local full suite remains RUNNING at this checkpoint. Later non-manifested documentation changes do not alter the qualified application/config/tool/test/deploy/workflow bytes.
