"""Durable source cursors/records (SQLite) and content-addressed artifacts outside Git (AC-D02/AC-D04).

`commit(batch)` is one SQLite transaction: compare-and-set on the cursor version, then immutable record
inserts. A crash between pages loses nothing committed and duplicates nothing (records are keyed by
record_id; reinserting identical bytes is idempotent, different bytes is an integrity error). The
artifact directory holds the permitted raw item bytes and saved text that model inputs are built from;
it must live outside the repository (F-49 raw inputs; F-61 no private data in Git).
"""

from functools import wraps
from pathlib import Path
import json
import os
import sqlite3
import tempfile
import threading

from larp.contracts import Document
from larp.intelligence.common import require_hash, sha256_hex


class StoreConflict(RuntimeError):
    """Stale cursor version or changed immutable record."""


class SQLiteSourceStore:
    def __init__(self, path: str):
        self.path = path
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL") if path != ":memory:" else None
        self.db.execute("CREATE TABLE IF NOT EXISTS cursors (source_id TEXT PRIMARY KEY, version INTEGER, doc BLOB)")
        self.db.execute("CREATE TABLE IF NOT EXISTS records (record_id TEXT PRIMARY KEY, source_id TEXT, item_id TEXT,"
                        " version INTEGER, doc BLOB)")

    def cursor(self, source_id: str) -> dict | None:
        row = self.db.execute("SELECT doc FROM cursors WHERE source_id=?", (source_id,)).fetchone()
        return None if row is None else Document(bytes(row[0])).read()

    def latest(self, source_id: str, item_id: str) -> dict | None:
        """Durable item index: the newest stored version of an item, independent of the bounded cursor cache."""
        row = self.db.execute("SELECT doc FROM records WHERE source_id=? AND item_id=? ORDER BY version DESC LIMIT 1",
                              (source_id, item_id)).fetchone()
        return None if row is None else Document(bytes(row[0])).read()

    def records(self, source_id: str | None = None) -> list:
        query = "SELECT doc FROM records" + (" WHERE source_id=?" if source_id else "") + " ORDER BY rowid"
        return [Document(bytes(r[0])).read() for r in self.db.execute(query, (source_id,) if source_id else ())]

    def commit(self, batch: dict) -> dict:
        cursor = batch["cursor"]
        raw_cursor = Document.from_dict(cursor).payload
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT version FROM cursors WHERE source_id=?", (cursor["source_id"],)).fetchone()
            current = -1 if row is None else row[0]
            if current != batch["expected_cursor_version"]:
                raise StoreConflict("Stale source cursor version")
            for record in batch["records"]:
                raw = Document.from_dict(record).payload
                old = self.db.execute("SELECT doc FROM records WHERE record_id=?", (record["record_id"],)).fetchone()
                if old is not None:
                    if bytes(old[0]) != raw:
                        raise StoreConflict("Record ID reused with different bytes")
                    continue
                self.db.execute("INSERT INTO records VALUES (?,?,?,?,?)", (record["record_id"], record["source_id"],
                                                                          record["item_id"], record["version"], raw))
            self.db.execute("INSERT INTO cursors VALUES (?,?,?) ON CONFLICT(source_id) DO UPDATE SET version=excluded.version,"
                            " doc=excluded.doc", (cursor["source_id"], cursor["version"], raw_cursor))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return {"status": "COMMITTED", "cursor_version": cursor["version"], "records": len(batch["records"])}

    def close(self):
        self.db.close()


def _locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


class SQLiteEvidenceStore:
    """Durable EDGAR evidence store (EvidenceStore port of larp.intelligence.ingest) for the live ingestion runner.

    Same semantics as the in-memory test double: compare-and-set on cursor and state versions, idempotent batch IDs
    (a reused ID with different bytes is an integrity error), immutable records and jobs. One SQLite transaction
    per batch. It serves the hosted shadow ingestion run until the runtime's PostgreSQL store takes this role
    (Keegan, IDEA-042).

    The assessor reads evidence on its own worker thread (and an abandoned worker may still be reading), so the one
    connection is opened for use from any thread and every method holds a re-entrant lock: reads, and each commit's
    whole transaction, never interleave (IDEA-041 R01).

    `read_only=True` defaults to a DELETE-journal database (IDEA-047 R15). It refuses a legacy WAL file before SQLite
    can create incompatible sidecars, and leaves migration/recovery to the writer. Shared readers need no writable
    mount. Private writers retain WAL by default; a private WAL reader must request journal_mode='WAL' explicitly.
    """

    def __init__(self, path: str, *, read_only: bool = False, journal_mode: str | None = None):
        journal_mode = journal_mode if journal_mode is not None else ('DELETE' if read_only else 'WAL')
        if journal_mode not in ('DELETE', 'WAL'):
            raise ValueError('Unsupported evidence journal mode')
        self.path, self.read_only = path, read_only
        self._lock = threading.RLock()
        if read_only:
            if path == ":memory:":
                raise ValueError("A read-only evidence store needs a database file")
            if journal_mode == 'DELETE':
                try:
                    with open(path, 'rb') as stream:
                        header = stream.read(20)
                except OSError:
                    raise sqlite3.OperationalError('Evidence database is not available for reading') from None
                if header[:16] != b'SQLite format 3\x00' or header[18:20] != b'\x01\x01':
                    raise sqlite3.OperationalError('Evidence database requires writer initialization/migration')
            self.db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True,
                                      isolation_level=None, check_same_thread=False)
            return
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        if path != ':memory:':
            try:
                actual = self.db.execute('PRAGMA journal_mode=' + journal_mode).fetchone()[0]
                if actual.upper() != journal_mode:
                    raise sqlite3.OperationalError('Evidence journal mode unavailable')
            except Exception:
                self.db.close()
                raise
        for table in ("batches (batch_id TEXT PRIMARY KEY, doc BLOB)",
                      "ecursors (source_id TEXT, issuer_id TEXT, version INTEGER, doc BLOB, PRIMARY KEY (source_id, issuer_id))",
                      "erecords (record_id TEXT PRIMARY KEY, issuer_id TEXT, doc BLOB)",
                      "ejobs (job_id TEXT PRIMARY KEY, doc BLOB)",
                      "estates (issuer_id TEXT PRIMARY KEY, version INTEGER, doc BLOB)"):
            self.db.execute("CREATE TABLE IF NOT EXISTS " + table)

    @_locked
    def read_cursor(self, source_id: str, issuer_id: str):
        row = self.db.execute("SELECT doc FROM ecursors WHERE source_id=? AND issuer_id=?",
                              (source_id, issuer_id)).fetchone()
        return None if row is None else Document(bytes(row[0]))

    @_locked
    def records(self, issuer_id: str) -> tuple:
        return tuple(Document(bytes(r[0])) for r in self.db.execute(
            "SELECT doc FROM erecords WHERE issuer_id=? ORDER BY rowid", (issuer_id,)))

    @_locked
    def read_state(self, issuer_id: str):
        row = self.db.execute("SELECT doc FROM estates WHERE issuer_id=?", (issuer_id,)).fetchone()
        return None if row is None else Document(bytes(row[0]))

    @_locked
    def jobs(self) -> list:
        return [Document(bytes(r[0])).read() for r in self.db.execute("SELECT doc FROM ejobs ORDER BY rowid")]

    def _receipt(self, batch_id, status, **extra) -> Document:
        return Document.from_dict({"schema": "CommitReceipt.v1", "batch_id": batch_id, "status": status, **extra})

    @_locked
    def commit(self, batch: Document) -> Document:
        if self.read_only:
            raise StoreConflict("Read-only evidence store")
        b = batch.read()
        batch_id = b.get("batch_id")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            held = self.db.execute("SELECT doc FROM batches WHERE batch_id=?", (batch_id,)).fetchone()
            if held is not None:
                self.db.execute("ROLLBACK")
                return self._receipt(batch_id, "IDEMPOTENT" if bytes(held[0]) == batch.payload else "INTEGRITY_ERROR")
            for job in b.get("jobs", []):
                old = self.db.execute("SELECT doc FROM ejobs WHERE job_id=?", (job["job_id"],)).fetchone()
                if old is not None and bytes(old[0]) != Document.from_dict(job).payload:
                    self.db.execute("ROLLBACK")
                    return self._receipt(batch_id, "INTEGRITY_ERROR", job_id=job["job_id"])
            if b["schema"] == "IngestionBatch.v1":
                row = self.db.execute("SELECT version FROM ecursors WHERE source_id=? AND issuer_id=?",
                                      (b["source_id"], b["issuer_id"])).fetchone()
                if (row[0] if row else 0) != b["expected_cursor_version"]:
                    self.db.execute("ROLLBACK")
                    return self._receipt(batch_id, "CONFLICT")
                self.db.execute("INSERT INTO ecursors VALUES (?,?,?,?) ON CONFLICT(source_id, issuer_id) DO UPDATE "
                                "SET version=excluded.version, doc=excluded.doc",
                                (b["source_id"], b["issuer_id"], b["cursor"]["version"],
                                 Document.from_dict(b["cursor"]).payload))
                for record in b["records"]:
                    raw = Document.from_dict(record).payload
                    old = self.db.execute("SELECT doc FROM erecords WHERE record_id=?", (record["record_id"],)).fetchone()
                    if old is None:
                        self.db.execute("INSERT INTO erecords VALUES (?,?,?)", (record["record_id"], b["issuer_id"], raw))
                    elif bytes(old[0]) != raw:
                        raise StoreConflict("Record ID reused with different bytes")
            elif b["schema"] == "EvidenceStateBatch.v1":
                row = self.db.execute("SELECT version FROM estates WHERE issuer_id=?", (b["issuer_id"],)).fetchone()
                if (row[0] if row else 0) != b["expected_state_version"]:
                    self.db.execute("ROLLBACK")
                    return self._receipt(batch_id, "CONFLICT")
                self.db.execute("INSERT INTO estates VALUES (?,?,?) ON CONFLICT(issuer_id) DO UPDATE SET "
                                "version=excluded.version, doc=excluded.doc",
                                (b["issuer_id"], b["state"]["version"], Document.from_dict(b["state"]).payload))
            else:
                raise ValueError("Unknown batch schema")
            for job in b.get("jobs", []):
                self.db.execute("INSERT OR IGNORE INTO ejobs VALUES (?,?)", (job["job_id"], Document.from_dict(job).payload))
            self.db.execute("INSERT INTO batches VALUES (?,?)", (batch_id, batch.payload))
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise
        return self._receipt(batch_id, "COMMITTED")

    @_locked
    def close(self):
        self.db.close()


class FileArtifacts:
    """Content-addressed bytes under `root` (outside the repository)."""

    def __init__(self, root: str, *, group_readable: bool = False):
        # Shared public evidence is readable by the runtime's supplementary group. Other artifact sinks remain
        # private. NamedTemporaryFile always starts at 0600, regardless of the process umask.
        self.file_mode = 0o640 if group_readable else 0o600
        self.root = Path(root).resolve()
        repo = Path(__file__).resolve().parents[2]
        if self.root.resolve() == repo or repo in self.root.resolve().parents:
            raise ValueError("Artifacts must be stored outside the repository (no source text in Git)")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, digest: str) -> Path:
        require_hash(digest, "artifact address")
        path = self.root / digest[:2] / digest
        if path.parent.is_symlink() or path.is_symlink() or self.root not in path.resolve().parents:
            raise StoreConflict("Artifact path is not confined to its store")
        return path

    @staticmethod
    def _sync_directory(path: Path) -> None:
        if os.name == "nt":  # Windows does not support opening directories for fsync.
            return
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def put(self, content: bytes) -> str:
        digest = sha256_hex(content)
        path = self._path(digest)
        held = self.get(digest)
        if held is not None:
            self._sync_directory(path.parent)
            self._sync_directory(self.root)
            return digest
        path.parent.mkdir(exist_ok=True)
        self._path(digest)  # refuse a pre-existing symlink directory
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".artifact-", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                if os.name != "nt":
                    os.fchmod(handle.fileno(), self.file_mode)
                os.fsync(handle.fileno())
            try:
                # Publish without replacing a competing writer's immutable object.
                os.link(temporary, path)
            except FileExistsError:
                if self.get(digest) != content:
                    raise StoreConflict("Artifact content address collision") from None
            self._sync_directory(path.parent)
            self._sync_directory(self.root)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return digest

    def get(self, digest: str) -> bytes | None:
        path = self._path(digest)
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return None
        if sha256_hex(content) != digest:
            raise StoreConflict("Artifact bytes differ from their content address")
        return content


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
