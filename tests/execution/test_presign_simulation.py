"""IDEA-070 KG-DEC-01: a swap whose exact payload fails simulation is refused before any attempt, authority or
signature exists. The simulation is the mandatory exact-payload gas estimate in Executor.prepare (no fallback)."""
from pathlib import Path
import tempfile
import unittest

from larp.execution import Blocked, DependencyUnavailable, Executor
from larp.execution_live.venue import LiveVenue
from larp.marketdata.web3 import Unavailable
from tests.execution_fixtures import (FakeDecoder, FakeGuards, FakeSigner, FakeVenue, SQLiteFixture, finalized,
                                      intent)


class PreSignSimulation(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = SQLiteFixture(Path(self.directory.name) / 'fixture.sqlite')
        self.addCleanup(self.store.close)
        self.guards, self.signer = FakeGuards(self.store), FakeSigner(self.store)
        self.venue = FakeVenue(self.store)
        self.engine = Executor(self.store, self.guards, self.venue, self.signer, FakeDecoder())
        self.economic = intent()
        self.key = self.economic.key

    def approved(self):
        """Approval final; the next prepare quotes and simulates the swap."""
        self.engine.create(self.economic, 10)
        self.engine.prepare(self.key, 10)
        self.engine.authorize(self.key, 10)
        self.engine.sign(self.key, 10)
        state = self.engine.broadcast(self.key, 11)
        self.venue.outcomes[state.attempts[-1].tx_hash] = finalized(state.attempts[-1])
        self.engine.reconcile(self.key, 12)
        self.guards.nonce = 1
        return self.signer.calls

    def refuse(self, failure, reason):
        signed_before = self.approved()

        def estimate(payload):
            raise failure
        self.venue.estimate_gas = estimate
        state = self.engine.prepare(self.key, 13)
        self.assertEqual([a.step for a in state.attempts], ['APPROVE'])  # no SWAP attempt exists
        self.assertIn(reason, state.blocked_reason)
        self.assertEqual(self.engine.authorize(self.key, 13).attempts, state.attempts)
        self.assertEqual(self.engine.sign(self.key, 13).attempts, state.attempts)
        self.assertEqual(self.signer.calls, signed_before)  # nothing was offered to the signer
        self.assertEqual(len(self.venue.broadcasts), 1)  # only the approval

    def test_reverting_rfq_swap_is_refused_before_signing(self):
        self.refuse(Blocked('execution reverted: RFQ_OrderExpired'), 'RFQ_OrderExpired')

    def test_min_return_revert_is_refused_before_signing(self):
        self.refuse(Blocked('execution reverted: Min return not reached'), 'Min return not reached')

    def test_unavailable_simulation_is_a_refusal_not_a_pass(self):
        self.refuse(DependencyUnavailable('venue dependency unavailable'), 'venue dependency unavailable')
        self.refuse_timeout()

    def refuse_timeout(self):
        def estimate(payload):
            raise TimeoutError()
        self.venue.estimate_gas = estimate
        state = self.engine.prepare(self.key, 14)
        self.assertEqual([a.step for a in state.attempts], ['APPROVE'])
        self.assertEqual(state.blocked_reason, 'quote/gas dependency unavailable')

    def test_a_missing_estimate_never_falls_back_to_the_quote_gas(self):
        self.approved()
        self.venue.estimate = None
        state = self.engine.prepare(self.key, 13)
        self.assertEqual([a.step for a in state.attempts], ['APPROVE'])


class LiveVenueSimulation(unittest.TestCase):
    """The live estimate is the Web3 API's exact-payload gas-limit call; its failures surface as refusals."""
    def venue(self, request):
        client = type('Client', (), {'request': staticmethod(request)})()
        return LiveVenue(client, chain=None, decoder=FakeDecoder())

    def payload(self):
        from tests.execution_fixtures import WALLET, ROUTER
        from larp.execution import Payload
        return Payload(56, WALLET, ROUTER, 0, 1, 100000, 1, '0xad43f73d00')

    def test_api_failure_and_non_positive_estimate_refuse(self):
        def reverted(*args):
            raise Unavailable('execution_reverted')
        with self.assertRaises(DependencyUnavailable):
            self.venue(reverted).estimate_gas(self.payload())
        with self.assertRaises(Blocked):
            self.venue(lambda *a: {'response': {'data': [{'gasLimit': '0'}]}}).estimate_gas(self.payload())
        self.assertEqual(self.venue(lambda *a: {'response': {'data': [{'gasLimit': '731144'}]}}).estimate_gas(self.payload()), 731144)


if __name__ == '__main__':
    unittest.main()
