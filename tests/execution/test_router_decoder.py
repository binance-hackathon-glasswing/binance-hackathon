"""IDEA-070 R1-R4, R8: the swap decoder pinned to router evidence.

Every ABI here is SYNTHETIC. It exercises the decoder's rules; it says nothing about the real router, whose evidence
must come from its verified source (docs/build/GATE_B.md).
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from eth_abi import encode

from larp.contracts import ContractError
from larp.execution import BSTOCKS, NATIVE_BNB, USDT, Blocked, Gates, Payload, validate_payload
from larp.execution_live import router as module
from larp.execution_live.router import PinnedRouterDecoder, check_routes, load_evidence, selector, validate_evidence
from tests.execution_fixtures import intent

ROUTER = '0x' + 'ab' * 20
WALLET = '0x' + '1' * 40
TOKEN = sorted(BSTOCKS)[0]
SENTINEL = '0x' + 'ee' * 20
SIGNATURE = ('syntheticSwap((address,address,uint256,uint256,address,uint256),'
             '(address,uint256,bytes)[])')
TYPES = ['(address,address,uint256,uint256,address,uint256)', '(address,uint256,bytes)[]']


def evidence(**changes):
    value = dict(
        schema='RouterEvidence.v1', chain_id=56, router=ROUTER, implementation=None,
        function=dict(signature=SIGNATURE, selector=selector(SIGNATURE)),
        fields=dict(pay_token=[0, 0], receive_token=[0, 1], amount=[0, 2], minimum_output=[0, 3],
                    recipient=[0, 4], deadline=[0, 5]),
        native_sentinels=[SENTINEL],
        source=dict(verified_on='SYNTHETIC', url='synthetic://not-a-real-router', contract_name='Synthetic',
                    compiler='none', source_sha256='0' * 64, abi_sha256='1' * 64, retrieved_at='2026-10-16'),
        guarantees=dict(minimum_output_checked_on_recipient_balance=True, deadline_enforced=True,
                        input_pulled_only_from_sender=True, wallet_debits_limited_to_pay_token_and_amount=True),
        review=dict(reviewed_by='synthetic-test', review_ref='IDEA-070 R1'))
    value.update(changes)
    return value


def calldata(pay=USDT, receive=TOKEN, amount=100, minimum=90, recipient=WALLET, deadline=500, steps=None):
    steps = steps if steps is not None else [('0x' + '33' * 20, 7, b'\x01\x02\x03')]
    body = encode(TYPES, [(pay, receive, amount, minimum, recipient, deadline), steps])
    return selector(SIGNATURE) + body.hex()


def payload(data=None, to=ROUTER, value=0):
    return Payload(56, WALLET, to, value, 0, 100000, 1, data or calldata())


def gates(**changes):
    return replace(Gates(1, 1, 0, 0, 1000, True, True, True, True, True, True, True, True), **changes)


class EvidenceValidation(unittest.TestCase):  # R1, R2
    def test_known_selectors(self):
        self.assertEqual(selector('transfer(address,uint256)'), '0xa9059cbb')
        self.assertEqual(selector('approve(address,uint256)'), '0x095ea7b3')

    def test_valid_evidence_is_accepted(self):
        self.assertEqual(validate_evidence(evidence())['router'], ROUTER)

    def test_each_defect_is_refused(self):
        bad_fields = lambda **f: dict(evidence()['fields'], **f)
        cases = {
            'schema': evidence(schema='RouterEvidence.v0'),
            'chain': evidence(chain_id=1),
            'chain bool': evidence(chain_id=True),
            'router case': evidence(router=ROUTER.upper().replace('0X', '0x')),
            'router is token': evidence(router=USDT),
            'implementation': evidence(implementation='0x123'),
            'selector mismatch': evidence(function=dict(signature=SIGNATURE, selector='0xad43f73d')),
            'non canonical type': evidence(function=dict(signature=SIGNATURE.replace('uint256', 'uint', 1),
                                                         selector=selector(SIGNATURE.replace('uint256', 'uint', 1)))),
            'spaces': evidence(function=dict(signature=SIGNATURE.replace(',', ', ', 1),
                                             selector=selector(SIGNATURE.replace(',', ', ', 1)))),
            'unparseable': evidence(function=dict(signature='swap(', selector=selector('swap('))),
            'missing field': evidence(fields={k: v for k, v in evidence()['fields'].items() if k != 'deadline'}),
            'out of range': evidence(fields=bad_fields(deadline=[0, 9])),
            'into array': evidence(fields=bad_fields(deadline=[1, 0, 1])),
            'stops on tuple': evidence(fields=bad_fields(amount=[0])),
            'token not address': evidence(fields=bad_fields(pay_token=[0, 2])),
            'amount not uint': evidence(fields=bad_fields(amount=[0, 4])),
            'bool index': evidence(fields=bad_fields(amount=[0, True])),
            'sentinel repeat': evidence(native_sentinels=[SENTINEL, SENTINEL]),
            'sentinel is token': evidence(native_sentinels=[USDT]),
            'guarantee false': evidence(guarantees=dict(evidence()['guarantees'], deadline_enforced=False)),
            'guarantee truthy': evidence(guarantees=dict(evidence()['guarantees'], deadline_enforced=1)),
            'no reviewer': evidence(review=dict(reviewed_by=' ', review_ref='x')),
            'bad source hash': evidence(source=dict(evidence()['source'], abi_sha256='XYZ')),
            'unknown key': dict(evidence(), extra=1),
            'missing key': {k: v for k, v in evidence().items() if k != 'review'},
        }
        for name, value in cases.items():
            with self.subTest(name), self.assertRaises(ContractError):
                validate_evidence(value)

    def test_pinned_file_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'router.json'
            raw = json.dumps(evidence()).encode()
            path.write_bytes(raw)
            decoder = load_evidence(path, hashlib.sha256(raw).hexdigest())
            self.assertEqual(decoder.evidence_sha256, hashlib.sha256(raw).hexdigest())
            for wrong in ('0' * 64, 'not-a-hash'):
                with self.subTest(wrong), self.assertRaises(ContractError):
                    load_evidence(path, wrong)

    def test_settings_are_both_or_neither(self):
        self.assertIsNone(module.evidence_settings({}))
        self.assertEqual(module.evidence_settings(dict(router_evidence_file='f', router_evidence_sha256='h')),
                         ('f', 'h'))
        for config in (dict(router_evidence_file='f'), dict(router_evidence_sha256='h')):
            with self.subTest(config), self.assertRaises(ContractError):
                module.evidence_settings(config)


class ByteBinding(unittest.TestCase):  # R3, R4
    def setUp(self):
        self.decoder = PinnedRouterDecoder(evidence())

    def test_canonical_route_decodes_to_its_values(self):
        economics = self.decoder.decode(payload())
        self.assertEqual((economics.pay_token, economics.receive_token, economics.amount, economics.minimum_output,
                          economics.recipient, economics.deadline, economics.native_value),
                         (USDT, TOKEN, 100, 90, WALLET, 500, 0))

    def test_malformed_routes_are_refused(self):
        data = calldata()
        raw = bytearray(bytes.fromhex(data[2:]))
        dirty = bytearray(raw)
        dirty[4 + 32 * 4 + 31 - 20 - 1] = 1  # a high byte of the recipient's address word (5th word of the tuple)
        shifted = bytearray(raw)
        # The array's head offset (word 6) moved by 32 with a zero word inserted: same values, non-canonical bytes.
        offset = int.from_bytes(raw[4 + 32 * 6:4 + 32 * 7], 'big')
        shifted[4 + 32 * 6:4 + 32 * 7] = (offset + 32).to_bytes(32, 'big')
        shifted[4 + offset:4 + offset] = bytes(32)
        cases = {
            'selector': '0x' + format(int(data[2:10], 16) ^ 1, '08x') + data[10:],
            'trailing byte': data + '00',
            'trailing word': data + '00' * 32,
            'truncated': data[:-2],
            'dirty padding': '0x' + dirty.hex(),
            'non canonical offset': '0x' + shifted.hex(),
            'odd hex': data + '0',
            'not hex': data[:-2] + 'zz',
        }
        for name, mutated in cases.items():
            with self.subTest(name), self.assertRaises(Blocked):
                self.decoder.decode(payload(mutated))
        with self.assertRaises(Blocked):
            self.decoder.decode(payload(to='0x' + 'cd' * 20))

    def test_changed_fields_fail_validation_against_the_intent(self):
        wanted = intent(wallet=WALLET, router=ROUTER, amount=100, minimum_output=90, valid_until=600)
        validate_payload(wanted, 'SWAP', payload(), gates(), 10, self.decoder)
        for name, data in {
                'recipient': calldata(recipient='0x' + '44' * 20),
                'amount': calldata(amount=101),
                'minimum output': calldata(minimum=89),
                'pay token': calldata(pay=sorted(BSTOCKS)[1]),
                'receive token': calldata(receive=sorted(BSTOCKS)[1]),
                'deadline past intent': calldata(deadline=601),
                'deadline expired': calldata(deadline=10)}.items():
            with self.subTest(name), self.assertRaises(Blocked):
                validate_payload(wanted, 'SWAP', payload(data), gates(), 10, self.decoder)

    def test_native_sentinel_is_bnb_only_when_listed(self):
        economics = self.decoder.decode(payload(calldata(receive=SENTINEL)))
        self.assertEqual(economics.receive_token, NATIVE_BNB)
        zero = self.decoder.decode(payload(calldata(receive='0x' + '0' * 40)))
        self.assertEqual(zero.receive_token, '0x' + '0' * 40)
        with self.assertRaises(Blocked):
            self.decoder.decode(payload(calldata(recipient=SENTINEL)))

    def test_native_value_is_reported_from_the_payload(self):
        self.assertEqual(self.decoder.decode(payload(value=5)).native_value, 5)


def artifact(directory, endpoint, params, data):
    record = dict(schema='Web3Observation.v1', source_id='BINANCE_WEB3', endpoint=endpoint, method='GET',
                  params=params, requested_at='2026-10-17T00:00:00Z', outcome='ok', http_status=200,
                  response=dict(code=0, data=data))
    raw = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
    (Path(directory) / (hashlib.sha256(raw).hexdigest() + '.json')).write_bytes(raw)


def quote(directory, pay, receive, amount, minimum, data=None, *, wallet=WALLET, router=ROUTER):
    artifact(directory, 'aggregator/quote-and-swap',
             dict(fromTokenAddress=pay, toTokenAddress=receive, amount=str(amount), userWalletAddress=wallet,
                  binanceChainId='56'),
             dict(executionMode='SWAP', tx=dict(to=router, value='0', gas='250000', gasPrice='100000000',
                                                minReceiveAmount=str(minimum),
                                                data=data or calldata(pay, receive, amount, minimum,
                                                                      recipient=wallet))))


class RecordedRouteCheck(unittest.TestCase):  # R8
    def setUp(self):
        self.decoder = PinnedRouterDecoder(evidence(), evidence_sha256='e' * 64)

    def test_both_directions_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            quote(directory, USDT, TOKEN, 100, 90)
            quote(directory, TOKEN, USDT, 50, 40)
            artifact(directory, 'aggregator/approve-transaction', dict(tokenContractAddress=USDT, binanceChainId='56'),
                     dict(dexContractAddress=ROUTER.upper().replace('0X', '0x'), data='0x', gasLimit='1'))
            report = check_routes(self.decoder, directory)
        self.assertEqual(report['status'], 'PASS', report)
        self.assertEqual(report['directions'], ['BUY', 'SELL'])
        self.assertEqual(report['evidence_sha256'], 'e' * 64)
        self.assertEqual(len(report['artifacts_read']), 3)

    def test_gas_route_with_a_router_side_native_sentinel(self):
        decoder = PinnedRouterDecoder(evidence(native_sentinels=['0x' + '0' * 40]))
        with tempfile.TemporaryDirectory() as directory:
            quote(directory, USDT, TOKEN, 100, 90)
            quote(directory, TOKEN, USDT, 50, 40)
            # The API asks for 0xeee...e; the router encodes its own sentinel (here the zero address).
            quote(directory, USDT, NATIVE_BNB, 30, 20, data=calldata(USDT, '0x' + '0' * 40, 30, 20))
            report = check_routes(decoder, directory)
        self.assertEqual(report['status'], 'PASS', report)
        self.assertEqual(report['directions'], ['BUY', 'GAS', 'SELL'])

    def test_one_direction_is_not_enough(self):
        with tempfile.TemporaryDirectory() as directory:
            quote(directory, USDT, TOKEN, 100, 90)
            self.assertEqual(check_routes(self.decoder, directory)['status'], 'FAIL')

    def test_mismatches_fail(self):
        cases = {
            'amount': calldata(USDT, TOKEN, 101, 90),
            'minimum': calldata(USDT, TOKEN, 100, 89),
            'recipient': calldata(USDT, TOKEN, 100, 90, recipient='0x' + '44' * 20),
            'undecodable': calldata(USDT, TOKEN, 100, 90) + '00',
        }
        for name, data in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as directory:
                quote(directory, USDT, TOKEN, 100, 90, data=data)
                quote(directory, TOKEN, USDT, 50, 40)
                report = check_routes(self.decoder, directory)
                self.assertEqual(report['status'], 'FAIL')
                self.assertTrue(report['routes'][0]['problems'] or report['routes'][1]['problems'])

    def test_other_spender_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            quote(directory, USDT, TOKEN, 100, 90)
            quote(directory, TOKEN, USDT, 50, 40)
            artifact(directory, 'aggregator/approve-transaction', dict(tokenContractAddress=USDT, binanceChainId='56'),
                     dict(dexContractAddress='0x' + '99' * 20, data='0x', gasLimit='1'))
            self.assertEqual(check_routes(self.decoder, directory)['status'], 'FAIL')

    def test_no_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(check_routes(self.decoder, directory)['status'], 'NO_ROUTES')

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = json.dumps(evidence()).encode()
            path = Path(directory) / 'evidence.json'
            path.write_bytes(raw)
            routes = Path(directory) / 'artifacts'
            routes.mkdir()
            quote(routes, USDT, TOKEN, 100, 90)
            quote(routes, TOKEN, USDT, 50, 40)
            out = Path(directory) / 'report.json'
            code = module.main(['check', '--evidence', str(path), '--sha256', hashlib.sha256(raw).hexdigest(),
                                '--artifacts', str(routes), '--out', str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.read_text())['status'], 'PASS')
            self.assertEqual(module.main(['check', '--evidence', str(path), '--sha256', '0' * 64,
                                          '--artifacts', str(routes)]), 4)


if __name__ == '__main__':
    unittest.main()
