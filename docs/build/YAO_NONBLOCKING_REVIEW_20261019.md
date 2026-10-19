# Yao local PR133 work — PC-YAO-NB01

Completed against PR133 `aca1b7c`: source-link trust review/regressions and the
missing original interim-summary handoff. Criteria were committed/pushed at
`47fa8f9` before the checks; test/data source `35f42b9`, provenance verifier
`6833462`. Keegan's independent trust review and Keith's summary review remain.

## PC-LABEL02-INJ01-R1: source trust review

The recorded benign invitation matches the detector's generic `visit https://`
branch in `larp/intelligence/tools.py`. The marker means untrusted instruction
text is present; it does not establish a malicious document. The current policy
deliberately makes such an assessment incomplete. No URL/domain exception is
introduced: source text remains data, tools take pinned record identifiers and
cannot follow arbitrary destinations, and verified claims retain their existing
authority checks. This keeps the conservative coverage loss visible for review.

New [regressions](../../tests/intelligence/test_source_link_trust.py) exercise the
exact repository capped v3 file (SHA `a5fca50a…22d8d`) and current shadow config,
with the pinned primary/review addenda. They check all three composed stages,
ten instruction examples, rejected URL-tool attempts, ordinary-text controls and
the six-call global bound. Optional local input is the original saved public HTML
(13,253 bytes, SHA `74b6088a…977c3`); its bytes are checked before use. That HTML
is embedded in a synthetic issuer/record/time fixture and uses mocked provider
responses. This is a real-source-text harness regression, not a replay of the
original request or a live-provider/semantic-quality evaluation. Private corpus,
labels, old predictions and scores remain outside this change.

Results at `35f42b9`: **5 tests / 13 subtests PASS**, including the optional source.
The benign link keeps `UNTRUSTED_INSTRUCTIONS_IN_EVIDENCE` and incomplete coverage
in primary, both reviewers and the combined result. Prompts remain exact; tool
redirection is refused. Current behavior is retained, with the false-positive
coverage cost explicit. No runtime, detector, prompt or authority change.

Broader intelligence suite: **425 passed / 2 skipped / 1,394 subtests**, 13.39 s,
macOS arm64/Python 3.12.14. Skips: optional private source (passed separately) and
disposable PostgreSQL (AC-I04). The initial sandbox run had two loopback-bind
permission failures; the same suite passed with local loopback permission.
[Machine receipt](evidence/source-link-trust-20261019.json) pins all tested files.

Reproduce from repository root with the optional private public-source file:

```sh
LARP_INJ01_SOURCE_FILE=/private/path/document-02.original-source.txt \
  python -m pytest -q tests/intelligence/test_source_link_trust.py
```

**Remaining:** Keegan independently accepts/rejects this conservative trust
disposition and regression evidence. The historical one-filing/21-request
incomplete result is preserved. Exact deployed-build/provider qualification,
T01, M9 and independent human labels remain under their existing gates.

## YP-01: original interim-summary provenance recovered

The [original handoff files](evidence/interim-provenance-20261019/README.md)
are now available in Git for Keith. All four original transfer checksums match,
and they also match the previously retained local deployment copies. Summary SHA
`41e17b4d…be2b`; report SHA `0195e576…4f89`; capture identity
`2ec51d51…de7da`. The retained rehearsal profile's actual file SHA is
`d951207f…4542`, and its embedded summary equals this recovered original.

The metadata's original two capture snapshots are exact byte prefixes of the
already-committed later KMP-QUOTE01 export. Their pre-existing byte counts and
hashes both verify: 180 + 336 = 516 records (430 stock samples, 86 BNB quotes).
No records were edited, reserialized or selected by a new cutoff. Running the
existing summarizer on those hash-proven original bytes reproduces the entire
summary object, report coverage and symbol details exactly.

Coverage stays interim: two UTC days, each token 9 US-session / 77 off-session
samples. All 860 swap-gas estimates are fallback. The current final defaults
correctly refuse the original snapshot. Its old `fee_bps` description asserts
netting; that is retained as historical bytes and superseded by FN3/#119's
UNVERIFIED disposition. No raw API-response re-verification, new profile,
approval, capture resumption or final fee/gas/cap acceptance is claimed.

**Remaining:** Keith reviews the delivered originals/verification, finishes the
actual final capture/profile/gas/fee work, and Isaac retains #119/#120/#44
acceptance. The Yao export dependency is complete.
