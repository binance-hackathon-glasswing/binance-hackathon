import hashlib
import json
import unittest

from larp.audit.protocol import build_event,sign,verify_event
from larp.contracts import ContractError

ADDRESS='0x'+'1'*40


def event(identity='evt',round_id='round',text='hold',orders=None,mappings=()):
    return build_event(event_id=identity,round_id=round_id,version_id='fixture',decision_ids=['d'],
        address=ADDRESS,timestamp_ms=1791590400000,input_record={'synthetic':True},rationale=text,
        output='HOLD',orders=orders or [],swap_mappings=mappings)


class Protocol(unittest.TestCase):
    def test_official_vectors(self):
        secret='5f3a0123456789abcdef0123456789abcdef0123456789abcdef9b2c7e1d4a6f'
        wallet='0xb843d56afc902e37a6433eed534feadc91be71b8'
        nonce='0f8e2a9c4b7d4e1f9a3c5b6d7e8f9012'
        raw=b'{"protocolVersion":"2.0","address":"0xb843d56AfC902e37a6433eEd534Feadc91BE71b8","chunkCount":1,"totalBytes":2,"contentSha256":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a","encoding":"plain","payload":"{}"}'
        self.assertEqual('ab6216a66effdfc88a6beba78829bff9ee9326767f6acaeaf5fc63f8433c929f',hashlib.sha256(raw).hexdigest())
        self.assertEqual('451191a2b2f2f87eb60a6725fef648e7f3f6ef6efd2a1b8fe2c3cf2ec994ac27',
            sign(secret,'PUT','/v1/events/evt-1790242207430-3fa6651c2d4b/chunks/0',1790242207500,nonce,wallet,raw))
        raw=b'{"eventId":"evt-1","event":{"timestamp":1790242207430,"data":{"input":"i","cot":"c","output":"o","orders":[]}}}\n'
        self.assertEqual('997222a8ba50a845cfb99e479f6f4e38abdf5796a3b0bf2480ae07c4d982c3fc',
            sign(secret,'POST','/v1/files',1790242207500,nonce,wallet,raw))

    def test_unicode_and_escaping_preserve_exact_bytes(self):
        e=event(text='🙂漢字\x01'*30000).read()
        self.assertGreater(len(e['chunks']),1)
        rebuilt=''.join(json.loads(chunk)['payload'] for chunk in e['chunks'])
        self.assertEqual(e['log'],rebuilt)
        for chunk in e['chunks']:
            self.assertLessEqual(len(json.loads(chunk)['payload'].encode()),65536)
            self.assertLess(len(chunk.encode()),256*1024)

    def test_orders_require_hash_mapping_and_eligible_symbol(self):
        order=dict(symbol='NVDAB',side='BUY',amount='1',tx_hash='0x'+'a'*64)
        with self.assertRaises(ContractError): event(orders=[order])
        valid=event(orders=[order],mappings=[dict(tx_hash=order['tx_hash'],decision_id='d',step='swap')])
        verify_event(valid)
        with self.assertRaises(ContractError):
            event(orders=[order],mappings=[dict(tx_hash=order['tx_hash'],decision_id='d',step='approve')])
        with self.assertRaises(ContractError): event(orders=[dict(symbol='BNB',side='BUY',amount='1')])

    def test_oversize_rejected_without_truncating_reasoning(self):
        with self.assertRaises(ContractError): event(text='x'*(8*1024*1024))
