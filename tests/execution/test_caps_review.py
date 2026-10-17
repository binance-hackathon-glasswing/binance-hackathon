"""GB-CAP1..3: synthetic offline numeric review, never policy approval."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest

from larp.contracts import ContractError, Document
from larp.execution import Blocked, NATIVE_BNB, USDT
from larp.execution_live.caps_review import main, review
from larp.marketdata.port import TOKENS
from larp.research.fixtures import snapshot
from larp.strategy.profiles import build_live_profiles
from tests.strategy.live_fixtures import registry, summary
from tools.deploy.propose_signer_caps import build, ROUTER
from tests.execution.test_signer_caps_proposal import inputs as reference

WALLET = '0x' + '12' * 20
NOW = '2026-10-21T00:00:00Z'


class CapsReview(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        costs = summary().read()
        costs.update(bnb_decimals=18, bnb_price_units=700_000_000)
        for row in costs['symbols'].values():
            row.update(approve_gas_bnb_units=3 * 10**12, swap_gas_bnb_units=5 * 10**12)
        self.profile = build_live_profiles(Document.from_dict(costs), registry())['REHEARSAL'].read()
        self.policy = build(reference())['candidates']['development']['signing_policy']
        self.config = dict(schema='ExecutionService.v1', run_id='run', build_id='a' * 40, mode='dev',
                           wallet_address=WALLET, interval_seconds=1, database_dsn_file='/not-read',
                           router=ROUTER, token_decimals={s: 18 for s in TOKENS},
                           max_gas=100_000, max_gas_price=2 * 10**9, gas_budget=4 * 10**14,
                           strategy_profile_file='profile.json', strategy_profile_sha256='')
        self.ledger = snapshot().context.read()['portfolio']
        self.ledger.update(mode='dev', run_id='run', wallet_id=WALLET, bnb_decimals=18, bnb_units=10**15,
                           positions={s: dict(units=10**16, decimals=18, cost_basis_units=1) for s in TOKENS})
        self.inputs = dict(schema='GateBCapsInputs.v1', wallet=WALLET, run_id='run', build_id='a' * 40,
                           environment='REHEARSAL', max_age_seconds=60, files={}, quote_artifacts=[])
        self.save_inputs()
        for symbol, token in sorted(TOKENS.items()):
            for side in ('BUY', 'SELL'):
                self.add_quote(symbol + side, USDT if side == 'BUY' else token,
                               token if side == 'BUY' else USDT, 20 * 10**18 if side == 'BUY' else 10**16)
        self.add_quote('BNB', USDT, NATIVE_BNB, 2 * 10**18)

    def pin(self, name, value):
        raw = json.dumps(value).encode()
        (self.root / name).write_bytes(raw)
        return dict(path=name, sha256=hashlib.sha256(raw).hexdigest())

    def save_inputs(self):
        files = self.inputs['files']
        files['profile'] = self.pin('profile.json', self.profile)
        self.config['strategy_profile_sha256'] = files['profile']['sha256']
        for name, value in [('signing_policy', self.policy), ('execution_config', self.config),
                            ('initial_state', self.ledger)]:
            files[name] = self.pin(name + '.json', value)

    def add_quote(self, name, pay, receive, amount):
        record = dict(schema='Web3Observation.v1', source_id='BINANCE_WEB3',
                      requested_at=NOW, endpoint='aggregator/quote-and-swap', outcome='ok', http_status=200,
                      params=dict(binanceChainId='56', userWalletAddress=WALLET,
                                  fromTokenAddress=pay, toTokenAddress=receive, amount=str(amount)),
                      response=dict(code=0, data=dict(executionMode='SWAP', tx=dict(
                          to=ROUTER, value='0', gas='40000', gasPrice='2000000000', minReceiveAmount='1'))))
        self.inputs['quote_artifacts'].append(self.pin(name + '.json', record))

    def report(self):
        return review(self.inputs, now=NOW, base_dir=self.root)

    def test_covered_candidate_still_needs_owners_and_never_enables_signing(self):
        result = self.report()
        self.assertEqual(result['numeric_status'], 'COVERED')
        self.assertEqual(result['blockers'], ['OWNER_REVIEW_REQUIRED', 'POLICY_APPROVAL_REQUIRED'])
        self.assertEqual(result['missing_quote_coverage'], [])
        self.assertFalse(result['signing_enabled'])
        self.assertFalse(result['ready_to_install'])
        self.policy['cap_basis'] = 'synthetic decision only'
        self.save_inputs()
        self.assertEqual(self.report()['blockers'], ['OWNER_REVIEW_REQUIRED'])
        self.assertEqual(self.report()['status'], 'BLOCKED')

    def test_exact_cash_holding_and_fee_boundaries(self):
        self.policy['max_input_units'][USDT] = str(self.profile['per_trade_cap_units'] * 10**12)
        for token in TOKENS.values():
            self.policy['max_input_units'][token] = str(10**16)
        self.save_inputs()
        self.assertEqual(self.report()['numeric_status'], 'COVERED')
        for what in ('cash', 'holding', 'fee'):
            with self.subTest(what=what):
                policy = deepcopy(self.policy)
                if what == 'cash':
                    self.policy['max_input_units'][USDT] = str(int(self.policy['max_input_units'][USDT]) - 1)
                elif what == 'holding':
                    self.policy['max_input_units'][TOKENS['MSFTB']] = str(10**16 - 1)
                else:
                    self.policy['max_fee_wei'] = str(2 * 10**14 - 1)
                self.save_inputs()
                self.assertEqual(self.report()['numeric_status'], 'BLOCKED')
                self.policy = policy
        self.save_inputs()

    def test_non18_stock_units_are_compared_without_rescaling(self):
        self.config['token_decimals']['NVDAB'] = 8
        self.ledger['positions']['NVDAB'].update(decimals=8, units=10**8)
        self.policy['max_input_units'][TOKENS['NVDAB']] = str(10**8)
        # Replace that recorded sell with the same raw eight-decimal amount.
        for i, ref in enumerate(self.inputs['quote_artifacts']):
            if ref['path'] == 'NVDABSELL.json':
                record = json.loads((self.root / ref['path']).read_bytes())
                record['params']['amount'] = str(10**8)
                self.inputs['quote_artifacts'][i] = self.pin(ref['path'], record)
        self.save_inputs()
        self.assertEqual(self.report()['numeric_status'], 'COVERED')
        self.ledger['positions']['NVDAB']['units'] += 1
        self.save_inputs()
        self.assertIn('FULL_HOLDING_NVDAB', self.report()['blockers'])

    def test_s1_full_position_cap_and_measured_fee_rounding(self):
        from tests.strategy.test_s1_core import block
        costs = self.profile['quote_cost_summary']
        weights = {s: [7, 40] for s in TOKENS}
        weights['NVDAB'] = [3, 10]
        self.profile = build_live_profiles(Document.from_dict(costs), registry(),
            s1=block(weights=weights), s1_decision='synthetic-unapproved-values')['REHEARSAL'].read()
        self.save_inputs()
        self.assertEqual(self.report()['numeric_status'], 'COVERED')
        cash_check = next(c for c in self.report()['checks'] if c['check'] == 'FULL_POSITION_AND_TOPUP_USDT')
        self.assertEqual(cash_check['required'], str(28_600_000 * 10**12))
        # A cap that covered EQUAL_WEIGHT can block S1's largest frozen position.
        self.policy['max_input_units'][USDT] = str(25 * 10**18)
        self.save_inputs()
        self.assertIn('FULL_POSITION_AND_TOPUP_USDT', self.report()['blockers'])

    def test_scope_missing_metadata_and_duplicate_captures_cannot_pass(self):
        self.policy['allowed_spenders'].append(WALLET)
        self.save_inputs()
        self.assertIn('TOKEN_OR_SPENDER_SCOPE', self.report()['blockers'])
        self.inputs['quote_artifacts'].append(self.inputs['quote_artifacts'][0])
        self.assertIn('QUOTE_ARTIFACT_REFUSED', self.report()['blockers'])
        self.ledger['reservations'] = {'existing': {}}
        self.save_inputs()
        self.assertIn('IN_FLIGHT_PORTFOLIO_REVIEW', self.report()['blockers'])
        self.config['token_decimals']['NVDAB'] = 8
        self.save_inputs()
        with self.assertRaises(ContractError):
            self.report()

    def test_mismatched_identity_units_and_boolean_quantities_refuse(self):
        for target, changes in [
                ('config', dict(build_id='b' * 40)), ('config', dict(wallet_address=ROUTER)),
                ('config', dict(mode='live')), ('config', dict(max_gas=True)),
                ('ledger', dict(wallet_id=ROUTER)), ('ledger', dict(run_id='other')),
                ('ledger', dict(bnb_decimals=6)), ('ledger', dict(cash_units=True)),
                ('ledger', dict(positions={})), ('profile', dict(environment='FINAL'))]:
            with self.subTest(target=target, changes=changes):
                old = deepcopy(getattr(self, target))
                getattr(self, target).update(changes)
                self.save_inputs()
                with self.assertRaises((ContractError, ValueError)):
                    self.report()
                setattr(self, target, old)
        self.save_inputs()

    def test_quote_mutations_staleness_and_missing_coverage_are_blockers(self):
        ref = self.inputs['quote_artifacts'][0]
        original = json.loads((self.root / ref['path']).read_bytes())
        cases = [dict(requested_at='2026-10-20T23:58:59Z'), dict(requested_at='2026-10-21T00:00:01Z'),
                 dict(http_status=True), dict(outcome='error')]
        for changes in cases:
            with self.subTest(changes=changes):
                self.inputs['quote_artifacts'][0] = self.pin(ref['path'], dict(original, **changes))
                self.assertIn('QUOTE_ARTIFACT_REFUSED', self.report()['blockers'])
                self.assertIn('QUOTE_COVERAGE_INCOMPLETE', self.report()['blockers'])
        self.inputs['quote_artifacts'][0] = ref
        (self.root / ref['path']).write_text(json.dumps(original))
        self.inputs['quote_artifacts'].pop()  # gas top-up absent; stock-only coverage is insufficient
        self.assertEqual(self.report()['missing_quote_coverage'], ['BNB:BUY'])

    def test_wrong_quote_wallet_pair_gas_and_amount_cannot_be_covered(self):
        ref = self.inputs['quote_artifacts'][0]
        original = json.loads((self.root / ref['path']).read_bytes())
        cases = []
        for field, value in [('userWalletAddress', ROUTER), ('binanceChainId', True),
                             ('amount', True), ('amount', str(10**40)), ('fromTokenAddress', NATIVE_BNB)]:
            record = deepcopy(original); record['params'][field] = value; cases.append(record)
        for field, value in [('gas', True), ('gas', '100001'), ('gasPrice', '2000000001'),
                             ('value', '1'), ('to', WALLET)]:
            record = deepcopy(original); record['response']['data']['tx'][field] = value; cases.append(record)
        for record in cases:
            with self.subTest(record=record):
                self.inputs['quote_artifacts'][0] = self.pin(ref['path'], record)
                self.assertEqual(self.report()['numeric_status'], 'BLOCKED')

    def test_pins_and_private_output_no_overwrite_or_content_echo(self):
        src, dst = self.root / 'inputs.json', self.root / 'review.json'
        src.write_text(json.dumps(self.inputs))
        args = ['--inputs', str(src), '--output', str(dst), '--now', NOW]
        with redirect_stdout(StringIO()):
            self.assertEqual(main(args), 2)
            original = dst.read_bytes()
            self.assertEqual(main(args), 4)
        self.assertEqual(dst.read_bytes(), original)
        if os.name == 'posix':
            self.assertEqual(dst.stat().st_mode & 0o777, 0o600)
        for ref in self.inputs['files'].values():
            path = self.root / ref['path']
            raw = path.read_bytes()
            path.write_bytes(raw + b' ')
            try:
                with self.assertRaises((ContractError, Blocked)):
                    self.report()
            finally:
                path.write_bytes(raw)
        bad = deepcopy(self.inputs); bad['unexpected'] = 'DO_NOT_ECHO'
        src.write_text(json.dumps(bad))
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['--inputs', str(src), '--output', str(self.root / 'unused')]), 4)
        self.assertNotIn('DO_NOT_ECHO', output.getvalue())
        self.assertFalse((self.root / 'unused').exists())


if __name__ == '__main__':
    unittest.main()
