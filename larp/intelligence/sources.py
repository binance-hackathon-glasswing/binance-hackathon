"""Owner-local source/store/artifact interfaces for ingestion.

These are development ports for the evidence path. `EvidenceStore.commit` follows the
common `commit(batch: Document) -> Document` vocabulary in PARALLEL_BUILD.md; Keegan's
store adapter maps `IngestionBatch.v1` into the shared CommitBatch/jobs tables. Until that
adapter exists, the in-memory implementations in fakes.py are explicitly temporary.
"""

from dataclasses import dataclass
from typing import Protocol

from larp.contracts import Document


@dataclass(frozen=True, slots=True)
class Listing:
    status: str  # OK | UNAVAILABLE | INVALID
    retrieved_ms: int
    submissions: dict | None
    response_sha256: str | None
    error: str | None = None
    # Older filings beyond the recent block (EDGAR `filings.files`), fetched only for a window.
    history: tuple = ()  # columnar blocks, same keys as filings.recent
    history_status: str = "NOT_REQUESTED"  # NOT_REQUESTED | OK | PARTIAL
    history_files: tuple = ()  # {"name", "status", "response_sha256", "error"} per file


@dataclass(frozen=True, slots=True)
class FetchedDocument:
    name: str
    doc_type: str
    role: str  # PRIMARY | EXHIBIT
    url: str
    status: str  # OK | FAILED
    retrieved_ms: int
    content: bytes | None
    content_type: str | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class FetchedFiling:
    accession: str
    index_status: str  # OK | FAILED | NOT_REQUESTED
    documents: tuple
    truncated: bool = False  # readable documents omitted by the retrieval bound


class FilingSource(Protocol):
    source_id: str

    def list_filings(self, cik: int, window: tuple | None = None) -> Listing: ...

    def fetch_filing(self, cik: int, row: dict, max_documents: int) -> FetchedFiling: ...


class ArtifactSink(Protocol):
    def put(self, content: bytes) -> str: ...  # content-addressed; returns sha256

    def get(self, sha256: str) -> bytes | None: ...


class EvidenceStore(Protocol):
    def read_cursor(self, source_id: str, issuer_id: str) -> Document | None: ...

    def commit(self, batch: Document) -> Document: ...

    def records(self, issuer_id: str) -> tuple: ...  # EvidenceRecord.v1 documents
