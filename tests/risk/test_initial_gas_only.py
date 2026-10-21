"""LD08-OG01: synthetic initial-only boundaries; no measurements or installation."""
from copy import deepcopy
from dataclasses import replace
import json
import hashlib
import unittest

import pytest

from larp.contracts import ContractError, Document
from larp.execution import Blocked, NATIVE_BNB, Payload, USDT
from larp.execution_live.service import map_command
from larp.research.fixtures import changed
from larp.risk.planner import plan
from larp.signer.policy import SigningPolicy
from larp.strategy.policy import decide
from larp.strategy.profiles import TOP_UP_KEYS, build_live_profiles, validate_live
from tests.strategy.live_fixtures import live_snapshot, registry, summary


def initial_only(p):
    p = deepcopy(p)
    for key in TOP_UP_KEYS:
        p.pop(key)
        p['provenance'].pop(key)
    p['initial_gas_only'] = True
    p['provenance']['initial_gas_only'] = {'decision_id': 'SYNTHETIC LD07', 'formula': 'initial only'}
    p['gas_action_budget_units'] = max(r['approve_gas_bnb_units'] + r['swap_gas_bnb_units']
                                     for r in p['quote_cost_summary']['symbols'].values())
    p['provenance']['gas_action_budget_units'] = {'decision_id': 'SYNTHETIC LD08', 'formula': 'max pair'}
    return p


def result(*, bnb, held=None):
    s = live_snapshot(held=held, quoted=True)
    c = s.context.read()
    p = initial_only(c['profile'])
    c['portfolio']['bnb_units'] = bnb
    s = replace(changed(s, profile=p, portfolio=c['portfolio']),
                policy_profile_hash=Document.from_dict(p).digest('StrategyProfile.v1'))
    return plan(s, decide(s, s.policy_state)).read()


@pytest.mark.parametrize('bnb', [0, 60_000])
def test_low_gas_never_requests_or_plans_a_topup_or_consumes_exit_reserve(bnb):
    r = result(bnb=bnb)
    assert not r['intents']  # the 80,000-unit full-exit reserve cannot fund a new buy
    assert all(q['symbol'] != 'BNB' for q in r['quote_requests'])


def test_affordable_mandatory_exit_continues_below_the_reserve():
    r = result(bnb=60_000, held={'NVDAB': 15_000})
    assert r['intents']
    assert all(i['side'] == 'SELL' and i['mandatory'] for i in r['intents'])
    assert all(i.get('kind') != 'GAS_TOP_UP' for i in r['intents'])


def test_candidate_profile_has_no_topup_values_and_keeps_reserve_and_provenance():
    from tests.strategy.test_s1_core import block
    for s1 in (None, block()):
        profiles = build_live_profiles(summary(), registry(), s1=s1, initial_gas_only=True)
        for p in (d.read() for d in profiles.values()):
            validate_live(p)
            assert p['initial_gas_only'] is True
            assert not set(TOP_UP_KEYS) & set(p)
            assert p['exit_gas_reserve_units'] == (5 if s1 else 4) * 20_000
            for what in ('reserve', 'provenance', 'contradictory', 'type'):
                broken = deepcopy(p)
                if what == 'reserve':
                    broken['exit_gas_reserve_units'] -= 1
                elif what == 'provenance':
                    del broken['provenance']['initial_gas_only']
                elif what == 'contradictory':
                    broken['gas_top_up_cash_units'] = 1
                else:
                    broken['initial_gas_only'] = 'true'
                with pytest.raises(ContractError):
                    validate_live(broken)


def test_execution_mapping_refuses_topup_even_when_native_tracing_is_enabled():
    from larp.execution_live.main import execution_mapping
    from tests.integration.test_gas_top_up_round import _command, LIMITS, ROUTER, WALLET
    mapping = execution_mapping(dict(build_id='v', router=ROUTER, native_trace=True,
        **{k: LIMITS[k] for k in ('max_gas', 'max_gas_price', 'gas_budget')}),
        dict(per_trade_cap_units=LIMITS['per_trade_cap_units'], slippage_bps=20, initial_gas_only=True),
        {'NVDAB': 18}, wallet=WALLET)
    with pytest.raises(Blocked, match='initial-only'):
        map_command(_command(), run_id='run', now_ms=100, **mapping)
    for side in ('BUY', 'SELL'):
        assert map_command(_command('NVDAB', side, 'BSTOCK_TRADE'), run_id='run', now_ms=100,
                           **mapping).kind == 'BSTOCK_TRADE'


def test_independent_signer_refuses_native_approve_and_swap_with_initial_policy():
    from tests.execution.test_signer_caps_proposal import inputs
    from tests.execution_fixtures import FakeDecoder, intent
    from tools.deploy.propose_signer_caps import build
    policy_value = build(inputs(), initial_gas_only=True)['candidates']['development']['signing_policy']
    policy = SigningPolicy.from_config(policy_value)
    assert NATIVE_BNB not in policy.allowed_tokens
    i = intent(kind='GAS_TOP_UP', receive_token=NATIVE_BNB, router=next(iter(policy.allowed_spenders)))
    for step in ('APPROVE', 'SWAP'):
        with pytest.raises(Blocked, match='intent token not allowed'):
            policy.check(i, step, Payload(56, i.wallet, i.router, 0, 0, 1, 1, '0x00'), FakeDecoder(), i.wallet)


def test_gate_b_initial_scope_keeps_missing_funding_and_measurement_gates_visible():
    from larp.research.fixtures import snapshot
    from tests.execution.test_gate_b_evidence import ReportTests, ChainEvidenceTests, ChainOpener, WALLET
    case = ReportTests('test_gb_report_uses_real_profile_validator_and_never_authorizes_signing')
    case.setUp()
    try:
        config = json.loads((case.root / 'execution.json').read_bytes())
        raw = json.dumps(build_live_profiles(summary(), registry(), initial_gas_only=True)['REHEARSAL'].read()).encode()
        (case.root / 'profile.json').write_bytes(raw)
        config['strategy_profile_sha256'] = hashlib.sha256(raw).hexdigest()
        raw = json.dumps(config).encode()
        (case.root / 'execution.json').write_bytes(raw)
        case.inputs['files']['execution_config']['sha256'] = hashlib.sha256(raw).hexdigest()
        missing = case.report()
        assert missing['checks']['DR-09']['status'] == 'VALIDATED'
        assert 'initial-only' in missing['checks']['DR-06']['detail']
        capture = ChainEvidenceTests().probe(case.root / 'chain-artifacts', ChainOpener())
        capture['source_id'] = 'fixture-rpc'
        ledger = snapshot().context.read()['portfolio']
        ledger.update(mode='dev', run_id='run', wallet_id=WALLET, bnb_decimals=18, bnb_units=10**18)
        for name, value in (('chain', capture), ('initial_state', ledger)):
            raw = json.dumps(value).encode()
            path = case.root / (name + '.json')
            path.write_bytes(raw)
            case.inputs['files'][name] = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}
        present = case.report()
        detail = present['checks']['DR-06']['detail']
        assert 'Initial-only funding/18-decimal ledger checked' in detail
        assert 'whole-run seeding' in detail and 'low-gas incident/alarm' in detail
        assert 'top-up still required' not in detail
        assert present['status'] == 'BLOCKED' and present['signing_enabled'] is False
    finally:
        case.doCleanups()


class InitialCaps(unittest.TestCase):
    def setUp(self):
        from tests.execution.test_caps_review import CapsReview
        self.fixture = CapsReview('test_covered_candidate_still_needs_owners_and_never_enables_signing')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configure(self.fixture)

    @staticmethod
    def configure(fixture):
        fixture.profile = initial_only(fixture.profile)
        old_pair = fixture.profile['gas_action_budget_units']
        fixture.profile['gas_sizing_budget_units'] = old_pair
        fixture.profile['provenance']['gas_sizing_budget_units'] = {'decision_id': 'SYNTHETIC LD10', 'formula': 'expected pair'}
        fixture.profile['gas_action_budget_units'] = fixture.config['gas_budget']
        fixture.profile['exit_gas_reserve_units'] = 4 * fixture.config['gas_budget']
        fixture.ledger['bnb_units'] = 3 * 10**15
        fixture.policy['allowed_tokens'].remove(NATIVE_BNB)
        fixture.inputs['quote_artifacts'] = [r for r in fixture.inputs['quote_artifacts'] if r['path'] != 'BNB.json']
        fixture.save_inputs()

    def test_stock_only_coverage_retains_false_readiness_and_exact_caps(self):
        r = self.fixture.report()
        self.assertEqual(r['numeric_status'], 'COVERED')
        self.assertEqual(r['gas_scope'], 'INITIAL_ONLY')
        self.assertEqual(r['missing_quote_coverage'], [])
        self.assertFalse(r['ready_to_install'])
        self.assertFalse(r['signing_enabled'])
        self.fixture.policy['max_input_units'][USDT] = str(self.fixture.profile['per_trade_cap_units'] * 10**12 - 1)
        self.fixture.save_inputs()
        self.assertIn('FULL_POSITION_USDT', self.fixture.report()['blockers'])

    def test_signed_child_envelope_and_profile_reservation_must_cover_the_configuration(self):
        original = self.fixture.config['gas_budget']
        self.fixture.config['gas_budget'] = original - 1
        self.fixture.save_inputs()
        self.assertIn('INITIAL_SIGNED_CHILD_GAS_ENVELOPE', self.fixture.report()['blockers'])
        self.fixture.config['gas_budget'] = original + 1
        self.fixture.save_inputs()
        self.assertIn('INITIAL_PROFILE_ACTION_BUDGET', self.fixture.report()['blockers'])

    def test_starting_native_balance_must_cover_the_exit_reserve(self):
        self.fixture.ledger['bnb_units'] = self.fixture.profile['exit_gas_reserve_units'] - 1
        self.fixture.save_inputs()
        r = self.fixture.report()
        self.assertEqual(r['numeric_status'], 'BLOCKED')
        self.assertIn('INITIAL_BNB_EXIT_RESERVE', r['blockers'])

    def test_native_policy_or_quote_cannot_pass_initial_only_coverage(self):
        self.fixture.policy['allowed_tokens'].append(NATIVE_BNB)
        self.fixture.save_inputs()
        self.assertIn('TOKEN_OR_SPENDER_SCOPE', self.fixture.report()['blockers'])
        self.fixture.policy['allowed_tokens'].remove(NATIVE_BNB)
        self.fixture.add_quote('native-again', USDT, NATIVE_BNB, 10**18)
        self.fixture.save_inputs()
        self.assertIn('QUOTE_ARTIFACT_REFUSED', self.fixture.report()['blockers'])

    def test_assembly_excludes_native_but_keeps_measurement_release_and_host_gates(self):
        from tests.signer.test_assembly import SignerAssembly
        case = SignerAssembly('test_candidate_reports_exact_hashes_and_keeps_approval_and_release_gates_open')
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.configure(case.fixture)
        files = case.build()
        config = json.loads(files['signer.json'])
        report = json.loads(files['signer-assembly-report.json'])
        self.assertNotIn(NATIVE_BNB, config['signing_policy']['allowed_tokens'])
        for flag in ('ready_to_install', 'signing_enabled', 'gate_b_accepted'):
            self.assertFalse(report[flag])
        self.assertIn('INITIAL_GAS_RESERVE_SEEDING_AND_ROUTE_FEE_QUALIFICATION', report['remaining_gates'])
        self.assertIn('SIGNING_LIFETIME_27', report['remaining_gates'])
        self.assertIn('REGISTERED_RELEASE_AND_HOST_ACCEPTANCE', report['remaining_gates'])

    def test_initial_only_and_allowance_recovery_keep_both_acceptance_gates(self):
        from tests.execution.test_mode_readiness import ModeReadiness
        case = ModeReadiness('test_assembly_untrusted_path_copies_only_policy_pair_and_retains_gates')
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.select_untrusted()
        fixture = case.case.fixture
        self.configure(fixture)
        fixture.config['allowance_recovery'] = True
        fixture.policy['allowance_recovery'] = True
        fixture.save_inputs()
        report = case.report()
        self.assertTrue(report['allowance_recovery'])
        self.assertEqual(report['numeric_review']['gas_scope'], 'INITIAL_ONLY')
        self.assertIn('INITIAL_GAS_RESERVE_SEEDING_AND_ROUTE_FEE_QUALIFICATION', report['remaining_gates'])
        self.assertIn('ALLOWANCE_RECOVERY_GAS_AND_HOST_ACCEPTANCE', report['remaining_gates'])
        self.assertFalse(report['ready_to_install'])
        fixture.config['allowance_recovery'] = False
        fixture.save_inputs()
        with self.assertRaises(ContractError):
            case.report()
