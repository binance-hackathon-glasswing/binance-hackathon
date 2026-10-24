# PC-LABEL02 — retrospective deterministic assessment review

Yao requested independent labels on the collected deterministic run and will
arrange independent annotators. This is a retrospective diagnostic, separate
from the approved v3 trial population and from T01 held-out qualification.

## Criteria before packet selection or annotation

- Retain a read-only, cutoff-bound export for Oct17 11:00 UTC through Oct18
  11:00 UTC. Include every requested assessment and corresponding audit result,
  including unavailable/late/failed results; never select by a favourable answer.
- Use the complete set of referenced issuer/filing-record pairs in that window.
  Freeze each pair's earliest request (cutoff then job/round ID for deterministic
  ties); retain all duplicate requests separately. Every selected source revision
  must have been available at its representative request's original cutoff.
- Retain and hash exact saved UTF-8 and original source bytes. Annotators receive
  issuer/source identity, source metadata, original cutoff and pinned taxonomy/
  predicates only. Keep predictions, model identities, statuses, rationales,
  request context/known facts and the answer mapping in a separate custodian set.
- Retain hashes/byte counts of population, selection and blind manifests before
  annotation. Explicitly record unreadable/missing evidence; no case replacement.
- Independent annotators must not see baseline/routed answers. Obtain two separate
  readings; adjudicate uncertain/disputed labels before unblinding. Preserve both
  original labels and adjudication provenance; private labels stay outside Git.
- Use the approved KMP-LABEL01 one-to-one event matching semantics: exact issuer,
  filing/revision, actor, actuality, material event/period and supporting span;
  score the frozen representative at its original cutoff/deadline. Report TP/FP/FN,
  precision/recall and uncertainty; missing/late results cannot be rescued by a
  later retry. Report numeric/statement errors separately. A zero-positive sample
  gives unqualified recall, never 100%.
- Do not run the assessor again before gold labels are frozen. Existing answers
  are already present: do not claim that these labels preceded their predictions.
  This small diagnostic cannot satisfy T01's 60 held-out-document/two-independent-
  annotator/pre-prediction-label requirements, nor v3 M9 natural-route/positive/
  duration requirements. No adoption, accuracy score or PASS before real labels.

## Verified inventory

Read-only base64 SSM exported 43 fixed-window round requests and all 43 matching
nested audit inputs, plus four saved filing records and ten raw/text artifacts.
All audit requests equal the original round-table requests. Four records comprise
five saved documents, covering two issuers; all four are referenced by requests.
Transport uses bounded chunks to avoid SSM's 24,000-byte output truncation and
requires an identical full-export SHA-256 across chunks. Failed extraction and
truncated output attempts remain diagnostics and are not substituted for evidence.
No runtime/service change or inference was performed.

Packet construction, frozen hashes, independent readings and scoring results
will be recorded below. Yao owns obtaining the independent readings; the custodian
prepares/fixes the sealed packet; Keith owns rubric/report review. KMP-LABEL01,
T01 and the later signed/adoption gates stay open.

## Packet delivery and verification

Criteria 059b250 were pushed with normal merge 6820c7b before packet selection.
The complete referenced population produces four cases / five documents / two
issuers; 43 requests give four frozen representative requests and 39 duplicate
requests retained separately. All ten raw/text artifacts passed SHA-256 checks;
all 43 audit inputs equal the round-table requests. Every selected revision was
available at its representative cutoff. No rerun or paid call was made.

Private packet is retained outside the repository in Yao's Downloads directory,
LARP-independent-labels-20261018. Only LARP-blind-annotation-20261018.zip is for
annotators: 39,380 bytes, SHA-256
`253ac12e649272bb46361c4489bca357fcfded2148f7556c0a072b1132db2249`.
The 25 ZIP files include exact saved text/original bytes, source metadata,
character-offset indexes, pinned predicates/taxonomy, instructions and an empty
label template. Custodian requests, predictions, duplicate outcomes and maps
are separate and must not be forwarded with the blind ZIP. Population,
selection, blind and file manifests were hashed before annotation.

ZIP integrity, all included file hashes, source references, cutoff checks,
absence of prediction/context fields from blind metadata and unstarted label
state PASS. Sanitized manifest hashes/byte counts and QA are recorded in
[evidence/deterministic-label-packet-20261018.json](evidence/deterministic-label-packet-20261018.json).
No source text, prediction details or labels enter Git.

**Remaining:** Yao obtains two separate independent readings; an independent
reviewer resolves uncertain/disputed labels before unblinding; preserve and hash
both originals and adjudicated gold. Custodian/Keith validates source spans and
one-to-one matching, then scores the four original representatives and reports
duplicate outcomes separately. Actual labels NOT_STARTED; scoring NOT_RUN.
T01/v3 M9 remain unqualified. Empty templates are not gold negatives.

## PC-LABEL02-R1 — two AI readings returned; blind adjudication pending

Yao supplied the Claude and GPT annotation files. Both original byte streams are
retained privately unchanged, with SHA-256/byte counts recorded in the sanitized
[evidence review](evidence/deterministic-label-return-review-20261018.json).
Both parse as IndependentBlindLabels.v1, cover all four cases and declare full
saved-document reading and no baseline-answer exposure. All31 exact quotation
records (15 and16) match their source file hashes and zero-based Unicode spans;
no citation/offset repair was needed.

These are AI-generated readings, not two verified independent human annotations.
One explicitly declines implementer-independence attestation; the other limits
its independence statement to its annotation session and discloses repository
summary exposure. Preserve those provenance limitations rather than upgrading
independence silently. One reading leaves a case uncertain; semantic statement
classification/scope/granularity questions remain for a reviewer. Citation
correctness alone is not gold-label correctness.

The custodian performed mechanical validation only, and did not semantically
adjudicate gold or access baseline outputs for this returned-label review.
The frozen rubric requires independent review of uncertainty before unblinding
and excludes an output-aware custodian from acting as its blind annotator.

A private source/labels/questions/template ZIP was prepared for the baseline-
blind adjudicator: LARP-blind-adjudication-20261018.zip,59023 bytes, SHA-256
`0865de5ffec62453ccc0e074feeeb0cac39149c5e3da4eec46ebfa206101ac14`.
Original source-file hashes and every review-manifest file were reverified;
ZIP integrity PASS. No assessor outputs, private answer/case maps or population
exports are included. Private packet is beside the original in Downloads under
label-review-20261018. Source labels/dispute content remain outside Git.

**Remaining:** Yao supplies a baseline-blind independent adjudication with final
source-supported labels, question resolutions and exposure/identity provenance.
Custodian/Keith verifies it, freezes/hashes gold, then scores the already frozen
first requests with duplicate outcomes separate. Gold NOT_FROZEN; scoring NOT_RUN.
No paid calls, model reruns or host changes. Formal T01/v3 M9 stay unqualified.

## PC-LABEL02-R2 — adjudication frozen and original assessments scored

**Interpretation corrected in PC-LABEL02-R3 below:** these counts characterize the temporary rule-assessor outputs against the annotation task, not semantic intelligence or a numerical rating of the harness.

Yao returned the adjudicated label bytes and detached checksum. Exact SHA-256
`f4274c0b1c887f0b4c85d4ebe80d2d0bf2b0408a00b4ac69e6e03822ca3933be`
(87,177 bytes) matches. All four case reviews/six decisions are complete with
no blocking disputes. All27 final supporting quotation spans pass saved-source
hash/Unicode-offset checks; all31 original label dispositions resolve to final
records. Original annotations and adjudication are retained unchanged outside
Git. The adjudicator declares baseline blinding; AI provenance, repository
summary exposure and limited/declined independence remain explicit. This does
not create human ground truth or pre-prediction labels.

Validated freeze at2026-10-18T13:11:54.477674Z precedes this scoring pass. The
existing source/population/selection hashes were rechecked. Scoring uses the
four original earliest requests at their original cutoff/deadline; all39 repeats
remain separate. No model replay, live fetch or host change was performed.
Private pairwise and case-level matching records are retained outside Git.

| Measure | Observed result | Meaning / limit |
|---|---|---|
| Supplemental broad adverse-flag presence | 4/4 agreement; Wilson95% interval0.510109–1 | Tiny descriptive flag comparison, not full semantic accuracy |
| Strict adverse-event matching | TP0 / unmatched prediction1 / FN1 | The correct coarse item-type alert has only ITEM_METADATA facts with null text spans; actor/actuality/event proof is absent. The frozen source-span matching rule cannot award a TP. The unmatched prediction does not establish a fabricated source event |
| Scoped statement detail | 0/7 adjudicated propositions explicitly emitted;0 statement FP | Metadata item findings do not encode the supported proposition/actuality/span; supplementary context is outside this denominator |
| Class1/2 | 0 false promotions;0 positive gold events | Negative behavior only; positive trigger recall unqualified |
| Scoped financial metrics | 0 predicted facts;0 gold facts | Appropriate silence on these sources; no positive numeric extraction test |
| Timing/availability | 4/4 representatives and39/39 repeats ASSESSED within original cutoff+60s | Local processing2–16ms, median8ms; maximum cutoff-to-completion18.092s. Not LLM latency or source-to-event latency |
| Coverage flag | 1/4 distinct filings incomplete;21/43 requests | Conservative instruction regex matches a benign public-link invitation. Original flag retained;21 includes repeats, not21 independent filings |

Aggregate measures, frozen input hashes and matching-record/script hashes:
[evidence/deterministic-diagnostic-score-20261018.json](evidence/deterministic-diagnostic-score-20261018.json).
Cross-checks against the raw runtime export verify representative selection,
all43 original deadlines, gold counts, null metadata spans and unchanged gold.
No application code/tests or golden files changed; no application suite rerun.

**Diagnostic completed, limited result:** fast operational baseline and coarse
flag agreement on this tiny set, with no demonstrated source-backed semantic
event recall. Four filings/two issuers and one non-actionable taxonomy adverse
event cannot establish general accuracy, profitability or superiority to an LLM.
T01, v3 M9, human independence and adoption remain unqualified.

**PC-LABEL02-INJ01 remaining (Yao Zhu):** review the benign public-link
instruction flag in the exact new routed configuration with Keegan peer review;
record intended trust/coverage behavior and real-source regression evidence
before calling that source fully qualified. Preserve actual injection defenses
and the old outputs; do not erase or relabel the historical incomplete result.

## PC-LABEL02-R3 — harness versus assessor boundary

Yao clarified the intended boundary: the harness supplies point-in-time evidence, bounded tools, claim verification, deterministic policy/risk/execution and audit; the selected LLM performs semantic evidence assessment. The deployed RuleBaselineModel is the temporary deterministic assessment path. Its small retrospective output comparison is not a test of whether the harness can act as the LLM analyst.

The conversational 4/10 judgment was not a predefined or statistically validated metric and is withdrawn. It must not be treated as a harness rating or readiness gate. Likewise, the seven proposition-level annotation details absent from the rule output describe an output/task representation gap; they do not establish that the harness failed its intended semantic-analysis task, because it has no such assigned task. The frozen strict matching counts still describe what the saved baseline outputs contain under the chosen rubric; no labels, outputs, matching rules or counts have been changed after unblinding.

Appropriate interpretation: the collected run supplies evidence about ingestion, scheduling, completion, recovery, verification/control wiring and audit delivery, with the recorded source gaps and benign-link trust/coverage limitation. It does not measure the semantic performance of the selected LLM or the complete LLM-plus-harness system. That needs actual composed-model outputs, supported claims and separate blind evaluation. Verification and policy rules still constrain which supported model claims can be accepted; adding a model does not silently alter those contracts.

Source architecture checked: IDEA-012 role split, IDEA-056 deterministic boundaries and runtime service/RuleBaselineModel versus routed assessor wiring. No runtime, schema, model, prompt, threshold, guardrail or release change follows from this interpretation correction. Original gold, score JSON, pairwise records and report are preserved.


## PC-LABEL02-INJ01-R1 — local trust review delivered (2026-10-19 SGT)

[PC-YAO-NB01](YAO_NONBLOCKING_REVIEW_20261019.md) supplies the local review and
regressions against the exact capped v3 routing/pinned stage prompts, with saved
public-source HTML and mocked transports. Five tests/13 subtests pass; the benign
link retains its instruction flag/incomplete coverage in all three stages and
the combined result. Tool URL redirection is refused; detector and historical
outputs/labels/scores remain unchanged. This records the cost of the existing
conservative behavior; no domain exception or live-model quality claim follows.
Keegan's independent review remains. T01, v3 M9, human labels and actual deployed
provider/source qualification keep their separate gates.
