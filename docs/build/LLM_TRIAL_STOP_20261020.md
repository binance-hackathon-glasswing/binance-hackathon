# PC-STOP01 — collect and stop the unsigned model trial (2026-10-20)

Yao Zhu requests retrieval of the AWS trial data and shutdown to stop further
model spend. Scope: the existing unsigned primary-host trial only; preserve
accounting and all historical evidence. This is an early operational stop, not
model adoption or a change to the frozen quality criteria/cutoff.

Prospective acceptance, recorded before export/shutdown:

1. Confirm exact current host/run/build/database and shadow execution; refuse an
   unexpected identity or active signing/execution.
2. Obtain a private pre-stop export: verified PostgreSQL logical backup, original
   model/market artifacts, SQLite-consistent evidence/source/budget backups and
   source polls. Transfer privately and verify archive/file checksums locally.
3. Stop and disable the runtime and evidence workers that can initiate paid
   calls. Keep uploader/archive available until pending audit work is drained;
   preserve failures and require an anchor covering the stopped journal.
4. Obtain and verify the final stopped snapshot and accounting; preserve all
   UNKNOWN reservations, latches, policies and original databases. Do not reset
   the ledger, rewrite logs, run inference or trade. Verify stopped/disabled
   workers and stable charge counts after a separate observation.
5. Record actual duration/populations/cost limits and remaining label/quality,
   provider-billing/rights and hosted/signed acceptance. Update PR133 LD11/LD12
   accurately; do not check off either whole item from export/shutdown alone.

Private exports belong under git-ignored
`deploy/activation/trial-stop-20261020/`; no raw model/source/label data,
credentials, private endpoints or presigned URLs go into Git.

Operational addition before execution: the 12:00 UTC scheduled ACK anchor covers
sequence 187, while the stopped journal is sequence 188. The exact-run retirement
script [close-and-anchor.sh](ops/trial-stop-20261020/close-and-anchor.sh) uses the
installed `S3Archive` implementation to preserve a separate on-demand `Anchor.v2`
under a new namespace, with version read-back, checksum, KMS and compliance
retention verification. It does not change the journal or scheduled outbox, claim
a later scheduled-hour ACK, or require another model round. All audit work must
be drained and the process session closed before this final anchor is written.
