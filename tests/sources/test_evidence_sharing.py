"""IDEA-047 R3/R4: the runtime reads the poller's evidence store read-only; a refused evidence start stops its unit."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import Document
from larp.sources import live
from larp.sources.store import SQLiteEvidenceStore, StoreConflict
from tests.host_support import synthetic_release
from tests.runtime.test_host_units import directives, value
from tests.sources.test_live import AGENT


def state_batch(batch_id, version):
    return Document.from_dict({"schema": "EvidenceStateBatch.v1", "batch_id": batch_id, "issuer_id": "ISSUER",
                               "expected_state_version": version - 1,
                               "state": {"version": version, "status": "CLEAR"}, "jobs": []})


class ReadOnlyEvidenceStore(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = str(Path(tmp.name) / "evidence.sqlite")
        self.writer = SQLiteEvidenceStore(self.path)
        self.addCleanup(self.writer.close)

    def test_r3_reader_sees_committed_batches_of_a_live_wal_writer(self):
        self.assertEqual(self.writer.commit(state_batch("b1", 1)).read()["status"], "COMMITTED")
        reader = SQLiteEvidenceStore(self.path, read_only=True)
        self.addCleanup(reader.close)
        self.assertEqual(reader.read_state("ISSUER").read()["version"], 1)
        # The writer keeps going while the reader is open; the reader sees each new commit.
        self.assertEqual(self.writer.commit(state_batch("b2", 2)).read()["status"], "COMMITTED")
        self.assertEqual(reader.read_state("ISSUER").read()["version"], 2)
        self.assertEqual(self.writer.db.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_r3_reader_refuses_every_write(self):
        self.writer.commit(state_batch("b1", 1))
        reader = SQLiteEvidenceStore(self.path, read_only=True)
        self.addCleanup(reader.close)
        with self.assertRaises(StoreConflict):
            reader.commit(state_batch("b2", 2))
        for sql in ("INSERT INTO ejobs VALUES ('j', x'00')", "DELETE FROM estates",
                    "CREATE TABLE extra (x)", "PRAGMA journal_mode=DELETE"):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.OperationalError):
                reader.db.execute(sql).fetchall()
        self.assertEqual(self.writer.read_state("ISSUER").read()["version"], 1)

    def test_r3_reader_never_creates_a_store(self):
        missing = str(Path(self.path).with_name("absent.sqlite"))
        with self.assertRaises(sqlite3.OperationalError):
            SQLiteEvidenceStore(missing, read_only=True)
        self.assertFalse(Path(missing).exists())
        with self.assertRaises(ValueError):
            SQLiteEvidenceStore(":memory:", read_only=True)


class RefusedStart(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root, self.manifest = synthetic_release(tmp.name)

    def run_cli(self, argv, env):
        err = io.StringIO()
        with patch.object(live, "git_state", side_effect=AssertionError("git used")), \
                redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = live.main(argv, env=env)
        return code, err.getvalue()

    def test_r4_live_preflight_refusal_exits_4_with_its_reasons(self):
        # The committed live configuration still has null live parameters and terms hashes (DR-12, GAP-23).
        env = {"LARP_SEC_USER_AGENT": AGENT, "LARP_ARTIFACT_ROOT": str(self.tmp / "artifacts")}
        self.assertTrue(live.preflight(env))
        code, err = self.run_cli(["run", "--hours", "0", "--release-manifest", str(self.manifest),
                                  "--release-root", str(self.root)], env)
        self.assertEqual(code, 4)
        self.assertIn("Live preflight refused", err)
        self.assertIn("INTELLIGENCE_CONFIG_REFUSED:live", err)
        self.assertFalse((self.tmp / "artifacts" / "evidence.sqlite").exists())

    def test_r4_unverified_or_incomplete_release_exits_4(self):
        (self.root / "larp/runtime/operations.py").write_text("# changed after the build\n")
        for argv in (["--release-manifest", str(self.manifest), "--release-root", str(self.root)],
                     ["--release-manifest", str(self.manifest)]):
            with self.subTest(argv=argv):
                code, err = self.run_cli(["run", "--hours", "0", *argv], {})
                self.assertEqual(code, 4)
                self.assertIn("release", err)

    def test_r4_other_commands_keep_their_exit_codes(self):
        self.assertEqual(self.run_cli(["preflight"], {})[0], 1)


class EvidenceUnits(unittest.TestCase):
    def test_r3_evidence_state_is_shared_with_the_runtime_group_only(self):
        evidence, runtime = directives("larp-evidence"), directives("larp-runtime")
        self.assertEqual(value(evidence, "StateDirectoryMode"), ["0770"])
        self.assertEqual(value(evidence, "UMask"), ["0007"])
        self.assertEqual(value(runtime, "SupplementaryGroups"), ["larp-evidence"])
        self.assertEqual(value(runtime, "ReadWritePaths"), ["-/var/lib/larp-evidence"])
        self.assertEqual(value(runtime, "UMask"), ["0077"])
        for unit in ("larp-signer", "larp-execution", "larp-uploader", "larp-archive"):
            d = directives(unit)
            with self.subTest(unit=unit):
                self.assertEqual(value(d, "SupplementaryGroups"), [])
                self.assertFalse(any("larp-evidence" in line for line in d))

    def test_r4_a_refused_evidence_start_is_not_restarted(self):
        d = directives("larp-evidence")
        self.assertEqual(value(d, "RestartPreventExitStatus"), ["4"])
        self.assertIn("Restart=always", d)  # the clean exit after each 24 h run still restarts


if __name__ == "__main__":
    unittest.main()
