"""IDEA-047 V01: the evidence runner on a host verifies its release bundle instead of a git checkout."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.sources import live
from tests.host_support import BUILD, synthetic_release


class Runner:
    log = type('Log', (), dict(path='polls.jsonl'))()

    def run(self, until):
        return 0


class ReleaseMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root, self.manifest = synthetic_release(self.tmp.name)

    def test_v01_verified_release_names_the_build(self):
        self.assertEqual(live.release_state(str(self.manifest), str(self.root)),
                         dict(commit=BUILD, dirty=False, pushed=True))

    def test_v01_unverified_release_is_refused(self):
        with self.assertRaises(SystemExit):
            live.release_state(str(self.manifest), None)
        (self.root / 'larp/runtime/operations.py').write_text('# changed after the build\n')
        with self.assertRaises(SystemExit):
            live.release_state(str(self.manifest), str(self.root))

    def test_v01_run_uses_the_release_and_never_git(self):
        seen = {}

        def build_runner(env, *, config_mode, edgar_interval_ms, commit):
            seen['commit'] = commit
            return Runner()
        with patch.object(live, 'git_state', side_effect=AssertionError('git used')), \
                patch.object(live, 'build_runner', build_runner), redirect_stdout(io.StringIO()):
            code = live.main(['run', '--hours', '0', '--release-manifest', str(self.manifest),
                              '--release-root', str(self.root)], env={})
        self.assertEqual((code, seen['commit']), (0, BUILD))

    def test_v01_git_path_is_unchanged(self):
        with patch.object(live, 'git_state', return_value=dict(commit='c' * 40, dirty=True, pushed=False)):
            with self.assertRaises(SystemExit):
                live.main(['run', '--hours', '0'], env={})


if __name__ == '__main__':
    unittest.main()
