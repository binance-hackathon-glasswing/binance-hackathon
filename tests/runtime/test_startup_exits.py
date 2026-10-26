"""IDEA-108 F2 (EX-1/EX-2): which start-up errors refuse for good (exit 4) and which are transient (exit 1)."""
import errno
import json
import socket
import unittest

import requests

from larp.contracts import ContractError
from larp.runtime.exits import refuses_start


class StartupExits(unittest.TestCase):
    def test_ex1_transient_os_errors_do_not_refuse(self):
        for error in (ConnectionError('c'), ConnectionResetError('r'), ConnectionRefusedError('r'),
                      BrokenPipeError('b'), TimeoutError('t'), socket.gaierror('dns'), OSError(errno.EIO, 'io'),
                      requests.exceptions.ConnectionError('c'), requests.exceptions.Timeout('t')):
            with self.subTest(error=type(error).__name__):
                self.assertFalse(refuses_start(error))

    def test_ex2_contract_value_and_file_errors_refuse(self):
        for error in (ContractError('c'), ValueError('v'), json.JSONDecodeError('m', '{', 0),
                      FileNotFoundError('f'), PermissionError('p'), IsADirectoryError('d'), NotADirectoryError('n')):
            with self.subTest(error=type(error).__name__):
                self.assertTrue(refuses_start(error))
