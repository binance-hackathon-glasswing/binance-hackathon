"""IDEA-104 S5 (R3): FS1 on the dev wallet as it is, with FS1's AIand/ChatGPT model calls and evidence authority,
FS1's pinned token history and a window ending Tue Oct 27 12:00 SGT. Synthetic ports only."""
import hashlib
import json
from pathlib import Path

import pytest

from larp.contracts import ContractError, TargetKind
from larp.research.fixtures import changed, with_quotes
from larp.strategy.policy import decide
from larp.strategy.profiles import validate_live
from tests.strategy import test_s2_weekend as s2
from tests.strategy.test_execution_bounds import at, milliseconds, run
from tests.strategy.test_s1_core import block
from tests.strategy.test_s1_plan import AT_95

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence'
FS1_BLOCK = EVIDENCE / 'fs1-final-20261025/fs1-block.json'
FS1 = EVIDENCE / 'fs1-final-20261025/fs1-final-recovery.json'
S5 = EVIDENCE / 's5-rehearsal-profile-20261026/rehearsal-s5.json'
ROUTING = ROOT / 'config/intelligence/aiand-routing.fs1.json'
WINDOW = ('trade_after', 'new_risk_end', 'flatten_start', 'signing_end')
S5_WINDOW = ['2026-10-26T06:00:00Z', '2026-10-26T23:00:00Z', '2026-10-27T00:00:00Z', '2026-10-27T04:00:00Z']
DECISION = ("IDEA-104 S5 (2026-10-26): the FS1 final block (S2's block: IDEA-084 PF-01 values; weights 1/5, start UP, "
            "legs 3, expiry 3, deterministic limiter; hours KIT_OPEN_STATE, 5 attempts per leg) on the dev wallet, "
            "selling everything from Tuesday Oct 27 08:00 SGT")
# Profiles that S5 must leave byte for byte (file SHA-256).
UNCHANGED = {
    'fs1-final-20261025/fs1-final.json': '19176e6c6537291bb41f440636f51d7f6313d2444ebf7242cc145316d840f291',
    'fs1-final-20261025/fs1-final-recovery.json': 'b8ba06e248b48b6406d77c1bda4110001324382e91bb63c71a27ce514731892f',
    'fs1-rehearsal-20261025/fs1-rehearsal.json': '54802665f3fd28cfcdf4fcb3dd9653db2ce5fab00b4ecfd8a183774d436c4115',
    'fs1-rehearsal-20261025/fs1-rehearsal-recovery.json': '17ab891dec35f8db5388623042e826c65aa7ee7c1ca5861b18913e146d976e36',
}
# S5R3-1: the only non-provenance keys in which S5 may differ from FS1 FINAL (with recovery).
FS1_DIFFERENCES = sorted(('environment', 'cost_reserve_units', 'expected_equity_units', 'per_trade_cap_units', *WINDOW,
                          'policy_id', 'activation_self_check'))


def build(**options):
    from tools.deploy.build_rehearsal_candidate import build as rehearsal
    options.setdefault('fs1_rehearsal', True)
    options.setdefault('allowance_recovery', True)
    options.setdefault('s5', True)
    return rehearsal(2, s1_raw=FS1_BLOCK.read_bytes(), s1_decision=DECISION, **options)


def routing_options():
    raw = ROUTING.read_bytes()
    return dict(model_routing_raw=raw, model_routing_sha256=hashlib.sha256(raw).hexdigest())


def test_s5r3_1_s5_is_fs1_at_rehearsal_size():
    s5, fs1 = build().read(), json.loads(FS1.read_bytes())
    validate_live(s5)
    changed_keys = sorted(k for k in set(s5) | set(fs1) if k != 'provenance' and s5.get(k) != fs1.get(k))
    assert changed_keys == FS1_DIFFERENCES
    assert 'activation_self_check' not in s5 and s5['s1_capital_basis'] == 'EXCLUDE_GAS'
    assert s5['s1'] == fs1['s1'] and s5['slippage_bps'] == 20 and s5['environment'] == 'REHEARSAL'
    assert (s5['evidence_mode'], s5['falsifier_authority'], s5['statement_authority']) == (
        'BOUNDED_FALSIFIER', 'DISCRETIONARY_EXIT', 'SHADOW')
    assert s5['red_flag_authority'] == fs1['red_flag_authority']
    assert s5['policy_id'] == 'larp-s5-rehearsal-v1'


def test_s5r2_2_the_window_ends_tuesday_12_sgt():
    s5 = build().read()
    assert [s5[k] for k in WINDOW] == S5_WINDOW
    times = [milliseconds(v) for v in S5_WINDOW]
    assert times == sorted(times) and len(set(times)) == 4
    assert s5['signing_end'] == '2026-10-27T04:00:00Z'  # Tue Oct 27 12:00 SGT
    assert times[-1] < milliseconds('2026-10-28T00:00:00Z')  # inside the extended development time (F-126)


@pytest.mark.parametrize('options', [dict(fs1_rehearsal=False), dict(allowance_recovery=False),
                                     dict(carry_over=True), dict(scheduled_flatten_at='2026-10-27T00:00:00Z')])
def test_s5_3_builder_refusals(options):
    with pytest.raises(ContractError):
        build(**options)


def test_s5_4_committed_profile_rebuilds_and_fs1_is_unchanged():
    assert S5.read_bytes() == build().payload + b'\n'
    for name, sha in UNCHANGED.items():
        assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == sha, name


def test_s5r2_4_s5_and_fs1_require_history_and_other_profiles_do_not():
    from larp.marketdata.history import requires_history
    required = {name: requires_history(json.loads((EVIDENCE / name).read_bytes())) for name in UNCHANGED}
    assert all(required.values()), required
    assert requires_history(json.loads(S5.read_bytes()))
    for name in ('s2-rehearsal-profile-20261024/rehearsal-s2-deterministic.json',
                 's3-rehearsal-profile-20261024/rehearsal-s3-deterministic.json',
                 's4-rehearsal-profile-20261025/rehearsal-s4-deterministic.json',
                 's1-rehearsal-profile-20261023/rehearsal-s1-deterministic.json',
                 'rehearsal-exit-split-20261021/rehearsal-deterministic.json'):
        assert not requires_history(json.loads((EVIDENCE / name).read_bytes())), name


def test_s5r3_2_open_state_scope_admits_s5_only_in_dev():
    from larp.strategy.execution_bounds import require_open_state_scope
    s5 = json.loads(S5.read_bytes())
    for mode in ('dev', None):
        require_open_state_scope(s5, mode)
    for mode in ('live', 'offline', ''):
        with pytest.raises(ContractError):
            require_open_state_scope(s5, mode)
    fs1r = json.loads((EVIDENCE / 'fs1-rehearsal-20261025/fs1-rehearsal-recovery.json').read_bytes())
    s2_profile = json.loads((EVIDENCE / 's2-rehearsal-profile-20261024/rehearsal-s2-deterministic.json').read_bytes())
    authority = dict(evidence_mode='BOUNDED_FALSIFIER', falsifier_authority='DISCRETIONARY_EXIT')
    for other in (dict(fs1r, **authority), dict(s2_profile, **authority), dict(s5, statement_authority='BOUNDED'),
                  dict(s5, evidence_mode='SHADOW'), dict(s5, environment='FINAL')):
        with pytest.raises(ContractError):
            require_open_state_scope(other, 'dev')


def round_at(value, held=None, *, cash_units=None, bnb_units=None, sizing=False):
    """A round at `value` on the S5 window, inside one synthetic session that spans Mon 13:30Z to Tue 13:30Z."""
    p = json.loads(S5.read_bytes())
    session = at(value).context.read()['session_index']
    changes = dict(s1=block(execution=dict(s2.EXECUTION, hours='KIT_OPEN_STATE')), **dict(zip(WINDOW, S5_WINDOW)))
    if sizing:
        changes.update({k: p[k] for k in ('cost_reserve_units', 'minimum_trade_units', 'per_trade_cap_units',
                                          'entry_cost_basis', 's1_reduction_cost_cap_bps', 'slippage_bps')})
        changes['s1_capital_basis'] = p['s1_capital_basis']
    s = at(value, held=held, profile_changes=changes, risk=dict(day=value[:10]),
           execution_session=dict(index=session, open_ms=milliseconds('2026-10-26T13:30:00Z'),
                                  close_ms=milliseconds('2026-10-26T20:00:00Z'),
                                  next_open_ms=milliseconds('2026-10-27T13:30:00Z')))
    if cash_units is not None:
        portfolio = s.context.read()['portfolio']
        bnb_price = p['quote_cost_summary']['bnb_price_units']
        positions = sum(v['units'] * 10_000 for v in portfolio['positions'].values())
        equity = cash_units + positions + bnb_units * bnb_price // 10**18
        portfolio.update(cash_units=cash_units, bnb_units=bnb_units, bnb_price_units=bnb_price, bnb_decimals=18,
                         opening_equity_units=equity)
        portfolio['risk'].update(day_anchor_units=equity, peak_units=equity)
        s = changed(s, portfolio=portfolio)
    return s, run(with_quotes(s))


def test_s5r3_5_buys_until_tue_07_sgt_and_sells_everything_from_08_sgt():
    _, before = round_at('2026-10-26T22:59:00Z')
    assert [(i['side'], i['mandatory']) for i in before['intents']] == [('BUY', False)], before['rejections']
    _, stopped = round_at('2026-10-26T23:00:00Z')
    assert not [i for i in stopped['intents'] if i['side'] == 'BUY']
    assert not [q for q in stopped['quote_requests'] if q['side'] == 'BUY']
    _, flatten = round_at('2026-10-27T00:00:00Z', held=dict(NVDAB=AT_95, SKHYB=AT_95))
    assert {r['symbol']: r['reasons'] for r in flatten['requirements']} == {
        'NVDAB': ['TERMINAL_FLATTEN'], 'SKHYB': ['TERMINAL_FLATTEN']}
    assert flatten['intents'] and all((i['side'], i['mandatory']) == ('SELL', True) for i in flatten['intents'])


# Run 6's closing balance of the dev wallet (IDEA-097): 81.373047 USDT and 0.024973 BNB.
RUN6_CASH, RUN6_BNB = 81_373_047, 24_973_000_000_000_000


def test_s5r3_4_gas_excluded_capital_needs_about_98_usdt_of_cash():
    p = json.loads(S5.read_bytes())
    s, short = round_at('2026-10-26T16:00:00Z', cash_units=RUN6_CASH, bnb_units=RUN6_BNB, sizing=True)
    assert not [t for t in decide(s, s.policy_state).targets if t.kind is TargetKind.TARGET_WEIGHT]
    assert not [i for i in short['intents'] if i['side'] == 'BUY'], short['intents']
    assert not [q for q in short['quote_requests'] if q['side'] == 'BUY'], short['quote_requests']
    _, funded = round_at('2026-10-26T16:00:00Z', cash_units=RUN6_CASH + 20_000_000, bnb_units=RUN6_BNB, sizing=True)
    buys = [i for i in funded['intents'] if i['side'] == 'BUY']
    assert len(buys) == 1 and int(buys[0]['cash_units']) >= p['minimum_trade_units'], funded['intents']


def test_s5r2_3_signed_dev_preparation_with_fs1_routing_pins_history_and_models():
    from larp.marketdata.history import CONFIG_FILE
    from larp.runtime import gate_a_check
    from tests.strategy import test_s1_rehearsal as rh
    raw = S5.read_bytes()
    files = rh.prepared(json.loads(raw), **routing_options(), **s2.POLICY)
    values = {n: json.loads(item) for n, item in files.items() if n.endswith('.json')}
    driver = values['runtime.json']['driver']
    assert driver['assessor'] == 'aiand_routed'
    assert driver['model_routing_sha256'] == hashlib.sha256(ROUTING.read_bytes()).hexdigest()
    assert files['model-routing.json'] == ROUTING.read_bytes()
    assert driver['token_history_file'] == CONFIG_FILE
    assert driver['token_history_sha256'] == hashlib.sha256(files['token-history.json']).hexdigest()
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)


def test_s5r3_3_deterministic_signed_preparation_is_refused():
    from tests.strategy import test_s1_rehearsal as rh
    with pytest.raises(ContractError):
        rh.prepared(json.loads(S5.read_bytes()), **s2.POLICY)


def test_s5r2_3_preparation_refuses_s5_without_token_history():
    from tests.strategy import test_s1_rehearsal as rh
    with pytest.raises(ContractError, match='token history'):
        rh.prepared(json.loads(S5.read_bytes()), token_history_raw=None, **routing_options(), **s2.POLICY)


def routed_runtime(history=True):
    """The S5 runtime as M4 prepares it: dev mode, service execution, FS1 routing. Returns (runtime, fixture)."""
    from unittest.mock import patch
    from larp.intelligence.model_budget import ModelBudget
    from larp.runtime import gate_a
    from larp.runtime.service import build_driver
    from tests.runtime.test_driver import Composition, Store
    from tests.runtime.test_gate_a import captured
    from tests.marketdata.test_session_history import SEMANTICS
    fixture = Composition(); fixture.setUp()
    raw, profile = ROUTING.read_bytes(), S5.read_bytes()
    (fixture.root / 'routing.json').write_bytes(raw)
    pacing = json.loads(raw)['openai_pacing']
    ModelBudget.initialize(fixture.root / 'openai-budget.sqlite', json.loads(raw)['budget_account'],
                           initial_spent=pacing['prior_spent_micro_usd'], total=pacing['total_micro_usd'],
                           reserve=0, pacing=pacing)
    cfg = fixture.config(execution='service', intelligence_mode='live', expiry_grace_ms=5000, assessor='aiand_routed',
                         model_routing_file=str(fixture.root / 'routing.json'),
                         model_routing_sha256=hashlib.sha256(raw).hexdigest(), model_budget_root=str(fixture.root),
                         model_adoption_ref='SYNTHETIC IDEA-104 S5')
    base = json.loads((gate_a.ROOT / 'config/runtime/runtime.example.json').read_bytes())['driver']
    for key in ('balance_check_interval_ms', 'balance_check_max_age_ms', 'price_jump_check_bps',
                'assessment_workers', 'continuation_rounds'):
        cfg['driver'][key] = base[key]
    cfg['driver']['balance_rpc_providers'] = [dict(url='https://rpc.invalid/', source_id='synthetic-rpc')]
    (fixture.root / 'profile.json').write_bytes(profile)
    cfg['driver']['strategy_profile_sha256'] = gate_a.digest(profile)
    cfg['driver']['issuers'] = gate_a.issuer_map(captured())
    if history:
        history_raw = json.dumps(SEMANTICS).encode()
        (fixture.root / 'token-history.json').write_bytes(history_raw)
        cfg['driver'].update(token_history_file=str(fixture.root / 'token-history.json'),
                             token_history_sha256=hashlib.sha256(history_raw).hexdigest())
    cfg['mode'] = 'dev'
    secrets = dict(fixture.secrets, LARP_AIAND_API_KEY='synthetic-aiand-runtime-key')
    try:
        with patch('socket.create_connection', side_effect=AssertionError('No network during construction')):
            return build_driver(cfg, Store(), secrets), fixture
    except BaseException:
        fixture.doCleanups()
        raise


def test_s5r3_3_dev_runtime_runs_five_routed_assessors_and_session_history():
    from larp.intelligence.routing import RoutedAssessor
    from larp.marketdata.history import SessionHistory
    runtime, fixture = routed_runtime()
    try:
        runtime.ports['evidence'].close()
        assert isinstance(runtime.coordinator.assessor, RoutedAssessor)
        pool = runtime.assessments.assessors
        assert len(pool) == 5 and all(isinstance(a, RoutedAssessor) for a in pool)
        assert isinstance(runtime.coordinator.context_builder.series, SessionHistory)
    finally:
        fixture.doCleanups()


def test_s5r2_3_startup_refuses_s5_without_token_history():
    with pytest.raises(ContractError, match='token history'):
        routed_runtime(history=False)
