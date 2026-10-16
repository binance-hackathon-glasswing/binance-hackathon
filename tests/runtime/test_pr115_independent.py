"""PR115-C01/C02: independent safety regressions; synthetic ports and disposable PostgreSQL only."""

from datetime import datetime, timezone

from larp.runtime.driver import DayRoll
from larp.runtime.coordinator import batch_for
from tests.runtime.test_balance_adoption import AdoptionHarness, MINUTE, PRICE, RUN, SECOND


class Confirmation(AdoptionHarness):
    def test_hold_only_cadence_cannot_starve_balance_confirmation(self):
        driver = self.prepare(raw=dict(NVDAB=2010))
        self.rounds_on = True
        first = self.tick(driver)
        self.assertEqual(first['balance_check'], 'SURPLUS_ONLY')
        self.assertIsNotNone(first['round_id'])
        record = self.store.event(RUN, 'plan:' + first['round_id'])['record']
        self.assertEqual(record['plan']['intents'], [])
        self.assertEqual(record['plan']['reservation_deltas'], [])
        second = self.tick(driver, MINUTE)
        self.assertEqual(second['balance_check'], 'ADJUSTED')
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 2010)
        self.assertIsNotNone(second['round_id'])

    def test_transient_reservation_between_reads_still_invalidates_confirmation(self):
        driver = self.prepare(raw=dict(NVDAB=2010))
        check, t = driver.balance_check, self.w.clock() + SECOND
        self.assertEqual(check(t), 'SURPLUS_ONLY')
        for event_id, units in [('reserve', 1), ('release', -1)]:
            current = self.store.load(RUN)
            self.store.commit(batch_for(current, 'fixture:' + event_id,
                dict(kind='INCIDENT', incident=dict(type='FIXTURE_RESOURCE')),
                reservation_deltas=[dict(intent_id='fixture', asset='USDT', units=units)]))
        self.assertFalse(self.store.load(RUN).read()['reservations'])
        self.assertNotEqual(check(t + MINUTE), 'ADJUSTED')
        self.assertEqual(self.events('BALANCE_ADJUSTED'), [])
        self.assertEqual(check(t + 2 * MINUTE), 'ADJUSTED')

    def interrupted_confirmation(self, early_units):
        driver = self.prepare(raw=dict(NVDAB=2010))
        check, t = driver.balance_check, self.w.clock() + SECOND
        self.assertEqual(check(t), 'SURPLUS_ONLY')
        self.chain.tokens['NVDAB'] = early_units
        check(t + SECOND)  # an immediate check may run before the scheduled retry
        self.chain.tokens['NVDAB'] = 2010
        self.assertNotEqual(check(t + MINUTE), 'ADJUSTED')
        self.assertEqual(self.events('BALANCE_ADJUSTED'), [])
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 2000)
        self.assertEqual(check(t + 2 * MINUTE), 'ADJUSTED')
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 2010)

    def test_early_match_breaks_the_original_mismatch_sequence(self):
        self.interrupted_confirmation(2000)

    def test_early_different_mismatch_breaks_the_original_sequence(self):
        self.interrupted_confirmation(2020)

    def test_early_contradiction_does_not_discard_another_assets_agreeing_reads(self):
        driver = self.prepare(raw=dict(NVDAB=2010, GOOGLB=100))
        check, t = driver.balance_check, self.w.clock() + SECOND
        self.assertEqual(check(t), 'SURPLUS_ONLY')
        self.chain.tokens['NVDAB'] = 2020
        check(t + SECOND)
        self.chain.tokens['NVDAB'] = 2010
        self.assertEqual(check(t + MINUTE), 'ADJUSTED')
        [event] = self.events('BALANCE_ADJUSTED')
        self.assertEqual([row['asset'] for row in event['adjustments']], ['GOOGLB'])
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 2000)
        self.assertEqual(check(t + 2 * MINUTE), 'ADJUSTED')
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 2010)


class MidnightJump(AdoptionHarness):
    def split_first_seen_by_day_roll(self, price, units):
        driver = self.prepare()
        self.round(driver)  # journal the previous, pre-split mark through the real context path
        self.assertEqual(self.projection()['marks']['NVDAB'], PRICE)
        self.assertFalse(self.projection()['price_jump'])
        before = self.projection().get('risk_state') or self.book()['risk']
        midnight = int(datetime(2026, 10, 11, tzinfo=timezone.utc).timestamp() * 1000)
        self.w.clock.now = midnight + SECOND
        self.feed.prices['NVDAB'] = price
        roll = DayRoll(driver.coordinator, window_ms=5 * MINUTE)
        self.assertEqual(roll(self.w.clock(), self.feed(self.w.clock())), 'PRICE_JUMP_HOLD')
        self.assertEqual(self.events('DAY_ROLLED'), [])
        self.assertEqual(self.projection().get('risk_state') or self.book()['risk'], before)
        self.round(driver, at=midnight + 2 * SECOND)
        self.assertIn('NVDAB', self.projection()['price_jump'])
        self.chain.tokens['NVDAB'] = units
        self.assertEqual(self.tick(driver)['balance_check'], 'SURPLUS_ONLY' if units > 2000 else 'DEFICIT')
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        self.assertFalse(self.projection()['price_jump'])
        self.assertEqual(roll(self.w.clock(), self.feed(self.w.clock())), 'ROLLED')
        [event] = self.events('DAY_ROLLED')
        # Split-adjusted token value is unchanged: neither the halved nor doubled price anchors old units.
        self.assertEqual(event['anchor_units'], before['day_anchor_units'])

    def test_forward_split_in_midnight_fetch_does_not_lower_the_daily_anchor(self):
        self.split_first_seen_by_day_roll(PRICE // 2, 4000)

    def test_reverse_split_in_midnight_fetch_does_not_inflate_the_daily_anchor(self):
        self.split_first_seen_by_day_roll(PRICE * 2, 1000)

    def test_guard_disabled_keeps_the_existing_day_roll_behavior(self):
        driver = self.prepare(jump=False)
        midnight = int(datetime(2026, 10, 11, tzinfo=timezone.utc).timestamp() * 1000)
        self.w.clock.now = midnight + SECOND
        roll = DayRoll(driver.coordinator, window_ms=5 * MINUTE)
        self.assertEqual(roll(self.w.clock(), self.feed(self.w.clock())), 'ROLLED')
