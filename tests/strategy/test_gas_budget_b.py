"""IDEA-061 LD09-B B1-B5: cap-price action budget and reserve, expected-price sizing budget (committed inputs)."""
import hashlib
import json
import re
from pathlib import Path

import pytest

from larp.contracts import ContractError, Document
from larp.strategy.profiles import build_live_profiles, main, validate_live

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / 'docs/build/evidence/quotes-complete-20261020'
LD04 = ROOT / 'docs/build/evidence/ld04-authority-profiles-20261020'
AUTHORITY = dict(seconds=660, margin=30, decision_id='IDEA-049-C LD04-V01 (Keegan, 2026-10-20)',
                 data_hash=hashlib.sha256((ROOT / 'docs/build/evidence/ld02-execution-packet-20261020.json')
                                          .read_bytes()).hexdigest())
ACTION, SIZING = 200_011_400_000_000, 80_004_560_000_000  # 1,000,057 gas * 5/4 at 0.16 / 0.064 gwei
BUDGET = dict(action_units=ACTION, sizing_units=SIZING, decision_id='IDEA-061 LD09-B', data_hash='b' * 64)


def inputs():
    return (Document.from_dict(json.loads((CAPTURE / 'quote-cost-summary.json').read_bytes())),
            Document.from_dict(json.loads((ROOT / 'config/intelligence/red_flags.v1.json').read_bytes())))


def refused(profile, reason):
    """validate_live reports every refusal as 'Malformed or incomplete'; the specific reason is the cause."""
    with pytest.raises(ContractError) as info:
        validate_live(profile)
    assert re.search(reason, str(info.value.__cause__ or info.value)), str(info.value.__cause__ or info.value)


def candidates(**options):
    return {env: doc.read() for env, doc in build_live_profiles(*inputs(), initial_gas_only=True,
                                                                  authority=AUTHORITY, **options).items()}


def test_b2_without_a_sizing_budget_the_ld04_candidates_reproduce_byte_for_byte(monkeypatch):
    # Historical artifacts retain the window under which they were frozen.
    from larp.strategy.profiles import WINDOWS
    monkeypatch.setitem(WINDOWS, "REHEARSAL", ("2026-10-21T00:00:00Z", "2026-10-22T00:00:00Z",
                                             "2026-10-23T00:00:00Z", "2026-10-26T14:45:00Z"))
    for env, doc in build_live_profiles(*inputs(), initial_gas_only=True, authority=AUTHORITY).items():
        assert doc.payload + b'\n' == (LD04 / (env.lower() + '-live.json')).read_bytes()


def test_b3_b4_reserve_at_cap_price_minimum_at_expected_price():
    plain, b = candidates(), candidates(gas_budget=BUDGET)
    for env in b:
        p = b[env]
        assert (p['gas_action_budget_units'], p['gas_sizing_budget_units']) == (ACTION, SIZING)
        assert p['exit_gas_reserve_units'] == 4 * ACTION
        assert 18_000_000 < p['minimum_trade_units'] <= 20_000_000  # about 18.64 USDT: fits a 20-USDT position
        assert p['minimum_trade_units'] > plain[env]['minimum_trade_units']  # sizing exceeds the FALLBACK pair
        for key in ('gas_action_budget_units', 'gas_sizing_budget_units', 'exit_gas_reserve_units',
                    'minimum_trade_units'):
            assert p['provenance'][key]['decision_id'] == 'IDEA-061 LD09-B'
            assert p['provenance'][key]['data_hash'] == 'b' * 64
        changed = {'gas_action_budget_units', 'gas_sizing_budget_units', 'exit_gas_reserve_units',
                   'minimum_trade_units', 'provenance'}
        assert {k: v for k, v in p.items() if k not in changed} == {
            k: v for k, v in plain[env].items() if k not in changed}
        validate_live(p)


def test_b1_b2_sizing_bounds_and_the_reserve_still_uses_the_action_budget():
    p = candidates(gas_budget=BUDGET)['REHEARSAL']
    for value, message in ((ACTION + 1, 'between'), (10**9, 'between'), (0, 'Invalid integer')):
        refused(dict(p, gas_sizing_budget_units=value), message)
    refused(dict(p, exit_gas_reserve_units=4 * ACTION - 1), 'exit gas reserve')
    coupled = {k: v for k, v in p.items() if k != 'gas_sizing_budget_units'}
    coupled['provenance'] = {k: v for k, v in p['provenance'].items() if k != 'gas_sizing_budget_units'}
    refused(coupled, 'minimum')  # without decoupling, the cap-price budget refuses the 20-USDT rehearsal minimum
    unsourced = dict(p, provenance={k: v for k, v in p['provenance'].items() if k != 'gas_sizing_budget_units'})
    refused(unsourced, 'Unset/unsourced')


def test_b1_top_up_profiles_refuse_a_sizing_budget():
    p = build_live_profiles(*inputs())['REHEARSAL'].read()
    p['gas_sizing_budget_units'] = SIZING
    p['provenance']['gas_sizing_budget_units'] = {'decision_id': 'X', 'formula': 'stray'}
    refused(p, 'Top-up profile')


@pytest.mark.parametrize('budget, scope', [
    (BUDGET, False),
    ({**BUDGET, 'sizing_units': ACTION + 1}, True),
    ({**BUDGET, 'sizing_units': 1}, True),
    ({k: v for k, v in BUDGET.items() if k != 'data_hash'}, True),
    ({**BUDGET, 'decision_id': ' '}, True),
])
def test_b3_builder_refusals(budget, scope):
    with pytest.raises(ContractError):
        build_live_profiles(*inputs(), initial_gas_only=scope, gas_budget=budget)


def test_b3_cli_flags_together(tmp_path, capsys):
    evidence = tmp_path / 'evidence.json'
    evidence.write_bytes(b'{"measured": true}\n')
    base = ['--summary', str(CAPTURE / 'quote-cost-summary.json'),
            '--predicates', str(ROOT / 'config/intelligence/red_flags.v1.json'), '--initial-gas-only']
    gas = ['--gas-action-budget-units', str(ACTION), '--gas-sizing-budget-units', str(SIZING),
           '--gas-budget-decision', 'IDEA-061 LD09-B', '--gas-budget-evidence', str(evidence)]
    with pytest.raises(SystemExit):
        main(base + ['--output-dir', str(tmp_path / 'partial')] + gas[:4])
    assert 'must be supplied together' in capsys.readouterr().err
    main(base + ['--output-dir', str(tmp_path / 'out')] + gas)
    p = json.loads((tmp_path / 'out/rehearsal-live.json').read_bytes())
    assert p['gas_sizing_budget_units'] == SIZING
    assert p['provenance']['gas_sizing_budget_units']['data_hash'] == hashlib.sha256(evidence.read_bytes()).hexdigest()


@pytest.mark.parametrize('candidate_dir', ['ld09b-gas-budget-profiles-20261021', 'rv120-profiles-20261021'])
def test_b4_committed_ld09b_candidates_reproduce_byte_for_byte(monkeypatch, candidate_dir):
    from larp.strategy.profiles import WINDOWS
    if candidate_dir.startswith('ld09b-'):
        # Historical artifacts retain the window under which they were frozen.
        monkeypatch.setitem(WINDOWS, "REHEARSAL", ("2026-10-21T00:00:00Z", "2026-10-22T00:00:00Z",
                                                 "2026-10-23T00:00:00Z", "2026-10-26T14:45:00Z"))
    folder = ROOT / 'docs/build/evidence' / candidate_dir
    evidence = ROOT / 'docs/build/evidence/ld02d-size-sell-20261021.json'
    budget = dict(BUDGET, decision_id='IDEA-061 LD09-B (Keegan, 2026-10-21)',
                  data_hash=hashlib.sha256(evidence.read_bytes()).hexdigest())
    built = build_live_profiles(*inputs(), initial_gas_only=True, authority=AUTHORITY, gas_budget=budget)
    for env, doc in built.items():
        assert doc.payload + b'\n' == (folder / (env.lower() + '-live.json')).read_bytes()


def test_split_budget_keeps_s1_five_action_reserve_and_monitor_thresholds():
    from larp.runtime.gas import InitialGasCheck
    from tests.strategy.live_fixtures import summary, registry, live_snapshot
    from tests.strategy.test_s1_core import block
    from larp.integration.runtime import initial_projection
    from types import SimpleNamespace
    budget = dict(action_units=50_000, sizing_units=25_000, decision_id='SYNTHETIC RV01', data_hash='c' * 64)
    p = build_live_profiles(summary(), registry(), s1=block(), initial_gas_only=True, gas_budget=budget)['FINAL'].read()
    assert p['exit_gas_reserve_units'] == 250_000
    monitor = InitialGasCheck(SimpleNamespace(), p)
    book = live_snapshot().context.read()['portfolio']
    for bnb, expected in [(25_000, 'PAIR_UNAFFORDABLE'), (50_000, 'BELOW_EXIT_RESERVE'), (250_000, 'OK')]:
        book['bnb_units'] = bnb
        assert monitor._state(initial_projection(book), [])['status'] == expected
    p['exit_gas_reserve_units'] = 5 * budget['sizing_units']
    refused(p, 'exit gas reserve')


def test_split_budget_does_not_spend_the_cap_price_exit_reserve_on_entries():
    from dataclasses import replace
    from larp.research.fixtures import changed
    from larp.risk.planner import plan
    from larp.strategy.policy import decide
    from tests.strategy.live_fixtures import live_snapshot, summary, registry
    budget = dict(action_units=50_000, sizing_units=25_000, decision_id='SYNTHETIC RV01', data_hash='c' * 64)
    p = build_live_profiles(summary(), registry(), initial_gas_only=True, gas_budget=budget)['FINAL'].read()
    s = live_snapshot(quoted=True)
    c = s.context.read()
    # Enough for four sizing budgets plus the fixture quote, insufficient to retain the cap-price reserve.
    c['portfolio']['bnb_units'] = 150_000
    s = replace(changed(s, profile=p, portfolio=c['portfolio']),
                policy_profile_hash=Document.from_dict(p).digest('StrategyProfile.v1'))
    result = plan(s, decide(s, s.policy_state)).read()
    assert not result['intents']


def test_scoped_rehearsal_candidate_reproduces_and_covers_two_signed_children():
    from tools.deploy.build_rehearsal_candidate import build
    doc = build()
    assert doc.payload + b'\n' == (ROOT / 'docs/build/evidence/rehearsal-qualified-inputs-20261021/rehearsal-deterministic.json').read_bytes()
    p = doc.read()
    assert p['gas_action_budget_units'] == 2 * 1200000 * 160000000
    assert p['exit_gas_reserve_units'] == 4 * p['gas_action_budget_units']
    assert p['gas_sizing_budget_units'] == 80004608000000
    assert p['evidence_mode'] == 'SHADOW' and p['baseline'] == 'EQUAL_WEIGHT'
    from larp.integration.contract import authority
    assert authority(p)['falsifier'] == 'SHADOW'
    validate_live(p)


def test_exit_split_rehearsal_candidate_reserves_two_children_per_position():
    # LD10-P03 D3: four positions x two balanced exit children x the signed-child action budget.
    from tools.deploy.build_rehearsal_candidate import build
    doc = build(exit_children=2)
    assert doc.payload + b'\n' == (ROOT / 'docs/build/evidence/rehearsal-exit-split-20261021/rehearsal-deterministic.json').read_bytes()
    p = doc.read()
    assert p['exit_gas_reserve_units'] == 8 * p['gas_action_budget_units'] == 3_072_000_000_000_000
    assert 'LD10-P03' in p['provenance']['exit_gas_reserve_units']['decision_id']
    previous = build().read()
    assert {k for k in p if p[k] != previous[k]} == {'exit_gas_reserve_units', 'provenance'}
    validate_live(p)
