# Signed rehearsal prerequisites — SP-01

Isaac workstream, 2026-10-18 SGT. User scope: progress source/route, fees,
native tracing, PR165, gas/caps, network and supplied policy proposals; update
PR133. No AWS changes or wallet-key placement. Unsigned model trial remains a
separate release. Records: IDEA-070 SP-01, IDEA-039 SP-NATIVE,
IDEA-063 SP-FEE, IDEA-062 SP-NET, IDEA-049-C SP-CAPS and IDEA-076 EB-RV2.

## Prospective verification contract

1. Retain bounded public read-only source requests for exact chain56 router
   `0xb44446b0c8e56988c34f7ff73ae904982b5fdda5` and candidate facet
   `0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603`: BscScan Code and Sourcify v2.
   At most eight HTTP GETs, 20s each, no retries, redirects, account keys or
   verification/publish actions. Retain UTC, status/error and response hashes;
   challenge/error bytes never become source/ABI evidence. Only complete
   attributable source/ABI bound to deployed router/facets/helpers can establish
   the four guarantees. Obtain Keegan's actual independent review before running
   `router check` on Keith's retained artifacts. Otherwise record NOT_RUN and
   the exact blocker; never fabricate an ABI to make the command run.
2. Verify all interim handoff manifest file hashes; inventory both directions,
   route identities, gas and raw fee fields. Fee inclusion passes only with
   applicable attributable source/vendor semantics or an exact quote/agent-swap
   receipt comparison covering wallet transfers, decimals, gas and timestamps.
   Public API prose or null custom-fee fields alone cannot close #119.
3. Native provider check: at most twelve read-only RPC calls total across the
   existing BNB Chain and NodeReal public providers, 20s each, no retries or
   credentials. Use chain56, a finalized block, one recent transaction and the
   known historical funding transaction; standalone `prestateTracer` with
   `diffMode`, code/storage disabled. Recheck the numeric block after tracing.
   A recent trace can demonstrate endpoint capability; it cannot qualify our
   native top-up without its own canonical transaction-bound evidence, actual
   execution-provider selection and host acceptance. Leave native_trace off
   while any required qualification is absent.
4. Set a conservative draft execution ceiling with exact integer arithmetic
   within the proposed 200000000000000-wei per-transaction cap. Distinguish API
   gas fields and fallback estimates from measured gas. Do not finalize #44
   without the selected final measured profile, fresh reconciled full holdings,
   actual input/metadata coverage and approval hashes for that environment.
5. Review signed/live model destinations against merged SLM-01 and provider
   rights/declaration gates; application scope approval is distinct from model
   adoption, provider-policy compatibility and hosted route evidence. No AWS
   permission changes follow from this review.
6. Decide supplied KMP-SIGN01 recommendations in Isaac's scope; preserve
   Keegan's #27 implementation/finite-lifetime decision and Yao's host ownership.
   PR165 review/combined offline validation follows EB-RV2 before completion.

### SP-01 T1 — transport correction (prospective)

The first Python transport failed before receiving any HTTP body on all six
GETs and both chain-ID RPCs. No endpoint support/verification verdict follows
from URLError. Use the system curl trust store once for the distinct candidate
Code/Sourcify GETs (eight GETs total) and up to ten remaining RPC calls; retain
stderr/exit code as well as response bodies. This is an explicit transport
correction within the original request caps, not a transient retry loop. Keep
TLS verification, no redirects, a20s timeout and the same read-only methods.

Results and remaining owners are recorded below.

## Evidence results — SP-01 R1

Public report: [report.json](evidence/signed-prereqs-20261018/report.json), SHA256
`21908394dca4cb9e356ff7a11e18e064c61b197103beb7fea4b8eb54e33c28ed`.
Original requests, response bodies and headers are retained outside Git at
`/private/tmp/larp-sp01-public-20261018`; the committed report retains exact public
request identities, UTC timestamps, response hashes and RPC errors. Empty-body
hashes from Python transport failures are not source or endpoint evidence.

**Router / #139:** at07:44:34 UTC the distinct candidate facet's BscScan Code
page returned403 with a Cloudflare challenge; Sourcify v2 returned404 with
`match`, `creationMatch` and `runtimeMatch` all null. This does not establish
whether the facet is verified on BscScan. The prior Isaac browser report that
the router itself is unverified remains attributed evidence from RE-01.
No complete source, ABI, compiler/dispatch/helper binding or independently
reviewed four-guarantee evidence was obtained. Exact-address web searches and
the checked LiquidMesh API overview yielded no attributable chain56 source.
No cross-chain address match or decoded event is substituted for it.

**Next action / Isaac:** obtain the candidate's complete verified source/ABI and
router dispatch/helper code via an ordinary permitted browser export or the
existing vendor-request draft in PR139's ROUTER_SOURCE_REVIEW.md. No external
message was sent. **Keegan:** independently review that evidence. **Router check:
NOT_RUN**, explicitly dependent on those two steps. All29 handoff file hashes
and lengths verify;15 retained successful quote/requote routes cover BUY/SELL
for all five stocks and use router0xb444…fdda5/selector0xad43f73d. The handoff
contains no native-BNB top-up quote. Do not run the checker with a guessed ABI,
a challenge-page hash, invented reviewer or synthetic RouterEvidence.

**Fees / #119:** all15 current retained routes have nonzero `tradeFee` and null
`feeAmount`, `feeToken`, `actualSwapAmount`; request inputs agree with returned
input amounts. The [Binance Flash API field documentation](https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/trading-api)
identifies `tradeFee` as estimated network fees in USD. The checked [LiquidMesh
Quote](https://docs.liquidmesh.io/docs/quote-api) and [Flash](https://docs.liquidmesh.io/docs/flash-api)
overviews do not establish wallet-net fee semantics for these exact bStock
routes. No applicable source guarantee or transaction-bound quote/agent receipt
exists here. **UNVERIFIED; #119/#120 stay open.** Isaac and Keith must retain the
first planned agent swap's exact quote plus actual wallet debits/credits,
receipt gas, decimals and UTCs after Gate B opens. The different manual MetaMask
funding route is not that evidence. No new trade, fee rate or `_costs` change.

**Native tracing / #30:** both official-list public providers returned chain56
and finalized blocks; their numeric block hashes rechecked unchanged. At07:44:36–39
UTC both returned `-32000 missing trie node` for the historical funding hash.
Crucially, both also returned **`-32002 the resource debug_traceTransaction is
not available.` for a recent transaction in their own freshly finalized block**:
BNB0x7a6137d / tx0xb54100f8…e5d6525; NodeReal0x7a61381 /
tx0x8aea9aca…0eb072. Thus an archive-only remedy is insufficiently specified:
the chosen execution endpoint must expose this exact tracer for recent receipts,
with usable historical retention for recovery. Capability remains UNQUALIFIED;
no native trace setting was enabled. Twelve RPC calls total include the first
two transport failures. No balance change is substituted for a transaction diff.
Isaac supplies/qualifies a permitted trace-capable endpoint (not a paid account
created implicitly); Yao later verifies the selected host/runtime path. The
implemented planner→settlement→audit tests and historical funding record remain
valid separate engineering/funding evidence.

## Draft gas ceiling — SP-CAPS / #44

Set the repository's execution example to `max_gas:1200000` and
`max_gas_price:160000000` wei (0.16gwei). Worst signed fee per transaction is
192000000000000wei =0.000192BNB, below the candidate0.0002BNB ceiling by
8000000000000wei. These are maximum refusal limits, not a selected gas price.
The250000 API gas field alone is insufficient: the interim capture's1,700 swap
gas estimates are all FALLBACK, using the existing1,116,000-gas historical-kit
floor. The proposed1,200,000 ceiling covers that fallback; it is not measured
route adequacy. Current15 returned prices span52530943–62282249wei; the largest
fallback swap fee across850 samples is117060138252000wei, below both ceilings.
A future gas estimate/price above these limits must be refused, never truncated
or offset by weakening the signer's cap.

The example remains incomplete and uninstalled. Its aggregate action gas budget
is still unset and must cover approve plus swap/recovery separately from the
per-transaction fee ceiling. Final profile and fresh reconciled full holdings
are absent, current quotes use40USDT above the35USDT development input cap,
no current native-top-up quote is retained, and default cost coverage is refused
(nine US-session samples per token, ten required). Consequently the full
`caps_review` cannot truthfully run on current/final inputs. Isaac/Keith retain
measured profile/holding/token-scale/top-up/fee checks and explicit environment
policy hashes. Yao retains assembly/installation after approval. **#44 stays
open; ready_to_install=false.** The final wallet needs its own review.

## Supplied policy decisions — SP-D1..D5

The user explicitly delegates deciding the proposals when Keith supplies them.
KMP-SIGN01 is now present in PR133 and merged PR168; these are Isaac-workstream
decisions, not attributed personal approvals by other owners.

- **SP-D1, first trade:** use the existing Oct21 00:00–Oct22 00:00UTC window
  (Oct21 08:00–Oct22 08:00SGT), after all actual signing gates. Do not add an
  earlier window. If gates miss it, record the shortfall and obtain a reviewed
  development-window/version change; never force a trade or count signed time
  as unsigned-trial hours.
- **SP-D2, rehearsal profile:** adopt Keith's conditional selection rule: build
  a measured EQUAL_WEIGHT rehearsal profile on Oct20 if S1's actual inputs,
  frozen weights/parameters, EXP007 disposition and B4 remain unqualified. Use
  the exact TREND_GUARDED_VOL profile only after those prerequisites and its
  explicit adoption. This decides the rule, not an unseen profile/hash or final
  strategy; four-name80% fallback evidence does not qualify five-name95% S1.
- **SP-D3, limiter mode:** choose DETERMINISTIC for an adopted S1 rehearsal/final limiter:
  code maps verified LLM evidence into reduce-only exposure levels. The routed
  LLM assessor still operates. Keegan's B4 producer, audit/expiry and actual
  profile adoption remain required; MODEL is not selected. Keegan retains
  release/services/DEV-19 reconciliation and the team parameter freeze. Original
  IDEA075 O6 is the **assessor adoption** choice, not this limiter-mode setting;
  its model/deterministic adoption gate remains open pending trial/rights review.
- **SP-D4, POLICY-HOLD:** retain the existing bounded **per-symbol price-jump
  hold**, including Class1/TERMINAL_FLATTEN requirements, until comparable chain
  reconciliation clears it or its original configured expiry is reached. Keep
  the mandatory requirement outstanding; preserve chain-safe size, quote
  freshness, min-output and signing deadline checks. Keith's phrase
  "mandatory-sale HALT" describes this imprecisely: the reviewed planner marks
  BLOCKED_PRICE_JUMP, and no new global/permanent HALT is adopted. This accepts
  the risk of delaying an urgent exit during the bounded reconciliation window,
  including near the flatten deadline; it does not guarantee timely liquidation.
  Any bypass needs its own reviewed policy/code and signed acceptance. Yao/Keith
  retain host/rehearsal verification of clearing/expiry and safe actual holdings.
- **SP-D5, #27:** support the conditional OptionA recommendation (separate fresh
  admission and finite immutable signing authority). Do not adopt illustrative
  60s, extend ≤15s proposal admission or refresh authority on re-quote/restart.
  Keegan still decides/implements finite L, margins and per-action windows using
  actual encoded-deadline and Yao's latency evidence. #27 remains blocking.

## Signed/live network review — SP-NET

Review complete; propose the **application destination scope** of primary/larp-runtime→
`api.aiand.com:443` (pinned Chat Completions path) and `api.openai.com:443`
(pinned Responses path) for explicitly prepared signed rehearsal and live builds.
SLM-01/PR164 already implements that capability with explicit adoption reference,
reviewed LIVE profile, hashed routing/prompts, nonblocking single-slot assessment,
main-thread verification/safety planning and durable audit. The old table's claim
that all service/live routing is refused is stale. No additional hosts, signer
internet access, model-selected endpoint or AWS route/security change is proposed.

**Scope approval is now recorded in SP-NET D2 (2026-10-18).** The user asked
to carry out each listed immediate point in its own PR, including this exact
reviewed proposal. The following describes the earlier review-only blocker;
it is superseded by D2. Automatic approval review originally rejected publishing the
approval because the user requested review, not authorization to broaden sensitive
egress. The approved table remains shadow-only and no route/runtime change is
part of this safer alternative. The review-ready exact proposal is below. Explicit
user approval is required before updating that policy table; no deployment follows
from that approval. It would allow the primary runtime to send scoped public
filing evidence/model requests during signed/live operation to these providers.
It is not authority to dispatch under an unqualified provider contract or activate
trading. Keegan must resolve KMP-RIGHTS01's signed-use policy
compatibility, account/model terms, services declaration/DEV-19 and team adoption.
Keith retains trial/quality/funding evidence; Yao retains P0, secret/budget/route
and exact-release hosted qualification. The legacy40USD limit/10USD reserve
applies to v1/v2; Yao approved the KMP-BUD01 v3 protocol in PC-REL05; implementation/release
conformance, measured affordability and actual hosted qualification remain. The proposed network scope would not select a routing/budget version. Signer
isolation remains RDS/S3 only, and primary HTTPS is not an FQDN firewall.

## Remaining ownership

| Open dependency | Owner / record |
|---|---|
| Verified router/facet/helper export; then independent source review and real route replay | Isaac; Keegan review — #139/#33, IDEA070 SP-01 |
| Net fee evidence and final measured profile/full-holding caps hashes | Isaac + Keith — #119/#120/#44, IDEA063 SP-FEE / IDEA049-C SP-CAPS |
| Actual trace-capable execution endpoint and transaction-local native evidence | Isaac; Yao hosted check — #30, IDEA039 SP-NATIVE |
| Finite signing lifetime/margins implementation and host latency | Keegan; Yao measurements — #27, C-OPEN-003 |
| PR165 exact-release Linux/mirror and hosted qualification | Keegan/Keith/Yao — IDEA076 EB-RV2; code review/full local verification complete, merged817eb71 |
| Provider policy compatibility/adoption and release declaration | Keegan; Keith quality/funding, Yao hosted inputs — KMP-RIGHTS01 / IDEA057 |
| Signer access, host assembly and approved session | Yao; Isaac key placement only in that session — IDEA080 |

No AWS, key placement, wallet signing/broadcast, paid inference or official log
upload occurred. The separate unsigned trial remains pending its own host gates.

### Exact network-scope proposal — approved in SP-NET D2

Replace only the approved application scope for the existing two destinations:

| From / unit | Destination | Proposed scope and constraints |
|---|---|---|
| primary / larp-runtime with aiand_routed | api.aiand.com:443 | Shadow plus explicitly adopted signed/live builds; fixed /v1/chat/completions, pinned model/effort/routing/prompts, only lawful registered evidence; provider-policy/account/model terms, funded account, declarations, trial/adoption and exact-release/host gates first |
| primary / larp-runtime with aiand_routed | api.openai.com:443 | Same signed/live gates; fixed /v1/responses, optional runtime key and exact adopted durable budget; v1/v2 reserve remains unchanged, v3 protocol approved PC-REL05; implementation/release/host conformance separate |

No execution/signer unit receives model-network scope. No AWS, firewall, secret,
provider setting, runtime configuration or service change is included. The existing
application table would cite this decision and explain SLM-01's merged capability
without claiming that service/live is mechanically unavailable. SP-NET D2 updates the table; all provider-policy/adoption/host gates above
remain mandatory before use.

## PR165 completion and SP-01 verification

PR165 merged normally into integration at817eb71 (2026-10-18 07:54UTC), after
full source/review-record inspection and combined-head verification at8f2d364:
2021 passed /9 explicit platform-or-external skips /2981 subtests,415.04s.
Focused B6:80 passed /57 subtests,9.52s. No remaining reproducible B6 finding
was identified or personal peer approval attributed. GitHub39109312981 at
d635ce9 ran no steps; runtime/infrastructure annotations confirm billing/#98.
Linux/mirror release qualification remains open. See IDEA076 EB-RV2.

SP-01 validation at pushed7e96ca7: existing route, caps-proposal/current-input,
native-accounting and GateB evidence regressions **61 passed /135 subtests**,
1.51s, no skips. The actual SigningPolicy parser/check accepts the draft gas
envelope and refuses an over-cap price in **8 synthetic approve/swap cases**
across development/final candidates, without keys or signatures. All29 quote
handoff hashes/lengths verify. These local checks do not substitute for the
full current-input caps review, actual gas measurement or source/native gates.

### Final integration verification and handoff

At pushed694d8e8, the short final merged-tree gas/native/route suite again passes:
**61 tests /135 subtests, no skips**,1.38s. No changed runtime behavior needed a
second full run after EB-RV2: the only additional operational input is the
uninstalled example gas ceiling, covered by the current-input/policy checks.
JSON/report digest/all29 handoff hashes, exact gas arithmetic, diff/conflict and
private-key/env-path checks pass. The rejected network expansion was removed;
approved network scope and route/runtime code are unchanged by SP-01.

PR165 is MERGED817eb71; PR139 remains DRAFT atb9fbaaa; PR133 remains OPEN.
All session changes are committed/pushed, no session unpushed commits remain;
working trees were clean and local main matched origin/main (0/0) at the final
check. The original IDE checkout stays on its pre-existing signed-LLM branch
(behind its remote by3, no local edits); this work uses isolated checkouts.
Open owners/records are listed above, including explicit user approval for the
network proposal. No AWS changes or wallet-key placement occurred. The local
throwaway PostgreSQL is disposed after testing. Ready for a new session with
these explicit source/provider/data/approval/release gates still open.

## SP-NET D2 current disposition

The earlier pending-user-approval status is superseded by explicit authorization
to carry out the immediate network point in its own PR. Architecture table and
route-report wording are updated; runtime endpoints/allowlists/configs and AWS
permissions are unchanged. See IDEA-062 SP-NET D2 for criteria/results. All
provider-policy, rights/account/model, funded budget, trial/adoption, declaration
and release/host gates remain; this does not activate signed model traffic.
