"""IDEA-042 4.7: deployed prompts and image instructions are version-bound."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from larp.contracts import ContractError, Document
from larp.runtime.preflight import release_files, verify_release
from larp.runtime.register import SERVICES, DEVIATIONS, load_register

class ManifestBehaviorInputs(unittest.TestCase):
    def test_prompt_or_image_change_invalidates_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=Path(__file__).resolve().parents[2]
            for name in (SERVICES,DEVIATIONS,'docs/proposal/proposal_answers.md'):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((source/name).read_bytes())
            for name,data in {'larp/runtime/operations.py':b'# synthetic code',
                              'config/intelligence/prompts/assessor.v2.txt':b'synthetic prompt',
                              'deploy/Dockerfile':b'FROM synthetic'}.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            files={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in release_files(root)}
            manifest=Document.from_dict(dict(schema='ReleaseManifest.v1',build_id='a'*40,repository='synthetic',
                remote_verified=True,services=['synthetic'],files=files,release_register=load_register(root),
                registration_evidence=dict(schema='RegistrationEvidence.v1',evidence_ref='synthetic',
                                           build_id='a'*40,repository='synthetic')))
            verify_release(manifest,root)
            for name in ('config/intelligence/prompts/assessor.v2.txt','deploy/Dockerfile'):
                self.assertIn(name,files)
                original=(root/name).read_bytes();(root/name).write_bytes(original+b' changed')
                with self.assertRaises(ContractError):verify_release(manifest,root)
                (root/name).write_bytes(original)
