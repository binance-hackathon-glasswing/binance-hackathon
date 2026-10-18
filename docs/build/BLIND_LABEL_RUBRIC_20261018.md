# Blind-label matching and frozen selection — KMP-LABEL01

Keith, 2026-10-18 UTC. Prospective rubric for the new unsigned v3 trial; Keegan
confirms with the protocol before its first assessment. Criteria: `1536af8`.
The selection method is TR-AC2 unchanged; this adds matching semantics, not a
new seed or an outcome-selected population. Private labels/documents stay outside Git.

## Population and selection

At the declared unsigned cutoff, freeze all eligible requested trial assessments
and their exact issuer/filing artifact pairs, including ABSTAIN, UNAVAILABLE,
late, failed and retry records. Bind build/config/prompt/protocol/cutoff and raw
export hash. Never select only successful jobs or only filings flagged by a model.
Keep the complete eligible population before deduplication.

Use seed `larp-model-trial-20261018-M9-v1`. Include all unique `(issuer ID, filing
artifact hash)` pairs if ≤40; otherwise select 40. For repeated jobs on a pair,
use earliest recorded request, breaking ties by assessment ID, to assign the
stratum `(issuer ID, ordered routing-stage labels, final status)`. Rank strata
by SHA-256 of canonical JSON `[seed,"stratum",issuer,stages,status]`; within a
stratum rank pairs by SHA-256 of `[seed,"filing",issuer,artifact_hash]`. Break
hash ties lexically by those same canonical bytes. Canonical JSON is UTF-8,
sorted object keys, compact separators and ASCII escaping. Round-robin one
pair from each ranked stratum until 40 or population exhaustion. Record every
unrepresented stratum; no replacing inconvenient/missing/failed cases.

Before annotation, retain SHA-256 and byte counts of the immutable population,
selection and blind manifests outside Git. The selection manifest records the
representative job, stratum/rank/round and all duplicate job IDs. The blind
manifest maps opaque case IDs to exact source artifacts in a separate custodian
file, and supplies only the issuer/source identity and documents needed for an
independent reading. Hide model names, stages/statuses, predictions, rationales,
scores and baseline answers from annotators. Report ambiguous or missing input;
do not silently redraw. Supplemental positives/route probes are a separate,
predeclared set and cannot substitute for the frozen natural sample.

## Gold labels before unblinding

An annotator who has not seen routed or baseline answers labels the saved
source documents, not current web revisions. A second independent reviewer
adjudicates disputed/uncertain cases before either answer is revealed; retain
original labels, disagreement and adjudication provenance. Keith owns the
rubric/report; any model-output-aware custodian must not act as its blind annotator.

For each factual adverse event record: opaque case/event IDs, issuer/CIK,
accession and exact source SHA-256, filing family, event/predicate, actor,
actuality (occurred/forward-looking/hypothetical/attributed/negated), event versus
discovery/disclosure dates, affected period if relevant, exact clause span/offset
and source metadata. Mark uncertainty/unreadable evidence explicitly. A gold
negative requires a complete enough source read; missing text is not a negative.

Class 1/2 follows the pinned `red_flags.v1.json`, not an annotator's forecast of
price impact: issuer's Item4.02 non-reliance, Item1.05 material cybersecurity
incident and Item2.06 material impairment predicates, required metadata/clause,
issuer scope, original/amendment and freshness conditions. Record adverse facts
separately from whether they are currently actionable. A historical event can
be factual while failing actionable freshness; hypothetical, negated or another
issuer's event does not become an occurred event for this issuer. Other event
families use the frozen assessment taxonomy. Do not expand that taxonomy after
seeing which events the model missed.

## One-to-one matching

Match a final, accepted, on-time routed finding to one gold event only when
issuer, source filing/revision, factual event/predicate, actor, actuality and
material event/period identity agree, and its evidence span supports that event.
Paraphrases and equivalent date formats may match; a changed sign/unit/scale,
different event, stale revision, attribution or hypothetical-to-actual error does
not. A duplicated paraphrase gets no extra true positive. One broad prediction
cannot match several distinct gold events without separately supported findings.
Keep a pairwise match/adjudication record; do not use an embedding similarity
score as the sole decision. Apply the same rubric and source snapshots to baseline.

- TP: a matched final verified finding delivered within the frozen deadline.
- FN: each unmatched gold adverse event, including when the job abstains, is
  unavailable/late, or a stage found it but the final accepted result did not.
- FP: each unmatched claimed adverse event. Report duplicate claims separately;
  any unsupported Class1/2 finding in the scored final outputs fails the zero
  unsupported-finding bar. Also report rejected stage-level attempts in M5.

Recall is `TP/(TP+FN)` and omission is `FN/(TP+FN)` on the same adjudicated set;
zero positives means unqualified recall, not 100%. Compare routed/baseline
omission on identical case/event IDs. Report source-level and distinct-event
counts so repeated filings of the same event cannot manufacture 10 positives.
At least 10 distinct adverse events across 5 filing families, including both
classes, are required by TR-AC2. Separately report all M5 paths/stages; the
40-filing selection alone does not guarantee their minimum counts.

## Application status

**NOT_RUN: no immutable v3 job/evidence export has been supplied.** Therefore
there is no valid real population, selected/blind manifest, label set or M9
result to hash yet. Applying selection to interim quotes or synthetic jobs would
not satisfy the requested trial. No fabricated draw or empty-sample pass is
reported. The missing-input status is machine-readable in
[sampling-status.json](evidence/model-prerequisites-20261018/sampling-status.json).

Yao supplies the cutoff-bound job/stage export and corresponding source artifact
bytes privately. Keith/custodian applies the frozen method above, records the
three hashes before annotation and hands the blind documents to the independent
annotator; Keegan confirms protocol/rubric first. This remains an open item in
PR #133 and the live backlog until the actual draw and labels are verified.
