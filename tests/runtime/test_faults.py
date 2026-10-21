"""IDEA-042 RG2-H01 H1/H3/H4: the fault hook is inert by default, fires once, and final runs refuse it."""
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import ContractError
from larp.runtime import faults


class Killed(BaseException):
    """Stands in for SIGKILL: not an Exception, so no service handler can swallow it."""


class FaultPoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.token = Path(self.tmp.name) / 'drill.token'
        self.token.write_text('F7b')
        self.kills = []

        def kill(pid, sig):
            self.kills.append((pid, sig))
            raise Killed()
        patcher = patch.object(faults, '_kill', kill)
        patcher.start()
        self.addCleanup(patcher.stop)

    def env(self, name='F7b', token=None):
        return {faults.POINT_ENV: name, faults.TOKEN_ENV: str(self.token if token is None else token)}

    def test_inert_without_the_environment_and_touches_no_file(self):
        with patch.object(os, 'rename', side_effect=AssertionError('file system touched')), \
                patch.object(os.path, 'isabs', side_effect=AssertionError('file system touched')):
            for name in sorted(faults.POINTS):
                faults.point(name, environ={})
        self.assertEqual(self.kills, [])

    def test_inert_for_another_point_a_missing_or_relative_token(self):
        faults.point('F5', environ=self.env('F7b'))
        faults.point('F7b', environ=self.env(token=self.token.with_name('absent')))
        faults.point('F7b', environ=self.env(token='drill.token'))
        faults.point('F7b', environ={faults.POINT_ENV: 'F7b'})
        self.assertEqual(self.kills, [])
        self.assertTrue(self.token.exists())

    def test_fires_exactly_once_with_sigkill_and_consumes_the_token(self):
        with self.assertRaises(Killed):
            faults.point('F7b', environ=self.env())
        self.assertEqual(self.kills, [(os.getpid(), signal.SIGKILL)])
        self.assertFalse(self.token.exists())
        self.assertTrue(self.token.with_name('drill.token.consumed').exists())
        faults.point('F7b', environ=self.env())  # the restarted process: no token left
        self.assertEqual(len(self.kills), 1)

    def test_unknown_point_in_code_is_a_programming_error(self):
        with self.assertRaises(ValueError):
            faults.point('F6', environ={})


class FinalRefusal(unittest.TestCase):
    def test_check(self):
        token = {faults.TOKEN_ENV: '/run/larp/drill.token'}
        for mode in ('offline', 'dev', 'live'):
            faults.check(mode, environ={})
        faults.check('dev', environ={faults.POINT_ENV: 'F8', **token})
        for environ, mode, reason in [({faults.POINT_ENV: 'F8', **token}, 'live', 'final'),
                                      ({faults.POINT_ENV: 'F9', **token}, 'dev', 'Unknown'),
                                      ({faults.POINT_ENV: 'F8'}, 'dev', 'absolute'),
                                      ({faults.POINT_ENV: 'F8', faults.TOKEN_ENV: 'rel'}, 'dev', 'absolute')]:
            with self.subTest(environ=environ, mode=mode), self.assertRaisesRegex(ContractError, reason):
                faults.check(mode, environ=environ)


if __name__ == '__main__':
    unittest.main()
