"""IDEA-047 R13: preflight refusal is the main-process exit status; success replaces the process."""
import sys
import unittest
from unittest.mock import Mock, patch

from larp.runtime import launch


class Launch(unittest.TestCase):
    ARGS = ['--manifest', '/synthetic/release.json', '--root', '/synthetic', '--', '-m', 'larp.sources.live', 'run']

    def test_refusal_exits_4_without_executing_a_service(self):
        execute = Mock()
        with patch.object(launch.preflight, 'main', return_value=1):
            self.assertEqual(launch.main(self.ARGS, execv=execute), 4)
        execute.assert_not_called()

    def test_success_execs_same_interpreter_and_preserves_service_arguments(self):
        execute = Mock()
        with patch.object(launch.preflight, 'main', return_value=0) as check:
            self.assertEqual(launch.main(self.ARGS, execv=execute), 0)
        check.assert_called_once_with(self.ARGS[:4])
        execute.assert_called_once_with(sys.executable, [sys.executable, *self.ARGS[5:]])

    def test_invalid_launch_and_exec_failure(self):
        for argv in ([], ['--'], self.ARGS[:4], self.ARGS[:5]):
            with self.subTest(argv=argv):
                self.assertEqual(launch.main(argv, execv=Mock()), 4)
        with patch.object(launch.preflight, 'main', return_value=0):
            self.assertEqual(launch.main(self.ARGS, execv=Mock(side_effect=OSError)), 1)
