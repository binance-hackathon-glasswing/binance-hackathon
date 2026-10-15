"""C-ASM-009: API-only selection, fixture secrets only."""
from pathlib import Path
import tempfile
import unittest

from larp.marketdata.web3 import Unavailable, credentials


class CredentialSelection(unittest.TestCase):
    def select(self, text):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'fixture.env'
            path.write_text(text)
            return credentials(path, environ={})

    def test_c_asm_009_blank_optional_fields_preserve_web3_pair(self):
        pair = 'BINANCE_API_KEY=fixture-key\nBINANCE_SECRET_KEY=fixture-secret\n'
        for blank in ('', '""', "''", '# optional'):
            with self.subTest(blank=blank):
                selected = self.select(pair + ''.join(name + '=' + blank + '\n' for name in (
                    'AI_SEEDS_ADDRESS', 'BN_WEB3_API_KEY', 'BN_WEB3_API_SECRET', 'BN_WEB3_SECRET_KEY')))
                self.assertEqual(selected, dict(BINANCE_API_KEY='fixture-key', BINANCE_SECRET_KEY='fixture-secret'))

    def test_c_asm_009_missing_conflicting_or_nonliteral_credentials_stay_refused(self):
        pair = 'BINANCE_API_KEY=fixture-key\nBINANCE_SECRET_KEY=fixture-secret\n'
        for text in ('BINANCE_API_KEY=\nBINANCE_SECRET_KEY=\n',
                     pair + 'BN_WEB3_API_KEY=another-fixture-key\n',
                     pair + 'AI_SEEDS_ADDRESS=${PUBLIC_ADDRESS}\n'):
            with self.subTest(text=text), self.assertRaises(Unavailable):
                self.select(text)
