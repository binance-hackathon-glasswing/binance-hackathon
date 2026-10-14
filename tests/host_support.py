"""Synthetic verified releases for host service CLI tests (IDEA-047). Never a registered build."""
import hashlib
from pathlib import Path

from larp.contracts import Document
from larp.runtime.preflight import release_files
from larp.runtime.register import DEVIATIONS, SERVICES, load_register

ROOT = Path(__file__).resolve().parents[1]
BUILD = 'b' * 40


def synthetic_release(directory, service_configs=None, build_id=BUILD):
    """A minimal release root and its manifest file; returns (root, manifest_path)."""
    root = Path(directory) / 'release'
    for name in ('larp/runtime/operations.py', SERVICES, DEVIATIONS, 'docs/proposal/proposal_answers.md'):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes((ROOT / name).read_bytes())
    files = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in release_files(root)}
    evidence = dict(schema='RegistrationEvidence.v1', evidence_ref='synthetic-only', build_id=build_id,
                    repository='synthetic')
    manifest = dict(schema='ReleaseManifest.v1', build_id=build_id, repository='synthetic', remote_verified=True,
                    services=['synthetic'], files=files, registration_evidence=evidence,
                    release_register=load_register(root))
    if service_configs is not None:
        manifest['service_configs_sha256'] = {name: hashlib.sha256(raw).hexdigest()
                                              for name, raw in service_configs.items()}
    path = Path(directory) / 'release.json'
    path.write_bytes(Document.from_dict(manifest).payload)
    return root, path
