"""Wallet-specific runtime paths; no credential values are serialized."""
from dataclasses import dataclass
from pathlib import Path
import re

from larp.contracts import ContractError
from larp.execution import Blocked, address


@dataclass(frozen=True)
class WalletBinding:
    run_id: str
    wallet: str
    root: Path

    @classmethod
    def create(cls, run_id, wallet, root, *, expected_wallet):
        if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', run_id):
            raise Blocked('safe unique run identity required')
        normalized = address(wallet.lower())
        if normalized != address(expected_wallet.lower()):
            raise Blocked('configured wallet does not match registered address')
        return cls(run_id, normalized, Path(root).resolve())

    @property
    def directory(self):
        return self.root / self.wallet / self.run_id

    @property
    def nonce_namespace(self):
        # Wallet-wide barrier cannot be evaded by starting another run.
        return '56:' + self.wallet

    @property
    def audit_directory(self):
        return self.directory / '.ai-seeds'


def _pair(config, prefix):
    path, sha256 = config.get(prefix + '_file'), config.get(prefix + '_sha256')
    if path in (None, '') and sha256 in (None, ''):
        return None
    if path in (None, '') or sha256 in (None, ''):
        raise ContractError('Set both %s_file and %s_sha256, or neither' % (prefix, prefix))
    return path, sha256


def evidence_settings(config):
    """`(path, sha256)` from a service config, or None when neither is set; both or neither (IDEA-070 R6).
    Refuses a config that also names an untrusted-router policy: one swap decoder per service (B02-U)."""
    settings = _pair(config, 'router_evidence')
    if settings is not None and untrusted_router_settings(config) is not None:
        raise ContractError('Configure router evidence or an untrusted-router policy, not both')
    return settings


def untrusted_router_settings(config):
    """`(path, sha256)` of an UntrustedRouterPolicy.v1 (IDEA-070 B02-U, DEV-23), or None; both or neither."""
    return _pair(config, 'untrusted_router_policy')
