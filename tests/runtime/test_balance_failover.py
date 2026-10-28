"""IDEA-055 PR 5, F1-F8: an ordered list of balance RPC providers with failover (D5, owner decisions 2026-10-16).

Synthetic providers and disposable PostgreSQL; no credentials, network, signing or upload.
"""

import json
from pathlib import Path
import unittest

from larp.contracts import ContractError
from larp.execution_live.chain import Blocked, DependencyUnavailable
from tests.runtime.test_balance_adoption import AdoptionHarness
from tests.runtime.test_balance_reconciliation import INTERVAL, MAX_AGE, MINUTE, WALLET, chain_for, ledger

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = dict(url='https://primary-rpc.example/', source_id='primary-rpc')
BACKUP = dict(url='https://backup-rpc.example/', source_id='backup-rpc')
COMMON = dict(balance_check_interval_ms=INTERVAL, balance_check_max_age_ms=MAX_AGE, price_jump_check_bps=3000)


def providers(*chains):
    from larp.execution_live.balances import BalanceProviders, DecimalsCache
    return BalanceProviders(list(chains), wallet=WALLET, decimals=DecimalsCache())


def named(chain, source_id):
    chain.source_id = source_id
    return chain


# ---------------------------------------------------------------------------------------------- F1 settings
class Settings(unittest.TestCase):
    def settings(self, d, mode='dev'):
        from larp.runtime.service import balance_settings
        return balance_settings(d, mode)

    def test_f1_an_ordered_list_and_the_legacy_single_provider_are_accepted(self):
        two = self.settings(dict(COMMON, balance_rpc_providers=[PRIMARY, BACKUP]))
        self.assertEqual(two['providers'], [PRIMARY, BACKUP])
        one = self.settings(dict(COMMON, balance_rpc_providers=[PRIMARY]))
        self.assertEqual(one['providers'], [PRIMARY])
        legacy = self.settings(dict(COMMON, balance_rpc_url=PRIMARY['url'], balance_rpc_source_id='primary-rpc'))
        self.assertEqual(legacy['providers'], [PRIMARY])
        from larp.runtime.service import balance_settings
        self.assertIsNone(balance_settings({}, 'offline'))

    def test_f1_refusals(self):
        bad = {
            'both forms': dict(COMMON, balance_rpc_providers=[PRIMARY], balance_rpc_url=BACKUP['url'],
                               balance_rpc_source_id='backup-rpc'),
            'missing': dict(COMMON),
            'empty': dict(COMMON, balance_rpc_providers=[]),
            'null url': dict(COMMON, balance_rpc_providers=[PRIMARY, dict(url=None, source_id='backup-rpc')]),
            'null source': dict(COMMON, balance_rpc_providers=[dict(PRIMARY, source_id=None)]),
            'http': dict(COMMON, balance_rpc_providers=[dict(PRIMARY, url='http://primary-rpc.example/')]),
            'duplicate source': dict(COMMON, balance_rpc_providers=[PRIMARY, dict(BACKUP, source_id='primary-rpc')]),
            'five': dict(COMMON, balance_rpc_providers=[dict(url=f'https://rpc{i}.example/', source_id=f'rpc-{i}')
                                                        for i in range(5)]),
            'not a list': dict(COMMON, balance_rpc_providers=PRIMARY),
            'extra field': dict(COMMON, balance_rpc_providers=[dict(PRIMARY, key='x')]),
        }
        for mode in ('dev', 'live'):
            for name, d in bad.items():
                with self.subTest(mode=mode, case=name), self.assertRaises(ContractError):
                    self.settings(d, mode)


# ---------------------------------------------------------------------------------------------- F2, F3 failover
class Failover(unittest.TestCase):
    def test_f2_the_backup_serves_the_same_check_and_the_primary_is_tried_first_again(self):
        book = ledger()
        for failure in (DependencyUnavailable('RPC unavailable'), Blocked('RPC response rejected')):
            with self.subTest(failure=type(failure).__name__):
                primary, backup = named(chain_for(book), 'primary-rpc'), named(chain_for(book), 'backup-rpc')
                read = providers(primary, backup)
                primary.fail = failure
                o = read(1_000)
                self.assertEqual(o['source_id'], 'backup-rpc')
                self.assertTrue(backup.calls)
                primary.fail = None
                primary.calls.clear()
                self.assertEqual(read(2_000)['source_id'], 'primary-rpc')
                self.assertTrue(primary.calls)

    def test_f3_a_check_fails_only_when_every_provider_fails(self):
        book = ledger()
        primary, backup = named(chain_for(book), 'primary-rpc'), named(chain_for(book), 'backup-rpc')
        read = providers(primary, backup)
        primary.fail = backup.fail = DependencyUnavailable('RPC unavailable')
        with self.assertRaises(DependencyUnavailable):
            read(1_000)
        backup.fail = Blocked('RPC response rejected')
        with self.assertRaises(Blocked):
            read(2_000)


class FailoverDriver(AdoptionHarness):
    def two(self, driver):
        from larp.execution_live.balances import BalanceProviders, DecimalsCache
        self.primary = named(self.chain, 'primary-rpc')
        self.backup = named(chain_for(self.book(), **self.raw), 'backup-rpc')
        driver.balance_check.reader = BalanceProviders([self.primary, self.backup], wallet=WALLET,
                                                       decimals=DecimalsCache())
        return driver

    def test_f3_one_provider_down_keeps_checks_comparable(self):
        self.raw = {}
        driver = self.two(self.prepare())
        self.primary.fail = DependencyUnavailable('RPC unavailable')
        self.assertEqual(self.tick(driver)['balance_check'], 'MATCH')
        self.assertTrue(self.health(driver)['balances_ok'])
        self.backup.fail = DependencyUnavailable('RPC unavailable')
        self.assertEqual(self.tick(driver, INTERVAL)['balance_check'], 'SKIPPED:RPC_UNAVAILABLE')
        self.assertEqual(driver.balance_check.next_ms, self.w.clock() + MINUTE)
        self.assertTrue(self.health(driver)['balances_ok'])  # until the maximum age
        self.w.clock.now += MAX_AGE - INTERVAL
        self.assertFalse(self.health(driver)['balances_ok'])

    def test_f4_an_adoption_can_be_confirmed_by_another_provider(self):
        self.raw = dict(NVDAB=2010)
        driver = self.two(self.prepare(raw=self.raw))
        self.assertEqual(self.tick(driver)['balance_check'], 'SURPLUS_ONLY')  # from the primary
        self.primary.fail = DependencyUnavailable('RPC unavailable')
        self.backup.height = self.primary.height + 1  # a newer finalized block (IDEA-055 R1)
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')  # confirmed by the backup
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 2010)
        [adjustment] = self.events('BALANCE_ADJUSTED')[0]['adjustments']
        # The observations name their provider, so the two reads hash differently.
        self.assertNotEqual(adjustment['first_observation_sha256'], adjustment['confirm_observation_sha256'])


# ---------------------------------------------------------------------------------------------- F5 composition
class Composition(unittest.TestCase):
    def build(self, **block):
        from larp.runtime.service import build_driver
        from tests.runtime import test_driver as driver_tests
        case = driver_tests.Composition('test_d7_valid_configuration_builds_real_ports_that_pass_the_live_start_check')
        case.setUp()
        self.addCleanup(case.doCleanups)
        return build_driver(case.config(**block), driver_tests.Store(), case.secrets)

    def test_f5_build_driver_wires_the_providers_in_order(self):
        driver = self.build(**COMMON, balance_rpc_providers=[PRIMARY, BACKUP])
        self.assertEqual([p.source_id for p in driver.balance_check.reader.providers], ['primary-rpc', 'backup-rpc'])
        self.assertEqual([p.url for p in driver.balance_check.reader.providers], [PRIMARY['url'], BACKUP['url']])
        legacy = self.build(**COMMON, balance_rpc_url=PRIMARY['url'], balance_rpc_source_id='primary-rpc')
        self.assertEqual([p.source_id for p in legacy.balance_check.reader.providers], ['primary-rpc'])


# ---------------------------------------------------------------------------------------------- F6 routes
class Routes(unittest.TestCase):
    def plan(self, providers=None, **legacy):
        from larp.runtime import routes
        from tests.runtime.test_routes import configs, sources
        cfgs = configs()
        driver = cfgs['runtime']['driver']
        for key in ('balance_rpc_url', 'balance_rpc_source_id', 'balance_rpc_providers'):
            driver.pop(key, None)
        if providers is not None:
            driver['balance_rpc_providers'] = providers
        driver.update(legacy)
        return routes.plan('primary', cfgs, sources())['destinations']

    def test_f6_every_provider_is_planned(self):
        hosts = {d['host'] for d in self.plan([PRIMARY, BACKUP])}
        self.assertTrue({'primary-rpc.example', 'backup-rpc.example'} <= hosts)
        legacy = {d['host'] for d in self.plan(balance_rpc_url=PRIMARY['url'], balance_rpc_source_id='primary-rpc')}
        self.assertIn('primary-rpc.example', legacy)

    def test_f6_an_unset_backup_is_unset_and_a_bad_url_is_refused(self):
        rows = self.plan([PRIMARY, dict(url=None, source_id=None)])
        unset = [d for d in rows if d['host'] is None]
        self.assertEqual(len(unset), 1)
        self.assertIn('balance_rpc_providers[1]', json.dumps(unset))
        with self.assertRaises(ContractError):
            self.plan([PRIMARY, dict(BACKUP, url='http://backup-rpc.example/')])

    def test_f6_the_approved_table_names_the_provider_list(self):
        doc = (ROOT / 'docs/build/architecture-deployment.md').read_text(encoding='utf-8')
        section = doc.split('## Approved network destinations', 1)[1].split('\n## ', 1)[0]
        self.assertIn('`driver.balance_rpc_providers`', section)


# ---------------------------------------------------------------------------------------------- F7, F8
class Declared(unittest.TestCase):
    def test_f7_the_services_manifest_declares_the_bsc_rpc(self):
        from larp.runtime.register import validate_services
        services = validate_services(json.loads((ROOT / 'config/release/services.v1.json').read_text()))
        [rpc] = [s for s in services['services'] if s['service_id'] == 'bsc-rpc']
        # Isaac selected the providers (IDEA-055 RPC-Q01 D1); GAP62-F03 declares them for the FS1 scored run.
        self.assertEqual(rpc['status'], 'ACTIVE')
        self.assertEqual(rpc['selection_scope'], 'FS1_SCORED_RUN')
        self.assertEqual(rpc['development_balance_source_ids'], ['BSC_BNBCHAIN_PUBLIC', 'BSC_NODEREAL_PUBLIC'])

    def test_f8_the_example_names_two_unset_providers(self):
        import importlib.util
        example = json.loads((ROOT / 'config/runtime/runtime.example.json').read_text())
        self.assertEqual(example['driver']['balance_rpc_providers'],
                         [dict(url=None, source_id=None), dict(url=None, source_id=None)])
        self.assertNotIn('balance_rpc_url', example['driver'])
        spec = importlib.util.spec_from_file_location('render', ROOT / 'tools/deploy/render_host_configs.py')
        render = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(render)
        missing = render.unset(example)
        self.assertIn('driver.balance_rpc_providers[0].url', missing)
        self.assertIn('driver.balance_rpc_providers[1].url', missing)


class ProviderFloor(unittest.TestCase):
    def test_rr2_r3_a_lagging_primary_uses_the_backup_and_all_lagging_still_refuses(self):
        from larp.execution_live.balances import BalanceProviders, DecimalsCache
        from tests.runtime.test_balance_reconciliation import HEIGHT
        book = ledger()
        primary, backup = named(chain_for(book), 'primary-rpc'), named(chain_for(book), 'backup-rpc')
        primary.height, backup.height = HEIGHT - 1, HEIGHT + 1
        floor = HEIGHT
        read = BalanceProviders([primary, backup], wallet=WALLET, decimals=DecimalsCache(), min_block=lambda: floor)
        self.assertEqual(read(1_000)['source_id'], 'backup-rpc')
        self.assertTrue(backup.calls)
        floor += 2
        with self.assertRaises(Blocked):
            read(2_000)
        primary.height = floor + 1
        self.assertEqual(read(3_000)['source_id'], 'primary-rpc')

    def test_rr2_r3_build_driver_reads_the_floor_from_the_current_run(self):
        from unittest.mock import patch
        from larp.contracts import Document
        from larp.runtime.service import build_driver
        from tests.runtime import test_driver as driver_tests
        case = driver_tests.Composition('test_d7_valid_configuration_builds_real_ports_that_pass_the_live_start_check')
        case.setUp()
        self.addCleanup(case.doCleanups)
        store = driver_tests.Store()
        driver = build_driver(case.config(**COMMON, balance_rpc_providers=[PRIMARY, BACKUP]), store, case.secrets)
        for floor in (None, 123, 456):
            with self.subTest(floor=floor), patch.object(store, 'load', return_value=Document.from_dict(
                    dict(projection=dict(settled_block=floor)))):
                self.assertEqual(driver.balance_check.reader.min_block(), floor)


if __name__ == '__main__':
    unittest.main()
