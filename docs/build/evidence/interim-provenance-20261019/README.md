# YP-01 — original interim summary handoff

Original bytes from Yao's retained Oct17 download, checked against its original
`SHA256SUMS` and the retained deployment copy. This is the older **interim**
summary, not the later Oct18 capture or a final profile. Source, parameters,
file-prefix byte counts and original capture hashes are in `run-metadata.json`.

Run from repository root:

```sh
PYTHONPATH=. python docs/build/evidence/interim-provenance-20261019/verify.py
```

The verifier hashes all original files, verifies exact original snapshot prefixes
inside the already-committed Oct18 capture, reproduces the summary object and
report coverage/symbol details, and confirms final defaults still refuse. It
makes no network call or write. [Verification receipt](verification.json).

Important historical caveat: the original report's fee-netting assertion is an
unverified assumption (IDEA-063 FN3, #119); raw bytes are preserved for provenance.
All860 swap-gas estimates are fallback. Two-day/nine-US-session-sample coverage
does not satisfy final defaults; no profile or numeric-policy acceptance follows.

Review and remaining owners: [PC-YAO-NB01](../../YAO_NONBLOCKING_REVIEW_20261019.md).
