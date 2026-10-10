import io
from datetime import datetime, timezone
import unittest

from larp.contracts import ContractError
from larp.storage.archive import S3Archive
from larp.storage.postgres import IntegrityError, Unavailable, digest


class FakeS3:
    """Models immutable key/version behavior; not evidence of hosted AWS access."""
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.lost_ack = False
        self.tamper = False

    def put_object(self, **kwargs):
        from botocore.exceptions import ClientError
        self.calls.append(kwargs)
        key = kwargs['Key']
        if key in self.objects:
            raise ClientError({'Error': {'Code': 'PreconditionFailed'}}, 'PutObject')
        self.objects[key] = kwargs
        if self.lost_ack:
            self.lost_ack = False
            from botocore.exceptions import ReadTimeoutError
            raise ReadTimeoutError(endpoint_url='https://synthetic.invalid')
        return {'VersionId': 'version-1'}

    def head_object(self, **kwargs):
        return {'VersionId': 'version-1'}

    def get_object(self, **kwargs):
        item = self.objects[kwargs['Key']]
        raw = item['Body'] + (b'bad' if self.tamper else b'')
        return dict(Body=io.BytesIO(raw), ContentLength=len(raw), VersionId='version-1',
                    ObjectLockMode=item['ObjectLockMode'], ObjectLockRetainUntilDate=item['ObjectLockRetainUntilDate'],
                    ServerSideEncryption=item['ServerSideEncryption'], SSEKMSKeyId=item['SSEKMSKeyId'])


class Archives(unittest.TestCase):
    def setUp(self):
        self.client = FakeS3()
        self.archive = S3Archive(self.client, bucket='fixture', account_id='123456789012',
                                kms_key='arn:synthetic:key', prefix='archive/development', retention_days=7)

    def test_lost_ack_retries_same_key_and_verifies_exact_version(self):
        self.client.lost_ack = True
        with self.assertRaises(Unavailable):
            self.archive.put('run/anchor/0.json', b'{}', created_ms=0, now_ms=10)
        receipt = self.archive.put('run/anchor/0.json', b'{}', created_ms=0, now_ms=11)
        self.assertEqual(1, len(self.client.objects))
        self.assertEqual(self.client.calls[0], self.client.calls[1])
        self.assertEqual('*', self.client.calls[0]['IfNoneMatch'])
        self.assertEqual(b'{}', self.archive.fetch(receipt))

    def test_changed_bytes_and_missing_retention_fail(self):
        self.archive.put('run/anchor/0.json', b'{}', created_ms=0, now_ms=10)
        with self.assertRaises(IntegrityError):
            self.archive.put('run/anchor/0.json', b'{"changed":true}', created_ms=0, now_ms=11)
        self.client.objects['archive/development/run/anchor/0.json']['ObjectLockMode'] = 'GOVERNANCE'
        with self.assertRaises(IntegrityError):
            self.archive.put('run/anchor/0.json', b'{}', created_ms=0, now_ms=12)

    def test_corrupt_read_limits_and_expired_retention(self):
        receipt = self.archive.put('run/backup/0.json', b'{}', created_ms=0, now_ms=10)
        self.client.tamper = True
        with self.assertRaises(IntegrityError): self.archive.fetch(receipt)
        with self.assertRaises(ContractError):
            self.archive.put('../escape.json', b'{}', created_ms=0, now_ms=0)
        with self.assertRaises(ContractError):
            self.archive.put('expired.json', b'{}', created_ms=0, now_ms=7*86400000)

    def test_real_sdk_request_shape_is_supported(self):
        # botocore validates actual AWS model parameters without network access.
        import boto3
        from botocore.stub import Stubber, ANY
        from botocore.response import StreamingBody
        client = boto3.client('s3', region_name='us-east-1', aws_access_key_id='synthetic',
                              aws_secret_access_key='synthetic')
        archive = S3Archive(client, bucket='fixture', account_id='123456789012', kms_key='arn:synthetic:key',
                            prefix='archive/dev', retention_days=1)
        retain = datetime.fromtimestamp(86400, timezone.utc)
        with Stubber(client) as stub:
            stub.add_response('put_object', {'VersionId': 'v1'}, dict(
                Bucket='fixture', Key='archive/dev/test.json', Body=b'{}', ExpectedBucketOwner='123456789012',
                IfNoneMatch='*', ContentType='application/json', ContentMD5=ANY,
                ServerSideEncryption='aws:kms', SSEKMSKeyId='arn:synthetic:key', ObjectLockMode='COMPLIANCE',
                ObjectLockRetainUntilDate=retain, Metadata={'sha256': digest(b'{}')}))
            stub.add_response('get_object', dict(Body=StreamingBody(io.BytesIO(b'{}'), 2), ContentLength=2,
                ObjectLockMode='COMPLIANCE', ObjectLockRetainUntilDate=retain,
                ServerSideEncryption='aws:kms', SSEKMSKeyId='arn:synthetic:key'),
                dict(Bucket='fixture', Key='archive/dev/test.json', VersionId='v1', ExpectedBucketOwner='123456789012'))
            self.assertEqual('STORED', archive.put('test.json', b'{}', created_ms=0, now_ms=1).read()['status'])
            stub.assert_no_pending_responses()
