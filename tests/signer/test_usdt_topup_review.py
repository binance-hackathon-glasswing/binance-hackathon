"""IDEA-104 S5R2-8: an exactly declared USDT top-up of the dev wallet is accepted by the hosted caps review."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from tests.signer import test_hosted_rehearsal_assembly as hosted
from tests.signer.test_hosted_rehearsal_assembly import BUILD, NOW, covered
from tools.deploy import review_rehearsal_caps as tool

TOPUP = 20_000_000


class DeclaredUsdtTopUp(unittest.TestCase):
    setUp = hosted.HostedRehearsalAssembly.setUp  # the same synthetic hosted packet and bindings

    def run_hosted(self, name='run', *, bindings=None, packet=None, usdt_deficit=0, usdt_surplus=0):
        with patch.object(tool, 'review', covered), patch('larp.signer.assembly.review', covered):
            return tool.assemble_hosted(packet or self.packet, self.root / (name + '-private'),
                                        bindings or self.bindings, self.root / (name + '-signer'), now=NOW,
                                        usdt_deficit=usdt_deficit, usdt_surplus=usdt_surplus)

    def topped_up(self, surplus=TOPUP):
        packet = deepcopy(self.packet)
        holdings = packet['holdings']
        holdings['status'] = 'SURPLUS_ONLY'
        holdings['assets']['USDT'].update(chain=holdings['assets']['USDT']['ledger'] + surplus, cls='SURPLUS')
        return packet

    def test_s5r2_8_new_run_starts_from_chain_cash_with_exactly_the_declared_top_up(self):
        packet = self.topped_up()
        self.run_hosted(packet=packet, usdt_surplus=TOPUP)
        holdings = json.loads((self.root / 'run-private/current-holdings.json').read_bytes())
        self.assertEqual(holdings['cash_units'], packet['holdings']['assets']['USDT']['chain'])
        rebinding = json.loads((self.root / 'run-private/portfolio-rebinding.json').read_bytes())
        self.assertEqual(rebinding['accepted_usdt_surplus_units'], TOPUP)
        self.assertEqual(rebinding['accepted_usdt_deficit_units'], 0)
        self.assertTrue((self.root / 'run-signer/signer.json').exists())

    def test_s5r2_8_any_other_top_up_refuses(self):
        mismatched = self.topped_up()
        mismatched['holdings']['status'] = 'MATCH'
        cases = dict(undeclared=(self.topped_up(), 0, 0), more=(self.topped_up(TOPUP + 1), TOPUP, 0),
                     less=(self.topped_up(TOPUP - 1), TOPUP, 0), declared_without_top_up=(self.packet, TOPUP, 0),
                     negative=(self.topped_up(), -TOPUP, 0), not_integer=(self.topped_up(), float(TOPUP), 0),
                     boolean=(self.topped_up(1), True, 0), with_deficit=(self.topped_up(), TOPUP, 1),
                     status_disagrees=(mismatched, TOPUP, 0))
        for name, (packet, surplus, deficit) in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(AssertionError):
                    self.run_hosted(name, packet=packet, usdt_surplus=surplus, usdt_deficit=deficit)
                self.assertFalse((self.root / (name + '-signer')).exists())

    def test_s5r2_8_numeric_only_mode_refuses_a_top_up(self):
        with self.assertRaises(AssertionError):
            tool.collect(self.topped_up(), self.root / 'numeric-private', BUILD, now=NOW, usdt_surplus=TOPUP)

    def test_s5r2_8_cli_needs_bindings_for_a_top_up(self):
        with self.assertRaises(SystemExit):
            tool.main(['--packet', str(self.root / 'none.json'), '--output-dir', str(self.root / 'cli'),
                       '--build-id', BUILD, '--accept-usdt-surplus-units', str(TOPUP)])

