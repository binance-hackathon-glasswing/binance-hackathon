"""IDEA-047 R3/R4: the runtime reads the poller's evidence store read-only; a refused evidence start stops its unit."""
from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import Document
from larp.sources import live
from larp.sources.store import FileArtifacts, SQLiteEvidenceStore, StoreConflict
from tests.host_support import synthetic_release
from tests.runtime.test_host_units import directives, value
from tests.sources.test_live import AGENT, unset_live_parameter


def state_batch(batch_id, version):
    return Document.from_dict({"schema": "EvidenceStateBatch.v1", "batch_id": batch_id, "issuer_id": "ISSUER",
                               "expected_state_version": version - 1,
                               "state": {"version": version, "status": "CLEAR"}, "jobs": []})


class ReadOnlyEvidenceStore(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = str(Path(tmp.name) / "evidence.sqlite")
        self.writer = SQLiteEvidenceStore(self.path, journal_mode='DELETE')
        self.addCleanup(self.writer.close)

    def test_r3_reader_sees_committed_batches_of_a_live_shared_writer(self):
        self.assertEqual(self.writer.commit(state_batch("b1", 1)).read()["status"], "COMMITTED")
        reader = SQLiteEvidenceStore(self.path, read_only=True)
        self.addCleanup(reader.close)
        self.assertEqual(reader.read_state("ISSUER").read()["version"], 1)
        # The writer keeps going while the reader is open; the reader sees each new commit.
        self.assertEqual(self.writer.commit(state_batch("b2", 2)).read()["status"], "COMMITTED")
        self.assertEqual(reader.read_state("ISSUER").read()["version"], 2)
        self.assertEqual(self.writer.db.execute("PRAGMA journal_mode").fetchone()[0], "delete")

    def test_r3_reader_refuses_every_write(self):
        self.writer.commit(state_batch("b1", 1))
        reader = SQLiteEvidenceStore(self.path, read_only=True)
        self.addCleanup(reader.close)
        with self.assertRaises(StoreConflict):
            reader.commit(state_batch("b2", 2))
        for sql in ("INSERT INTO ejobs VALUES ('j', x'00')", "DELETE FROM estates",
                    "CREATE TABLE extra (x)", "PRAGMA journal_mode=WAL"):
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

    def test_r15_legacy_wal_reader_refuses_before_sidecar_creation_and_writer_migrates(self):
        path = str(Path(self.path).with_name('legacy.sqlite'))
        legacy = SQLiteEvidenceStore(path)
        legacy.commit(state_batch('b1', 1))
        legacy.close()
        self.assertFalse(Path(path + '-wal').exists())
        with self.assertRaisesRegex(sqlite3.OperationalError, 'migration'):
            SQLiteEvidenceStore(path, read_only=True)
        self.assertFalse(Path(path + '-wal').exists())
        self.assertFalse(Path(path + '-shm').exists())
        writer = SQLiteEvidenceStore(path, journal_mode='DELETE')
        self.assertEqual(writer.read_state('ISSUER').read()['version'], 1)
        writer.close()
        reader = SQLiteEvidenceStore(path, read_only=True)
        self.addCleanup(reader.close)
        writer = SQLiteEvidenceStore(path, journal_mode='DELETE')
        self.addCleanup(writer.close)
        writer.commit(state_batch('b2', 2))
        self.assertEqual(reader.read_state('ISSUER').read()['version'], 2)
        self.assertFalse(Path(path + '-wal').exists())
        self.assertFalse(Path(path + '-shm').exists())

    def test_r15_private_wal_store_still_supports_an_explicit_private_reader(self):
        path = str(Path(self.path).with_name('private.sqlite'))
        writer = SQLiteEvidenceStore(path)
        self.addCleanup(writer.close)
        writer.commit(state_batch('private', 1))
        reader = SQLiteEvidenceStore(path, read_only=True, journal_mode='WAL')
        self.addCleanup(reader.close)
        self.assertEqual(writer.db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        self.assertEqual(reader.read_state('ISSUER').read()['version'], 1)

    def test_r15_migration_preserves_committed_data_left_in_wal_after_a_crash(self):
        path = str(Path(self.path).with_name('crashed-writer.sqlite'))
        source = '''
import os, sys
from larp.contracts import Document
from larp.sources.store import SQLiteEvidenceStore
store = SQLiteEvidenceStore(sys.argv[1])
store.commit(Document.from_dict({'schema':'EvidenceStateBatch.v1', 'batch_id':'crash', 'issuer_id':'ISSUER',
                                 'expected_state_version':0, 'state':{'version':1}, 'jobs':[]}))
os._exit(0)
'''
        subprocess.run([sys.executable, '-c', source, path], cwd=Path(__file__).resolve().parents[2],
                       capture_output=True, check=True, timeout=15)
        self.assertTrue(Path(path + '-wal').exists())
        wal = Path(path + '-wal').read_bytes()
        with self.assertRaisesRegex(sqlite3.OperationalError, 'migration'):
            SQLiteEvidenceStore(path, read_only=True)
        self.assertEqual(Path(path + '-wal').read_bytes(), wal)
        writer = SQLiteEvidenceStore(path, journal_mode='DELETE')
        try:
            self.assertEqual(writer.read_state('ISSUER').read()['version'], 1)
        finally:
            writer.close()
        reader = SQLiteEvidenceStore(path, read_only=True)
        try:
            self.assertEqual(reader.read_state('ISSUER').read()['version'], 1)
        finally:
            reader.close()

    def test_r15_live_runner_wires_the_shared_writer_in_delete_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {'LARP_SEC_USER_AGENT': AGENT, 'LARP_ARTIFACT_ROOT': directory}
            # Exercise real store wiring only; live terms are an explicitly open deployment prerequisite.
            # No source port is called in this synthetic constructor test.
            with patch.object(live, 'preflight', return_value=[]):
                runner = live.build_runner(env, config_mode='development', edgar_interval_ms=60000,
                                           commit='b' * 40)
            try:
                self.assertEqual(runner.edgar.store.db.execute('PRAGMA journal_mode').fetchone()[0], 'delete')
                reader = SQLiteEvidenceStore(str(Path(directory) / 'evidence.sqlite'), read_only=True)
                try:
                    self.assertEqual(reader.records('ISSUER'), ())
                finally:
                    reader.close()
            finally:
                runner.edgar.store.close()
                runner.sources.store.db.close()


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
        # LV-01 committed the live values; one unset live parameter must still refuse the start (DR-12).
        env = {"LARP_SEC_USER_AGENT": AGENT, "LARP_ARTIFACT_ROOT": str(self.tmp / "artifacts")}
        with unset_live_parameter():
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
        self.assertEqual(value(runtime, "ReadWritePaths"), [])
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


@unittest.skipIf(os.name == 'nt', 'POSIX artifact permissions')
class SharedArtifacts(unittest.TestCase):
    def test_r12_public_artifacts_are_group_readable_but_private_stores_stay_private(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = os.umask(0o007)
            try:
                for shared, expected in ((False, 0o600), (True, 0o640)):
                    artifacts = FileArtifacts(str(Path(directory) / str(shared)), group_readable=shared)
                    saved = artifacts.put(b'synthetic public filing')
                    path = artifacts._path(saved)
                    self.assertEqual(path.stat().st_mode & 0o777, expected)
                    self.assertEqual(artifacts.get(saved), b'synthetic public filing')
                    self.assertEqual(artifacts.put(b'synthetic public filing'), saved)
                    self.assertEqual(path.stat().st_mode & 0o777, expected)
            finally:
                os.umask(previous)


if __name__ == "__main__":
    unittest.main()
