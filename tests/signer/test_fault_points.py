"""IDEA-042 RG2-H01 H3/H6: signer-side fault points F3/F4 and the final-run refusals (real PostgreSQL)."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import Document
from larp.execution import Conflict
from larp.execution_live.store import ExecutionStore
from larp.runtime import faults, preflight
from tests.execution_fixtures import intent
from tests.host_support import ROOT, synthetic_release
from tests.signer.test_service import SigningCase


class Killed(BaseException):
    """Stands in for SIGKILL in-process: no `except Exception` handler can swallow it."""


class SignerFaultPoints(SigningCase):
    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.token = Path(tmp.name) / 'drill.token'

        def kill(pid, sig):
            raise Killed()
        patcher = patch.object(faults, '_kill', kill)
        patcher.start()
        self.addCleanup(patcher.stop)

    def arm(self, point):
        self.token.write_text('armed')
        return patch.dict(os.environ, {faults.POINT_ENV: point, faults.TOKEN_ENV: str(self.token)})

    def test_f3_dies_before_the_signature_and_the_request_is_served_again(self):
        state, attempt = self.authorized()
        self.request(state, attempt)
        with self.arm('F3'), self.assertRaises(Killed):
            self.service.once()
        self.assertEqual(self.signatures(), [])
        self.service = self.signer()  # restarted signer: the token is gone, the request still pending
        with self.arm('F3'):
            self.token.unlink()
            self.assertEqual(self.service.once(), 1)
        self.assertEqual([a for a, _ in self.signatures()], [attempt.attempt_id])
        self.assertEqual(self.refusals(), {})

    def test_f4_dies_after_the_signature_and_never_signs_twice(self):
        state, attempt = self.authorized()
        self.request(state, attempt)
        with self.arm('F4'), self.assertRaises(Killed):
            self.service.once()
        rows = self.signatures()
        self.assertEqual([a for a, _ in rows], [attempt.attempt_id])
        self.service = self.signer()
        self.assertEqual(self.service.once(), 0)  # pending() excludes a signed attempt
        self.assertEqual(self.signatures(), rows)
        recovered = self.executor.recover_signature(state.intent.key, 13).attempts[-1]
        self.assertEqual(recovered.state, 'SIGNED_DURABLE')

    def test_check_signing_run_refuses_an_armed_live_run_first(self):
        run = dict(mode='live', wallet_id=self.wallet, projection=Document.from_dict({}).payload)
        with self.arm('F7b'), self.assertRaisesRegex(Conflict, 'final'):
            ExecutionStore.check_signing_run(run, intent(wallet=self.wallet))
        with self.assertRaisesRegex(Conflict, 'registered signing version'):  # unarmed: the usual checks apply
            ExecutionStore.check_signing_run(run, intent(wallet=self.wallet))


class PreflightRefusal(unittest.TestCase):
    def preflight(self, mode, environ):
        """Run the real preflight verify path on a synthetic release pinning an execution config of `mode`."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        raw = json.dumps(dict(schema='ExecutionService.v1', mode=mode)).encode()
        config = Path(tmp.name) / 'execution.json'
        config.write_bytes(raw)
        root, _ = synthetic_release(tmp.name)
        (root / 'deploy').mkdir(exist_ok=True)
        for lock in ('requirements-runtime.lock', 'requirements-aws.lock'):
            (root / 'deploy' / lock).write_bytes((ROOT / 'deploy' / lock).read_bytes())
        _, manifest = synthetic_release(tmp.name, {'execution': raw})
        out = io.StringIO()
        with patch.dict(os.environ, environ), redirect_stdout(out):
            code = preflight.main(['--manifest', str(manifest), '--root', str(root),
                                   '--service-config', 'execution=' + str(config)])
        return code, json.loads(out.getvalue())['release_verified']

    def test_preflight_refuses_an_armed_live_config_and_a_misconfigured_drill(self):
        token = {faults.TOKEN_ENV: '/run/larp-execution/drill.token'}
        for key in (faults.POINT_ENV, faults.TOKEN_ENV):
            os.environ.pop(key, None)
        self.assertEqual(self.preflight('live', {}), (0, True))
        self.assertEqual(self.preflight('dev', {faults.POINT_ENV: 'F7b', **token}), (0, True))
        for mode, environ in (('live', {faults.POINT_ENV: 'F7b', **token}),
                              ('dev', {faults.POINT_ENV: 'F6', **token}),
                              ('dev', {faults.POINT_ENV: 'F7b', faults.TOKEN_ENV: 'relative'})):
            with self.subTest(mode=mode, environ=environ):
                self.assertEqual(self.preflight(mode, environ), (1, False))
