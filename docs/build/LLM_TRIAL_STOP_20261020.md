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

## Verified result — PC-STOP01

Stopped on **2026-10-20 at 20:38:32 SGT (12:38:32 UTC)**. Exact run:
`larp-dev-llm-trial-20261018t170339z`, build
`ea25b52325656a19b29e8ddb07b94dd792be6e18`, database `larp_trial2`,
`driver.execution=shadow`. The clean runtime session lasted **43.56 hours** from
Oct18 17:04:43 UTC. This is an early stop by user decision; the frozen 72-hour
unsigned observation criterion is unmet. No quality/adoption pass is inferred.

The final private archive is
`deploy/activation/trial-stop-20261020/final.tar.gz` (31,701,204 bytes), SHA-256
`587aeb67bafde94061889eeff55bf57a91811e64864e998e20d20f87dbe398d0`.
All **14,544 file checksums**, the PostgreSQL `Backup.v1` payload digest, and all
three SQLite integrity checks pass locally. The AWS copy has KMS encryption,
versioning and COMPLIANCE retention through **2027-01-10 12:42:19 UTC**.
Original model/market artifacts, source polls/corpora, evidence/source databases,
selected non-secret configs and the full accounting ledger are retained privately.
The pre-stop archive was separately downloaded/verified before the workers stopped.
It used SSE-S3 encryption; the final archive uses KMS. No raw data is committed.

All six trial units (runtime, evidence, uploader, execution, archive service and
archive timer) are inactive/disabled; process-bearing units have PID zero. The
last independent check at 12:43:00 UTC confirms unchanged charges. Original EC2,
RDS, configurations and databases are retained for later reviewed work.

All **70 rounds are CLOSED**, **109 audit chunks ACK**, and no audit event is
unchunked. The clean runtime session is ended. The new on-demand anchor has
`sequence=188`, matches the stopped journal head, and was read back as `STORED`
with 82-day KMS/COMPLIANCE protection. The scheduled outbox is unchanged.
The two initial anchor-observer attempts failed because ACKed outbox payloads
are empty after delivery; the successful check retrieved the version-pinned
object through its retained receipt. No application or accounting repair occurred.

Pre-stop and final budget backup hashes are **identical**: 104 SETTLED entries
sum to **2,880,356 micro-USD**, including the 2,000,000 initial charge; three
UNKNOWN reservations sum to **337,180 micro-USD**; 106 trial attribution rows
remain. These are shared OpenAI ledger amounts, including pre-existing costs,
not an invoice or an AIand cost total. No UNKNOWN was forgiven, no policy/latch
was reset, and no model call or transaction was initiated by this collection.

There are **70 distinct assessor job IDs**, 41 distinct context hashes and two
issuers. Outcomes: **41 ASSESSED, 29 UNAVAILABLE** (25 deadline exceeded, four
model errors). The trace records 201 requests started, 174 completed-step records
(163 OK/11 ERROR) and 27 call records still in flight at their assessment deadline;
those are historical deadline states, not running workers after shutdown. There
are 502 original model artifact files. Assessment elapsed time ranges from
3,118 to 60,026 ms, median 18,135.5 ms. SQL `jobs` has zero rows: assessor job IDs
come from round records. Repeated inputs and self-reported outcomes do not
establish independently labelled accuracy.

Machine evidence: [llm-trial-stop-20261020.json](evidence/llm-trial-stop-20261020.json).

Remaining owners: **Keith** applies the frozen sampling/label procedure and
reports model/route quality, costs/latencies, affordability and inconclusive
results. **Yao/account owners** reconcile all three UNKNOWN entries and actual
provider billing/AIand usage, expiry/funding/rights, plus remaining host evidence.
**Keegan/team** decide trial disposition/adoption and retain all signed-release,
profile, source and host acceptance gates. PR133 LD11/LD12 remain partial; the
export/preservation/shutdown subtask is complete. A later deployment is separate
work; stopping here does not authorize a restart or erase the fixed cutoff.
