"""LD08-IG01: durable low-gas evidence; PostgreSQL, synthetic balances, no live I/O."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from larp.contracts import ContractError, Document
from larp.integration.runtime import initial_projection
from larp.runtime.coordinator import batch_for
from larp.runtime.driver import RoundDriver
from larp.runtime.maintenance import Maintenance, HOUR_MS
from larp.runtime.operations import publish_health
from larp.strategy.profiles import build_live_profiles, validate_live
from tests.strategy.live_fixtures import live_snapshot, registry, summary
from tests.support import DatabaseCase


def profile():
    return build_live_profiles(summary(), registry(), initial_gas_only=True)['FINAL'].read()


class ProfileBudget(unittest.TestCase):
    def test_budget_is_sourced_and_covers_a_pair_without_hiding_cleanup(self):
        p = profile()
        self.assertEqual(p['gas_action_budget_units'], 20_000)
        self.assertIn('gas_action_budget_units', p['provenance'])
        p['gas_action_budget_units'] = 30_000  # a reviewed larger action can include supporting cleanup
        with self.assertRaises(ContractError):
            validate_live(p)  # the full book's reserve must grow with the action budget
        p['exit_gas_reserve_units'] = 4 * 30_000
        with self.assertRaises(ContractError):
            validate_live(p)  # the minimum trade must cover the larger action's gas cost too
        p['minimum_trade_units'] = (p['minimum_trade_units'] * 3 + 1) // 2
        validate_live(p)
        for bad in (None, True, 0, 19_999, p['exit_gas_reserve_units'] + 1):
            broken = deepcopy(p)
            broken['gas_action_budget_units'] = bad
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                validate_live(broken)
        del p['gas_action_budget_units']
        with self.assertRaises(ContractError):
            validate_live(p)

    def test_budget_cites_its_own_decision_and_top_up_profiles_refuse_one(self):
        self.assertEqual(profile()['provenance']['gas_action_budget_units']['decision_id'], 'IDEA-061 LD07/LD08')
        legacy = build_live_profiles(summary(), registry())['FINAL'].read()
        validate_live(legacy)
        legacy['gas_action_budget_units'] = 50_000
        legacy['provenance']['gas_action_budget_units'] = {'decision_id': 'SYNTHETIC', 'formula': 'stray'}
        with self.assertRaises(ContractError):
            validate_live(legacy)

    def test_five_name_exit_covers_five_complete_action_budgets(self):
        from tests.strategy.test_s1_core import block
        p = build_live_profiles(summary(), registry(), s1=block(), initial_gas_only=True)['FINAL'].read()
        p['gas_action_budget_units'] = 25_000
        p['minimum_trade_units'] = (p['minimum_trade_units'] * 5 + 3) // 4
        with self.assertRaises(ContractError):
            validate_live(p)
        p['exit_gas_reserve_units'] = 5 * 25_000
        validate_live(p)

    def test_driver_wires_only_the_pinned_initial_only_profile(self):
        import hashlib
        import json
        from tests.runtime.test_driver import Composition, Store
        from larp.runtime.service import build_driver
        case = Composition()
        case.setUp()
        self.addCleanup(case.doCleanups)
        raw = json.dumps(profile()).encode()
        (case.root / 'profile.json').write_bytes(raw)
        case.driver_block['strategy_profile_sha256'] = hashlib.sha256(raw).hexdigest()
        driver = build_driver(dict(schema='RuntimeService.v1', run_id='run', build_id='b' * 40,
            mode='offline', wallet_address=case.wallet, driver=case.driver_block), Store(),
            {'BINANCE_API_KEY': 'synthetic-key', 'BINANCE_SECRET_KEY': 'synthetic-secret'}, clock_ms=lambda: 0)
        self.assertEqual(driver.gas_check.action_budget, 20_000)
        self.assertIsNone(driver.market.gas)


class GasHealth(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.p = profile()
        book = live_snapshot().context.read()['portfolio']
        book['bnb_units'] = 19_999
        self.initial = Document.from_dict(initial_projection(book))
        self.store.initialize('gas', 'gas-wallet', 56, self.initial)
        self.store.takeover('gas', 1, offline=True)
        self.c = SimpleNamespace(store=self.store, run_id='gas')

    def monitor(self):
        from larp.runtime.gas import InitialGasCheck
        return InitialGasCheck(self.c, self.p)

    def update(self, change):
        current = self.store.load('gas')
        projection = current.read()['projection']
        change(projection)
        self.store.commit(batch_for(current, 'fixture:' + str(current.read()['version']),
                                     dict(kind='INCIDENT', incident={'type': 'SYNTHETIC'}), projection=projection))

    def state(self):
        return self.store.load('gas').read()

    def test_low_gas_is_atomic_durable_and_does_not_halt_or_change_money(self):
        before = self.state()
        self.assertEqual(self.monitor()(100), 'PAIR_UNAFFORDABLE')
        after = self.state()
        self.assertTrue(after['projection']['gas_health']['pair_unaffordable'])
        self.assertEqual(after['projection']['gas_health']['action_budget_units'], 20_000)
        self.assertEqual(after['projection']['balances'], before['projection']['balances'])
        self.assertEqual(after['projection']['portfolio'], before['projection']['portfolio'])
        self.assertNotIn('halt', after['projection'])
        self.assertEqual(after['reservations'], before['reservations'])
        self.assertEqual((after['epoch'], after['quarantined']), (before['epoch'], before['quarantined']))
        self.assertEqual(after['version'], before['version'] + 1)
        self.monitor()(101)  # restart must not emit another incident
        self.assertEqual(self.state()['version'], after['version'])
        with self.store.transaction() as db:
            event = db.execute("SELECT batch FROM events WHERE run_id='gas' ORDER BY sequence DESC LIMIT 1").fetchone()
        self.assertEqual(Document(bytes(event[0])).read()['event']['incident']['type'], 'LOW_GAS')

    def test_exact_pair_budget_remains_affordable_and_clear_is_journaled(self):
        self.monitor()(100)
        def fund(p):
            p['portfolio']['bnb_units'] = p['balances']['BNB'] = 20_000
        self.update(fund)
        before = self.state()['version']
        self.assertEqual(self.monitor()(200), 'BELOW_EXIT_RESERVE')
        self.assertFalse(self.state()['projection']['gas_health']['pair_unaffordable'])
        self.assertEqual(self.state()['version'], before + 1)
        self.update(lambda p: p['portfolio'].update(bnb_units=80_000) or p['balances'].update(BNB=80_000))
        self.assertEqual(self.monitor()(300), 'OK')
        self.assertEqual(self.state()['projection']['gas_health']['status'], 'OK')

    def test_clock_rollback_does_not_clear_a_durable_alarm(self):
        self.monitor()(100)
        self.update(lambda p: p['portfolio'].update(bnb_units=80_000) or p['balances'].update(BNB=80_000))
        before = self.state()['version']
        self.assertEqual(self.monitor()(99), 'CLOCK_REFUSED')
        self.assertTrue(self.state()['projection']['gas_health']['pair_unaffordable'])
        self.assertEqual(self.state()['version'], before)

    def test_chain_deficit_is_not_available_gas(self):
        self.update(lambda p: p['portfolio'].update(bnb_units=80_000) or p['balances'].update(BNB=80_000))
        self.update(lambda p: p.update(balance_check={'deficits': {'BNB': 60_001}}))
        self.assertEqual(self.monitor()(100), 'PAIR_UNAFFORDABLE')
        self.assertEqual(self.state()['projection']['gas_health']['spendable_bnb_units'], 19_999)

    def test_unreadable_ledger_is_skipped_not_raised(self):
        monitor = self.monitor()
        monitor.decimals = 9
        before = self.state()['version']
        self.assertEqual(monitor(100), 'SKIPPED')
        self.assertEqual(self.state()['version'], before)

    def test_top_up_profile_clears_an_earlier_alarm_once(self):
        from larp.runtime.gas import RetiredGasCheck
        self.monitor()(100)
        legacy = build_live_profiles(summary(), registry())['FINAL'].read()
        self.assertEqual(RetiredGasCheck(self.c, legacy)(200), 'NOT_MONITORED')
        after = self.state()
        self.assertFalse(after['projection']['gas_health']['pair_unaffordable'])
        self.assertFalse(Maintenance(self.store, None, backup_interval_ms=24 * HOUR_MS).service_health('gas', 201).read()['gas_pair_unaffordable'])
        RetiredGasCheck(self.c, legacy)(300)  # a restart does not journal again
        self.assertEqual(self.state()['version'], after['version'])

    def test_pending_execution_is_not_invalidated_by_a_health_commit(self):
        self.update(lambda p: p.update(round_records={'r': {'execution_pending': True}}))
        before = self.state()['version']
        self.assertEqual(self.monitor()(100), 'DEFERRED_IN_FLIGHT')
        self.assertEqual(self.state()['version'], before)

    def test_open_round_defers_until_a_quiet_boundary(self):
        self.store.open_round('gas', 'r', Document.from_dict({'synthetic': True}), self.state()['epoch'])
        before = self.state()['version']
        self.assertEqual(self.monitor()(100), 'DEFERRED_IN_FLIGHT')
        self.assertEqual(self.state()['version'], before)

    def test_archive_health_and_metric_report_alarm_and_recovery(self):
        self.monitor()(100)
        health = Maintenance(self.store, None, backup_interval_ms=24 * HOUR_MS).service_health('gas', 101).read()
        self.assertTrue(health['gas_pair_unaffordable'])
        client = MagicMock()
        publish_health(client, 'synthetic', True, health)
        metric = next(m for m in client.put_metric_data.call_args.kwargs['MetricData'] if m['MetricName'] == 'GasPairUnaffordable')
        self.assertEqual(metric['Value'], 1)
        self.update(lambda p: p['portfolio'].update(bnb_units=80_000) or p['balances'].update(BNB=80_000))
        self.monitor()(200)
        self.assertFalse(Maintenance(self.store, None, backup_interval_ms=24 * HOUR_MS).service_health('gas', 201).read()['gas_pair_unaffordable'])

    def test_incident_replay_preserves_the_exact_projection_and_hashes(self):
        from larp.runtime.replay import replay
        self.monitor()(100)
        other = DatabaseCase()
        other.setUp()
        self.addCleanup(other.doCleanups)
        batches = self.store.journal('gas')
        replay(batches, self.initial, other.store, run_id='gas', wallet_id='gas-wallet', chain_id=56,
               version_id='synthetic', profile_hash='a' * 64, address=None,
               policy=None, planner=None, execution=None, reducer=None)
        self.assertEqual(other.store.load('gas').read()['projection'], self.state()['projection'])
        self.assertEqual(other.store.load('gas').read()['head'], self.state()['head'])


class DriverBoundary(unittest.TestCase):
    def test_waiting_command_skips_monitor_without_a_version_change(self):
        c, execution, work, gas = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        execution.settle_open.return_value = []
        execution.reauthorize.return_value = []
        execution.waiting.return_value = ['command']
        driver = RoundDriver(c, work, execution=execution, gas_check=gas)
        self.assertEqual(driver.once(100)['waiting_for_claim'], ['command'])
        gas.assert_not_called()

    def test_gas_check_waits_for_its_interval_without_a_reconciliation(self):
        c, execution, work, gas = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        execution.settle_open.return_value = []
        execution.waiting.return_value = []
        execution.reauthorize.return_value = []
        work.next.return_value = None
        gas.due.return_value = False
        RoundDriver(c, work, execution=execution, gas_check=gas).once(100)
        gas.assert_not_called()
        gas.due.return_value = True
        RoundDriver(c, work, execution=execution, gas_check=gas).once(200)
        gas.assert_called_once_with(200)

    def test_gas_check_runs_after_balance_reconciliation_before_work(self):
        c, execution, work = MagicMock(), MagicMock(), MagicMock()
        execution.settle_open.return_value = []
        execution.waiting.return_value = []
        execution.reauthorize.return_value = []
        work.next.return_value = None
        calls = []
        balance = MagicMock(side_effect=lambda now: calls.append('balance'))
        balance.due.return_value = True
        gas = lambda now: calls.append('gas') or 'PAIR_UNAFFORDABLE'
        work.next.side_effect = lambda *args: calls.append('work')
        driver = RoundDriver(c, work, execution=execution, balance_check=balance, gas_check=gas)
        driver.once(100)
        self.assertEqual(calls, ['balance', 'gas', 'work'])
