import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest

from larp.contracts import ContractError
from larp.runtime.worker import IsolatedWorker,ServiceLanes,WorkerFailure
from larp.runtime.release import capabilities,redact,verify_manifest
from larp.storage.postgres import doc
from tests.support import request


class Release(unittest.TestCase):
    def test_manifest_mode_and_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'code'; path.write_bytes(b'code')
            manifest=doc(dict(schema='ReleaseManifest.v1',build_id='synthetic',files={'code':hashlib.sha256(b'code').hexdigest()}))
            for mode in ('offline','paper'):
                result=capabilities(doc(dict(mode=mode)),manifest,directory).read()
                self.assertFalse(result['signing']); self.assertFalse(result['broadcast'])
            with self.assertRaises(ContractError): capabilities(doc(dict(mode='live')),manifest,directory)
            path.write_bytes(b'changed')
            with self.assertRaises(ContractError): verify_manifest(manifest,directory)
        self.assertEqual({'api_key':'[REDACTED]','message':'value=[REDACTED]'},
                         redact({'api_key':'secret','message':'value=secret'},['secret']))

    def test_independent_service_lanes(self):
        started=threading.Event(); release=threading.Event(); safety=threading.Event()
        lanes=ServiceLanes()
        try:
            lanes.submit('evidence',lambda:(started.set(),release.wait(2)))
            self.assertTrue(started.wait(1))
            self.assertFalse(lanes.submit('evidence',lambda:None))
            lanes.submit('safety',safety.set)
            self.assertTrue(safety.wait(.5))
        finally:
            release.set(); lanes.close()


@unittest.skipUnless(sys.platform=='linux' and shutil.which('bwrap'),'Linux bubblewrap required')
class Sandbox(unittest.TestCase):
    def test_no_home_network_or_inherited_credentials(self):
        os.environ['LARP_SENTINEL_SECRET']='must-not-cross'
        try:
            value=IsolatedWorker(timeout=3).call('larp.runtime.fixtures:inspect_capabilities',doc({})).read()
        finally:
            del os.environ['LARP_SENTINEL_SECRET']
        # Python locale coercion and bubblewrap's cwd are nonsecret runtime metadata.
        self.assertLessEqual(set(value['environment']),{'LC_CTYPE','PWD'})
        self.assertFalse(value['home_exists']); self.assertFalse(value['env_exists']); self.assertFalse(value['network'])

    def test_hang_exception_and_input_budget(self):
        with self.assertRaises(WorkerFailure): IsolatedWorker(timeout=.1).call('larp.runtime.fixtures:hang',doc({}))
        with self.assertRaises(WorkerFailure): IsolatedWorker().call('larp.runtime.fixtures:fail',doc({}))
        with self.assertRaises(WorkerFailure): IsolatedWorker(max_bytes=1).call('larp.runtime.fixtures:assess',request())

    def test_valid_assessment(self):
        result=IsolatedWorker(timeout=3).call('larp.runtime.fixtures:assess',request())
        self.assertEqual('AssessmentResult.v1',result.read()['schema'])
