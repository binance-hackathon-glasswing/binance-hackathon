"""Durable source cursors/records (SQLite) and content-addressed artifacts outside Git (AC-D02/AC-D04).

`commit(batch)` is one SQLite transaction: compare-and-set on the cursor version, then immutable record
inserts. A crash between pages loses nothing committed and duplicates nothing (records are keyed by
record_id; reinserting identical bytes is idempotent, different bytes is an integrity error). The
artifact directory holds the permitted raw item bytes and saved text that model inputs are built from;
it must live outside the repository (F-49 raw inputs; F-61 no private data in Git).
"""

from pathlib import Path
import hashlib
import json
import sqlite3

from larp.contracts import Document


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


class FileArtifacts:
    """Content-addressed bytes under `root` (outside the repository)."""

    def __init__(self, root: str):
        self.root = Path(root)
        repo = Path(__file__).resolve().parents[2]
        if self.root.resolve() == repo or repo in self.root.resolve().parents:
            raise ValueError("Artifacts must be stored outside the repository (no source text in Git)")
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes) -> str:
        digest = hashlib.sha256(content).hexdigest()
        path = self.root / digest[:2] / digest
        if not path.exists():
            path.parent.mkdir(exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(content)
            tmp.replace(path)
        return digest

    def get(self, digest: str) -> bytes | None:
        path = self.root / digest[:2] / digest
        return path.read_bytes() if path.exists() else None


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
