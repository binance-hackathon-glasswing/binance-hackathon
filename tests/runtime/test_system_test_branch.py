"""IDEA-049 PR21-R4: review branches retain the system runner's safety gates."""
import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('review_system_runner', ROOT / 'tools/system_test.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class SystemTestBranchGuard(unittest.TestCase):
    def preflight_error(self, branch, *, dirty=False, pushed=True):
        commit = 'a' * 40

        def fake_git(*args):
            return {
                ('branch', '--show-current'): branch,
                ('rev-parse', 'HEAD'): commit,
                ('status', '--porcelain'): ' M file.py' if dirty else '',
                ('rev-parse', '--verify', 'origin/' + branch): commit if pushed else 'b' * 40,
            }[args]

        error = io.StringIO()
        with patch.object(runner, 'git', side_effect=fake_git), \
                patch.object(runner.sys, 'argv', ['system_test.py', '--system-only']), \
                patch.dict(runner.os.environ, {}, clear=True), \
                patch.object(runner.subprocess, 'run') as child, \
                contextlib.redirect_stderr(error), self.assertRaises(SystemExit) as stopped:
            runner.main()
        self.assertEqual(stopped.exception.code, 2)
        child.assert_not_called()
        return error.getvalue()

    def test_each_clean_pushed_review_section_reaches_disposable_database_guard(self):
        for section in 'abcd':
            with self.subTest(section=section):
                self.assertIn('Set a disposable local larp_test database',
                    self.preflight_error(f'review/final-{section}-20261014'))

    def test_existing_system_branch_still_reaches_disposable_database_guard(self):
        self.assertIn('Set a disposable local larp_test database',
            self.preflight_error('codex/system-testing-20261012'))

    def test_dirty_review_branch_stays_refused(self):
        self.assertIn('Use a clean', self.preflight_error('review/final-d-20261014', dirty=True))

    def test_unpublished_review_head_stays_refused(self):
        self.assertIn('Commit and push the tested head first',
            self.preflight_error('review/final-c-20261014', pushed=False))

    def test_unrelated_or_malformed_review_branches_stay_refused(self):
        for branch in ('main', 'codex/final-review-prompts-20261014', 'review/final-x-20261014',
                       'review/final-a-', 'review/final-a-20261014-extra', 'review/final-a-2026101',
                       'review/final-a-abcdefgh'):
            with self.subTest(branch=branch):
                self.assertIn('Use a clean', self.preflight_error(branch))


if __name__ == '__main__':
    unittest.main()
