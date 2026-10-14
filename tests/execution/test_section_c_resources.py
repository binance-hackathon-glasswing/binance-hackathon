"""C-REQ-017/018/028: journaled pay-token and gas reserves, real PostgreSQL."""
from larp.execution import Attempt, Execution, Payload, USDT
from larp.execution_live.loop import RunAuthorization
from larp.execution_live.store import ExecutionStore
from larp.marketdata.port import TOKENS
from larp.runtime.coordinator import batch_for
from tests.execution_fixtures import intent, ROUTER
from tests.support import DatabaseCase


class Resources(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.economic = intent(amount=100 * 10**12, gas_budget=2 * 10**12)
        self.registry = ExecutionStore(self.store, run_id='run', wallet=self.economic.wallet)
        self.authority = RunAuthorization(self.store, run_id='run', build_id='version')

    def planned(self, *, pay=100, gas=2, pay_asset='USDT', reserve_intent=None,
                scale=6, mode='dev', sell=False):
        if sell:
            self.economic = intent(pay_token=TOKENS['NVDAB'], receive_token=USDT,
                                   amount=100, gas_budget=2 * 10**12)
        record = dict(plan=dict(intents=[dict(intent_id=self.economic.intent_id)]), final_intents=[])
        projection = self.store.load('run').read()['projection']
        projection['balances']['NVDAB'] = 100
        projection['portfolio'] = {} if scale is None else dict(bnb_decimals=scale)
        projection['round_records'] = {self.economic.round_id: record}
        deltas = [dict(intent_id=reserve_intent or self.economic.intent_id, asset=asset, units=units)
                  for asset, units in ((pay_asset, pay), ('BNB', gas)) if units]
        self.store.commit(batch_for(self.store.load('run'), 'plan:' + self.economic.round_id,
            dict(kind='ROUND_PLANNED', record=record), projection=projection, reservation_deltas=deltas))
        with self.store.transaction() as db:
            db.execute('UPDATE runs SET mode=%s WHERE run_id=%s', (mode, 'run'))

    def valid(self):
        return self.authority.facts(self.economic, 12)['reservation_valid']

    def test_c_req_017_018_matching_non18_reserves_are_valid(self):
        self.planned()
        self.assertTrue(self.valid())

    def test_c_req_018_pay_token_without_first_bnb_is_refused(self):
        self.planned(gas=0)
        self.assertFalse(self.valid())

    def test_c_req_017_bnb_without_pay_token_is_refused(self):
        self.planned(pay=0)
        self.assertFalse(self.valid())

    def test_c_req_017_insufficient_pay_token_is_refused(self):
        self.planned(pay=99)
        self.assertFalse(self.valid())

    def test_c_req_018_insufficient_gas_budget_is_refused(self):
        self.planned(gas=1)
        self.assertFalse(self.valid())

    def test_c_req_017_unrelated_asset_cannot_cover_pay_token(self):
        self.planned(pay_asset='NVDAB')
        self.assertFalse(self.valid())

    def test_c_req_017_incoming_token_cannot_cover_a_sell(self):
        self.planned(pay_asset='INCOMING:NVDAB', sell=True)
        self.assertFalse(self.valid())

    def test_c_req_017_actual_token_reserve_covers_a_sell(self):
        self.planned(pay_asset='NVDAB', sell=True)
        self.assertTrue(self.valid())

    def test_c_req_018_another_intent_cannot_supply_reservations(self):
        self.planned(reserve_intent='another-intent')
        self.assertFalse(self.valid())

    def test_c_req_018_missing_production_bnb_scale_is_refused(self):
        self.planned(scale=None)
        self.assertFalse(self.valid())

    def test_c_req_018_invalid_production_bnb_scale_is_refused(self):
        self.planned(scale=True)
        self.assertFalse(self.valid())

    def test_c_req_028_final_approval_gas_counts_against_remaining_budget(self):
        self.planned(gas=1)
        payload = Payload(56, self.economic.wallet, USDT, '0x00', 0, 0, 1000, 10**9)
        attempt = Attempt('fixture-approval', 'APPROVE', 'FINAL_SUCCESS', payload,
                          self.epoch, self.epoch, gas_used=1000)
        state = Execution(self.economic, attempts=(attempt,))
        self.registry.commit(None, state, dict(kind='FIXTURE_FINAL_APPROVAL'), self.epoch,
                             self.store.load('run').read()['version'])
        self.assertTrue(self.valid())
