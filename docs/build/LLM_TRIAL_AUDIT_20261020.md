# PC-AUDIT01 — captured trial and current-code audit (2026-10-20)

Requested by Yao: analyze the preserved unsigned trial, assess system performance,
and identify inconsistencies/unwanted behavior that remain after newer merged
LLM changes. Current comparison baseline is canonical commit
`697ff3a` (`origin/codex/system-testing-20261012` at audit start); captured
runtime is `ea25b52325656a19b29e8ddb07b94dd792be6e18`.

Prospective audit criteria (before replay / scoring):

- A1: verify the private final export's file manifest and Backup.v1 digest; independently
  recompute all journal batch/event/head hashes and terminal projection; reconcile
  rounds, audit payloads/chunks/ACKs and zero execution/signing rows.
- A2: join all captured assessments, stage results, original request/reply/tool
  artifacts and evidence sources. Check point-in-time cutoffs, provenance,
  model/effort identity, tool/stage limits and accepted unsupported content.
- A3: measure availability/latency/status/coverage/duplication by issuer and
  route with honest denominators. Replay the same immutable requests through
  the deterministic baseline offline where reconstructable; missing evidence
  remains missing. Apply existing frozen protocol definitions, never tune them.
- A4: reconcile OpenAI ledger entries, recorded usage and unmetered/late calls;
  distinguish known costs, conservative reservations and unavailable invoices.
- A5: inspect each candidate defect against the latest merged code and existing
  regression evidence. Exclude already-fixed behavior from remaining findings.
  Reproduce remaining candidates offline with real captured inputs where possible.
- A6: retain source/model/label data and per-case audit details privately; publish
  aggregate measurements, exact source/data hashes, concrete remaining findings
  and confidence/limits. No paid inference, AWS mutation, trading or deployment.

This is a retrospective engineering audit, not a new blind-label experiment.
No independent accuracy/profit or absence-of-all-defects claim is possible from
an unsigned two-issuer capture. Existing trial sampling/labels/adoption gates stand.

## Result

**Engineering integrity is strong; current model usefulness is not established,
and four remaining repairs were confirmed.** This report compares every finding
with canonical `697ff3a9e4f310aae7980dc61f0fedc376d148a7` (remote rechecked before
publication). It does not list resolved legacy timing/review behavior as current
work. No new hosted inference, AWS operation or trading occurred.

The source is the private PC-STOP01 final archive, SHA-256
`587aeb67bafde94061889eeff55bf57a91811e64864e998e20d20f87dbe398d0`.
The captured build is older than canonical; observed historical percentages are
not a measured performance estimate for the updated router.

## Performance and scope

| Measurement | Verified result | Meaning |
|---|---|---|
| Observation | 70 assessment requests, 43.56-hour clean session | Original unsigned capture only |
| Actual evidence diversity | Two repeatedly assessed filing records, two issuers; four records stored in total | 70 jobs are not 70 independent filings |
| OpenAI primary | 68/70 ASSESSED; 103/103 returned messages schema-valid; recorded proposed claims 58/58 verifier-passing | Its supported claims in this capture are filing item tags, not numerical forecasts |
| Accepted combined content | Six nonempty ASSESSED outputs; 35 empty ASSESSED outputs; other 29 outputs unavailable | No investment-performance interpretation; these are captured-build outcomes |
| Emitted claims | All 24 reverify against saved sources with current verifier; all are repeated `ITEM:2.02`/`ITEM:9.01` tags | No accepted unsupported claim found in this narrow population; no Class 1/2 positive-event recall test |
| Offline rule baseline | Same 70 original requests, source bytes, historical config and cutoffs; 70 ASSESSED | Among the captured run's 41 ASSESSED results, all finding/claim-metric sets match baseline; no additional economic fact demonstrated |
| SK hynix | 35 ASSESSED results, all with zero claims and UNKNOWN thesis | Successful processing of a sparse cover filing, not demonstrated analytical insight |
| Portfolio | All 350 stock targets were KEEP_QUANTITY / MISSING_MARKET_OR_BASIS; zero intents/orders/commands | This trial does not measure entry/exit performance, execution quality or trading alpha |

The profile was the historical EQUAL_WEIGHT rehearsal profile, with entry opening
Oct21, and all 350 captured market rows had unverified basis. It was not the
later selected S1 deployment. Three issuers had successful polling but no stored
filings in this evidence store. Evidence/issuer coverage, independent labels and
the current full strategy/rehearsal gates retain their existing owners; an empty
claim set or a hold is not a correct-negative label. Baseline agreement cannot
substitute for independent accuracy or omission measurement.

## Remaining findings

### R1 / P1 — earlier normalized model inputs acquire later tool results

**Observed:** 81 of 174 completed-step normalized input records differ from the
exact saved HTTP inputs: OpenAI35, Kimi34, GLM12. Every difference is
`input.tool_results`. An earlier step is recorded with a fetched exhibit that
was only obtained after that model call selected the fetch tool.

**Still present:** `larp/intelligence/agent.py` `_State._view` returns the mutable
`self.tool_results` list (line143). The request dictionary retained in `io.steps`
is not frozen, although the separate `Document` sent to the model is frozen
(lines306–320). Later appends therefore change the earlier normalized trace.
An offline current-code witness on the first real request, using the deterministic
model and dispatch-time input snapshots, reproduces this on its first of two
steps. The original raw HTTP artifacts are hash-correct and recover the real
inputs. This is a semantic audit/replay defect, not a corrupted hash chain or
proof that future tool output reached the actual provider.

**Repair:** Isaac/LLM implementation owner freezes the full input at dispatch
before both in-flight and completed-step retention. Test two tool rounds,
truncation, errors and deferred/parallel round traces against dispatch snapshots
and exact wire payloads. Preserve historical records; use the private mismatch
manifest and original payload hashes for retrospective reconstruction. Never
rewrite the uploaded trace to hide the difference. **Fix before another run.**

### R2 / P2 — high-effort reviewers exhaust the unchanged output cap

**Observed:** all eleven recorded external response errors are a single choice
with `finish_reason=length` and exactly4,096 completion tokens: seven Kimi and
four GLM. In nine cases reasoning alone consumed the entire4,096 tokens. The
current codec rejects all11 original raw replies identically. The captured
routing spec is byte-identical to the current checked-in trial example and
still supplies4,096 via `max_completion_tokens`; increasing elapsed-time
allowance alone cannot recover a reply that exhausted its token allocation.

These errors safely become unavailable; they are not accepted decisions.
Their cost is obscured in the normalized usage: known raw AIand replies contain
336,797 input /71,194 completion tokens, versus273,288 /26,138 in normalized
step usage. The45,056 missing completion tokens are exactly11×4,096. The raw
responses retain the recoverable usage. The25 historical external calls without
a completed-step record are not assigned zero cost; invoices remain necessary.

**Repair:** Keith and Isaac choose per-stage token budgets, prompt/citation
compactness and bounded completion handling with measured affordability. Keep
model/effort/claim guards unless separately approved. Do not globally raise the
shared cap without reviewing the larger OpenAI maximum reservations and total
trial budget. Preserve usage/finish reason even for rejected completions.

### R3 / P2 — reviewer citations/output schema remain unreliable

**Observed:** Kimi proposed35 claims across its finished stage outputs;15 were
rejected: six span-text mismatches, seven metric-not-in-span errors and two
item/source-record mismatches. Five stages abstained for unsupported claims;
one additional stage abstained for model-output schema. The resulting recorded
claim-verification rate is20/35 (57.14%); it is a contract-verification statistic,
not independently labelled accuracy.

**Still present:** all six cases replay through the current assessor with
**identical original HTTP model inputs and pinned prompts**, using recorded
responses only. The same rejections occur despite a180s replay ceiling. The
current review-outcome function correctly produces DISSENT/ABSTAIN for all six
when paired with their recorded ASSESSED primary. This is a case reproduction,
not a prediction of the updated live router's aggregate availability.

**Repair:** Keith/Isaac improve the source-record/span contract and compact
allowlisted citation representation, with real captured inputs as private
regression data. Preserve strict verification and the adopted dissent policy;
fix malformed reviewer output rather than accepting unsupported claims.

### R4 / P2 — offline metrics still assume a60s ceiling

**Still present:** `larp/intelligence/bakeoff.py:27` fixes `DEADLINE_MS=60000`, and
line106 uses that for `within_deadline`, while current `MAX_ASSESSMENT_MS=180000`.
A reporting-only witness with a120,000ms result is counted outside its deadline.
This does not establish a120s live latency; it proves a reporting inconsistency.
Stage-specific allowances make a single hard-coded ceiling inappropriate.

The same helper counts the eleven length-limited completions as schema-invalid
messages and reports zero provider errors. Keep the frozen M5 denominator, but
add an explicit token-limit failure breakdown so truncation is distinguishable
from an ordinary malformed schema, transport failure or unsupported claim.

**Repair:** Keith/LLM tooling owner binds metrics to the actual request/stage
budget and retains the tested historical protocol as an explicit parameter.
Include raw known usage from rejected completions without inventing an invoice
or refunding conservative reservations.

## Checks that passed

- Every export file checksum and PostgreSQL payload digest;188 sequential
  journal batch/event/head hashes; terminal projection/policy/execution-state
  bytes; exact journal-to-outbox and109 audit-chunk payloads/ACKs. All70 rounds
  closed; execution, signing, reservations and command tables empty.
- All496 referenced artifact addresses resolve and match their content hashes.
  All70 request/assessment identities, reference hashes and source publication/
  availability cutoffs agree. Tool allowlist/count/start-time checks pass;
  no accepted ASSESSED result exceeds its captured deadline.
- All103 returned OpenAI model identities match. All71 recorded AIand response
  metadata pairs match the requested model and high effort. This is identity
  evidence for returned calls; it does not invent metadata for in-flight ones.
- Every one of103 settled OpenAI entries matches its recorded per-call cost:
  $0.880356. The three UNKNOWN reservations remain$0.337180 total, including
  prior/shared usage. No duplicate completed request ID or ledger discrepancy
  found. AIand invoice reconciliation remains unavailable.
- No credential-pattern candidate found in the scanned text artifacts; this is
  a bounded pattern scan, not proof that every possible secret format is absent.
- Current-code focused regression tests: **38 PASS**, Python3.12.14/macOS
  (`ReviewOutcomes`, stage prompts, provider codecs/deadlines and bakeoff).
  Two localhost transport tests initially lacked sandbox socket permission;
  the full focused rerun with loopback access passed. No Linux/PostgreSQL/
  systemd or live-provider qualification is inferred.

## Reproduction and disposition

[Read-only audit scripts](ops/trial-audit-20261020/README.md) reconstruct the
checks, wire/log mismatch manifest, deterministic baseline and current-code
witnesses from the private export. Scripts emit private per-job details and
aggregate reports; they never construct a live provider or access AWS.
[Aggregate receipt](evidence/llm-trial-audit-20261020.json) includes source/data/
script/result hashes. Raw inputs, outputs and any future labels stay outside Git.

Audit complete **with findings**, not a clean system acceptance. Repair order:
R1 first, then R2/R3, then R4 before using the next qualification report. Existing
independent-label/source/profile/rehearsal gates remain; no new paid trial or
restart is authorized or performed here. No application fix is claimed by this
audit-only delivery.
