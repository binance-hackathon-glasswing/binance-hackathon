"""Wallet-specific runtime paths; no credential values are serialized."""
from dataclasses import dataclass
from pathlib import Path
import re

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
