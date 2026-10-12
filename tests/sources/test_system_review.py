"""IDEA-044 artifact confinement, durable writes, coverage reports and live revision guards."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from larp.intelligence.common import IntelligenceError, sha256_hex
from larp.intelligence.tools import PortEvidenceReader, ToolError
from larp.sources import live
from larp.sources.store import FileArtifacts, StoreConflict
from larp.sources.rights import filter_item


class Artifacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "artifacts"
        self.artifacts = FileArtifacts(str(self.root))

    def test_addresses_cannot_select_arbitrary_files(self):
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_bytes(b"synthetic private bytes")
        for digest in (str(outside), "../outside.txt", "ab/../../outside.txt", "A" * 64, "", None):
            with self.subTest(digest=digest), self.assertRaises(IntelligenceError):
                self.artifacts.get(digest)

    def test_corruption_is_reported_by_both_read_and_idempotent_write(self):
        content = b"original permitted bytes"
        digest = self.artifacts.put(content)
        path = self.root / digest[:2] / digest
        path.write_bytes(b"corrupt")
        with self.assertRaises(StoreConflict):
            self.artifacts.get(digest)
        with self.assertRaises(StoreConflict):
            self.artifacts.put(content)
        self.assertEqual(path.read_bytes(), b"corrupt")  # corruption is reported, never silently rewritten
        with self.assertRaises(ToolError):
            PortEvidenceReader(None, self.artifacts).text(digest)

    def test_symlinks_cannot_redirect_read_or_write(self):
        content = b"bytes with the expected hash"
        digest = sha256_hex(content)
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / digest).write_bytes(content)
        try:
            (self.root / digest[:2]).symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("OS does not permit unprivileged symlink creation")
        with self.assertRaises(StoreConflict):
            self.artifacts.get(digest)
        with self.assertRaises(StoreConflict):
            self.artifacts.put(content)
        (self.root / digest[:2]).unlink()
        (self.root / digest[:2]).mkdir()
        (self.root / digest[:2] / digest).symlink_to(outside / digest)
        with self.assertRaises(StoreConflict):
            self.artifacts.get(digest)

    def test_concurrent_identical_writes_are_atomic_and_idempotent(self):
        content = b"synthetic exact artifact" * 1024
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(self.artifacts.put, [content] * 32))
        self.assertEqual(set(results), {sha256_hex(content)})
        self.assertEqual(self.artifacts.get(results[0]), content)
        self.assertEqual([p for p in self.root.rglob("*") if p.is_file()],
                         [self.root / results[0][:2] / results[0]])

    def test_bytes_are_fsynced_before_put_completes(self):
        with patch("larp.sources.store.os.fsync", wraps=__import__("os").fsync) as sync:
            digest = self.artifacts.put(b"durable content")
        self.assertGreaterEqual(sync.call_count, 1)
        self.assertEqual(self.artifacts.get(digest), b"durable content")
        with patch.object(self.artifacts, "_sync_directory", wraps=self.artifacts._sync_directory) as sync:
            self.assertEqual(self.artifacts.put(b"durable content"), digest)
        self.assertEqual([call.args[0] for call in sync.call_args_list], [self.root / digest[:2], self.root])


class CoverageReports(unittest.TestCase):
    def lines(self, **update):
        return [dict(target="edgar:issuer", started_ms=t, finished_ms=t, cadence_ms=100,
                     status="OK", **update) for t in range(0, 1001, 100)]

    def report(self, lines):
        return live.gap_report(lines, cadences={"edgar:issuer": 100}, start_ms=0, end_ms=1000, required_ms=1000)

    def test_incomplete_coverage_cannot_satisfy_readiness(self):
        for change in ({"truncated": True}, {"rejected": 1}, {"retry_pending": 1}, {"dead_letter": 1},
                       {"malformed_rows": 1}, {"unexpected_forms": 1}, {"rejected_future": 1},
                       {"coverage_complete": False}):
            with self.subTest(change=change):
                report = self.report(self.lines(**change))
                self.assertEqual(report["verdict"], "FAIL")
                self.assertEqual(report["targets"]["edgar:issuer"]["successful_polls"], 0)
        partial = [dict(line, status="PARTIAL_HISTORY") for line in self.lines()]
        self.assertEqual(self.report(partial)["verdict"], "FAIL")
        self.assertEqual(self.report(self.lines())["verdict"], "PASS")

    def test_completion_outside_window_cannot_close_its_gaps(self):
        lines = [dict(line, finished_ms=1001) for line in self.lines()]
        self.assertEqual(self.report(lines)["verdict"], "FAIL")


class LiveRevisionGuard(unittest.TestCase):
    def test_dirty_flag_has_no_bypass_and_push_must_be_verified(self):
        for state in ({"dirty": True, "pushed": True}, {"dirty": False, "pushed": False}, {"dirty": False}):
            for allow in (True, False):
                with self.subTest(state=state, allow=allow), self.assertRaises(SystemExit):
                    live.require_committed(state, allow_dirty=allow)
        live.require_committed({"dirty": False, "pushed": True}, allow_dirty=False)

    def test_remote_head_is_checked_without_returning_remote_credentials(self):
        head = "a" * 40
        def run(command, **kwargs):
            args = command[1:]
            if args == ["rev-parse", "HEAD"]:
                result = head
            elif args == ["status", "--porcelain"]:
                result = ""
            elif args == ["symbolic-ref", "--quiet", "--short", "HEAD"]:
                result = "codex/test"
            elif args == ["config", "--get", "branch.codex/test.remote"]:
                result = "origin"
            elif args == ["config", "--get", "branch.codex/test.merge"]:
                result = "refs/heads/codex/test"
            else:
                self.assertEqual(args, ["ls-remote", "--exit-code", "origin", "refs/heads/codex/test"])
                result = head + "\trefs/heads/codex/test\n"
            return subprocess.CompletedProcess(command, 0, stdout=result, stderr="not returned")
        with patch("larp.sources.live.subprocess.run", side_effect=run):
            self.assertEqual(live.git_state(), {"commit": head, "dirty": False, "pushed": True})

    def test_unreachable_remote_fails_closed(self):
        def run(command, **kwargs):
            if command[1] == "symbolic-ref":
                raise subprocess.CalledProcessError(1, command, stderr="sensitive synthetic error")
            return subprocess.CompletedProcess(command, 0, stdout="a" * 40 if command[1] == "rev-parse" else "")
        with patch("larp.sources.live.subprocess.run", side_effect=run):
            state = live.git_state()
        self.assertFalse(state["pushed"])
        self.assertNotIn("sensitive", str(state))


class RightsEntities(unittest.TestCase):
    def test_entity_encoded_notices_are_excluded_like_literal_notices(self):
        for notice in ("&copy; 2026 Example", "&#169; 2026 Example", "&#xA9; 2026 Example",
                       "all&nbsp;rights&nbsp;reserved", "copy<span>right</span> 2026 Example",
                       "all&#x200b; rights reserved", "copy&#x200b;right 2026 Example"):
            with self.subTest(notice=notice):
                self.assertEqual(filter_item(notice, "<p>Release</p>")[2], "THIRD_PARTY_RIGHTS")
                self.assertEqual(filter_item("Release", f"<p>{notice}</p>")[2], "THIRD_PARTY_RIGHTS")
                body, exclusions, error = filter_item("Release", f"<p>Own permitted text</p><p>{notice}</p>")
                self.assertIsNone(error)
                self.assertIn("Own permitted text", body)
                self.assertNotIn(notice, body)
                self.assertIn("THIRD_PARTY_PARAGRAPHS_REMOVED:1", exclusions)

    def test_entity_encoded_item_restriction_is_refused(self):
        self.assertEqual(filter_item("Release", "<p>Text may&nbsp;not&nbsp;be&nbsp;reproduced</p>")[2],
                         "THIRD_PARTY_RIGHTS")
