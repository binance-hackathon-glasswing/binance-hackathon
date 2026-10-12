"""I4 acceptance against the actual runtime validator after PR #13 integration."""
from dataclasses import replace
import unittest
from larp.execution_live.service import broadcast_observation
from larp.execution_live.settlement import final_observation
from larp import ports
from tests.execution import test_settlement as fixtures


@unittest.skipUnless(hasattr(ports,'validate_execution_observation'), 'runtime I4 consumer awaits PR13 integration')
class RuntimeConsumer(unittest.TestCase):
    def test_broadcast_and_receipts_pass_actual_consumer(self):
        f = fixtures.SettlementTests(); f.setUp()
        for step in ('APPROVE', 'SWAP'):
            attempt = replace(f.attempt, step=step)
            broadcast = broadcast_observation(f.state,attempt,wallet_id='fake-wallet')
            ports.validate_execution_observation(broadcast)
            self.assertEqual(broadcast['step'],step.lower())
            self.assertNotIn('settlement',broadcast)
            for status in ('0x1', '0x0'):
                f.proof['receipt']['status'] = status
                fact = final_observation(f.state,attempt,f.proof,wallet_id='fake-wallet',
                                        bnb_price_units=700000000,observed_at=fixtures.STAMP)
                ports.validate_execution_observation(fact)
                self.assertFalse(fact['round_terminal'])  # one receipt cannot attest a whole round
