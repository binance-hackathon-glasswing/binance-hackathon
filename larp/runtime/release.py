"""Fail-closed release inspection. This increment has no live signer capability."""

import hashlib
from pathlib import Path
import re

from larp.contracts import ContractError,Document

SECRET_KEYS=re.compile(r'(secret|password|private.?key|mnemonic|authorization|api.?key|access.?token|refresh.?token)',re.I)


def redact(value,secrets=()):
    if isinstance(value,dict):
        return {k:'[REDACTED]' if SECRET_KEYS.search(k) else redact(v,secrets) for k,v in value.items()}
    if isinstance(value,list):
        return [redact(v,secrets) for v in value]
    if isinstance(value,str):
        for secret in secrets:
            if secret:
                value=value.replace(secret,'[REDACTED]')
    return value


def verify_manifest(manifest,root):
    m=manifest.read(); root=Path(root).resolve()
    if m.get('schema')!='ReleaseManifest.v1' or not m.get('files'):
        raise ContractError('Invalid release manifest')
    for filename,expected in m['files'].items():
        path=(root/filename).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ContractError('Manifest path escaped or is missing')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ContractError('Manifest hash mismatch')
    return m


def capabilities(config,manifest,root):
    """Only reviewed offline/paper capability bundles can currently be created."""
    c=config.read(); m=verify_manifest(manifest,root)
    mode=c.get('mode','offline')
    if mode not in ('offline','paper','dev','live'):
        raise ContractError('Unknown runtime mode')
    if mode in ('dev','live'):
        required=('database','artifact_root','backup_destination','anchor_destination','retention_days',
                  'registered_wallet','registered_repository','registered_build','policy_profile',
                  'risk_profile','scored_start_ms','scored_end_ms','funding_evidence','gas_evidence',
                  'registration_proof','rehearsal_evidence','signer_isolation_evidence')
        missing=[key for key in required if not c.get(key)]
        if missing:
            raise ContractError('Missing activation settings: '+','.join(missing))
        raise ContractError('Live capability adapter and independent acceptance are not integrated')
    return Document.from_dict(dict(mode=mode,signing=False,broadcast=False,
        audit_remote=False,market_reads=mode=='paper',build=m.get('build_id')))
