"""SYNTHETIC test doubles: fake clock, filing source, evidence store and artifact sink.

Owner-local and explicitly temporary (PARALLEL_BUILD.md): they exist so the evidence path
runs offline before the shared store, scheduler and real adapters are integrated. Each class
sets `synthetic = True`; `require_real` refuses them for any live wiring.
"""

import json

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError, sha256_hex
from larp.intelligence.edgar import select_documents
from larp.intelligence.sources import FetchedDocument, FetchedFiling, Listing


def require_real(*components) -> None:
    for component in components:
        if getattr(component, "synthetic", False):
            raise IntelligenceError(f"{type(component).__name__} is a synthetic test double; refused for live use")


class FakeClock:
    synthetic = True

    def __init__(self, now_ms: int):
        self.now = now_ms

    def __call__(self) -> int:
        return self.now

    def advance(self, ms: int) -> None:
        if ms < 0:
            raise ValueError("Fake clock never moves backward")
        self.now += ms


class FakeFilingSource:
    """Serves synthetic filings. A filing appears in listings once the clock reaches `visible_ms`."""

    synthetic = True
    source_id = "sec-edgar"

    def __init__(self, clock, entities: dict):
        self.clock, self.entities = clock, dict(entities)  # cik -> entity name
        self.filings = {}  # cik -> list of filing specs
        self.available = True
        self.failing_documents = {}  # (accession, name) -> remaining failures
        self.listing_calls = self.fetch_calls = 0

    def add(self, cik: int, *, accession, form, items, acceptance, documents, visible_ms=None,
            primary=None) -> None:
        self.filings.setdefault(cik, []).append({
            "accession": accession, "form": form, "items": items, "acceptance": acceptance,
            "documents": [dict(d) for d in documents], "visible_ms": visible_ms,
            "primary": primary or documents[0]["name"]})

    def replace_document(self, accession: str, name: str, content: bytes) -> None:
        for specs in self.filings.values():
            for spec in specs:
                if spec["accession"] == accession:
                    for doc in spec["documents"]:
                        if doc["name"] == name:
                            doc["content"] = content
                            return
        raise KeyError((accession, name))

    def list_filings(self, cik: int, window: tuple | None = None) -> Listing:  # every filing is in `recent`
        self.listing_calls += 1
        now = self.clock()
        if not self.available:
            return Listing("UNAVAILABLE", now, None, None, "HTTP 503")
        visible = [s for s in self.filings.get(cik, []) if s["visible_ms"] is None or s["visible_ms"] <= now]
        visible.sort(key=lambda s: s["acceptance"], reverse=True)  # EDGAR lists newest first
        recent = {"accessionNumber": [s["accession"] for s in visible], "form": [s["form"] for s in visible],
                  "items": [",".join(s["items"]) for s in visible],
                  "acceptanceDateTime": [s["acceptance"] for s in visible],
                  "filingDate": [s["acceptance"][:10] for s in visible], "reportDate": ["" for _ in visible],
                  "primaryDocument": [s["primary"] for s in visible]}
        submissions = {"cik": str(cik), "name": self.entities.get(cik, "UNKNOWN"), "filings": {"recent": recent}}
        body = json.dumps(submissions, sort_keys=True).encode()
        return Listing("OK", now, submissions, sha256_hex(body))

    def fetch_filing(self, cik: int, row: dict, max_documents: int) -> FetchedFiling:
        self.fetch_calls += 1
        spec = next(s for s in self.filings[cik] if s["accession"] == row["accession"])
        index_rows = tuple((d["type"], d["name"], d.get("description", "")) for d in spec["documents"])
        all_documents = select_documents(index_rows, row["primary_document"], row["form"], len(index_rows) + 1)
        chosen = all_documents[:max_documents]
        by_name = {d["name"]: d for d in spec["documents"]}
        documents = []
        for doc in chosen:
            key = (row["accession"], doc["name"])
            url = f"synthetic://edgar/{cik}/{row['accession']}/{doc['name']}"
            if self.failing_documents.get(key, 0) > 0:
                self.failing_documents[key] -= 1
                documents.append(FetchedDocument(doc["name"], doc["doc_type"], doc["role"], url, "FAILED",
                                                 self.clock(), None, None, "HTTP 500"))
                continue
            source = by_name[doc["name"]]
            documents.append(FetchedDocument(doc["name"], doc["doc_type"], doc["role"], url, "OK", self.clock(),
                                             source["content"], source.get("content_type", "text/html")))
        return FetchedFiling(row["accession"], "OK", tuple(documents), truncated=len(all_documents) > len(chosen))


class MemoryArtifacts:
    synthetic = True

    def __init__(self):
        self.blobs = {}

    def put(self, content: bytes) -> str:
        digest = sha256_hex(content)
        self.blobs.setdefault(digest, bytes(content))
        return digest

    def get(self, sha256: str):
        return self.blobs.get(sha256)


class MemoryEvidenceStore:
    """In-memory stand-in for the shared store: CAS on cursor/state versions, idempotent batch IDs."""

    synthetic = True

    def __init__(self):
        self.cursors, self.batches, self.jobs, self.states = {}, {}, {}, {}
        self._records = {}
        self.lose_next_ack = False

    def read_cursor(self, source_id: str, issuer_id: str):
        return self.cursors.get((source_id, issuer_id))

    def records(self, issuer_id: str) -> tuple:
        return tuple(self._records.get(issuer_id, []))

    def read_state(self, issuer_id: str):
        return self.states.get(issuer_id)

    def commit(self, batch: Document) -> Document:
        b = batch.read()
        batch_id = b.get("batch_id")
        if batch_id in self.batches:
            status = "IDEMPOTENT" if self.batches[batch_id] == batch.payload else "INTEGRITY_ERROR"
            return Document.from_dict({"schema": "CommitReceipt.v1", "batch_id": batch_id, "status": status})
        for job in b.get("jobs", []):
            held = self.jobs.get(job["job_id"])
            if held is not None and held != Document.from_dict(job).payload:
                return Document.from_dict({"schema": "CommitReceipt.v1", "batch_id": batch_id,
                                           "status": "INTEGRITY_ERROR", "job_id": job["job_id"]})
        if b["schema"] == "IngestionBatch.v1":
            key = (b["source_id"], b["issuer_id"])
            held = self.cursors.get(key)
            if (held.read()["version"] if held else 0) != b["expected_cursor_version"]:
                return Document.from_dict({"schema": "CommitReceipt.v1", "batch_id": batch_id, "status": "CONFLICT"})
            self.cursors[key] = Document.from_dict(b["cursor"])
            existing = {d.read()["record_id"] for d in self._records.get(b["issuer_id"], [])}
            for record in b["records"]:
                if record["record_id"] not in existing:
                    self._records.setdefault(b["issuer_id"], []).append(Document.from_dict(record))
        elif b["schema"] == "EvidenceStateBatch.v1":
            held = self.states.get(b["issuer_id"])
            if (held.read()["version"] if held else 0) != b["expected_state_version"]:
                return Document.from_dict({"schema": "CommitReceipt.v1", "batch_id": batch_id, "status": "CONFLICT"})
            self.states[b["issuer_id"]] = Document.from_dict(b["state"])
        else:
            raise IntelligenceError("Unknown batch schema")
        for job in b.get("jobs", []):
            self.jobs[job["job_id"]] = Document.from_dict(job).payload
        self.batches[batch_id] = batch.payload
        if self.lose_next_ack:
            self.lose_next_ack = False
            raise ConnectionError("synthetic: commit applied, acknowledgement lost")
        return Document.from_dict({"schema": "CommitReceipt.v1", "batch_id": batch_id, "status": "COMMITTED"})
