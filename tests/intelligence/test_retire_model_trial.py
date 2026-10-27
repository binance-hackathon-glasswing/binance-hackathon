"""S5-DEPLOY01: expired-trial retirement preserves accounting and refuses unsafe transitions. No network."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from larp.contracts import ContractError
from larp.intelligence.model_budget import ModelBudget
from tools.deploy.retire_model_trial import retire

ROOT = Path(__file__).resolve().parents[2]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def setup(tmp_path):
    tmp_path.chmod(0o700)
    spec = json.loads((ROOT / 'config/intelligence/aiand-routing.fs1.json').read_bytes())
    spec['openai_pacing'].update(start_ms=0, end_ms=100_000, period_ms=10_000)
    trial = dict(schema='OpenAITrial.v1', trial_id='synthetic-expired', start_ms=0, end_ms=10_000,
                 total_micro_usd=8_000_000, utc_day_micro_usd=2_500_000)
    path = tmp_path / 'budget.sqlite'
    budget = ModelBudget.initialize(path, spec['budget_account'], initial_spent=2_000_000,
        total=50_000_000, reserve=0, pacing=spec['openai_pacing'], trial=trial, clock_ms=lambda: 1_000)
    a = budget.admit(100, 'settled'); budget.before_dispatch(a); budget.settle(a, 70)
    b = budget.admit(100, 'unknown'); budget.before_dispatch(b); budget.settle(b, None)
    return path, spec, trial


def run(path, spec, *, now=20_000, expected=None):
    raw = json.dumps(spec).encode()
    return retire(path, raw, expected_sha256=expected or digest(path.read_bytes()), routing_sha256=digest(raw),
                  backup_dir=path.parent / 'retired', now_ms=now)


def rows(path, table):
    with sqlite3.connect(path) as db:
        return db.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall()


def test_preserves_every_charge_unknown_attribution_clock_and_original_bytes(tmp_path):
    path, spec, trial = setup(tmp_path)
    raw = path.read_bytes()
    before = {t: rows(path,t) for t in ['account','charges','switches','trial','trial_charges','pacing']}
    result = run(path,spec)
    assert result['status'] == 'EXPIRED_TRIAL_RETIRED'
    assert result['charged_micro_usd'] == 2_000_170 and result['unknown_micro_usd'] == 100
    assert next((tmp_path/'retired').glob('*.sqlite')).read_bytes() == raw
    for t in ['account','charges','switches']:
        assert rows(path,t) == before[t]
    assert rows(path,'retired_trial') == before['trial']
    assert rows(path,'retired_trial_charges') == before['trial_charges']
    assert rows(path,'pacing')[0][2] == before['pacing'][0][2]
    b = ModelBudget(path,spec['budget_account'],total=50_000_000,reserve=0,
                    pacing=spec['openai_pacing'],clock_ms=lambda:20_000)
    assert b.snapshot()['charged_micro_usd'] == 2_000_170
    with pytest.raises(ContractError):
        ModelBudget(path,spec['budget_account'],total=50_000_000,reserve=0,
                    pacing=spec['openai_pacing'],trial=trial,clock_ms=lambda:20_000)


@pytest.mark.parametrize('case', ['unexpired','clock','global_stop','trial_stop','reserved','pacing','account',
                                  'missing_attribution','hash','already_retired'])
def test_refusals_do_not_change_ledger(tmp_path,case):
    path,spec,trial = setup(tmp_path)
    now, expected = 20_000, None
    if case == 'unexpired': now = 9_999
    elif case == 'hash': expected = '0'*64
    elif case == 'pacing': spec['openai_pacing']['prior_spent_micro_usd'] += 1
    elif case == 'account': spec['budget_account'] = 'another-account'
    elif case == 'already_retired': run(path,spec)
    else:
        with sqlite3.connect(path) as db:
            if case == 'clock': db.execute('UPDATE pacing SET last_ms=30000')
            elif case == 'global_stop': db.execute("UPDATE account SET external_only=1,reason='STORAGE_STOP'")
            elif case == 'trial_stop': db.execute("UPDATE trial SET stopped=1,reason='ACCOUNTING_STOP'")
            elif case == 'reserved': db.execute("UPDATE charges SET state='RESERVED' WHERE request_id='unknown'")
            elif case == 'missing_attribution': db.execute('DELETE FROM trial_charges')
    before = path.read_bytes()
    with pytest.raises(ContractError): run(path,spec,now=now,expected=expected)
    assert path.read_bytes() == before


def test_changed_routing_bytes_refused_before_backup(tmp_path):
    path,spec,_ = setup(tmp_path)
    before = path.read_bytes()
    with pytest.raises(ContractError):
        retire(path,json.dumps(spec).encode(),expected_sha256=digest(before),routing_sha256='0'*64,
               backup_dir=tmp_path/'retired',now_ms=20_000)
    assert path.read_bytes() == before and not (tmp_path/'retired').exists()
