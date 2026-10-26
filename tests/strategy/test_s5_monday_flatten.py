"""IDEA-104 S5-1..S5-5 and R2 S5R2-1..S5R2-5: FS1's settings on the dev wallet, running to Tue Oct 27 12:00 SGT with
FS1's pinned token-history input. Synthetic ports only."""
import hashlib
import json
from pathlib import Path

import pytest

from larp.contracts import ContractError
from larp.research.fixtures import with_quotes
from larp.strategy.profiles import validate_live
from tests.strategy import test_s2_weekend as s2
from tests.strategy.test_execution_bounds import at, milliseconds, run
from tests.strategy.test_s1_core import block
from tests.strategy.test_s1_plan import AT_95

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence'
FS1_BLOCK = EVIDENCE / 'fs1-final-20261025/fs1-block.json'
FS1R = EVIDENCE / 'fs1-rehearsal-20261025/fs1-rehearsal-recovery.json'
S5 = EVIDENCE / 's5-rehearsal-profile-20261026/rehearsal-s5.json'
WINDOW = ('trade_after', 'new_risk_end', 'flatten_start', 'signing_end')
S5_WINDOW = ['2026-10-26T06:00:00Z', '2026-10-26T23:00:00Z', '2026-10-27T00:00:00Z', '2026-10-27T04:00:00Z']
DECISION = ("IDEA-104 S5 (2026-10-26): the FS1 final block (S2's block: IDEA-084 PF-01 values; weights 1/5, start UP, "
            "legs 3, expiry 3, deterministic limiter; hours KIT_OPEN_STATE, 5 attempts per leg) on the dev wallet, "
            "selling everything from Monday 21:00 SGT")
# Profiles that S5 must leave byte for byte (file SHA-256).
UNCHANGED = {
    'fs1-final-20261025/fs1-final.json': '19176e6c6537291bb41f440636f51d7f6313d2444ebf7242cc145316d840f291',
    'fs1-final-20261025/fs1-final-recovery.json': 'b8ba06e248b48b6406d77c1bda4110001324382e91bb63c71a27ce514731892f',
    'fs1-rehearsal-20261025/fs1-rehearsal.json': '54802665f3fd28cfcdf4fcb3dd9653db2ce5fab00b4ecfd8a183774d436c4115',
    'fs1-rehearsal-20261025/fs1-rehearsal-recovery.json': '17ab891dec35f8db5388623042e826c65aa7ee7c1ca5861b18913e146d976e36',
}


def build(**options):
    from tools.deploy.build_rehearsal_candidate import build as rehearsal
    options.setdefault('fs1_rehearsal', True)
    options.setdefault('allowance_recovery', True)
    options.setdefault('s5', True)
    return rehearsal(2, s1_raw=FS1_BLOCK.read_bytes(), s1_decision=DECISION, **options)


def test_s5_1_differs_from_fs1_r_recovery_only_in_the_window_and_policy():
    s5, fs1r = build().read(), json.loads(FS1R.read_bytes())
    validate_live(s5)
    changed = sorted(k for k in set(s5) | set(fs1r) if s5.get(k) != fs1r.get(k))
    assert changed == sorted(WINDOW + ('policy_id', 'provenance'))
    prov = sorted(k for k in set(s5['provenance']) | set(fs1r['provenance'])
                  if s5['provenance'].get(k) != fs1r['provenance'].get(k))
    # s1 and baseline carry the decision text behind the same block bytes; nothing else in them differs.
    assert prov == sorted(WINDOW + ('baseline', 'policy_id', 's1'))
    for key in ('s1', 'baseline'):
        a, b = s5['provenance'][key], fs1r['provenance'][key]
        assert [k for k in set(a) | set(b) if a.get(k) != b.get(k)] == ['decision_id'], key
    assert s5['provenance']['s1']['data_hash'] == fs1r['provenance']['s1']['data_hash']
    assert s5['s1'] == fs1r['s1'] and s5['slippage_bps'] == 20 and s5['environment'] == 'REHEARSAL'
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


def round_at(value, held=None):
    """A round at `value` on the S5 window, inside one synthetic session that spans Mon 22:59Z to Tue 00:00Z."""
    session = at(value).context.read()['session_index']
    changes = dict(s1=block(execution=dict(s2.EXECUTION, hours='KIT_OPEN_STATE')),
                   **dict(zip(WINDOW, S5_WINDOW)))
    return run(with_quotes(at(value, held=held, profile_changes=changes, risk=dict(day=value[:10]),
        execution_session=dict(index=session, open_ms=milliseconds('2026-10-26T13:30:00Z'),
                               close_ms=milliseconds('2026-10-26T20:00:00Z'),
                               next_open_ms=milliseconds('2026-10-27T13:30:00Z')))))


def test_s5r2_5_buys_until_tue_07_sgt_and_sells_everything_from_08_sgt():
    before = round_at('2026-10-26T22:59:00Z')
    assert [(i['side'], i['mandatory']) for i in before['intents']] == [('BUY', False)], before['rejections']
    stopped = round_at('2026-10-26T23:00:00Z')
    assert not [i for i in stopped['intents'] if i['side'] == 'BUY']
    assert not [q for q in stopped['quote_requests'] if q['side'] == 'BUY']
    flatten = round_at('2026-10-27T00:00:00Z', held=dict(NVDAB=AT_95, SKHYB=AT_95))
    assert {r['symbol']: r['reasons'] for r in flatten['requirements']} == {
        'NVDAB': ['TERMINAL_FLATTEN'], 'SKHYB': ['TERMINAL_FLATTEN']}
    assert flatten['intents'] and all((i['side'], i['mandatory']) == ('SELL', True) for i in flatten['intents'])


def test_s5r2_3_signed_dev_preparation_pins_token_history_and_the_runtime_uses_it():
    from larp.marketdata.history import CONFIG_FILE, SessionHistory
    from larp.runtime import gate_a_check
    from tests.strategy import test_s1_rehearsal as rh
    raw = S5.read_bytes()
    files = rh.prepared(json.loads(raw), **s2.POLICY)
    values = {n: json.loads(item) for n, item in files.items() if n.endswith('.json')}
    driver = values['runtime.json']['driver']
    assert driver['token_history_file'] == CONFIG_FILE
    assert driver['token_history_sha256'] == hashlib.sha256(files['token-history.json']).hexdigest()
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)
    runtime = s2.build_runtime(raw)
    assert isinstance(runtime.coordinator.context_builder.series, SessionHistory)


def test_s5r2_3_preparation_and_startup_refuse_s5_without_token_history():
    from tests.strategy import test_s1_rehearsal as rh
    with pytest.raises(ContractError, match='token history'):
        rh.prepared(json.loads(S5.read_bytes()), token_history_raw=None, **s2.POLICY)
    with pytest.raises(ContractError, match='token history'):
        s2.build_runtime(S5.read_bytes(), history=False)
