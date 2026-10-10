"""Point-in-time filing ingestion with a durable cursor (IDEA-013 R3, IDEA-021 ENG-08).

One `poll` lists an issuer's filings, ingests every expected-form accession at or after the
cursor floor that is not yet known, and commits records, assessment job requests and the
new cursor in ONE `IngestionBatch.v1` through the store port. The cursor therefore never
advances past work that is not durable. Properties:

- Deduplication is by accession; re-listing the same filings creates nothing.
- A filing first seen after a later filing (EDGAR indexing lag) is still ingested and is
  flagged `late_delivery`; the floor, not the newest timestamp, bounds what is considered.
- Source outage commits only a health change. Catch-up after the outage ingests every
  missed filing once, with `available_ms` = our retrieval time, never backdated.
- `recheck` re-fetches known accessions; changed bytes create revision n+1 linked to the
  superseded content hash. Earlier records are never rewritten.
- Per-filing fetch failures are retried on later polls; after `max_fetch_attempts` the
  accession is recorded as MISSING (dead letter) so downstream sees a known-unreadable filing.
- BACKFILL mode ingests an explicit older window without moving the live watermark. The
  source is given the window so it can read EDGAR's historical submissions files; any history
  file it could not read makes the outcome PARTIAL_HISTORY, listed per file.

Jobs follow the runtime job vocabulary (lane/due_ms/valid_until_ms/max_attempts/missed);
the store owns attempts, status and scheduling. Jobs carry no trade command.
"""

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError, digest
from larp.intelligence.edgar import check_identity, listing_rows
from larp.intelligence.issuers import DOMESTIC_FORMS, FOREIGN_PRIVATE_FORMS
from larp.intelligence.text import document_text

MODES = ("LIVE", "BACKFILL")
# Current/periodic forms of either filer class: one arriving from the other class is a mapping anomaly.
ALL_PERIODIC_AND_CURRENT = frozenset(DOMESTIC_FORMS) | frozenset(FOREIGN_PRIVATE_FORMS)


def initial_cursor(source_id: str, issuer_id: str, floor_ms: int) -> dict:
    return {"schema": "EvidenceCursor.v1", "source_id": source_id, "issuer_id": issuer_id, "version": 0,
            "floor_ms": floor_ms, "watermark_ms": None, "known": {}, "pending": {}, "dead_letter": {},
            "health": {"status": "NEVER_POLLED", "last_success_ms": None, "last_attempt_ms": None,
                       "unavailable_since_ms": None, "consecutive_failures": 0, "last_error": None}}


def assessment_job(record: dict, now_ms: int, config, *, severity_items: dict) -> dict:
    adverse = any(severity_items.get(i, ["UNKNOWN", 0])[0] == "ADVERSE" for i in record["items"])
    priority = {"CURRENT": 20, "QUARTERLY": 30, "ANNUAL": 30}[record["form_class"]] - (10 if adverse else 0)
    if record["ingest_mode"] == "BACKFILL":
        priority += 50
    payload = {"kind": "ASSESS_FILING", "issuer_id": record["issuer_id"], "accession": record["accession"],
               "record_id": record["record_id"], "content_hash": record["content_hash"],
               "revision": record["revision"]}
    return {"job_id": "evidence:" + digest("larp.intel.job.v1", payload), "lane": "evidence",
            "due_ms": now_ms, "valid_until_ms": now_ms + config.p("job_validity_ms"),
            "max_attempts": config.p("job_max_attempts"), "priority": priority,
            "calendar_id": "UTC", "tzdata_version": "utc-only-no-tzdata", "missed": "catch_up",
            "payload": payload}


class Ingestor:
    def __init__(self, *, registry, source, store, artifacts, config, clock_ms, run_id: str,
                 synthetic: bool = False):
        self.registry, self.source, self.store, self.artifacts = registry, source, store, artifacts
        self.config, self.clock, self.run_id, self.synthetic = config, clock_ms, run_id, synthetic

    def _cursor(self, issuer_id: str) -> dict:
        stored = self.store.read_cursor(self.source.source_id, issuer_id)
        if stored is None:
            return initial_cursor(self.source.source_id, issuer_id,
                                  self.clock() - self.config.p("initial_backfill_ms"))
        cursor = stored.read()
        if cursor.get("schema") != "EvidenceCursor.v1" or cursor["issuer_id"] != issuer_id:
            raise IntelligenceError("Stored cursor belongs to another issuer or schema")
        return cursor

    def poll(self, issuer_id: str, *, mode: str = "LIVE", window: tuple | None = None,
             recheck: frozenset = frozenset()) -> Document:
        if mode not in MODES or (mode == "BACKFILL") != (window is not None):
            raise IntelligenceError("BACKFILL needs a (from_ms, to_ms) window; LIVE takes none")
        entry = self.registry.by_issuer(issuer_id)
        cursor = self._cursor(issuer_id)
        expected_version = cursor["version"]
        now = self.clock()
        listing = self.source.list_filings(entry.cik, window=window)
        health = dict(cursor["health"], last_attempt_ms=now)
        outcome = {"status": "OK", "new_records": [], "revisions": [], "duplicates": 0, "late": [],
                   "retry_pending": [], "dead_letter": [], "rejected_future": [], "ignored_forms": 0,
                   "unexpected_forms": [], "malformed_rows": 0, "history_status": listing.history_status,
                   "history_files": [dict(f) for f in listing.history_files]}
        if listing.status == "OK":
            try:
                check_identity(listing.submissions, entry.cik, entry.entity_name)
            except IntelligenceError as exc:
                listing = type(listing)("INVALID", listing.retrieved_ms, None, listing.response_sha256, str(exc))
        if listing.status != "OK":
            health.update(status="UNAVAILABLE", consecutive_failures=health["consecutive_failures"] + 1,
                          unavailable_since_ms=health["unavailable_since_ms"] or now, last_error=listing.error)
            outcome["status"] = "SOURCE_UNAVAILABLE" if listing.status == "UNAVAILABLE" else "INVALID_SOURCE"
            return self._commit(cursor, expected_version, health, [], [], outcome, listing)

        records, jobs = [], []
        old_watermark, newest = cursor["watermark_ms"], cursor["watermark_ms"]
        if listing.history_status == "PARTIAL":
            outcome["status"] = "PARTIAL_HISTORY"
        for row in sorted(listing_rows(listing.submissions, listing.history),
                          key=lambda r: (r["original_ms"] or 0, r["accession"] or "")):
            if row["malformed"]:
                outcome["malformed_rows"] += 1
                continue
            accession, form_class = row["accession"], entry.form_class(row["form"])
            if form_class is None:
                if row["form"] in ALL_PERIODIC_AND_CURRENT:
                    outcome["unexpected_forms"].append([accession, row["form"]])
                outcome["ignored_forms"] += 1
                continue
            in_scope = (row["original_ms"] >= cursor["floor_ms"] if mode == "LIVE"
                        else window[0] <= row["original_ms"] <= window[1])
            if not in_scope and accession not in cursor["pending"]:
                continue
            if row["original_ms"] > now + self.config.p("max_clock_skew_ms"):
                outcome["rejected_future"].append(accession)
                continue
            known = cursor["known"].get(accession)
            if (known or accession in cursor["dead_letter"]) and accession not in recheck:
                outcome["duplicates"] += 1
                continue
            record = self._ingest(entry, row, form_class, cursor, known, mode, old_watermark, outcome,
                                  listing.response_sha256)
            if record is None:
                continue
            records.append(record)
            if record["quality"] != "MISSING":
                jobs.append(assessment_job(record, now, self.config, severity_items=self.config.severity["items"]))
            if mode == "LIVE":
                newest = row["original_ms"] if newest is None else max(newest, row["original_ms"])
        cursor["watermark_ms"] = newest
        self._bound_known(cursor)
        health.update(status="OK", last_success_ms=listing.retrieved_ms, unavailable_since_ms=None,
                      consecutive_failures=0, last_error=None)
        return self._commit(cursor, expected_version, health, records, jobs, outcome, listing)

    def _ingest(self, entry, row, form_class, cursor, known, mode, old_watermark, outcome, listing_hash):
        accession = row["accession"]
        fetched = self.source.fetch_filing(entry.cik, row, self.config.limits["max_documents_per_filing"])
        failed = fetched.index_status == "FAILED" or any(d.status != "OK" for d in fetched.documents)
        primary_ok = any(d.role == "PRIMARY" and d.status == "OK" for d in fetched.documents)
        attempts = cursor["pending"].get(accession, {}).get("attempts", 0) + 1
        if failed and attempts < self.config.limits["max_fetch_attempts"]:
            cursor["pending"][accession] = {"attempts": attempts, "original_ms": row["original_ms"],
                                            "last_error": next((d.error for d in fetched.documents if d.error),
                                                               "INDEX_FAILED")}
            outcome["retry_pending"].append(accession)
            return None
        cursor["pending"].pop(accession, None)
        documents = []
        for doc in fetched.documents:
            entry_doc = {"name": doc.name, "doc_type": doc.doc_type, "role": doc.role, "url": doc.url,
                         "status": doc.status, "retrieved_ms": doc.retrieved_ms, "content_type": doc.content_type,
                         "error": doc.error, "raw_sha256": None, "text_sha256": None, "text_bytes": None,
                         "encoding": None, "decode_lossy": None}
            if doc.status == "OK":
                saved = document_text(doc.content, doc.name, doc.content_type)
                if self.artifacts.put(doc.content) != saved.raw_sha256 or \
                        self.artifacts.put(saved.saved_bytes) != saved.text_sha256:
                    raise IntelligenceError("Artifact store returned a different content address")
                entry_doc.update(raw_sha256=saved.raw_sha256, text_sha256=saved.text_sha256,
                                 text_bytes=len(saved.saved_bytes), encoding=saved.encoding,
                                 decode_lossy=saved.lossy)
            documents.append(entry_doc)
        if not primary_ok:
            quality = "MISSING"
            cursor["dead_letter"][accession] = {"attempts": attempts, "original_ms": row["original_ms"]}
            outcome["dead_letter"].append(accession)
        else:
            quality = "SYNTHETIC" if self.synthetic else "VALID"
        content_hash = digest("larp.intel.content.v1", {"documents": sorted(
            [d["name"], d["text_sha256"]] for d in documents if d["text_sha256"])})
        if known and known["content_hash"] == content_hash:
            outcome["duplicates"] += 1
            return None
        retrieved = max([d["retrieved_ms"] for d in documents] or [self.clock()])
        late = mode == "LIVE" and old_watermark is not None and row["original_ms"] < old_watermark
        record = {"schema": "EvidenceRecord.v1", "source_id": self.source.source_id,
                  "issuer_id": entry.issuer_id, "cik": entry.cik, "accession": accession, "form": row["form"],
                  "form_class": form_class, "amendment": row["form"].endswith("/A"), "items": row["items"],
                  "acceptance_raw": row["acceptance_raw"], "original_ms": row["original_ms"],
                  "filing_date": row["filing_date"], "report_date": row["report_date"],
                  "retrieved_ms": retrieved, "available_ms": retrieved, "available_basis": "FIRST_RETRIEVAL",
                  "ingest_mode": mode, "late_delivery": late,
                  "revision": known["revision"] + 1 if known else 0,
                  "supersedes": known["content_hash"] if known else None,
                  "content_hash": content_hash, "quality": quality,
                  "incomplete": failed and primary_ok, "index_status": fetched.index_status,
                  "listing_sha256": listing_hash, "documents": documents}
        record["record_id"] = "rec:" + digest("larp.intel.record.v1", record)
        cursor["known"][accession] = {"original_ms": row["original_ms"], "content_hash": content_hash,
                                      "revision": record["revision"], "record_id": record["record_id"]}
        (outcome["revisions"] if known else outcome["new_records"]).append(record["record_id"])
        if late:
            outcome["late"].append(accession)
        return record

    def _bound_known(self, cursor: dict) -> None:
        limit = self.config.limits["max_known_accessions"]
        if len(cursor["known"]) <= limit:
            return
        ordered = sorted(cursor["known"].items(), key=lambda kv: (kv[1]["original_ms"], kv[0]))
        drop = ordered[: len(ordered) - limit]
        for accession, _ in drop:
            del cursor["known"][accession]
        # Raise the floor so a forgotten accession can never be re-ingested as new.
        cursor["floor_ms"] = max(cursor["floor_ms"], drop[-1][1]["original_ms"] + 1)

    def _commit(self, cursor, expected_version, health, records, jobs, outcome, listing) -> Document:
        cursor = dict(cursor, version=expected_version + 1, health=health)
        batch = {"schema": "IngestionBatch.v1", "run_id": self.run_id, "source_id": self.source.source_id,
                 "issuer_id": cursor["issuer_id"], "expected_cursor_version": expected_version,
                 "cursor": cursor, "records": records, "jobs": jobs,
                 "listing": {"status": listing.status, "retrieved_ms": listing.retrieved_ms,
                             "response_sha256": listing.response_sha256, "error": listing.error,
                             "history_status": listing.history_status,
                             "history_files": [dict(f) for f in listing.history_files]}}
        batch["batch_id"] = "ingest:" + digest("larp.intel.batch.v1", batch)
        receipt = self.store.commit(Document.from_dict(batch)).read()
        if receipt.get("status") not in ("COMMITTED", "IDEMPOTENT"):
            outcome = dict(outcome, status="CONFLICT", new_records=[], revisions=[], late=[])
            jobs = []
        return Document.from_dict({"schema": "IngestionOutcome.v1", "issuer_id": cursor["issuer_id"],
                                   "batch_id": batch["batch_id"], "receipt": receipt,
                                   "cursor_version": cursor["version"], "jobs": [j["job_id"] for j in jobs],
                                   **outcome})
