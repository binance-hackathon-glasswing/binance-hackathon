"""IDEA-110 TS-6: standalone preparation of the temporary self-check on the final wallet. No external calls."""
import json
from unittest.mock import patch

import pytest

from larp.contracts import ContractError
from larp.runtime import gate_a, gate_a_check
from larp.strategy import self_check
from tests.runtime import test_fs1_standalone as standalone, test_gate_a
from tests.runtime.test_fs1_standalone import FINAL, prepare
from tests.runtime.test_gate_a import WALLET, terraform_output
from tools.deploy.build_selfcheck_temp import WINDOW
import render_host_configs

TEMP = dict(temp_self_check=True, run_id='larp-final-selfcheck-temp2', database_name='larp_final_selfcheck2')
# The temp window must start after the pinned quote measurement (2026-10-19T23:57Z) and end by the F-127 pause.
NOW = '2026-10-27T18:00:30Z'


@pytest.fixture(autouse=True)
def activation_time(monkeypatch):
    for module in (standalone, test_gate_a):
        monkeypatch.setattr(module, 'NOW', NOW)


def test_ts6_temp_preparation_uses_its_own_run_database_directories_and_stamped_profile():
    files = prepare(**TEMP)
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    runtime, profile = values['runtime.json'], values['strategy-profile.json']
    assert runtime['run_id'] == 'larp-final-selfcheck-temp2' and runtime['mode'] == 'live'
    assert all(values[n]['database_name'] == 'larp_final_selfcheck2' for n in
               ('runtime.json', 'uploader.json', 'operations.json'))
    directory = '/var/lib/larp-runtime/final-' + WALLET[2:] + '-selfcheck-temp2'
    assert (runtime['ai_seeds_dir'], runtime['nonce_dir']) == (directory + '/ai-seeds', directory + '/nonce')
    assert profile['policy_id'] == self_check.TEMP_POLICY_ID
    assert {k: profile['activation_self_check'][k] for k in WINDOW} == WINDOW  # W2 fixed window
    assert profile['activation_self_check']['pay_units'] < 1_000_000
    assert gate_a.digest(files['strategy-profile.json']) != gate_a.digest(FINAL.read_bytes())
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)


@pytest.mark.parametrize('changes', [
    dict(TEMP, run_id='larp-final-fs1'), dict(TEMP, database_name='larp_final'),
    dict(run_id='larp-final-selfcheck-temp2', database_name='larp_final_selfcheck2'),  # temp identity on FS1
    dict(TEMP, temp_self_check='yes')])
def test_ts6_temp_and_fs1_identities_never_mix(changes):
    with pytest.raises(ContractError):
        prepare(**changes)


def test_ts6_fs1_preparation_is_unchanged():
    files = prepare()
    assert files['strategy-profile.json'] == FINAL.read_bytes()
    assert json.loads(files['runtime.json'])['run_id'] == 'larp-final-fs1'


def test_ts6_cli_temp_mode_prints_the_stamped_window(tmp_path, monkeypatch, capsys):
    from tools.deploy import prepare_fs1
    import prepare_shadow
    prepared = prepare(**TEMP)
    capture = tmp_path / 'capture.json'; capture.write_bytes(prepared['input-capture.json'])
    history = tmp_path / 'history.json'; history.write_bytes(prepared['token-history.json'])
    terraform = tmp_path / 'terraform.json'; terraform.write_text(json.dumps(terraform_output()))
    monkeypatch.setattr(prepare_fs1, 'utc', lambda: NOW)
    monkeypatch.setattr(prepare_shadow, 'rpc_providers', lambda _: [dict(url='https://rpc.invalid/', source_id='synthetic-rpc')])
    monkeypatch.setattr(render_host_configs, 'ignored_by_git', lambda _: True)
    args = ['--terraform-output', str(terraform), '--wallet', WALLET, '--capture', str(capture),
        '--token-history-config', str(history), '--build-id', 'b' * 40, '--balance-rpc-config', 'synthetic-rpc.json',
        '--rds-ca-sha256', 'c' * 64, '--out', str(tmp_path / 'prepared'), '--model-adoption-ref', 'SYNTHETIC FINAL',
        '--temp-self-check']
    with patch('socket.socket', side_effect=AssertionError('No network')):
        assert prepare_fs1.main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['status'] == 'TEMP_SELF_CHECK_PREPARED_REQUIRES_APPROVAL' and report['signing_enabled'] is False
    assert report['run_id'] == 'larp-final-selfcheck-temp2' and report['activation_self_check']['pay_units'] == 900_000
    assert report['activation_self_check']['buy_after'] == '2026-10-28T07:00:00Z'
    written = (tmp_path / 'prepared/strategy-profile.json').read_bytes()
    assert report['profile_sha256'] == gate_a.digest(written) and written == prepared['strategy-profile.json']


def test_w2_2_preparation_at_different_times_gives_identical_profile_bytes():
    first = prepare(**TEMP)['strategy-profile.json']
    assert prepare(**TEMP, now='2026-10-27T18:04:00Z')['strategy-profile.json'] == first
    with pytest.raises(ContractError, match='window closed'):
        prepare(**TEMP, now='2026-10-28T08:30:00Z')
