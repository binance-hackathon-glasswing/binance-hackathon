"""IDEA-088 QV1-QV5: the UNTRUSTED-router quote verifier (SJ-11-QV01).

Quotes are the real recorded responses in docs/build/evidence/quotes-interim-20261018/selected-raw; the router policy
and live router state are tests/execution/test_untrusted_router.py's fixtures. Nothing calls the network or signs.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest

from larp.contracts import ContractError
from larp.execution import USDT, DependencyUnavailable, Payload, SwapEconomics
from larp.execution_live import untrusted_router as u
from larp.marketdata.port import MarketPort, TOKENS
from larp.marketdata.quote_verifier import GAS_BASIS, ProviderRpc, UntrustedQuoteVerifier
from larp.marketdata.web3 import Unavailable
from larp.risk.planner import _quote_at_cap
from tests.execution.test_untrusted_router import QUOTES, FakeRpc, policy, word
from tests.marketdata.test_live_port import Client

ROOT = Path(__file__).resolve().parents[2]
S1_PROFILE = ROOT / 'docs/build/evidence/s1-rehearsal-profile-20261023/rehearsal-s1-deterministic.json'
SYMBOL = {token: symbol for symbol, token in TOKENS.items()}


def recorded():
    """(record, sha256) of every recorded quote-and-swap response, BUY and SELL."""
    for path in sorted(QUOTES.glob('*.json')):
        raw = path.read_bytes()
        record = json.loads(raw)
        if record['endpoint'] == 'aggregator/quote-and-swap':
            yield dict(record, artifact_sha256=hashlib.sha256(raw).hexdigest())


def side_of(record):
    return 'BUY' if record['params']['fromTokenAddress'] == USDT else 'SELL'


def profile(**changes):
    # The run-3 S1 REHEARSAL profile; the recorded quotes are 40 USDT at 0.5 % slippage, so the cap and limits
    # follow them. Its gas budgets and BNB scale are unchanged.
    value = json.loads(S1_PROFILE.read_bytes())
    value.update(slippage_bps=50, impact_bps=50, per_trade_cap_units=50_000_000)
    value.update(changes)
    return value


class RecordedClient(Client):
    """Synthetic market metadata; the quote endpoint returns one recorded response (or a changed copy)."""

    def __init__(self, record):
        self.record, self.quote_params = record, []

    def request(self, method, endpoint, params):
        if endpoint != 'aggregator/quote-and-swap':
            return super().request(method, endpoint, params)
        self.quote_params.append(params)
        return deepcopy(self.record)


def request_for(record):
    params, buy = record['params'], side_of(record) == 'BUY'
    symbol = SYMBOL[params['toTokenAddress'] if buy else params['fromTokenAddress']]
    amount = int(params['amount'])
    return dict(schema='MarketRequest.v1', symbol=symbol, side=side_of(record), amount_kind='EXACT_IN',
                pay_asset='USDT' if buy else symbol, pay_units=amount // 10**12 if buy else amount,
                pay_decimals=6 if buy else 18, mandatory=not buy)


def changed(record, **tx):
    """A copy whose bytes changed: a new artifact hash, as the client would compute for different bytes."""
    record = deepcopy(record)
    record['response']['data']['tx'].update(tx)
    record['artifact_sha256'] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    return record


class Harness(unittest.TestCase):
    def setUp(self):
        self.records = list(recorded())
        self.buy = next(r for r in self.records if side_of(r) == 'BUY')
        self.sell = next(r for r in self.records if side_of(r) == 'SELL')

    def verifier(self, record, decoder=None, profile_value=None, **rpc):
        params = record['params']
        decoder = decoder or u.UntrustedRouterDecoder(policy())
        self.rpc = FakeRpc(decoder, params['userWalletAddress'].lower(), params['fromTokenAddress'].lower(),
                           0, **rpc)
        decoder.bind(self.rpc)
        return UntrustedQuoteVerifier(decoder, profile_value or profile(), wallet=params['userWalletAddress'],
                                      bnb_decimals=18)

    def observe(self, record, *, verifier=None, limits=None, **rpc):
        wallet = record['params']['userWalletAddress']
        port = MarketPort(RecordedClient(record), wallet, quote_verifier=verifier or self.verifier(record, **rpc),
                          quote_limits=limits or profile(), cost_observation=lambda symbol: None)
        return port.observe(request_for(record))


class Executable(Harness):  # QV1, QV4
    def test_qv1_recorded_buy_and_sell_quotes_become_executable(self):
        p = profile()
        self.assertEqual(len(self.records), 15)
        for record in (self.buy, self.sell):
            with self.subTest(side=side_of(record)):
                row = self.observe(record)
                self.assertEqual(row['quote_status'], 'VERIFIED_EXECUTABLE')
                [quote] = row['quotes']
                tx = record['response']['data']['tx']
                deadline = u.UntrustedRouterDecoder(policy()).decode(
                    Payload(56, record['params']['userWalletAddress'].lower(), tx['to'].lower(), 0, 0, 1, 1,
                            tx['data'])).deadline
                self.assertEqual((quote['gas_bnb_units'], quote['expected_gas_bnb_units']),
                                 (p['gas_action_budget_units'], p['gas_sizing_budget_units']))
                self.assertEqual((quote['fee_units'], quote['slippage_bps'], quote['route_valid']), (0, 50, True))
                self.assertEqual(quote['expires_at'], datetime.fromtimestamp(deadline, timezone.utc).isoformat())
                self.assertEqual(quote['quote_id'], record['artifact_sha256'])
                now = datetime.fromisoformat(record['available_at'].replace('Z', '+00:00'))
                accepted = _quote_at_cap(row, side_of(record), quote['pay_units'], p, now, quote['token_units'],
                                         side_of(record) == 'SELL')
                self.assertIs(accepted[0], quote)

    def test_qv3_preflight_reads_one_numeric_block_on_the_pinned_router(self):
        self.observe(self.buy)
        methods = [m for m, _ in self.rpc.calls]
        self.assertEqual(methods[0], 'eth_getBlockByNumber')
        self.assertEqual(methods.count('eth_call'), len(u.TOKENS))
        self.assertTrue(all(params[-1] == '0x10' for m, params in self.rpc.calls[1:]))

    def test_qv4_profile_must_carry_initial_only_gas_budgets_at_the_ledger_scale(self):
        decoder = u.UntrustedRouterDecoder(policy()).bind(FakeRpc(u.UntrustedRouterDecoder(policy()), '0x' + '1' * 40,
                                                                   USDT, 0))
        base = profile()
        no_sizing = {k: v for k, v in base.items() if k != 'gas_sizing_budget_units'}
        no_action = {k: v for k, v in base.items() if k != 'gas_action_budget_units'}
        for name, value, scale in (('top-up profile', dict(base, initial_gas_only=False), 18),
                                   ('no sizing budget', no_sizing, 18), ('no action budget', no_action, 18),
                                   ('sizing above action', dict(base, gas_sizing_budget_units=base[
                                       'gas_action_budget_units'] + 1), 18),
                                   ('ledger scale', base, 9)):
            with self.subTest(name), self.assertRaises(ContractError):
                UntrustedQuoteVerifier(decoder, value, wallet='0x' + '1' * 40, bnb_decimals=scale)
        with self.assertRaises(ContractError):  # an unbound decoder cannot run the preflight
            UntrustedQuoteVerifier(u.UntrustedRouterDecoder(policy()), base, wallet='0x' + '1' * 40, bnb_decimals=18)

    def test_qv4_fee_authority_proofs_need_an_expected_gas_inside_the_reservation(self):
        verifier = self.verifier(self.buy)
        for change in (dict(expected_gas_bnb_units=None), dict(expected_gas_bnb_units=0),
                       dict(expected_gas_bnb_units=profile()['gas_action_budget_units'] + 1),
                       dict(gas_basis='MEASURED_SOMEWHERE')):
            def altered(*args, change=change):
                proof = dict(verifier(*args), **change)
                return {k: v for k, v in proof.items() if v is not None}
            altered.decoder = verifier.decoder
            with self.subTest(change), self.assertRaises(Unavailable):
                self.observe(self.buy, verifier=altered)


class Refusals(Harness):  # QV2, QV3
    def assertRefused(self, record, **kwargs):
        with self.assertRaises(Unavailable):
            self.observe(record, **kwargs)

    def test_qv2_every_tampered_calldata_copy_is_refused(self):
        data = self.buy['response']['data']['tx']['data']
        for name, tampered in u.mutations(data).items():
            with self.subTest(name):
                self.assertRefused(changed(self.buy, data=tampered))

    def test_qv2_route_identity_and_economics_are_bound(self):
        tx = self.buy['response']['data']['tx']
        minimum = int(tx['minReceiveAmount'])
        for name, record in (
                ('other router', changed(self.buy, to='0x' + 'cd' * 20)),
                ('native value', changed(self.buy, value='1')),
                ('other wallet', changed(self.buy, **{'from': '0x' + '9' * 40})),
                ('lower minimum', changed(self.buy, minReceiveAmount=str(minimum - 1))),
                ('higher minimum', changed(self.buy, minReceiveAmount=str(minimum + 1))),
                ('wider slippage echo', changed(self.buy, slippagePercent='1'))):
            with self.subTest(name):
                self.assertRefused(record)
        for name, update in (('rfq', dict(rfq={'id': 1})), ('mode', dict(executionMode='RFQ'))):
            record = deepcopy(self.buy)
            record['response']['data'].update(update)
            with self.subTest(name):
                self.assertRefused(record)
        for name, update in (('vendor', dict(vendorName='OtherVendor')), ('fee', dict(feeAmount='12'))):
            record = deepcopy(self.buy)
            record['response']['data']['routerResult'].update(update)
            with self.subTest(name):
                self.assertRefused(record)

    def test_qv2_a_quote_whose_deadline_passed_at_retrieval_is_refused(self):
        record = deepcopy(self.buy)
        record['available_at'] = '2027-01-01T00:00:00Z'
        self.assertRefused(record)

    def test_qv2_the_proof_is_bound_to_the_response_bytes(self):
        verifier = self.verifier(self.buy)

        def other_bytes(raw, request, observation):
            return dict(verifier(raw, request, observation), source_hash='0' * 64)
        other_bytes.decoder = verifier.decoder
        self.assertRefused(self.buy, verifier=other_bytes)

    def test_qv3_live_router_state_must_match_the_pinned_policy(self):
        decoder = u.UntrustedRouterDecoder(policy())
        other_facet = '0x' + '0' * 24 + '2' * 40
        for name, rpc in (('facet', dict(storage=other_facet)),
                          ('router code', dict(code={decoder.router: '0x60', decoder.facet: '0x' + b'\x60\x80facet'.hex()})),
                          ('facet code', dict(code={decoder.router: '0x' + b'\x60\x80router'.hex(), decoder.facet: '0x60'})),
                          ('dirty allowance', dict(allowances={**{t: 0 for t in u.TOKENS}, u.ROUTER: 0,
                                                               next(t for t in sorted(u.TOKENS) if t != USDT): 1}))):
            with self.subTest(name):
                self.assertRefused(self.buy, **rpc)
        verifier = self.verifier(self.buy)
        self.rpc.fail = DependencyUnavailable('RPC unavailable')
        self.assertRefused(self.buy, verifier=verifier)


class Recipient(Harness):  # QV5
    def test_qv5_an_unverified_recipient_needs_the_untrusted_decoder(self):
        verifier = self.verifier(self.buy)

        def no_decoder(*args):
            return verifier(*args)
        self.assertEqual(verifier(*self._args())['economics'].recipient, None)
        with self.assertRaises(Unavailable):
            self.observe(self.buy, verifier=no_decoder)

        class Pinned:
            mode = 'pinned'
        no_decoder.decoder = Pinned()
        with self.assertRaises(Unavailable):
            self.observe(self.buy, verifier=no_decoder)

    def _args(self):
        client = RecordedClient(self.buy)
        raw = client.request('GET', 'aggregator/quote-and-swap', {})
        return raw, request_for(self.buy), {}


class Failover(unittest.TestCase):
    def test_providers_are_tried_in_order_and_only_on_unavailability(self):
        class Provider:
            def __init__(self, result):
                self.result, self.calls = result, 0

            def call(self, method, params):
                self.calls += 1
                if isinstance(self.result, Exception):
                    raise self.result
                return self.result
        down, up, last = Provider(DependencyUnavailable('RPC unavailable')), Provider('0x1'), Provider('0x2')
        self.assertEqual(ProviderRpc([down, up, last]).call('eth_chainId', []), '0x1')
        self.assertEqual((down.calls, up.calls, last.calls), (1, 1, 0))
        from larp.execution import Blocked
        with self.assertRaises(Blocked):
            ProviderRpc([Provider(Blocked('RPC response rejected')), up]).call('eth_chainId', [])
        with self.assertRaises(DependencyUnavailable):
            ProviderRpc([down]).call('eth_chainId', [])
        self.assertEqual(ProviderRpc([up]).mode, 'live')
        with self.assertRaises(ContractError):
            ProviderRpc([])


if __name__ == '__main__':
    unittest.main()
