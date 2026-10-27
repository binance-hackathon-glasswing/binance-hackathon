"""IDEA-104 OBS03-B2-RQ01: execution refuses RFQ-maker quotes and re-quotes within the original authority.

RV01 (read-only, 30 quotes) found RFQ routes named in `routerResult.dexRouterList[].dexProtocol.dexName` and executable
for only about 1.5 s after the quote. Synthetic Web3 responses and the LD06 harness only; no venue, chain or key.
"""
from dataclasses import replace
import tempfile
import unittest

from larp.execution import Blocked, DependencyUnavailable, NATIVE_BNB
from larp.execution_live.venue import LiveVenue, dex_names
from larp.marketdata.port import TOKENS, MarketPort
from tests.execution import test_allowance_recovery as recovery
from tests.execution.test_requote_at_authorized_minimum import AUTHORIZED, Wire, authorized_intent
from tests.execution_fixtures import FakeDecoder

AMM_NAMES = ('Tessera V', 'Metric V2', 'Pancakeswap V3', 'Uniswap V3', 'Uniswap V4', 'Elfomofi')  # RV01


class RoutedWire(Wire):
    """Wire with route legs: `routes` gives each call's leg names (the last repeats); None omits the list."""

    def __init__(self, i, outputs, routes, **kwargs):
        super().__init__(i, outputs, **kwargs)
        self.routes, self.params = list(routes), []

    def request(self, method, endpoint, params):
        self.params.append(dict(params))
        response = super().request(method, endpoint, params)
        names = self.routes.pop(0) if len(self.routes) > 1 else self.routes[0]
        if names is not None:
            response['response']['data']['routerResult']['dexRouterList'] = [
                dict(dexProtocol=dict(dexName=name, percent='50.00'), fromTokenIndex='0') for name in names]
        return response


def rfq_refusal():
    """The exact error LiveVenue raises for an RFQ quote, for the executor harness below."""
    i = authorized_intent()
    try:
        LiveVenue(RoutedWire(i, [1_000_000], [['Rfq Neptunex']]), None, decoder=FakeDecoder()).quote(i, 0)
    except DependencyUnavailable as error:
        return error
    raise AssertionError('RFQ quote was not refused')


class VenueRefusal(unittest.TestCase):
    def quote(self, routes, outputs=(1_000_000,)):
        i = authorized_intent()
        client = RoutedWire(i, outputs, routes)
        venue = LiveVenue(client, None, decoder=FakeDecoder())
        try:
            venue.quote(i, 0)
        except Blocked as error:
            return venue, i, client, error
        return venue, i, client, None

    def test_rq1_any_rfq_leg_is_refused_as_a_dependency_outcome(self):
        for names in (['Rfq Neptunex'], ['RFQ Neptunex'], ['Pancakeswap V3', 'rfq maker'], ['PcsXRfq'],
                      [' Rfq Other ']):
            with self.subTest(names=names):
                venue, i, client, error = self.quote([names])
                self.assertIsInstance(error, DependencyUnavailable)
                self.assertEqual(str(error), 'fresh quote uses an RFQ maker route')
                self.assertNotIn(i.key, venue.vendors)
                with self.assertRaisesRegex(Blocked, 'fresh validated quote required before approval'):
                    venue.approve(i, 1)
                self.assertEqual(len(client.slippages), 1)  # no tighter second request after a refusal

    def test_rq1_amm_routes_and_responses_without_names_pass(self):
        for routes in ([list(AMM_NAMES)], [[name] for name in AMM_NAMES], [None], [[]]):
            with self.subTest(routes=routes[0]):
                venue, i, client, error = self.quote(routes)
                self.assertIsNone(error)
                self.assertEqual(venue.vendors[i.key], 'LiquidMesh')

    def test_rq1_rfq_on_the_tighter_second_request_is_refused(self):
        # IDEA-090: an adverse fresh output inside the limit triggers a second request; it is RFQ-routed this time.
        venue, i, client, error = self.quote([['Tessera V'], ['Rfq Neptunex']], outputs=(999_500,))
        self.assertEqual(len(client.slippages), 2)
        self.assertIsInstance(error, DependencyUnavailable)
        self.assertNotIn(i.key, venue.vendors)

    def test_rq1_a_refusal_clears_an_earlier_validated_vendor(self):
        i = authorized_intent()
        client = RoutedWire(i, [1_000_000], [['Tessera V'], ['Rfq Neptunex']])
        venue = LiveVenue(client, None, decoder=FakeDecoder())
        venue.quote(i, 0)
        self.assertIn(i.key, venue.vendors)
        with self.assertRaises(DependencyUnavailable):
            venue.quote(i, 0)
        self.assertNotIn(i.key, venue.vendors)

    def test_rq6_every_execution_quote_request_asks_for_no_rfq(self):
        # Both IDEA-090 requests (the second at the tighter slippage) carry enableRFQ=false.
        venue, i, client, error = self.quote([['Tessera V']], outputs=(999_500,))
        self.assertIsNone(error)
        self.assertEqual(len(client.params), 2)
        self.assertTrue(all(p['enableRFQ'] == 'false' for p in client.params))

    def test_rq6_planning_quotes_ask_for_no_rfq(self):
        class Client:
            def __init__(self):
                self.calls = []

            def request(self, method, endpoint, params):
                self.calls.append((method, endpoint, params))
                return {}
        client = Client()
        port = MarketPort(client, '0x' + 'ab' * 20)
        for symbol in TOKENS:
            for side in ('BUY', 'SELL'):
                port.quote(symbol, side, 10**18, 18)
        self.assertEqual(len(client.calls), 10)
        for method, endpoint, params in client.calls:
            self.assertEqual((method, endpoint, params['enableRFQ'], params['vendor']),
                             ('GET', 'aggregator/quote-and-swap', 'false', 'LiquidMesh'))

    def test_native_gas_topup_quote_parameters_are_unchanged(self):
        i = replace(authorized_intent(), kind='GAS_TOP_UP', receive_token=NATIVE_BNB)
        client = RoutedWire(i, [1_000_000], [['Pancakeswap V3']])
        LiveVenue(client, None, decoder=FakeDecoder()).quote(i, 0)
        self.assertTrue(client.params)
        self.assertTrue(all('enableRFQ' not in p for p in client.params))

    def test_dex_names_reads_nested_legs_only_as_strings(self):
        rr = dict(vendorName='LiquidMesh', dexRouterList=[dict(dexProtocol=dict(dexName='A')),
                                                          dict(subRouterList=[dict(dexProtocol=dict(dexName='B'))]),
                                                          dict(dexProtocol=dict(dexName=7))])
        self.assertEqual(list(dex_names(rr)), ['A', 'B'])
        self.assertEqual(list(dex_names(None)), [])


class RfqVenue(recovery.Venue):
    """LD06 harness venue whose next `rfq` quotes are RFQ-routed (refused exactly as LiveVenue refuses them)."""

    rfq = 0

    def quote(self, i, nonce):
        if self.rfq:
            self.rfq -= 1
            self.quote_calls += 1
            raise rfq_refusal()
        return super().quote(i, nonce)


class ExecutorRefusal(unittest.TestCase):
    def harness(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        h = recovery.Harness(tmp.name)
        self.addCleanup(h.close)
        h.venue = RfqVenue(h.store)
        h.restart()
        return h

    def test_rq2_rfq_before_the_approve_prepares_nothing_then_requotes(self):
        h = self.harness(); i = h.intent()
        h.executor.create(i, h.now)
        h.venue.rfq = 1
        h.now += 1
        state = h.executor.prepare(i.key, h.now)
        self.assertEqual((state.status, state.abort_pending, state.attempts), ('ACTIVE', False, ()))
        self.assertEqual(state.prepare_probes, 1)
        self.assertEqual(state.blocked_reason, 'fresh quote uses an RFQ maker route')
        self.assertEqual(state.intent, i)
        self.assertEqual(h.venue.broadcasts, [])
        state = h.finish_step(i)  # the next quote is an AMM route
        self.assertEqual([a.step for a in state.attempts], ['APPROVE'])
        self.assertEqual(state.prepare_probes, 0)  # a finalized approve starts the swap step's own budget

    def test_rq3_rfq_after_the_approve_keeps_the_approval_then_swaps(self):
        h = self.harness(); i = h.intent()
        h.executor.create(i, h.now)
        h.finish_step(i)
        h.venue.rfq = 1
        h.now += 1
        state = h.executor.prepare(i.key, h.now)
        self.assertEqual((state.status, state.abort_pending), ('ACTIVE', False))
        self.assertEqual([a.step for a in state.attempts], ['APPROVE'])
        self.assertEqual(len(h.venue.broadcasts), 1)
        state = h.finish_step(i)
        self.assertEqual([a.step for a in state.attempts], ['APPROVE', 'SWAP'])
        self.assertEqual(state.status, 'COMPLETED')
        self.assertEqual(state.intent, i)

    def test_rq3_persistent_rfq_exhausts_the_budget_into_existing_cleanup(self):
        h = self.harness(); i = h.intent()
        h.executor.create(i, h.now)
        h.finish_step(i)
        h.venue.rfq = 100
        while True:
            h.now += 1
            try:
                state = h.executor.prepare(i.key, h.now)
            except Blocked as error:
                self.assertRegex(str(error), 'prepare probe budget exhausted')
                break
            self.assertFalse(state.abort_pending)
            self.assertEqual(len(state.attempts), 1)
        self.assertEqual(state.prepare_probes, i.max_prepare_probes)
        state = h.executor.abort_unsigned(i.key, h.now)
        self.assertTrue(state.abort_pending)
        self.assertEqual(state.intent, i)
        self.assertEqual(len(h.venue.broadcasts), 1)  # only the approve; nothing new was signed or sent


if __name__ == '__main__':
    unittest.main()
