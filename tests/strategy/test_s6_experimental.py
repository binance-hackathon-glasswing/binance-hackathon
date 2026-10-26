"""IDEA-106: S6 is EXPERIMENTAL and must not deploy. Offline only; no keys, network or wallet.

These tests prove that the live profile validator refuses the S6 design document and any FS1 profile grafted with
S6 (baseline, block or environment), that FS1 itself still validates, and that the design values are consistent."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

from larp.contracts import ContractError
from larp.strategy.profiles import validate_live

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / 'config/strategy/experimental/s6-design.v0.json'
FS1 = ROOT / 'docs/build/evidence/fs1-final-20261025/fs1-final.json'
SYMBOLS = {'GOOGLB', 'MSFTB', 'NVDAB', 'SKHYB', 'TSLAB'}


def design():
    return json.loads(DESIGN.read_bytes())


def fs1():
    return json.loads(FS1.read_bytes())


def sourced(p, key):
    """Give a grafted key provenance, so a refusal cannot come from missing provenance alone."""
    p['provenance'][key] = {'decision_id': 'IDEA-106 S6 (experimental, not approved)',
                            'formula': 'IDEA-106 design value'}
    return p


def test_design_carries_do_not_deploy_markers():
    d = design()
    assert d['schema'] == 'S6ExperimentDesign.v0' and d['schema'] != 'StrategyProfile.v1'
    assert (d['mode'], d['environment'], d['deploy_status'], d['ledger']) == (
        'EXPERIMENTAL_DO_NOT_DEPLOY', 'EXPERIMENTAL', 'NOT_APPROVED', 'IDEA-106')
    assert d['mode'] != 'LIVE' and d['environment'] not in ('FINAL', 'REHEARSAL')
    assert 'IDEA-106' in d['notice'] and 'Must not be installed' in d['notice']


def test_design_names_no_wallet_or_credential():
    text = DESIGN.read_text().lower()
    for word in ('wallet_address', 'private', 'mnemonic', 'secret', 'api_key', '0x'):
        assert word not in text


def test_validate_live_refuses_the_design_document():
    with pytest.raises(ContractError):
        validate_live(design())


def test_fs1_control_still_validates():
    validate_live(fs1())  # the refusals below come from the S6 changes, not from a broken base profile


@pytest.mark.parametrize('environment', ['FINAL', 'REHEARSAL'])
def test_fs1_with_s6_baseline_and_block_is_refused(environment):
    p = fs1()
    p['environment'] = environment
    p['baseline'] = design()['baseline']
    p['s6'] = deepcopy(design()['s6'])
    for key in ('baseline', 's6'):
        sourced(p, key)
    with pytest.raises(ContractError):
        validate_live(p)


@pytest.mark.parametrize('environment', ['FINAL', 'REHEARSAL'])
def test_s6_baseline_hits_the_decided_scope_refusal(environment):
    """On a generated profile that validates, changing only the baseline to S6 is refused by the v1 scope check."""
    from larp.strategy.profiles import build_live_profiles
    from tests.strategy.live_fixtures import registry, summary
    p = build_live_profiles(summary(), registry())[environment].read()
    validate_live(p)
    p['baseline'] = design()['baseline']
    sourced(p, 'baseline')
    with pytest.raises(ContractError, match='Live profile differs from decided v1 scope'):
        validate_live(p)


def test_fs1_with_s6_block_added_is_refused():
    p = sourced(fs1(), 's6')
    p['s6'] = deepcopy(design()['s6'])
    p['s1'].pop('weights')  # an S6 book replaces the 1/5 weights
    sourced(p, 's1')
    with pytest.raises(ContractError):
        validate_live(p)


@pytest.mark.parametrize('environment', ['EXPERIMENTAL', 'S6', '', None])
def test_fs1_in_an_experimental_environment_is_refused(environment):
    p = fs1()
    p['environment'] = environment
    with pytest.raises(ContractError, match='LIVE values must be measured and decided'):
        validate_live(p)


def test_fs1_with_the_design_values_origin_is_refused():
    p = fs1()
    p['values_origin'] = design()['values_origin']
    with pytest.raises(ContractError, match='LIVE values must be measured and decided'):
        validate_live(p)


def test_fs1_with_an_s6_concentrated_top_position_is_refused():
    """S6's ~63 USDT positions exceed FS1's 38.2 USDT per-trade cap; validate_live refuses the book (IDEA-106 plan 6)."""
    p = fs1()
    p['s1']['weights'] = {'GOOGLB': [1, 3], 'MSFTB': [0, 1], 'NVDAB': [1, 3], 'SKHYB': [1, 3], 'TSLAB': [0, 1]}
    p['s1']['weight_cap'] = [1, 3]
    p['s1']['hard_name_weight'] = [2, 5]
    with pytest.raises(ContractError):
        validate_live(p)


def test_design_values_are_consistent():
    d = design()
    s = d['s6']
    k = s['held_names']
    gross, name, cap = (Fraction(*s[key]) for key in ('gross_weight', 'name_weight', 'weight_cap'))
    assert set(d['symbols']) == SYMBOLS and 1 <= k < len(SYMBOLS)
    assert name * k == gross <= Fraction(19, 20)
    assert name <= cap < Fraction(*s['hard_name_weight']) <= 1
    assert s['max_swaps_per_session'] == 1 and 0 < s['max_swaps_per_run'] <= 6
    assert s['lookback_sessions'] == 10 and s['swap_margin_bps'] == 150
    assert s['model_view_authority'] == 'SHADOW' and s['rotation_sell_requires_buy_permitted'] is True
    sizes = d['sizes_usdt_units']
    position = sizes['expected_equity_units'] * name
    legs = -(-position // sizes['per_trade_cap_units'])
    assert legs == 2 and position / legs >= sizes['minimum_trade_units']  # every rotation leg is above the minimum


def test_design_costs_cite_the_unchanged_fs1_profile():
    assert design()['backtest']['cost_source_profile_sha256'] == hashlib.sha256(FS1.read_bytes()).hexdigest()
