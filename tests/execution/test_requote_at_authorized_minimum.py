"""IDEA-090 F11-F14 (S2-F6): the post-approve swap requote at the authorized minimum.

Run 4, 07:15Z: the approve confirmed but no swap was sent. After the approve, the execution service re-quotes the swap
with the same slippage as the planning quote, and `validate_payload` requires the fresh minimum to reach the intent's
authorized minimum, so any adverse move between planning and the swap blocked it. Synthetic Web3 responses that apply
the requested slippage; no venue, chain or key.
"""
from dataclasses import asdict, replace
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from larp.execution import Blocked, Executor, SwapEconomics, canonical
from larp.execution_live.venue import LiveVenue
from tests.execution_fixtures import (FakeDecoder, FakeGuards, FakeSigner, FakeVenue, SQLiteFixture, finalized,
                                      intent)

SLIPPAGE_BPS = 8
PLANNED = 1_000_000  # the planning quote's output
AUTHORIZED = PLANNED * (10000 - SLIPPAGE_BPS) // 10000  # the intent's minimum: 999200


def authorized_intent(**changes):
    return intent(**{**dict(minimum_output=AUTHORIZED, max_slippage_bps=SLIPPAGE_BPS), **changes})


class Wire:
    """aggregator/quote-and-swap: each call returns the next output (the last repeats), with the minimum the API
    derives from the requested slippage."""

    def __init__(self, i, outputs, *, vendor='LiquidMesh', minimum=None):
        self.i, self.outputs, self.vendor, self.minimum = i, list(outputs), vendor, minimum
        self.slippages = []

    def request(self, method, endpoint, params):
        assert (method, endpoint) == ('GET', 'aggregator/quote-and-swap')
        self.slippages.append(params['slippagePercent'])
        bps = int(Decimal(params['slippagePercent']) * 100)
        output = self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]
        minimum = self.minimum(output, bps) if self.minimum else output * (10000 - bps) // 10000
        economics = SwapEconomics(self.i.pay_token, self.i.receive_token, self.i.amount, self.i.wallet, minimum,
                                  self.i.valid_until, 0)
        return dict(response=dict(data=dict(
            executionMode='SWAP', routerResult=dict(vendorName=self.vendor, toTokenAmount=str(output)),
            tx=dict(minReceiveAmount=str(minimum), to=self.i.router, value='0', gas='100000', gasPrice='1',
                    data='0xfafafafa' + canonical(asdict(economics)).encode().hex()))))


def bps(percent):
    return Decimal(percent) * 100


class VenueRequote(unittest.TestCase):
    def quote(self, outputs, **wire):
        i = authorized_intent()
        client = Wire(i, outputs, **wire)
        venue = LiveVenue(client, None, decoder=FakeDecoder())
        try:
            payload = venue.quote(i, 0)
        except Blocked as error:
            return None, client.slippages, error
        return FakeDecoder().decode(payload), client.slippages, None

    def test_f11_f12_an_adverse_move_inside_the_limit_is_requoted_at_the_authorized_minimum(self):
        for fresh in (999_500, 999_300, 999_900, 999_999):
            with self.subTest(fresh=fresh):
                economics, slippages, error = self.quote([fresh])
                self.assertIsNone(error)
                self.assertGreaterEqual(economics.minimum_output, AUTHORIZED)
                self.assertEqual(len(slippages), 2)
                self.assertEqual(bps(slippages[0]), SLIPPAGE_BPS)
                second = bps(slippages[1])
                self.assertEqual(second, second.to_integral_value())  # whole bps
                self.assertTrue(1 <= second < SLIPPAGE_BPS, second)
                self.assertTrue(all(bps(s) <= SLIPPAGE_BPS for s in slippages))

    def test_f13_one_request_when_the_first_quote_already_meets_the_minimum(self):
        for fresh in (PLANNED, PLANNED + 5_000):
            with self.subTest(fresh=fresh):
                economics, slippages, error = self.quote([fresh])
                self.assertIsNone(error)
                self.assertEqual([bps(s) for s in slippages], [SLIPPAGE_BPS])
                self.assertEqual(economics.minimum_output, fresh * (10000 - SLIPPAGE_BPS) // 10000)

    def test_f13_no_second_request_below_the_authorized_minimum_or_at_zero_bps(self):
        for fresh in (AUTHORIZED - 1, 990_000, AUTHORIZED, AUTHORIZED + 99):
            with self.subTest(fresh=fresh):
                economics, slippages, error = self.quote([fresh])
                self.assertEqual([bps(s) for s in slippages], [SLIPPAGE_BPS])
                self.assertIsNone(error)  # the venue returns the quote; validate_payload blocks it as before
                self.assertLess(economics.minimum_output, AUTHORIZED)

    def test_f14_the_second_quote_goes_through_every_existing_check(self):
        # The output fell again between the two requests: the second minimum still misses; returned, then blocked.
        economics, slippages, error = self.quote([999_500, 999_000])
        self.assertEqual(len(slippages), 2)
        self.assertLess(economics.minimum_output, AUTHORIZED)
        # A second response from another vendor, or with a minimum wider than its own slippage, is refused.
        _, slippages, error = self.quote([999_500], vendor='Other')
        self.assertRegex(str(error), 'unexpected quote vendor')
        self.assertEqual(len(slippages), 1)
        calls = []

        def loose(output, requested):
            calls.append(requested)
            if len(calls) == 1:
                return output * (10000 - requested) // 10000
            return output * (10000 - SLIPPAGE_BPS) // 10000 - 1  # wider than the intent's own limit
        _, slippages, error = self.quote([999_500], minimum=loose)
        self.assertRegex(str(error), 'slippage limit')
        self.assertEqual(len(slippages), 2)


class ExecutorRequote(unittest.TestCase):
    """The executor path of run 4's buy: prepare and send the approve, finalize it, then prepare the swap."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = SQLiteFixture(Path(directory.name) / 'state.db')
        self.addCleanup(self.store.close)

    def swap_after_approve(self, outputs):
        i = authorized_intent()
        client = Wire(i, outputs)
        live = LiveVenue(client, None, decoder=FakeDecoder())
        store = self.store

        class Venue(FakeVenue):
            def quote(self, economic_intent, nonce):
                return live.quote(economic_intent, nonce)
        venue, guards = Venue(store), FakeGuards(store)
        executor = Executor(store, guards, venue, FakeSigner(store), FakeDecoder())
        executor.create(i, 10)
        approve = executor.prepare(i.key, 11).attempts[-1]
        self.assertEqual(approve.step, 'APPROVE')
        executor.authorize(i.key, 12)
        executor.sign(i.key, 13)
        sent = executor.broadcast(i.key, 14).attempts[-1]
        venue.outcomes[sent.tx_hash] = finalized(sent)
        self.assertEqual(executor.reconcile(i.key, 15).attempts[-1].state, 'FINAL_SUCCESS')
        guards.nonce = 1
        return executor.prepare(i.key, 16), client.slippages

    def test_f11_the_swap_is_prepared_after_an_adverse_move_inside_the_limit(self):
        state, slippages = self.swap_after_approve([PLANNED, 999_500])
        self.assertIsNone(state.blocked_reason)
        swap = state.attempts[-1]
        self.assertEqual((swap.step, swap.state), ('SWAP', 'PREPARED'))
        self.assertGreaterEqual(FakeDecoder().decode(swap.payload).minimum_output, AUTHORIZED)
        self.assertEqual([bps(s) for s in slippages], [SLIPPAGE_BPS, SLIPPAGE_BPS, 3])

    def test_f14_below_the_authorized_minimum_the_swap_is_still_blocked(self):
        state, slippages = self.swap_after_approve([PLANNED, AUTHORIZED - 1])
        self.assertEqual(state.attempts[-1].step, 'APPROVE')
        self.assertIn('swap economics', state.blocked_reason)
        self.assertEqual([bps(s) for s in slippages], [SLIPPAGE_BPS, SLIPPAGE_BPS])


if __name__ == '__main__':
    unittest.main()
