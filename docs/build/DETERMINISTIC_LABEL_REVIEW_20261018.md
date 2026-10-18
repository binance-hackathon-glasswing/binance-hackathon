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
