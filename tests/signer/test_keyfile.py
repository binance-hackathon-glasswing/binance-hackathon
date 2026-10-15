"""IDEA-047 K01-K02: the signer's wallet key file (IDEA-046 B2)."""
import os
import stat
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

from larp.execution import Blocked
from larp.signer.keyfile import load_key_file

KEY = 'ab' * 32
MARKER_KEY = 'cd' * 32
WORDS = ' '.join(['abandon'] * 11 + ['about'])


class KeyFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / 'signer'
        self.dir.mkdir(mode=0o700)
        self.path = self.dir / 'wallet.key'

    def write(self, text, mode=0o600):
        self.path.write_text(text, encoding='utf-8')
        os.chmod(self.path, mode)
        return self.path

    def refused(self, path=None):
        with self.assertRaises(Blocked) as raised:
            load_key_file(path or self.path)
        return str(raised.exception)

    def test_private_key_with_or_without_prefix_and_trailing_newline(self):
        for text in (KEY, '0x' + KEY, KEY + '\n', '  0x' + KEY.upper() + '\r\n'):
            with self.subTest(text=text[:6]):
                self.write(text)
                self.assertEqual(dict(load_key_file(self.path)), {'WALLET_PRIVATE_KEY': '0x' + KEY})

    def test_mnemonic_word_counts(self):
        for count in (12, 15, 18, 21, 24):
            with self.subTest(count=count):
                self.write(' '.join(['abandon'] * count) + '\n')
                self.assertEqual(set(load_key_file(self.path)), {'WALLET_MNEMONIC'})
        self.write(WORDS.replace(' ', '\n'))
        self.assertEqual(load_key_file(self.path)['WALLET_MNEMONIC'], WORDS)
        for count in (11, 13, 25):
            with self.subTest(bad=count):
                self.write(' '.join(['abandon'] * count))
                self.refused()

    def test_result_feeds_local_signer_loader(self):
        try:
            from eth_account import Account
        except ImportError:
            self.skipTest('signer dependency not installed')
        from larp.signer.local import LocalSigner
        account = Account.create()
        self.write(account.key.hex())
        secrets = dict(load_key_file(self.path), AI_SEEDS_ADDRESS=account.address.lower())
        registry = type('R', (), dict(lookup=lambda *a: None, check_authority=lambda *a: None,
                                      put_if_absent=lambda *a: None))()
        signer = LocalSigner.from_secret_store(secrets, registry=registry, authorization=lambda *a: None,
                                               signer_host=True)
        self.assertEqual(signer.account.address, account.address)

    def test_mode_bits_for_group_or_other_are_refused(self):
        for mode in (0o640, 0o604, 0o620, 0o602, 0o610, 0o601, 0o644, 0o666):
            with self.subTest(mode=oct(mode)):
                self.write(KEY, mode)
                self.assertIn('mode', self.refused())
        self.write(KEY, 0o400)
        self.assertIn('WALLET_PRIVATE_KEY', load_key_file(self.path))

    def test_not_a_regular_file(self):
        self.assertIn('missing', self.refused(self.dir / 'absent.key'))
        self.write(KEY)
        link = self.dir / 'link.key'
        link.symlink_to(self.path)
        self.assertIn('regular', self.refused(link))
        self.assertIn('regular', self.refused(self.dir))
        fifo = self.dir / 'fifo.key'
        os.mkfifo(fifo, 0o600)
        self.assertIn('regular', self.refused(fifo))

    def test_symlinked_parent_directory_is_refused(self):
        self.write(KEY)
        alias = Path(self.tmp.name) / 'alias'
        alias.symlink_to(self.dir)
        self.assertIn('directory', self.refused(alias / 'wallet.key'))

    def test_extra_hard_link_is_refused(self):
        self.write(KEY)
        os.link(self.path, self.dir / 'copy.key')
        self.assertIn('link', self.refused())

    def test_other_owner_is_refused(self):
        self.write(KEY)
        real = os.lstat(self.path)
        fake = os.stat_result((real.st_mode, real.st_ino, real.st_dev, 1, real.st_uid + 4242, real.st_gid,
                               real.st_size, 0, 0, 0))
        with patch('larp.signer.keyfile.os.fstat', return_value=fake), \
                patch('larp.signer.keyfile.os.lstat', side_effect=lambda p, *a, **k: fake
                      if Path(p) == self.path else os.stat(p, follow_symlinks=False)):
            self.assertIn('owner', self.refused())

    def test_unsafe_directory_is_refused(self):
        self.write(KEY)
        for mode in (0o770, 0o707, 0o730, 0o703):
            with self.subTest(mode=oct(mode)):
                os.chmod(self.dir, mode)
                self.assertIn('directory', self.refused())
        os.chmod(self.dir, 0o755)  # readable directory is fine; the file mode protects the key
        self.assertIn('WALLET_PRIVATE_KEY', load_key_file(self.path))

    def test_swapped_after_check_is_refused(self):
        self.write(KEY)
        other = self.dir / 'other.key'
        other.write_text(MARKER_KEY)
        os.chmod(other, 0o600)
        real_lstat = os.lstat(other)
        with patch('larp.signer.keyfile.os.lstat', side_effect=lambda p, *a, **k: real_lstat
                   if Path(p) == self.path else os.stat(p, follow_symlinks=False)):
            message = self.refused()
        self.assertIn('changed', message)
        self.assertNotIn(MARKER_KEY, message)

    def test_size_and_content(self):
        for text in ('', '\n  \n', 'x' * 5000, 'not a key', KEY[:-2], KEY + 'zz', KEY + '\n' + KEY,
                     '0x' + KEY + ' ' + WORDS, 'WALLET_PRIVATE_KEY=' + KEY, WORDS + ' Abandon'):
            with self.subTest(text=text[:12]):
                self.write(text)
                self.refused()

    def test_no_refusal_or_repr_contains_key_material(self):
        bad_texts = [MARKER_KEY + 'zz', MARKER_KEY + '\n' + MARKER_KEY, 'marker-word ' * 12]
        for text in bad_texts:
            self.write(text)
            try:
                load_key_file(self.path)
            except Blocked:
                rendered = traceback.format_exc()
            else:
                self.fail('bad key accepted')
            self.assertNotIn(MARKER_KEY, rendered)
            self.assertNotIn('marker-word', rendered)
        self.write(MARKER_KEY, 0o644)
        try:
            load_key_file(self.path)
        except Blocked:
            self.assertNotIn(MARKER_KEY, traceback.format_exc())
        self.write(MARKER_KEY)
        loaded = load_key_file(self.path)
        self.assertNotIn(MARKER_KEY, repr(loaded))
        self.assertNotIn(MARKER_KEY, str(loaded))


if __name__ == '__main__':
    unittest.main()
