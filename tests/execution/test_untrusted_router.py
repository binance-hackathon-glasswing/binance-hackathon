"""IDEA-070 B02-U: the untrusted-router swap mode (DEV-23).

Decoding uses the real recorded quotes in docs/build/evidence/quotes-interim-20261018/selected-raw. Live router state
comes from a fake RPC; nothing here calls the network or signs.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from eth_utils import keccak

from larp.contracts import ContractError
from larp.execution import BSTOCKS, USDT, Blocked, DependencyUnavailable, Executor, Gates, Payload, validate_payload
from larp.execution_live import untrusted_router as u
from larp.execution_live.loop import RunAuthorization
from larp.execution_live.router import PinnedRouterDecoder
from larp.signer import service as signer_service
from larp.signer.policy import SigningPolicy
from tests.execution.test_router_decoder import evidence
from tests.execution_fixtures import intent
from tests.execution import test_gate_b_evidence as gb
from tests.runtime import test_halt_split as hs

QUOTES = Path(__file__).resolve().parents[2] / 'docs/build/evidence/quotes-interim-20261018/selected-raw'
ROUTER_CODE, FACET_CODE = b'\x60\x80router', b'\x60\x80facet'


def word(value):
    return '0x' + format(value, '064x')


def policy(**changes):
    value = dict(schema=u.SCHEMA, chain_id=56, router=u.ROUTER, router_codehash='0x' + keccak(ROUTER_CODE).hex(),
                 selector=u.SWAP_SELECTOR, diamond_storage_base=u.DIAMOND_STORAGE_BASE,
                 facet_slot=u.selector_slot(u.SWAP_SELECTOR, u.DIAMOND_STORAGE_BASE),
                 facet='0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603',
                 facet_codehash='0x' + keccak(FACET_CODE).hex(),
                 fixed_words={'1': word(0), '2': word(0x3d90f66b534dd8482b181e24655a9e8265316be9),
                              '7': word(0xd2a27f8fdbaaec431d59046a8bce4e5db665a271), '9': word(0x140)},
                 inner_selector=u.INNER_SELECTOR, deviation='DEV-23',
                 review=dict(reviewed_by='Keegan', review_ref='IDEA-070 B02-U'))
    value.update(changes)
    return value


def quotes():
    return list(u._quotes(QUOTES))


def swap(params, tx, **changes):
    return replace(Payload(56, params['userWalletAddress'].lower(), str(tx['to']).lower(), 0, 7, 250000, 1, tx['data']),
                   **changes)


def swap_intent(params, tx, decoder):
    deadline = decoder.decode(swap(params, tx)).deadline
    return intent(wallet=params['userWalletAddress'].lower(), router=u.ROUTER, pay_token=params['fromTokenAddress'].lower(),
                  receive_token=params['toTokenAddress'].lower(), amount=int(params['amount']),
                  minimum_output=int(tx['minReceiveAmount']), valid_until=deadline, max_gas=300000, max_gas_price=10,
                  gas_budget=10**7)


def gates(now):
    return Gates(1, 1, 7, now, now + 10, audit_durable=True, reservation_valid=True, version_valid=True,
                 risk_valid=True, health_valid=True, token_market_open=True, underlying_market_open=True,
                 clock_trusted=True)


class FakeRpc:
    mode = 'live'

    def __init__(self, decoder, wallet, pay, amount, **overrides):
        self.calls, self.fail = [], None
        self.storage = '0x' + '0' * 23 + '2' + decoder.facet[2:]
        self.code = {decoder.router: '0x' + ROUTER_CODE.hex(), decoder.facet: '0x' + FACET_CODE.hex()}
        self.allowances = {t: 0 for t in u.TOKENS}
        self.allowances[pay] = amount
        self.wallet, self.router = wallet, decoder.router
        for key, value in overrides.items():
            setattr(self, key, value)

    def call(self, method, params):
        self.calls.append((method, params))
        if self.fail is not None:
            raise self.fail
        if method == 'eth_getBlockByNumber':
            return dict(number='0x10')
        assert params[-1] == '0x10', 'reads must use the numeric block'
        if method == 'eth_getStorageAt':
            assert params[:2] == [self.router, u.selector_slot(u.SWAP_SELECTOR, u.DIAMOND_STORAGE_BASE)]
            return self.storage
        if method == 'eth_getCode':
            return self.code.get(params[0], '0x')
        if method == 'eth_call':
            call = params[0]
            assert call['data'] == u.ALLOWANCE_CALL + self.wallet[2:].rjust(64, '0') + self.router[2:].rjust(64, '0')
            return word(self.allowances[call['to']])
        raise AssertionError(method)


class Decode(unittest.TestCase):  # U1, U2
    def setUp(self):
        self.decoder = u.UntrustedRouterDecoder(policy())
        self.quotes = quotes()

    def test_u1_all_recorded_quotes_decode_to_their_quote(self):
        self.assertEqual(len(self.quotes), 15)
        for params, tx in ((p, t) for _, p, t in self.quotes):
            with self.subTest(tx['data'][:74]):
                e = self.decoder.decode(swap(params, tx))
                self.assertEqual((e.pay_token, e.receive_token, e.amount, e.minimum_output, e.recipient),
                                 (params['fromTokenAddress'].lower(), params['toTokenAddress'].lower(),
                                  int(params['amount']), int(tx['minReceiveAmount']), None))
                self.assertGreater(e.deadline, 1_790_000_000)

    def test_u2_every_tampered_copy_is_refused(self):
        for _, params, tx in self.quotes:
            for name, data in u.mutations(tx['data']).items():
                with self.subTest(name), self.assertRaises(Blocked):
                    self.decoder.decode(swap(params, tx, data=data))

    def test_u2_other_router_and_report(self):
        _, params, tx = self.quotes[0]
        with self.assertRaises(Blocked):
            self.decoder.decode(swap(params, tx, to='0x' + 'cd' * 20))
        report = u.check(self.decoder, QUOTES)
        self.assertEqual((report['status'], report['quotes'], report['signing_enabled']), ('PASS', 15, False))

    def test_policy_refusals(self):
        cases = {
            'slot not the selector slot': dict(facet_slot=word(1)),
            'offset word not pinned': dict(fixed_words={'2': policy()['fixed_words']['2']}),
            'economic word pinned': dict(fixed_words=dict(policy()['fixed_words'], **{'4': word(1)})),
            'review left as drafted': dict(review=dict(reviewed_by=u.REVIEW_REQUIRED, review_ref='x')),
            'router is a token': dict(router=USDT),
            'extra key': dict(observed=1),
        }
        for name, change in cases.items():
            with self.subTest(name), self.assertRaises(ContractError):
                u.validate_policy(dict(policy(), **change) if name != 'extra key' else {**policy(), **change})


class Preflight(unittest.TestCase):  # U3
    def setUp(self):
        self.decoder = u.UntrustedRouterDecoder(policy())
        _, self.params, self.tx = quotes()[0]
        self.intent = swap_intent(self.params, self.tx, self.decoder)
        self.payload = swap(self.params, self.tx)

    def bound(self, **overrides):
        rpc = FakeRpc(self.decoder, self.intent.wallet, self.intent.pay_token, self.intent.amount, **overrides)
        return u.UntrustedRouterDecoder(policy()).bind(rpc), rpc

    def test_u3_all_correct_passes_with_allowlisted_reads(self):
        decoder, rpc = self.bound()
        decoder.preflight(self.intent, self.payload)
        self.assertEqual({m for m, _ in rpc.calls}, {'eth_getBlockByNumber', 'eth_getStorageAt', 'eth_getCode', 'eth_call'})
        self.assertEqual(sum(m == 'eth_call' for m, _ in rpc.calls), len(u.TOKENS))
        from larp.execution_live.chain import METHODS, balance_call
        for method, params in rpc.calls:
            if method == 'eth_call':
                balance_call(params)  # the production RPC allow-list accepts every preflight read
            else:
                self.assertIn(method, METHODS)
        decoder, _ = self.bound(allowances=dict({t: 0 for t in u.TOKENS}))
        decoder.preflight(self.intent, self.payload)  # zero is within the limit
        leftover = dict({t: 0 for t in u.TOKENS}, **{self.intent.pay_token: 10 * self.intent.amount})
        decoder, _ = self.bound(allowances=leftover)
        decoder.preflight(self.intent, self.payload, approved=False)  # our approve overwrites the pay allowance
        with self.assertRaises(Blocked):
            decoder.preflight(self.intent, self.payload)  # but not once approved
        other = sorted(u.TOKENS - {self.intent.pay_token})[0]
        decoder, _ = self.bound(allowances=dict({t: 0 for t in u.TOKENS}, **{other: 1}))
        with self.assertRaises(Blocked):
            decoder.preflight(self.intent, self.payload, approved=False)  # another token's leftover always refuses

    def test_u3_refusals(self):
        other = sorted(u.TOKENS - {self.intent.pay_token})[0]
        cases = {
            'facet replaced': dict(storage=word(0xdead)),
            'router code changed': dict(code={self.decoder.router: '0x60', self.decoder.facet: '0x' + FACET_CODE.hex()}),
            'facet code changed': dict(code={self.decoder.router: '0x' + ROUTER_CODE.hex(), self.decoder.facet: '0x60'}),
            'facet has no code': dict(code={self.decoder.router: '0x' + ROUTER_CODE.hex()}),
            'other token allowance': dict(allowances=dict({t: 0 for t in u.TOKENS}, **{other: 1})),
            'pay allowance above amount': dict(allowances=dict({t: 0 for t in u.TOKENS},
                                                               **{self.intent.pay_token: self.intent.amount + 1})),
        }
        for name, overrides in cases.items():
            decoder, _ = self.bound(**overrides)
            with self.subTest(name), self.assertRaises(Blocked):
                decoder.preflight(self.intent, self.payload)
        decoder, rpc = self.bound()
        rpc.fail = DependencyUnavailable('RPC unavailable')
        with self.assertRaises(DependencyUnavailable):
            decoder.preflight(self.intent, self.payload)
        with self.assertRaises(Blocked):
            u.UntrustedRouterDecoder(policy()).preflight(self.intent, self.payload)  # unbound: signer side


class Port:
    def __init__(self, mode):
        self.mode = mode


class Wiring(unittest.TestCase):  # U4
    def setUp(self):
        self.decoder = u.UntrustedRouterDecoder(policy())
        _, self.params, self.tx = quotes()[0]
        self.intent = swap_intent(self.params, self.tx, self.decoder)
        self.payload = swap(self.params, self.tx)
        self.now = self.intent.valid_until - 100

    def test_u4_executor_needs_a_bound_decoder(self):
        with self.assertRaises(Blocked):
            Executor(object(), Port('live'), Port('live'), Port('live'), self.decoder)
        rpc = FakeRpc(self.decoder, self.intent.wallet, self.intent.pay_token, self.intent.amount)
        Executor(object(), Port('live'), Port('live'), Port('live'), self.decoder.bind(rpc))

    def test_u4_every_swap_validation_runs_preflight(self):
        rpc = FakeRpc(self.decoder, self.intent.wallet, self.intent.pay_token, self.intent.amount)
        executor = Executor(object(), Port('live'), Port('live'), Port('live'), self.decoder.bind(rpc))
        state = SimpleNamespace(intent=self.intent, last_observed_at=0, attempts=())
        rpc.allowances[self.intent.pay_token] = 10 * self.intent.amount  # before the approve: not limited
        executor._validate(state, 'SWAP', self.payload, gates(self.now), self.now)
        self.assertTrue(any(m == 'eth_getStorageAt' for m, _ in rpc.calls))
        rpc.allowances[self.intent.pay_token] = self.intent.amount
        rpc.storage = word(0xdead)
        with self.assertRaises(Blocked):
            executor._validate(state, 'SWAP', self.payload, gates(self.now), self.now)

    def test_u4_unverified_recipient_only_from_untrusted_mode(self):
        validate_payload(self.intent, 'SWAP', self.payload, gates(self.now), self.now, self.decoder)

        class Pretender(PinnedRouterDecoder):  # a verified-mode decoder that returns no recipient
            def decode(inner, payload):
                return replace(self.decoder.decode(payload), recipient=None)
        with self.assertRaises(Blocked):
            validate_payload(self.intent, 'SWAP', self.payload, gates(self.now), self.now, Pretender(evidence()))
        caps = SigningPolicy.from_config(dict(
            cap_basis='TEST_FIXTURE', allowed_spenders=[u.ROUTER], allowed_tokens=sorted({USDT} | BSTOCKS),
            max_input_units={t: str(10**24) for t in {USDT} | BSTOCKS}, max_fee_wei=str(10**12)))
        caps.check(self.intent, 'SWAP', self.payload, self.decoder, self.intent.wallet)
        with self.assertRaises(Blocked):
            caps.check(self.intent, 'SWAP', self.payload, Pretender(evidence()), self.intent.wallet)


class Settings(unittest.TestCase):  # U5
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        raw = json.dumps(policy()).encode()
        self.path = Path(tmp.name) / 'untrusted-router.json'
        self.path.write_bytes(raw)
        self.config = dict(untrusted_router_policy_file=str(self.path),
                           untrusted_router_policy_sha256=hashlib.sha256(raw).hexdigest())
        self.caps = lambda spenders: SigningPolicy.from_config(dict(
            cap_basis='TEST_FIXTURE', allowed_spenders=list(spenders), allowed_tokens=[USDT],
            max_input_units={USDT: '1000'}, max_fee_wei='1000'))

    def test_u5_signer_loads_the_pinned_policy_offline(self):
        decoder = signer_service.router_decoder(self.config, self.caps([u.ROUTER]))
        self.assertEqual((decoder.mode, decoder.rpc), ('untrusted', None))
        self.assertEqual(signer_service._decoder_identity(decoder)['swap_decoder'], 'UNTRUSTED')

    def test_u5_refusals(self):
        from larp.execution_live.config import evidence_settings, untrusted_router_settings
        with self.assertRaises(ContractError):
            signer_service.router_decoder(self.config, self.caps(['0x' + 'cd' * 20]))
        with self.assertRaises(ContractError):
            untrusted_router_settings(dict(untrusted_router_policy_file=str(self.path)))
        with self.assertRaises(ContractError):
            evidence_settings(dict(self.config, router_evidence_file='f', router_evidence_sha256='0' * 64))
        with self.assertRaises(ContractError):
            signer_service.router_decoder(dict(self.config, untrusted_router_policy_sha256='0' * 64),
                                          self.caps([u.ROUTER]))


class GateB(unittest.TestCase):  # DR-02 readiness labels the untrusted mode; never signing permission
    report = gb.ReportTests.report

    def setUp(self):
        gb.ReportTests.setUp(self)
        raw = json.dumps(policy()).encode()
        (self.root / 'untrusted-router.json').write_bytes(raw)
        self.policy_sha = hashlib.sha256(raw).hexdigest()
        path = Path(self.inputs['files']['execution_config']['path'])
        config = dict(json.loads(path.read_bytes()), router=u.ROUTER, untrusted_router_policy_file='untrusted-router.json',
                      untrusted_router_policy_sha256=self.policy_sha)
        path.write_bytes(json.dumps(config).encode())
        self.inputs['files']['execution_config']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()

    def with_check(self, report):
        raw = json.dumps(report).encode()
        (self.root / 'router-check.json').write_bytes(raw)
        return dict(self.inputs, files=dict(self.inputs['files'], router_check=dict(
            path='router-check.json', sha256=hashlib.sha256(raw).hexdigest())))

    def test_dr02_untrusted_policy_and_passing_check(self):
        self.assertEqual(self.report()['checks']['DR-02']['status'], 'BLOCKED')  # no route check supplied
        check = u.check(u.UntrustedRouterDecoder(policy(), policy_sha256=self.policy_sha), QUOTES)
        result = self.report(self.with_check(check))
        self.assertEqual(result['checks']['DR-02']['status'], 'VALIDATED')
        self.assertIn('UNTRUSTED', result['checks']['DR-02']['detail'])
        self.assertFalse(result['signing_enabled'])
        for bad in (dict(check, status='FAIL'), dict(check, policy_sha256='0' * 64), dict(check, quotes=0)):
            with self.subTest(bad=bad['status']):
                self.assertEqual(self.report(self.with_check(bad))['checks']['DR-02']['status'], 'BLOCKED')


class SettlementHold(hs.Split):  # U6, on the halt-split service harness (real PostgreSQL)
    def test_u6_unsettled_fill_withholds_risk_authority(self):
        round_id, i = self.planned_then_halted('DELIVERY_DEADLINE')  # a pausing HALT keeps the mandatory sell valid
        signing = self.signing_intent(round_id, i)
        now = self.w.clock() // hs.SECOND
        self.assertTrue(RunAuthorization(self.store, run_id=hs.RUN, build_id=hs.VERSION,
                                         settlement_hold=lambda: False).facts(signing, now)['risk_valid'])
        self.assertFalse(RunAuthorization(self.store, run_id=hs.RUN, build_id=hs.VERSION,
                                          settlement_hold=lambda: True).facts(signing, now)['risk_valid'])


for name in [n for n in vars(hs.Split) if n.startswith('test_')]:
    setattr(SettlementHold, name, None)  # only U6 runs here; Split's own tests run in their module


if __name__ == '__main__':
    unittest.main()
