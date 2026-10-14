"""Source-derived final-review B requirements; synthetic external inputs only."""

from dataclasses import replace

import pytest

from larp.contracts import ContractError, Document
from larp.research.fixtures import changed
from larp.strategy.schema import profile
from tests.strategy.live_fixtures import live_snapshot


def bind_profile(snapshot, values):
    return replace(changed(snapshot, profile=values),
                   policy_profile_hash=Document.from_dict(values).digest("StrategyProfile.v1"))


@pytest.mark.parametrize("field,changed_value", [
    ("operating_name_weight", [1, 10]),
    ("operating_gross_weight", [7, 10]),
    ("hard_name_weight", [6, 25]),
    ("hard_gross_weight", [17, 20]),
    ("top_up_below_gross_weight", [7, 10]),
])
def test_b_req_050_live_profile_cannot_change_adopted_caps(field, changed_value):
    snapshot = live_snapshot()
    values = snapshot.context.read()["profile"]
    values[field] = changed_value
    with pytest.raises(ContractError):
        profile(bind_profile(snapshot, values))


def test_b_req_010_equivalent_fractions_and_separate_stress_budget_are_valid():
    snapshot = live_snapshot()
    values = snapshot.context.read()["profile"]
    values.update(operating_name_weight=[2, 10], operating_gross_weight=[8, 10],
                  hard_name_weight=[2, 8], hard_gross_weight=[18, 20],
                  top_up_below_gross_weight=[6, 8], regime_gross_weight=[2, 5])
    assert profile(bind_profile(snapshot, values))["regime_gross_weight"] == [2, 5]
