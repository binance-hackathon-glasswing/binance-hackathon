# LD08-GC01 — bounded initial-gas candidates

**Offline calculation/candidate checks PASS; deployment/seeding acceptance open.**
Prospective criteria `91e04cc`; code/tests `fe91326`, committed and pushed before
execution. Base canonical `f10d9ad`. These files are new technical candidates;
all DC-01/LD04/LD09-B/RV120-02 historical files remain byte-identical.

## Envelope and actual execution boundary

CAP-02 approves 1,200,000 gas and 160,000,000wei/gas execution ceilings; their
product is 192,000,000,000,000wei per child, below the signer's independent
200,000,000,000,000wei fee ceiling. A cleanup-disabled parent has two signed
children: normal approval and swap. A cleanup-enabled parent can have six
additional zero approvals. Production `validate_payload`, `validate_sequence`
and signer policy enforce per-child and aggregate-parent constraints; a failed
or uncertain child does not create an unbounded same-parent retry loop.

| Bound | BNB wei | BNB |
|---|---:|---:|
| Ordinary two-child action | 384,000,000,000,000 | 0.000384 |
| Four-position EW terminal reserve | 1,536,000,000,000,000 | 0.001536 |
| Five-position S1 terminal bound | 1,920,000,000,000,000 | 0.001920 |
| Eight-child cleanup scenario per action | 1,536,000,000,000,000 | 0.001536 |

Cleanup stays **disabled** under the approved CAP-02 policy. The eight-child
number is a non-adopted upper-bound scenario; it does not approve cleanup policy,
API behavior, timing or installation. The S1 number is a five-exit bound only;
no S1 weights/profile are fabricated. All exit counts assume each full holding
fits one allowed economic action; fresh actual quantities must establish that.

Production `Executor.prepare` uses `max(quote gas, ceil(estimate * 6/5))` for the
swap. The recorded 55,243/944,814 observed estimates give 192,011,040,000,000wei
when each child receives 20% headroom and is rounded separately. The historical
25% proposal gives 200,011,520,000,000wei, which exceeds its old fractional-pair
budget by 120,000,000wei. Neither observed pair is a guarantee about future routes
or original approval gas limits. The new candidate instead covers both children
at their configured ceilings, while heavier individual payloads remain refused.

**Binding still required:** actual execution.json's `gas_budget` must fit the
accepted funded action envelope, and the planner's per-command BNB reservation
must cover that parent budget. `RunAuthorization.resources_reserved` independently
refuses insufficient reservation. Merely increasing a profile reserve cannot
make an under-reserved command executable. No execution config or quote-proof
producer/reservation is changed by this review.

## Candidate construction and seeding

The production builder produces new initial-only EQUAL_WEIGHT candidates with
action384,000,000,000,000wei and four-action reserve1,536,000,000,000,000wei.
It retains the separately sourced expected-cost sizing budget80,004,560,000,000wei,
so minimum trade remains18.637420USDT. Production validation and repeat-byte
construction pass. [Exact hashes/report](review.json).

Preserved profile choices remain subject to #120: fee zero is conditional on
unverified #119 netting, final terminal gates still need PF-04 reconciliation,
and preferred S1 needs actual frozen weights. Neither candidate is pinned to a
runtime/release or adopted for deployment.

For whole-run seeding, define **N as non-terminal economic actions**, including
planned failures/retries. Compute `ceil(N * action * margin_num / margin_den)`
plus a separately counted terminal-exit reserve. Historical N15/30 proposals
included exits and cannot silently be substituted into this definition. The
machine report gives sensitivity calculations only, with an illustrative5/4
count margin; no N, margin or wallet funding amount is adopted here. Keith must
supply accepted per-environment counts/scope; the operator supplies current
reconciled holdings/funding disposition. Initial-only has no agent gas top-up.

## Verification and remaining work

macOS arm64/Python3.12.14: focused gas/initial-only/allowance/sequence/decoder/
read-only-boundary suite at final source `ffe91d9`: **68 tests PASS /280 subtests**, three PostgreSQL-backed
tests skipped because no disposable test database was selected. All16 new tests
pass. Both new candidate files and report reproduce byte for byte. No full-suite,
CI, actual receipt-gas, installed alarm, signer-session or host result is claimed.

Reproduce into a new private directory outside the checkout:

```sh
PYTHONPATH=. python3 tools/deploy/review_initial_gas.py --out /private/tmp/new-gc01-review
```

Remaining owners: Keith/Isaac selected profile/counts/fee/economics; Isaac current
complete-holdings/config/reservation and full-exit coverage; Keegan policy/release;
approved operator funding disposition and alarm/host/exit acceptance. Priority2's
offline envelope/calculator/candidate work is delivered; LD08/LD10 deployment
acceptance remains open for those concrete inputs. Nothing is funded or installed.
