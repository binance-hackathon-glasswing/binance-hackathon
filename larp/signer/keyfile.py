"""The wallet key file on the signer host (IDEA-046 B2; IDEA-047 K01-K02).

The key is a root-only file on the signer's encrypted disk, handed to the service by systemd `LoadCredential`
(deploy/systemd/larp-signer.service). This loader is the last check before the key enters the process: it accepts
only a regular, single-link file owned by root or this process's user, with no group or other permission bits, in a
directory that is not a symlink and that nobody else can write. Refusals name the failed check, never key material.
"""

import os
from pathlib import Path
import re
import stat

from larp.execution import Blocked

MAX_BYTES = 4096
MNEMONIC_WORDS = (12, 15, 18, 21, 24)
_HEX_KEY = re.compile(r'(?:0x)?([0-9a-fA-F]{64})')
_WORD = re.compile(r'[a-z]+')


class KeyMaterial(dict):
    """One credential name -> value; its repr names the key only."""

    def __repr__(self):
        return 'KeyMaterial(' + ', '.join(sorted(self)) + ')'

    __str__ = __repr__


def _owner_ok(uid):
    return uid in (0, os.geteuid())


def _check_directory(directory):
    try:
        info = os.lstat(directory)
    except OSError:
        raise Blocked('key directory missing') from None
    if not stat.S_ISDIR(info.st_mode):
        raise Blocked('key directory is not a real directory')
    if not _owner_ok(info.st_uid):
        raise Blocked('key directory owner is not root or the signer user')
    if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise Blocked('key directory is writable by group or other')


def _check_file(info):
    if not stat.S_ISREG(info.st_mode):
        raise Blocked('key path is not a regular file')
    if not _owner_ok(info.st_uid):
        raise Blocked('key file owner is not root or the signer user')
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise Blocked('key file mode allows group or other access')
    if info.st_nlink != 1:
        raise Blocked('key file has another hard link')
    if not 0 < info.st_size <= MAX_BYTES:
        raise Blocked('key file size is out of range')


def _parse(text):
    tokens = text.split()
    if len(tokens) == 1:
        match = _HEX_KEY.fullmatch(tokens[0])
        if match:
            return KeyMaterial(WALLET_PRIVATE_KEY='0x' + match.group(1).lower())
    if len(tokens) in MNEMONIC_WORDS and all(_WORD.fullmatch(t) for t in tokens):
        return KeyMaterial(WALLET_MNEMONIC=' '.join(tokens))
    raise Blocked('key file holds no single recognised credential')


def load_key_file(path):
    """Read exactly one wallet credential; the result feeds LocalSigner.from_secret_store."""
    path = Path(path)
    _check_directory(path.parent)
    try:
        before = os.lstat(path)
    except OSError:
        raise Blocked('key file missing') from None
    _check_file(before)
    try:
        # O_NOFOLLOW refuses a symlink swapped in after the check; O_NONBLOCK keeps a swapped-in FIFO from hanging.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, 'O_CLOEXEC', 0))
    except OSError:
        raise Blocked('key file could not be opened safely') from None
    try:
        after = os.fstat(fd)
        if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
            raise Blocked('key file changed during the check')
        _check_file(after)
        raw = b''
        while len(raw) <= MAX_BYTES:
            chunk = os.read(fd, MAX_BYTES + 1 - len(raw))
            if not chunk:
                break
            raw += chunk
    finally:
        os.close(fd)
    if len(raw) > MAX_BYTES:
        raise Blocked('key file size is out of range')
    try:
        text = raw.decode('ascii')
    except UnicodeDecodeError:
        raise Blocked('key file holds no single recognised credential') from None
    return _parse(text)
