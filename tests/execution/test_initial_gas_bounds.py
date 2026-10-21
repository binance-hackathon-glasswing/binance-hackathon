"""GC01 bounds: configured maximum children, integer rounding, no funding authority."""
import pytest

from larp.contracts import ContractError
from tools.deploy.review_initial_gas import build, envelope, seeding


def test_two_children_and_all_six_cleanup_children_fit_independent_fee_ceiling():
    assert envelope(1_200_000, 160_000_000, 200_000_000_000_000, cleanup=False) == 384_000_000_000_000
    assert envelope(1_200_000, 160_000_000, 200_000_000_000_000, cleanup=True) == 1_536_000_000_000_000
    with pytest.raises(ContractError):
        envelope(1_200_000, 160_000_000, 191_999_999_999_999, cleanup=False)


@pytest.mark.parametrize('bad', [True, 0, -1, 1.2, '2', 2**256])
def test_numeric_bounds_refuse_malformed_or_overflowing_values(bad):
    with pytest.raises(ContractError):
        envelope(bad, 1, 1, cleanup=False)


def test_exit_reserve_is_counted_once_and_fractional_nonterminal_margin_rounds_up():
    assert seeding(0, 3, 4, 5, 4) == 12
    assert seeding(1, 3, 4, 5, 4) == 16
    assert seeding(15, 384_000_000_000_000, 4, 5, 4) == 8_736_000_000_000_000
    with pytest.raises(ContractError):
        seeding(15, 3, 4, 3, 4)
    with pytest.raises(ContractError):
        envelope(1, 1, 1, cleanup='true')


def test_new_candidates_preserve_historical_bytes_and_expected_cost_sizing():
    import json
    files = build()
    report = json.loads(files['review.json'])
    assert not report['signing_enabled'] and not report['ready_to_install']
    assert not report['cleanup_enabled']
    assert report['rounded_observed_25_percent_pair_wei'] == 200_011_520_000_000
    assert report['rounded_observed_20_percent_pair_wei'] == 192_011_040_000_000
    for name in ('rehearsal-live.json', 'final-live.json'):
        p = json.loads(files[name])
        assert p['exit_gas_reserve_units'] == 1_536_000_000_000_000
        assert p['gas_action_budget_units'] == 384_000_000_000_000
        assert p['gas_sizing_budget_units'] == 80_004_560_000_000
        assert p['minimum_trade_units'] == 18_637_420
