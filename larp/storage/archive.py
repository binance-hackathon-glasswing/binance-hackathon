"""Conditional, version-pinned S3 archive writes; no imports fetch credentials."""

import base64
from datetime import datetime, timezone
import hashlib
import re

from larp.contracts import ContractError
from larp.storage.postgres import IntegrityError, Unavailable, doc, digest


class S3Archive:
    def __init__(self, client, *, bucket, account_id, kms_key, prefix, retention_days,
                 max_bytes=64 * 1024 * 1024):
        if not re.fullmatch(r'[a-zA-Z0-9/_-]+', prefix) or '..' in prefix:
            raise ContractError('Invalid archive namespace')
        if not re.fullmatch(r'\d{12}', account_id) or not bucket or not kms_key:
            raise ContractError('Missing archive destination')
        if type(retention_days) is not int or retention_days < 1 or max_bytes < 1:
            raise ContractError('Invalid archive retention or size limit')
        self.client = client
        self.bucket, self.account_id, self.kms_key = bucket, account_id, kms_key
        self.prefix = prefix.strip('/')
        self.retention_days, self.max_bytes = retention_days, max_bytes

    def _read(self, key, version_id):
        result = self.client.get_object(Bucket=self.bucket, Key=key,
                                        VersionId=version_id, ExpectedBucketOwner=self.account_id)
        body = result['Body']
        try:
            raw = body.read(self.max_bytes + 1)
        finally:
            body.close()
        if len(raw) > self.max_bytes or result.get('ContentLength') != len(raw):
            raise IntegrityError('Archive size mismatch')
        return raw, result

    def put(self, key, payload, *, created_ms, now_ms):
        from botocore.exceptions import BotoCoreError, ClientError
        if not re.fullmatch(r'[a-zA-Z0-9/_-]+\.json', key) or '..' in key:
            raise ContractError('Invalid archive object key')
        if not payload or len(payload) > self.max_bytes:
            raise ContractError('Archive object exceeds configured limit')
        if created_ms < 0 or now_ms < created_ms:
            raise ContractError('Invalid archive time')
        # S3 stores Object Lock dates to whole seconds: request the next whole second, never less than the
        # retention, so the read-back check compares the date S3 actually keeps (IDEA-082).
        retain_ms = -(-(created_ms + self.retention_days * 86400000) // 1000) * 1000
        if retain_ms <= now_ms:
            raise ContractError('Archive retention window exhausted; explicit recovery required')
        retain_until = datetime.fromtimestamp(retain_ms / 1000, timezone.utc)
        full_key = self.prefix + '/' + key
        try:
            try:
                response = self.client.put_object(
                    Bucket=self.bucket, Key=full_key, Body=payload,
                    ExpectedBucketOwner=self.account_id, IfNoneMatch='*',
                    ContentType='application/json',
                    ContentMD5=base64.b64encode(hashlib.md5(payload).digest()).decode('ascii'),
                    ServerSideEncryption='aws:kms', SSEKMSKeyId=self.kms_key,
                    ObjectLockMode='COMPLIANCE', ObjectLockRetainUntilDate=retain_until,
                    Metadata={'sha256': digest(payload)})
                version = response.get('VersionId')
            except ClientError as exc:
                if exc.response.get('Error', {}).get('Code') not in ('PreconditionFailed', '412'):
                    raise
                # A lost PUT acknowledgement or a concurrent writer. Fetch the
                # current version's identity, then compare the exact version bytes.
                existing = self.client.head_object(Bucket=self.bucket, Key=full_key,
                                                   ExpectedBucketOwner=self.account_id)
                version = existing.get('VersionId')
            if not version or version == 'null':
                raise IntegrityError('Archive did not return a versioned object')
            raw, result = self._read(full_key, version)
            if raw != payload:
                raise IntegrityError('Archive ID already contains different bytes')
            if (result.get('ObjectLockMode') != 'COMPLIANCE'
                    or result.get('ObjectLockRetainUntilDate', datetime.min.replace(tzinfo=timezone.utc)) < retain_until
                    or result.get('ServerSideEncryption') != 'aws:kms'
                    or result.get('SSEKMSKeyId') != self.kms_key):
                raise IntegrityError('Archive retention/encryption verification failed')
            return doc(dict(schema='ArchiveReceipt.v1', status='STORED', bucket=self.bucket,
                            key=full_key, version_id=version, sha256=digest(payload),
                            retain_until_ms=retain_ms))
        except (BotoCoreError, ClientError):
            raise Unavailable('Archive request failed; durable work retained') from None

    def fetch(self, receipt):
        """Read an explicitly selected backup version; never selects latest itself."""
        from botocore.exceptions import BotoCoreError, ClientError
        r = receipt.read()
        if (r.get('bucket') != self.bucket or not r.get('key', '').startswith(self.prefix + '/')
                or not r.get('version_id') or r['version_id'] == 'null'):
            raise IntegrityError('Archive receipt destination mismatch')
        try:
            raw, _ = self._read(r['key'], r['version_id'])
        except (BotoCoreError, ClientError):
            raise Unavailable('Archive read failed') from None
        if digest(raw) != r.get('sha256'):
            raise IntegrityError('Archive checksum mismatch')
        return raw
