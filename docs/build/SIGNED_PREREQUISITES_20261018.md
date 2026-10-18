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

Results and remaining owners will be appended after verification.
