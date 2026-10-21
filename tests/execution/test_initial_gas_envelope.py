"""GE-01: actual caps/assembler boundaries and exact configured gas envelopes, offline only."""
from copy import deepcopy

import pytest

from tests.execution import test_caps_review as caps_fixtures
from tests.risk import test_initial_gas_only as initial_fixtures


@pytest.fixture
def case():
    c = caps_fixtures.CapsReview('test_covered_candidate_still_needs_owners_and_never_enables_signing')
    c.setUp()
    initial_fixtures.InitialCaps.configure(c)
    try:
        yield c
    finally:
        c.doCleanups()


def set_action(case, amount):
    p = case.profile
    measured = max(r['approve_gas_bnb_units'] + r['swap_gas_bnb_units']
                   for r in p['quote_cost_summary']['symbols'].values())
    p['gas_action_budget_units'] = amount
    p['gas_sizing_budget_units'] = measured
    p['provenance']['gas_sizing_budget_units'] = dict(decision_id='SYNTHETIC GE01', formula='measured sizing')
    p['exit_gas_reserve_units'] = 4 * amount
    case.ledger['bnb_units'] = 5 * amount
    case.save_inputs()


def test_profile_budget_must_cover_the_configured_execution_parent(case):
    # Before GE-01 this reports COVERED with an 8e12 profile budget and 4e14 parent.
    case.profile['gas_action_budget_units'] = 8 * 10**12
    case.profile['exit_gas_reserve_units'] = 4 * 8 * 10**12
    case.save_inputs()
    r = case.report()
    assert r['numeric_status'] == 'BLOCKED'
    assert 'INITIAL_PROFILE_ACTION_ENVELOPE_WEI' in r['blockers']


def test_configured_parent_covers_two_independently_bounded_transactions(case):
    set_action(case, 4 * 10**14)
    case.config['gas_budget'] = 4 * 10**14 - 1
    case.save_inputs()
    assert 'CONFIGURED_ACTION_ENVELOPE_WEI' in case.report()['blockers']


def test_cleanup_scope_budgets_every_allowed_supporting_step(case):
    set_action(case, 2 * 10**15)
    case.config.update(untrusted_router_policy_file='/not-read', untrusted_router_policy_sha256='a' * 64)
    case.config['allowance_recovery'] = True
    case.policy['allowance_recovery'] = True
    case.save_inputs()
    assert 'CONFIGURED_ACTION_ENVELOPE_WEI' in case.report()['blockers']


def test_covered_action_still_preserves_readiness_and_expected_sizing(case):
    set_action(case, 4 * 10**14)
    r = case.report()
    assert r['numeric_status'] == 'COVERED'
    assert r['gas_envelope']['max_transactions'] == 2
    assert r['gas_envelope']['configured_action_wei'] == 4 * 10**14
    assert not r['ready_to_install'] and not r['signing_enabled']
