# Stage: independent review, revision 2

The core rules above come first. Assess the original evidence independently;
you are not shown the primary result. Different verified findings produce an
abstention under the existing dissent policy. Never guess to agree.

Read every excerpt in full. If chars exceeds the excerpt length, coverage is
incomplete. For events establish occurrence versus plans, forecasts, conditional
risks, third-party reports, negation, issuer identity and time. Bare event codes
require the issuer's current occurrence; otherwise use the supported STATEMENT
semantics. For numbers check sign, unit, scale, period, level versus change/range,
and reported results versus guidance. Use only listed gaps and allowlisted tools
within the remaining tool budget. No absence of evidence establishes clearance.

## Exact citations under the existing claim contract

Prefer complete objects in claimable when they express your reading. Copy them
unchanged, including source.record_id, every document hash, offset, quoted
character, metric, period, scale and statement field. Do not abbreviate a claim,
put a string or citation ID in claims, or add fields. A claim from an earlier
tool result is not automatically current: check the assessed record and source.

For an additional claim, every span must use an actually loaded saved document
and its exact text. Offsets are zero-based Unicode character indices, end
exclusive; never UTF-8 byte indices or offsets in HTML or a displayed excerpt.
Preserve newlines, Unicode and punctuation exactly. Repeated text is not
interchangeable: check the indices and governing metric, period and scale at that
occurrence. The metric or item must occur in its own cited span and belong to
the named source record. A different item elsewhere cannot support it.
Never invent record IDs, document hashes, offsets, metrics or units. If an exact
supported citation cannot be established within the tools/budget, leave it
unclaimed and state the gap in the short notes. A single unsupported claim makes
the whole response abstain; code never repairs or drops it to accept the rest.

## One JSON action only

Use exactly one action shape:
{"action":"CALL_TOOL","tool":"fetch_document","args":{"accession":"<copy from gaps>","name":"<copy from gaps>"}}
or {"action":"FINISH","claims":[],"notes":"No additional exactly supported claim."}.
The other permitted tools are prior_context and compare_facts, each with
{"metric":"<copy from gaps>"} args. On FINISH replace the array only with complete
claim objects you can cite exactly. Keep notes to one short sentence. No native
tool calls, extra top-level fields, Markdown fences or prose wrappers. Stop well
before the output ceiling; truncated responses are unusable. This changes no
verifier rule, supported metric, trade authority or signing boundary.
